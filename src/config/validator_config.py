"""
Configuration for artifact validator.
"""

from typing import Dict, Any, Optional
from pathlib import Path
from pydantic import BaseModel, Field, field_validator
from .imagekit_config import ImageKitConfig
from .tag_config import TagConfig
from .notes_config import NotesConfig
from .species_config import SpeciesConfig
from .variety_config import VarietyConfig
from .geographic_config import GeographicConfig
from .sensory_config import SensoryConfig
from .hash_config import HashConfig
from .text_cleaning_config import TextCleaningConfig
from .text_normalization_config import TextNormalizationConfig


class ValidatorConfig(BaseModel):
    """Configuration for artifact validator."""
    
    storage_path: str = Field(default="data/fetcher", description="Path to A.2 storage directory")
    invalid_artifacts_path: str = Field(default="data/validator/invalid_artifacts", description="Path for storing invalid artifacts")
    enable_strict_validation: bool = Field(default=True, description="Enable strict Pydantic validation")
    enable_error_persistence: bool = Field(default=True, description="Enable persistence of invalid artifacts")
    max_validation_errors: int = Field(default=100, ge=1, description="Maximum validation errors to track")
    validation_timeout_seconds: int = Field(default=30, ge=1, description="Timeout for validation operations")
    # Image processing configuration
    enable_image_deduplication: bool = Field(default=True, description="Enable image deduplication (F.1)")
    enable_imagekit_upload: bool = Field(default=True, description="Enable ImageKit upload (F.2)")
    imagekit_config: Optional[ImageKitConfig] = Field(default=None, description="ImageKit configuration for CDN upload")
    # Weight parser configuration
    enable_weight_parsing: bool = Field(default=True, description="Enable weight parsing")
    weight_confidence_threshold: float = Field(default=0.8, ge=0.0, le=1.0, description="Minimum confidence for weight parsing")
    weight_fallback_unit: str = Field(default="g", description="Fallback unit for ambiguous weights")
    # Roast parser configuration
    enable_roast_parsing: bool = Field(default=True, description="Enable roast level parsing")
    roast_confidence_threshold: float = Field(default=0.7, ge=0.0, le=1.0, description="Minimum confidence for roast parsing")
    # Process parser configuration
    enable_process_parsing: bool = Field(default=True, description="Enable process method parsing")
    process_confidence_threshold: float = Field(default=0.7, ge=0.0, le=1.0, description="Minimum confidence for process parsing")
    # Grind/brewing parser configuration
    enable_grind_brewing_parsing: bool = Field(default=True, description="Enable grind/brewing method parsing")
    grind_brewing_confidence_threshold: float = Field(default=0.7, ge=0.0, le=1.0, description="Minimum confidence for grind/brewing parsing")
    # Tag normalization configuration
    enable_tag_normalization: bool = Field(default=True, description="Enable tag normalization")
    tag_config: Optional[TagConfig] = Field(default=None, description="Tag normalization configuration")
    # Notes extraction configuration
    enable_notes_extraction: bool = Field(default=True, description="Enable notes extraction")
    notes_config: Optional[NotesConfig] = Field(default=None, description="Notes extraction configuration")
    # Species parser configuration
    enable_species_parsing: bool = Field(default=True, description="Enable species parsing")
    species_config: Optional[SpeciesConfig] = Field(default=None, description="Species parser configuration")
    # Variety extraction configuration
    enable_variety_parsing: bool = Field(default=True, description="Enable variety extraction")
    variety_config: Optional[VarietyConfig] = Field(default=None, description="Variety extraction configuration")
    # Geographic parser configuration
    enable_geographic_parsing: bool = Field(default=True, description="Enable geographic parsing")
    geographic_config: Optional[GeographicConfig] = Field(default=None, description="Geographic parser configuration")
    # Sensory parser configuration
    enable_sensory_parsing: bool = Field(default=True, description="Enable sensory parameter parsing")
    sensory_config: Optional[SensoryConfig] = Field(default=None, description="Sensory parser configuration")
    # Hash generation configuration
    enable_hash_generation: bool = Field(default=True, description="Enable content hash generation")
    hash_config: Optional[HashConfig] = Field(default=None, description="Hash generation configuration")
    # Text cleaning configuration
    enable_text_cleaning: bool = Field(default=True, description="Enable text cleaning for names and descriptions")
    text_cleaning_config: Optional[TextCleaningConfig] = Field(default=None, description="Text cleaning configuration")
    # Text normalization configuration
    enable_text_normalization: bool = Field(default=True, description="Enable text normalization for names and descriptions")
    text_normalization_config: Optional[TextNormalizationConfig] = Field(default=None, description="Text normalization configuration")
    
    # C.8 Normalizer Pipeline configuration
    enable_normalizer_pipeline: bool = Field(default=True, description="Enable C.8 normalizer pipeline orchestration")
    enable_llm_fallback: bool = Field(default=True, description="Enable LLM fallback for ambiguous cases using Epic D services")
    pipeline_confidence_threshold: float = Field(default=0.7, ge=0.0, le=1.0, description="Confidence threshold for pipeline processing")
    enable_pipeline_metrics: bool = Field(default=True, description="Enable pipeline metrics and monitoring")
    
    # Coffee Classification configuration (A.7)
    enable_coffee_classification: bool = Field(default=True, description="Enable coffee classification parser")
    classification_confidence_threshold: float = Field(default=0.7, ge=0.0, le=1.0, description="Confidence threshold for code-based classification")
    classification_llm_threshold: float = Field(default=0.6, ge=0.0, le=1.0, description="Confidence threshold for LLM fallback")
    classification_skip_threshold: float = Field(default=0.3, ge=0.0, le=1.0, description="Confidence threshold below which to skip to equipment")
    enable_classification_metrics: bool = Field(default=True, description="Enable classification metrics and monitoring")
    
    @field_validator('storage_path', 'invalid_artifacts_path')
    @classmethod
    def validate_paths(cls, v):
        """Validate and create paths if they don't exist."""
        path = Path(v)
        path.mkdir(parents=True, exist_ok=True)
        return str(path)
    
    def __init__(self, **data):
        """Initialize validator configuration with Pydantic validation."""
        super().__init__(**data)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return self.model_dump()
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'ValidatorConfig':
        """Create configuration from dictionary."""
        return cls.model_validate(config_dict)
    
    def validate_config(self) -> bool:
        """
        Validate configuration settings.
        
        Returns:
            True if configuration is valid
        """
        try:
            # Pydantic validation is handled automatically, but we can add additional checks
            storage_path = Path(self.storage_path)
            invalid_artifacts_path = Path(self.invalid_artifacts_path)
            
            # Ensure paths exist
            storage_path.mkdir(parents=True, exist_ok=True)
            invalid_artifacts_path.mkdir(parents=True, exist_ok=True)
            
            return True
            
        except Exception:
            return False
