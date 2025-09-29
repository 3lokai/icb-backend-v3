"""
Configuration for Indian Coffee Variety Extraction Service
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class VarietyConfig:
    """Configuration for variety extraction service."""
    
    # Enable/disable variety extraction
    enable_variety_extraction: bool = True
    
    # Confidence threshold for variety detection
    confidence_threshold: float = 0.7
    
    # Maximum number of varieties to extract per description
    max_varieties_per_description: int = 5
    
    # Enable conflict detection
    enable_conflict_detection: bool = True
    
    # Enable batch processing optimization
    enable_batch_processing: bool = True
    
    # Logging configuration
    log_level: str = "INFO"
    log_extraction_details: bool = False
    
    # Performance settings
    batch_size: int = 100
    max_processing_time_seconds: int = 30
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            'enable_variety_extraction': self.enable_variety_extraction,
            'confidence_threshold': self.confidence_threshold,
            'max_varieties_per_description': self.max_varieties_per_description,
            'enable_conflict_detection': self.enable_conflict_detection,
            'enable_batch_processing': self.enable_batch_processing,
            'log_level': self.log_level,
            'log_extraction_details': self.log_extraction_details,
            'batch_size': self.batch_size,
            'max_processing_time_seconds': self.max_processing_time_seconds
        }
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'VarietyConfig':
        """Create configuration from dictionary."""
        return cls(
            enable_variety_extraction=config_dict.get('enable_variety_extraction', True),
            confidence_threshold=config_dict.get('confidence_threshold', 0.7),
            max_varieties_per_description=config_dict.get('max_varieties_per_description', 5),
            enable_conflict_detection=config_dict.get('enable_conflict_detection', True),
            enable_batch_processing=config_dict.get('enable_batch_processing', True),
            log_level=config_dict.get('log_level', 'INFO'),
            log_extraction_details=config_dict.get('log_extraction_details', False),
            batch_size=config_dict.get('batch_size', 100),
            max_processing_time_seconds=config_dict.get('max_processing_time_seconds', 30)
        )
