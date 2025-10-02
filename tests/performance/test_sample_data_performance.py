"""
Performance validation infrastructure for sample data processing.

This module provides performance monitoring, memory usage tracking, and
regression detection for large dataset processing.
"""

import asyncio
import gc
import logging
import os
import psutil
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import Mock, patch

import pytest
import tracemalloc

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Performance metrics for a test execution."""
    test_name: str
    execution_time: float
    memory_peak: float
    memory_average: float
    cpu_usage: float
    memory_leaks: int = 0
    gc_collections: int = 0
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class PerformanceThresholds:
    """Performance thresholds for validation."""
    max_execution_time: float = 300.0  # 5 minutes
    max_memory_usage: float = 1024.0  # 1GB
    max_cpu_usage: float = 80.0  # 80%
    max_memory_leaks: int = 0
    min_success_rate: float = 95.0  # 95%


class PerformanceMonitor:
    """Performance monitoring for large dataset processing."""
    
    def __init__(self, thresholds: PerformanceThresholds):
        self.thresholds = thresholds
        self.metrics: List[PerformanceMetrics] = []
        self.monitoring_active = False
        self.start_time: Optional[datetime] = None
        self.process = psutil.Process()
        
    async def start_monitoring(self, test_name: str) -> str:
        """Start performance monitoring for a test."""
        self.monitoring_active = True
        self.start_time = datetime.now()
        
        # Start memory tracing
        tracemalloc.start()
        
        # Force garbage collection
        gc.collect()
        
        logger.info(f"Started performance monitoring for {test_name}")
        return test_name
    
    async def stop_monitoring(self, test_name: str) -> PerformanceMetrics:
        """Stop performance monitoring and return metrics."""
        if not self.monitoring_active:
            raise RuntimeError("Monitoring not active")
        
        end_time = datetime.now()
        execution_time = (end_time - self.start_time).total_seconds()
        
        # Get memory statistics
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        # Get system metrics
        memory_info = self.process.memory_info()
        memory_peak = memory_info.rss / 1024 / 1024  # Convert to MB
        memory_average = memory_info.rss / 1024 / 1024  # Average during execution
        
        # Get CPU usage
        cpu_usage = self.process.cpu_percent()
        
        # Check for memory leaks
        gc.collect()
        memory_leaks = self._detect_memory_leaks()
        
        # Get garbage collection stats
        gc_stats = gc.get_stats()
        gc_collections = sum(stat['collections'] for stat in gc_stats)
        
        metrics = PerformanceMetrics(
            test_name=test_name,
            execution_time=execution_time,
            memory_peak=memory_peak,
            memory_average=memory_average,
            cpu_usage=cpu_usage,
            memory_leaks=memory_leaks,
            gc_collections=gc_collections
        )
        
        self.metrics.append(metrics)
        self.monitoring_active = False
        
        logger.info(f"Performance monitoring completed for {test_name}")
        logger.info(f"Execution time: {execution_time:.2f}s, Memory peak: {memory_peak:.2f}MB")
        
        return metrics
    
    def _detect_memory_leaks(self) -> int:
        """Detect potential memory leaks."""
        # Simple heuristic: check if memory usage is unusually high
        memory_info = self.process.memory_info()
        current_memory = memory_info.rss / 1024 / 1024  # MB
        
        # If memory usage is above 80% of threshold, consider it a potential leak
        if current_memory > (self.thresholds.max_memory_usage * 0.8):
            return 1
        return 0
    
    def validate_performance(self, metrics: PerformanceMetrics) -> Dict[str, Any]:
        """Validate performance against thresholds."""
        violations = []
        
        if metrics.execution_time > self.thresholds.max_execution_time:
            violations.append(f"Execution time {metrics.execution_time:.2f}s exceeds threshold {self.thresholds.max_execution_time}s")
        
        if metrics.memory_peak > self.thresholds.max_memory_usage:
            violations.append(f"Memory peak {metrics.memory_peak:.2f}MB exceeds threshold {self.thresholds.max_memory_usage}MB")
        
        if metrics.cpu_usage > self.thresholds.max_cpu_usage:
            violations.append(f"CPU usage {metrics.cpu_usage:.2f}% exceeds threshold {self.thresholds.max_cpu_usage}%")
        
        if metrics.memory_leaks > self.thresholds.max_memory_leaks:
            violations.append(f"Memory leaks {metrics.memory_leaks} exceed threshold {self.thresholds.max_memory_leaks}")
        
        return {
            'valid': len(violations) == 0,
            'violations': violations,
            'metrics': metrics
        }
    
    def detect_regression(self, baseline_metrics: PerformanceMetrics, current_metrics: PerformanceMetrics) -> Dict[str, Any]:
        """Detect performance regression compared to baseline."""
        regressions = []
        
        # Check execution time regression (20% increase)
        time_increase = (current_metrics.execution_time - baseline_metrics.execution_time) / baseline_metrics.execution_time
        if time_increase > 0.2:
            regressions.append(f"Execution time increased by {time_increase:.1%}")
        
        # Check memory regression (20% increase)
        memory_increase = (current_metrics.memory_peak - baseline_metrics.memory_peak) / baseline_metrics.memory_peak
        if memory_increase > 0.2:
            regressions.append(f"Memory usage increased by {memory_increase:.1%}")
        
        # Check CPU regression (20% increase)
        cpu_increase = (current_metrics.cpu_usage - baseline_metrics.cpu_usage) / baseline_metrics.cpu_usage
        if cpu_increase > 0.2:
            regressions.append(f"CPU usage increased by {cpu_increase:.1%}")
        
        return {
            'has_regression': len(regressions) > 0,
            'regressions': regressions,
            'baseline': baseline_metrics,
            'current': current_metrics
        }


class PerformanceValidator:
    """Performance validation for sample data processing."""
    
    def __init__(self, thresholds: PerformanceThresholds):
        self.thresholds = thresholds
        self.monitor = PerformanceMonitor(thresholds)
        self.baseline_metrics: Optional[PerformanceMetrics] = None
    
    async def validate_sample_data_processing(self, sample_data_path: str) -> Dict[str, Any]:
        """Validate performance of sample data processing."""
        logger.info(f"Starting performance validation for sample data at {sample_data_path}")
        
        # Start monitoring
        test_name = await self.monitor.start_monitoring("sample_data_processing")
        
        try:
            # Simulate sample data processing
            await self._process_sample_data(sample_data_path)
            
            # Stop monitoring and get metrics
            metrics = await self.monitor.stop_monitoring(test_name)
            
            # Validate performance
            validation_result = self.monitor.validate_performance(metrics)
            
            # Check for regression if baseline exists
            regression_result = None
            if self.baseline_metrics:
                regression_result = self.monitor.detect_regression(self.baseline_metrics, metrics)
            
            return {
                'validation': validation_result,
                'regression': regression_result,
                'metrics': metrics,
                'sample_data_path': sample_data_path
            }
            
        except Exception as e:
            logger.error(f"Performance validation failed: {e}")
            raise
    
    async def _process_sample_data(self, sample_data_path: str):
        """Simulate sample data processing for performance testing."""
        sample_files = list(Path(sample_data_path).glob("**/*.json"))
        
        logger.info(f"Processing {len(sample_files)} sample files")
        
        for sample_file in sample_files:
            # Simulate file processing
            with open(sample_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Simulate processing time
            await asyncio.sleep(0.01)  # 10ms per file
            
            # Simulate memory usage
            _ = [i for i in range(1000)]  # Create some memory usage
    
    def set_baseline_metrics(self, metrics: PerformanceMetrics):
        """Set baseline metrics for regression detection."""
        self.baseline_metrics = metrics
        logger.info(f"Baseline metrics set for {metrics.test_name}")
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary across all tests."""
        if not self.monitor.metrics:
            return {'message': 'No performance data available'}
        
        total_tests = len(self.monitor.metrics)
        avg_execution_time = sum(m.execution_time for m in self.monitor.metrics) / total_tests
        avg_memory_peak = sum(m.memory_peak for m in self.monitor.metrics) / total_tests
        avg_cpu_usage = sum(m.cpu_usage for m in self.monitor.metrics) / total_tests
        
        return {
            'total_tests': total_tests,
            'average_execution_time': avg_execution_time,
            'average_memory_peak': avg_memory_peak,
            'average_cpu_usage': avg_cpu_usage,
            'thresholds': {
                'max_execution_time': self.thresholds.max_execution_time,
                'max_memory_usage': self.thresholds.max_memory_usage,
                'max_cpu_usage': self.thresholds.max_cpu_usage
            }
        }


