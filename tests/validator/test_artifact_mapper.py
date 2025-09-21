"""
Tests for artifact mapper functionality.
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


class TestArtifactMapper:
    """Test cases for artifact mapper."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mapper = ArtifactMapper()
    
    def create_test_artifact(self) -> ArtifactModel:
        """Create a test artifact."""
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
        
        # Create test normalization
        normalization = NormalizationModel(
            is_coffee=True,
            content_hash="hash123",
            name_clean="Test Coffee",
            description_md_clean="# Test Coffee\nA test coffee.",
            roast_level_enum=RoastLevelEnum.LIGHT,
            roast_level_raw="Light Roast",
            process_enum=ProcessEnum.WASHED,
            process_raw="Fully Washed",
            bean_species=SpeciesEnum.ARABICA,
            varieties=["Bourbon"],
            region="Ethiopia",
            country="Ethiopia",
            altitude_m=1800
        )
        
        # Create test audit
        audit = AuditModel(
            artifact_id="artifact-123",
            created_at=datetime.now(timezone.utc),
            collected_by="test-collector"
        )
        
        # Create test artifact
        artifact = ArtifactModel(
            source=SourceEnum.SHOPIFY,
            roaster_domain="test.com",
            scraped_at=datetime.now(timezone.utc),
            product=product,
            normalization=normalization,
            audit=audit
        )
        
        return artifact
    
    def test_map_artifact_to_rpc_payloads_success(self):
        """Test successful artifact mapping to RPC payloads."""
        artifact = self.create_test_artifact()
        roaster_id = "roaster-123"
        
        result = self.mapper.map_artifact_to_rpc_payloads(
            artifact=artifact,
            roaster_id=roaster_id,
            metadata_only=False
        )
        
        # Verify structure
        assert 'coffee' in result
        assert 'variants' in result
        assert 'prices' in result
        assert 'images' in result
        assert result['roaster_id'] == roaster_id
        assert result['metadata_only'] is False
        assert result['platform_product_id'] == "prod-123"
        
        # Verify coffee payload
        coffee = result['coffee']
        assert coffee['p_bean_species'] == 'arabica'
        assert coffee['p_name'] == 'Test Coffee'
        assert coffee['p_slug'] == 'test-coffee'
        assert coffee['p_roaster_id'] == roaster_id
        assert coffee['p_process'] == 'washed'
        assert coffee['p_roast_level'] == 'light'
        assert coffee['p_description_md'] == '# Test Coffee\nA test coffee.'
        assert coffee['p_platform_product_id'] == 'prod-123'
        assert 'p_source_raw' in coffee
        assert 'p_notes_raw' in coffee
        
        # Verify variants payload
        assert len(result['variants']) == 1
        variant = result['variants'][0]
        assert variant['p_platform_variant_id'] == 'var-123'
        assert variant['p_sku'] == 'SKU123'
        assert variant['p_weight_g'] == 250
        assert variant['p_currency'] == 'USD'
        assert variant['p_in_stock'] is True
        assert variant['p_compare_at_price'] == 29.99
        
        # Verify prices payload
        assert len(result['prices']) == 1
        price = result['prices'][0]
        assert price['p_price'] == 24.99
        assert price['p_currency'] == 'USD'
        assert price['p_is_sale'] is True  # price < compare_at_price
        assert 'p_scraped_at' in price
        assert 'p_source_url' in price
        
        # Verify mapping stats
        assert self.mapper.mapping_stats['total_mapped'] == 1
        assert self.mapper.mapping_stats['coffee_mapped'] == 1
        assert self.mapper.mapping_stats['variants_mapped'] == 1
        assert self.mapper.mapping_stats['prices_mapped'] == 1
    
    def test_map_artifact_metadata_only(self):
        """Test artifact mapping with metadata-only flag."""
        artifact = self.create_test_artifact()
        roaster_id = "roaster-123"
        
        result = self.mapper.map_artifact_to_rpc_payloads(
            artifact=artifact,
            roaster_id=roaster_id,
            metadata_only=True
        )
        
        # Verify metadata-only flag
        assert result['metadata_only'] is True
        
        # Verify images are empty for metadata-only
        assert len(result['images']) == 0
        
        # Verify other payloads are still present
        assert 'coffee' in result
        assert 'variants' in result
        assert 'prices' in result
    
    def test_map_artifact_with_images(self):
        """Test artifact mapping with images."""
        artifact = self.create_test_artifact()
        
        # Add images to product
        image1 = ImageModel(
            url="https://test.com/image1.jpg",
            alt_text="Test image 1",
            order=1,
            source_id="img1"
        )
        image2 = ImageModel(
            url="https://test.com/image2.jpg",
            alt_text="Test image 2",
            order=2,
            source_id="img2"
        )
        artifact.product.images = [image1, image2]
        
        result = self.mapper.map_artifact_to_rpc_payloads(
            artifact=artifact,
            roaster_id="roaster-123",
            metadata_only=False
        )
        
        # Verify images payload
        assert len(result['images']) == 2
        
        image1_payload = result['images'][0]
        assert image1_payload['p_url'] == "https://test.com/image1.jpg"
        assert image1_payload['p_alt'] == "Test image 1"
        assert image1_payload['p_sort_order'] == 1
        
        image2_payload = result['images'][1]
        assert image2_payload['p_url'] == "https://test.com/image2.jpg"
        assert image2_payload['p_alt'] == "Test image 2"
        assert image2_payload['p_sort_order'] == 2
        
        assert self.mapper.mapping_stats['images_mapped'] == 2
    
    def test_map_artifact_without_normalization(self):
        """Test artifact mapping without normalization data."""
        artifact = self.create_test_artifact()
        artifact.normalization = None
        
        result = self.mapper.map_artifact_to_rpc_payloads(
            artifact=artifact,
            roaster_id="roaster-123",
            metadata_only=False
        )
        
        # Verify default values are used
        coffee = result['coffee']
        assert coffee['p_bean_species'] == 'arabica'  # Default
        assert coffee['p_name'] == 'Test Coffee'  # From product title
        assert coffee['p_process'] == 'other'  # Default
        assert coffee['p_roast_level'] == 'unknown'  # Default
        assert coffee['p_notes_raw'] is None
    
    def test_map_artifact_without_audit(self):
        """Test artifact mapping without audit data."""
        artifact = self.create_test_artifact()
        artifact.audit = None
        
        result = self.mapper.map_artifact_to_rpc_payloads(
            artifact=artifact,
            roaster_id="roaster-123",
            metadata_only=False
        )
        
        # Verify source_raw handles missing audit
        coffee = result['coffee']
        source_raw = coffee['p_source_raw']
        assert source_raw['artifact_id'] is None
        assert 'scraped_at' in source_raw
        assert 'source' in source_raw
        assert 'roaster_domain' in source_raw
    
    def test_map_artifact_with_grind_options(self):
        """Test artifact mapping with grind options."""
        artifact = self.create_test_artifact()
        
        # Add grind options to variant
        artifact.product.variants[0].options = ["Whole Bean", "Ground", "Espresso"]
        
        result = self.mapper.map_artifact_to_rpc_payloads(
            artifact=artifact,
            roaster_id="roaster-123",
            metadata_only=False
        )
        
        # Verify grind is mapped from options
        variant = result['variants'][0]
        assert variant['p_grind'] == 'whole'  # "Whole Bean" should map to 'whole'
    
    def test_map_artifact_with_decaf_detection(self):
        """Test artifact mapping with decaf detection."""
        artifact = self.create_test_artifact()
        
        # Add decaf keyword to title
        artifact.product.title = "Decaf Test Coffee"
        
        result = self.mapper.map_artifact_to_rpc_payloads(
            artifact=artifact,
            roaster_id="roaster-123",
            metadata_only=False
        )
        
        # Verify decaf flag is detected
        coffee = result['coffee']
        assert coffee['p_decaf'] is True
    
    def test_map_artifact_currency_normalization(self):
        """Test artifact mapping with currency normalization."""
        artifact = self.create_test_artifact()
        
        # Test various currency formats
        test_cases = [
            ("usd", "USD"),
            ("CAD", "CAD"),
            ("eur", "EUR"),
            ("gbp", "GBP"),
            ("aud", "AUD"),
            ("unknown", "UNKNOWN")
        ]
        
        for input_currency, expected_currency in test_cases:
            artifact.product.variants[0].currency = input_currency
            
            result = self.mapper.map_artifact_to_rpc_payloads(
                artifact=artifact,
                roaster_id="roaster-123",
                metadata_only=False
            )
            
            variant = result['variants'][0]
            assert variant['p_currency'] == expected_currency
    
    def test_map_artifact_sale_price_detection(self):
        """Test artifact mapping with sale price detection."""
        artifact = self.create_test_artifact()
        
        # Set price higher than compare_at_price (not a sale)
        artifact.product.variants[0].price_decimal = 35.99
        artifact.product.variants[0].compare_at_price_decimal = 29.99
        
        result = self.mapper.map_artifact_to_rpc_payloads(
            artifact=artifact,
            roaster_id="roaster-123",
            metadata_only=False
        )
        
        # Verify sale status is correctly detected
        price = result['prices'][0]
        assert price['p_is_sale'] is False  # price > compare_at_price
    
    def test_map_artifact_error_handling(self):
        """Test artifact mapping error handling."""
        # Create valid artifact but with problematic data that might cause mapping errors
        artifact = self.create_test_artifact()
        
        # Test with invalid roaster_id (empty string)
        result = self.mapper.map_artifact_to_rpc_payloads(
            artifact=artifact,
            roaster_id="",  # Empty roaster_id might cause issues
            metadata_only=False
        )
        
        # Should still work but might have warnings
        assert 'coffee' in result
        assert result['roaster_id'] == ""
        
        # Test with None roaster_id
        result = self.mapper.map_artifact_to_rpc_payloads(
            artifact=artifact,
            roaster_id=None,  # None roaster_id
            metadata_only=False
        )
        
        # Should still work
        assert 'coffee' in result
        assert result['roaster_id'] is None
    
    def test_get_mapping_stats(self):
        """Test mapping statistics retrieval."""
        # Set some stats
        self.mapper.mapping_stats['total_mapped'] = 10
        self.mapper.mapping_stats['coffee_mapped'] = 10
        self.mapper.mapping_stats['variants_mapped'] = 25
        self.mapper.mapping_stats['prices_mapped'] = 25
        self.mapper.mapping_stats['images_mapped'] = 15
        self.mapper.mapping_stats['mapping_errors'] = 2
        
        stats = self.mapper.get_mapping_stats()
        
        assert stats['total_mapped'] == 10
        assert stats['coffee_mapped'] == 10
        assert stats['variants_mapped'] == 25
        assert stats['prices_mapped'] == 25
        assert stats['images_mapped'] == 15
        assert stats['mapping_errors'] == 2
        assert stats['success_rate'] == 0.8  # (10 - 2) / 10
        assert stats['error_rate'] == 0.2  # 2 / 10
    
    def test_reset_stats(self):
        """Test mapping statistics reset."""
        # Set some stats
        self.mapper.mapping_stats['total_mapped'] = 10
        self.mapper.mapping_stats['coffee_mapped'] = 10
        
        self.mapper.reset_stats()
        
        assert self.mapper.mapping_stats['total_mapped'] == 0
        assert self.mapper.mapping_stats['coffee_mapped'] == 0
        assert self.mapper.mapping_stats['variants_mapped'] == 0
        assert self.mapper.mapping_stats['prices_mapped'] == 0
        assert self.mapper.mapping_stats['images_mapped'] == 0
        assert self.mapper.mapping_stats['mapping_errors'] == 0
