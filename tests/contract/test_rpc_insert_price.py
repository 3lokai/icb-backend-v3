"""
Contract tests for rpc_insert_price RPC function.

Tests validate:
- RPC schema and database constraints
- Parameter types and required fields
- Error handling and edge cases
- Performance and timeout handling
"""

import pytest
import time
import uuid
from typing import Dict, Any, Optional
from unittest.mock import Mock, patch
from src.validator.rpc_client import RPCClient, RPCError, RPCValidationError, RPCConstraintError


class TestRPCInsertPriceContract:
    """Contract tests for rpc_insert_price function."""
    
    @pytest.fixture
    def mock_supabase_client(self):
        """Create mock Supabase client."""
        client = Mock()
        client.rpc.return_value.execute.return_value.data = ["price-id-123"]
        return client
    
    @pytest.fixture
    def rpc_client(self, mock_supabase_client):
        """Create RPC client with mock Supabase client."""
        return RPCClient(mock_supabase_client)
    
    @pytest.fixture
    def valid_price_data(self):
        """Valid price data for testing."""
        return {
            'variant_id': str(uuid.uuid4()),
            'price': 450.00
        }
    
    def test_rpc_insert_price_required_parameters(self, rpc_client, valid_price_data):
        """Test that all required parameters are validated."""
        # Test with all required parameters
        result = rpc_client.insert_price(**valid_price_data)
        assert result == "price-id-123"
        
        # Verify RPC was called with correct parameters
        rpc_client.supabase_client.rpc.assert_called_once()
        call_args = rpc_client.supabase_client.rpc.call_args
        assert call_args[0][0] == 'rpc_insert_price'
        
        parameters = call_args[0][1]
        assert parameters['p_variant_id'] == valid_price_data['variant_id']
        assert parameters['p_price'] == 450.00
    
    def test_rpc_insert_price_optional_parameters(self, rpc_client, valid_price_data):
        """Test optional parameters are correctly passed."""
        # Add optional parameters
        optional_data = {
            'currency': 'INR',
            'is_sale': True,
            'scraped_at': '2024-01-15T10:30:00Z',
            'source_url': 'https://example.com/product',
            'source_raw': {'platform': 'shopify', 'variant_id': 'var123'}
        }
        
        result = rpc_client.insert_price(**valid_price_data, **optional_data)
        assert result == "price-id-123"
        
        # Verify optional parameters were passed
        call_args = rpc_client.supabase_client.rpc.call_args
        parameters = call_args[0][1]
        
        assert parameters['p_currency'] == 'INR'
        assert parameters['p_is_sale'] is True
        assert parameters['p_scraped_at'] == '2024-01-15T10:30:00Z'
        assert parameters['p_source_url'] == 'https://example.com/product'
        assert parameters['p_source_raw'] == {'platform': 'shopify', 'variant_id': 'var123'}
    
    def test_rpc_insert_price_currency_validation(self, rpc_client, valid_price_data):
        """Test currency parameter validation."""
        # Test valid currency codes
        valid_currencies = ['INR', 'USD', 'EUR', 'GBP', 'CAD', 'AUD']
        
        for currency in valid_currencies:
            test_data = valid_price_data.copy()
            test_data['currency'] = currency
            
            result = rpc_client.insert_price(**test_data)
            assert result == "price-id-123"
    
    def test_rpc_insert_price_invalid_currency(self, rpc_client, valid_price_data):
        """Test that invalid currency codes are handled."""
        # Test with invalid currency
        test_data = valid_price_data.copy()
        test_data['currency'] = 'INVALID'
        
        # Mock RPC to raise validation error
        rpc_client.supabase_client.rpc.return_value.execute.side_effect = Exception(
            "invalid input value for currency: 'INVALID'"
        )
        
        with pytest.raises(RPCError):
            rpc_client.insert_price(**test_data)
    
    def test_rpc_insert_price_missing_required_parameters(self, rpc_client):
        """Test that missing required parameters are handled."""
        # Test with missing required parameter
        incomplete_data = {
            'price': 450.00
            # Missing variant_id
        }
        
        with pytest.raises(TypeError):
            rpc_client.insert_price(**incomplete_data)
    
    def test_rpc_insert_price_foreign_key_constraints(self, rpc_client, valid_price_data):
        """Test foreign key constraint validation."""
        # Test with invalid variant_id
        invalid_data = valid_price_data.copy()
        invalid_data['variant_id'] = 'invalid-variant-id'
        
        # Mock RPC to raise constraint error
        rpc_client.supabase_client.rpc.return_value.execute.side_effect = Exception(
            "insert or update on table 'prices' violates foreign key constraint"
        )
        
        with pytest.raises(RPCError):
            rpc_client.insert_price(**invalid_data)
    
    def test_rpc_insert_price_duplicate_constraints(self, rpc_client, valid_price_data):
        """Test duplicate constraint handling."""
        # Test duplicate price for same variant and timestamp
        rpc_client.supabase_client.rpc.return_value.execute.side_effect = Exception(
            "duplicate key value violates unique constraint 'prices_variant_id_scraped_at_key'"
        )
        
        with pytest.raises(RPCError):
            rpc_client.insert_price(**valid_price_data)
    
    def test_rpc_insert_price_performance_timeout(self, rpc_client, valid_price_data):
        """Test RPC performance and timeout handling."""
        start_time = time.time()
        
        # Mock slow response
        def slow_execute():
            time.sleep(0.05)  # Simulate slow response
            result = Mock()
            result.data = ["price-id-123"]
            return result
        
        rpc_client.supabase_client.rpc.return_value.execute = slow_execute
        
        result = rpc_client.insert_price(**valid_price_data)
        
        elapsed_time = time.time() - start_time
        assert result == "price-id-123"
        assert elapsed_time >= 0.05  # Should take at least 50ms
    
    def test_rpc_insert_price_retry_logic(self, rpc_client, valid_price_data):
        """Test retry logic for transient failures."""
        # Mock network error followed by success
        call_count = 0
        
        def mock_execute():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("network timeout")
            else:
                result = Mock()
                result.data = ["price-id-123"]
                return result
        
        rpc_client.supabase_client.rpc.return_value.execute = mock_execute
        
        result = rpc_client.insert_price(**valid_price_data)
        
        assert result == "price-id-123"
        assert call_count == 2  # Should retry once
    
    def test_rpc_insert_price_constraint_error_no_retry(self, rpc_client, valid_price_data):
        """Test that constraint errors are not retried."""
        # Mock constraint error
        rpc_client.supabase_client.rpc.return_value.execute.side_effect = Exception(
            "constraint violation"
        )
        
        with pytest.raises(RPCError):
            rpc_client.insert_price(**valid_price_data)
        
        # Should only call once (no retry for constraint errors)
        assert rpc_client.supabase_client.rpc.call_count == 1
    
    def test_rpc_insert_price_validation_error_no_retry(self, rpc_client, valid_price_data):
        """Test that validation errors are not retried."""
        # Mock validation error
        rpc_client.supabase_client.rpc.return_value.execute.side_effect = Exception(
            "invalid input value"
        )
        
        with pytest.raises(RPCError):
            rpc_client.insert_price(**valid_price_data)
        
        # Should only call once (no retry for validation errors)
        assert rpc_client.supabase_client.rpc.call_count == 1
    
    def test_rpc_insert_price_numeric_validation(self, rpc_client, valid_price_data):
        """Test numeric parameter validation."""
        # Test with various price values
        price_values = [0.01, 1.0, 100.0, 1000.0, 9999.99, 0.0]
        
        for price in price_values:
            test_data = valid_price_data.copy()
            test_data['price'] = price
            
            result = rpc_client.insert_price(**test_data)
            assert result == "price-id-123"
    
    def test_rpc_insert_price_negative_price(self, rpc_client, valid_price_data):
        """Test negative price handling."""
        # Test with negative price
        test_data = valid_price_data.copy()
        test_data['price'] = -10.0
        
        # Mock RPC to raise validation error
        rpc_client.supabase_client.rpc.return_value.execute.side_effect = Exception(
            "price must be positive"
        )
        
        with pytest.raises(RPCError):
            rpc_client.insert_price(**test_data)
    
    def test_rpc_insert_price_boolean_parameters(self, rpc_client, valid_price_data):
        """Test boolean parameter handling."""
        boolean_data = {
            'is_sale': True
        }
        
        result = rpc_client.insert_price(**valid_price_data, **boolean_data)
        assert result == "price-id-123"
        
        # Verify boolean parameters were passed correctly
        call_args = rpc_client.supabase_client.rpc.call_args
        parameters = call_args[0][1]
        
        assert parameters['p_is_sale'] is True
    
    def test_rpc_insert_price_timestamp_handling(self, rpc_client, valid_price_data):
        """Test timestamp parameter handling."""
        timestamp_data = {
            'scraped_at': '2024-01-15T10:30:00Z'
        }
        
        result = rpc_client.insert_price(**valid_price_data, **timestamp_data)
        assert result == "price-id-123"
        
        # Verify timestamp parameters were passed correctly
        call_args = rpc_client.supabase_client.rpc.call_args
        parameters = call_args[0][1]
        
        assert parameters['p_scraped_at'] == '2024-01-15T10:30:00Z'
    
    def test_rpc_insert_price_url_handling(self, rpc_client, valid_price_data):
        """Test URL parameter handling."""
        url_data = {
            'source_url': 'https://example.com/product/variant-123'
        }
        
        result = rpc_client.insert_price(**valid_price_data, **url_data)
        assert result == "price-id-123"
        
        # Verify URL parameters were passed correctly
        call_args = rpc_client.supabase_client.rpc.call_args
        parameters = call_args[0][1]
        
        assert parameters['p_source_url'] == 'https://example.com/product/variant-123'
    
    def test_rpc_insert_price_json_parameters(self, rpc_client, valid_price_data):
        """Test JSON parameter handling."""
        json_data = {
            'source_raw': {
                'platform': 'shopify',
                'variant_id': 'var123',
                'price_data': {
                    'original_price': 500.0,
                    'sale_price': 450.0,
                    'discount_percent': 10
                },
                'metadata': {
                    'scraped_at': '2024-01-15T10:30:00Z',
                    'user_agent': 'bot/1.0'
                }
            }
        }
        
        result = rpc_client.insert_price(**valid_price_data, **json_data)
        assert result == "price-id-123"
        
        # Verify JSON parameters were passed correctly
        call_args = rpc_client.supabase_client.rpc.call_args
        parameters = call_args[0][1]
        
        assert parameters['p_source_raw'] == json_data['source_raw']
    
    def test_rpc_insert_price_edge_cases(self, rpc_client, valid_price_data):
        """Test edge cases and boundary conditions."""
        # Test with zero price
        zero_price_data = valid_price_data.copy()
        zero_price_data['price'] = 0.0
        
        result = rpc_client.insert_price(**zero_price_data)
        assert result == "price-id-123"
        
        # Test with very small price
        small_price_data = valid_price_data.copy()
        small_price_data['price'] = 0.01
        
        result = rpc_client.insert_price(**small_price_data)
        assert result == "price-id-123"
        
        # Test with very large price
        large_price_data = valid_price_data.copy()
        large_price_data['price'] = 999999.99
        
        result = rpc_client.insert_price(**large_price_data)
        assert result == "price-id-123"
    
    def test_rpc_insert_price_special_characters(self, rpc_client, valid_price_data):
        """Test with special characters in strings."""
        special_data = {
            'source_url': 'https://example.com/product?variant=123&price=450.00',
            'source_raw': {
                'description': 'Coffee "Special" (100% Arabica)',
                'notes': 'Price includes 10% discount'
            }
        }
        
        result = rpc_client.insert_price(**valid_price_data, **special_data)
        assert result == "price-id-123"
    
    def test_rpc_insert_price_unicode_handling(self, rpc_client, valid_price_data):
        """Test Unicode character handling."""
        unicode_data = {
            'source_url': 'https://example.com/café-español',
            'source_raw': {
                'description': 'Café Español con Acentos',
                'notes': 'Precio en ₹ (Rupias)'
            }
        }
        
        result = rpc_client.insert_price(**valid_price_data, **unicode_data)
        assert result == "price-id-123"
    
    def test_rpc_insert_price_large_data(self, rpc_client, valid_price_data):
        """Test with large data payloads."""
        large_data = {
            'source_raw': {
                'large_data': 'x' * 10000,  # Large JSON payload
                'nested': {
                    'level1': {'level2': {'level3': 'deep' * 1000}}
                },
                'array_data': [{'item': i} for i in range(1000)]
            }
        }
        
        result = rpc_client.insert_price(**valid_price_data, **large_data)
        assert result == "price-id-123"
    
    def test_rpc_insert_price_concurrent_access(self, rpc_client, valid_price_data):
        """Test concurrent access handling."""
        # This would typically be tested with actual concurrent calls
        # For now, we'll test that the RPC can handle multiple calls
        results = []
        
        for i in range(5):
            test_data = valid_price_data.copy()
            test_data['price'] = 450.00 + i
            
            result = rpc_client.insert_price(**test_data)
            results.append(result)
        
        # All calls should succeed
        assert all(result == "price-id-123" for result in results)
        assert len(results) == 5
    
    def test_rpc_insert_price_transaction_safety(self, rpc_client, valid_price_data):
        """Test transaction safety."""
        # Mock RPC to simulate transaction rollback
        rpc_client.supabase_client.rpc.return_value.execute.side_effect = Exception(
            "transaction rolled back"
        )
        
        with pytest.raises(RPCError):
            rpc_client.insert_price(**valid_price_data)
    
    def test_rpc_insert_price_data_integrity(self, rpc_client, valid_price_data):
        """Test data integrity constraints."""
        # Test with invalid price format
        invalid_data = valid_price_data.copy()
        invalid_data['price'] = 'invalid_price'
        
        # Mock RPC to raise validation error
        rpc_client.supabase_client.rpc.return_value.execute.side_effect = Exception(
            "invalid input syntax for type numeric"
        )
        
        with pytest.raises(RPCError):
            rpc_client.insert_price(**invalid_data)
