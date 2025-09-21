"""
Tests for WooCommerce fetcher implementation.
"""

import pytest
import asyncio
import json
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import Response

from src.fetcher.woocommerce_fetcher import WooCommerceFetcher
from src.fetcher.base_fetcher import FetcherConfig


class TestWooCommerceFetcher:
    """Test cases for WooCommerceFetcher."""
    
    @pytest.fixture
    def fetcher_config(self):
        """Create a test fetcher configuration."""
        return FetcherConfig(
            timeout=10.0,
            max_retries=2,
            retry_delay=0.1,
            politeness_delay=0.1,
            jitter_range=0.05,
            max_concurrent=2,
        )
    
    @pytest.fixture
    def woocommerce_fetcher(self, fetcher_config):
        """Create a test WooCommerce fetcher."""
        return WooCommerceFetcher(
            config=fetcher_config,
            roaster_id="test-roaster",
            base_url="https://test-store.com",
            consumer_key="test-key",
            consumer_secret="test-secret",
        )
    
    @pytest.fixture
    def mock_woocommerce_response(self):
        """Mock WooCommerce API response."""
        return [
            {
                "id": 1,
                "name": "Test Coffee",
                "slug": "test-coffee",
                "variations": [
                    {
                        "id": 1,
                        "name": "250g",
                        "price": "15.00",
                        "stock_quantity": 10
                    }
                ]
            }
        ]
    
    @pytest.mark.asyncio
    async def test_fetch_products_success(self, woocommerce_fetcher, mock_woocommerce_response):
        """Test successful product fetching."""
        with patch.object(woocommerce_fetcher, '_make_request') as mock_request:
            mock_request.return_value = (
                200,
                {'content-type': 'application/json'},
                json.dumps(mock_woocommerce_response).encode()
            )
            
            products = await woocommerce_fetcher.fetch_products(limit=50, page=1)
            
            assert len(products) == 1
            assert products[0]['name'] == "Test Coffee"
            assert products[0]['slug'] == "test-coffee"
            
            # Verify request was made with correct parameters
            mock_request.assert_called_once()
            call_args = mock_request.call_args
            params = call_args[1]['params']
            assert params['per_page'] == 50
            assert params['page'] == 1
    
    @pytest.mark.asyncio
    async def test_fetch_products_with_filters(self, woocommerce_fetcher, mock_woocommerce_response):
        """Test product fetching with date filters."""
        with patch.object(woocommerce_fetcher, '_make_request') as mock_request:
            mock_request.return_value = (
                200,
                {'content-type': 'application/json'},
                json.dumps(mock_woocommerce_response).encode()
            )
            
            products = await woocommerce_fetcher.fetch_products(
                limit=50,
                page=1,
                after="2024-01-01T00:00:00Z",
                before="2024-12-31T23:59:59Z"
            )
            
            assert len(products) == 1
            
            # Verify filters were included in request
            call_args = mock_request.call_args
            params = call_args[1]['params']
            assert params['after'] == "2024-01-01T00:00:00Z"
            assert params['before'] == "2024-12-31T23:59:59Z"
    
    @pytest.mark.asyncio
    async def test_fetch_products_authentication_failed(self, woocommerce_fetcher):
        """Test handling of authentication failures."""
        with patch.object(woocommerce_fetcher, '_make_request') as mock_request:
            mock_request.return_value = (
                401,
                {'content-type': 'application/json'},
                b'Unauthorized'
            )
            
            products = await woocommerce_fetcher.fetch_products(limit=50, page=1)
            
            assert products == []
    
    @pytest.mark.asyncio
    async def test_fetch_products_rate_limit(self, woocommerce_fetcher):
        """Test handling of rate limit responses."""
        with patch.object(woocommerce_fetcher, '_make_request') as mock_request:
            mock_request.return_value = (
                429,
                {'retry-after': '60'},
                b'Rate limit exceeded'
            )
            
            products = await woocommerce_fetcher.fetch_products(limit=50, page=1)
            
            assert products == []
    
    @pytest.mark.asyncio
    async def test_fetch_products_error_response(self, woocommerce_fetcher):
        """Test handling of error responses."""
        with patch.object(woocommerce_fetcher, '_make_request') as mock_request:
            mock_request.return_value = (
                500,
                {'content-type': 'application/json'},
                b'Internal server error'
            )
            
            products = await woocommerce_fetcher.fetch_products(limit=50, page=1)
            
            assert products == []
    
    @pytest.mark.asyncio
    async def test_fetch_all_products_pagination(self, woocommerce_fetcher):
        """Test fetching all products with pagination."""
        # Mock responses for multiple pages - need to simulate full pages to continue pagination
        page1_response = [{"id": 1, "name": "Product 1"}] * 100  # Full page
        page2_response = [{"id": 2, "name": "Product 2"}] * 100  # Full page
        page3_response = []  # Empty page indicates end
        
        with patch.object(woocommerce_fetcher, '_make_request') as mock_request:
            mock_request.side_effect = [
                (200, {}, json.dumps(page1_response).encode()),
                (200, {}, json.dumps(page2_response).encode()),
                (200, {}, json.dumps(page3_response).encode()),
            ]
            
            products = await woocommerce_fetcher.fetch_all_products()
            
            assert len(products) == 200  # 100 + 100
            assert products[0]['name'] == "Product 1"
            assert products[100]['name'] == "Product 2"
            
            # Verify pagination parameters were used
            assert mock_request.call_count == 3
            calls = mock_request.call_args_list
            
            # Check that page parameter was incremented
            assert calls[0][1]['params']['page'] == 1
            assert calls[1][1]['params']['page'] == 2
            assert calls[2][1]['params']['page'] == 3
    
    @pytest.mark.asyncio
    async def test_fetch_all_products_safety_limit(self, woocommerce_fetcher):
        """Test that pagination stops at safety limit."""
        with patch.object(woocommerce_fetcher, '_make_request') as mock_request:
            # Mock response that always has full pages (to test safety limit)
            mock_response = [{"id": 1, "name": "Product"}] * 100  # Full page
            mock_request.return_value = (
                200,
                {'content-type': 'application/json'},
                json.dumps(mock_response).encode()
            )
            
            products = await woocommerce_fetcher.fetch_all_products()
            
            # Should stop at safety limit (1000 pages)
            assert mock_request.call_count == 1000
            assert len(products) == 100000  # 100 * 1000
    
    @pytest.mark.asyncio
    async def test_get_product_count(self, woocommerce_fetcher):
        """Test getting product count."""
        mock_response = [{"id": 1, "name": "Product"}]
        
        with patch.object(woocommerce_fetcher, '_make_request') as mock_request:
            mock_request.return_value = (
                200,
                {'content-type': 'application/json', 'X-WP-Total': '5'},
                json.dumps(mock_response).encode()
            )
            
            count = await woocommerce_fetcher.get_product_count()
            
            assert count == 5  # From X-WP-Total header
    
    @pytest.mark.asyncio
    async def test_get_product_count_fallback(self, woocommerce_fetcher):
        """Test getting product count when header is missing."""
        mock_response = [{"id": 1, "name": "Product"}]
        
        with patch.object(woocommerce_fetcher, '_make_request') as mock_request:
            mock_request.return_value = (
                200,
                {'content-type': 'application/json'},  # No X-WP-Total header
                json.dumps(mock_response).encode()
            )
            
            count = await woocommerce_fetcher.get_product_count()
            
            assert count == 1  # Fallback to response length
    
    @pytest.mark.asyncio
    async def test_test_connection_success(self, woocommerce_fetcher):
        """Test successful connection test."""
        with patch.object(woocommerce_fetcher, '_make_request') as mock_request:
            mock_request.return_value = (
                200,
                {'content-type': 'application/json'},
                json.dumps([]).encode()
            )
            
            success = await woocommerce_fetcher.test_connection()
            
            assert success is True
    
    @pytest.mark.asyncio
    async def test_test_connection_failure(self, woocommerce_fetcher):
        """Test failed connection test."""
        with patch.object(woocommerce_fetcher, '_make_request') as mock_request:
            mock_request.return_value = (
                401,
                {'content-type': 'application/json'},
                b'Unauthorized'
            )
            
            success = await woocommerce_fetcher.test_connection()
            
            assert success is False
    
    @pytest.mark.asyncio
    async def test_limit_enforcement(self, woocommerce_fetcher):
        """Test that limit is enforced to WooCommerce maximum."""
        with patch.object(woocommerce_fetcher, '_make_request') as mock_request:
            mock_request.return_value = (
                200,
                {'content-type': 'application/json'},
                json.dumps([]).encode()
            )
            
            # Try to fetch more than WooCommerce's max limit
            await woocommerce_fetcher.fetch_products(limit=200, page=1)
            
            # Verify limit was capped at 100
            call_args = mock_request.call_args
            assert call_args[1]['params']['per_page'] == 100
    
    @pytest.mark.asyncio
    async def test_json_decode_error(self, woocommerce_fetcher):
        """Test handling of invalid JSON response."""
        with patch.object(woocommerce_fetcher, '_make_request') as mock_request:
            mock_request.return_value = (
                200,
                {'content-type': 'application/json'},
                b'Invalid JSON'
            )
            
            products = await woocommerce_fetcher.fetch_products(limit=50, page=1)
            
            assert products == []
    
    def test_initialization_with_consumer_key(self, fetcher_config):
        """Test fetcher initialization with consumer key/secret."""
        fetcher = WooCommerceFetcher(
            config=fetcher_config,
            roaster_id="test-roaster",
            base_url="https://test-store.com",
            consumer_key="test-key",
            consumer_secret="test-secret",
        )
        
        assert fetcher.roaster_id == "test-roaster"
        assert fetcher.base_url == "https://test-store.com"
        assert fetcher.platform == "woocommerce"
        assert fetcher.consumer_key == "test-key"
        assert fetcher.consumer_secret == "test-secret"
        
        # Verify politeness delay was set for WooCommerce
        assert fetcher.config.politeness_delay == 0.1
    
    def test_initialization_with_jwt(self, fetcher_config):
        """Test fetcher initialization with JWT token."""
        fetcher = WooCommerceFetcher(
            config=fetcher_config,
            roaster_id="test-roaster",
            base_url="https://test-store.com",
            jwt_token="test-jwt-token",
        )
        
        assert fetcher.roaster_id == "test-roaster"
        assert fetcher.base_url == "https://test-store.com"
        assert fetcher.platform == "woocommerce"
        assert fetcher.jwt_token == "test-jwt-token"
        assert fetcher.consumer_key is None
        assert fetcher.consumer_secret is None
