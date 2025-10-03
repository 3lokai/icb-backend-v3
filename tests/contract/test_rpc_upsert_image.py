"""
Contract tests for rpc_upsert_coffee_image RPC function.

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


class TestRPCUpsertImageContract:
    """Contract tests for rpc_upsert_coffee_image function."""
    
    @pytest.fixture
    def mock_supabase_client(self):
        """Create mock Supabase client."""
        client = Mock()
        client.rpc.return_value.execute.return_value.data = ["image-id-123"]
        return client
    
    @pytest.fixture
    def rpc_client(self, mock_supabase_client):
        """Create RPC client with mock Supabase client."""
        return RPCClient(mock_supabase_client)
    
    @pytest.fixture
    def valid_image_data(self):
        """Valid image data for testing."""
        return {
            'coffee_id': str(uuid.uuid4()),
            'url': 'https://example.com/images/coffee.jpg'
        }
    
    def test_rpc_upsert_image_required_parameters(self, rpc_client, valid_image_data):
        """Test that all required parameters are validated."""
        # Test with all required parameters
        result = rpc_client.upsert_coffee_image(**valid_image_data)
        assert result == "image-id-123"
        
        # Verify RPC was called with correct parameters
        rpc_client.supabase_client.rpc.assert_called_once()
        call_args = rpc_client.supabase_client.rpc.call_args
        assert call_args[0][0] == 'rpc_upsert_coffee_image'
        
        parameters = call_args[0][1]
        assert parameters['p_coffee_id'] == valid_image_data['coffee_id']
        assert parameters['p_url'] == 'https://example.com/images/coffee.jpg'
    
    def test_rpc_upsert_image_optional_parameters(self, rpc_client, valid_image_data):
        """Test optional parameters are correctly passed."""
        # Add optional parameters
        optional_data = {
            'alt': 'Coffee product image',
            'width': 800,
            'height': 600,
            'sort_order': 1,
            'source_raw': {'platform': 'shopify', 'image_id': 'img123'},
            'content_hash': 'sha256:abc123def456',
            'imagekit_url': 'https://ik.imagekit.io/coffee/image.jpg'
        }
        
        result = rpc_client.upsert_coffee_image(**valid_image_data, **optional_data)
        assert result == "image-id-123"
        
        # Verify optional parameters were passed
        call_args = rpc_client.supabase_client.rpc.call_args
        parameters = call_args[0][1]
        
        assert parameters['p_alt'] == 'Coffee product image'
        assert parameters['p_width'] == 800
        assert parameters['p_height'] == 600
        assert parameters['p_sort_order'] == 1
        assert parameters['p_source_raw'] == {'platform': 'shopify', 'image_id': 'img123'}
        assert parameters['p_content_hash'] == 'sha256:abc123def456'
        assert parameters['p_imagekit_url'] == 'https://ik.imagekit.io/coffee/image.jpg'
    
    def test_rpc_upsert_image_url_validation(self, rpc_client, valid_image_data):
        """Test URL parameter validation."""
        # Test valid URLs
        valid_urls = [
            'https://example.com/image.jpg',
            'https://cdn.example.com/images/coffee.png',
            'https://storage.googleapis.com/bucket/image.webp',
            'https://ik.imagekit.io/coffee/image.jpg'
        ]
        
        for url in valid_urls:
            test_data = valid_image_data.copy()
            test_data['url'] = url
            
            result = rpc_client.upsert_coffee_image(**test_data)
            assert result == "image-id-123"
    
    def test_rpc_upsert_image_invalid_url(self, rpc_client, valid_image_data):
        """Test that invalid URLs are handled."""
        # Test with invalid URL
        test_data = valid_image_data.copy()
        test_data['url'] = 'not-a-valid-url'
        
        # Mock RPC to raise validation error
        rpc_client.supabase_client.rpc.return_value.execute.side_effect = Exception(
            "invalid URL format"
        )
        
        with pytest.raises(RPCError):
            rpc_client.upsert_coffee_image(**test_data)
    
    def test_rpc_upsert_image_missing_required_parameters(self, rpc_client):
        """Test that missing required parameters are handled."""
        # Test with missing required parameter
        incomplete_data = {
            'url': 'https://example.com/image.jpg'
            # Missing coffee_id
        }
        
        with pytest.raises(TypeError):
            rpc_client.upsert_coffee_image(**incomplete_data)
    
    def test_rpc_upsert_image_foreign_key_constraints(self, rpc_client, valid_image_data):
        """Test foreign key constraint validation."""
        # Test with invalid coffee_id
        invalid_data = valid_image_data.copy()
        invalid_data['coffee_id'] = 'invalid-coffee-id'
        
        # Mock RPC to raise constraint error
        rpc_client.supabase_client.rpc.return_value.execute.side_effect = Exception(
            "insert or update on table 'coffee_images' violates foreign key constraint"
        )
        
        with pytest.raises(RPCError):
            rpc_client.upsert_coffee_image(**invalid_data)
    
    def test_rpc_upsert_image_duplicate_constraints(self, rpc_client, valid_image_data):
        """Test duplicate constraint handling."""
        # Test duplicate URL for same coffee
        rpc_client.supabase_client.rpc.return_value.execute.side_effect = Exception(
            "duplicate key value violates unique constraint 'coffee_images_coffee_id_url_key'"
        )
        
        with pytest.raises(RPCError):
            rpc_client.upsert_coffee_image(**valid_image_data)
    
    def test_rpc_upsert_image_performance_timeout(self, rpc_client, valid_image_data):
        """Test RPC performance and timeout handling."""
        start_time = time.time()
        
        # Mock slow response
        def slow_execute():
            time.sleep(0.1)  # Simulate slow response
            result = Mock()
            result.data = ["image-id-123"]
            return result
        
        rpc_client.supabase_client.rpc.return_value.execute = slow_execute
        
        result = rpc_client.upsert_coffee_image(**valid_image_data)
        
        elapsed_time = time.time() - start_time
        assert result == "image-id-123"
        assert elapsed_time >= 0.1  # Should take at least 100ms
    
    def test_rpc_upsert_image_retry_logic(self, rpc_client, valid_image_data):
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
                result.data = ["image-id-123"]
                return result
        
        rpc_client.supabase_client.rpc.return_value.execute = mock_execute
        
        result = rpc_client.upsert_coffee_image(**valid_image_data)
        
        assert result == "image-id-123"
        assert call_count == 2  # Should retry once
    
    def test_rpc_upsert_image_constraint_error_no_retry(self, rpc_client, valid_image_data):
        """Test that constraint errors are not retried."""
        # Mock constraint error
        rpc_client.supabase_client.rpc.return_value.execute.side_effect = Exception(
            "constraint violation"
        )
        
        with pytest.raises(RPCError):
            rpc_client.upsert_coffee_image(**valid_image_data)
        
        # Should only call once (no retry for constraint errors)
        assert rpc_client.supabase_client.rpc.call_count == 1
    
    def test_rpc_upsert_image_validation_error_no_retry(self, rpc_client, valid_image_data):
        """Test that validation errors are not retried."""
        # Mock validation error
        rpc_client.supabase_client.rpc.return_value.execute.side_effect = Exception(
            "invalid input value"
        )
        
        with pytest.raises(RPCError):
            rpc_client.upsert_coffee_image(**valid_image_data)
        
        # Should only call once (no retry for validation errors)
        assert rpc_client.supabase_client.rpc.call_count == 1
    
    def test_rpc_upsert_image_numeric_parameters(self, rpc_client, valid_image_data):
        """Test numeric parameter validation."""
        numeric_data = {
            'width': 1920,
            'height': 1080,
            'sort_order': 5
        }
        
        result = rpc_client.upsert_coffee_image(**valid_image_data, **numeric_data)
        assert result == "image-id-123"
        
        # Verify numeric parameters were passed correctly
        call_args = rpc_client.supabase_client.rpc.call_args
        parameters = call_args[0][1]
        
        assert parameters['p_width'] == 1920
        assert parameters['p_height'] == 1080
        assert parameters['p_sort_order'] == 5
    
    def test_rpc_upsert_image_string_parameters(self, rpc_client, valid_image_data):
        """Test string parameter handling."""
        string_data = {
            'alt': 'Beautiful coffee beans',
            'content_hash': 'sha256:abc123def456789',
            'imagekit_url': 'https://ik.imagekit.io/coffee/optimized-image.jpg'
        }
        
        result = rpc_client.upsert_coffee_image(**valid_image_data, **string_data)
        assert result == "image-id-123"
        
        # Verify string parameters were passed correctly
        call_args = rpc_client.supabase_client.rpc.call_args
        parameters = call_args[0][1]
        
        assert parameters['p_alt'] == 'Beautiful coffee beans'
        assert parameters['p_content_hash'] == 'sha256:abc123def456789'
        assert parameters['p_imagekit_url'] == 'https://ik.imagekit.io/coffee/optimized-image.jpg'
    
    def test_rpc_upsert_image_json_parameters(self, rpc_client, valid_image_data):
        """Test JSON parameter handling."""
        json_data = {
            'source_raw': {
                'platform': 'shopify',
                'image_id': 'img123',
                'metadata': {
                    'original_size': 2048000,
                    'format': 'jpeg',
                    'quality': 85
                },
                'processing': {
                    'resized': True,
                    'optimized': True,
                    'watermarked': False
                }
            }
        }
        
        result = rpc_client.upsert_coffee_image(**valid_image_data, **json_data)
        assert result == "image-id-123"
        
        # Verify JSON parameters were passed correctly
        call_args = rpc_client.supabase_client.rpc.call_args
        parameters = call_args[0][1]
        
        assert parameters['p_source_raw'] == json_data['source_raw']
    
    def test_rpc_upsert_image_edge_cases(self, rpc_client, valid_image_data):
        """Test edge cases and boundary conditions."""
        # Test with empty strings
        edge_data = {
            'alt': '',
            'content_hash': '',
            'imagekit_url': ''
        }
        
        result = rpc_client.upsert_coffee_image(**valid_image_data, **edge_data)
        assert result == "image-id-123"
        
        # Test with None values for optional parameters
        none_data = {
            'alt': None,
            'width': None,
            'height': None,
            'sort_order': None,
            'source_raw': None,
            'content_hash': None,
            'imagekit_url': None
        }
        
        result = rpc_client.upsert_coffee_image(**valid_image_data, **none_data)
        assert result == "image-id-123"
    
    def test_rpc_upsert_image_large_data(self, rpc_client, valid_image_data):
        """Test with large data payloads."""
        large_data = {
            'alt': 'A' * 1000,  # Large alt text
            'source_raw': {
                'large_data': 'x' * 50000,  # Large JSON payload
                'nested': {
                    'level1': {'level2': {'level3': 'deep' * 1000}}
                }
            }
        }
        
        result = rpc_client.upsert_coffee_image(**valid_image_data, **large_data)
        assert result == "image-id-123"
    
    def test_rpc_upsert_image_special_characters(self, rpc_client, valid_image_data):
        """Test with special characters in strings."""
        special_data = valid_image_data.copy()
        special_data.update({
            'alt': 'Coffee "Special" (100% Arabica) - Image',
            'url': 'https://example.com/café-español.jpg',
            'imagekit_url': 'https://ik.imagekit.io/coffee/café-español.jpg'
        })
        
        result = rpc_client.upsert_coffee_image(**special_data)
        assert result == "image-id-123"
    
    def test_rpc_upsert_image_unicode_handling(self, rpc_client, valid_image_data):
        """Test Unicode character handling."""
        unicode_data = valid_image_data.copy()
        unicode_data.update({
            'alt': 'Café Español con Acentos - Imagen',
            'url': 'https://example.com/café-español.jpg',
            'imagekit_url': 'https://ik.imagekit.io/coffee/café-español.jpg'
        })
        
        result = rpc_client.upsert_coffee_image(**unicode_data)
        assert result == "image-id-123"
    
    def test_rpc_upsert_image_content_hash_validation(self, rpc_client, valid_image_data):
        """Test content hash validation."""
        # Test valid hash formats
        valid_hashes = [
            'sha256:abc123def456',
            'sha256:1234567890abcdef',
            'md5:abc123def456',
            'sha1:abc123def456'
        ]
        
        for hash_value in valid_hashes:
            test_data = valid_image_data.copy()
            test_data['content_hash'] = hash_value
            
            result = rpc_client.upsert_coffee_image(**test_data)
            assert result == "image-id-123"
    
    def test_rpc_upsert_image_invalid_content_hash(self, rpc_client, valid_image_data):
        """Test invalid content hash handling."""
        # Test with invalid hash format
        test_data = valid_image_data.copy()
        test_data['content_hash'] = 'invalid-hash-format'
        
        # Mock RPC to raise validation error
        rpc_client.supabase_client.rpc.return_value.execute.side_effect = Exception(
            "invalid hash format"
        )
        
        with pytest.raises(RPCError):
            rpc_client.upsert_coffee_image(**test_data)
    
    def test_rpc_upsert_image_imagekit_url_validation(self, rpc_client, valid_image_data):
        """Test ImageKit URL validation."""
        # Test valid ImageKit URLs
        valid_imagekit_urls = [
            'https://ik.imagekit.io/coffee/image.jpg',
            'https://ik.imagekit.io/coffee/optimized-image.jpg',
            'https://ik.imagekit.io/coffee/transformed-image.jpg'
        ]
        
        for url in valid_imagekit_urls:
            test_data = valid_image_data.copy()
            test_data['imagekit_url'] = url
            
            result = rpc_client.upsert_coffee_image(**test_data)
            assert result == "image-id-123"
    
    def test_rpc_upsert_image_sort_order_validation(self, rpc_client, valid_image_data):
        """Test sort order validation."""
        # Test with various sort order values
        sort_orders = [0, 1, 5, 10, 100, 999]
        
        for sort_order in sort_orders:
            test_data = valid_image_data.copy()
            test_data['sort_order'] = sort_order
            
            result = rpc_client.upsert_coffee_image(**test_data)
            assert result == "image-id-123"
    
    def test_rpc_upsert_image_dimension_validation(self, rpc_client, valid_image_data):
        """Test image dimension validation."""
        # Test with various dimension values
        dimensions = [
            (100, 100),
            (800, 600),
            (1920, 1080),
            (4096, 4096)
        ]
        
        for width, height in dimensions:
            test_data = valid_image_data.copy()
            test_data['width'] = width
            test_data['height'] = height
            
            result = rpc_client.upsert_coffee_image(**test_data)
            assert result == "image-id-123"
    
    def test_rpc_upsert_image_negative_dimensions(self, rpc_client, valid_image_data):
        """Test negative dimension handling."""
        # Test with negative dimensions
        test_data = valid_image_data.copy()
        test_data['width'] = -100
        test_data['height'] = -100
        
        # Mock RPC to raise validation error
        rpc_client.supabase_client.rpc.return_value.execute.side_effect = Exception(
            "dimensions must be positive"
        )
        
        with pytest.raises(RPCError):
            rpc_client.upsert_coffee_image(**test_data)
    
    def test_rpc_upsert_image_concurrent_access(self, rpc_client, valid_image_data):
        """Test concurrent access handling."""
        # This would typically be tested with actual concurrent calls
        # For now, we'll test that the RPC can handle multiple calls
        results = []
        
        for i in range(5):
            test_data = valid_image_data.copy()
            test_data['url'] = f'https://example.com/image-{i}.jpg'
            
            result = rpc_client.upsert_coffee_image(**test_data)
            results.append(result)
        
        # All calls should succeed
        assert all(result == "image-id-123" for result in results)
        assert len(results) == 5
    
    def test_rpc_upsert_image_transaction_safety(self, rpc_client, valid_image_data):
        """Test transaction safety."""
        # Mock RPC to simulate transaction rollback
        rpc_client.supabase_client.rpc.return_value.execute.side_effect = Exception(
            "transaction rolled back"
        )
        
        with pytest.raises(RPCError):
            rpc_client.upsert_coffee_image(**valid_image_data)
    
    def test_rpc_upsert_image_data_integrity(self, rpc_client, valid_image_data):
        """Test data integrity constraints."""
        # Test with invalid URL format
        invalid_data = valid_image_data.copy()
        invalid_data['url'] = 'not-a-valid-url'
        
        # Mock RPC to raise validation error
        rpc_client.supabase_client.rpc.return_value.execute.side_effect = Exception(
            "invalid URL format"
        )
        
        with pytest.raises(RPCError):
            rpc_client.upsert_coffee_image(**invalid_data)
