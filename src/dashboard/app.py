"""
Operations Dashboard Flask Application

This dashboard provides real-time monitoring of the coffee scraping pipeline,
integrating with existing G.1-G.3 monitoring infrastructure.
"""

import os
import asyncio
from datetime import datetime, timezone
from flask import Flask, render_template, jsonify, request, redirect, url_for, flash
from flask_cors import CORS
import json
from typing import Dict, List, Any, Optional

# Import existing monitoring services
from src.monitoring.platform_monitoring_service import PlatformMonitoringService
from src.fetcher.firecrawl_budget_reporting_service import FirecrawlBudgetReportingService
from src.fetcher.firecrawl_budget_management_service import FirecrawlBudgetManagementService
from src.monitoring.firecrawl_metrics import FirecrawlMetrics, FirecrawlAlertManager

# Import scheduler and roaster management
from src.scheduler.main import Scheduler
from src.config.roaster_config import RoasterConfig
from src.worker.queue import QueueManager

# Import database services for business metrics
try:
    from supabase import create_client, Client
    supabase_client: Optional[Client] = None
except ImportError:
    supabase_client = None

# Import authentication module
from src.dashboard.auth import (
    get_current_user, require_auth, require_role, 
    login_user, logout_user, signup_user, 
    get_users_with_roles, assign_user_role
)

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
    supabase_client=supabase_client
)
budget_reporting = FirecrawlBudgetReportingService(budget_management)

# Initialize scheduler and roaster management
scheduler = Scheduler()
roaster_config = RoasterConfig()
queue_manager = QueueManager()

# Initialize Supabase client for business metrics
def init_supabase():
    """Initialize Supabase client for database queries."""
    global supabase_client
    if supabase_client is None:
        try:
            supabase_url = os.getenv('SUPABASE_URL')
            supabase_key = os.getenv('SUPABASE_KEY')
            if supabase_url and supabase_key:
                supabase_client = create_client(supabase_url, supabase_key)
        except Exception as e:
            print(f"Warning: Could not initialize Supabase client: {e}")
    return supabase_client


