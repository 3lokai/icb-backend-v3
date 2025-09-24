"""
Integration tests for weight parser with real product data samples.

Tests weight parser integration with actual Shopify and WooCommerce data.
"""

import json
import pytest
from pathlib import Path
from src.parser.weight_parser import WeightParser


class TestWeightParserIntegration:
    """Integration tests for WeightParser with real data."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.parser = WeightParser()
        
        # Load real sample data
        self.samples_dir = Path(__file__).parent.parent.parent / "data" / "samples"
        self.shopify_samples = list((self.samples_dir / "shopify").glob("*.json"))
        self.woocommerce_samples = list((self.samples_dir / "woocommerce").glob("*.json"))
    
    def test_shopify_data_integration(self):
        """Test weight parser with real Shopify data."""
        for sample_file in self.shopify_samples:
            with open(sample_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Extract weight data from Shopify variants
            if 'products' in data:
                for product in data['products']:
                    variants = product.get('variants', [])
                    for variant in variants:
                        # Check for grams field (Shopify standard)
                        grams = variant.get('grams')
                        if grams is not None and grams > 0:
                            # Test parsing the grams value
                            result = self.parser.parse_weight(grams)
                            
                            # Should parse successfully
                            assert isinstance(result.grams, int), f"Failed to parse grams {grams} from {sample_file.name}"
                            assert result.grams >= 0, f"Negative grams {result.grams} from {sample_file.name}"
                            
                            # For explicit grams, confidence should be high
                            if isinstance(grams, (int, float)) and grams > 0:
                                assert result.confidence >= 0.7, f"Low confidence {result.confidence} for explicit grams {grams}"
    
    def test_woocommerce_data_integration(self):
        """Test weight parser with real WooCommerce data."""
        for sample_file in self.woocommerce_samples:
            with open(sample_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # WooCommerce data structure is different
            if isinstance(data, list):
                for product in data:
                    # Check for weight in attributes or variations
                    attributes = product.get('attributes', [])
                    for attr in attributes:
                        if attr.get('name', '').lower() in ['weight', 'size', 'package']:
                            weight_value = attr.get('options', [None])[0]
                            if weight_value:
                                result = self.parser.parse_weight(weight_value)
                                
                                # Should parse successfully
                                assert isinstance(result.grams, int), f"Failed to parse weight {weight_value} from {sample_file.name}"
                                assert result.grams >= 0, f"Negative grams {result.grams} from {sample_file.name}"
    
    def test_batch_processing_real_data(self):
        """Test batch processing with real data samples."""
        all_weight_inputs = []
        
        # Collect weight data from Shopify samples
        for sample_file in self.shopify_samples:
            with open(sample_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if 'products' in data:
                for product in data['products']:
                    variants = product.get('variants', [])
                    for variant in variants:
                        grams = variant.get('grams')
                        if grams is not None and grams > 0:
                            all_weight_inputs.append(grams)
        
        # Collect weight data from WooCommerce samples
        for sample_file in self.woocommerce_samples:
            with open(sample_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if isinstance(data, list):
                for product in data:
                    attributes = product.get('attributes', [])
                    for attr in attributes:
                        if attr.get('name', '').lower() in ['weight', 'size', 'package']:
                            weight_value = attr.get('options', [None])[0]
                            if weight_value:
                                all_weight_inputs.append(weight_value)
        
        # Test batch processing
        if all_weight_inputs:
            results = self.parser.batch_parse_weights(all_weight_inputs)
            
            assert len(results) == len(all_weight_inputs), "Batch processing returned incorrect number of results"
            
            # Check that most results are successful
            successful_results = [r for r in results if r.grams > 0]
            success_rate = len(successful_results) / len(results) if results else 0
            
            # Should have reasonable success rate with real data
            assert success_rate >= 0.5, f"Success rate {success_rate:.2f} too low for real data"
    
    def test_error_handling_real_data(self):
        """Test error handling with real data edge cases."""
        # Test with various real data edge cases
        edge_cases = [
            None,
            "",
            "0",
            "unknown",
            "N/A",
            "TBD",
            "varies",
            "multiple",
            "250g, 500g",  # Multiple values
            "250g - 500g",  # Range
        ]
        
        for edge_case in edge_cases:
            result = self.parser.parse_weight(edge_case)
            
            # Should handle gracefully without crashing
            assert isinstance(result.grams, int), f"Failed to handle edge case: {edge_case}"
            assert result.grams >= 0, f"Negative grams for edge case: {edge_case}"
            assert 0.0 <= result.confidence <= 1.0, f"Invalid confidence for edge case: {edge_case}"
    
    def test_performance_with_real_data(self):
        """Test performance with real data volume."""
        import time
        
        # Create a large dataset based on real data patterns
        test_inputs = []
        
        # Add common coffee weights
        common_weights = [
            "250g", "500g", "1kg", "0.25kg", "0.5kg",
            "8.8oz", "12oz", "1lb", "0.5lb",
            "250", "500", "1000", "8.8", "12", "1"
        ]
        
        # Create batch of 1000 items
        for _ in range(100):
            test_inputs.extend(common_weights)
        
        # Test batch processing performance
        start_time = time.time()
        results = self.parser.batch_parse_weights(test_inputs)
        end_time = time.time()
        
        total_time = end_time - start_time
        items_per_second = len(test_inputs) / total_time
        
        # Should process at least 1000 items per second
        assert items_per_second >= 1000, f"Performance {items_per_second:.0f} items/sec below 1000 target"
        assert len(results) == len(test_inputs), "Batch processing returned incorrect number of results"
    
    def test_confidence_scoring_real_data(self):
        """Test confidence scoring with real data patterns."""
        # Test cases with known confidence levels
        test_cases = [
            ("250g", 0.95),  # Explicit unit, high confidence
            ("0.25kg", 0.95),  # Explicit unit, high confidence
            ("8.8oz", 0.95),  # Explicit unit, high confidence
            ("250", 0.7),  # Ambiguous, medium confidence
            ("8.8", 0.5),  # Ambiguous, low confidence
        ]
        
        for input_str, min_confidence in test_cases:
            result = self.parser.parse_weight(input_str)
            
            assert result.confidence >= min_confidence, f"Confidence {result.confidence} below expected {min_confidence} for {input_str}"
            assert result.grams > 0, f"Should parse {input_str} successfully"
    
    def test_warning_generation_real_data(self):
        """Test warning generation with real data edge cases."""
        # Test cases that should generate warnings
        warning_cases = [
            "250",  # Ambiguous
            "8.8",  # Ambiguous
            "1.5",  # Ambiguous
            "g250",  # Malformed
            "oz8.8",  # Malformed
        ]
        
        for input_str in warning_cases:
            result = self.parser.parse_weight(input_str)
            
            # Should have warnings for ambiguous or malformed input
            if input_str in ["250", "8.8", "1.5"]:
                assert len(result.parsing_warnings) > 0, f"Should have warnings for ambiguous input: {input_str}"
            elif input_str in ["g250", "oz8.8"]:
                assert len(result.parsing_warnings) > 0, f"Should have warnings for malformed input: {input_str}"
    
    def test_conversion_accuracy_real_data(self):
        """Test conversion accuracy with real data values."""
        # Test known conversions
        conversion_cases = [
            ("250g", 250),
            ("0.25kg", 250),
            ("8.8oz", 249),  # 8.8 * 28.3495 = 249.47, rounded to 249
            ("1lb", 453),  # 1 * 453.592 = 453.592, rounded to 453
            ("500mg", 0),  # 500 * 0.001 = 0.5, rounded to 0
        ]
        
        for input_str, expected_grams in conversion_cases:
            result = self.parser.parse_weight(input_str)
            
            assert result.grams == expected_grams, f"Conversion failed for {input_str}: expected {expected_grams}, got {result.grams}"
            assert result.confidence >= 0.95, f"Confidence too low for explicit unit: {input_str}"
