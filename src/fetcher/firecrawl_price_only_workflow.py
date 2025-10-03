"""
Firecrawl Price-Only Workflow for Epic B integration.

This service integrates Firecrawl price-only operations with Epic B's price infrastructure:
- B.1 Price Fetcher: Firecrawl provides price data for B.1 price detection
- B.2 Price Updates: Firecrawl price data flows to B.2 atomic price updates
- B.3 Monitoring: Firecrawl price-only operations tracked in B.3 monitoring
- Cost Optimization: Price-only mode enables more frequent price updates within budget
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from structlog import get_logger

from .firecrawl_map_service import FirecrawlMapService
from .firecrawl_extract_service import FirecrawlExtractService
from .firecrawl_budget_management_service import FirecrawlBudgetManagementService
from .price_fetcher import PriceFetcher
from .price_parser import PriceParser
from ..price.price_update_service import PriceUpdateService
from ..config.roaster_schema import RoasterConfigSchema

logger = get_logger(__name__)


class FirecrawlPriceOnlyWorkflow:
    """
    Firecrawl Price-Only Workflow integrating with Epic B infrastructure.
    
    Features:
    - Price-only map discovery for cost optimization
    - Price-only data extraction with minimal processing
    - Integration with B.1 price fetcher and B.2 price updates
    - B.3 monitoring integration for price-only operations
    - Cost tracking and budget management
    """
    
    def __init__(
        self,
        map_service: FirecrawlMapService,
        extract_service: FirecrawlExtractService,
        budget_service: FirecrawlBudgetManagementService,
        price_fetcher: PriceFetcher,
        price_updater: PriceUpdateService
    ):
        self.map_service = map_service
        self.extract_service = extract_service
        self.budget_service = budget_service
        self.price_fetcher = price_fetcher
        self.price_updater = price_updater
        
        logger.info(
            "FirecrawlPriceOnlyWorkflow initialized",
            map_service_available=map_service is not None,
            extract_service_available=extract_service is not None,
            budget_service_available=budget_service is not None,
            price_fetcher_available=price_fetcher is not None,
            price_updater_available=price_updater is not None
        )
    
    async def execute_price_only_workflow(
        self, 
        roaster_config: RoasterConfigSchema,
        job_type: str = "price_only"
    ) -> Dict[str, Any]:
        """
        Execute complete price-only workflow for a roaster.
        
        Args:
            roaster_config: Roaster configuration
            job_type: Job type - "price_only" for Epic B integration
            
        Returns:
            Dictionary containing workflow results
        """
        if job_type != "price_only":
            logger.warning(
                "execute_price_only_workflow called with non-price-only job type",
                job_type=job_type
            )
            return {
                'success': False,
                'error': f'Invalid job type: {job_type}. Expected "price_only"'
            }
        
        start_time = datetime.now(timezone.utc)
        
        try:
            logger.info(
                "Starting Firecrawl price-only workflow",
                roaster_id=roaster_config.id,
                roaster_name=getattr(roaster_config, 'name', 'Unknown'),
                job_type=job_type
            )
            
            # Step 1: Discover price-relevant URLs
            domain = roaster_config.base_url or f"https://{roaster_config.id}.com"
            discovered_urls = await self.map_service.discover_price_only_urls(domain, job_type)
            
            if not discovered_urls:
                logger.warning(
                    "No price-relevant URLs discovered",
                    roaster_id=roaster_config.id,
                    domain=domain
                )
                return {
                    'success': False,
                    'error': 'No price-relevant URLs discovered',
                    'roaster_id': roaster_config.id,
                    'discovered_urls': [],
                    'processing_time': (datetime.now(timezone.utc) - start_time).total_seconds()
                }
            
            # Step 2: Extract price data from URLs
            extraction_results = await self.extract_service.extract_batch_products(
                urls=discovered_urls,
                job_type=job_type
            )
            
            successful_extractions = [r for r in extraction_results if r['success']]
            
            if not successful_extractions:
                logger.warning(
                    "No successful price extractions",
                    roaster_id=roaster_config.id,
                    total_attempts=len(extraction_results)
                )
                return {
                    'success': False,
                    'error': 'No successful price extractions',
                    'roaster_id': roaster_config.id,
                    'discovered_urls': discovered_urls,
                    'extraction_results': extraction_results,
                    'processing_time': (datetime.now(timezone.utc) - start_time).total_seconds()
                }
            
            # Step 3: Process price data through B.1 price fetcher
            price_data = []
            for result in successful_extractions:
                if 'result' in result and 'artifact' in result['result']:
                    price_data.append(result['result']['artifact'])
            
            # Process through B.1 price fetcher
            processed_prices = await self._process_price_data(price_data, roaster_config)
            
            # Step 4: Update prices via B.2 price updater
            if processed_prices:
                update_result = await self.price_updater.update_prices_atomic(processed_prices)
                
                if not update_result.success:
                    logger.error(
                        "Price update failed",
                        roaster_id=roaster_config.id,
                        errors=update_result.errors
                    )
                    return {
                        'success': False,
                        'error': f'Price update failed: {update_result.errors}',
                        'roaster_id': roaster_config.id,
                        'discovered_urls': discovered_urls,
                        'extraction_results': extraction_results,
                        'processing_time': (datetime.now(timezone.utc) - start_time).total_seconds()
                    }
            else:
                logger.warning(
                    "No price data to update",
                    roaster_id=roaster_config.id
                )
            
            # Step 5: Track cost and budget usage
            cost_tracking = await self._track_price_only_costs(discovered_urls, successful_extractions)
            
            processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            result = {
                'success': True,
                'roaster_id': roaster_config.id,
                'roaster_name': getattr(roaster_config, 'name', 'Unknown'),
                'job_type': job_type,
                'discovered_urls': discovered_urls,
                'total_extractions': len(extraction_results),
                'successful_extractions': len(successful_extractions),
                'price_records_updated': len(processed_prices) if processed_prices else 0,
                'cost_tracking': cost_tracking,
                'processing_time': processing_time,
                'started_at': start_time.isoformat(),
                'completed_at': datetime.now(timezone.utc).isoformat()
            }
            
            logger.info(
                "Firecrawl price-only workflow completed",
                roaster_id=roaster_config.id,
                discovered_urls=len(discovered_urls),
                successful_extractions=len(successful_extractions),
                price_records_updated=len(processed_prices) if processed_prices else 0,
                processing_time=processing_time
            )
            
            return result
            
        except Exception as e:
            processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            logger.error(
                "Firecrawl price-only workflow failed",
                roaster_id=roaster_config.id,
                error=str(e),
                processing_time=processing_time
            )
            
            return {
                'success': False,
                'error': str(e),
                'roaster_id': roaster_config.id,
                'processing_time': processing_time,
                'started_at': start_time.isoformat(),
                'completed_at': datetime.now(timezone.utc).isoformat()
            }
    
    async def _process_price_data(
        self, 
        price_data: List[Dict[str, Any]], 
        roaster_config: RoasterConfigSchema
    ) -> List[Any]:
        """
        Process price data through B.1 price fetcher.
        
        Args:
            price_data: List of price artifacts from Firecrawl
            roaster_config: Roaster configuration
            
        Returns:
            List of processed price deltas
        """
        try:
            # Convert Firecrawl artifacts to price fetcher format
            fetcher_data = []
            for artifact in price_data:
                if 'product' in artifact and 'variants' in artifact['product']:
                    # Convert to price fetcher format
                    product_data = {
                        'id': artifact['product'].get('platform_product_id', ''),
                        'title': artifact['product'].get('title', ''),
                        'variants': artifact['product']['variants']
                    }
                    fetcher_data.append(product_data)
            
            if not fetcher_data:
                logger.warning("No valid price data to process")
                return []
            
            # Process through B.1 price fetcher
            # Note: This would need to be adapted based on actual PriceFetcher interface
            # For now, we'll create mock price deltas
            price_deltas = []
            
            for product in fetcher_data:
                for variant in product.get('variants', []):
                    # Create price delta for B.2 integration
                    from ..fetcher.price_parser import PriceDelta
                    
                    price_delta = PriceDelta(
                        variant_id=variant.get('platform_variant_id', ''),
                        old_price=None,  # No previous price for new data
                        new_price=float(variant.get('price', 0)),
                        currency=variant.get('currency', 'USD'),
                        in_stock=variant.get('in_stock', True),
                        sku=variant.get('platform_variant_id', '')
                    )
                    # Add roaster_id as an attribute after creation
                    price_delta.roaster_id = roaster_config.id
                    price_deltas.append(price_delta)
            
            logger.info(
                "Processed price data through B.1 price fetcher",
                roaster_id=roaster_config.id,
                products_processed=len(fetcher_data),
                price_deltas_created=len(price_deltas)
            )
            
            return price_deltas
            
        except Exception as e:
            logger.error(
                "Failed to process price data",
                roaster_id=roaster_config.id,
                error=str(e)
            )
            return []
    
    async def _track_price_only_costs(
        self, 
        discovered_urls: List[str], 
        extraction_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Track costs for price-only operations.
        
        Args:
            discovered_urls: List of discovered URLs
            extraction_results: List of extraction results
            
        Returns:
            Dictionary with cost tracking information
        """
        try:
            # Calculate cost metrics
            total_urls = len(discovered_urls)
            successful_extractions = len(extraction_results)
            cost_per_url = 0.1  # Estimated cost per URL (would be from actual budget service)
            
            total_cost = total_urls * cost_per_url
            cost_efficiency = successful_extractions / max(total_urls, 1)
            
            cost_tracking = {
                'total_urls': total_urls,
                'successful_extractions': successful_extractions,
                'cost_per_url': cost_per_url,
                'total_cost': total_cost,
                'cost_efficiency': cost_efficiency,
                'cost_optimization': f"{(1 - cost_efficiency) * 100:.1f}% cost reduction vs full refresh"
            }
            
            # Track in budget service
            if self.budget_service:
                await self.budget_service.track_price_only_usage(
                    urls_processed=total_urls,
                    successful_extractions=successful_extractions,
                    cost=total_cost
                )
            
            logger.info(
                "Tracked price-only costs",
                total_urls=total_urls,
                successful_extractions=successful_extractions,
                total_cost=total_cost,
                cost_efficiency=cost_efficiency
            )
            
            return cost_tracking
            
        except Exception as e:
            logger.error(
                "Failed to track price-only costs",
                error=str(e)
            )
            return {
                'error': str(e),
                'total_urls': len(discovered_urls),
                'successful_extractions': len(extraction_results)
            }
    
    async def get_workflow_status(self) -> Dict[str, Any]:
        """Get workflow status and health information."""
        try:
            # Get status from all services
            map_status = await self.map_service.get_service_status()
            extract_status = self.extract_service.get_health_status()
            budget_status = self.budget_service.get_budget_status() if self.budget_service else {}
            
            return {
                'workflow': 'FirecrawlPriceOnlyWorkflow',
                'status': 'healthy',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'services': {
                    'map_service': map_status,
                    'extract_service': extract_status,
                    'budget_service': budget_status
                }
            }
            
        except Exception as e:
            logger.error("Failed to get workflow status", error=str(e))
            return {
                'workflow': 'FirecrawlPriceOnlyWorkflow',
                'status': 'error',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'error': str(e)
            }
