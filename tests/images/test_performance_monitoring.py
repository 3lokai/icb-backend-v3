"""
Performance monitoring tests for image deduplication services.
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock

from src.images.performance_monitor import ImagePerformanceMonitor, PerformanceMetrics


class TestImagePerformanceMonitor:
    """Test cases for ImagePerformanceMonitor."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.monitor = ImagePerformanceMonitor(enable_system_monitoring=False)
    
    def test_start_monitoring(self):
        """Test starting performance monitoring."""
        metrics = self.monitor.start_monitoring()
        
        assert metrics is not None
        assert metrics.images_processed == 0
        assert metrics.hashes_computed == 0
        assert metrics.duplicates_found == 0
        assert metrics.new_images == 0
        assert metrics.errors == 0
        assert self.monitor.current_metrics is not None
    
    def test_stop_monitoring(self):
        """Test stopping performance monitoring."""
        # Start monitoring
        self.monitor.start_monitoring()
        
        # Record some activity
        self.monitor.record_image_processed(1.0, is_duplicate=False)
        self.monitor.record_image_processed(0.5, is_duplicate=True)
        
        # Stop monitoring
        final_metrics = self.monitor.stop_monitoring()
        
        assert final_metrics.images_processed == 2
        assert final_metrics.hashes_computed == 2
        assert final_metrics.duplicates_found == 1
        assert final_metrics.new_images == 1
        assert final_metrics.total_duration > 0
        assert self.monitor.current_metrics is None
    
    def test_record_image_processed_new_image(self):
        """Test recording processing of a new image."""
        self.monitor.start_monitoring()
        
        self.monitor.record_image_processed(1.5, is_duplicate=False)
        
        metrics = self.monitor.current_metrics
        assert metrics.images_processed == 1
        assert metrics.hashes_computed == 1
        assert metrics.duplicates_found == 0
        assert metrics.new_images == 1
        assert metrics.max_processing_time == 1.5
        assert metrics.min_processing_time == 1.5
    
    def test_record_image_processed_duplicate(self):
        """Test recording processing of a duplicate image."""
        self.monitor.start_monitoring()
        
        self.monitor.record_image_processed(0.8, is_duplicate=True)
        
        metrics = self.monitor.current_metrics
        assert metrics.images_processed == 1
        assert metrics.hashes_computed == 1
        assert metrics.duplicates_found == 1
        assert metrics.new_images == 0
    
    def test_record_image_processed_error(self):
        """Test recording processing with error."""
        self.monitor.start_monitoring()
        
        self.monitor.record_image_processed(2.0, is_duplicate=False, is_error=True)
        
        metrics = self.monitor.current_metrics
        assert metrics.images_processed == 1
        assert metrics.hashes_computed == 1
        assert metrics.errors == 1
    
    def test_record_cache_hit_miss(self):
        """Test recording cache hits and misses."""
        self.monitor.start_monitoring()
        
        self.monitor.record_cache_hit()
        self.monitor.record_cache_hit()
        self.monitor.record_cache_miss()
        
        metrics = self.monitor.current_metrics
        assert metrics.cache_hits == 2
        assert metrics.cache_misses == 1
        assert metrics.cache_hit_rate == 2/3
    
    def test_calculate_metrics(self):
        """Test metrics calculation."""
        metrics = PerformanceMetrics()
        metrics.images_processed = 10
        metrics.hashes_computed = 10
        metrics.duplicates_found = 3
        metrics.new_images = 7
        metrics.errors = 1
        metrics.cache_hits = 6
        metrics.cache_misses = 4
        metrics.start_time = time.time() - 10.0
        metrics.end_time = time.time()
        
        metrics.calculate_metrics()
        
        assert metrics.total_duration > 0
        assert metrics.avg_processing_time > 0
        assert metrics.cache_hit_rate == 0.6
    
    def test_performance_thresholds_warning(self):
        """Test performance threshold warnings."""
        self.monitor.start_monitoring()
        
        # Record high processing time
        self.monitor.record_image_processed(10.0, is_duplicate=False)
        
        # Stop monitoring to trigger threshold checks
        with patch('src.images.performance_monitor.logger') as mock_logger:
            self.monitor.stop_monitoring()
            
            # Check if warning was logged
            mock_logger.warning.assert_called()
    
    def test_get_performance_recommendations(self):
        """Test getting performance recommendations."""
        # Create metrics with poor performance
        metrics = PerformanceMetrics()
        metrics.cache_hit_rate = 0.3
        metrics.avg_processing_time = 3.0
        metrics.memory_usage_mb = 300.0
        metrics.duplicates_found = 8
        metrics.new_images = 2
        
        self.monitor.metrics_history = [metrics]
        
        recommendations = self.monitor.get_performance_recommendations()
        
        assert len(recommendations) > 0
        assert any("cache" in rec.lower() for rec in recommendations)
        assert any("parallel" in rec.lower() for rec in recommendations)
        assert any("streaming" in rec.lower() for rec in recommendations)
        assert any("duplicate" in rec.lower() for rec in recommendations)
    
    def test_get_performance_stats(self):
        """Test getting performance statistics."""
        # Create some metrics history
        metrics1 = PerformanceMetrics()
        metrics1.images_processed = 5
        metrics1.duplicates_found = 2
        metrics1.errors = 1
        metrics1.total_duration = 10.0
        metrics1.avg_processing_time = 2.0
        metrics1.memory_usage_mb = 100.0
        metrics1.cache_hit_rate = 0.8
        
        metrics2 = PerformanceMetrics()
        metrics2.images_processed = 10
        metrics2.duplicates_found = 3
        metrics2.errors = 0
        metrics2.total_duration = 15.0
        metrics2.avg_processing_time = 1.5
        metrics2.memory_usage_mb = 150.0
        metrics2.cache_hit_rate = 0.7
        
        self.monitor.metrics_history = [metrics1, metrics2]
        
        stats = self.monitor.get_performance_stats()
        
        assert stats['total_sessions'] == 2
        assert stats['total_images_processed'] == 15
        assert stats['total_duplicates_found'] == 5
        assert stats['total_errors'] == 1
        assert stats['total_duration'] == 25.0
        assert stats['avg_processing_time'] == 1.75
        assert stats['avg_memory_usage_mb'] == 125.0
        assert stats['avg_cache_hit_rate'] == 0.75
        assert stats['duplicate_rate'] == 5/15
        assert stats['error_rate'] == 1/15
        assert 'recommendations' in stats
    
    def test_reset_history(self):
        """Test resetting performance history."""
        # Add some metrics to history
        metrics = PerformanceMetrics()
        metrics.images_processed = 5
        self.monitor.metrics_history = [metrics]
        
        # Reset history
        self.monitor.reset_history()
        
        assert len(self.monitor.metrics_history) == 0
    
    def test_batch_processing_monitoring(self):
        """Test monitoring batch processing operations."""
        self.monitor.start_monitoring()
        
        # Simulate batch processing
        batch_size = 100
        for i in range(batch_size):
            processing_time = 0.1 + (i % 10) * 0.01  # Varying processing times
            is_duplicate = i % 3 == 0  # 1/3 duplicates
            is_error = i % 20 == 0  # 1/20 errors
            
            self.monitor.record_image_processed(processing_time, is_duplicate, is_error)
            
            # Simulate cache hits/misses
            if i % 2 == 0:
                self.monitor.record_cache_hit()
            else:
                self.monitor.record_cache_miss()
        
        # Stop monitoring
        final_metrics = self.monitor.stop_monitoring()
        
        assert final_metrics.images_processed == batch_size
        assert final_metrics.hashes_computed == batch_size
        # Calculate expected duplicates: every 3rd item (0, 3, 6, 9, ...)
        expected_duplicates = sum(1 for i in range(batch_size) if i % 3 == 0)
        assert final_metrics.duplicates_found == expected_duplicates
        assert final_metrics.new_images == batch_size - expected_duplicates
        assert final_metrics.errors == batch_size // 20
        assert final_metrics.cache_hits == batch_size // 2
        assert final_metrics.cache_misses == batch_size // 2
        assert final_metrics.cache_hit_rate == 0.5
    
    def test_system_monitoring_disabled(self):
        """Test monitoring with system monitoring disabled."""
        monitor = ImagePerformanceMonitor(enable_system_monitoring=False)
        monitor.start_monitoring()
        
        # Record some activity
        monitor.record_image_processed(1.0)
        
        # Stop monitoring
        final_metrics = monitor.stop_monitoring()
        
        # System metrics should be 0 when disabled
        assert final_metrics.memory_usage_mb == 0.0
        assert final_metrics.cpu_usage_percent == 0.0
    
    @patch('src.images.performance_monitor.psutil.Process')
    def test_system_monitoring_enabled(self, mock_process):
        """Test monitoring with system monitoring enabled."""
        # Mock system metrics
        mock_process_instance = Mock()
        mock_process_instance.memory_info.return_value = Mock(rss=100 * 1024 * 1024)  # 100MB
        mock_process_instance.cpu_percent.return_value = 25.0
        mock_process.return_value = mock_process_instance
        
        monitor = ImagePerformanceMonitor(enable_system_monitoring=True)
        monitor.start_monitoring()
        
        # Record some activity
        monitor.record_image_processed(1.0)
        
        # Stop monitoring
        final_metrics = monitor.stop_monitoring()
        
        # System metrics should be populated
        assert final_metrics.memory_usage_mb > 0
        assert final_metrics.cpu_usage_percent > 0
