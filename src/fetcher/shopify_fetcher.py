"""
Shopify products fetcher implementation.
Handles Shopify products.json API with pagination and rate limiting.
"""

import json
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

from structlog import get_logger

from .base_fetcher import BaseFetcher, FetcherConfig

logger = get_logger(__name__)


class ShopifyFetcher(BaseFetcher):
    """
    Shopify products fetcher with pagination and rate limiting compliance.
    
    Features:
    - Fetches from {domain}/products.json endpoint
    - Handles Shopify pagination (limit, page parameters)
    - Respects Shopify rate limits (2 calls per second)
    - Supports created_at_min, updated_at_min filters
    - Returns raw Shopify product data
    """
    
    def __init__(
        self,
        config: FetcherConfig,
        roaster_id: str,
        base_url: str,
        api_key: Optional[str] = None,
    ):
        super().__init__(config, roaster_id, base_url, "shopify")
        self.api_key = api_key
        
        # Shopify-specific headers
        if api_key:
            self._client.headers['X-Shopify-Access-Token'] = api_key
        
        # Shopify rate limiting: 2 calls per second
        self.config.politeness_delay = 0.5  # 500ms between requests
        
        logger.info(
            "Initialized Shopify fetcher",
            roaster_id=roaster_id,
            base_url=base_url,
            has_api_key=bool(api_key),
        )
    
    def _build_products_url(self) -> str:
        """Build the products.json URL."""
        return self._build_url('/products.json')
    
    async def fetch_products(
        self,
        limit: int = 50,
        page: int = 1,
        created_at_min: Optional[str] = None,
        updated_at_min: Optional[str] = None,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Fetch products from Shopify with pagination.
        
        Args:
            limit: Number of products per page (max 250 for Shopify)
            page: Page number (1-based)
            created_at_min: Filter products created after this date (ISO format)
            updated_at_min: Filter products updated after this date (ISO format)
            **kwargs: Additional Shopify parameters
            
        Returns:
            List of Shopify product dictionaries
        """
        # Shopify limits
        limit = min(limit, 250)  # Shopify max is 250
        
        params = {
            'limit': limit,
            'page': page,
        }
        
        # Add optional filters
        if created_at_min:
            params['created_at_min'] = created_at_min
        if updated_at_min:
            params['updated_at_min'] = updated_at_min
        
        # Add any additional Shopify parameters
        params.update(kwargs)
        
        url = self._build_products_url()
        
        try:
            status_code, headers, content = await self._make_request(
                url=url,
                params=params
            )
            
            if status_code == 200:
                data = json.loads(content.decode('utf-8'))
                products = data.get('products', [])
                
                logger.info(
                    "Fetched Shopify products",
                    roaster_id=self.roaster_id,
                    page=page,
                    limit=limit,
                    products_count=len(products),
                    total_products=data.get('products', []).__len__() if 'products' in data else 0,
                )
                
                return products
            
            elif status_code == 429:
                logger.warning(
                    "Shopify rate limit exceeded",
                    roaster_id=self.roaster_id,
                    page=page,
                    retry_after=headers.get('Retry-After', 'unknown'),
                )
                # Shopify returns 429 for rate limiting
                # The base fetcher will handle retries with exponential backoff
                return []
            
            else:
                logger.error(
                    "Failed to fetch Shopify products",
                    roaster_id=self.roaster_id,
                    page=page,
                    status_code=status_code,
                )
                return []
        
        except json.JSONDecodeError as e:
            logger.error(
                "Invalid JSON response from Shopify",
                roaster_id=self.roaster_id,
                page=page,
                error=str(e),
            )
            return []
        
        except Exception as e:
            logger.error(
                "Unexpected error fetching Shopify products",
                roaster_id=self.roaster_id,
                page=page,
                error=str(e),
            )
            return []
    
    async def fetch_all_products(
        self,
        created_at_min: Optional[str] = None,
        updated_at_min: Optional[str] = None,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Fetch all products with automatic pagination.
        
        Args:
            created_at_min: Filter products created after this date
            updated_at_min: Filter products updated after this date
            **kwargs: Additional Shopify parameters
            
        Returns:
            List of all Shopify product dictionaries
        """
        all_products = []
        page = 1
        limit = 250  # Use maximum limit for efficiency
        
        logger.info(
            "Starting to fetch all Shopify products",
            roaster_id=self.roaster_id,
            created_at_min=created_at_min,
            updated_at_min=updated_at_min,
        )
        
        while True:
            # Use direct _make_request to avoid error handling in fetch_products
            params = {
                'limit': limit,
                'page': page,
            }
            
            # Add optional filters
            if created_at_min:
                params['created_at_min'] = created_at_min
            if updated_at_min:
                params['updated_at_min'] = updated_at_min
            
            # Add any additional Shopify parameters
            params.update(kwargs)
            
            url = self._build_products_url()
            
            try:
                status_code, headers, content = await self._make_request(
                    url=url,
                    params=params
                )
                
                if status_code == 200:
                    data = json.loads(content.decode('utf-8'))
                    products = data.get('products', [])
                    
                    if not products:
                        # No more products
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
                
                elif status_code == 429:
                    logger.warning(
                        "Shopify rate limit exceeded during pagination",
                        roaster_id=self.roaster_id,
                        page=page,
                        retry_after=headers.get('Retry-After', 'unknown'),
                    )
                    break
                
                else:
                    logger.error(
                        "Failed to fetch Shopify products during pagination",
                        roaster_id=self.roaster_id,
                        page=page,
                        status_code=status_code,
                    )
                    break
            
            except Exception as e:
                logger.error(
                    "Unexpected error during pagination",
                    roaster_id=self.roaster_id,
                    page=page,
                    error=str(e),
                )
                break
        
        logger.info(
            "Completed fetching all Shopify products",
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
                params={'limit': 1}
            )
            
            if status_code == 200:
                data = json.loads(content.decode('utf-8'))
                # Shopify doesn't provide total count in the response
                # We'd need to make a separate API call to get this
                # For now, return the count of products in the first page
                products = data.get('products', [])
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
        Test the connection to Shopify API.
        
        Returns:
            True if connection is successful, False otherwise
        """
        try:
            status_code, headers, content = await self._make_request(
                url=self._build_products_url(),
                params={'limit': 1}
            )
            
            success = status_code == 200
            logger.info(
                "Shopify connection test",
                roaster_id=self.roaster_id,
                success=success,
                status_code=status_code,
            )
            
            return success
        
        except Exception as e:
            logger.error(
                "Shopify connection test failed",
                roaster_id=self.roaster_id,
                error=str(e),
            )
            return False
