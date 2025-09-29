"""
Tests for sensory parameter parsing service.
"""

import pytest
from src.parser.sensory_parser import SensoryParserService, SensoryResult
from src.config.sensory_config import SensoryConfig


class TestSensoryParserService:
    """Test cases for SensoryParserService."""
    
    def test_parse_sensory_basic(self):
        """Test basic sensory parameter extraction."""
        config = SensoryConfig()
        parser = SensoryParserService(config)
        
        description = "This coffee has high acidity and full body with bright citrus notes"
        result = parser.parse_sensory(description)
        
        assert isinstance(result, SensoryResult)
        assert result.acidity is not None
        assert result.body is not None
        assert result.source == "icb_inferred"
        assert result.confidence in ["high", "medium", "low"]
    
    def test_parse_sensory_no_match(self):
        """Test sensory parsing with no matching patterns."""
        config = SensoryConfig()
        parser = SensoryParserService(config)
        
        description = "This is a generic coffee product"
        result = parser.parse_sensory(description)
        
        assert isinstance(result, SensoryResult)
        assert result.acidity is None
        assert result.body is None
        assert result.confidence == "low"
    
    def test_parse_sensory_batch(self):
        """Test batch sensory parameter extraction."""
        config = SensoryConfig()
        parser = SensoryParserService(config)
        
        descriptions = [
            "High acidity coffee with bright citrus notes",
            "Full body coffee with rich chocolate flavors",
            "Generic coffee product"
        ]
        
        results = parser.parse_sensory_batch(descriptions)
        
        assert len(results) == 3
        assert all(isinstance(r, SensoryResult) for r in results)
        assert results[0].acidity is not None  # High acidity
        assert results[1].body is not None     # Full body
        assert results[2].acidity is None      # No match
    
    def test_confidence_calculation(self):
        """Test confidence calculation based on extraction success."""
        config = SensoryConfig()
        parser = SensoryParserService(config)
        
        # High confidence - multiple parameters
        description1 = "This coffee has high acidity, full body, and sweet caramel notes"
        result1 = parser.parse_sensory(description1)
        assert result1.confidence == "high"
        
        # Medium confidence - some parameters
        description2 = "Medium acidity coffee"
        result2 = parser.parse_sensory(description2)
        assert result2.confidence == "medium"
        
        # Low confidence - no parameters
        description3 = "Generic coffee"
        result3 = parser.parse_sensory(description3)
        assert result3.confidence == "low"
    
    def test_stats_tracking(self):
        """Test service statistics tracking."""
        config = SensoryConfig()
        parser = SensoryParserService(config)
        
        # Initial stats
        stats = parser.get_stats()
        assert stats['total_processed'] == 0
        
        # Process some descriptions
        parser.parse_sensory("High acidity coffee")
        parser.parse_sensory("Full body coffee")
        parser.parse_sensory("Generic coffee")
        
        # Check updated stats
        stats = parser.get_stats()
        assert stats['total_processed'] == 3
        assert stats['successful_extractions'] == 3
        assert stats['success_rate'] == 1.0
    
    def test_reset_stats(self):
        """Test statistics reset functionality."""
        config = SensoryConfig()
        parser = SensoryParserService(config)
        
        # Process some descriptions
        parser.parse_sensory("High acidity coffee")
        
        # Verify stats are populated
        stats = parser.get_stats()
        assert stats['total_processed'] == 1
        
        # Reset stats
        parser.reset_stats()
        
        # Verify stats are reset
        stats = parser.get_stats()
        assert stats['total_processed'] == 0
        assert stats['successful_extractions'] == 0
