"""
Tests for ImageKit service functionality.
"""

import pytest
from unittest.mock import MagicMock, patch
from src.images.imagekit_service import ImageKitService, ImageKitResult
from src.config.imagekit_config import ImageKitConfig
import time


@pytest.fixture
def imagekit_config():
    """Create ImageKit configuration for testing."""
    return ImageKitConfig(
        public_key="public_test_key",
        private_key="private_test_key",
        url_endpoint="https://ik.imagekit.io/test",
        folder="/coffee-images/",
        enabled=True
    )


@pytest.fixture
def imagekit_service(imagekit_config):
    """Create ImageKit service for testing."""
    return ImageKitService(imagekit_config, max_retries=3, backoff_factor=2.0)


def test_imagekit_service_init(imagekit_service, imagekit_config):
    """Test ImageKit service initialization."""
    assert imagekit_service.config == imagekit_config
    assert imagekit_service.max_retries == 3
    assert imagekit_service.stats['uploads_successful'] == 0
    assert imagekit_service.stats['uploads_failed'] == 0


def test_generate_filename(imagekit_service):
    """Test filename generation from image URL."""
    # Test with full URL
    url1 = "https://example.com/images/coffee1.jpg"
    filename1 = imagekit_service._generate_filename(url1)
    assert filename1 == "coffee1.jpg"
    
    # Test with URL without extension
    url2 = "https://example.com/images/coffee2"
    filename2 = imagekit_service._generate_filename(url2)
    assert filename2 == "coffee2"
    
    # Test with complex URL
    url3 = "https://example.com/path/to/image.png?version=123"
    filename3 = imagekit_service._generate_filename(url3)
    assert filename3 == "image.png"


@patch('src.images.imagekit_service.ImageKit.upload_file')
def test_upload_image_success(mock_upload_file, imagekit_service):
    """Test successful image upload."""
    mock_result = MagicMock()
    mock_result.url = "https://ik.imagekit.io/test/coffee-images/test.jpg"
    mock_result.fileId = "file_123"
    mock_upload_file.return_value = mock_result
    
    result = imagekit_service.upload_image(
        image_url="https://example.com/test.jpg",
        content=b"test image content"
    )
    
    assert result.success is True
    assert result.imagekit_url == "https://ik.imagekit.io/test/coffee-images/test.jpg"
    assert result.file_id == "file_123"


@patch('src.images.imagekit_service.ImageKit.upload_file')
def test_upload_image_failure(mock_upload_file, imagekit_service):
    """Test failed image upload."""
    mock_upload_file.side_effect = Exception("Network timeout")
    
    result = imagekit_service.upload_image(
        image_url="https://example.com/test.jpg",
        content=b"test image content"
    )
    
    assert result.success is False
    assert "Network timeout" in result.error


@patch('src.images.imagekit_service.ImageKit.upload_file')
def test_upload_image_with_retry_success(mock_upload_file, imagekit_service):
    """Test image upload with retry logic that eventually succeeds."""
    # First call fails, second succeeds
    mock_upload_file.side_effect = [
        Exception("Temporary network error"),
        MagicMock(url="https://ik.imagekit.io/test/coffee-images/test.jpg", fileId="file_123")
    ]
    
    result = imagekit_service.upload_image(
        image_url="https://example.com/test.jpg",
        content=b"test image content"
    )
    
    assert result.success is True
    assert result.imagekit_url == "https://ik.imagekit.io/test/coffee-images/test.jpg"
    assert result.file_id == "file_123"
    assert mock_upload_file.call_count == 2


@patch('src.images.imagekit_service.ImageKit.upload_file')
def test_upload_image_retry_exhausted(mock_upload_file, imagekit_service):
    """Test image upload with retry logic that eventually fails."""
    mock_upload_file.side_effect = Exception("Persistent network error")
    
    result = imagekit_service.upload_image(
        image_url="https://example.com/test.jpg",
        content=b"test image content"
    )
    
    assert result.success is False
    assert "Persistent network error" in result.error
    assert mock_upload_file.call_count == 4  # 1 initial + 3 retries


def test_upload_image_disabled(imagekit_config):
    """Test upload when ImageKit is disabled."""
    imagekit_config.enabled = False
    service = ImageKitService(imagekit_config)
    
    result = service.upload_image(
        image_url="https://example.com/test.jpg",
        content=b"test image content"
    )
    
    assert result.success is False
    assert result.error == "ImageKit upload disabled"


def test_get_stats(imagekit_service):
    """Test statistics tracking."""
    # Initial stats
    stats = imagekit_service.get_stats()
    assert stats['uploads_attempted'] == 0
    assert stats['success_rate'] == 0.0
    
    # Simulate some uploads
    imagekit_service.stats['uploads_attempted'] = 10
    imagekit_service.stats['uploads_successful'] = 7
    imagekit_service.stats['uploads_failed'] = 3
    imagekit_service.stats['total_upload_time'] = 15.0
    
    stats = imagekit_service.get_stats()
    assert stats['uploads_attempted'] == 10
    assert stats['success_rate'] == 0.7
    assert stats['failure_rate'] == 0.3
    assert stats['avg_upload_time'] == 15.0 / 7


def test_reset_stats(imagekit_service):
    """Test statistics reset."""
    # Set some stats
    imagekit_service.stats['uploads_attempted'] = 5
    imagekit_service.stats['uploads_successful'] = 3
    
    # Reset
    imagekit_service.reset_stats()
    
    assert imagekit_service.stats['uploads_attempted'] == 0
    assert imagekit_service.stats['uploads_successful'] == 0
    assert imagekit_service.stats['uploads_failed'] == 0
    assert imagekit_service.stats['total_upload_time'] == 0.0