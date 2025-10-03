"""
Tests for roaster configuration functionality.

This module tests:
- Configuration schema validation
- Default value handling
- Migration utilities
- Error handling and edge cases
"""

import pytest
from datetime import datetime, timezone
from pydantic import ValidationError

from src.config.roaster_schema import (
    RoasterConfigSchema,
    RoasterConfigValidator,
    RoasterConfigDefaults
)


class TestRoasterConfigSchema:
    """Test roaster configuration schema validation."""
    
    def test_valid_config(self):
        """Test valid configuration."""
        config = {
            'id': 'test_roaster',
            'name': 'Test Roaster',
            'full_cadence': '0 3 1 * *',
            'price_cadence': '0 4 * * 0',
            'default_concurrency': 3,
            'use_firecrawl_fallback': False,
            'firecrawl_budget_limit': 1000,
            'use_llm': False,
            'alert_price_delta_pct': 20.0
        }
        
        schema = RoasterConfigSchema(**config)
        assert schema.id == 'test_roaster'
        assert schema.name == 'Test Roaster'
        assert schema.default_concurrency == 3
    
    def test_default_values(self):
        """Test default value assignment."""
        config = {
            'id': 'test_roaster',
            'name': 'Test Roaster'
        }
        
        schema = RoasterConfigSchema(**config)
        assert schema.active is True
        assert schema.full_cadence == '0 3 1 * *'
        assert schema.price_cadence == '0 4 * * 0'
        assert schema.default_concurrency == 3
        assert schema.use_firecrawl_fallback is False
        assert schema.use_llm is False
        assert schema.alert_price_delta_pct == 20.0
    
    def test_invalid_cron_expression(self):
        """Test invalid cron expression validation."""
        config = {
            'id': 'test_roaster',
            'name': 'Test Roaster',
            'full_cadence': 'invalid cron'
        }
        
        with pytest.raises(ValidationError) as exc_info:
            RoasterConfigSchema(**config)
        
        assert 'Invalid cron expression' in str(exc_info.value)
    
    def test_invalid_concurrency(self):
        """Test invalid concurrency values."""
        config = {
            'id': 'test_roaster',
            'name': 'Test Roaster',
            'default_concurrency': 15  # Too high
        }
        
        with pytest.raises(ValidationError):
            RoasterConfigSchema(**config)
        
        config['default_concurrency'] = 0  # Too low
        
        with pytest.raises(ValidationError):
            RoasterConfigSchema(**config)
    
    def test_invalid_base_url(self):
        """Test invalid base URL validation."""
        config = {
            'id': 'test_roaster',
            'name': 'Test Roaster',
            'base_url': 'invalid-url'
        }
        
        with pytest.raises(ValidationError) as exc_info:
            RoasterConfigSchema(**config)
        
        assert 'must start with http:// or https://' in str(exc_info.value)
    
    def test_invalid_api_endpoints(self):
        """Test invalid API endpoints validation."""
        config = {
            'id': 'test_roaster',
            'name': 'Test Roaster',
            'base_url': 'https://example.com',
            'api_endpoints': {
                'products': 'invalid-endpoint'  # Should start with /
            }
        }
        
        with pytest.raises(ValidationError) as exc_info:
            RoasterConfigSchema(**config)
        
        assert 'must start with' in str(exc_info.value)
    
    def test_missing_base_url_with_endpoints(self):
        """Test validation when endpoints are configured without base URL."""
        config = {
            'id': 'test_roaster',
            'name': 'Test Roaster',
            'api_endpoints': {
                'products': '/products.json'
            }
        }
        
        with pytest.raises(ValidationError) as exc_info:
            RoasterConfigSchema(**config)
        
        assert 'base_url must be set' in str(exc_info.value)
    
    def test_valid_complex_config(self):
        """Test complex valid configuration."""
        config = {
            'id': 'complex_roaster',
            'name': 'Complex Roaster',
            'active': True,
            'full_cadence': '0 2 1 * *',
            'price_cadence': '0 3 * * 0',
            'default_concurrency': 5,
            'use_firecrawl_fallback': True,
            'firecrawl_budget_limit': 2000,
            'use_llm': True,
            'alert_price_delta_pct': 15.0,
            'base_url': 'https://api.example.com',
            'api_endpoints': {
                'products': '/products.json',
                'collections': '/collections.json',
                'pages': '/pages.json'
            },
            'last_etag': 'abc123',
            'last_modified': datetime.now(timezone.utc)
        }
        
        schema = RoasterConfigSchema(**config)
        assert schema.id == 'complex_roaster'
        assert schema.use_firecrawl_fallback is True
        assert schema.use_llm is True
        assert len(schema.api_endpoints) == 3


