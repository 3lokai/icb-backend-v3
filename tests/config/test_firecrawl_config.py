"""
Unit tests for Firecrawl configuration.

Tests:
- Configuration validation
- Budget tracking
- Default values
- Error handling
"""

import pytest
from pydantic import ValidationError

from src.config.firecrawl_config import (
    FirecrawlConfig,
    FirecrawlBudgetTracker,
    FirecrawlConfigDefaults,
    FirecrawlConfigValidator
)


class TestFirecrawlConfig:
    """Test Firecrawl configuration validation and defaults."""
    
    def test_valid_config_creation(self):
        """Test creating a valid Firecrawl configuration."""
        config = FirecrawlConfig(
            api_key="test_api_key_1234567890",
            base_url="https://api.firecrawl.dev",
            budget_limit=1000,
            max_pages=50
        )
        
        assert config.api_key == "test_api_key_1234567890"
        assert config.base_url == "https://api.firecrawl.dev"
        assert config.budget_limit == 1000
        assert config.max_pages == 50
        assert config.include_subdomains is False
        assert config.sitemap_only is False
        # Check that basic coffee keywords are included
        expected_basic_keywords = [
            'coffee', 'bean', 'roast', 'brew', 'espresso',
            'latte', 'cappuccino', 'mocha', 'americano'
        ]
        for keyword in expected_basic_keywords:
            assert keyword in config.coffee_keywords
        
        # Check that the list is comprehensive (should have more than just basic terms)
        assert len(config.coffee_keywords) > 10
    
    def test_config_with_custom_values(self):
        """Test configuration with custom values."""
        config = FirecrawlConfig(
            api_key="custom_key_1234567890",
            base_url="https://custom.firecrawl.dev",
            budget_limit=5000,
            max_pages=200,
            include_subdomains=True,
            sitemap_only=True,
            coffee_keywords=['coffee', 'bean', 'roast'],
            timeout=60.0,
            max_retries=5,
            retry_delay=2.0,
            enable_monitoring=True,
            log_level="DEBUG"
        )
        
        assert config.api_key == "custom_key_1234567890"
        assert config.base_url == "https://custom.firecrawl.dev"
        assert config.budget_limit == 5000
        assert config.max_pages == 200
        assert config.include_subdomains is True
        assert config.sitemap_only is True
        assert config.coffee_keywords == ['coffee', 'bean', 'roast']
        assert config.timeout == 60.0
        assert config.max_retries == 5
        assert config.retry_delay == 2.0
        assert config.enable_monitoring is True
        assert config.log_level == "DEBUG"
    
    def test_api_key_validation(self):
        """Test API key validation."""
        # Test empty API key
        with pytest.raises(ValidationError) as exc_info:
            FirecrawlConfig(api_key="")
        assert "API key cannot be empty" in str(exc_info.value)
        
        # Test short API key
        with pytest.raises(ValidationError) as exc_info:
            FirecrawlConfig(api_key="short")
        assert "API key appears to be too short" in str(exc_info.value)
        
        # Test valid API key
        config = FirecrawlConfig(api_key="valid_api_key_1234567890")
        assert config.api_key == "valid_api_key_1234567890"
    
    def test_base_url_validation(self):
        """Test base URL validation."""
        # Test invalid URL
        with pytest.raises(ValidationError) as exc_info:
            FirecrawlConfig(api_key="test_key_1234567890", base_url="invalid_url")
        assert "Base URL must start with http:// or https://" in str(exc_info.value)
        
        # Test valid URLs
        config1 = FirecrawlConfig(api_key="test_key_1234567890", base_url="https://api.firecrawl.dev")
        assert config1.base_url == "https://api.firecrawl.dev"
        
        config2 = FirecrawlConfig(api_key="test_key_1234567890", base_url="http://localhost:8080")
        assert config2.base_url == "http://localhost:8080"
    
    def test_budget_limit_validation(self):
        """Test budget limit validation."""
        # Test negative budget
        with pytest.raises(ValidationError):
            FirecrawlConfig(api_key="test_key_1234567890", budget_limit=-1)
        
        # Test valid budget
        config = FirecrawlConfig(api_key="test_key_1234567890", budget_limit=1000)
        assert config.budget_limit == 1000
    
    def test_max_pages_validation(self):
        """Test max pages validation."""
        # Test too low
        with pytest.raises(ValidationError):
            FirecrawlConfig(api_key="test_key_1234567890", max_pages=0)
        
        # Test too high
        with pytest.raises(ValidationError):
            FirecrawlConfig(api_key="test_key_1234567890", max_pages=1001)
        
        # Test valid range
        config = FirecrawlConfig(api_key="test_key_1234567890", max_pages=50)
        assert config.max_pages == 50
    
    def test_keywords_validation(self):
        """Test keywords validation."""
        # Test empty keywords
        config = FirecrawlConfig(api_key="test_key_1234567890", coffee_keywords=[])
        assert config.coffee_keywords == []
        
        # Test duplicate keywords
        with pytest.raises(ValidationError) as exc_info:
            FirecrawlConfig(api_key="test_key_1234567890", coffee_keywords=['coffee', 'bean', 'coffee'])
        assert "Keywords must be unique" in str(exc_info.value)
        
        # Test valid keywords
        keywords = ['coffee', 'bean', 'roast']
        config = FirecrawlConfig(api_key="test_key_1234567890", coffee_keywords=keywords)
        assert config.coffee_keywords == keywords
    
    def test_log_level_validation(self):
        """Test log level validation."""
        # Test invalid log level
        with pytest.raises(ValidationError) as exc_info:
            FirecrawlConfig(api_key="test_key_1234567890", log_level="INVALID")
        assert "Log level must be one of" in str(exc_info.value)
        
        # Test valid log levels
        for level in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']:
            config = FirecrawlConfig(api_key="test_key_1234567890", log_level=level)
            assert config.log_level == level
    
    def test_to_dict_conversion(self):
        """Test configuration to dictionary conversion."""
        config = FirecrawlConfig(
            api_key="test_key_1234567890",
            budget_limit=1000,
            max_pages=50
        )
        
        config_dict = config.to_dict()
        
        assert isinstance(config_dict, dict)
        assert config_dict['api_key'] == "test_key_1234567890"
        assert config_dict['budget_limit'] == 1000
        assert config_dict['max_pages'] == 50
    
    def test_from_dict_creation(self):
        """Test configuration creation from dictionary."""
        config_dict = {
            'api_key': 'test_key_1234567890',
            'budget_limit': 1000,
            'max_pages': 50,
            'include_subdomains': True
        }
        
        config = FirecrawlConfig.from_dict(config_dict)
        
        assert config.api_key == "test_key_1234567890"
        assert config.budget_limit == 1000
        assert config.max_pages == 50
        assert config.include_subdomains is True


