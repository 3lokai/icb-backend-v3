"""
ImageKit integration service with F.1 deduplication.

Combines ImageKit upload functionality with F.1 image deduplication
to provide optimized image processing with CDN delivery.
"""

import time
from typing import Dict, Any, List, Optional, Tuple
from structlog import get_logger

from .imagekit_service import ImageKitService
from .deduplication_service import ImageDeduplicationService
from ..config.imagekit_config import ImageKitConfig, ImageKitResult, BatchUploadConfig
from .logging_config import get_image_deduplication_logger
from ..validator.rpc_client import RPCClient

logger = get_logger(__name__)


class ImageKitIntegrationService:
    """
    Integration service combining ImageKit upload with F.1 deduplication.
    
    Features:
    - ImageKit CDN upload with deduplication optimization
    - Fallback mechanism for upload failures
    - Batch processing with performance optimization
    - Comprehensive error handling and logging
    - Integration with existing A.1-A.5 pipeline
    """
    
    def __init__(
        self, 
        rpc_client: RPCClient,
        imagekit_config: ImageKitConfig,
        enable_deduplication: bool = True,
        enable_imagekit: bool = True
    ):
        """
        Initialize ImageKit integration service.
        
        Args:
            rpc_client: RPC client for database operations
            imagekit_config: ImageKit configuration
            enable_deduplication: Whether to enable F.1 deduplication
            enable_imagekit: Whether to enable ImageKit upload
        """
        self.rpc_client = rpc_client
        self.imagekit_config = imagekit_config
        self.enable_deduplication = enable_deduplication
        self.enable_imagekit = enable_imagekit
        
        # Initialize services
        self.imagekit_service = ImageKitService(imagekit_config) if enable_imagekit else None
        self.deduplication_service = ImageDeduplicationService(rpc_client) if enable_deduplication else None
        self.dedup_logger = get_image_deduplication_logger()
        
        # Integration statistics
        self.stats = {
            'images_processed': 0,
            'imagekit_uploads': 0,
            'imagekit_failures': 0,
            'duplicates_skipped': 0,
            'fallback_used': 0,
            'total_processing_time': 0.0
        }
        
        logger.info(
            "ImageKit integration service initialized",
            enable_deduplication=enable_deduplication,
            enable_imagekit=enable_imagekit
        )
    
    def process_image_with_imagekit(
        self, 
        image_data: Dict[str, Any], 
        coffee_id: str
    ) -> Dict[str, Any]:
        """
        Process image with ImageKit upload and deduplication.
        
        Args:
            image_data: Image data dictionary
            coffee_id: Coffee ID for the image
            
        Returns:
            Processed image data with ImageKit and deduplication information
        """
        start_time = time.time()
        image_url = image_data.get('url', 'unknown')
        
        try:
            # Step 1: Check for duplicates if deduplication is enabled
            if self.enable_deduplication and self.deduplication_service:
                self.dedup_logger.log_deduplication_processing_start(coffee_id, 1)
                
                # Process with deduplication
                dedup_result = self.deduplication_service.process_image_with_deduplication(
                    image_data, coffee_id
                )
                
                # If duplicate found, skip ImageKit upload
                if dedup_result.get('is_duplicate', False):
                    self.stats['duplicates_skipped'] += 1
                    
                    logger.info(
                        "Duplicate image found, skipping ImageKit upload",
                        image_url=image_url,
                        existing_image_id=dedup_result.get('existing_image_id')
                    )
                    
                    return {
                        **dedup_result,
                        'imagekit_upload_skipped': True,
                        'reason': 'duplicate_found'
                    }
                
                # Use deduplication result as base
                processed_data = dedup_result
            else:
                processed_data = image_data.copy()
            
            # Step 2: Upload to ImageKit if enabled
            imagekit_result = None
            if self.enable_imagekit and self.imagekit_service:
                try:
                    # Upload to ImageKit
                    imagekit_result = self.imagekit_service.upload_image(
                        image_url=image_url,
                        content=image_data.get('content'),
                        filename=image_data.get('filename')
                    )
                    
                    if imagekit_result.success:
                        self.stats['imagekit_uploads'] += 1
                        processed_data['imagekit_url'] = imagekit_result.imagekit_url
                        processed_data['imagekit_file_id'] = imagekit_result.file_id
                        processed_data['imagekit_upload_time'] = imagekit_result.upload_time
                        
                        logger.info(
                            "ImageKit upload successful",
                            image_url=image_url,
                            imagekit_url=imagekit_result.imagekit_url,
                            upload_time=imagekit_result.upload_time
                        )
                    else:
                        # ImageKit upload failed - use fallback
                        self.stats['imagekit_failures'] += 1
                        self.stats['fallback_used'] += 1
                        
                        processed_data['imagekit_upload_failed'] = True
                        processed_data['imagekit_error'] = imagekit_result.error
                        processed_data['fallback_url'] = image_url
                        
                        logger.warning(
                            "ImageKit upload failed, using fallback",
                            image_url=image_url,
                            error=imagekit_result.error
                        )
                        
                except Exception as e:
                    # ImageKit service error - use fallback
                    self.stats['imagekit_failures'] += 1
                    self.stats['fallback_used'] += 1
                    
                    processed_data['imagekit_upload_failed'] = True
                    processed_data['imagekit_error'] = str(e)
                    processed_data['fallback_url'] = image_url
                    
                    logger.error(
                        "ImageKit service error, using fallback",
                        image_url=image_url,
                        error=str(e)
                    )
            else:
                # ImageKit disabled - use original URL
                processed_data['imagekit_disabled'] = True
                processed_data['fallback_url'] = image_url
                
                logger.debug(
                    "ImageKit disabled, using original URL",
                    image_url=image_url
                )
            
            # Step 3: Prepare final result
            processed_data['integration_status'] = 'completed'
            processed_data['processing_time'] = time.time() - start_time
            
            return processed_data
            
        except Exception as e:
            processing_time = time.time() - start_time
            
            logger.error(
                "ImageKit integration processing failed",
                image_url=image_url,
                coffee_id=coffee_id,
                error=str(e),
                processing_time=processing_time
            )
            
            # Return error result with fallback
            return {
                **image_data,
                'integration_status': 'error',
                'integration_error': str(e),
                'fallback_url': image_url,
                'processing_time': processing_time
            }
        
        finally:
            # Update statistics
            processing_time = time.time() - start_time
            self.stats['images_processed'] += 1
            self.stats['total_processing_time'] += processing_time
    
    def process_batch_with_imagekit(
        self, 
        images_data: List[Dict[str, Any]], 
        coffee_id: str,
        batch_config: Optional[BatchUploadConfig] = None
    ) -> List[Dict[str, Any]]:
        """
        Process multiple images with ImageKit upload and deduplication.
        
        Args:
            images_data: List of image data dictionaries
            coffee_id: Coffee ID for the images
            batch_config: Batch upload configuration
            
        Returns:
            List of processed image data with ImageKit and deduplication information
        """
        start_time = time.time()
        
        logger.info(
            "Starting batch ImageKit integration processing",
            total_images=len(images_data),
            coffee_id=coffee_id,
            enable_deduplication=self.enable_deduplication,
            enable_imagekit=self.enable_imagekit
        )
        
        results = []
        
        # Process each image
        for image_data in images_data:
            try:
                result = self.process_image_with_imagekit(image_data, coffee_id)
                results.append(result)
                
            except Exception as e:
                logger.error(
                    "Failed to process image in batch",
                    image_url=image_data.get('url'),
                    coffee_id=coffee_id,
                    error=str(e)
                )
                
                # Add error result to maintain batch integrity
                results.append({
                    'url': image_data.get('url'),
                    'integration_status': 'error',
                    'integration_error': str(e),
                    'fallback_url': image_data.get('url')
                })
        
        processing_time = time.time() - start_time
        
        # Calculate batch statistics
        successful = sum(1 for r in results if r.get('integration_status') == 'completed')
        failed = len(results) - successful
        duplicates_skipped = sum(1 for r in results if r.get('imagekit_upload_skipped', False))
        imagekit_failures = sum(1 for r in results if r.get('imagekit_upload_failed', False))
        
        logger.info(
            "Batch ImageKit integration processing completed",
            total_images=len(images_data),
            successful=successful,
            failed=failed,
            duplicates_skipped=duplicates_skipped,
            imagekit_failures=imagekit_failures,
            processing_time=processing_time,
            avg_time_per_image=processing_time / len(images_data) if images_data else 0
        )
        
        return results
    
    def get_integration_stats(self) -> Dict[str, Any]:
        """
        Get integration service statistics.
        
        Returns:
            Dictionary with integration statistics
        """
        stats = self.stats.copy()
        
        # Calculate rates
        if stats['images_processed'] > 0:
            stats['success_rate'] = (
                stats['images_processed'] - stats['imagekit_failures']
            ) / stats['images_processed']
            stats['duplicate_rate'] = stats['duplicates_skipped'] / stats['images_processed']
            stats['fallback_rate'] = stats['fallback_used'] / stats['images_processed']
            stats['avg_processing_time'] = stats['total_processing_time'] / stats['images_processed']
        else:
            stats['success_rate'] = 0.0
            stats['duplicate_rate'] = 0.0
            stats['fallback_rate'] = 0.0
            stats['avg_processing_time'] = 0.0
        
        # Add service-specific stats
        if self.imagekit_service:
            stats['imagekit_stats'] = self.imagekit_service.get_stats()
        
        if self.deduplication_service:
            stats['deduplication_stats'] = self.deduplication_service.get_deduplication_stats()
        
        return stats
    
    def reset_stats(self):
        """Reset integration service statistics."""
        self.stats = {
            'images_processed': 0,
            'imagekit_uploads': 0,
            'imagekit_failures': 0,
            'duplicates_skipped': 0,
            'fallback_used': 0,
            'total_processing_time': 0.0
        }
        
        if self.imagekit_service:
            self.imagekit_service.reset_stats()
        
        if self.deduplication_service:
            self.deduplication_service.reset_stats()
        
        logger.info("ImageKit integration service statistics reset")
