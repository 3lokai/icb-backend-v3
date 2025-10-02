"""
Firecrawl monitoring and metrics collection.

This module provides:
- Firecrawl operation metrics tracking
- Performance monitoring
- Budget usage tracking
- Error rate monitoring
- Health check integration
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import time

from structlog import get_logger

logger = get_logger(__name__)


class FirecrawlMetrics:
    """
    Firecrawl operation metrics collector.
    
    Tracks:
    - Map operations performed
    - URLs discovered
    - Budget usage
    - Error rates
    - Performance metrics
    """
    
    def __init__(self):
        self.metrics = {
            'total_map_operations': 0,
            'successful_map_operations': 0,
            'failed_map_operations': 0,
            'total_urls_discovered': 0,
            'total_budget_used': 0,
            'average_operation_time': 0.0,
            'operation_times': [],
            'error_counts': {},
            'roaster_metrics': {},
            'start_time': datetime.now(timezone.utc),
            'last_operation_time': None
        }
        
        logger.info("Firecrawl metrics initialized")
    
    def record_map_operation(
        self,
        roaster_id: str,
        operation_type: str,
        success: bool,
        urls_discovered: int = 0,
        budget_used: int = 0,
        operation_time: float = 0.0,
        error_type: Optional[str] = None
    ):
        """Record a map operation."""
        self.metrics['total_map_operations'] += 1
        self.metrics['last_operation_time'] = datetime.now(timezone.utc)
        
        if success:
            self.metrics['successful_map_operations'] += 1
            self.metrics['total_urls_discovered'] += urls_discovered
            self.metrics['total_budget_used'] += budget_used
        else:
            self.metrics['failed_map_operations'] += 1
            if error_type:
                self.metrics['error_counts'][error_type] = self.metrics['error_counts'].get(error_type, 0) + 1
        
        # Track operation time
        if operation_time > 0:
            self.metrics['operation_times'].append(operation_time)
            # Keep only last 100 operation times
            if len(self.metrics['operation_times']) > 100:
                self.metrics['operation_times'] = self.metrics['operation_times'][-100:]
            
            # Update average
            self.metrics['average_operation_time'] = sum(self.metrics['operation_times']) / len(self.metrics['operation_times'])
        
        # Track roaster-specific metrics
        if roaster_id not in self.metrics['roaster_metrics']:
            self.metrics['roaster_metrics'][roaster_id] = {
                'total_operations': 0,
                'successful_operations': 0,
                'failed_operations': 0,
                'total_urls_discovered': 0,
                'total_budget_used': 0,
                'last_operation_time': None
            }
        
        roaster_metrics = self.metrics['roaster_metrics'][roaster_id]
        roaster_metrics['total_operations'] += 1
        roaster_metrics['last_operation_time'] = datetime.now(timezone.utc)
        
        if success:
            roaster_metrics['successful_operations'] += 1
            roaster_metrics['total_urls_discovered'] += urls_discovered
            roaster_metrics['total_budget_used'] += budget_used
        else:
            roaster_metrics['failed_operations'] += 1
        
        logger.info(
            "Firecrawl operation recorded",
            roaster_id=roaster_id,
            operation_type=operation_type,
            success=success,
            urls_discovered=urls_discovered,
            budget_used=budget_used,
            operation_time=operation_time,
            error_type=error_type
        )
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get comprehensive metrics summary."""
        total_operations = self.metrics['total_map_operations']
        successful_operations = self.metrics['successful_map_operations']
        failed_operations = self.metrics['failed_map_operations']
        
        success_rate = (successful_operations / total_operations * 100) if total_operations > 0 else 0
        failure_rate = (failed_operations / total_operations * 100) if total_operations > 0 else 0
        
        # Calculate uptime
        uptime_seconds = (datetime.now(timezone.utc) - self.metrics['start_time']).total_seconds()
        uptime_hours = uptime_seconds / 3600
        
        return {
            'overview': {
                'total_operations': total_operations,
                'successful_operations': successful_operations,
                'failed_operations': failed_operations,
                'success_rate_percent': round(success_rate, 2),
                'failure_rate_percent': round(failure_rate, 2),
                'uptime_hours': round(uptime_hours, 2)
            },
            'discovery': {
                'total_urls_discovered': self.metrics['total_urls_discovered'],
                'average_urls_per_operation': round(
                    self.metrics['total_urls_discovered'] / max(successful_operations, 1), 2
                )
            },
            'budget': {
                'total_budget_used': self.metrics['total_budget_used'],
                'average_budget_per_operation': round(
                    self.metrics['total_budget_used'] / max(successful_operations, 1), 2
                )
            },
            'performance': {
                'average_operation_time_seconds': round(self.metrics['average_operation_time'], 2),
                'total_operation_time_seconds': round(sum(self.metrics['operation_times']), 2)
            },
            'errors': self.metrics['error_counts'],
            'roaster_breakdown': self.metrics['roaster_metrics'],
            'last_operation_time': self.metrics['last_operation_time'].isoformat() if self.metrics['last_operation_time'] else None
        }
    
    def get_roaster_metrics(self, roaster_id: str) -> Optional[Dict[str, Any]]:
        """Get metrics for a specific roaster."""
        if roaster_id not in self.metrics['roaster_metrics']:
            return None
        
        roaster_metrics = self.metrics['roaster_metrics'][roaster_id]
        total_ops = roaster_metrics['total_operations']
        successful_ops = roaster_metrics['successful_operations']
        
        success_rate = (successful_ops / total_ops * 100) if total_ops > 0 else 0
        
        return {
            'roaster_id': roaster_id,
            'total_operations': total_ops,
            'successful_operations': successful_ops,
            'failed_operations': roaster_metrics['failed_operations'],
            'success_rate_percent': round(success_rate, 2),
            'total_urls_discovered': roaster_metrics['total_urls_discovered'],
            'total_budget_used': roaster_metrics['total_budget_used'],
            'last_operation_time': roaster_metrics['last_operation_time'].isoformat() if roaster_metrics['last_operation_time'] else None
        }
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get health status based on recent metrics."""
        total_operations = self.metrics['total_map_operations']
        failed_operations = self.metrics['failed_map_operations']
        
        # Calculate health based on recent performance
        if total_operations == 0:
            return {
                'status': 'unknown',
                'message': 'No operations recorded yet',
                'last_operation_time': None
            }
        
        failure_rate = (failed_operations / total_operations * 100) if total_operations > 0 else 0
        
        # Determine health status
        if failure_rate > 50:
            status = 'unhealthy'
            message = f'High failure rate: {failure_rate:.1f}%'
        elif failure_rate > 25:
            status = 'degraded'
            message = f'Elevated failure rate: {failure_rate:.1f}%'
        else:
            status = 'healthy'
            message = f'Normal operation: {failure_rate:.1f}% failure rate'
        
        return {
            'status': status,
            'message': message,
            'total_operations': total_operations,
            'failure_rate_percent': round(failure_rate, 2),
            'last_operation_time': self.metrics['last_operation_time'].isoformat() if self.metrics['last_operation_time'] else None
        }
    
    def reset_metrics(self):
        """Reset all metrics."""
        self.metrics = {
            'total_map_operations': 0,
            'successful_map_operations': 0,
            'failed_map_operations': 0,
            'total_urls_discovered': 0,
            'total_budget_used': 0,
            'average_operation_time': 0.0,
            'operation_times': [],
            'error_counts': {},
            'roaster_metrics': {},
            'start_time': datetime.now(timezone.utc),
            'last_operation_time': None
        }
        
        logger.info("Firecrawl metrics reset")
    
    def export_metrics(self) -> Dict[str, Any]:
        """Export metrics for external monitoring systems."""
        return {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'metrics': self.get_metrics_summary(),
            'health': self.get_health_status()
        }


class FirecrawlAlertManager:
    """Manages alerts for Firecrawl operations."""
    
    def __init__(self, metrics: FirecrawlMetrics):
        self.metrics = metrics
        self.alert_thresholds = {
            'failure_rate_percent': 25.0,
            'budget_usage_percent': 80.0,
            'operation_time_seconds': 60.0
        }
        self.active_alerts = []
        
        logger.info("Firecrawl alert manager initialized")
    
    def check_alerts(self) -> List[Dict[str, Any]]:
        """Check for alert conditions."""
        alerts = []
        summary = self.metrics.get_metrics_summary()
        
        # Check failure rate
        failure_rate = summary['overview']['failure_rate_percent']
        if failure_rate > self.alert_thresholds['failure_rate_percent']:
            alerts.append({
                'type': 'high_failure_rate',
                'severity': 'warning' if failure_rate < 50 else 'critical',
                'message': f'High failure rate: {failure_rate:.1f}%',
                'threshold': self.alert_thresholds['failure_rate_percent'],
                'current_value': failure_rate
            })
        
        # Check budget usage (if we have budget limit info)
        # This would need to be passed in from configuration
        # For now, we'll skip this check
        
        # Check operation time
        avg_time = summary['performance']['average_operation_time_seconds']
        if avg_time > self.alert_thresholds['operation_time_seconds']:
            alerts.append({
                'type': 'slow_operations',
                'severity': 'warning',
                'message': f'Slow operations: {avg_time:.1f}s average',
                'threshold': self.alert_thresholds['operation_time_seconds'],
                'current_value': avg_time
            })
        
        # Update active alerts
        self.active_alerts = alerts
        
        if alerts:
            logger.warning("Firecrawl alerts triggered", alerts=alerts)
        
        return alerts
    
    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get currently active alerts."""
        return self.active_alerts.copy()
    
    def clear_alerts(self):
        """Clear all active alerts."""
        self.active_alerts = []
        logger.info("Firecrawl alerts cleared")
