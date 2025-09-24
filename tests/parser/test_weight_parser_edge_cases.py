"""
Tests for enhanced edge case handling and heuristics in weight parser.
"""

import pytest
from src.parser.weight_parser import WeightParser, WeightResult


class TestWeightParserEdgeCases:
    """Test cases for edge case handling and heuristics."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.parser = WeightParser()
    
    def test_coffee_context_heuristics(self):
        """Test coffee-specific heuristics for weight detection."""
        test_cases = [
            # Coffee context with typical bag sizes
            ("250 coffee beans", 250, 0.8),  # 200-1000g range
            ("500 whole bean coffee", 500, 0.8),
            ("0.5kg arabica coffee", 500, 0.8),  # 0.2-1.0kg range
            ("12oz roasted coffee", 340, 0.7),  # 8-16oz range
            ("8oz ground coffee", 226, 0.7),
        ]
        
        for input_str, expected_grams, expected_confidence in test_cases:
            result = self.parser.parse_weight(input_str)
            assert result.grams == expected_grams, f"Failed for {input_str}: expected {expected_grams}, got {result.grams}"
            assert result.confidence >= expected_confidence, f"Failed for {input_str}: expected confidence >= {expected_confidence}, got {result.confidence}"
            # Only check for coffee context heuristics for ambiguous inputs (not explicit units)
            if not any(unit in input_str.lower() for unit in ['kg', 'g', 'oz', 'lb']):
                assert 'coffee' in result.conversion_notes.lower() or 'heuristic' in result.conversion_notes.lower()
    
    def test_edge_case_handling(self):
        """Test edge case handling for malformed inputs."""
        test_cases = [
            # Very long strings
            ("This is a very long string that contains way too much text to be a reasonable weight input and should be rejected", 0, 0.0),
            
            # No numbers
            ("no numbers here", 0, 0.0),
            ("just text", 0, 0.0),
            
            # Too many numbers
            ("1 2 3 4 5 6 7 8 9 10", 0, 0.0),
            ("250g 500g 1kg 2kg", 0, 0.0),
            
            # Negative weights
            ("-250g", 0, 0.0),
            ("250g - 100g", 0, 0.0),
            
            # Scientific notation
            ("1e3", 1000, 0.7),  # 1000 grams
            ("2.5e2", 250, 0.7),  # 250 grams
            ("1e-3", 0, 0.0),  # Invalid (negative)
        ]
        
        for input_str, expected_grams, expected_confidence in test_cases:
            result = self.parser.parse_weight(input_str)
            assert result.grams == expected_grams, f"Failed for {input_str}: expected {expected_grams}, got {result.grams}"
            assert result.confidence == expected_confidence, f"Failed for {input_str}: expected confidence {expected_confidence}, got {result.confidence}"
    
    def test_ambiguous_formats_with_heuristics(self):
        """Test ambiguous formats with enhanced heuristics."""
        test_cases = [
            # General heuristics
            ("250", 250, 0.7),  # >= 1000 would be grams, but 250 is in coffee range
            ("1500", 1500, 0.7),  # >= 1000, assume grams
            ("2.5", 2500, 0.6),  # 1-10 range, assume kg
            ("0.5", 500, 0.6),  # < 1, assume kg
            
            # Coffee context heuristics
            ("250 coffee", 250, 0.8),  # Coffee context, 200-1000g range
            ("0.5kg beans", 500, 0.8),  # Coffee context, 0.2-1.0kg range
            ("12oz roast", 340, 0.7),  # Coffee context, 8-16oz range
        ]
        
        for input_str, expected_grams, expected_confidence in test_cases:
            result = self.parser.parse_weight(input_str)
            assert result.grams == expected_grams, f"Failed for {input_str}: expected {expected_grams}, got {result.grams}"
            assert result.confidence >= expected_confidence, f"Failed for {input_str}: expected confidence >= {expected_confidence}, got {result.confidence}"
    
    def test_error_handling_robustness(self):
        """Test error handling for various invalid inputs."""
        invalid_inputs = [
            None,
            [],
            {},
            "",
            "   ",
            "invalid",
            "g250",  # Wrong order
            "oz8.8",  # Wrong order
            "weight: unknown",
            "N/A",
            "TBD",
            "?",
            "∞",  # Infinity symbol
            "NaN",
        ]
        
        for invalid_input in invalid_inputs:
            result = self.parser.parse_weight(invalid_input)
            assert isinstance(result, WeightResult), f"Should return WeightResult for {invalid_input}"
            assert result.grams == 0, f"Invalid input {invalid_input} should result in 0 grams"
            assert result.confidence == 0.0, f"Invalid input {invalid_input} should have 0 confidence"
            assert len(result.parsing_warnings) > 0, f"Invalid input {invalid_input} should have parsing warnings"
    
    def test_performance_with_large_inputs(self):
        """Test performance with various input sizes."""
        import time
        
        # Test with reasonable inputs
        test_inputs = [
            "250g",
            "0.5kg",
            "8.8oz",
            "1lb",
            "8 1/2 oz",
            "250g (8.8oz)",
            "250 coffee beans",
            "0.5kg whole bean",
        ]
        
        start_time = time.time()
        for _ in range(100):  # Parse each input 100 times
            for test_input in test_inputs:
                result = self.parser.parse_weight(test_input)
                assert isinstance(result, WeightResult)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Should complete in reasonable time (less than 1 second for 800 parses)
        assert total_time < 1.0, f"Performance test took too long: {total_time:.2f}s"
    
    def test_confidence_scoring(self):
        """Test confidence scoring for different input types."""
        test_cases = [
            # High confidence (explicit units)
            ("250g", 0.95),
            ("0.5kg", 0.95),
            ("8.8oz", 0.95),
            ("1lb", 0.95),
            
            # Medium confidence (heuristics)
            ("250", 0.7),
            ("0.5", 0.6),
            ("250 coffee", 0.8),  # Coffee context
            
            # Low confidence (ambiguous)
            ("250g (8.8oz)", 0.9),  # Mixed format
            ("8 1/2 oz", 0.95),  # Fraction format
        ]
        
        for input_str, expected_min_confidence in test_cases:
            result = self.parser.parse_weight(input_str)
            assert result.confidence >= expected_min_confidence, \
                f"Failed for {input_str}: expected confidence >= {expected_min_confidence}, got {result.confidence}"
    
    def test_warning_messages(self):
        """Test that appropriate warning messages are generated."""
        test_cases = [
            ("250", ["Ambiguous unit - using heuristics"]),
            ("250 coffee", ["Ambiguous unit - coffee context heuristics"]),
            ("", ["Empty or null weight input"]),
            ("no numbers", ["No numeric content found"]),
            ("1 2 3 4 5 6 7 8 9 10", ["Too many numbers found"]),
            ("-250g", ["Negative weight not supported"]),
        ]
        
        for input_str, expected_warnings in test_cases:
            result = self.parser.parse_weight(input_str)
            for expected_warning in expected_warnings:
                assert any(expected_warning in warning for warning in result.parsing_warnings), \
                    f"Expected warning '{expected_warning}' not found in {result.parsing_warnings}"
    
    def test_conversion_notes_quality(self):
        """Test that conversion notes provide useful information."""
        test_cases = [
            ("250g", "Converted 250.0 g to 250 grams"),
            ("0.5kg", "Converted 0.5 kg to 500 grams"),
            ("250", "Assumed grams for value 250"),
            ("250 coffee", "Assumed grams for coffee bag size 250.0g"),
        ]
        
        for input_str, expected_note_pattern in test_cases:
            result = self.parser.parse_weight(input_str)
            assert expected_note_pattern.lower() in result.conversion_notes.lower(), \
                f"Expected note pattern '{expected_note_pattern}' not found in '{result.conversion_notes}'"
    
    def test_batch_processing_edge_cases(self):
        """Test batch processing with edge cases."""
        mixed_inputs = [
            "250g",  # Valid
            "invalid",  # Invalid
            "0.5kg",  # Valid
            "",  # Empty
            "8.8oz",  # Valid
            None,  # None
            "250 coffee",  # Valid with heuristics
        ]
        
        results = self.parser.batch_parse_weights(mixed_inputs)
        
        assert len(results) == len(mixed_inputs)
        
        # Check that valid inputs were parsed
        valid_results = [r for r in results if r.grams > 0]
        assert len(valid_results) == 4  # 250g, 0.5kg, 8.8oz, 250 coffee
        
        # Check that invalid inputs were handled gracefully
        invalid_results = [r for r in results if r.grams == 0]
        assert len(invalid_results) == 3  # invalid, "", None
