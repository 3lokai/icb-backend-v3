"""
Unit tests for Indian Coffee Geographic Parser Service
"""

import pytest
from unittest.mock import patch, MagicMock
from src.parser.geographic_parser import GeographicParserService, GeographicResult


class TestGeographicParserService:
    """Test cases for geographic parser service."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.service = GeographicParserService()
    
    def test_init(self):
        """Test service initialization."""
        assert self.service is not None
        assert hasattr(self.service, 'region_patterns')
        assert hasattr(self.service, 'estate_patterns')
        assert hasattr(self.service, 'state_patterns')
        assert hasattr(self.service, 'country_patterns')
        assert hasattr(self.service, 'altitude_patterns')
        assert hasattr(self.service, 'stats')
        assert len(self.service.region_patterns) > 0
        assert len(self.service.estate_patterns) > 0
    
    def test_parse_geographic_chikmagalur(self):
        """Test parsing of Chikmagalur region."""
        description = "High-grown Arabica from Chikmagalur region"
        result = self.service.parse_geographic(description)
        
        assert isinstance(result, GeographicResult)
        assert result.region == 'chikmagalur'
        assert result.country == 'india'  # Correctly inferred from region
        assert result.state == 'karnataka'  # Correctly inferred from region
        assert result.estate == 'unknown'
        assert result.altitude is None
        assert result.confidence > 0
        assert len(result.warnings) == 0
    
    def test_parse_geographic_coorg(self):
        """Test parsing of Coorg region."""
        description = "Coffee from Coorg, Karnataka"
        result = self.service.parse_geographic(description)
        
        assert isinstance(result, GeographicResult)
        assert result.region == 'coorg'
        assert result.state == 'karnataka'
        assert result.confidence > 0
    
    def test_parse_geographic_estate(self):
        """Test parsing of coffee estate."""
        description = "Premium coffee from Krishnagiri Estate"
        result = self.service.parse_geographic(description)
        
        assert isinstance(result, GeographicResult)
        assert result.estate == 'krishnagiri_estate'
        assert result.confidence > 0
    
    def test_parse_geographic_altitude(self):
        """Test parsing of altitude information."""
        description = "High-grown coffee at 1500m altitude"
        result = self.service.parse_geographic(description)
        
        assert isinstance(result, GeographicResult)
        assert result.altitude == 1500
        assert result.confidence > 0
    
    def test_parse_geographic_altitude_feet(self):
        """Test parsing of altitude in feet."""
        description = "Coffee grown at 5000ft above sea level"
        result = self.service.parse_geographic(description)
        
        assert isinstance(result, GeographicResult)
        assert result.altitude == 1524  # 5000 * 0.3048
        assert result.confidence > 0
    
    def test_parse_geographic_complete(self):
        """Test parsing of complete geographic information."""
        description = "S795 from Krishnagiri Estate, Chikmagalur, Karnataka at 1500m altitude"
        result = self.service.parse_geographic(description)
        
        assert isinstance(result, GeographicResult)
        assert result.region == 'chikmagalur'
        assert result.estate == 'krishnagiri_estate'
        assert result.state == 'karnataka'
        assert result.altitude == 1500
        assert result.confidence > 0
    
    def test_parse_geographic_no_match(self):
        """Test parsing with no geographic matches."""
        description = "Generic coffee blend"
        result = self.service.parse_geographic(description)
        
        assert isinstance(result, GeographicResult)
        assert result.region == 'unknown'
        assert result.country == 'unknown'
        assert result.state == 'unknown'
        assert result.estate == 'unknown'
        assert result.altitude is None
        assert result.confidence == 0.0
        assert len(result.warnings) == 1
        assert "No geographic information detected" in result.warnings[0]
    
    def test_parse_geographic_invalid_input(self):
        """Test parsing with invalid input."""
        result = self.service.parse_geographic(None)
        
        assert isinstance(result, GeographicResult)
        assert result.region == 'unknown'
        assert result.country == 'unknown'
        assert result.state == 'unknown'
        assert result.estate == 'unknown'
        assert result.altitude is None
        assert result.confidence == 0.0
        assert len(result.warnings) == 1
        assert "Invalid or empty description" in result.warnings[0]
    
    def test_parse_geographic_empty_string(self):
        """Test parsing with empty string."""
        result = self.service.parse_geographic("")
        
        assert isinstance(result, GeographicResult)
        assert result.region == 'unknown'
        assert result.country == 'unknown'
        assert result.state == 'unknown'
        assert result.estate == 'unknown'
        assert result.altitude is None
        assert result.confidence == 0.0
        assert len(result.warnings) == 1
        assert "Invalid or empty description" in result.warnings[0]
    
    def test_parse_geographic_case_insensitive(self):
        """Test case insensitive geographic parsing."""
        description = "Coffee from CHIKMAGALUR and KARNATAKA"
        result = self.service.parse_geographic(description)
        
        assert isinstance(result, GeographicResult)
        assert result.region == 'chikmagalur'
        assert result.state == 'karnataka'
    
    def test_parse_geographic_batch(self):
        """Test batch geographic parsing."""
        descriptions = [
            "Coffee from Chikmagalur, Karnataka",
            "Selection from Coorg region",
            "Generic coffee blend"
        ]
        
        results = self.service.parse_geographic_batch(descriptions)
        
        assert len(results) == 3
        assert isinstance(results[0], GeographicResult)
        assert results[0].region == 'chikmagalur'
        assert results[1].region == 'coorg'
        assert results[2].region == 'unknown'
    
    def test_parse_geographic_batch_empty(self):
        """Test batch parsing with empty list."""
        results = self.service.parse_geographic_batch([])
        
        assert len(results) == 0
    
    def test_parse_geographic_batch_invalid(self):
        """Test batch parsing with invalid descriptions."""
        descriptions = [None, "", "Valid description from Chikmagalur"]
        
        results = self.service.parse_geographic_batch(descriptions)
        
        assert len(results) == 3
        assert results[0].region == 'unknown'
        assert results[1].region == 'unknown'
        assert results[2].region == 'chikmagalur'
    
    def test_extract_region(self):
        """Test region extraction."""
        description = "Coffee from Chikmagalur region"
        region = self.service._extract_region(description)
        
        assert region == 'chikmagalur'
    
    def test_extract_country(self):
        """Test country extraction."""
        description = "Indian coffee from Chikmagalur"
        country = self.service._extract_country(description)
        
        assert country == 'india'
    
    def test_extract_state(self):
        """Test state extraction."""
        description = "Coffee from Karnataka state"
        state = self.service._extract_state(description)
        
        assert state == 'karnataka'
    
    def test_extract_estate(self):
        """Test estate extraction."""
        description = "Coffee from Krishnagiri Estate"
        estate = self.service._extract_estate(description)
        
        assert estate == 'krishnagiri_estate'
    
    def test_extract_altitude(self):
        """Test altitude extraction."""
        description = "Coffee grown at 1500m altitude"
        altitude = self.service._extract_altitude(description)
        
        assert altitude == 1500
    
    def test_extract_altitude_feet(self):
        """Test altitude extraction in feet."""
        description = "Coffee grown at 5000ft above sea level"
        altitude = self.service._extract_altitude(description)
        
        assert altitude == 1524  # 5000 * 0.3048
    
    def test_calculate_confidence(self):
        """Test confidence calculation."""
        confidence = self.service._calculate_confidence(
            region='chikmagalur',
            country='india',
            state='karnataka',
            estate='krishnagiri_estate',
            altitude=1500
        )
        
        assert confidence > 0
        assert confidence <= 1.0
    
    def test_calculate_confidence_no_data(self):
        """Test confidence calculation with no data."""
        confidence = self.service._calculate_confidence(
            region='unknown',
            country='unknown',
            state='unknown',
            estate='unknown',
            altitude=None
        )
        
        assert confidence == 0.0
    
    def test_generate_warnings_region_state_mismatch(self):
        """Test warning generation for region-state mismatch."""
        warnings = self.service._generate_warnings(
            region='chikmagalur',
            country='india',
            state='tamil_nadu',  # Mismatch - Chikmagalur is in Karnataka
            estate='unknown',
            altitude=None
        )
        
        assert len(warnings) > 0
        assert any('Region-state mismatch' in warning for warning in warnings)
    
    def test_generate_warnings_altitude_validation(self):
        """Test warning generation for altitude validation."""
        warnings = self.service._generate_warnings(
            region='unknown',
            country='unknown',
            state='unknown',
            estate='unknown',
            altitude=-100  # Negative altitude
        )
        
        assert len(warnings) > 0
        assert any('Negative altitude' in warning for warning in warnings)
    
    def test_generate_warnings_high_altitude(self):
        """Test warning generation for high altitude."""
        warnings = self.service._generate_warnings(
            region='unknown',
            country='unknown',
            state='unknown',
            estate='unknown',
            altitude=4000  # Very high altitude
        )
        
        assert len(warnings) > 0
        assert any('Very high altitude' in warning for warning in warnings)
    
    def test_generate_warnings_low_altitude(self):
        """Test warning generation for low altitude."""
        warnings = self.service._generate_warnings(
            region='unknown',
            country='unknown',
            state='unknown',
            estate='unknown',
            altitude=100  # Very low altitude
        )
        
        assert len(warnings) > 0
        assert any('Very low altitude' in warning for warning in warnings)
    
    def test_generate_warnings_no_geographic_info(self):
        """Test warning generation for no geographic information."""
        warnings = self.service._generate_warnings(
            region='unknown',
            country='unknown',
            state='unknown',
            estate='unknown',
            altitude=None
        )
        
        assert len(warnings) > 0
        assert any('No geographic information detected' in warning for warning in warnings)
    
    def test_get_parsing_stats(self):
        """Test parsing statistics."""
        # Parse some descriptions to generate stats
        self.service.parse_geographic("Coffee from Chikmagalur")
        self.service.parse_geographic("Coffee from Coorg")
        
        stats = self.service.get_parsing_stats()
        
        assert 'total_parses' in stats
        assert 'successful_parses' in stats
        assert 'failed_parses' in stats
        assert 'regions_found' in stats
        assert 'estates_found' in stats
        assert 'altitudes_found' in stats
        assert 'warnings_generated' in stats
        assert 'success_rate' in stats
        assert 'failure_rate' in stats
        assert 'region_extraction_rate' in stats
        assert 'estate_extraction_rate' in stats
        assert 'altitude_extraction_rate' in stats
    
    def test_reset_stats(self):
        """Test statistics reset."""
        # Generate some stats
        self.service.parse_geographic("Coffee from Chikmagalur")
        
        # Reset stats
        self.service.reset_stats()
        
        stats = self.service.get_parsing_stats()
        assert stats['total_parses'] == 0
        assert stats['successful_parses'] == 0
        assert stats['failed_parses'] == 0
        assert stats['regions_found'] == 0
        assert stats['estates_found'] == 0
        assert stats['altitudes_found'] == 0
        assert stats['warnings_generated'] == 0
    
    def test_health_check(self):
        """Test health check."""
        health = self.service.health_check()
        
        assert 'status' in health
        assert 'region_patterns_count' in health
        assert 'estate_patterns_count' in health
        assert 'state_patterns_count' in health
        assert 'country_patterns_count' in health
        assert 'altitude_patterns_count' in health
        assert 'stats' in health
        assert health['status'] == 'healthy'
        assert health['region_patterns_count'] > 0
        assert health['estate_patterns_count'] > 0
    
    def test_to_dict(self):
        """Test GeographicResult to_dict method."""
        result = GeographicResult(
            region='chikmagalur',
            country='india',
            state='karnataka',
            estate='krishnagiri_estate',
            altitude=1500,
            confidence=0.9,
            warnings=[]
        )
        
        result_dict = result.to_dict()
        
        assert isinstance(result_dict, dict)
        assert result_dict['region'] == 'chikmagalur'
        assert result_dict['country'] == 'india'
        assert result_dict['state'] == 'karnataka'
        assert result_dict['estate'] == 'krishnagiri_estate'
        assert result_dict['altitude'] == 1500
        assert result_dict['confidence'] == 0.9
        assert result_dict['warnings'] == []
    
    def test_parse_geographic_with_config(self):
        """Test parsing with custom configuration."""
        config = {
            'confidence_threshold': 0.8,
            'enable_altitude_validation': True
        }
        
        service = GeographicParserService(config)
        result = service.parse_geographic("Coffee from Chikmagalur at 1500m")
        
        assert isinstance(result, GeographicResult)
        assert result.region == 'chikmagalur'
        assert result.altitude == 1500
    
    def test_parse_geographic_error_handling(self):
        """Test error handling in geographic parsing."""
        with patch('re.search', side_effect=Exception("Regex error")):
            result = self.service.parse_geographic("Coffee from Chikmagalur")
            
            assert isinstance(result, GeographicResult)
            assert result.region == 'unknown'
            assert result.confidence == 0.0
            assert len(result.warnings) == 1
            assert "Geographic parsing failed" in result.warnings[0]
    
    def test_parse_geographic_batch_error_handling(self):
        """Test error handling in batch parsing."""
        with patch('re.search', side_effect=Exception("Regex error")):
            descriptions = ["Coffee from Chikmagalur", "Coffee from Coorg"]
            results = self.service.parse_geographic_batch(descriptions)
            
            assert len(results) == 2
            for result in results:
                assert isinstance(result, GeographicResult)
                assert result.region == 'unknown'
                assert result.confidence == 0.0
                assert len(result.warnings) == 1
                assert "Geographic parsing failed" in result.warnings[0]
