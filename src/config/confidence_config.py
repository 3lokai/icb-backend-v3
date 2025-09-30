"""Configuration for confidence evaluation service."""

from pydantic import BaseModel, Field
from typing import Dict, List, Optional
from dataclasses import dataclass


class ConfidenceConfig(BaseModel):
    """Configuration for confidence evaluation service."""
    
    # Default confidence threshold
    confidence_threshold: float = Field(default=0.7, ge=0.0, le=1.0)
    
    # Field-specific thresholds
    field_thresholds: Dict[str, float] = Field(default_factory=dict)
    
    # Evaluation rules configuration
    evaluation_rules: List[str] = Field(default_factory=list)
    
    # Performance settings
    batch_size: int = Field(default=100, gt=0)
    evaluation_timeout: float = Field(default=0.1, gt=0)  # 100ms max per evaluation
    
    # Error handling
    max_retries: int = Field(default=3, ge=0)
    retry_delay: float = Field(default=0.1, gt=0)
    
    # Logging
    log_evaluations: bool = Field(default=True)
    log_confidence_scores: bool = Field(default=True)


@dataclass
class EvaluationRule:
    """Individual evaluation rule for confidence scoring."""
    
    name: str
    field_pattern: str  # Regex pattern to match fields
    confidence_multiplier: float = 1.0
    confidence_bonus: float = 0.0
    min_confidence: float = 0.0
    max_confidence: float = 1.0
    
    def matches(self, field: str) -> bool:
        """Check if this rule matches the given field."""
        import re
        return bool(re.match(self.field_pattern, field))
    
    def apply(self, confidence: float) -> float:
        """Apply this rule to the confidence score."""
        # Apply multiplier
        adjusted = confidence * self.confidence_multiplier
        
        # Apply bonus
        adjusted += self.confidence_bonus
        
        # Clamp to min/max bounds
        return max(self.min_confidence, min(self.max_confidence, adjusted))


class ConfidenceConfigBuilder:
    """Builder for confidence configuration with common presets."""
    
    @staticmethod
    def default() -> ConfidenceConfig:
        """Create default confidence configuration."""
        return ConfidenceConfig()
    
    @staticmethod
    def strict() -> ConfidenceConfig:
        """Create strict confidence configuration (higher thresholds)."""
        return ConfidenceConfig(
            confidence_threshold=0.8,
            field_thresholds={
                "roast_level": 0.9,
                "process_method": 0.85,
                "bean_species": 0.9,
                "varieties": 0.75,
                "geographic_data": 0.8,
                "sensory_parameters": 0.85
            }
        )
    
    @staticmethod
    def permissive() -> ConfidenceConfig:
        """Create permissive confidence configuration (lower thresholds)."""
        return ConfidenceConfig(
            confidence_threshold=0.6,
            field_thresholds={
                "roast_level": 0.7,
                "process_method": 0.65,
                "bean_species": 0.7,
                "varieties": 0.6,
                "geographic_data": 0.65,
                "sensory_parameters": 0.7
            }
        )
    
    @staticmethod
    def custom(threshold: float, field_thresholds: Dict[str, float] = None) -> ConfidenceConfig:
        """Create custom confidence configuration."""
        return ConfidenceConfig(
            confidence_threshold=threshold,
            field_thresholds=field_thresholds or {}
        )
