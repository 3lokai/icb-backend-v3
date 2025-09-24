"""
Tests for ImageKit fallback scenarios and error conditions.

Tests the fallback mechanisms when ImageKit upload fails,
including network errors, authentication failures, and service unavailability.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from src.config.imagekit_config import ImageKitConfig
from src.images.imagekit_service import ImageKitService, ImageKitResult
from src.images.imagekit_integration import ImageKitIntegrationService
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
def imagekit_service(imagekit_config):
    """Create ImageKit service for testing."""
    return ImageKitService(imagekit_config)


@pytest.fixture
def imagekit_integration_service(mock_rpc_client, imagekit_config):
    """Create ImageKit integration service for testing."""
    return ImageKitIntegrationService(
        rpc_client=mock_rpc_client,
        imagekit_config=imagekit_config,
        enable_deduplication=True,
        enable_imagekit=True
    )


def test_imagekit_upload_network_error_fallback(imagekit_service):
    """Test fallback when ImageKit upload fails due to network error."""
    # Mock network error
    with patch('src.images.imagekit_service.ImageKit.upload_file') as mock_upload:
        mock_upload.side_effect = Exception("Network connection failed")
        
        image_url = "https://example.com/network_error.jpg"
        content = b"fake_image_content"
        
        result = imagekit_service.upload_image(image_url, content)
        
        # Verify upload failed
        assert result.success is False
        assert result.imagekit_url is None
        assert result.file_id is None
        assert "Network connection failed" in result.error
        
        # Verify stats
        assert imagekit_service.stats['uploads_attempted'] == 1
        assert imagekit_service.stats['uploads_successful'] == 0
        assert imagekit_service.stats['uploads_failed'] == 1


def test_imagekit_upload_authentication_error_fallback(imagekit_service):
    """Test fallback when ImageKit upload fails due to authentication error."""
    # Mock authentication error
    with patch('src.images.imagekit_service.ImageKit.upload_file') as mock_upload:
        mock_upload.side_effect = Exception("Authentication failed: Invalid credentials")
        
        image_url = "https://example.com/auth_error.jpg"
        content = b"fake_image_content"
        
        result = imagekit_service.upload_image(image_url, content)
        
        # Verify upload failed
        assert result.success is False
        assert result.imagekit_url is None
        assert result.file_id is None
        assert "Authentication failed" in result.error
        
        # Verify stats
        assert imagekit_service.stats['uploads_attempted'] == 1
        assert imagekit_service.stats['uploads_successful'] == 0
        assert imagekit_service.stats['uploads_failed'] == 1


def test_imagekit_upload_timeout_error_fallback(imagekit_service):
    """Test fallback when ImageKit upload fails due to timeout."""
    # Mock timeout error
    with patch('src.images.imagekit_service.ImageKit.upload_file') as mock_upload:
        mock_upload.side_effect = Exception("Request timeout")
        
        image_url = "https://example.com/timeout_error.jpg"
        content = b"fake_image_content"
        
        result = imagekit_service.upload_image(image_url, content)
        
        # Verify upload failed
        assert result.success is False
        assert result.imagekit_url is None
        assert result.file_id is None
        assert "Request timeout" in result.error
        
        # Verify stats
        assert imagekit_service.stats['uploads_attempted'] == 1
        assert imagekit_service.stats['uploads_successful'] == 0
        assert imagekit_service.stats['uploads_failed'] == 1


def test_imagekit_upload_service_unavailable_fallback(imagekit_service):
    """Test fallback when ImageKit service is unavailable."""
    # Mock service unavailable error
    with patch('src.images.imagekit_service.ImageKit.upload_file') as mock_upload:
        mock_upload.side_effect = Exception("Service unavailable: 503")
        
        image_url = "https://example.com/service_unavailable.jpg"
        content = b"fake_image_content"
        
        result = imagekit_service.upload_image(image_url, content)
        
        # Verify upload failed
        assert result.success is False
        assert result.imagekit_url is None
        assert result.file_id is None
        assert "Service unavailable" in result.error
        
        # Verify stats
        assert imagekit_service.stats['uploads_attempted'] == 1
        assert imagekit_service.stats['uploads_successful'] == 0
        assert imagekit_service.stats['uploads_failed'] == 1


def test_imagekit_upload_quota_exceeded_fallback(imagekit_service):
    """Test fallback when ImageKit quota is exceeded."""
    # Mock quota exceeded error
    with patch('src.images.imagekit_service.ImageKit.upload_file') as mock_upload:
        mock_upload.side_effect = Exception("Quota exceeded: 429")
        
        image_url = "https://example.com/quota_exceeded.jpg"
        content = b"fake_image_content"
        
        result = imagekit_service.upload_image(image_url, content)
        
        # Verify upload failed
        assert result.success is False
        assert result.imagekit_url is None
        assert result.file_id is None
        assert "Quota exceeded" in result.error
        
        # Verify stats
        assert imagekit_service.stats['uploads_attempted'] == 1
        assert imagekit_service.stats['uploads_successful'] == 0
        assert imagekit_service.stats['uploads_failed'] == 1


def test_imagekit_upload_file_too_large_fallback(imagekit_service):
    """Test fallback when image file is too large for ImageKit."""
    # Mock file too large error
    with patch('src.images.imagekit_service.ImageKit.upload_file') as mock_upload:
        mock_upload.side_effect = Exception("File too large: 413")
        
        image_url = "https://example.com/large_file.jpg"
        content = b"fake_image_content" * 1000  # Simulate large file
        
        result = imagekit_service.upload_image(image_url, content)
        
        # Verify upload failed
        assert result.success is False
        assert result.imagekit_url is None
        assert result.file_id is None
        assert "File too large" in result.error
        
        # Verify stats
        assert imagekit_service.stats['uploads_attempted'] == 1
        assert imagekit_service.stats['uploads_successful'] == 0
        assert imagekit_service.stats['uploads_failed'] == 1


def test_imagekit_upload_invalid_file_format_fallback(imagekit_service):
    """Test fallback when image file format is invalid."""
    # Mock invalid file format error
    with patch('src.images.imagekit_service.ImageKit.upload_file') as mock_upload:
        mock_upload.side_effect = Exception("Invalid file format")
        
        image_url = "https://example.com/invalid_format.txt"
        content = b"not_an_image"
        
        result = imagekit_service.upload_image(image_url, content)
        
        # Verify upload failed
        assert result.success is False
        assert result.imagekit_url is None
        assert result.file_id is None
        assert "Invalid file format" in result.error
        
        # Verify stats
        assert imagekit_service.stats['uploads_attempted'] == 1
        assert imagekit_service.stats['uploads_successful'] == 0
        assert imagekit_service.stats['uploads_failed'] == 1


def test_imagekit_upload_retry_exhausted_fallback(imagekit_service):
    """Test fallback when all retry attempts are exhausted."""
    # Mock retry exhaustion
    with patch('src.images.imagekit_service.ImageKit.upload_file') as mock_upload:
        mock_upload.side_effect = Exception("Persistent error")
        
        # Set max retries to 2
        imagekit_service.max_retries = 2
        
        image_url = "https://example.com/retry_exhausted.jpg"
        content = b"fake_image_content"
        
        result = imagekit_service.upload_image(image_url, content)
        
        # Verify upload failed after retries
        assert result.success is False
        assert result.imagekit_url is None
        assert result.file_id is None
        assert "Persistent error" in result.error
        
        # Verify stats
        assert imagekit_service.stats['uploads_attempted'] == 1
        assert imagekit_service.stats['uploads_successful'] == 0
        assert imagekit_service.stats['uploads_failed'] == 1


def test_imagekit_upload_disabled_fallback(imagekit_service):
    """Test fallback when ImageKit upload is disabled."""
    # Disable ImageKit
    imagekit_service.config.enabled = False
    
    image_url = "https://example.com/disabled.jpg"
    content = b"fake_image_content"
    
    result = imagekit_service.upload_image(image_url, content)
    
    # Verify upload was skipped
    assert result.success is False
    assert result.imagekit_url is None
    assert result.file_id is None
    assert result.error == "ImageKit upload disabled"
    
    # Verify stats
    assert imagekit_service.stats['uploads_attempted'] == 0
    assert imagekit_service.stats['uploads_successful'] == 0
    assert imagekit_service.stats['uploads_failed'] == 0


def test_imagekit_integration_fallback_on_upload_failure(imagekit_integration_service):
    """Test ImageKit integration fallback when upload fails."""
    # Mock the integration service to return upload failure
    with patch.object(imagekit_integration_service, 'process_image_with_imagekit') as mock_process:
        mock_process.return_value = {
            'url': 'https://example.com/fail.jpg',
            'is_duplicate': False,
            'imagekit_upload_failed': True,
            'imagekit_error': 'Upload failed',
            'fallback_url': 'https://example.com/fail.jpg',
            'integration_status': 'completed'
        }
        
        image_data = {'url': 'https://example.com/fail.jpg', 'alt': 'Failed Image'}
        coffee_id = 'coffee_123'
        
        result = imagekit_integration_service.process_image_with_imagekit(image_data, coffee_id)
        
        # Verify fallback was used
        assert result['imagekit_upload_failed'] is True
        assert result['imagekit_error'] == 'Upload failed'
        assert result['fallback_url'] == 'https://example.com/fail.jpg'
        assert result['integration_status'] == 'completed'


def test_imagekit_integration_fallback_on_service_error(imagekit_integration_service):
    """Test ImageKit integration fallback when service error occurs."""
    # Mock the integration service to return service error
    with patch.object(imagekit_integration_service, 'process_image_with_imagekit') as mock_process:
        mock_process.return_value = {
            'url': 'https://example.com/error.jpg',
            'integration_status': 'error',
            'integration_error': 'Service unavailable',
            'fallback_url': 'https://example.com/error.jpg'
        }
        
        image_data = {'url': 'https://example.com/error.jpg', 'alt': 'Error Image'}
        coffee_id = 'coffee_123'
        
        result = imagekit_integration_service.process_image_with_imagekit(image_data, coffee_id)
        
        # Verify fallback was used
        assert result['integration_status'] == 'error'
        assert result['integration_error'] == 'Service unavailable'
        assert result['fallback_url'] == 'https://example.com/error.jpg'


def test_imagekit_integration_fallback_on_deduplication_error(imagekit_integration_service):
    """Test ImageKit integration fallback when deduplication error occurs."""
    # Mock the integration service to return deduplication error
    with patch.object(imagekit_integration_service, 'process_image_with_imagekit') as mock_process:
        mock_process.return_value = {
            'url': 'https://example.com/dedup_error.jpg',
            'integration_status': 'error',
            'integration_error': 'Deduplication service error',
            'fallback_url': 'https://example.com/dedup_error.jpg'
        }
        
        image_data = {'url': 'https://example.com/dedup_error.jpg', 'alt': 'Dedup Error Image'}
        coffee_id = 'coffee_123'
        
        result = imagekit_integration_service.process_image_with_imagekit(image_data, coffee_id)
        
        # Verify fallback was used
        assert result['integration_status'] == 'error'
        assert result['integration_error'] == 'Deduplication service error'
        assert result['fallback_url'] == 'https://example.com/dedup_error.jpg'


def test_imagekit_integration_fallback_on_missing_url(imagekit_integration_service):
    """Test ImageKit integration fallback when image URL is missing."""
    # Mock the integration service to return missing URL error
    with patch.object(imagekit_integration_service, 'process_image_with_imagekit') as mock_process:
        mock_process.return_value = {
            'integration_status': 'error',
            'integration_error': 'Image URL is missing',
            'fallback_url': None
        }
        
        image_data = {'alt': 'No URL Image'}  # Missing URL
        coffee_id = 'coffee_123'
        
        result = imagekit_integration_service.process_image_with_imagekit(image_data, coffee_id)
        
        # Verify error handling
        assert result['integration_status'] == 'error'
        assert result['integration_error'] == 'Image URL is missing'
        assert result['fallback_url'] is None


def test_imagekit_integration_fallback_on_missing_content(imagekit_integration_service):
    """Test ImageKit integration fallback when image content is missing."""
    # Mock the integration service to return missing content error
    with patch.object(imagekit_integration_service, 'process_image_with_imagekit') as mock_process:
        mock_process.return_value = {
            'url': 'https://example.com/no_content.jpg',
            'integration_status': 'error',
            'integration_error': 'Image content is missing',
            'fallback_url': 'https://example.com/no_content.jpg'
        }
        
        image_data = {'url': 'https://example.com/no_content.jpg', 'alt': 'No Content Image'}
        coffee_id = 'coffee_123'
        
        result = imagekit_integration_service.process_image_with_imagekit(image_data, coffee_id)
        
        # Verify fallback was used
        assert result['integration_status'] == 'error'
        assert result['integration_error'] == 'Image content is missing'
        assert result['fallback_url'] == 'https://example.com/no_content.jpg'


def test_imagekit_integration_fallback_on_batch_processing_error(imagekit_integration_service):
    """Test ImageKit integration fallback during batch processing."""
    # Mock the integration service to return batch processing error
    with patch.object(imagekit_integration_service, 'process_batch_with_imagekit') as mock_process:
        mock_process.return_value = [
            {
                'url': 'https://example.com/batch1.jpg',
                'integration_status': 'completed',
                'imagekit_url': 'https://ik.imagekit.io/test/batch1.jpg'
            },
            {
                'url': 'https://example.com/batch2.jpg',
                'integration_status': 'error',
                'integration_error': 'Batch processing error',
                'fallback_url': 'https://example.com/batch2.jpg'
            }
        ]
        
        images_data = [
            {'url': 'https://example.com/batch1.jpg', 'alt': 'Batch Image 1'},
            {'url': 'https://example.com/batch2.jpg', 'alt': 'Batch Image 2'}
        ]
        coffee_id = 'coffee_123'
        
        results = imagekit_integration_service.process_batch_with_imagekit(images_data, coffee_id)
        
        # Verify mixed results
        assert len(results) == 2
        assert results[0]['integration_status'] == 'completed'
        assert results[1]['integration_status'] == 'error'
        assert results[1]['integration_error'] == 'Batch processing error'
        assert results[1]['fallback_url'] == 'https://example.com/batch2.jpg'


def test_imagekit_integration_fallback_on_service_disabled(imagekit_integration_service):
    """Test ImageKit integration fallback when service is disabled."""
    # Disable ImageKit
    imagekit_integration_service.enable_imagekit = False
    
    # Mock the integration service to return disabled status
    with patch.object(imagekit_integration_service, 'process_image_with_imagekit') as mock_process:
        mock_process.return_value = {
            'url': 'https://example.com/disabled.jpg',
            'imagekit_disabled': True,
            'fallback_url': 'https://example.com/disabled.jpg',
            'integration_status': 'completed'
        }
        
        image_data = {'url': 'https://example.com/disabled.jpg', 'alt': 'Disabled Image'}
        coffee_id = 'coffee_123'
        
        result = imagekit_integration_service.process_image_with_imagekit(image_data, coffee_id)
        
        # Verify fallback was used
        assert result['imagekit_disabled'] is True
        assert result['fallback_url'] == 'https://example.com/disabled.jpg'
        assert result['integration_status'] == 'completed'


def test_imagekit_integration_fallback_on_deduplication_disabled(imagekit_integration_service):
    """Test ImageKit integration fallback when deduplication is disabled."""
    # Disable deduplication
    imagekit_integration_service.enable_deduplication = False
    
    # Mock the integration service to return no deduplication
    with patch.object(imagekit_integration_service, 'process_image_with_imagekit') as mock_process:
        mock_process.return_value = {
            'url': 'https://example.com/nodedup.jpg',
            'is_duplicate': False,
            'imagekit_url': 'https://ik.imagekit.io/test/nodedup.jpg',
            'integration_status': 'completed'
        }
        
        image_data = {'url': 'https://example.com/nodedup.jpg', 'alt': 'No Dedup Image'}
        coffee_id = 'coffee_123'
        
        result = imagekit_integration_service.process_image_with_imagekit(image_data, coffee_id)
        
        # Verify no deduplication was performed
        assert result['is_duplicate'] is False
        assert result['imagekit_url'] == 'https://ik.imagekit.io/test/nodedup.jpg'
        assert result['integration_status'] == 'completed'


def test_imagekit_integration_fallback_on_both_services_disabled(imagekit_integration_service):
    """Test ImageKit integration fallback when both services are disabled."""
    # Disable both services
    imagekit_integration_service.enable_imagekit = False
    imagekit_integration_service.enable_deduplication = False
    
    # Mock the integration service to return both services disabled
    with patch.object(imagekit_integration_service, 'process_image_with_imagekit') as mock_process:
        mock_process.return_value = {
            'url': 'https://example.com/both_disabled.jpg',
            'imagekit_disabled': True,
            'fallback_url': 'https://example.com/both_disabled.jpg',
            'integration_status': 'completed'
        }
        
        image_data = {'url': 'https://example.com/both_disabled.jpg', 'alt': 'Both Disabled Image'}
        coffee_id = 'coffee_123'
        
        result = imagekit_integration_service.process_image_with_imagekit(image_data, coffee_id)
        
        # Verify fallback was used
        assert result['imagekit_disabled'] is True
        assert result['fallback_url'] == 'https://example.com/both_disabled.jpg'
        assert result['integration_status'] == 'completed'
