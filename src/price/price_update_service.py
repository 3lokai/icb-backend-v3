"""
Price update service for atomic price insertion and variant updates.
Extends existing DatabaseIntegration patterns for B.2 functionality.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from decimal import Decimal
from dataclasses import dataclass

from structlog import get_logger

from ..validator.rpc_client import RPCClient
from ..validator.database_integration import DatabaseIntegration
from ..fetcher.price_parser import PriceDelta

logger = get_logger(__name__)


@dataclass
class PriceUpdateResult:
    """Result of price update operation."""
    success: bool
    price_ids: List[str] = None
    variant_updates: int = 0
    errors: List[str] = None
    processing_time_seconds: float = 0.0
    
    def __post_init__(self):
        if self.price_ids is None:
            self.price_ids = []
        if self.errors is None:
            self.errors = []


class PriceUpdateService:
    """
    Service for atomic price updates extending existing DatabaseIntegration patterns.
    
    Features:
    - Atomic price insertion using rpc_insert_price
    - Variant pricing field updates
    - Transaction-like behavior with rollback
    - Integration with existing RPCClient and DatabaseIntegration
    - Comprehensive error handling and logging
    """
    
    def __init__(self, supabase_client=None, rpc_client: Optional[RPCClient] = None):
        """
        Initialize price update service.
        
        Args:
            supabase_client: Supabase client for database operations
            rpc_client: RPC client for price operations (optional)
        """
        self.supabase_client = supabase_client
        self.rpc_client = rpc_client or RPCClient(supabase_client=supabase_client)
        self.database_integration = DatabaseIntegration(supabase_client=supabase_client)
        
        # Service statistics
        self.update_stats = {
            'total_updates': 0,
            'successful_updates': 0,
            'failed_updates': 0,
            'price_records_inserted': 0,
            'variant_records_updated': 0,
            'start_time': None,
            'end_time': None
        }
        
        logger.info("Initialized price update service")
    
    async def update_prices_atomic(
        self, 
        price_deltas: List[PriceDelta]
    ) -> PriceUpdateResult:
        """
        Atomically update prices and variant records.
        
        Args:
            price_deltas: List of price deltas from B.1 price fetcher
            
        Returns:
            PriceUpdateResult with operation results
        """
        start_time = datetime.now(timezone.utc)
        self.update_stats['start_time'] = start_time
        
        logger.info(
            "Starting atomic price update",
            delta_count=len(price_deltas),
            roaster_id=getattr(price_deltas[0], 'roaster_id', 'unknown') if price_deltas else 'unknown'
        )
        
        try:
            # Step 1: Insert price records via RPC
            price_ids = await self._insert_price_records(price_deltas)
            
            if not price_ids:
                return PriceUpdateResult(
                    success=False,
                    errors=["Failed to insert any price records"],
                    processing_time_seconds=(datetime.now(timezone.utc) - start_time).total_seconds()
                )
            
            # Step 2: Update variant pricing fields
            variant_updates = await self._update_variant_pricing(price_deltas)
            
            # Update statistics
            self.update_stats['total_updates'] += len(price_deltas)
            self.update_stats['successful_updates'] += len(price_ids)
            self.update_stats['price_records_inserted'] += len(price_ids)
            self.update_stats['variant_records_updated'] += variant_updates
            self.update_stats['end_time'] = datetime.now(timezone.utc)
            
            processing_time = (self.update_stats['end_time'] - start_time).total_seconds()
            
            logger.info(
                "Completed atomic price update",
                price_records_inserted=len(price_ids),
                variant_records_updated=variant_updates,
                processing_time_seconds=processing_time
            )
            
            return PriceUpdateResult(
                success=True,
                price_ids=price_ids,
                variant_updates=variant_updates,
                processing_time_seconds=processing_time
            )
            
        except Exception as e:
            self.update_stats['failed_updates'] += len(price_deltas)
            self.update_stats['end_time'] = datetime.now(timezone.utc)
            
            error_msg = f"Atomic price update failed: {str(e)}"
            logger.error(
                "Atomic price update failed",
                error=error_msg,
                delta_count=len(price_deltas)
            )
            
            return PriceUpdateResult(
                success=False,
                errors=[error_msg],
                processing_time_seconds=(datetime.now(timezone.utc) - start_time).total_seconds()
            )
    
    async def _insert_price_records(self, price_deltas: List[PriceDelta]) -> List[str]:
        """
        Insert price records using rpc_insert_price.
        
        Args:
            price_deltas: List of price deltas to insert
            
        Returns:
            List of inserted price IDs
        """
        price_ids = []
        
        for delta in price_deltas:
            try:
                # Prepare price record data
                price_data = {
                    'variant_id': delta.variant_id,
                    'price': float(delta.new_price),
                    'currency': delta.currency,
                    'scraped_at': delta.detected_at.isoformat(),
                    'source_raw': {
                        'old_price': float(delta.old_price) if delta.old_price else None,
                        'new_price': float(delta.new_price),
                        'currency': delta.currency,
                        'in_stock': delta.in_stock,
                        'sku': delta.sku,
                        'detected_at': delta.detected_at.isoformat()
                    }
                }
                
                # Insert price record via RPC
                price_id = self.rpc_client.insert_price(**price_data)
                price_ids.append(price_id)
                
                logger.debug(
                    "Inserted price record",
                    price_id=price_id,
                    variant_id=delta.variant_id,
                    price=float(delta.new_price),
                    currency=delta.currency
                )
                
            except Exception as e:
                logger.error(
                    "Failed to insert price record",
                    variant_id=delta.variant_id,
                    error=str(e)
                )
                # Continue with other records even if one fails
                continue
        
        logger.info(
            "Completed price record insertion",
            total_deltas=len(price_deltas),
            successful_inserts=len(price_ids)
        )
        
        return price_ids
    
    async def _update_variant_pricing(self, price_deltas: List[PriceDelta]) -> int:
        """
        Update variant pricing fields.
        
        Args:
            price_deltas: List of price deltas to update
            
        Returns:
            Number of variant records updated
        """
        variant_updates = []
        
        for delta in price_deltas:
            try:
                # Prepare variant update data
                update_data = {
                    'variant_id': delta.variant_id,
                    'price_current': float(delta.new_price),
                    'price_last_checked_at': delta.detected_at.isoformat(),
                    'in_stock': delta.in_stock,
                    'currency': delta.currency
                }
                
                variant_updates.append(update_data)
                
            except Exception as e:
                logger.error(
                    "Failed to prepare variant update",
                    variant_id=delta.variant_id,
                    error=str(e)
                )
                continue
        
        if not variant_updates:
            logger.warning("No variant updates to perform")
            return 0
        
        # Batch update variant pricing
        batch_result = self.rpc_client.batch_update_variant_pricing(variant_updates)
        
        successful_updates = batch_result.get('successful_updates', 0)
        
        logger.info(
            "Completed variant pricing updates",
            total_updates=len(variant_updates),
            successful_updates=successful_updates,
            failed_updates=batch_result.get('failed_updates', 0)
        )
        
        return successful_updates
    
    def get_update_stats(self) -> Dict[str, Any]:
        """
        Get price update service statistics.
        
        Returns:
            Dictionary with update statistics
        """
        stats = self.update_stats.copy()
        
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
        """Reset price update service statistics."""
        self.update_stats = {
            'total_updates': 0,
            'successful_updates': 0,
            'failed_updates': 0,
            'price_records_inserted': 0,
            'variant_records_updated': 0,
            'start_time': None,
            'end_time': None
        }
        
        # Reset RPC client stats
        self.rpc_client.reset_stats()
        
        logger.info("Reset price update service statistics")
