"""
Performance monitoring for image deduplication services.

This module provides performance tracking, metrics collection, and optimization
recommendations for image hash computation and deduplication operations.
"""

import time
import psutil
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timezone
from structlog import get_logger

logger = get_logger(__name__)


@dataclass
class PerformanceMetrics:
    """Performance metrics for image processing operations."""
    
    # Timing metrics
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    total_duration: float = 0.0
    
    # Processing metrics
    images_processed: int = 0
    hashes_computed: int = 0
    duplicates_found: int = 0
    new_images: int = 0
    errors: int = 0
    
    # Performance metrics
    avg_processing_time: float = 0.0
    max_processing_time: float = 0.0
    min_processing_time: float = float('inf')
    
    # System metrics
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    
    # Cache metrics
    cache_hits: int = 0
    cache_misses: int = 0
    cache_hit_rate: float = 0.0
    
    def calculate_metrics(self):
        """Calculate derived metrics."""
        if self.end_time is None:
            self.end_time = time.time()
        
        self.total_duration = self.end_time - self.start_time
        
        if self.images_processed > 0:
            self.avg_processing_time = self.total_duration / self.images_processed
        
        if self.min_processing_time == float('inf'):
            self.min_processing_time = 0.0
        
        total_cache_requests = self.cache_hits + self.cache_misses
        if total_cache_requests > 0:
            self.cache_hit_rate = self.cache_hits / total_cache_requests


