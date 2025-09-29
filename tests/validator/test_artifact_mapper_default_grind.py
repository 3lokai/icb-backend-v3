"""
Tests for ArtifactMapper default grind determination logic.
"""

from datetime import datetime, timezone
from unittest.mock import Mock

import pytest

from src.validator.artifact_mapper import ArtifactMapper
from src.validator.integration_service import ValidatorIntegrationService
from src.config.validator_config import ValidatorConfig
from src.parser.grind_brewing_parser import GrindBrewingParser, GrindBrewingResult
from src.validator.models import ArtifactModel, ProductModel, VariantModel, NormalizationModel, SourceEnum


class TestArtifactMapperDefaultGrind:
    """Test default grind determination logic."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = ValidatorConfig(enable_grind_brewing_parsing=True)
        self.integration_service = ValidatorIntegrationService(config=self.config)
        self.artifact_mapper = ArtifactMapper(integration_service=self.integration_service)
    
    def test_determine_default_grind_whole_bean_priority(self):
        """Test that whole bean gets highest priority."""
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
            ),
            VariantModel(
                platform_variant_id="v3",
                title="Espresso Grind", 
                price="25.99",
                price_decimal=25.99,
                currency="USD",
                in_stock=True,
                weight_g=250,
                options=["Size", "Espresso Grind"]
            )
        ]
        
        default_grind = self.artifact_mapper._determine_default_grind(variants)
        assert default_grind == "whole"
    
    def test_determine_default_grind_most_common(self):
        """Test that most common grind is selected when no whole bean."""
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
                title="French Press Grind", 
                price="25.99",
                price_decimal=25.99,
                currency="USD",
                in_stock=True,
                weight_g=250,
                options=["Size", "French Press Grind"]
            ),
            VariantModel(
                platform_variant_id="v3",
                title="Espresso Grind",
                price="25.99", 
                price_decimal=25.99,
                currency="USD",
                in_stock=True,
                weight_g=250,
                options=["Size", "Espresso Grind"]
            )
        ]
        
        default_grind = self.artifact_mapper._determine_default_grind(variants)
        assert default_grind == "french_press"
    
    def test_determine_default_grind_preference_order(self):
        """Test that preference order is used for tied grinds."""
        variants = [
            VariantModel(
                platform_variant_id="v1",
                title="Filter Grind",
                price="25.99",
                price_decimal=25.99,
                currency="USD",
                in_stock=True,
                weight_g=250,
                options=["Size", "Filter Grind"]
            ),
            VariantModel(
                platform_variant_id="v2",
                title="Espresso Grind",
                price="25.99",
                price_decimal=25.99,
                currency="USD",
                in_stock=True,
                weight_g=250,
                options=["Size", "Espresso Grind"]
            )
        ]
        
        default_grind = self.artifact_mapper._determine_default_grind(variants)
        # Espresso should be preferred over filter (more specific)
        assert default_grind == "espresso"
    
    def test_determine_default_grind_no_grind_data(self):
        """Test that None is returned when no grind data is available."""
        variants = [
            VariantModel(
                platform_variant_id="v1",
                title="Default Title",
                price="25.99",
                price_decimal=25.99,
                currency="USD",
                in_stock=True,
                weight_g=250,
                options=["Size"]
            )
        ]
        
        default_grind = self.artifact_mapper._determine_default_grind(variants)
        assert default_grind is None
    
    def test_determine_default_grind_low_confidence_filtered(self):
        """Test that low confidence results are filtered out."""
        # Mock the parser to return low confidence results
        mock_parser = Mock(spec=GrindBrewingParser)
        mock_parser.parse_grind_brewing.return_value = GrindBrewingResult(
            grind_type="french_press",
            confidence=0.3,  # Below threshold
            source="variant_title",
            warnings=[],
            original_text="French Press"
        )
        
        self.artifact_mapper.grind_brewing_parser = mock_parser
        
        variants = [
            VariantModel(
                platform_variant_id="v1",
                title="French Press",
                price="25.99",
                price_decimal=25.99,
                currency="USD",
                in_stock=True,
                weight_g=250,
                options=["Size", "French Press"]
            )
        ]
        
        default_grind = self.artifact_mapper._determine_default_grind(variants)
        assert default_grind is None
    
    def test_determine_default_grind_parser_error_handling(self):
        """Test that parser errors are handled gracefully."""
        # Mock the parser to raise an exception
        mock_parser = Mock(spec=GrindBrewingParser)
        mock_parser.parse_grind_brewing.side_effect = Exception("Parser error")
        
        self.artifact_mapper.grind_brewing_parser = mock_parser
        
        variants = [
            VariantModel(
                platform_variant_id="v1",
                title="French Press",
                price="25.99",
                price_decimal=25.99,
                currency="USD",
                in_stock=True,
                weight_g=250,
                options=["Size", "French Press"]
            )
        ]
        
        # Should not raise exception
        default_grind = self.artifact_mapper._determine_default_grind(variants)
        assert default_grind is None
    
    def test_determine_default_grind_no_parser(self):
        """Test that None is returned when parser is not available."""
        self.artifact_mapper.grind_brewing_parser = None
        
        variants = [
            VariantModel(
                platform_variant_id="v1",
                title="French Press",
                price="25.99",
                price_decimal=25.99,
                currency="USD",
                in_stock=True,
                weight_g=250,
                options=["Size", "French Press"]
            )
        ]
        
        default_grind = self.artifact_mapper._determine_default_grind(variants)
        assert default_grind is None
    
    def test_determine_default_grind_empty_variants(self):
        """Test that None is returned for empty variants list."""
        default_grind = self.artifact_mapper._determine_default_grind([])
        assert default_grind is None
    
    def test_coffee_mapping_includes_default_grind(self):
        """Test that coffee mapping includes default grind when available."""
        # Create test artifact with variants
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
        
        # Map the artifact
        coffee_payload = self.artifact_mapper._map_coffee_data(artifact, "test-roaster-id")
        
        # Assertions
        assert 'p_default_grind' in coffee_payload
        assert coffee_payload['p_default_grind'] == "whole"  # Whole bean should be selected
    
    def test_coffee_mapping_no_default_grind_when_none(self):
        """Test that coffee mapping doesn't include default grind when None."""
        # Create test artifact with variants that have no grind data
        variants = [
            VariantModel(
                platform_variant_id="v1",
                title="Default Title",
                price="25.99",
                price_decimal=25.99,
                currency="USD",
                in_stock=True,
                weight_g=250,
                options=["Size"]
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
        
        # Map the artifact
        coffee_payload = self.artifact_mapper._map_coffee_data(artifact, "test-roaster-id")
        
        # Assertions
        assert 'p_default_grind' not in coffee_payload
    
    def test_determine_default_grind_confidence_tracking(self):
        """Test that confidence is tracked for each grind type."""
        # Mock the parser to return different confidence levels
        mock_parser = Mock(spec=GrindBrewingParser)
        
        def mock_parse(variant_dict):
            title = variant_dict.get('title', '')
            if 'French Press' in title:
                return GrindBrewingResult(
                    grind_type="french_press",
                    confidence=0.9,
                    source="variant_title",
                    warnings=[],
                    original_text=title
                )
            elif 'Espresso' in title:
                return GrindBrewingResult(
                    grind_type="espresso",
                    confidence=0.7,
                    source="variant_title", 
                    warnings=[],
                    original_text=title
                )
            else:
                return GrindBrewingResult(
                    grind_type="unknown",
                    confidence=0.0,
                    source="variant_title",
                    warnings=[],
                    original_text=title
                )
        
        mock_parser.parse_grind_brewing.side_effect = mock_parse
        self.artifact_mapper.grind_brewing_parser = mock_parser
        
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
                title="Espresso Grind",
                price="25.99",
                price_decimal=25.99,
                currency="USD",
                in_stock=True,
                weight_g=250,
                options=["Size", "Espresso Grind"]
            )
        ]
        
        default_grind = self.artifact_mapper._determine_default_grind(variants)
        # Both have same count (1 each), but french_press should be preferred due to higher confidence
        assert default_grind == "french_press"
