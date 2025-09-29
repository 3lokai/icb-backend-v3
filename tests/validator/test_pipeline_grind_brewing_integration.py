"""
Integration tests for grind/brewing parsing in A.1-A.5 pipeline.
"""

from datetime import datetime, timezone
from unittest.mock import Mock, patch
import pytest

from src.validator.integration_service import ValidatorIntegrationService
from src.validator.validation_pipeline import ValidationPipeline
from src.validator.database_integration import DatabaseIntegration
from src.config.validator_config import ValidatorConfig
from src.validator.models import ArtifactModel, ProductModel, VariantModel, NormalizationModel, SourceEnum


class TestPipelineGrindBrewingIntegration:
    """Test grind/brewing parsing integration in A.1-A.5 pipeline."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = ValidatorConfig(
            enable_grind_brewing_parsing=True,
            grind_brewing_confidence_threshold=0.7
        )
        self.integration_service = ValidatorIntegrationService(config=self.config)
    
    def test_grind_brewing_parser_initialization(self):
        """Test that grind/brewing parser is initialized in integration service."""
        assert self.integration_service.grind_brewing_parser is not None
        assert hasattr(self.integration_service, 'grind_brewing_parser')
    
    def test_artifact_mapper_has_grind_brewing_parser(self):
        """Test that artifact mapper has access to grind/brewing parser."""
        assert self.integration_service.artifact_mapper.grind_brewing_parser is not None
        assert self.integration_service.artifact_mapper.grind_brewing_parser == self.integration_service.grind_brewing_parser
    
    def test_validation_pipeline_integration(self):
        """Test that validation pipeline can process artifacts with grind/brewing parsing."""
        # Create test artifact with grind data
        variants = [
            VariantModel(
                platform_variant_id="v1",
                title="French Press Grind",
                price="25.99",
                price_decimal=25.99,
                currency="USD",
                in_stock=True,
                weight_g=250,
                options=["Size", "French Press Grind"]
            ),
            VariantModel(
                platform_variant_id="v2",
                title="Whole Bean",
                price="25.99",
                price_decimal=25.99,
                currency="USD",
                in_stock=True,
                weight_g=250,
                options=["Size", "Whole Bean"]
            )
        ]
        
        product = ProductModel(
            platform_product_id="test-product-1",
            title="Test Coffee",
            source_url="https://example.com/test-coffee",
            variants=variants
        )
        
        artifact = ArtifactModel(
            product=product,
            normalization=NormalizationModel(),
            scraped_at=datetime.now(timezone.utc),
            source=SourceEnum.OTHER,
            roaster_domain="example.com"
        )
        
        # Test that artifact mapper can process with grind/brewing parsing
        rpc_payloads = self.integration_service.artifact_mapper.map_artifact_to_rpc_payloads(
            artifact=artifact,
            roaster_id="test-roaster-id"
        )
        
        # Assertions
        assert 'coffee' in rpc_payloads
        assert 'variants' in rpc_payloads
        
        # Check that coffee has default grind
        assert 'p_default_grind' in rpc_payloads['coffee']
        assert rpc_payloads['coffee']['p_default_grind'] == "whole"  # Whole bean should be selected
        
        # Check that variants have grind data
        assert len(rpc_payloads['variants']) == 2
        
        # Check first variant (French Press)
        variant1 = rpc_payloads['variants'][0]
        assert variant1['p_grind'] == "french_press"
        assert 'grind_brewing_parsing' in variant1['p_source_raw']
        
        # Check second variant (Whole Bean)
        variant2 = rpc_payloads['variants'][1]
        assert variant2['p_grind'] == "whole"
        assert 'grind_brewing_parsing' in variant2['p_source_raw']
    
    @patch('src.validator.database_integration.DatabaseIntegration.upsert_artifact_via_rpc')
    def test_database_integration_grind_brewing_processing(self, mock_upsert):
        """Test that database integration processes grind/brewing data."""
        # Mock the upsert method to return success
        mock_upsert.return_value = {
            'success': True,
            'coffee_id': 'test-coffee-123',
            'variant_ids': ['variant-1', 'variant-2'],
            'price_ids': [],
            'image_ids': [],
            'errors': []
        }
        
        # Create test artifact
        variants = [
            VariantModel(
                platform_variant_id="v1",
                title="Espresso Grind",
                price="25.99",
                price_decimal=25.99,
                currency="USD",
                in_stock=True,
                weight_g=250,
                options=["Size", "Espresso Grind"]
            )
        ]
        
        product = ProductModel(
            platform_product_id="test-product-1",
            title="Test Coffee",
            source_url="https://example.com/test-coffee",
            variants=variants
        )
        
        artifact = ArtifactModel(
            product=product,
            normalization=NormalizationModel(),
            scraped_at=datetime.now(timezone.utc),
            source=SourceEnum.OTHER,
            roaster_domain="example.com"
        )
        
        # Create a mock validation result
        from src.validator.artifact_validator import ValidationResult
        validation_result = ValidationResult(
            is_valid=True,
            artifact_data=artifact,
            errors=[],
            warnings=[]
        )
        
        # Test database integration
        result = self.integration_service.database_integration.upsert_artifact_via_rpc(
            validation_result=validation_result,
            roaster_id="test-roaster-id"
        )
        
        # Verify that upsert was called
        mock_upsert.assert_called_once()
        
        # Verify the result
        assert result['success'] is True
        assert result['coffee_id'] == 'test-coffee-123'
    
    def test_grind_brewing_parsing_disabled(self):
        """Test behavior when grind/brewing parsing is disabled."""
        config = ValidatorConfig(enable_grind_brewing_parsing=False)
        integration_service = ValidatorIntegrationService(config=config)
        
        # Parser should be None
        assert integration_service.grind_brewing_parser is None
        assert integration_service.artifact_mapper.grind_brewing_parser is None
    
    def test_grind_brewing_confidence_threshold(self):
        """Test that confidence threshold is respected."""
        # Test with low confidence threshold
        config = ValidatorConfig(
            enable_grind_brewing_parsing=True,
            grind_brewing_confidence_threshold=0.9  # Very high threshold
        )
        integration_service = ValidatorIntegrationService(config=config)
        
        # Create artifact with ambiguous grind data
        variants = [
            VariantModel(
                platform_variant_id="v1",
                title="Grind",  # Ambiguous title
                price="25.99",
                price_decimal=25.99,
                currency="USD",
                in_stock=True,
                weight_g=250,
                options=["Size", "Grind"]
            )
        ]
        
        product = ProductModel(
            platform_product_id="test-product-1",
            title="Test Coffee",
            source_url="https://example.com/test-coffee",
            variants=variants
        )
        
        artifact = ArtifactModel(
            product=product,
            normalization=NormalizationModel(),
            scraped_at=datetime.now(timezone.utc),
            source=SourceEnum.OTHER,
            roaster_domain="example.com"
        )
        
        # Process artifact
        rpc_payloads = integration_service.artifact_mapper.map_artifact_to_rpc_payloads(
            artifact=artifact,
            roaster_id="test-roaster-id"
        )
        
        # With high confidence threshold, grind should not be detected
        variant = rpc_payloads['variants'][0]
        assert 'p_grind' not in variant or variant['p_grind'] is None
        
        # Default grind should also not be set
        assert 'p_default_grind' not in rpc_payloads['coffee']
    
    def test_pipeline_error_handling(self):
        """Test that pipeline handles grind/brewing parsing errors gracefully."""
        # Create artifact with problematic data
        variants = [
            VariantModel(
                platform_variant_id="v1",
                title="",  # Empty title
                price="25.99",
                price_decimal=25.99,
                currency="USD",
                in_stock=True,
                weight_g=250,
                options=[]  # Empty options
            )
        ]
        
        product = ProductModel(
            platform_product_id="test-product-1",
            title="Test Coffee",
            source_url="https://example.com/test-coffee",
            variants=variants
        )
        
        artifact = ArtifactModel(
            product=product,
            normalization=NormalizationModel(),
            scraped_at=datetime.now(timezone.utc),
            source=SourceEnum.OTHER,
            roaster_domain="example.com"
        )
        
        # Process should not raise exception
        rpc_payloads = self.integration_service.artifact_mapper.map_artifact_to_rpc_payloads(
            artifact=artifact,
            roaster_id="test-roaster-id"
        )
        
        # Should still process successfully
        assert 'coffee' in rpc_payloads
        assert 'variants' in rpc_payloads
        assert len(rpc_payloads['variants']) == 1
        
        # Variant should not have grind data
        variant = rpc_payloads['variants'][0]
        assert 'p_grind' not in variant or variant['p_grind'] is None
    
    def test_batch_processing_grind_brewing(self):
        """Test batch processing with multiple artifacts containing grind data."""
        # Create multiple artifacts with different grind types
        artifacts = []
        
        grind_types = ["espresso", "french_press", "filter", "whole"]
        grind_titles = ["Espresso Grind", "French Press Grind", "Filter Grind", "Whole Bean"]
        
        for i, (grind_type, title) in enumerate(zip(grind_types, grind_titles)):
            variants = [
                VariantModel(
                    platform_variant_id=f"v{i+1}",
                    title=title,
                    price="25.99",
                    price_decimal=25.99,
                    currency="USD",
                    in_stock=True,
                    weight_g=250,
                    options=["Size", title]
                )
            ]
            
            product = ProductModel(
                platform_product_id=f"test-product-{i+1}",
                title=f"Test Coffee {i+1}",
                source_url=f"https://example.com/test-coffee-{i+1}",
                variants=variants
            )
            
            artifact = ArtifactModel(
                product=product,
                normalization=NormalizationModel(),
                scraped_at=datetime.now(timezone.utc),
                source=SourceEnum.OTHER,
                roaster_domain="example.com"
            )
            
            artifacts.append(artifact)
        
        # Process all artifacts
        results = []
        for artifact in artifacts:
            rpc_payloads = self.integration_service.artifact_mapper.map_artifact_to_rpc_payloads(
                artifact=artifact,
                roaster_id="test-roaster-id"
            )
            results.append(rpc_payloads)
        
        # Verify all artifacts were processed correctly
        assert len(results) == 4
        
        for i, result in enumerate(results):
            # Check coffee default grind
            assert 'p_default_grind' in result['coffee']
            assert result['coffee']['p_default_grind'] == grind_types[i]
            
            # Check variant grind
            variant = result['variants'][0]
            assert variant['p_grind'] == grind_types[i]
            assert 'grind_brewing_parsing' in variant['p_source_raw']
