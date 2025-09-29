"""
Integration tests for bean species parser with validator integration.
"""

import pytest
from unittest.mock import Mock, patch
from src.parser.species_parser import BeanSpeciesParserService, SpeciesConfig
from src.validator.integration_service import ValidatorIntegrationService
from src.validator.artifact_mapper import ArtifactMapper
from src.config.validator_config import ValidatorConfig
from src.config.species_config import SpeciesConfig as SpeciesConfigClass


class TestSpeciesParserIntegration:
    """Integration tests for species parser with validator components."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.species_config = SpeciesConfigClass(
            confidence_threshold=0.7,
            enable_blend_detection=True,
            enable_chicory_detection=True,
            enable_ratio_detection=True,
            batch_size=100
        )
        
        self.validator_config = ValidatorConfig(
            enable_species_parsing=True,
            species_config=self.species_config
        )
        
        # Mock supabase client
        self.mock_supabase_client = Mock()
        
        # Create integration service
        self.integration_service = ValidatorIntegrationService(
            config=self.validator_config,
            supabase_client=self.mock_supabase_client
        )
    
    def test_integration_service_species_parser_initialization(self):
        """Test that species parser is properly initialized in integration service."""
        assert self.integration_service.species_parser is not None
        assert isinstance(self.integration_service.species_parser, BeanSpeciesParserService)
        assert self.integration_service.species_parser.config.confidence_threshold == 0.7
    
    def test_integration_service_species_parser_disabled(self):
        """Test that species parser is None when disabled."""
        validator_config = ValidatorConfig(enable_species_parsing=False)
        integration_service = ValidatorIntegrationService(
            config=validator_config,
            supabase_client=self.mock_supabase_client
        )
        
        assert integration_service.species_parser is None
    
    def test_artifact_mapper_species_parsing(self):
        """Test species parsing in artifact mapper."""
        # Mock artifact with product data
        mock_artifact = Mock()
        mock_artifact.product.title = "100% Arabica Coffee"
        mock_artifact.product.description = "Pure arabica beans from Ethiopia"
        mock_artifact.normalization = None  # No existing species data
        
        # Create artifact mapper with integration service
        artifact_mapper = ArtifactMapper(integration_service=self.integration_service)
        
        # Test species mapping
        species = artifact_mapper._map_bean_species(
            normalization=None,
            product=mock_artifact.product
        )
        
        assert species == 'arabica'
    
    def test_artifact_mapper_species_parsing_with_existing_data(self):
        """Test that existing species data takes precedence over parsing."""
        # Mock artifact with existing species data
        mock_normalization = Mock()
        mock_normalization.bean_species.value = 'robusta'
        
        mock_artifact = Mock()
        mock_artifact.product.title = "100% Arabica Coffee"
        mock_artifact.product.description = "Pure arabica beans"
        mock_artifact.normalization = mock_normalization
        
        # Create artifact mapper
        artifact_mapper = ArtifactMapper(integration_service=self.integration_service)
        
        # Test species mapping - should use existing data
        species = artifact_mapper._map_bean_species(
            normalization=mock_normalization,
            product=mock_artifact.product
        )
        
        assert species == 'robusta'  # Should use existing data, not parse
    
    def test_artifact_mapper_species_parsing_low_confidence(self):
        """Test that low confidence parsing results are ignored."""
        # Mock artifact with ambiguous content
        mock_artifact = Mock()
        mock_artifact.product.title = "Coffee"
        mock_artifact.product.description = "Premium coffee beans"
        mock_artifact.normalization = None
        
        # Create artifact mapper
        artifact_mapper = ArtifactMapper(integration_service=self.integration_service)
        
        # Test species mapping - should return None due to low confidence
        species = artifact_mapper._map_bean_species(
            normalization=None,
            product=mock_artifact.product
        )
        
        assert species is None  # Should be None due to low confidence
    
    def test_artifact_mapper_species_parsing_error_handling(self):
        """Test error handling in species parsing."""
        # Mock artifact with problematic content
        mock_artifact = Mock()
        mock_artifact.product.title = None
        mock_artifact.product.description = None
        mock_artifact.normalization = None
        
        # Create artifact mapper
        artifact_mapper = ArtifactMapper(integration_service=self.integration_service)
        
        # Test species mapping - should handle errors gracefully
        species = artifact_mapper._map_bean_species(
            normalization=None,
            product=mock_artifact.product
        )
        
        assert species is None  # Should be None due to error
    
    def test_batch_processing_integration(self):
        """Test batch processing with integration service."""
        # Mock products
        products = [
            {'title': '100% Arabica', 'description': 'Pure arabica beans'},
            {'title': 'Robusta Coffee', 'description': 'Strong robusta beans'},
            {'title': 'Coffee Blend', 'description': 'Arabica and robusta blend'},
            {'title': 'Chicory Coffee', 'description': 'Arabica with chicory'}
        ]
        
        # Test batch parsing
        results = self.integration_service.species_parser.batch_parse_species(products)
        
        assert len(results) == 4
        assert results[0].species == 'arabica'
        assert results[1].species == 'robusta'
        assert results[2].species == 'blend'
        assert results[3].species == 'arabica_chicory'
    
    def test_species_parser_configuration_integration(self):
        """Test that species parser configuration is properly integrated."""
        # Test custom configuration
        custom_species_config = SpeciesConfigClass(
            confidence_threshold=0.9,
            enable_blend_detection=False,
            batch_size=50
        )
        
        validator_config = ValidatorConfig(
            enable_species_parsing=True,
            species_config=custom_species_config
        )
        
        integration_service = ValidatorIntegrationService(
            config=validator_config,
            supabase_client=self.mock_supabase_client
        )
        
        assert integration_service.species_parser.config.confidence_threshold == 0.9
        assert integration_service.species_parser.config.enable_blend_detection is False
        assert integration_service.species_parser.config.batch_size == 50
    
    def test_species_enum_validation_integration(self):
        """Test species enum validation in integration context."""
        # Test valid species
        valid_species = [
            'arabica', 'robusta', 'liberica', 'blend',
            'arabica_80_robusta_20', 'arabica_chicory', 'filter_coffee_mix'
        ]
        
        for species in valid_species:
            assert self.integration_service.species_parser.validate_species_enum(species)
        
        # Test invalid species
        assert not self.integration_service.species_parser.validate_species_enum('invalid')
    
    def test_performance_metrics_integration(self):
        """Test performance metrics in integration context."""
        metrics = self.integration_service.species_parser.get_performance_metrics()
        
        assert 'parser_version' in metrics
        assert 'supported_species' in metrics
        assert 'pattern_count' in metrics
        assert 'confidence_threshold' in metrics
        assert 'batch_size' in metrics
        
        # Verify configuration values
        assert metrics['confidence_threshold'] == 0.7
        assert metrics['batch_size'] == 100
    
    def test_species_parser_without_integration_service(self):
        """Test species parser without integration service."""
        # Create artifact mapper without integration service
        artifact_mapper = ArtifactMapper()
        
        # Mock artifact
        mock_artifact = Mock()
        mock_artifact.product.title = "100% Arabica Coffee"
        mock_artifact.product.description = "Pure arabica beans"
        mock_artifact.normalization = None
        
        # Test species mapping - should return None without integration service
        species = artifact_mapper._map_bean_species(
            normalization=None,
            product=mock_artifact.product
        )
        
        assert species is None
    
    def test_species_parser_error_recovery(self):
        """Test error recovery in species parsing."""
        # Mock integration service with broken species parser
        mock_integration_service = Mock()
        mock_integration_service.species_parser = Mock()
        mock_integration_service.species_parser.parse_species.side_effect = Exception("Parser error")
        
        # Create artifact mapper
        artifact_mapper = ArtifactMapper(integration_service=mock_integration_service)
        
        # Mock artifact
        mock_artifact = Mock()
        mock_artifact.product.title = "100% Arabica Coffee"
        mock_artifact.product.description = "Pure arabica beans"
        mock_artifact.normalization = None
        
        # Test species mapping - should handle error gracefully
        species = artifact_mapper._map_bean_species(
            normalization=None,
            product=mock_artifact.product
        )
        
        assert species is None  # Should be None due to error
    
    def test_species_parser_confidence_threshold_integration(self):
        """Test confidence threshold integration."""
        # Test with high confidence threshold
        high_confidence_config = SpeciesConfigClass(confidence_threshold=0.95)
        validator_config = ValidatorConfig(
            enable_species_parsing=True,
            species_config=high_confidence_config
        )
        
        integration_service = ValidatorIntegrationService(
            config=validator_config,
            supabase_client=self.mock_supabase_client
        )
        
        # Mock artifact with ambiguous content
        mock_artifact = Mock()
        mock_artifact.product.title = "Coffee"
        mock_artifact.product.description = "Premium coffee"
        mock_artifact.normalization = None
        
        # Create artifact mapper
        artifact_mapper = ArtifactMapper(integration_service=integration_service)
        
        # Test species mapping - should return None due to high threshold
        species = artifact_mapper._map_bean_species(
            normalization=None,
            product=mock_artifact.product
        )
        
        assert species is None  # Should be None due to high confidence threshold

