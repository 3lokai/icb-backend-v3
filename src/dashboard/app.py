"""
Operations Dashboard Flask Application

This dashboard provides real-time monitoring of the coffee scraping pipeline,
integrating with existing G.1-G.3 monitoring infrastructure.
"""

import os
import asyncio
from datetime import datetime, timezone
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import json

# Import existing monitoring services
from src.monitoring.platform_monitoring_service import PlatformMonitoringService
from src.fetcher.firecrawl_budget_reporting_service import FirecrawlBudgetReportingService
from src.fetcher.firecrawl_budget_management_service import FirecrawlBudgetManagementService
from src.monitoring.firecrawl_metrics import FirecrawlMetrics, FirecrawlAlertManager

app = Flask(__name__)
CORS(app)

# Configuration
app.config['SECRET_KEY'] = os.getenv('DASHBOARD_SECRET_KEY', 'dev-secret-key-change-in-production')

# Initialize monitoring services
platform_monitoring = PlatformMonitoringService()
firecrawl_metrics = FirecrawlMetrics()
firecrawl_alerts = FirecrawlAlertManager(firecrawl_metrics)

# Initialize budget services
budget_management = FirecrawlBudgetManagementService(
    budget_tracker=None,  # Will be initialized when needed
    supabase_client=None
)
budget_reporting = FirecrawlBudgetReportingService(budget_management)


@app.route('/')
def dashboard():
    """Main dashboard page."""
    return render_template('dashboard.html')


@app.route('/api/health')
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'services': {
            'platform_monitoring': 'available',
            'firecrawl_metrics': 'available',
            'budget_reporting': 'available'
        }
    })


@app.route('/api/dashboard/overview')
def dashboard_overview():
    """Get dashboard overview data."""
    try:
        # Get platform summary
        platform_summary = asyncio.run(platform_monitoring.get_platform_summary_report())
        
        # Get Firecrawl metrics
        firecrawl_metrics_data = firecrawl_metrics.get_metrics_summary()
        
        # Get active alerts
        active_alerts = firecrawl_alerts.get_active_alerts()
        
        overview = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'platform_summary': platform_summary,
            'firecrawl_metrics': firecrawl_metrics_data,
            'active_alerts': active_alerts,
            'system_health': _assess_system_health(firecrawl_metrics_data, active_alerts)
        }
        
        return jsonify(overview)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/dashboard/roasters')
def roasters_data():
    """Get roaster-specific monitoring data."""
    try:
        # Get platform distribution
        distribution = asyncio.run(platform_monitoring.get_platform_distribution())
        
        # Get platform usage stats
        usage_stats = asyncio.run(platform_monitoring.get_platform_usage_stats())
        
        # Get recent activity
        recent_activity = asyncio.run(platform_monitoring.get_recent_platform_activity())
        
        roasters_data = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'distribution': distribution,
            'usage_stats': usage_stats,
            'recent_activity': recent_activity
        }
        
        return jsonify(roasters_data)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/dashboard/budget')
def budget_data():
    """Get budget and cost monitoring data."""
    try:
        # Get budget report
        budget_report = asyncio.run(budget_reporting.generate_budget_report())
        
        # Get operations dashboard data
        operations_data = asyncio.run(budget_reporting.generate_operations_dashboard_data())
        
        budget_data = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'budget_report': budget_report,
            'operations_data': operations_data
        }
        
        return jsonify(budget_data)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/dashboard/metrics')
def metrics_data():
    """Get detailed metrics data."""
    try:
        # Get platform performance metrics
        performance_metrics = asyncio.run(platform_monitoring.get_platform_performance_metrics())
        
        # Get platform health dashboard
        health_dashboard = asyncio.run(platform_monitoring.get_platform_health_dashboard())
        
        # Get Firecrawl usage tracking
        firecrawl_usage = asyncio.run(platform_monitoring.get_firecrawl_usage_tracking())
        
        metrics_data = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'performance_metrics': performance_metrics,
            'health_dashboard': health_dashboard,
            'firecrawl_usage': firecrawl_usage
        }
        
        return jsonify(metrics_data)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def _assess_system_health(metrics_summary, active_alerts):
    """Assess overall system health."""
    health_score = 100
    
    # Reduce score based on active alerts
    if active_alerts:
        health_score -= len(active_alerts) * 10
    
    # Check error rates
    if metrics_summary.get('error_rate', 0) > 0.05:  # 5% error rate threshold
        health_score -= 20
    
    # Check budget usage
    budget_usage = metrics_summary.get('budget_usage_percentage', 0)
    if budget_usage > 90:
        health_score -= 15
    elif budget_usage > 75:
        health_score -= 10
    
    # Determine health status
    if health_score >= 90:
        status = 'excellent'
    elif health_score >= 75:
        status = 'good'
    elif health_score >= 50:
        status = 'warning'
    else:
        status = 'critical'
    
    return {
        'status': status,
        'score': max(0, health_score),
        'alerts_count': len(active_alerts),
        'budget_usage': budget_usage,
        'error_rate': metrics_summary.get('error_rate', 0)
    }


if __name__ == '__main__':
    # Development server
    app.run(host='0.0.0.0', port=5000, debug=True)
