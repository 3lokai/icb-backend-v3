"""
Unit tests for bean species parser.
"""

import pytest
from src.parser.species_parser import BeanSpeciesParserService, SpeciesResult, SpeciesConfig


class TestBeanSpeciesParserService:
    """Test cases for BeanSpeciesParserService."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.parser = BeanSpeciesParserService()
    
    def test_parse_arabica_species(self):
        """Test parsing arabica species from content."""
        result = self.parser.parse_species(
            title="100% Arabica Coffee",
            description="Pure arabica beans from Ethiopia"
        )
        
        assert result.species == 'arabica'
        assert result.confidence > 0.8
        assert result.source == 'content_parsing'
        assert 'arabica' in result.detected_species
    
    def test_parse_robusta_species(self):
        """Test parsing robusta species from content."""
        result = self.parser.parse_species(
            title="Robusta Coffee Beans",
            description="100% robusta coffee from Vietnam"
        )
        
        assert result.species == 'robusta'
        assert result.confidence > 0.8
        assert result.source == 'content_parsing'
        assert 'robusta' in result.detected_species
    
    def test_parse_liberica_species(self):
        """Test parsing liberica species from content."""
        result = self.parser.parse_species(
            title="Liberica Coffee",
            description="Rare liberica beans from Philippines"
        )
        
        assert result.species == 'liberica'
        assert result.confidence > 0.8
        assert result.source == 'content_parsing'
        assert 'liberica' in result.detected_species
    
    def test_parse_ratio_blend_80_20(self):
        """Test parsing 80/20 arabica-robusta blend."""
        result = self.parser.parse_species(
            title="Coffee Blend",
            description="80% arabica and 20% robusta blend"
        )
        
        assert result.species == 'arabica_80_robusta_20'
        assert result.confidence > 0.8
        assert result.source == 'content_parsing'
    
    def test_parse_ratio_blend_70_30(self):
        """Test parsing 70/30 arabica-robusta blend."""
        result = self.parser.parse_species(
            title="Premium Blend",
            description="70% arabica, 30% robusta coffee"
        )
        
        assert result.species == 'arabica_70_robusta_30'
        assert result.confidence > 0.8
        assert result.source == 'content_parsing'
    
    def test_parse_arabica_chicory(self):
        """Test parsing arabica chicory mix."""
        result = self.parser.parse_species(
            title="Chicory Coffee",
            description="Arabica coffee with chicory"
        )
        
        assert result.species == 'arabica_chicory'
        assert result.confidence > 0.8
        assert result.source == 'content_parsing'
    
    def test_parse_robusta_chicory(self):
        """Test parsing robusta chicory mix."""
        result = self.parser.parse_species(
            title="Chicory Blend",
            description="Robusta coffee with chicory"
        )
        
        assert result.species == 'robusta_chicory'
        assert result.confidence > 0.8
        assert result.source == 'content_parsing'
    
    def test_parse_blend_chicory(self):
        """Test parsing generic blend chicory mix."""
        result = self.parser.parse_species(
            title="Chicory Coffee Mix",
            description="Coffee blend with chicory"
        )
        
        assert result.species == 'blend_chicory'
        assert result.confidence > 0.8
        assert result.source == 'content_parsing'
    
    def test_parse_filter_coffee_mix(self):
        """Test parsing filter coffee mix."""
        result = self.parser.parse_species(
            title="South Indian Filter Coffee",
            description="Traditional filter coffee mix"
        )
        
        assert result.species == 'filter_coffee_mix'
        assert result.confidence > 0.8
        assert result.source == 'content_parsing'
    
    def test_parse_generic_blend(self):
        """Test parsing generic blend."""
        result = self.parser.parse_species(
            title="Coffee Blend",
            description="Arabica and robusta blend"
        )
        
        assert result.species == 'blend'
        assert result.confidence > 0.8
        assert result.source == 'blend_detection'
    
    def test_parse_unknown_species(self):
        """Test parsing when no species is detected."""
        result = self.parser.parse_species(
            title="Coffee Beans",
            description="Premium coffee beans"
        )
        
        assert result.species == 'unknown'
        assert result.confidence == 0.0
        assert result.source == 'no_match'
        assert len(result.warnings) > 0
    
    def test_parse_empty_content(self):
        """Test parsing with empty content."""
        result = self.parser.parse_species(
            title="",
            description=""
        )
        
        assert result.species == 'unknown'
        assert result.confidence == 0.0
        assert result.source == 'no_match'
        assert 'Empty title and description' in result.warnings
    
    def test_parse_with_confidence_threshold(self):
        """Test parsing with custom confidence threshold."""
        config = SpeciesConfig(confidence_threshold=0.9)
        parser = BeanSpeciesParserService(config)
        
        result = parser.parse_species(
            title="Arabica Coffee",
            description="Premium arabica beans"
        )
        
        # Should still detect arabica but with lower confidence
        assert result.species == 'arabica'
        assert result.confidence >= 0.8
    
    def test_batch_parse_species(self):
        """Test batch parsing of multiple products."""
        products = [
            {'title': '100% Arabica', 'description': 'Pure arabica beans'},
            {'title': 'Robusta Coffee', 'description': 'Strong robusta beans'},
            {'title': 'Coffee Blend', 'description': 'Mixed coffee blend'},
            {'title': 'Unknown Coffee', 'description': 'Premium coffee'}
        ]
        
        results = self.parser.batch_parse_species(products)
        
        assert len(results) == 4
        assert results[0].species == 'arabica'
        assert results[1].species == 'robusta'
        assert results[2].species == 'blend'
        assert results[3].species == 'unknown'
    
    def test_validate_species_enum(self):
        """Test species enum validation."""
        valid_species = [
            'arabica', 'robusta', 'liberica', 'blend',
            'arabica_80_robusta_20', 'arabica_70_robusta_30',
            'arabica_60_robusta_40', 'arabica_50_robusta_50',
            'robusta_80_arabica_20',
            'arabica_chicory', 'robusta_chicory', 'blend_chicory',
            'filter_coffee_mix'
        ]
        
        for species in valid_species:
            assert self.parser.validate_species_enum(species)
        
        # Test invalid species
        assert not self.parser.validate_species_enum('invalid_species')
        assert not self.parser.validate_species_enum('unknown')
    
    def test_get_performance_metrics(self):
        """Test performance metrics retrieval."""
        metrics = self.parser.get_performance_metrics()
        
        assert 'parser_version' in metrics
        assert 'supported_species' in metrics
        assert 'pattern_count' in metrics
        assert 'confidence_threshold' in metrics
        assert 'batch_size' in metrics
        
        assert metrics['parser_version'] == '1.0.0'
        assert isinstance(metrics['supported_species'], list)
        assert metrics['pattern_count'] > 0
    
    def test_species_result_serialization(self):
        """Test SpeciesResult serialization."""
        result = SpeciesResult(
            species='arabica',
            confidence=0.9,
            source='content_parsing',
            warnings=[],
            detected_species=['arabica']
        )
        
        # Test to_dict
        result_dict = result.to_dict()
        assert result_dict['species'] == 'arabica'
        assert result_dict['confidence'] == 0.9
        
        # Test from_dict
        new_result = SpeciesResult.from_dict(result_dict)
        assert new_result.species == 'arabica'
        assert new_result.confidence == 0.9
    
    def test_species_config(self):
        """Test SpeciesConfig functionality."""
        config = SpeciesConfig(
            confidence_threshold=0.8,
            enable_blend_detection=False,
            batch_size=50
        )
        
        assert config.confidence_threshold == 0.8
        assert config.enable_blend_detection is False
        assert config.batch_size == 50
        
        # Test serialization
        config_dict = config.to_dict()
        assert config_dict['confidence_threshold'] == 0.8
        
        # Test deserialization
        new_config = SpeciesConfig.from_dict(config_dict)
        assert new_config.confidence_threshold == 0.8
    
    def test_error_handling(self):
        """Test error handling in parsing."""
        # Test with None values
        result = self.parser.parse_species(None, None)
        assert result.species == 'unknown'
        assert result.source == 'error'
        assert len(result.warnings) > 0
    
    def test_context_patterns(self):
        """Test context pattern detection."""
        result = self.parser.parse_species(
            title="Coffee Species",
            description="This arabica coffee is a single species variety"
        )
        
        # Should have higher confidence due to context
        assert result.species == 'arabica'
        assert result.confidence >= 0.9
    
    def test_blend_detection_disabled(self):
        """Test blend detection when disabled."""
        config = SpeciesConfig(enable_blend_detection=False)
        parser = BeanSpeciesParserService(config)
        
        result = parser.parse_species(
            title="Coffee Blend",
            description="Arabica and robusta blend"
        )
        
        # Should not detect as blend
        assert result.species != 'blend'
    
    def test_chicory_detection_disabled(self):
        """Test chicory detection when disabled."""
        config = SpeciesConfig(enable_chicory_detection=False)
        parser = BeanSpeciesParserService(config)
        
        result = parser.parse_species(
            title="Chicory Coffee",
            description="Arabica coffee with chicory"
        )
        
        # Should not detect as chicory mix
        assert result.species != 'arabica_chicory'
    
    def test_ratio_detection_disabled(self):
        """Test ratio detection when disabled."""
        config = SpeciesConfig(enable_ratio_detection=False)
        parser = BeanSpeciesParserService(config)
        
        result = parser.parse_species(
            title="Coffee Blend",
            description="80% arabica and 20% robusta"
        )
        
        # Should not detect as ratio blend
        assert result.species != 'arabica_80_robusta_20'

