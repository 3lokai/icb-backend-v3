"""
Unit tests for ImageKit integration service.

Tests the integration between ImageKit upload and F.1 deduplication,
including fallback mechanisms and batch processing.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from src.images.imagekit_integration import ImageKitIntegrationService
from src.config.imagekit_config import ImageKitConfig, ImageKitResult
from src.validator.rpc_client import RPCClient


@pytest.fixture
def mock_rpc_client():
    """Create mock RPC client for testing."""
    return Mock(spec=RPCClient)


@pytest.fixture
def imagekit_config():
    """Create ImageKit configuration for testing."""
    return ImageKitConfig(
        public_key="public_test_key",
        private_key="private_test_key",
        url_endpoint="https://ik.imagekit.io/test"
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


def test_imagekit_integration_init(imagekit_integration_service, mock_rpc_client, imagekit_config):
    """Test ImageKit integration service initialization."""
    assert imagekit_integration_service.rpc_client == mock_rpc_client
    assert imagekit_integration_service.imagekit_config == imagekit_config
    assert imagekit_integration_service.enable_deduplication is True
    assert imagekit_integration_service.enable_imagekit is True
    assert imagekit_integration_service.imagekit_service is not None
    assert imagekit_integration_service.deduplication_service is not None


def test_imagekit_integration_init_disabled():
    """Test ImageKit integration service with services disabled."""
    mock_rpc_client = Mock(spec=RPCClient)
    imagekit_config = ImageKitConfig(
        public_key="public_test_key",
        private_key="private_test_key",
        url_endpoint="https://ik.imagekit.io/test"
    )
    
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


def test_process_image_with_deduplication_duplicate_found(imagekit_integration_service):
    """Test image processing when duplicate is found."""
    # Mock deduplication service to return duplicate
    with patch.object(imagekit_integration_service.deduplication_service, 'process_image_with_deduplication') as mock_dedup:
        mock_dedup.return_value = {
            'url': 'https://example.com/duplicate.jpg',
            'is_duplicate': True,
            'existing_image_id': 'img_123',
            'content_hash': 'hash_123'
        }
        
        image_data = {'url': 'https://example.com/duplicate.jpg', 'alt': 'Duplicate Image'}
        coffee_id = 'coffee_123'
        
        result = imagekit_integration_service.process_image_with_imagekit(image_data, coffee_id)
        
        assert result['is_duplicate'] is True
        assert result['imagekit_upload_skipped'] is True
        assert result['reason'] == 'duplicate_found'
        assert result['existing_image_id'] == 'img_123'
        
        # ImageKit service should not be called for duplicates
        if imagekit_integration_service.imagekit_service:
            with patch.object(imagekit_integration_service.imagekit_service, 'upload_image') as mock_upload:
                mock_upload.assert_not_called()


def test_process_image_with_imagekit_success(imagekit_integration_service):
    """Test successful image processing with ImageKit upload."""
    # Mock deduplication service to return new image
    with patch.object(imagekit_integration_service.deduplication_service, 'process_image_with_deduplication') as mock_dedup:
        mock_dedup.return_value = {
            'url': 'https://example.com/new.jpg',
            'is_duplicate': False,
            'content_hash': 'hash_new'
        }
        
        # Mock ImageKit service to return successful upload
        with patch.object(imagekit_integration_service.imagekit_service, 'upload_image') as mock_imagekit:
            mock_imagekit.return_value = ImageKitResult(
                success=True,
                imagekit_url="https://ik.imagekit.io/test/new.jpg",
                file_id="file_new",
                upload_time=1.5
            )
            
            image_data = {'url': 'https://example.com/new.jpg', 'alt': 'New Image'}
            coffee_id = 'coffee_123'
            
            result = imagekit_integration_service.process_image_with_imagekit(image_data, coffee_id)
            
            assert result['is_duplicate'] is False
            assert result['imagekit_url'] == "https://ik.imagekit.io/test/new.jpg"
            assert result['imagekit_file_id'] == "file_new"
            assert result['imagekit_upload_time'] == 1.5
            assert result['integration_status'] == 'completed'
            
            # Verify services were called
            mock_dedup.assert_called_once_with(image_data, coffee_id)
            mock_imagekit.assert_called_once()


def test_process_image_with_imagekit_failure(imagekit_integration_service):
    """Test image processing when ImageKit upload fails."""
    # Mock deduplication service to return new image
    imagekit_integration_service.deduplication_service.process_image_with_deduplication = Mock(return_value={
        'url': 'https://example.com/fail.jpg',
        'is_duplicate': False,
        'content_hash': 'hash_fail'
    })
    
    # Mock ImageKit service to return failed upload
    imagekit_integration_service.imagekit_service.upload_image = Mock(return_value=ImageKitResult(
        success=False,
        error="Network timeout"
    ))
    
    image_data = {'url': 'https://example.com/fail.jpg', 'alt': 'Failed Image'}
    coffee_id = 'coffee_123'
    
    result = imagekit_integration_service.process_image_with_imagekit(image_data, coffee_id)
    
    assert result['is_duplicate'] is False
    assert result['imagekit_upload_failed'] is True
    assert result['imagekit_error'] == "Network timeout"
    assert result['fallback_url'] == 'https://example.com/fail.jpg'
    assert result['integration_status'] == 'completed'


def test_process_image_with_imagekit_disabled(imagekit_integration_service):
    """Test image processing when ImageKit is disabled."""
    # Disable ImageKit
    imagekit_integration_service.enable_imagekit = False
    
    # Mock the deduplication service to avoid real HTTP requests
    imagekit_integration_service.deduplication_service = Mock()
    imagekit_integration_service.deduplication_service.process_image_with_deduplication = Mock(return_value={
        'url': 'https://example.com/disabled.jpg',
        'is_duplicate': False,
        'content_hash': 'test_hash'
    })
    
    image_data = {'url': 'https://example.com/disabled.jpg', 'alt': 'Disabled Image'}
    coffee_id = 'coffee_123'
    
    result = imagekit_integration_service.process_image_with_imagekit(image_data, coffee_id)
    
    assert result['imagekit_disabled'] is True
    assert result['fallback_url'] == 'https://example.com/disabled.jpg'
    assert result['integration_status'] == 'completed'


def test_process_image_with_imagekit_exception(imagekit_integration_service):
    """Test image processing when ImageKit service raises exception."""
    # Mock the deduplication service to avoid real HTTP requests
    imagekit_integration_service.deduplication_service = Mock()
    imagekit_integration_service.deduplication_service.process_image_with_deduplication = Mock(return_value={
        'url': 'https://example.com/error.jpg',
        'is_duplicate': False,
        'content_hash': 'test_hash'
    })
    
    # Mock ImageKit service to raise exception
    imagekit_integration_service.imagekit_service.upload_image = Mock(side_effect=Exception("ImageKit service error"))
    
    image_data = {'url': 'https://example.com/error.jpg', 'alt': 'Error Image'}
    coffee_id = 'coffee_123'
    
    result = imagekit_integration_service.process_image_with_imagekit(image_data, coffee_id)
    
    assert result['imagekit_upload_failed'] is True
    assert "ImageKit service error" in result['imagekit_error']
    assert result['fallback_url'] == 'https://example.com/error.jpg'
    assert result['integration_status'] == 'completed'


def test_process_image_with_missing_url(imagekit_integration_service):
    """Test image processing with missing URL."""
    image_data = {'alt': 'No URL Image'}  # Missing URL
    coffee_id = 'coffee_123'
    
    result = imagekit_integration_service.process_image_with_imagekit(image_data, coffee_id)
    
    assert result['integration_status'] == 'error'
    assert 'integration_error' in result
    assert result['fallback_url'] == 'unknown'


@patch('src.images.imagekit_integration.ImageKitIntegrationService.process_image_with_imagekit')
def test_process_batch_with_imagekit(mock_process_image, imagekit_integration_service):
    """Test batch image processing."""
    # Mock individual image processing
    mock_process_image.side_effect = [
        {'url': 'img1.jpg', 'integration_status': 'completed', 'imagekit_url': 'https://ik.imagekit.io/test/img1.jpg'},
        {'url': 'img2.jpg', 'integration_status': 'completed', 'imagekit_url': 'https://ik.imagekit.io/test/img2.jpg'},
        {'url': 'img3.jpg', 'integration_status': 'error', 'integration_error': 'Processing failed'}
    ]
    
    images_data = [
        {'url': 'https://example.com/img1.jpg'},
        {'url': 'https://example.com/img2.jpg'},
        {'url': 'https://example.com/img3.jpg'}
    ]
    coffee_id = 'coffee_123'
    
    results = imagekit_integration_service.process_batch_with_imagekit(images_data, coffee_id)
    
    assert len(results) == 3
    assert results[0]['integration_status'] == 'completed'
    assert results[1]['integration_status'] == 'completed'
    assert results[2]['integration_status'] == 'error'
    assert mock_process_image.call_count == 3


def test_get_integration_stats(imagekit_integration_service):
    """Test integration statistics collection."""
    # Set some stats
    imagekit_integration_service.stats['images_processed'] = 10
    imagekit_integration_service.stats['imagekit_uploads'] = 8
    imagekit_integration_service.stats['imagekit_failures'] = 2
    imagekit_integration_service.stats['duplicates_skipped'] = 3
    imagekit_integration_service.stats['fallback_used'] = 2
    imagekit_integration_service.stats['total_processing_time'] = 15.0
    
    stats = imagekit_integration_service.get_integration_stats()
    
    assert stats['images_processed'] == 10
    assert stats['imagekit_uploads'] == 8
    assert stats['imagekit_failures'] == 2
    assert stats['duplicates_skipped'] == 3
    assert stats['fallback_used'] == 2
    assert stats['success_rate'] == 0.8  # (10-2)/10
    assert stats['duplicate_rate'] == 0.3  # 3/10
    assert stats['fallback_rate'] == 0.2  # 2/10
    assert stats['avg_processing_time'] == 1.5  # 15.0/10


def test_reset_stats(imagekit_integration_service):
    """Test statistics reset."""
    # Set some stats
    imagekit_integration_service.stats['images_processed'] = 5
    imagekit_integration_service.stats['imagekit_uploads'] = 4
    
    # Reset stats
    imagekit_integration_service.reset_stats()
    
    assert imagekit_integration_service.stats['images_processed'] == 0
    assert imagekit_integration_service.stats['imagekit_uploads'] == 0


def test_process_image_with_deduplication_disabled(imagekit_integration_service):
    """Test image processing when deduplication is disabled."""
    # Disable deduplication
    imagekit_integration_service.enable_deduplication = False
    
    # Mock ImageKit service to return successful upload
    imagekit_integration_service.imagekit_service.upload_image = Mock(return_value=ImageKitResult(
        success=True,
        imagekit_url="https://ik.imagekit.io/test/nodedup.jpg",
        file_id="file_nodedup"
    ))
    
    image_data = {'url': 'https://example.com/nodedup.jpg', 'alt': 'No Dedup Image'}
    coffee_id = 'coffee_123'
    
    result = imagekit_integration_service.process_image_with_imagekit(image_data, coffee_id)
    
    assert result['imagekit_url'] == "https://ik.imagekit.io/test/nodedup.jpg"
    assert result['integration_status'] == 'completed'
    
    # ImageKit service should be called
    imagekit_integration_service.imagekit_service.upload_image.assert_called_once()


def test_process_image_with_both_services_disabled(imagekit_integration_service):
    """Test image processing when both services are disabled."""
    # Disable both services
    imagekit_integration_service.enable_deduplication = False
    imagekit_integration_service.enable_imagekit = False
    
    image_data = {'url': 'https://example.com/disabled.jpg', 'alt': 'Disabled Image'}
    coffee_id = 'coffee_123'
    
    result = imagekit_integration_service.process_image_with_imagekit(image_data, coffee_id)
    
    assert result['imagekit_disabled'] is True
    assert result['fallback_url'] == 'https://example.com/disabled.jpg'
    assert result['integration_status'] == 'completed'


def test_process_image_with_deduplication_exception(imagekit_integration_service):
    """Test image processing when deduplication service raises exception."""
    # Mock deduplication service to raise exception
    imagekit_integration_service.deduplication_service.process_image_with_deduplication = Mock(side_effect=Exception("Dedup service error"))
    
    image_data = {'url': 'https://example.com/deduperror.jpg', 'alt': 'Dedup Error Image'}
    coffee_id = 'coffee_123'
    
    result = imagekit_integration_service.process_image_with_imagekit(image_data, coffee_id)
    
    assert result['integration_status'] == 'error'
    assert "Dedup service error" in result['integration_error']
    assert result['fallback_url'] == 'https://example.com/deduperror.jpg'
