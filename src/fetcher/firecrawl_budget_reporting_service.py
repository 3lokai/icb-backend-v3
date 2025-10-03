"""
Firecrawl budget reporting service for operations team.

This module provides:
- Budget reporting for operations team
- Integration with monitoring system
- Budget usage reporting
- Cost analysis and trends
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timezone, timedelta
from structlog import get_logger

from src.fetcher.firecrawl_budget_management_service import FirecrawlBudgetManagementService
from src.monitoring.firecrawl_metrics import FirecrawlMetrics, FirecrawlAlertManager

logger = get_logger(__name__)


class FirecrawlBudgetReportingService:
    """
    Budget reporting service for operations team.
    
    Features:
    - Budget usage reporting
    - Cost analysis and trends
    - Integration with monitoring
    - Operations team dashboard data
    """
    
    def __init__(self, budget_service: FirecrawlBudgetManagementService):
        self.budget_service = budget_service
        self.metrics = FirecrawlMetrics()
        self.alert_manager = FirecrawlAlertManager(self.metrics)
        
        logger.info("Firecrawl budget reporting service initialized")
    
    async def generate_budget_report(self, roaster_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate comprehensive budget report.
        
        Args:
            roaster_id: Optional specific roaster ID, None for all roasters
            
        Returns:
            Dictionary with budget report data
        """
        try:
            logger.info(
                "Generating budget report",
                roaster_id=roaster_id or "all_roasters"
            )
            
            # Get base budget data
            budget_data = self.budget_service.get_budget_report()
            
            # Get metrics summary
            metrics_summary = self.metrics.get_metrics_summary()
            
            # Get active alerts
            active_alerts = self.alert_manager.get_active_alerts()
            
            # Generate roaster-specific or global report
            if roaster_id:
                roaster_report = await self._generate_roaster_report(roaster_id)
                report = {
                    'report_type': 'roaster_specific',
                    'roaster_id': roaster_id,
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'roaster_data': roaster_report,
                    'alerts': active_alerts
                }
            else:
                global_report = await self._generate_global_report()
                report = {
                    'report_type': 'global',
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'global_data': global_report,
                    'budget_data': budget_data,
                    'metrics_summary': metrics_summary,
                    'alerts': active_alerts
                }
            
            logger.info(
                "Budget report generated",
                report_type=report['report_type'],
                roaster_id=roaster_id
            )
            
            return report
            
        except Exception as e:
            logger.error(
                "Error generating budget report",
                roaster_id=roaster_id,
                error=str(e)
            )
            
            return {
                'error': str(e),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
    
    async def _generate_roaster_report(self, roaster_id: str) -> Dict[str, Any]:
        """Generate report for a specific roaster."""
        try:
            # Get roaster budget status
            budget_status = await self.budget_service.get_roaster_budget_status(roaster_id)
            
            if not budget_status:
                return {
                    'error': f'No budget data found for roaster {roaster_id}',
                    'roaster_id': roaster_id
                }
            
            # Calculate usage trends (simplified - in real implementation, use historical data)
            usage_trend = self._calculate_usage_trend(roaster_id)
            
            # Determine status and recommendations
            status_info = self._analyze_budget_status(budget_status)
            
            return {
                'roaster_id': roaster_id,
                'budget_status': budget_status,
                'usage_trend': usage_trend,
                'status_analysis': status_info,
                'recommendations': self._generate_recommendations(budget_status, usage_trend)
            }
            
        except Exception as e:
            logger.error(
                "Error generating roaster report",
                roaster_id=roaster_id,
                error=str(e)
            )
            
            return {
                'error': str(e),
                'roaster_id': roaster_id
            }
    
    async def _generate_global_report(self) -> Dict[str, Any]:
        """Generate global budget report for all roasters."""
        try:
            # Get global budget data
            budget_data = self.budget_service.get_budget_report()
            
            # Calculate global statistics
            global_stats = self._calculate_global_stats(budget_data)
            
            # Get roaster summaries
            roaster_summaries = await self._get_roaster_summaries()
            
            return {
                'global_statistics': global_stats,
                'roaster_summaries': roaster_summaries,
                'budget_distribution': self._analyze_budget_distribution(roaster_summaries),
                'cost_analysis': self._analyze_costs(roaster_summaries)
            }
            
        except Exception as e:
            logger.error("Error generating global report", error=str(e))
            return {'error': str(e)}
    
    def _calculate_usage_trend(self, roaster_id: str) -> Dict[str, Any]:
        """Calculate usage trend for a roaster (simplified implementation)."""
        # In a real implementation, this would analyze historical data
        return {
            'trend': 'stable',  # stable, increasing, decreasing
            'daily_average': 0,  # Average daily usage
            'weekly_average': 0,  # Average weekly usage
            'projected_exhaustion': None  # When budget will be exhausted
        }
    
    def _analyze_budget_status(self, budget_status: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze budget status and provide insights."""
        usage_percentage = budget_status['usage_percentage']
        remaining_budget = budget_status['remaining_budget']
        
        if usage_percentage >= 100:
            status = 'exhausted'
            priority = 'critical'
        elif usage_percentage >= 90:
            status = 'critical'
            priority = 'high'
        elif usage_percentage >= 80:
            status = 'warning'
            priority = 'medium'
        else:
            status = 'healthy'
            priority = 'low'
        
        return {
            'status': status,
            'priority': priority,
            'usage_percentage': usage_percentage,
            'remaining_budget': remaining_budget,
            'firecrawl_enabled': budget_status['firecrawl_enabled']
        }
    
    def _generate_recommendations(
        self, 
        budget_status: Dict[str, Any], 
        usage_trend: Dict[str, Any]
    ) -> List[str]:
        """Generate recommendations based on budget status and trends."""
        recommendations = []
        
        usage_percentage = budget_status['usage_percentage']
        
        if usage_percentage >= 100:
            recommendations.extend([
                'Budget exhausted - disable Firecrawl operations',
                'Consider increasing budget limit',
                'Review usage patterns for optimization'
            ])
        elif usage_percentage >= 90:
            recommendations.extend([
                'Budget critically low - monitor closely',
                'Consider increasing budget limit',
                'Prepare fallback procedures'
            ])
        elif usage_percentage >= 80:
            recommendations.extend([
                'Budget warning - monitor usage',
                'Consider budget increase if needed',
                'Review operation efficiency'
            ])
        else:
            recommendations.append('Budget healthy - continue normal operations')
        
        return recommendations
    
    def _calculate_global_stats(self, budget_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate global budget statistics."""
        roaster_budgets = budget_data.get('roaster_budgets', {})
        
        if not roaster_budgets:
            return {
                'total_roasters': 0,
                'total_budget_allocated': 0,
                'total_budget_used': 0,
                'average_usage_percentage': 0
            }
        
        total_roasters = len(roaster_budgets)
        total_budget_allocated = sum(
            budget['budget_limit'] for budget in roaster_budgets.values()
        )
        total_budget_used = sum(
            budget['used_budget'] for budget in roaster_budgets.values()
        )
        
        average_usage_percentage = (
            (total_budget_used / total_budget_allocated * 100) 
            if total_budget_allocated > 0 else 0
        )
        
        return {
            'total_roasters': total_roasters,
            'total_budget_allocated': total_budget_allocated,
            'total_budget_used': total_budget_used,
            'total_remaining_budget': total_budget_allocated - total_budget_used,
            'average_usage_percentage': average_usage_percentage
        }
    
    async def _get_roaster_summaries(self) -> List[Dict[str, Any]]:
        """Get summaries for all roasters."""
        # In a real implementation, this would query all roasters from database
        # For now, return empty list as we don't have database integration
        return []
    
    def _analyze_budget_distribution(self, roaster_summaries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze budget distribution across roasters."""
        # Simplified implementation
        return {
            'distribution_type': 'equal',  # equal, weighted, custom
            'variance': 0,  # Budget variance across roasters
            'recommendations': ['Monitor individual roaster usage patterns']
        }
    
    def _analyze_costs(self, roaster_summaries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze cost patterns and efficiency."""
        # Simplified implementation
        return {
            'cost_per_operation': 0,  # Average cost per operation
            'efficiency_score': 0,  # Efficiency score (0-100)
            'optimization_opportunities': [
                'Review operation frequency',
                'Optimize batch processing',
                'Consider cost-effective alternatives'
            ]
        }
    
    async def generate_operations_dashboard_data(self) -> Dict[str, Any]:
        """Generate data for operations team dashboard."""
        try:
            # Get current budget report
            budget_report = await self.generate_budget_report()
            
            # Get metrics summary
            metrics_summary = self.metrics.get_metrics_summary()
            
            # Get active alerts
            active_alerts = self.alert_manager.get_active_alerts()
            
            # Generate dashboard data
            dashboard_data = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'budget_overview': budget_report.get('global_data', {}),
                'metrics_summary': metrics_summary,
                'active_alerts': active_alerts,
                'system_health': self._assess_system_health(metrics_summary, active_alerts)
            }
            
            return dashboard_data
            
        except Exception as e:
            logger.error("Error generating dashboard data", error=str(e))
            return {'error': str(e)}
    
    def _assess_system_health(
        self, 
        metrics_summary: Dict[str, Any], 
        active_alerts: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Assess overall system health."""
        # Count critical alerts
        critical_alerts = len([alert for alert in active_alerts if alert.get('severity') == 'critical'])
        warning_alerts = len([alert for alert in active_alerts if alert.get('severity') == 'warning'])
        
        # Determine health status
        if critical_alerts > 0:
            health_status = 'critical'
        elif warning_alerts > 2:
            health_status = 'warning'
        else:
            health_status = 'healthy'
        
        return {
            'status': health_status,
            'critical_alerts': critical_alerts,
            'warning_alerts': warning_alerts,
            'total_alerts': len(active_alerts),
            'recommendations': self._generate_health_recommendations(health_status, active_alerts)
        }
    
    def _generate_health_recommendations(
        self, 
        health_status: str, 
        active_alerts: List[Dict[str, Any]]
    ) -> List[str]:
        """Generate health recommendations."""
        recommendations = []
        
        if health_status == 'critical':
            recommendations.extend([
                'Immediate attention required',
                'Review critical alerts',
                'Consider system maintenance'
            ])
        elif health_status == 'warning':
            recommendations.extend([
                'Monitor system closely',
                'Address warning alerts',
                'Review system configuration'
            ])
        else:
            recommendations.append('System operating normally')
        
        return recommendations
