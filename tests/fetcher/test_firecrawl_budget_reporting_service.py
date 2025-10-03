"""
Tests for Firecrawl budget reporting service.

This module tests:
- Budget reporting functionality
- Integration with monitoring
- Dashboard data generation
- Cost analysis
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone

from src.fetcher.firecrawl_budget_reporting_service import FirecrawlBudgetReportingService
from src.fetcher.firecrawl_budget_management_service import FirecrawlBudgetManagementService


class TestFirecrawlBudgetReportingService:
    """Test cases for FirecrawlBudgetReportingService."""
    
    @pytest.fixture
    def mock_budget_service(self):
        """Create mock budget service."""
        service = Mock(spec=FirecrawlBudgetManagementService)
        service.get_budget_report.return_value = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'global_stats': {
                'total_budget_used': 500,
                'last_updated': datetime.now(timezone.utc).isoformat()
            },
            'roaster_budgets': {
                'roaster1': {
                    'used_budget': 200,
                    'budget_limit': 1000,
                    'remaining_budget': 800
                },
                'roaster2': {
                    'used_budget': 300,
                    'budget_limit': 1000,
                    'remaining_budget': 700
                }
            }
        }
        service.get_roaster_budget_status = AsyncMock()
        return service
    
    @pytest.fixture
    def reporting_service(self, mock_budget_service):
        """Create FirecrawlBudgetReportingService instance."""
        return FirecrawlBudgetReportingService(mock_budget_service)
    
    @pytest.mark.asyncio
    async def test_generate_budget_report_global(self, reporting_service):
        """Test global budget report generation."""
        result = await reporting_service.generate_budget_report()
        
        assert result['report_type'] == 'global'
        assert 'timestamp' in result
        assert 'global_data' in result
        assert 'budget_data' in result
        assert 'metrics_summary' in result
        assert 'alerts' in result
    
    @pytest.mark.asyncio
    async def test_generate_budget_report_roaster_specific(self, reporting_service):
        """Test roaster-specific budget report generation."""
        roaster_id = "test_roaster"
        
        # Mock roaster budget status
        reporting_service.budget_service.get_roaster_budget_status.return_value = {
            'roaster_id': roaster_id,
            'budget_limit': 1000,
            'used_budget': 200,
            'remaining_budget': 800,
            'usage_percentage': 20.0,
            'firecrawl_enabled': True,
            'status': 'healthy'
        }
        
        result = await reporting_service.generate_budget_report(roaster_id)
        
        assert result['report_type'] == 'roaster_specific'
        assert result['roaster_id'] == roaster_id
        assert 'roaster_data' in result
        assert 'alerts' in result
    
    @pytest.mark.asyncio
    async def test_generate_budget_report_error(self, reporting_service):
        """Test budget report generation with error."""
        # Mock error in budget service
        reporting_service.budget_service.get_budget_report.side_effect = Exception("Service error")
        
        result = await reporting_service.generate_budget_report()
        
        assert 'error' in result
        assert result['error'] == "Service error"
        assert 'timestamp' in result
    
    @pytest.mark.asyncio
    async def test_generate_roaster_report_success(self, reporting_service):
        """Test successful roaster report generation."""
        roaster_id = "test_roaster"
        
        # Mock roaster budget status
        reporting_service.budget_service.get_roaster_budget_status.return_value = {
            'roaster_id': roaster_id,
            'budget_limit': 1000,
            'used_budget': 200,
            'remaining_budget': 800,
            'usage_percentage': 20.0,
            'firecrawl_enabled': True,
            'status': 'healthy'
        }
        
        result = await reporting_service._generate_roaster_report(roaster_id)
        
        assert result['roaster_id'] == roaster_id
        assert 'budget_status' in result
        assert 'usage_trend' in result
        assert 'status_analysis' in result
        assert 'recommendations' in result
    
    @pytest.mark.asyncio
    async def test_generate_roaster_report_no_data(self, reporting_service):
        """Test roaster report generation with no data."""
        roaster_id = "test_roaster"
        
        # Mock no budget status
        reporting_service.budget_service.get_roaster_budget_status.return_value = None
        
        result = await reporting_service._generate_roaster_report(roaster_id)
        
        assert 'error' in result
        assert f'No budget data found for roaster {roaster_id}' in result['error']
        assert result['roaster_id'] == roaster_id
    
    @pytest.mark.asyncio
    async def test_generate_roaster_report_error(self, reporting_service):
        """Test roaster report generation with error."""
        roaster_id = "test_roaster"
        
        # Mock error in budget service
        reporting_service.budget_service.get_roaster_budget_status.side_effect = Exception("Service error")
        
        result = await reporting_service._generate_roaster_report(roaster_id)
        
        assert 'error' in result
        assert result['error'] == "Service error"
        assert result['roaster_id'] == roaster_id
    
    @pytest.mark.asyncio
    async def test_generate_global_report(self, reporting_service):
        """Test global report generation."""
        result = await reporting_service._generate_global_report()
        
        assert 'global_statistics' in result
        assert 'roaster_summaries' in result
        assert 'budget_distribution' in result
        assert 'cost_analysis' in result
    
    def test_calculate_usage_trend(self, reporting_service):
        """Test usage trend calculation."""
        roaster_id = "test_roaster"
        
        trend = reporting_service._calculate_usage_trend(roaster_id)
        
        assert 'trend' in trend
        assert 'daily_average' in trend
        assert 'weekly_average' in trend
        assert 'projected_exhaustion' in trend
    
    def test_analyze_budget_status_healthy(self, reporting_service):
        """Test budget status analysis for healthy budget."""
        budget_status = {
            'usage_percentage': 50.0,
            'remaining_budget': 500,
            'firecrawl_enabled': True
        }
        
        result = reporting_service._analyze_budget_status(budget_status)
        
        assert result['status'] == 'healthy'
        assert result['priority'] == 'low'
        assert result['usage_percentage'] == 50.0
        assert result['firecrawl_enabled'] is True
    
    def test_analyze_budget_status_warning(self, reporting_service):
        """Test budget status analysis for warning budget."""
        budget_status = {
            'usage_percentage': 85.0,
            'remaining_budget': 150,
            'firecrawl_enabled': True
        }
        
        result = reporting_service._analyze_budget_status(budget_status)
        
        assert result['status'] == 'warning'
        assert result['priority'] == 'medium'
        assert result['usage_percentage'] == 85.0
    
    def test_analyze_budget_status_critical(self, reporting_service):
        """Test budget status analysis for critical budget."""
        budget_status = {
            'usage_percentage': 97.0,
            'remaining_budget': 30,
            'firecrawl_enabled': True
        }
        
        result = reporting_service._analyze_budget_status(budget_status)
        
        assert result['status'] == 'critical'
        assert result['priority'] == 'high'
        assert result['usage_percentage'] == 97.0
    
    def test_analyze_budget_status_exhausted(self, reporting_service):
        """Test budget status analysis for exhausted budget."""
        budget_status = {
            'usage_percentage': 100.0,
            'remaining_budget': 0,
            'firecrawl_enabled': False
        }
        
        result = reporting_service._analyze_budget_status(budget_status)
        
        assert result['status'] == 'exhausted'
        assert result['priority'] == 'critical'
        assert result['usage_percentage'] == 100.0
        assert result['firecrawl_enabled'] is False
    
    def test_generate_recommendations_healthy(self, reporting_service):
        """Test recommendation generation for healthy budget."""
        budget_status = {
            'usage_percentage': 50.0,
            'remaining_budget': 500
        }
        usage_trend = {'trend': 'stable'}
        
        recommendations = reporting_service._generate_recommendations(budget_status, usage_trend)
        
        assert len(recommendations) == 1
        assert 'continue normal operations' in recommendations[0]
    
    def test_generate_recommendations_warning(self, reporting_service):
        """Test recommendation generation for warning budget."""
        budget_status = {
            'usage_percentage': 85.0,
            'remaining_budget': 150
        }
        usage_trend = {'trend': 'increasing'}
        
        recommendations = reporting_service._generate_recommendations(budget_status, usage_trend)
        
        assert len(recommendations) >= 2
        assert any('monitor usage' in rec for rec in recommendations)
        assert any('Consider budget increase if needed' in rec for rec in recommendations)
    
    def test_generate_recommendations_critical(self, reporting_service):
        """Test recommendation generation for critical budget."""
        budget_status = {
            'usage_percentage': 97.0,
            'remaining_budget': 30
        }
        usage_trend = {'trend': 'increasing'}
        
        recommendations = reporting_service._generate_recommendations(budget_status, usage_trend)
        
        assert len(recommendations) >= 2
        assert any('monitor closely' in rec for rec in recommendations)
        assert any('Prepare fallback procedures' in rec for rec in recommendations)
    
    def test_generate_recommendations_exhausted(self, reporting_service):
        """Test recommendation generation for exhausted budget."""
        budget_status = {
            'usage_percentage': 100.0,
            'remaining_budget': 0
        }
        usage_trend = {'trend': 'increasing'}
        
        recommendations = reporting_service._generate_recommendations(budget_status, usage_trend)
        
        assert len(recommendations) >= 3
        assert any('disable firecrawl' in rec.lower() for rec in recommendations)
        assert any('consider increasing budget limit' in rec.lower() for rec in recommendations)
        assert any('optimization' in rec.lower() for rec in recommendations)
    
    def test_calculate_global_stats(self, reporting_service):
        """Test global statistics calculation."""
        budget_data = {
            'roaster_budgets': {
                'roaster1': {
                    'used_budget': 200,
                    'budget_limit': 1000,
                    'remaining_budget': 800
                },
                'roaster2': {
                    'used_budget': 300,
                    'budget_limit': 1000,
                    'remaining_budget': 700
                }
            }
        }
        
        stats = reporting_service._calculate_global_stats(budget_data)
        
        assert stats['total_roasters'] == 2
        assert stats['total_budget_allocated'] == 2000
        assert stats['total_budget_used'] == 500
        assert stats['total_remaining_budget'] == 1500
        assert stats['average_usage_percentage'] == 25.0
    
    def test_calculate_global_stats_empty(self, reporting_service):
        """Test global statistics calculation with empty data."""
        budget_data = {'roaster_budgets': {}}
        
        stats = reporting_service._calculate_global_stats(budget_data)
        
        assert stats['total_roasters'] == 0
        assert stats['total_budget_allocated'] == 0
        assert stats['total_budget_used'] == 0
        assert stats['average_usage_percentage'] == 0
    
    def test_analyze_budget_distribution(self, reporting_service):
        """Test budget distribution analysis."""
        roaster_summaries = []
        
        result = reporting_service._analyze_budget_distribution(roaster_summaries)
        
        assert 'distribution_type' in result
        assert 'variance' in result
        assert 'recommendations' in result
        assert result['distribution_type'] == 'equal'
    
    def test_analyze_costs(self, reporting_service):
        """Test cost analysis."""
        roaster_summaries = []
        
        result = reporting_service._analyze_costs(roaster_summaries)
        
        assert 'cost_per_operation' in result
        assert 'efficiency_score' in result
        assert 'optimization_opportunities' in result
        assert isinstance(result['optimization_opportunities'], list)
    
    @pytest.mark.asyncio
    async def test_generate_operations_dashboard_data(self, reporting_service):
        """Test operations dashboard data generation."""
        result = await reporting_service.generate_operations_dashboard_data()
        
        assert 'timestamp' in result
        assert 'budget_overview' in result
        assert 'metrics_summary' in result
        assert 'active_alerts' in result
        assert 'system_health' in result
    
    @pytest.mark.asyncio
    async def test_generate_operations_dashboard_data_error(self, reporting_service):
        """Test operations dashboard data generation with error."""
        # Mock error in budget service
        reporting_service.generate_budget_report = AsyncMock(side_effect=Exception("Service error"))
        
        result = await reporting_service.generate_operations_dashboard_data()
        
        assert 'error' in result
        assert result['error'] == "Service error"
    
    def test_assess_system_health_healthy(self, reporting_service):
        """Test system health assessment for healthy system."""
        metrics_summary = {}
        active_alerts = []
        
        health = reporting_service._assess_system_health(metrics_summary, active_alerts)
        
        assert health['status'] == 'healthy'
        assert health['critical_alerts'] == 0
        assert health['warning_alerts'] == 0
        assert health['total_alerts'] == 0
    
    def test_assess_system_health_warning(self, reporting_service):
        """Test system health assessment for warning system."""
        metrics_summary = {}
        active_alerts = [
            {'severity': 'warning'},
            {'severity': 'warning'},
            {'severity': 'warning'}
        ]
        
        health = reporting_service._assess_system_health(metrics_summary, active_alerts)
        
        assert health['status'] == 'warning'
        assert health['critical_alerts'] == 0
        assert health['warning_alerts'] == 3
        assert health['total_alerts'] == 3
    
    def test_assess_system_health_critical(self, reporting_service):
        """Test system health assessment for critical system."""
        metrics_summary = {}
        active_alerts = [
            {'severity': 'critical'},
            {'severity': 'warning'}
        ]
        
        health = reporting_service._assess_system_health(metrics_summary, active_alerts)
        
        assert health['status'] == 'critical'
        assert health['critical_alerts'] == 1
        assert health['warning_alerts'] == 1
        assert health['total_alerts'] == 2
    
    def test_generate_health_recommendations_healthy(self, reporting_service):
        """Test health recommendation generation for healthy system."""
        health_status = 'healthy'
        active_alerts = []
        
        recommendations = reporting_service._generate_health_recommendations(health_status, active_alerts)
        
        assert len(recommendations) == 1
        assert 'operating normally' in recommendations[0]
    
    def test_generate_health_recommendations_warning(self, reporting_service):
        """Test health recommendation generation for warning system."""
        health_status = 'warning'
        active_alerts = [{'severity': 'warning'}]
        
        recommendations = reporting_service._generate_health_recommendations(health_status, active_alerts)
        
        assert len(recommendations) >= 2
        assert any('monitor' in rec.lower() for rec in recommendations)
        assert any('warning' in rec.lower() for rec in recommendations)
    
    def test_generate_health_recommendations_critical(self, reporting_service):
        """Test health recommendation generation for critical system."""
        health_status = 'critical'
        active_alerts = [{'severity': 'critical'}]
        
        recommendations = reporting_service._generate_health_recommendations(health_status, active_alerts)
        
        assert len(recommendations) >= 2
        assert any('immediate attention' in rec.lower() for rec in recommendations)
        assert any('critical' in rec.lower() for rec in recommendations)
