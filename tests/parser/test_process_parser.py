"""
Unit tests for the process method parser.

Tests comprehensive process method parsing functionality including:
- Explicit process method patterns
- Numeric process method mappings
- Ambiguous format handling
- Edge cases and error handling
- Performance requirements
"""

import json
import pytest
from pathlib import Path
from src.parser.process_parser import ProcessMethodParser, ProcessResult


class TestProcessMethodParser:
    """Test suite for ProcessMethodParser."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.parser = ProcessMethodParser()
        
        # Load test fixtures
        fixtures_path = Path(__file__).parent / "fixtures" / "process_formats.json"
        with open(fixtures_path, 'r') as f:
            self.test_fixtures = json.load(f)
    
    def test_parser_initialization(self):
        """Test parser initialization."""
        assert self.parser is not None
        assert hasattr(self.parser, 'process_patterns')
        assert hasattr(self.parser, 'ambiguous_patterns')
        assert len(self.parser.process_patterns) == 5  # washed, natural, honey, anaerobic, other
    
    def test_explicit_process_methods(self):
        """Test explicit process method parsing."""
        test_cases = self.test_fixtures['test_cases'][0]['test_cases']
        
        for test_case in test_cases:
            result = self.parser.parse_process_method(test_case['input'])
            
            assert result.enum_value == test_case['expected_enum']
            assert result.confidence >= test_case['expected_confidence']
            assert result.original_text == test_case['input']
            assert len(result.parsing_warnings) == 0
    
    def test_numeric_process_methods(self):
        """Test numeric process method parsing."""
        test_cases = self.test_fixtures['test_cases'][1]['test_cases']
        
        for test_case in test_cases:
            result = self.parser.parse_process_method(test_case['input'])
            
            assert result.enum_value == test_case['expected_enum']
            assert result.confidence >= test_case['expected_confidence']
            assert result.original_text == test_case['input']
            assert len(result.parsing_warnings) == 0
    
    def test_ambiguous_formats(self):
        """Test ambiguous format handling."""
        test_cases = self.test_fixtures['test_cases'][2]['test_cases']
        
        for test_case in test_cases:
            result = self.parser.parse_process_method(test_case['input'])
            
            assert result.enum_value == test_case['expected_enum']
            assert result.confidence >= test_case['expected_confidence']
            assert result.original_text == test_case['input']
            # Ambiguous formats should have warnings
            assert len(result.parsing_warnings) > 0
    
    def test_edge_cases(self):
        """Test edge cases and malformed input."""
        test_cases = self.test_fixtures['test_cases'][3]['test_cases']
        
        for test_case in test_cases:
            result = self.parser.parse_process_method(test_case['input'])
            
            assert result.enum_value == test_case['expected_enum']
            assert result.confidence >= test_case['expected_confidence']
            assert result.original_text == test_case['input']
    
    def test_unicode_special(self):
        """Test unicode and special character handling."""
        test_cases = self.test_fixtures['test_cases'][4]['test_cases']
        
        for test_case in test_cases:
            result = self.parser.parse_process_method(test_case['input'])
            
            assert result.enum_value == test_case['expected_enum']
            assert result.confidence >= test_case['expected_confidence']
            assert result.original_text == test_case['input']
    
    def test_empty_input(self):
        """Test empty input handling."""
        result = self.parser.parse_process_method("")
        assert result.enum_value == "other"
        assert result.confidence == 0.0
        assert len(result.parsing_warnings) > 0
    
    def test_none_input(self):
        """Test None input handling."""
        result = self.parser.parse_process_method(None)
        assert result.enum_value == "other"
        assert result.confidence == 0.0
        assert len(result.parsing_warnings) > 0
    
    def test_invalid_numeric_process_method(self):
        """Test invalid numeric process method handling."""
        result = self.parser.parse_process_method("6")
        assert result.enum_value == "other"
        assert result.confidence == 0.0
        assert len(result.parsing_warnings) > 0
    
    def test_negative_numeric_process_method(self):
        """Test negative numeric process method handling."""
        result = self.parser.parse_process_method("-1")
        assert result.enum_value == "other"
        assert result.confidence == 0.0
        assert len(result.parsing_warnings) > 0
    
    def test_very_long_input(self):
        """Test very long input handling."""
        long_input = "Washed Process " * 50  # Very long string
        result = self.parser.parse_process_method(long_input)
        assert result.enum_value == "other"
        assert result.confidence == 0.0
        assert len(result.parsing_warnings) > 0
    
    def test_no_letters_input(self):
        """Test input with no letters."""
        result = self.parser.parse_process_method("123456")
        assert result.enum_value == "other"
        assert result.confidence == 0.0
        assert len(result.parsing_warnings) > 0
    
    def test_batch_parsing(self):
        """Test batch parsing functionality."""
        inputs = ["Washed Process", "Natural Process", "Honey Process", "Washed", "Natural", "Honey"]
        results = self.parser.batch_parse_process_methods(inputs)
        
        assert len(results) == len(inputs)
        assert all(isinstance(result, ProcessResult) for result in results)
        assert results[0].enum_value == "washed"
        assert results[1].enum_value == "natural"
        assert results[2].enum_value == "honey"
        assert results[3].enum_value == "washed"
        assert results[4].enum_value == "natural"
        assert results[5].enum_value == "honey"
    
    def test_performance_metrics(self):
        """Test performance metrics."""
        metrics = self.parser.get_performance_metrics()
        
        assert 'parser_version' in metrics
        assert 'supported_process_methods' in metrics
        assert 'pattern_count' in metrics
        assert 'ambiguous_pattern_count' in metrics
        assert metrics['parser_version'] == '1.0.0'
        assert len(metrics['supported_process_methods']) == 5
    
    def test_process_result_to_dict(self):
        """Test ProcessResult to_dict method."""
        result = ProcessResult(
            enum_value="washed",
            confidence=0.95,
            original_text="Washed Process",
            parsing_warnings=[],
            conversion_notes="Test conversion"
        )
        
        result_dict = result.to_dict()
        
        assert result_dict['enum_value'] == "washed"
        assert result_dict['confidence'] == 0.95
        assert result_dict['original_text'] == "Washed Process"
        assert result_dict['parsing_warnings'] == []
        assert result_dict['conversion_notes'] == "Test conversion"
    
    def test_coffee_context_heuristics(self):
        """Test coffee context heuristics."""
        # Test with coffee context
        result = self.parser.parse_process_method("washed coffee bean")
        assert result.enum_value == "washed"
        assert result.confidence >= 0.8  # Higher confidence for coffee context
        
        # Test without coffee context
        result = self.parser.parse_process_method("washed process")
        assert result.enum_value == "washed"
        assert result.confidence >= 0.7  # Lower confidence without coffee context
    
    def test_accuracy_requirements(self):
        """Test accuracy requirements (>= 95% on test fixtures)."""
        all_test_cases = []
        for category in self.test_fixtures['test_cases']:
            all_test_cases.extend(category['test_cases'])
        
        successful_parses = 0
        total_parses = len(all_test_cases)
        
        for test_case in all_test_cases:
            result = self.parser.parse_process_method(test_case['input'])
            if result.enum_value == test_case['expected_enum']:
                successful_parses += 1
        
        accuracy = successful_parses / total_parses
        assert accuracy >= 0.95, f"Accuracy {accuracy:.2%} is below required 95%"
    
    def test_performance_requirements(self):
        """Test performance requirements."""
        import time
        
        # Test single parsing performance
        start_time = time.time()
        result = self.parser.parse_process_method("Washed Process")
        end_time = time.time()
        
        parsing_time_ms = (end_time - start_time) * 1000
        assert parsing_time_ms <= 1.0, f"Parsing time {parsing_time_ms:.2f}ms exceeds 1ms requirement"
        
        # Test batch parsing performance
        inputs = ["Washed Process", "Natural Process", "Honey Process"] * 100  # 300 inputs
        start_time = time.time()
        results = self.parser.batch_parse_process_methods(inputs)
        end_time = time.time()
        
        batch_time_ms = (end_time - start_time) * 1000
        assert batch_time_ms <= 1000, f"Batch parsing time {batch_time_ms:.2f}ms exceeds 1000ms requirement"
        assert len(results) == len(inputs)
    
    def test_error_handling(self):
        """Test comprehensive error handling."""
        # Test exception handling
        result = self.parser.parse_process_method("Washed Process")
        assert isinstance(result, ProcessResult)
        assert result.enum_value == "washed"
        assert result.confidence > 0
        
        # Test malformed input
        result = self.parser.parse_process_method("Washed Process - Natural Process")
        assert result.enum_value == "other"
        assert result.confidence == 0.0
        assert len(result.parsing_warnings) > 0
    
    def test_confidence_scoring(self):
        """Test confidence scoring for different input types."""
        # High confidence for explicit patterns
        result = self.parser.parse_process_method("Washed Process")
        assert result.confidence >= 0.95
        
        # Medium confidence for ambiguous patterns
        result = self.parser.parse_process_method("process")
        assert result.confidence == 0.0  # Unknown for generic terms
        
        # Lower confidence for ambiguous patterns
        result = self.parser.parse_process_method("natural process")
        assert result.confidence >= 0.95
        
        # Zero confidence for invalid patterns
        result = self.parser.parse_process_method("Invalid Process")
        assert result.confidence == 0.0
    
    def test_parsing_warnings(self):
        """Test parsing warning generation."""
        # Test warnings for ambiguous input
        result = self.parser.parse_process_method("process")
        assert len(result.parsing_warnings) > 0
        assert "Unable to parse" in result.parsing_warnings[0]
        
        # Test warnings for invalid input
        result = self.parser.parse_process_method("Invalid Process")
        assert len(result.parsing_warnings) > 0
        assert "Unable to parse" in result.parsing_warnings[0]
        
        # Test no warnings for explicit patterns
        result = self.parser.parse_process_method("Washed Process")
        assert len(result.parsing_warnings) == 0
    
    def test_conversion_notes(self):
        """Test conversion notes generation."""
        # Test notes for explicit patterns
        result = self.parser.parse_process_method("Washed Process")
        assert "Matched explicit" in result.conversion_notes
        
        # Test notes for ambiguous patterns
        result = self.parser.parse_process_method("process")
        assert "Unrecognized process method format" in result.conversion_notes
        
        # Test notes for explicit patterns
        result = self.parser.parse_process_method("Natural Process")
        assert "Matched explicit" in result.conversion_notes
    
    def test_process_method_coverage(self):
        """Test coverage of all supported process methods."""
        supported_methods = ['washed', 'natural', 'honey', 'anaerobic', 'other']
        
        for method in supported_methods:
            # Test that parser can handle each method
            if method == 'other':
                result = self.parser.parse_process_method("Unknown")
            else:
                result = self.parser.parse_process_method(f"{method.title()} Process")
            
            assert result.enum_value == method
            assert result.confidence > 0
    
    def test_process_method_edge_cases(self):
        """Test edge cases for process method parsing."""
        # Test case sensitivity
        result = self.parser.parse_process_method("washed process")
        assert result.enum_value == "washed"
        
        # Test whitespace handling
        result = self.parser.parse_process_method("  Washed Process  ")
        assert result.enum_value == "washed"
        
        # Test punctuation handling
        result = self.parser.parse_process_method("Washed Process,")
        assert result.enum_value == "washed"
        
        # Test mixed case
        result = self.parser.parse_process_method("WaShEd PrOcEsS")
        assert result.enum_value == "washed"
    
    def test_process_method_validation(self):
        """Test process method validation."""
        # Test valid process methods
        valid_methods = ['washed', 'natural', 'honey', 'anaerobic', 'other']
        for method in valid_methods:
            result = self.parser.parse_process_method(f"{method.title()} Process")
            assert result.enum_value == method
            assert result.confidence > 0
        
        # Test invalid process methods
        invalid_inputs = ["Invalid Process", "Not a Process", "Random Text"]
        for invalid_input in invalid_inputs:
            result = self.parser.parse_process_method(invalid_input)
            assert result.enum_value == "other"
            assert result.confidence == 0.0
            assert len(result.parsing_warnings) > 0
    
    def test_specific_process_methods(self):
        """Test specific process method patterns."""
        # Test washed process variations
        washed_inputs = ["Washed Process", "Wet Processed", "Fully Washed", "Traditional"]
        for input_text in washed_inputs:
            result = self.parser.parse_process_method(input_text)
            assert result.enum_value == "washed"
            assert result.confidence >= 0.95
        
        # Test natural process variations
        natural_inputs = ["Natural Process", "Dry Processed", "Sun Dried", "Unwashed"]
        for input_text in natural_inputs:
            result = self.parser.parse_process_method(input_text)
            assert result.enum_value == "natural"
            assert result.confidence >= 0.95
        
        # Test honey process variations
        honey_inputs = ["Honey Process", "Semi-Washed", "Pulped Natural", "Miel"]
        for input_text in honey_inputs:
            result = self.parser.parse_process_method(input_text)
            assert result.enum_value == "honey"
            assert result.confidence >= 0.95
        
        # Test anaerobic process variations
        anaerobic_inputs = ["Anaerobic Process", "Fermented", "Co-Fermented", "Experimental"]
        for input_text in anaerobic_inputs:
            result = self.parser.parse_process_method(input_text)
            assert result.enum_value == "anaerobic"
            assert result.confidence >= 0.95
    
    def test_real_world_patterns(self):
        """Test real-world process method patterns from actual coffee data."""
        # Test patterns found in actual sample data
        real_world_patterns = {
            "Washed": "washed",
            "Natural": "natural",
            "Washed Coffee": "washed",
            "Natural Beans": "natural",
            "Process: Washed": "washed"
        }

        for input_text, expected_method in real_world_patterns.items():
            result = self.parser.parse_process_method(input_text)
            assert result.enum_value == expected_method
            assert result.confidence >= 0.9
    
    def test_ambiguous_heuristics(self):
        """Test ambiguous format heuristics."""
        # Test ambiguous text inputs
        ambiguous_inputs = ["process", "processed", "processing", "method", "technique"]
        expected_methods = ["other", "other", "other", "other", "other"] 

        for input_text, expected_method in zip(ambiguous_inputs, expected_methods):
            result = self.parser.parse_process_method(input_text)
            assert result.enum_value == expected_method
            assert result.confidence == 0.0  # Unknown for generic terms
            assert len(result.parsing_warnings) > 0  # Should have warnings for ambiguous input
    
    def test_batch_parsing_performance(self):
        """Test batch parsing performance."""
        import time
        
        # Test with large batch
        inputs = ["Washed Process", "Natural Process", "Honey Process"] * 1000  # 3000 inputs
        start_time = time.time()
        results = self.parser.batch_parse_process_methods(inputs)
        end_time = time.time()
        
        # Should complete in reasonable time
        batch_time_ms = (end_time - start_time) * 1000
        assert batch_time_ms <= 5000, f"Batch parsing time {batch_time_ms:.2f}ms exceeds 5000ms requirement"
        assert len(results) == len(inputs)
        
        # All results should be valid
        assert all(isinstance(result, ProcessResult) for result in results)
        assert all(result.enum_value in ['washed', 'natural', 'honey', 'anaerobic', 'other'] for result in results)
