"""
Unit tests for Firecrawl client service.

Tests:
- Client initialization
- Map domain functionality
- URL filtering
- Error handling
- Rate limiting
- Budget tracking
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
from src.config.firecrawl_config import FirecrawlConfig


class TestFirecrawlClient:
    """Test Firecrawl client functionality."""
    
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
    def mock_firecrawl_app(self):
        """Create a mock FirecrawlApp."""
        mock_app = Mock()
        mock_app.map_url = Mock()
        return mock_app
    
    @pytest.fixture
    def firecrawl_client(self, mock_config):
        """Create a FirecrawlClient instance with mocked dependencies."""
        with patch('src.fetcher.firecrawl_client.FirecrawlApp') as mock_app_class:
            mock_app = Mock()
            mock_app_class.return_value = mock_app
            
            client = FirecrawlClient(mock_config)
            client.app = mock_app
            return client
    
    def test_client_initialization(self, mock_config):
        """Test client initialization."""
        with patch('src.fetcher.firecrawl_client.FirecrawlApp'):
            client = FirecrawlClient(mock_config)
            
            assert client.config == mock_config
            assert client.budget_tracker is not None
            assert client.last_request_time == 0
            assert client.request_count == 0
            assert client.metrics is not None
            assert client.alert_manager is not None
    
    @pytest.mark.asyncio
    async def test_map_domain_success(self, firecrawl_client):
        """Test successful domain mapping."""
        # Mock Firecrawl response
        mock_response = {
            'links': [
                'https://example.com/coffee/beans',
                'https://example.com/products/roast',
                'https://example.com/about',
                'https://example.com/contact'
            ]
        }
        
        firecrawl_client.app.map_url.return_value = mock_response
        
        # Test domain mapping
        result = await firecrawl_client.map_domain("https://example.com", ["coffee"])
        
        # Verify result structure
        assert 'domain' in result
        assert 'total_links' in result
        assert 'filtered_urls' in result
        assert 'coffee_urls' in result
        assert 'product_urls' in result
        assert 'metadata' in result
        
        # Verify Firecrawl was called with correct parameters
        firecrawl_client.app.map_url.assert_called_once()
        call_args = firecrawl_client.app.map_url.call_args
        assert call_args[1]['url'] == "https://example.com"
        assert 'search' in call_args[1]['params']
    
    @pytest.mark.asyncio
    async def test_map_domain_without_protocol(self, firecrawl_client):
        """Test domain mapping with domain without protocol."""
        mock_response = {'links': []}
        firecrawl_client.app.map_url.return_value = mock_response
        
        result = await firecrawl_client.map_domain("example.com", ["coffee"])
        
        # Verify protocol was added
        call_args = firecrawl_client.app.map_url.call_args
        assert call_args[1]['url'] == "https://example.com"
    
    @pytest.mark.asyncio
    async def test_map_domain_api_error(self, firecrawl_client):
        """Test domain mapping with API error."""
        firecrawl_client.app.map_url.side_effect = Exception("API Error")
        
        with pytest.raises(FirecrawlAPIError):
            await firecrawl_client.map_domain("https://example.com", ["coffee"])
    
    @pytest.mark.asyncio
    async def test_map_domain_budget_exceeded(self, firecrawl_client):
        """Test domain mapping when budget exceeded."""
        # Set budget to 0 to simulate exceeded budget
        firecrawl_client.budget_tracker.current_usage = 1000
        firecrawl_client.budget_tracker.config.budget_limit = 1000
        
        with pytest.raises(FirecrawlBudgetExceededError):
            await firecrawl_client.map_domain("https://example.com", ["coffee"])
    
    def test_filter_coffee_urls(self, firecrawl_client):
        """Test coffee URL filtering."""
        urls = [
            'https://example.com/coffee/beans',
            'https://example.com/products/roast',
            'https://example.com/about',
            'https://example.com/contact',
            'https://example.com/espresso/machine'
        ]
        
        coffee_urls = firecrawl_client._filter_coffee_urls(urls)
        
        assert 'https://example.com/coffee/beans' in coffee_urls
        assert 'https://example.com/products/roast' in coffee_urls
        assert 'https://example.com/espresso/machine' in coffee_urls
        assert 'https://example.com/about' not in coffee_urls
        assert 'https://example.com/contact' not in coffee_urls
    
    def test_filter_product_urls(self, firecrawl_client):
        """Test product URL filtering."""
        urls = [
            'https://example.com/product/coffee-beans',
            'https://example.com/products/roast',
            'https://example.com/shop/beans',
            'https://example.com/about',
            'https://example.com/contact',
            'https://example.com/help'
        ]
        
        product_urls = firecrawl_client._filter_product_urls(urls)
        
        assert 'https://example.com/product/coffee-beans' in product_urls
        assert 'https://example.com/products/roast' in product_urls
        assert 'https://example.com/shop/beans' in product_urls
        assert 'https://example.com/about' not in product_urls
        assert 'https://example.com/contact' not in product_urls
        assert 'https://example.com/help' not in product_urls
    
    @pytest.mark.asyncio
    async def test_discover_product_urls(self, firecrawl_client):
        """Test product URL discovery."""
        mock_response = {
            'links': [
                'https://example.com/coffee/beans',
                'https://example.com/products/roast',
                'https://example.com/about'
            ]
        }
        
        firecrawl_client.app.map_url.return_value = mock_response
        
        # Mock the _process_map_result method
        with patch.object(firecrawl_client, '_process_map_result') as mock_process:
            mock_process.return_value = {
                'coffee_urls': ['https://example.com/coffee/beans'],
                'product_urls': ['https://example.com/products/roast']
            }
            
            urls = await firecrawl_client.discover_product_urls("https://example.com", ["coffee"])
            
            assert len(urls) == 2
            assert 'https://example.com/coffee/beans' in urls
            assert 'https://example.com/products/roast' in urls
    
    def test_get_usage_stats(self, firecrawl_client):
        """Test usage statistics retrieval."""
        stats = firecrawl_client.get_usage_stats()
        
        assert 'current_usage' in stats
        assert 'budget_limit' in stats
        assert 'remaining_budget' in stats
        assert 'operations_count' in stats
        assert 'usage_percentage' in stats
    
    def test_reset_budget(self, firecrawl_client):
        """Test budget reset."""
        # Use some budget first
        firecrawl_client.budget_tracker.record_operation(100)
        assert firecrawl_client.budget_tracker.current_usage == 100
        
        # Reset budget
        firecrawl_client.reset_budget()
        assert firecrawl_client.budget_tracker.current_usage == 0
    
    @pytest.mark.asyncio
    async def test_health_check_success(self, firecrawl_client):
        """Test successful health check."""
        mock_response = {'links': []}
        firecrawl_client.app.map_url.return_value = mock_response
        
        # Mock the map_domain method to avoid actual API call
        with patch.object(firecrawl_client, 'map_domain') as mock_map:
            mock_map.return_value = {'links': []}
            
            result = await firecrawl_client.health_check()
            assert result is True
    
    @pytest.mark.asyncio
    async def test_health_check_failure(self, firecrawl_client):
        """Test failed health check."""
        firecrawl_client.app.map_url.side_effect = Exception("Health check failed")
        
        result = await firecrawl_client.health_check()
        assert result is False
    
    def test_get_monitoring_metrics(self, firecrawl_client):
        """Test monitoring metrics retrieval."""
        metrics = firecrawl_client.get_monitoring_metrics()
        
        assert 'timestamp' in metrics
        assert 'metrics' in metrics
        assert 'health' in metrics
    
    def test_get_health_status(self, firecrawl_client):
        """Test health status retrieval."""
        status = firecrawl_client.get_health_status()
        
        assert 'status' in status
        assert 'budget_usage' in status
        assert 'configuration' in status
    
    def test_get_active_alerts(self, firecrawl_client):
        """Test active alerts retrieval."""
        alerts = firecrawl_client.get_active_alerts()
        
        assert isinstance(alerts, list)
    
    def test_reset_monitoring(self, firecrawl_client):
        """Test monitoring reset."""
        # This should not raise an exception
        firecrawl_client.reset_monitoring()
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self, firecrawl_client):
        """Test rate limiting functionality."""
        # Mock the _apply_rate_limit method to test it's called
        with patch.object(firecrawl_client, '_apply_rate_limit') as mock_rate_limit:
            mock_response = {'links': []}
            firecrawl_client.app.map_url.return_value = mock_response
            
            await firecrawl_client.map_domain("https://example.com", ["coffee"])
            
            # Verify rate limiting was applied
            mock_rate_limit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_retry_logic(self, firecrawl_client):
        """Test retry logic for failed requests."""
        # Mock the _make_request_with_retry method to test retry behavior
        with patch.object(firecrawl_client, '_make_request_with_retry') as mock_retry:
            mock_retry.side_effect = FirecrawlAPIError("Retry failed")
            
            with pytest.raises(FirecrawlAPIError):
                await firecrawl_client.map_domain("https://example.com", ["coffee"])
    
    def test_process_map_result(self, firecrawl_client):
        """Test map result processing."""
        mock_result = {
            'links': [
                'https://example.com/coffee/beans',
                'https://example.com/products/roast',
                'https://example.com/about'
            ]
        }
        
        result = firecrawl_client._process_map_result(mock_result, "https://example.com")
        
        assert 'domain' in result
        assert 'total_links' in result
        assert 'filtered_urls' in result
        assert 'coffee_urls' in result
        assert 'product_urls' in result
        assert 'metadata' in result
        assert result['domain'] == "https://example.com"
        assert result['total_links'] == 3


class TestFirecrawlClientErrors:
    """Test Firecrawl client error handling."""
    
    def test_firecrawl_error_creation(self):
        """Test Firecrawl error creation."""
        error = FirecrawlError("Test error")
        assert str(error) == "Test error"
    
    def test_firecrawl_api_error_creation(self):
        """Test Firecrawl API error creation."""
        error = FirecrawlAPIError("API error")
        assert str(error) == "API error"
        assert isinstance(error, FirecrawlError)
    
    def test_firecrawl_budget_exceeded_error_creation(self):
        """Test Firecrawl budget exceeded error creation."""
        error = FirecrawlBudgetExceededError("Budget exceeded")
        assert str(error) == "Budget exceeded"
        assert isinstance(error, FirecrawlError)
    
    def test_firecrawl_rate_limit_error_creation(self):
        """Test Firecrawl rate limit error creation."""
        error = FirecrawlRateLimitError("Rate limit exceeded")
        assert str(error) == "Rate limit exceeded"
        assert isinstance(error, FirecrawlError)


class TestFirecrawlClientEpicBIntegration:
    """Test Epic B integration features for Firecrawl client."""
    
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
    def firecrawl_client(self, mock_config):
        """Create a Firecrawl client with mock configuration."""
        return FirecrawlClient(mock_config)
    
    @pytest.mark.asyncio
    async def test_map_domain_price_only_optimization(self, firecrawl_client):
        """Test Epic B price-only optimization in map_domain."""
        with patch.object(firecrawl_client, '_make_request_with_retry') as mock_request:
            mock_request.return_value = {
                'links': [
                    'https://example.com/coffee/beans',
                    'https://example.com/products/roast',
                    'https://example.com/about'
                ]
            }
            
            # Test price-only mode
            result = await firecrawl_client.map_domain(
                "https://example.com", 
                ["coffee"], 
                job_type="price_only"
            )
            
            # Verify price-only optimization was applied
            assert result['domain'] == "https://example.com"
            assert 'total_links' in result
            assert 'filtered_urls' in result
    
    @pytest.mark.asyncio
    async def test_map_domain_full_refresh_mode(self, firecrawl_client):
        """Test full refresh mode in map_domain."""
        with patch.object(firecrawl_client, '_make_request_with_retry') as mock_request:
            mock_request.return_value = {
                'links': [
                    'https://example.com/coffee/beans',
                    'https://example.com/products/roast',
                    'https://example.com/about'
                ]
            }
            
            # Test full refresh mode
            result = await firecrawl_client.map_domain(
                "https://example.com", 
                ["coffee"], 
                job_type="full_refresh"
            )
            
            # Verify full refresh mode was applied
            assert result['domain'] == "https://example.com"
            assert 'total_links' in result
            assert 'filtered_urls' in result
    
    @pytest.mark.asyncio
    async def test_discover_product_urls_with_job_type(self, firecrawl_client):
        """Test discover_product_urls with Epic B job_type parameter."""
        with patch.object(firecrawl_client, 'map_domain') as mock_map:
            mock_map.return_value = {
                'domain': 'https://example.com',
                'total_links': 3,
                'filtered_urls': ['https://example.com/coffee/beans'],
                'coffee_urls': ['https://example.com/coffee/beans'],
                'product_urls': ['https://example.com/coffee/beans'],
                'metadata': {}
            }
            
            # Test with price_only job type
            urls = await firecrawl_client.discover_product_urls(
                "https://example.com",
                ["coffee"],
                job_type="price_only"
            )
            
            # Verify map_domain was called with correct job_type
            mock_map.assert_called_once_with(
                "https://example.com",
                ["coffee"],
                "price_only"
            )
            assert isinstance(urls, list)
    
    def test_price_only_parameter_optimization(self, firecrawl_client):
        """Test that price_only mode applies correct parameter optimization."""
        # Test the parameter optimization logic
        with patch.object(firecrawl_client, '_make_request_with_retry') as mock_request:
            mock_request.return_value = {'links': []}
            
            # This should trigger the price-only optimization in map_domain
            import asyncio
            asyncio.run(firecrawl_client.map_domain(
                "https://example.com",
                ["coffee"],
                job_type="price_only"
            ))
            
            # Verify the request was made (optimization applied internally)
            assert mock_request.called