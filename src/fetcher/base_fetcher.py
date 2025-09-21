"""
Base fetcher class with async HTTP client, concurrency control, and politeness delays.
Implements common functionality for Shopify and WooCommerce fetchers.
"""

import asyncio
import random
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse

import httpx
from structlog import get_logger

logger = get_logger(__name__)


class FetcherConfig:
    """Configuration for fetcher behavior."""
    
    def __init__(
        self,
        timeout: float = 30.0,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        politeness_delay: float = 0.25,
        jitter_range: float = 0.1,
        max_concurrent: int = 3,
    ):
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.politeness_delay = politeness_delay
        self.jitter_range = jitter_range
        self.max_concurrent = max_concurrent


class BaseFetcher(ABC):
    """
    Base class for async HTTP fetchers with concurrency control and politeness.
    
    Features:
    - Async httpx client with proper configuration
    - Per-roaster semaphore-based concurrency control
    - Politeness delays with jitter (250ms ± 100ms)
    - Timeout handling and exponential backoff
    - ETag/Last-Modified caching support
    """
    
    def __init__(
        self,
        config: FetcherConfig,
        roaster_id: str,
        base_url: str,
        platform: str,
    ):
        self.config = config
        self.roaster_id = roaster_id
        self.base_url = base_url.rstrip('/')
        self.platform = platform
        
        # Per-roaster semaphore for concurrency control
        self._semaphore = asyncio.Semaphore(config.max_concurrent)
        
        # HTTP client configuration
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(config.timeout),
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
            headers={
                'User-Agent': 'CoffeeScraper/1.0 (https://indiancoffeebeans.com)',
                'Accept': 'application/json',
            }
        )
        
        # Caching support
        self._etags: Dict[str, str] = {}
        self._last_modified: Dict[str, str] = {}
        
        logger.info(
            "Initialized fetcher",
            roaster_id=roaster_id,
            platform=platform,
            base_url=base_url,
            max_concurrent=config.max_concurrent,
        )
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - close HTTP client."""
        await self._client.aclose()
    
    async def _apply_politeness_delay(self):
        """Apply politeness delay with jitter."""
        base_delay = self.config.politeness_delay
        jitter = random.uniform(-self.config.jitter_range, self.config.jitter_range)
        delay = max(0, base_delay + jitter)
        
        if delay > 0:
            await asyncio.sleep(delay)
    
    async def _make_request(
        self,
        url: str,
        method: str = "GET",
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        use_cache: bool = True,
    ) -> Tuple[int, Dict[str, Any], bytes]:
        """
        Make HTTP request with concurrency control, retries, and caching.
        
        Returns:
            Tuple of (status_code, headers, response_body)
        """
        async with self._semaphore:
            await self._apply_politeness_delay()
            
            # Prepare headers with caching support
            request_headers = headers or {}
            if use_cache and url in self._etags:
                request_headers['If-None-Match'] = self._etags[url]
            if use_cache and url in self._last_modified:
                request_headers['If-Modified-Since'] = self._last_modified[url]
            
            # Merge with default headers
            final_headers = {**self._client.headers, **request_headers}
            
            for attempt in range(self.config.max_retries + 1):
                try:
                    logger.debug(
                        "Making request",
                        roaster_id=self.roaster_id,
                        url=url,
                        method=method,
                        attempt=attempt + 1,
                    )
                    
                    response = await self._client.request(
                        method=method,
                        url=url,
                        params=params,
                        headers=final_headers,
                    )
                    
                    # Update cache headers
                    if 'etag' in response.headers:
                        self._etags[url] = response.headers['etag']
                    if 'last-modified' in response.headers:
                        self._last_modified[url] = response.headers['last-modified']
                    
                    # Handle 304 Not Modified
                    if response.status_code == 304:
                        logger.info(
                            "Resource not modified",
                            roaster_id=self.roaster_id,
                            url=url,
                        )
                        return response.status_code, dict(response.headers), b''
                    
                    # Handle successful response
                    if response.status_code < 400:
                        logger.info(
                            "Request successful",
                            roaster_id=self.roaster_id,
                            url=url,
                            status_code=response.status_code,
                            content_length=len(response.content),
                        )
                        return response.status_code, dict(response.headers), response.content
                    
                    # Handle client errors (4xx) - don't retry
                    if 400 <= response.status_code < 500:
                        logger.warning(
                            "Client error - not retrying",
                            roaster_id=self.roaster_id,
                            url=url,
                            status_code=response.status_code,
                        )
                        return response.status_code, dict(response.headers), response.content
                    
                    # Handle server errors (5xx) - retry
                    if response.status_code >= 500:
                        logger.warning(
                            "Server error - will retry",
                            roaster_id=self.roaster_id,
                            url=url,
                            status_code=response.status_code,
                            attempt=attempt + 1,
                        )
                        if attempt < self.config.max_retries:
                            delay = self.config.retry_delay * (2 ** attempt)
                            await asyncio.sleep(delay)
                            continue
                        else:
                            return response.status_code, dict(response.headers), response.content
                
                except httpx.TimeoutException:
                    logger.warning(
                        "Request timeout",
                        roaster_id=self.roaster_id,
                        url=url,
                        attempt=attempt + 1,
                    )
                    if attempt < self.config.max_retries:
                        delay = self.config.retry_delay * (2 ** attempt)
                        await asyncio.sleep(delay)
                        continue
                    else:
                        raise
                
                except httpx.RequestError as e:
                    logger.error(
                        "Request error",
                        roaster_id=self.roaster_id,
                        url=url,
                        error=str(e),
                        attempt=attempt + 1,
                    )
                    if attempt < self.config.max_retries:
                        delay = self.config.retry_delay * (2 ** attempt)
                        await asyncio.sleep(delay)
                        continue
                    else:
                        raise
            
            # This should never be reached, but just in case
            raise httpx.RequestError("Max retries exceeded")
    
    def _build_url(self, endpoint: str) -> str:
        """Build full URL from base URL and endpoint."""
        return urljoin(self.base_url + '/', endpoint.lstrip('/'))
    
    @abstractmethod
    async def fetch_products(
        self,
        limit: int = 50,
        page: int = 1,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Fetch products from the platform.
        
        Args:
            limit: Number of products per page
            page: Page number (1-based)
            **kwargs: Platform-specific parameters
            
        Returns:
            List of product dictionaries
        """
        pass
    
    @abstractmethod
    async def fetch_all_products(self, **kwargs) -> List[Dict[str, Any]]:
        """
        Fetch all products with automatic pagination.
        
        Args:
            **kwargs: Platform-specific parameters
            
        Returns:
            List of all product dictionaries
        """
        pass
