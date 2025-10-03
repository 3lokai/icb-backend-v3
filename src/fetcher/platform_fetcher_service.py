"""
Platform-based fetcher service with intelligent cascade logic.

This module implements:
- Platform detection and fetcher selection
- Intelligent cascade: Shopify → WooCommerce → Firecrawl
- Platform field updates when successful fetcher is determined
- Cost optimization with Firecrawl as fallback only
"""

import asyncio
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum

import structlog

from .base_fetcher import FetcherConfig
from .shopify_fetcher import ShopifyFetcher
from .woocommerce_fetcher import WooCommerceFetcher
from .firecrawl_map_service import FirecrawlMapService
from .firecrawl_client import FirecrawlClient
from ..config.roaster_schema import RoasterConfigSchema
from ..config.firecrawl_config import FirecrawlConfig

logger = structlog.get_logger(__name__)


class FetcherResult:
    """Result from fetcher execution."""
    
    def __init__(
        self,
        success: bool,
        platform: str,
        products: List[Dict[str, Any]] = None,
        error: Optional[str] = None,
        should_update_platform: bool = False
    ):
        self.success = success
        self.platform = platform
        self.products = products or []
        self.error = error
        self.should_update_platform = should_update_platform


class PlatformFetcherService:
    """
    Platform-based fetcher service with intelligent cascade logic.
    
    Features:
    - Automatic platform detection
    - Intelligent cascade: Shopify → WooCommerce → Firecrawl
    - Platform field updates when successful fetcher is determined
    - Cost optimization with Firecrawl as fallback only
    """
    
    def __init__(
        self,
        roaster_config: RoasterConfigSchema,
        fetcher_config: FetcherConfig,
        firecrawl_config: Optional[FirecrawlConfig] = None
    ):
        self.roaster_config = roaster_config
        self.fetcher_config = fetcher_config
        self.firecrawl_config = firecrawl_config
        
        # Initialize fetchers
        self.shopify_fetcher = None
        self.woocommerce_fetcher = None
        self.firecrawl_service = None
        
        logger.info(
            "Initialized platform fetcher service",
            roaster_id=roaster_config.id,
            current_platform=roaster_config.platform,
            base_url=roaster_config.base_url
        )
    
    async def fetch_products_with_cascade(
        self,
        job_type: str = "full_refresh",
        **kwargs
    ) -> FetcherResult:
        """
        Fetch products using intelligent platform cascade.
        
        Args:
            job_type: Type of job (full_refresh, price_only)
            **kwargs: Additional parameters for fetchers
            
        Returns:
            FetcherResult with success status and products
        """
        logger.info(
            "Starting platform-based product fetch",
            roaster_id=self.roaster_config.id,
            current_platform=self.roaster_config.platform,
            job_type=job_type
        )
        
        # Determine fetcher sequence based on current platform
        fetcher_sequence = self._get_fetcher_sequence()
        
        for platform, fetcher in fetcher_sequence:
            try:
                logger.info(
                    "Attempting fetcher",
                    roaster_id=self.roaster_config.id,
                    platform=platform,
                    fetcher_type=type(fetcher).__name__
                )
                
                # Execute fetcher
                if platform == "shopify":
                    result = await self._execute_shopify_fetcher(fetcher, job_type, **kwargs)
                elif platform == "woocommerce":
                    result = await self._execute_woocommerce_fetcher(fetcher, job_type, **kwargs)
                elif platform == "firecrawl":
                    result = await self._execute_firecrawl_fetcher(fetcher, job_type, **kwargs)
                else:
                    logger.error(f"Unknown platform: {platform}")
                    continue
                
                if result.success:
                    logger.info(
                        "Fetcher succeeded",
                        roaster_id=self.roaster_config.id,
                        platform=platform,
                        products_count=len(result.products)
                    )
                    return result
                else:
                    logger.warning(
                        "Fetcher failed, trying next",
                        roaster_id=self.roaster_config.id,
                        platform=platform,
                        error=result.error
                    )
                    
            except Exception as e:
                logger.error(
                    "Fetcher execution error",
                    roaster_id=self.roaster_config.id,
                    platform=platform,
                    error=str(e),
                    exc_info=True
                )
                continue
        
        # All standard fetchers failed - trigger Firecrawl fallback
        logger.info(
            "Standard fetchers failed, triggering Firecrawl fallback",
            roaster_id=self.roaster_config.id,
            attempted_platforms=[p for p, _ in fetcher_sequence]
        )
        
        # Trigger Firecrawl fallback
        firecrawl_result = await self._trigger_firecrawl_fallback(job_type, **kwargs)
        
        if firecrawl_result.success:
            logger.info(
                "Firecrawl fallback succeeded",
                roaster_id=self.roaster_config.id,
                products_count=len(firecrawl_result.products)
            )
            return firecrawl_result
        else:
            logger.error(
                "Firecrawl fallback also failed",
                roaster_id=self.roaster_config.id,
                firecrawl_error=firecrawl_result.error
            )
            
            return FetcherResult(
                success=False,
                platform="unknown",
                error=f"All fetchers failed including Firecrawl: {firecrawl_result.error}"
            )
    
    def _get_fetcher_sequence(self) -> List[Tuple[str, Any]]:
        """
        Get the sequence of fetchers to try based on current platform.
        
        Returns:
            List of (platform, fetcher) tuples in order of preference
        """
        sequence = []
        
        # If platform is already known, try it first
        if self.roaster_config.platform:
            if self.roaster_config.platform == "shopify":
                sequence.append(("shopify", self._get_shopify_fetcher()))
            elif self.roaster_config.platform == "woocommerce":
                sequence.append(("woocommerce", self._get_woocommerce_fetcher()))
            elif self.roaster_config.platform in ["custom", "other"]:
                # For custom/other platforms, go straight to Firecrawl
                sequence.append(("firecrawl", self._get_firecrawl_service()))
        
        # Add cascade sequence for unknown platforms or after known platform fails
        if not self.roaster_config.platform or self.roaster_config.platform not in ["custom", "other"]:
            # Try Shopify first (fastest, cheapest)
            if not any(p == "shopify" for p, _ in sequence):
                sequence.append(("shopify", self._get_shopify_fetcher()))
            
            # Try WooCommerce second
            if not any(p == "woocommerce" for p, _ in sequence):
                sequence.append(("woocommerce", self._get_woocommerce_fetcher()))
        
        # Always try Firecrawl as final fallback
        if not any(p == "firecrawl" for p, _ in sequence):
            sequence.append(("firecrawl", self._get_firecrawl_service()))
        
        return sequence
    
    def _get_shopify_fetcher(self) -> ShopifyFetcher:
        """Get or create Shopify fetcher."""
        if self.shopify_fetcher is None:
            self.shopify_fetcher = ShopifyFetcher(
                config=self.fetcher_config,
                roaster_id=self.roaster_config.id,
                base_url=self.roaster_config.base_url or f"https://{self.roaster_config.id}.com",
                job_type="full_refresh"  # Will be overridden in execution
            )
        return self.shopify_fetcher
    
    def _get_woocommerce_fetcher(self) -> WooCommerceFetcher:
        """Get or create WooCommerce fetcher."""
        if self.woocommerce_fetcher is None:
            self.woocommerce_fetcher = WooCommerceFetcher(
                config=self.fetcher_config,
                roaster_id=self.roaster_config.id,
                base_url=self.roaster_config.base_url or f"https://{self.roaster_config.id}.com",
                job_type="full_refresh"  # Will be overridden in execution
            )
        return self.woocommerce_fetcher
    
    def _get_firecrawl_service(self) -> FirecrawlMapService:
        """Get or create Firecrawl service."""
        if self.firecrawl_service is None:
            if self.firecrawl_config is None:
                # Create default Firecrawl config
                self.firecrawl_config = FirecrawlConfig(
                    budget_limit=self.roaster_config.firecrawl_budget_limit,
                    max_pages=50,
                    include_subdomains=False,
                    sitemap_only=False,
                    coffee_keywords=[
                        'coffee', 'bean', 'roast', 'brew', 'espresso',
                        'latte', 'cappuccino', 'mocha', 'americano'
                    ],
                    timeout=30.0,
                    max_retries=3,
                    retry_delay=1.0,
                    enable_monitoring=True,
                    log_level='INFO'
                )
            
            firecrawl_client = FirecrawlClient(self.firecrawl_config)
            self.firecrawl_service = FirecrawlMapService(firecrawl_client)
        
        return self.firecrawl_service
    
    async def _execute_shopify_fetcher(
        self,
        fetcher: ShopifyFetcher,
        job_type: str,
        **kwargs
    ) -> FetcherResult:
        """Execute Shopify fetcher."""
        try:
            # Test connection first
            if not await fetcher.test_connection():
                return FetcherResult(
                    success=False,
                    platform="shopify",
                    error="Connection test failed"
                )
            
            # Fetch products based on job type
            if job_type == "price_only":
                products = await fetcher.fetch_price_only_all_products(**kwargs)
            else:
                products = await fetcher.fetch_all_products(**kwargs)
            
            if products:
                return FetcherResult(
                    success=True,
                    platform="shopify",
                    products=products,
                    should_update_platform=True  # Update platform field when Shopify succeeds
                )
            else:
                return FetcherResult(
                    success=False,
                    platform="shopify",
                    error="No products returned"
                )
                
        except Exception as e:
            return FetcherResult(
                success=False,
                platform="shopify",
                error=str(e)
            )
    
    async def _execute_woocommerce_fetcher(
        self,
        fetcher: WooCommerceFetcher,
        job_type: str,
        **kwargs
    ) -> FetcherResult:
        """Execute WooCommerce fetcher."""
        try:
            # Test connection first
            if not await fetcher.test_connection():
                return FetcherResult(
                    success=False,
                    platform="woocommerce",
                    error="Connection test failed"
                )
            
            # Fetch products based on job type
            if job_type == "price_only":
                products = await fetcher.fetch_price_only_all_products(**kwargs)
            else:
                products = await fetcher.fetch_all_products(**kwargs)
            
            if products:
                return FetcherResult(
                    success=True,
                    platform="woocommerce",
                    products=products,
                    should_update_platform=True  # Update platform field when WooCommerce succeeds
                )
            else:
                return FetcherResult(
                    success=False,
                    platform="woocommerce",
                    error="No products returned"
                )
                
        except Exception as e:
            return FetcherResult(
                success=False,
                platform="woocommerce",
                error=str(e)
            )
    
    async def _execute_firecrawl_fetcher(
        self,
        service: FirecrawlMapService,
        job_type: str,
        **kwargs
    ) -> FetcherResult:
        """Execute Firecrawl fetcher."""
        try:
            # Execute Firecrawl map discovery with Epic B job type support
            result = await service.discover_roaster_products(
                roaster_config=self.roaster_config,
                search_terms=kwargs.get('search_terms'),
                job_type=job_type
            )
            
            if result.get('status') == 'success' and result.get('discovered_urls'):
                # Convert discovered URLs to product-like format for consistency
                products = [
                    {
                        'id': f"firecrawl_{i}",
                        'title': f"Discovered Product {i+1}",
                        'url': url,
                        'source': 'firecrawl',
                        'discovered_at': result.get('discovered_at')
                    }
                    for i, url in enumerate(result.get('discovered_urls', []))
                ]
                
                return FetcherResult(
                    success=True,
                    platform="firecrawl",
                    products=products,
                    should_update_platform=False  # Don't update platform field for Firecrawl
                )
            else:
                return FetcherResult(
                    success=False,
                    platform="firecrawl",
                    error=result.get('error', 'Firecrawl discovery failed')
                )
                
        except Exception as e:
            return FetcherResult(
                success=False,
                platform="firecrawl",
                error=str(e)
            )
    
    async def _trigger_firecrawl_fallback(self, job_type: str, **job_data: Any) -> FetcherResult:
        """
        Trigger Firecrawl fallback when standard fetchers fail.
        
        Args:
            job_type: Type of job being executed
            **job_data: Additional job data
            
        Returns:
            FetcherResult from Firecrawl fallback
        """
        logger.info(
            "Triggering Firecrawl fallback",
            roaster_id=self.roaster_config.id,
            job_type=job_type
        )
        
        try:
            # Create Firecrawl job data for fallback
            firecrawl_job_data = {
                'id': f"firecrawl_fallback_{self.roaster_config.id}_{job_type}",
                'roaster_id': self.roaster_config.id,
                'data': {
                    'job_type': 'firecrawl_map',
                    'fallback_reason': 'standard_fetchers_failed',
                    'search_terms': job_data.get('search_terms')
                }
            }
            
            # Create Firecrawl configuration
            firecrawl_config = {
                'FIRECRAWL_API_KEY': getattr(self.firecrawl_config, 'api_key', ''),
                'FIRECRAWL_BASE_URL': getattr(self.firecrawl_config, 'base_url', 'https://api.firecrawl.dev'),
                'FIRECRAWL_BUDGET_LIMIT': self.roaster_config.firecrawl_budget_limit,
                'FIRECRAWL_MAX_PAGES': getattr(self.firecrawl_config, 'max_pages', 50),
                'FIRECRAWL_INCLUDE_SUBDOMAINS': getattr(self.firecrawl_config, 'include_subdomains', False),
                'FIRECRAWL_SITEMAP_ONLY': getattr(self.firecrawl_config, 'sitemap_only', False),
                'FIRECRAWL_COFFEE_KEYWORDS': getattr(self.firecrawl_config, 'coffee_keywords', []),
                'FIRECRAWL_TIMEOUT': getattr(self.firecrawl_config, 'timeout', 30.0),
                'FIRECRAWL_MAX_RETRIES': getattr(self.firecrawl_config, 'max_retries', 3),
                'FIRECRAWL_RETRY_DELAY': getattr(self.firecrawl_config, 'retry_delay', 1.0),
                'FIRECRAWL_ENABLE_MONITORING': getattr(self.firecrawl_config, 'enable_monitoring', True),
                'FIRECRAWL_LOG_LEVEL': getattr(self.firecrawl_config, 'log_level', 'INFO'),
                'roaster_name': self.roaster_config.name,
                'base_url': self.roaster_config.base_url,
                'platform': self.roaster_config.platform,
                'use_firecrawl_fallback': True,
                'firecrawl_budget_limit': self.roaster_config.firecrawl_budget_limit
            }
            
            # Import and execute Firecrawl job
            from ..worker.tasks import execute_firecrawl_map_job
            
            # Execute Firecrawl fallback job
            firecrawl_result = await execute_firecrawl_map_job(firecrawl_job_data, firecrawl_config)
            
            if firecrawl_result.get('status') == 'completed':
                # Convert Firecrawl result to FetcherResult
                discovered_urls = firecrawl_result.get('discovered_urls', [])
                
                # For now, return discovered URLs as "products" (in real implementation, 
                # these would be processed through the full Firecrawl pipeline)
                products = []
                for url in discovered_urls:
                    products.append({
                        'url': url,
                        'source': 'firecrawl_fallback',
                        'discovered_at': firecrawl_result.get('processed_at')
                    })
                
                return FetcherResult(
                    success=True,
                    products=products,
                    platform='firecrawl',
                    should_update_platform=False,  # Don't update platform for Firecrawl
                    error=None
                )
            else:
                return FetcherResult(
                    success=False,
                    products=[],
                    platform='firecrawl',
                    should_update_platform=False,
                    error=firecrawl_result.get('error', 'Firecrawl fallback failed')
                )
                
        except Exception as e:
            logger.error(
                "Firecrawl fallback trigger failed",
                roaster_id=self.roaster_config.id,
                error=str(e),
                exc_info=True
            )
            
            return FetcherResult(
                success=False,
                products=[],
                platform='firecrawl',
                should_update_platform=False,
                error=f"Firecrawl fallback trigger failed: {str(e)}"
            )

    async def close(self):
        """Close all fetcher connections."""
        if self.shopify_fetcher:
            await self.shopify_fetcher.__aexit__(None, None, None)
        if self.woocommerce_fetcher:
            await self.woocommerce_fetcher.__aexit__(None, None, None)
        if self.firecrawl_service:
            # Firecrawl service doesn't need explicit closing
            pass
