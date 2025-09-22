"""
Tests for price fetcher functionality.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from src.fetcher.price_fetcher import PriceFetcher
from src.fetcher.price_parser import PriceParser, PriceDelta
from src.fetcher.base_fetcher import BaseFetcher, FetcherConfig


class MockBaseFetcher(BaseFetcher):
    """Mock base fetcher for testing."""
    
    def __init__(self, roaster_id="test_roaster", platform="shopify", job_type="price_only"):
        config = FetcherConfig()
        super().__init__(config, roaster_id, "https://test.com", platform, job_type)
        self._mock_products = []
        self._mock_endpoint_available = True
    
    async def fetch_products(self, limit=50, page=1, **kwargs):
        """Mock fetch_products method."""
        return self._mock_products
    
    async def fetch_all_products(self, **kwargs):
        """Mock fetch_all_products method."""
        return self._mock_products
    
    async def fetch_price_only_products(self, limit=50, page=1, **kwargs):
        """Mock fetch_price_only_products method."""
        return self._mock_products
    
    async def fetch_price_only_all_products(self, **kwargs):
        """Mock fetch_price_only_all_products method."""
        return self._mock_products
    
    def _build_products_url(self):
        """Mock _build_products_url method."""
        return "https://test.com/products.json"
    
    async def _make_request(self, url, params=None, use_cache=True):
        """Mock _make_request method."""
        if self._mock_endpoint_available:
            return 200, {}, b'{"products": []}'
        else:
            return 404, {}, b'{"error": "Not found"}'
    
    async def test_connection(self):
        """Mock test_connection method."""
        return True


class TestPriceFetcher:
    """Test cases for PriceFetcher class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.base_fetcher = MockBaseFetcher()
        self.price_fetcher = PriceFetcher(self.base_fetcher)
    
    def test_initialization(self):
        """Test price fetcher initialization."""
        assert self.price_fetcher.roaster_id == "test_roaster"
        assert self.price_fetcher.platform == "shopify"
        assert self.price_fetcher.job_type == "price_only"
        assert isinstance(self.price_fetcher.price_parser, PriceParser)
    
    @pytest.mark.asyncio
    async def test_fetch_price_data_success(self):
        """Test successful price data fetching."""
        # Mock products data
        self.base_fetcher._mock_products = [
            {
                'id': 12345,
                'title': 'Test Coffee',
                'variants': [
                    {
                        'id': 67890,
                        'price': '25.99',
                        'available': True,
                        'sku': 'TEST-001',
                    }
                ]
            }
        ]
        
        result = await self.price_fetcher.fetch_price_data(limit=50, page=1)
        
        assert result['success'] is True
        assert result['roaster_id'] == "test_roaster"
        assert result['platform'] == "shopify"
        assert result['job_type'] == "price_only"
        assert result['products_processed'] == 1
        assert result['price_data_extracted'] == 1
        assert len(result['price_data']) == 1
    
    @pytest.mark.asyncio
    async def test_fetch_price_data_endpoint_unavailable(self):
        """Test price data fetching when endpoint is unavailable."""
        # Mock endpoint as unavailable
        self.base_fetcher._mock_endpoint_available = False
        
        result = await self.price_fetcher.fetch_price_data(limit=50, page=1)
        
        # Should still succeed but with fallback
        assert result['success'] is True
        assert result['products_processed'] == 0  # No products from fallback
    
    @pytest.mark.asyncio
    async def test_fetch_price_data_error(self):
        """Test price data fetching with error."""
        # Mock an error in the base fetcher
        async def mock_fetch_error(*args, **kwargs):
            raise Exception("Test error")
        
        self.base_fetcher.fetch_products = mock_fetch_error
        
        result = await self.price_fetcher.fetch_price_data(limit=50, page=1)
        
        assert result['success'] is False
        assert 'error' in result
        assert result['error'] == "Test error"
    
    @pytest.mark.asyncio
    async def test_check_list_endpoint_availability_success(self):
        """Test successful endpoint availability check."""
        self.base_fetcher._mock_endpoint_available = True
        
        is_available = await self.price_fetcher._check_list_endpoint_availability()
        
        assert is_available is True
    
    @pytest.mark.asyncio
    async def test_check_list_endpoint_availability_failure(self):
        """Test failed endpoint availability check."""
        self.base_fetcher._mock_endpoint_available = False
        
        is_available = await self.price_fetcher._check_list_endpoint_availability()
        
        assert is_available is False
    
    @pytest.mark.asyncio
    async def test_fetch_from_list_endpoint(self):
        """Test fetching from list endpoint."""
        self.base_fetcher._mock_products = [
            {'id': 1, 'title': 'Product 1'},
            {'id': 2, 'title': 'Product 2'},
        ]
        
        products = await self.price_fetcher._fetch_from_list_endpoint(limit=50, page=1)
        
        assert len(products) == 2
        assert products[0]['id'] == 1
        assert products[1]['id'] == 2
    
    @pytest.mark.asyncio
    async def test_fetch_per_product_no_handles(self):
        """Test per-product fetching with no existing handles."""
        # Mock empty product handles
        with patch.object(self.price_fetcher, '_get_existing_product_handles', return_value=[]):
            products = await self.price_fetcher._fetch_per_product()
            
            assert products == []
    
    @pytest.mark.asyncio
    async def test_fetch_per_product_with_handles(self):
        """Test per-product fetching with existing handles."""
        # Mock product handles
        handles = ['product-1', 'product-2']
        
        with patch.object(self.price_fetcher, '_get_existing_product_handles', return_value=handles):
            with patch.object(self.price_fetcher, '_fetch_single_product', return_value={'id': 1}):
                products = await self.price_fetcher._fetch_per_product()
                
                assert len(products) == 2
                assert products[0]['id'] == 1
                assert products[1]['id'] == 1
    
    @pytest.mark.asyncio
    async def test_fetch_single_product_shopify(self):
        """Test fetching single product from Shopify."""
        self.base_fetcher.platform = "shopify"
        
        with patch.object(self.base_fetcher, '_make_request', return_value=(200, {}, b'{"product": {"id": 123}}')):
            product = await self.price_fetcher._fetch_single_product("test-handle")
            
            assert product == {"id": 123}
    
    @pytest.mark.asyncio
    async def test_fetch_single_product_woocommerce(self):
        """Test fetching single product from WooCommerce."""
        self.base_fetcher.platform = "woocommerce"
        
        with patch.object(self.base_fetcher, '_make_request', return_value=(200, {}, b'{"id": 456}')):
            product = await self.price_fetcher._fetch_single_product("test-handle")
            
            assert product == {"id": 456}
    
    @pytest.mark.asyncio
    async def test_fetch_single_product_error(self):
        """Test fetching single product with error."""
        with patch.object(self.base_fetcher, '_make_request', return_value=(404, {}, b'{"error": "Not found"}')):
            product = await self.price_fetcher._fetch_single_product("test-handle")
            
            assert product is None
    
    @pytest.mark.asyncio
    async def test_detect_and_report_deltas(self):
        """Test detecting and reporting price deltas."""
        # Mock fetched data
        fetched_data = [
            {
                'platform_product_id': '12345',
                'variants': [
                    {
                        'platform_variant_id': '67890',
                        'price_decimal': 29.99,
                        'currency': 'USD',
                        'in_stock': True,
                        'sku': 'TEST-001',
                    }
                ]
            }
        ]
        
        # Mock existing variants
        existing_variants = [
            {
                'platform_variant_id': '67890',
                'price_current': 25.99,
                'currency': 'USD',
                'in_stock': True,
            }
        ]
        
        deltas = await self.price_fetcher.detect_and_report_deltas(fetched_data, existing_variants)
        
        assert len(deltas) == 1
        assert deltas[0].variant_id == '67890'
        assert float(deltas[0].old_price) == 25.99
        assert float(deltas[0].new_price) == 29.99
    
    @pytest.mark.asyncio
    async def test_detect_and_report_deltas_error(self):
        """Test detecting deltas with error."""
        # Mock parser to raise error
        with patch.object(self.price_fetcher.price_parser, 'detect_price_deltas', side_effect=Exception("Test error")):
            deltas = await self.price_fetcher.detect_and_report_deltas([], [])
            
            assert deltas == []
    
    def test_get_performance_metrics(self):
        """Test getting performance metrics."""
        metrics = self.price_fetcher.get_performance_metrics()
        
        assert metrics['roaster_id'] == "test_roaster"
        assert metrics['platform'] == "shopify"
        assert metrics['job_type'] == "price_only"
        assert 'parser_metrics' in metrics
    
    @pytest.mark.asyncio
    async def test_get_existing_product_handles(self):
        """Test getting existing product handles."""
        # This is a placeholder implementation
        handles = await self.price_fetcher._get_existing_product_handles()
        
        assert handles == []  # Placeholder returns empty list
    
    def test_price_fetcher_with_custom_parser(self):
        """Test price fetcher with custom parser."""
        custom_parser = PriceParser(job_type="custom")
        fetcher = PriceFetcher(self.base_fetcher, custom_parser)
        
        assert fetcher.price_parser.job_type == "custom"
    
    @pytest.mark.asyncio
    async def test_fetch_price_data_with_different_job_types(self):
        """Test fetching with different job types."""
        # Test with full_refresh job type
        self.base_fetcher.job_type = "full_refresh"
        fetcher = PriceFetcher(self.base_fetcher)
        
        result = await fetcher.fetch_price_data(limit=50, page=1)
        
        # Should still work but use regular fetch methods
        assert result['success'] is True
        assert result['job_type'] == "full_refresh"
