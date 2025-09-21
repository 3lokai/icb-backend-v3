"""
Pydantic v2 models for artifact validation based on canonical JSON schema.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any, Union, Literal
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict
from enum import Enum


class SourceEnum(str, Enum):
    """Source platform enumeration."""
    SHOPIFY = "shopify"
    WOOCOMMERCE = "woocommerce"
    FIRECRAWL = "firecrawl"
    MANUAL = "manual"
    OTHER = "other"


class PlatformEnum(str, Enum):
    """Product platform enumeration."""
    SHOPIFY = "shopify"
    WOOCOMMERCE = "woocommerce"
    OTHER = "other"


class WeightUnitEnum(str, Enum):
    """Weight unit enumeration."""
    GRAMS = "g"
    KILOGRAMS = "kg"
    OUNCES = "oz"


class RoastLevelEnum(str, Enum):
    """Roast level enumeration."""
    LIGHT = "light"
    LIGHT_MEDIUM = "light-medium"
    MEDIUM = "medium"
    MEDIUM_DARK = "medium-dark"
    DARK = "dark"
    UNKNOWN = "unknown"


class ProcessEnum(str, Enum):
    """Process method enumeration."""
    WASHED = "washed"
    NATURAL = "natural"
    HONEY = "honey"
    ANAEROBIC = "anaerobic"
    OTHER = "other"


class GrindEnum(str, Enum):
    """Grind type enumeration."""
    WHOLE = "whole"
    ESPRESSO = "espresso"
    FILTER = "filter"
    GROUND = "ground"
    UNKNOWN = "unknown"


class SpeciesEnum(str, Enum):
    """Coffee species enumeration."""
    ARABICA = "arabica"
    ROBUSTA = "robusta"
    LIBERICA = "liberica"
    BLEND = "blend"


class SensoryConfidenceEnum(str, Enum):
    """Sensory confidence enumeration."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class SensorySourceEnum(str, Enum):
    """Sensory source enumeration."""
    ROASTER = "roaster"
    ICB_INFERRED = "icb_inferred"
    ICB_MANUAL = "icb_manual"


class CollectorMetaModel(BaseModel):
    """Collector metadata model."""
    collector: Optional[str] = None
    collector_version: Optional[str] = None
    job_id: Optional[str] = None
    notes: Optional[str] = None

    model_config = ConfigDict(extra="allow")  # Allow additional properties


class ImageModel(BaseModel):
    """Product image model."""
    url: str = Field(..., description="Image URL")
    alt_text: Optional[str] = None
    order: Optional[int] = None
    source_id: Optional[str] = None

    model_config = ConfigDict(extra="allow")  # Allow additional properties


class VariantModel(BaseModel):
    """Product variant model."""
    platform_variant_id: str = Field(..., description="Platform variant ID")
    sku: Optional[str] = None
    title: Optional[str] = None
    price: str = Field(..., description="Price as string")
    price_decimal: Optional[float] = None
    currency: Optional[str] = None
    compare_at_price: Optional[str] = None
    compare_at_price_decimal: Optional[float] = None
    in_stock: Optional[bool] = None
    grams: Optional[int] = None
    weight_unit: Optional[WeightUnitEnum] = None
    options: Optional[List[str]] = None
    raw_variant_json: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(extra="allow")  # Allow additional properties


class ProductModel(BaseModel):
    """Product model."""
    platform_product_id: str = Field(..., description="Platform product ID")
    platform: Optional[PlatformEnum] = None
    title: str = Field(..., description="Product title")
    handle: Optional[str] = None
    slug: Optional[str] = None
    description_html: Optional[str] = None
    description_md: Optional[str] = None
    source_url: str = Field(..., description="Source URL")
    product_type: Optional[str] = None
    tags: Optional[List[str]] = None
    images: Optional[List[ImageModel]] = None
    variants: List[VariantModel] = Field(..., min_length=1, description="Product variants")
    raw_meta: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(extra="allow")  # Allow additional properties


