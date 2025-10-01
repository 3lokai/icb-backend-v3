"""
LLM configuration for normalizer pipeline integration.

Features:
- Epic D service configuration
- LLM fallback settings
- Rate limiting and caching configuration
- Confidence evaluation settings
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from structlog import get_logger

from .deepseek_config import DeepSeekConfig
from .cache_config import CacheConfig
from .confidence_config import ConfidenceConfig
from .review_config import ReviewConfig

logger = get_logger(__name__)


class LLMFallbackConfig(BaseModel):
    """Configuration for LLM fallback service."""
    
    enable_fallback: bool = Field(default=True, description="Whether LLM fallback is enabled")
    llm_fallback_threshold: float = Field(default=0.7, description="Confidence threshold for LLM fallback")
    max_llm_retries: int = Field(default=2, description="Maximum LLM retry attempts")
    llm_retry_delay_seconds: int = Field(default=1, description="Delay between retries in seconds")
    timeout_seconds: float = Field(default=60.0, description="LLM timeout in seconds")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return self.model_dump()
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LLMFallbackConfig':
        """Create LLMFallbackConfig from dictionary."""
        return cls(**data)


class LLMConfig(BaseModel):
    """Configuration for LLM fallback integration."""
    
    # Epic D service configurations
    deepseek_config: DeepSeekConfig = Field(default_factory=DeepSeekConfig)
    cache_config: CacheConfig = Field(default_factory=CacheConfig)
    confidence_config: ConfidenceConfig = Field(default_factory=ConfidenceConfig)
    review_config: ReviewConfig = Field(default_factory=ReviewConfig)
    
    # LLM fallback settings
    enabled: bool = Field(default=True, description="Whether LLM fallback is enabled")
    confidence_threshold: float = Field(default=0.7, description="Confidence threshold for LLM fallback")
    timeout_seconds: float = Field(default=60.0, description="LLM timeout in seconds")
    max_retries: int = Field(default=3, description="Maximum LLM retry attempts")
    batch_size: int = Field(default=10, description="Batch size for LLM processing")
    rate_limit_per_minute: int = Field(default=60, description="Rate limit for LLM calls per minute")
    
    # Field-specific settings
    field_configs: Dict[str, Dict[str, Any]] = Field(
        default_factory=lambda: {
            'weight': {'enabled': True, 'confidence_threshold': 0.7},
            'roast': {'enabled': True, 'confidence_threshold': 0.8},
            'process': {'enabled': True, 'confidence_threshold': 0.8},
            'tags': {'enabled': True, 'confidence_threshold': 0.6},
            'notes': {'enabled': True, 'confidence_threshold': 0.6},
            'grind': {'enabled': True, 'confidence_threshold': 0.7},
            'species': {'enabled': True, 'confidence_threshold': 0.8},
            'variety': {'enabled': True, 'confidence_threshold': 0.6},
            'geographic': {'enabled': True, 'confidence_threshold': 0.7},
            'sensory': {'enabled': True, 'confidence_threshold': 0.6}
        },
        description="Field-specific LLM configuration"
    )
    
    # Performance settings
    enable_caching: bool = Field(default=True, description="Enable LLM result caching")
    cache_ttl_seconds: int = Field(default=3600, description="Cache TTL in seconds")
    enable_rate_limiting: bool = Field(default=True, description="Enable rate limiting")
    enable_batch_processing: bool = Field(default=True, description="Enable batch processing")
    
    # Error handling
    enable_graceful_degradation: bool = Field(default=True, description="Enable graceful degradation on LLM failures")
    fallback_to_deterministic: bool = Field(default=True, description="Fallback to deterministic results on LLM failure")
    
    def get_field_config(self, field: str) -> Dict[str, Any]:
        """Get configuration for specific field."""
        return self.field_configs.get(field, {
            'enabled': True,
            'confidence_threshold': self.confidence_threshold
        })
    
    def is_field_enabled(self, field: str) -> bool:
        """Check if LLM fallback is enabled for specific field."""
        field_config = self.get_field_config(field)
        return field_config.get('enabled', True) and self.enabled
    
    def get_field_threshold(self, field: str) -> float:
        """Get confidence threshold for specific field."""
        field_config = self.get_field_config(field)
        return field_config.get('confidence_threshold', self.confidence_threshold)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return self.model_dump()
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LLMConfig':
        """Create LLMConfig from dictionary."""
        return cls(**data)

