"""
Firecrawl configuration and validation.

This module provides:
- Pydantic models for Firecrawl configuration
- Configuration validation and defaults
- API key management
- Rate limiting and budget tracking
"""

from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field, field_validator
import structlog

logger = structlog.get_logger(__name__)


class FirecrawlConfig(BaseModel):
    """Pydantic model for Firecrawl configuration validation."""
    
    # API Configuration
    api_key: str = Field(..., description="Firecrawl API key")
    base_url: str = Field(
        default="https://api.firecrawl.dev", 
        description="Firecrawl API base URL"
    )
    
    # Rate limiting and budget
    budget_limit: int = Field(
        default=1000, 
        ge=0, 
        description="Maximum budget for Firecrawl operations"
    )
    rate_limit_per_minute: int = Field(
        default=60, 
        ge=1, 
        description="Rate limit per minute"
    )
    
    # Map operation configuration
    max_pages: int = Field(
        default=50, 
        ge=1, 
        le=1000, 
        description="Maximum pages to map"
    )
    include_subdomains: bool = Field(
        default=False, 
        description="Include subdomains in mapping"
    )
    sitemap_only: bool = Field(
        default=False, 
        description="Use sitemap only for mapping"
    )
    
    # Search and filtering
    search_terms: List[str] = Field(
        default_factory=list, 
        description="Search terms for filtering URLs"
    )
    coffee_keywords: List[str] = Field(
        default_factory=lambda: [
            # Basic coffee terms
            "coffee", "bean", "roast", "brew", "espresso",
            "latte", "cappuccino", "mocha", "americano",
            
            # Species (from species_enum)
            "arabica", "robusta", "liberica", "blend",
            "chicory", "filter coffee mix",
            
            # Roast levels (from roast_level_enum)
            "light roast", "light medium", "medium roast", 
            "medium dark", "dark roast",
            
            # Processing methods (from process_enum)
            "washed", "natural", "honey", "pulped natural",
            "monsooned", "wet hulled", "anaerobic", 
            "carbonic maceration", "double fermented", "experimental",
            
            # Grind types (from grind_enum)
            "whole bean", "filter grind", "espresso grind", "omni",
            "turkish", "moka", "cold brew", "aeropress", "channi",
            "french press", "pour over", "syphon", "south indian filter",
            
            # Specialty coffee terms
            "specialty", "speciality", "single origin", "micro lot",
            "green coffee", "estate", "plantation", "organic",
            
            # Regional terms
            "coorg", "karnataka", "indian coffee", "ethiopian",
            "colombian", "brazilian", "guatemalan", "kenyan",
            
            # Product categories
            "ground coffee", "coffee powder", "instant coffee",
            "cold brew", "pour over", "french press", "aeropress",
            "moka pot", "turkish coffee", "filter coffee",
            
            # Status terms (from coffee_status_enum)
            "active", "seasonal", "discontinued", "coming soon",
            
            # Additional coffee terminology
            "cupping", "tasting notes", "flavor profile", "aroma",
            "acidity", "body", "finish", "aftertaste", "balance"
        ],
        description="Comprehensive coffee-related keywords for filtering"
    )
    
    # Timeout and retry configuration
    timeout: float = Field(
        default=30.0, 
        ge=5.0, 
        le=300.0, 
        description="Request timeout in seconds"
    )
    max_retries: int = Field(
        default=3, 
        ge=0, 
        le=10, 
        description="Maximum retry attempts"
    )
    retry_delay: float = Field(
        default=1.0, 
        ge=0.1, 
        le=60.0, 
        description="Delay between retries in seconds"
    )
    
    # Monitoring and logging
    enable_monitoring: bool = Field(
        default=True, 
        description="Enable monitoring and metrics"
    )
    log_level: str = Field(
        default="INFO", 
        description="Logging level"
    )
    
    @field_validator('api_key')
    @classmethod
    def validate_api_key(cls, v):
        """Validate API key format."""
        if not v or len(v.strip()) == 0:
            raise ValueError("API key cannot be empty")
        if len(v) < 10:
            raise ValueError("API key appears to be too short")
        return v.strip()
    
    @field_validator('base_url')
    @classmethod
    def validate_base_url(cls, v):
        """Validate base URL format."""
        if not v.startswith(('http://', 'https://')):
            raise ValueError("Base URL must start with http:// or https://")
        return v.rstrip('/')
    
    @field_validator('search_terms', 'coffee_keywords')
    @classmethod
    def validate_keywords(cls, v):
        """Validate keyword lists."""
        if not isinstance(v, list):
            raise ValueError("Keywords must be a list")
        
        # Filter out empty strings and normalize
        filtered = [term.strip().lower() for term in v if term.strip()]
        
        if len(filtered) != len(set(filtered)):
            raise ValueError("Keywords must be unique")
        
        return filtered
    
    @field_validator('log_level')
    @classmethod
    def validate_log_level(cls, v):
        """Validate log level."""
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of: {valid_levels}")
        return v.upper()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return self.model_dump()
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FirecrawlConfig':
        """Create configuration from dictionary."""
        return cls(**data)


