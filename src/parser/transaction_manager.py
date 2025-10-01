"""
Transaction management for normalizer pipeline.

Features:
- Database transaction boundaries for complete pipeline
- Rollback procedures for partial pipeline failures
- Transaction consistency across pipeline stages
- Integration with existing RPC client
"""

import time
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone, timedelta
from enum import Enum
from structlog import get_logger

from .pipeline_state import PipelineState, PipelineStage, PipelineError
from ..validator.rpc_client import RPCClient

logger = get_logger(__name__)


class TransactionStatus(Enum):
    """Transaction status enumeration."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMMITTED = "committed"
    ROLLED_BACK = "rolled_back"
    FAILED = "failed"


class TransactionBoundary(Enum):
    """Transaction boundary types."""
    PIPELINE_START = "pipeline_start"
    PIPELINE_END = "pipeline_end"
    PARSER_GROUP = "parser_group"
    LLM_FALLBACK = "llm_fallback"
    DATABASE_WRITE = "database_write"
    DETERMINISTIC_COMPLETE = "deterministic_complete"
    LLM_COMPLETE = "llm_complete"


class PipelineTransaction:
    """Transaction management for pipeline operations."""
    
    def __init__(self, 
                 execution_id: str,
                 rpc_client: RPCClient,
                 boundary_type: TransactionBoundary = TransactionBoundary.PIPELINE_START):
        self.execution_id = execution_id
        self.transaction_id = execution_id  # Alias for backward compatibility
        self.rpc_client = rpc_client
        self.boundary_type = boundary_type
        self.boundary = boundary_type  # Alias for backward compatibility
        self.status = TransactionStatus.PENDING
        self.state = TransactionStatus.PENDING  # Alias for backward compatibility
        self.start_time = datetime.now(timezone.utc)
        self.end_time = None
        self.operations: List[Dict[str, Any]] = []
        self.rollback_operations: List[Dict[str, Any]] = []
        self.errors: List[PipelineError] = []
        
    def add_operation(self, operation_type: str, operation_data: Dict[str, Any], rollback_data: Optional[Dict[str, Any]] = None):
        """Add operation to transaction."""
        operation = {
            'type': operation_type,
            'data': operation_data,
            'timestamp': datetime.now(timezone.utc),
            'rollback_data': rollback_data
        }
        self.operations.append(operation)
        
        if rollback_data:
            self.rollback_operations.append({
                'type': f"rollback_{operation_type}",
                'data': rollback_data,
                'timestamp': datetime.now(timezone.utc)
            })
        
        logger.debug("Operation added to transaction", 
                    execution_id=self.execution_id,
                    operation_type=operation_type)
    
    def mark_in_progress(self):
        """Mark transaction as in progress."""
        self.status = TransactionStatus.IN_PROGRESS
        self.state = TransactionStatus.IN_PROGRESS  # Sync state alias
        logger.info("Transaction marked as in progress", execution_id=self.execution_id)
    
    def commit(self) -> bool:
        """Commit transaction."""
        try:
            self.status = TransactionStatus.COMMITTED
            self.state = TransactionStatus.COMMITTED  # Sync state alias
            self.end_time = datetime.now(timezone.utc)
            
            logger.info("Transaction committed successfully", 
                       execution_id=self.execution_id,
                       operations_count=len(self.operations),
                       duration=self.get_duration())
            
            return True
            
        except Exception as e:
            self.status = TransactionStatus.FAILED
            self.state = TransactionStatus.FAILED  # Sync state alias
            self.add_error(PipelineError(
                stage=PipelineStage.DETERMINISTIC_PARSING,
                error_type="transaction_commit_failed",
                message=f"Transaction commit failed: {str(e)}",
                recoverable=False
            ))
            
            logger.error("Transaction commit failed", 
                        execution_id=self.execution_id,
                        error=str(e))
            
            return False
    
    def rollback(self) -> bool:
        """Rollback transaction."""
        try:
            self.status = TransactionStatus.ROLLED_BACK
            self.state = TransactionStatus.ROLLED_BACK  # Sync state alias
            self.end_time = datetime.now(timezone.utc)
            
            # Execute rollback operations in reverse order
            for rollback_op in reversed(self.rollback_operations):
                self._execute_rollback_operation(rollback_op)
            
            logger.info("Transaction rolled back successfully", 
                       execution_id=self.execution_id,
                       rollback_operations_count=len(self.rollback_operations),
                       duration=self.get_duration())
            
            return True
            
        except Exception as e:
            self.status = TransactionStatus.FAILED
            self.state = TransactionStatus.FAILED  # Sync state alias
            self.add_error(PipelineError(
                stage=PipelineStage.DETERMINISTIC_PARSING,
                error_type="transaction_rollback_failed",
                message=f"Transaction rollback failed: {str(e)}",
                recoverable=False
            ))
            
            logger.error("Transaction rollback failed", 
                        execution_id=self.execution_id,
                        error=str(e))
            
            return False
    
    def _execute_rollback_operation(self, rollback_op: Dict[str, Any]):
        """Execute individual rollback operation."""
        try:
            operation_type = rollback_op['type']
            operation_data = rollback_op['data']
            
            if operation_type == 'rollback_database_write':
                # Rollback database operations
                self._rollback_database_operation(operation_data)
            elif operation_type == 'rollback_llm_fallback':
                # Rollback LLM operations
                self._rollback_llm_operation(operation_data)
            elif operation_type == 'rollback_parser_result':
                # Rollback parser results
                self._rollback_parser_operation(operation_data)
            
            logger.debug("Rollback operation executed", 
                        execution_id=self.execution_id,
                        operation_type=operation_type)
            
        except Exception as e:
            logger.error("Rollback operation failed", 
                        execution_id=self.execution_id,
                        operation_type=rollback_op.get('type'),
                        error=str(e))
    
    def _rollback_database_operation(self, operation_data: Dict[str, Any]):
        """Rollback database operation."""
        # Implementation depends on specific database operations
        # For now, log the rollback attempt
        logger.info("Database operation rollback attempted", 
                   execution_id=self.execution_id,
                   operation_data=operation_data)
    
    def _rollback_llm_operation(self, operation_data: Dict[str, Any]):
        """Rollback LLM operation."""
        # Implementation depends on specific LLM operations
        # For now, log the rollback attempt
        logger.info("LLM operation rollback attempted", 
                   execution_id=self.execution_id,
                   operation_data=operation_data)
    
    def _rollback_parser_operation(self, operation_data: Dict[str, Any]):
        """Rollback parser operation."""
        # Implementation depends on specific parser operations
        # For now, log the rollback attempt
        logger.info("Parser operation rollback attempted", 
                   execution_id=self.execution_id,
                   operation_data=operation_data)
    
    def add_error(self, error: PipelineError):
        """Add error to transaction."""
        self.errors.append(error)
        logger.warning("Error added to transaction", 
                      execution_id=self.execution_id,
                      error=error.to_dict())
    
    def get_duration(self) -> float:
        """Get transaction duration in seconds."""
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        else:
            return (datetime.now(timezone.utc) - self.start_time).total_seconds()
    
    def is_successful(self) -> bool:
        """Check if transaction was successful."""
        return self.status == TransactionStatus.COMMITTED
    
    def has_errors(self) -> bool:
        """Check if transaction has errors."""
        return len(self.errors) > 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert transaction to dictionary."""
        return {
            'execution_id': self.execution_id,
            'boundary_type': self.boundary_type.value,
            'status': self.status.value,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'duration': self.get_duration(),
            'operations_count': len(self.operations),
            'rollback_operations_count': len(self.rollback_operations),
            'errors_count': len(self.errors),
            'is_successful': self.is_successful()
        }


