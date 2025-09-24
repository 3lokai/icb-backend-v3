"""
Integration tests for price-only image guards.

Tests the integration of image guards across the entire pipeline
to ensure price-only runs never trigger image operations.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, List

from src.validator.artifact_mapper import ArtifactMapper
from src.validator.database_integration import DatabaseIntegration
from src.validator.rpc_client import RPCClient
from src.validator.models import ArtifactModel, ProductModel, VariantModel, ImageModel, SourceEnum
from src.images.processing_guard import ImageProcessingGuard


class TestPriceOnlyImageGuardIntegration:
    """Integration tests for price-only image guards across the pipeline."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_supabase_client = Mock()
        self.mock_rpc_client = Mock()
        
        # Create test artifact with images
        self.test_artifact = self._create_test_artifact_with_images()
    
    def _create_test_artifact_with_images(self) -> ArtifactModel:
        """Create a test artifact with images."""
        # Create mock images
        images = [
            ImageModel(
                url="https://example.com/image1.jpg",
                alt_text="Test image 1",
                width=800,
                height=600,
                order=1,
                source_id="test_source_1"
            ),
            ImageModel(
                url="https://example.com/image2.jpg",
                alt_text="Test image 2",
                width=400,
                height=300,
                order=2,
                source_id="test_source_2"
            )
        ]
        
        # Create mock variant first
        variant = VariantModel(
            platform_variant_id="test_variant_123",
            title="Test Variant",
            price="25.99",
            currency="USD",
            grams=250,
            weight_unit="g"
        )
        
        # Create mock product with images and variants
        product = ProductModel(
            platform_product_id="test_product_123",
            title="Test Coffee",
            source_url="https://example.com/product",
            images=images,
            variants=[variant]
        )
        
        # Create artifact
        artifact = ArtifactModel(
            source=SourceEnum.SHOPIFY,
            roaster_domain="test.example.com",
            scraped_at="2025-01-12T10:00:00Z",
            product=product
        )
        
        return artifact
    
    def test_artifact_mapper_metadata_only_true(self):
        """Test ArtifactMapper with metadata_only=True skips image processing."""
        # Create mapper with metadata_only=True
        mapper = ArtifactMapper(metadata_only=True)
        
        # Mock the deduplication service to avoid actual processing
        mapper.deduplication_service = None
        
        # Map artifact to RPC payloads
        result = mapper.map_artifact_to_rpc_payloads(
            artifact=self.test_artifact,
            roaster_id="test_roaster",
            metadata_only=True
        )
        
        # Verify that images are not processed
        assert result['metadata_only'] is True
        assert result['images'] == []  # Should be empty for metadata-only
        assert len(result['coffee']) > 0  # Coffee data should be present
        assert len(result['variants']) > 0  # Variants should be present
        # Note: Prices may be empty if no price data in test artifact
        assert 'prices' in result
    
    def test_artifact_mapper_metadata_only_false(self):
        """Test ArtifactMapper with metadata_only=False processes images."""
        # Create mapper with metadata_only=False
        mapper = ArtifactMapper(metadata_only=False)
        
        # Mock the deduplication service
        mapper.deduplication_service = Mock()
        mapper.deduplication_service.process_batch_with_deduplication = Mock(
            return_value=[
                {
                    'url': 'https://example.com/image1.jpg',
                    'alt': 'Test image 1',
                    'width': 800,
                    'height': 600,
                    'sort_order': 1,
                    'source_raw': {'source_id': 'test_source_1'},
                    'content_hash': 'test_hash_1',
                    'imagekit_url': 'https://ik.imagekit.io/test/image1.jpg'
                }
            ]
        )
        
        # Map artifact to RPC payloads
        result = mapper.map_artifact_to_rpc_payloads(
            artifact=self.test_artifact,
            roaster_id="test_roaster",
            metadata_only=False
        )
        
        # Verify that images are processed
        assert result['metadata_only'] is False
        assert len(result['images']) > 0  # Should have images
        assert len(result['coffee']) > 0  # Coffee data should be present
        assert len(result['variants']) > 0  # Variants should be present
        # Note: Prices may be empty if no price data in test artifact
        assert 'prices' in result
    
    def test_database_integration_metadata_only_true(self):
        """Test DatabaseIntegration with metadata_only=True skips image upserts."""
        # Create database integration
        db_integration = DatabaseIntegration(supabase_client=self.mock_supabase_client)
        
        # Mock the RPC client
        db_integration.rpc_client = Mock()
        db_integration.rpc_client.upsert_coffee = Mock(return_value="test_coffee_id")
        db_integration.rpc_client.upsert_variant = Mock(return_value="test_variant_id")
        db_integration.rpc_client.insert_price = Mock(return_value="test_price_id")
        
        # Create mock validation result
        validation_result = Mock()
        validation_result.is_valid = True
        validation_result.artifact_data = self.test_artifact
        validation_result.artifact_id = "test_artifact_123"
        
        # Mock the artifact mapper
        db_integration.artifact_mapper = Mock()
        db_integration.artifact_mapper.map_artifact_to_rpc_payloads = Mock(
            return_value={
                'coffee': {'name': 'Test Coffee'},
                'variants': [{'name': 'Test Variant'}],
                'prices': [{'price': 25.99}],
                'images': [{'url': 'https://example.com/image1.jpg'}],
                'metadata_only': True
            }
        )
        
        # Upsert artifact with metadata_only=True
        result = db_integration.upsert_artifact_via_rpc(
            validation_result=validation_result,
            roaster_id="test_roaster",
            metadata_only=True
        )
        
        # Verify that image upserts were skipped
        assert result['success'] is True
        assert result['coffee_id'] == "test_coffee_id"
        assert len(result['variant_ids']) == 1
        assert len(result['price_ids']) == 1
        assert len(result['image_ids']) == 0  # Should be empty for metadata-only
        
        # Verify that upsert_coffee_image was not called
        db_integration.rpc_client.upsert_coffee_image.assert_not_called()
    
    def test_database_integration_metadata_only_false(self):
        """Test DatabaseIntegration with metadata_only=False processes images."""
        # Create database integration
        db_integration = DatabaseIntegration(supabase_client=self.mock_supabase_client)
        
        # Mock the RPC client
        db_integration.rpc_client = Mock()
        db_integration.rpc_client.upsert_coffee = Mock(return_value="test_coffee_id")
        db_integration.rpc_client.upsert_variant = Mock(return_value="test_variant_id")
        db_integration.rpc_client.insert_price = Mock(return_value="test_price_id")
        db_integration.rpc_client.upsert_coffee_image = Mock(return_value="test_image_id")
        
        # Create mock validation result
        validation_result = Mock()
        validation_result.is_valid = True
        validation_result.artifact_data = self.test_artifact
        validation_result.artifact_id = "test_artifact_123"
        
        # Mock the artifact mapper
        db_integration.artifact_mapper = Mock()
        db_integration.artifact_mapper.map_artifact_to_rpc_payloads = Mock(
            return_value={
                'coffee': {'name': 'Test Coffee'},
                'variants': [{'name': 'Test Variant'}],
                'prices': [{'price': 25.99}],
                'images': [{'url': 'https://example.com/image1.jpg'}],
                'metadata_only': False
            }
        )
        
        # Upsert artifact with metadata_only=False
        result = db_integration.upsert_artifact_via_rpc(
            validation_result=validation_result,
            roaster_id="test_roaster",
            metadata_only=False
        )
        
        # Verify that image upserts were processed
        assert result['success'] is True
        assert result['coffee_id'] == "test_coffee_id"
        assert len(result['variant_ids']) == 1
        assert len(result['price_ids']) == 1
        assert len(result['image_ids']) == 1  # Should have images
        
        # Verify that upsert_coffee_image was called
        db_integration.rpc_client.upsert_coffee_image.assert_called_once()
    
    def test_rpc_client_metadata_only_true(self):
        """Test RPCClient with metadata_only=True blocks image upserts."""
        # Create RPC client with metadata_only=True
        rpc_client = RPCClient(
            supabase_client=self.mock_supabase_client,
            metadata_only=True
        )
        
        # Attempt to upsert coffee image
        with pytest.raises(Exception, match="Image processing blocked for price-only run"):
            rpc_client.upsert_coffee_image(
                coffee_id="test_coffee_id",
                url="https://example.com/image1.jpg",
                alt="Test image"
            )
    
    def test_rpc_client_metadata_only_false(self):
        """Test RPCClient with metadata_only=False allows image upserts."""
        # Create RPC client with metadata_only=False
        rpc_client = RPCClient(
            supabase_client=self.mock_supabase_client,
            metadata_only=False
        )
        
        # Mock the RPC execution
        rpc_client._execute_rpc_with_retry = Mock(return_value="test_image_id")
        
        # Upsert coffee image
        result = rpc_client.upsert_coffee_image(
            coffee_id="test_coffee_id",
            url="https://example.com/image1.jpg",
            alt="Test image"
        )
        
        # Verify that the operation was allowed
        assert result == "test_image_id"
        rpc_client._execute_rpc_with_retry.assert_called_once()
    
    def test_end_to_end_price_only_pipeline(self):
        """Test end-to-end price-only pipeline with image guards."""
        # Create components with metadata_only=True
        mapper = ArtifactMapper(metadata_only=True)
        db_integration = DatabaseIntegration(supabase_client=self.mock_supabase_client)
        
        # Mock the RPC client entirely to avoid actual database calls
        mock_rpc_client = Mock()
        mock_rpc_client.upsert_coffee = Mock(return_value="test_coffee_id")
        mock_rpc_client.upsert_variant = Mock(return_value="test_variant_id")
        mock_rpc_client.insert_price = Mock(return_value="test_price_id")
        mock_rpc_client.upsert_coffee_image = Mock(return_value="test_image_id")
        
        # Replace the RPC client in database integration
        db_integration.rpc_client = mock_rpc_client
        
        # Mock validation result
        validation_result = Mock()
        validation_result.is_valid = True
        validation_result.artifact_data = self.test_artifact
        validation_result.artifact_id = "test_artifact_123"
        
        # Mock artifact mapper to return expected data structure with all required fields
        db_integration.artifact_mapper = Mock()
        db_integration.artifact_mapper.map_artifact_to_rpc_payloads = Mock(
            return_value={
                'coffee': {
                    'bean_species': 'Arabica',
                    'name': 'Test Coffee',
                    'slug': 'test-coffee',
                    'roaster_id': 'test_roaster',
                    'process': 'Washed',
                    'process_raw': 'Washed',
                    'roast_level': 'Medium',
                    'roast_level_raw': 'Medium',
                    'roast_style_raw': 'Medium',
                    'description_md': 'Test coffee description',
                    'direct_buy_url': 'https://example.com/buy',
                    'platform_product_id': 'test_product_123'
                },
                'variants': [{
                    'platform_variant_id': 'test_variant_123',
                    'name': 'Test Variant',
                    'price': 25.99,
                    'currency': 'USD'
                }],
                'prices': [{
                    'price': 25.99,
                    'currency': 'USD',
                    'variant_id': 'test_variant_123'
                }],
                'images': [],
                'metadata_only': True
            }
        )
        
        # Process artifact through price-only pipeline
        result = db_integration.upsert_artifact_via_rpc(
            validation_result=validation_result,
            roaster_id="test_roaster",
            metadata_only=True
        )
        
        # Verify that only price-related operations were performed
        assert result['success'] is True
        assert result['coffee_id'] == "test_coffee_id"
        assert len(result['variant_ids']) == 1
        assert len(result['price_ids']) == 1
        assert len(result['image_ids']) == 0  # No images processed
        
        # Verify that image operations were not attempted
        mock_rpc_client.upsert_coffee_image.assert_not_called()
    
    def test_end_to_end_full_pipeline(self):
        """Test end-to-end full pipeline with image processing."""
        # Create components with metadata_only=False
        mapper = ArtifactMapper(metadata_only=False)
        db_integration = DatabaseIntegration(supabase_client=self.mock_supabase_client)
        
        # Mock the RPC client entirely to avoid actual database calls
        mock_rpc_client = Mock()
        mock_rpc_client.upsert_coffee = Mock(return_value="test_coffee_id")
        mock_rpc_client.upsert_variant = Mock(return_value="test_variant_id")
        mock_rpc_client.insert_price = Mock(return_value="test_price_id")
        mock_rpc_client.upsert_coffee_image = Mock(return_value="test_image_id")
        
        # Replace the RPC client in database integration
        db_integration.rpc_client = mock_rpc_client
        
        # Mock validation result
        validation_result = Mock()
        validation_result.is_valid = True
        validation_result.artifact_data = self.test_artifact
        validation_result.artifact_id = "test_artifact_123"
        
        # Mock artifact mapper to return expected data structure with all required fields
        db_integration.artifact_mapper = Mock()
        db_integration.artifact_mapper.map_artifact_to_rpc_payloads = Mock(
            return_value={
                'coffee': {
                    'bean_species': 'Arabica',
                    'name': 'Test Coffee',
                    'slug': 'test-coffee',
                    'roaster_id': 'test_roaster',
                    'process': 'Washed',
                    'process_raw': 'Washed',
                    'roast_level': 'Medium',
                    'roast_level_raw': 'Medium',
                    'roast_style_raw': 'Medium',
                    'description_md': 'Test coffee description',
                    'direct_buy_url': 'https://example.com/buy',
                    'platform_product_id': 'test_product_123'
                },
                'variants': [{
                    'platform_variant_id': 'test_variant_123',
                    'name': 'Test Variant',
                    'price': 25.99,
                    'currency': 'USD'
                }],
                'prices': [{
                    'price': 25.99,
                    'currency': 'USD',
                    'variant_id': 'test_variant_123'
                }],
                'images': [{'url': 'https://example.com/image1.jpg'}],
                'metadata_only': False
            }
        )
        
        # Process artifact through full pipeline
        result = db_integration.upsert_artifact_via_rpc(
            validation_result=validation_result,
            roaster_id="test_roaster",
            metadata_only=False
        )
        
        # Verify that all operations were performed
        assert result['success'] is True
        assert result['coffee_id'] == "test_coffee_id"
        assert len(result['variant_ids']) == 1
        assert len(result['price_ids']) == 1
        assert len(result['image_ids']) > 0  # Images should be processed
        
        # Verify that image operations were attempted
        mock_rpc_client.upsert_coffee_image.assert_called()
    
    def test_mixed_pipeline_scenarios(self):
        """Test mixed scenarios with both price-only and full pipeline runs."""
        # Test that components can handle both scenarios
        rpc_client_price_only = RPCClient(
            supabase_client=self.mock_supabase_client,
            metadata_only=True
        )
        
        rpc_client_full = RPCClient(
            supabase_client=self.mock_supabase_client,
            metadata_only=False
        )
        
        # Price-only should block images
        with pytest.raises(Exception, match="Image processing blocked"):
            rpc_client_price_only.upsert_coffee_image(
                coffee_id="test_coffee_id",
                url="https://example.com/image1.jpg"
            )
        
        # Full pipeline should allow images
        rpc_client_full._execute_rpc_with_retry = Mock(return_value="test_image_id")
        result = rpc_client_full.upsert_coffee_image(
            coffee_id="test_coffee_id",
            url="https://example.com/image1.jpg"
        )
        
        assert result == "test_image_id"
    
    def test_guard_performance_impact(self):
        """Test that guards have minimal performance impact."""
        import time
        
        # Create guard with metadata_only=True
        guard = ImageProcessingGuard(metadata_only=True)
        
        # Measure time for multiple guard checks
        start_time = time.time()
        
        for i in range(1000):
            guard.check_image_processing_allowed(f"operation_{i}")
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should complete in less than 1 second for 1000 operations
        assert duration < 1.0
        
        # Verify guard statistics
        stats = guard.get_guard_stats()
        assert stats['blocks_attempted'] == 1000
        assert stats['operations_skipped'] == 0  # No guard_image_processing calls
    
    def test_guard_error_handling(self):
        """Test guard error handling and recovery."""
        # Create guard with metadata_only=True
        guard = ImageProcessingGuard(metadata_only=True)
        
        # Test that guard violations are handled gracefully
        result = guard.check_image_processing_allowed("test_operation")
        assert result is False
        
        # Test that guard statistics are maintained
        stats = guard.get_guard_stats()
        assert stats['blocks_attempted'] == 1
        
        # Test that guard can be reset
        guard.reset_stats()
        stats = guard.get_guard_stats()
        assert stats['blocks_attempted'] == 0