class FirecrawlBudgetTracker:
    """Track Firecrawl budget usage and limits."""
    
    def __init__(self, config: FirecrawlConfig):
        self.config = config
        self.current_usage = 0
        self.operations_count = 0
        
    def can_operate(self) -> bool:
        """Check if budget allows for more operations."""
        return self.current_usage < self.config.budget_limit
    
    def record_operation(self, cost: int = 1) -> bool:
        """Record an operation and its cost."""
        if not self.can_operate():
            logger.warning(
                "Budget limit reached",
                current_usage=self.current_usage,
                budget_limit=self.config.budget_limit
            )
            return False
        
        self.current_usage += cost
        self.operations_count += 1
        
        logger.info(
            "Operation recorded",
            cost=cost,
            current_usage=self.current_usage,
            budget_limit=self.config.budget_limit,
            operations_count=self.operations_count
        )
        
        return True
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """Get current usage statistics."""
        return {
            'current_usage': self.current_usage,
            'budget_limit': self.config.budget_limit,
            'remaining_budget': self.config.budget_limit - self.current_usage,
            'operations_count': self.operations_count,
            'usage_percentage': (self.current_usage / self.config.budget_limit) * 100
        }
    
    def reset(self):
        """Reset usage tracking."""
        self.current_usage = 0
        self.operations_count = 0
        logger.info("Budget tracker reset")


