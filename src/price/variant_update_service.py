"""
Variant update service for managing variant record modifications.
Extends existing database integration patterns for variant updates.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from decimal import Decimal

from structlog import get_logger

from ..validator.rpc_client import RPCClient
from ..validator.database_integration import DatabaseIntegration

logger = get_logger(__name__)


class VariantUpdateService:
    """
    Service for variant record updates extending existing DatabaseIntegration patterns.
    
    Features:
    - Variant pricing field updates
    - Batch variant operations
    - Integration with existing RPCClient
    - Comprehensive error handling and logging
    """
    
    def __init__(self, supabase_client=None, rpc_client: Optional[RPCClient] = None):
        """
        Initialize variant update service.
        
        Args:
            supabase_client: Supabase client for database operations
            rpc_client: RPC client for variant operations (optional)
        """
        self.supabase_client = supabase_client
        self.rpc_client = rpc_client or RPCClient(supabase_client=supabase_client)
        self.database_integration = DatabaseIntegration(supabase_client=supabase_client)
        
        # Service statistics
        self.variant_stats = {
            'total_updates': 0,
            'successful_updates': 0,
            'failed_updates': 0,
            'start_time': None,
            'end_time': None
        }
        
        logger.info("Initialized variant update service")
    
    async def update_variant_pricing(
        self,
        variant_id: str,
        new_price: Decimal,
        currency: str,
        in_stock: bool,
        scraped_at: datetime
    ) -> bool:
        """
        Update variant price fields atomically.
        
        Args:
            variant_id: Variant ID to update
            new_price: New price value
            currency: Currency code
            in_stock: Stock availability status
            scraped_at: Scraping timestamp
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(
                "Updating variant pricing",
                variant_id=variant_id,
                new_price=float(new_price),
                currency=currency,
                in_stock=in_stock
            )
            
            # Update variant pricing fields
            success = self.rpc_client.update_variant_pricing(
                variant_id=variant_id,
                price_current=float(new_price),
                price_last_checked_at=scraped_at.isoformat(),
                in_stock=in_stock,
                currency=currency
            )
            
            if success:
                self.variant_stats['successful_updates'] += 1
                logger.info(
                    "Successfully updated variant pricing",
                    variant_id=variant_id
                )
            else:
                self.variant_stats['failed_updates'] += 1
                logger.error(
                    "Failed to update variant pricing",
                    variant_id=variant_id
                )
            
            self.variant_stats['total_updates'] += 1
            return success
            
        except Exception as e:
            self.variant_stats['failed_updates'] += 1
            self.variant_stats['total_updates'] += 1
            
            logger.error(
                "Error updating variant pricing",
                variant_id=variant_id,
                error=str(e)
            )
            return False
    
    async def batch_update_variant_pricing(
        self,
        variant_updates: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Batch update variant pricing for multiple variants.
        
        Args:
            variant_updates: List of variant update dictionaries
            
        Returns:
            Dictionary with batch update results
        """
        start_time = datetime.now(timezone.utc)
        self.variant_stats['start_time'] = start_time
        
        logger.info(
            "Starting batch variant pricing update",
            update_count=len(variant_updates)
        )
        
        try:
            # Use RPC client batch update
            batch_result = self.rpc_client.batch_update_variant_pricing(variant_updates)
            
            # Update statistics
            self.variant_stats['total_updates'] += len(variant_updates)
            self.variant_stats['successful_updates'] += batch_result.get('successful_updates', 0)
            self.variant_stats['failed_updates'] += batch_result.get('failed_updates', 0)
            self.variant_stats['end_time'] = datetime.now(timezone.utc)
            
            processing_time = (self.variant_stats['end_time'] - start_time).total_seconds()
            
            logger.info(
                "Completed batch variant pricing update",
                total_updates=len(variant_updates),
                successful_updates=batch_result.get('successful_updates', 0),
                failed_updates=batch_result.get('failed_updates', 0),
                processing_time_seconds=processing_time
            )
            
            # Add processing time to result
            batch_result['processing_time_seconds'] = processing_time
            
            return batch_result
            
        except Exception as e:
            self.variant_stats['failed_updates'] += len(variant_updates)
            self.variant_stats['total_updates'] += len(variant_updates)
            self.variant_stats['end_time'] = datetime.now(timezone.utc)
            
            error_msg = f"Batch variant update failed: {str(e)}"
            logger.error(
                "Batch variant update failed",
                error=error_msg,
                update_count=len(variant_updates)
            )
            
            return {
                'total_updates': len(variant_updates),
                'successful_updates': 0,
                'failed_updates': len(variant_updates),
                'errors': [error_msg],
                'processing_time_seconds': (datetime.now(timezone.utc) - start_time).total_seconds()
            }
    
    async def update_variant_availability(
        self,
        variant_id: str,
        in_stock: bool,
        stock_qty: Optional[int] = None
    ) -> bool:
        """
        Update variant availability status.
        
        Args:
            variant_id: Variant ID to update
            in_stock: Stock availability status
            stock_qty: Stock quantity (optional)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            update_data = {
                'variant_id': variant_id,
                'in_stock': in_stock
            }
            
            if stock_qty is not None:
                update_data['stock_qty'] = stock_qty
            
            logger.info(
                "Updating variant availability",
                variant_id=variant_id,
                in_stock=in_stock,
                stock_qty=stock_qty
            )
            
            # Use RPC client for update
            success = self.rpc_client.update_variant_pricing(**update_data)
            
            if success:
                self.variant_stats['successful_updates'] += 1
                logger.info(
                    "Successfully updated variant availability",
                    variant_id=variant_id
                )
            else:
                self.variant_stats['failed_updates'] += 1
                logger.error(
                    "Failed to update variant availability",
                    variant_id=variant_id
                )
            
            self.variant_stats['total_updates'] += 1
            return success
            
        except Exception as e:
            self.variant_stats['failed_updates'] += 1
            self.variant_stats['total_updates'] += 1
            
            logger.error(
                "Error updating variant availability",
                variant_id=variant_id,
                error=str(e)
            )
            return False
    
    def get_variant_stats(self) -> Dict[str, Any]:
        """
        Get variant update service statistics.
        
        Returns:
            Dictionary with variant statistics
        """
        stats = self.variant_stats.copy()
        
        # Calculate success rate
        if stats['total_updates'] > 0:
            stats['success_rate'] = stats['successful_updates'] / stats['total_updates']
            stats['failure_rate'] = stats['failed_updates'] / stats['total_updates']
        else:
            stats['success_rate'] = 0.0
            stats['failure_rate'] = 0.0
        
        # Add processing time
        if stats['start_time'] and stats['end_time']:
            stats['total_processing_time'] = (
                stats['end_time'] - stats['start_time']
            ).total_seconds()
        else:
            stats['total_processing_time'] = 0.0
        
        return stats
    
    def reset_stats(self):
        """Reset variant update service statistics."""
        self.variant_stats = {
            'total_updates': 0,
            'successful_updates': 0,
            'failed_updates': 0,
            'start_time': None,
            'end_time': None
        }
        
        logger.info("Reset variant update service statistics")
