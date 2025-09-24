"""
Integration tests for roast and process parsers working together.

Tests comprehensive integration functionality including:
- Combined roast and process parsing
- Batch processing with both parsers
- Performance requirements
- Error handling integration
- Real-world usage scenarios
"""

import pytest
from src.parser.roast_parser import RoastLevelParser, RoastResult
from src.parser.process_parser import ProcessMethodParser, ProcessResult


class TestRoastProcessIntegration:
    """Test suite for integrated roast and process parsing."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.roast_parser = RoastLevelParser()
        self.process_parser = ProcessMethodParser()
    
    def test_combined_parsing(self):
        """Test combined roast and process parsing."""
        # Test data with both roast and process information
        test_data = [
            {
                'roast': 'Medium Roast',
                'process': 'Washed Process',
                'expected_roast': 'medium',
                'expected_process': 'washed'
            },
            {
                'roast': 'Light Roast',
                'process': 'Natural Process',
                'expected_roast': 'light',
                'expected_process': 'natural'
            },
            {
                'roast': 'Dark Roast',
                'process': 'Honey Process',
                'expected_roast': 'dark',
                'expected_process': 'honey'
            },
            {
                'roast': 'Light-Medium Roast',
                'process': 'Semi-Washed',
                'expected_roast': 'light-medium',
                'expected_process': 'honey'
            },
            {
                'roast': 'Medium-Dark Roast',
                'process': 'Pulped Natural',
                'expected_roast': 'medium-dark',
                'expected_process': 'honey'
            }
        ]
        
        for data in test_data:
            roast_result = self.roast_parser.parse_roast_level(data['roast'])
            process_result = self.process_parser.parse_process_method(data['process'])
            
            assert roast_result.enum_value == data['expected_roast']
            assert process_result.enum_value == data['expected_process']
            assert isinstance(roast_result, RoastResult)
            assert isinstance(process_result, ProcessResult)
    
    def test_batch_combined_parsing(self):
        """Test batch parsing with both parsers."""
        roast_inputs = ['Light Roast', 'Medium Roast', 'Dark Roast', 'Light-Medium', 'Medium-Dark']
        process_inputs = ['Washed Process', 'Natural Process', 'Honey Process', 'Semi-Washed', 'Pulped Natural']
        
        roast_results = self.roast_parser.batch_parse_roast_levels(roast_inputs)
        process_results = self.process_parser.batch_parse_process_methods(process_inputs)
        
        assert len(roast_results) == len(roast_inputs)
        assert len(process_results) == len(process_inputs)
        
        # Verify results are properly paired
        for i, (roast_result, process_result) in enumerate(zip(roast_results, process_results)):
            assert isinstance(roast_result, RoastResult)
            assert isinstance(process_result, ProcessResult)
            assert roast_result.original_text == roast_inputs[i]
            assert process_result.original_text == process_inputs[i]
    
    def test_integration_performance(self):
        """Test integration performance requirements."""
        import time
        
        # Test combined parsing performance
        roast_inputs = ['Light Roast', 'Medium Roast', 'Dark Roast'] * 100
        process_inputs = ['Washed Process', 'Natural Process', 'Honey Process'] * 100
        
        start_time = time.time()
        roast_results = self.roast_parser.batch_parse_roast_levels(roast_inputs)
        process_results = self.process_parser.batch_parse_process_methods(process_inputs)
        end_time = time.time()
        
        integration_time_ms = (end_time - start_time) * 1000
        assert integration_time_ms <= 2000, f"Integration parsing time {integration_time_ms:.2f}ms exceeds 2000ms requirement"
        
        assert len(roast_results) == len(roast_inputs)
        assert len(process_results) == len(process_inputs)
    
    def test_error_handling_integration(self):
        """Test error handling in integrated parsing."""
        # Test with invalid inputs
        invalid_roast = "Invalid Roast"
        invalid_process = "Invalid Process"
        
        roast_result = self.roast_parser.parse_roast_level(invalid_roast)
        process_result = self.process_parser.parse_process_method(invalid_process)
        
        assert roast_result.enum_value == 'unknown'
        assert process_result.enum_value == 'other'
        assert roast_result.confidence == 0.0
        assert process_result.confidence == 0.0
        assert len(roast_result.parsing_warnings) > 0
        assert len(process_result.parsing_warnings) > 0
    
    def test_real_world_scenarios(self):
        """Test real-world usage scenarios."""
        # Scenario 1: Coffee product with both roast and process
        coffee_data = {
            'roast': 'Medium Roast',
            'process': 'Washed Process',
            'description': 'Medium roast coffee with washed process'
        }
        
        roast_result = self.roast_parser.parse_roast_level(coffee_data['roast'])
        process_result = self.process_parser.parse_process_method(coffee_data['process'])
        
        assert roast_result.enum_value == 'medium'
        assert process_result.enum_value == 'washed'
        assert roast_result.confidence >= 0.95
        assert process_result.confidence >= 0.95
        
        # Scenario 2: Light-Medium format
        light_medium_data = {
            'roast': 'Light-Medium Roast',
            'process': 'Semi-Washed',
            'description': 'Light-medium roast and semi-washed process'
        }
        
        roast_result = self.roast_parser.parse_roast_level(light_medium_data['roast'])
        process_result = self.process_parser.parse_process_method(light_medium_data['process'])
        
        assert roast_result.enum_value == 'light-medium'
        assert process_result.enum_value == 'honey'
        assert roast_result.confidence >= 0.9
        assert process_result.confidence >= 0.9
        
        # Scenario 3: Ambiguous format
        ambiguous_data = {
            'roast': 'Medium Roast',
            'process': 'Process',
            'description': 'Ambiguous roast and process'
        }

        roast_result = self.roast_parser.parse_roast_level(ambiguous_data['roast'])                                                                             
        process_result = self.process_parser.parse_process_method(ambiguous_data['process'])                                                                    

        assert roast_result.enum_value == 'medium'
        assert process_result.enum_value == 'other'  # Generic "Process" returns "other"
        assert roast_result.confidence >= 0.7
        assert process_result.confidence == 0.0  # Generic "Process" has no confidence
        # "Medium Roast" is explicitly matched, no warnings
        assert len(roast_result.parsing_warnings) == 0
        assert len(process_result.parsing_warnings) > 0
    
    def test_confidence_scoring_integration(self):
        """Test confidence scoring in integrated parsing."""
        # High confidence for explicit patterns
        roast_result = self.roast_parser.parse_roast_level('Medium Roast')
        process_result = self.process_parser.parse_process_method('Washed Process')
        
        assert roast_result.confidence >= 0.95
        assert process_result.confidence >= 0.95
        
        # High confidence for explicit patterns
        roast_result = self.roast_parser.parse_roast_level('Medium-Dark Roast')
        process_result = self.process_parser.parse_process_method('Washed Process')
        
        assert roast_result.confidence >= 0.9
        assert process_result.confidence >= 0.9
        
        # Lower confidence for ambiguous patterns
        roast_result = self.roast_parser.parse_roast_level('Medium')
        process_result = self.process_parser.parse_process_method('Process')    

        assert roast_result.confidence >= 0.7
        assert process_result.confidence == 0.0  # Generic "Process" returns 0.0 confidence
    
    def test_parsing_warnings_integration(self):
        """Test parsing warnings in integrated parsing."""
        # Test warnings for ambiguous input
        roast_result = self.roast_parser.parse_roast_level('Unknown Roast')     
        process_result = self.process_parser.parse_process_method('Unknown Process')                                                                            

        # "Unknown Roast" is explicitly matched as "unknown", no warnings
        # "Unknown Process" is explicitly matched as "other", no warnings
        assert len(roast_result.parsing_warnings) == 0
        assert len(process_result.parsing_warnings) == 0
        
        # Test no warnings for explicit patterns
        roast_result = self.roast_parser.parse_roast_level('Medium Roast')
        process_result = self.process_parser.parse_process_method('Washed Process')
        
        assert len(roast_result.parsing_warnings) == 0
        assert len(process_result.parsing_warnings) == 0
    
    def test_conversion_notes_integration(self):
        """Test conversion notes in integrated parsing."""
        # Test notes for explicit patterns
        roast_result = self.roast_parser.parse_roast_level('Medium Roast')
        process_result = self.process_parser.parse_process_method('Washed Process')
        
        assert 'Matched explicit' in roast_result.conversion_notes
        assert 'Matched explicit' in process_result.conversion_notes
        
        # Test notes for ambiguous patterns
        roast_result = self.roast_parser.parse_roast_level('Unknown Roast')     
        process_result = self.process_parser.parse_process_method('Unknown Process')                                                                            

        # Both are explicitly matched
        assert 'Matched explicit' in roast_result.conversion_notes
        assert 'Matched explicit' in process_result.conversion_notes
    
    def test_result_serialization_integration(self):
        """Test result serialization in integrated parsing."""
        roast_result = self.roast_parser.parse_roast_level('Medium Roast')
        process_result = self.process_parser.parse_process_method('Washed Process')
        
        # Test to_dict serialization
        roast_dict = roast_result.to_dict()
        process_dict = process_result.to_dict()
        
        assert isinstance(roast_dict, dict)
        assert isinstance(process_dict, dict)
        assert roast_dict['enum_value'] == 'medium'
        assert process_dict['enum_value'] == 'washed'
        assert roast_dict['confidence'] >= 0.95
        assert process_dict['confidence'] >= 0.95
        
        # Test serialization for storage
        storage_data = {
            'roast_level': roast_dict,
            'process_method': process_dict
        }
        
        assert storage_data['roast_level']['enum_value'] == 'medium'
        assert storage_data['process_method']['enum_value'] == 'washed'
    
    def test_batch_processing_integration(self):
        """Test batch processing with both parsers."""
        # Test with large batch
        roast_inputs = ['Light Roast', 'Medium Roast', 'Dark Roast'] * 100
        process_inputs = ['Washed Process', 'Natural Process', 'Honey Process'] * 100
        
        roast_results = self.roast_parser.batch_parse_roast_levels(roast_inputs)
        process_results = self.process_parser.batch_parse_process_methods(process_inputs)
        
        assert len(roast_results) == len(roast_inputs)
        assert len(process_results) == len(process_inputs)
        
        # Test combined results
        combined_results = []
        for roast_result, process_result in zip(roast_results, process_results):
            combined_result = {
                'roast_level': roast_result.to_dict(),
                'process_method': process_result.to_dict()
            }
            combined_results.append(combined_result)
        
        assert len(combined_results) == len(roast_inputs)
        assert all('roast_level' in result for result in combined_results)
        assert all('process_method' in result for result in combined_results)
    
    def test_performance_metrics_integration(self):
        """Test performance metrics for both parsers."""
        roast_metrics = self.roast_parser.get_performance_metrics()
        process_metrics = self.process_parser.get_performance_metrics()
        
        assert roast_metrics['parser_version'] == '1.0.0'
        assert process_metrics['parser_version'] == '1.0.0'
        assert len(roast_metrics['supported_roast_levels']) == 6
        assert len(process_metrics['supported_process_methods']) == 5
        
        # Test combined metrics
        combined_metrics = {
            'roast_parser': roast_metrics,
            'process_parser': process_metrics
        }
        
        assert 'roast_parser' in combined_metrics
        assert 'process_parser' in combined_metrics
        assert combined_metrics['roast_parser']['parser_version'] == '1.0.0'
        assert combined_metrics['process_parser']['parser_version'] == '1.0.0'
    
    def test_edge_cases_integration(self):
        """Test edge cases in integrated parsing."""
        # Test with empty inputs
        roast_result = self.roast_parser.parse_roast_level('')
        process_result = self.process_parser.parse_process_method('')
        
        assert roast_result.enum_value == 'unknown'
        assert process_result.enum_value == 'other'
        assert roast_result.confidence == 0.0
        assert process_result.confidence == 0.0
        
        # Test with None inputs
        roast_result = self.roast_parser.parse_roast_level(None)
        process_result = self.process_parser.parse_process_method(None)
        
        assert roast_result.enum_value == 'unknown'
        assert process_result.enum_value == 'other'
        assert roast_result.confidence == 0.0
        assert process_result.confidence == 0.0
        
        # Test with invalid inputs
        roast_result = self.roast_parser.parse_roast_level('Invalid Roast')
        process_result = self.process_parser.parse_process_method('Invalid Process')
        
        assert roast_result.enum_value == 'unknown'
        assert process_result.enum_value == 'other'
        assert roast_result.confidence == 0.0
        assert process_result.confidence == 0.0
        assert len(roast_result.parsing_warnings) > 0
        assert len(process_result.parsing_warnings) > 0
    
    def test_coffee_context_integration(self):
        """Test coffee context heuristics in integrated parsing."""
        # Test with coffee context
        roast_result = self.roast_parser.parse_roast_level('1 coffee bean')
        process_result = self.process_parser.parse_process_method('1 coffee bean')
        
        # "1 coffee bean" doesn't contain heuristic keywords, returns "unknown"/"other"
        assert roast_result.enum_value == 'unknown'
        assert process_result.enum_value == 'other'
        assert roast_result.confidence == 0.0  # No confidence for unrecognized input
        assert process_result.confidence == 0.0  # No confidence for unrecognized input
        
        # Test without coffee context
        roast_result = self.roast_parser.parse_roast_level('Light Roast')
        process_result = self.process_parser.parse_process_method('Washed Process')
        
        assert roast_result.enum_value == 'light'
        assert process_result.enum_value == 'washed'
        assert roast_result.confidence >= 0.7  # Lower confidence without coffee context
        assert process_result.confidence >= 0.7  # Lower confidence without coffee context
    
    def test_accuracy_requirements_integration(self):
        """Test accuracy requirements for integrated parsing."""
        # Test with known good data
        test_cases = [
            ('Medium Roast', 'Washed Process', 'medium', 'washed'),
            ('Light Roast', 'Natural Process', 'light', 'natural'),
            ('Dark Roast', 'Honey Process', 'dark', 'honey'),
            ('Light-Medium Roast', 'Semi-Washed', 'light-medium', 'honey'),
            ('Medium-Dark Roast', 'Pulped Natural', 'medium-dark', 'honey'),
        ]
        
        successful_parses = 0
        total_parses = len(test_cases)
        
        for roast_input, process_input, expected_roast, expected_process in test_cases:
            roast_result = self.roast_parser.parse_roast_level(roast_input)
            process_result = self.process_parser.parse_process_method(process_input)
            
            if (roast_result.enum_value == expected_roast and 
                process_result.enum_value == expected_process):
                successful_parses += 1
        
        accuracy = successful_parses / total_parses
        assert accuracy >= 0.95, f"Integration accuracy {accuracy:.2%} is below required 95%"
    
    def test_memory_efficiency_integration(self):
        """Test memory efficiency in integrated parsing."""
        import sys
        
        # Test memory usage with large batches
        roast_inputs = ['Light Roast', 'Medium Roast', 'Dark Roast'] * 1000
        process_inputs = ['Washed Process', 'Natural Process', 'Honey Process'] * 1000
        
        # Get initial memory usage
        initial_memory = sys.getsizeof(roast_inputs) + sys.getsizeof(process_inputs)
        
        # Parse with both parsers
        roast_results = self.roast_parser.batch_parse_roast_levels(roast_inputs)
        process_results = self.process_parser.batch_parse_process_methods(process_inputs)
        
        # Get final memory usage
        final_memory = (sys.getsizeof(roast_results) + 
                        sys.getsizeof(process_results) + 
                        sys.getsizeof(roast_inputs) + 
                        sys.getsizeof(process_inputs))
        
        # Memory usage should be reasonable
        memory_ratio = final_memory / initial_memory
        assert memory_ratio <= 10, f"Memory usage ratio {memory_ratio:.2f} exceeds 10x requirement"
        
        # Results should be valid
        assert len(roast_results) == len(roast_inputs)
        assert len(process_results) == len(process_inputs)
        assert all(isinstance(result, RoastResult) for result in roast_results)
        assert all(isinstance(result, ProcessResult) for result in process_results)
