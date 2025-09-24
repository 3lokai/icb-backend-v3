"""
Enhanced edge-case handling and heuristics tests for process method parser.

Tests advanced heuristics, coffee context detection, and edge-case scenarios.
"""

import pytest
from src.parser.process_parser import ProcessMethodParser, ProcessResult


class TestProcessParserEdgeCases:
    """Test enhanced edge-case handling and heuristics for process method parser."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.parser = ProcessMethodParser()
    
    def test_coffee_processing_terminology_heuristics(self):
        """Test coffee processing terminology heuristics for ambiguous inputs."""
        test_cases = [
            ('wet process', 'washed', 0.95),  # Explicitly matched
            ('clean process', 'washed', 0.7),  # Heuristic
            ('bright coffee', 'washed', 0.7),  # Heuristic
            ('dry process', 'natural', 0.95),  # Explicitly matched
            ('sun-dried coffee', 'natural', 0.7),  # Heuristic
            ('fruit process', 'natural', 0.7),  # Heuristic
            ('semi-washed', 'honey', 0.95),  # Explicitly matched
            ('pulped natural', 'honey', 0.95),  # Explicitly matched
            ('miel process', 'honey', 0.95),  # Explicitly matched
            ('sticky process', 'honey', 0.7),  # Heuristic
            ('fermented coffee', 'anaerobic', 0.95),  # Explicitly matched
            ('co-fermented', 'anaerobic', 0.95),  # Explicitly matched
            ('experimental process', 'anaerobic', 0.95),  # Explicitly matched
        ]

        for input_text, expected_enum, expected_confidence in test_cases:       
            result = self.parser.parse_process_method(input_text)

            assert result.enum_value == expected_enum
            assert result.confidence >= expected_confidence
            # Only check for heuristic notes if confidence is < 0.95 (heuristic)
            if result.confidence < 0.95:
                assert 'heuristic' in result.conversion_notes.lower()
                assert len(result.parsing_warnings) > 0
    
    def test_regional_processing_heuristics(self):
        """Test regional processing heuristics."""
        test_cases = [
            ('ethiopian coffee', 'natural', 0.6),
            ('yirgacheffe process', 'natural', 0.6),
            ('sidamo coffee', 'natural', 0.6),
            ('costa rican coffee', 'washed', 0.6),
            ('colombian process', 'washed', 0.6),
            ('guatemalan coffee', 'washed', 0.6),
        ]
        
        for input_text, expected_enum, expected_confidence in test_cases:       
            result = self.parser.parse_process_method(input_text)

            assert result.enum_value == expected_enum
            assert result.confidence >= expected_confidence
            assert 'heuristic' in result.conversion_notes.lower()
            assert len(result.parsing_warnings) > 0
    
    def test_malformed_input_handling(self):
        """Test handling of malformed and edge-case inputs."""
        test_cases = [
            ('', 'other', 0.0, 'Empty or null process input'),
            ('   ', 'other', 0.0, 'Empty or null process input'),
            ('none', 'other', 0.0, 'Empty or null process input'),
            ('null', 'other', 0.0, 'Empty or null process input'),
            ('N/A', 'other', 0.95, None),  # Explicitly matched by "other" pattern
            ('not specified', 'other', 0.95, None),  # Explicitly matched by "other" pattern     
        ]

        for input_text, expected_enum, expected_confidence, expected_warning in test_cases:                                                                     
            result = self.parser.parse_process_method(input_text)

            assert result.enum_value == expected_enum
            assert result.confidence == expected_confidence
            if expected_warning:
                assert expected_warning in result.parsing_warnings[0]
    
    def test_ambiguous_format_heuristics(self):
        """Test ambiguous format heuristics."""
        test_cases = [
            ('process', 'other', 0.0),  # Generic term without context
            ('washed process', 'washed', 0.95),  # Explicitly matched
            ('natural process', 'natural', 0.95),  # Explicitly matched
            ('honey process', 'honey', 0.95),  # Explicitly matched
            ('anaerobic process', 'anaerobic', 0.95),  # Explicitly matched
        ]

        for input_text, expected_enum, expected_confidence in test_cases:       
            result = self.parser.parse_process_method(input_text)

            assert result.enum_value == expected_enum
            assert result.confidence >= expected_confidence
            # Only check for heuristics if confidence is between 0.6 and 0.95 (heuristic range)
            if 0.6 <= result.confidence < 0.95:
                assert 'heuristic' in result.conversion_notes.lower()
                assert len(result.parsing_warnings) > 0
    
    def test_confidence_scoring_edge_cases(self):
        """Test confidence scoring for various edge cases."""
        test_cases = [
            ('Washed Process', 0.95),  # Explicit pattern
            ('washed process', 0.95),  # Case insensitive
            ('WASHED PROCESS', 0.95),  # All caps
            ('wet process', 0.7),       # Terminology heuristic
            ('ethiopian coffee', 0.6),  # Regional heuristic
            ('process', 0.0),          # Ambiguous
        ]
        
        for input_text, expected_min_confidence in test_cases:
            result = self.parser.parse_process_method(input_text)
            assert result.confidence >= expected_min_confidence
    
    def test_parsing_warnings_edge_cases(self):
        """Test parsing warnings for edge cases."""
        test_cases = [
            ('process', 'Unable to parse'),
            ('wet process', None),  # Explicit match, no warnings
            ('ethiopian coffee', 'regional heuristics'),
            ('', 'Empty or null process input'),
        ]

        for input_text, expected_warning_content in test_cases:
            result = self.parser.parse_process_method(input_text)

            if expected_warning_content:
                assert any(expected_warning_content in warning for warning in result.parsing_warnings)
            else:
                assert len(result.parsing_warnings) == 0
    
    def test_conversion_notes_edge_cases(self):
        """Test conversion notes for edge cases."""
        test_cases = [
            ('Washed Process', 'Matched explicit'),
            ('wet process', 'Matched explicit'),  # Explicitly matched
            ('ethiopian coffee', 'Ethiopian coffee typically natural'),
            ('process', 'Unrecognized process method format'),
        ]

        for input_text, expected_note_content in test_cases:
            result = self.parser.parse_process_method(input_text)
            assert expected_note_content in result.conversion_notes
    
    def test_batch_processing_edge_cases(self):
        """Test batch processing with edge cases."""
        edge_case_inputs = [
            'Washed Process',
            'wet process',
            'ethiopian coffee',
            'process',
            '',
            'none',
            'honey process',
            'colombian coffee'
        ]
        
        results = self.parser.batch_parse_process_methods(edge_case_inputs)
        
        assert len(results) == len(edge_case_inputs)
        
        # Check that results are properly categorized
        explicit_results = [r for r in results if r.confidence >= 0.95]
        heuristic_results = [r for r in results if 0.6 <= r.confidence < 0.95]  
        ambiguous_results = [r for r in results if r.confidence < 0.6]

        assert len(explicit_results) >= 3  # 'Washed Process', 'wet process', 'honey process'
        assert len(heuristic_results) >= 2  # Regional heuristics: ethiopian coffee, colombian coffee
        assert len(ambiguous_results) >= 2  # Empty and ambiguous inputs
    
    def test_error_handling_robustness(self):
        """Test error handling robustness with various input types."""
        test_cases = [
            None,  # None input
            123,   # Numeric input
            [],    # List input
            {},    # Dict input
            'a' * 1000,  # Very long string
            '🚀☕',  # Unicode input
        ]
        
        for input_text in test_cases:
            result = self.parser.parse_process_method(input_text)
            
            # Should not raise exception
            assert isinstance(result, ProcessResult)
            assert result.enum_value in ['washed', 'natural', 'honey', 'anaerobic', 'other']
            assert 0.0 <= result.confidence <= 1.0
            assert isinstance(result.parsing_warnings, list)
            assert isinstance(result.conversion_notes, str)
    
    def test_performance_with_edge_cases(self):
        """Test performance with edge cases."""
        import time
        
        # Large batch of mixed edge cases
        edge_case_inputs = [
            'Washed Process', 'wet process', 'ethiopian coffee', 'process',
            '', 'none', 'honey process', 'colombian coffee', 'natural process',
            'anaerobic process', 'fermented coffee', 'costa rican coffee'
        ] * 100  # 1200 inputs
        
        start_time = time.time()
        results = self.parser.batch_parse_process_methods(edge_case_inputs)
        end_time = time.time()
        
        processing_time = end_time - start_time
        
        assert len(results) == len(edge_case_inputs)
        assert processing_time < 5.0  # Should process 1200 inputs in under 5 seconds
        assert all(isinstance(r, ProcessResult) for r in results)
    
    def test_heuristic_confidence_scoring(self):
        """Test confidence scoring for different heuristic types."""
        test_cases = [
            # Explicit matches (high confidence)
            ('wet process', 0.95),
            ('dry process', 0.95),
            ('fermented coffee', 0.95),
            ('washed process', 0.95),
            ('natural process', 0.95),

            # Regional heuristics (lower confidence)
            ('ethiopian coffee', 0.6),
            ('colombian coffee', 0.6),
        ]

        for input_text, expected_min_confidence in test_cases:
            result = self.parser.parse_process_method(input_text)
            assert result.confidence >= expected_min_confidence
            # Only check for heuristics if confidence is < 0.95
            if result.confidence < 0.95:
                assert 'heuristic' in result.conversion_notes.lower()
    
    def test_edge_case_original_text_preservation(self):
        """Test that original text is preserved correctly for edge cases."""
        test_cases = [
            '  Washed Process ',  # Whitespace
            'Washed\nProcess',    # Newlines
            'Washed\tProcess',    # Tabs
            'Washed Process',     # Normal
        ]
        
        for input_text in test_cases:
            result = self.parser.parse_process_method(input_text)
            assert result.original_text == input_text
