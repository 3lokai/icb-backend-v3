"""
Performance tests for sensory parameter parsing service.
"""

import pytest
import time
from src.parser.sensory_parser import SensoryParserService
from src.config.sensory_config import SensoryConfig


class TestSensoryParserPerformance:
    """Performance tests for SensoryParserService."""
    
    def test_batch_processing_performance(self):
        """Test batch processing performance for 100+ products."""
        config = SensoryConfig()
        parser = SensoryParserService(config)
        
        # Generate 100 test descriptions
        descriptions = [
            f"Coffee {i}: High acidity, full body, sweet caramel notes, medium bitterness, long aftertaste, high clarity"
            for i in range(100)
        ]
        
        # Measure processing time
        start_time = time.time()
        results = parser.parse_sensory_batch(descriptions)
        end_time = time.time()
        
        processing_time = end_time - start_time
        
        # Verify performance requirements
        assert processing_time < 4.0, f"Batch processing took {processing_time:.2f}s, expected < 4.0s"
        assert len(results) == 100, "Should process all 100 descriptions"
        
        # Verify results quality
        successful_extractions = sum(1 for r in results if r.acidity is not None or r.body is not None)
        success_rate = successful_extractions / 100
        assert success_rate > 0.8, f"Success rate {success_rate:.2%} should be > 80%"
        
        print(f"Batch processing: {processing_time:.2f}s for 100 products ({processing_time*10:.1f}ms per product)")
    
    def test_memory_usage_batch_processing(self):
        """Test memory usage during batch processing."""
        import psutil
        import os
        
        config = SensoryConfig()
        parser = SensoryParserService(config)
        
        # Get initial memory usage
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Generate 200 test descriptions (stress test)
        descriptions = [
            f"Coffee {i}: High acidity, full body, sweet caramel notes, medium bitterness, long aftertaste, high clarity"
            for i in range(200)
        ]
        
        # Process batch
        results = parser.parse_sensory_batch(descriptions)
        
        # Get final memory usage
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Verify memory usage is reasonable
        assert memory_increase < 200, f"Memory increase {memory_increase:.1f}MB should be < 200MB"
        assert len(results) == 200, "Should process all 200 descriptions"
        
        print(f"Memory usage: {memory_increase:.1f}MB increase for 200 products")
    
    def test_individual_parsing_performance(self):
        """Test individual parsing performance."""
        config = SensoryConfig()
        parser = SensoryParserService(config)
        
        description = "This coffee has high acidity, full body, sweet caramel notes, medium bitterness, long aftertaste, and high clarity"
        
        # Measure individual parsing time
        start_time = time.time()
        for _ in range(100):
            result = parser.parse_sensory(description)
        end_time = time.time()
        
        avg_time = (end_time - start_time) / 100
        
        # Verify individual parsing is fast
        assert avg_time < 0.1, f"Individual parsing took {avg_time*1000:.1f}ms, expected < 100ms"
        
        print(f"Individual parsing: {avg_time*1000:.1f}ms per product")
    
    def test_confidence_calculation_performance(self):
        """Test confidence calculation performance."""
        config = SensoryConfig()
        parser = SensoryParserService(config)
        
        # Test with various description lengths
        descriptions = [
            "High acidity coffee",  # Short
            "This coffee has high acidity, full body, sweet caramel notes, medium bitterness, long aftertaste, and high clarity",  # Long
            "Medium acidity, balanced body, moderate sweetness, low bitterness, short aftertaste, medium clarity"  # Medium
        ]
        
        start_time = time.time()
        for description in descriptions:
            result = parser.parse_sensory(description)
            assert result.confidence in ["high", "medium", "low"]
        end_time = time.time()
        
        processing_time = end_time - start_time
        assert processing_time < 1.0, f"Confidence calculation took {processing_time:.2f}s, expected < 1.0s"
        
        print(f"Confidence calculation: {processing_time:.3f}s for 3 descriptions")
    
    def test_stats_tracking_performance(self):
        """Test statistics tracking performance."""
        config = SensoryConfig()
        parser = SensoryParserService(config)
        
        # Process many descriptions
        descriptions = [f"Coffee {i}: High acidity" for i in range(1000)]
        
        start_time = time.time()
        results = parser.parse_sensory_batch(descriptions)
        end_time = time.time()
        
        processing_time = end_time - start_time
        
        # Verify stats are tracked efficiently
        stats = parser.get_stats()
        assert stats['total_processed'] == 1000
        assert processing_time < 10.0, f"Stats tracking took {processing_time:.2f}s, expected < 10.0s"
        
        print(f"Stats tracking: {processing_time:.2f}s for 1000 products")
