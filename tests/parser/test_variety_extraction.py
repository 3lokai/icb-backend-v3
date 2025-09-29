"""
Unit tests for Indian Coffee Variety Extraction Service
"""

import pytest
from unittest.mock import patch, MagicMock
from src.parser.variety_extraction import VarietyExtractionService, VarietyResult


class TestVarietyExtractionService:
    """Test cases for variety extraction service."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.service = VarietyExtractionService()
    
    def test_init(self):
        """Test service initialization."""
        assert self.service is not None
        assert hasattr(self.service, 'variety_patterns')
        assert hasattr(self.service, 'stats')
        assert len(self.service.variety_patterns) > 0
    
    def test_extract_varieties_s795(self):
        """Test extraction of S795 variety."""
        description = "Premium S795 Arabica from Chikmagalur"
        result = self.service.extract_varieties(description)
        
        assert isinstance(result, VarietyResult)
        assert 's795' in result.varieties
        assert len(result.confidence_scores) == 1
        assert result.confidence_scores[0] == 0.9
        assert len(result.warnings) == 0
    
    def test_extract_varieties_s9(self):
        """Test extraction of S9 variety."""
        description = "Selection 9 coffee from Coorg region"
        result = self.service.extract_varieties(description)
        
        assert isinstance(result, VarietyResult)
        assert 's9' in result.varieties
        assert len(result.confidence_scores) == 1
        assert result.confidence_scores[0] == 0.9
    
    def test_extract_varieties_geisha(self):
        """Test extraction of Geisha variety."""
        description = "Green Tip Gesha from Riverdale Estate"
        result = self.service.extract_varieties(description)
        
        assert isinstance(result, VarietyResult)
        assert 'geisha' in result.varieties
        assert len(result.confidence_scores) == 1
        assert result.confidence_scores[0] == 0.9
    
    def test_extract_varieties_monsoon_malabar(self):
        """Test extraction of Monsoon Malabar variety."""
        description = "Monsoon Malabar coffee from Kerala"
        result = self.service.extract_varieties(description)
        
        assert isinstance(result, VarietyResult)
        assert 'monsoon_malabar' in result.varieties
        # Note: This may also match 'malabar' pattern, so we check for at least 1 confidence score
        assert len(result.confidence_scores) >= 1
        assert all(score == 0.9 for score in result.confidence_scores)
    
    def test_extract_varieties_multiple(self):
        """Test extraction of multiple varieties."""
        description = "S795 and Chandagiri varieties from Krishnagiri Estate"
        result = self.service.extract_varieties(description)
        
        assert isinstance(result, VarietyResult)
        assert 's795' in result.varieties
        assert 'chandagiri' in result.varieties
        assert len(result.varieties) == 2
        assert len(result.confidence_scores) == 2
        assert all(score == 0.9 for score in result.confidence_scores)
    
    def test_extract_varieties_no_match(self):
        """Test extraction with no variety matches."""
        description = "Generic coffee blend"
        result = self.service.extract_varieties(description)
        
        assert isinstance(result, VarietyResult)
        assert len(result.varieties) == 0
        assert len(result.confidence_scores) == 0
        assert len(result.warnings) == 0
    
    def test_extract_varieties_invalid_input(self):
        """Test extraction with invalid input."""
        result = self.service.extract_varieties(None)
        
        assert isinstance(result, VarietyResult)
        assert len(result.varieties) == 0
        assert len(result.confidence_scores) == 0
        assert len(result.warnings) == 1
        assert "Invalid or empty description" in result.warnings[0]
    
    def test_extract_varieties_empty_string(self):
        """Test extraction with empty string."""
        result = self.service.extract_varieties("")
        
        assert isinstance(result, VarietyResult)
        assert len(result.varieties) == 0
        assert len(result.confidence_scores) == 0
        assert len(result.warnings) == 1
        assert "Invalid or empty description" in result.warnings[0]
    
    def test_extract_varieties_case_insensitive(self):
        """Test case insensitive variety extraction."""
        description = "S795 and SL28 varieties"
        result = self.service.extract_varieties(description)
        
        assert isinstance(result, VarietyResult)
        assert 's795' in result.varieties
        assert 'sl28' in result.varieties
        assert len(result.varieties) == 2
    
    def test_extract_varieties_batch(self):
        """Test batch variety extraction."""
        descriptions = [
            "S795 Arabica from Chikmagalur",
            "Selection 9 coffee from Coorg",
            "Generic coffee blend"
        ]
        
        results = self.service.extract_varieties_batch(descriptions)
        
        assert len(results) == 3
        assert isinstance(results[0], VarietyResult)
        assert 's795' in results[0].varieties
        assert 's9' in results[1].varieties
        assert len(results[2].varieties) == 0
    
    def test_extract_varieties_batch_empty(self):
        """Test batch extraction with empty list."""
        results = self.service.extract_varieties_batch([])
        
        assert len(results) == 0
    
    def test_extract_varieties_batch_invalid(self):
        """Test batch extraction with invalid descriptions."""
        descriptions = [None, "", "Valid description"]
        
        results = self.service.extract_varieties_batch(descriptions)
        
        assert len(results) == 3
        assert len(results[0].varieties) == 0
        assert len(results[1].varieties) == 0
        assert len(results[2].varieties) >= 0  # May or may not have matches
    
    def test_check_variety_conflicts(self):
        """Test variety conflict detection."""
        # Test conflicting varieties
        conflicting_varieties = ['s795', 's9']
        conflicts = self.service._check_variety_conflicts(conflicting_varieties)
        
        assert len(conflicts) > 0
        assert any('s795' in conflict and 's9' in conflict for conflict in conflicts)
    
    def test_check_variety_conflicts_no_conflicts(self):
        """Test variety conflict detection with no conflicts."""
        non_conflicting_varieties = ['s795', 'chandagiri']
        conflicts = self.service._check_variety_conflicts(non_conflicting_varieties)
        
        assert len(conflicts) == 0
    
    def test_get_extraction_stats(self):
        """Test extraction statistics."""
        # Extract some varieties to generate stats
        self.service.extract_varieties("S795 Arabica")
        self.service.extract_varieties("Selection 9 coffee")
        
        stats = self.service.get_extraction_stats()
        
        assert 'total_extractions' in stats
        assert 'successful_extractions' in stats
        assert 'failed_extractions' in stats
        assert 'varieties_found' in stats
        assert 'warnings_generated' in stats
        assert 'success_rate' in stats
        assert 'failure_rate' in stats
        assert 'avg_varieties_per_extraction' in stats
    
    def test_reset_stats(self):
        """Test statistics reset."""
        # Generate some stats
        self.service.extract_varieties("S795 Arabica")
        
        # Reset stats
        self.service.reset_stats()
        
        stats = self.service.get_extraction_stats()
        assert stats['total_extractions'] == 0
        assert stats['successful_extractions'] == 0
        assert stats['failed_extractions'] == 0
        assert stats['varieties_found'] == 0
        assert stats['warnings_generated'] == 0
    
    def test_health_check(self):
        """Test health check."""
        health = self.service.health_check()
        
        assert 'status' in health
        assert 'variety_patterns_count' in health
        assert 'stats' in health
        assert health['status'] == 'healthy'
        assert health['variety_patterns_count'] > 0
    
    def test_to_dict(self):
        """Test VarietyResult to_dict method."""
        result = VarietyResult(
            varieties=['s795', 's9'],
            confidence_scores=[0.9, 0.9],
            warnings=[]
        )
        
        result_dict = result.to_dict()
        
        assert isinstance(result_dict, dict)
        assert result_dict['varieties'] == ['s795', 's9']
        assert result_dict['confidence_scores'] == [0.9, 0.9]
        assert result_dict['warnings'] == []
    
    def test_extract_varieties_with_config(self):
        """Test extraction with custom configuration."""
        config = {
            'confidence_threshold': 0.8,
            'max_varieties_per_description': 3
        }
        
        service = VarietyExtractionService(config)
        result = service.extract_varieties("S795 and S9 and S8 varieties")
        
        assert isinstance(result, VarietyResult)
        assert len(result.varieties) <= 3  # Should respect max limit
    
    def test_extract_varieties_error_handling(self):
        """Test error handling in variety extraction."""
        with patch('re.search', side_effect=Exception("Regex error")):
            result = self.service.extract_varieties("S795 Arabica")
            
            assert isinstance(result, VarietyResult)
            assert len(result.varieties) == 0
            assert len(result.warnings) == 1
            assert "Variety extraction failed" in result.warnings[0]
    
    def test_extract_varieties_batch_error_handling(self):
        """Test error handling in batch extraction."""
        with patch('re.search', side_effect=Exception("Regex error")):
            descriptions = ["S795 Arabica", "Selection 9 coffee"]
            results = self.service.extract_varieties_batch(descriptions)
            
            assert len(results) == 2
            for result in results:
                assert isinstance(result, VarietyResult)
                assert len(result.warnings) == 1
                assert "Variety extraction failed" in result.warnings[0]
