"""
Error handling tests for Firecrawl operations.

Tests:
- API error handling
- Network error handling
- Budget exceeded errors
- Rate limiting errors
- Configuration errors
- Recovery mechanisms
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, List, Any

from src.fetcher.firecrawl_client import (
    FirecrawlClient,
    FirecrawlError,
    FirecrawlAPIError,
    FirecrawlBudgetExceededError,
    FirecrawlRateLimitError
)
from src.fetcher.firecrawl_map_service import FirecrawlMapService
from src.config.firecrawl_config import FirecrawlConfig
from src.config.roaster_schema import RoasterConfigSchema


class TestFirecrawlErrorHandling:
    """Test Firecrawl error handling functionality."""
    
    @pytest.fixture
    def mock_config(self):
        """Create a mock Firecrawl configuration."""
        return FirecrawlConfig(
            api_key="test_api_key_1234567890",
            base_url="https://api.firecrawl.dev",
            budget_limit=1000,
            max_pages=50,
            include_subdomains=False,
            sitemap_only=False,
            coffee_keywords=['coffee', 'bean', 'roast'],
            timeout=30.0,
            max_retries=3,
            retry_delay=1.0,
            enable_monitoring=True,
            log_level="INFO"
        )
    
    @pytest.fixture
    def mock_roaster_config(self):
        """Create a mock roaster configuration."""
        return RoasterConfigSchema(
            roaster_id="test_roaster_123",
            name="Test Roaster",
            website="https://testroaster.com",
            enabled=True,
            firecrawl_enabled=True,
            firecrawl_config={
                "max_pages": 25,
                "coffee_keywords": ["espresso", "latte"]
            }
        )
    
    @pytest.fixture
    def mock_firecrawl_app(self):
        """Create a mock FirecrawlApp."""
        mock_app = Mock()
        mock_app.map_url = Mock()
        return mock_app
    
    @pytest.fixture
    def firecrawl_client(self, mock_config, mock_firecrawl_app):
        """Create a FirecrawlClient with mocked dependencies."""
        with patch('src.fetcher.firecrawl_client.FirecrawlApp') as mock_app_class:
            mock_app_class.return_value = mock_firecrawl_app
            
            client = FirecrawlClient(mock_config)
            client.app = mock_firecrawl_app
            return client
    
    @pytest.fixture
    def firecrawl_map_service(self, mock_config, firecrawl_client):
        """Create a FirecrawlMapService with mocked dependencies."""
        service = FirecrawlMapService(mock_config)
        service.client = firecrawl_client
        return service
    
    @pytest.mark.asyncio
    async def test_api_error_handling(self, firecrawl_client):
        """Test API error handling."""
        # Mock API error
        firecrawl_client.app.map_url.side_effect = Exception("API Error")
        
        with pytest.raises(FirecrawlAPIError):
            await firecrawl_client.map_domain("https://example.com", ["coffee"])
    
    @pytest.mark.asyncio
    async def test_network_error_handling(self, firecrawl_client):
        """Test network error handling."""
        # Mock network error
        firecrawl_client.app.map_url.side_effect = ConnectionError("Network Error")
        
        with pytest.raises(FirecrawlAPIError):
            await firecrawl_client.map_domain("https://example.com", ["coffee"])
    
    @pytest.mark.asyncio
    async def test_timeout_error_handling(self, firecrawl_client):
        """Test timeout error handling."""
        # Mock timeout error
        firecrawl_client.app.map_url.side_effect = TimeoutError("Request timeout")
        
        with pytest.raises(FirecrawlAPIError):
            await firecrawl_client.map_domain("https://example.com", ["coffee"])
    
    @pytest.mark.asyncio
    async def test_budget_exceeded_error(self, firecrawl_client):
        """Test budget exceeded error handling."""
        # Set budget to 0 to simulate exceeded budget
        firecrawl_client.budget_tracker.current_usage = 1000
        firecrawl_client.budget_tracker.config.budget_limit = 1000
        
        with pytest.raises(FirecrawlBudgetExceededError):
            await firecrawl_client.map_domain("https://example.com", ["coffee"])
    
    @pytest.mark.asyncio
    async def test_rate_limit_error(self, firecrawl_client):
        """Test rate limit error handling."""
        # Mock rate limit error
        firecrawl_client.app.map_url.side_effect = Exception("Rate limit exceeded")
        
        with pytest.raises(FirecrawlAPIError):
            await firecrawl_client.map_domain("https://example.com", ["coffee"])
    
    @pytest.mark.asyncio
    async def test_invalid_api_key_error(self, firecrawl_client):
        """Test invalid API key error handling."""
        # Mock invalid API key error
        firecrawl_client.app.map_url.side_effect = Exception("Invalid API key")
        
        with pytest.raises(FirecrawlAPIError):
            await firecrawl_client.map_domain("https://example.com", ["coffee"])
    
    @pytest.mark.asyncio
    async def test_invalid_domain_error(self, firecrawl_client):
        """Test invalid domain error handling."""
        # Mock invalid domain error
        firecrawl_client.app.map_url.side_effect = Exception("Invalid domain")
        
        with pytest.raises(FirecrawlAPIError):
            await firecrawl_client.map_domain("https://invalid-domain.com", ["coffee"])
    
    @pytest.mark.asyncio
    async def test_service_unavailable_error(self, firecrawl_client):
        """Test service unavailable error handling."""
        # Mock service unavailable error
        firecrawl_client.app.map_url.side_effect = Exception("Service unavailable")
        
        with pytest.raises(FirecrawlAPIError):
            await firecrawl_client.map_domain("https://example.com", ["coffee"])
    
    @pytest.mark.asyncio
    async def test_map_service_error_handling(self, firecrawl_map_service, mock_roaster_config):
        """Test map service error handling."""
        # Mock client error
        firecrawl_map_service.client.discover_product_urls.side_effect = Exception("Client error")
        
        result = await firecrawl_map_service.discover_roaster_products(mock_roaster_config)
        
        # Verify error handling
        assert result['urls_discovered'] == 0
        assert result['urls'] == []
        assert 'error' in result['metadata']
        assert result['metadata']['error'] == "Client error"
    
    @pytest.mark.asyncio
    async def test_disabled_roaster_error_handling(self, firecrawl_map_service):
        """Test disabled roaster error handling."""
        disabled_roaster = RoasterConfigSchema(
            roaster_id="disabled_roaster",
            name="Disabled Roaster",
            website="https://disabledroaster.com",
            enabled=False,
            firecrawl_enabled=True
        )
        
        result = await firecrawl_map_service.discover_roaster_products(disabled_roaster)
        
        # Verify error handling
        assert result['urls_discovered'] == 0
        assert result['urls'] == []
        assert result['metadata']['skipped'] is True
        assert result['metadata']['reason'] == "Roaster or Firecrawl disabled"
    
    @pytest.mark.asyncio
    async def test_firecrawl_disabled_error_handling(self, firecrawl_map_service):
        """Test Firecrawl disabled error handling."""
        firecrawl_disabled_roaster = RoasterConfigSchema(
            roaster_id="firecrawl_disabled_roaster",
            name="Firecrawl Disabled Roaster",
            website="https://firecrawldisabledroaster.com",
            enabled=True,
            firecrawl_enabled=False
        )
        
        result = await firecrawl_map_service.discover_roaster_products(firecrawl_disabled_roaster)
        
        # Verify error handling
        assert result['urls_discovered'] == 0
        assert result['urls'] == []
        assert result['metadata']['skipped'] is True
        assert result['metadata']['reason'] == "Roaster or Firecrawl disabled"
    
    @pytest.mark.asyncio
    async def test_invalid_website_error_handling(self, firecrawl_map_service):
        """Test invalid website error handling."""
        invalid_roaster = RoasterConfigSchema(
            roaster_id="invalid_roaster",
            name="Invalid Roaster",
            website="not-a-valid-url",
            enabled=True,
            firecrawl_enabled=True
        )
        
        result = await firecrawl_map_service.discover_roaster_products(invalid_roaster)
        
        # Verify error handling
        assert result['urls_discovered'] == 0
        assert result['urls'] == []
        assert 'error' in result['metadata']
        assert 'Invalid website URL' in result['metadata']['error']
    
    @pytest.mark.asyncio
    async def test_retry_logic_error_handling(self, firecrawl_client):
        """Test retry logic error handling."""
        # Mock retry logic
        with patch.object(firecrawl_client, '_make_request_with_retry') as mock_retry:
            mock_retry.side_effect = FirecrawlAPIError("Retry failed")
            
            with pytest.raises(FirecrawlAPIError):
                await firecrawl_client.map_domain("https://example.com", ["coffee"])
    
    @pytest.mark.asyncio
    async def test_budget_tracking_error_handling(self, firecrawl_client):
        """Test budget tracking error handling."""
        # Mock budget tracking error
        with patch.object(firecrawl_client.budget_tracker, 'is_within_budget') as mock_budget:
            mock_budget.return_value = False
            
            with pytest.raises(FirecrawlBudgetExceededError):
                await firecrawl_client.map_domain("https://example.com", ["coffee"])
    
    @pytest.mark.asyncio
    async def test_rate_limiting_error_handling(self, firecrawl_client):
        """Test rate limiting error handling."""
        # Mock rate limiting
        with patch.object(firecrawl_client, '_apply_rate_limit') as mock_rate_limit:
            mock_rate_limit.side_effect = FirecrawlRateLimitError("Rate limit exceeded")
            
            with pytest.raises(FirecrawlRateLimitError):
                await firecrawl_client.map_domain("https://example.com", ["coffee"])
    
    @pytest.mark.asyncio
    async def test_health_check_error_handling(self, firecrawl_client):
        """Test health check error handling."""
        # Mock health check error
        firecrawl_client.app.map_url.side_effect = Exception("Health check failed")
        
        result = await firecrawl_client.health_check()
        assert result is False
    
    @pytest.mark.asyncio
    async def test_service_status_error_handling(self, firecrawl_map_service):
        """Test service status error handling."""
        # Mock client error
        firecrawl_map_service.client.get_usage_stats.side_effect = Exception("Client error")
        firecrawl_map_service.client.health_check.return_value = False
        
        status = await firecrawl_map_service.get_service_status()
        
        # Verify error handling
        assert status['client_health'] is False
        assert 'error' in status
        assert 'Client error' in status['error']
    
    @pytest.mark.asyncio
    async def test_recovery_mechanisms(self, firecrawl_client):
        """Test recovery mechanisms."""
        # Mock recovery scenario
        firecrawl_client.app.map_url.side_effect = [
            Exception("Temporary error"),
            Exception("Temporary error"),
            {'links': ['https://example.com/coffee/beans']}
        ]
        
        # Test recovery
        result = await firecrawl_client.map_domain("https://example.com", ["coffee"])
        
        # Verify recovery
        assert 'domain' in result
        assert 'total_links' in result
        assert 'filtered_urls' in result
        assert 'coffee_urls' in result
        assert 'product_urls' in result
        assert 'metadata' in result
    
    @pytest.mark.asyncio
    async def test_error_metadata_creation(self, firecrawl_map_service, mock_roaster_config):
        """Test error metadata creation."""
        error_metadata = firecrawl_map_service._create_error_metadata(
            mock_roaster_config,
            "Test error message"
        )
        
        # Verify error metadata
        assert 'roaster_id' in error_metadata
        assert 'roaster_name' in error_metadata
        assert 'website' in error_metadata
        assert 'error' in error_metadata
        assert 'timestamp' in error_metadata
        assert error_metadata['roaster_id'] == "test_roaster_123"
        assert error_metadata['error'] == "Test error message"
    
    @pytest.mark.asyncio
    async def test_error_handling_with_custom_config(self, firecrawl_map_service):
        """Test error handling with custom roaster configuration."""
        custom_roaster = RoasterConfigSchema(
            roaster_id="custom_roaster",
            name="Custom Roaster",
            website="https://customroaster.com",
            enabled=True,
            firecrawl_enabled=True,
            firecrawl_config={
                "max_pages": 25,
                "coffee_keywords": ["espresso", "latte"]
            }
        )
        
        # Mock client error
        firecrawl_map_service.client.discover_product_urls.side_effect = Exception("Custom config error")
        
        result = await firecrawl_map_service.discover_roaster_products(custom_roaster)
        
        # Verify error handling
        assert result['urls_discovered'] == 0
        assert result['urls'] == []
        assert 'error' in result['metadata']
        assert result['metadata']['error'] == "Custom config error"
    
    @pytest.mark.asyncio
    async def test_error_handling_with_invalid_config(self, firecrawl_map_service):
        """Test error handling with invalid roaster configuration."""
        invalid_roaster = RoasterConfigSchema(
            roaster_id="invalid_roaster",
            name="Invalid Roaster",
            website="https://invalidroaster.com",
            enabled=True,
            firecrawl_enabled=True,
            firecrawl_config={
                "invalid_key": "invalid_value"
            }
        )
        
        # Mock client error
        firecrawl_map_service.client.discover_product_urls.side_effect = Exception("Invalid config error")
        
        result = await firecrawl_map_service.discover_roaster_products(invalid_roaster)
        
        # Verify error handling
        assert result['urls_discovered'] == 0
        assert result['urls'] == []
        assert 'error' in result['metadata']
        assert result['metadata']['error'] == "Invalid config error"
    
    @pytest.mark.asyncio
    async def test_error_handling_with_missing_config(self, firecrawl_map_service):
        """Test error handling with missing roaster configuration."""
        missing_config_roaster = RoasterConfigSchema(
            roaster_id="missing_config_roaster",
            name="Missing Config Roaster",
            website="https://missingconfigroaster.com",
            enabled=True,
            firecrawl_enabled=True
        )
        
        # Mock client error
        firecrawl_map_service.client.discover_product_urls.side_effect = Exception("Missing config error")
        
        result = await firecrawl_map_service.discover_roaster_products(missing_config_roaster)
        
        # Verify error handling
        assert result['urls_discovered'] == 0
        assert result['urls'] == []
        assert 'error' in result['metadata']
        assert result['metadata']['error'] == "Missing config error"
    
    @pytest.mark.asyncio
    async def test_error_handling_with_empty_response(self, firecrawl_map_service, mock_roaster_config):
        """Test error handling with empty response."""
        # Mock empty response
        firecrawl_map_service.client.discover_product_urls.return_value = []
        
        result = await firecrawl_map_service.discover_roaster_products(mock_roaster_config)
        
        # Verify error handling
        assert result['urls_discovered'] == 0
        assert result['urls'] == []
        assert 'metadata' in result
        assert 'budget_usage' in result
    
    @pytest.mark.asyncio
    async def test_error_handling_with_malformed_response(self, firecrawl_map_service, mock_roaster_config):
        """Test error handling with malformed response."""
        # Mock malformed response
        firecrawl_map_service.client.discover_product_urls.return_value = None
        
        result = await firecrawl_map_service.discover_roaster_products(mock_roaster_config)
        
        # Verify error handling
        assert result['urls_discovered'] == 0
        assert result['urls'] == []
        assert 'error' in result['metadata']
        assert 'Malformed response' in result['metadata']['error']
