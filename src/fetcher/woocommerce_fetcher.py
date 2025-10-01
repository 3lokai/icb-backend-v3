"""
WooCommerce products fetcher implementation.
Handles WooCommerce REST API with pagination and authentication.
"""

import json
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin
import base64

from structlog import get_logger
from .encoding_utils import safe_decode_json

from .base_fetcher import BaseFetcher, FetcherConfig

logger = get_logger(__name__)


class WooCommerceFetcher(BaseFetcher):
    """
    WooCommerce products fetcher with pagination and authentication.
    
    Features:
    - Fetches from /wp-json/wc/store/products endpoint
    - Handles WooCommerce pagination (per_page, page parameters)
    - Supports consumer key/secret authentication
    - Supports JWT authentication
    - Rate limiting: 100 requests per 15 minutes
    - Returns raw WooCommerce product data
    """
    
    def __init__(
        self,
        config: FetcherConfig,
        roaster_id: str,
        base_url: str,
        consumer_key: Optional[str] = None,
        consumer_secret: Optional[str] = None,
        jwt_token: Optional[str] = None,
        job_type: str = "full_refresh",
    ):
        super().__init__(config, roaster_id, base_url, "woocommerce", job_type)
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self.jwt_token = jwt_token
        
        # WooCommerce authentication
        if jwt_token:
            self._client.headers['Authorization'] = f'Bearer {jwt_token}'
        elif consumer_key and consumer_secret:
            # Basic auth with consumer key/secret
            credentials = f"{consumer_key}:{consumer_secret}"
            encoded_credentials = base64.b64encode(credentials.encode()).decode()
            self._client.headers['Authorization'] = f'Basic {encoded_credentials}'
        
        # WooCommerce rate limiting: 100 requests per 15 minutes
        # More lenient than Shopify, but still need politeness
        self.config.politeness_delay = 0.1  # 100ms between requests
        
        logger.info(
            "Initialized WooCommerce fetcher",
            roaster_id=roaster_id,
            base_url=base_url,
            has_consumer_key=bool(consumer_key),
            has_jwt_token=bool(jwt_token),
        )
    
    def _build_products_url(self) -> str:
        """Build the WooCommerce products API URL."""
        return self._build_url('/wp-json/wc/store/products')
    
    async def fetch_products(
        self,
        limit: int = 50,
        page: int = 1,
        after: Optional[str] = None,
        before: Optional[str] = None,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Fetch products from WooCommerce with pagination.
        
        Args:
            limit: Number of products per page (max 100 for WooCommerce)
            page: Page number (1-based)
            after: Filter products created after this date (ISO format)
            before: Filter products created before this date (ISO format)
            **kwargs: Additional WooCommerce parameters
            
        Returns:
            List of WooCommerce product dictionaries
        """
        # WooCommerce limits
        limit = min(limit, 100)  # WooCommerce max is typically 100
        
        params = {
            'per_page': limit,
            'page': page,
        }
        
        # Add optional date filters
        if after:
            params['after'] = after
        if before:
            params['before'] = before
        
        # Add any additional WooCommerce parameters
        params.update(kwargs)
        
        url = self._build_products_url()
        
        try:
            status_code, headers, content = await self._make_request(
                url=url,
                params=params
            )
            
            if status_code == 200:
                products = safe_decode_json(content)
                
                logger.info(
                    "Fetched WooCommerce products",
                    roaster_id=self.roaster_id,
                    page=page,
                    limit=limit,
                    products_count=len(products),
                )
                
                return products
            
            elif status_code == 401:
                logger.error(
                    "WooCommerce authentication failed",
                    roaster_id=self.roaster_id,
                    page=page,
                )
                return []
            
            elif status_code == 429:
                logger.warning(
                    "WooCommerce rate limit exceeded",
                    roaster_id=self.roaster_id,
                    page=page,
                    retry_after=headers.get('Retry-After', 'unknown'),
                )
                return []
            
            else:
                logger.error(
                    "Failed to fetch WooCommerce products",
                    roaster_id=self.roaster_id,
                    page=page,
                    status_code=status_code,
                )
                return []
        
        except json.JSONDecodeError as e:
            logger.error(
                "Invalid JSON response from WooCommerce",
                roaster_id=self.roaster_id,
                page=page,
                error=str(e),
            )
            return []
        
        except Exception as e:
            logger.error(
                "Unexpected error fetching WooCommerce products",
                roaster_id=self.roaster_id,
                page=page,
                error=str(e),
            )
            return []
    
    async def fetch_all_products(
        self,
        after: Optional[str] = None,
        before: Optional[str] = None,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Fetch all products with automatic pagination.
        
        Args:
            after: Filter products created after this date
            before: Filter products created before this date
            **kwargs: Additional WooCommerce parameters
            
        Returns:
            List of all WooCommerce product dictionaries
        """
        all_products = []
        page = 1
        limit = 100  # Use maximum limit for efficiency
        
        logger.info(
            "Starting to fetch all WooCommerce products",
            roaster_id=self.roaster_id,
            after=after,
            before=before,
        )
        
        while True:
            products = await self.fetch_products(
                limit=limit,
                page=page,
                after=after,
                before=before,
                **kwargs
            )
            
            if not products:
                # No more products or error occurred
                break
            
            all_products.extend(products)
            
            # If we got fewer products than the limit, we've reached the end
            if len(products) < limit:
                break
            
            page += 1
            
            # Safety check to prevent infinite loops
            if page > 1000:  # Reasonable upper bound
                logger.warning(
                    "Reached maximum page limit",
                    roaster_id=self.roaster_id,
                    max_pages=1000,
                    total_products=len(all_products),
                )
                break
        
        logger.info(
            "Completed fetching all WooCommerce products",
            roaster_id=self.roaster_id,
            total_products=len(all_products),
            pages_fetched=page,
        )
        
        return all_products
    
    async def get_product_count(self) -> int:
        """
        Get the total number of products available.
        This is a lightweight operation that doesn't fetch all products.
        """
        try:
            # Fetch just one product to get total count from headers
            status_code, headers, content = await self._make_request(
                url=self._build_products_url(),
                params={'per_page': 1}
            )
            
            if status_code == 200:
                # WooCommerce typically includes total count in headers
                total_count = headers.get('X-WP-Total')
                if total_count:
                    try:
                        return int(total_count)
                    except ValueError:
                        pass
                
                # Fallback: count products in response
                products = safe_decode_json(content)
                return len(products)
            
            return 0
        
        except Exception as e:
            logger.error(
                "Failed to get product count",
                roaster_id=self.roaster_id,
                error=str(e),
            )
            return 0
    
    async def test_connection(self) -> bool:
        """
        Test the connection to WooCommerce API.
        
        Returns:
            True if connection is successful, False otherwise
        """
        try:
            status_code, headers, content = await self._make_request(
                url=self._build_products_url(),
                params={'per_page': 1}
            )
            
            success = status_code == 200
            logger.info(
                "WooCommerce connection test",
                roaster_id=self.roaster_id,
                success=success,
                status_code=status_code,
            )
            
            return success
        
        except Exception as e:
            logger.error(
                "WooCommerce connection test failed",
                roaster_id=self.roaster_id,
                error=str(e),
            )
            return False
    
    async def fetch_price_only_products(
        self,
        limit: int = 50,
        page: int = 1,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Fetch products in price-only mode with minimal fields.
        
        Args:
            limit: Number of products per page
            page: Page number
            **kwargs: Additional parameters
            
        Returns:
            List of products with price-only data
        """
        if self.job_type != "price_only":
            # Fallback to regular fetch if not in price-only mode
            return await self.fetch_products(limit, page, **kwargs)
        
        try:
            # Use WooCommerce API with minimal fields
            params = {
                'per_page': min(limit, 100),  # WooCommerce max
                'page': page,
                'fields': 'id,title,variations',  # Only fetch essential fields
            }
            params.update(kwargs)
            
            url = self._build_products_url()
            
            status_code, headers, content = await self._make_request(
                url=url,
                params=params
            )
            
            if status_code == 200:
                products = safe_decode_json(content)
                
                # Filter to only include products with variations
                price_only_products = []
                for product in products:
                    variations = product.get('variations', [])
                    if variations:
                        # Keep only essential fields for price-only mode
                        price_only_product = {
                            'id': product.get('id'),
                            'title': product.get('title'),
                            'variants': [
                                {
                                    'id': variation.get('id'),
                                    'price': variation.get('price'),
                                    'regular_price': variation.get('regular_price'),
                                    'sale_price': variation.get('sale_price'),
                                    'stock_status': variation.get('stock_status'),
                                    'sku': variation.get('sku'),
                                    'weight': variation.get('weight'),
                                }
                                for variation in variations
                            ]
                        }
                        price_only_products.append(price_only_product)
                
                logger.info(
                    "Fetched WooCommerce price-only products",
                    roaster_id=self.roaster_id,
                    page=page,
                    limit=limit,
                    products_count=len(price_only_products),
                )
                
                return price_only_products
            
            else:
                logger.error(
                    "Failed to fetch WooCommerce price-only products",
                    roaster_id=self.roaster_id,
                    page=page,
                    status_code=status_code,
                )
                return []
        
        except Exception as e:
            logger.error(
                "Error fetching WooCommerce price-only products",
                roaster_id=self.roaster_id,
                page=page,
                error=str(e),
            )
            return []
    
    async def fetch_price_only_all_products(self, **kwargs) -> List[Dict[str, Any]]:
        """
        Fetch all products in price-only mode with pagination.
        
        Args:
            **kwargs: Additional parameters
            
        Returns:
            List of all products with price-only data
        """
        all_products = []
        page = 1
        limit = 100  # Use maximum limit for efficiency
        
        logger.info(
            "Starting to fetch all WooCommerce price-only products",
            roaster_id=self.roaster_id,
        )
        
        while True:
            products = await self.fetch_price_only_products(
                limit=limit,
                page=page,
                **kwargs
            )
            
            if not products:
                break
            
            all_products.extend(products)
            page += 1
            
            # Safety limit to prevent infinite loops
            if page > 100:  # 100 pages * 100 products = 10,000 products max
                logger.warning(
                    "Reached safety limit for WooCommerce price-only fetch",
                    roaster_id=self.roaster_id,
                    page=page,
                )
                break
        
        logger.info(
            "Completed WooCommerce price-only fetch",
            roaster_id=self.roaster_id,
            total_products=len(all_products),
            pages_fetched=page - 1,
        )
        
        return all_products