class SensoryParamsModel(BaseModel):
    """Sensory parameters model."""
    acidity: Optional[float] = Field(None, ge=0, le=10)
    sweetness: Optional[float] = Field(None, ge=0, le=10)
    bitterness: Optional[float] = Field(None, ge=0, le=10)
    body: Optional[float] = Field(None, ge=0, le=10)
    clarity: Optional[float] = Field(None, ge=0, le=10)
    aftertaste: Optional[float] = Field(None, ge=0, le=10)
    confidence: Optional[SensoryConfidenceEnum] = None
    source: Optional[SensorySourceEnum] = None

    model_config = ConfigDict(extra="allow")  # Allow additional properties


class NormalizationModel(BaseModel):
    """Normalization data model."""
    is_coffee: Optional[bool] = None
    content_hash: Optional[str] = None
    raw_payload_hash: Optional[str] = None
    parsing_warnings: Optional[List[str]] = None
    name_clean: Optional[str] = None
    description_md_clean: Optional[str] = None
    tags_normalized: Optional[List[str]] = None
    notes_raw: Optional[List[str]] = None
    roast_level_raw: Optional[str] = None
    roast_level_enum: Optional[RoastLevelEnum] = None
    process_raw: Optional[str] = None
    process_enum: Optional[ProcessEnum] = None
    varieties: Optional[List[str]] = None
    region: Optional[str] = None
    country: Optional[str] = None
    altitude_m: Optional[int] = None
    default_pack_weight_g: Optional[int] = None
    default_grind: Optional[GrindEnum] = None
    bean_species: Optional[SpeciesEnum] = None
    sensory_params: Optional[SensoryParamsModel] = None
    llm_enrichment: Optional[Dict[str, Any]] = None
    llm_confidence: Optional[float] = None
    roast_inferred: Optional[bool] = None

    model_config = ConfigDict(extra="allow")  # Allow additional properties


class CollectorSignalsModel(BaseModel):
    """Collector signals model."""
    response_status: Optional[int] = None
    response_headers: Optional[Dict[str, Any]] = None
    download_time_ms: Optional[int] = None
    size_bytes: Optional[int] = None

    model_config = ConfigDict(extra="allow")  # Allow additional properties


class AuditModel(BaseModel):
    """Audit information model."""
    artifact_id: Optional[str] = None
    created_at: Optional[datetime] = None
    collected_by: Optional[str] = None

    model_config = ConfigDict(extra="allow")  # Allow additional properties


class ArtifactModel(BaseModel):
    """Main artifact model for validation."""
    source: SourceEnum = Field(..., description="Source platform")
    roaster_domain: str = Field(..., description="Roaster domain")
    scraped_at: datetime = Field(..., description="Scraping timestamp")
    collector_meta: Optional[CollectorMetaModel] = None
    product: ProductModel = Field(..., description="Product data")
    normalization: Optional[NormalizationModel] = None
    collector_signals: Optional[CollectorSignalsModel] = None
    audit: Optional[AuditModel] = None

    model_config = ConfigDict(
        extra="forbid"  # Strict validation - no additional properties
    )

    @field_validator('roaster_domain')
    @classmethod
    def validate_roaster_domain(cls, v):
        """Validate roaster domain format."""
        if not v or not isinstance(v, str):
            raise ValueError('roaster_domain must be a non-empty string')
        # Basic hostname validation
        if '.' not in v:
            raise ValueError('roaster_domain must be a valid hostname')
        return v

    @field_validator('scraped_at', mode='before')
    @classmethod
    def validate_scraped_at(cls, v):
        """Validate and parse scraped_at timestamp."""
        if isinstance(v, str):
            try:
                return datetime.fromisoformat(v.replace('Z', '+00:00'))
            except ValueError:
                raise ValueError('scraped_at must be a valid ISO 8601 timestamp')
        return v

    @model_validator(mode='after')
    def validate_required_fields(self):
        """Validate required fields are present."""
        if not self.source:
            raise ValueError('source is required')
        if not self.roaster_domain:
            raise ValueError('roaster_domain is required')
        if not self.scraped_at:
            raise ValueError('scraped_at is required')
        if not self.product:
            raise ValueError('product is required')
        return self
