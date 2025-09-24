"""
Unit tests for image deduplication service functionality.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from src.images.deduplication_service import ImageDeduplicationService, ImageDeduplicationError
from src.images.hash_computation import ImageHashComputer


class TestImageDeduplicationService:
    """Test cases for ImageDeduplicationService."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_rpc_client = Mock()
        self.mock_hash_computer = Mock(spec=ImageHashComputer)
        self.deduplication_service = ImageDeduplicationService(
            rpc_client=self.mock_rpc_client,
            hash_computer=self.mock_hash_computer
        )
    
    def test_process_image_with_deduplication_new_image(self):
        """Test processing new image (no duplicate)."""
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
        
        # Mock duplicate check (no duplicate found)
        with patch.object(self.deduplication_service, '_check_duplicate_hash') as mock_check:
            mock_check.return_value = None
            
            result = self.deduplication_service.process_image_with_deduplication(
                image_data, coffee_id
            )
        
        # Verify result
        assert result['url'] == 'https://example.com/image.jpg'
        assert result['content_hash'] == 'hash123'
        assert result['is_duplicate'] is False
        assert result['deduplication_status'] == 'new_image'
        
        # Verify hash computation was called
        self.mock_hash_computer.compute_image_hash.assert_called_once_with(
            'https://example.com/image.jpg'
        )
        
        # Verify stats
        assert self.deduplication_service.stats['images_processed'] == 1
        assert self.deduplication_service.stats['new_images'] == 1
        assert self.deduplication_service.stats['duplicates_found'] == 0
    
    def test_process_image_with_deduplication_duplicate_found(self):
        """Test processing duplicate image."""
        # Test data
        image_data = {
            'url': 'https://example.com/image.jpg',
            'alt': 'Test image'
        }
        coffee_id = 'coffee-123'
        
        # Mock hash computation
        self.mock_hash_computer.compute_image_hash.return_value = 'hash123'
        
        # Mock duplicate check (duplicate found)
        with patch.object(self.deduplication_service, '_check_duplicate_hash') as mock_check:
            mock_check.return_value = 'existing-image-456'
            
            result = self.deduplication_service.process_image_with_deduplication(
                image_data, coffee_id
            )
        
        # Verify result
        assert result['image_id'] == 'existing-image-456'
        assert result['url'] == 'https://example.com/image.jpg'
        assert result['content_hash'] == 'hash123'
        assert result['is_duplicate'] is True
        assert result['deduplication_status'] == 'skipped_duplicate'
        
        # Verify stats
        assert self.deduplication_service.stats['images_processed'] == 1
        assert self.deduplication_service.stats['duplicates_found'] == 1
        assert self.deduplication_service.stats['new_images'] == 0
    
    def test_process_image_with_deduplication_missing_url(self):
        """Test processing image with missing URL."""
        # Test data without URL
        image_data = {
            'alt': 'Test image'
        }
        coffee_id = 'coffee-123'
        
        # Should raise error
        with pytest.raises(ImageDeduplicationError):
            self.deduplication_service.process_image_with_deduplication(
                image_data, coffee_id
            )
        
        # Verify stats
        assert self.deduplication_service.stats['deduplication_errors'] == 1
    
    def test_process_image_with_deduplication_hash_computation_error(self):
        """Test processing image with hash computation error."""
        # Test data
        image_data = {
            'url': 'https://example.com/image.jpg',
            'alt': 'Test image'
        }
        coffee_id = 'coffee-123'
        
        # Mock hash computation failure
        self.mock_hash_computer.compute_image_hash.side_effect = Exception("Hash computation failed")
        
        # Should raise error
        with pytest.raises(ImageDeduplicationError):
            self.deduplication_service.process_image_with_deduplication(
                image_data, coffee_id
            )
        
        # Verify stats
        assert self.deduplication_service.stats['deduplication_errors'] == 1
    
    def test_process_batch_with_deduplication_success(self):
        """Test successful batch processing."""
        # Test data
        images_data = [
            {'url': 'https://example.com/image1.jpg', 'alt': 'Image 1'},
            {'url': 'https://example.com/image2.jpg', 'alt': 'Image 2'},
            {'url': 'https://example.com/image3.jpg', 'alt': 'Image 3'}
        ]
        coffee_id = 'coffee-123'
        
        # Mock hash computation
        self.mock_hash_computer.compute_image_hash.side_effect = ['hash1', 'hash2', 'hash3']
        
        # Mock duplicate check (no duplicates)
        with patch.object(self.deduplication_service, '_check_duplicate_hash') as mock_check:
            mock_check.return_value = None
            
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
        
        # Verify stats
        assert self.deduplication_service.stats['images_processed'] == 3
        assert self.deduplication_service.stats['new_images'] == 3
        assert self.deduplication_service.stats['duplicates_found'] == 0
    
    def test_process_batch_with_deduplication_mixed_results(self):
        """Test batch processing with mixed results (some duplicates, some errors)."""
        # Test data
        images_data = [
            {'url': 'https://example.com/image1.jpg', 'alt': 'Image 1'},
            {'url': 'https://example.com/image2.jpg', 'alt': 'Image 2'},
            {'url': 'https://example.com/image3.jpg', 'alt': 'Image 3'}
        ]
        coffee_id = 'coffee-123'
        
        # Mock hash computation
        self.mock_hash_computer.compute_image_hash.side_effect = [
            'hash1',
            Exception("Hash computation failed"),
            'hash3'
        ]
        
        # Mock duplicate check - only for successful hash computations
        with patch.object(self.deduplication_service, '_check_duplicate_hash') as mock_check:
            # Only the first and third images will reach duplicate check
            mock_check.side_effect = [None, 'existing-image-456']
            
            results = self.deduplication_service.process_batch_with_deduplication(
                images_data, coffee_id
            )
        
        # Verify results
        assert len(results) == 3
        
        # First image: new
        assert results[0]['url'] == 'https://example.com/image1.jpg'
        assert results[0]['content_hash'] == 'hash1'
        assert results[0]['is_duplicate'] is False
        
        # Second image: error
        assert results[1]['url'] == 'https://example.com/image2.jpg'
        assert 'error' in results[1]
        assert results[1]['deduplication_status'] == 'error'
        
        # Third image: duplicate
        assert results[2]['url'] == 'https://example.com/image3.jpg'
        assert results[2]['content_hash'] == 'hash3'
        assert results[2]['is_duplicate'] is True
        assert results[2]['deduplication_status'] == 'skipped_duplicate'
    
    def test_check_duplicate_hash_implementation(self):
        """Test duplicate hash check with database integration."""
        # Mock RPC client response
        self.mock_rpc_client.check_content_hash.return_value = None
        
        # Test with no duplicate found
        result = self.deduplication_service._check_duplicate_hash('test_hash')
        
        assert result is None
        self.mock_rpc_client.check_content_hash.assert_called_once_with('test_hash')
    
    def test_check_duplicate_hash_duplicate_found(self):
        """Test duplicate hash check when duplicate is found."""
        # Mock RPC client response (duplicate found)
        self.mock_rpc_client.check_content_hash.return_value = 'existing-image-123'
        
        # Test with duplicate found
        result = self.deduplication_service._check_duplicate_hash('test_hash')
        
        assert result == 'existing-image-123'
        self.mock_rpc_client.check_content_hash.assert_called_once_with('test_hash')
    
    def test_check_duplicate_hash_rpc_error(self):
        """Test duplicate hash check with RPC error."""
        # Mock RPC client error
        self.mock_rpc_client.check_content_hash.side_effect = Exception("RPC error")
        
        # Test with RPC error (should return None to allow processing to continue)
        result = self.deduplication_service._check_duplicate_hash('test_hash')
        
        assert result is None
        self.mock_rpc_client.check_content_hash.assert_called_once_with('test_hash')
    
    def test_get_deduplication_stats(self):
        """Test deduplication statistics retrieval."""
        # Set some stats
        self.deduplication_service.stats['images_processed'] = 10
        self.deduplication_service.stats['duplicates_found'] = 3
        self.deduplication_service.stats['new_images'] = 6
        self.deduplication_service.stats['deduplication_errors'] = 1
        
        # Mock hash computer stats
        self.mock_hash_computer.get_stats.return_value = {
            'content_hashes_computed': 5,
            'header_hashes_computed': 5,
            'failed_computations': 0
        }
        
        stats = self.deduplication_service.get_deduplication_stats()
        
        # Verify basic stats
        assert stats['images_processed'] == 10
        assert stats['duplicates_found'] == 3
        assert stats['new_images'] == 6
        assert stats['deduplication_errors'] == 1
        
        # Verify calculated rates
        assert stats['duplicate_rate'] == 0.3  # 3/10
        assert stats['new_image_rate'] == 0.6  # 6/10
        assert stats['error_rate'] == 0.1  # 1/10
        
        # Verify hash computation stats are included
        assert 'hash_computation' in stats
        assert stats['hash_computation']['content_hashes_computed'] == 5
    
    def test_reset_stats(self):
        """Test statistics reset."""
        # Set some stats
        self.deduplication_service.stats['images_processed'] = 5
        self.deduplication_service.stats['duplicates_found'] = 2
        
        # Reset stats
        self.deduplication_service.reset_stats()
        
        # Verify reset
        assert self.deduplication_service.stats['images_processed'] == 0
        assert self.deduplication_service.stats['duplicates_found'] == 0
        
        # Verify hash computer stats were also reset
        self.mock_hash_computer.reset_stats.assert_called_once()