class TestRoasterConfigValidator:
    """Test configuration validator."""
    
    def test_validate_config(self):
        """Test configuration validation."""
        config = {
            'id': 'test_roaster',
            'name': 'Test Roaster',
            'default_concurrency': 3
        }
        
        validated = RoasterConfigValidator.validate_config(config)
        assert isinstance(validated, RoasterConfigSchema)
        assert validated.id == 'test_roaster'
    
    def test_validate_invalid_config(self):
        """Test validation of invalid configuration."""
        config = {
            'id': 'test_roaster',
            'name': 'Test Roaster',
            'default_concurrency': -1  # Invalid
        }
        
        with pytest.raises(ValueError) as exc_info:
            RoasterConfigValidator.validate_config(config)
        
        assert 'Invalid roaster configuration' in str(exc_info.value)
    
    def test_validate_batch_configs(self):
        """Test batch configuration validation."""
        configs = [
            {
                'id': 'roaster_1',
                'name': 'Roaster 1',
                'default_concurrency': 3
            },
            {
                'id': 'roaster_2',
                'name': 'Roaster 2',
                'default_concurrency': 5
            }
        ]
        
        validated = RoasterConfigValidator.validate_batch_configs(configs)
        assert len(validated) == 2
        assert all(isinstance(config, RoasterConfigSchema) for config in validated)
    
    def test_validate_batch_with_errors(self):
        """Test batch validation with errors."""
        configs = [
            {
                'id': 'roaster_1',
                'name': 'Roaster 1',
                'default_concurrency': 3
            },
            {
                'id': 'roaster_2',
                'name': 'Roaster 2',
                'default_concurrency': -1  # Invalid
            }
        ]
        
        with pytest.raises(ValueError) as exc_info:
            RoasterConfigValidator.validate_batch_configs(configs)
        
        assert 'Batch validation failed' in str(exc_info.value)


class TestRoasterConfigDefaults:
    """Test default configuration values."""
    
    def test_get_default_config(self):
        """Test default configuration."""
        config = RoasterConfigDefaults.get_default_config()
        
        assert config['active'] is True
        assert config['full_cadence'] == '0 3 1 * *'
        assert config['price_cadence'] == '0 4 * * 0'
        assert config['default_concurrency'] == 3
        assert config['use_firecrawl_fallback'] is False
        assert config['use_llm'] is False
        assert config['alert_price_delta_pct'] == 20.0
    
    def test_get_high_volume_config(self):
        """Test high-volume configuration."""
        config = RoasterConfigDefaults.get_high_volume_config()
        
        assert config['default_concurrency'] == 5
        assert config['use_firecrawl_fallback'] is True
        assert config['firecrawl_budget_limit'] == 10
        assert config['use_llm'] is True
        assert config['alert_price_delta_pct'] == 15.0
    
    def test_get_low_volume_config(self):
        """Test low-volume configuration."""
        config = RoasterConfigDefaults.get_low_volume_config()
        
        assert config['default_concurrency'] == 1
        assert config['use_firecrawl_fallback'] is False
        assert config['firecrawl_budget_limit'] == 3
        assert config['use_llm'] is False
        assert config['alert_price_delta_pct'] == 30.0


