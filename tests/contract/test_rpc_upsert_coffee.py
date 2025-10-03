"""
Contract tests for rpc_upsert_coffee RPC function.

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


class TestRPCUpsertCoffeeContract:
    """Contract tests for rpc_upsert_coffee function."""
    
    @pytest.fixture
    def mock_supabase_client(self):
        """Create mock Supabase client."""
        client = Mock()
        client.rpc.return_value.execute.return_value.data = ["coffee-id-123"]
        return client
    
    @pytest.fixture
    def rpc_client(self, mock_supabase_client):
        """Create RPC client with mock Supabase client."""
        return RPCClient(mock_supabase_client)
    
    @pytest.fixture
    def valid_coffee_data(self):
        """Valid coffee data for testing."""
        return {
            'bean_species': 'arabica',
            'name': 'Test Coffee',
            'slug': 'test-coffee',
            'roaster_id': str(uuid.uuid4()),
            'process': 'washed',
            'process_raw': 'Washed Process',
            'roast_level': 'medium',
            'roast_level_raw': 'Medium Roast',
            'roast_style_raw': 'City Roast',
            'description_md': 'A great test coffee',
            'direct_buy_url': 'https://example.com/coffee',
            'platform_product_id': 'prod-123'
        }
    
    def test_rpc_upsert_coffee_required_parameters(self, rpc_client, valid_coffee_data):
        """Test that all required parameters are validated."""
        # Test with all required parameters
        result = rpc_client.upsert_coffee(**valid_coffee_data)
        assert result == "coffee-id-123"
        
        # Verify RPC was called with correct parameters
        rpc_client.supabase_client.rpc.assert_called_once()
        call_args = rpc_client.supabase_client.rpc.call_args
        assert call_args[0][0] == 'rpc_upsert_coffee'
        
        parameters = call_args[0][1]
        assert parameters['p_bean_species'] == 'arabica'
        assert parameters['p_name'] == 'Test Coffee'
        assert parameters['p_slug'] == 'test-coffee'
        assert parameters['p_roaster_id'] == valid_coffee_data['roaster_id']
        assert parameters['p_process'] == 'washed'
        assert parameters['p_roast_level'] == 'medium'
        assert parameters['p_platform_product_id'] == 'prod-123'
        assert parameters['p_description_md'] == 'A great test coffee'
        assert parameters['p_direct_buy_url'] == 'https://example.com/coffee'
        assert parameters['p_process_raw'] == 'Washed Process'
        assert parameters['p_roast_level_raw'] == 'Medium Roast'
        assert parameters['p_roast_style_raw'] == 'City Roast'
    
    def test_rpc_upsert_coffee_optional_parameters(self, rpc_client, valid_coffee_data):
        """Test optional parameters are correctly passed."""
        # Add optional parameters
        optional_data = {
            'decaf': True,
            'notes_raw': {'source': 'test'},
            'source_raw': {'platform': 'shopify'},
            'status': 'active',
            'tags': ['fruity', 'bright'],
            'default_grind': 'whole',
            'varieties': ['heirloom'],
            'region': 'Yirgacheffe',
            'country': 'Ethiopia',
            'altitude': 2000,
            'acidity': 8.5,
            'body': 6.0,
            'flavors': ['blueberry', 'lemon'],
            'content_hash': 'hash123',
            'raw_hash': 'rawhash123',
            'title_cleaned': 'Clean Title',
            'description_cleaned': 'Clean Description'
        }
        
        result = rpc_client.upsert_coffee(**valid_coffee_data, **optional_data)
        assert result == "coffee-id-123"
        
        # Verify optional parameters were passed
        call_args = rpc_client.supabase_client.rpc.call_args
        parameters = call_args[0][1]
        
        assert parameters['p_decaf'] is True
        assert parameters['p_notes_raw'] == {'source': 'test'}
        assert parameters['p_source_raw'] == {'platform': 'shopify'}
        assert parameters['p_status'] == 'active'
        assert parameters['p_tags'] == ['fruity', 'bright']
        assert parameters['p_default_grind'] == 'whole'
        assert parameters['p_varieties'] == ['heirloom']
        assert parameters['p_region'] == 'Yirgacheffe'
        assert parameters['p_country'] == 'Ethiopia'
        assert parameters['p_altitude'] == 2000
        assert parameters['p_acidity'] == 8.5
        assert parameters['p_body'] == 6.0
        assert parameters['p_flavors'] == ['blueberry', 'lemon']
        assert parameters['p_content_hash'] == 'hash123'
        assert parameters['p_raw_hash'] == 'rawhash123'
        assert parameters['p_title_cleaned'] == 'Clean Title'
        assert parameters['p_description_cleaned'] == 'Clean Description'
    
    def test_rpc_upsert_coffee_enum_validation(self, rpc_client, valid_coffee_data):
        """Test enum parameter validation."""
        # Test valid enum values
        valid_enums = {
            'bean_species': ['arabica', 'robusta', 'liberica', 'excelsa'],
            'process': ['washed', 'natural', 'honey', 'semi-washed'],
            'roast_level': ['light', 'medium', 'medium-dark', 'dark']
        }
        
        for param, values in valid_enums.items():
            for value in values:
                test_data = valid_coffee_data.copy()
                test_data[param] = value
                
                result = rpc_client.upsert_coffee(**test_data)
                assert result == "coffee-id-123"
    
    def test_rpc_upsert_coffee_invalid_enum_values(self, rpc_client, valid_coffee_data):
        """Test that invalid enum values are rejected."""
        invalid_cases = [
            ('bean_species', 'invalid_species'),
            ('process', 'invalid_process'),
            ('roast_level', 'invalid_roast')
        ]
        
        for param, invalid_value in invalid_cases:
            test_data = valid_coffee_data.copy()
            test_data[param] = invalid_value
            
            # Mock RPC to raise validation error
            rpc_client.supabase_client.rpc.return_value.execute.side_effect = Exception(
                f"invalid input value for enum {param}_enum: '{invalid_value}'"
            )
            
            with pytest.raises(RPCError):
                rpc_client.upsert_coffee(**test_data)
    
    def test_rpc_upsert_coffee_missing_required_parameters(self, rpc_client):
        """Test that missing required parameters are handled."""
        # Test with missing required parameter
        incomplete_data = {
            'bean_species': 'arabica',
            'name': 'Test Coffee',
            # Missing slug, roaster_id, etc.
        }
        
        with pytest.raises(TypeError):
            rpc_client.upsert_coffee(**incomplete_data)
    
    def test_rpc_upsert_coffee_foreign_key_constraints(self, rpc_client, valid_coffee_data):
        """Test foreign key constraint validation."""
        # Test with invalid roaster_id
        invalid_data = valid_coffee_data.copy()
        invalid_data['roaster_id'] = 'invalid-roaster-id'
        
        # Mock RPC to raise constraint error
        rpc_client.supabase_client.rpc.return_value.execute.side_effect = Exception(
            "insert or update on table 'coffees' violates foreign key constraint"
        )
        
        with pytest.raises(RPCError):
            rpc_client.upsert_coffee(**invalid_data)
    
    def test_rpc_upsert_coffee_duplicate_constraints(self, rpc_client, valid_coffee_data):
        """Test duplicate constraint handling."""
        # Test duplicate slug per roaster
        rpc_client.supabase_client.rpc.return_value.execute.side_effect = Exception(
            "duplicate key value violates unique constraint 'coffees_slug_roaster_id_key'"
        )
        
        with pytest.raises(RPCError):
            rpc_client.upsert_coffee(**valid_coffee_data)
    
    def test_rpc_upsert_coffee_performance_timeout(self, rpc_client, valid_coffee_data):
        """Test RPC performance and timeout handling."""
        start_time = time.time()
        
        # Mock slow response
        def slow_execute():
            time.sleep(0.1)  # Simulate slow response
            result = Mock()
            result.data = ["coffee-id-123"]
            return result
        
        rpc_client.supabase_client.rpc.return_value.execute = slow_execute
        
        result = rpc_client.upsert_coffee(**valid_coffee_data)
        
        elapsed_time = time.time() - start_time
        assert result == "coffee-id-123"
        assert elapsed_time >= 0.1  # Should take at least 100ms
    
    def test_rpc_upsert_coffee_retry_logic(self, rpc_client, valid_coffee_data):
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
                result.data = ["coffee-id-123"]
                return result
        
        rpc_client.supabase_client.rpc.return_value.execute = mock_execute
        
        result = rpc_client.upsert_coffee(**valid_coffee_data)
        
        assert result == "coffee-id-123"
        assert call_count == 2  # Should retry once
    
    def test_rpc_upsert_coffee_constraint_error_no_retry(self, rpc_client, valid_coffee_data):
        """Test that constraint errors are not retried."""
        # Mock constraint error
        rpc_client.supabase_client.rpc.return_value.execute.side_effect = Exception(
            "constraint violation"
        )
        
        with pytest.raises(RPCError):
            rpc_client.upsert_coffee(**valid_coffee_data)
        
        # Should only call once (no retry for constraint errors)
        assert rpc_client.supabase_client.rpc.call_count == 1
    
    def test_rpc_upsert_coffee_validation_error_no_retry(self, rpc_client, valid_coffee_data):
        """Test that validation errors are not retried."""
        # Mock validation error
        rpc_client.supabase_client.rpc.return_value.execute.side_effect = Exception(
            "invalid input value"
        )
        
        with pytest.raises(RPCError):
            rpc_client.upsert_coffee(**valid_coffee_data)
        
        # Should only call once (no retry for validation errors)
        assert rpc_client.supabase_client.rpc.call_count == 1
    
    def test_rpc_upsert_coffee_json_parameters(self, rpc_client, valid_coffee_data):
        """Test JSON parameter handling."""
        json_data = {
            'notes_raw': {
                'sensory': {'acidity': 8.5, 'body': 6.0},
                'flavors': ['blueberry', 'lemon'],
                'source': 'llm_enrichment'
            },
            'source_raw': {
                'platform': 'shopify',
                'product_id': '12345',
                'variants': [{'id': 'var1', 'price': 450.0}]
            }
        }
        
        result = rpc_client.upsert_coffee(**valid_coffee_data, **json_data)
        assert result == "coffee-id-123"
        
        # Verify JSON parameters were passed correctly
        call_args = rpc_client.supabase_client.rpc.call_args
        parameters = call_args[0][1]
        
        assert parameters['p_notes_raw'] == json_data['notes_raw']
        assert parameters['p_source_raw'] == json_data['source_raw']
    
    def test_rpc_upsert_coffee_array_parameters(self, rpc_client, valid_coffee_data):
        """Test array parameter handling."""
        array_data = {
            'tags': ['fruity', 'bright', 'ethiopian', 'single-origin'],
            'varieties': ['heirloom', 'geisha'],
            'flavors': ['blueberry', 'lemon', 'jasmine', 'honey']
        }
        
        result = rpc_client.upsert_coffee(**valid_coffee_data, **array_data)
        assert result == "coffee-id-123"
        
        # Verify array parameters were passed correctly
        call_args = rpc_client.supabase_client.rpc.call_args
        parameters = call_args[0][1]
        
        assert parameters['p_tags'] == array_data['tags']
        assert parameters['p_varieties'] == array_data['varieties']
        assert parameters['p_flavors'] == array_data['flavors']
    
    def test_rpc_upsert_coffee_numeric_parameters(self, rpc_client, valid_coffee_data):
        """Test numeric parameter validation."""
        numeric_data = {
            'altitude': 2000,
            'acidity': 8.5,
            'body': 6.0
        }
        
        result = rpc_client.upsert_coffee(**valid_coffee_data, **numeric_data)
        assert result == "coffee-id-123"
        
        # Verify numeric parameters were passed correctly
        call_args = rpc_client.supabase_client.rpc.call_args
        parameters = call_args[0][1]
        
        assert parameters['p_altitude'] == 2000
        assert parameters['p_acidity'] == 8.5
        assert parameters['p_body'] == 6.0
    
    def test_rpc_upsert_coffee_boolean_parameters(self, rpc_client, valid_coffee_data):
        """Test boolean parameter handling."""
        boolean_data = {
            'decaf': True
        }
        
        result = rpc_client.upsert_coffee(**valid_coffee_data, **boolean_data)
        assert result == "coffee-id-123"
        
        # Verify boolean parameters were passed correctly
        call_args = rpc_client.supabase_client.rpc.call_args
        parameters = call_args[0][1]
        
        assert parameters['p_decaf'] is True
    
    def test_rpc_upsert_coffee_string_parameters(self, rpc_client, valid_coffee_data):
        """Test string parameter handling."""
        string_data = {
            'region': 'Yirgacheffe',
            'country': 'Ethiopia',
            'content_hash': 'sha256:abc123def456',
            'raw_hash': 'sha256:raw123hash456',
            'title_cleaned': 'Clean Coffee Title',
            'description_cleaned': 'Clean coffee description'
        }
        
        result = rpc_client.upsert_coffee(**valid_coffee_data, **string_data)
        assert result == "coffee-id-123"
        
        # Verify string parameters were passed correctly
        call_args = rpc_client.supabase_client.rpc.call_args
        parameters = call_args[0][1]
        
        assert parameters['p_region'] == 'Yirgacheffe'
        assert parameters['p_country'] == 'Ethiopia'
        assert parameters['p_content_hash'] == 'sha256:abc123def456'
        assert parameters['p_raw_hash'] == 'sha256:raw123hash456'
        assert parameters['p_title_cleaned'] == 'Clean Coffee Title'
        assert parameters['p_description_cleaned'] == 'Clean coffee description'
    
    def test_rpc_upsert_coffee_edge_cases(self, rpc_client, valid_coffee_data):
        """Test edge cases and boundary conditions."""
        # Test with empty strings - create new data to avoid conflicts
        edge_data = valid_coffee_data.copy()
        edge_data.update({
            'description_md': '',
            'direct_buy_url': '',
            'process_raw': '',
            'roast_level_raw': '',
            'roast_style_raw': ''
        })
        
        result = rpc_client.upsert_coffee(**edge_data)
        assert result == "coffee-id-123"
        
        # Test with None values for optional parameters
        none_data = {
            'decaf': None,
            'notes_raw': None,
            'source_raw': None,
            'status': None
        }
        
        result = rpc_client.upsert_coffee(**valid_coffee_data, **none_data)
        assert result == "coffee-id-123"
    
    def test_rpc_upsert_coffee_large_data(self, rpc_client, valid_coffee_data):
        """Test with large data payloads."""
        large_data = valid_coffee_data.copy()
        large_data.update({
            'description_md': 'A' * 10000,  # Large description
            'source_raw': {
                'large_data': 'x' * 50000,  # Large JSON payload
                'nested': {
                    'level1': {'level2': {'level3': 'deep' * 1000}}
                }
            },
            'tags': ['tag' + str(i) for i in range(100)],  # Many tags
            'flavors': ['flavor' + str(i) for i in range(50)]  # Many flavors
        })
        
        result = rpc_client.upsert_coffee(**large_data)
        assert result == "coffee-id-123"
    
    def test_rpc_upsert_coffee_special_characters(self, rpc_client, valid_coffee_data):
        """Test with special characters in strings."""
        special_data = valid_coffee_data.copy()
        special_data.update({
            'name': 'Café & Co. "Special" Coffee (100%)',
            'slug': 'cafe-co-special-coffee-100',
            'description_md': 'Coffee with **bold** and *italic* text\n\n- List item\n- Another item',
            'region': 'São Paulo, Brazil',
            'country': 'Brasil'
        })
        
        result = rpc_client.upsert_coffee(**special_data)
        assert result == "coffee-id-123"
    
    def test_rpc_upsert_coffee_unicode_handling(self, rpc_client, valid_coffee_data):
        """Test Unicode character handling."""
        unicode_data = valid_coffee_data.copy()
        unicode_data.update({
            'name': 'Café Español con Acentos',
            'description_md': 'Café con acentos: áéíóú ñü',
            'region': 'São Paulo',
            'country': 'Brasil',
            'tags': ['café', 'español', 'acentos']
        })
        
        result = rpc_client.upsert_coffee(**unicode_data)
        assert result == "coffee-id-123"
