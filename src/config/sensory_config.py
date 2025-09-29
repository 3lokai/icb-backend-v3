"""
Configuration for sensory parameter parsing.
"""

from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field, field_validator


class SensoryConfig(BaseModel):
    """Configuration for sensory parameter parsing."""
    
    # Pattern configuration
    acidity_patterns: Dict[str, List[str]] = Field(
        default={
            'low': [r'low\s*acidity', r'mild\s*acidity', r'smooth', r'soft'],
            'medium': [r'medium\s*acidity', r'balanced\s*acidity', r'moderate'],
            'high': [r'high\s*acidity', r'bright\s*acidity', r'citrus', r'lemon', r'orange']
        },
        description="Patterns for acidity detection"
    )
    
    body_patterns: Dict[str, List[str]] = Field(
        default={
            'light': [r'light\s*body', r'thin\s*body', r'delicate', r'clean'],
            'medium': [r'medium\s*body', r'balanced\s*body', r'moderate'],
            'full': [r'full\s*body', r'heavy\s*body', r'rich', r'bold', r'creamy']
        },
        description="Patterns for body detection"
    )
    
    sweetness_patterns: Dict[str, List[str]] = Field(
        default={
            'low': [r'low\s*sweetness', r'dry', r'bitter'],
            'medium': [r'medium\s*sweetness', r'balanced\s*sweetness'],
            'high': [r'high\s*sweetness', r'sweet', r'caramel', r'honey']
        },
        description="Patterns for sweetness detection"
    )
    
    bitterness_patterns: Dict[str, List[str]] = Field(
        default={
            'low': [r'low\s*bitterness', r'smooth', r'mild'],
            'medium': [r'medium\s*bitterness', r'balanced\s*bitterness'],
            'high': [r'high\s*bitterness', r'bitter', r'strong']
        },
        description="Patterns for bitterness detection"
    )
    
    aftertaste_patterns: Dict[str, List[str]] = Field(
        default={
            'short': [r'short\s*aftertaste', r'clean\s*finish'],
            'medium': [r'medium\s*aftertaste', r'balanced\s*finish'],
            'long': [r'long\s*aftertaste', r'lingering\s*finish', r'persistent']
        },
        description="Patterns for aftertaste detection"
    )
    
    clarity_patterns: Dict[str, List[str]] = Field(
        default={
            'low': [r'low\s*clarity', r'muddy', r'cloudy'],
            'medium': [r'medium\s*clarity', r'balanced\s*clarity'],
            'high': [r'high\s*clarity', r'clear', r'clean', r'bright']
        },
        description="Patterns for clarity detection"
    )
    
    # Numeric rating mapping
    rating_mapping: Dict[str, float] = Field(
        default={
            'low': 3.0,
            'short': 3.0,
            'medium': 6.0,
            'high': 8.5,
            'long': 8.5
        },
        description="Mapping from text levels to numeric ratings (1-10 scale)"
    )
    
    # Confidence scoring
    confidence_threshold: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Minimum confidence threshold for sensory parameter extraction"
    )
    
    # Source tracking
    default_source: str = Field(
        default="icb_inferred",
        description="Default source for sensory parameters"
    )
    
    # Batch processing
    batch_size: int = Field(
        default=100,
        ge=1,
        description="Batch size for processing multiple products"
    )
    
    # Performance settings
    max_processing_time_seconds: int = Field(
        default=4,
        ge=1,
        description="Maximum processing time for batch operations"
    )
    
    @field_validator('acidity_patterns', 'body_patterns', 'sweetness_patterns', 
                    'bitterness_patterns', 'aftertaste_patterns', 'clarity_patterns')
    @classmethod
    def validate_patterns(cls, v):
        """Validate pattern dictionaries."""
        if not isinstance(v, dict):
            raise ValueError("Patterns must be dictionaries")
        
        for level, patterns in v.items():
            if not isinstance(patterns, list):
                raise ValueError(f"Patterns for level '{level}' must be a list")
            
            for pattern in patterns:
                if not isinstance(pattern, str):
                    raise ValueError(f"Pattern must be a string, got {type(pattern)}")
        
        return v
    
    @field_validator('rating_mapping')
    @classmethod
    def validate_rating_mapping(cls, v):
        """Validate rating mapping."""
        if not isinstance(v, dict):
            raise ValueError("Rating mapping must be a dictionary")
        
        for level, rating in v.items():
            if not isinstance(rating, (int, float)):
                raise ValueError(f"Rating for level '{level}' must be numeric")
            if not (1.0 <= rating <= 10.0):
                raise ValueError(f"Rating for level '{level}' must be between 1.0 and 10.0")
        
        return v
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return self.model_dump()
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'SensoryConfig':
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
