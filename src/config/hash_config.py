"""
Configuration for content hash generation.
"""

from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field, field_validator


class HashConfig(BaseModel):
    """Configuration for content hash generation."""
    
    # Hash algorithm configuration
    hash_algorithm: str = Field(
        default="sha256",
        description="Hash algorithm to use (sha256, md5)"
    )
    
    # Content fields for hashing
    content_fields: List[str] = Field(
        default=[
            'title',
            'description', 
            'weight_g',
            'roast_level',
            'process',
            'grind_type',
            'species'
        ],
        description="Fields to include in content hash for change detection"
    )
    
    # Raw payload configuration
    include_raw_payload: bool = Field(
        default=True,
        description="Whether to generate raw payload hash"
    )
    
    # Hash collision detection
    enable_collision_detection: bool = Field(
        default=True,
        description="Enable hash collision detection and handling"
    )
    
    # Batch processing
    batch_size: int = Field(
        default=100,
        ge=1,
        description="Batch size for processing multiple artifacts"
    )
    
    # Performance settings
    max_processing_time_seconds: int = Field(
        default=1,
        ge=1,
        description="Maximum processing time for hash generation per artifact"
    )
    
    # Memory optimization
    max_memory_usage_mb: int = Field(
        default=200,
        ge=1,
        description="Maximum memory usage for batch processing"
    )
    
    @field_validator('hash_algorithm')
    @classmethod
    def validate_hash_algorithm(cls, v):
        """Validate hash algorithm."""
        supported_algorithms = ['sha256', 'md5']
        if v not in supported_algorithms:
            raise ValueError(f"Hash algorithm must be one of {supported_algorithms}")
        return v
    
    @field_validator('content_fields')
    @classmethod
    def validate_content_fields(cls, v):
        """Validate content fields."""
        if not isinstance(v, list):
            raise ValueError("Content fields must be a list")
        
        if not v:
            raise ValueError("Content fields cannot be empty")
        
        for field in v:
            if not isinstance(field, str):
                raise ValueError(f"Content field must be a string, got {type(field)}")
        
        return v
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return self.model_dump()
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'HashConfig':
        """Create configuration from dictionary."""
        return cls.model_validate(config_dict)
    
    def validate_config(self) -> bool:
        """
        Validate configuration settings.
        
        Returns:
            True if configuration is valid
        """
        try:
            # Pydantic validation is handled automatically
            return True
        except Exception:
            return False
