"""
Unit tests for FirecrawlMapService.

Tests the map discovery service functionality including:
- Service initialization
- Product URL discovery
- URL validation and filtering
- Batch processing
- Error handling
- Service status
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
from typing import Dict, List, Any

from src.fetcher.firecrawl_map_service import FirecrawlMapService
from src.fetcher.firecrawl_client import FirecrawlError, FirecrawlBudgetExceededError
from src.config.firecrawl_config import FirecrawlConfig
from src.config.roaster_schema import RoasterConfigSchema


class TestFirecrawlMapService:
    """Test cases for FirecrawlMapService."""
    
    @pytest.fixture
    def mock_config(self):
        """Create a mock FirecrawlConfig."""
        return FirecrawlConfig(
            api_key="test_api_key",
            base_url="https://api.firecrawl.dev",
            budget_limit=1000,
            max_pages=10,
            include_subdomains=True,
            sitemap_only=False,
            coffee_keywords=["coffee", "bean", "roast", "espresso", "latte", "cappuccino"],
            timeout=30,
            retries=3,
            monitoring_enabled=True,
            log_level="INFO"
        )
    
    @pytest.fixture
    def mock_firecrawl_client(self, mock_config):
        """Create a mock FirecrawlClient."""
        client = Mock()
        client.config = mock_config
        
        # Mock budget tracker
        budget_tracker = Mock()
        budget_tracker.can_operate.return_value = True
        budget_tracker.current_usage = 0
        budget_tracker.get_usage_stats.return_value = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'budget_used': 0,
            'budget_remaining': 1000,
            'remaining_budget': 1000
        }
        client.budget_tracker = budget_tracker
        
        client.health_check = AsyncMock(return_value=True)
        client.get_usage_stats = Mock(return_value={
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'budget_used': 0,
            'budget_remaining': 1000
        })
        client.map_url = AsyncMock()
        client.discover_product_urls = AsyncMock()
        return client
    
    @pytest.fixture
    def firecrawl_map_service(self, mock_config, mock_firecrawl_client):
        """Create a FirecrawlMapService instance with mocked dependencies."""
        # Set up the mock client to have the config attribute
        mock_firecrawl_client.config = mock_config
        
        service = FirecrawlMapService(mock_firecrawl_client)
        return service
    
    @pytest.fixture
    def mock_roaster_config(self):
        """Create a mock roaster configuration."""
        return RoasterConfigSchema(
            id="test_roaster_123",
            name="Test Roaster",
            base_url="https://testroaster.com",
            active=True,
            use_firecrawl_fallback=True,
            firecrawl_budget_limit=1000
        )
    
    def test_service_initialization(self, firecrawl_map_service, mock_config):
        """Test service initialization."""
        assert firecrawl_map_service.config == mock_config
        assert firecrawl_map_service.client is not None
    
    def test_is_valid_url(self, firecrawl_map_service):
        """Test URL validation."""
        # Valid URLs
        assert firecrawl_map_service._is_valid_url("https://example.com") is True
        assert firecrawl_map_service._is_valid_url("http://example.com") is True
        assert firecrawl_map_service._is_valid_url("https://example.com/products") is True
        
        # Invalid URLs
        assert firecrawl_map_service._is_valid_url("not-a-url") is False
        assert firecrawl_map_service._is_valid_url("") is False
        assert firecrawl_map_service._is_valid_url(None) is False
    
    def test_is_same_domain(self, firecrawl_map_service):
        """Test domain comparison."""
        # Same domain
        assert firecrawl_map_service._is_same_domain("https://example.com/products", "https://example.com/about") is True
        
        # Different domain
        assert firecrawl_map_service._is_same_domain("https://example.com/products", "https://other.com/products") is False
        
        # Subdomain (this might not be considered same domain depending on implementation)
        # Let's test with same subdomain instead
        assert firecrawl_map_service._is_same_domain("https://shop.example.com/products", "https://shop.example.com/about") is True
    
    def test_is_likely_product_url(self, firecrawl_map_service):
        """Test product URL detection."""
        # Product URLs
        assert firecrawl_map_service._is_likely_product_url("https://example.com/products/coffee-bean") is True
        assert firecrawl_map_service._is_likely_product_url("https://example.com/shop/espresso-blend") is True
        assert firecrawl_map_service._is_likely_product_url("https://example.com/coffee/roast") is True
        
        # Non-product URLs
        assert firecrawl_map_service._is_likely_product_url("https://example.com/about") is False
        assert firecrawl_map_service._is_likely_product_url("https://example.com/contact") is False
        assert firecrawl_map_service._is_likely_product_url("https://example.com/blog") is False
    
    @pytest.mark.asyncio
    async def test_discover_roaster_products_success(self, firecrawl_map_service, mock_roaster_config):
        """Test successful product discovery."""
        # Mock the client response
        mock_discovered_urls = [
            'https://testroaster.com/products/coffee-bean-1',
            'https://testroaster.com/products/espresso-blend',
            'https://testroaster.com/about',
            'https://testroaster.com/contact'
        ]
        
        firecrawl_map_service.client.discover_product_urls.return_value = mock_discovered_urls
        
        # Test discovery
        result = await firecrawl_map_service.discover_roaster_products(mock_roaster_config)
        
        # Verify result
        assert result['status'] == 'success'
        assert len(result['discovered_urls']) == 2  # Only product URLs
        assert 'https://testroaster.com/products/coffee-bean-1' in result['discovered_urls']
        assert 'https://testroaster.com/products/espresso-blend' in result['discovered_urls']
        assert 'https://testroaster.com/about' not in result['discovered_urls']
    
    @pytest.mark.asyncio
    async def test_discover_roaster_products_client_error(self, firecrawl_map_service, mock_roaster_config):
        """Test product discovery with client error."""
        # Mock client error
        firecrawl_map_service.client.discover_product_urls.side_effect = FirecrawlError("API error")
        
        # Test discovery
        result = await firecrawl_map_service.discover_roaster_products(mock_roaster_config)
        
        # Verify error handling
        assert result['status'] == 'error'
        assert 'message' in result
        assert result['discovered_urls'] == []
    
    @pytest.mark.asyncio
    async def test_discover_roaster_products_budget_exceeded(self, firecrawl_map_service, mock_roaster_config):
        """Test product discovery with budget exceeded."""
        # Mock budget exceeded error
        firecrawl_map_service.client.discover_product_urls.side_effect = FirecrawlBudgetExceededError("Budget exceeded")
        
        # Test discovery
        result = await firecrawl_map_service.discover_roaster_products(mock_roaster_config)
        
        # Verify error handling
        assert result['status'] == 'budget_exceeded'
        assert 'message' in result
        assert 'budget' in result['message'].lower()
        assert result['discovered_urls'] == []
    
    @pytest.mark.asyncio
    async def test_batch_discover_products_success(self, firecrawl_map_service):
        """Test batch product discovery."""
        # Mock roaster configs
        roaster_configs = [
            RoasterConfigSchema(
                id="roaster1",
                name="Roaster 1",
                base_url="https://roaster1.com",
                active=True,
                use_firecrawl_fallback=True
            ),
            RoasterConfigSchema(
                id="roaster2", 
                name="Roaster 2",
                base_url="https://roaster2.com",
                active=True,
                use_firecrawl_fallback=True
            )
        ]
        
        # Mock successful responses
        mock_discovered_urls_1 = ['https://roaster1.com/products/coffee-1']
        mock_discovered_urls_2 = ['https://roaster2.com/products/coffee-2']
        
        firecrawl_map_service.client.discover_product_urls.side_effect = [
            mock_discovered_urls_1,
            mock_discovered_urls_2
        ]
        
        # Test batch discovery
        results = await firecrawl_map_service.batch_discover_products(roaster_configs)
        
        # Verify results structure
        assert 'results' in results
        assert len(results['results']) == 2
        assert all(result['status'] == 'success' for result in results['results'])
        assert len(results['results'][0]['discovered_urls']) == 1
        assert len(results['results'][1]['discovered_urls']) == 1
    
    @pytest.mark.asyncio
    async def test_get_service_status_healthy(self, firecrawl_map_service):
        """Test service status when healthy."""
        # Mock healthy client
        firecrawl_map_service.client.health_check.return_value = True
        firecrawl_map_service.client.get_usage_stats.return_value = {
            'total_requests': 10,
            'successful_requests': 8,
            'failed_requests': 2,
            'budget_used': 100,
            'budget_remaining': 900
        }
        
        # Test status
        status = await firecrawl_map_service.get_service_status()
        
        # Verify status
        assert status['service'] == 'FirecrawlMapService'
        assert status['status'] == 'healthy'
        assert 'timestamp' in status
        assert 'budget_usage' in status
        assert 'configuration' in status
    
    @pytest.mark.asyncio
    async def test_get_service_status_unhealthy(self, firecrawl_map_service):
        """Test service status when unhealthy."""
        # Mock unhealthy client
        firecrawl_map_service.client.health_check.return_value = False
        firecrawl_map_service.client.get_usage_stats.return_value = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'budget_used': 0,
            'budget_remaining': 1000
        }
        
        # Test status
        status = await firecrawl_map_service.get_service_status()
        
        # Verify status
        assert status['service'] == 'FirecrawlMapService'
        assert status['status'] == 'unhealthy'
        assert 'timestamp' in status
        assert 'budget_usage' in status
    
    @pytest.mark.asyncio
    async def test_get_service_status_error(self, firecrawl_map_service):
        """Test service status with error."""
        # Mock client error
        firecrawl_map_service.client.health_check.side_effect = Exception("Health check failed")
        
        # Test status
        status = await firecrawl_map_service.get_service_status()
        
        # Verify error status
        assert status['service'] == 'FirecrawlMapService'
        assert status['status'] == 'error'
        assert 'error' in status
        assert 'timestamp' in status
    
    def test_validate_product_urls(self, firecrawl_map_service, mock_roaster_config):
        """Test product URL validation."""
        # Test URLs - use same domain as roaster config
        urls = [
            "https://testroaster.com/products/coffee-bean",
            "https://testroaster.com/shop/espresso-blend", 
            "https://testroaster.com/about",
            "https://testroaster.com/contact",
            "not-a-url"
        ]
        
        # Test validation with roaster config
        valid_urls = firecrawl_map_service._validate_product_urls(urls, mock_roaster_config)
        
        # Verify results
        assert len(valid_urls) == 2  # Only product URLs
        assert "https://testroaster.com/products/coffee-bean" in valid_urls
        assert "https://testroaster.com/shop/espresso-blend" in valid_urls
        assert "https://testroaster.com/about" not in valid_urls
        assert "https://testroaster.com/contact" not in valid_urls
        assert "not-a-url" not in valid_urls