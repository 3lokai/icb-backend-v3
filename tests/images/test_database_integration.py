"""
Database integration tests for image deduplication functionality.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import json

from src.images.deduplication_service import ImageDeduplicationService
from src.images.hash_computation import ImageHashComputer
from src.validator.rpc_client import RPCClient


class TestImageDeduplicationDatabaseIntegration:
    """Test cases for image deduplication database integration."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_supabase_client = Mock()
        self.mock_rpc_client = Mock(spec=RPCClient)
        self.mock_hash_computer = Mock(spec=ImageHashComputer)
        
        # Mock RPC client methods
        self.mock_rpc_client.supabase_client = self.mock_supabase_client
        
        self.deduplication_service = ImageDeduplicationService(
            rpc_client=self.mock_rpc_client,
            hash_computer=self.mock_hash_computer
        )
    
    def test_check_duplicate_hash_existing_image(self):
        """Test checking for duplicate hash when image exists."""
        # Mock RPC client response
        self.mock_rpc_client.check_content_hash.return_value = 'existing-image-123'
        
        # Test duplicate check
        result = self.deduplication_service._check_duplicate_hash('test_hash_123')
        
        # Verify result
        assert result == 'existing-image-123'
        
        # Verify RPC call was made
        self.mock_rpc_client.check_content_hash.assert_called_once_with('test_hash_123')
    
    def test_check_duplicate_hash_no_existing_image(self):
        """Test checking for duplicate hash when no image exists."""
        # Mock RPC client response (no results)
        self.mock_rpc_client.check_content_hash.return_value = None
        
        # Test duplicate check
        result = self.deduplication_service._check_duplicate_hash('new_hash_456')
        
        # Verify result
        assert result is None
        
        # Verify RPC call was made
        self.mock_rpc_client.check_content_hash.assert_called_once_with('new_hash_456')
    
    def test_check_duplicate_hash_database_error(self):
        """Test checking for duplicate hash with database error."""
        # Mock RPC client error
        self.mock_rpc_client.check_content_hash.side_effect = Exception("Database connection failed")
        
        # Test should handle error gracefully
        result = self.deduplication_service._check_duplicate_hash('test_hash_789')
        
        # Should return None to allow processing to continue
        assert result is None
    
    def test_process_image_with_deduplication_database_integration(self):
        """Test full deduplication process with database integration."""
        # Test data
        image_data = {
            'url': 'https://example.com/image.jpg',
            'alt': 'Test image',
            'width': 800,
            'height': 600
        }
        coffee_id = 'coffee-123'
        
        # Mock hash computation
        self.mock_hash_computer.compute_image_hash.return_value = 'hash123'
        
        # Mock RPC client responses
        self.mock_rpc_client.check_content_hash.return_value = None  # No duplicates found
        
        # Process image
        result = self.deduplication_service.process_image_with_deduplication(
            image_data, coffee_id
        )
        
        # Verify result
        assert result['url'] == 'https://example.com/image.jpg'
        assert result['content_hash'] == 'hash123'
        assert result['is_duplicate'] is False
        assert result['deduplication_status'] == 'new_image'
        
        # Verify RPC calls
        self.mock_rpc_client.check_content_hash.assert_called_once_with('hash123')
    
    def test_process_image_with_deduplication_duplicate_found(self):
        """Test deduplication when duplicate is found in database."""
        # Test data
        image_data = {
            'url': 'https://example.com/duplicate.jpg',
            'alt': 'Duplicate image'
        }
        coffee_id = 'coffee-456'
        
        # Mock hash computation
        self.mock_hash_computer.compute_image_hash.return_value = 'duplicate_hash_789'
        
        # Mock RPC client response (duplicate found)
        self.mock_rpc_client.check_content_hash.return_value = 'existing-image-789'
        
        # Process image
        result = self.deduplication_service.process_image_with_deduplication(
            image_data, coffee_id
        )
        
        # Verify result
        assert result['image_id'] == 'existing-image-789'
        assert result['url'] == 'https://example.com/duplicate.jpg'
        assert result['content_hash'] == 'duplicate_hash_789'
        assert result['is_duplicate'] is True
        assert result['deduplication_status'] == 'skipped_duplicate'
        
        # Verify RPC call was made
        self.mock_rpc_client.check_content_hash.assert_called_once_with('duplicate_hash_789')
    
    def test_batch_processing_database_integration(self):
        """Test batch processing with database integration."""
        # Test data
        images_data = [
            {'url': 'https://example.com/image1.jpg', 'alt': 'Image 1'},
            {'url': 'https://example.com/image2.jpg', 'alt': 'Image 2'},
            {'url': 'https://example.com/image3.jpg', 'alt': 'Image 3'}
        ]
        coffee_id = 'coffee-789'
        
        # Mock hash computation
        self.mock_hash_computer.compute_image_hash.side_effect = ['hash1', 'hash2', 'hash3']
        
        # Mock RPC client responses (no duplicates found)
        self.mock_rpc_client.check_content_hash.side_effect = [None, None, None]  # No duplicates
        self.mock_rpc_client.upsert_coffee_image.side_effect = ['new-image-123', 'new-image-124', 'new-image-125']
        
        # Process batch
        results = self.deduplication_service.process_batch_with_deduplication(
            images_data, coffee_id
        )
        
        # Verify results
        assert len(results) == 3
        for i, result in enumerate(results):
            assert result['url'] == f'https://example.com/image{i+1}.jpg'
            assert result['content_hash'] == f'hash{i+1}'
            assert result['is_duplicate'] is False
            assert result['deduplication_status'] == 'new_image'
        
        # Verify RPC client calls (only duplicate checks, not upserts)
        assert self.mock_rpc_client.check_content_hash.call_count == 3
        
        # Verify all duplicate checks were made
        for i in range(3):
            self.mock_rpc_client.check_content_hash.assert_any_call(f'hash{i+1}')
    
    def test_database_error_handling(self):
        """Test error handling for database failures."""
        # Test data
        image_data = {
            'url': 'https://example.com/error.jpg',
            'alt': 'Error image'
        }
        coffee_id = 'coffee-error'
        
        # Mock hash computation
        self.mock_hash_computer.compute_image_hash.return_value = 'error_hash'
        
        # Mock database error
        self.mock_rpc_client.check_content_hash.side_effect = Exception("Database connection lost")
        
        # Process image (should handle error gracefully)
        result = self.deduplication_service.process_image_with_deduplication(
            image_data, coffee_id
        )
        
        # Should proceed as new image (error handling allows continuation)
        assert result['url'] == 'https://example.com/error.jpg'
        assert result['content_hash'] == 'error_hash'
        assert result['is_duplicate'] is False
        assert result['deduplication_status'] == 'new_image'
    
    def test_performance_with_large_batch(self):
        """Test performance with large batch of images."""
        # Create large batch of test images
        images_data = [
            {'url': f'https://example.com/image{i}.jpg', 'alt': f'Image {i}'}
            for i in range(100)
        ]
        coffee_id = 'coffee-performance'
        
        # Mock hash computation
        self.mock_hash_computer.compute_image_hash.side_effect = [
            f'hash{i}' for i in range(100)
        ]
        
        # Mock database responses (no duplicates)
        self.mock_rpc_client.check_content_hash.return_value = None
        
        # Process batch
        results = self.deduplication_service.process_batch_with_deduplication(
            images_data, coffee_id
        )
        
        # Verify all images were processed
        assert len(results) == 100
        
        # Verify all database calls were made
        assert self.mock_rpc_client.check_content_hash.call_count == 100
        
        # Verify performance stats
        stats = self.deduplication_service.get_deduplication_stats()
        assert stats['images_processed'] == 100
        assert stats['new_images'] == 100
        assert stats['duplicates_found'] == 0