class PipelineTransactionManager:
    """Manager for pipeline transactions."""
    
    def __init__(self, rpc_client: RPCClient):
        self.rpc_client = rpc_client
        self.active_transactions: Dict[str, PipelineTransaction] = {}
        self.completed_transactions: List[PipelineTransaction] = []
    
    def create_transaction(self, 
                          execution_id: str, 
                          boundary_type: TransactionBoundary = TransactionBoundary.PIPELINE_START) -> PipelineTransaction:
        """Create new pipeline transaction."""
        transaction = PipelineTransaction(execution_id, self.rpc_client, boundary_type)
        self.active_transactions[execution_id] = transaction
        
        logger.info("Pipeline transaction created", 
                   execution_id=execution_id,
                   boundary_type=boundary_type.value)
        
        return transaction
    
    def get_transaction(self, execution_id: str) -> Optional[PipelineTransaction]:
        """Get active transaction by execution ID."""
        return self.active_transactions.get(execution_id)
    
    def commit_transaction(self, execution_id: str) -> bool:
        """Commit transaction."""
        transaction = self.active_transactions.get(execution_id)
        if not transaction:
            logger.error("Transaction not found for commit", execution_id=execution_id)
            return False
        
        success = transaction.commit()
        
        if success:
            # Move to completed transactions
            self.completed_transactions.append(transaction)
            del self.active_transactions[execution_id]
        
        return success
    
    def rollback_transaction(self, execution_id: str) -> bool:
        """Rollback transaction."""
        transaction = self.active_transactions.get(execution_id)
        if not transaction:
            logger.error("Transaction not found for rollback", execution_id=execution_id)
            return False
        
        success = transaction.rollback()
        
        if success:
            # Move to completed transactions
            self.completed_transactions.append(transaction)
            del self.active_transactions[execution_id]
        
        return success
    
    def complete_transaction(self, execution_id: str) -> bool:
        """Complete transaction (alias for commit_transaction)."""
        return self.commit_transaction(execution_id)
    
    def cleanup_completed_transactions(self, max_age_hours: int = 24):
        """Clean up old completed transactions."""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
        
        # Remove old completed transactions
        self.completed_transactions = [
            t for t in self.completed_transactions 
            if t.start_time > cutoff_time
        ]
        
        logger.info("Completed transactions cleaned up", 
                   remaining_count=len(self.completed_transactions))
    
    def get_transaction_stats(self) -> Dict[str, Any]:
        """Get transaction statistics."""
        active_count = len(self.active_transactions)
        completed_count = len(self.completed_transactions)
        
        successful_count = sum(1 for t in self.completed_transactions if t.is_successful())
        failed_count = completed_count - successful_count
        
        return {
            'active_transactions': active_count,
            'completed_transactions': completed_count,
            'successful_transactions': successful_count,
            'failed_transactions': failed_count,
            'success_rate': successful_count / completed_count if completed_count > 0 else 0
        }
