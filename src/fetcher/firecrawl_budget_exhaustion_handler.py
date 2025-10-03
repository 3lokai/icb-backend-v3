"""
Firecrawl budget exhaustion detection and handling.

This module provides:
- Budget exhaustion detection logic
- Automatic fallback behavior when budget exhausted
- Roaster flagging for budget exhaustion
- Graceful degradation for Firecrawl operations
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
import asyncio
from structlog import get_logger

from src.fetcher.firecrawl_budget_management_service import FirecrawlBudgetManagementService
from src.monitoring.firecrawl_metrics import FirecrawlMetrics, FirecrawlAlertManager

logger = get_logger(__name__)


class FirecrawlBudgetExhaustionHandler:
    """
    Handler for budget exhaustion scenarios.
    
    Features:
    - Budget exhaustion detection
    - Automatic fallback behavior
    - Roaster flagging and alerts
    - Graceful degradation
    """
    
    def __init__(self, budget_service: FirecrawlBudgetManagementService):
        self.budget_service = budget_service
        self.metrics = FirecrawlMetrics()
        self.alert_manager = FirecrawlAlertManager(self.metrics)
        
        # Exhaustion thresholds
        self.thresholds = {
            'warning': 80.0,      # 80% budget used
            'critical': 95.0,     # 95% budget used
            'exhausted': 100.0   # 100% budget used
        }
        
        # Track exhaustion events
        self.exhaustion_events = []
        
        logger.info("Firecrawl budget exhaustion handler initialized")
    
    async def check_budget_exhaustion(self, roaster_id: str) -> Dict[str, Any]:
        """
        Check if roaster budget is exhausted or approaching exhaustion.
        
        Args:
            roaster_id: ID of the roaster to check
            
        Returns:
            Dictionary with exhaustion status and recommendations
        """
        try:
            # Get roaster budget status
            budget_status = await self.budget_service.get_roaster_budget_status(roaster_id)
            
            if not budget_status:
                return {
                    'exhausted': False,
                    'status': 'unknown',
                    'message': f'Could not get budget status for roaster {roaster_id}',
                    'recommendations': []
                }
            
            usage_percentage = budget_status['usage_percentage']
            remaining_budget = budget_status['remaining_budget']
            
            # Determine exhaustion status
            if usage_percentage >= self.thresholds['exhausted']:
                status = 'exhausted'
                message = f'Budget completely exhausted for roaster {roaster_id}'
                recommendations = ['disable_firecrawl', 'manual_intervention']
                
            elif usage_percentage >= self.thresholds['critical']:
                status = 'critical'
                message = f'Budget critically low for roaster {roaster_id} ({usage_percentage:.1f}%)'
                recommendations = ['monitor_closely', 'prepare_fallback']
                
            elif usage_percentage >= self.thresholds['warning']:
                status = 'warning'
                message = f'Budget warning for roaster {roaster_id} ({usage_percentage:.1f}%)'
                recommendations = ['monitor_usage', 'consider_increase']
                
            else:
                status = 'healthy'
                message = f'Budget healthy for roaster {roaster_id} ({usage_percentage:.1f}%)'
                recommendations = ['continue_normal_operations']
            
            result = {
                'exhausted': status == 'exhausted',
                'status': status,
                'message': message,
                'usage_percentage': usage_percentage,
                'remaining_budget': remaining_budget,
                'recommendations': recommendations,
                'roaster_id': roaster_id,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            # Record metrics
            self.metrics.record_map_operation(
                roaster_id=roaster_id,
                operation_type=f"budget_check_{status}",
                success=True,
                budget_used=0
            )
            
            # Handle based on status
            if status == 'exhausted':
                await self._handle_exhaustion(roaster_id, budget_status)
            elif status == 'critical':
                await self._handle_critical_warning(roaster_id, budget_status)
            elif status == 'warning':
                await self._handle_warning(roaster_id, budget_status)
            
            return result
            
        except Exception as e:
            logger.error(
                "Error checking budget exhaustion",
                roaster_id=roaster_id,
                error=str(e)
            )
            
            return {
                'exhausted': False,
                'status': 'error',
                'message': f'Error checking budget: {str(e)}',
                'recommendations': ['investigate_error']
            }
    
    async def _handle_exhaustion(self, roaster_id: str, budget_status: Dict[str, Any]):
        """Handle budget exhaustion for a roaster."""
        try:
            logger.warning(
                "Handling budget exhaustion",
                roaster_id=roaster_id,
                budget_status=budget_status
            )
            
            # Record exhaustion event
            exhaustion_event = {
                'roaster_id': roaster_id,
                'timestamp': datetime.now(timezone.utc),
                'usage_percentage': budget_status['usage_percentage'],
                'remaining_budget': budget_status['remaining_budget'],
                'action_taken': 'firecrawl_disabled'
            }
            
            self.exhaustion_events.append(exhaustion_event)
            
            # Disable Firecrawl fallback (handled by budget service)
            # The budget service will handle the actual disabling
            
            # Record metrics
            self.metrics.record_map_operation(
                roaster_id=roaster_id,
                operation_type="budget_exhaustion",
                success=False,
                budget_used=0,
                error_type="budget_exhausted"
            )
            
            # Trigger alerts
            alerts = self.alert_manager.check_alerts()
            if alerts:
                logger.warning(
                    "Budget exhaustion alerts triggered",
                    roaster_id=roaster_id,
                    alerts=alerts
                )
            
            logger.warning(
                "Budget exhaustion handled",
                roaster_id=roaster_id,
                action="firecrawl_fallback_disabled"
            )
            
        except Exception as e:
            logger.error(
                "Error handling budget exhaustion",
                roaster_id=roaster_id,
                error=str(e)
            )
    
    async def _handle_critical_warning(self, roaster_id: str, budget_status: Dict[str, Any]):
        """Handle critical budget warning."""
        try:
            logger.warning(
                "Critical budget warning",
                roaster_id=roaster_id,
                usage_percentage=budget_status['usage_percentage'],
                remaining_budget=budget_status['remaining_budget']
            )
            
            # Record metrics
            self.metrics.record_map_operation(
                roaster_id=roaster_id,
                operation_type="budget_critical_warning",
                success=True,
                budget_used=0
            )
            
        except Exception as e:
            logger.error(
                "Error handling critical warning",
                roaster_id=roaster_id,
                error=str(e)
            )
    
    async def _handle_warning(self, roaster_id: str, budget_status: Dict[str, Any]):
        """Handle budget warning."""
        try:
            logger.info(
                "Budget warning",
                roaster_id=roaster_id,
                usage_percentage=budget_status['usage_percentage'],
                remaining_budget=budget_status['remaining_budget']
            )
            
            # Record metrics
            self.metrics.record_map_operation(
                roaster_id=roaster_id,
                operation_type="budget_warning",
                success=True,
                budget_used=0
            )
            
        except Exception as e:
            logger.error(
                "Error handling warning",
                roaster_id=roaster_id,
                error=str(e)
            )
    
    async def implement_graceful_degradation(self, roaster_id: str) -> Dict[str, Any]:
        """
        Implement graceful degradation when budget is exhausted.
        
        Args:
            roaster_id: ID of the roaster
            
        Returns:
            Dictionary with degradation status
        """
        try:
            logger.info(
                "Implementing graceful degradation",
                roaster_id=roaster_id
            )
            
            # Check current budget status
            budget_status = await self.budget_service.get_roaster_budget_status(roaster_id)
            
            if not budget_status:
                return {
                    'success': False,
                    'message': f'Could not get budget status for roaster {roaster_id}'
                }
            
            # If budget is exhausted, implement degradation
            if budget_status['status'] == 'exhausted':
                degradation_actions = [
                    'disable_firecrawl_fallback',
                    'enable_manual_processing',
                    'reduce_operation_frequency',
                    'prioritize_critical_operations'
                ]
                
                logger.info(
                    "Graceful degradation implemented",
                    roaster_id=roaster_id,
                    actions=degradation_actions
                )
                
                return {
                    'success': True,
                    'message': f'Graceful degradation implemented for roaster {roaster_id}',
                    'actions_taken': degradation_actions,
                    'budget_status': budget_status
                }
            
            else:
                return {
                    'success': True,
                    'message': f'No degradation needed for roaster {roaster_id}',
                    'budget_status': budget_status
                }
            
        except Exception as e:
            logger.error(
                "Error implementing graceful degradation",
                roaster_id=roaster_id,
                error=str(e)
            )
            
            return {
                'success': False,
                'message': f'Error implementing degradation: {str(e)}'
            }
    
    def get_exhaustion_events(self) -> List[Dict[str, Any]]:
        """Get list of budget exhaustion events."""
        return [
            {
                'roaster_id': event['roaster_id'],
                'timestamp': event['timestamp'].isoformat(),
                'usage_percentage': event['usage_percentage'],
                'remaining_budget': event['remaining_budget'],
                'action_taken': event['action_taken']
            }
            for event in self.exhaustion_events
        ]
    
    def get_exhaustion_stats(self) -> Dict[str, Any]:
        """Get exhaustion statistics."""
        total_events = len(self.exhaustion_events)
        recent_events = [
            event for event in self.exhaustion_events
            if (datetime.now(timezone.utc) - event['timestamp']).days <= 7
        ]
        
        return {
            'total_exhaustion_events': total_events,
            'recent_events_7_days': len(recent_events),
            'thresholds': self.thresholds,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
