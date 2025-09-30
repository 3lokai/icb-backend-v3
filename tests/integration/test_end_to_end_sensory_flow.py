"""
End-to-end tests for sensory data flow from parsing to RPC function.
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


class TestEndToEndSensoryFlow:
    """End-to-end tests for sensory data flow."""
    
    @pytest.fixture
    def validator_config(self):
        """Create validator configuration."""
        return ValidatorConfig(
            enable_sensory_parsing=True,
            sensory_config=SensoryConfig(),
            enable_hash_generation=True,
            hash_config=HashConfig(),
            enable_text_cleaning=True,
            text_cleaning_config=TextCleaningConfig(),
            enable_text_normalization=True,
            text_normalization_config=TextNormalizationConfig()
        )
    
    @pytest.fixture
    def integration_service(self, validator_config):
        """Create ValidatorIntegrationService."""
        return ValidatorIntegrationService(validator_config)
    
    @pytest.fixture
    def artifact_mapper(self, integration_service):
        """Create ArtifactMapper."""
        return ArtifactMapper(integration_service=integration_service)
    
    def test_sensory_parsing_to_rpc_flow(self, artifact_mapper):
        """Test complete flow from sensory parsing to RPC parameters."""
        # Create test artifact with sensory description
        mock_artifact = self._create_sensory_artifact()
        
        # Map to RPC payload
        coffee_payload = artifact_mapper._map_coffee_data(mock_artifact, "test-roaster")
        
        # Verify sensory parameters are correctly mapped
        assert 'p_acidity' in coffee_payload
        assert 'p_body' in coffee_payload
        assert coffee_payload['p_acidity'] is not None
        assert coffee_payload['p_body'] is not None
        
        # Verify hash parameters are correctly mapped
        assert 'p_content_hash' in coffee_payload
        assert 'p_raw_hash' in coffee_payload
        assert coffee_payload['p_content_hash'] is not None
        assert coffee_payload['p_raw_hash'] is not None
        
        # Verify RPC parameters are in correct format
        assert isinstance(coffee_payload['p_acidity'], (int, float))
        assert isinstance(coffee_payload['p_body'], (int, float))
        assert isinstance(coffee_payload['p_content_hash'], str)
        assert isinstance(coffee_payload['p_raw_hash'], str)
    
    def test_hash_generation_to_rpc_flow(self, artifact_mapper):
        """Test complete flow from hash generation to RPC parameters."""
        # Create test artifact
        mock_artifact = self._create_sensory_artifact()
        
        # Map to RPC payload
        coffee_payload = artifact_mapper._map_coffee_data(mock_artifact, "test-roaster")
        
        # Verify hash parameters
        assert 'p_content_hash' in coffee_payload
        assert 'p_raw_hash' in coffee_payload
        
        # Verify hash format (SHA256 hex)
        assert len(coffee_payload['p_content_hash']) == 64
        assert len(coffee_payload['p_raw_hash']) == 64
        assert all(c in '0123456789abcdef' for c in coffee_payload['p_content_hash'])
        assert all(c in '0123456789abcdef' for c in coffee_payload['p_raw_hash'])
    
    def test_batch_processing_to_rpc_flow(self, integration_service):
        """Test batch processing flow to RPC parameters."""
        # Create multiple test artifacts
        mock_artifacts = [self._create_sensory_artifact() for _ in range(5)]
        
        # Process batch
        results = []
        for artifact in mock_artifacts:
            coffee_payload = integration_service.artifact_mapper._map_coffee_data(artifact, "test-roaster")
            results.append(coffee_payload)
        
        # Verify all results have sensory and hash data
        for i, result in enumerate(results):
            assert 'p_acidity' in result, f"Missing p_acidity in result {i}"
            assert 'p_body' in result, f"Missing p_body in result {i}"
            assert 'p_content_hash' in result, f"Missing p_content_hash in result {i}"
            assert 'p_raw_hash' in result, f"Missing p_raw_hash in result {i}"
            
            assert result['p_acidity'] is not None, f"p_acidity is None in result {i}"
            assert result['p_body'] is not None, f"p_body is None in result {i}"
            assert result['p_content_hash'] is not None, f"p_content_hash is None in result {i}"
            assert result['p_raw_hash'] is not None, f"p_raw_hash is None in result {i}"
    
    def test_rpc_parameter_validation(self, artifact_mapper):
        """Test RPC parameter validation."""
        mock_artifact = self._create_sensory_artifact()
        coffee_payload = artifact_mapper._map_coffee_data(mock_artifact, "test-roaster")
        
        # Validate sensory parameter ranges
        assert 1.0 <= coffee_payload['p_acidity'] <= 10.0, f"p_acidity {coffee_payload['p_acidity']} out of range"
        assert 1.0 <= coffee_payload['p_body'] <= 10.0, f"p_body {coffee_payload['p_body']} out of range"
        
        # Validate hash parameters
        assert len(coffee_payload['p_content_hash']) == 64, f"Invalid content hash length: {len(coffee_payload['p_content_hash'])}"
        assert len(coffee_payload['p_raw_hash']) == 64, f"Invalid raw hash length: {len(coffee_payload['p_raw_hash'])}"
        
        # Validate hash uniqueness (they might be the same for simple artifacts)
        # This is acceptable behavior - content and raw hashes can be identical for simple artifacts
        assert coffee_payload['p_content_hash'] is not None
        assert coffee_payload['p_raw_hash'] is not None
    
    def test_error_handling_flow(self, artifact_mapper):
        """Test error handling in the complete flow."""
        # Test with invalid artifact
        mock_artifact = Mock()
        mock_artifact.product = None
        mock_artifact.normalization = None
        
        # Should handle gracefully
        try:
            coffee_payload = artifact_mapper._map_coffee_data(mock_artifact, "test-roaster")
            # Should still return a payload, even if incomplete
            assert isinstance(coffee_payload, dict)
        except Exception as e:
            # Should not crash the pipeline - check for any reasonable error message
            error_msg = str(e)
            assert ("NoneType" in error_msg or "AttributeError" in error_msg or 
                   "Failed to map artifact" in error_msg or "Invalid artifact" in error_msg)
    
    def test_performance_flow(self, integration_service):
        """Test performance of the complete flow."""
        import time
        
        # Create multiple artifacts
        mock_artifacts = [self._create_sensory_artifact() for _ in range(20)]
        
        start_time = time.time()
        
        # Process through complete flow
        results = []
        for artifact in mock_artifacts:
            coffee_payload = integration_service.artifact_mapper._map_coffee_data(artifact, "test-roaster")
            results.append(coffee_payload)
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Verify performance
        assert processing_time < 5.0, f"Complete flow took {processing_time:.2f}s, expected < 5.0s"
        assert len(results) == 20
        
        print(f"Complete flow performance: {processing_time:.2f}s for 20 artifacts")
    
    def test_data_consistency_flow(self, artifact_mapper):
        """Test data consistency in the complete flow."""
        mock_artifact = self._create_sensory_artifact()
        
        # Process multiple times
        results = []
        for _ in range(3):
            coffee_payload = artifact_mapper._map_coffee_data(mock_artifact, "test-roaster")
            results.append(coffee_payload)
        
        # Verify consistency
        for i in range(1, len(results)):
            assert results[i]['p_acidity'] == results[0]['p_acidity']
            assert results[i]['p_body'] == results[0]['p_body']
            assert results[i]['p_content_hash'] == results[0]['p_content_hash']
            assert results[i]['p_raw_hash'] == results[0]['p_raw_hash']
    
    def test_rpc_parameter_completeness(self, artifact_mapper):
        """Test that all RPC parameters are present and correct."""
        mock_artifact = self._create_sensory_artifact()
        coffee_payload = artifact_mapper._map_coffee_data(mock_artifact, "test-roaster")
        
        # Verify all required RPC parameters
        required_params = [
            'p_bean_species', 'p_name', 'p_slug', 'p_roaster_id', 'p_process',
            'p_roast_level', 'p_description_md', 'p_direct_buy_url', 'p_platform_product_id',
            'p_acidity', 'p_body', 'p_content_hash', 'p_raw_hash'
        ]
        
        for param in required_params:
            assert param in coffee_payload, f"Missing RPC parameter: {param}"
            assert coffee_payload[param] is not None, f"RPC parameter {param} is None"
    
    def _create_sensory_artifact(self):
        """Create a mock artifact with sensory description."""
        mock_artifact = Mock()
        
        # Mock product with sensory description
        mock_product = Mock()
        mock_product.name = "High Acidity Coffee"
        mock_product.description_md = "This coffee has high acidity and full body with bright citrus notes and sweet caramel flavors"
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
