"""
Integration tests for price-only fetcher using real sample data.
Tests the complete workflow with actual Shopify and WooCommerce data.
"""

import json
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch
from decimal import Decimal

from src.fetcher.price_parser import PriceParser
from src.fetcher.price_fetcher import PriceFetcher
from src.fetcher.shopify_fetcher import ShopifyFetcher
from src.fetcher.woocommerce_fetcher import WooCommerceFetcher
from src.fetcher.base_fetcher import FetcherConfig
from src.config.fetcher_config import SourceConfig, RoasterConfig


class TestPriceOnlyIntegration:
    """Integration tests using real sample data."""
    
    @pytest.fixture
    def sample_data_dir(self):
        """Get the sample data directory."""
        return Path(__file__).parent.parent.parent / "data" / "samples"
    
    @pytest.fixture
    def shopify_sample_data(self, sample_data_dir):
        """Load Shopify sample data."""
        shopify_file = sample_data_dir / "shopify" / "bluetokaicoffee-shopify.json"
        with open(shopify_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    @pytest.fixture
    def woocommerce_sample_data(self, sample_data_dir):
        """Load WooCommerce sample data."""
        woo_file = sample_data_dir / "woocommerce" / "bababeans-woocommerce.json"
        with open(woo_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return FetcherConfig(
            timeout=30.0,
            max_retries=3,
            retry_delay=1.0,
        )
    
    @pytest.fixture
    def roaster_id(self):
        """Test roaster ID."""
        return "test_roaster"
    
    def test_shopify_price_parser_integration(self, shopify_sample_data):
        """Test price parser with real Shopify data."""
        parser = PriceParser(job_type="price_only")
        
        # Test with first product from sample data
        first_product = shopify_sample_data['products'][0]
        result = parser.extract_price_data(first_product)
        
        # Verify basic structure
        assert result is not None
        assert 'platform_product_id' in result
        assert 'variants' in result
        assert len(result['variants']) > 0
        
        # Verify variant data
        variant = result['variants'][0]
        assert 'platform_variant_id' in variant
        assert 'price_decimal' in variant
        assert 'currency' in variant
        assert 'in_stock' in variant
        
        # Verify price extraction
        assert isinstance(variant['price_decimal'], Decimal)
        assert variant['price_decimal'] > 0
        
        print(f"✅ Shopify parser extracted: {result['platform_product_id']} with {len(result['variants'])} variants")
    
    def test_woocommerce_price_parser_integration(self, woocommerce_sample_data):
        """Test price parser with real WooCommerce data."""
        parser = PriceParser(job_type="price_only")
        
        # Test with first product from sample data
        first_product = woocommerce_sample_data[0]
        result = parser.extract_price_data(first_product)
        
        # Verify basic structure
        assert result is not None
        assert 'platform_product_id' in result
        assert 'variants' in result
        assert len(result['variants']) > 0
        
        # Verify variant data
        variant = result['variants'][0]
        assert 'platform_variant_id' in variant
        assert 'price_decimal' in variant
        assert 'currency' in variant
        assert 'in_stock' in variant
        
        # Verify price extraction
        assert isinstance(variant['price_decimal'], Decimal)
        assert variant['price_decimal'] > 0
        
        print(f"✅ WooCommerce parser extracted: {result['platform_product_id']} with {len(result['variants'])} variants")
    
    def test_price_delta_detection_integration(self, shopify_sample_data):
        """Test price delta detection with real data."""
        parser = PriceParser(job_type="price_only")
        
        # Extract price data from sample
        sample_product = shopify_sample_data['products'][0]
        fetched_data = [parser.extract_price_data(sample_product)]
        
        # Create mock existing variants with different prices
        existing_variants = [
            {
                'platform_variant_id': str(fetched_data[0]['variants'][0]['platform_variant_id']),
                'price_current': 5000.00,  # Different price
                'currency': 'INR',
                'in_stock': True,
            }
        ]
        
        # Detect deltas
        deltas = parser.detect_price_deltas(fetched_data, existing_variants)
        
        # Should detect price change
        assert len(deltas) > 0
        delta = deltas[0]
        assert delta.variant_id == str(fetched_data[0]['variants'][0]['platform_variant_id'])
        assert delta.old_price != delta.new_price
        
        print(f"✅ Detected {len(deltas)} price deltas")
    
    @pytest.mark.asyncio
    async def test_shopify_fetcher_integration(self, config, roaster_id, shopify_sample_data):
        """Test Shopify fetcher with real sample data."""
        # Mock the fetcher to return sample data
        shopify_fetcher = ShopifyFetcher(
            config=config,
            roaster_id=roaster_id,
            base_url="https://test-shop.myshopify.com",
            job_type="price_only"
        )
        
        # Mock the fetch method to return sample data
        shopify_fetcher.fetch_products = AsyncMock(return_value=shopify_sample_data['products'])
        shopify_fetcher.test_connection = AsyncMock(return_value=True)
        
        # Create price fetcher
        price_fetcher = PriceFetcher(shopify_fetcher)
        
        # Test fetching price data
        result = await price_fetcher.fetch_price_data(limit=50, page=1)
        
        # Verify results
        assert result['success'] is True
        assert result['roaster_id'] == roaster_id
        assert result['platform'] == "shopify"
        assert result['job_type'] == "price_only"
        assert result['products_processed'] > 0
        assert result['price_data_extracted'] > 0
        
        # Verify price data structure
        price_data = result['price_data'][0]
        assert 'platform_product_id' in price_data
        assert 'variants' in price_data
        assert len(price_data['variants']) > 0
        
        print(f"✅ Shopify fetcher processed {result['products_processed']} products, extracted {result['price_data_extracted']} price records")
    
    @pytest.mark.asyncio
    async def test_woocommerce_fetcher_integration(self, config, roaster_id, woocommerce_sample_data):
        """Test WooCommerce fetcher with real sample data."""
        # Mock the fetcher to return sample data
        woo_fetcher = WooCommerceFetcher(
            config=config,
            roaster_id=roaster_id,
            base_url="https://test-store.com",
            job_type="price_only"
        )
        
        # Mock the fetch method to return sample data
        woo_fetcher.fetch_products = AsyncMock(return_value=woocommerce_sample_data)
        woo_fetcher.test_connection = AsyncMock(return_value=True)
        
        # Create price fetcher
        price_fetcher = PriceFetcher(woo_fetcher)
        
        # Test fetching price data
        result = await price_fetcher.fetch_price_data(limit=50, page=1)
        
        # Verify results
        assert result['success'] is True
        assert result['roaster_id'] == roaster_id
        assert result['platform'] == "woocommerce"
        assert result['job_type'] == "price_only"
        assert result['products_processed'] > 0
        assert result['price_data_extracted'] > 0
        
        # Verify price data structure
        price_data = result['price_data'][0]
        assert 'platform_product_id' in price_data
        assert 'variants' in price_data
        assert len(price_data['variants']) > 0
        
        print(f"✅ WooCommerce fetcher processed {result['products_processed']} products, extracted {result['price_data_extracted']} price records")
    
    def test_performance_metrics_integration(self, shopify_sample_data):
        """Test performance metrics with real data."""
        parser = PriceParser(job_type="price_only")
        
        # Process multiple products
        products = shopify_sample_data['products'][:5]  # First 5 products
        
        for product in products:
            parser.extract_price_data(product)
        
        # Get performance metrics
        metrics = parser.get_performance_metrics()
        
        # Verify metrics
        assert 'job_type' in metrics
        assert 'parser_version' in metrics
        assert 'price_fields' in metrics
        assert metrics['job_type'] == 'price_only'
        
        print(f"✅ Performance metrics: {metrics}")
    
    @pytest.mark.asyncio
    async def test_error_handling_integration(self, config, roaster_id):
        """Test error handling with real fetcher."""
        # Create fetcher that will fail
        shopify_fetcher = ShopifyFetcher(
            config=config,
            roaster_id=roaster_id,
            base_url="https://test-shop.myshopify.com",
            job_type="price_only"
        )
        
        # Mock error in fetch
        shopify_fetcher.fetch_products = AsyncMock(side_effect=Exception("API Error"))
        shopify_fetcher.test_connection = AsyncMock(return_value=True)
        
        price_fetcher = PriceFetcher(shopify_fetcher)
        
        # Test error handling
        result = await price_fetcher.fetch_price_data(limit=50, page=1)
        
        # Should handle error gracefully
        assert result['success'] is False
        assert 'error' in result
        assert result['error'] == "API Error"
        
        print(f"✅ Error handling: {result['error']}")
    
    def test_multiple_products_price_only(self, shopify_sample_data):
        """Test price-only processing with multiple products."""
        parser = PriceParser(job_type="price_only")
        
        # Process first 3 products
        products = shopify_sample_data['products'][:3]
        results = []
        
        for product in products:
            result = parser.extract_price_data(product)
            if result and result.get('variants'):
                results.append(result)
        
        # Verify results
        assert len(results) > 0
        assert all('platform_product_id' in r for r in results)
        assert all('variants' in r for r in results)
        
        total_variants = sum(len(r['variants']) for r in results)
        print(f"✅ Processed {len(results)} products with {total_variants} total variants")
    
    def test_empty_results_handling(self):
        """Test handling of empty results."""
        parser = PriceParser(job_type="price_only")
        
        # Test with empty product data
        empty_product = {'id': 123, 'title': 'Empty Product', 'variants': []}
        result = parser.extract_price_data(empty_product)
        
        # Should handle empty variants gracefully
        assert result is not None
        assert result['variants'] == []
        
        print("✅ Empty results handled gracefully")
    
    def test_currency_handling_integration(self, shopify_sample_data, woocommerce_sample_data):
        """Test currency handling with real data."""
        parser = PriceParser(job_type="price_only")
        
        # Test Shopify currency (should be INR based on sample)
        shopify_product = shopify_sample_data['products'][0]
        shopify_result = parser.extract_price_data(shopify_product)
        
        # Test WooCommerce currency
        woo_product = woocommerce_sample_data[0]
        woo_result = parser.extract_price_data(woo_product)
        
        # Verify currencies are extracted
        assert shopify_result['variants'][0]['currency'] in ['INR', 'USD']
        assert woo_result['variants'][0]['currency'] in ['INR', 'USD']
        
        print(f"✅ Currencies: Shopify={shopify_result['variants'][0]['currency']}, WooCommerce={woo_result['variants'][0]['currency']}")
    
    def test_availability_parsing_integration(self, shopify_sample_data):
        """Test availability parsing with real data."""
        parser = PriceParser(job_type="price_only")
        
        # Test with sample product
        product = shopify_sample_data['products'][0]
        result = parser.extract_price_data(product)
        
        # Verify availability is parsed correctly
        variant = result['variants'][0]
        assert 'in_stock' in variant
        assert isinstance(variant['in_stock'], bool)
        
        print(f"✅ Availability parsed: {variant['in_stock']}")
    
    def test_weight_parsing_integration(self, shopify_sample_data):
        """Test weight parsing with real data."""
        parser = PriceParser(job_type="price_only")
        
        # Test with sample product
        product = shopify_sample_data['products'][0]
        result = parser.extract_price_data(product)
        
        # Verify weight is parsed if available
        variant = result['variants'][0]
        if 'weight_grams' in variant:
            assert isinstance(variant['weight_grams'], (int, float))
            print(f"✅ Weight parsed: {variant['weight_grams']}g")
        else:
            print("✅ Weight not available in sample data (expected)")