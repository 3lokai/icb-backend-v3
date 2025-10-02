"""
Price-only fetcher for lightweight price updates.
Extends existing fetcher infrastructure with price-only mode.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from structlog import get_logger

from .base_fetcher import BaseFetcher, FetcherConfig
from .price_parser import PriceParser, PriceDelta
from .shopify_fetcher import ShopifyFetcher
from .woocommerce_fetcher import WooCommerceFetcher
from .encoding_utils import safe_decode_json

logger = get_logger(__name__)


class PriceFetcher:
    """
    Price-only fetcher that extends existing fetcher infrastructure.
    
    Features:
    - Lightweight price-only fetching from list endpoints
    - Fallback to per-product fetching for missing endpoints
    - Price delta detection and comparison
    - Performance optimization for speed
    """
    
    def __init__(
        self,
        base_fetcher: BaseFetcher,
        price_parser: Optional[PriceParser] = None,
        supabase_client=None,
    ):
        self.base_fetcher = base_fetcher
        self.price_parser = price_parser or PriceParser(job_type="price_only")
        self.supabase_client = supabase_client
        self.roaster_id = base_fetcher.roaster_id
        self.platform = base_fetcher.platform
        self.job_type = base_fetcher.job_type
        
        logger.info(
            "Initialized price fetcher",
            roaster_id=self.roaster_id,
            platform=self.platform,
            job_type=self.job_type,
        )
    
    async def fetch_price_data(
        self,
        limit: int = 50,
        page: int = 1,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Fetch price-only data from the platform.
        
        Args:
            limit: Number of products per page
            page: Page number
            **kwargs: Additional fetch parameters
            
        Returns:
            Dictionary with price data and metadata
        """
        start_time = datetime.now(timezone.utc)
        
        try:
            logger.info(
                "Starting price-only fetch",
                roaster_id=self.roaster_id,
                platform=self.platform,
                limit=limit,
                page=page,
            )
            
            # Check if list endpoint is available
            if await self._check_list_endpoint_availability():
                # Use list endpoint for price data
                products = await self._fetch_from_list_endpoint(limit, page, **kwargs)
            else:
                # Fallback to per-product fetching
                products = await self._fetch_per_product(**kwargs)
            
            # Extract price data from products
            price_data = []
            for product in products:
                extracted = self.price_parser.extract_price_data(product)
                if extracted and extracted.get('variants'):
                    price_data.append(extracted)
            
            # Calculate performance metrics
            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            result = {
                'roaster_id': self.roaster_id,
                'platform': self.platform,
                'job_type': self.job_type,
                'products_processed': len(products),
                'price_data_extracted': len(price_data),
                'duration_seconds': duration,
                'price_data': price_data,
                'started_at': start_time.isoformat(),
                'completed_at': datetime.now(timezone.utc).isoformat(),
                'success': True,
            }
            
            logger.info(
                "Completed price-only fetch",
                roaster_id=self.roaster_id,
                products_processed=len(products),
                price_data_extracted=len(price_data),
                duration_seconds=duration,
            )
            
            return result
            
        except Exception as e:
            error_msg = str(e)
            logger.error(
                "Failed price-only fetch",
                roaster_id=self.roaster_id,
                error=error_msg,
                duration_seconds=(datetime.now(timezone.utc) - start_time).total_seconds(),
            )
            
            return {
                'roaster_id': self.roaster_id,
                'platform': self.platform,
                'job_type': self.job_type,
                'products_processed': 0,
                'price_data_extracted': 0,
                'success': False,
                'error': error_msg,
                'started_at': start_time.isoformat(),
                'completed_at': datetime.now(timezone.utc).isoformat(),
            }
    
    async def _check_list_endpoint_availability(self) -> bool:
        """
        Check if the list endpoint is available and responding.
        
        Returns:
            True if endpoint is available, False otherwise
        """
        try:
            # Try to make a minimal request to test endpoint
            if hasattr(self.base_fetcher, '_build_products_url'):
                url = self.base_fetcher._build_products_url()
            else:
                # Fallback URL construction
                url = f"{self.base_fetcher.base_url}/products.json"
            
            status_code, headers, content = await self.base_fetcher._make_request(
                url=url,
                params={'limit': 1},  # Minimal request
                use_cache=False,  # Don't use cache for availability check
            )
            
            is_available = status_code == 200
            logger.info(
                "Checked list endpoint availability",
                roaster_id=self.roaster_id,
                url=url,
                status_code=status_code,
                available=is_available,
            )
            
            return is_available
            
        except Exception as e:
            logger.warning(
                "List endpoint availability check failed",
                roaster_id=self.roaster_id,
                error=str(e),
            )
            return False
    
    async def _fetch_from_list_endpoint(
        self,
        limit: int = 50,
        page: int = 1,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Fetch products from the list endpoint.
        
        Args:
            limit: Number of products per page
            page: Page number
            **kwargs: Additional parameters
            
        Returns:
            List of product dictionaries
        """
        try:
            # Use the base fetcher's fetch_products method
            products = await self.base_fetcher.fetch_products(
                limit=limit,
                page=page,
                **kwargs
            )
            
            logger.info(
                "Fetched from list endpoint",
                roaster_id=self.roaster_id,
                products_count=len(products),
                limit=limit,
                page=page,
            )
            
            return products
            
        except Exception as e:
            logger.error(
                "Failed to fetch from list endpoint",
                roaster_id=self.roaster_id,
                error=str(e),
            )
            raise
    
    async def _fetch_per_product(self, **kwargs) -> List[Dict[str, Any]]:
        """
        Fallback to per-product fetching when list endpoint is unavailable.
        
        Args:
            **kwargs: Additional parameters
            
        Returns:
            List of product dictionaries
        """
        try:
            # Get existing product handles from database
            # This would need to be implemented with actual database integration
            product_handles = await self._get_existing_product_handles()
            
            if not product_handles:
                logger.warning(
                    "No existing product handles found for per-product fetch",
                    roaster_id=self.roaster_id,
                )
                return []
            
            # Fetch each product individually
            products = []
            for handle in product_handles[:50]:  # Limit to 50 products for performance
                try:
                    product = await self._fetch_single_product(handle)
                    if product:
                        products.append(product)
                except Exception as e:
                    logger.warning(
                        "Failed to fetch individual product",
                        roaster_id=self.roaster_id,
                        handle=handle,
                        error=str(e),
                    )
                    continue
            
            logger.info(
                "Completed per-product fetch",
                roaster_id=self.roaster_id,
                handles_attempted=len(product_handles),
                products_fetched=len(products),
            )
            
            return products
            
        except Exception as e:
            logger.error(
                "Failed per-product fetch",
                roaster_id=self.roaster_id,
                error=str(e),
            )
            raise
    
    async def _get_existing_product_handles(self) -> List[str]:
        """
        Get existing product handles from database.
        
        Returns:
            List of product handles
        """
        try:
            logger.info(
                "Getting existing product handles",
                roaster_id=self.roaster_id,
            )
            
            # Query database for existing product handles
            if self.supabase_client:
                # Query coffees table for existing products
                # We want both platform_product_id and slug, so we don't filter by null platform_product_id
                result = self.supabase_client.table("coffees").select(
                    "platform_product_id, slug"
                ).eq("roaster_id", self.roaster_id).execute()
                
                if result.data:
                    # Extract handles from platform_product_id or slug
                    handles = []
                    for coffee in result.data:
                        # Use platform_product_id as handle, fallback to slug
                        handle = coffee.get('platform_product_id') or coffee.get('slug')
                        if handle:
                            handles.append(handle)
                    
                    logger.info(
                        "Retrieved existing product handles",
                        roaster_id=self.roaster_id,
                        handle_count=len(handles)
                    )
                    return handles
                else:
                    logger.info(
                        "No existing product handles found",
                        roaster_id=self.roaster_id
                    )
                    return []
            else:
                # No database client available - return empty list
                logger.warning(
                    "No database client available for product handles",
                    roaster_id=self.roaster_id
                )
                return []
                
        except Exception as e:
            logger.error(
                "Failed to get existing product handles",
                roaster_id=self.roaster_id,
                error=str(e)
            )
            return []
    
    async def _fetch_single_product(self, handle: str) -> Optional[Dict[str, Any]]:
        """
        Fetch a single product by handle.
        
        Args:
            handle: Product handle
            
        Returns:
            Product dictionary or None if failed
        """
        try:
            # Construct product URL based on platform
            current_platform = self.base_fetcher.platform
            if current_platform == "shopify":
                url = f"{self.base_fetcher.base_url}/products/{handle}.json"
            elif current_platform == "woocommerce":
                url = f"{self.base_fetcher.base_url}/wp-json/wc/store/products/{handle}"
            else:
                logger.warning(
                    "Unknown platform for per-product fetch",
                    platform=current_platform,
                )
                return None
            
            status_code, headers, content = await self.base_fetcher._make_request(url=url)
            
            if status_code == 200:
                import json
                product_data = safe_decode_json(content)
                
                # Extract product from response
                if current_platform == "shopify":
                    return product_data.get('product')
                elif current_platform == "woocommerce":
                    # WooCommerce returns the product directly
                    return product_data
                else:
                    return product_data
            else:
                logger.warning(
                    "Failed to fetch single product",
                    handle=handle,
                    status_code=status_code,
                )
                return None
                
        except Exception as e:
            logger.warning(
                "Error fetching single product",
                handle=handle,
                error=str(e),
            )
            return None
    
    async def detect_and_report_deltas(
        self,
        fetched_data: List[Dict[str, Any]],
        existing_variants: List[Dict[str, Any]],
    ) -> List[PriceDelta]:
        """
        Detect price deltas and return them for processing.
        
        Args:
            fetched_data: Price data from fetch
            existing_variants: Existing variant data from database
            
        Returns:
            List of price deltas
        """
        try:
            # Extract all variants from fetched data
            all_variants = []
            for product in fetched_data:
                variants = product.get('variants', [])
                all_variants.extend(variants)
            
            # Detect deltas
            deltas = self.price_parser.detect_price_deltas(
                fetched_products=fetched_data,
                existing_variants=existing_variants,
            )
            
            logger.info(
                "Detected price deltas",
                roaster_id=self.roaster_id,
                total_variants=len(all_variants),
                deltas_found=len(deltas),
            )
            
            return deltas
            
        except Exception as e:
            logger.error(
                "Failed to detect price deltas",
                roaster_id=self.roaster_id,
                error=str(e),
            )
            return []
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for the price fetcher."""
        return {
            'roaster_id': self.roaster_id,
            'platform': self.platform,
            'job_type': self.job_type,
            'parser_metrics': self.price_parser.get_performance_metrics(),
        }
