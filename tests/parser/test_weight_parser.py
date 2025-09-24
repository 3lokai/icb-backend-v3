"""
Comprehensive unit tests for the weight parser library.

Tests all supported weight formats, edge cases, and performance requirements.
"""

import json
import pytest
import time
from pathlib import Path
from src.parser.weight_parser import WeightParser, WeightResult


class TestWeightParser:
    """Test suite for WeightParser class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.parser = WeightParser()
        
        # Load test fixtures
        fixtures_path = Path(__file__).parent / "fixtures" / "weight_formats.json"
        with open(fixtures_path, 'r') as f:
            self.test_data = json.load(f)
    
    def test_metric_units(self):
        """Test metric unit parsing (g, kg, mg)."""
        metric_cases = self.test_data['test_cases'][0]['test_cases']
        
        for case in metric_cases:
            result = self.parser.parse_weight(case['input'])
            
            assert result.grams == case['expected_grams'], f"Failed for {case['input']}: expected {case['expected_grams']}, got {result.grams}"
            assert result.confidence >= case['expected_confidence'], f"Failed for {case['input']}: expected confidence >= {case['expected_confidence']}, got {result.confidence}"
            assert result.original_format == case['input'], f"Failed for {case['input']}: original format mismatch"
    
    def test_imperial_units(self):
        """Test imperial unit parsing (oz, lb)."""
        imperial_cases = self.test_data['test_cases'][1]['test_cases']
        
        for case in imperial_cases:
            result = self.parser.parse_weight(case['input'])
            
            assert result.grams == case['expected_grams'], f"Failed for {case['input']}: expected {case['expected_grams']}, got {result.grams}"
            assert result.confidence >= case['expected_confidence'], f"Failed for {case['input']}: expected confidence >= {case['expected_confidence']}, got {result.confidence}"
            assert result.original_format == case['input'], f"Failed for {case['input']}: original format mismatch"
    
    def test_mixed_formats(self):
        """Test mixed format parsing with parentheses."""
        mixed_cases = self.test_data['test_cases'][2]['test_cases']
        
        for case in mixed_cases:
            result = self.parser.parse_weight(case['input'])
            
            assert result.grams == case['expected_grams'], f"Failed for {case['input']}: expected {case['expected_grams']}, got {result.grams}"
            assert result.confidence >= case['expected_confidence'], f"Failed for {case['input']}: expected confidence >= {case['expected_confidence']}, got {result.confidence}"
            assert result.original_format == case['input'], f"Failed for {case['input']}: original format mismatch"
    
    def test_ambiguous_formats(self):
        """Test ambiguous format parsing with heuristics."""
        ambiguous_cases = self.test_data['test_cases'][3]['test_cases']
        
        for case in ambiguous_cases:
            result = self.parser.parse_weight(case['input'])
            
            assert result.grams == case['expected_grams'], f"Failed for {case['input']}: expected {case['expected_grams']}, got {result.grams}"
            assert result.confidence >= case['expected_confidence'], f"Failed for {case['input']}: expected confidence >= {case['expected_confidence']}, got {result.confidence}"
            assert result.original_format == case['input'], f"Failed for {case['input']}: original format mismatch"
            # Ambiguous formats should have warnings
            assert len(result.parsing_warnings) > 0, f"Failed for {case['input']}: expected parsing warnings for ambiguous format"
    
    def test_edge_cases(self):
        """Test edge cases and malformed input."""
        edge_cases = self.test_data['test_cases'][4]['test_cases']
        
        for case in edge_cases:
            result = self.parser.parse_weight(case['input'])
            
            assert result.grams == case['expected_grams'], f"Failed for {case['input']}: expected {case['expected_grams']}, got {result.grams}"
            assert result.confidence >= case['expected_confidence'], f"Failed for {case['input']}: expected confidence >= {case['expected_confidence']}, got {result.confidence}"
            assert result.original_format == case['input'].strip(), f"Failed for {case['input']}: original format mismatch"
    
    def test_unicode_special(self):
        """Test unicode and special character handling."""
        unicode_cases = self.test_data['test_cases'][5]['test_cases']
        
        for case in unicode_cases:
            result = self.parser.parse_weight(case['input'])
            
            assert result.grams == case['expected_grams'], f"Failed for {case['input']}: expected {case['expected_grams']}, got {result.grams}"
            assert result.confidence >= case['expected_confidence'], f"Failed for {case['input']}: expected confidence >= {case['expected_confidence']}, got {result.grams}"
            assert result.original_format == case['input'], f"Failed for {case['input']}: original format mismatch"
    
    def test_accuracy_requirement(self):
        """Test that accuracy meets >= 99% requirement."""
        all_cases = []
        for category in self.test_data['test_cases']:
            all_cases.extend(category['test_cases'])
        
        successful_parses = 0
        total_cases = len(all_cases)
        
        for case in all_cases:
            result = self.parser.parse_weight(case['input'])
            if result.grams == case['expected_grams']:
                successful_parses += 1
        
        accuracy = successful_parses / total_cases
        min_accuracy = self.test_data['performance_requirements']['min_accuracy']
        
        assert accuracy >= min_accuracy, f"Accuracy {accuracy:.3f} below required {min_accuracy:.3f}"
    
    def test_performance_requirement(self):
        """Test that parsing meets performance requirements."""
        test_inputs = ["250g", "0.25kg", "8.8oz", "1lb", "250", "8.8"]
        max_time_ms = self.test_data['performance_requirements']['max_parsing_time_ms']
        
        for input_str in test_inputs:
            start_time = time.time()
            result = self.parser.parse_weight(input_str)
            end_time = time.time()
            
            parsing_time_ms = (end_time - start_time) * 1000
            assert parsing_time_ms <= max_time_ms, f"Parsing time {parsing_time_ms:.3f}ms exceeds limit {max_time_ms}ms"
    
    def test_batch_processing(self):
        """Test batch processing performance."""
        batch_size = self.test_data['performance_requirements']['batch_processing_target']
        test_inputs = ["250g", "0.25kg", "8.8oz", "1lb"] * (batch_size // 4)
        
        start_time = time.time()
        results = self.parser.batch_parse_weights(test_inputs)
        end_time = time.time()
        
        total_time_ms = (end_time - start_time) * 1000
        avg_time_per_item = total_time_ms / len(test_inputs)
        
        # Should process 1000+ items per second
        items_per_second = 1000 / avg_time_per_item
        assert items_per_second >= 1000, f"Batch processing {items_per_second:.0f} items/sec below 1000 target"
        assert len(results) == len(test_inputs), "Batch processing returned incorrect number of results"
    
    def test_weight_result_to_dict(self):
        """Test WeightResult serialization."""
        result = self.parser.parse_weight("250g")
        result_dict = result.to_dict()
        
        assert isinstance(result_dict, dict), "to_dict() should return a dictionary"
        assert 'grams' in result_dict, "Result dict should contain 'grams'"
        assert 'confidence' in result_dict, "Result dict should contain 'confidence'"
        assert 'original_format' in result_dict, "Result dict should contain 'original_format'"
        assert 'parsing_warnings' in result_dict, "Result dict should contain 'parsing_warnings'"
        assert 'conversion_notes' in result_dict, "Result dict should contain 'conversion_notes'"
    
    def test_error_handling(self):
        """Test error handling for invalid input."""
        invalid_inputs = [None, [], {}, "invalid_format", "g250", "oz8.8"] 

        for invalid_input in invalid_inputs:
            result = self.parser.parse_weight(invalid_input)
            
            assert isinstance(result, WeightResult), "Should return WeightResult even for invalid input"
            assert result.grams == 0, "Invalid input should result in 0 grams"
            assert result.confidence == 0.0, "Invalid input should have 0 confidence"
            assert len(result.parsing_warnings) > 0, "Invalid input should have parsing warnings"
    
    def test_fraction_parsing(self):
        """Test fraction parsing for imperial units."""
        fraction_cases = [
            ("8 1/2 oz", 240),  # 8.5 * 28.3495 = 240.97, rounded to 240
            ("1 1/4 lb", 566),  # 1.25 * 453.592 = 566.99, rounded to 566
            ("2 3/4 oz", 77),   # 2.75 * 28.3495 = 77.96, rounded to 77
        ]
        
        for input_str, expected_grams in fraction_cases:
            result = self.parser.parse_weight(input_str)
            assert result.grams == expected_grams, f"Failed for {input_str}: expected {expected_grams}, got {result.grams}"
            assert result.confidence >= 0.95, f"Failed for {input_str}: confidence too low"
    
    def test_mixed_format_consistency(self):
        """Test mixed format consistency checking."""
        consistent_cases = [
            ("250g (8.8oz)", 250),  # Should use metric
            ("1kg (2.2lb)", 1000),  # Should use metric
        ]
        
        for input_str, expected_grams in consistent_cases:
            result = self.parser.parse_weight(input_str)
            assert result.grams == expected_grams, f"Failed for {input_str}: expected {expected_grams}, got {result.grams}"
            assert result.confidence >= 0.9, f"Failed for {input_str}: confidence too low"
    
    def test_performance_metrics(self):
        """Test performance metrics functionality."""
        metrics = self.parser.get_performance_metrics()
        
        assert isinstance(metrics, dict), "Performance metrics should be a dictionary"
        assert 'parser_version' in metrics, "Metrics should contain parser version"
        assert 'supported_units' in metrics, "Metrics should contain supported units"
        assert 'pattern_count' in metrics, "Metrics should contain pattern count"
        assert 'conversion_factors' in metrics, "Metrics should contain conversion factors"
        
        assert isinstance(metrics['supported_units'], list), "Supported units should be a list"
        assert len(metrics['supported_units']) > 0, "Should support multiple units"
        assert 'g' in metrics['supported_units'], "Should support grams"
        assert 'kg' in metrics['supported_units'], "Should support kilograms"
        assert 'oz' in metrics['supported_units'], "Should support ounces"
        assert 'lb' in metrics['supported_units'], "Should support pounds"
