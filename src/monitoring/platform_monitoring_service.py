"""
Platform monitoring service for tracking platform distribution and usage statistics.

This service provides methods to query the platform monitoring views created for
Story A.6: Platform-Based Fetcher Selection with Automatic Fallback.
"""

import os
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from supabase import create_client, Client
from structlog import get_logger

logger = get_logger(__name__)


class PlatformMonitoringService:
    """
    Service for monitoring platform distribution and usage statistics.
    
    Provides methods to query platform monitoring views and generate
    reports for platform-based fetcher selection monitoring.
    """
    
    def __init__(self, supabase_client: Optional[Client] = None):
        """
        Initialize the platform monitoring service.
        
        Args:
            supabase_client: Optional Supabase client instance.
                           If not provided, will create one from environment variables.
        """
        if supabase_client:
            self.supabase_client = supabase_client
        else:
            # Create Supabase client from environment variables
            supabase_url = os.getenv('SUPABASE_URL')
            supabase_key = os.getenv('SUPABASE_KEY')
            
            if not supabase_url or not supabase_key:
                raise ValueError(
                    "SUPABASE_URL and SUPABASE_KEY environment variables are required"
                )
            
            self.supabase_client = create_client(supabase_url, supabase_key)
    
    async def get_platform_distribution(self) -> List[Dict[str, Any]]:
        """
        Get platform distribution summary.
        
        Returns:
            List of platform distribution data with counts and percentages
        """
        try:
            result = self.supabase_client.table("platform_distribution").select("*").execute()
            
            logger.info(
                "Retrieved platform distribution",
                platform_count=len(result.data)
            )
            
            return result.data
            
        except Exception as e:
            logger.error(
                "Failed to get platform distribution",
                error=str(e)
            )
            return []
    
    async def get_platform_usage_stats(self) -> List[Dict[str, Any]]:
        """
        Get detailed platform usage statistics.
        
        Returns:
            List of platform usage statistics including coffee counts, ratings, and pricing
        """
        try:
            result = self.supabase_client.table("platform_usage_stats").select("*").execute()
            
            logger.info(
                "Retrieved platform usage stats",
                platform_count=len(result.data)
            )
            
            return result.data
            
        except Exception as e:
            logger.error(
                "Failed to get platform usage stats",
                error=str(e)
            )
            return []
    
    async def get_firecrawl_usage_tracking(self) -> List[Dict[str, Any]]:
        """
        Get Firecrawl usage and budget consumption tracking.
        
        Returns:
            List of Firecrawl usage data across platforms
        """
        try:
            result = self.supabase_client.table("firecrawl_usage_tracking").select("*").execute()
            
            logger.info(
                "Retrieved Firecrawl usage tracking",
                platform_count=len(result.data)
            )
            
            return result.data
            
        except Exception as e:
            logger.error(
                "Failed to get Firecrawl usage tracking",
                error=str(e)
            )
            return []
    
    async def get_platform_performance_metrics(self) -> List[Dict[str, Any]]:
        """
        Get platform performance metrics.
        
        Returns:
            List of platform performance data including averages and coverage
        """
        try:
            result = self.supabase_client.table("platform_performance_metrics").select("*").execute()
            
            logger.info(
                "Retrieved platform performance metrics",
                platform_count=len(result.data)
            )
            
            return result.data
            
        except Exception as e:
            logger.error(
                "Failed to get platform performance metrics",
                error=str(e)
            )
            return []
    
    async def get_recent_platform_activity(self) -> List[Dict[str, Any]]:
        """
        Get recent platform activity and changes.
        
        Returns:
            List of recent activity data for each platform
        """
        try:
            result = self.supabase_client.table("recent_platform_activity").select("*").execute()
            
            logger.info(
                "Retrieved recent platform activity",
                platform_count=len(result.data)
            )
            
            return result.data
            
        except Exception as e:
            logger.error(
                "Failed to get recent platform activity",
                error=str(e)
            )
            return []
    
    async def get_platform_health_dashboard(self) -> List[Dict[str, Any]]:
        """
        Get comprehensive platform health dashboard.
        
        Returns:
            List of platform health data with activity status
        """
        try:
            result = self.supabase_client.table("platform_health_dashboard").select("*").execute()
            
            logger.info(
                "Retrieved platform health dashboard",
                platform_count=len(result.data)
            )
            
            return result.data
            
        except Exception as e:
            logger.error(
                "Failed to get platform health dashboard",
                error=str(e)
            )
            return []
    
    async def get_platform_summary_report(self) -> Dict[str, Any]:
        """
        Get a comprehensive platform summary report.
        
        Returns:
            Dictionary containing all platform monitoring data
        """
        try:
            # Get all monitoring data
            distribution = await self.get_platform_distribution()
            usage_stats = await self.get_platform_usage_stats()
            firecrawl_usage = await self.get_firecrawl_usage_tracking()
            performance_metrics = await self.get_platform_performance_metrics()
            recent_activity = await self.get_recent_platform_activity()
            health_dashboard = await self.get_platform_health_dashboard()
            
            # Calculate summary statistics
            total_roasters = sum(item.get('roaster_count', 0) for item in distribution)
            total_coffees = sum(item.get('total_coffees', 0) for item in usage_stats)
            total_firecrawl_enabled = sum(item.get('firecrawl_enabled_count', 0) for item in firecrawl_usage)
            
            summary = {
                'generated_at': datetime.now(timezone.utc).isoformat(),
                'total_roasters': total_roasters,
                'total_coffees': total_coffees,
                'total_firecrawl_enabled': total_firecrawl_enabled,
                'firecrawl_percentage': round(total_firecrawl_enabled * 100.0 / total_roasters, 2) if total_roasters > 0 else 0,
                'platform_distribution': distribution,
                'platform_usage_stats': usage_stats,
                'firecrawl_usage_tracking': firecrawl_usage,
                'platform_performance_metrics': performance_metrics,
                'recent_platform_activity': recent_activity,
                'platform_health_dashboard': health_dashboard
            }
            
            logger.info(
                "Generated platform summary report",
                total_roasters=total_roasters,
                total_coffees=total_coffees,
                firecrawl_enabled=total_firecrawl_enabled
            )
            
            return summary
            
        except Exception as e:
            logger.error(
                "Failed to generate platform summary report",
                error=str(e)
            )
            return {}
    
    async def get_platform_alerts(self) -> List[Dict[str, Any]]:
        """
        Get platform monitoring alerts based on health dashboard data.
        
        Returns:
            List of alerts for platforms that need attention
        """
        try:
            health_data = await self.get_platform_health_dashboard()
            alerts = []
            
            for platform_data in health_data:
                platform = platform_data.get('platform')
                active_percentage = platform_data.get('active_percentage', 0)
                activity_status = platform_data.get('activity_status', 'Unknown')
                avg_rating = platform_data.get('avg_rating', 0)
                
                # Generate alerts based on thresholds
                if active_percentage < 50:
                    alerts.append({
                        'platform': platform,
                        'alert_type': 'low_activity',
                        'message': f'Platform {platform} has low activity ({active_percentage}% active roasters)',
                        'severity': 'warning',
                        'value': active_percentage,
                        'threshold': 50
                    })
                
                if activity_status == 'Stale':
                    alerts.append({
                        'platform': platform,
                        'alert_type': 'stale_activity',
                        'message': f'Platform {platform} has stale activity (no updates in 30+ days)',
                        'severity': 'critical',
                        'value': activity_status,
                        'threshold': 'Recent'
                    })
                
                if avg_rating < 3.0 and avg_rating > 0:
                    alerts.append({
                        'platform': platform,
                        'alert_type': 'low_rating',
                        'message': f'Platform {platform} has low average rating ({avg_rating})',
                        'severity': 'warning',
                        'value': avg_rating,
                        'threshold': 3.0
                    })
            
            logger.info(
                "Generated platform alerts",
                alert_count=len(alerts)
            )
            
            return alerts
            
        except Exception as e:
            logger.error(
                "Failed to generate platform alerts",
                error=str(e)
            )
            return []
    
    async def close(self):
        """Close the monitoring service and clean up resources."""
        # Supabase client doesn't need explicit closing
        logger.info("Platform monitoring service closed")
