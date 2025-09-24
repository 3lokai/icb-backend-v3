"""
Image hash computation utilities for content-based deduplication.

This module provides SHA256 hash computation from image content and headers
for efficient image deduplication across the coffee pipeline.
"""

import hashlib
import requests
from typing import Optional, Dict, Any, List
from urllib.parse import urlparse
import time
from structlog import get_logger

logger = get_logger(__name__)


class ImageHashComputationError(Exception):
    """Exception raised for image hash computation errors."""
    pass


class ImageHashComputer:
    """
    Computes SHA256 hashes from image content and headers for deduplication.
    
    Features:
    - Content-based hashing from actual image bytes
    - Header-based hashing from ETag and Last-Modified headers
    - Batch processing optimization for multiple images
    - Comprehensive error handling and fallback strategies
    - Performance monitoring and caching
    """
    
    def __init__(self, timeout: int = 30, max_retries: int = 3):
        """
        Initialize image hash computer.
        
        Args:
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts for failed requests
        """
        self.timeout = timeout
        self.max_retries = max_retries
        self.session = requests.Session()
        
        # Performance tracking
        self.stats = {
            'content_hashes_computed': 0,
            'header_hashes_computed': 0,
            'failed_computations': 0,
            'cache_hits': 0,
            'total_processing_time': 0.0
        }
        
        # In-memory cache for frequently accessed hashes
        self.hash_cache: Dict[str, str] = {}
        self.cache_max_size = 1000
    
    def compute_image_hash(
        self, 
        image_url: str, 
        content: Optional[bytes] = None,
        use_cache: bool = True
    ) -> str:
        """
        Compute SHA256 hash from image content or headers.
        
        Args:
            image_url: URL of the image
            content: Pre-fetched image content (optional)
            use_cache: Whether to use cache for hash lookup
            
        Returns:
            SHA256 hash as hexadecimal string
            
        Raises:
            ImageHashComputationError: If hash computation fails
        """
        start_time = time.time()
        
        try:
            # Check cache first
            if use_cache and image_url in self.hash_cache:
                self.stats['cache_hits'] += 1
                logger.debug("Hash cache hit", image_url=image_url)
                return self.hash_cache[image_url]
            
            # Try content-based hashing first
            if content:
                hash_result = self._compute_content_hash(content)
                self.stats['content_hashes_computed'] += 1
            else:
                # Fallback to header-based hashing
                hash_result = self._compute_header_hash(image_url)
                self.stats['header_hashes_computed'] += 1
            
            # Update cache
            if use_cache:
                self._update_cache(image_url, hash_result)
            
            # Update performance stats
            processing_time = time.time() - start_time
            self.stats['total_processing_time'] += processing_time
            
            logger.debug(
                "Image hash computed successfully",
                image_url=image_url,
                hash=hash_result,
                processing_time=processing_time,
                method="content" if content else "header"
            )
            
            return hash_result
            
        except Exception as e:
            self.stats['failed_computations'] += 1
            
            logger.error(
                "Failed to compute image hash",
                image_url=image_url,
                error=str(e)
            )
            
            raise ImageHashComputationError(
                f"Failed to compute hash for image {image_url}: {str(e)}"
            )
    
    def _compute_content_hash(self, content: bytes) -> str:
        """
        Compute SHA256 hash from image content.
        
        Args:
            content: Image content as bytes
            
        Returns:
            SHA256 hash as hexadecimal string
        """
        if not content:
            raise ImageHashComputationError("Empty image content provided")
        
        # Compute SHA256 hash
        hash_obj = hashlib.sha256()
        hash_obj.update(content)
        return hash_obj.hexdigest()
    
    def _compute_header_hash(self, image_url: str) -> str:
        """
        Compute SHA256 hash from image headers (ETag + Last-Modified).
        
        Args:
            image_url: URL of the image
            
        Returns:
            SHA256 hash as hexadecimal string
        """
        try:
            # Make HEAD request to get headers
            response = self._make_request_with_retry(image_url, method='HEAD')
            
            # Extract relevant headers
            etag = response.headers.get('ETag', '').strip('"')
            last_modified = response.headers.get('Last-Modified', '')
            
            if not etag and not last_modified:
                raise ImageHashComputationError(
                    "No ETag or Last-Modified headers available for hash computation"
                )
            
            # Combine headers for hash computation
            header_data = f"{etag}:{last_modified}".encode('utf-8')
            
            # Compute SHA256 hash
            hash_obj = hashlib.sha256()
            hash_obj.update(header_data)
            return hash_obj.hexdigest()
            
        except Exception as e:
            raise ImageHashComputationError(
                f"Failed to compute header hash for {image_url}: {str(e)}"
            )
    
    def _make_request_with_retry(self, url: str, method: str = 'GET') -> requests.Response:
        """
        Make HTTP request with retry logic.
        
        Args:
            url: URL to request
            method: HTTP method
            
        Returns:
            Response object
            
        Raises:
            ImageHashComputationError: If all retry attempts fail
        """
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                logger.debug(
                    f"Making {method} request to image URL",
                    url=url,
                    attempt=attempt + 1,
                    max_retries=self.max_retries
                )
                
                if method.upper() == 'HEAD':
                    response = self.session.head(url, timeout=self.timeout)
                else:
                    response = self.session.get(url, timeout=self.timeout)
                
                response.raise_for_status()
                return response
                
            except Exception as e:
                last_exception = e
                
                if attempt < self.max_retries:
                    delay = 2 ** attempt  # Exponential backoff
                    logger.warning(
                        f"Request failed, retrying after delay",
                        url=url,
                        attempt=attempt + 1,
                        delay=delay,
                        error=str(e)
                    )
                    time.sleep(delay)
                else:
                    logger.error(
                        f"All retry attempts exhausted",
                        url=url,
                        max_retries=self.max_retries,
                        final_error=str(e)
                    )
        
        raise ImageHashComputationError(
            f"Failed to fetch {url} after {self.max_retries} retries: {str(last_exception)}"
        )
    
    def _update_cache(self, image_url: str, hash_result: str):
        """
        Update hash cache with size management.
        
        Args:
            image_url: Image URL
            hash_result: Computed hash
        """
        # Remove oldest entries if cache is full
        while len(self.hash_cache) >= self.cache_max_size:
            if self.hash_cache:
                self.hash_cache.pop(next(iter(self.hash_cache)))
        
        self.hash_cache[image_url] = hash_result
    
    def compute_batch_hashes(
        self, 
        image_urls: List[str], 
        use_cache: bool = True
    ) -> Dict[str, str]:
        """
        Compute hashes for multiple images in batch.
        
        Args:
            image_urls: List of image URLs
            use_cache: Whether to use cache for hash lookup
            
        Returns:
            Dictionary mapping image URLs to their hashes
            
        Raises:
            ImageHashComputationError: If batch processing fails
        """
        start_time = time.time()
        results = {}
        failed_urls = []
        
        logger.info(
            "Starting batch hash computation",
            total_images=len(image_urls),
            use_cache=use_cache
        )
        
        for image_url in image_urls:
            try:
                hash_result = self.compute_image_hash(
                    image_url=image_url,
                    content=None,  # Will use header-based hashing
                    use_cache=use_cache
                )
                results[image_url] = hash_result
                
            except ImageHashComputationError as e:
                logger.warning(
                    "Failed to compute hash for image in batch",
                    image_url=image_url,
                    error=str(e)
                )
                failed_urls.append(image_url)
                continue
        
        processing_time = time.time() - start_time
        
        logger.info(
            "Batch hash computation completed",
            total_images=len(image_urls),
            successful=len(results),
            failed=len(failed_urls),
            processing_time=processing_time,
            avg_time_per_image=processing_time / len(image_urls) if image_urls else 0
        )
        
        if failed_urls:
            logger.warning(
                "Some images failed hash computation",
                failed_count=len(failed_urls),
                failed_urls=failed_urls[:5]  # Log first 5 failed URLs
            )
        
        return results
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get performance statistics.
        
        Returns:
            Dictionary with performance statistics
        """
        stats = self.stats.copy()
        
        # Calculate averages
        total_computations = (
            stats['content_hashes_computed'] + 
            stats['header_hashes_computed'] + 
            stats['failed_computations']
        )
        
        if total_computations > 0:
            stats['success_rate'] = (
                stats['content_hashes_computed'] + stats['header_hashes_computed']
            ) / total_computations
            stats['failure_rate'] = stats['failed_computations'] / total_computations
            stats['avg_processing_time'] = stats['total_processing_time'] / total_computations
        else:
            stats['success_rate'] = 0.0
            stats['failure_rate'] = 0.0
            stats['avg_processing_time'] = 0.0
        
        stats['cache_size'] = len(self.hash_cache)
        stats['cache_hit_rate'] = (
            stats['cache_hits'] / total_computations if total_computations > 0 else 0.0
        )
        
        return stats
    
    def reset_stats(self):
        """Reset performance statistics."""
        self.stats = {
            'content_hashes_computed': 0,
            'header_hashes_computed': 0,
            'failed_computations': 0,
            'cache_hits': 0,
            'total_processing_time': 0.0
        }
    
    def clear_cache(self):
        """Clear the hash cache."""
        self.hash_cache.clear()
        logger.info("Hash cache cleared")