class FirecrawlConfigDefaults:
    """Default configuration values for Firecrawl."""
    
    @staticmethod
    def get_default_config() -> Dict[str, Any]:
        """Get default configuration."""
        return {
            'api_key': '',  # Must be set via environment
            'base_url': 'https://api.firecrawl.dev',
            'budget_limit': 1000,
            'rate_limit_per_minute': 60,
            'max_pages': 50,
            'include_subdomains': False,
            'sitemap_only': False,
            'search_terms': [],
            'coffee_keywords': [
                # Basic coffee terms
                'coffee', 'bean', 'roast', 'brew', 'espresso',
                'latte', 'cappuccino', 'mocha', 'americano',
                
                # Species (from species_enum)
                'arabica', 'robusta', 'liberica', 'blend',
                'chicory', 'filter coffee mix',
                
                # Roast levels (from roast_level_enum)
                'light roast', 'light medium', 'medium roast', 
                'medium dark', 'dark roast',
                
                # Processing methods (from process_enum)
                'washed', 'natural', 'honey', 'pulped natural',
                'monsooned', 'wet hulled', 'anaerobic', 
                'carbonic maceration', 'double fermented', 'experimental',
                
                # Grind types (from grind_enum)
                'whole bean', 'filter grind', 'espresso grind', 'omni',
                'turkish', 'moka', 'cold brew', 'aeropress', 'channi',
                'french press', 'pour over', 'syphon', 'south indian filter',
                
                # Specialty coffee terms
                'specialty', 'speciality', 'single origin', 'micro lot',
                'green coffee', 'estate', 'plantation', 'organic',
                
                # Regional terms
                'coorg', 'karnataka', 'indian coffee', 'ethiopian',
                'colombian', 'brazilian', 'guatemalan', 'kenyan',
                
                # Product categories
                'ground coffee', 'coffee powder', 'instant coffee',
                'cold brew', 'pour over', 'french press', 'aeropress',
                'moka pot', 'turkish coffee', 'filter coffee',
                
                # Status terms (from coffee_status_enum)
                'active', 'seasonal', 'discontinued', 'coming soon',
                
                # Additional coffee terminology
                'cupping', 'tasting notes', 'flavor profile', 'aroma',
                'acidity', 'body', 'finish', 'aftertaste', 'balance'
            ],
            'timeout': 30.0,
            'max_retries': 3,
            'retry_delay': 1.0,
            'enable_monitoring': True,
            'log_level': 'INFO'
        }
    
    @staticmethod
    def get_high_volume_config() -> Dict[str, Any]:
        """Get configuration for high-volume operations."""
        return {
            'api_key': '',  # Must be set via environment
            'base_url': 'https://api.firecrawl.dev',
            'budget_limit': 5000,
            'rate_limit_per_minute': 120,
            'max_pages': 200,
            'include_subdomains': True,
            'sitemap_only': False,
            'search_terms': [],
            'coffee_keywords': [
                # Basic coffee terms
                'coffee', 'bean', 'roast', 'brew', 'espresso',
                'latte', 'cappuccino', 'mocha', 'americano',
                
                # Species (from species_enum)
                'arabica', 'robusta', 'liberica', 'blend',
                'chicory', 'filter coffee mix',
                
                # Roast levels (from roast_level_enum)
                'light roast', 'light medium', 'medium roast', 
                'medium dark', 'dark roast',
                
                # Processing methods (from process_enum)
                'washed', 'natural', 'honey', 'pulped natural',
                'monsooned', 'wet hulled', 'anaerobic', 
                'carbonic maceration', 'double fermented', 'experimental',
                
                # Grind types (from grind_enum)
                'whole bean', 'filter grind', 'espresso grind', 'omni',
                'turkish', 'moka', 'cold brew', 'aeropress', 'channi',
                'french press', 'pour over', 'syphon', 'south indian filter',
                
                # Specialty coffee terms
                'specialty', 'speciality', 'single origin', 'micro lot',
                'green coffee', 'estate', 'plantation', 'organic',
                
                # Regional terms
                'coorg', 'karnataka', 'indian coffee', 'ethiopian',
                'colombian', 'brazilian', 'guatemalan', 'kenyan',
                
                # Product categories
                'ground coffee', 'coffee powder', 'instant coffee',
                'cold brew', 'pour over', 'french press', 'aeropress',
                'moka pot', 'turkish coffee', 'filter coffee',
                
                # Status terms (from coffee_status_enum)
                'active', 'seasonal', 'discontinued', 'coming soon',
                
                # Additional coffee terminology
                'cupping', 'tasting notes', 'flavor profile', 'aroma',
                'acidity', 'body', 'finish', 'aftertaste', 'balance'
            ],
            'timeout': 60.0,
            'max_retries': 5,
            'retry_delay': 2.0,
            'enable_monitoring': True,
            'log_level': 'INFO'
        }
    
    @staticmethod
    def get_conservative_config() -> Dict[str, Any]:
        """Get configuration for conservative usage."""
        return {
            'api_key': '',  # Must be set via environment
            'base_url': 'https://api.firecrawl.dev',
            'budget_limit': 100,
            'rate_limit_per_minute': 30,
            'max_pages': 10,
            'include_subdomains': False,
            'sitemap_only': True,
            'search_terms': [],
            'coffee_keywords': [
                # Basic coffee terms (conservative set)
                'coffee', 'bean', 'roast', 'brew', 'espresso',
                'latte', 'cappuccino', 'mocha', 'americano',
                
                # Essential specialty terms
                'specialty', 'single origin', 'organic',
                
                # Key regional terms
                'indian coffee', 'coorg', 'karnataka',
                
                # Basic product categories
                'ground coffee', 'filter coffee'
            ],
            'timeout': 15.0,
            'max_retries': 2,
            'retry_delay': 0.5,
            'enable_monitoring': True,
            'log_level': 'WARNING'
        }


class FirecrawlConfigValidator:
    """Validates Firecrawl configuration against schema."""
    
    @staticmethod
    def validate_config(config: Dict[str, Any]) -> FirecrawlConfig:
        """Validate configuration against schema."""
        try:
            return FirecrawlConfig(**config)
        except Exception as e:
            logger.error(
                "Firecrawl configuration validation failed",
                config=config,
                error=str(e)
            )
            raise ValueError(f"Invalid Firecrawl configuration: {e}")
    
    @staticmethod
    def validate_batch_configs(configs: List[Dict[str, Any]]) -> List[FirecrawlConfig]:
        """Validate a batch of configurations."""
        validated_configs = []
        errors = []
        
        for i, config in enumerate(configs):
            try:
                validated = FirecrawlConfigValidator.validate_config(config)
                validated_configs.append(validated)
            except Exception as e:
                errors.append(f"Config {i}: {e}")
        
        if errors:
            raise ValueError(f"Batch validation failed: {'; '.join(errors)}")
        
        return validated_configs
