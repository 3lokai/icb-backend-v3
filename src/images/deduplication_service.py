"""
Image deduplication service for content-based duplicate detection.

This service integrates with the existing A.1-A.5 pipeline to provide
image deduplication based on SHA256 content hashing.
"""

from typing import Dict, Any, Optional, List, Tuple
from structlog import get_logger

from .hash_computation import ImageHashComputer, ImageHashComputationError
from ..validator.rpc_client import RPCClient

logger = get_logger(__name__)


class ImageDeduplicationError(Exception):
    """Exception raised for image deduplication errors."""
    pass


class ImageDeduplicationService:
    """
    Service for image deduplication based on content hashing.
    
    Features:
    - Content-based duplicate detection using SHA256 hashes
    - Integration with existing A.1-A.5 pipeline
    - Database integration for hash storage and lookup
    - Batch processing optimization
    - Performance monitoring and caching
    """
    
    def __init__(self, rpc_client: RPCClient, hash_computer: Optional[ImageHashComputer] = None):
        """
        Initialize image deduplication service.
        
        Args:
            rpc_client: RPC client for database operations
            hash_computer: Image hash computer instance (optional)
        """
        self.rpc_client = rpc_client
        self.hash_computer = hash_computer or ImageHashComputer()
        
        # Deduplication statistics
        self.stats = {
            'images_processed': 0,
            'duplicates_found': 0,
            'new_images': 0,
            'deduplication_errors': 0,
            'cache_hits': 0
        }
    
    def process_image_with_deduplication(
        self, 
        image_data: Dict[str, Any],
        coffee_id: str
    ) -> Dict[str, Any]:
        """
        Process image with deduplication logic.
        
        Args:
            image_data: Image data dictionary with URL and metadata
            coffee_id: Coffee ID for the image
            
        Returns:
            Processed image data with deduplication status
            
        Raises:
            ImageDeduplicationError: If deduplication processing fails
        """
        try:
            self.stats['images_processed'] += 1
            
            image_url = image_data.get('url')
            if not image_url:
                raise ImageDeduplicationError("Image URL is required")
            
            logger.debug(
                "Processing image with deduplication",
                image_url=image_url,
                coffee_id=coffee_id
            )
            
            # Compute image hash
            content_hash = self.hash_computer.compute_image_hash(image_url)
            
            # Check for existing hash in database
            existing_image_id = self._check_duplicate_hash(content_hash)
            
            if existing_image_id:
                # Duplicate found - skip upload
                self.stats['duplicates_found'] += 1
                
                logger.info(
                    "Duplicate image detected, skipping upload",
                    image_url=image_url,
                    content_hash=content_hash,
                    existing_image_id=existing_image_id
                )
                
                return {
                    'image_id': existing_image_id,
                    'url': image_url,
                    'content_hash': content_hash,
                    'is_duplicate': True,
                    'deduplication_status': 'skipped_duplicate'
                }
            else:
                # New image - proceed with upload
                self.stats['new_images'] += 1
                
                logger.info(
                    "New image detected, proceeding with upload",
                    image_url=image_url,
                    content_hash=content_hash
                )
                
                # Add content hash to image data
                image_data['content_hash'] = content_hash
                image_data['is_duplicate'] = False
                image_data['deduplication_status'] = 'new_image'
                
                return image_data
                
        except Exception as e:
            self.stats['deduplication_errors'] += 1
            
            logger.error(
                "Failed to process image with deduplication",
                image_url=image_data.get('url'),
                coffee_id=coffee_id,
                error=str(e)
            )
            
            raise ImageDeduplicationError(
                f"Failed to process image {image_data.get('url')}: {str(e)}"
            )
    
    def _check_duplicate_hash(self, content_hash: str) -> Optional[str]:
        """
        Check if image hash exists in database.
        
        Args:
            content_hash: SHA256 hash to check
            
        Returns:
            Existing image ID if found, None if new
        """
        try:
            logger.debug(
                "Checking for duplicate hash",
                content_hash=content_hash
            )
            
            # Query database for existing hash using RPC function
            existing_image_id = self.rpc_client.check_content_hash(content_hash)
            
            if existing_image_id:
                logger.debug(
                    "Duplicate hash found in database",
                    content_hash=content_hash,
                    existing_image_id=existing_image_id
                )
                return existing_image_id
            else:
                logger.debug(
                    "No duplicate hash found in database",
                    content_hash=content_hash
                )
                return None
            
        except Exception as e:
            logger.error(
                "Failed to check duplicate hash",
                content_hash=content_hash,
                error=str(e)
            )
            # Return None to allow processing to continue
            return None
    
    def process_batch_with_deduplication(
        self, 
        images_data: List[Dict[str, Any]], 
        coffee_id: str
    ) -> List[Dict[str, Any]]:
        """
        Process multiple images with deduplication logic.
        
        Args:
            images_data: List of image data dictionaries
            coffee_id: Coffee ID for the images
            
        Returns:
            List of processed image data with deduplication status
        """
        results = []
        
        logger.info(
            "Processing batch of images with deduplication",
            total_images=len(images_data),
            coffee_id=coffee_id
        )
        
        for image_data in images_data:
            try:
                result = self.process_image_with_deduplication(image_data, coffee_id)
                results.append(result)
                
            except ImageDeduplicationError as e:
                logger.warning(
                    "Failed to process image in batch",
                    image_url=image_data.get('url'),
                    error=str(e)
                )
                # Add error result to maintain batch integrity
                results.append({
                    'url': image_data.get('url'),
                    'error': str(e),
                    'deduplication_status': 'error'
                })
                continue
        
        logger.info(
            "Batch deduplication processing completed",
            total_images=len(images_data),
            successful=len([r for r in results if 'error' not in r]),
            failed=len([r for r in results if 'error' in r])
        )
        
        return results
    
    def get_deduplication_stats(self) -> Dict[str, Any]:
        """
        Get deduplication statistics.
        
        Returns:
            Dictionary with deduplication statistics
        """
        stats = self.stats.copy()
        
        # Calculate rates
        if stats['images_processed'] > 0:
            stats['duplicate_rate'] = stats['duplicates_found'] / stats['images_processed']
            stats['new_image_rate'] = stats['new_images'] / stats['images_processed']
            stats['error_rate'] = stats['deduplication_errors'] / stats['images_processed']
        else:
            stats['duplicate_rate'] = 0.0
            stats['new_image_rate'] = 0.0
            stats['error_rate'] = 0.0
        
        # Add hash computation stats
        stats['hash_computation'] = self.hash_computer.get_stats()
        
        return stats
    
    def reset_stats(self):
        """Reset deduplication statistics."""
        self.stats = {
            'images_processed': 0,
            'duplicates_found': 0,
            'new_images': 0,
            'deduplication_errors': 0,
            'cache_hits': 0
        }
        self.hash_computer.reset_stats()
