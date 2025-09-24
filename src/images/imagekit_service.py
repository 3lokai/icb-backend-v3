"""
ImageKit service for image upload integration.

Provides ImageKit CDN integration with retry logic, batch processing,
and comprehensive error handling for the coffee pipeline.
"""

import time
from typing import Dict, Any, Optional
from structlog import get_logger
from imagekitio import ImageKit
from imagekitio.models.UploadFileRequestOptions import UploadFileRequestOptions

from ..config.imagekit_config import ImageKitConfig, ImageKitResult

logger = get_logger(__name__)


class ImageKitUploadError(Exception):
    """Exception raised for ImageKit upload errors."""
    pass


class ImageKitService:
    """
    Service for ImageKit CDN integration with image upload capabilities.
    
    Features:
    - Image upload with retry logic and exponential backoff
    - Batch processing optimization for multiple images
    - Comprehensive error handling and logging
    - Fallback mechanism for upload failures
    - Performance monitoring and caching
    """
    
    def __init__(self, config: ImageKitConfig, max_retries: int = 3, backoff_factor: float = 2.0):
        """
        Initialize ImageKit service.
        
        Args:
            config: ImageKit configuration
            max_retries: Maximum number of retry attempts
            backoff_factor: Exponential backoff factor
        """
        self.config = config
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        
        # Initialize retry configuration
        from ..config.imagekit_config import RetryConfig
        self.retry_config = RetryConfig(
            max_retries=max_retries,
            backoff_factor=backoff_factor
        )
        
        # Initialize ImageKit client
        self.client = ImageKit(
            public_key=config.public_key,
            private_key=config.private_key,
            url_endpoint=config.url_endpoint
        )
        
        # Performance tracking
        self.stats = {
            'uploads_attempted': 0,
            'uploads_successful': 0,
            'uploads_failed': 0,
            'total_upload_time': 0.0
        }
        
        logger.info(
            "ImageKit service initialized",
            url_endpoint=config.url_endpoint,
            max_retries=max_retries
        )
    
    def upload_image(self, image_url: str, content: bytes, file_name: Optional[str] = None) -> ImageKitResult:
        """
        Upload image to ImageKit CDN with retry logic.

        Args:
            image_url: The original URL of the image (for logging/filename generation).
            content: The image content as bytes.
            file_name: Optional, specific filename for ImageKit. If None, one is generated.

        Returns:
            An ImageKitResult object indicating success or failure.
        """
        if not self.config.enabled:
            logger.info("ImageKit upload is disabled by configuration.", image_url=image_url)
            return ImageKitResult(success=False, error="ImageKit upload disabled")

        self.stats['uploads_attempted'] += 1
        start_time = time.time()
        last_exception = None

        for attempt in range(self.max_retries + 1):
            try:
                logger.debug(
                    "Attempting ImageKit upload",
                    image_url=image_url,
                    attempt=attempt + 1,
                    max_retries=self.max_retries
                )

                options = UploadFileRequestOptions(
                    folder=self.config.folder,
                    use_unique_file_name=True,
                    transformation=self.config.default_transformation
                )
                
                upload_file_name = file_name if file_name else self._generate_filename(image_url)

                result = self.client.upload_file(
                    file=content,
                    file_name=upload_file_name,
                    options=options
                )

                self.stats['uploads_successful'] += 1
                processing_time = time.time() - start_time
                self.stats['total_upload_time'] += processing_time
                logger.info(
                    "ImageKit upload successful",
                    image_url=image_url,
                    imagekit_url=result.url,
                    file_id=result.fileId,
                    processing_time=processing_time
                )
                return ImageKitResult(success=True, imagekit_url=result.url, file_id=result.fileId)

            except Exception as e:
                last_exception = e
                if attempt < self.max_retries:
                    delay = self.backoff_factor ** attempt
                    logger.warning(
                        "ImageKit upload failed, retrying",
                        image_url=image_url,
                        attempt=attempt + 1,
                        delay=delay,
                        error=str(e)
                    )
                    time.sleep(delay)
                else:
                    self.stats['uploads_failed'] += 1
                    processing_time = time.time() - start_time
                    self.stats['total_upload_time'] += processing_time
                    logger.error(
                        "ImageKit upload failed after multiple retries",
                        image_url=image_url,
                        max_retries=self.max_retries,
                        final_error=str(e),
                        processing_time=processing_time
                    )
                    return ImageKitResult(success=False, error=str(last_exception))
    
    def _generate_filename(self, original_url: str) -> str:
        """Generates a filename for ImageKit based on the original URL."""
        # Simple approach: use the last part of the URL, ensure it's unique
        # ImageKit's use_unique_filename option handles uniqueness, so this is for readability
        filename = original_url.split('/')[-1]
        if '?' in filename:
            filename = filename.split('?')[0]
        if not filename:
            filename = f"image_{int(time.time())}" # Fallback
        return filename
    
    def get_stats(self) -> Dict[str, Any]:
        """Returns performance statistics for ImageKit uploads."""
        stats = self.stats.copy()
        total_attempts = stats['uploads_attempted']
        if total_attempts > 0:
            stats['success_rate'] = stats['uploads_successful'] / total_attempts
            stats['failure_rate'] = stats['uploads_failed'] / total_attempts
            stats['avg_upload_time'] = stats['total_upload_time'] / stats['uploads_successful'] if stats['uploads_successful'] > 0 else 0.0
        else:
            stats['success_rate'] = 0.0
            stats['failure_rate'] = 0.0
            stats['avg_upload_time'] = 0.0
        return stats

    def reset_stats(self):
        """Resets performance statistics."""
        self.stats = {
            'uploads_attempted': 0,
            'uploads_successful': 0,
            'uploads_failed': 0,
            'total_upload_time': 0.0
        }