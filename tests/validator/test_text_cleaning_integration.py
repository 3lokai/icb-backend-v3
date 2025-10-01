"""
Integration tests for text cleaning and normalization services in ValidatorIntegrationService.
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from src.validator.integration_service import ValidatorIntegrationService
from src.config.validator_config import ValidatorConfig
from src.config.text_cleaning_config import TextCleaningConfig
from src.config.text_normalization_config import TextNormalizationConfig
from src.validator.models import ArtifactModel, ProductModel, VariantModel, NormalizationModel, SourceEnum
from src.validator.artifact_mapper import ArtifactMapper


class TestTextCleaningIntegration:
    """Test text cleaning and normalization integration with ValidatorIntegrationService."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = ValidatorConfig(
            enable_text_cleaning=True,
            text_cleaning_config=TextCleaningConfig(),
            enable_text_normalization=True,
            text_normalization_config=TextNormalizationConfig(),
            enable_image_deduplication=False,
            enable_imagekit_upload=False,
            enable_weight_parsing=False,
            enable_roast_parsing=False,
            enable_process_parsing=False,
            enable_grind_brewing_parsing=False,
            enable_tag_normalization=False,
            enable_notes_extraction=False,
            enable_species_parsing=False,
            enable_variety_parsing=False,
            enable_geographic_parsing=False,
            enable_sensory_parsing=False,
            enable_hash_generation=False
        )
        
        self.integration_service = ValidatorIntegrationService(
            config=self.config,
            supabase_client=Mock()
        )
        
        # Create test artifact with HTML content
        self.test_artifact = ArtifactModel(
            source=SourceEnum.SHOPIFY,
            roaster_domain="test-roaster.com",
            scraped_at=datetime.now(),
            product=ProductModel(
                platform_product_id="test-123",
                title="<h1>Test Coffee</h1> with <em>special</em> features",
                description_html="<p>This is a <strong>great</strong> coffee with <br/>line breaks</p>",
                description_md=None,
                slug="test-coffee",
                source_url="https://example.com/coffee",
                handle="test-coffee",
                variants=[
                    VariantModel(
                        platform_variant_id="variant-1",
                        title="250g bag",
                        sku="TEST-250G",
                        weight_raw="250g",
                        grams=250,
                        currency="USD",
                        price="15.99",
                        in_stock=True,
                        source_raw={}
                    )
                ]
            ),
            normalization=NormalizationModel()
        )
    
    def test_text_cleaning_service_initialization(self):
        """Test that text cleaning service is properly initialized."""
        assert self.integration_service.text_cleaning_service is not None
        assert self.integration_service.text_normalization_service is not None
    
    def test_artifact_mapper_has_text_services(self):
        """Test that ArtifactMapper has access to text services."""
        assert self.integration_service.artifact_mapper.integration_service is not None
        assert hasattr(self.integration_service.artifact_mapper.integration_service, 'text_cleaning_service')
        assert hasattr(self.integration_service.artifact_mapper.integration_service, 'text_normalization_service')
    
    def test_coffee_name_cleaning_and_normalization(self):
        """Test that coffee names are cleaned and normalized."""
        # Map artifact to RPC payloads
        rpc_payloads = self.integration_service.artifact_mapper.map_artifact_to_rpc_payloads(
            artifact=self.test_artifact,
            roaster_id="test-roaster"
        )
        
        coffee_payload = rpc_payloads['coffee']
        
        # Check that cleaned text is included
        assert 'p_title_cleaned' in coffee_payload
        assert 'p_description_cleaned' in coffee_payload
        
        # Check that HTML is removed from title
        title_cleaned = coffee_payload['p_title_cleaned']
        assert '<h1>' not in title_cleaned
        assert '<em>' not in title_cleaned
        assert 'Test Coffee' in title_cleaned
        assert 'special' in title_cleaned
        
        # Check that HTML is removed from description
        description_cleaned = coffee_payload['p_description_cleaned']
        assert '<p>' not in description_cleaned
        assert '<strong>' not in description_cleaned
        assert '<br/>' not in description_cleaned
        assert 'This is a' in description_cleaned
        assert 'great' in description_cleaned
        assert 'coffee' in description_cleaned
    
    def test_text_cleaning_with_smart_quotes(self):
        """Test that smart quotes are standardized."""
        # Create artifact with smart quotes
        artifact_with_quotes = ArtifactModel(
            source=SourceEnum.SHOPIFY,
            roaster_domain="test-roaster.com",
            scraped_at=datetime.now(),
            product=ProductModel(
                platform_product_id="test-quotes",
                title="Coffee \u201cRoasted\u201d with \u2018Special\u2019 care",
                description_html="<p>This coffee has \u201camazing\u201d flavor and \u2018unique\u2019 taste</p>",
                description_md=None,
                slug="test-quotes",
                source_url="https://example.com/quotes",
                handle="test-quotes",
                variants=[
                    VariantModel(
                        platform_variant_id="variant-quotes",
                        title="250g bag",
                        sku="QUOTES-250G",
                        weight_raw="250g",
                        grams=250,
                        currency="USD",
                        price="15.99",
                        in_stock=True,
                        source_raw={}
                    )
                ]
            ),
            normalization=NormalizationModel()
        )
        
        # Map artifact to RPC payloads
        rpc_payloads = self.integration_service.artifact_mapper.map_artifact_to_rpc_payloads(
            artifact=artifact_with_quotes,
            roaster_id="test-roaster"
        )
        
        coffee_payload = rpc_payloads['coffee']
        
        # Check that smart quotes are standardized
        title_cleaned = coffee_payload['p_title_cleaned']
        description_cleaned = coffee_payload['p_description_cleaned']
        
        # Smart quotes should be converted to regular quotes
        assert '"' in title_cleaned  # Regular double quotes
        assert "'" in title_cleaned  # Regular single quotes
        # Check that smart quotes are not present (using Unicode escape sequences)
        assert '\u201c' not in title_cleaned  # No smart double quotes
        assert '\u201d' not in title_cleaned  # No smart double quotes
        assert '\u2018' not in title_cleaned  # No smart single quotes
        assert '\u2019' not in title_cleaned  # No smart single quotes
        
        assert '"' in description_cleaned  # Regular double quotes
        assert "'" in description_cleaned  # Regular single quotes
    
    def test_text_cleaning_disabled(self):
        """Test behavior when text cleaning is disabled."""
        config_no_cleaning = ValidatorConfig(
            enable_text_cleaning=False,
            enable_text_normalization=False,
            enable_image_deduplication=False,
            enable_imagekit_upload=False,
            enable_weight_parsing=False,
            enable_roast_parsing=False,
            enable_process_parsing=False,
            enable_grind_brewing_parsing=False,
            enable_tag_normalization=False,
            enable_notes_extraction=False,
            enable_species_parsing=False,
            enable_variety_parsing=False,
            enable_geographic_parsing=False,
            enable_sensory_parsing=False,
            enable_hash_generation=False
        )
        
        integration_service_no_cleaning = ValidatorIntegrationService(
            config=config_no_cleaning,
            supabase_client=Mock()
        )
        
        # Map artifact to RPC payloads
        rpc_payloads = integration_service_no_cleaning.artifact_mapper.map_artifact_to_rpc_payloads(
            artifact=self.test_artifact,
            roaster_id="test-roaster"
        )
        
        coffee_payload = rpc_payloads['coffee']
        
        # Check that cleaned text fields are still present but contain original text
        assert 'p_title_cleaned' in coffee_payload
        assert 'p_description_cleaned' in coffee_payload
        
        # With consistent HTML-first strategy, both title and description have HTML converted to plain text
        # Title: "<h1>Test Coffee</h1> with <em>special</em> features" -> "Test Coffee with special features"
        expected_title = "Test Coffee with special features"
        assert coffee_payload['p_title_cleaned'] == expected_title
        
        # Description: HTML is converted to plain text even when cleaning is disabled
        expected_description = "This is a great coffee with line breaks"
        assert coffee_payload['p_description_cleaned'] == expected_description
    
    def test_text_cleaning_error_handling(self):
        """Test that text cleaning errors are handled gracefully."""
        # Mock text cleaning service to raise an error
        with patch.object(self.integration_service.text_cleaning_service, 'clean_text') as mock_clean:
            mock_clean.side_effect = Exception("Cleaning failed")
            
            # Map artifact to RPC payloads
            rpc_payloads = self.integration_service.artifact_mapper.map_artifact_to_rpc_payloads(
                artifact=self.test_artifact,
                roaster_id="test-roaster"
            )
            
            coffee_payload = rpc_payloads['coffee']
            
            # Should still have cleaned text fields (using original text as fallback)
            assert 'p_title_cleaned' in coffee_payload
            assert 'p_description_cleaned' in coffee_payload
            
            # Should use HTML-converted text when cleaning fails (consistent HTML-first strategy)
            expected_title = "Test Coffee with special features"  # HTML converted to plain text
            assert coffee_payload['p_title_cleaned'] == expected_title
    
    def test_text_normalization_error_handling(self):
        """Test that text normalization errors are handled gracefully."""
        # Mock text normalization service to raise an error
        with patch.object(self.integration_service.text_normalization_service, 'normalize_text') as mock_normalize:
            mock_normalize.side_effect = Exception("Normalization failed")
            
            # Map artifact to RPC payloads
            rpc_payloads = self.integration_service.artifact_mapper.map_artifact_to_rpc_payloads(
                artifact=self.test_artifact,
                roaster_id="test-roaster"
            )
            
            coffee_payload = rpc_payloads['coffee']
            
            # Should still have cleaned text fields
            assert 'p_title_cleaned' in coffee_payload
            assert 'p_description_cleaned' in coffee_payload
    
    def test_rpc_payload_structure(self):
        """Test that RPC payload has correct structure for text cleaning parameters."""
        rpc_payloads = self.integration_service.artifact_mapper.map_artifact_to_rpc_payloads(
            artifact=self.test_artifact,
            roaster_id="test-roaster"
        )
        
        coffee_payload = rpc_payloads['coffee']
        
        # Check that all required parameters are present
        required_params = [
            'p_bean_species', 'p_name', 'p_slug', 'p_roaster_id', 'p_process',
            'p_process_raw', 'p_roast_level', 'p_roast_level_raw', 'p_roast_style_raw',
            'p_description_md', 'p_direct_buy_url', 'p_platform_product_id'
        ]
        
        for param in required_params:
            assert param in coffee_payload
        
        # Check that text cleaning parameters are present
        assert 'p_title_cleaned' in coffee_payload
        assert 'p_description_cleaned' in coffee_payload
        
        # Check that cleaned text is not None
        assert coffee_payload['p_title_cleaned'] is not None
        assert coffee_payload['p_description_cleaned'] is not None
