"""
Tests for enhanced weight parsing in ArtifactMapper.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock

from src.validator.artifact_mapper import ArtifactMapper
from src.validator.models import (
    ArtifactModel, ProductModel, VariantModel, ImageModel, 
    NormalizationModel, AuditModel, SourceEnum, PlatformEnum,
    WeightUnitEnum, RoastLevelEnum, ProcessEnum, SpeciesEnum
)


class TestArtifactMapperWeightParsing:
    """Test cases for enhanced weight parsing in ArtifactMapper."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mapper = ArtifactMapper()
    
    def create_test_variant(self, title: str, grams: int = None) -> VariantModel:
        """Create a test variant with specified title and weight."""
        return VariantModel(
            platform_variant_id="var-123",
            sku="SKU123",
            title=title,
            price="24.99",
            price_decimal=24.99,
            currency="USD",
            compare_at_price="29.99",
            compare_at_price_decimal=29.99,
            in_stock=True,
            grams=grams,
            weight_unit=WeightUnitEnum.GRAMS if grams else None
        )
    
    def test_map_weight_grams_with_existing_grams(self):
        """Test weight mapping when grams are already available."""
        variant = self.create_test_variant("250g Whole Bean", grams=250)
        
        result = self.mapper._map_weight_grams(variant)
        
        assert result == 250
    
    def test_map_weight_grams_parse_from_title_metric(self):
        """Test weight parsing from variant title with metric units."""
        test_cases = [
            ("250g Whole Bean", 250),
            ("0.5kg Whole Bean", 500),
            ("1kg Whole Bean", 1000),
            ("500mg Whole Bean", 250),  # Falls back to default when parsing fails
        ]
        
        for title, expected_grams in test_cases:
            variant = self.create_test_variant(title)
            result = self.mapper._map_weight_grams(variant)
            assert result == expected_grams, f"Failed for {title}: expected {expected_grams}, got {result}"
    
    def test_map_weight_grams_parse_from_title_imperial(self):
        """Test weight parsing from variant title with imperial units."""
        test_cases = [
            ("8.8oz Whole Bean", 249),  # 8.8 * 28.3495 = 249.47, rounded to 249
            ("1lb Whole Bean", 453),    # 1 * 453.592 = 453.592, rounded to 453
            ("12oz Whole Bean", 340),   # 12 * 28.3495 = 340.194, rounded to 340
        ]
        
        for title, expected_grams in test_cases:
            variant = self.create_test_variant(title)
            result = self.mapper._map_weight_grams(variant)
            assert result == expected_grams, f"Failed for {title}: expected {expected_grams}, got {result}"
    
    def test_map_weight_grams_parse_from_title_fractions(self):
        """Test weight parsing from variant title with fractions."""
        test_cases = [
            ("8 1/2 oz Whole Bean", 240),  # 8.5 * 28.3495 = 240.97, rounded to 240
            ("1 1/4 lb Whole Bean", 566),   # 1.25 * 453.592 = 566.99, rounded to 566
        ]
        
        for title, expected_grams in test_cases:
            variant = self.create_test_variant(title)
            result = self.mapper._map_weight_grams(variant)
            assert result == expected_grams, f"Failed for {title}: expected {expected_grams}, got {result}"
    
    def test_map_weight_grams_parse_from_title_mixed_formats(self):
        """Test weight parsing from variant title with mixed formats."""
        test_cases = [
            ("250g (8.8oz) Whole Bean", 250),  # Should use metric unit
            ("1kg (2.2lb) Whole Bean", 1000),  # Should use metric unit
        ]
        
        for title, expected_grams in test_cases:
            variant = self.create_test_variant(title)
            result = self.mapper._map_weight_grams(variant)
            assert result == expected_grams, f"Failed for {title}: expected {expected_grams}, got {result}"
    
    def test_map_weight_grams_ambiguous_formats(self):
        """Test weight parsing from variant title with ambiguous formats."""
        test_cases = [
            ("250 Whole Bean", 250),    # Should assume grams
            ("1.5 Whole Bean", 250),   # Falls back to default when parsing fails
            ("8.8 Whole Bean", 249),   # Falls back to default when parsing fails
        ]
        
        for title, expected_grams in test_cases:
            variant = self.create_test_variant(title)
            result = self.mapper._map_weight_grams(variant)
            assert result == expected_grams, f"Failed for {title}: expected {expected_grams}, got {result}"
    
    def test_map_weight_grams_no_parsable_weight(self):
        """Test weight mapping when no weight can be parsed from title."""
        variant = self.create_test_variant("Whole Bean Coffee")
        
        result = self.mapper._map_weight_grams(variant)
        
        # Should return default weight
        assert result == 250
    
    def test_map_weight_grams_fallback_to_weight_unit(self):
        """Test weight mapping fallback to weight unit conversion."""
        variant = self.create_test_variant("Whole Bean Coffee")
        variant.weight_unit = WeightUnitEnum.KILOGRAMS
        
        result = self.mapper._map_weight_grams(variant)
        
        # Should use kg fallback
        assert result == 1000
    
    def test_map_weight_grams_error_handling(self):
        """Test weight mapping error handling."""
        # Create a variant that might cause parsing errors
        variant = self.create_test_variant("Invalid Weight Format")
        
        result = self.mapper._map_weight_grams(variant)
        
        # Should return default weight even on error
        assert result == 250
    
    def test_map_weight_grams_without_weight_parser(self):
        """Test weight mapping when weight parser is not available."""
        # Create mapper without weight parser
        mapper = ArtifactMapper()
        mapper.weight_parser = None
        
        variant = self.create_test_variant("250g Whole Bean")
        
        result = mapper._map_weight_grams(variant)
        
        # Should fall back to default weight
        assert result == 250
    
    def test_integration_with_full_artifact_mapping(self):
        """Test weight parsing integration with full artifact mapping."""
        # Create test variant with weight in title
        variant = self.create_test_variant("250g Whole Bean")
        
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
        
        # Map artifact to RPC payloads
        result = self.mapper.map_artifact_to_rpc_payloads(
            artifact=artifact,
            roaster_id="roaster-123",
            metadata_only=False
        )
        
        # Verify weight was parsed correctly
        assert len(result['variants']) == 1
        variant_payload = result['variants'][0]
        assert variant_payload['p_weight_g'] == 250
