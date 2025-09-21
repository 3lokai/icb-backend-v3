"""
Tests for Pydantic models.
"""

import pytest
from datetime import datetime, timezone
from pydantic import ValidationError

from src.validator.models import (
    ArtifactModel,
    ProductModel,
    VariantModel,
    ImageModel,
    NormalizationModel,
    SensoryParamsModel,
    SourceEnum,
    PlatformEnum,
    RoastLevelEnum,
    ProcessEnum,
    GrindEnum,
    SpeciesEnum,
    SensoryConfidenceEnum,
    SensorySourceEnum
)


class TestArtifactModel:
    """Test cases for ArtifactModel."""
    
    def test_valid_artifact(self):
        """Test valid artifact creation."""
        artifact_data = {
            "source": "shopify",
            "roaster_domain": "example.com",
            "scraped_at": "2025-01-12T10:00:00Z",
            "product": {
                "platform_product_id": "123",
                "title": "Test Product",
                "source_url": "https://example.com/product",
                "variants": [
                    {
                        "platform_variant_id": "v-001",
                        "price": "10.00"
                    }
                ]
            }
        }
        
        artifact = ArtifactModel(**artifact_data)
        
        assert artifact.source == SourceEnum.SHOPIFY
        assert artifact.roaster_domain == "example.com"
        assert isinstance(artifact.scraped_at, datetime)
        assert artifact.product.platform_product_id == "123"
        assert len(artifact.product.variants) == 1
    
    def test_invalid_source(self):
        """Test invalid source enum."""
        artifact_data = {
            "source": "invalid_platform",
            "roaster_domain": "example.com",
            "scraped_at": "2025-01-12T10:00:00Z",
            "product": {
                "platform_product_id": "123",
                "title": "Test Product",
                "source_url": "https://example.com/product",
                "variants": [
                    {
                        "platform_variant_id": "v-001",
                        "price": "10.00"
                    }
                ]
            }
        }
        
        with pytest.raises(ValidationError) as exc_info:
            ArtifactModel(**artifact_data)
        
        assert "source" in str(exc_info.value)
    
    def test_invalid_roaster_domain(self):
        """Test invalid roaster domain."""
        artifact_data = {
            "source": "shopify",
            "roaster_domain": "",  # Empty domain
            "scraped_at": "2025-01-12T10:00:00Z",
            "product": {
                "platform_product_id": "123",
                "title": "Test Product",
                "source_url": "https://example.com/product",
                "variants": [
                    {
                        "platform_variant_id": "v-001",
                        "price": "10.00"
                    }
                ]
            }
        }
        
        with pytest.raises(ValidationError) as exc_info:
            ArtifactModel(**artifact_data)
        
        assert "roaster_domain" in str(exc_info.value)
    
    def test_invalid_timestamp(self):
        """Test invalid timestamp format."""
        artifact_data = {
            "source": "shopify",
            "roaster_domain": "example.com",
            "scraped_at": "invalid-timestamp",
            "product": {
                "platform_product_id": "123",
                "title": "Test Product",
                "source_url": "https://example.com/product",
                "variants": [
                    {
                        "platform_variant_id": "v-001",
                        "price": "10.00"
                    }
                ]
            }
        }
        
        with pytest.raises(ValidationError) as exc_info:
            ArtifactModel(**artifact_data)
        
        assert "scraped_at" in str(exc_info.value)
    
    def test_missing_required_fields(self):
        """Test missing required fields."""
        artifact_data = {
            "source": "shopify",
            # Missing roaster_domain, scraped_at, product
        }
        
        with pytest.raises(ValidationError) as exc_info:
            ArtifactModel(**artifact_data)
        
        error_str = str(exc_info.value)
        assert "roaster_domain" in error_str
        assert "scraped_at" in error_str
        assert "product" in error_str


class TestProductModel:
    """Test cases for ProductModel."""
    
    def test_valid_product(self):
        """Test valid product creation."""
        product_data = {
            "platform_product_id": "123",
            "title": "Test Product",
            "source_url": "https://example.com/product",
            "variants": [
                {
                    "platform_variant_id": "v-001",
                    "price": "10.00"
                }
            ]
        }
        
        product = ProductModel(**product_data)
        
        assert product.platform_product_id == "123"
        assert product.title == "Test Product"
        assert product.source_url == "https://example.com/product"
        assert len(product.variants) == 1
    
    def test_missing_required_fields(self):
        """Test missing required product fields."""
        product_data = {
            "title": "Test Product",
            # Missing platform_product_id, source_url, variants
        }
        
        with pytest.raises(ValidationError) as exc_info:
            ProductModel(**product_data)
        
        error_str = str(exc_info.value)
        assert "platform_product_id" in error_str
        assert "source_url" in error_str
        assert "variants" in error_str
    
    def test_empty_variants(self):
        """Test product with empty variants array."""
        product_data = {
            "platform_product_id": "123",
            "title": "Test Product",
            "source_url": "https://example.com/product",
            "variants": []  # Empty variants
        }
        
        with pytest.raises(ValidationError) as exc_info:
            ProductModel(**product_data)
        
        assert "variants" in str(exc_info.value)