class TestFirecrawlBudgetTracker:
    """Test Firecrawl budget tracking functionality."""
    
    def test_budget_tracker_initialization(self):
        """Test budget tracker initialization."""
        config = FirecrawlConfig(api_key="test_key_1234567890", budget_limit=1000)
        tracker = FirecrawlBudgetTracker(config)
        
        assert tracker.current_usage == 0
        assert tracker.operations_count == 0
        assert tracker.config.budget_limit == 1000
    
    def test_can_operate_within_budget(self):
        """Test can_operate when within budget."""
        config = FirecrawlConfig(api_key="test_key_1234567890", budget_limit=1000)
        tracker = FirecrawlBudgetTracker(config)
        
        assert tracker.can_operate() is True
        
        # Use some budget
        tracker.record_operation(100)
        assert tracker.can_operate() is True
    
    def test_can_operate_exceeds_budget(self):
        """Test can_operate when budget exceeded."""
        config = FirecrawlConfig(api_key="test_key_1234567890", budget_limit=100)
        tracker = FirecrawlBudgetTracker(config)
        
        # Use all budget
        tracker.record_operation(100)
        assert tracker.can_operate() is False
    
    def test_record_operation_success(self):
        """Test successful operation recording."""
        config = FirecrawlConfig(api_key="test_key_1234567890", budget_limit=1000)
        tracker = FirecrawlBudgetTracker(config)
        
        result = tracker.record_operation(50)
        
        assert result is True
        assert tracker.current_usage == 50
        assert tracker.operations_count == 1
    
    def test_record_operation_budget_exceeded(self):
        """Test operation recording when budget exceeded."""
        config = FirecrawlConfig(api_key="test_key_1234567890", budget_limit=100)
        tracker = FirecrawlBudgetTracker(config)
        
        # Use all budget
        tracker.record_operation(100)
        
        # Try to record another operation
        result = tracker.record_operation(50)
        
        assert result is False
        assert tracker.current_usage == 100  # Should not change
        assert tracker.operations_count == 1  # Should not increment
    
    def test_get_usage_stats(self):
        """Test usage statistics retrieval."""
        config = FirecrawlConfig(api_key="test_key_1234567890", budget_limit=1000)
        tracker = FirecrawlBudgetTracker(config)
        
        # Record some operations
        tracker.record_operation(100)
        tracker.record_operation(200)
        
        stats = tracker.get_usage_stats()
        
        assert stats['current_usage'] == 300
        assert stats['budget_limit'] == 1000
        assert stats['remaining_budget'] == 700
        assert stats['operations_count'] == 2
        assert stats['usage_percentage'] == 30.0
    
    def test_reset_budget(self):
        """Test budget tracker reset."""
        config = FirecrawlConfig(api_key="test_key_1234567890", budget_limit=1000)
        tracker = FirecrawlBudgetTracker(config)
        
        # Record some operations
        tracker.record_operation(100)
        tracker.record_operation(200)
        
        # Reset
        tracker.reset()
        
        assert tracker.current_usage == 0
        assert tracker.operations_count == 0


