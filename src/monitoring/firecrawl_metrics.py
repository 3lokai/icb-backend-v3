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
    
    def record_price_only_usage(
        self,
        urls_processed: int,
        successful_extractions: int,
        cost: float,
        cost_efficiency: float
    ):
        """
        Record price-only usage metrics.
        
        Args:
            urls_processed: Number of URLs processed
            successful_extractions: Number of successful extractions
            cost: Cost of the operation
            cost_efficiency: Cost efficiency ratio
        """
        try:
            # Initialize price-only metrics if not exists
            if 'price_only_metrics' not in self.metrics:
                self.metrics['price_only_metrics'] = {
                    'total_operations': 0,
                    'total_urls_processed': 0,
                    'total_successful_extractions': 0,
                    'total_cost': 0.0,
                    'average_cost_efficiency': 0.0,
                    'cost_optimization_percentage': 0.0
                }
            
            # Update price-only metrics
            price_only_metrics = self.metrics['price_only_metrics']
            price_only_metrics['total_operations'] += 1
            price_only_metrics['total_urls_processed'] += urls_processed
            price_only_metrics['total_successful_extractions'] += successful_extractions
            price_only_metrics['total_cost'] += cost
            
            # Calculate running average cost efficiency
            total_operations = price_only_metrics['total_operations']
            total_urls = price_only_metrics['total_urls_processed']
            total_successful = price_only_metrics['total_successful_extractions']
            
            price_only_metrics['average_cost_efficiency'] = total_successful / max(total_urls, 1)
            
            # Calculate cost optimization percentage
            # Assume full refresh costs 3x more than price-only
            full_refresh_equivalent_cost = price_only_metrics['total_cost'] * 3
            cost_savings = full_refresh_equivalent_cost - price_only_metrics['total_cost']
            price_only_metrics['cost_optimization_percentage'] = (
                cost_savings / max(full_refresh_equivalent_cost, 1)
            ) * 100
            
            logger.info(
                "Recorded price-only usage metrics",
                urls_processed=urls_processed,
                successful_extractions=successful_extractions,
                cost=cost,
                cost_efficiency=cost_efficiency,
                total_operations=total_operations,
                cost_optimization_percentage=price_only_metrics['cost_optimization_percentage']
            )
            
        except Exception as e:
            logger.error(
                "Failed to record price-only usage metrics",
                error=str(e),
                urls_processed=urls_processed,
                successful_extractions=successful_extractions,
                cost=cost
            )
    
    def get_price_only_metrics(self) -> Dict[str, Any]:
        """Get price-only metrics summary."""
        try:
            if 'price_only_metrics' not in self.metrics:
                return {
                    'total_operations': 0,
                    'total_urls_processed': 0,
                    'total_successful_extractions': 0,
                    'total_cost': 0.0,
                    'average_cost_efficiency': 0.0,
                    'cost_optimization_percentage': 0.0,
                    'status': 'No price-only operations recorded'
                }
            
            price_only_metrics = self.metrics['price_only_metrics']
            
            return {
                'total_operations': price_only_metrics['total_operations'],
                'total_urls_processed': price_only_metrics['total_urls_processed'],
                'total_successful_extractions': price_only_metrics['total_successful_extractions'],
                'total_cost': price_only_metrics['total_cost'],
                'average_cost_efficiency': price_only_metrics['average_cost_efficiency'],
                'cost_optimization_percentage': price_only_metrics['cost_optimization_percentage'],
                'status': 'Price-only metrics available'
            }
            
        except Exception as e:
            logger.error(
                "Failed to get price-only metrics",
                error=str(e)
            )
            return {
                'error': str(e),
                'status': 'Error retrieving price-only metrics'
            }
    
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
    
    async def send_price_only_efficiency_alert(
        self,
        cost_efficiency: float,
        threshold: float
    ):
        """
        Send alert for low price-only efficiency.
        
        Args:
            cost_efficiency: Current cost efficiency ratio
            threshold: Efficiency threshold
        """
        try:
            alert = {
                'type': 'price_only_efficiency',
                'severity': 'warning',
                'message': f'Price-only efficiency below threshold: {cost_efficiency:.2f} < {threshold}',
                'cost_efficiency': cost_efficiency,
                'threshold': threshold,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            self.active_alerts.append(alert)
            
            logger.warning(
                "Price-only efficiency alert triggered",
                cost_efficiency=cost_efficiency,
                threshold=threshold
            )
            
        except Exception as e:
            logger.error(
                "Failed to send price-only efficiency alert",
                error=str(e),
                cost_efficiency=cost_efficiency,
                threshold=threshold
            )
    
    async def send_price_only_cost_alert(
        self,
        cost: float,
        threshold: float
    ):
        """
        Send alert for high price-only cost.
        
        Args:
            cost: Current cost
            threshold: Cost threshold
        """
        try:
            alert = {
                'type': 'price_only_cost',
                'severity': 'warning',
                'message': f'Price-only cost above threshold: ${cost:.2f} > ${threshold}',
                'cost': cost,
                'threshold': threshold,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            self.active_alerts.append(alert)
            
            logger.warning(
                "Price-only cost alert triggered",
                cost=cost,
                threshold=threshold
            )
            
        except Exception as e:
            logger.error(
                "Failed to send price-only cost alert",
                error=str(e),
                cost=cost,
                threshold=threshold
            )
    
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
        
        # Check budget usage
        budget_used = summary['budget']['total_budget_used']
        budget_limit = self.metrics.metrics.get('budget_limit')
        if budget_limit and budget_used > 0:
            budget_usage_percent = (budget_used / budget_limit) * 100
            if budget_usage_percent > self.alert_thresholds['budget_usage_percent']:
                alerts.append({
                    'type': 'budget_near_exhaustion',
                    'severity': 'warning' if budget_usage_percent < 95 else 'critical',
                    'message': f'Budget usage high: {budget_usage_percent:.1f}%',
                    'threshold': self.alert_thresholds['budget_usage_percent'],
                    'current_value': budget_usage_percent
                })
        
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
        
        # Check for no URLs discovered in recent operations
        total_urls = summary['discovery']['total_urls_discovered']
        total_operations = summary['overview']['total_operations']
        if total_operations >= 5 and total_urls == 0:  # At least 5 operations with no URLs
            alerts.append({
                'type': 'no_urls_discovered',
                'severity': 'warning',
                'message': f'No URLs discovered in {total_operations} operations',
                'threshold': 0,
                'current_value': total_urls
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
