"""
Integration tests for RPC functionality with staging database.
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timezone

from src.validator.integration_service import ValidatorIntegrationService
from src.config.validator_config import ValidatorConfig
from src.config.imagekit_config import ImageKitConfig
from src.validator.artifact_validator import ValidationResult
from src.validator.models import (
    ArtifactModel, ProductModel, VariantModel,
    SourceEnum, PlatformEnum, WeightUnitEnum, RoastLevelEnum, 
    ProcessEnum, SpeciesEnum
)


class TestRPCIntegration:
    """Integration tests for RPC functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_supabase = Mock()
        
        # Create proper config with real ImageKitConfig
        self.config = ValidatorConfig(
            storage_path="/tmp/test_storage",
            enable_imagekit_upload=True,
            imagekit_config=ImageKitConfig(
                public_key="public_test_key",
                private_key="private_test_key", 
                url_endpoint="https://test.imagekit.io"
            )
        )
        
        self.integration_service = ValidatorIntegrationService(
            config=self.config,
            supabase_client=self.mock_supabase
        )
        
        # Mock the RPC client methods
        self.integration_service.rpc_client.upsert_coffee = Mock()
        self.integration_service.rpc_client.upsert_variant = Mock()
        self.integration_service.rpc_client.insert_price = Mock()
        self.integration_service.rpc_client.upsert_coffee_image = Mock()
        
        # Mock the artifact mapper
        self.integration_service.artifact_mapper.map_artifact_to_rpc_payloads = Mock()
        
        # Mock the database integration methods
        self.integration_service.database_integration.store_batch_validation_results = Mock()
    
    def create_test_validation_result(self) -> ValidationResult:
        """Create a test validation result."""
        # Create test variant
        variant = VariantModel(
            platform_variant_id="var-123",
            sku="SKU123",
            title="250g Whole Bean",
            price="24.99",
            price_decimal=24.99,
            currency="USD",
            compare_at_price="29.99",
            compare_at_price_decimal=29.99,
            in_stock=True,
            grams=250,
            weight_unit=WeightUnitEnum.GRAMS
        )
        
        # Create test product
        product = ProductModel(
            platform_product_id="prod-123",
            platform=PlatformEnum.SHOPIFY,
            title="Test Coffee",
            handle="test-coffee",
            slug="test-coffee",
            description_md="# Test Coffee\nA test coffee.",
            source_url="https://test.com/coffee",
            variants=[variant]
        )
        
        # Create test artifact
        artifact = ArtifactModel(
            source=SourceEnum.SHOPIFY,
            roaster_domain="test.com",
            scraped_at=datetime.now(timezone.utc),
            product=product
        )
        
        # Create validation result
        validation_result = ValidationResult(
            artifact_id="artifact-123",
            artifact_data=artifact,
            is_valid=True,
            errors=[]
        )
        
        return validation_result
    
    @patch('src.validator.integration_service.ValidationPipeline')
    def test_process_artifacts_with_rpc_upsert_success(self, mock_pipeline_class):
        """Test successful artifact processing with RPC upsert."""
        # Mock validation pipeline
        mock_pipeline = Mock()
        mock_pipeline_class.return_value = mock_pipeline
        
        # Create test validation results
        validation_result = self.create_test_validation_result()
        mock_pipeline.process_storage_artifacts.return_value = [validation_result]
        
        # Replace the actual validation pipeline with our mock
        self.integration_service.validation_pipeline = mock_pipeline
        
        # Mock artifact mapper to return RPC payloads
        self.integration_service.artifact_mapper.map_artifact_to_rpc_payloads.return_value = {
            'coffee': {'title': 'Test Coffee', 'roaster_id': 'roaster-123'},
            'variants': [{'title': '250g Whole Bean', 'sku': 'SKU123'}],
            'prices': [{'price': 24.99, 'currency': 'USD'}],
            'images': []
        }
        
        # Mock RPC client responses
        self.integration_service.rpc_client.upsert_coffee.return_value = "coffee-123"
        self.integration_service.rpc_client.upsert_variant.return_value = "variant-123"
        self.integration_service.rpc_client.insert_price.return_value = "price-123"
        
        # Mock database integration
        self.integration_service.database_integration.store_batch_validation_results.return_value = ["artifact-123"]
        
        # Test processing
        result = self.integration_service.process_artifacts_with_rpc_upsert(
            roaster_id="roaster-123",
            platform="shopify",
            scrape_run_id="run-123",
            response_filenames=["test.json"],
            metadata_only=False
        )
        
        # Verify results
        assert result['roaster_id'] == "roaster-123"
        assert result['platform'] == "shopify"
        assert result['scrape_run_id'] == "run-123"
        assert result['total_artifacts'] == 1
        assert result['valid_artifacts'] == 1
        assert result['invalid_artifacts'] == 0
        assert result['success'] is True
        
        # Verify RPC transformation results
        rpc_results = result['rpc_transformation']
        assert rpc_results['successful_transformations'] == 1
        assert rpc_results['successful_upserts'] == 3  # coffee + variant + price
        assert rpc_results['failed_transformations'] == 0
        assert rpc_results['failed_upserts'] == 0
        
        # Verify RPC calls were made
        self.integration_service.rpc_client.upsert_coffee.assert_called_once()
        self.integration_service.rpc_client.upsert_variant.assert_called_once()
        self.integration_service.rpc_client.insert_price.assert_called_once()
    
    @patch('src.validator.integration_service.ValidationPipeline')
    def test_process_artifacts_with_rpc_upsert_metadata_only(self, mock_pipeline_class):
        """Test artifact processing with metadata-only flag."""
        # Mock validation pipeline
        mock_pipeline = Mock()
        mock_pipeline_class.return_value = mock_pipeline
        
        # Create test validation results
        validation_result = self.create_test_validation_result()
        mock_pipeline.process_storage_artifacts.return_value = [validation_result]
        
        # Replace the actual validation pipeline with our mock
        self.integration_service.validation_pipeline = mock_pipeline
        
        # Mock artifact mapper to return RPC payloads
        self.integration_service.artifact_mapper.map_artifact_to_rpc_payloads.return_value = {
            'coffee': {'title': 'Test Coffee', 'roaster_id': 'roaster-123'},
            'variants': [{'title': '250g Whole Bean', 'sku': 'SKU123'}],
            'prices': [{'price': 24.99, 'currency': 'USD'}],
            'images': []
        }
        
        # Mock RPC client responses
        self.integration_service.rpc_client.upsert_coffee.return_value = "coffee-123"
        self.integration_service.rpc_client.upsert_variant.return_value = "variant-123"
        self.integration_service.rpc_client.insert_price.return_value = "price-123"
        
        # Mock database integration
        self.integration_service.database_integration.store_batch_validation_results.return_value = ["artifact-123"]
        
        # Test processing with metadata-only flag
        result = self.integration_service.process_artifacts_with_rpc_upsert(
            roaster_id="roaster-123",
            platform="shopify",
            scrape_run_id="run-123",
            response_filenames=["test.json"],
            metadata_only=True
        )
        
        # Verify results
        assert result['success'] is True
        
        # Verify RPC transformation results
        rpc_results = result['rpc_transformation']
        assert rpc_results['metadata_only'] is True
        assert rpc_results['successful_upserts'] == 3  # coffee + variant + price (no images)
        
        # Verify images were not processed
        assert len(rpc_results['image_ids']) == 0
    
    @patch('src.validator.integration_service.ValidationPipeline')
    def test_process_artifacts_with_rpc_upsert_no_valid_artifacts(self, mock_pipeline_class):
        """Test artifact processing with no valid artifacts."""
        # Mock validation pipeline
        mock_pipeline = Mock()
        mock_pipeline_class.return_value = mock_pipeline
        
        # Create invalid validation result
        validation_result = ValidationResult(
            artifact_id="artifact-123",
            artifact_data=None,
            is_valid=False,
            errors=["Validation failed"],
        )
        
        mock_pipeline.process_storage_artifacts.return_value = [validation_result]
        
        # Mock database integration
        self.integration_service.database_integration.store_batch_validation_results.return_value = ["artifact-123"]
        
        # Test processing
        result = self.integration_service.process_artifacts_with_rpc_upsert(
            roaster_id="roaster-123",
            platform="shopify",
            scrape_run_id="run-123",
            response_filenames=["test.json"],
            metadata_only=False
        )
        
        # Verify results
        assert result['roaster_id'] == "roaster-123"
        assert result['total_artifacts'] == 1
        assert result['valid_artifacts'] == 0
        assert result['invalid_artifacts'] == 1
        assert result['success'] is False
        assert result['error'] == 'No valid artifacts found'
        
        # Verify no RPC calls were made
        self.integration_service.rpc_client.upsert_coffee.assert_not_called()
        self.integration_service.rpc_client.upsert_variant.assert_not_called()
        self.integration_service.rpc_client.insert_price.assert_not_called()
    
    @patch('src.validator.integration_service.ValidationPipeline')
    def test_process_artifacts_with_rpc_upsert_transformation_error(self, mock_pipeline_class):
        """Test artifact processing with transformation error."""
        # Mock validation pipeline
        mock_pipeline = Mock()
        mock_pipeline_class.return_value = mock_pipeline
        
        # Create test validation results
        validation_result = self.create_test_validation_result()
        mock_pipeline.process_storage_artifacts.return_value = [validation_result]
        
        # Replace the actual validation pipeline with our mock
        self.integration_service.validation_pipeline = mock_pipeline
        
        # Mock artifact mapper to return RPC payloads
        self.integration_service.artifact_mapper.map_artifact_to_rpc_payloads.return_value = {
            'coffee': {'title': 'Test Coffee', 'roaster_id': 'roaster-123'},
            'variants': [{'title': '250g Whole Bean', 'sku': 'SKU123'}],
            'prices': [{'price': 24.99, 'currency': 'USD'}],
            'images': []
        }
        
        # Mock RPC client to raise error
        self.integration_service.rpc_client.upsert_coffee.side_effect = Exception("RPC error")
        
        # Mock database integration
        self.integration_service.database_integration.store_batch_validation_results.return_value = ["artifact-123"]
        
        # Test processing
        result = self.integration_service.process_artifacts_with_rpc_upsert(
            roaster_id="roaster-123",
            platform="shopify",
            scrape_run_id="run-123",
            response_filenames=["test.json"],
            metadata_only=False
        )
        
        # Verify results
        assert result['success'] is True  # Overall processing succeeded
        
        # Verify RPC transformation results show errors
        rpc_results = result['rpc_transformation']
        assert rpc_results['successful_transformations'] == 1  # Transformation succeeded
        assert rpc_results['failed_transformations'] == 1  # But upsert failed, so counted as failed transformation
        assert rpc_results['successful_upserts'] == 0  # But upsert failed
        assert rpc_results['failed_upserts'] == 1
        assert len(rpc_results['errors']) == 1
        assert rpc_results['errors'][0]['error'] == "RPC error"
    
    def test_transform_and_upsert_artifacts_success(self):
        """Test successful artifact transformation and upsert."""
        # Create test validation results
        validation_result = self.create_test_validation_result()
        
        # Mock artifact mapper to return RPC payloads
        self.integration_service.artifact_mapper.map_artifact_to_rpc_payloads.return_value = {
            'coffee': {'title': 'Test Coffee', 'roaster_id': 'roaster-123'},
            'variants': [{'title': '250g Whole Bean', 'sku': 'SKU123'}],
            'prices': [{'price': 24.99, 'currency': 'USD'}],
            'images': []
        }
        
        # Mock RPC client responses
        self.integration_service.rpc_client.upsert_coffee.return_value = "coffee-123"
        self.integration_service.rpc_client.upsert_variant.return_value = "variant-123"
        self.integration_service.rpc_client.insert_price.return_value = "price-123"
        
        # Test transformation
        result = self.integration_service.transform_and_upsert_artifacts(
            validation_results=[validation_result],
            roaster_id="roaster-123",
            metadata_only=False
        )
        
        # Verify results
        assert result['roaster_id'] == "roaster-123"
        assert result['metadata_only'] is False
        assert result['total_artifacts'] == 1
        assert result['successful_transformations'] == 1
        assert result['failed_transformations'] == 0
        assert result['successful_upserts'] == 3  # coffee + variant + price
        assert result['failed_upserts'] == 0
        assert len(result['coffee_ids']) == 1
        assert len(result['variant_ids']) == 1
        assert len(result['price_ids']) == 1
        assert len(result['errors']) == 0
        
        # Verify RPC calls were made
        self.integration_service.rpc_client.upsert_coffee.assert_called_once()
        self.integration_service.rpc_client.upsert_variant.assert_called_once()
        self.integration_service.rpc_client.insert_price.assert_called_once()
    
    def test_transform_and_upsert_artifacts_with_invalid_artifacts(self):
        """Test transformation with invalid artifacts."""
        # Create invalid validation result
        validation_result = ValidationResult(
            artifact_id="artifact-123",
            artifact_data=None,
            is_valid=False,
            errors=["Validation failed"],
        )
        
        # Test transformation
        result = self.integration_service.transform_and_upsert_artifacts(
            validation_results=[validation_result],
            roaster_id="roaster-123",
            metadata_only=False
        )
        
        # Verify results
        assert result['total_artifacts'] == 1
        assert result['successful_transformations'] == 0
        assert result['failed_transformations'] == 1
        assert result['successful_upserts'] == 0
        assert result['failed_upserts'] == 0
        
        # Verify no RPC calls were made
        self.integration_service.rpc_client.upsert_coffee.assert_not_called()
        self.integration_service.rpc_client.upsert_variant.assert_not_called()
        self.integration_service.rpc_client.insert_price.assert_not_called()
    
    def test_transform_and_upsert_artifacts_with_transformation_error(self):
        """Test transformation with transformation error."""
        # Create test validation result
        validation_result = self.create_test_validation_result()
        
        # Mock artifact mapper to raise error
        self.integration_service.artifact_mapper.map_artifact_to_rpc_payloads.side_effect = Exception("Mapping error")
        
        # Test transformation
        result = self.integration_service.transform_and_upsert_artifacts(
            validation_results=[validation_result],
            roaster_id="roaster-123",
            metadata_only=False
        )
        
        # Verify results
        assert result['total_artifacts'] == 1
        assert result['successful_transformations'] == 0
        assert result['failed_transformations'] == 1
        assert result['successful_upserts'] == 0
        assert result['failed_upserts'] == 1
        assert len(result['errors']) == 1
        assert result['errors'][0]['error'] == "Mapping error"
    
    def test_get_service_stats_with_rpc_components(self):
        """Test service statistics include RPC components."""
        # Set some stats
        self.integration_service.rpc_client.rpc_stats['total_calls'] = 10
        self.integration_service.rpc_client.rpc_stats['successful_calls'] = 8
        self.integration_service.artifact_mapper.mapping_stats['total_mapped'] = 5
        self.integration_service.artifact_mapper.mapping_stats['coffee_mapped'] = 5
        
        stats = self.integration_service.get_service_stats()
        
        # Verify RPC stats are included
        assert 'rpc_stats' in stats
        assert stats['rpc_stats']['total_calls'] == 10
        assert stats['rpc_stats']['successful_calls'] == 8
        
        # Verify mapper stats are included
        assert 'mapper_stats' in stats
        assert stats['mapper_stats']['total_mapped'] == 5
        assert stats['mapper_stats']['coffee_mapped'] == 5
    
    def test_reset_service_stats_with_rpc_components(self):
        """Test service statistics reset includes RPC components."""
        # Set some stats
        self.integration_service.rpc_client.rpc_stats['total_calls'] = 10
        self.integration_service.artifact_mapper.mapping_stats['total_mapped'] = 5
        
        # Reset stats
        self.integration_service.reset_service_stats()
        
        # Verify RPC stats are reset
        assert self.integration_service.rpc_client.rpc_stats['total_calls'] == 0
        assert self.integration_service.rpc_client.rpc_stats['successful_calls'] == 0
        
        # Verify mapper stats are reset
        assert self.integration_service.artifact_mapper.mapping_stats['total_mapped'] == 0
        assert self.integration_service.artifact_mapper.mapping_stats['coffee_mapped'] == 0
