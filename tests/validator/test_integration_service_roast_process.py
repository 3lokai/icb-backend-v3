"""
Tests for ValidatorIntegrationService roast and process parsing integration.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, patch

from src.validator.integration_service import ValidatorIntegrationService
from src.validator.models import (
    ArtifactModel, ProductModel, VariantModel, NormalizationModel, 
    SourceEnum, PlatformEnum, RoastLevelEnum, ProcessEnum, SpeciesEnum
)
from src.validator.artifact_validator import ValidationResult


class TestValidatorIntegrationServiceRoastProcess:
    """Test cases for ValidatorIntegrationService roast and process parsing integration."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.service = ValidatorIntegrationService()
    
    def create_test_validation_result(self) -> ValidationResult:
        """Create a test validation result with roast and process data."""
        # Create test variant
        variant = VariantModel(
            platform_variant_id="var-123",
            sku="SKU123",
            title="250g Whole Bean",
            price="24.99",
            price_decimal=24.99,
            currency="USD",
            in_stock=True
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
        
        # Create test normalization with roast and process data
        normalization = NormalizationModel(
            is_coffee=True,
            roast_level_raw="Medium Roast",
            roast_level_enum=RoastLevelEnum.MEDIUM,
            process_raw="Washed Process",
            process_enum=ProcessEnum.WASHED,
            bean_species=SpeciesEnum.ARABICA
        )
        
        # Create test artifact
        artifact = ArtifactModel(
            source=SourceEnum.SHOPIFY,
            roaster_domain="test.com",
            scraped_at=datetime.now(timezone.utc),
            product=product,
            normalization=normalization
        )
        
        # Create validation result
        validation_result = ValidationResult(
            artifact_data=artifact.model_dump(),
            is_valid=True,
            errors=[],
            warnings=[]
        )
        
        return validation_result
    
    def test_artifact_mapper_initialization(self):
        """Test that ArtifactMapper is properly initialized with roast and process parsers."""
        # Check that parsers are initialized
        assert self.service.artifact_mapper.roast_parser is not None
        assert self.service.artifact_mapper.process_parser is not None
        
        # Check that they are the correct types
        from src.parser.roast_parser import RoastLevelParser
        from src.parser.process_parser import ProcessMethodParser
        
        assert isinstance(self.service.artifact_mapper.roast_parser, RoastLevelParser)
        assert isinstance(self.service.artifact_mapper.process_parser, ProcessMethodParser)
    
    @patch('src.validator.integration_service.RPCClient')
    def test_transform_and_upsert_artifacts_with_roast_process(self, mock_rpc_client):
        """Test that transform_and_upsert_artifacts includes roast and process parsing."""
        # Mock RPC client
        mock_rpc = Mock()
        mock_rpc.upsert_coffee.return_value = "coffee-123"
        mock_rpc.upsert_variant.return_value = "variant-123"
        mock_rpc.insert_price.return_value = "price-123"
        mock_rpc.upsert_coffee_image.return_value = "image-123"
        mock_rpc_client.return_value = mock_rpc
        
        # Create service with mocked RPC client
        service = ValidatorIntegrationService()
        service.rpc_client = mock_rpc
        
        # Create test validation result
        validation_result = self.create_test_validation_result()
        
        # Convert artifact_data back to ArtifactModel for the test
        artifact = ArtifactModel(**validation_result.artifact_data)
        validation_result.artifact_data = artifact
        
        # Test transformation
        results = service.transform_and_upsert_artifacts(
            validation_results=[validation_result],
            roaster_id="roaster-123",
            metadata_only=False
        )
        
        # Verify results
        assert results['successful_transformations'] == 1
        assert results['successful_upserts'] > 0
        assert len(results['coffee_ids']) == 1
        assert len(results['variant_ids']) == 1
        
        # Verify RPC calls were made
        mock_rpc.upsert_coffee.assert_called_once()
        mock_rpc.upsert_variant.assert_called_once()
        mock_rpc.insert_price.assert_called_once()
        # Note: upsert_coffee_image is not called because there are no images in test data
        
        # Verify coffee upsert includes roast and process data
        coffee_call_args = mock_rpc.upsert_coffee.call_args[1]
        assert 'p_roast_level' in coffee_call_args
        assert 'p_process' in coffee_call_args
        assert 'p_roast_level_raw' in coffee_call_args
        assert 'p_process_raw' in coffee_call_args
        
        # Verify roast and process are parsed correctly
        assert coffee_call_args['p_roast_level'] == 'medium'
        assert coffee_call_args['p_process'] == 'washed'
        assert coffee_call_args['p_roast_level_raw'] == "Medium Roast"
        assert coffee_call_args['p_process_raw'] == "Washed Process"
    
    def test_artifact_mapper_roast_parsing_integration(self):
        """Test that ArtifactMapper correctly parses roast levels."""
        validation_result = self.create_test_validation_result()
        
        # Convert artifact_data back to ArtifactModel for testing
        artifact = ArtifactModel(**validation_result.artifact_data)
        
        # Test mapping
        rpc_payloads = self.service.artifact_mapper.map_artifact_to_rpc_payloads(
            artifact=artifact,
            roaster_id="roaster-123",
            metadata_only=False
        )
        
        # Verify coffee payload includes parsed roast data
        coffee_payload = rpc_payloads['coffee']
        assert 'p_roast_level' in coffee_payload
        assert 'p_roast_level_raw' in coffee_payload
        assert coffee_payload['p_roast_level'] == 'medium'
        assert coffee_payload['p_roast_level_raw'] == "Medium Roast"
    
    def test_artifact_mapper_process_parsing_integration(self):
        """Test that ArtifactMapper correctly parses process methods."""
        validation_result = self.create_test_validation_result()
        
        # Convert artifact_data back to ArtifactModel for testing
        artifact = ArtifactModel(**validation_result.artifact_data)
        
        # Test mapping
        rpc_payloads = self.service.artifact_mapper.map_artifact_to_rpc_payloads(
            artifact=artifact,
            roaster_id="roaster-123",
            metadata_only=False
        )
        
        # Verify coffee payload includes parsed process data
        coffee_payload = rpc_payloads['coffee']
        assert 'p_process' in coffee_payload
        assert 'p_process_raw' in coffee_payload
        assert coffee_payload['p_process'] == 'washed'
        assert coffee_payload['p_process_raw'] == "Washed Process"
    
    def test_roast_parser_fallback_handling(self):
        """Test roast parser fallback when parser fails."""
        # Create validation result with problematic roast data
        validation_result = self.create_test_validation_result()
        validation_result.artifact_data['normalization']['roast_level_raw'] = "Invalid Roast Format"
        validation_result.artifact_data['normalization']['roast_level_enum'] = None  # Clear the enum to test fallback
        
        # Convert artifact_data back to ArtifactModel for testing
        artifact = ArtifactModel(**validation_result.artifact_data)
        
        # Mock parser to fail
        mock_parser = Mock()
        mock_parser.parse_roast_level.side_effect = Exception("Parser error")
        self.service.artifact_mapper.roast_parser = mock_parser
        
        # Test mapping
        rpc_payloads = self.service.artifact_mapper.map_artifact_to_rpc_payloads(
            artifact=artifact,
            roaster_id="roaster-123",
            metadata_only=False
        )
        
        # Should fallback to None when parsing fails
        coffee_payload = rpc_payloads['coffee']
        assert coffee_payload['p_roast_level'] is None  # Fallback to None
    
    def test_process_parser_fallback_handling(self):
        """Test process parser fallback when parser fails."""
        # Create validation result with problematic process data
        validation_result = self.create_test_validation_result()
        validation_result.artifact_data['normalization']['process_raw'] = "Invalid Process Format"
        validation_result.artifact_data['normalization']['process_enum'] = None  # Clear the enum to test fallback
        
        # Convert artifact_data back to ArtifactModel for testing
        artifact = ArtifactModel(**validation_result.artifact_data)
        
        # Mock parser to fail
        mock_parser = Mock()
        mock_parser.parse_process_method.side_effect = Exception("Parser error")
        self.service.artifact_mapper.process_parser = mock_parser
        
        # Test mapping
        rpc_payloads = self.service.artifact_mapper.map_artifact_to_rpc_payloads(
            artifact=artifact,
            roaster_id="roaster-123",
            metadata_only=False
        )
        
        # Should fallback to None when parsing fails
        coffee_payload = rpc_payloads['coffee']
        assert coffee_payload['p_process'] is None  # Fallback to None
    
    def test_missing_roast_process_data_handling(self):
        """Test handling of missing roast and process data."""
        # Create validation result without roast/process data
        validation_result = self.create_test_validation_result()
        validation_result.artifact_data['normalization']['roast_level_raw'] = None
        validation_result.artifact_data['normalization']['process_raw'] = None
        validation_result.artifact_data['normalization']['roast_level_enum'] = None
        validation_result.artifact_data['normalization']['process_enum'] = None
        
        # Convert artifact_data back to ArtifactModel for testing
        artifact = ArtifactModel(**validation_result.artifact_data)
        
        # Test mapping
        rpc_payloads = self.service.artifact_mapper.map_artifact_to_rpc_payloads(
            artifact=artifact,
            roaster_id="roaster-123",
            metadata_only=False
        )
        
        # Should handle missing data gracefully by returning None
        coffee_payload = rpc_payloads['coffee']
        assert coffee_payload['p_roast_level'] is None
        assert coffee_payload['p_process'] is None
        assert coffee_payload['p_roast_level_raw'] is None
        assert coffee_payload['p_process_raw'] is None
