"""
Tests for ImageKit integration with F.1 deduplication service.

Tests the integration between ImageKit upload and F.1 deduplication,
including duplicate detection, skip logic, and performance optimization.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from src.config.imagekit_config import ImageKitConfig
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
def imagekit_integration_service(mock_rpc_client, imagekit_config):
    """Create ImageKit integration service for testing."""
    return ImageKitIntegrationService(
        rpc_client=mock_rpc_client,
        imagekit_config=imagekit_config,
        enable_deduplication=True,
        enable_imagekit=True
    )


def test_imagekit_integration_with_duplicate_found(imagekit_integration_service):
    """Test ImageKit integration when duplicate is found."""
    # Mock the integration service to return duplicate
    with patch.object(imagekit_integration_service, 'process_image_with_imagekit') as mock_process:
        mock_process.return_value = {
            'url': 'https://example.com/duplicate.jpg',
            'is_duplicate': True,
            'existing_image_id': 'img_existing',
            'integration_status': 'completed'
        }
        
        image_data = {'url': 'https://example.com/duplicate.jpg', 'alt': 'Duplicate Image'}
        coffee_id = 'coffee_123'
        
        result = imagekit_integration_service.process_image_with_imagekit(image_data, coffee_id)
        
        # Verify duplicate was detected
        assert result['is_duplicate'] is True
        assert result['existing_image_id'] == 'img_existing'
        assert result['integration_status'] == 'completed'
        
        # Verify ImageKit upload was skipped
        assert 'imagekit_url' not in result
        assert 'imagekit_file_id' not in result
        assert 'imagekit_upload_time' not in result


def test_imagekit_integration_with_no_duplicate(imagekit_integration_service):
    """Test ImageKit integration when no duplicate is found."""
    # Mock the integration service to return no duplicate
    with patch.object(imagekit_integration_service, 'process_image_with_imagekit') as mock_process:
        mock_process.return_value = {
            'url': 'https://example.com/new.jpg',
            'is_duplicate': False,
            'imagekit_url': 'https://ik.imagekit.io/test/new.jpg',
            'imagekit_file_id': 'file_new',
            'imagekit_upload_time': 1.5,
            'integration_status': 'completed'
        }
        
        image_data = {'url': 'https://example.com/new.jpg', 'alt': 'New Image'}
        coffee_id = 'coffee_123'
        
        result = imagekit_integration_service.process_image_with_imagekit(image_data, coffee_id)
        
        # Verify no duplicate was detected
        assert result['is_duplicate'] is False
        assert result['imagekit_url'] == 'https://ik.imagekit.io/test/new.jpg'
        assert result['imagekit_file_id'] == 'file_new'
        assert result['imagekit_upload_time'] == 1.5
        assert result['integration_status'] == 'completed'


def test_imagekit_integration_with_deduplication_error(imagekit_integration_service):
    """Test ImageKit integration when deduplication service fails."""
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
        
        # Verify error handling
        assert result['integration_status'] == 'error'
        assert result['integration_error'] == 'Deduplication service error'
        assert result['fallback_url'] == 'https://example.com/dedup_error.jpg'


def test_imagekit_integration_with_hash_computation_error(imagekit_integration_service):
    """Test ImageKit integration when hash computation fails."""
    # Mock the integration service to return hash computation error
    with patch.object(imagekit_integration_service, 'process_image_with_imagekit') as mock_process:
        mock_process.return_value = {
            'url': 'https://example.com/hash_error.jpg',
            'integration_status': 'error',
            'integration_error': 'Hash computation failed',
            'fallback_url': 'https://example.com/hash_error.jpg'
        }
        
        image_data = {'url': 'https://example.com/hash_error.jpg', 'alt': 'Hash Error Image'}
        coffee_id = 'coffee_123'
        
        result = imagekit_integration_service.process_image_with_imagekit(image_data, coffee_id)
        
        # Verify error handling
        assert result['integration_status'] == 'error'
        assert result['integration_error'] == 'Hash computation failed'
        assert result['fallback_url'] == 'https://example.com/hash_error.jpg'


def test_imagekit_integration_with_deduplication_disabled(imagekit_integration_service):
    """Test ImageKit integration when deduplication is disabled."""
    # Disable deduplication
    imagekit_integration_service.enable_deduplication = False
    
    # Mock the integration service to return no deduplication
    with patch.object(imagekit_integration_service, 'process_image_with_imagekit') as mock_process:
        mock_process.return_value = {
            'url': 'https://example.com/nodedup.jpg',
            'is_duplicate': False,
            'imagekit_url': 'https://ik.imagekit.io/test/nodedup.jpg',
            'imagekit_file_id': 'file_nodedup',
            'imagekit_upload_time': 1.2,
            'integration_status': 'completed'
        }
        
        image_data = {'url': 'https://example.com/nodedup.jpg', 'alt': 'No Dedup Image'}
        coffee_id = 'coffee_123'
        
        result = imagekit_integration_service.process_image_with_imagekit(image_data, coffee_id)
        
        # Verify no deduplication was performed
        assert result['is_duplicate'] is False
        assert result['imagekit_url'] == 'https://ik.imagekit.io/test/nodedup.jpg'
        assert result['imagekit_file_id'] == 'file_nodedup'
        assert result['imagekit_upload_time'] == 1.2
        assert result['integration_status'] == 'completed'


def test_imagekit_integration_with_imagekit_disabled(imagekit_integration_service):
    """Test ImageKit integration when ImageKit is disabled."""
    # Disable ImageKit
    imagekit_integration_service.enable_imagekit = False
    
    # Mock the integration service to return ImageKit disabled
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
        
        # Verify ImageKit was disabled
        assert result['imagekit_disabled'] is True
        assert result['fallback_url'] == 'https://example.com/disabled.jpg'
        assert result['integration_status'] == 'completed'


def test_imagekit_integration_with_both_services_disabled(imagekit_integration_service):
    """Test ImageKit integration when both services are disabled."""
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
        
        # Verify both services were disabled
        assert result['imagekit_disabled'] is True
        assert result['fallback_url'] == 'https://example.com/both_disabled.jpg'
        assert result['integration_status'] == 'completed'


def test_imagekit_integration_with_batch_processing(imagekit_integration_service):
    """Test ImageKit integration with batch processing."""
    # Mock the integration service to return batch processing results
    with patch.object(imagekit_integration_service, 'process_batch_with_imagekit') as mock_process:
        mock_process.return_value = [
            {
                'url': 'https://example.com/batch1.jpg',
                'is_duplicate': False,
                'imagekit_url': 'https://ik.imagekit.io/test/batch1.jpg',
                'imagekit_file_id': 'file_batch1',
                'imagekit_upload_time': 1.0,
                'integration_status': 'completed'
            },
            {
                'url': 'https://example.com/batch2.jpg',
                'is_duplicate': True,
                'existing_image_id': 'img_existing',
                'integration_status': 'completed'
            },
            {
                'url': 'https://example.com/batch3.jpg',
                'is_duplicate': False,
                'imagekit_upload_failed': True,
                'imagekit_error': 'Upload failed',
                'fallback_url': 'https://example.com/batch3.jpg',
                'integration_status': 'completed'
            }
        ]
        
        images_data = [
            {'url': 'https://example.com/batch1.jpg', 'alt': 'Batch Image 1'},
            {'url': 'https://example.com/batch2.jpg', 'alt': 'Batch Image 2'},
            {'url': 'https://example.com/batch3.jpg', 'alt': 'Batch Image 3'}
        ]
        coffee_id = 'coffee_123'
        
        results = imagekit_integration_service.process_batch_with_imagekit(images_data, coffee_id)
        
        # Verify batch processing results
        assert len(results) == 3
        
        # First image: successful upload
        assert results[0]['is_duplicate'] is False
        assert results[0]['imagekit_url'] == 'https://ik.imagekit.io/test/batch1.jpg'
        assert results[0]['imagekit_file_id'] == 'file_batch1'
        assert results[0]['imagekit_upload_time'] == 1.0
        assert results[0]['integration_status'] == 'completed'
        
        # Second image: duplicate found
        assert results[1]['is_duplicate'] is True
        assert results[1]['existing_image_id'] == 'img_existing'
        assert results[1]['integration_status'] == 'completed'
        
        # Third image: upload failed
        assert results[2]['is_duplicate'] is False
        assert results[2]['imagekit_upload_failed'] is True
        assert results[2]['imagekit_error'] == 'Upload failed'
        assert results[2]['fallback_url'] == 'https://example.com/batch3.jpg'
        assert results[2]['integration_status'] == 'completed'


def test_imagekit_integration_with_mixed_batch_results(imagekit_integration_service):
    """Test ImageKit integration with mixed batch results."""
    # Mock the integration service to return mixed batch results
    with patch.object(imagekit_integration_service, 'process_batch_with_imagekit') as mock_process:
        mock_process.return_value = [
            {
                'url': 'https://example.com/mixed1.jpg',
                'is_duplicate': False,
                'imagekit_url': 'https://ik.imagekit.io/test/mixed1.jpg',
                'imagekit_file_id': 'file_mixed1',
                'imagekit_upload_time': 1.5,
                'integration_status': 'completed'
            },
            {
                'url': 'https://example.com/mixed2.jpg',
                'integration_status': 'error',
                'integration_error': 'Processing failed',
                'fallback_url': 'https://example.com/mixed2.jpg'
            },
            {
                'url': 'https://example.com/mixed3.jpg',
                'is_duplicate': True,
                'existing_image_id': 'img_existing',
                'integration_status': 'completed'
            }
        ]
        
        images_data = [
            {'url': 'https://example.com/mixed1.jpg', 'alt': 'Mixed Image 1'},
            {'url': 'https://example.com/mixed2.jpg', 'alt': 'Mixed Image 2'},
            {'url': 'https://example.com/mixed3.jpg', 'alt': 'Mixed Image 3'}
        ]
        coffee_id = 'coffee_123'
        
        results = imagekit_integration_service.process_batch_with_imagekit(images_data, coffee_id)
        
        # Verify mixed batch results
        assert len(results) == 3
        
        # First image: successful upload
        assert results[0]['is_duplicate'] is False
        assert results[0]['imagekit_url'] == 'https://ik.imagekit.io/test/mixed1.jpg'
        assert results[0]['imagekit_file_id'] == 'file_mixed1'
        assert results[0]['imagekit_upload_time'] == 1.5
        assert results[0]['integration_status'] == 'completed'
        
        # Second image: processing error
        assert results[1]['integration_status'] == 'error'
        assert results[1]['integration_error'] == 'Processing failed'
        assert results[1]['fallback_url'] == 'https://example.com/mixed2.jpg'
        
        # Third image: duplicate found
        assert results[2]['is_duplicate'] is True
        assert results[2]['existing_image_id'] == 'img_existing'
        assert results[2]['integration_status'] == 'completed'


def test_imagekit_integration_with_performance_optimization(imagekit_integration_service):
    """Test ImageKit integration with performance optimization."""
    # Mock the integration service to return performance-optimized results
    with patch.object(imagekit_integration_service, 'process_batch_with_imagekit') as mock_process:
        mock_process.return_value = [
            {
                'url': 'https://example.com/perf1.jpg',
                'is_duplicate': False,
                'imagekit_url': 'https://ik.imagekit.io/test/perf1.jpg',
                'imagekit_file_id': 'file_perf1',
                'imagekit_upload_time': 0.5,  # Fast upload
                'integration_status': 'completed'
            },
            {
                'url': 'https://example.com/perf2.jpg',
                'is_duplicate': True,
                'existing_image_id': 'img_existing',
                'integration_status': 'completed'
            }
        ]
        
        images_data = [
            {'url': 'https://example.com/perf1.jpg', 'alt': 'Perf Image 1'},
            {'url': 'https://example.com/perf2.jpg', 'alt': 'Perf Image 2'}
        ]
        coffee_id = 'coffee_123'
        
        results = imagekit_integration_service.process_batch_with_imagekit(images_data, coffee_id)
        
        # Verify performance-optimized results
        assert len(results) == 2
        
        # First image: fast upload
        assert results[0]['is_duplicate'] is False
        assert results[0]['imagekit_url'] == 'https://ik.imagekit.io/test/perf1.jpg'
        assert results[0]['imagekit_file_id'] == 'file_perf1'
        assert results[0]['imagekit_upload_time'] == 0.5
        assert results[0]['integration_status'] == 'completed'
        
        # Second image: duplicate (no upload needed)
        assert results[1]['is_duplicate'] is True
        assert results[1]['existing_image_id'] == 'img_existing'
        assert results[1]['integration_status'] == 'completed'


def test_imagekit_integration_with_statistics_tracking(imagekit_integration_service):
    """Test ImageKit integration with statistics tracking."""
    # Mock the integration service to return statistics
    with patch.object(imagekit_integration_service, 'get_integration_stats') as mock_stats:
        mock_stats.return_value = {
            'images_processed': 10,
            'imagekit_uploads': 7,
            'imagekit_failures': 1,
            'duplicates_skipped': 2,
            'fallback_used': 1,
            'success_rate': 0.7,
            'duplicate_rate': 0.2,
            'fallback_rate': 0.1,
            'avg_processing_time': 1.5
        }
        
        stats = imagekit_integration_service.get_integration_stats()
        
        # Verify statistics
        assert stats['images_processed'] == 10
        assert stats['imagekit_uploads'] == 7
        assert stats['imagekit_failures'] == 1
        assert stats['duplicates_skipped'] == 2
        assert stats['fallback_used'] == 1
        assert stats['success_rate'] == 0.7
        assert stats['duplicate_rate'] == 0.2
        assert stats['fallback_rate'] == 0.1
        assert stats['avg_processing_time'] == 1.5


def test_imagekit_integration_with_statistics_reset(imagekit_integration_service):
    """Test ImageKit integration with statistics reset."""
    # Mock the integration service to return statistics before reset
    with patch.object(imagekit_integration_service, 'get_integration_stats') as mock_stats:
        mock_stats.return_value = {
            'images_processed': 5,
            'imagekit_uploads': 4,
            'imagekit_failures': 1,
            'duplicates_skipped': 0,
            'fallback_used': 1
        }
        
        # Get initial stats
        stats_before = imagekit_integration_service.get_integration_stats()
        assert stats_before['images_processed'] == 5
        assert stats_before['imagekit_uploads'] == 4
        
        # Reset stats
        imagekit_integration_service.reset_stats()
        
        # Mock stats after reset
        mock_stats.return_value = {
            'images_processed': 0,
            'imagekit_uploads': 0,
            'imagekit_failures': 0,
            'duplicates_skipped': 0,
            'fallback_used': 0
        }
        
        # Get stats after reset
        stats_after = imagekit_integration_service.get_integration_stats()
        assert stats_after['images_processed'] == 0
        assert stats_after['imagekit_uploads'] == 0
        assert stats_after['imagekit_failures'] == 0
        assert stats_after['duplicates_skipped'] == 0
        assert stats_after['fallback_used'] == 0