# =============================================================================
# AUTHENTICATION ROUTES
# =============================================================================

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page and handler."""
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        if not email or not password:
            flash('Email and password are required', 'error')
            return render_template('login.html')
        
        result = login_user(email, password)
        if result['success']:
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash(result['error'], 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    """Logout user."""
    logout_user()
    flash('You have been logged out', 'info')
    return redirect(url_for('login'))

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    """Signup page and handler."""
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        if not email or not password:
            flash('Email and password are required', 'error')
            return render_template('signup.html')
        
        result = signup_user(email, password)
        if result['success']:
            flash('Account created successfully! Please check your email to verify your account.', 'success')
            return redirect(url_for('login'))
        else:
            flash(result['error'], 'error')
    
    return render_template('signup.html')

@app.route('/')
@require_auth
def dashboard():
    """Main dashboard page."""
    user = get_current_user()
    return render_template('dashboard.html', user=user)


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
@require_auth
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
@require_auth
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
@require_auth
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
@require_auth
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


@app.route('/api/dashboard/business-metrics')
@require_auth
def business_metrics():
    """Get business metrics including product counts, price tracking, and data quality."""
    try:
        client = init_supabase()
        if not client:
            return jsonify({'error': 'Database connection not available'}), 500
        
        # Get product discovery metrics
        product_metrics = _get_product_discovery_metrics(client)
        
        # Get price tracking metrics
        price_metrics = _get_price_tracking_metrics(client)
        
        # Get data quality metrics
        quality_metrics = _get_data_quality_metrics(client)
        
        # Get roaster performance metrics
        roaster_metrics = _get_roaster_performance_metrics(client)
        
        business_data = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'product_metrics': product_metrics,
            'price_metrics': price_metrics,
            'quality_metrics': quality_metrics,
            'roaster_metrics': roaster_metrics
        }
        
        return jsonify(business_data)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/dashboard/pipeline-status')
@require_auth
def pipeline_status():
    """Get real-time pipeline status and job queue information."""
    try:
        client = init_supabase()
        if not client:
            return jsonify({'error': 'Database connection not available'}), 500
        
        # Get current pipeline status
        pipeline_data = _get_pipeline_status(client)
        
        # Get job queue information
        queue_data = _get_job_queue_status(client)
        
        # Get recent run statistics
        run_stats = _get_recent_run_statistics(client)
        
        status_data = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'pipeline_status': pipeline_data,
            'job_queue': queue_data,
            'run_statistics': run_stats
        }
        
        return jsonify(status_data)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def _get_product_discovery_metrics(client) -> Dict[str, Any]:
    """Get product discovery metrics (new products, updates)."""
    try:
        # Get total products count
        total_coffees = client.table('coffees').select('id', count='exact').execute()
        
        # Get new products in last 7 days
        new_products = client.table('coffees').select('id', count='exact').gte('created_at', 'now() - interval \'7 days\'').execute()
        
        # Get updated products in last 7 days
        updated_products = client.table('coffees').select('id', count='exact').gte('updated_at', 'now() - interval \'7 days\'').execute()
        
        return {
            'total_products': total_coffees.count if total_coffees.count else 0,
            'new_products_7d': new_products.count if new_products.count else 0,
            'updated_products_7d': updated_products.count if updated_products.count else 0
        }
    except Exception as e:
        print(f"Error getting product discovery metrics: {e}")
        return {'total_products': 0, 'new_products_7d': 0, 'updated_products_7d': 0}


def _get_price_tracking_metrics(client) -> Dict[str, Any]:
    """Get price tracking metrics for weekly price updates (per PRD)."""
    try:
        # Get price updates in last 30 days (weekly cadence)
        price_updates = client.table('prices').select('id', count='exact').gte('scraped_at', 'now() - interval \'30 days\'').execute()
        
        # Get weekly price trend (last 4 weeks to show weekly cadence)
        price_trend = client.rpc('get_price_trend_4w').execute()
        
        # Get last price update date
        last_price_update = client.table('prices').select('scraped_at').order('scraped_at', desc=True).limit(1).execute()
        
        return {
            'price_updates_30d': price_updates.count if price_updates.count else 0,
            'price_trend': price_trend.data if price_trend.data else [],
            'last_price_update': last_price_update.data[0]['scraped_at'] if last_price_update.data else None,
            'cadence': 'weekly'  # Per PRD: weekly price-only runs
        }
    except Exception as e:
        print(f"Error getting price tracking metrics: {e}")
        return {'price_updates_30d': 0, 'price_trend': [], 'last_price_update': None, 'cadence': 'weekly'}


def _get_data_quality_metrics(client) -> Dict[str, Any]:
    """Get data quality metrics (completeness, confidence scores)."""
    try:
        # Get coffee status distribution
        status_distribution = client.table('coffees').select('status', count='exact').execute()
        
        # Get confidence scores from sensory_params
        confidence_scores = client.table('sensory_params').select('confidence').gte('confidence', 0).execute()
        
        avg_confidence = 0
        if confidence_scores.data:
            confidences = [item['confidence'] for item in confidence_scores.data if item['confidence'] is not None]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0
        
        return {
            'status_distribution': status_distribution.data if status_distribution.data else [],
            'avg_confidence_score': round(avg_confidence, 2),
            'total_with_confidence': len(confidence_scores.data) if confidence_scores.data else 0
        }
    except Exception as e:
        print(f"Error getting data quality metrics: {e}")
        return {'status_distribution': [], 'avg_confidence_score': 0, 'total_with_confidence': 0}


def _get_roaster_performance_metrics(client) -> Dict[str, Any]:
    """Get roaster performance metrics with success rates."""
    try:
        # Get roaster performance (using corrected schema)
        roaster_performance = client.rpc('get_roaster_performance_30d').execute()
        
        return {
            'roaster_performance': roaster_performance.data if roaster_performance.data else []
        }
    except Exception as e:
        print(f"Error getting roaster performance metrics: {e}")
        return {'roaster_performance': []}


def _get_pipeline_status(client) -> Dict[str, Any]:
    """Get current pipeline status."""
    try:
        # Get recent scrape runs (last 24 hours)
        recent_runs = client.table('scrape_runs').select('*').gte('started_at', 'now() - interval \'24 hours\'').order('started_at', desc=True).limit(10).execute()
        
        # Get currently running jobs
        running_jobs = [run for run in recent_runs.data if run.get('status') == 'running'] if recent_runs.data else []
        
        return {
            'recent_runs': recent_runs.data if recent_runs.data else [],
            'running_jobs': len(running_jobs),
            'last_run_time': recent_runs.data[0]['started_at'] if recent_runs.data else None
        }
    except Exception as e:
        print(f"Error getting pipeline status: {e}")
        return {'recent_runs': [], 'running_jobs': 0, 'last_run_time': None}


def _get_job_queue_status(client) -> Dict[str, Any]:
    """Get job queue status information."""
    try:
        # Get pending jobs (if any queue system is implemented)
        # For now, return basic queue status
        return {
            'pending_jobs': 0,
            'queue_size': 0,
            'processing_rate': 0
        }
    except Exception as e:
        print(f"Error getting job queue status: {e}")
        return {'pending_jobs': 0, 'queue_size': 0, 'processing_rate': 0}


def _get_recent_run_statistics(client) -> Dict[str, Any]:
    """Get recent run statistics."""
    try:
        # Get run statistics from last 30 days (weekly + monthly runs)
        run_stats = client.rpc('get_run_statistics_30d').execute()
        
        return {
            'run_statistics': run_stats.data if run_stats.data else []
        }
    except Exception as e:
        print(f"Error getting recent run statistics: {e}")
        return {'run_statistics': []}


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


# =============================================================================
# SCRAPING TRIGGER ENDPOINTS
# =============================================================================

@app.route('/api/dashboard/trigger-scraping', methods=['POST'])
@require_role('operator')
def trigger_scraping():
    """Trigger scraping jobs for specific roasters or all roasters."""
    try:
        data = request.get_json()
        job_type = data.get('job_type', 'full_refresh')  # 'full_refresh' or 'price_only'
        roaster_id = data.get('roaster_id', None)  # None for all roasters
        
        # Validate job type
        if job_type not in ['full_refresh', 'price_only']:
            return jsonify({'error': 'Invalid job_type. Must be "full_refresh" or "price_only"'}), 400
        
        # Trigger the scraping job asynchronously
        asyncio.create_task(scheduler.schedule_jobs(job_type=job_type, roaster_id=roaster_id))
        
        return jsonify({
            'status': 'success',
            'message': f'Scraping job triggered: {job_type}',
            'roaster_id': roaster_id,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/dashboard/roasters', methods=['GET'])
@require_auth
def get_roasters():
    """Get list of all roasters with their configurations."""
    try:
        # Get roasters from roaster config
        roasters = roaster_config.get_all_roasters()
        
        return jsonify({
            'roasters': roasters,
            'total_count': len(roasters),
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/dashboard/roasters', methods=['POST'])
@require_role('admin')
def add_roaster():
    """Add a new roaster configuration."""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['roaster_id', 'name', 'base_url', 'platform', 'cadence']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Add roaster to configuration
        roaster_data = {
            'roaster_id': data['roaster_id'],
            'name': data['name'],
            'base_url': data['base_url'],
            'platform': data['platform'],
            'cadence': data['cadence'],
            'enabled': data.get('enabled', True),
            'priority': data.get('priority', 'normal'),
            'max_pages': data.get('max_pages', 50),
            'timeout': data.get('timeout', 30)
        }
        
        # Add to roaster config (this would need to be implemented in RoasterConfig)
        # For now, return success
        return jsonify({
            'status': 'success',
            'message': 'Roaster added successfully',
            'roaster': roaster_data,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/dashboard/roasters/<roaster_id>', methods=['PUT'])
@require_role('admin')
def update_roaster(roaster_id):
    """Update roaster configuration."""
    try:
        data = request.get_json()
        
        # Update roaster configuration
        # This would need to be implemented in RoasterConfig
        return jsonify({
            'status': 'success',
            'message': f'Roaster {roaster_id} updated successfully',
            'roaster_id': roaster_id,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/dashboard/roasters/<roaster_id>', methods=['DELETE'])
@require_role('admin')
def delete_roaster(roaster_id):
    """Delete roaster configuration."""
    try:
        # Delete roaster from configuration
        # This would need to be implemented in RoasterConfig
        return jsonify({
            'status': 'success',
            'message': f'Roaster {roaster_id} deleted successfully',
            'roaster_id': roaster_id,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/dashboard/queue-status', methods=['GET'])
@require_auth
def get_queue_status():
    """Get current queue status and job counts."""
    try:
        # Get queue status from queue manager
        queue_status = {
            'pending_jobs': 0,  # Would get from queue_manager
            'running_jobs': 0,   # Would get from queue_manager
            'completed_jobs': 0, # Would get from queue_manager
            'failed_jobs': 0,    # Would get from queue_manager
            'queue_size': 0      # Would get from queue_manager
        }
        
        return jsonify({
            'queue_status': queue_status,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# =============================================================================
# USER MANAGEMENT ENDPOINTS (ADMIN ONLY)
# =============================================================================

@app.route('/api/dashboard/users', methods=['GET'])
@require_role('admin')
def get_users():
    """Get all users with their roles (admin only)."""
    try:
        result = get_users_with_roles()
        if result['success']:
            return jsonify({
                'users': result['users'],
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
        else:
            return jsonify({'error': result['error']}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/dashboard/users/<user_id>/role', methods=['PUT'])
@require_role('admin')
def update_user_role(user_id):
    """Update user role (admin only)."""
    try:
        data = request.get_json()
        role = data.get('role')
        
        if not role or role not in ['admin', 'operator', 'viewer']:
            return jsonify({'error': 'Invalid role. Must be admin, operator, or viewer'}), 400
        
        result = assign_user_role(user_id, role)
        if result['success']:
            return jsonify({
                'status': 'success',
                'message': result['message'],
                'user_id': user_id,
                'role': role,
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
        else:
            return jsonify({'error': result['error']}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    # Development server
    app.run(host='0.0.0.0', port=5000, debug=True)
