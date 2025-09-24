"""
Unit tests for the roast level parser.

Tests comprehensive roast level parsing functionality including:
- Explicit roast level patterns
- Numeric roast level mappings
- Ambiguous format handling
- Edge cases and error handling
- Performance requirements
"""

import json
import pytest
from pathlib import Path
from src.parser.roast_parser import RoastLevelParser, RoastResult


class TestRoastLevelParser:
    """Test suite for RoastLevelParser."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.parser = RoastLevelParser()
        
        # Load test fixtures
        fixtures_path = Path(__file__).parent / "fixtures" / "roast_formats.json"
        with open(fixtures_path, 'r') as f:
            self.test_fixtures = json.load(f)
    
    def test_parser_initialization(self):
        """Test parser initialization."""
        assert self.parser is not None
        assert hasattr(self.parser, 'roast_patterns')
        assert hasattr(self.parser, 'ambiguous_patterns')
        assert len(self.parser.roast_patterns) == 6  # light, light-medium, medium, medium-dark, dark, unknown
    
    def test_explicit_roast_levels(self):
        """Test explicit roast level parsing."""
        test_cases = self.test_fixtures['test_cases'][0]['test_cases']
        
        for test_case in test_cases:
            result = self.parser.parse_roast_level(test_case['input'])
            
            assert result.enum_value == test_case['expected_enum']
            assert result.confidence >= test_case['expected_confidence']
            assert result.original_text == test_case['input']
            assert len(result.parsing_warnings) == 0
    
    def test_numeric_roast_levels(self):
        """Test numeric roast level parsing."""
        test_cases = self.test_fixtures['test_cases'][1]['test_cases']
        
        for test_case in test_cases:
            result = self.parser.parse_roast_level(test_case['input'])
            
            assert result.enum_value == test_case['expected_enum']
            assert result.confidence >= test_case['expected_confidence']
            assert result.original_text == test_case['input']
            assert len(result.parsing_warnings) == 0
    
    def test_ambiguous_formats(self):
        """Test ambiguous format handling."""
        test_cases = self.test_fixtures['test_cases'][2]['test_cases']
        
        for test_case in test_cases:
            result = self.parser.parse_roast_level(test_case['input'])
            
            assert result.enum_value == test_case['expected_enum']
            assert result.confidence >= test_case['expected_confidence']
            assert result.original_text == test_case['input']
            # Ambiguous formats should have warnings
            assert len(result.parsing_warnings) > 0
    
    def test_edge_cases(self):
        """Test edge cases and malformed input."""
        test_cases = self.test_fixtures['test_cases'][3]['test_cases']
        
        for test_case in test_cases:
            result = self.parser.parse_roast_level(test_case['input'])
            
            assert result.enum_value == test_case['expected_enum']
            assert result.confidence >= test_case['expected_confidence']
            assert result.original_text == test_case['input']
    
    def test_unicode_special(self):
        """Test unicode and special character handling."""
        test_cases = self.test_fixtures['test_cases'][4]['test_cases']
        
        for test_case in test_cases:
            result = self.parser.parse_roast_level(test_case['input'])
            
            assert result.enum_value == test_case['expected_enum']
            assert result.confidence >= test_case['expected_confidence']
            assert result.original_text == test_case['input']
    
    def test_empty_input(self):
        """Test empty input handling."""
        result = self.parser.parse_roast_level("")
        assert result.enum_value == "unknown"
        assert result.confidence == 0.0
        assert len(result.parsing_warnings) > 0
    
    def test_none_input(self):
        """Test None input handling."""
        result = self.parser.parse_roast_level(None)
        assert result.enum_value == "unknown"
        assert result.confidence == 0.0
        assert len(result.parsing_warnings) > 0
    
    def test_invalid_numeric_roast_level(self):
        """Test invalid numeric roast level handling."""
        result = self.parser.parse_roast_level("6")
        assert result.enum_value == "unknown"
        assert result.confidence == 0.0
        assert len(result.parsing_warnings) > 0
    
    def test_negative_numeric_roast_level(self):
        """Test negative numeric roast level handling."""
        result = self.parser.parse_roast_level("-1")
        assert result.enum_value == "unknown"
        assert result.confidence == 0.0
        assert len(result.parsing_warnings) > 0
    
    def test_very_long_input(self):
        """Test very long input handling."""
        long_input = "Medium Roast " * 50  # Very long string
        result = self.parser.parse_roast_level(long_input)
        assert result.enum_value == "unknown"
        assert result.confidence == 0.0
        assert len(result.parsing_warnings) > 0
    
    def test_no_letters_input(self):
        """Test input with no letters."""
        result = self.parser.parse_roast_level("123456")
        assert result.enum_value == "unknown"
        assert result.confidence == 0.0
        assert len(result.parsing_warnings) > 0
    
    def test_batch_parsing(self):
        """Test batch parsing functionality."""
        inputs = ["Light Roast", "Medium Roast", "Dark Roast", "Light-Medium Roast", "Medium-Dark Roast", "Dark Roast Blend"]
        results = self.parser.batch_parse_roast_levels(inputs)
        
        assert len(results) == len(inputs)
        assert all(isinstance(result, RoastResult) for result in results)
        assert results[0].enum_value == "light"
        assert results[1].enum_value == "medium"
        assert results[2].enum_value == "dark"
        assert results[3].enum_value == "light-medium"
        assert results[4].enum_value == "medium-dark"
        assert results[5].enum_value == "dark"
    
    def test_performance_metrics(self):
        """Test performance metrics."""
        metrics = self.parser.get_performance_metrics()
        
        assert 'parser_version' in metrics
        assert 'supported_roast_levels' in metrics
        assert 'pattern_count' in metrics
        assert 'ambiguous_pattern_count' in metrics
        assert metrics['parser_version'] == '1.0.0'
        assert len(metrics['supported_roast_levels']) == 6
    
    def test_roast_result_to_dict(self):
        """Test RoastResult to_dict method."""
        result = RoastResult(
            enum_value="medium",
            confidence=0.95,
            original_text="Medium Roast",
            parsing_warnings=[],
            conversion_notes="Test conversion"
        )
        
        result_dict = result.to_dict()
        
        assert result_dict['enum_value'] == "medium"
        assert result_dict['confidence'] == 0.95
        assert result_dict['original_text'] == "Medium Roast"
        assert result_dict['parsing_warnings'] == []
        assert result_dict['conversion_notes'] == "Test conversion"
    
    def test_coffee_context_heuristics(self):
        """Test coffee context heuristics."""
        # Test with coffee context
        result = self.parser.parse_roast_level("light coffee bean")
        assert result.enum_value == "light"
        assert result.confidence >= 0.8  # Higher confidence for coffee context
        
        # Test without coffee context
        result = self.parser.parse_roast_level("light roast")
        assert result.enum_value == "light"
        assert result.confidence >= 0.7  # Lower confidence without coffee context
    
    def test_accuracy_requirements(self):
        """Test accuracy requirements (>= 95% on test fixtures)."""
        all_test_cases = []
        for category in self.test_fixtures['test_cases']:
            all_test_cases.extend(category['test_cases'])
        
        successful_parses = 0
        total_parses = len(all_test_cases)
        
        for test_case in all_test_cases:
            result = self.parser.parse_roast_level(test_case['input'])
            if result.enum_value == test_case['expected_enum']:
                successful_parses += 1
        
        accuracy = successful_parses / total_parses
        assert accuracy >= 0.95, f"Accuracy {accuracy:.2%} is below required 95%"
    
    def test_performance_requirements(self):
        """Test performance requirements."""
        import time
        
        # Test single parsing performance
        start_time = time.time()
        result = self.parser.parse_roast_level("Medium Roast")
        end_time = time.time()
        
        parsing_time_ms = (end_time - start_time) * 1000
        assert parsing_time_ms <= 1.0, f"Parsing time {parsing_time_ms:.2f}ms exceeds 1ms requirement"
        
        # Test batch parsing performance
        inputs = ["Light Roast", "Medium Roast", "Dark Roast"] * 100  # 300 inputs
        start_time = time.time()
        results = self.parser.batch_parse_roast_levels(inputs)
        end_time = time.time()
        
        batch_time_ms = (end_time - start_time) * 1000
        assert batch_time_ms <= 1000, f"Batch parsing time {batch_time_ms:.2f}ms exceeds 1000ms requirement"
        assert len(results) == len(inputs)
    
    def test_error_handling(self):
        """Test comprehensive error handling."""
        # Test exception handling
        result = self.parser.parse_roast_level("Medium Roast")
        assert isinstance(result, RoastResult)
        assert result.enum_value == "medium"
        assert result.confidence > 0
        
        # Test malformed input
        result = self.parser.parse_roast_level("Medium Roast - Dark Roast")
        assert result.enum_value == "unknown"
        assert result.confidence == 0.0
        assert len(result.parsing_warnings) > 0
    
    def test_confidence_scoring(self):
        """Test confidence scoring for different input types."""
        # High confidence for explicit patterns
        result = self.parser.parse_roast_level("Medium Roast")
        assert result.confidence >= 0.95
        
        # Medium confidence for ambiguous patterns
        result = self.parser.parse_roast_level("roast")
        assert result.confidence == 0.0  # Unknown for generic terms
        
        # Lower confidence for ambiguous patterns
        result = self.parser.parse_roast_level("medium roast")
        assert result.confidence >= 0.95
        
        # Zero confidence for invalid patterns
        result = self.parser.parse_roast_level("Invalid Roast")
        assert result.confidence == 0.0
    
    def test_parsing_warnings(self):
        """Test parsing warning generation."""
        # Test warnings for ambiguous input
        result = self.parser.parse_roast_level("roast")
        assert len(result.parsing_warnings) > 0
        assert "Unable to parse roast level format" in result.parsing_warnings[0]
        
        # Test warnings for invalid input
        result = self.parser.parse_roast_level("Invalid Roast")
        assert len(result.parsing_warnings) > 0
        assert "Unable to parse" in result.parsing_warnings[0]
        
        # Test no warnings for explicit patterns
        result = self.parser.parse_roast_level("Medium Roast")
        assert len(result.parsing_warnings) == 0
    
    def test_conversion_notes(self):
        """Test conversion notes generation."""
        # Test notes for explicit patterns
        result = self.parser.parse_roast_level("Medium Roast")
        assert "Matched explicit" in result.conversion_notes
        
        # Test notes for ambiguous patterns
        result = self.parser.parse_roast_level("roast")
        assert "Unrecognized roast level format" in result.conversion_notes
        
        # Test notes for explicit patterns
        result = self.parser.parse_roast_level("Medium Roast")
        assert "Matched explicit" in result.conversion_notes
    
    def test_roast_level_coverage(self):
        """Test coverage of all supported roast levels."""
        supported_levels = ['light', 'light-medium', 'medium', 'medium-dark', 'dark', 'unknown']
        
        for level in supported_levels:
            # Test that parser can handle each level
            if level == 'unknown':
                result = self.parser.parse_roast_level("Unknown")
            else:
                result = self.parser.parse_roast_level(f"{level.title()} Roast")
            
            assert result.enum_value == level
            assert result.confidence > 0
    
    def test_roast_level_edge_cases(self):
        """Test edge cases for roast level parsing."""
        # Test case sensitivity
        result = self.parser.parse_roast_level("medium roast")
        assert result.enum_value == "medium"
        
        # Test whitespace handling
        result = self.parser.parse_roast_level("  Medium Roast  ")
        assert result.enum_value == "medium"
        
        # Test punctuation handling
        result = self.parser.parse_roast_level("Medium Roast,")
        assert result.enum_value == "medium"
        
        # Test mixed case
        result = self.parser.parse_roast_level("MeDiUm RoAsT")
        assert result.enum_value == "medium"
    
    def test_roast_level_validation(self):
        """Test roast level validation."""
        # Test valid roast levels
        valid_levels = ['light', 'light-medium', 'medium', 'medium-dark', 'dark', 'unknown']
        for level in valid_levels:
            result = self.parser.parse_roast_level(f"{level.title()} Roast")
            assert result.enum_value == level
            assert result.confidence > 0
        
        # Test invalid roast levels
        invalid_inputs = ["Invalid Roast", "Not a Roast", "Random Text"]
        for invalid_input in invalid_inputs:
            result = self.parser.parse_roast_level(invalid_input)
            assert result.enum_value == "unknown"
            assert result.confidence == 0.0
            assert len(result.parsing_warnings) > 0
