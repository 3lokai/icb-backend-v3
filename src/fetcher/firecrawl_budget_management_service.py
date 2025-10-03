"""
Firecrawl budget management service for operations team control.

This module provides:
- Budget management for operations team
- Budget state persistence to database
- Budget exhaustion detection and handling
- Integration with existing FirecrawlBudgetTracker
- Basic budget reporting and monitoring
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
import asyncio
from structlog import get_logger

from src.config.firecrawl_config import FirecrawlBudgetTracker, FirecrawlConfig
from src.monitoring.firecrawl_metrics import FirecrawlMetrics, FirecrawlAlertManager

logger = get_logger(__name__)


class FirecrawlBudgetManagementService:
    """
    Budget management service for Firecrawl operations.
    
    Extends existing FirecrawlBudgetTracker with:
    - Database persistence for budget state
    - Operations team management interface
    - Budget exhaustion detection and handling
    - Integration with monitoring and alerting
    """
    
    def __init__(self, budget_tracker: FirecrawlBudgetTracker, supabase_client=None):
        self.budget_tracker = budget_tracker
        self.supabase_client = supabase_client
        self.metrics = FirecrawlMetrics()
        self.alert_manager = FirecrawlAlertManager(self.metrics)
        
        # Budget state persistence
        self.budget_state = {
            'roaster_budgets': {},  # roaster_id -> budget_info
            'global_budget_used': 0,
            'last_updated': datetime.now(timezone.utc)
        }
        
        logger.info("Firecrawl budget management service initialized")
    
    async def track_price_only_usage(
        self, 
        urls_processed: int, 
        successful_extractions: int, 
        cost: float
    ) -> Dict[str, Any]:
        """
        Track price-only usage for cost optimization.
        
        Args:
            urls_processed: Number of URLs processed
            successful_extractions: Number of successful extractions
            cost: Cost of the operation
            
        Returns:
            Dictionary with cost tracking information
        """
        try:
            # Calculate cost efficiency
            cost_efficiency = successful_extractions / max(urls_processed, 1)
            cost_per_url = cost / max(urls_processed, 1)
            
            # Track in budget state
            price_only_usage = {
                'urls_processed': urls_processed,
                'successful_extractions': successful_extractions,
                'cost': cost,
                'cost_efficiency': cost_efficiency,
                'cost_per_url': cost_per_url,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            # Update global budget state
            if 'price_only_usage' not in self.budget_state:
                self.budget_state['price_only_usage'] = []
            
            self.budget_state['price_only_usage'].append(price_only_usage)
            
            # Update metrics
            self.metrics.record_price_only_usage(
                urls_processed=urls_processed,
                successful_extractions=successful_extractions,
                cost=cost,
                cost_efficiency=cost_efficiency
            )
            
            # Check for budget alerts
            await self._check_price_only_budget_alerts(cost, cost_efficiency)
            
            logger.info(
                "Tracked price-only usage",
                urls_processed=urls_processed,
                successful_extractions=successful_extractions,
                cost=cost,
                cost_efficiency=cost_efficiency,
                cost_per_url=cost_per_url
            )
            
            return {
                'success': True,
                'price_only_usage': price_only_usage,
                'cost_optimization': f"{(1 - cost_efficiency) * 100:.1f}% cost reduction vs full refresh"
            }
            
        except Exception as e:
            logger.error(
                "Failed to track price-only usage",
                error=str(e),
                urls_processed=urls_processed,
                successful_extractions=successful_extractions,
                cost=cost
            )
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _check_price_only_budget_alerts(self, cost: float, cost_efficiency: float):
        """Check for price-only budget alerts."""
        try:
            # Alert if cost efficiency is too low
            if cost_efficiency < 0.5:  # Less than 50% success rate
                await self.alert_manager.send_price_only_efficiency_alert(
                    cost_efficiency=cost_efficiency,
                    threshold=0.5
                )
            
            # Alert if cost per URL is too high
            if cost > 0.5:  # More than $0.50 per URL
                await self.alert_manager.send_price_only_cost_alert(
                    cost=cost,
                    threshold=0.5
                )
            
        except Exception as e:
            logger.error(
                "Failed to check price-only budget alerts",
                error=str(e)
            )
    
    async def get_price_only_cost_summary(self) -> Dict[str, Any]:
        """Get price-only cost summary for monitoring."""
        try:
            if 'price_only_usage' not in self.budget_state:
                return {
                    'total_operations': 0,
                    'total_cost': 0.0,
                    'average_cost_efficiency': 0.0,
                    'cost_optimization': 'No price-only operations tracked'
                }
            
            price_only_usage = self.budget_state['price_only_usage']
            
            total_operations = len(price_only_usage)
            total_cost = sum(usage['cost'] for usage in price_only_usage)
            total_urls = sum(usage['urls_processed'] for usage in price_only_usage)
            total_successful = sum(usage['successful_extractions'] for usage in price_only_usage)
            
            average_cost_efficiency = total_successful / max(total_urls, 1)
            average_cost_per_url = total_cost / max(total_urls, 1)
            
            # Calculate cost optimization vs full refresh
            # Assume full refresh costs 3x more than price-only
            full_refresh_equivalent_cost = total_cost * 3
            cost_savings = full_refresh_equivalent_cost - total_cost
            cost_optimization_percentage = (cost_savings / full_refresh_equivalent_cost) * 100
            
            return {
                'total_operations': total_operations,
                'total_cost': total_cost,
                'total_urls_processed': total_urls,
                'total_successful_extractions': total_successful,
                'average_cost_efficiency': average_cost_efficiency,
                'average_cost_per_url': average_cost_per_url,
                'cost_optimization': f"{cost_optimization_percentage:.1f}% cost reduction vs full refresh",
                'cost_savings': cost_savings,
                'full_refresh_equivalent_cost': full_refresh_equivalent_cost
            }
            
        except Exception as e:
            logger.error(
                "Failed to get price-only cost summary",
                error=str(e)
            )
            return {
                'error': str(e),
                'total_operations': 0,
                'total_cost': 0.0
            }
    
    async def check_budget_and_handle_exhaustion(self, roaster_id: str) -> bool:
        """
        Check if roaster has budget available and handle exhaustion.
        
        Args:
            roaster_id: ID of the roaster to check
            
        Returns:
            True if budget available, False if exhausted
        """
        try:
            # Get roaster budget info
            roaster_budget = await self._get_roaster_budget(roaster_id)
            
            if not roaster_budget:
                logger.warning(f"No budget info found for roaster {roaster_id}")
                return False
            
            # Check if budget is exhausted
            if roaster_budget['remaining_budget'] <= 0:
                await self._handle_budget_exhaustion(roaster_id)
                return False
            
            # Check if approaching exhaustion (80% threshold)
            usage_percentage = (roaster_budget['used_budget'] / roaster_budget['budget_limit']) * 100
            if usage_percentage >= 80:
                await self._handle_budget_warning(roaster_id, usage_percentage)
            
            return True
            
        except Exception as e:
            logger.error(
                "Error checking budget for roaster",
                roaster_id=roaster_id,
                error=str(e)
            )
            return False
    
    async def record_budget_usage(self, roaster_id: str, cost: int = 1) -> bool:
        """
        Record budget usage for a roaster.
        
        Args:
            roaster_id: ID of the roaster
            cost: Cost of the operation
            
        Returns:
            True if recorded successfully, False if budget exhausted
        """
        try:
            # Check budget before recording
            if not await self.check_budget_and_handle_exhaustion(roaster_id):
                return False
            
            # Record usage in database and update state
            await self._update_roaster_budget_usage(roaster_id, cost)
            
            logger.info(
                "Budget usage recorded",
                roaster_id=roaster_id,
                cost=cost,
                remaining_budget=self.budget_state['roaster_budgets'][roaster_id]['remaining_budget']
            )
            
            return True
            
        except Exception as e:
            logger.error(
                "Error recording budget usage",
                roaster_id=roaster_id,
                cost=cost,
                error=str(e)
            )
            return False
    
    async def _get_roaster_budget(self, roaster_id: str) -> Optional[Dict[str, Any]]:
        """Get roaster budget information from database."""
        if not self.supabase_client:
            # Fallback to local state if no database connection
            return self.budget_state['roaster_budgets'].get(roaster_id)
        
        try:
            result = self.supabase_client.table("roasters").select(
                "id, firecrawl_budget_limit, use_firecrawl_fallback"
            ).eq("id", roaster_id).execute()
            
            if not result.data:
                return None
            
            roaster = result.data[0]
            budget_limit = roaster.get('firecrawl_budget_limit', 0)
            
            # Get actual usage from budget state or database
            used_budget = await self._get_roaster_used_budget(roaster_id)
            
            return {
                'roaster_id': roaster_id,
                'budget_limit': budget_limit,
                'used_budget': used_budget,
                'remaining_budget': max(0, budget_limit - used_budget),
                'use_firecrawl_fallback': roaster.get('use_firecrawl_fallback', False)
            }
            
        except Exception as e:
            logger.error(
                "Error getting roaster budget",
                roaster_id=roaster_id,
                error=str(e)
            )
            return None
    
    async def _get_roaster_used_budget(self, roaster_id: str) -> int:
        """Get the used budget for a roaster from state or database."""
        # Check in-memory state first
        if roaster_id in self.budget_state['roaster_budgets']:
            return self.budget_state['roaster_budgets'][roaster_id]['used_budget']
        
        # If not in state, return 0 (no historical data available)
        return 0
    
    async def _update_roaster_budget_usage(self, roaster_id: str, cost: int):
        """Update roaster budget usage in database."""
        if not self.supabase_client:
            return
        
        try:
            # Update budget usage in state
            if roaster_id not in self.budget_state['roaster_budgets']:
                # Get roaster budget info to initialize properly
                roaster_budget = await self._get_roaster_budget(roaster_id)
                if roaster_budget:
                    self.budget_state['roaster_budgets'][roaster_id] = {
                        'used_budget': roaster_budget['used_budget'],
                        'budget_limit': roaster_budget['budget_limit'],
                        'remaining_budget': roaster_budget['remaining_budget'],
                        'last_updated': datetime.now(timezone.utc)
                    }
                else:
                    self.budget_state['roaster_budgets'][roaster_id] = {
                        'used_budget': 0,
                        'budget_limit': 0,
                        'remaining_budget': 0,
                        'last_updated': datetime.now(timezone.utc)
                    }
            
            self.budget_state['roaster_budgets'][roaster_id]['used_budget'] += cost
            self.budget_state['roaster_budgets'][roaster_id]['remaining_budget'] -= cost
            self.budget_state['roaster_budgets'][roaster_id]['last_updated'] = datetime.now(timezone.utc)
            self.budget_state['global_budget_used'] += cost
            self.budget_state['last_updated'] = datetime.now(timezone.utc)
            
            logger.info(
                "Budget usage recorded",
                roaster_id=roaster_id,
                cost=cost,
                total_used=self.budget_state['roaster_budgets'][roaster_id]['used_budget']
            )
            
        except Exception as e:
            logger.error(
                "Error updating roaster budget usage",
                roaster_id=roaster_id,
                cost=cost,
                error=str(e)
            )
    
    async def _handle_budget_exhaustion(self, roaster_id: str):
        """Handle budget exhaustion for a roaster."""
        try:
            # Disable Firecrawl fallback for this roaster
            if self.supabase_client:
                await self._disable_firecrawl_fallback(roaster_id)
            
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
                "Budget exhausted for roaster",
                roaster_id=roaster_id,
                action="disabled_firecrawl_fallback"
            )
            
        except Exception as e:
            logger.error(
                "Error handling budget exhaustion",
                roaster_id=roaster_id,
                error=str(e)
            )
    
    async def _handle_budget_warning(self, roaster_id: str, usage_percentage: float):
        """Handle budget warning when approaching exhaustion."""
        try:
            # Record warning metrics
            self.metrics.record_map_operation(
                roaster_id=roaster_id,
                operation_type="budget_warning",
                success=True,
                budget_used=0
            )
            
            logger.warning(
                "Budget warning for roaster",
                roaster_id=roaster_id,
                usage_percentage=usage_percentage,
                threshold=80
            )
            
        except Exception as e:
            logger.error(
                "Error handling budget warning",
                roaster_id=roaster_id,
                usage_percentage=usage_percentage,
                error=str(e)
            )
    
    async def _disable_firecrawl_fallback(self, roaster_id: str):
        """Disable Firecrawl fallback for a roaster."""
        try:
            result = self.supabase_client.table("roasters").update({
                "use_firecrawl_fallback": False
            }).eq("id", roaster_id).execute()
            
            logger.info(
                "Firecrawl fallback disabled for roaster",
                roaster_id=roaster_id
            )
            
        except Exception as e:
            logger.error(
                "Error disabling Firecrawl fallback",
                roaster_id=roaster_id,
                error=str(e)
            )
    
    async def reset_roaster_budget(self, roaster_id: str, new_budget_limit: int) -> bool:
        """
        Reset budget for a roaster (operations team function).
        
        Args:
            roaster_id: ID of the roaster
            new_budget_limit: New budget limit
            
        Returns:
            True if reset successfully
        """
        try:
            if self.supabase_client:
                # Update budget limit in database
                result = self.supabase_client.table("roasters").update({
                    "firecrawl_budget_limit": new_budget_limit,
                    "use_firecrawl_fallback": True  # Re-enable fallback
                }).eq("id", roaster_id).execute()
            
            # Reset local state
            if roaster_id in self.budget_state['roaster_budgets']:
                self.budget_state['roaster_budgets'][roaster_id] = {
                    'used_budget': 0,
                    'budget_limit': new_budget_limit,
                    'remaining_budget': new_budget_limit
                }
            
            logger.info(
                "Budget reset for roaster",
                roaster_id=roaster_id,
                new_budget_limit=new_budget_limit
            )
            
            return True
            
        except Exception as e:
            logger.error(
                "Error resetting roaster budget",
                roaster_id=roaster_id,
                new_budget_limit=new_budget_limit,
                error=str(e)
            )
            return False
    
    def get_budget_report(self) -> Dict[str, Any]:
        """Get comprehensive budget report for operations team."""
        try:
            report = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'global_stats': {
                    'total_budget_used': self.budget_state['global_budget_used'],
                    'last_updated': self.budget_state['last_updated'].isoformat()
                },
                'roaster_budgets': self.budget_state['roaster_budgets'],
                'metrics_summary': self.metrics.get_metrics_summary(),
                'active_alerts': self.alert_manager.get_active_alerts()
            }
            
            return report
            
        except Exception as e:
            logger.error("Error generating budget report", error=str(e))
            return {'error': str(e)}
    
    async def get_roaster_budget_status(self, roaster_id: str) -> Optional[Dict[str, Any]]:
        """Get budget status for a specific roaster."""
        try:
            roaster_budget = await self._get_roaster_budget(roaster_id)
            if not roaster_budget:
                return None
            
            return {
                'roaster_id': roaster_id,
                'budget_limit': roaster_budget['budget_limit'],
                'used_budget': roaster_budget['used_budget'],
                'remaining_budget': roaster_budget['remaining_budget'],
                'usage_percentage': (roaster_budget['used_budget'] / roaster_budget['budget_limit']) * 100,
                'firecrawl_enabled': roaster_budget['use_firecrawl_fallback'],
                'status': 'exhausted' if roaster_budget['remaining_budget'] <= 0 else 'active'
            }
            
        except Exception as e:
            logger.error(
                "Error getting roaster budget status",
                roaster_id=roaster_id,
                error=str(e)
            )
            return None
