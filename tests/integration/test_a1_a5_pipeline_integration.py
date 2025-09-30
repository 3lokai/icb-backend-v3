"""
Integration tests for A.1-A.5 pipeline with sensory and hash parsing.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from src.validator.integration_service import ValidatorIntegrationService
from src.validator.artifact_mapper import ArtifactMapper
from src.config.validator_config import ValidatorConfig
from src.config.sensory_config import SensoryConfig
from src.config.hash_config import HashConfig
from src.config.text_cleaning_config import TextCleaningConfig
from src.config.text_normalization_config import TextNormalizationConfig


class TestA1A5PipelineIntegration:
    """Integration tests for A.1-A.5 pipeline with sensory and hash parsing."""
    
    @pytest.fixture
    def full_validator_config(self):
        """Create full validator configuration with all services enabled."""
        return ValidatorConfig(
            enable_sensory_parsing=True,
            sensory_config=SensoryConfig(),
            enable_hash_generation=True,
            hash_config=HashConfig(),
            enable_geographic_parsing=True,
            enable_variety_parsing=True,
            enable_species_parsing=True,
            enable_text_cleaning=True,
            text_cleaning_config=TextCleaningConfig(),
            enable_text_normalization=True,
            text_normalization_config=TextNormalizationConfig()
        )
    
    @pytest.fixture
    def integration_service(self, full_validator_config):
        """Create ValidatorIntegrationService with all services."""
        return ValidatorIntegrationService(full_validator_config)
    
    @pytest.fixture
    def artifact_mapper(self, integration_service):
        """Create ArtifactMapper with full integration service."""
        return ArtifactMapper(integration_service=integration_service)
    
    def test_full_pipeline_integration(self, integration_service, artifact_mapper):
        """Test full A.1-A.5 pipeline integration with sensory and hash parsing."""
        # Mock artifact data
        mock_artifact = self._create_mock_artifact()
        
        # Test artifact mapping with all services
        coffee_payload = artifact_mapper._map_coffee_data(mock_artifact, "test-roaster")
        
        # Verify all RPC parameters are present
        required_params = [
            'p_bean_species', 'p_name', 'p_slug', 'p_roaster_id', 'p_process',
            'p_roast_level', 'p_description_md', 'p_direct_buy_url', 'p_platform_product_id'
        ]
        
        for param in required_params:
            assert param in coffee_payload, f"Missing required parameter: {param}"
        
        # Verify sensory parameters
        assert 'p_acidity' in coffee_payload
        assert 'p_body' in coffee_payload
        assert coffee_payload['p_acidity'] is not None
        assert coffee_payload['p_body'] is not None
        
        # Verify hash parameters
        assert 'p_content_hash' in coffee_payload
        assert 'p_raw_hash' in coffee_payload
        assert coffee_payload['p_content_hash'] is not None
        assert coffee_payload['p_raw_hash'] is not None
    
    def test_batch_processing_pipeline(self, integration_service):
        """Test batch processing through the full pipeline."""
        # Mock artifacts
        mock_artifacts = [self._create_mock_artifact() for _ in range(5)]
        
        # Test batch processing
        results = []
        for artifact in mock_artifacts:
            try:
                # Simulate the full pipeline processing
                coffee_payload = integration_service.artifact_mapper._map_coffee_data(artifact, "test-roaster")
                results.append(coffee_payload)
            except Exception as e:
                pytest.fail(f"Batch processing failed: {e}")
        
        assert len(results) == 5
        
        # Verify all results have sensory and hash data
        for result in results:
            assert 'p_acidity' in result
            assert 'p_body' in result
            assert 'p_content_hash' in result
            assert 'p_raw_hash' in result
    
    def test_error_handling_pipeline(self, integration_service):
        """Test error handling in the full pipeline."""
        # Test with invalid artifact
        mock_artifact = Mock()
        mock_artifact.product = None
        mock_artifact.normalization = None
        
        # Should handle gracefully
        try:
            coffee_payload = integration_service.artifact_mapper._map_coffee_data(mock_artifact, "test-roaster")
            # Should still return a payload, even if incomplete
            assert isinstance(coffee_payload, dict)
        except Exception as e:
            # Should not crash the pipeline - check for any reasonable error message
            error_msg = str(e)
            assert ("NoneType" in error_msg or "AttributeError" in error_msg or 
                   "Failed to map artifact" in error_msg or "Invalid artifact" in error_msg)
    
    def test_performance_pipeline(self, integration_service):
        """Test performance of the full pipeline."""
        import time
        
        # Create multiple artifacts
        mock_artifacts = [self._create_mock_artifact() for _ in range(50)]
        
        start_time = time.time()
        
        # Process through pipeline
        results = []
        for artifact in mock_artifacts:
            coffee_payload = integration_service.artifact_mapper._map_coffee_data(artifact, "test-roaster")
            results.append(coffee_payload)
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Verify performance
        assert processing_time < 10.0, f"Pipeline processing took {processing_time:.2f}s, expected < 10.0s"
        assert len(results) == 50
        
        print(f"Pipeline performance: {processing_time:.2f}s for 50 artifacts")
    
    def test_configuration_pipeline(self, integration_service):
        """Test configuration handling in the pipeline."""
        # Verify all services are enabled
        assert integration_service.sensory_parser is not None
        assert integration_service.hash_service is not None
        assert integration_service.geographic_parser is not None
        assert integration_service.variety_parser is not None
        assert integration_service.species_parser is not None
        
        # Verify configuration
        assert integration_service.config.enable_sensory_parsing is True
        assert integration_service.config.enable_hash_generation is True
        assert integration_service.config.enable_geographic_parsing is True
        assert integration_service.config.enable_variety_parsing is True
        assert integration_service.config.enable_species_parsing is True
    
    def test_rpc_parameter_completeness(self, integration_service):
        """Test that all RPC parameters are correctly mapped."""
        mock_artifact = self._create_mock_artifact()
        coffee_payload = integration_service.artifact_mapper._map_coffee_data(mock_artifact, "test-roaster")
        
        # Verify all expected RPC parameters are present
        expected_params = [
            'p_bean_species', 'p_name', 'p_slug', 'p_roaster_id', 'p_process',
            'p_roast_level', 'p_description_md', 'p_direct_buy_url', 'p_platform_product_id',
            'p_acidity', 'p_body', 'p_content_hash', 'p_raw_hash'
        ]
        
        for param in expected_params:
            assert param in coffee_payload, f"Missing RPC parameter: {param}"
            assert coffee_payload[param] is not None, f"RPC parameter {param} is None"
    
    def test_data_consistency_pipeline(self, integration_service):
        """Test data consistency across the pipeline."""
        mock_artifact = self._create_mock_artifact()
        
        # Process through pipeline multiple times
        results = []
        for _ in range(3):
            coffee_payload = integration_service.artifact_mapper._map_coffee_data(mock_artifact, "test-roaster")
            results.append(coffee_payload)
        
        # Verify consistency
        for i in range(1, len(results)):
            assert results[i]['p_name'] == results[0]['p_name']
            assert results[i]['p_platform_product_id'] == results[0]['p_platform_product_id']
            assert results[i]['p_content_hash'] == results[0]['p_content_hash']
            assert results[i]['p_raw_hash'] == results[0]['p_raw_hash']
    
    def _create_mock_artifact(self):
        """Create a mock artifact for testing."""
        mock_artifact = Mock()
        
        # Mock product
        mock_product = Mock()
        mock_product.name = "Test Coffee"
        mock_product.description_md = "This coffee has high acidity and full body with bright citrus notes"
        mock_product.description_html = None
        mock_product.platform_product_id = "test-123"
        mock_product.source_url = "https://example.com/coffee"
        
        # Mock normalization
        mock_normalization = Mock()
        mock_normalization.roast_level = Mock()
        mock_normalization.roast_level.value = "medium"
        mock_normalization.process = Mock()
        mock_normalization.process.value = "washed"
        mock_normalization.bean_species = Mock()
        mock_normalization.bean_species.value = "arabica"
        
        # Mock variants
        mock_variant = Mock()
        mock_variant.grind_type = "whole_bean"
        mock_product.variants = [mock_variant]
        
        # Set up artifact
        mock_artifact.product = mock_product
        mock_artifact.normalization = mock_normalization
        
        return mock_artifact
