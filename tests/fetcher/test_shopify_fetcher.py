"""
Tests for Shopify fetcher implementation.
"""

import pytest
import asyncio
import json
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import Response

from src.fetcher.shopify_fetcher import ShopifyFetcher
from src.fetcher.base_fetcher import FetcherConfig


class TestShopifyFetcher:
    """Test cases for ShopifyFetcher."""
    
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
    def shopify_fetcher(self, fetcher_config):
        """Create a test Shopify fetcher."""
        return ShopifyFetcher(
            config=fetcher_config,
            roaster_id="test-roaster",
            base_url="https://test-shop.myshopify.com",
            api_key="test-api-key",
        )
    
    @pytest.fixture
    def mock_shopify_response(self):
        """Mock Shopify API response."""
        return {
            "products": [
                {
                    "id": 1,
                    "title": "Test Coffee",
                    "handle": "test-coffee",
                    "variants": [
                        {
                            "id": 1,
                            "title": "250g",
                            "price": "15.00",
                            "inventory_quantity": 10
                        }
                    ]
                }
            ]
        }
    
    @pytest.mark.asyncio
    async def test_fetch_products_success(self, shopify_fetcher, mock_shopify_response):
        """Test successful product fetching."""
        with patch.object(shopify_fetcher, '_make_request') as mock_request:
            mock_request.return_value = (
                200,
                {'content-type': 'application/json'},
                json.dumps(mock_shopify_response).encode()
            )
            
            products = await shopify_fetcher.fetch_products(limit=50, page=1)
            
            assert len(products) == 1
            assert products[0]['title'] == "Test Coffee"
            assert products[0]['handle'] == "test-coffee"
            
            # Verify request was made with correct parameters
            mock_request.assert_called_once()
            call_args = mock_request.call_args
            params = call_args[1]['params']
            assert params['limit'] == 50
            assert params['page'] == 1
    
    @pytest.mark.asyncio
    async def test_fetch_products_with_filters(self, shopify_fetcher, mock_shopify_response):
        """Test product fetching with date filters."""
        with patch.object(shopify_fetcher, '_make_request') as mock_request:
            mock_request.return_value = (
                200,
                {'content-type': 'application/json'},
                json.dumps(mock_shopify_response).encode()
            )
            
            products = await shopify_fetcher.fetch_products(
                limit=50,
                page=1,
                created_at_min="2024-01-01T00:00:00Z",
                updated_at_min="2024-01-01T00:00:00Z"
            )
            
            assert len(products) == 1
            
            # Verify filters were included in request
            call_args = mock_request.call_args
            params = call_args[1]['params']
            assert params['created_at_min'] == "2024-01-01T00:00:00Z"
            assert params['updated_at_min'] == "2024-01-01T00:00:00Z"
    
    @pytest.mark.asyncio
    async def test_fetch_products_rate_limit(self, shopify_fetcher):
        """Test handling of rate limit responses."""
        with patch.object(shopify_fetcher, '_make_request') as mock_request:
            mock_request.return_value = (
                429,
                {'retry-after': '60'},
                b'Rate limit exceeded'
            )
            
            products = await shopify_fetcher.fetch_products(limit=50, page=1)
            
            assert products == []
    
    @pytest.mark.asyncio
    async def test_fetch_products_error_response(self, shopify_fetcher):
        """Test handling of error responses."""
        with patch.object(shopify_fetcher, '_make_request') as mock_request:
            mock_request.return_value = (
                500,
                {'content-type': 'application/json'},
                b'Internal server error'
            )
            
            products = await shopify_fetcher.fetch_products(limit=50, page=1)
            
            assert products == []
    
    @pytest.mark.asyncio
    async def test_fetch_all_products_pagination(self, shopify_fetcher):
        """Test fetching all products with pagination."""
        # Mock responses for multiple pages - need to simulate full pages to continue pagination
        page1_response = {
            "products": [{"id": 1, "title": "Product 1"}] * 250  # Full page
        }
        page2_response = {
            "products": [{"id": 2, "title": "Product 2"}] * 250  # Full page
        }
        page3_response = {
            "products": []  # Empty page indicates end
        }
        
        with patch.object(shopify_fetcher, '_make_request') as mock_request:
            mock_request.side_effect = [
                (200, {}, json.dumps(page1_response).encode()),
                (200, {}, json.dumps(page2_response).encode()),
                (200, {}, json.dumps(page3_response).encode()),
            ]
            
            products = await shopify_fetcher.fetch_all_products()
            
            assert len(products) == 500  # 250 + 250
            assert products[0]['title'] == "Product 1"
            assert products[250]['title'] == "Product 2"
            
            # Verify pagination parameters were used
            assert mock_request.call_count == 3
            calls = mock_request.call_args_list
            
            # Check that page parameter was incremented
            assert calls[0][1]['params']['page'] == 1
            assert calls[1][1]['params']['page'] == 2
            assert calls[2][1]['params']['page'] == 3
    
    @pytest.mark.asyncio
    async def test_fetch_all_products_safety_limit(self, shopify_fetcher):
        """Test that pagination stops at safety limit."""
        with patch.object(shopify_fetcher, '_make_request') as mock_request:
            # Mock response that always has full pages (to test safety limit)
            mock_response = {
                "products": [{"id": 1, "title": "Product"}] * 250  # Full page
            }
            mock_request.return_value = (
                200,
                {'content-type': 'application/json'},
                json.dumps(mock_response).encode()
            )
            
            products = await shopify_fetcher.fetch_all_products()
            
            # Should stop at safety limit (1000 pages)
            assert mock_request.call_count == 1000
            assert len(products) == 250000  # 250 * 1000
    
    @pytest.mark.asyncio
    async def test_get_product_count(self, shopify_fetcher):
        """Test getting product count."""
        mock_response = {
            "products": [{"id": 1, "title": "Product"}]
        }
        
        with patch.object(shopify_fetcher, '_make_request') as mock_request:
            mock_request.return_value = (
                200,
                {'content-type': 'application/json'},
                json.dumps(mock_response).encode()
            )
            
            count = await shopify_fetcher.get_product_count()
            
            assert count == 1
            
            # Verify request was made with limit=1
            call_args = mock_request.call_args
            assert call_args[1]['params']['limit'] == 1
    
    @pytest.mark.asyncio
    async def test_test_connection_success(self, shopify_fetcher):
        """Test successful connection test."""
        with patch.object(shopify_fetcher, '_make_request') as mock_request:
            mock_request.return_value = (
                200,
                {'content-type': 'application/json'},
                json.dumps({"products": []}).encode()
            )
            
            success = await shopify_fetcher.test_connection()
            
            assert success is True
    
    @pytest.mark.asyncio
    async def test_test_connection_failure(self, shopify_fetcher):
        """Test failed connection test."""
        with patch.object(shopify_fetcher, '_make_request') as mock_request:
            mock_request.return_value = (
                401,
                {'content-type': 'application/json'},
                b'Unauthorized'
            )
            
            success = await shopify_fetcher.test_connection()
            
            assert success is False
    
    @pytest.mark.asyncio
    async def test_limit_enforcement(self, shopify_fetcher):
        """Test that limit is enforced to Shopify maximum."""
        with patch.object(shopify_fetcher, '_make_request') as mock_request:
            mock_request.return_value = (
                200,
                {'content-type': 'application/json'},
                json.dumps({"products": []}).encode()
            )
            
            # Try to fetch more than Shopify's max limit
            await shopify_fetcher.fetch_products(limit=500, page=1)
            
            # Verify limit was capped at 250
            call_args = mock_request.call_args
            assert call_args[1]['params']['limit'] == 250
    
    @pytest.mark.asyncio
    async def test_json_decode_error(self, shopify_fetcher):
        """Test handling of invalid JSON response."""
        with patch.object(shopify_fetcher, '_make_request') as mock_request:
            mock_request.return_value = (
                200,
                {'content-type': 'application/json'},
                b'Invalid JSON'
            )
            
            products = await shopify_fetcher.fetch_products(limit=50, page=1)
            
            assert products == []
    
    def test_initialization(self, fetcher_config):
        """Test fetcher initialization."""
        fetcher = ShopifyFetcher(
            config=fetcher_config,
            roaster_id="test-roaster",
            base_url="https://test-shop.myshopify.com",
            api_key="test-api-key",
        )
        
        assert fetcher.roaster_id == "test-roaster"
        assert fetcher.base_url == "https://test-shop.myshopify.com"
        assert fetcher.platform == "shopify"
        assert fetcher.api_key == "test-api-key"
        
        # Verify politeness delay was set for Shopify
        assert fetcher.config.politeness_delay == 0.5
