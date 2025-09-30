"""
Configuration for text normalization service.
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class TextNormalizationConfig(BaseModel):
    """Configuration for text normalization service."""
    
    # Case normalization
    normalize_case: bool = Field(default=False, description="Enable case normalization")
    case_style: str = Field(default="preserve", description="Case style: preserve, title, lower, upper, sentence")
    
    # Spacing normalization
    normalize_spacing: bool = Field(default=True, description="Normalize spacing")
    remove_extra_spaces: bool = Field(default=True, description="Remove extra spaces")
    normalize_punctuation_spacing: bool = Field(default=True, description="Normalize spacing around punctuation")
    
    # Punctuation normalization
    normalize_punctuation: bool = Field(default=True, description="Normalize punctuation")
    standardize_quotes: bool = Field(default=True, description="Standardize quote characters")
    standardize_dashes: bool = Field(default=True, description="Standardize dash characters")
    
    # Normalization rules
    normalization_rules: Dict[str, Any] = Field(
        default_factory=lambda: {
            "preserve_apostrophes": True,
            "preserve_hyphens": True,
            "normalize_ellipsis": True,
            "standardize_quotes": True
        },
        description="Text normalization rules"
    )
    
    # Performance settings
    batch_size: int = Field(default=100, description="Batch size for processing")
    max_text_length: int = Field(default=10000, description="Maximum text length to process")
    
    # Error handling
    fail_on_error: bool = Field(default=False, description="Fail on processing errors")
    log_errors: bool = Field(default=True, description="Log processing errors")
    
    # Confidence scoring
    enable_confidence_scoring: bool = Field(default=True, description="Enable confidence scoring")
    confidence_threshold: float = Field(default=0.8, description="Confidence threshold for warnings")
    
    class Config:
        """Pydantic configuration."""
        extra = "forbid"
        validate_assignment = True
