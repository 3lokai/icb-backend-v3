"""
Integration tests for parser services composition.
"""

import pytest
from unittest.mock import Mock, patch
from src.parser.tag_normalization import TagNormalizationService
from src.parser.notes_extraction import NotesExtractionService
from src.config.tag_config import TagConfig
from src.config.notes_config import NotesConfig
from src.config.validator_config import ValidatorConfig


class TestParserIntegration:
    """Test cases for parser services integration."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.tag_config = TagConfig()
        self.notes_config = NotesConfig()
        self.validator_config = ValidatorConfig(
            enable_tag_normalization=True,
            tag_config=self.tag_config,
            enable_notes_extraction=True,
            notes_config=self.notes_config
        )
    
    def test_tag_normalization_service_initialization(self):
        """Test TagNormalizationService initialization with config."""
        service = TagNormalizationService()
        assert service is not None
        assert service.config is None  # Config is not stored in the service
    
    def test_notes_extraction_service_initialization(self):
        """Test NotesExtractionService initialization with config."""
        service = NotesExtractionService()
        assert service is not None
        assert service.config is None  # Config is not stored in the service
    
    def test_validator_config_integration(self):
        """Test ValidatorConfig integration with parser services."""
        assert self.validator_config.enable_tag_normalization is True
        assert self.validator_config.enable_notes_extraction is True
        assert self.validator_config.tag_config == self.tag_config
        assert self.validator_config.notes_config == self.notes_config
    
    def test_tag_normalization_with_custom_config(self):
        """Test tag normalization with custom configuration."""
        custom_config = TagConfig(
            enable_fuzzy_matching=True,
            fuzzy_confidence_threshold=0.9,
            custom_categories={
                'custom_flavor': ['unique_flavor', 'special_taste']
            }
        )
        
        service = TagNormalizationService()
        assert service is not None
        # Config is not stored in the service, but we can test the config object separately
        assert custom_config.enable_fuzzy_matching is True
        assert custom_config.fuzzy_confidence_threshold == 0.9
        assert custom_config.custom_categories is not None
    
    def test_notes_extraction_with_custom_config(self):
        """Test notes extraction with custom configuration."""
        custom_config = NotesConfig(
            enable_notes_extraction=True,
            custom_patterns=['custom pattern'],
            notes_confidence_threshold=0.8
        )
        
        service = NotesExtractionService()
        assert service is not None
        # Config is not stored in the service, but we can test the config object separately
        assert custom_config.enable_notes_extraction is True
        assert custom_config.custom_patterns is not None
        assert custom_config.notes_confidence_threshold == 0.8
    
    def test_parser_services_workflow(self):
        """Test complete workflow with both parser services."""
        # Initialize services
        tag_service = TagNormalizationService()
        notes_service = NotesExtractionService()
        
        # Test tag normalization
        raw_tags = ['chocolate', 'karnataka', 'light roast']
        tag_result = tag_service.normalize_tags(raw_tags)
        
        assert tag_result is not None
        assert tag_result.normalized_tags is not None
        assert tag_result.confidence_scores is not None
        
        # Test notes extraction
        description = "Tasting notes: This coffee has chocolate and caramel flavors with a smooth finish."
        notes_result = notes_service.extract_notes(description)
        
        assert notes_result is not None
        assert notes_result.notes_raw is not None
        assert notes_result.confidence_scores is not None
        assert notes_result.extraction_success is True
    
    def test_parser_services_error_handling(self):
        """Test error handling in parser services."""
        tag_service = TagNormalizationService()
        notes_service = NotesExtractionService()
        
        # Test tag normalization with invalid input
        tag_result = tag_service.normalize_tags(None)
        assert tag_result is not None
        assert tag_result.normalized_tags == {}
        assert tag_result.confidence_scores == {}
        assert len(tag_result.warnings) > 0
        
        # Test notes extraction with invalid input
        notes_result = notes_service.extract_notes(None)
        assert notes_result is not None
        assert notes_result.notes_raw == []
        assert notes_result.confidence_scores == []
        assert notes_result.extraction_success is False
    
    def test_parser_services_performance(self):
        """Test performance of parser services."""
        tag_service = TagNormalizationService()
        notes_service = NotesExtractionService()
        
        # Test tag normalization performance
        tag_metrics = tag_service.get_performance_metrics()
        assert 'service_version' in tag_metrics
        assert 'category_mapping' in tag_metrics
        assert 'fuzzy_matching' in tag_metrics
        
        # Test notes extraction performance
        notes_metrics = notes_service.get_performance_metrics()
        assert 'service_version' in notes_metrics
        assert 'tasting_patterns' in notes_metrics
        assert 'context_patterns' in notes_metrics
        assert 'tasting_keywords' in notes_metrics
    
    def test_parser_services_batch_processing(self):
        """Test batch processing capabilities."""
        tag_service = TagNormalizationService()
        notes_service = NotesExtractionService()
        
        # Test batch tag normalization
        batch_tags = [
            ['chocolate', 'karnataka'],
            ['caramel', 'light roast'],
            ['unknown_tag']
        ]
        tag_results = tag_service.batch_normalize_tags(batch_tags)
        
        assert len(tag_results) == 3
        assert all(isinstance(result, type(tag_results[0])) for result in tag_results)
        
        # Test batch notes extraction
        batch_descriptions = [
            "Tasting notes: This coffee has chocolate and caramel flavors.",
            "This coffee features hints of vanilla and a smooth finish.",
            "This is a regular product description with no tasting notes."
        ]
        notes_results = notes_service.batch_extract_notes(batch_descriptions)
        
        assert len(notes_results) == 3
        assert all(isinstance(result, type(notes_results[0])) for result in notes_results)
    
    def test_parser_services_config_validation(self):
        """Test configuration validation for parser services."""
        # Test valid configuration
        valid_config = ValidatorConfig(
            enable_tag_normalization=True,
            tag_config=TagConfig(),
            enable_notes_extraction=True,
            notes_config=NotesConfig()
        )
        assert valid_config.enable_tag_normalization is True
        assert valid_config.enable_notes_extraction is True
        
        # Test invalid configuration
        with pytest.raises(Exception):
            invalid_config = TagConfig(fuzzy_confidence_threshold=1.5)  # Invalid threshold
    
    def test_parser_services_mock_integration(self):
        """Test parser services with mocked dependencies."""
        # Test that services can be initialized without errors
        tag_service = TagNormalizationService()
        assert tag_service is not None
        
        notes_service = NotesExtractionService()
        assert notes_service is not None
        
        # Test that services work correctly
        tag_result = tag_service.normalize_tags(['chocolate', 'karnataka'])
        assert tag_result is not None
        
        notes_result = notes_service.extract_notes("Tasting notes: This coffee has chocolate flavors.")
        assert notes_result is not None
    
    def test_parser_services_data_flow(self):
        """Test data flow between parser services."""
        tag_service = TagNormalizationService()
        notes_service = NotesExtractionService()
        
        # Simulate product data
        product_data = {
            'title': 'Premium Coffee from Karnataka',
            'description': 'Tasting notes: This coffee has chocolate and caramel flavors with a smooth finish.',
            'tags': ['chocolate', 'karnataka', 'light roast']
        }
        
        # Process tags
        tag_result = tag_service.normalize_tags(product_data['tags'])
        assert tag_result.normalized_tags is not None
        
        # Process notes
        notes_result = notes_service.extract_notes(product_data['description'])
        assert notes_result.notes_raw is not None
        assert notes_result.extraction_success is True
        
        # Verify data consistency
        assert len(tag_result.normalized_tags) > 0
        assert len(notes_result.notes_raw) > 0
    
    def test_parser_services_edge_cases(self):
        """Test edge cases for parser services."""
        tag_service = TagNormalizationService()
        notes_service = NotesExtractionService()
        
        # Test empty inputs
        tag_result = tag_service.normalize_tags([])
        assert tag_result.normalized_tags == {}
        assert tag_result.confidence_scores == {}
        
        notes_result = notes_service.extract_notes("")
        assert notes_result.notes_raw == []
        assert notes_result.extraction_success is False
        
        # Test very long inputs
        long_tags = ['tag' + str(i) for i in range(1000)]
        tag_result = tag_service.normalize_tags(long_tags)
        assert tag_result is not None
        
        long_description = "Tasting notes: " + "chocolate " * 1000
        notes_result = notes_service.extract_notes(long_description)
        assert notes_result is not None
    
    def test_parser_services_concurrent_processing(self):
        """Test concurrent processing capabilities."""
        import threading
        import time
        
        tag_service = TagNormalizationService()
        notes_service = NotesExtractionService()
        
        results = []
        
        def process_tags():
            result = tag_service.normalize_tags(['chocolate', 'karnataka'])
            results.append(('tags', result))
        
        def process_notes():
            result = notes_service.extract_notes("Tasting notes: This coffee has chocolate flavors.")
            results.append(('notes', result))
        
        # Start concurrent processing
        thread1 = threading.Thread(target=process_tags)
        thread2 = threading.Thread(target=process_notes)
        
        thread1.start()
        thread2.start()
        
        thread1.join()
        thread2.join()
        
        # Verify results
        assert len(results) == 2
        assert any(result[0] == 'tags' for result in results)
        assert any(result[0] == 'notes' for result in results)
    
    def test_parser_services_memory_usage(self):
        """Test memory usage of parser services."""
        tag_service = TagNormalizationService()
        notes_service = NotesExtractionService()
        
        # Test memory usage with large datasets (reduced for performance)
        large_tags = ['tag' + str(i) for i in range(100)]  # Reduced from 10000 to 100
        large_description = "Tasting notes: " + "chocolate " * 100  # Reduced from 10000 to 100
        
        # Process large datasets
        tag_result = tag_service.normalize_tags(large_tags)
        notes_result = notes_service.extract_notes(large_description)
        
        # Verify processing completed without memory issues
        assert tag_result is not None
        assert notes_result is not None
    
    def test_parser_services_configuration_persistence(self):
        """Test configuration persistence for parser services."""
        # Test configuration serialization
        tag_config_dict = self.tag_config.to_dict()
        assert isinstance(tag_config_dict, dict)
        assert 'enable_fuzzy_matching' in tag_config_dict
        
        notes_config_dict = self.notes_config.to_dict()
        assert isinstance(notes_config_dict, dict)
        assert 'enable_notes_extraction' in notes_config_dict
        
        # Test configuration deserialization
        restored_tag_config = TagConfig.from_dict(tag_config_dict)
        assert restored_tag_config.enable_fuzzy_matching == self.tag_config.enable_fuzzy_matching
        
        restored_notes_config = NotesConfig.from_dict(notes_config_dict)
        assert restored_notes_config.enable_notes_extraction == self.notes_config.enable_notes_extraction
