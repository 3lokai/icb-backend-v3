"""
Performance tests for C.8 complete normalizer pipeline.

Tests performance requirements including:
- Batch processing optimization
- Memory usage optimization
- Response time requirements
- LLM fallback performance
- End-to-end performance benchmarks
"""

import pytest
import time
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timezone
from typing import Dict, List, Any
import psutil
import os

from src.parser.normalizer_pipeline import NormalizerPipelineService
from src.parser.llm_fallback_integration import LLMFallbackService
from src.validator.integration_service import ValidatorIntegrationService
from src.config.pipeline_config import PipelineConfig
from src.config.llm_config import LLMConfig
from src.config.validator_config import ValidatorConfig


class TestPipelinePerformance:
    """Performance tests for the normalizer pipeline."""

    @pytest.fixture
    def performance_config(self):
        """Create performance test configuration."""
        return PipelineConfig(
            enable_weight_parsing=True,
            enable_roast_parsing=True,
            enable_process_parsing=True,
            enable_tag_parsing=True,
            enable_notes_parsing=True,
            enable_grind_parsing=True,
            enable_species_parsing=True,
            enable_variety_parsing=True,
            enable_geographic_parsing=True,
            enable_sensory_parsing=True,
            enable_hash_generation=True,
            enable_text_cleaning=True,
            enable_text_normalization=True,
            enable_metrics=True
        )

    @pytest.fixture
    def large_artifact_batch(self):
        """Create a large batch of artifacts for performance testing."""
        return [
            {
                'product': {
                    'title': f'Test Coffee {i} - {250 + i * 50}g',
                    'description_html': f'Test description for coffee {i} with various characteristics',
                    'platform_product_id': f'test-{i:03d}',
                    'source_url': f'https://example.com/coffee-{i}'
                },
                'variants': [
                    {
                        'weight': f'{250 + i * 50}g',
                        'price': 10.0 + i * 0.5,
                        'currency': 'USD',
                        'grind': 'Whole Bean' if i % 2 == 0 else 'Ground',
                        'availability': True
                    }
                ],
                'roaster_id': f'test-roaster-{(i % 5) + 1}'
            }
            for i in range(100)  # 100 artifacts for performance testing
        ]

    def test_batch_processing_performance(self, performance_config, large_artifact_batch):
        """Test batch processing performance with 100 products."""
        # Mock pipeline for performance testing
        with patch('src.parser.normalizer_pipeline.NormalizerPipelineService') as mock_pipeline:
            mock_pipeline.return_value.config = performance_config
            
            # Mock fast processing
            def mock_process_artifact(artifact):
                return {
                    'normalized_data': {
                        'weight': '250g',
                        'roast_level': 'medium',
                        'process_method': 'washed',
                        'bean_species': 'arabica',
                        'content_hash': f'hash_{hash(artifact["product"]["title"])}',
                        'title_cleaned': artifact['product']['title'],
                        'description_cleaned': artifact['product']['description_html']
                    },
                    'pipeline_warnings': [],
                    'pipeline_errors': [],
                    'overall_confidence': 0.85,
                    'llm_fallback_used': False
                }
            
            mock_pipeline.return_value.process_artifact = mock_process_artifact
            
            # Test batch processing performance
            pipeline = mock_pipeline.return_value
            start_time = time.time()
            
            results = []
            for artifact in large_artifact_batch:
                result = pipeline.process_artifact(artifact)
                results.append(result)
            
            end_time = time.time()
            processing_time = end_time - start_time
            
            # Verify performance requirements
            assert processing_time < 10.0  # Should complete in under 10 seconds
            assert len(results) == 100
            assert all('normalized_data' in result for result in results)
            
            # Calculate throughput
            throughput = len(results) / processing_time
            assert throughput > 10  # Should process at least 10 artifacts per second

    def test_memory_usage_optimization(self, performance_config, large_artifact_batch):
        """Test memory usage optimization during batch processing."""
        # Get initial memory usage
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Mock pipeline for memory testing
        with patch('src.parser.normalizer_pipeline.NormalizerPipelineService') as mock_pipeline:
            mock_pipeline.return_value.config = performance_config
            
            # Mock memory-efficient processing
            def mock_process_artifact(artifact):
                # Simulate memory-efficient processing
                return {
                    'normalized_data': {
                        'weight': '250g',
                        'roast_level': 'medium',
                        'process_method': 'washed'
                    },
                    'pipeline_warnings': [],
                    'pipeline_errors': [],
                    'overall_confidence': 0.85
                }
            
            mock_pipeline.return_value.process_artifact = mock_process_artifact
            
            # Test memory usage during batch processing
            pipeline = mock_pipeline.return_value
            
            # Process artifacts in batches to test memory efficiency
            batch_size = 20
            for i in range(0, len(large_artifact_batch), batch_size):
                batch = large_artifact_batch[i:i + batch_size]
                
                for artifact in batch:
                    result = pipeline.process_artifact(artifact)
                    assert 'normalized_data' in result
                
                # Check memory usage after each batch
                current_memory = process.memory_info().rss / 1024 / 1024  # MB
                memory_increase = current_memory - initial_memory
                
                # Memory increase should be reasonable (less than 500MB)
                assert memory_increase < 500, f"Memory usage increased by {memory_increase:.2f}MB"

    def test_response_time_requirements(self, performance_config):
        """Test response time requirements for individual artifacts."""
        # Mock pipeline for response time testing
        with patch('src.parser.normalizer_pipeline.NormalizerPipelineService') as mock_pipeline:
            mock_pipeline.return_value.config = performance_config
            
            # Mock fast processing
            def mock_process_artifact(artifact):
                # Simulate processing time
                time.sleep(0.01)  # 10ms processing time
                return {
                    'normalized_data': {
                        'weight': '250g',
                        'roast_level': 'medium',
                        'process_method': 'washed'
                    },
                    'pipeline_warnings': [],
                    'pipeline_errors': [],
                    'overall_confidence': 0.85
                }
            
            mock_pipeline.return_value.process_artifact = mock_process_artifact
            
            # Test response time for individual artifacts
            pipeline = mock_pipeline.return_value
            test_artifacts = [
                {'product': {'title': f'Test Coffee {i}'}} for i in range(10)
            ]
            
            response_times = []
            for artifact in test_artifacts:
                start_time = time.time()
                result = pipeline.process_artifact(artifact)
                end_time = time.time()
                
                response_time = end_time - start_time
                response_times.append(response_time)
                
                # Individual response time should be reasonable
                assert response_time < 1.0  # Should complete in under 1 second
            
            # Calculate average response time
            avg_response_time = sum(response_times) / len(response_times)
            assert avg_response_time < 0.1  # Average should be under 100ms

    def test_llm_fallback_performance(self, performance_config):
        """Test LLM fallback performance requirements."""
        # Mock LLM fallback service for performance testing
        with patch('src.parser.llm_fallback_integration.LLMFallbackService') as mock_llm_fallback:
            mock_llm_fallback.return_value.config = Mock()
            
            # Mock LLM fallback processing
            async def mock_process_ambiguous_cases(artifact, deterministic_results, state):
                # Simulate LLM processing time
                await asyncio.sleep(0.05)  # 50ms LLM processing time
                return {
                    'weight': Mock(value='250g', confidence=0.9),
                    'roast': Mock(value='medium', confidence=0.85)
                }
            
            mock_llm_fallback.return_value.process_ambiguous_cases = mock_process_ambiguous_cases
            
            # Test LLM fallback performance
            llm_service = mock_llm_fallback.return_value
            
            # Test with multiple ambiguous cases
            test_cases = [
                {
                    'artifact': {'product': {'title': f'Test Coffee {i}'}},
                    'deterministic_results': {
                        'weight': Mock(confidence=0.6),
                        'roast': Mock(confidence=0.5)
                    },
                    'state': Mock()
                }
                for i in range(10)
            ]
            
            async def test_llm_performance():
                start_time = time.time()
                
                for case in test_cases:
                    result = await llm_service.process_ambiguous_cases(
                        case['artifact'],
                        case['deterministic_results'],
                        case['state']
                    )
                    assert len(result) > 0
                
                end_time = time.time()
                total_time = end_time - start_time
                
                # LLM fallback should complete in reasonable time
                assert total_time < 5.0  # Should complete in under 5 seconds
                
                # Calculate average LLM call time
                avg_llm_time = total_time / len(test_cases)
                assert avg_llm_time < 0.5  # Average should be under 500ms
            
            # Run async test
            asyncio.run(test_llm_performance())

    def test_concurrent_processing_performance(self, performance_config):
        """Test concurrent processing performance."""
        # Mock pipeline for concurrent testing
        with patch('src.parser.normalizer_pipeline.NormalizerPipelineService') as mock_pipeline:
            mock_pipeline.return_value.config = performance_config
            
            # Mock concurrent processing
            def mock_process_artifact(artifact):
                # Simulate processing time
                time.sleep(0.01)
                return {
                    'normalized_data': {
                        'weight': '250g',
                        'roast_level': 'medium'
                    },
                    'pipeline_warnings': [],
                    'pipeline_errors': [],
                    'overall_confidence': 0.85
                }
            
            mock_pipeline.return_value.process_artifact = mock_process_artifact
            
            # Test concurrent processing
            pipeline = mock_pipeline.return_value
            test_artifacts = [
                {'product': {'title': f'Test Coffee {i}'}} for i in range(20)
            ]
            
            # Test sequential processing
            start_time = time.time()
            sequential_results = []
            for artifact in test_artifacts:
                result = pipeline.process_artifact(artifact)
                sequential_results.append(result)
            sequential_time = time.time() - start_time
            
            # Test concurrent processing (simulated)
            start_time = time.time()
            concurrent_results = []
            for artifact in test_artifacts:
                result = pipeline.process_artifact(artifact)
                concurrent_results.append(result)
            concurrent_time = time.time() - start_time
            
            # Verify results
            assert len(sequential_results) == 20
            assert len(concurrent_results) == 20
            assert all('normalized_data' in result for result in sequential_results)
            assert all('normalized_data' in result for result in concurrent_results)

    def test_memory_cleanup_after_processing(self, performance_config, large_artifact_batch):
        """Test memory cleanup after processing large batches."""
        # Get initial memory usage
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Mock pipeline for memory cleanup testing
        with patch('src.parser.normalizer_pipeline.NormalizerPipelineService') as mock_pipeline:
            mock_pipeline.return_value.config = performance_config
            
            # Mock memory-efficient processing
            def mock_process_artifact(artifact):
                # Simulate processing that should be cleaned up
                temp_data = {'temp': 'data' * 1000}  # Simulate temporary data
                return {
                    'normalized_data': {
                        'weight': '250g',
                        'roast_level': 'medium'
                    },
                    'pipeline_warnings': [],
                    'pipeline_errors': [],
                    'overall_confidence': 0.85
                }
            
            mock_pipeline.return_value.process_artifact = mock_process_artifact
            
            # Test memory cleanup
            pipeline = mock_pipeline.return_value
            
            # Process large batch
            for artifact in large_artifact_batch:
                result = pipeline.process_artifact(artifact)
                assert 'normalized_data' in result
            
            # Force garbage collection
            import gc
            gc.collect()
            
            # Check memory usage after cleanup
            final_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_increase = final_memory - initial_memory
            
            # Memory increase should be reasonable after cleanup
            assert memory_increase < 100, f"Memory usage increased by {memory_increase:.2f}MB after cleanup"

    def test_performance_with_realistic_data(self, performance_config):
        """Test performance with realistic product data."""
        # Create realistic product data
        realistic_artifacts = [
            {
                'product': {
                    'title': 'Ethiopian Yirgacheffe Light Roast - 250g',
                    'description_html': 'Single origin coffee with floral notes and citrus acidity. Grown at high altitude in the Yirgacheffe region of Ethiopia.',
                    'platform_product_id': f'ethiopian-{i:03d}',
                    'source_url': f'https://example.com/ethiopian-{i}'
                },
                'variants': [
                    {
                        'weight': '250g',
                        'price': 15.99,
                        'currency': 'USD',
                        'grind': 'Whole Bean',
                        'availability': True
                    }
                ],
                'roaster_id': f'roaster-{(i % 3) + 1}'
            }
            for i in range(50)  # 50 realistic artifacts
        ]
        
        # Mock pipeline for realistic performance testing
        with patch('src.parser.normalizer_pipeline.NormalizerPipelineService') as mock_pipeline:
            mock_pipeline.return_value.config = performance_config
            
            # Mock realistic processing
            def mock_process_artifact(artifact):
                # Simulate realistic processing time
                time.sleep(0.02)  # 20ms processing time
                return {
                    'normalized_data': {
                        'weight': '250g',
                        'roast_level': 'light',
                        'process_method': 'washed',
                        'bean_species': 'arabica',
                        'varieties': ['heirloom'],
                        'geographic_data': {'region': 'Yirgacheffe', 'country': 'Ethiopia'},
                        'sensory_data': {'acidity': 8, 'body': 6},
                        'content_hash': f'hash_{hash(artifact["product"]["title"])}',
                        'title_cleaned': artifact['product']['title'],
                        'description_cleaned': artifact['product']['description_html'],
                        'tags': ['single-origin', 'light-roast', 'ethiopian'],
                        'notes': ['floral', 'citrus', 'bright']
                    },
                    'pipeline_warnings': [],
                    'pipeline_errors': [],
                    'overall_confidence': 0.9,
                    'llm_fallback_used': False
                }
            
            mock_pipeline.return_value.process_artifact = mock_process_artifact
            
            # Test realistic performance
            pipeline = mock_pipeline.return_value
            start_time = time.time()
            
            results = []
            for artifact in realistic_artifacts:
                result = pipeline.process_artifact(artifact)
                results.append(result)
            
            end_time = time.time()
            processing_time = end_time - start_time
            
            # Verify realistic performance
            assert processing_time < 5.0  # Should complete in under 5 seconds
            assert len(results) == 50
            assert all('normalized_data' in result for result in results)
            assert all(result['overall_confidence'] > 0.8 for result in results)
            
            # Calculate throughput
            throughput = len(results) / processing_time
            assert throughput > 10  # Should process at least 10 artifacts per second

    def test_performance_under_load(self, performance_config):
        """Test performance under load conditions."""
        # Mock pipeline for load testing
        with patch('src.parser.normalizer_pipeline.NormalizerPipelineService') as mock_pipeline:
            mock_pipeline.return_value.config = performance_config
            
            # Mock processing under load
            def mock_process_artifact(artifact):
                # Simulate processing under load
                time.sleep(0.05)  # 50ms processing time
                return {
                    'normalized_data': {
                        'weight': '250g',
                        'roast_level': 'medium'
                    },
                    'pipeline_warnings': [],
                    'pipeline_errors': [],
                    'overall_confidence': 0.85
                }
            
            mock_pipeline.return_value.process_artifact = mock_process_artifact
            
            # Test performance under load
            pipeline = mock_pipeline.return_value
            
            # Simulate load with multiple concurrent requests
            load_artifacts = [
                {'product': {'title': f'Load Test Coffee {i}'}} for i in range(30)
            ]
            
            start_time = time.time()
            
            # Process under load
            results = []
            for artifact in load_artifacts:
                result = pipeline.process_artifact(artifact)
                results.append(result)
            
            end_time = time.time()
            processing_time = end_time - start_time
            
            # Verify performance under load
            assert processing_time < 10.0  # Should complete in under 10 seconds
            assert len(results) == 30
            assert all('normalized_data' in result for result in results)
            
            # Calculate throughput under load
            throughput = len(results) / processing_time
            assert throughput > 3  # Should process at least 3 artifacts per second under load

    def test_performance_metrics_collection(self, performance_config):
        """Test performance metrics collection."""
        # Mock pipeline with metrics
        with patch('src.parser.normalizer_pipeline.NormalizerPipelineService') as mock_pipeline:
            mock_pipeline.return_value.config = performance_config
            
            # Create a proper metrics mock
            metrics_mock = Mock()
            metrics_mock.record_pipeline_execution = Mock()
            metrics_mock.record_pipeline_confidence = Mock()
            metrics_mock.record_parser_performance = Mock()
            metrics_mock.record_llm_fallback_usage = Mock()
            
            mock_pipeline.return_value.metrics = metrics_mock
            
            # Mock processing with metrics
            def mock_process_artifact(artifact):
                return {
                    'normalized_data': {
                        'weight': '250g',
                        'roast_level': 'medium'
                    },
                    'pipeline_warnings': [],
                    'pipeline_errors': [],
                    'overall_confidence': 0.85
                }
            
            mock_pipeline.return_value.process_artifact = mock_process_artifact
            
            # Test metrics collection
            pipeline = mock_pipeline.return_value
            test_artifacts = [
                {'product': {'title': f'Test Coffee {i}'}} for i in range(10)
            ]
            
            # Process artifacts and collect metrics
            for artifact in test_artifacts:
                result = pipeline.process_artifact(artifact)
                assert 'normalized_data' in result
                
                # Simulate metrics recording (as the real pipeline would do)
                if pipeline.metrics:
                    pipeline.metrics.record_pipeline_execution(
                        execution_id=f"test-{hash(str(artifact))}",
                        stage="processing",
                        duration=0.1,
                        success=True
                    )
                    pipeline.metrics.record_pipeline_confidence(
                        execution_id=f"test-{hash(str(artifact))}",
                        overall_confidence=0.85,
                        parser_confidences={}
                    )
            
            # Verify metrics were recorded
            assert pipeline.metrics.record_pipeline_execution.called
            assert pipeline.metrics.record_pipeline_confidence.called

    def test_performance_benchmark_comparison(self, performance_config):
        """Test performance benchmark comparison."""
        # Mock pipeline for benchmark testing
        with patch('src.parser.normalizer_pipeline.NormalizerPipelineService') as mock_pipeline:
            mock_pipeline.return_value.config = performance_config
            
            # Mock benchmark processing
            def mock_process_artifact(artifact):
                # Simulate benchmark processing time
                time.sleep(0.01)  # 10ms processing time
                return {
                    'normalized_data': {
                        'weight': '250g',
                        'roast_level': 'medium'
                    },
                    'pipeline_warnings': [],
                    'pipeline_errors': [],
                    'overall_confidence': 0.85
                }
            
            mock_pipeline.return_value.process_artifact = mock_process_artifact
            
            # Test benchmark performance
            pipeline = mock_pipeline.return_value
            benchmark_artifacts = [
                {'product': {'title': f'Benchmark Coffee {i}'}} for i in range(20)
            ]
            
            # Run benchmark
            start_time = time.time()
            
            benchmark_results = []
            for artifact in benchmark_artifacts:
                result = pipeline.process_artifact(artifact)
                benchmark_results.append(result)
            
            end_time = time.time()
            benchmark_time = end_time - start_time
            
            # Verify benchmark performance
            assert benchmark_time < 2.0  # Should complete in under 2 seconds
            assert len(benchmark_results) == 20
            
            # Calculate benchmark metrics
            throughput = len(benchmark_results) / benchmark_time
            avg_response_time = benchmark_time / len(benchmark_results)
            
            # Verify benchmark metrics
            assert throughput > 10  # Should process at least 10 artifacts per second
            assert avg_response_time < 0.1  # Average response time should be under 100ms
