"""
Tests for weight parsing integration in ValidatorIntegrationService.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, patch
from pathlib import Path

from src.validator.integration_service import ValidatorIntegrationService
from src.config.validator_config import ValidatorConfig
from src.config.imagekit_config import ImageKitConfig
from src.validator.models import (
    ArtifactModel, ProductModel, VariantModel, ImageModel, 
    NormalizationModel, AuditModel, SourceEnum, PlatformEnum,
    WeightUnitEnum, RoastLevelEnum, ProcessEnum, SpeciesEnum
)


class TestValidatorIntegrationServiceWeightParsing:
    """Test cases for weight parsing integration in ValidatorIntegrationService."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Mock the dependencies
        self.mock_supabase_client = Mock()
        
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
        
        # Create service with mocked dependencies
        with patch('src.validator.integration_service.StorageReader'), \
             patch('src.validator.integration_service.ArtifactValidator'), \
             patch('src.validator.integration_service.ValidationPipeline'), \
             patch('src.validator.integration_service.DatabaseIntegration'), \
             patch('src.validator.integration_service.RPCClient'), \
             patch('src.validator.integration_service.RawArtifactPersistence'):
            
            self.service = ValidatorIntegrationService(
                config=self.config,
                supabase_client=self.mock_supabase_client
            )
    
    def create_test_artifact_with_weight_in_title(self) -> ArtifactModel:
        """Create a test artifact with weight information in variant titles."""
        # Create test variant with weight in title
        variant = VariantModel(
            platform_variant_id="var-123",
            sku="SKU123",
            title="250g Whole Bean Coffee",  # Weight in title
            price="24.99",
            price_decimal=24.99,
            currency="USD",
            compare_at_price="29.99",
            compare_at_price_decimal=29.99,
            in_stock=True,
            grams=None,  # No explicit grams - should be parsed from title
            weight_unit=None
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
        
        # Create test normalization
        normalization = NormalizationModel(
            bean_species=SpeciesEnum.ARABICA,
            process=ProcessEnum.WASHED,
            roast_level=RoastLevelEnum.LIGHT,
            roast_style="Light Roast"
        )
        
        # Create test audit
        audit = AuditModel(
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            source=SourceEnum.SHOPIFY,
            notes="Test artifact"
        )
        
        # Create test artifact
        artifact = ArtifactModel(
            source=SourceEnum.SHOPIFY,
            roaster_domain="test-roaster.com",
            scraped_at=datetime.now(timezone.utc),
            product=product,
            normalization=normalization,
            audit=audit
        )
        
        return artifact
    
    def test_artifact_mapper_has_weight_parser(self):
        """Test that ArtifactMapper has weight parser initialized."""
        assert self.service.artifact_mapper is not None
        assert hasattr(self.service.artifact_mapper, 'weight_parser')
        assert self.service.artifact_mapper.weight_parser is not None
    
    def test_weight_parsing_in_artifact_mapper(self):
        """Test that weight parsing works in the ArtifactMapper."""
        artifact = self.create_test_artifact_with_weight_in_title()
        
        # Test weight parsing through artifact mapper
        rpc_payloads = self.service.artifact_mapper.map_artifact_to_rpc_payloads(
            artifact=artifact,
            roaster_id="roaster-123",
            metadata_only=False
        )
        
        # Verify weight was parsed correctly
        assert len(rpc_payloads['variants']) == 1
        variant_payload = rpc_payloads['variants'][0]
        assert variant_payload['p_weight_g'] == 250  # Parsed from "250g Whole Bean Coffee"
    
    def test_weight_parsing_with_different_formats(self):
        """Test weight parsing with various weight formats in variant titles."""
        test_cases = [
            ("250g Whole Bean", 250),
            ("0.5kg Whole Bean", 500),
            ("8.8oz Whole Bean", 249),  # 8.8 * 28.3495 = 249.47, rounded to 249
            ("1lb Whole Bean", 453),    # 1 * 453.592 = 453.592, rounded to 453
            ("8 1/2 oz Whole Bean", 240),  # 8.5 * 28.3495 = 240.97, rounded to 240
        ]
        
        for title, expected_grams in test_cases:
            # Create variant with specific title
            variant = VariantModel(
                platform_variant_id="var-123",
                sku="SKU123",
                title=title,
                price="24.99",
                price_decimal=24.99,
                currency="USD",
                compare_at_price="29.99",
                compare_at_price_decimal=29.99,
                in_stock=True,
                grams=None,
                weight_unit=None
            )
            
            # Create product with this variant
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
            
            # Create artifact
            artifact = ArtifactModel(
                source=SourceEnum.SHOPIFY,
                roaster_domain="test-roaster.com",
                scraped_at=datetime.now(timezone.utc),
                product=product,
                normalization=NormalizationModel(
                    bean_species=SpeciesEnum.ARABICA,
                    process=ProcessEnum.WASHED,
                    roast_level=RoastLevelEnum.LIGHT,
                    roast_style="Light Roast"
                ),
                audit=AuditModel(
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                    source=SourceEnum.SHOPIFY,
                    notes="Test artifact"
                )
            )
            
            # Test weight parsing
            rpc_payloads = self.service.artifact_mapper.map_artifact_to_rpc_payloads(
                artifact=artifact,
                roaster_id="roaster-123",
                metadata_only=False
            )
            
            # Verify weight was parsed correctly
            assert len(rpc_payloads['variants']) == 1
            variant_payload = rpc_payloads['variants'][0]
            assert variant_payload['p_weight_g'] == expected_grams, \
                f"Failed for {title}: expected {expected_grams}, got {variant_payload['p_weight_g']}"
    
    def test_weight_parsing_fallback_behavior(self):
        """Test weight parsing fallback behavior when no weight can be parsed."""
        # Create variant without weight information
        variant = VariantModel(
            platform_variant_id="var-123",
            sku="SKU123",
            title="Whole Bean Coffee",  # No weight information
            price="24.99",
            price_decimal=24.99,
            currency="USD",
            compare_at_price="29.99",
            compare_at_price_decimal=29.99,
            in_stock=True,
            grams=None,
            weight_unit=None
        )
        
        # Create product with this variant
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
        
        # Create artifact
        artifact = ArtifactModel(
            source=SourceEnum.SHOPIFY,
            roaster_domain="test-roaster.com",
            scraped_at=datetime.now(timezone.utc),
            product=product,
            normalization=NormalizationModel(
                bean_species=SpeciesEnum.ARABICA,
                process=ProcessEnum.WASHED,
                roast_level=RoastLevelEnum.LIGHT,
                roast_style="Light Roast"
            ),
            audit=AuditModel(
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                source=SourceEnum.SHOPIFY,
                notes="Test artifact"
            )
        )
        
        # Test weight parsing
        rpc_payloads = self.service.artifact_mapper.map_artifact_to_rpc_payloads(
            artifact=artifact,
            roaster_id="roaster-123",
            metadata_only=False
        )
        
        # Verify fallback weight was used
        assert len(rpc_payloads['variants']) == 1
        variant_payload = rpc_payloads['variants'][0]
        assert variant_payload['p_weight_g'] == 250  # Default fallback weight
    
    def test_weight_parsing_with_existing_grams(self):
        """Test that existing grams are preserved when available."""
        # Create variant with explicit grams
        variant = VariantModel(
            platform_variant_id="var-123",
            sku="SKU123",
            title="250g Whole Bean Coffee",
            price="24.99",
            price_decimal=24.99,
            currency="USD",
            compare_at_price="29.99",
            compare_at_price_decimal=29.99,
            in_stock=True,
            grams=500,  # Explicit grams should be used
            weight_unit=WeightUnitEnum.GRAMS
        )
        
        # Create product with this variant
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
        
        # Create artifact
        artifact = ArtifactModel(
            source=SourceEnum.SHOPIFY,
            roaster_domain="test-roaster.com",
            scraped_at=datetime.now(timezone.utc),
            product=product,
            normalization=NormalizationModel(
                bean_species=SpeciesEnum.ARABICA,
                process=ProcessEnum.WASHED,
                roast_level=RoastLevelEnum.LIGHT,
                roast_style="Light Roast"
            ),
            audit=AuditModel(
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                source=SourceEnum.SHOPIFY,
                notes="Test artifact"
            )
        )
        
        # Test weight parsing
        rpc_payloads = self.service.artifact_mapper.map_artifact_to_rpc_payloads(
            artifact=artifact,
            roaster_id="roaster-123",
            metadata_only=False
        )
        
        # Verify existing grams were used
        assert len(rpc_payloads['variants']) == 1
        variant_payload = rpc_payloads['variants'][0]
        assert variant_payload['p_weight_g'] == 500  # Should use existing grams, not parse from title
