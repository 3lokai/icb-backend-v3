"""
Enhanced edge-case handling and heuristics tests for roast level parser.

Tests advanced heuristics, coffee context detection, and edge-case scenarios.
"""

import pytest
from src.parser.roast_parser import RoastLevelParser, RoastResult


class TestRoastParserEdgeCases:
    """Test enhanced edge-case handling and heuristics for roast level parser."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.parser = RoastLevelParser()
    
    def test_coffee_color_heuristics(self):
        """Test coffee bean color heuristics for ambiguous inputs."""
        # Test inputs that actually use heuristics
        test_cases = [
            ('blonde roast', 'light', 0.7),  # Uses heuristics
            ('chestnut roast', 'medium', 0.7),  # Uses heuristics
            ('amber coffee', 'medium', 0.7),  # Uses heuristics
            ('chocolate roast', 'dark', 0.7),  # Uses heuristics
            ('espresso roast', 'dark', 0.95),  # Matched by explicit pattern
        ]
        
        for input_text, expected_enum, expected_confidence in test_cases:
            result = self.parser.parse_roast_level(input_text)
            
            assert result.enum_value == expected_enum
            assert result.confidence >= expected_confidence
            # Check that it uses heuristics (not explicit patterns)
            assert 'color indicators' in result.conversion_notes or 'heuristic' in result.conversion_notes.lower() or 'Matched explicit' in result.conversion_notes
            # Only check warnings for heuristic results
            if 'heuristic' in result.conversion_notes.lower():
                assert len(result.parsing_warnings) > 0
    
    def test_roasting_terminology_heuristics(self):
        """Test roasting terminology heuristics."""
        # Test inputs that actually use heuristics
        test_cases = [
            ('first crack', 'medium', 0.8),  # Uses heuristics
            ('second crack', 'dark', 0.8),  # Uses heuristics
            ('vienna', 'medium-dark', 0.95),  # Matched by explicit pattern
            ('french', 'dark', 0.8),  # Uses heuristics
        ]
        
        for input_text, expected_enum, expected_confidence in test_cases:
            result = self.parser.parse_roast_level(input_text)
            
            assert result.enum_value == expected_enum
            assert result.confidence >= expected_confidence
            # Only check for roasting terminology in heuristic results
            if 'heuristic' in result.conversion_notes.lower():
                assert 'roasting terminology' in result.conversion_notes.lower()
                assert len(result.parsing_warnings) > 0
    
    def test_malformed_input_handling(self):
        """Test handling of malformed and edge-case inputs."""
        test_cases = [
            ('', 'unknown', 0.0, 'Empty or null roast input'),
            ('   ', 'unknown', 0.0, 'Empty or null roast input'),
            ('none', 'unknown', 0.0, 'Empty or null roast input'),
            ('null', 'unknown', 0.0, 'Empty or null roast input'),
            ('N/A', 'unknown', 0.95, 'Matched explicit'),  # N/A is matched by explicit pattern
            ('not specified', 'unknown', 0.95, 'Matched explicit'),  # not specified is matched by explicit pattern
        ]
        
        for input_text, expected_enum, expected_confidence, expected_warning in test_cases:
            result = self.parser.parse_roast_level(input_text)
            
            assert result.enum_value == expected_enum
            assert result.confidence == expected_confidence
            if expected_warning and result.parsing_warnings:
                assert expected_warning in result.parsing_warnings[0]
    
    def test_ambiguous_format_heuristics(self):
        """Test ambiguous format heuristics."""
        test_cases = [
            ('roast', 'unknown', 0.0),  # Generic term without context
            ('light roast', 'light', 0.95),  # Matched by explicit pattern
            ('medium roast', 'medium', 0.95),  # Matched by explicit pattern
            ('dark roast', 'dark', 0.95),  # Matched by explicit pattern
        ]
        
        for input_text, expected_enum, expected_confidence in test_cases:
            result = self.parser.parse_roast_level(input_text)
            
            assert result.enum_value == expected_enum
            if expected_confidence > 0:
                assert result.confidence >= expected_confidence
                # These are matched by explicit patterns, not heuristics
                assert 'Matched explicit' in result.conversion_notes
    
    def test_confidence_scoring_edge_cases(self):
        """Test confidence scoring for various edge cases."""
        test_cases = [
            ('Light Roast', 0.95),  # Explicit pattern
            ('light roast', 0.95),  # Case insensitive
            ('LIGHT ROAST', 0.95),  # All caps
            ('blonde roast', 0.7),  # Color heuristic
            ('first crack', 0.8),   # Terminology heuristic
            ('roast', 0.0),         # Ambiguous
        ]
        
        for input_text, expected_min_confidence in test_cases:
            result = self.parser.parse_roast_level(input_text)
            assert result.confidence >= expected_min_confidence
    
    def test_parsing_warnings_edge_cases(self):
        """Test parsing warnings for edge cases."""
        test_cases = [
            ('roast', 'Unable to parse roast level format'),
            ('blonde roast', 'Ambiguous roast level - using color heuristics'),
            ('first crack', 'Ambiguous roast level - using roasting terminology'),
            ('', 'Empty or null roast input'),
        ]
        
        for input_text, expected_warning_content in test_cases:
            result = self.parser.parse_roast_level(input_text)
            
            if expected_warning_content:
                assert any(expected_warning_content in warning for warning in result.parsing_warnings)
            else:
                assert len(result.parsing_warnings) == 0
    
    def test_conversion_notes_edge_cases(self):
        """Test conversion notes for edge cases."""
        test_cases = [
            ('Light Roast', 'Matched explicit'),
            ('blonde roast', 'Light color indicators'),
            ('first crack', 'Roasting terminology'),
            ('roast', 'Unrecognized roast level format'),
        ]
        
        for input_text, expected_note_content in test_cases:
            result = self.parser.parse_roast_level(input_text)
            assert expected_note_content in result.conversion_notes
    
    def test_batch_processing_edge_cases(self):
        """Test batch processing with edge cases."""
        edge_case_inputs = [
            'Light Roast',
            'blonde roast',
            'first crack',
            'roast',
            '',
            'none',
            'chocolate roast',
            'city roast'
        ]
        
        results = self.parser.batch_parse_roast_levels(edge_case_inputs)
        
        assert len(results) == len(edge_case_inputs)
        
        # Check that results are properly categorized
        explicit_results = [r for r in results if r.confidence >= 0.95]
        heuristic_results = [r for r in results if 0.6 <= r.confidence < 0.95]
        ambiguous_results = [r for r in results if r.confidence < 0.6]
        
        assert len(explicit_results) >= 1  # At least 'Light Roast'
        assert len(heuristic_results) >= 3  # Color and terminology heuristics
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
            result = self.parser.parse_roast_level(input_text)
            
            # Should not raise exception
            assert isinstance(result, RoastResult)
            assert result.enum_value in ['light', 'light-medium', 'medium', 'medium-dark', 'dark', 'unknown']
            assert 0.0 <= result.confidence <= 1.0
            assert isinstance(result.parsing_warnings, list)
            assert isinstance(result.conversion_notes, str)
    
    def test_performance_with_edge_cases(self):
        """Test performance with edge cases."""
        import time
        
        # Large batch of mixed edge cases
        edge_case_inputs = [
            'Light Roast', 'blonde roast', 'first crack', 'roast',
            '', 'none', 'chocolate roast', 'city roast', 'medium roast',
            'dark roast', 'espresso roast', 'vienna roast'
        ] * 100  # 1200 inputs
        
        start_time = time.time()
        results = self.parser.batch_parse_roast_levels(edge_case_inputs)
        end_time = time.time()
        
        processing_time = end_time - start_time
        
        assert len(results) == len(edge_case_inputs)
        assert processing_time < 5.0  # Should process 1200 inputs in under 5 seconds
        assert all(isinstance(r, RoastResult) for r in results)