# Test cases for performance validation
class TestPerformanceValidation:
    """Test cases for performance validation infrastructure."""
    
    @pytest.fixture
    def performance_thresholds(self):
        """Performance thresholds for testing."""
        return PerformanceThresholds(
            max_execution_time=60.0,  # 1 minute for tests
            max_memory_usage=512.0,  # 512MB for tests
            max_cpu_usage=70.0,  # 70% for tests
            max_memory_leaks=0,
            min_success_rate=90.0
        )
    
    @pytest.fixture
    def performance_monitor(self, performance_thresholds):
        """Performance monitor instance."""
        return PerformanceMonitor(performance_thresholds)
    
    @pytest.fixture
    def performance_validator(self, performance_thresholds):
        """Performance validator instance."""
        return PerformanceValidator(performance_thresholds)
    
    @pytest.mark.asyncio
    async def test_performance_monitoring(self, performance_monitor):
        """Test performance monitoring start and stop."""
        test_name = "test_performance_monitoring"
        
        # Start monitoring
        await performance_monitor.start_monitoring(test_name)
        assert performance_monitor.monitoring_active
        assert performance_monitor.start_time is not None
        
        # Simulate some work
        await asyncio.sleep(0.1)
        
        # Stop monitoring
        metrics = await performance_monitor.stop_monitoring(test_name)
        
        assert not performance_monitor.monitoring_active
        assert metrics.test_name == test_name
        assert metrics.execution_time > 0
        assert metrics.memory_peak >= 0
        assert len(performance_monitor.metrics) == 1
    
    @pytest.mark.asyncio
    async def test_performance_validation(self, performance_validator):
        """Test performance validation."""
        # Create a temporary sample data directory
        sample_data_path = "data/samples"
        
        # Mock the sample data processing
        with patch.object(performance_validator, '_process_sample_data') as mock_process:
            mock_process.return_value = None
            
            result = await performance_validator.validate_sample_data_processing(sample_data_path)
            
            assert 'validation' in result
            assert 'metrics' in result
            assert 'sample_data_path' in result
            assert result['sample_data_path'] == sample_data_path
    
    def test_performance_thresholds_validation(self, performance_monitor):
        """Test performance threshold validation."""
        # Create metrics that should pass
        good_metrics = PerformanceMetrics(
            test_name="good_test",
            execution_time=30.0,  # Under 60s threshold
            memory_peak=256.0,    # Under 512MB threshold
            memory_average=200.0,
            cpu_usage=50.0,       # Under 70% threshold
            memory_leaks=0
        )
        
        validation_result = performance_monitor.validate_performance(good_metrics)
        assert validation_result['valid'] is True
        assert len(validation_result['violations']) == 0
        
        # Create metrics that should fail
        bad_metrics = PerformanceMetrics(
            test_name="bad_test",
            execution_time=120.0,  # Over 60s threshold
            memory_peak=1024.0,    # Over 512MB threshold
            memory_average=800.0,
            cpu_usage=90.0,       # Over 70% threshold
            memory_leaks=1        # Over 0 threshold
        )
        
        validation_result = performance_monitor.validate_performance(bad_metrics)
        assert validation_result['valid'] is False
        assert len(validation_result['violations']) > 0
    
    def test_regression_detection(self, performance_monitor):
        """Test performance regression detection."""
        baseline_metrics = PerformanceMetrics(
            test_name="baseline",
            execution_time=30.0,
            memory_peak=256.0,
            memory_average=200.0,
            cpu_usage=50.0
        )
        
        # Current metrics with regression
        current_metrics = PerformanceMetrics(
            test_name="current",
            execution_time=45.0,  # 50% increase
            memory_peak=384.0,    # 50% increase
            memory_average=300.0,
            cpu_usage=75.0        # 50% increase
        )
        
        regression_result = performance_monitor.detect_regression(baseline_metrics, current_metrics)
        
        assert regression_result['has_regression'] is True
        assert len(regression_result['regressions']) > 0
    
    def test_performance_summary(self, performance_validator):
        """Test performance summary generation."""
        # Add some mock metrics
        performance_validator.monitor.metrics = [
            PerformanceMetrics("test1", 30.0, 256.0, 200.0, 50.0),
            PerformanceMetrics("test2", 45.0, 384.0, 300.0, 60.0),
            PerformanceMetrics("test3", 20.0, 192.0, 150.0, 40.0)
        ]
        
        summary = performance_validator.get_performance_summary()
        
        assert summary['total_tests'] == 3
        assert abs(summary['average_execution_time'] - 31.67) < 0.01  # (30+45+20)/3
        assert abs(summary['average_memory_peak'] - 277.33) < 0.01    # (256+384+192)/3
        assert summary['average_cpu_usage'] == 50.0        # (50+60+40)/3
        assert 'thresholds' in summary


if __name__ == "__main__":
    # Run performance validation tests
    pytest.main([__file__, "-v"])
