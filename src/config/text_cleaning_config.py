"""
Configuration for text cleaning service.
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class TextCleaningConfig(BaseModel):
    """Configuration for text cleaning service."""
    
    # HTML cleaning options
    use_beautifulsoup: bool = Field(default=True, description="Use BeautifulSoup for HTML parsing")
    remove_html_tags: bool = Field(default=True, description="Remove HTML tags")
    decode_html_entities: bool = Field(default=True, description="Decode HTML entities")
    
    # Special character handling
    normalize_unicode: bool = Field(default=True, description="Normalize unicode characters")
    remove_control_characters: bool = Field(default=True, description="Remove control characters")
    
    # Whitespace normalization
    normalize_whitespace: bool = Field(default=True, description="Normalize whitespace")
    preserve_line_breaks: bool = Field(default=False, description="Preserve line breaks")
    
    # Cleaning rules
    cleaning_rules: Dict[str, Any] = Field(
        default_factory=lambda: {
            "remove_extra_spaces": True,
            "remove_tabs": True,
            "remove_newlines": True,
            "strip_whitespace": True
        },
        description="Text cleaning rules"
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
