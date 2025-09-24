"""
Unit tests for image hash computation functionality.
"""

import pytest
import hashlib
from unittest.mock import Mock, patch, MagicMock
import requests

from src.images.hash_computation import ImageHashComputer, ImageHashComputationError


class TestImageHashComputer:
    """Test cases for ImageHashComputer."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.hash_computer = ImageHashComputer(timeout=5, max_retries=1)
    
    def test_compute_content_hash_success(self):
        """Test successful content hash computation."""
        # Test data
        test_content = b"test image content"
        expected_hash = hashlib.sha256(test_content).hexdigest()
        
        # Compute hash
        result = self.hash_computer._compute_content_hash(test_content)
        
        # Verify result
        assert result == expected_hash
        assert len(result) == 64  # SHA256 hex length
        assert result.isalnum()  # Should be alphanumeric
    
    def test_compute_content_hash_empty_content(self):
        """Test content hash computation with empty content."""
        with pytest.raises(ImageHashComputationError):
            self.hash_computer._compute_content_hash(b"")
    
    def test_compute_content_hash_none_content(self):
        """Test content hash computation with None content."""
        with pytest.raises(ImageHashComputationError):
            self.hash_computer._compute_content_hash(None)
    
    def test_compute_header_hash_success(self):
        """Test successful header hash computation."""
        # Mock response with headers
        mock_response = Mock()
        mock_response.headers = {
            'ETag': '"abc123"',
            'Last-Modified': 'Wed, 21 Oct 2015 07:28:00 GMT'
        }
        mock_response.raise_for_status.return_value = None
        
        # Mock the session's head method
        self.hash_computer.session.head = Mock(return_value=mock_response)
        
        # Test hash computation
        result = self.hash_computer._compute_header_hash("https://example.com/image.jpg")
        
        # Verify result
        assert result is not None
        assert len(result) == 64  # SHA256 hex length
        assert result.isalnum()  # Should be alphanumeric
        
        # Verify session was called
        self.hash_computer.session.head.assert_called_once_with(
            "https://example.com/image.jpg", 
            timeout=5
        )
    
    @patch('src.images.hash_computation.requests.Session')
    def test_compute_header_hash_no_headers(self, mock_session_class):
        """Test header hash computation with no relevant headers."""
        # Mock response without headers
        mock_response = Mock()
        mock_response.headers = {}
        mock_response.raise_for_status.return_value = None
        
        # Mock session
        mock_session = Mock()
        mock_session.head.return_value = mock_response
        mock_session_class.return_value = mock_session
        
        # Test should raise error
        with pytest.raises(ImageHashComputationError):
            self.hash_computer._compute_header_hash("https://example.com/image.jpg")
    
    @patch('src.images.hash_computation.requests.Session')
    def test_compute_header_hash_request_failure(self, mock_session_class):
        """Test header hash computation with request failure."""
        # Mock session that raises exception
        mock_session = Mock()
        mock_session.head.side_effect = requests.RequestException("Network error")
        mock_session_class.return_value = mock_session
        
        # Test should raise error
        with pytest.raises(ImageHashComputationError):
            self.hash_computer._compute_header_hash("https://example.com/image.jpg")
    
    def test_compute_image_hash_with_content(self):
        """Test image hash computation with provided content."""
        test_content = b"test image content"
        expected_hash = hashlib.sha256(test_content).hexdigest()
        
        result = self.hash_computer.compute_image_hash(
            "https://example.com/image.jpg",
            content=test_content
        )
        
        assert result == expected_hash
        assert self.hash_computer.stats['content_hashes_computed'] == 1
    
    @patch('src.images.hash_computation.ImageHashComputer._compute_header_hash')
    def test_compute_image_hash_without_content(self, mock_header_hash):
        """Test image hash computation without content (header-based)."""
        mock_header_hash.return_value = "header_hash_123"
        
        result = self.hash_computer.compute_image_hash("https://example.com/image.jpg")
        
        assert result == "header_hash_123"
        assert self.hash_computer.stats['header_hashes_computed'] == 1
        mock_header_hash.assert_called_once_with("https://example.com/image.jpg")
    
    def test_compute_image_hash_caching(self):
        """Test image hash computation with caching."""
        test_content = b"test image content"
        
        # First computation
        result1 = self.hash_computer.compute_image_hash(
            "https://example.com/image.jpg",
            content=test_content,
            use_cache=True
        )
        
        # Second computation (should use cache)
        result2 = self.hash_computer.compute_image_hash(
            "https://example.com/image.jpg",
            content=test_content,
            use_cache=True
        )
        
        assert result1 == result2
        assert self.hash_computer.stats['cache_hits'] == 1
        assert self.hash_computer.stats['content_hashes_computed'] == 1  # Only computed once
    
    def test_compute_image_hash_error_handling(self):
        """Test image hash computation error handling."""
        with pytest.raises(ImageHashComputationError):
            self.hash_computer.compute_image_hash("invalid_url")
        
        assert self.hash_computer.stats['failed_computations'] == 1
    
    def test_compute_batch_hashes_success(self):
        """Test successful batch hash computation."""
        test_urls = [
            "https://example.com/image1.jpg",
            "https://example.com/image2.jpg",
            "https://example.com/image3.jpg"
        ]
        
        with patch.object(self.hash_computer, 'compute_image_hash') as mock_compute:
            mock_compute.side_effect = ["hash1", "hash2", "hash3"]
            
            results = self.hash_computer.compute_batch_hashes(test_urls)
            
            assert len(results) == 3
            assert results["https://example.com/image1.jpg"] == "hash1"
            assert results["https://example.com/image2.jpg"] == "hash2"
            assert results["https://example.com/image3.jpg"] == "hash3"
    
    def test_compute_batch_hashes_with_failures(self):
        """Test batch hash computation with some failures."""
        test_urls = [
            "https://example.com/image1.jpg",
            "https://example.com/image2.jpg",
            "https://example.com/image3.jpg"
        ]
        
        with patch.object(self.hash_computer, 'compute_image_hash') as mock_compute:
            mock_compute.side_effect = [
                "hash1",
                ImageHashComputationError("Failed"),
                "hash3"
            ]
            
            results = self.hash_computer.compute_batch_hashes(test_urls)
            
            # Should have 2 successful results
            assert len(results) == 2
            assert results["https://example.com/image1.jpg"] == "hash1"
            assert results["https://example.com/image3.jpg"] == "hash3"
    
    def test_cache_management(self):
        """Test cache size management."""
        # Set small cache size for testing
        self.hash_computer.cache_max_size = 2
        
        # Add items to cache
        self.hash_computer._update_cache("url1", "hash1")
        self.hash_computer._update_cache("url2", "hash2")
        
        assert len(self.hash_computer.hash_cache) == 2
        
        # Add one more item (should trigger cache cleanup)
        self.hash_computer._update_cache("url3", "hash3")
        
        # Cache should be cleaned up
        assert len(self.hash_computer.hash_cache) <= 2
    
    def test_get_stats(self):
        """Test statistics retrieval."""
        # Perform some operations
        self.hash_computer.stats['content_hashes_computed'] = 5
        self.hash_computer.stats['header_hashes_computed'] = 3
        self.hash_computer.stats['failed_computations'] = 2
        self.hash_computer.stats['cache_hits'] = 1
        self.hash_computer.stats['total_processing_time'] = 10.0
        
        stats = self.hash_computer.get_stats()
        
        assert stats['content_hashes_computed'] == 5
        assert stats['header_hashes_computed'] == 3
        assert stats['failed_computations'] == 2
        assert stats['cache_hits'] == 1
        assert stats['success_rate'] == 0.8  # 8/10
        assert stats['failure_rate'] == 0.2  # 2/10
        assert stats['avg_processing_time'] == 1.0  # 10.0/10
    
    def test_reset_stats(self):
        """Test statistics reset."""
        # Set some stats
        self.hash_computer.stats['content_hashes_computed'] = 5
        self.hash_computer.stats['failed_computations'] = 2
        
        # Reset stats
        self.hash_computer.reset_stats()
        
        # Verify reset
        assert self.hash_computer.stats['content_hashes_computed'] == 0
        assert self.hash_computer.stats['failed_computations'] == 0
    
    def test_clear_cache(self):
        """Test cache clearing."""
        # Add items to cache
        self.hash_computer._update_cache("url1", "hash1")
        self.hash_computer._update_cache("url2", "hash2")
        
        assert len(self.hash_computer.hash_cache) == 2
        
        # Clear cache
        self.hash_computer.clear_cache()
        
        assert len(self.hash_computer.hash_cache) == 0
