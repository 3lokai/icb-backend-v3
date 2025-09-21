"""
Tests for RPC client wrapper functionality.
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timezone

from src.validator.rpc_client import RPCClient, RPCError, RPCConstraintError, RPCNetworkError, RPCValidationError


class TestRPCClient:
    """Test cases for RPC client wrapper."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_supabase = Mock()
        self.rpc_client = RPCClient(supabase_client=self.mock_supabase, max_retries=2, base_delay=0.1)
    
    def test_init(self):
        """Test RPC client initialization."""
        assert self.rpc_client.supabase_client == self.mock_supabase
        assert self.rpc_client.max_retries == 2
        assert self.rpc_client.base_delay == 0.1
        assert self.rpc_client.rpc_stats['total_calls'] == 0
    
    def test_upsert_coffee_success(self):
        """Test successful coffee upsert."""
        # Mock successful RPC response
        mock_result = Mock()
        mock_result.data = ["coffee-123"]
        self.mock_supabase.rpc.return_value.execute.return_value = mock_result
        
        result = self.rpc_client.upsert_coffee(
            bean_species="arabica",
            name="Test Coffee",
            slug="test-coffee",
            roaster_id="roaster-123",
            process="washed",
            process_raw="Fully Washed",
            roast_level="light",
            roast_level_raw="Light Roast",
            roast_style_raw="City Roast",
            description_md="# Test Coffee\nA test coffee.",
            direct_buy_url="https://test.com/coffee",
            platform_product_id="prod-123"
        )
        
        assert result == "coffee-123"
        assert self.rpc_client.rpc_stats['total_calls'] == 1
        assert self.rpc_client.rpc_stats['successful_calls'] == 1
        assert self.rpc_client.rpc_stats['failed_calls'] == 0
        
        # Verify RPC was called with correct parameters
        self.mock_supabase.rpc.assert_called_once_with('rpc_upsert_coffee', {
            'p_bean_species': 'arabica',
            'p_name': 'Test Coffee',
            'p_slug': 'test-coffee',
            'p_roaster_id': 'roaster-123',
            'p_process': 'washed',
            'p_process_raw': 'Fully Washed',
            'p_roast_level': 'light',
            'p_roast_level_raw': 'Light Roast',
            'p_roast_style_raw': 'City Roast',
            'p_description_md': '# Test Coffee\nA test coffee.',
            'p_direct_buy_url': 'https://test.com/coffee',
            'p_platform_product_id': 'prod-123'
        })
    
    def test_upsert_coffee_with_optional_params(self):
        """Test coffee upsert with optional parameters."""
        mock_result = Mock()
        mock_result.data = ["coffee-123"]
        self.mock_supabase.rpc.return_value.execute.return_value = mock_result
        
        result = self.rpc_client.upsert_coffee(
            bean_species="arabica",
            name="Test Coffee",
            slug="test-coffee",
            roaster_id="roaster-123",
            process="washed",
            process_raw="Fully Washed",
            roast_level="light",
            roast_level_raw="Light Roast",
            roast_style_raw="City Roast",
            description_md="# Test Coffee\nA test coffee.",
            direct_buy_url="https://test.com/coffee",
            platform_product_id="prod-123",
            decaf=True,
            notes_raw={"test": "data"},
            source_raw={"raw": "data"},
            status="active"
        )
        
        assert result == "coffee-123"
        
        # Verify optional parameters were included
        call_args = self.mock_supabase.rpc.call_args[0]
        assert call_args[1]['p_decaf'] is True
        assert call_args[1]['p_notes_raw'] == {"test": "data"}
        assert call_args[1]['p_source_raw'] == {"raw": "data"}
        assert call_args[1]['p_status'] == "active"
    
    def test_upsert_variant_success(self):
        """Test successful variant upsert."""
        mock_result = Mock()
        mock_result.data = ["variant-123"]
        self.mock_supabase.rpc.return_value.execute.return_value = mock_result
        
        result = self.rpc_client.upsert_variant(
            coffee_id="coffee-123",
            platform_variant_id="var-123",
            sku="SKU123",
            weight_g=250,
            currency="USD",
            in_stock=True,
            compare_at_price=29.99
        )
        
        assert result == "variant-123"
        assert self.rpc_client.rpc_stats['successful_calls'] == 1
        
        # Verify RPC was called with correct parameters
        call_args = self.mock_supabase.rpc.call_args[0]
        assert call_args[0] == 'rpc_upsert_variant'
        assert call_args[1]['p_coffee_id'] == "coffee-123"
        assert call_args[1]['p_platform_variant_id'] == "var-123"
        assert call_args[1]['p_sku'] == "SKU123"
        assert call_args[1]['p_weight_g'] == 250
        assert call_args[1]['p_currency'] == "USD"
        assert call_args[1]['p_in_stock'] is True
        assert call_args[1]['p_compare_at_price'] == 29.99
    
    def test_insert_price_success(self):
        """Test successful price insertion."""
        mock_result = Mock()
        mock_result.data = ["price-123"]
        self.mock_supabase.rpc.return_value.execute.return_value = mock_result
        
        result = self.rpc_client.insert_price(
            variant_id="variant-123",
            price=24.99,
            currency="USD",
            is_sale=True,
            scraped_at="2024-01-01T12:00:00Z"
        )
        
        assert result == "price-123"
        assert self.rpc_client.rpc_stats['successful_calls'] == 1
        
        # Verify RPC was called with correct parameters
        call_args = self.mock_supabase.rpc.call_args[0]
        assert call_args[0] == 'rpc_insert_price'
        assert call_args[1]['p_variant_id'] == "variant-123"
        assert call_args[1]['p_price'] == 24.99
        assert call_args[1]['p_currency'] == "USD"
        assert call_args[1]['p_is_sale'] is True
        assert call_args[1]['p_scraped_at'] == "2024-01-01T12:00:00Z"
    
    def test_upsert_coffee_image_success(self):
        """Test successful coffee image upsert."""
        mock_result = Mock()
        mock_result.data = ["image-123"]
        self.mock_supabase.rpc.return_value.execute.return_value = mock_result
        
        result = self.rpc_client.upsert_coffee_image(
            coffee_id="coffee-123",
            url="https://test.com/image.jpg",
            alt="Test image",
            width=800,
            height=600,
            sort_order=1
        )
        
        assert result == "image-123"
        assert self.rpc_client.rpc_stats['successful_calls'] == 1
        
        # Verify RPC was called with correct parameters
        call_args = self.mock_supabase.rpc.call_args[0]
        assert call_args[0] == 'rpc_upsert_coffee_image'
        assert call_args[1]['p_coffee_id'] == "coffee-123"
        assert call_args[1]['p_url'] == "https://test.com/image.jpg"
        assert call_args[1]['p_alt'] == "Test image"
        assert call_args[1]['p_width'] == 800
        assert call_args[1]['p_height'] == 600
        assert call_args[1]['p_sort_order'] == 1
    
    def test_rpc_network_error_retry(self):
        """Test RPC network error with retry logic."""
        # Mock network error on first call, success on second
        mock_result_fail = Mock()
        mock_result_fail.data = None
        mock_result_fail.error = "Connection timeout"
        
        mock_result_success = Mock()
        mock_result_success.data = ["coffee-123"]
        
        self.mock_supabase.rpc.return_value.execute.side_effect = [
            Exception("Connection timeout"),
            mock_result_success
        ]
        
        result = self.rpc_client.upsert_coffee(
            bean_species="arabica",
            name="Test Coffee",
            slug="test-coffee",
            roaster_id="roaster-123",
            process="washed",
            process_raw="Fully Washed",
            roast_level="light",
            roast_level_raw="Light Roast",
            roast_style_raw="City Roast",
            description_md="# Test Coffee\nA test coffee.",
            direct_buy_url="https://test.com/coffee",
            platform_product_id="prod-123"
        )
        
        assert result == "coffee-123"
        assert self.rpc_client.rpc_stats['total_calls'] == 1
        assert self.rpc_client.rpc_stats['successful_calls'] == 1
        assert self.rpc_client.rpc_stats['failed_calls'] == 0
        assert self.rpc_client.rpc_stats['retry_attempts'] == 1
        assert self.rpc_client.rpc_stats['network_errors'] == 1
    
    def test_rpc_constraint_error_no_retry(self):
        """Test RPC constraint error without retry."""
        # Mock constraint error
        self.mock_supabase.rpc.return_value.execute.side_effect = Exception("Unique constraint violation")
        
        with pytest.raises(RPCError):
            self.rpc_client.upsert_coffee(
                bean_species="arabica",
                name="Test Coffee",
                slug="test-coffee",
                roaster_id="roaster-123",
                process="washed",
                process_raw="Fully Washed",
                roast_level="light",
                roast_level_raw="Light Roast",
                roast_style_raw="City Roast",
                description_md="# Test Coffee\nA test coffee.",
                direct_buy_url="https://test.com/coffee",
                platform_product_id="prod-123"
            )
        
        assert self.rpc_client.rpc_stats['total_calls'] == 1
        assert self.rpc_client.rpc_stats['successful_calls'] == 0
        assert self.rpc_client.rpc_stats['failed_calls'] == 1
        assert self.rpc_client.rpc_stats['constraint_errors'] == 1
        assert self.rpc_client.rpc_stats['retry_attempts'] == 0
    
    def test_rpc_validation_error_no_retry(self):
        """Test RPC validation error without retry."""
        # Mock validation error
        self.mock_supabase.rpc.return_value.execute.side_effect = Exception("Invalid parameter type")
        
        with pytest.raises(RPCError):
            self.rpc_client.upsert_coffee(
                bean_species="arabica",
                name="Test Coffee",
                slug="test-coffee",
                roaster_id="roaster-123",
                process="washed",
                process_raw="Fully Washed",
                roast_level="light",
                roast_level_raw="Light Roast",
                roast_style_raw="City Roast",
                description_md="# Test Coffee\nA test coffee.",
                direct_buy_url="https://test.com/coffee",
                platform_product_id="prod-123"
            )
        
        assert self.rpc_client.rpc_stats['total_calls'] == 1
        assert self.rpc_client.rpc_stats['successful_calls'] == 0
        assert self.rpc_client.rpc_stats['failed_calls'] == 1
        assert self.rpc_client.rpc_stats['validation_errors'] == 1
        assert self.rpc_client.rpc_stats['retry_attempts'] == 0
    
    def test_rpc_max_retries_exceeded(self):
        """Test RPC call with max retries exceeded."""
        # Mock persistent network error
        self.mock_supabase.rpc.return_value.execute.side_effect = Exception("Connection timeout")
        
        with pytest.raises(RPCError, match="RPC call failed after 2 retries"):
            self.rpc_client.upsert_coffee(
                bean_species="arabica",
                name="Test Coffee",
                slug="test-coffee",
                roaster_id="roaster-123",
                process="washed",
                process_raw="Fully Washed",
                roast_level="light",
                roast_level_raw="Light Roast",
                roast_style_raw="City Roast",
                description_md="# Test Coffee\nA test coffee.",
                direct_buy_url="https://test.com/coffee",
                platform_product_id="prod-123"
            )
        
        assert self.rpc_client.rpc_stats['total_calls'] == 1
        assert self.rpc_client.rpc_stats['successful_calls'] == 0
        assert self.rpc_client.rpc_stats['failed_calls'] == 1
        assert self.rpc_client.rpc_stats['retry_attempts'] == 2
        assert self.rpc_client.rpc_stats['network_errors'] == 1
    
    def test_rpc_no_data_returned(self):
        """Test RPC call that returns no data."""
        mock_result = Mock()
        mock_result.data = None
        mock_result.error = "No data returned"
        self.mock_supabase.rpc.return_value.execute.return_value = mock_result
        
        with pytest.raises(RPCError, match="RPC rpc_upsert_coffee returned no data"):
            self.rpc_client.upsert_coffee(
                bean_species="arabica",
                name="Test Coffee",
                slug="test-coffee",
                roaster_id="roaster-123",
                process="washed",
                process_raw="Fully Washed",
                roast_level="light",
                roast_level_raw="Light Roast",
                roast_style_raw="City Roast",
                description_md="# Test Coffee\nA test coffee.",
                direct_buy_url="https://test.com/coffee",
                platform_product_id="prod-123"
            )
    
    def test_classify_error(self):
        """Test error classification."""
        # Test constraint error
        constraint_error = Exception("Unique constraint violation")
        assert self.rpc_client._classify_error(constraint_error) == 'constraint'
        
        # Test network error
        network_error = Exception("Connection timeout")
        assert self.rpc_client._classify_error(network_error) == 'network'
        
        # Test validation error
        validation_error = Exception("Invalid parameter type")
        assert self.rpc_client._classify_error(validation_error) == 'validation'
        
        # Test unknown error (defaults to network for retry logic)
        unknown_error = Exception("Unknown error")
        assert self.rpc_client._classify_error(unknown_error) == 'network'
    
    def test_get_rpc_stats(self):
        """Test RPC statistics retrieval."""
        # Set some stats
        self.rpc_client.rpc_stats['total_calls'] = 10
        self.rpc_client.rpc_stats['successful_calls'] = 8
        self.rpc_client.rpc_stats['failed_calls'] = 2
        self.rpc_client.rpc_stats['retry_attempts'] = 3
        
        stats = self.rpc_client.get_rpc_stats()
        
        assert stats['total_calls'] == 10
        assert stats['successful_calls'] == 8
        assert stats['failed_calls'] == 2
        assert stats['retry_attempts'] == 3
        assert stats['success_rate'] == 0.8
        assert stats['failure_rate'] == 0.2
        assert stats['retry_rate'] == 0.3
    
    def test_reset_stats(self):
        """Test RPC statistics reset."""
        # Set some stats
        self.rpc_client.rpc_stats['total_calls'] = 10
        self.rpc_client.rpc_stats['successful_calls'] = 8
        
        self.rpc_client.reset_stats()
        
        assert self.rpc_client.rpc_stats['total_calls'] == 0
        assert self.rpc_client.rpc_stats['successful_calls'] == 0
        assert self.rpc_client.rpc_stats['failed_calls'] == 0
        assert self.rpc_client.rpc_stats['retry_attempts'] == 0
        assert self.rpc_client.rpc_stats['constraint_errors'] == 0
        assert self.rpc_client.rpc_stats['network_errors'] == 0
        assert self.rpc_client.rpc_stats['validation_errors'] == 0
