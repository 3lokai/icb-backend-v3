"""
Configuration for bean species parser.
"""

from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class SpeciesConfig(BaseModel):
    """Configuration for species parser."""
    
    confidence_threshold: float = Field(default=0.7, ge=0.0, le=1.0, description="Minimum confidence for species detection")
    enable_blend_detection: bool = Field(default=True, description="Enable blend detection")
    enable_chicory_detection: bool = Field(default=True, description="Enable chicory mix detection")
    enable_ratio_detection: bool = Field(default=True, description="Enable ratio-based blend detection")
    batch_size: int = Field(default=100, ge=1, description="Batch size for processing")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return self.model_dump()
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'SpeciesConfig':
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