class TestRoasterConfigMigration:
    """Test configuration migration utilities."""
    
    def test_migrate_to_v2(self):
        """Test migration to v2 schema using Pydantic aliases."""
        old_config = {
            'id': 'test_roaster',
            'name': 'Test Roaster',
            'concurrency': 3,  # Old field name
            'cadence': '0 3 1 * *'  # Old field name
        }

        # Pydantic V2 handles aliases automatically
        migrated = RoasterConfigSchema.model_validate(old_config)

        assert migrated.id == 'test_roaster'
        assert migrated.name == 'Test Roaster'
        assert migrated.default_concurrency == 3  # Migrated via alias
        assert migrated.full_cadence == '0 3 1 * *'  # Migrated via alias
        assert migrated.active is True  # Default added
    
    def test_validate_migration(self):
        """Test migration validation using Pydantic."""
        valid_config = {
            'id': 'test_roaster',
            'name': 'Test Roaster',
            'default_concurrency': 3
        }
        
        # Should validate successfully
        RoasterConfigSchema.model_validate(valid_config)
        
        # Test with old field names (should work via aliases)
        old_config = {
            'id': 'test_roaster',
            'name': 'Test Roaster',
            'concurrency': 3,  # Old field name
            'cadence': '0 3 1 * *'  # Old field name
        }
        
        # Should also validate successfully
        RoasterConfigSchema.model_validate(old_config)


class TestRoasterConfigIntegration:
    """Integration tests for roaster configuration."""
    
    def test_full_configuration_workflow(self):
        """Test complete configuration workflow."""
        # 1. Create configuration
        config = {
            'id': 'integration_roaster',
            'name': 'Integration Roaster',
            'full_cadence': '0 2 1 * *',
            'price_cadence': '0 3 * * 0',
            'default_concurrency': 4,
            'use_firecrawl_fallback': True,
            'firecrawl_budget_limit': 1500,
            'use_llm': True,
            'alert_price_delta_pct': 18.0,
            'base_url': 'https://api.integration.com',
            'api_endpoints': {
                'products': '/products.json',
                'collections': '/collections.json'
            }
        }
        
        # 2. Validate configuration
        validated = RoasterConfigValidator.validate_config(config)
        assert isinstance(validated, RoasterConfigSchema)
        
        # 3. Test serialization
        json_data = validated.model_dump_json()
        assert 'integration_roaster' in json_data
        assert 'api.integration.com' in json_data
        
        # 4. Test deserialization
        parsed = RoasterConfigSchema.model_validate_json(json_data)
        assert parsed.id == 'integration_roaster'
        assert parsed.base_url == 'https://api.integration.com'
    
    def test_configuration_edge_cases(self):
        """Test configuration edge cases."""
        # Test with minimal required fields
        minimal_config = {
            'id': 'minimal_roaster',
            'name': 'Minimal Roaster'
        }
        
        validated = RoasterConfigValidator.validate_config(minimal_config)
        assert validated.id == 'minimal_roaster'
        assert validated.active is True  # Default value
        
        # Test with all optional fields
        full_config = {
            'id': 'full_roaster',
            'name': 'Full Roaster',
            'active': False,
            'full_cadence': '0 1 1 * *',
            'price_cadence': '0 2 * * 0',
            'default_concurrency': 10,
            'use_firecrawl_fallback': True,
            'firecrawl_budget_limit': 5000,
            'use_llm': True,
            'alert_price_delta_pct': 5.0,
            'base_url': 'https://api.full.com',
            'api_endpoints': {
                'products': '/products.json',
                'collections': '/collections.json',
                'pages': '/pages.json',
                'blogs': '/blogs.json'
            },
            'last_etag': 'etag123',
            'last_modified': datetime.now(timezone.utc)
        }
        
        validated = RoasterConfigValidator.validate_config(full_config)
        assert validated.id == 'full_roaster'
        assert validated.active is False
        assert validated.default_concurrency == 10
        assert len(validated.api_endpoints) == 4
