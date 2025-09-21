"""
Roaster configuration schema and validation.

This module provides:
- Pydantic models for roaster configuration
- Configuration validation and defaults
- Schema migration utilities
- Configuration testing utilities
"""

from datetime import datetime
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field, field_validator, model_validator, AliasChoices
import structlog

logger = structlog.get_logger(__name__)


class RoasterConfigSchema(BaseModel):
    """Pydantic model for roaster configuration validation."""
    
    # Core identification
    id: str = Field(..., description="Unique roaster identifier")
    name: str = Field(..., description="Human-readable roaster name")
    active: bool = Field(default=True, description="Whether roaster is active")
    
    # Scheduling configuration
    full_cadence: str = Field(
        default="0 3 1 * *", 
        description="Cron expression for full refresh",
        alias=AliasChoices('full_cadence', 'cadence')
    )
    price_cadence: str = Field(default="0 4 * * 0", description="Cron expression for price updates")
    
    # Concurrency and performance
    default_concurrency: int = Field(
        default=3, 
        ge=1, 
        le=10, 
        description="Default worker concurrency",
        alias=AliasChoices('default_concurrency', 'concurrency')
    )
    
    # External service configuration
    use_firecrawl_fallback: bool = Field(default=False, description="Enable Firecrawl fallback")
    firecrawl_budget_limit: int = Field(default=1000, ge=0, description="Firecrawl budget limit")
    use_llm: bool = Field(default=False, description="Enable LLM enrichment")
    
    # Monitoring and alerting
    alert_price_delta_pct: float = Field(default=20.0, ge=0, le=100, description="Price spike threshold")
    
    # Caching and optimization
    last_etag: Optional[str] = Field(default=None, description="Last ETag for 304 handling")
    last_modified: Optional[datetime] = Field(default=None, description="Last-Modified timestamp")
    
    # API configuration
    base_url: Optional[str] = Field(default=None, description="Base URL for roaster API")
    api_endpoints: Dict[str, str] = Field(default_factory=dict, description="API endpoint mappings")
    
    # Additional metadata
    created_at: Optional[datetime] = Field(default=None, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(default=None, description="Last update timestamp")
    
    @field_validator('full_cadence', 'price_cadence')
    @classmethod
    def validate_cron_expression(cls, v):
        """Validate cron expressions."""
        if not v:
            return v
        
        # Basic cron validation (5 fields)
        parts = v.split()
        if len(parts) != 5:
            raise ValueError(f"Invalid cron expression: {v}. Must have 5 fields.")
        
        # Validate each field
        valid_fields = [
            (0, 59),    # minute
            (0, 23),    # hour
            (1, 31),    # day
            (1, 12),    # month
            (0, 6),     # day of week
        ]
        
        for i, (min_val, max_val) in enumerate(valid_fields):
            field = parts[i]
            if field != '*':
                try:
                    value = int(field)
                    if not (min_val <= value <= max_val):
                        raise ValueError(f"Field {i} out of range: {value}")
                except ValueError:
                    raise ValueError(f"Invalid field {i}: {field}")
        
        return v
    
    @field_validator('base_url')
    @classmethod
    def validate_base_url(cls, v):
        """Validate base URL format."""
        if v and not v.startswith(('http://', 'https://')):
            raise ValueError("Base URL must start with http:// or https://")
        return v
    
    @field_validator('api_endpoints')
    @classmethod
    def validate_api_endpoints(cls, v):
        """Validate API endpoints."""
        if not v:
            return v
        
        for endpoint_name, endpoint_url in v.items():
            if not endpoint_name:
                raise ValueError("Endpoint name cannot be empty")
            if not endpoint_url.startswith('/'):
                raise ValueError(f"Endpoint URL must start with '/': {endpoint_url}")
        
        return v
    
    @model_validator(mode='after')
    def validate_configuration(self):
        """Validate overall configuration."""
        # Check that at least one cadence is set
        if not self.full_cadence and not self.price_cadence:
            raise ValueError("At least one cadence must be configured")
        
        # Check that base_url is set if api_endpoints are configured
        if self.api_endpoints and not self.base_url:
            raise ValueError("base_url must be set when api_endpoints are configured")
        
        return self
    
    model_config = {
        "json_encoders": {
            datetime: lambda v: v.isoformat()
        }
    }


class RoasterConfigValidator:
    """Validates roaster configuration against schema."""
    
    @staticmethod
    def validate_config(config: Dict[str, Any]) -> RoasterConfigSchema:
        """Validate configuration against schema."""
        try:
            return RoasterConfigSchema(**config)
        except Exception as e:
            logger.error("Configuration validation failed", 
                        config=config, 
                        error=str(e))
            raise ValueError(f"Invalid roaster configuration: {e}")
    
    @staticmethod
    def validate_batch_configs(configs: List[Dict[str, Any]]) -> List[RoasterConfigSchema]:
        """Validate a batch of configurations."""
        validated_configs = []
        errors = []
        
        for i, config in enumerate(configs):
            try:
                validated = RoasterConfigValidator.validate_config(config)
                validated_configs.append(validated)
            except Exception as e:
                errors.append(f"Config {i}: {e}")
        
        if errors:
            raise ValueError(f"Batch validation failed: {'; '.join(errors)}")
        
        return validated_configs


class RoasterConfigDefaults:
    """Default configuration values for roasters."""
    
    @staticmethod
    def get_default_config() -> Dict[str, Any]:
        """Get default configuration."""
        return {
            'active': True,
            'full_cadence': '0 3 1 * *',  # Monthly at 3 AM
            'price_cadence': '0 4 * * 0',  # Weekly on Sunday at 4 AM
            'default_concurrency': 3,
            'use_firecrawl_fallback': False,
            'firecrawl_budget_limit': 1000,
            'use_llm': False,
            'alert_price_delta_pct': 20.0,
            'api_endpoints': {}
        }
    
    @staticmethod
    def get_high_volume_config() -> Dict[str, Any]:
        """Get configuration for high-volume roasters."""
        return {
            'active': True,
            'full_cadence': '0 2 1 * *',  # Earlier in the month
            'price_cadence': '0 3 * * 0',  # Earlier on Sunday
            'default_concurrency': 5,  # Higher concurrency
            'use_firecrawl_fallback': True,
            'firecrawl_budget_limit': 2000,
            'use_llm': True,
            'alert_price_delta_pct': 15.0,  # Lower threshold
            'api_endpoints': {}
        }
    
    @staticmethod
    def get_low_volume_config() -> Dict[str, Any]:
        """Get configuration for low-volume roasters."""
        return {
            'active': True,
            'full_cadence': '0 4 1 * *',  # Later in the month
            'price_cadence': '0 5 * * 0',  # Later on Sunday
            'default_concurrency': 1,  # Lower concurrency
            'use_firecrawl_fallback': False,
            'firecrawl_budget_limit': 500,
            'use_llm': False,
            'alert_price_delta_pct': 30.0,  # Higher threshold
            'api_endpoints': {}
        }


