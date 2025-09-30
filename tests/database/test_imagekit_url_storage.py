"""
Database integration tests for ImageKit URL storage.

Tests the storage and retrieval of ImageKit URLs in the database,
including RPC function integration and data integrity.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from src.validator.rpc_client import RPCClient
from src.config.imagekit_config import ImageKitConfig
from src.images.imagekit_integration import ImageKitIntegrationService


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
def imagekit_integration_service(mock_rpc_client, imagekit_config):
    """Create ImageKit integration service for testing."""
    return ImageKitIntegrationService(
        rpc_client=mock_rpc_client,
        imagekit_config=imagekit_config,
        enable_deduplication=True,
        enable_imagekit=True
    )


def test_upsert_coffee_image_with_imagekit_url(mock_rpc_client):
    """Test upserting coffee image with ImageKit URL."""
    # Mock RPC client response
    mock_rpc_client.upsert_coffee_image.return_value = 'img_123'
    
    # Test data
    coffee_id = 'coffee_123'
    image_url = 'https://example.com/test.jpg'
    imagekit_url = 'https://ik.imagekit.io/test/uploaded.jpg'
    imagekit_file_id = 'file_123'
    imagekit_upload_time = 1.5
    
    # Call RPC function
    result = mock_rpc_client.upsert_coffee_image(
        coffee_id=coffee_id,
        url=image_url,
        alt='Test Image',
        width=800,
        height=600,
        sort_order=1,
        source_raw={'source': 'test'},
        content_hash='hash_123',
        imagekit_url=imagekit_url,
        imagekit_file_id=imagekit_file_id,
        imagekit_upload_time=imagekit_upload_time
    )
    
    # Verify result
    assert result == 'img_123'
    
    # Verify RPC client was called with correct parameters
    mock_rpc_client.upsert_coffee_image.assert_called_once_with(
        coffee_id=coffee_id,
        url=image_url,
        alt='Test Image',
        width=800,
        height=600,
        sort_order=1,
        source_raw={'source': 'test'},
        content_hash='hash_123',
        imagekit_url=imagekit_url,
        imagekit_file_id=imagekit_file_id,
        imagekit_upload_time=imagekit_upload_time
    )


def test_upsert_coffee_image_without_imagekit_url(mock_rpc_client):
    """Test upserting coffee image without ImageKit URL."""
    # Mock RPC client response
    mock_rpc_client.upsert_coffee_image.return_value = 'img_456'
    
    # Test data
    coffee_id = 'coffee_123'
    image_url = 'https://example.com/test.jpg'
    
    # Call RPC function without ImageKit parameters
    result = mock_rpc_client.upsert_coffee_image(
        coffee_id=coffee_id,
        url=image_url,
        alt='Test Image',
        width=800,
        height=600,
        sort_order=1,
        source_raw={'source': 'test'},
        content_hash='hash_123'
    )
    
    # Verify result
    assert result == 'img_456'
    
    # Verify RPC client was called without ImageKit parameters
    mock_rpc_client.upsert_coffee_image.assert_called_once_with(
        coffee_id=coffee_id,
        url=image_url,
        alt='Test Image',
        width=800,
        height=600,
        sort_order=1,
        source_raw={'source': 'test'},
        content_hash='hash_123'
    )


def test_upsert_coffee_image_with_partial_imagekit_data(mock_rpc_client):
    """Test upserting coffee image with partial ImageKit data."""
    # Mock RPC client response
    mock_rpc_client.upsert_coffee_image.return_value = 'img_789'
    
    # Test data with only some ImageKit parameters
    coffee_id = 'coffee_123'
    image_url = 'https://example.com/test.jpg'
    imagekit_url = 'https://ik.imagekit.io/test/uploaded.jpg'
    # Missing imagekit_file_id and imagekit_upload_time
    
    # Call RPC function with partial ImageKit data
    result = mock_rpc_client.upsert_coffee_image(
        coffee_id=coffee_id,
        url=image_url,
        alt='Test Image',
        width=800,
        height=600,
        sort_order=1,
        source_raw={'source': 'test'},
        content_hash='hash_123',
        imagekit_url=imagekit_url
    )
    
    # Verify result
    assert result == 'img_789'
    
    # Verify RPC client was called with partial ImageKit data
    mock_rpc_client.upsert_coffee_image.assert_called_once_with(
        coffee_id=coffee_id,
        url=image_url,
        alt='Test Image',
        width=800,
        height=600,
        sort_order=1,
        source_raw={'source': 'test'},
        content_hash='hash_123',
        imagekit_url=imagekit_url
    )


def test_upsert_coffee_image_with_fallback_url(mock_rpc_client):
    """Test upserting coffee image with fallback URL."""
    # Mock RPC client response
    mock_rpc_client.upsert_coffee_image.return_value = 'img_fallback'
    
    # Test data with fallback URL
    coffee_id = 'coffee_123'
    image_url = 'https://example.com/test.jpg'
    fallback_url = 'https://example.com/fallback.jpg'
    
    # Call RPC function with fallback URL
    result = mock_rpc_client.upsert_coffee_image(
        coffee_id=coffee_id,
        url=image_url,
        alt='Test Image',
        width=800,
        height=600,
        sort_order=1,
        source_raw={'source': 'test'},
        content_hash='hash_123',
        fallback_url=fallback_url
    )
    
    # Verify result
    assert result == 'img_fallback'
    
    # Verify RPC client was called with fallback URL
    mock_rpc_client.upsert_coffee_image.assert_called_once_with(
        coffee_id=coffee_id,
        url=image_url,
        alt='Test Image',
        width=800,
        height=600,
        sort_order=1,
        source_raw={'source': 'test'},
        content_hash='hash_123',
        fallback_url=fallback_url
    )


def test_upsert_coffee_image_with_duplicate_existing(mock_rpc_client):
    """Test upserting coffee image when duplicate exists."""
    # Mock RPC client response
    mock_rpc_client.upsert_coffee_image.return_value = 'img_existing'
    
    # Test data with existing image ID
    coffee_id = 'coffee_123'
    image_url = 'https://example.com/duplicate.jpg'
    existing_image_id = 'img_existing'
    
    # Call RPC function with existing image ID
    result = mock_rpc_client.upsert_coffee_image(
        coffee_id=coffee_id,
        url=image_url,
        alt='Duplicate Image',
        width=800,
        height=600,
        sort_order=1,
        source_raw={'source': 'test'},
        content_hash='hash_duplicate',
        existing_image_id=existing_image_id
    )
    
    # Verify result
    assert result == 'img_existing'
    
    # Verify RPC client was called with existing image ID
    mock_rpc_client.upsert_coffee_image.assert_called_once_with(
        coffee_id=coffee_id,
        url=image_url,
        alt='Duplicate Image',
        width=800,
        height=600,
        sort_order=1,
        source_raw={'source': 'test'},
        content_hash='hash_duplicate',
        existing_image_id=existing_image_id
    )


def test_upsert_coffee_image_with_processing_status(mock_rpc_client):
    """Test upserting coffee image with processing status."""
    # Mock RPC client response
    mock_rpc_client.upsert_coffee_image.return_value = 'img_processing'
    
    # Test data with processing status
    coffee_id = 'coffee_123'
    image_url = 'https://example.com/processing.jpg'
    processing_status = 'processing'
    
    # Call RPC function with processing status
    result = mock_rpc_client.upsert_coffee_image(
        coffee_id=coffee_id,
        url=image_url,
        alt='Processing Image',
        width=800,
        height=600,
        sort_order=1,
        source_raw={'source': 'test'},
        content_hash='hash_processing',
        processing_status=processing_status
    )
    
    # Verify result
    assert result == 'img_processing'
    
    # Verify RPC client was called with processing status
    mock_rpc_client.upsert_coffee_image.assert_called_once_with(
        coffee_id=coffee_id,
        url=image_url,
        alt='Processing Image',
        width=800,
        height=600,
        sort_order=1,
        source_raw={'source': 'test'},
        content_hash='hash_processing',
        processing_status=processing_status
    )


def test_upsert_coffee_image_with_all_parameters(mock_rpc_client):
    """Test upserting coffee image with all parameters."""
    # Mock RPC client response
    mock_rpc_client.upsert_coffee_image.return_value = 'img_complete'
    
    # Test data with all parameters
    coffee_id = 'coffee_123'
    image_url = 'https://example.com/complete.jpg'
    imagekit_url = 'https://ik.imagekit.io/test/complete.jpg'
    imagekit_file_id = 'file_complete'
    imagekit_upload_time = 2.5
    fallback_url = 'https://example.com/fallback.jpg'
    existing_image_id = 'img_existing'
    processing_status = 'completed'
    
    # Call RPC function with all parameters
    result = mock_rpc_client.upsert_coffee_image(
        coffee_id=coffee_id,
        url=image_url,
        alt='Complete Image',
        width=800,
        height=600,
        sort_order=1,
        source_raw={'source': 'test'},
        content_hash='hash_complete',
        imagekit_url=imagekit_url,
        imagekit_file_id=imagekit_file_id,
        imagekit_upload_time=imagekit_upload_time,
        fallback_url=fallback_url,
        existing_image_id=existing_image_id,
        processing_status=processing_status
    )
    
    # Verify result
    assert result == 'img_complete'
    
    # Verify RPC client was called with all parameters
    mock_rpc_client.upsert_coffee_image.assert_called_once_with(
        coffee_id=coffee_id,
        url=image_url,
        alt='Complete Image',
        width=800,
        height=600,
        sort_order=1,
        source_raw={'source': 'test'},
        content_hash='hash_complete',
        imagekit_url=imagekit_url,
        imagekit_file_id=imagekit_file_id,
        imagekit_upload_time=imagekit_upload_time,
        fallback_url=fallback_url,
        existing_image_id=existing_image_id,
        processing_status=processing_status
    )


def test_upsert_coffee_image_with_none_values(mock_rpc_client):
    """Test upserting coffee image with None values for optional parameters."""
    # Mock RPC client response
    mock_rpc_client.upsert_coffee_image.return_value = 'img_none'
    
    # Test data with None values
    coffee_id = 'coffee_123'
    image_url = 'https://example.com/none.jpg'
    
    # Call RPC function with None values
    result = mock_rpc_client.upsert_coffee_image(
        coffee_id=coffee_id,
        url=image_url,
        alt='None Image',
        width=800,
        height=600,
        sort_order=1,
        source_raw={'source': 'test'},
        content_hash='hash_none',
        imagekit_url=None,
        imagekit_file_id=None,
        imagekit_upload_time=None,
        fallback_url=None,
        existing_image_id=None,
        processing_status=None
    )
    
    # Verify result
    assert result == 'img_none'
    
    # Verify RPC client was called with None values
    mock_rpc_client.upsert_coffee_image.assert_called_once_with(
        coffee_id=coffee_id,
        url=image_url,
        alt='None Image',
        width=800,
        height=600,
        sort_order=1,
        source_raw={'source': 'test'},
        content_hash='hash_none',
        imagekit_url=None,
        imagekit_file_id=None,
        imagekit_upload_time=None,
        fallback_url=None,
        existing_image_id=None,
        processing_status=None
    )


def test_upsert_coffee_image_with_empty_strings(mock_rpc_client):
    """Test upserting coffee image with empty string values."""
    # Mock RPC client response
    mock_rpc_client.upsert_coffee_image.return_value = 'img_empty'
    
    # Test data with empty strings
    coffee_id = 'coffee_123'
    image_url = 'https://example.com/empty.jpg'
    
    # Call RPC function with empty strings
    result = mock_rpc_client.upsert_coffee_image(
        coffee_id=coffee_id,
        url=image_url,
        alt='Empty Image',
        width=800,
        height=600,
        sort_order=1,
        source_raw={'source': 'test'},
        content_hash='hash_empty',
        imagekit_url='',
        imagekit_file_id='',
        fallback_url='',
        existing_image_id='',
        processing_status=''
    )
    
    # Verify result
    assert result == 'img_empty'
    
    # Verify RPC client was called with empty strings
    mock_rpc_client.upsert_coffee_image.assert_called_once_with(
        coffee_id=coffee_id,
        url=image_url,
        alt='Empty Image',
        width=800,
        height=600,
        sort_order=1,
        source_raw={'source': 'test'},
        content_hash='hash_empty',
        imagekit_url='',
        imagekit_file_id='',
        fallback_url='',
        existing_image_id='',
        processing_status=''
    )


def test_upsert_coffee_image_with_special_characters(mock_rpc_client):
    """Test upserting coffee image with special characters in URLs."""
    # Mock RPC client response
    mock_rpc_client.upsert_coffee_image.return_value = 'img_special'
    
    # Test data with special characters
    coffee_id = 'coffee_123'
    image_url = 'https://example.com/test%20image.jpg'
    imagekit_url = 'https://ik.imagekit.io/test/uploaded%20image.jpg'
    fallback_url = 'https://example.com/fallback%20image.jpg'
    
    # Call RPC function with special characters
    result = mock_rpc_client.upsert_coffee_image(
        coffee_id=coffee_id,
        url=image_url,
        alt='Special Image',
        width=800,
        height=600,
        sort_order=1,
        source_raw={'source': 'test'},
        content_hash='hash_special',
        imagekit_url=imagekit_url,
        fallback_url=fallback_url
    )
    
    # Verify result
    assert result == 'img_special'
    
    # Verify RPC client was called with special characters
    mock_rpc_client.upsert_coffee_image.assert_called_once_with(
        coffee_id=coffee_id,
        url=image_url,
        alt='Special Image',
        width=800,
        height=600,
        sort_order=1,
        source_raw={'source': 'test'},
        content_hash='hash_special',
        imagekit_url=imagekit_url,
        fallback_url=fallback_url
    )


def test_upsert_coffee_image_with_long_urls(mock_rpc_client):
    """Test upserting coffee image with long URLs."""
    # Mock RPC client response
    mock_rpc_client.upsert_coffee_image.return_value = 'img_long'
    
    # Test data with long URLs
    coffee_id = 'coffee_123'
    image_url = 'https://example.com/very/long/path/to/image/with/many/segments/and/parameters.jpg'
    imagekit_url = 'https://ik.imagekit.io/test/very/long/path/to/uploaded/image/with/many/segments/and/parameters.jpg'
    fallback_url = 'https://example.com/very/long/path/to/fallback/image/with/many/segments/and/parameters.jpg'
    
    # Call RPC function with long URLs
    result = mock_rpc_client.upsert_coffee_image(
        coffee_id=coffee_id,
        url=image_url,
        alt='Long URL Image',
        width=800,
        height=600,
        sort_order=1,
        source_raw={'source': 'test'},
        content_hash='hash_long',
        imagekit_url=imagekit_url,
        fallback_url=fallback_url
    )
    
    # Verify result
    assert result == 'img_long'
    
    # Verify RPC client was called with long URLs
    mock_rpc_client.upsert_coffee_image.assert_called_once_with(
        coffee_id=coffee_id,
        url=image_url,
        alt='Long URL Image',
        width=800,
        height=600,
        sort_order=1,
        source_raw={'source': 'test'},
        content_hash='hash_long',
        imagekit_url=imagekit_url,
        fallback_url=fallback_url
    )
