"""
Configuration for image processing and deduplication services.
"""

from typing import Dict, Any
from dataclasses import dataclass


@dataclass
class ImageProcessingConfig:
    """Configuration for image processing services."""
    
    # Hash computation settings
    hash_timeout: int = 30
    hash_max_retries: int = 3
    hash_cache_size: int = 1000
    
    # Batch processing settings
    batch_size: int = 100
    batch_timeout: int = 300
    
    # Performance settings
    enable_caching: bool = True
    enable_batch_processing: bool = True
    
    # Database settings
    content_hash_column: str = 'content_hash'
    content_hash_index: str = 'idx_coffee_images_content_hash'
    
    # Logging settings
    log_performance: bool = True
    log_deduplication_stats: bool = True


# Default configuration
DEFAULT_CONFIG = ImageProcessingConfig()


def get_config() -> ImageProcessingConfig:
    """
    Get image processing configuration.
    
    Returns:
        ImageProcessingConfig instance
    """
    return DEFAULT_CONFIG


def update_config(**kwargs) -> ImageProcessingConfig:
    """
    Update configuration with new values.
    
    Args:
        **kwargs: Configuration values to update
        
    Returns:
        Updated ImageProcessingConfig instance
    """
    global DEFAULT_CONFIG
    
    # Create new config with updated values
    config_dict = DEFAULT_CONFIG.__dict__.copy()
    config_dict.update(kwargs)
    
    DEFAULT_CONFIG = ImageProcessingConfig(**config_dict)
    return DEFAULT_CONFIG
