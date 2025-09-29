"""
Test grind/brewing parser integration with ArtifactMapper.
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timezone

from src.validator.artifact_mapper import ArtifactMapper
from src.validator.models import ArtifactModel, ProductModel, VariantModel, NormalizationModel
from src.parser.grind_brewing_parser import GrindBrewingParser, GrindBrewingResult


class TestArtifactMapperGrindBrewingIntegration:
    """Test grind/brewing parser integration with ArtifactMapper."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_rpc_client = Mock()
        self.mock_integration_service = Mock()
        self.mock_integration_service.grind_brewing_parser = GrindBrewingParser()
        
        self.artifact_mapper = ArtifactMapper(
            rpc_client=self.mock_rpc_client,
            integration_service=self.mock_integration_service
        )
    
    def test_grind_brewing_parser_initialization(self):
        """Test that grind/brewing parser is properly initialized."""
        assert self.artifact_mapper.grind_brewing_parser is not None
        assert isinstance(self.artifact_mapper.grind_brewing_parser, GrindBrewingParser)
    
    def test_variant_mapping_with_grind_parsing(self):
        """Test variant mapping with grind/brewing parsing."""
        # Create test artifact with variants
        variant = VariantModel(
            platform_variant_id="test-variant-1",
            sku="TEST-SKU-001",
            title="French Press Grind",
            price="25.99",
            price_decimal=25.99,
            currency="USD",
            in_stock=True,
            weight_g=250,
            options=["Size", "French Press Grind"],
            raw_variant_json={"title": "French Press Grind"}
        )
        
        product = ProductModel(
            platform_product_id="test-product-1",
            title="Test Coffee",
            source_url="https://example.com/test-coffee",
            variants=[variant]
        )
        
        artifact = ArtifactModel(
            product=product,
            normalization=NormalizationModel(),
            scraped_at=datetime.now(timezone.utc),
            source="other",
            roaster_domain="example.com"
        )
        
        # Map variants
        variants_payloads = self.artifact_mapper._map_variants_data(artifact, metadata_only=False)
        
        # Verify grind parsing was applied
        assert len(variants_payloads) == 1
        variant_payload = variants_payloads[0]
        
        # Check that grind was parsed and added
        assert 'p_grind' in variant_payload
        assert variant_payload['p_grind'] == 'french_press'
        
        # Check that parsing metadata was added
        assert 'p_source_raw' in variant_payload
        assert 'grind_brewing_parsing' in variant_payload['p_source_raw']
        
        parsing_metadata = variant_payload['p_source_raw']['grind_brewing_parsing']
        assert parsing_metadata['grind_type'] == 'french_press'
        assert parsing_metadata['confidence'] > 0.7
        assert parsing_metadata['source'] == 'variant_title'
    
    def test_variant_mapping_with_unknown_grind(self):
        """Test variant mapping when grind cannot be determined."""
        # Create test artifact with unknown grind variant
        variant = VariantModel(
            platform_variant_id="test-variant-2",
            sku="TEST-SKU-002",
            title="Unknown Grind Type",
            price="25.99",
            price_decimal=25.99,
            currency="USD",
            in_stock=True,
            weight_g=250,
            options=["Size", "Unknown Grind Type"],
            raw_variant_json={"title": "Unknown Grind Type"}
        )
        
        product = ProductModel(
            platform_product_id="test-product-2",
            title="Test Coffee",
            source_url="https://example.com/test-coffee-2",
            variants=[variant]
        )
        
        artifact = ArtifactModel(
            product=product,
            normalization=NormalizationModel(),
            scraped_at=datetime.now(timezone.utc),
            source="other",
            roaster_domain="example.com"
        )
        
        # Map variants
        variants_payloads = self.artifact_mapper._map_variants_data(artifact, metadata_only=False)
        
        # Verify no grind was added for unknown grind
        assert len(variants_payloads) == 1
        variant_payload = variants_payloads[0]
        
        # Check that no grind was added
        assert 'p_grind' not in variant_payload
    
    def test_variant_mapping_with_grind_parsing_error(self):
        """Test variant mapping when grind parsing fails."""
        # Mock grind parser to raise an exception
        mock_parser = Mock()
        mock_parser.parse_grind_brewing.side_effect = Exception("Parsing error")
        
        self.artifact_mapper.grind_brewing_parser = mock_parser
        
        # Create test artifact
        variant = VariantModel(
            platform_variant_id="test-variant-3",
            sku="TEST-SKU-003",
            title="French Press Grind",
            price="25.99",
            price_decimal=25.99,
            currency="USD",
            in_stock=True,
            weight_g=250,
            options=["Size", "French Press Grind"],
            raw_variant_json={"title": "French Press Grind"}
        )
        
        product = ProductModel(
            platform_product_id="test-product-3",
            title="Test Coffee",
            source_url="https://example.com/test-coffee-3",
            variants=[variant]
        )
        
        artifact = ArtifactModel(
            product=product,
            normalization=NormalizationModel(),
            scraped_at=datetime.now(timezone.utc),
            source="other",
            roaster_domain="example.com"
        )
        
        # Map variants - should not raise exception
        variants_payloads = self.artifact_mapper._map_variants_data(artifact, metadata_only=False)
        
        # Verify variant was still processed despite parsing error
        assert len(variants_payloads) == 1
        variant_payload = variants_payloads[0]
        
        # Check that no grind was added due to error
        assert 'p_grind' not in variant_payload
    
    def test_variant_mapping_without_grind_parser(self):
        """Test variant mapping when grind parser is not available."""
        # Set grind parser to None
        self.artifact_mapper.grind_brewing_parser = None
        
        # Create test artifact
        variant = VariantModel(
            platform_variant_id="test-variant-4",
            sku="TEST-SKU-004",
            title="French Press Grind",
            price="25.99",
            price_decimal=25.99,
            currency="USD",
            in_stock=True,
            weight_g=250,
            options=["Size", "French Press Grind"],
            raw_variant_json={"title": "French Press Grind"}
        )
        
        product = ProductModel(
            platform_product_id="test-product-4",
            title="Test Coffee",
            source_url="https://example.com/test-coffee-4",
            variants=[variant]
        )
        
        artifact = ArtifactModel(
            product=product,
            normalization=NormalizationModel(),
            scraped_at=datetime.now(timezone.utc),
            source="other",
            roaster_domain="example.com"
        )
        
        # Map variants
        variants_payloads = self.artifact_mapper._map_variants_data(artifact, metadata_only=False)
        
        # Verify variant was processed without grind parsing
        assert len(variants_payloads) == 1
        variant_payload = variants_payloads[0]
        
        # Check that no grind was added
        assert 'p_grind' not in variant_payload
    
    def test_variant_mapping_with_shopify_options(self):
        """Test variant mapping with Shopify-style options."""
        # Create test artifact with Shopify-style options
        variant = VariantModel(
            platform_variant_id="test-variant-5",
            sku="TEST-SKU-005",
            title="Default Title",
            price="25.99",
            price_decimal=25.99,
            currency="USD",
            in_stock=True,
            weight_g=250,
            options=["Size", "Espresso Grind"],  # Second option is grind
            raw_variant_json={"title": "Default Title"}
        )
        
        product = ProductModel(
            platform_product_id="test-product-5",
            title="Test Coffee",
            source_url="https://example.com/test-coffee-5",
            variants=[variant]
        )
        
        artifact = ArtifactModel(
            product=product,
            normalization=NormalizationModel(),
            scraped_at=datetime.now(timezone.utc),
            source="other",
            roaster_domain="example.com"
        )
        
        # Map variants
        variants_payloads = self.artifact_mapper._map_variants_data(artifact, metadata_only=False)
        
        # Verify grind parsing was applied from options
        assert len(variants_payloads) == 1
        variant_payload = variants_payloads[0]
        
        # Check that grind was parsed from options
        assert 'p_grind' in variant_payload
        assert variant_payload['p_grind'] == 'espresso'
        
        # Check parsing metadata
        parsing_metadata = variant_payload['p_source_raw']['grind_brewing_parsing']
        assert parsing_metadata['source'] == 'variant_option'
    
    def test_variant_mapping_with_woocommerce_attributes(self):
        """Test variant mapping with WooCommerce-style attributes."""
        # Create test artifact with WooCommerce-style attributes
        variant = VariantModel(
            platform_variant_id="test-variant-6",
            sku="TEST-SKU-006",
            title="Default Title",
            price="25.99",
            price_decimal=25.99,
            currency="USD",
            in_stock=True,
            weight_g=250,
            options=["Size", "Default Title"],
            attributes=[
                {
                    "name": "Grind Size",
                    "terms": [{"name": "Cold Brew"}]
                }
            ],
            raw_variant_json={"title": "Default Title"}
        )
        
        product = ProductModel(
            platform_product_id="test-product-6",
            title="Test Coffee",
            source_url="https://example.com/test-coffee-6",
            variants=[variant]
        )
        
        artifact = ArtifactModel(
            product=product,
            normalization=NormalizationModel(),
            scraped_at=datetime.now(timezone.utc),
            source="other",
            roaster_domain="example.com"
        )
        
        # Map variants
        variants_payloads = self.artifact_mapper._map_variants_data(artifact, metadata_only=False)
        
        # Verify grind parsing was applied from attributes
        assert len(variants_payloads) == 1
        variant_payload = variants_payloads[0]
        
        # Check that grind was parsed from attributes
        assert 'p_grind' in variant_payload
        assert variant_payload['p_grind'] == 'cold_brew'
        
        # Check parsing metadata
        parsing_metadata = variant_payload['p_source_raw']['grind_brewing_parsing']
        assert parsing_metadata['source'] == 'variant_attribute'
