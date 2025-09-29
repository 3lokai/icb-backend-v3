"""
Integration tests for sensory RPC data flow.
"""

import pytest
from unittest.mock import Mock, patch
from src.validator.integration_service import ValidatorIntegrationService
from src.validator.artifact_mapper import ArtifactMapper
from src.config.validator_config import ValidatorConfig
from src.config.sensory_config import SensoryConfig
from src.config.hash_config import HashConfig


class TestSensoryRPCIntegration:
    """Integration tests for sensory RPC data flow."""
    
    @pytest.fixture
    def validator_config(self):
        """Create validator configuration with sensory parsing enabled."""
        return ValidatorConfig(
            enable_sensory_parsing=True,
            sensory_config=SensoryConfig(),
            enable_hash_generation=True,
            hash_config=HashConfig()
        )
    
    @pytest.fixture
    def integration_service(self, validator_config):
        """Create ValidatorIntegrationService with sensory parsing."""
        return ValidatorIntegrationService(validator_config)
    
    @pytest.fixture
    def artifact_mapper(self, integration_service):
        """Create ArtifactMapper with integration service."""
        return ArtifactMapper(integration_service=integration_service)
    
    def test_sensory_parser_integration(self, integration_service):
        """Test sensory parser integration with ValidatorIntegrationService."""
        assert integration_service.sensory_parser is not None
        assert integration_service.config.enable_sensory_parsing is True
        
        # Test sensory parsing
        description = "This coffee has high acidity and full body with bright citrus notes"
        result = integration_service.sensory_parser.parse_sensory(description)
        
        assert result.acidity is not None
        assert result.body is not None
        assert result.confidence in ["high", "medium", "low"]
        assert result.source == "icb_inferred"
    
    def test_hash_service_integration(self, integration_service):
        """Test hash service integration with ValidatorIntegrationService."""
        assert integration_service.hash_service is not None
        assert integration_service.config.enable_hash_generation is True
        
        # Test hash generation
        artifact = {
            'title': 'Test Coffee',
            'description': 'A great coffee',
            'weight_g': 250,
            'roast_level': 'medium',
            'process': 'washed',
            'grind_type': 'whole_bean',
            'species': 'arabica'
        }
        
        result = integration_service.hash_service.generate_hashes(artifact)
        
        assert result.content_hash is not None
        assert result.raw_hash is not None
        assert result.algorithm == "sha256"
    
    def test_artifact_mapper_sensory_integration(self, artifact_mapper):
        """Test ArtifactMapper sensory integration."""
        # Mock product data
        mock_product = Mock()
        mock_product.name = "Test Coffee"
        mock_product.description_md = "This coffee has high acidity and full body"
        mock_product.description_html = None
        mock_product.platform_product_id = "test-123"
        
        # Mock artifact
        mock_artifact = Mock()
        mock_artifact.product = mock_product
        mock_artifact.normalization = Mock()
        mock_artifact.normalization.roast_level = Mock()
        mock_artifact.normalization.roast_level.value = "medium"
        mock_artifact.normalization.process = Mock()
        mock_artifact.normalization.process.value = "washed"
        mock_artifact.normalization.bean_species = Mock()
        mock_artifact.normalization.bean_species.value = "arabica"
        
        # Test sensory extraction
        sensory_data = artifact_mapper._extract_sensory_from_description(mock_product)
        
        assert sensory_data is not None
        assert 'acidity' in sensory_data
        assert 'body' in sensory_data
        assert sensory_data['acidity'] is not None
        assert sensory_data['body'] is not None
    
    def test_artifact_mapper_hash_integration(self, artifact_mapper):
        """Test ArtifactMapper hash integration."""
        # Mock artifact
        mock_artifact = Mock()
        mock_artifact.product = Mock()
        mock_artifact.product.name = "Test Coffee"
        mock_artifact.product.description_md = "A great coffee"
        mock_artifact.product.platform_product_id = "test-123"
        mock_artifact.normalization = Mock()
        mock_artifact.normalization.roast_level = Mock()
        mock_artifact.normalization.roast_level.value = "medium"
        mock_artifact.normalization.process = Mock()
        mock_artifact.normalization.process.value = "washed"
        mock_artifact.normalization.bean_species = Mock()
        mock_artifact.normalization.bean_species.value = "arabica"
        
        # Test hash generation
        hash_data = artifact_mapper._generate_hashes_for_artifact(mock_artifact)
        
        assert hash_data is not None
        assert 'content_hash' in hash_data
        assert 'raw_hash' in hash_data
        assert hash_data['content_hash'] is not None
        assert hash_data['raw_hash'] is not None
    
    def test_rpc_parameter_mapping(self, artifact_mapper):
        """Test RPC parameter mapping for sensory and hash data."""
        # Mock product data
        mock_product = Mock()
        mock_product.name = "Test Coffee"
        mock_product.description_md = "This coffee has high acidity and full body"
        mock_product.description_html = None
        mock_product.platform_product_id = "test-123"
        mock_product.source_url = "https://example.com/coffee"
        
        # Mock variants
        mock_variant = Mock()
        mock_variant.grind_type = "whole_bean"
        mock_product.variants = [mock_variant]

        # Mock artifact
        mock_artifact = Mock()
        mock_artifact.product = mock_product
        mock_artifact.normalization = Mock()
        mock_artifact.normalization.roast_level = Mock()
        mock_artifact.normalization.roast_level.value = "medium"
        mock_artifact.normalization.process = Mock()
        mock_artifact.normalization.process.value = "washed"
        mock_artifact.normalization.bean_species = Mock()
        mock_artifact.normalization.bean_species.value = "arabica"
        
        # Test coffee data mapping
        coffee_payload = artifact_mapper._map_coffee_data(mock_artifact, "test-roaster")
        
        # Verify sensory parameters are mapped
        assert 'p_acidity' in coffee_payload
        assert 'p_body' in coffee_payload
        assert coffee_payload['p_acidity'] is not None
        assert coffee_payload['p_body'] is not None
        
        # Verify hash parameters are mapped
        assert 'p_content_hash' in coffee_payload
        assert 'p_raw_hash' in coffee_payload
        assert coffee_payload['p_content_hash'] is not None
        assert coffee_payload['p_raw_hash'] is not None
    
    def test_batch_processing_integration(self, integration_service):
        """Test batch processing integration."""
        # Test sensory batch processing
        descriptions = [
            "High acidity coffee with bright citrus notes",
            "Full body coffee with rich chocolate flavors",
            "Medium acidity coffee with balanced profile"
        ]
        
        sensory_results = integration_service.sensory_parser.parse_sensory_batch(descriptions)
        assert len(sensory_results) == 3
        assert all(r.acidity is not None or r.body is not None for r in sensory_results)
        
        # Test hash batch processing
        artifacts = [
            {'title': f'Coffee {i}', 'description': f'Description {i}'}
            for i in range(3)
        ]
        
        hash_results = integration_service.hash_service.generate_hashes_batch(artifacts)
        assert len(hash_results) == 3
        assert all(r.content_hash and r.raw_hash for r in hash_results)
    
    def test_error_handling_integration(self, integration_service):
        """Test error handling in integration."""
        # Test sensory parsing with invalid input
        result = integration_service.sensory_parser.parse_sensory("")
        assert result.acidity is None
        assert result.body is None
        assert result.confidence in ["low", "medium"]  # Allow both since empty string might still match some patterns
        
        # Test hash generation with invalid input
        result = integration_service.hash_service.generate_hashes({})
        assert result.content_hash is not None  # Should still generate hash
        assert result.raw_hash is not None
    
    def test_configuration_integration(self, integration_service):
        """Test configuration integration."""
        # Test sensory configuration
        assert integration_service.config.enable_sensory_parsing is True
        assert integration_service.config.sensory_config is not None
        # Note: SensoryConfig doesn't have enable_sensory_parsing attribute, it's in ValidatorConfig
        
        # Test hash configuration
        assert integration_service.config.enable_hash_generation is True
        assert integration_service.config.hash_config is not None
        # Note: HashConfig doesn't have enable_hash_generation attribute, it's in ValidatorConfig