class TestFirecrawlConfigDefaults:
    """Test Firecrawl configuration defaults."""
    
    def test_get_default_config(self):
        """Test getting default configuration."""
        default_config = FirecrawlConfigDefaults.get_default_config()
        
        assert isinstance(default_config, dict)
        assert 'api_key' in default_config
        assert 'base_url' in default_config
        assert 'budget_limit' in default_config
        assert 'max_pages' in default_config
        assert default_config['budget_limit'] == 1000
        assert default_config['max_pages'] == 50
    
    def test_get_high_volume_config(self):
        """Test getting high volume configuration."""
        high_volume_config = FirecrawlConfigDefaults.get_high_volume_config()
        
        assert isinstance(high_volume_config, dict)
        assert high_volume_config['budget_limit'] == 5000
        assert high_volume_config['max_pages'] == 200
        assert high_volume_config['include_subdomains'] is True
    
    def test_get_conservative_config(self):
        """Test getting conservative configuration."""
        conservative_config = FirecrawlConfigDefaults.get_conservative_config()
        
        assert isinstance(conservative_config, dict)
        assert conservative_config['budget_limit'] == 100
        assert conservative_config['max_pages'] == 10
        assert conservative_config['sitemap_only'] is True


class TestFirecrawlConfigValidator:
    """Test Firecrawl configuration validator."""
    
    def test_validate_config_success(self):
        """Test successful configuration validation."""
        config_dict = {
            'api_key': 'test_key_1234567890',
            'budget_limit': 1000,
            'max_pages': 50
        }
        
        config = FirecrawlConfigValidator.validate_config(config_dict)
        
        assert isinstance(config, FirecrawlConfig)
        assert config.api_key == "test_key_1234567890"
        assert config.budget_limit == 1000
        assert config.max_pages == 50
    
    def test_validate_config_failure(self):
        """Test configuration validation failure."""
        invalid_config = {
            'api_key': '',  # Invalid empty key
            'budget_limit': -1,  # Invalid negative budget
            'max_pages': 0  # Invalid zero pages
        }
        
        with pytest.raises(ValueError) as exc_info:
            FirecrawlConfigValidator.validate_config(invalid_config)
        assert "Invalid Firecrawl configuration" in str(exc_info.value)
    
    def test_validate_batch_configs_success(self):
        """Test successful batch configuration validation."""
        configs = [
            {'api_key': 'key1_1234567890', 'budget_limit': 1000},
            {'api_key': 'key2_1234567890', 'budget_limit': 2000},
            {'api_key': 'key3_1234567890', 'budget_limit': 3000}
        ]
        
        validated_configs = FirecrawlConfigValidator.validate_batch_configs(configs)
        
        assert len(validated_configs) == 3
        assert all(isinstance(config, FirecrawlConfig) for config in validated_configs)
    
    def test_validate_batch_configs_failure(self):
        """Test batch configuration validation failure."""
        configs = [
            {'api_key': 'key1_1234567890', 'budget_limit': 1000},  # Valid
            {'api_key': '', 'budget_limit': 2000},  # Invalid
            {'api_key': 'key3_1234567890', 'budget_limit': 3000}  # Valid
        ]
        
        with pytest.raises(ValueError) as exc_info:
            FirecrawlConfigValidator.validate_batch_configs(configs)
        assert "Batch validation failed" in str(exc_info.value)
