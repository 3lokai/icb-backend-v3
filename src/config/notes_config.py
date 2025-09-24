"""
Configuration for notes extraction service.
"""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


class NotesConfig(BaseModel):
    """Configuration for notes extraction service."""
    
    # Service enablement
    enable_notes_extraction: bool = Field(default=True, description="Enable notes extraction")
    
    # Confidence thresholds
    notes_confidence_threshold: float = Field(
        default=0.6, 
        ge=0.0, 
        le=1.0, 
        description="Minimum confidence for notes extraction"
    )
    
    # Batch processing settings
    batch_size: int = Field(
        default=100, 
        ge=1, 
        description="Batch size for processing multiple products"
    )
    
    # Extraction patterns (can be overridden)
    custom_patterns: Optional[List[str]] = Field(
        default=None, 
        description="Custom extraction patterns"
    )
    
    # Pattern confidence levels
    high_confidence_threshold: float = Field(
        default=0.9, 
        ge=0.0, 
        le=1.0, 
        description="Confidence for high-confidence patterns"
    )
    
    medium_confidence_threshold: float = Field(
        default=0.7, 
        ge=0.0, 
        le=1.0, 
        description="Confidence for medium-confidence patterns"
    )
    
    low_confidence_threshold: float = Field(
        default=0.5, 
        ge=0.0, 
        le=1.0, 
        description="Confidence for low-confidence patterns"
    )
    
    # Text processing settings
    min_note_length: int = Field(
        default=3, 
        ge=1, 
        description="Minimum length for extracted notes"
    )
    
    max_note_length: int = Field(
        default=200, 
        ge=10, 
        description="Maximum length for extracted notes"
    )
    
    # Performance settings
    max_notes_per_product: int = Field(
        default=20, 
        ge=1, 
        description="Maximum notes to extract per product"
    )
    
    # Logging settings
    log_warnings: bool = Field(
        default=True, 
        description="Log extraction warnings"
    )
    
    @field_validator('notes_confidence_threshold', 'high_confidence_threshold', 
                     'medium_confidence_threshold', 'low_confidence_threshold')
    @classmethod
    def validate_confidence_thresholds(cls, v):
        """Validate confidence thresholds are within bounds."""
        if not 0.0 <= v <= 1.0:
            raise ValueError("Confidence thresholds must be between 0.0 and 1.0")
        return v
    
    @field_validator('batch_size', 'min_note_length', 'max_note_length', 'max_notes_per_product')
    @classmethod
    def validate_positive_integers(cls, v):
        """Validate positive integer fields."""
        if v <= 0:
            raise ValueError("Must be a positive integer")
        return v
    
    @field_validator('max_note_length')
    @classmethod
    def validate_max_note_length(cls, v, info):
        """Validate max note length is greater than min note length."""
        if 'min_note_length' in info.data and v <= info.data['min_note_length']:
            raise ValueError("max_note_length must be greater than min_note_length")
        return v
    
    def to_dict(self) -> Dict[str, any]:
        """Convert configuration to dictionary."""
        return self.model_dump()
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, any]) -> 'NotesConfig':
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
            confidence_fields = [
                self.notes_confidence_threshold,
                self.high_confidence_threshold,
                self.medium_confidence_threshold,
                self.low_confidence_threshold
            ]
            
            for threshold in confidence_fields:
                if not 0.0 <= threshold <= 1.0:
                    return False
            
            # Validate batch size
            if self.batch_size <= 0:
                return False
            
            # Validate note length constraints
            if self.min_note_length <= 0 or self.max_note_length <= 0:
                return False
            
            if self.max_note_length <= self.min_note_length:
                return False
            
            # Validate max notes per product
            if self.max_notes_per_product <= 0:
                return False
            
            return True
            
        except Exception:
            return False
