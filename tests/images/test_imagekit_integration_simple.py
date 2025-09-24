"""
Simplified tests for ImageKit integration service functionality.
"""

import pytest
from unittest.mock import MagicMock, patch
from src.images.imagekit_integration import ImageKitIntegrationService
from src.config.imagekit_config import ImageKitConfig
from src.validator.rpc_client import RPCClient


@pytest.fixture
def mock_rpc_client():
    """Create mock RPC client."""
    return MagicMock(spec=RPCClient)


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
def imagekit_integration_service(mock_rpc_client, imagekit_config):
    """Create ImageKit integration service for testing."""
    return ImageKitIntegrationService(
        rpc_client=mock_rpc_client,
        imagekit_config=imagekit_config,
        enable_deduplication=True,
        enable_imagekit=True
    )


def test_imagekit_integration_init(imagekit_integration_service, imagekit_config):
    """Test ImageKit integration service initialization."""
    assert imagekit_integration_service.imagekit_config == imagekit_config
    assert imagekit_integration_service.enable_deduplication is True
    assert imagekit_integration_service.enable_imagekit is True
    assert imagekit_integration_service.imagekit_service is not None
    assert imagekit_integration_service.deduplication_service is not None


def test_imagekit_integration_init_disabled(mock_rpc_client, imagekit_config):
    """Test ImageKit integration service initialization with services disabled."""
    service = ImageKitIntegrationService(
        rpc_client=mock_rpc_client,
        imagekit_config=imagekit_config,
        enable_deduplication=False,
        enable_imagekit=False
    )
    
    assert service.enable_deduplication is False
    assert service.enable_imagekit is False
    assert service.imagekit_service is None
    assert service.deduplication_service is None


@patch('src.images.imagekit_integration.ImageKitService.upload_image')
def test_process_image_with_imagekit_success(mock_upload, imagekit_integration_service):
    """Test successful image processing with ImageKit upload."""
    # Mock successful ImageKit upload
    mock_upload.return_value = MagicMock(
        success=True,
        imagekit_url="https://ik.imagekit.io/test/uploaded.jpg",
        file_id="file_123"
    )
    
    # Mock deduplication service to return no duplicate
    imagekit_integration_service.deduplication_service.process_image_with_deduplication = MagicMock(return_value={
        'is_duplicate': False,
        'content_hash': 'hash123',
        'existing_image_id': None
    })
    
    image_data = {
        'url': 'https://example.com/test.jpg',
        'alt': 'Test image',
        'content': b'fake_image_content'
    }
    coffee_id = 'coffee_123'
    
    result = imagekit_integration_service.process_image_with_imagekit(image_data, coffee_id)
    
    assert result['integration_status'] == 'completed'
    assert result['imagekit_url'] == "https://ik.imagekit.io/test/uploaded.jpg"
    assert result['content_hash'] == 'hash123'
    assert result['is_duplicate'] is False


@patch('src.images.imagekit_integration.ImageKitService.upload_image')
def test_process_image_with_imagekit_failure(mock_upload, imagekit_integration_service):
    """Test image processing with ImageKit upload failure."""
    # Mock failed ImageKit upload
    mock_upload.return_value = MagicMock(
        success=False,
        error="Upload failed"
    )
    
    # Mock deduplication service to return no duplicate
    imagekit_integration_service.deduplication_service.process_image_with_deduplication = MagicMock(return_value={
        'is_duplicate': False,
        'content_hash': 'hash123',
        'existing_image_id': None
    })
    
    image_data = {
        'url': 'https://example.com/test.jpg',
        'alt': 'Test image',
        'content': b'fake_image_content'
    }
    coffee_id = 'coffee_123'
    
    result = imagekit_integration_service.process_image_with_imagekit(image_data, coffee_id)
    
    assert result['integration_status'] == 'completed'
    assert result['fallback_url'] == 'https://example.com/test.jpg'
    assert result['imagekit_error'] == "Upload failed"


def test_process_image_with_missing_url(imagekit_integration_service):
    """Test image processing with missing URL."""
    image_data = {'alt': 'No URL Image'}  # Missing URL
    coffee_id = 'coffee_123'

    result = imagekit_integration_service.process_image_with_imagekit(image_data, coffee_id)

    assert result['integration_status'] == 'error'
    assert 'integration_error' in result
    assert result['fallback_url'] == 'unknown'  # This is the expected behavior


def test_process_batch_with_imagekit(imagekit_integration_service):
    """Test batch image processing."""
    images_data = [
        {'url': 'https://example.com/test1.jpg', 'alt': 'Test 1'},
        {'url': 'https://example.com/test2.jpg', 'alt': 'Test 2'}
    ]
    coffee_id = 'coffee_123'
    
    # Mock the process_image_with_imagekit method
    with patch.object(imagekit_integration_service, 'process_image_with_imagekit') as mock_process:
        mock_process.side_effect = [
            {'integration_status': 'success', 'imagekit_url': 'url1'},
            {'integration_status': 'success', 'imagekit_url': 'url2'}
        ]
        
        results = imagekit_integration_service.process_batch_with_imagekit(images_data, coffee_id)
        
        assert len(results) == 2
        assert results[0]['integration_status'] == 'success'
        assert results[1]['integration_status'] == 'success'


def test_get_integration_stats(imagekit_integration_service):
    """Test integration statistics collection."""
    # Set some stats
    imagekit_integration_service.stats['images_processed'] = 10
    imagekit_integration_service.stats['imagekit_uploads'] = 8
    imagekit_integration_service.stats['imagekit_failures'] = 2
    
    stats = imagekit_integration_service.get_integration_stats()
    
    assert stats['images_processed'] == 10
    assert stats['imagekit_uploads'] == 8
    assert stats['imagekit_failures'] == 2
    assert 'imagekit_stats' in stats
    assert 'deduplication_stats' in stats


def test_reset_stats(imagekit_integration_service):
    """Test statistics reset."""
    # Set some stats
    imagekit_integration_service.stats['images_processed'] = 5
    
    # Reset
    imagekit_integration_service.reset_stats()
    
    assert imagekit_integration_service.stats['images_processed'] == 0
    assert imagekit_integration_service.stats['imagekit_uploads'] == 0
    assert imagekit_integration_service.stats['imagekit_failures'] == 0
