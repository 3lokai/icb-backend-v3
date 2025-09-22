"""
Price integration service for B.1 → B.2 pipeline.
Connects B.1 price fetcher with B.2 update service for end-to-end price updates.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from structlog import get_logger

from .price_update_service import PriceUpdateService, PriceUpdateResult
from .variant_update_service import VariantUpdateService
from ..fetcher.price_fetcher import PriceFetcher
from ..fetcher.price_parser import PriceDelta

logger = get_logger(__name__)


class PriceIntegrationService:
    """
    Integration service for B.1 → B.2 price update pipeline.
    
    Features:
    - Connects B.1 price fetcher with B.2 update service
    - End-to-end price update pipeline
    - Performance monitoring and metrics
    - Error handling and recovery
    """
    
    def __init__(
        self,
        supabase_client=None,
        price_fetcher: Optional[PriceFetcher] = None,
        price_update_service: Optional[PriceUpdateService] = None,
        variant_update_service: Optional[VariantUpdateService] = None
    ):
        """
        Initialize price integration service.
        
        Args:
            supabase_client: Supabase client for database operations
            price_fetcher: B.1 price fetcher (optional)
            price_update_service: B.2 price update service (optional)
            variant_update_service: B.2 variant update service (optional)
        """
        self.supabase_client = supabase_client
        
        # Initialize services
        self.price_fetcher = price_fetcher
        self.price_update_service = price_update_service or PriceUpdateService(supabase_client=supabase_client)
        self.variant_update_service = variant_update_service or VariantUpdateService(supabase_client=supabase_client)
        
        # Integration statistics
        self.integration_stats = {
            'total_jobs': 0,
            'successful_jobs': 0,
            'failed_jobs': 0,
            'total_deltas_processed': 0,
            'total_price_records_inserted': 0,
            'total_variant_records_updated': 0,
            'start_time': None,
            'end_time': None
        }
        
        logger.info("Initialized price integration service")
    
    async def run_price_update_job(
        self,
        roaster_id: str,
        platform: str = "shopify",
        limit: int = 50,
        page: int = 1
    ) -> Dict[str, Any]:
        """
        Run complete B.1 → B.2 price update job.
        
        Args:
            roaster_id: Roaster identifier
            platform: Platform type (shopify, woocommerce)
            limit: Number of products to fetch
            page: Page number for pagination
            
        Returns:
            Dictionary with job results
        """
        start_time = datetime.now(timezone.utc)
        self.integration_stats['start_time'] = start_time
        self.integration_stats['total_jobs'] += 1
        
        logger.info(
            "Starting price update job",
            roaster_id=roaster_id,
            platform=platform,
            limit=limit,
            page=page
        )
        
        try:
            # Step 1: B.1 - Fetch price data and detect deltas
            price_deltas = await self._fetch_and_detect_price_deltas(
                roaster_id=roaster_id,
                platform=platform,
                limit=limit,
                page=page
            )
            
            if not price_deltas:
                logger.info(
                    "No price changes detected",
                    roaster_id=roaster_id,
                    platform=platform
                )
                
                self.integration_stats['successful_jobs'] += 1
                self.integration_stats['end_time'] = datetime.now(timezone.utc)
                
                return {
                    'roaster_id': roaster_id,
                    'platform': platform,
                    'success': True,
                    'price_deltas_found': 0,
                    'price_records_inserted': 0,
                    'variant_records_updated': 0,
                    'processing_time_seconds': (datetime.now(timezone.utc) - start_time).total_seconds(),
                    'message': 'No price changes detected'
                }
            
            # Step 2: B.2 - Update prices atomically
            update_result = await self.price_update_service.update_prices_atomic(price_deltas)
            
            if not update_result.success:
                self.integration_stats['failed_jobs'] += 1
                self.integration_stats['end_time'] = datetime.now(timezone.utc)
                
                logger.error(
                    "Price update job failed",
                    roaster_id=roaster_id,
                    platform=platform,
                    errors=update_result.errors
                )
                
                return {
                    'roaster_id': roaster_id,
                    'platform': platform,
                    'success': False,
                    'price_deltas_found': len(price_deltas),
                    'price_records_inserted': 0,
                    'variant_records_updated': 0,
                    'processing_time_seconds': (datetime.now(timezone.utc) - start_time).total_seconds(),
                    'errors': update_result.errors
                }
            
            # Update integration statistics
            self.integration_stats['successful_jobs'] += 1
            self.integration_stats['total_deltas_processed'] += len(price_deltas)
            self.integration_stats['total_price_records_inserted'] += len(update_result.price_ids)
            self.integration_stats['total_variant_records_updated'] += update_result.variant_updates
            self.integration_stats['end_time'] = datetime.now(timezone.utc)
            
            processing_time = (self.integration_stats['end_time'] - start_time).total_seconds()
            
            logger.info(
                "Completed price update job",
                roaster_id=roaster_id,
                platform=platform,
                price_deltas_found=len(price_deltas),
                price_records_inserted=len(update_result.price_ids),
                variant_records_updated=update_result.variant_updates,
                processing_time_seconds=processing_time
            )
            
            return {
                'roaster_id': roaster_id,
                'platform': platform,
                'success': True,
                'price_deltas_found': len(price_deltas),
                'price_records_inserted': len(update_result.price_ids),
                'variant_records_updated': update_result.variant_updates,
                'price_ids': update_result.price_ids,
                'processing_time_seconds': processing_time,
                'price_update_result': update_result
            }
            
        except Exception as e:
            self.integration_stats['failed_jobs'] += 1
            self.integration_stats['end_time'] = datetime.now(timezone.utc)
            
            error_msg = f"Price update job failed: {str(e)}"
            logger.error(
                "Price update job failed with exception",
                roaster_id=roaster_id,
                platform=platform,
                error=error_msg
            )
            
            return {
                'roaster_id': roaster_id,
                'platform': platform,
                'success': False,
                'price_deltas_found': 0,
                'price_records_inserted': 0,
                'variant_records_updated': 0,
                'processing_time_seconds': (datetime.now(timezone.utc) - start_time).total_seconds(),
                'error': error_msg
            }
    
    async def _fetch_and_detect_price_deltas(
        self,
        roaster_id: str,
        platform: str,
        limit: int,
        page: int
    ) -> List[PriceDelta]:
        """
        Fetch price data and detect deltas using B.1 price fetcher.
        
        Args:
            roaster_id: Roaster identifier
            platform: Platform type
            limit: Number of products to fetch
            page: Page number
            
        Returns:
            List of price deltas
        """
        if not self.price_fetcher:
            logger.warning(
                "No price fetcher available, returning empty deltas",
                roaster_id=roaster_id,
                platform=platform
            )
            return []
        
        try:
            # Fetch price data using B.1 price fetcher
            fetch_result = await self.price_fetcher.fetch_price_data(
                limit=limit,
                page=page
            )
            
            if not fetch_result.get('success', False):
                logger.error(
                    "Price fetch failed",
                    roaster_id=roaster_id,
                    platform=platform,
                    error=fetch_result.get('error', 'Unknown error')
                )
                return []
            
            price_data = fetch_result.get('price_data', [])
            if not price_data:
                logger.info(
                    "No price data fetched",
                    roaster_id=roaster_id,
                    platform=platform
                )
                return []
            
            # Get existing variants for comparison
            existing_variants = await self._get_existing_variants(roaster_id)
            
            # Detect price deltas
            price_deltas = await self.price_fetcher.detect_and_report_deltas(
                fetched_data=price_data,
                existing_variants=existing_variants
            )
            
            logger.info(
                "Detected price deltas",
                roaster_id=roaster_id,
                platform=platform,
                deltas_found=len(price_deltas)
            )
            
            return price_deltas
            
        except Exception as e:
            logger.error(
                "Failed to fetch and detect price deltas",
                roaster_id=roaster_id,
                platform=platform,
                error=str(e)
            )
            return []
    
    async def _get_existing_variants(self, roaster_id: str) -> List[Dict[str, Any]]:
        """
        Get existing variants from database for price comparison.
        
        Args:
            roaster_id: Roaster identifier
            
        Returns:
            List of existing variant data
        """
        try:
            if not self.supabase_client:
                logger.warning("No Supabase client available for existing variants")
                return []
            
            # Query existing variants for the roaster
            result = self.supabase_client.table("variants").select(
                "id, platform_variant_id, price_current, currency, in_stock"
            ).eq("roaster_id", roaster_id).execute()
            
            if result.data:
                logger.info(
                    "Retrieved existing variants",
                    roaster_id=roaster_id,
                    variant_count=len(result.data)
                )
                return result.data
            else:
                logger.info(
                    "No existing variants found",
                    roaster_id=roaster_id
                )
                return []
                
        except Exception as e:
            logger.error(
                "Failed to get existing variants",
                roaster_id=roaster_id,
                error=str(e)
            )
            return []
    
    def get_integration_stats(self) -> Dict[str, Any]:
        """
        Get integration service statistics.
        
        Returns:
            Dictionary with integration statistics
        """
        stats = self.integration_stats.copy()
        
        # Calculate success rate
        if stats['total_jobs'] > 0:
            stats['success_rate'] = stats['successful_jobs'] / stats['total_jobs']
            stats['failure_rate'] = stats['failed_jobs'] / stats['total_jobs']
        else:
            stats['success_rate'] = 0.0
            stats['failure_rate'] = 0.0
        
        # Add processing time
        if stats['start_time'] and stats['end_time']:
            stats['total_processing_time'] = (
                stats['end_time'] - stats['start_time']
            ).total_seconds()
        else:
            stats['total_processing_time'] = 0.0
        
        # Add service stats
        stats['price_update_stats'] = self.price_update_service.get_update_stats()
        stats['variant_update_stats'] = self.variant_update_service.get_variant_stats()
        
        return stats
    
    def reset_integration_stats(self):
        """Reset integration service statistics."""
        self.integration_stats = {
            'total_jobs': 0,
            'successful_jobs': 0,
            'failed_jobs': 0,
            'total_deltas_processed': 0,
            'total_price_records_inserted': 0,
            'total_variant_records_updated': 0,
            'start_time': None,
            'end_time': None
        }
        
        # Reset service stats
        self.price_update_service.reset_stats()
        self.variant_update_service.reset_stats()
        
        logger.info("Reset integration service statistics")
