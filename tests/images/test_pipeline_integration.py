"""
Integration tests for image deduplication with A.1-A.5 pipeline.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone

from src.validator.artifact_mapper import ArtifactMapper
from src.validator.rpc_client import RPCClient
from src.images.deduplication_service import ImageDeduplicationService
from src.images.hash_computation import ImageHashComputer
from src.validator.models import ArtifactModel, ProductModel, VariantModel, ImageModel


class TestImageDeduplicationPipelineIntegration:
    """Test cases for image deduplication integration with A.1-A.5 pipeline."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_rpc_client = Mock(spec=RPCClient)
        self.mock_hash_computer = Mock(spec=ImageHashComputer)
        self.mock_deduplication_service = Mock(spec=ImageDeduplicationService)
        
        # Mock RPC client methods
        self.mock_rpc_client.upsert_coffee.return_value = 'coffee-123'
        self.mock_rpc_client.upsert_variant.return_value = 'variant-456'
        self.mock_rpc_client.insert_price.return_value = 'price-789'
        self.mock_rpc_client.upsert_coffee_image.return_value = 'image-101'
        
        # Initialize artifact mapper with deduplication
        self.artifact_mapper = ArtifactMapper(
            rpc_client=self.mock_rpc_client,
            enable_image_deduplication=True
        )
        
        # Mock the deduplication service
        self.artifact_mapper.deduplication_service = self.mock_deduplication_service
    
    def create_test_artifact(self) -> ArtifactModel:
        """Create a test artifact with images."""
        # Create test images
        images = [
            ImageModel(
                url='https://example.com/image1.jpg',
                alt_text='Coffee Image 1',
                order=1,
                source_id='img_001',
                width=800,
                height=600
            ),
            ImageModel(
                url='https://example.com/image2.jpg',
                alt_text='Coffee Image 2',
                order=2,
                source_id='img_002',
                width=1024,
                height=768
            )
        ]
        
        # Create test variant
        variant = VariantModel(
            platform_variant_id='variant_123',
            sku='COFFEE-001',
            title='Ethiopian Yirgacheffe - 250g',
            price='25.99',
            price_decimal=25.99,
            currency='USD',
            in_stock=True,
            weight_unit='g',
            grams=250
        )
        
        # Create test product
        product = ProductModel(
            platform_product_id='product_123',
            title='Ethiopian Yirgacheffe',
            description_md='A bright and floral coffee from Ethiopia',
            source_url='https://roaster.com/ethiopian-yirgacheffe',
            images=images,
            variants=[variant]
        )
        
        # Create test artifact
        artifact = ArtifactModel(
            product=product,
            scraped_at=datetime.now(timezone.utc),
            source='shopify',
            roaster_domain='roaster.com'
        )
        
        return artifact
    
    def test_artifact_mapper_with_deduplication_enabled(self):
        """Test artifact mapper with deduplication enabled."""
        # Create test artifact
        artifact = self.create_test_artifact()
        
        # Mock deduplication service response
        mock_deduplicated_images = [
            {
                'url': 'https://example.com/image1.jpg',
                'alt': 'Coffee Image 1',
                'width': 800,
                'height': 600,
                'sort_order': 1,
                'source_raw': {'source_id': 'img_001'},
                'content_hash': 'hash123',
                'is_duplicate': False,
                'deduplication_status': 'new_image'
            },
            {
                'url': 'https://example.com/image2.jpg',
                'alt': 'Coffee Image 2',
                'width': 1024,
                'height': 768,
                'sort_order': 2,
                'source_raw': {'source_id': 'img_002'},
                'content_hash': 'hash456',
                'is_duplicate': True,
                'image_id': 'existing-image-789',
                'deduplication_status': 'skipped_duplicate'
            }
        ]
        
        self.mock_deduplication_service.process_batch_with_deduplication.return_value = mock_deduplicated_images
        
        # Map artifact to RPC payloads
        result = self.artifact_mapper.map_artifact_to_rpc_payloads(
            artifact, roaster_id='roaster-123'
        )
        
        # Verify deduplication service was called
        self.mock_deduplication_service.process_batch_with_deduplication.assert_called_once()
        
        # Verify images were processed with deduplication
        images_payloads = result['images']
        assert len(images_payloads) == 2
        
        # Check first image (new)
        image1 = images_payloads[0]
        assert image1['p_url'] == 'https://example.com/image1.jpg'
        assert image1['p_content_hash'] == 'hash123'
        assert image1['p_deduplication_status'] == 'new_image'
        
        # Check second image (duplicate)
        image2 = images_payloads[1]
        assert image2['p_url'] == 'https://example.com/image2.jpg'
        assert image2['p_content_hash'] == 'hash456'
        assert image2['p_deduplication_status'] == 'skipped_duplicate'
        assert image2['p_existing_image_id'] == 'existing-image-789'
    
    def test_artifact_mapper_with_deduplication_disabled(self):
        """Test artifact mapper with deduplication disabled."""
        # Create artifact mapper without deduplication
        artifact_mapper = ArtifactMapper(
            rpc_client=self.mock_rpc_client,
            enable_image_deduplication=False
        )
        
        # Create test artifact
        artifact = self.create_test_artifact()
        
        # Map artifact to RPC payloads
        result = artifact_mapper.map_artifact_to_rpc_payloads(
            artifact, roaster_id='roaster-123'
        )
        
        # Verify deduplication service was not called
        assert artifact_mapper.deduplication_service is None
        
        # Verify images were processed without deduplication
        images_payloads = result['images']
        assert len(images_payloads) == 2
        
        # Check that deduplication fields are not present
        for image_payload in images_payloads:
            assert 'p_content_hash' not in image_payload
            assert 'p_deduplication_status' not in image_payload
            assert 'p_existing_image_id' not in image_payload
    
    def test_artifact_mapper_deduplication_service_failure(self):
        """Test artifact mapper when deduplication service fails."""
        # Create test artifact
        artifact = self.create_test_artifact()
        
        # Mock deduplication service failure
        self.mock_deduplication_service.process_batch_with_deduplication.side_effect = Exception("Deduplication service failed")
        
        # Map artifact to RPC payloads (should fall back to standard processing)
        result = self.artifact_mapper.map_artifact_to_rpc_payloads(
            artifact, roaster_id='roaster-123'
        )
        
        # Verify images were still processed (fallback to standard)
        images_payloads = result['images']
        assert len(images_payloads) == 2
        
        # Check that deduplication fields are not present (fallback mode)
        for image_payload in images_payloads:
            assert 'p_content_hash' not in image_payload
            assert 'p_deduplication_status' not in image_payload
    
    def test_artifact_mapper_with_mixed_deduplication_results(self):
        """Test artifact mapper with mixed deduplication results (some duplicates, some new)."""
        # Create test artifact
        artifact = self.create_test_artifact()
        
        # Mock deduplication service response with mixed results
        mock_deduplicated_images = [
            {
                'url': 'https://example.com/image1.jpg',
                'alt': 'Coffee Image 1',
                'width': 800,
                'height': 600,
                'sort_order': 1,
                'source_raw': {'source_id': 'img_001'},
                'content_hash': 'hash123',
                'is_duplicate': False,
                'deduplication_status': 'new_image'
            },
            {
                'url': 'https://example.com/image2.jpg',
                'alt': 'Coffee Image 2',
                'width': 1024,
                'height': 768,
                'sort_order': 2,
                'source_raw': {'source_id': 'img_002'},
                'content_hash': 'hash456',
                'is_duplicate': True,
                'image_id': 'existing-image-789',
                'deduplication_status': 'skipped_duplicate'
            }
        ]
        
        self.mock_deduplication_service.process_batch_with_deduplication.return_value = mock_deduplicated_images
        
        # Map artifact to RPC payloads
        result = self.artifact_mapper.map_artifact_to_rpc_payloads(
            artifact, roaster_id='roaster-123'
        )
        
        # Verify images were processed with deduplication
        images_payloads = result['images']
        assert len(images_payloads) == 2
        
        # Check first image (new)
        image1 = images_payloads[0]
        assert image1['p_deduplication_status'] == 'new_image'
        assert 'p_existing_image_id' not in image1
        
        # Check second image (duplicate)
        image2 = images_payloads[1]
        assert image2['p_deduplication_status'] == 'skipped_duplicate'
        assert image2['p_existing_image_id'] == 'existing-image-789'
    
    def test_artifact_mapper_with_deduplication_errors(self):
        """Test artifact mapper with deduplication errors."""
        # Create test artifact
        artifact = self.create_test_artifact()
        
        # Mock deduplication service response with errors
        mock_deduplicated_images = [
            {
                'url': 'https://example.com/image1.jpg',
                'alt': 'Coffee Image 1',
                'width': 800,
                'height': 600,
                'sort_order': 1,
                'source_raw': {'source_id': 'img_001'},
                'content_hash': 'hash123',
                'is_duplicate': False,
                'deduplication_status': 'new_image'
            },
            {
                'url': 'https://example.com/image2.jpg',
                'error': 'Hash computation failed',
                'deduplication_status': 'error'
            }
        ]
        
        self.mock_deduplication_service.process_batch_with_deduplication.return_value = mock_deduplicated_images
        
        # Map artifact to RPC payloads
        result = self.artifact_mapper.map_artifact_to_rpc_payloads(
            artifact, roaster_id='roaster-123'
        )
        
        # Verify only successful images were processed
        images_payloads = result['images']
        assert len(images_payloads) == 1  # Only one successful image
        
        # Check successful image
        image1 = images_payloads[0]
        assert image1['p_url'] == 'https://example.com/image1.jpg'
        assert image1['p_deduplication_status'] == 'new_image'
    
    def test_artifact_mapper_statistics(self):
        """Test artifact mapper statistics with deduplication."""
        # Create test artifact
        artifact = self.create_test_artifact()
        
        # Mock deduplication service response
        mock_deduplicated_images = [
            {
                'url': 'https://example.com/image1.jpg',
                'alt': 'Coffee Image 1',
                'content_hash': 'hash123',
                'is_duplicate': False,
                'deduplication_status': 'new_image'
            },
            {
                'url': 'https://example.com/image2.jpg',
                'alt': 'Coffee Image 2',
                'content_hash': 'hash456',
                'is_duplicate': True,
                'image_id': 'existing-image-789',
                'deduplication_status': 'skipped_duplicate'
            }
        ]
        
        self.mock_deduplication_service.process_batch_with_deduplication.return_value = mock_deduplicated_images
        
        # Map artifact to RPC payloads
        result = self.artifact_mapper.map_artifact_to_rpc_payloads(
            artifact, roaster_id='roaster-123'
        )
        
        # Verify statistics
        stats = self.artifact_mapper.get_mapping_stats()
        assert stats['images_mapped'] == 2
        assert stats['total_mapped'] == 1
        assert stats['mapping_errors'] == 0
    
    def test_artifact_mapper_with_no_images(self):
        """Test artifact mapper with no images."""
        # Create test artifact without images
        artifact = self.create_test_artifact()
        artifact.product.images = []
        
        # Map artifact to RPC payloads
        result = self.artifact_mapper.map_artifact_to_rpc_payloads(
            artifact, roaster_id='roaster-123'
        )
        
        # Verify no images were processed
        images_payloads = result['images']
        assert len(images_payloads) == 0
        
        # Verify deduplication service was not called
        self.mock_deduplication_service.process_batch_with_deduplication.assert_not_called()
    
    def test_artifact_mapper_metadata_only_mode(self):
        """Test artifact mapper in metadata-only mode (should skip images)."""
        # Create test artifact
        artifact = self.create_test_artifact()
        
        # Map artifact to RPC payloads in metadata-only mode
        result = self.artifact_mapper.map_artifact_to_rpc_payloads(
            artifact, roaster_id='roaster-123', metadata_only=True
        )
        
        # Verify no images were processed
        images_payloads = result['images']
        assert len(images_payloads) == 0
        
        # Verify deduplication service was not called
        self.mock_deduplication_service.process_batch_with_deduplication.assert_not_called()
