"""
Performance tests for content hash generation service.
"""

import pytest
import time
from src.parser.content_hash import ContentHashService
from src.config.hash_config import HashConfig


class TestContentHashPerformance:
    """Performance tests for ContentHashService."""
    
    def test_batch_hash_generation_performance(self):
        """Test batch hash generation performance for 100+ artifacts."""
        config = HashConfig()
        service = ContentHashService(config)
        
        # Generate 100 test artifacts
        artifacts = [
            {
                'title': f'Coffee {i}',
                'description': f'Great coffee {i} with high quality beans',
                'weight_g': 250 + i,
                'roast_level': 'medium',
                'process': 'washed',
                'grind_type': 'whole_bean',
                'species': 'arabica'
            }
            for i in range(100)
        ]
        
        # Measure processing time
        start_time = time.time()
        results = service.generate_hashes_batch(artifacts)
        end_time = time.time()
        
        processing_time = end_time - start_time
        
        # Verify performance requirements
        assert processing_time < 1.0, f"Batch hash generation took {processing_time:.2f}s, expected < 1.0s"
        assert len(results) == 100, "Should process all 100 artifacts"
        
        # Verify results quality
        successful_hashes = sum(1 for r in results if r.content_hash and r.raw_hash)
        success_rate = successful_hashes / 100
        assert success_rate == 1.0, f"Success rate {success_rate:.2%} should be 100%"
        
        print(f"Batch hash generation: {processing_time:.2f}s for 100 artifacts ({processing_time*10:.1f}ms per artifact)")
    
    def test_individual_hash_generation_performance(self):
        """Test individual hash generation performance."""
        config = HashConfig()
        service = ContentHashService(config)
        
        artifact = {
            'title': 'Test Coffee',
            'description': 'A great coffee with high quality beans',
            'weight_g': 250,
            'roast_level': 'medium',
            'process': 'washed',
            'grind_type': 'whole_bean',
            'species': 'arabica'
        }
        
        # Measure individual hash generation time
        start_time = time.time()
        for _ in range(100):
            result = service.generate_hashes(artifact)
        end_time = time.time()
        
        avg_time = (end_time - start_time) / 100
        
        # Verify individual hash generation is fast
        assert avg_time < 0.01, f"Individual hash generation took {avg_time*1000:.1f}ms, expected < 10ms"
        
        print(f"Individual hash generation: {avg_time*1000:.1f}ms per artifact")
    
    def test_hash_consistency_performance(self):
        """Test hash consistency performance."""
        config = HashConfig()
        service = ContentHashService(config)
        
        artifact = {
            'title': 'Test Coffee',
            'description': 'A great coffee with high quality beans',
            'weight_g': 250
        }
        
        # Generate hash multiple times
        start_time = time.time()
        hashes = []
        for _ in range(1000):
            result = service.generate_hashes(artifact)
            hashes.append(result.content_hash)
        end_time = time.time()
        
        processing_time = end_time - start_time
        
        # Verify all hashes are identical
        assert all(h == hashes[0] for h in hashes), "All hashes should be identical for same artifact"
        assert processing_time < 5.0, f"Hash consistency test took {processing_time:.2f}s, expected < 5.0s"
        
        print(f"Hash consistency: {processing_time:.2f}s for 1000 identical artifacts")
    
    def test_collision_detection_performance(self):
        """Test hash collision detection performance."""
        config = HashConfig()
        service = ContentHashService(config)
        
        # Generate hashes for different artifacts
        artifacts = [
            {'title': f'Coffee {i}', 'description': f'Description {i}'}
            for i in range(100)
        ]
        
        start_time = time.time()
        results = service.generate_hashes_batch(artifacts)
        end_time = time.time()
        
        processing_time = end_time - start_time
        
        # Test collision detection
        hashes = [r.content_hash for r in results]
        collision_checks = 0
        for i, hash1 in enumerate(hashes):
            for j, hash2 in enumerate(hashes[i+1:], i+1):
                collision = service.detect_hash_collision(hash1, [hash2])
                collision_checks += 1
        
        total_time = time.time() - start_time
        
        # Verify collision detection is efficient
        assert total_time < 2.0, f"Collision detection took {total_time:.2f}s, expected < 2.0s"
        assert collision_checks == 4950, "Should check all pairwise combinations"
        
        print(f"Collision detection: {total_time:.2f}s for {collision_checks} checks")
    
    def test_memory_usage_hash_generation(self):
        """Test memory usage during hash generation."""
        import psutil
        import os
        
        config = HashConfig()
        service = ContentHashService(config)
        
        # Get initial memory usage
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Generate 500 test artifacts (stress test)
        artifacts = [
            {
                'title': f'Coffee {i}',
                'description': f'Great coffee {i} with high quality beans and excellent flavor profile',
                'weight_g': 250 + i,
                'roast_level': 'medium',
                'process': 'washed',
                'grind_type': 'whole_bean',
                'species': 'arabica'
            }
            for i in range(500)
        ]
        
        # Process batch
        results = service.generate_hashes_batch(artifacts)
        
        # Get final memory usage
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Verify memory usage is reasonable
        assert memory_increase < 100, f"Memory increase {memory_increase:.1f}MB should be < 100MB"
        assert len(results) == 500, "Should process all 500 artifacts"
        
        print(f"Memory usage: {memory_increase:.1f}MB increase for 500 artifacts")
