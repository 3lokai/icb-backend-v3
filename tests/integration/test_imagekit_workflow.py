"""
Integration tests for ImageKit workflow.

Tests the complete workflow from image processing through
ImageKit upload, deduplication, and database storage.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone
from src.config.imagekit_config import ImageKitConfig
from src.images.imagekit_integration import ImageKitIntegrationService
from src.validator.artifact_mapper import ArtifactMapper
from src.validator.rpc_client import RPCClient
from src.validator.models import ArtifactModel, ProductModel, VariantModel, ImageModel, SourceEnum


def create_test_artifact():
    """Create a test ArtifactModel for testing."""
    image = ImageModel(
        url='https://example.com/test.jpg',
        alt_text='Test Image',
        width=800,
        height=600,
        order=0,
        source_id='test_source'
    )

    variant = VariantModel(
        platform_variant_id="test_variant_123",
        title="Test Variant",
        price="25.99",
        currency="USD",
        grams=250,
        weight_unit="g"
    )

    product = ProductModel(
        platform_product_id="test_product_123",
        title="Test Coffee",
        source_url="https://example.com/product",
        images=[image],
        variants=[variant]
    )

    return ArtifactModel(
        source=SourceEnum.SHOPIFY,
        roaster_domain="test.example.com",
        scraped_at="2025-01-12T10:00:00Z",
        product=product
    )


@pytest.fixture
def mock_rpc_client():
    """Create mock RPC client for testing."""
    return Mock(spec=RPCClient)


@pytest.fixture
def imagekit_config():
    """Create ImageKit configuration for testing."""
    return ImageKitConfig(
        public_key="public_test_public_key",
        private_key="private_test_private_key",
        url_endpoint="https://ik.imagekit.io/test"
    )


@pytest.fixture
def artifact_mapper_with_imagekit(mock_rpc_client, imagekit_config):
    """Create ArtifactMapper with ImageKit integration enabled."""
    return ArtifactMapper(
        rpc_client=mock_rpc_client,
        enable_image_deduplication=False,
        enable_imagekit=True,
        imagekit_config=imagekit_config
    )


@patch('src.images.hash_computation.requests.get')
@patch('src.images.deduplication_service.ImageDeduplicationService.process_batch_with_deduplication')
def test_complete_imagekit_workflow_success(mock_deduplication, mock_requests_get, artifact_mapper_with_imagekit, mock_rpc_client):
    """Test complete ImageKit workflow with successful upload."""
    # Mock HTTP requests for image hash computation
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.headers = {'content-length': '12345', 'content-type': 'image/jpeg'}
    mock_response.content = b'fake_image_content'
    mock_requests_get.return_value = mock_response
    
    # Mock deduplication service
    mock_deduplication.return_value = [{
        'url': 'https://example.com/test.jpg',
        'is_duplicate': False,
        'content_hash': 'fake_hash_123',
        'deduplication_status': 'new_image'
    }]
    
    # Mock the ImageKit integration service instance method
    mock_integration = artifact_mapper_with_imagekit.imagekit_integration
    mock_integration.process_batch_with_imagekit = Mock(return_value=[{
        'url': 'https://example.com/test.jpg',
        'is_duplicate': False,
        'imagekit_url': 'https://ik.imagekit.io/test/uploaded.jpg',
        'imagekit_file_id': 'file_123',
        'imagekit_upload_time': 1.5,
        'integration_status': 'completed'
    }])
    
    # Mock RPC client response
    mock_rpc_client.upsert_coffee_image.return_value = 'img_456'
    
    # Test data
    coffee_data = create_test_artifact()
    
    # Process the coffee data
    result = artifact_mapper_with_imagekit.map_artifact_to_rpc_payloads(coffee_data, roaster_id="test_roaster")
    
    
    # Verify ImageKit integration was called
    mock_integration.process_batch_with_imagekit.assert_called_once()
    
    # Verify the result contains ImageKit data
    assert 'images' in result
    assert len(result['images']) == 1
    image_data = result['images'][0]
    assert image_data['p_imagekit_url'] == 'https://ik.imagekit.io/test/uploaded.jpg'
    assert image_data['p_processing_status'] == 'processed'


@patch('src.images.hash_computation.requests.get')
@patch('src.images.deduplication_service.ImageDeduplicationService.process_batch_with_deduplication')
def test_complete_imagekit_workflow_duplicate_found(mock_deduplication, mock_requests_get, artifact_mapper_with_imagekit, mock_rpc_client):
    """Test complete ImageKit workflow when duplicate is found."""
    # Mock HTTP requests for image hash computation
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.headers = {'content-length': '12345', 'content-type': 'image/jpeg'}
    mock_response.content = b'fake_image_content'
    mock_requests_get.return_value = mock_response
    
    # Mock deduplication service
    mock_deduplication.return_value = {
        'url': 'https://example.com/test.jpg',
        'is_duplicate': True,
        'hash': 'fake_hash_123',
        'deduplication_status': 'completed'
    }
    
    # Mock the ImageKit integration service instance method
    mock_integration = artifact_mapper_with_imagekit.imagekit_integration
    mock_integration.process_batch_with_imagekit = Mock(return_value=[{
        'url': 'https://example.com/duplicate.jpg',
        'is_duplicate': True,
        'existing_image_id': 'img_existing',
        'imagekit_upload_skipped': True,
        'integration_status': 'completed'
    }])
    
    # Mock RPC client response
    mock_rpc_client.upsert_coffee_image.return_value = 'img_existing'
    
    # Test data
    coffee_data = create_test_artifact()
    
    # Process the coffee data
    result = artifact_mapper_with_imagekit.map_artifact_to_rpc_payloads(coffee_data, roaster_id="test_roaster")
    
    # Verify ImageKit integration was called
    mock_integration.process_batch_with_imagekit.assert_called_once()
    
    # Verify the result contains duplicate data
    assert 'images' in result
    assert len(result['images']) == 1
    image_data = result['images'][0]
    assert image_data['p_processing_status'] == 'skipped_duplicate'
    assert image_data['p_existing_image_id'] == 'img_existing'


@patch('src.images.hash_computation.requests.get')
@patch('src.images.deduplication_service.ImageDeduplicationService.process_batch_with_deduplication')
def test_complete_imagekit_workflow_upload_failure(mock_deduplication, mock_requests_get, artifact_mapper_with_imagekit, mock_rpc_client):
    """Test complete ImageKit workflow when upload fails."""
    # Mock HTTP requests for image hash computation
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.headers = {'content-length': '12345', 'content-type': 'image/jpeg'}
    mock_response.content = b'fake_image_content'
    mock_requests_get.return_value = mock_response
    
    # Mock deduplication service
    mock_deduplication.return_value = [{
        'url': 'https://example.com/test.jpg',
        'is_duplicate': False,
        'content_hash': 'fake_hash_123',
        'deduplication_status': 'new_image'
    }]
    
    # Mock the ImageKit integration service instance method
    mock_integration = artifact_mapper_with_imagekit.imagekit_integration
    mock_integration.process_batch_with_imagekit = Mock(return_value=[{
        'url': 'https://example.com/fail.jpg',
        'is_duplicate': False,
        'imagekit_upload_failed': True,
        'imagekit_error': 'Network timeout',
        'fallback_url': 'https://example.com/fail.jpg',
        'integration_status': 'completed'
    }])
    
    # Mock RPC client response
    mock_rpc_client.upsert_coffee_image.return_value = 'img_789'
    
    # Test data
    coffee_data = create_test_artifact()
    
    # Process the coffee data
    result = artifact_mapper_with_imagekit.map_artifact_to_rpc_payloads(coffee_data, roaster_id="test_roaster")
    
    # Verify ImageKit integration was called
    mock_integration.process_batch_with_imagekit.assert_called_once()
    
    # Verify the result contains failure data
    assert 'images' in result
    assert len(result['images']) == 1
    image_data = result['images'][0]
    assert image_data['p_processing_status'] == 'imagekit_failed'
    assert image_data['p_fallback_url'] == 'https://example.com/fail.jpg'


@patch('src.images.hash_computation.requests.get')
@patch('src.images.deduplication_service.ImageDeduplicationService.process_batch_with_deduplication')
def test_complete_imagekit_workflow_integration_error(mock_deduplication, mock_requests_get, artifact_mapper_with_imagekit, mock_rpc_client):
    """Test complete ImageKit workflow when integration fails."""
    # Mock HTTP requests for image hash computation
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.headers = {'content-length': '12345', 'content-type': 'image/jpeg'}
    mock_response.content = b'fake_image_content'
    mock_requests_get.return_value = mock_response
    
    # Mock deduplication service
    mock_deduplication.return_value = [{
        'url': 'https://example.com/test.jpg',
        'is_duplicate': False,
        'content_hash': 'fake_hash_123',
        'deduplication_status': 'new_image'
    }]
    
    # Mock the ImageKit integration service instance method
    mock_integration = artifact_mapper_with_imagekit.imagekit_integration
    mock_integration.process_batch_with_imagekit = Mock(return_value=[{
        'url': 'https://example.com/error.jpg',
        'integration_status': 'error',
        'integration_error': 'Service unavailable',
        'fallback_url': 'https://example.com/error.jpg'
    }])
    
    # Mock RPC client response
    mock_rpc_client.upsert_coffee_image.return_value = 'img_error'
    
    # Test data
    coffee_data = create_test_artifact()
    
    # Process the coffee data
    result = artifact_mapper_with_imagekit.map_artifact_to_rpc_payloads(coffee_data, roaster_id="test_roaster")
    
    # Verify ImageKit integration was called
    mock_integration.process_batch_with_imagekit.assert_called_once()
    
    # Verify the result contains no images (integration error causes image to be skipped)
    assert 'images' in result
    assert len(result['images']) == 0  # Integration error causes image to be skipped


@patch('src.images.hash_computation.requests.get')
@patch('src.images.deduplication_service.ImageDeduplicationService.process_batch_with_deduplication')
def test_complete_imagekit_workflow_batch_processing(mock_deduplication, mock_requests_get, artifact_mapper_with_imagekit, mock_rpc_client):
    """Test complete ImageKit workflow with batch image processing."""
    # Mock HTTP requests for image hash computation
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.headers = {'content-length': '12345', 'content-type': 'image/jpeg'}
    mock_response.content = b'fake_image_content'
    mock_requests_get.return_value = mock_response
    
    # Mock deduplication service
    mock_deduplication.return_value = [{
        'url': 'https://example.com/test.jpg',
        'is_duplicate': False,
        'content_hash': 'fake_hash_123',
        'deduplication_status': 'new_image'
    }]
    
    # Mock the ImageKit integration service instance method
    mock_integration = artifact_mapper_with_imagekit.imagekit_integration
    mock_integration.process_batch_with_imagekit = Mock(return_value=[
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
            'imagekit_upload_skipped': True,
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
    ])
    
    # Mock RPC client responses
    mock_rpc_client.upsert_coffee_image.side_effect = ['img_1', 'img_existing', 'img_3']
    
    # Test data with multiple images
    coffee_data = create_test_artifact()
    
    # Process the coffee data
    result = artifact_mapper_with_imagekit.map_artifact_to_rpc_payloads(coffee_data, roaster_id="test_roaster")
    
    # Verify ImageKit integration was called for batch processing
    mock_integration.process_batch_with_imagekit.assert_called_once()
    
    # Verify the result contains batch processing data
    assert 'images' in result
    assert len(result['images']) == 3
    
    # Verify first image (successful upload)
    image_1 = result['images'][0]
    assert image_1['p_imagekit_url'] == 'https://ik.imagekit.io/test/img1.jpg'
    assert image_1['p_processing_status'] == 'processed'
    
    # Verify second image (duplicate)
    image_2 = result['images'][1]
    assert image_2['p_processing_status'] == 'skipped_duplicate'
    assert image_2['p_existing_image_id'] == 'img_existing'
    
    # Verify third image (upload failure)
    image_3 = result['images'][2]
    assert image_3['p_processing_status'] == 'imagekit_failed'
    assert image_3['p_fallback_url'] == 'https://example.com/img3.jpg'


@patch('src.images.hash_computation.requests.get')
@patch('src.images.deduplication_service.ImageDeduplicationService.process_batch_with_deduplication')
def test_complete_imagekit_workflow_without_imagekit(mock_deduplication, mock_requests_get, artifact_mapper_with_imagekit, mock_rpc_client):
    """Test complete workflow when ImageKit is disabled."""
    # Mock HTTP requests for image hash computation
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.headers = {'content-length': '12345', 'content-type': 'image/jpeg'}
    mock_response.content = b'fake_image_content'
    mock_requests_get.return_value = mock_response
    
    # Mock deduplication service
    mock_deduplication.return_value = [{
        'url': 'https://example.com/test.jpg',
        'content_hash': 'fake_hash_123',
        'is_duplicate': False,
        'duplicate_of': None,
        'image_id': 'img_no_imagekit',
        'deduplication_status': 'new_image'
    }]
    
    # Create a new ArtifactMapper with deduplication enabled and ImageKit disabled
    from src.validator.artifact_mapper import ArtifactMapper
    artifact_mapper = ArtifactMapper(
        rpc_client=mock_rpc_client,
        enable_image_deduplication=True,
        enable_imagekit=False
    )
    
    # Test data
    coffee_data = create_test_artifact()
    
    # Process the coffee data
    result = artifact_mapper.map_artifact_to_rpc_payloads(coffee_data, roaster_id="test_roaster")
    
    # Verify deduplication was called (since it's still enabled)
    mock_deduplication.assert_called_once()
    
    # Verify the result contains the expected data
    assert 'coffee' in result
    assert 'images' in result
    assert len(result['images']) == 1
    
    # Verify image data in result
    image_data = result['images'][0]
    assert image_data['p_url'] == 'https://example.com/test.jpg'
    assert image_data['p_content_hash'] == 'fake_hash_123'
    assert image_data['p_deduplication_status'] == 'new_image'


@patch('src.images.hash_computation.requests.get')
@patch('src.images.deduplication_service.ImageDeduplicationService.process_batch_with_deduplication')
def test_complete_imagekit_workflow_without_deduplication(mock_deduplication, mock_requests_get, artifact_mapper_with_imagekit, mock_rpc_client):
    """Test complete workflow when deduplication is disabled."""
    # Mock HTTP requests for image hash computation
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.headers = {'content-length': '12345', 'content-type': 'image/jpeg'}
    mock_response.content = b'fake_image_content'
    mock_requests_get.return_value = mock_response
    
    # Disable deduplication
    artifact_mapper_with_imagekit.enable_image_deduplication = False
    
    # Mock the ImageKit integration service instance
    mock_integration = artifact_mapper_with_imagekit.imagekit_integration
    mock_integration.process_batch_with_imagekit = Mock()
    mock_integration.process_batch_with_imagekit.return_value = [{
        'url': 'https://example.com/nodedup.jpg',
        'content_hash': 'fake_hash_123',
        'is_duplicate': False,
        'duplicate_of': None,
        'image_id': 'img_nodedup',
        'imagekit_url': 'https://ik.imagekit.io/test/nodedup.jpg',
        'integration_status': 'completed'
    }]
    
    # Test data
    coffee_data = create_test_artifact()
    
    # Process the coffee data
    result = artifact_mapper_with_imagekit.map_artifact_to_rpc_payloads(coffee_data, roaster_id="test_roaster")
    
    # Verify ImageKit integration was called
    mock_integration.process_batch_with_imagekit.assert_called_once()
    
    # Verify the result contains the expected data
    assert 'coffee' in result
    assert 'images' in result
    assert len(result['images']) == 1
    
    # Verify image data in result
    image_data = result['images'][0]
    assert image_data['p_url'] == 'https://example.com/nodedup.jpg'
    assert image_data['p_content_hash'] == 'fake_hash_123'
    assert image_data['p_processing_status'] == 'processed'
    assert image_data['p_imagekit_url'] == 'https://ik.imagekit.io/test/nodedup.jpg'


@patch('src.images.hash_computation.requests.get')
@patch('src.images.deduplication_service.ImageDeduplicationService.process_batch_with_deduplication')
def test_complete_imagekit_workflow_without_both_services(mock_deduplication, mock_requests_get, artifact_mapper_with_imagekit, mock_rpc_client):
    """Test complete workflow when both services are disabled."""
    # Mock HTTP requests for image hash computation
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.headers = {'content-length': '12345', 'content-type': 'image/jpeg'}
    mock_response.content = b'fake_image_content'
    mock_requests_get.return_value = mock_response
    
    # Mock deduplication service (not used when both services are disabled)
    mock_deduplication.return_value = [{
        'url': 'https://example.com/test.jpg',
        'content_hash': 'fake_hash_123',
        'is_duplicate': False,
        'duplicate_of': None,
        'image_id': 'img_no_services',
        'deduplication_status': 'new_image'
    }]
    
    # Disable both services
    artifact_mapper_with_imagekit.enable_imagekit = False
    artifact_mapper_with_imagekit.enable_image_deduplication = False
    
    # Test data
    coffee_data = create_test_artifact()
    
    # Process the coffee data
    result = artifact_mapper_with_imagekit.map_artifact_to_rpc_payloads(coffee_data, roaster_id="test_roaster")
    
    # Verify deduplication was NOT called (both services disabled)
    mock_deduplication.assert_not_called()
    
    # Verify the result contains the expected data
    assert 'coffee' in result
    assert 'images' in result
    assert len(result['images']) == 1
    
    # Verify image data in result (standard processing)
    image_data = result['images'][0]
    assert image_data['p_url'] == 'https://example.com/test.jpg'
    # Standard processing doesn't include processing_status
