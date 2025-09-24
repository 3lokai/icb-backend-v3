"""
Performance tests for price-only image guards.

Tests the performance impact of image guards to ensure
price-only runs maintain speed without image overhead.
"""

import pytest
import time
import psutil
import os
from typing import Dict, Any, List
from unittest.mock import Mock, patch

from src.images.processing_guard import ImageProcessingGuard
from src.validator.artifact_mapper import ArtifactMapper
from src.validator.database_integration import DatabaseIntegration
from src.validator.rpc_client import RPCClient
from src.validator.models import ArtifactModel, ProductModel, VariantModel, PriceModel, ImageModel


class TestPriceOnlyPerformance:
    """Performance tests for price-only image guards."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_supabase_client = Mock()
        
        # Create test artifact with multiple images for performance testing
        self.test_artifact = self._create_large_test_artifact()
    
    def _create_large_test_artifact(self) -> ArtifactModel:
        """Create a test artifact with many images for performance testing."""
        # Create multiple mock images
        images = []
        for i in range(10):  # 10 images for performance testing
            images.append(ImageModel(
                url=f"https://example.com/image{i}.jpg",
                alt_text=f"Test image {i}",
                width=800,
                height=600,
                order=i,
                source_id=f"test_source_{i}"
            ))
        
        # Create mock product with images
        product = ProductModel(
            platform_product_id="test_product_123",
            name="Test Coffee",
            description="Test coffee description",
            images=images
        )
        
        # Create mock variant
        variant = VariantModel(
            platform_variant_id="test_variant_123",
            platform_product_id="test_product_123",
            name="Test Variant",
            weight="250g",
            price=25.99,
            currency="USD"
        )
        
        # Create mock price
        price = PriceModel(
            platform_variant_id="test_variant_123",
            price=25.99,
            currency="USD"
        )
        
        # Create artifact
        artifact = ArtifactModel(
            platform="test_platform",
            platform_product_id="test_product_123",
            scraped_at="2025-01-12T10:00:00Z",
            product=product,
            variants=[variant],
            prices=[price]
        )
        
        return artifact
    
    def test_guard_overhead_performance(self):
        """Test that guard operations have minimal overhead."""
        guard = ImageProcessingGuard(metadata_only=True)
        
        # Measure time for guard operations
        start_time = time.time()
        
        for i in range(10000):  # 10,000 operations
            guard.check_image_processing_allowed(f"operation_{i}")
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should complete in less than 1 second for 10,000 operations
        assert duration < 1.0
        
        # Calculate operations per second
        ops_per_second = 10000 / duration
        assert ops_per_second > 10000  # Should handle at least 10k ops/sec
    
    def test_guard_memory_usage(self):
        """Test that guards have minimal memory impact."""
        # Get initial memory usage
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # Create multiple guards
        guards = []
        for i in range(1000):  # 1000 guards
            guard = ImageProcessingGuard(metadata_only=(i % 2 == 0))
            guards.append(guard)
        
        # Get memory usage after creating guards
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (less than 100MB for 1000 guards)
        assert memory_increase < 100 * 1024 * 1024  # 100MB
        
        # Clean up
        del guards
    
    def test_artifact_mapper_performance_price_only(self):
        """Test ArtifactMapper performance with price-only runs."""
        # Create mapper with metadata_only=True
        mapper = ArtifactMapper(metadata_only=True)
        
        # Measure time for multiple mappings
        start_time = time.time()
        
        for i in range(100):  # 100 mappings
            result = mapper.map_artifact_to_rpc_payloads(
                artifact=self.test_artifact,
                roaster_id="test_roaster",
                metadata_only=True
            )
            assert result['metadata_only'] is True
            assert result['images'] == []  # Should be empty
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should complete in reasonable time
        assert duration < 5.0  # Less than 5 seconds for 100 mappings
        
        # Calculate mappings per second
        mappings_per_second = 100 / duration
        assert mappings_per_second > 10  # At least 10 mappings per second
    
    def test_artifact_mapper_performance_full_pipeline(self):
        """Test ArtifactMapper performance with full pipeline runs."""
        # Create mapper with metadata_only=False
        mapper = ArtifactMapper(metadata_only=False)
        
        # Mock the deduplication service to avoid actual processing
        mapper.deduplication_service = Mock()
        mapper.deduplication_service.process_batch_with_deduplication = Mock(
            return_value=[
                {
                    'url': f'https://example.com/image{i}.jpg',
                    'alt': f'Test image {i}',
                    'width': 800,
                    'height': 600,
                    'sort_order': i,
                    'source_raw': {'source_id': f'test_source_{i}'},
                    'content_hash': f'test_hash_{i}',
                    'imagekit_url': f'https://ik.imagekit.io/test/image{i}.jpg'
                }
                for i in range(10)
            ]
        )
        
        # Measure time for multiple mappings
        start_time = time.time()
        
        for i in range(50):  # 50 mappings (fewer due to image processing)
            result = mapper.map_artifact_to_rpc_payloads(
                artifact=self.test_artifact,
                roaster_id="test_roaster",
                metadata_only=False
            )
            assert result['metadata_only'] is False
            assert len(result['images']) > 0  # Should have images
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should complete in reasonable time
        assert duration < 10.0  # Less than 10 seconds for 50 mappings
        
        # Calculate mappings per second
        mappings_per_second = 50 / duration
        assert mappings_per_second > 5  # At least 5 mappings per second
    
    def test_database_integration_performance_price_only(self):
        """Test DatabaseIntegration performance with price-only runs."""
        # Create database integration
        db_integration = DatabaseIntegration(supabase_client=self.mock_supabase_client)
        
        # Mock the RPC client
        db_integration.rpc_client = Mock()
        db_integration.rpc_client.upsert_coffee = Mock(return_value="test_coffee_id")
        db_integration.rpc_client.upsert_variant = Mock(return_value="test_variant_id")
        db_integration.rpc_client.insert_price = Mock(return_value="test_price_id")
        
        # Mock validation result
        validation_result = Mock()
        validation_result.is_valid = True
        validation_result.artifact_data = self.test_artifact
        validation_result.artifact_id = "test_artifact_123"
        
        # Mock the artifact mapper
        db_integration.artifact_mapper = Mock()
        db_integration.artifact_mapper.map_artifact_to_rpc_payloads = Mock(
            return_value={
                'coffee': {'name': 'Test Coffee'},
                'variants': [{'name': 'Test Variant'}],
                'prices': [{'price': 25.99}],
                'images': [{'url': 'https://example.com/image1.jpg'}],
                'metadata_only': True
            }
        )
        
        # Measure time for multiple upserts
        start_time = time.time()
        
        for i in range(100):  # 100 upserts
            result = db_integration.upsert_artifact_via_rpc(
                validation_result=validation_result,
                roaster_id="test_roaster",
                metadata_only=True
            )
            assert result['success'] is True
            assert len(result['image_ids']) == 0  # No images
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should complete in reasonable time
        assert duration < 5.0  # Less than 5 seconds for 100 upserts
        
        # Calculate upserts per second
        upserts_per_second = 100 / duration
        assert upserts_per_second > 10  # At least 10 upserts per second
    
    def test_database_integration_performance_full_pipeline(self):
        """Test DatabaseIntegration performance with full pipeline runs."""
        # Create database integration
        db_integration = DatabaseIntegration(supabase_client=self.mock_supabase_client)
        
        # Mock the RPC client
        db_integration.rpc_client = Mock()
        db_integration.rpc_client.upsert_coffee = Mock(return_value="test_coffee_id")
        db_integration.rpc_client.upsert_variant = Mock(return_value="test_variant_id")
        db_integration.rpc_client.insert_price = Mock(return_value="test_price_id")
        db_integration.rpc_client.upsert_coffee_image = Mock(return_value="test_image_id")
        
        # Mock validation result
        validation_result = Mock()
        validation_result.is_valid = True
        validation_result.artifact_data = self.test_artifact
        validation_result.artifact_id = "test_artifact_123"
        
        # Mock the artifact mapper
        db_integration.artifact_mapper = Mock()
        db_integration.artifact_mapper.map_artifact_to_rpc_payloads = Mock(
            return_value={
                'coffee': {'name': 'Test Coffee'},
                'variants': [{'name': 'Test Variant'}],
                'prices': [{'price': 25.99}],
                'images': [{'url': 'https://example.com/image1.jpg'}],
                'metadata_only': False
            }
        )
        
        # Measure time for multiple upserts
        start_time = time.time()
        
        for i in range(50):  # 50 upserts (fewer due to image processing)
            result = db_integration.upsert_artifact_via_rpc(
                validation_result=validation_result,
                roaster_id="test_roaster",
                metadata_only=False
            )
            assert result['success'] is True
            assert len(result['image_ids']) > 0  # Should have images
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should complete in reasonable time
        assert duration < 10.0  # Less than 10 seconds for 50 upserts
        
        # Calculate upserts per second
        upserts_per_second = 50 / duration
        assert upserts_per_second > 5  # At least 5 upserts per second
    
    def test_rpc_client_performance_price_only(self):
        """Test RPCClient performance with price-only runs."""
        # Create RPC client with metadata_only=True
        rpc_client = RPCClient(
            supabase_client=self.mock_supabase_client,
            metadata_only=True
        )
        
        # Measure time for multiple guard checks
        start_time = time.time()
        
        for i in range(10000):  # 10,000 guard checks
            try:
                rpc_client.upsert_coffee_image(
                    coffee_id="test_coffee_id",
                    url=f"https://example.com/image{i}.jpg",
                    alt=f"Test image {i}"
                )
            except Exception:
                # Expected to fail due to guard
                pass
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should complete in reasonable time
        assert duration < 2.0  # Less than 2 seconds for 10,000 checks
        
        # Calculate checks per second
        checks_per_second = 10000 / duration
        assert checks_per_second > 5000  # At least 5k checks per second
    
    def test_rpc_client_performance_full_pipeline(self):
        """Test RPCClient performance with full pipeline runs."""
        # Create RPC client with metadata_only=False
        rpc_client = RPCClient(
            supabase_client=self.mock_supabase_client,
            metadata_only=False
        )
        
        # Mock the RPC execution
        rpc_client._execute_rpc_with_retry = Mock(return_value="test_image_id")
        
        # Measure time for multiple image upserts
        start_time = time.time()
        
        for i in range(1000):  # 1,000 image upserts
            result = rpc_client.upsert_coffee_image(
                coffee_id="test_coffee_id",
                url=f"https://example.com/image{i}.jpg",
                alt=f"Test image {i}"
            )
            assert result == "test_image_id"
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should complete in reasonable time
        assert duration < 5.0  # Less than 5 seconds for 1,000 upserts
        
        # Calculate upserts per second
        upserts_per_second = 1000 / duration
        assert upserts_per_second > 100  # At least 100 upserts per second
    
    def test_guard_statistics_performance(self):
        """Test that guard statistics don't impact performance."""
        guard = ImageProcessingGuard(metadata_only=True)
        
        # Perform many operations
        start_time = time.time()
        
        for i in range(10000):
            guard.check_image_processing_allowed(f"operation_{i}")
            guard.guard_image_processing(f"operation_{i}", Mock(), "arg1")
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should complete in reasonable time
        assert duration < 2.0  # Less than 2 seconds for 20,000 operations
        
        # Verify statistics are accurate
        stats = guard.get_guard_stats()
        assert stats['blocks_attempted'] == 20000  # 10k check + 10k guard
        assert stats['operations_skipped'] == 10000  # 10k guard operations
    
    def test_guard_reset_performance(self):
        """Test that guard reset operations are fast."""
        guard = ImageProcessingGuard(metadata_only=True)
        
        # Perform many operations
        for i in range(10000):
            guard.check_image_processing_allowed(f"operation_{i}")
        
        # Measure reset time
        start_time = time.time()
        guard.reset_stats()
        end_time = time.time()
        duration = end_time - start_time
        
        # Reset should be very fast
        assert duration < 0.001  # Less than 1ms
        
        # Verify stats are reset
        stats = guard.get_guard_stats()
        assert stats['blocks_attempted'] == 0
        assert stats['operations_skipped'] == 0
    
    def test_concurrent_guard_performance(self):
        """Test guard performance under concurrent access simulation."""
        import threading
        
        guard = ImageProcessingGuard(metadata_only=True)
        results = []
        
        def worker(worker_id):
            """Worker function for concurrent testing."""
            for i in range(1000):
                result = guard.check_image_processing_allowed(f"worker_{worker_id}_operation_{i}")
                results.append(result)
        
        # Create multiple threads
        threads = []
        for i in range(10):  # 10 concurrent threads
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
        
        # Start all threads
        start_time = time.time()
        for thread in threads:
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should complete in reasonable time
        assert duration < 5.0  # Less than 5 seconds for 10k operations across 10 threads
        
        # Verify all operations were blocked
        assert all(result is False for result in results)
        assert len(results) == 10000  # 10 threads * 1000 operations each
    
    def test_memory_leak_prevention(self):
        """Test that guards don't cause memory leaks."""
        # Get initial memory usage
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # Create and destroy many guards
        for i in range(1000):
            guard = ImageProcessingGuard(metadata_only=(i % 2 == 0))
            
            # Perform some operations
            for j in range(100):
                guard.check_image_processing_allowed(f"operation_{j}")
            
            # Destroy guard
            del guard
        
        # Force garbage collection
        import gc
        gc.collect()
        
        # Get final memory usage
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be minimal (less than 50MB)
        assert memory_increase < 50 * 1024 * 1024  # 50MB
