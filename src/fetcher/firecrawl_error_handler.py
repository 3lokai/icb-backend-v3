"""
Firecrawl error handler for fallback policies.

This module provides:
- Error handling for Firecrawl operations
- Retry logic with exponential backoff
- Fallback behavior for API failures and budget exhaustion
- Integration with monitoring and alerting
"""

from typing import Dict, Any, Optional, Callable, List
from datetime import datetime, timezone
import asyncio
import random
from structlog import get_logger

from src.config.firecrawl_config import FirecrawlConfig
from src.fetcher.firecrawl_budget_management_service import FirecrawlBudgetManagementService

logger = get_logger(__name__)


class FirecrawlErrorHandler:
    """
    Error handler for Firecrawl operations with fallback policies.
    
    Features:
    - Retry logic with exponential backoff
    - Budget exhaustion handling
    - API failure fallback
    - Integration with monitoring
    """
    
    def __init__(self, budget_service: FirecrawlBudgetManagementService):
        self.budget_service = budget_service
        self.retry_config = {
            'max_retries': 3,
            'base_delay': 1.0,  # seconds
            'max_delay': 60.0,  # seconds
            'jitter': True
        }
        
        logger.info("Firecrawl error handler initialized")
    
    async def execute_with_fallback(
        self,
        roaster_id: str,
        operation_name: str,
        operation_func: Callable,
        fallback_func: Optional[Callable] = None,
        *args,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute operation with error handling and fallback.
        
        Args:
            roaster_id: ID of the roaster
            operation_name: Name of the operation for logging
            operation_func: Primary operation function
            fallback_func: Fallback operation function
            *args, **kwargs: Arguments for the operation
            
        Returns:
            Result dictionary with success status and data
        """
        try:
            # Check budget before operation
            if not await self.budget_service.check_budget_and_handle_exhaustion(roaster_id):
                return {
                    'success': False,
                    'error': 'budget_exhausted',
                    'message': f'Budget exhausted for roaster {roaster_id}',
                    'fallback_used': False
                }
            
            # Execute operation with retry logic
            result = await self._execute_with_retry(
                roaster_id, operation_name, operation_func, *args, **kwargs
            )
            
            if result['success']:
                # Record successful budget usage
                await self.budget_service.record_budget_usage(roaster_id, cost=1)
                return {
                    'success': True,
                    'data': result['data'],
                    'fallback_used': False,
                    'attempts': result.get('attempts', 1)
                }
            
            # If primary operation failed, try fallback
            if fallback_func:
                logger.info(
                    f"Primary operation failed, trying fallback",
                    roaster_id=roaster_id,
                    operation_name=operation_name
                )
                
                fallback_result = await self._execute_fallback(
                    roaster_id, operation_name, fallback_func, *args, **kwargs
                )
                
                if fallback_result['success']:
                    return {
                        'success': True,
                        'data': fallback_result['data'],
                        'fallback_used': True,
                        'message': f'Fallback successful for {operation_name}'
                    }
            
            return {
                'success': False,
                'error': 'operation_failed',
                'message': f'Both primary and fallback operations failed for {operation_name}',
                'fallback_used': fallback_func is not None
            }
            
        except Exception as e:
            logger.error(
                f"Unexpected error in operation {operation_name}",
                roaster_id=roaster_id,
                error=str(e)
            )
            
            return {
                'success': False,
                'error': 'unexpected_error',
                'message': f'Unexpected error: {str(e)}',
                'fallback_used': False
            }
    
    async def _execute_with_retry(
        self,
        roaster_id: str,
        operation_name: str,
        operation_func: Callable,
        *args,
        **kwargs
    ) -> Dict[str, Any]:
        """Execute operation with retry logic."""
        last_error = None
        
        for attempt in range(self.retry_config['max_retries'] + 1):
            try:
                logger.debug(
                    f"Executing {operation_name} (attempt {attempt + 1})",
                    roaster_id=roaster_id,
                    attempt=attempt + 1,
                    max_retries=self.retry_config['max_retries']
                )
                
                result = await operation_func(*args, **kwargs)
                
                if attempt > 0:
                    logger.info(
                        f"{operation_name} succeeded on retry",
                        roaster_id=roaster_id,
                        attempt=attempt + 1
                    )
                
                return {
                    'success': True,
                    'data': result,
                    'attempts': attempt + 1
                }
                
            except Exception as e:
                last_error = e
                
                logger.warning(
                    f"{operation_name} failed (attempt {attempt + 1})",
                    roaster_id=roaster_id,
                    attempt=attempt + 1,
                    error=str(e)
                )
                
                # Don't retry on budget exhaustion
                if 'budget' in str(e).lower() or 'exhausted' in str(e).lower():
                    logger.warning(
                        f"Budget-related error, not retrying {operation_name}",
                        roaster_id=roaster_id,
                        error=str(e)
                    )
                    return {
                        'success': False,
                        'error': 'budget_exhausted',
                        'attempts': attempt + 1
                    }
                
                # Don't retry on last attempt
                if attempt < self.retry_config['max_retries']:
                    delay = self._calculate_retry_delay(attempt)
                    logger.info(
                        f"Retrying {operation_name} in {delay:.2f}s",
                        roaster_id=roaster_id,
                        delay=delay
                    )
                    await asyncio.sleep(delay)
        
        return {
            'success': False,
            'error': str(last_error) if last_error else 'unknown_error',
            'attempts': self.retry_config['max_retries'] + 1
        }
    
    async def _execute_fallback(
        self,
        roaster_id: str,
        operation_name: str,
        fallback_func: Callable,
        *args,
        **kwargs
    ) -> Dict[str, Any]:
        """Execute fallback operation."""
        try:
            logger.info(
                f"Executing fallback for {operation_name}",
                roaster_id=roaster_id
            )
            
            result = await fallback_func(*args, **kwargs)
            
            logger.info(
                f"Fallback successful for {operation_name}",
                roaster_id=roaster_id
            )
            
            return {
                'success': True,
                'data': result
            }
            
        except Exception as e:
            logger.error(
                f"Fallback failed for {operation_name}",
                roaster_id=roaster_id,
                error=str(e)
            )
            
            return {
                'success': False,
                'error': str(e)
            }
    
    def _calculate_retry_delay(self, attempt: int) -> float:
        """Calculate retry delay with exponential backoff and jitter."""
        base_delay = self.retry_config['base_delay'] * (2 ** attempt)
        delay = min(base_delay, self.retry_config['max_delay'])
        
        if self.retry_config['jitter']:
            # Add jitter to prevent thundering herd (max 10% of delay)
            jitter = random.uniform(0, delay * 0.1)
            delay += jitter
            # Ensure final delay doesn't exceed max_delay
            delay = min(delay, self.retry_config['max_delay'])
        
        return delay
    
    async def handle_budget_exhaustion(self, roaster_id: str) -> Dict[str, Any]:
        """
        Handle budget exhaustion scenario.
        
        Args:
            roaster_id: ID of the roaster with exhausted budget
            
        Returns:
            Result dictionary with handling status
        """
        try:
            logger.warning(
                "Handling budget exhaustion",
                roaster_id=roaster_id
            )
            
            # Get current budget status
            budget_status = await self.budget_service.get_roaster_budget_status(roaster_id)
            
            if not budget_status:
                return {
                    'success': False,
                    'error': 'budget_status_unavailable',
                    'message': f'Could not get budget status for roaster {roaster_id}'
                }
            
            # Check if budget is actually exhausted
            if budget_status['remaining_budget'] > 0:
                return {
                    'success': True,
                    'message': f'Budget not actually exhausted for roaster {roaster_id}',
                    'budget_status': budget_status
                }
            
            # Disable Firecrawl fallback (handled by budget service)
            logger.info(
                "Budget exhausted, Firecrawl fallback will be disabled",
                roaster_id=roaster_id,
                budget_status=budget_status
            )
            
            return {
                'success': True,
                'message': f'Budget exhaustion handled for roaster {roaster_id}',
                'budget_status': budget_status,
                'action_taken': 'firecrawl_fallback_disabled'
            }
            
        except Exception as e:
            logger.error(
                "Error handling budget exhaustion",
                roaster_id=roaster_id,
                error=str(e)
            )
            
            return {
                'success': False,
                'error': str(e),
                'message': f'Error handling budget exhaustion for roaster {roaster_id}'
            }
    
    def get_error_stats(self) -> Dict[str, Any]:
        """Get error handling statistics."""
        return {
            'retry_config': self.retry_config,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
