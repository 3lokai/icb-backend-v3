"""
Configuration for tag normalization service.
"""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


class TagConfig(BaseModel):
    """Configuration for tag normalization service."""
    
    # Service enablement
    enable_tag_normalization: bool = Field(default=True, description="Enable tag normalization")
    
    # Confidence thresholds
    tag_confidence_threshold: float = Field(
        default=0.7, 
        ge=0.0, 
        le=1.0, 
        description="Minimum confidence for tag normalization"
    )
    
    # Batch processing settings
    batch_size: int = Field(
        default=100, 
        ge=1, 
        description="Batch size for processing multiple products"
    )
    
    # Category mappings (can be overridden)
    custom_categories: Optional[Dict[str, List[str]]] = Field(
        default=None, 
        description="Custom category mappings"
    )
    
    # Fuzzy matching settings
    enable_fuzzy_matching: bool = Field(
        default=True, 
        description="Enable fuzzy matching for tag variations"
    )
    
    fuzzy_confidence_threshold: float = Field(
        default=0.6, 
        ge=0.0, 
        le=1.0, 
        description="Minimum confidence for fuzzy matches"
    )
    
    # Performance settings
    max_tags_per_product: int = Field(
        default=50, 
        ge=1, 
        description="Maximum tags to process per product"
    )
    
    # Logging settings
    log_warnings: bool = Field(
        default=True, 
        description="Log normalization warnings"
    )
    
    @field_validator('tag_confidence_threshold', 'fuzzy_confidence_threshold')
    @classmethod
    def validate_confidence_thresholds(cls, v):
        """Validate confidence thresholds are within bounds."""
        if not 0.0 <= v <= 1.0:
            raise ValueError("Confidence thresholds must be between 0.0 and 1.0")
        return v
    
    @field_validator('batch_size', 'max_tags_per_product')
    @classmethod
    def validate_positive_integers(cls, v):
        """Validate positive integer fields."""
        if v <= 0:
            raise ValueError("Must be a positive integer")
        return v
    
    def to_dict(self) -> Dict[str, any]:
        """Convert configuration to dictionary."""
        return self.model_dump()
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, any]) -> 'TagConfig':
        """Create configuration from dictionary."""
        return cls.model_validate(config_dict)
    
    def validate_config(self) -> bool:
        """
        Validate configuration settings.
        
        Returns:
            True if configuration is valid
        """
        try:
            # Validate confidence thresholds
            if self.tag_confidence_threshold < 0.0 or self.tag_confidence_threshold > 1.0:
                return False
            
            if self.fuzzy_confidence_threshold < 0.0 or self.fuzzy_confidence_threshold > 1.0:
                return False
            
            # Validate batch size
            if self.batch_size <= 0:
                return False
            
            # Validate max tags per product
            if self.max_tags_per_product <= 0:
                return False
            
            return True
            
        except Exception:
            return False
