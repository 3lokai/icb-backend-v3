"""
Unit tests for ArtifactMapper ImageKit integration.

Tests the integration of ImageKit upload functionality
with the ArtifactMapper for processing coffee images.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from src.validator.artifact_mapper import ArtifactMapper
from src.config.imagekit_config import ImageKitConfig
from src.images.imagekit_integration import ImageKitIntegrationService


@pytest.fixture
def mock_rpc_client():
    """Create mock RPC client for testing."""
    return Mock()


@pytest.fixture
def imagekit_config():
    """Create ImageKit configuration for testing."""
    return ImageKitConfig(
        public_key="public_test_key",
        private_key="private_test_key",
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


@pytest.fixture
def artifact_mapper_without_imagekit(mock_rpc_client):
    """Create ArtifactMapper without ImageKit integration."""
    return ArtifactMapper(
        rpc_client=mock_rpc_client,
        enable_imagekit=False
    )


def test_artifact_mapper_init_with_imagekit(artifact_mapper_with_imagekit, imagekit_config):
    """Test ArtifactMapper initialization with ImageKit enabled."""
    assert artifact_mapper_with_imagekit.enable_imagekit is True
    assert artifact_mapper_with_imagekit.imagekit_config == imagekit_config
    assert artifact_mapper_with_imagekit.imagekit_integration is not None
    assert isinstance(artifact_mapper_with_imagekit.imagekit_integration, ImageKitIntegrationService)


def test_artifact_mapper_init_without_imagekit(artifact_mapper_without_imagekit):
    """Test ArtifactMapper initialization without ImageKit."""
    assert artifact_mapper_without_imagekit.enable_imagekit is False
    assert artifact_mapper_without_imagekit.imagekit_config is None
    assert artifact_mapper_without_imagekit.imagekit_integration is None


@patch('src.validator.artifact_mapper.ImageKitIntegrationService')
def test_artifact_mapper_init_with_missing_config(MockImageKitIntegration, mock_rpc_client):
    """Test ArtifactMapper initialization with missing ImageKit config."""
    # Should not create ImageKit integration service without config
    mapper = ArtifactMapper(
        rpc_client=mock_rpc_client,
        enable_imagekit=True,
        imagekit_config=None
    )
    
    assert mapper.enable_imagekit is True
    assert mapper.imagekit_config is None
    assert mapper.imagekit_integration is None
    MockImageKitIntegration.assert_not_called()


@patch('src.validator.artifact_mapper.ImageKitIntegrationService')
def test_artifact_mapper_init_with_missing_rpc_client(MockImageKitIntegration, imagekit_config):
    """Test ArtifactMapper initialization with missing RPC client."""
    # Should not create ImageKit integration service without RPC client
    mapper = ArtifactMapper(
        rpc_client=None,
        enable_imagekit=True,
        imagekit_config=imagekit_config
    )
    
    assert mapper.enable_imagekit is True
    assert mapper.imagekit_config == imagekit_config
    assert mapper.imagekit_integration is None
    MockImageKitIntegration.assert_not_called()


@patch('src.validator.artifact_mapper.ImageKitIntegrationService')
def test_artifact_mapper_init_with_both_required(MockImageKitIntegration, mock_rpc_client, imagekit_config):
    """Test ArtifactMapper initialization with both RPC client and config."""
    # Should create ImageKit integration service with both required components
    mapper = ArtifactMapper(
        rpc_client=mock_rpc_client,
        enable_imagekit=True,
        imagekit_config=imagekit_config
    )
    
    assert mapper.enable_imagekit is True
    assert mapper.imagekit_config == imagekit_config
    assert mapper.imagekit_integration is not None
    MockImageKitIntegration.assert_called_once_with(
        rpc_client=mock_rpc_client,
        imagekit_config=imagekit_config,
            enable_deduplication=True,
        enable_imagekit=True
    )


@patch('src.validator.artifact_mapper.ImageKitIntegrationService')
def test_artifact_mapper_init_with_custom_deduplication(MockImageKitIntegration, mock_rpc_client, imagekit_config):
    """Test ArtifactMapper initialization with custom deduplication settings."""
    # Should create ImageKit integration service with custom deduplication settings
    mapper = ArtifactMapper(
        rpc_client=mock_rpc_client,
        enable_imagekit=True,
        imagekit_config=imagekit_config,
            enable_image_deduplication=False
    )
    
    MockImageKitIntegration.assert_called_once_with(
        rpc_client=mock_rpc_client,
        imagekit_config=imagekit_config,
            enable_deduplication=False,
        enable_imagekit=True
    )


@patch('src.validator.artifact_mapper.ImageKitIntegrationService')
def test_artifact_mapper_init_with_custom_imagekit(MockImageKitIntegration, mock_rpc_client, imagekit_config):
    """Test ArtifactMapper initialization with custom ImageKit settings."""
    # Should NOT create ImageKit integration service when ImageKit is disabled
    mapper = ArtifactMapper(
        rpc_client=mock_rpc_client,
        enable_imagekit=False,  # Disable ImageKit
        imagekit_config=imagekit_config
    )
    
    # When enable_imagekit=False, ImageKitIntegrationService should not be called
    MockImageKitIntegration.assert_not_called()


@patch('src.validator.artifact_mapper.ImageKitIntegrationService')
def test_artifact_mapper_init_with_all_custom_settings(MockImageKitIntegration, mock_rpc_client, imagekit_config):
    """Test ArtifactMapper initialization with all custom settings."""
    # Should create ImageKit integration service with all custom settings
    mapper = ArtifactMapper(
        rpc_client=mock_rpc_client,
        enable_imagekit=True,
        imagekit_config=imagekit_config,
            enable_image_deduplication=False
    )
    
    MockImageKitIntegration.assert_called_once_with(
        rpc_client=mock_rpc_client,
        imagekit_config=imagekit_config,
            enable_deduplication=False,
        enable_imagekit=True
    )


@patch('src.validator.artifact_mapper.ImageKitIntegrationService')
def test_artifact_mapper_init_with_defaults(MockImageKitIntegration, mock_rpc_client, imagekit_config):
    """Test ArtifactMapper initialization with default settings."""
    # Should create ImageKit integration service with default settings
    mapper = ArtifactMapper(
        rpc_client=mock_rpc_client,
        enable_imagekit=True,
        imagekit_config=imagekit_config
    )
    
    MockImageKitIntegration.assert_called_once_with(
        rpc_client=mock_rpc_client,
        imagekit_config=imagekit_config,
            enable_deduplication=True,  # Default
        enable_imagekit=True
    )


@patch('src.validator.artifact_mapper.ImageKitIntegrationService')
def test_artifact_mapper_init_with_minimal_settings(MockImageKitIntegration, mock_rpc_client, imagekit_config):
    """Test ArtifactMapper initialization with minimal settings."""
    # Should create ImageKit integration service with minimal settings
    mapper = ArtifactMapper(
        rpc_client=mock_rpc_client,
        enable_imagekit=True,
        imagekit_config=imagekit_config
    )
    
    MockImageKitIntegration.assert_called_once_with(
        rpc_client=mock_rpc_client,
        imagekit_config=imagekit_config,
            enable_deduplication=True,  # Default
        enable_imagekit=True
    )


@patch('src.validator.artifact_mapper.ImageKitIntegrationService')
def test_artifact_mapper_init_with_explicit_defaults(MockImageKitIntegration, mock_rpc_client, imagekit_config):
    """Test ArtifactMapper initialization with explicit default settings."""
    # Should create ImageKit integration service with explicit default settings
    mapper = ArtifactMapper(
        rpc_client=mock_rpc_client,
        enable_imagekit=True,
        imagekit_config=imagekit_config,
            enable_image_deduplication=True  # Explicit default
    )
    
    MockImageKitIntegration.assert_called_once_with(
        rpc_client=mock_rpc_client,
        imagekit_config=imagekit_config,
            enable_deduplication=True,
        enable_imagekit=True
    )


@patch('src.validator.artifact_mapper.ImageKitIntegrationService')
def test_artifact_mapper_init_with_explicit_disabled(MockImageKitIntegration, mock_rpc_client, imagekit_config):
    """Test ArtifactMapper initialization with explicit disabled settings."""
    # Should create ImageKit integration service with explicit disabled settings
    mapper = ArtifactMapper(
        rpc_client=mock_rpc_client,
        enable_imagekit=True,
        imagekit_config=imagekit_config,
            enable_image_deduplication=False  # Explicit disabled
    )
    
    MockImageKitIntegration.assert_called_once_with(
        rpc_client=mock_rpc_client,
        imagekit_config=imagekit_config,
            enable_deduplication=False,
        enable_imagekit=True
    )


@patch('src.validator.artifact_mapper.ImageKitIntegrationService')
def test_artifact_mapper_init_with_explicit_enabled(MockImageKitIntegration, mock_rpc_client, imagekit_config):
    """Test ArtifactMapper initialization with explicit enabled settings."""
    # Should create ImageKit integration service with explicit enabled settings
    mapper = ArtifactMapper(
        rpc_client=mock_rpc_client,
        enable_imagekit=True,
        imagekit_config=imagekit_config,
            enable_image_deduplication=True  # Explicit enabled
    )
    
    MockImageKitIntegration.assert_called_once_with(
        rpc_client=mock_rpc_client,
        imagekit_config=imagekit_config,
            enable_deduplication=True,
        enable_imagekit=True
    )


@patch('src.validator.artifact_mapper.ImageKitIntegrationService')
def test_artifact_mapper_init_with_explicit_both_disabled(MockImageKitIntegration, mock_rpc_client, imagekit_config):
    """Test ArtifactMapper initialization with both services explicitly disabled."""
    # Should NOT create ImageKit integration service when ImageKit is disabled
    mapper = ArtifactMapper(
        rpc_client=mock_rpc_client,
        enable_imagekit=False,  # Disabled
        imagekit_config=imagekit_config,
        enable_image_deduplication=False  # Disabled
    )
    
    # When enable_imagekit=False, ImageKitIntegrationService should not be called
    MockImageKitIntegration.assert_not_called()


@patch('src.validator.artifact_mapper.ImageKitIntegrationService')
def test_artifact_mapper_init_with_explicit_both_enabled(MockImageKitIntegration, mock_rpc_client, imagekit_config):
    """Test ArtifactMapper initialization with both services explicitly enabled."""
    # Should create ImageKit integration service with both services enabled
    mapper = ArtifactMapper(
        rpc_client=mock_rpc_client,
        enable_imagekit=True,  # Enabled
        imagekit_config=imagekit_config,
            enable_image_deduplication=True  # Enabled
    )
    
    MockImageKitIntegration.assert_called_once_with(
        rpc_client=mock_rpc_client,
        imagekit_config=imagekit_config,
            enable_deduplication=True,
        enable_imagekit=True
    )


@patch('src.validator.artifact_mapper.ImageKitIntegrationService')
def test_artifact_mapper_init_with_mixed_settings(MockImageKitIntegration, mock_rpc_client, imagekit_config):
    """Test ArtifactMapper initialization with mixed service settings."""
    # Should create ImageKit integration service with mixed settings
    mapper = ArtifactMapper(
        rpc_client=mock_rpc_client,
        enable_imagekit=True,  # Enabled
        imagekit_config=imagekit_config,
            enable_image_deduplication=False  # Disabled
    )
    
    MockImageKitIntegration.assert_called_once_with(
        rpc_client=mock_rpc_client,
        imagekit_config=imagekit_config,
            enable_deduplication=False,
        enable_imagekit=True
    )


@patch('src.validator.artifact_mapper.ImageKitIntegrationService')
def test_artifact_mapper_init_with_opposite_mixed_settings(MockImageKitIntegration, mock_rpc_client, imagekit_config):
    """Test ArtifactMapper initialization with opposite mixed service settings."""
    # Should NOT create ImageKit integration service when ImageKit is disabled
    mapper = ArtifactMapper(
        rpc_client=mock_rpc_client,
        enable_imagekit=False,  # Disabled
        imagekit_config=imagekit_config,
        enable_image_deduplication=True  # Enabled
    )
    
    # When enable_imagekit=False, ImageKitIntegrationService should not be called
    MockImageKitIntegration.assert_not_called()