class TestVariantModel:
    """Test cases for VariantModel."""
    
    def test_valid_variant(self):
        """Test valid variant creation."""
        variant_data = {
            "platform_variant_id": "v-001",
            "price": "10.00"
        }
        
        variant = VariantModel(**variant_data)
        
        assert variant.platform_variant_id == "v-001"
        assert variant.price == "10.00"
    
    def test_missing_required_fields(self):
        """Test missing required variant fields."""
        variant_data = {
            "sku": "TEST-001",
            # Missing platform_variant_id and price
        }
        
        with pytest.raises(ValidationError) as exc_info:
            VariantModel(**variant_data)
        
        error_str = str(exc_info.value)
        assert "platform_variant_id" in error_str
        assert "price" in error_str
    
    def test_invalid_weight_unit(self):
        """Test invalid weight unit enum."""
        variant_data = {
            "platform_variant_id": "v-001",
            "price": "10.00",
            "weight_unit": "invalid_unit"
        }
        
        with pytest.raises(ValidationError) as exc_info:
            VariantModel(**variant_data)
        
        assert "weight_unit" in str(exc_info.value)


class TestNormalizationModel:
    """Test cases for NormalizationModel."""
    
    def test_valid_normalization(self):
        """Test valid normalization data."""
        normalization_data = {
            "is_coffee": True,
            "roast_level_enum": "medium",
            "process_enum": "washed",
            "default_grind": "whole",
            "bean_species": "arabica"
        }
        
        normalization = NormalizationModel(**normalization_data)
        
        assert normalization.is_coffee is True
        assert normalization.roast_level_enum == RoastLevelEnum.MEDIUM
        assert normalization.process_enum == ProcessEnum.WASHED
        assert normalization.default_grind == GrindEnum.WHOLE
        assert normalization.bean_species == SpeciesEnum.ARABICA
    
    def test_invalid_enum_values(self):
        """Test invalid enum values."""
        normalization_data = {
            "roast_level_enum": "invalid_roast",
            "process_enum": "invalid_process",
            "default_grind": "invalid_grind",
            "bean_species": "invalid_species"
        }
        
        with pytest.raises(ValidationError) as exc_info:
            NormalizationModel(**normalization_data)
        
        error_str = str(exc_info.value)
        assert "roast_level_enum" in error_str
        assert "process_enum" in error_str
        assert "default_grind" in error_str
        assert "bean_species" in error_str
    
    def test_null_enum_values(self):
        """Test null enum values (should be allowed)."""
        normalization_data = {
            "roast_level_enum": None,
            "process_enum": None,
            "default_grind": None,
            "bean_species": None
        }
        
        normalization = NormalizationModel(**normalization_data)
        
        assert normalization.roast_level_enum is None
        assert normalization.process_enum is None
        assert normalization.default_grind is None
        assert normalization.bean_species is None


class TestSensoryParamsModel:
    """Test cases for SensoryParamsModel."""
    
    def test_valid_sensory_params(self):
        """Test valid sensory parameters."""
        sensory_data = {
            "acidity": 7.5,
            "sweetness": 6.0,
            "bitterness": 4.0,
            "body": 6.5,
            "clarity": 8.0,
            "aftertaste": 7.0,
            "confidence": "high",
            "source": "roaster"
        }
        
        sensory = SensoryParamsModel(**sensory_data)
        
        assert sensory.acidity == 7.5
        assert sensory.sweetness == 6.0
        assert sensory.confidence == SensoryConfidenceEnum.HIGH
        assert sensory.source == SensorySourceEnum.ROASTER
    
    def test_invalid_sensory_values(self):
        """Test invalid sensory parameter values."""
        sensory_data = {
            "acidity": 15.0,  # > 10
            "sweetness": -5.0,  # < 0
            "confidence": "invalid_confidence",
            "source": "invalid_source"
        }
        
        with pytest.raises(ValidationError) as exc_info:
            SensoryParamsModel(**sensory_data)
        
        error_str = str(exc_info.value)
        assert "acidity" in error_str
        assert "sweetness" in error_str
        assert "confidence" in error_str
        assert "source" in error_str
    
    def test_null_sensory_values(self):
        """Test null sensory parameter values (should be allowed)."""
        sensory_data = {
            "acidity": None,
            "sweetness": None,
            "confidence": None,
            "source": None
        }
        
        sensory = SensoryParamsModel(**sensory_data)
        
        assert sensory.acidity is None
        assert sensory.sweetness is None
        assert sensory.confidence is None
        assert sensory.source is None


class TestImageModel:
    """Test cases for ImageModel."""
    
    def test_valid_image(self):
        """Test valid image creation."""
        image_data = {
            "url": "https://example.com/image.jpg",
            "alt_text": "Test image",
            "order": 0,
            "source_id": "img-001"
        }
        
        image = ImageModel(**image_data)
        
        assert image.url == "https://example.com/image.jpg"
        assert image.alt_text == "Test image"
        assert image.order == 0
        assert image.source_id == "img-001"
    
    def test_minimal_image(self):
        """Test minimal image with only required fields."""
        image_data = {
            "url": "https://example.com/image.jpg"
        }
        
        image = ImageModel(**image_data)
        
        assert image.url == "https://example.com/image.jpg"
        assert image.alt_text is None
        assert image.order is None
        assert image.source_id is None
    
    def test_missing_required_url(self):
        """Test missing required URL field."""
        image_data = {
            "alt_text": "Test image"
        }
        
        with pytest.raises(ValidationError) as exc_info:
            ImageModel(**image_data)
        
        assert "url" in str(exc_info.value)
