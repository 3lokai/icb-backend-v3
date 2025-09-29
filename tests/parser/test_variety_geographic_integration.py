"""
Integration tests for Indian Coffee Variety and Geographic Parsing Services
"""

import pytest
import json
from pathlib import Path
from src.parser.variety_extraction import VarietyExtractionService
from src.parser.geographic_parser import GeographicParserService
from src.config.variety_config import VarietyConfig
from src.config.geographic_config import GeographicConfig


class TestVarietyGeographicIntegration:
    """Integration tests for variety and geographic parsing services."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.variety_service = VarietyExtractionService()
        self.geographic_service = GeographicParserService()
        
        # Load test fixtures
        self.fixtures_path = Path(__file__).parent / "fixtures" / "indian_variety_samples.json"
        with open(self.fixtures_path, 'r', encoding='utf-8') as f:
            self.test_data = json.load(f)
    
    def test_variety_extraction_integration(self):
        """Test variety extraction with real Indian coffee samples."""
        variety_samples = self.test_data.get('variety_samples', [])
        
        for sample in variety_samples:
            description = sample['description']
            expected_varieties = sample.get('expected_varieties', [])
            
            result = self.variety_service.extract_varieties(description)
            
            assert isinstance(result, type(result))
            assert hasattr(result, 'varieties')
            assert hasattr(result, 'confidence_scores')
            assert hasattr(result, 'warnings')
            
            # Check if expected varieties are found
            if expected_varieties:
                for expected_variety in expected_varieties:
                    assert expected_variety in result.varieties, f"Expected variety '{expected_variety}' not found in {result.varieties} for description: {description}"
    
    def test_geographic_parsing_integration(self):
        """Test geographic parsing with real Indian coffee samples."""
        geographic_samples = self.test_data.get('geographic_samples', [])
        
        for sample in geographic_samples:
            description = sample['description']
            expected_region = sample.get('expected_region')
            expected_state = sample.get('expected_state')
            expected_country = sample.get('expected_country')
            expected_altitude = sample.get('expected_altitude')
            
            result = self.geographic_service.parse_geographic(description)
            
            assert isinstance(result, type(result))
            assert hasattr(result, 'region')
            assert hasattr(result, 'country')
            assert hasattr(result, 'state')
            assert hasattr(result, 'estate')
            assert hasattr(result, 'altitude')
            assert hasattr(result, 'confidence')
            assert hasattr(result, 'warnings')
            
            # Check expected values
            if expected_region:
                assert result.region == expected_region, f"Expected region '{expected_region}' but got '{result.region}' for description: {description}"
            if expected_state:
                assert result.state == expected_state, f"Expected state '{expected_state}' but got '{result.state}' for description: {description}"
            if expected_country:
                assert result.country == expected_country, f"Expected country '{expected_country}' but got '{result.country}' for description: {description}"
            if expected_altitude:
                assert result.altitude == expected_altitude, f"Expected altitude '{expected_altitude}' but got '{result.altitude}' for description: {description}"
    
    def test_estate_parsing_integration(self):
        """Test estate parsing with real Indian coffee samples."""
        estate_samples = self.test_data.get('estate_samples', [])
        
        for sample in estate_samples:
            description = sample['description']
            expected_estate = sample.get('expected_estate')
            expected_region = sample.get('expected_region')
            
            result = self.geographic_service.parse_geographic(description)
            
            assert isinstance(result, type(result))
            
            # Check expected estate
            if expected_estate:
                assert result.estate == expected_estate, f"Expected estate '{expected_estate}' but got '{result.estate}' for description: {description}"
            if expected_region:
                assert result.region == expected_region, f"Expected region '{expected_region}' but got '{result.region}' for description: {description}"
    
    def test_altitude_parsing_integration(self):
        """Test altitude parsing with real Indian coffee samples."""
        altitude_samples = self.test_data.get('altitude_samples', [])
        
        for sample in altitude_samples:
            description = sample['description']
            expected_altitude = sample.get('expected_altitude')
            
            result = self.geographic_service.parse_geographic(description)
            
            assert isinstance(result, type(result))
            
            # Check expected altitude
            if expected_altitude:
                assert result.altitude == expected_altitude, f"Expected altitude '{expected_altitude}' but got '{result.altitude}' for description: {description}"
    
    def test_combined_variety_geographic_parsing(self):
        """Test combined variety and geographic parsing."""
        # Test with a description that has both variety and geographic information
        description = "S795 and Chandagiri varieties from Krishnagiri Estate, Chikmagalur at 1500m altitude"
        
        # Extract varieties
        variety_result = self.variety_service.extract_varieties(description)
        
        # Extract geographic data
        geographic_result = self.geographic_service.parse_geographic(description)
        
        # Verify variety extraction
        assert 's795' in variety_result.varieties
        assert 'chandagiri' in variety_result.varieties
        assert len(variety_result.varieties) == 2
        
        # Verify geographic parsing
        assert geographic_result.region == 'chikmagalur'
        assert geographic_result.estate == 'krishnagiri_estate'
        assert geographic_result.altitude == 1500
        assert geographic_result.confidence > 0
    
    def test_batch_processing_integration(self):
        """Test batch processing for both services."""
        descriptions = [
            "S795 Arabica from Chikmagalur",
            "Selection 9 coffee from Coorg",
            "Green Tip Gesha from Riverdale Estate, Yercaud",
            "Monsoon Malabar from Kerala"
        ]
        
        # Batch variety extraction
        variety_results = self.variety_service.extract_varieties_batch(descriptions)
        
        # Batch geographic parsing
        geographic_results = self.geographic_service.parse_geographic_batch(descriptions)
        
        # Verify results
        assert len(variety_results) == 4
        assert len(geographic_results) == 4
        
        # Check specific results
        assert 's795' in variety_results[0].varieties
        assert 's9' in variety_results[1].varieties
        assert 'geisha' in variety_results[2].varieties
        assert 'monsoon_malabar' in variety_results[3].varieties
        
        assert geographic_results[0].region == 'chikmagalur'
        assert geographic_results[1].region == 'coorg'
        assert geographic_results[2].region == 'yercaud'
        assert geographic_results[3].region == 'kerala'
    
    def test_service_configuration(self):
        """Test service configuration and initialization."""
        # Test variety service configuration
        variety_config = VarietyConfig(
            enable_variety_extraction=True,
            confidence_threshold=0.8,
            max_varieties_per_description=3
        )
        
        variety_service = VarietyExtractionService(variety_config.to_dict())
        assert variety_service.config['confidence_threshold'] == 0.8
        assert variety_service.config['max_varieties_per_description'] == 3
        
        # Test geographic service configuration
        geographic_config = GeographicConfig(
            enable_geographic_parsing=True,
            confidence_threshold=0.7,
            enable_altitude_validation=True
        )
        
        geographic_service = GeographicParserService(geographic_config.to_dict())
        assert geographic_service.config['confidence_threshold'] == 0.7
        assert geographic_service.config['enable_altitude_validation'] == True
    
    def test_error_handling_integration(self):
        """Test error handling in integration scenarios."""
        # Test with invalid input
        variety_result = self.variety_service.extract_varieties(None)
        assert variety_result.varieties == []
        assert len(variety_result.warnings) > 0
        
        geographic_result = self.geographic_service.parse_geographic(None)
        assert geographic_result.region == 'unknown'
        assert geographic_result.country == 'unknown'
        assert geographic_result.confidence == 0.0
        assert len(geographic_result.warnings) > 0
    
    def test_performance_integration(self):
        """Test performance with large batch processing."""
        # Create a large batch of descriptions
        descriptions = [
            "S795 Arabica from Chikmagalur",
            "Selection 9 coffee from Coorg",
            "Green Tip Gesha from Riverdale Estate, Yercaud",
            "Monsoon Malabar from Kerala",
            "Kent variety from Wayanad",
            "Cauvery from Nilgiris",
            "SL28 and SL34 from Coorg",
            "Catimor from Araku Valley"
        ] * 10  # 80 descriptions
        
        # Test variety extraction performance
        variety_results = self.variety_service.extract_varieties_batch(descriptions)
        assert len(variety_results) == 80
        
        # Test geographic parsing performance
        geographic_results = self.geographic_service.parse_geographic_batch(descriptions)
        assert len(geographic_results) == 80
        
        # Verify all results are valid
        for result in variety_results:
            assert isinstance(result, type(result))
            assert hasattr(result, 'varieties')
        
        for result in geographic_results:
            assert isinstance(result, type(result))
            assert hasattr(result, 'region')
    
    def test_statistics_integration(self):
        """Test statistics tracking in integration scenarios."""
        # Process some descriptions to generate stats
        descriptions = [
            "S795 Arabica from Chikmagalur",
            "Selection 9 coffee from Coorg",
            "Generic coffee blend"
        ]
        
        # Process with variety service
        self.variety_service.extract_varieties_batch(descriptions)
        variety_stats = self.variety_service.get_extraction_stats()
        
        assert variety_stats['total_extractions'] == 3
        assert variety_stats['successful_extractions'] >= 2  # At least 2 should succeed
        assert variety_stats['varieties_found'] > 0
        
        # Process with geographic service
        self.geographic_service.parse_geographic_batch(descriptions)
        geographic_stats = self.geographic_service.get_parsing_stats()
        
        assert geographic_stats['total_parses'] == 3
        assert geographic_stats['successful_parses'] >= 2  # At least 2 should succeed
        assert geographic_stats['regions_found'] > 0
    
    def test_health_check_integration(self):
        """Test health check functionality."""
        # Test variety service health check
        variety_health = self.variety_service.health_check()
        assert variety_health['status'] == 'healthy'
        assert 'variety_patterns_count' in variety_health
        assert variety_health['variety_patterns_count'] > 0
        
        # Test geographic service health check
        geographic_health = self.geographic_service.health_check()
        assert geographic_health['status'] == 'healthy'
        assert 'region_patterns_count' in geographic_health
        assert geographic_health['region_patterns_count'] > 0
        assert 'estate_patterns_count' in geographic_health
        assert geographic_health['estate_patterns_count'] > 0
