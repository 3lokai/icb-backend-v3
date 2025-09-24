"""
ImageKit configuration and settings for image upload integration.

Provides configuration management for ImageKit CDN integration
with retry logic, authentication, and performance optimization.
"""

from typing import Optional, Dict, Any, List, Callable
from enum import Enum
from pydantic import BaseModel, Field, field_validator


class ImageKitTransformation(Enum):
    """ImageKit transformation options."""
    MAINTAIN_RATIO = "maintain_ratio"
    CROP = "crop"
    FILL = "fill"
    SCALE = "scale"


class ImageKitConfig(BaseModel):
    """
    Configuration for ImageKit CDN integration.
    """
    public_key: str = Field(..., description="ImageKit public key")
    private_key: str = Field(..., description="ImageKit private key")
    url_endpoint: str = Field(..., description="ImageKit URL endpoint")
    folder: str = Field(default="/coffee-images/", description="Upload folder")
    default_transformation: Optional[Dict[str, Any]] = Field(default=None, description="Default transformation for uploaded images")
    enabled: bool = Field(default=True, description="Enable ImageKit upload")
    
    @field_validator('public_key')
    @classmethod
    def validate_public_key(cls, v):
        if not v.startswith('public_'):
            raise ValueError("Public key must start with 'public_'")
        return v
    
    @field_validator('private_key')
    @classmethod
    def validate_private_key(cls, v):
        if not v.startswith('private_'):
            raise ValueError("Private key must start with 'private_'")
        return v
    
    @field_validator('url_endpoint')
    @classmethod
    def validate_url_endpoint(cls, v):
        if not v.startswith('https://'):
            raise ValueError("URL endpoint must be HTTPS")
        return v
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return self.model_dump()
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'ImageKitConfig':
        """Create configuration from dictionary."""
        return cls(**config_dict)


class ImageKitResult(BaseModel):
    """
    Result of ImageKit upload operation.
    
    Attributes:
        success: Whether the upload was successful
        imagekit_url: ImageKit CDN URL (if successful)
        file_id: ImageKit file ID (if successful)
        error: Error message (if failed)
        original_url: Original image URL
        upload_time: Time taken for upload in seconds
    """
    success: bool
    imagekit_url: Optional[str] = None
    file_id: Optional[str] = None
    error: Optional[str] = None
    original_url: Optional[str] = None
    upload_time: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return self.model_dump()
    
    @classmethod
    def from_dict(cls, result_dict: Dict[str, Any]) -> 'ImageKitResult':
        """Create result from dictionary."""
        return cls(**result_dict)


class RetryConfig(BaseModel):
    """
    Configuration for retry logic with exponential backoff.
    
    Attributes:
        max_retries: Maximum number of retry attempts
        backoff_factor: Exponential backoff multiplier
        initial_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        status_forcelist: HTTP status codes that trigger retry
    """
    max_retries: int = Field(default=3, ge=1, le=10, description="Maximum retry attempts")
    backoff_factor: float = Field(default=2.0, ge=1.0, le=5.0, description="Exponential backoff multiplier")
    initial_delay: float = Field(default=1.0, ge=0.1, le=10.0, description="Initial delay in seconds")
    max_delay: float = Field(default=60.0, ge=1.0, le=300.0, description="Maximum delay in seconds")
    status_forcelist: List[int] = Field(default_factory=lambda: [500, 502, 503, 504, 429], description="HTTP status codes that trigger retry")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return self.model_dump()
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'RetryConfig':
        """Create configuration from dictionary."""
        return cls(**config_dict)


class BatchUploadConfig(BaseModel):
    """
    Configuration for batch upload operations.
    
    Attributes:
        batch_size: Number of images per batch
        max_concurrent: Maximum concurrent uploads
        progress_callback: Callback function for progress updates
        error_callback: Callback function for error handling
    """
    batch_size: int = Field(default=10, ge=1, le=100, description="Number of images per batch")
    max_concurrent: int = Field(default=5, ge=1, le=20, description="Maximum concurrent uploads")
    progress_callback: Optional[Callable] = Field(default=None, description="Progress callback function")
    error_callback: Optional[Callable] = Field(default=None, description="Error callback function")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return self.model_dump()
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'BatchUploadConfig':
        """Create configuration from dictionary."""
        return cls(**config_dict)


def create_default_config(
    public_key: str,
    private_key: str,
    url_endpoint: str,
    **kwargs
) -> ImageKitConfig:
    """
    Create default ImageKit configuration with validation.
    
    Args:
        public_key: ImageKit public key
        private_key: ImageKit private key
        url_endpoint: ImageKit URL endpoint
        **kwargs: Additional configuration options
        
    Returns:
        Configured ImageKitConfig instance
    """
    return ImageKitConfig(
        public_key=public_key,
        private_key=private_key,
        url_endpoint=url_endpoint,
        **kwargs
    )


def create_retry_config(**kwargs) -> RetryConfig:
    """
    Create retry configuration with validation.
    
    Args:
        **kwargs: Retry configuration options
        
    Returns:
        Configured RetryConfig instance
    """
    return RetryConfig(**kwargs)


def create_batch_config(**kwargs) -> BatchUploadConfig:
    """
    Create batch upload configuration with validation.
    
    Args:
        **kwargs: Batch configuration options
        
    Returns:
        Configured BatchUploadConfig instance
    """
    return BatchUploadConfig(**kwargs)
