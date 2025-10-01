"""
Configuration for normalizer pipeline orchestration.

Features:
- Pipeline execution configuration
- Parser enablement flags
- LLM fallback configuration
- Error recovery settings
- Performance optimization settings
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from structlog import get_logger

logger = get_logger(__name__)


class ParserConfig(BaseModel):
    """Configuration for individual parsers."""
    
    enabled: bool = Field(default=True, description="Whether parser is enabled")
    confidence_threshold: float = Field(default=0.7, description="Confidence threshold for parser")
    timeout_seconds: float = Field(default=30.0, description="Parser timeout in seconds")
    retry_attempts: int = Field(default=2, description="Number of retry attempts")
    custom_config: Dict[str, Any] = Field(default_factory=dict, description="Parser-specific configuration")


class LLMFallbackConfig(BaseModel):
    """Configuration for LLM fallback service."""
    
    # LLM fallback settings
    enabled: bool = Field(default=True, description="Whether LLM fallback is enabled")
    confidence_threshold: float = Field(default=0.7, ge=0.0, le=1.0, description="Confidence threshold for LLM fallback")
    timeout_seconds: float = Field(default=60.0, gt=0, description="LLM timeout in seconds")
    max_retries: int = Field(default=3, ge=0, description="Maximum LLM retry attempts")
    batch_size: int = Field(default=10, gt=0, description="Batch size for LLM processing")
    rate_limit_per_minute: int = Field(default=60, gt=0, description="Rate limit for LLM calls per minute")


class ErrorRecoveryConfig(BaseModel):
    """Configuration for error recovery."""
    
    enabled: bool = Field(default=True, description="Whether error recovery is enabled")
    max_retries: int = Field(default=3, description="Maximum retry attempts")
    retry_delay_seconds: float = Field(default=1.0, description="Delay between retries")
    exponential_backoff: bool = Field(default=True, description="Use exponential backoff")
    max_delay_seconds: float = Field(default=30.0, description="Maximum retry delay")
    graceful_degradation: bool = Field(default=True, description="Continue with partial results on failure")
    recoverable_parser_errors: Dict[str, List[str]] = Field(
        default_factory=lambda: {
            "WeightParser": ["ValueError", "TypeError"],
            "RoastLevelParser": ["ParsingError"],
            "ProcessMethodParser": ["ConnectionError"]
        },
        description="Parser-specific recoverable error types"
    )
    default_recovery_action: str = Field(default="skip", description="Default recovery action")


class PerformanceConfig(BaseModel):
    """Configuration for performance optimization."""
    
    batch_size: int = Field(default=100, description="Batch size for processing")
    max_concurrent_parsers: int = Field(default=5, description="Maximum concurrent parsers")
    memory_limit_mb: int = Field(default=500, description="Memory limit in MB")
    processing_timeout_seconds: float = Field(default=300.0, description="Overall processing timeout")
    enable_parallel_processing: bool = Field(default=True, description="Enable parallel processing")


class PipelineConfig(BaseModel):
    """Main configuration for normalizer pipeline."""
    
    # Parser configurations
    enable_weight_parsing: bool = Field(default=True, description="Enable weight parsing (C.1)")
    enable_roast_parsing: bool = Field(default=True, description="Enable roast level parsing (C.2)")
    enable_process_parsing: bool = Field(default=True, description="Enable process method parsing (C.2)")
    enable_tag_parsing: bool = Field(default=True, description="Enable tag normalization (C.3)")
    enable_notes_parsing: bool = Field(default=True, description="Enable notes extraction (C.3)")
    enable_grind_parsing: bool = Field(default=True, description="Enable grind type parsing (C.4)")
    enable_species_parsing: bool = Field(default=True, description="Enable bean species parsing (C.4)")
    enable_variety_parsing: bool = Field(default=True, description="Enable variety extraction (C.5)")
    enable_geographic_parsing: bool = Field(default=True, description="Enable geographic parsing (C.5)")
    enable_sensory_parsing: bool = Field(default=True, description="Enable sensory parsing (C.6)")
    enable_hash_generation: bool = Field(default=True, description="Enable content hash generation (C.6)")
    enable_text_cleaning: bool = Field(default=True, description="Enable text cleaning (C.7)")
    enable_text_normalization: bool = Field(default=True, description="Enable text normalization (C.7)")
    
    # Parser-specific configurations
    weight_config: ParserConfig = Field(default_factory=ParserConfig)
    roast_config: ParserConfig = Field(default_factory=ParserConfig)
    process_config: ParserConfig = Field(default_factory=ParserConfig)
    tag_config: ParserConfig = Field(default_factory=ParserConfig)
    notes_config: ParserConfig = Field(default_factory=ParserConfig)
    grind_config: ParserConfig = Field(default_factory=ParserConfig)
    species_config: ParserConfig = Field(default_factory=ParserConfig)
    variety_config: ParserConfig = Field(default_factory=ParserConfig)
    geographic_config: ParserConfig = Field(default_factory=ParserConfig)
    sensory_config: ParserConfig = Field(default_factory=ParserConfig)
    hash_config: ParserConfig = Field(default_factory=ParserConfig)
    text_cleaning_config: ParserConfig = Field(default_factory=ParserConfig)
    text_normalization_config: ParserConfig = Field(default_factory=ParserConfig)
    
    # LLM fallback configuration
    llm_fallback: LLMFallbackConfig = Field(default_factory=LLMFallbackConfig)
    
    # Error recovery configuration
    error_recovery: ErrorRecoveryConfig = Field(default_factory=ErrorRecoveryConfig)
    
    # Performance configuration
    performance: PerformanceConfig = Field(default_factory=PerformanceConfig)
    
    # Global settings
    llm_fallback_threshold: float = Field(default=0.7, description="Confidence threshold for LLM fallback")
    enable_checkpointing: bool = Field(default=True, description="Enable pipeline checkpointing")
    enable_metrics: bool = Field(default=True, description="Enable pipeline metrics")
    log_level: str = Field(default="INFO", description="Logging level")
    
    def get_enabled_parsers(self) -> List[str]:
        """Get list of enabled parsers."""
        enabled = []
        
        if self.enable_weight_parsing:
            enabled.append('weight')
        if self.enable_roast_parsing:
            enabled.append('roast')
        if self.enable_process_parsing:
            enabled.append('process')
        if self.enable_tag_parsing:
            enabled.append('tags')
        if self.enable_notes_parsing:
            enabled.append('notes')
        if self.enable_grind_parsing:
            enabled.append('grind')
        if self.enable_species_parsing:
            enabled.append('species')
        if self.enable_variety_parsing:
            enabled.append('variety')
        if self.enable_geographic_parsing:
            enabled.append('geographic')
        if self.enable_sensory_parsing:
            enabled.append('sensory')
        if self.enable_hash_generation:
            enabled.append('hash')
        if self.enable_text_cleaning:
            enabled.append('text_cleaning')
        if self.enable_text_normalization:
            enabled.append('text_normalization')
        
        return enabled
    
    def get_parser_config(self, parser_name: str) -> ParserConfig:
        """Get configuration for specific parser."""
        config_map = {
            'weight': self.weight_config,
            'roast': self.roast_config,
            'process': self.process_config,
            'tags': self.tag_config,
            'notes': self.notes_config,
            'grind': self.grind_config,
            'species': self.species_config,
            'variety': self.variety_config,
            'geographic': self.geographic_config,
            'sensory': self.sensory_config,
            'hash': self.hash_config,
            'text_cleaning': self.text_cleaning_config,
            'text_normalization': self.text_normalization_config
        }
        
        return config_map.get(parser_name, ParserConfig())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return self.model_dump()
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PipelineConfig':
        """Create PipelineConfig from dictionary."""
        return cls(**data)

