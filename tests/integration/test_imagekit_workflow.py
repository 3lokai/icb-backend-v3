"""
Integration tests for ImageKit workflow.

Tests the complete workflow from image processing through
ImageKit upload, deduplication, and database storage.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from src.images.imagekit_config import ImageKitConfig
from src.images.imagekit_integration import ImageKitIntegrationService
from src.validator.artifact_mapper import ArtifactMapper
from src.validator.rpc_client import RPCClient


@pytest.fixture
def mock_rpc_client():
    """Create mock RPC client for testing."""
    return Mock(spec=RPCClient)


@pytest.fixture
def imagekit_config():
    """Create ImageKit configuration for testing."""
    return ImageKitConfig(
        public_key="test_public_key",
        private_key="test_private_key",
        url_endpoint="https://ik.imagekit.io/test"
    )


@pytest.fixture
def artifact_mapper_with_imagekit(mock_rpc_client, imagekit_config):
    """Create ArtifactMapper with ImageKit integration enabled."""
    return ArtifactMapper(
        rpc_client=mock_rpc_client,
        enable_imagekit=True,
        imagekit_config=imagekit_config
    )


@patch('src.images.imagekit_integration.ImageKitIntegrationService')
def test_complete_imagekit_workflow_success(MockImageKitIntegration, artifact_mapper_with_imagekit, mock_rpc_client):
    """Test complete ImageKit workflow with successful upload."""
    # Mock the ImageKit integration service
    mock_integration = Mock()
    mock_integration.process_image_with_imagekit.return_value = {
        'url': 'https://example.com/test.jpg',
        'is_duplicate': False,
        'imagekit_url': 'https://ik.imagekit.io/test/uploaded.jpg',
        'imagekit_file_id': 'file_123',
        'imagekit_upload_time': 1.5,
        'integration_status': 'completed'
    }
    MockImageKitIntegration.return_value = mock_integration
    
    # Mock RPC client response
    mock_rpc_client.upsert_coffee_image.return_value = 'img_456'
    
    # Test data
    coffee_data = {
        'id': 'coffee_123',
        'name': 'Test Coffee',
        'images': [
            {
                'url': 'https://example.com/test.jpg',
                'alt': 'Test Image',
                'width': 800,
                'height': 600
            }
        ]
    }
    
    # Process the coffee data
    result = artifact_mapper_with_imagekit.map_coffee_data(coffee_data)
    
    # Verify ImageKit integration was called
    mock_integration.process_image_with_imagekit.assert_called_once()
    
    # Verify RPC client was called with ImageKit URL
    mock_rpc_client.upsert_coffee_image.assert_called_once()
    call_args = mock_rpc_client.upsert_coffee_image.call_args
    assert call_args[1]['imagekit_url'] == 'https://ik.imagekit.io/test/uploaded.jpg'
    assert call_args[1]['imagekit_file_id'] == 'file_123'
    assert call_args[1]['imagekit_upload_time'] == 1.5


@patch('src.images.imagekit_integration.ImageKitIntegrationService')
def test_complete_imagekit_workflow_duplicate_found(MockImageKitIntegration, artifact_mapper_with_imagekit, mock_rpc_client):
    """Test complete ImageKit workflow when duplicate is found."""
    # Mock the ImageKit integration service to return duplicate
    mock_integration = Mock()
    mock_integration.process_image_with_imagekit.return_value = {
        'url': 'https://example.com/duplicate.jpg',
        'is_duplicate': True,
        'existing_image_id': 'img_existing',
        'integration_status': 'completed'
    }
    MockImageKitIntegration.return_value = mock_integration
    
    # Mock RPC client response
    mock_rpc_client.upsert_coffee_image.return_value = 'img_existing'
    
    # Test data
    coffee_data = {
        'id': 'coffee_123',
        'name': 'Test Coffee',
        'images': [
            {
                'url': 'https://example.com/duplicate.jpg',
                'alt': 'Duplicate Image',
                'width': 800,
                'height': 600
            }
        ]
    }
    
    # Process the coffee data
    result = artifact_mapper_with_imagekit.map_coffee_data(coffee_data)
    
    # Verify ImageKit integration was called
    mock_integration.process_image_with_imagekit.assert_called_once()
    
    # Verify RPC client was called without ImageKit URL (duplicate)
    mock_rpc_client.upsert_coffee_image.assert_called_once()
    call_args = mock_rpc_client.upsert_coffee_image.call_args
    assert call_args[1]['imagekit_url'] is None
    assert call_args[1]['imagekit_file_id'] is None
    assert call_args[1]['imagekit_upload_time'] is None


@patch('src.images.imagekit_integration.ImageKitIntegrationService')
def test_complete_imagekit_workflow_upload_failure(MockImageKitIntegration, artifact_mapper_with_imagekit, mock_rpc_client):
    """Test complete ImageKit workflow when upload fails."""
    # Mock the ImageKit integration service to return upload failure
    mock_integration = Mock()
    mock_integration.process_image_with_imagekit.return_value = {
        'url': 'https://example.com/fail.jpg',
        'is_duplicate': False,
        'imagekit_upload_failed': True,
        'imagekit_error': 'Network timeout',
        'fallback_url': 'https://example.com/fail.jpg',
        'integration_status': 'completed'
    }
    MockImageKitIntegration.return_value = mock_integration
    
    # Mock RPC client response
    mock_rpc_client.upsert_coffee_image.return_value = 'img_789'
    
    # Test data
    coffee_data = {
        'id': 'coffee_123',
        'name': 'Test Coffee',
        'images': [
            {
                'url': 'https://example.com/fail.jpg',
                'alt': 'Failed Image',
                'width': 800,
                'height': 600
            }
        ]
    }
    
    # Process the coffee data
    result = artifact_mapper_with_imagekit.map_coffee_data(coffee_data)
    
    # Verify ImageKit integration was called
    mock_integration.process_image_with_imagekit.assert_called_once()
    
    # Verify RPC client was called with fallback URL
    mock_rpc_client.upsert_coffee_image.assert_called_once()
    call_args = mock_rpc_client.upsert_coffee_image.call_args
    assert call_args[1]['imagekit_url'] is None
    assert call_args[1]['imagekit_file_id'] is None
    assert call_args[1]['imagekit_upload_time'] is None
    assert call_args[1]['fallback_url'] == 'https://example.com/fail.jpg'


@patch('src.images.imagekit_integration.ImageKitIntegrationService')
def test_complete_imagekit_workflow_integration_error(MockImageKitIntegration, artifact_mapper_with_imagekit, mock_rpc_client):
    """Test complete ImageKit workflow when integration fails."""
    # Mock the ImageKit integration service to return integration error
    mock_integration = Mock()
    mock_integration.process_image_with_imagekit.return_value = {
        'url': 'https://example.com/error.jpg',
        'integration_status': 'error',
        'integration_error': 'Service unavailable',
        'fallback_url': 'https://example.com/error.jpg'
    }
    MockImageKitIntegration.return_value = mock_integration
    
    # Mock RPC client response
    mock_rpc_client.upsert_coffee_image.return_value = 'img_error'
    
    # Test data
    coffee_data = {
        'id': 'coffee_123',
        'name': 'Test Coffee',
        'images': [
            {
                'url': 'https://example.com/error.jpg',
                'alt': 'Error Image',
                'width': 800,
                'height': 600
            }
        ]
    }
    
    # Process the coffee data
    result = artifact_mapper_with_imagekit.map_coffee_data(coffee_data)
    
    # Verify ImageKit integration was called
    mock_integration.process_image_with_imagekit.assert_called_once()
    
    # Verify RPC client was called with fallback URL
    mock_rpc_client.upsert_coffee_image.assert_called_once()
    call_args = mock_rpc_client.upsert_coffee_image.call_args
    assert call_args[1]['imagekit_url'] is None
    assert call_args[1]['imagekit_file_id'] is None
    assert call_args[1]['imagekit_upload_time'] is None
    assert call_args[1]['fallback_url'] == 'https://example.com/error.jpg'


@patch('src.images.imagekit_integration.ImageKitIntegrationService')
def test_complete_imagekit_workflow_batch_processing(MockImageKitIntegration, artifact_mapper_with_imagekit, mock_rpc_client):
    """Test complete ImageKit workflow with batch image processing."""
    # Mock the ImageKit integration service for batch processing
    mock_integration = Mock()
    mock_integration.process_batch_with_imagekit.return_value = [
        {
            'url': 'https://example.com/img1.jpg',
            'is_duplicate': False,
            'imagekit_url': 'https://ik.imagekit.io/test/img1.jpg',
            'imagekit_file_id': 'file_1',
            'imagekit_upload_time': 1.0,
            'integration_status': 'completed'
        },
        {
            'url': 'https://example.com/img2.jpg',
            'is_duplicate': True,
            'existing_image_id': 'img_existing',
            'integration_status': 'completed'
        },
        {
            'url': 'https://example.com/img3.jpg',
            'is_duplicate': False,
            'imagekit_upload_failed': True,
            'imagekit_error': 'Upload failed',
            'fallback_url': 'https://example.com/img3.jpg',
            'integration_status': 'completed'
        }
    ]
    MockImageKitIntegration.return_value = mock_integration
    
    # Mock RPC client responses
    mock_rpc_client.upsert_coffee_image.side_effect = ['img_1', 'img_existing', 'img_3']
    
    # Test data with multiple images
    coffee_data = {
        'id': 'coffee_123',
        'name': 'Test Coffee',
        'images': [
            {
                'url': 'https://example.com/img1.jpg',
                'alt': 'Image 1',
                'width': 800,
                'height': 600
            },
            {
                'url': 'https://example.com/img2.jpg',
                'alt': 'Image 2',
                'width': 1024,
                'height': 768
            },
            {
                'url': 'https://example.com/img3.jpg',
                'alt': 'Image 3',
                'width': 640,
                'height': 480
            }
        ]
    }
    
    # Process the coffee data
    result = artifact_mapper_with_imagekit.map_coffee_data(coffee_data)
    
    # Verify ImageKit integration was called for batch processing
    mock_integration.process_batch_with_imagekit.assert_called_once()
    
    # Verify RPC client was called for each image
    assert mock_rpc_client.upsert_coffee_image.call_count == 3
    
    # Verify first image (successful upload)
    call_args_1 = mock_rpc_client.upsert_coffee_image.call_args_list[0]
    assert call_args_1[1]['imagekit_url'] == 'https://ik.imagekit.io/test/img1.jpg'
    assert call_args_1[1]['imagekit_file_id'] == 'file_1'
    assert call_args_1[1]['imagekit_upload_time'] == 1.0
    
    # Verify second image (duplicate)
    call_args_2 = mock_rpc_client.upsert_coffee_image.call_args_list[1]
    assert call_args_2[1]['imagekit_url'] is None
    assert call_args_2[1]['imagekit_file_id'] is None
    assert call_args_2[1]['imagekit_upload_time'] is None
    
    # Verify third image (upload failure)
    call_args_3 = mock_rpc_client.upsert_coffee_image.call_args_list[2]
    assert call_args_3[1]['imagekit_url'] is None
    assert call_args_3[1]['imagekit_file_id'] is None
    assert call_args_3[1]['imagekit_upload_time'] is None
    assert call_args_3[1]['fallback_url'] == 'https://example.com/img3.jpg'


@patch('src.images.imagekit_integration.ImageKitIntegrationService')
def test_complete_imagekit_workflow_without_imagekit(MockImageKitIntegration, artifact_mapper_with_imagekit, mock_rpc_client):
    """Test complete workflow when ImageKit is disabled."""
    # Disable ImageKit
    artifact_mapper_with_imagekit.enable_imagekit = False
    
    # Mock RPC client response
    mock_rpc_client.upsert_coffee_image.return_value = 'img_no_imagekit'
    
    # Test data
    coffee_data = {
        'id': 'coffee_123',
        'name': 'Test Coffee',
        'images': [
            {
                'url': 'https://example.com/no_imagekit.jpg',
                'alt': 'No ImageKit Image',
                'width': 800,
                'height': 600
            }
        ]
    }
    
    # Process the coffee data
    result = artifact_mapper_with_imagekit.map_coffee_data(coffee_data)
    
    # Verify ImageKit integration was not called
    MockImageKitIntegration.assert_not_called()
    
    # Verify RPC client was called without ImageKit parameters
    mock_rpc_client.upsert_coffee_image.assert_called_once()
    call_args = mock_rpc_client.upsert_coffee_image.call_args
    assert call_args[1]['imagekit_url'] is None
    assert call_args[1]['imagekit_file_id'] is None
    assert call_args[1]['imagekit_upload_time'] is None
    assert call_args[1]['fallback_url'] is None


@patch('src.images.imagekit_integration.ImageKitIntegrationService')
def test_complete_imagekit_workflow_without_deduplication(MockImageKitIntegration, artifact_mapper_with_imagekit, mock_rpc_client):
    """Test complete workflow when deduplication is disabled."""
    # Disable deduplication
    artifact_mapper_with_imagekit.enable_deduplication = False
    
    # Mock the ImageKit integration service
    mock_integration = Mock()
    mock_integration.process_image_with_imagekit.return_value = {
        'url': 'https://example.com/nodedup.jpg',
        'is_duplicate': False,
        'imagekit_url': 'https://ik.imagekit.io/test/nodedup.jpg',
        'imagekit_file_id': 'file_nodedup',
        'imagekit_upload_time': 1.2,
        'integration_status': 'completed'
    }
    MockImageKitIntegration.return_value = mock_integration
    
    # Mock RPC client response
    mock_rpc_client.upsert_coffee_image.return_value = 'img_nodedup'
    
    # Test data
    coffee_data = {
        'id': 'coffee_123',
        'name': 'Test Coffee',
        'images': [
            {
                'url': 'https://example.com/nodedup.jpg',
                'alt': 'No Dedup Image',
                'width': 800,
                'height': 600
            }
        ]
    }
    
    # Process the coffee data
    result = artifact_mapper_with_imagekit.map_coffee_data(coffee_data)
    
    # Verify ImageKit integration was called
    mock_integration.process_image_with_imagekit.assert_called_once()
    
    # Verify RPC client was called with ImageKit URL
    mock_rpc_client.upsert_coffee_image.assert_called_once()
    call_args = mock_rpc_client.upsert_coffee_image.call_args
    assert call_args[1]['imagekit_url'] == 'https://ik.imagekit.io/test/nodedup.jpg'
    assert call_args[1]['imagekit_file_id'] == 'file_nodedup'
    assert call_args[1]['imagekit_upload_time'] == 1.2


@patch('src.images.imagekit_integration.ImageKitIntegrationService')
def test_complete_imagekit_workflow_without_both_services(MockImageKitIntegration, artifact_mapper_with_imagekit, mock_rpc_client):
    """Test complete workflow when both services are disabled."""
    # Disable both services
    artifact_mapper_with_imagekit.enable_imagekit = False
    artifact_mapper_with_imagekit.enable_deduplication = False
    
    # Mock RPC client response
    mock_rpc_client.upsert_coffee_image.return_value = 'img_no_services'
    
    # Test data
    coffee_data = {
        'id': 'coffee_123',
        'name': 'Test Coffee',
        'images': [
            {
                'url': 'https://example.com/no_services.jpg',
                'alt': 'No Services Image',
                'width': 800,
                'height': 600
            }
        ]
    }
    
    # Process the coffee data
    result = artifact_mapper_with_imagekit.map_coffee_data(coffee_data)
    
    # Verify ImageKit integration was not called
    MockImageKitIntegration.assert_not_called()
    
    # Verify RPC client was called without ImageKit parameters
    mock_rpc_client.upsert_coffee_image.assert_called_once()
    call_args = mock_rpc_client.upsert_coffee_image.call_args
    assert call_args[1]['imagekit_url'] is None
    assert call_args[1]['imagekit_file_id'] is None
    assert call_args[1]['imagekit_upload_time'] is None
    assert call_args[1]['fallback_url'] is None
