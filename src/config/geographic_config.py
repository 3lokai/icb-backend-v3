"""
Configuration for Indian Coffee Geographic Parser Service
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class GeographicConfig:
    """Configuration for geographic parser service."""
    
    # Enable/disable geographic parsing
    enable_geographic_parsing: bool = True
    
    # Confidence threshold for geographic detection
    confidence_threshold: float = 0.6
    
    # Enable region-state validation
    enable_region_state_validation: bool = True
    
    # Enable altitude validation
    enable_altitude_validation: bool = True
    
    # Altitude validation settings
    min_altitude_meters: int = 0
    max_altitude_meters: int = 3000
    
    # Enable batch processing optimization
    enable_batch_processing: bool = True
    
    # Logging configuration
    log_level: str = "INFO"
    log_parsing_details: bool = False
    
    # Performance settings
    batch_size: int = 100
    max_processing_time_seconds: int = 30
    
    # Geographic focus settings
    focus_on_indian_regions: bool = True
    include_international_regions: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            'enable_geographic_parsing': self.enable_geographic_parsing,
            'confidence_threshold': self.confidence_threshold,
            'enable_region_state_validation': self.enable_region_state_validation,
            'enable_altitude_validation': self.enable_altitude_validation,
            'min_altitude_meters': self.min_altitude_meters,
            'max_altitude_meters': self.max_altitude_meters,
            'enable_batch_processing': self.enable_batch_processing,
            'log_level': self.log_level,
            'log_parsing_details': self.log_parsing_details,
            'batch_size': self.batch_size,
            'max_processing_time_seconds': self.max_processing_time_seconds,
            'focus_on_indian_regions': self.focus_on_indian_regions,
            'include_international_regions': self.include_international_regions
        }
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'GeographicConfig':
        """Create configuration from dictionary."""
        return cls(
            enable_geographic_parsing=config_dict.get('enable_geographic_parsing', True),
            confidence_threshold=config_dict.get('confidence_threshold', 0.6),
            enable_region_state_validation=config_dict.get('enable_region_state_validation', True),
            enable_altitude_validation=config_dict.get('enable_altitude_validation', True),
            min_altitude_meters=config_dict.get('min_altitude_meters', 0),
            max_altitude_meters=config_dict.get('max_altitude_meters', 3000),
            enable_batch_processing=config_dict.get('enable_batch_processing', True),
            log_level=config_dict.get('log_level', 'INFO'),
            log_parsing_details=config_dict.get('log_parsing_details', False),
            batch_size=config_dict.get('batch_size', 100),
            max_processing_time_seconds=config_dict.get('max_processing_time_seconds', 30),
            focus_on_indian_regions=config_dict.get('focus_on_indian_regions', True),
            include_international_regions=config_dict.get('include_international_regions', True)
        )
