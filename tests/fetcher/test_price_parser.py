"""
Tests for price parser functionality.
"""

import pytest
from decimal import Decimal
from datetime import datetime, timezone

from src.fetcher.price_parser import PriceParser, PriceDelta


class TestPriceParser:
    """Test cases for PriceParser class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.parser = PriceParser(job_type="price_only")
    
    def test_parser_initialization(self):
        """Test parser initialization."""
        assert self.parser.job_type == "price_only"
        assert self.parser.price_fields == ["price", "availability", "sku", "weight"]
    
    def test_extract_price_data_shopify(self):
        """Test extracting price data from Shopify product."""
        shopify_product = {
            'id': 12345,
            'title': 'Test Coffee',
            'variants': [
                {
                    'id': 67890,
                    'price': '25.99',
                    'compare_at_price': '29.99',
                    'available': True,
                    'sku': 'TEST-001',
                    'weight': 250,
                    'weight_unit': 'g',
                }
            ]
        }
        
        result = self.parser.extract_price_data(shopify_product)
        
        assert result['platform_product_id'] == '12345'
        assert len(result['variants']) == 1
        
        variant = result['variants'][0]
        assert variant['platform_variant_id'] == '67890'
        assert variant['price_decimal'] == Decimal('25.99')
        assert variant['currency'] == 'USD'
        assert variant['in_stock'] is True
        assert variant['sku'] == 'TEST-001'
        assert variant['weight_g'] == 250.0
    
    def test_extract_price_data_woocommerce(self):
        """Test extracting price data from WooCommerce product."""
        woo_product = {
            'id': 54321,
            'title': 'Test Coffee Woo',
            'variations': [
                {
                    'id': 98765,
                    'price': '24.50',
                    'regular_price': '24.50',
                    'sale_price': None,
                    'stock_status': 'instock',
                    'sku': 'WOO-001',
                    'weight': '250',
                }
            ]
        }
        
        result = self.parser.extract_price_data(woo_product)
        
        assert result['platform_product_id'] == '54321'
        assert len(result['variants']) == 1
        
        variant = result['variants'][0]
        assert variant['platform_variant_id'] == '98765'
        assert variant['price_decimal'] == Decimal('24.50')
        assert variant['currency'] == 'USD'
        assert variant['in_stock'] is True
        assert variant['sku'] == 'WOO-001'
        assert variant['weight_g'] == 250.0
    
    def test_extract_price_data_missing_variants(self):
        """Test handling products without variants."""
        product_no_variants = {
            'id': 11111,
            'title': 'No Variants Product',
            'variants': []
        }
        
        result = self.parser.extract_price_data(product_no_variants)
        
        assert result['platform_product_id'] == '11111'
        assert result['variants'] == []
    
    def test_extract_price_data_invalid_price(self):
        """Test handling invalid price data."""
        product_invalid_price = {
            'id': 22222,
            'title': 'Invalid Price Product',
            'variants': [
                {
                    'id': 33333,
                    'price': 'invalid',
                    'available': True,
                    'sku': 'INVALID-001',
                }
            ]
        }
        
        result = self.parser.extract_price_data(product_invalid_price)
        
        # Should handle invalid price gracefully
        assert result['platform_product_id'] == '22222'
        assert len(result['variants']) == 0  # Invalid variant should be filtered out
    
    def test_detect_price_deltas_no_changes(self):
        """Test detecting no price changes."""
        fetched_products = [
            {
                'platform_product_id': '12345',
                'variants': [
                    {
                        'platform_variant_id': '67890',
                        'price_decimal': Decimal('25.99'),
                        'currency': 'USD',
                        'in_stock': True,
                        'sku': 'TEST-001',
                    }
                ]
            }
        ]
        
        existing_variants = [
            {
                'platform_variant_id': '67890',
                'price_current': Decimal('25.99'),
                'currency': 'USD',
                'in_stock': True,
            }
        ]
        
        deltas = self.parser.detect_price_deltas(fetched_products, existing_variants)
        
        assert len(deltas) == 0  # No changes detected
    
    def test_detect_price_deltas_price_change(self):
        """Test detecting price changes."""
        fetched_products = [
            {
                'platform_product_id': '12345',
                'variants': [
                    {
                        'platform_variant_id': '67890',
                        'price_decimal': Decimal('29.99'),
                        'currency': 'USD',
                        'in_stock': True,
                        'sku': 'TEST-001',
                    }
                ]
            }
        ]
        
        existing_variants = [
            {
                'platform_variant_id': '67890',
                'price_current': Decimal('25.99'),
                'currency': 'USD',
                'in_stock': True,
            }
        ]
        
        deltas = self.parser.detect_price_deltas(fetched_products, existing_variants)
        
        assert len(deltas) == 1
        delta = deltas[0]
        assert delta.variant_id == '67890'
        assert delta.old_price == Decimal('25.99')
        assert delta.new_price == Decimal('29.99')
        assert delta.has_price_change() is True
    
    def test_detect_price_deltas_new_variant(self):
        """Test detecting new variants."""
        fetched_products = [
            {
                'platform_product_id': '12345',
                'variants': [
                    {
                        'platform_variant_id': '67890',
                        'price_decimal': Decimal('25.99'),
                        'currency': 'USD',
                        'in_stock': True,
                        'sku': 'TEST-001',
                    }
                ]
            }
        ]
        
        existing_variants = []  # No existing variants
        
        deltas = self.parser.detect_price_deltas(fetched_products, existing_variants)
        
        assert len(deltas) == 1
        delta = deltas[0]
        assert delta.variant_id == '67890'
        assert delta.old_price is None  # New variant
        assert delta.new_price == Decimal('25.99')
        assert delta.has_price_change() is True
    
    def test_price_delta_creation(self):
        """Test PriceDelta object creation."""
        delta = PriceDelta(
            variant_id='12345',
            old_price=Decimal('25.99'),
            new_price=Decimal('29.99'),
            currency='USD',
            in_stock=True,
            sku='TEST-001',
        )
        
        assert delta.variant_id == '12345'
        assert delta.old_price == Decimal('25.99')
        assert delta.new_price == Decimal('29.99')
        assert delta.currency == 'USD'
        assert delta.in_stock is True
        assert delta.sku == 'TEST-001'
        assert delta.has_price_change() is True
        assert delta.has_availability_change() is False
    
    def test_price_delta_no_change(self):
        """Test PriceDelta with no changes."""
        delta = PriceDelta(
            variant_id='12345',
            old_price=Decimal('25.99'),
            new_price=Decimal('25.99'),
            currency='USD',
            in_stock=True,
            sku='TEST-001',
        )
        
        assert delta.has_price_change() is False
    
    def test_price_delta_to_dict(self):
        """Test PriceDelta to_dict method."""
        delta = PriceDelta(
            variant_id='12345',
            old_price=Decimal('25.99'),
            new_price=Decimal('29.99'),
            currency='USD',
            in_stock=True,
            sku='TEST-001',
        )
        
        delta_dict = delta.to_dict()
        
        assert delta_dict['variant_id'] == '12345'
        assert delta_dict['old_price'] == 25.99
        assert delta_dict['new_price'] == 29.99
        assert delta_dict['currency'] == 'USD'
        assert delta_dict['in_stock'] is True
        assert delta_dict['sku'] == 'TEST-001'
        assert 'detected_at' in delta_dict
    
    def test_currency_normalization_placeholder(self):
        """Test currency normalization (placeholder implementation)."""
        price = Decimal('25.99')
        normalized = self.parser.normalize_currency(price, 'EUR', 'USD')
        
        # Currently returns original price (placeholder)
        assert normalized == price
    
    def test_performance_metrics(self):
        """Test getting performance metrics."""
        metrics = self.parser.get_performance_metrics()
        
        assert metrics['job_type'] == 'price_only'
        assert metrics['price_fields'] == ["price", "availability", "sku", "weight"]
        assert metrics['parser_version'] == '1.0.0'
    
    def test_extract_availability_different_formats(self):
        """Test extracting availability from different formats."""
        # Test boolean True
        variant_bool = {'available': True}
        assert self.parser._extract_availability(variant_bool) is True
        
        # Test boolean False
        variant_bool_false = {'available': False}
        assert self.parser._extract_availability(variant_bool_false) is False
        
        # Test integer > 0
        variant_int = {'inventory_quantity': 5}
        assert self.parser._extract_availability(variant_int) is True
        
        # Test integer 0
        variant_int_zero = {'inventory_quantity': 0}
        assert self.parser._extract_availability(variant_int_zero) is False
        
        # Test string 'true'
        variant_str = {'stock_status': 'true'}
        assert self.parser._extract_availability(variant_str) is True
        
        # Test string 'false'
        variant_str_false = {'stock_status': 'false'}
        assert self.parser._extract_availability(variant_str_false) is False
        
        # Test default (no fields)
        variant_default = {}
        assert self.parser._extract_availability(variant_default) is True
    
    def test_extract_weight_different_formats(self):
        """Test extracting weight from different formats."""
        # Test numeric weight
        variant_numeric = {'weight': 250}
        assert self.parser._extract_weight(variant_numeric) == 250.0
        
        # Test string weight
        variant_string = {'weight': '250'}
        assert self.parser._extract_weight(variant_string) == 250.0
        
        # Test float weight (weight parser converts to int grams)
        variant_float = {'weight': 250.5}
        assert self.parser._extract_weight(variant_float) == 250.0
        
        # Test invalid weight
        variant_invalid = {'weight': 'invalid'}
        assert self.parser._extract_weight(variant_invalid) is None
        
        # Test missing weight
        variant_missing = {}
        assert self.parser._extract_weight(variant_missing) is None
