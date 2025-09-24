"""
Tests for ArtifactMapper roast and process parsing integration.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock

from src.validator.artifact_mapper import ArtifactMapper
from src.validator.models import (
    ArtifactModel, ProductModel, VariantModel, NormalizationModel, 
    SourceEnum, PlatformEnum, RoastLevelEnum, ProcessEnum, SpeciesEnum
)


class TestArtifactMapperRoastProcess:
    """Test cases for ArtifactMapper roast and process parsing integration."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mapper = ArtifactMapper()
    
    def create_test_artifact_with_roast_process(self) -> ArtifactModel:
        """Create a test artifact with roast and process data."""
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
        
        return artifact
    
    def test_roast_parser_integration(self):
        """Test roast parser integration in ArtifactMapper."""
        artifact = self.create_test_artifact_with_roast_process()
        
        # Test coffee mapping with roast parsing
        coffee_payload = self.mapper._map_coffee_data(artifact, "roaster-123")
        
        # Verify roast level is parsed correctly
        assert 'p_roast_level' in coffee_payload
        assert coffee_payload['p_roast_level'] == 'medium'  # Should be parsed by roast parser
        
        # Verify raw roast level is preserved
        assert 'p_roast_level_raw' in coffee_payload
        assert coffee_payload['p_roast_level_raw'] == "Medium Roast"
    
    def test_process_parser_integration(self):
        """Test process parser integration in ArtifactMapper."""
        artifact = self.create_test_artifact_with_roast_process()
        
        # Test coffee mapping with process parsing
        coffee_payload = self.mapper._map_coffee_data(artifact, "roaster-123")
        
        # Verify process method is parsed correctly
        assert 'p_process' in coffee_payload
        assert coffee_payload['p_process'] == 'washed'  # Should be parsed by process parser
        
        # Verify raw process method is preserved
        assert 'p_process_raw' in coffee_payload
        assert coffee_payload['p_process_raw'] == "Washed Process"
    
    def test_roast_parser_fallback(self):
        """Test roast parser fallback when parser is not available."""
        # Create mapper without parsers
        mapper = ArtifactMapper()
        mapper.roast_parser = None
        
        artifact = self.create_test_artifact_with_roast_process()
        coffee_payload = mapper._map_coffee_data(artifact, "roaster-123")
        
        # Should fallback to enum value
        assert coffee_payload['p_roast_level'] == 'medium'
    
    def test_process_parser_fallback(self):
        """Test process parser fallback when parser is not available."""
        # Create mapper without parsers
        mapper = ArtifactMapper()
        mapper.process_parser = None
        
        artifact = self.create_test_artifact_with_roast_process()
        coffee_payload = mapper._map_coffee_data(artifact, "roaster-123")
        
        # Should fallback to enum value
        assert coffee_payload['p_process'] == 'washed'
    
    def test_roast_parser_error_handling(self):
        """Test roast parser error handling."""
        artifact = self.create_test_artifact_with_roast_process()
        
        # Mock parser to raise exception
        mock_parser = Mock()
        mock_parser.parse_roast_level.side_effect = Exception("Parser error")
        self.mapper.roast_parser = mock_parser
        
        coffee_payload = self.mapper._map_coffee_data(artifact, "roaster-123")
        
        # Should fallback to enum value when parser fails
        assert coffee_payload['p_roast_level'] == 'medium'
    
    def test_process_parser_error_handling(self):
        """Test process parser error handling."""
        artifact = self.create_test_artifact_with_roast_process()
        
        # Mock parser to raise exception
        mock_parser = Mock()
        mock_parser.parse_process_method.side_effect = Exception("Parser error")
        self.mapper.process_parser = mock_parser
        
        coffee_payload = self.mapper._map_coffee_data(artifact, "roaster-123")
        
        # Should fallback to enum value when parser fails
        assert coffee_payload['p_process'] == 'washed'
    
    def test_missing_roast_process_data(self):
        """Test handling of missing roast and process data."""
        # Create artifact without roast/process data
        variant = VariantModel(
            platform_variant_id="var-123",
            sku="SKU123",
            title="250g Whole Bean",
            price="24.99",
            price_decimal=24.99,
            currency="USD",
            in_stock=True
        )
        
        product = ProductModel(
            platform_product_id="prod-123",
            platform=PlatformEnum.SHOPIFY,
            title="Test Coffee",
            handle="test-coffee",
            slug="test-coffee",
            source_url="https://test.com/coffee",
            variants=[variant]
        )
        
        # Create normalization without roast/process data
        normalization = NormalizationModel(
            is_coffee=True,
            bean_species=SpeciesEnum.ARABICA
        )
        
        artifact = ArtifactModel(
            source=SourceEnum.SHOPIFY,
            roaster_domain="test.com",
            scraped_at=datetime.now(timezone.utc),
            product=product,
            normalization=normalization
        )
        
        coffee_payload = self.mapper._map_coffee_data(artifact, "roaster-123")
        
        # Should handle missing data gracefully
        assert coffee_payload['p_roast_level'] is None
        assert coffee_payload['p_process'] is None
        assert coffee_payload['p_roast_level_raw'] is None
        assert coffee_payload['p_process_raw'] is None
    
    def test_parser_initialization(self):
        """Test that parsers are properly initialized."""
        mapper = ArtifactMapper()
        
        # Should have parsers initialized
        assert mapper.roast_parser is not None
        assert mapper.process_parser is not None
        
        # Should be instances of the correct classes
        from src.parser.roast_parser import RoastLevelParser
        from src.parser.process_parser import ProcessMethodParser
        
        assert isinstance(mapper.roast_parser, RoastLevelParser)
        assert isinstance(mapper.process_parser, ProcessMethodParser)