class ImagePerformanceMonitor:
    """
    Performance monitor for image deduplication operations.
    
    Features:
    - Real-time performance tracking
    - System resource monitoring
    - Performance optimization recommendations
    - Batch processing optimization
    - Memory usage tracking
    """
    
    def __init__(self, enable_system_monitoring: bool = True):
        """
        Initialize performance monitor.
        
        Args:
            enable_system_monitoring: Whether to monitor system resources
        """
        self.enable_system_monitoring = enable_system_monitoring
        self.metrics_history: List[PerformanceMetrics] = []
        self.current_metrics: Optional[PerformanceMetrics] = None
        
        # Performance thresholds
        self.thresholds = {
            'max_processing_time': 5.0,  # seconds per image
            'max_memory_usage': 500.0,   # MB
            'min_cache_hit_rate': 0.7,   # 70%
            'max_error_rate': 0.05       # 5%
        }
    
    def start_monitoring(self) -> PerformanceMetrics:
        """
        Start performance monitoring.
        
        Returns:
            PerformanceMetrics instance for tracking
        """
        self.current_metrics = PerformanceMetrics()
        
        if self.enable_system_monitoring:
            self._update_system_metrics()
        
        logger.info("Started performance monitoring for image deduplication")
        return self.current_metrics
    
    def stop_monitoring(self) -> PerformanceMetrics:
        """
        Stop performance monitoring and calculate final metrics.
        
        Returns:
            Final performance metrics
        """
        if self.current_metrics is None:
            raise ValueError("No active monitoring session")
        
        self.current_metrics.end_time = time.time()
        self.current_metrics.calculate_metrics()
        
        if self.enable_system_monitoring:
            self._update_system_metrics()
        
        # Add to history
        self.metrics_history.append(self.current_metrics)
        
        # Log performance summary
        self._log_performance_summary()
        
        # Check for performance issues
        self._check_performance_thresholds()
        
        final_metrics = self.current_metrics
        self.current_metrics = None
        
        return final_metrics
    
    def record_image_processed(self, processing_time: float, is_duplicate: bool = False, is_error: bool = False):
        """
        Record processing of a single image.
        
        Args:
            processing_time: Time taken to process the image
            is_duplicate: Whether the image was a duplicate
            is_error: Whether an error occurred
        """
        if self.current_metrics is None:
            return
        
        self.current_metrics.images_processed += 1
        self.current_metrics.hashes_computed += 1
        
        if is_duplicate:
            self.current_metrics.duplicates_found += 1
        else:
            self.current_metrics.new_images += 1
        
        if is_error:
            self.current_metrics.errors += 1
        
        # Update timing metrics
        self.current_metrics.max_processing_time = max(
            self.current_metrics.max_processing_time, processing_time
        )
        self.current_metrics.min_processing_time = min(
            self.current_metrics.min_processing_time, processing_time
        )
    
    def record_cache_hit(self):
        """Record a cache hit."""
        if self.current_metrics is None:
            return
        
        self.current_metrics.cache_hits += 1
        self._update_cache_hit_rate()
    
    def record_cache_miss(self):
        """Record a cache miss."""
        if self.current_metrics is None:
            return
        
        self.current_metrics.cache_misses += 1
        self._update_cache_hit_rate()
    
    def _update_cache_hit_rate(self):
        """Update cache hit rate in real-time."""
        if self.current_metrics is None:
            return
        
        total_cache_requests = self.current_metrics.cache_hits + self.current_metrics.cache_misses
        if total_cache_requests > 0:
            self.current_metrics.cache_hit_rate = self.current_metrics.cache_hits / total_cache_requests
    
    def _update_system_metrics(self):
        """Update system resource metrics."""
        if self.current_metrics is None:
            return
        
        try:
            # Memory usage
            process = psutil.Process()
            memory_info = process.memory_info()
            self.current_metrics.memory_usage_mb = memory_info.rss / 1024 / 1024
            
            # CPU usage
            self.current_metrics.cpu_usage_percent = process.cpu_percent()
            
        except Exception as e:
            logger.warning("Failed to update system metrics", error=str(e))
    
    def _log_performance_summary(self):
        """Log performance summary."""
        if self.current_metrics is None:
            return
        
        metrics = self.current_metrics
        
        logger.info(
            "Image deduplication performance summary",
            total_duration=metrics.total_duration,
            images_processed=metrics.images_processed,
            duplicates_found=metrics.duplicates_found,
            new_images=metrics.new_images,
            errors=metrics.errors,
            avg_processing_time=metrics.avg_processing_time,
            max_processing_time=metrics.max_processing_time,
            min_processing_time=metrics.min_processing_time,
            memory_usage_mb=metrics.memory_usage_mb,
            cpu_usage_percent=metrics.cpu_usage_percent,
            cache_hit_rate=metrics.cache_hit_rate
        )
    
    def _check_performance_thresholds(self):
        """Check performance against thresholds and log warnings."""
        if self.current_metrics is None:
            return
        
        metrics = self.current_metrics
        
        # Check processing time
        if metrics.avg_processing_time > self.thresholds['max_processing_time']:
            logger.warning(
                "High average processing time detected",
                avg_processing_time=metrics.avg_processing_time,
                threshold=self.thresholds['max_processing_time']
            )
        
        # Check memory usage
        if metrics.memory_usage_mb > self.thresholds['max_memory_usage']:
            logger.warning(
                "High memory usage detected",
                memory_usage_mb=metrics.memory_usage_mb,
                threshold=self.thresholds['max_memory_usage']
            )
        
        # Check cache hit rate
        if metrics.cache_hit_rate < self.thresholds['min_cache_hit_rate']:
            logger.warning(
                "Low cache hit rate detected",
                cache_hit_rate=metrics.cache_hit_rate,
                threshold=self.thresholds['min_cache_hit_rate']
            )
        
        # Check error rate
        if metrics.images_processed > 0:
            error_rate = metrics.errors / metrics.images_processed
            if error_rate > self.thresholds['max_error_rate']:
                logger.warning(
                    "High error rate detected",
                    error_rate=error_rate,
                    threshold=self.thresholds['max_error_rate']
                )
    
    def get_performance_recommendations(self) -> List[str]:
        """
        Get performance optimization recommendations.
        
        Returns:
            List of optimization recommendations
        """
        recommendations = []
        
        if not self.metrics_history:
            return recommendations
        
        # Get latest metrics
        latest_metrics = self.metrics_history[-1]
        
        # Check for optimization opportunities
        if latest_metrics.cache_hit_rate < 0.5:
            recommendations.append(
                "Consider increasing cache size or improving cache strategy"
            )
        
        if latest_metrics.avg_processing_time > 2.0:
            recommendations.append(
                "Consider implementing parallel processing for hash computation"
            )
        
        if latest_metrics.memory_usage_mb > 200:
            recommendations.append(
                "Consider implementing streaming processing for large images"
            )
        
        if latest_metrics.duplicates_found > latest_metrics.new_images:
            recommendations.append(
                "High duplicate rate detected - consider improving image quality or source diversity"
            )
        
        return recommendations
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive performance statistics.
        
        Returns:
            Dictionary with performance statistics
        """
        if not self.metrics_history:
            return {}
        
        # Calculate aggregate stats
        total_images = sum(m.images_processed for m in self.metrics_history)
        total_duplicates = sum(m.duplicates_found for m in self.metrics_history)
        total_errors = sum(m.errors for m in self.metrics_history)
        total_duration = sum(m.total_duration for m in self.metrics_history)
        
        # Calculate averages
        avg_processing_time = sum(m.avg_processing_time for m in self.metrics_history) / len(self.metrics_history)
        avg_memory_usage = sum(m.memory_usage_mb for m in self.metrics_history) / len(self.metrics_history)
        avg_cache_hit_rate = sum(m.cache_hit_rate for m in self.metrics_history) / len(self.metrics_history)
        
        return {
            'total_sessions': len(self.metrics_history),
            'total_images_processed': total_images,
            'total_duplicates_found': total_duplicates,
            'total_errors': total_errors,
            'total_duration': total_duration,
            'avg_processing_time': avg_processing_time,
            'avg_memory_usage_mb': avg_memory_usage,
            'avg_cache_hit_rate': avg_cache_hit_rate,
            'duplicate_rate': total_duplicates / total_images if total_images > 0 else 0,
            'error_rate': total_errors / total_images if total_images > 0 else 0,
            'recommendations': self.get_performance_recommendations()
        }
    
    def reset_history(self):
        """Reset performance metrics history."""
        self.metrics_history.clear()
        logger.info("Performance metrics history reset")
