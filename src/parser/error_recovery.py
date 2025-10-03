"""
Error recovery service for normalizer pipeline.

Features:
- Handle partial failures gracefully
- Implement retry logic with exponential backoff
- Provide graceful degradation strategies
- Support checkpointing for error recovery
"""

import time
import asyncio
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from dataclasses import dataclass
from structlog import get_logger

from .pipeline_state import PipelineState, PipelineStage, PipelineError, ParserResult
from ..config.pipeline_config import ErrorRecoveryConfig

logger = get_logger(__name__)


class RecoveryAction(Enum):
    """Recovery actions for pipeline errors."""
    RETRY = "retry"
    SKIP = "skip"
    FALLBACK = "fallback"
    FAIL = "fail"


@dataclass
class RecoveryDecision:
    """Decision for error recovery."""
    
    action: RecoveryAction
    should_retry: bool
    retry_delay: float
    max_retries: int
    reason: str
    fallback_strategy: Optional[str] = None
    
    @property
    def retry_delay_seconds(self) -> float:
        """Alias for retry_delay for backward compatibility."""
        return self.retry_delay
    
    @property
    def message(self) -> str:
        """Alias for reason for backward compatibility."""
        return self.reason


class PipelineErrorRecovery:
    """Service for handling pipeline error recovery."""
    
    def __init__(self, config: ErrorRecoveryConfig):
        self.config = config
        self.retry_counts: Dict[str, int] = {}
        self.error_history: List[PipelineError] = []
    
    def is_recoverable(self, error: Exception) -> bool:
        """Check if error is recoverable."""
        # Check for general recoverable error patterns
        recoverable_errors = [
            "timeout",
            "connection",
            "rate limit",
            "rate_limit",
            "temporary",
            "network",
            "service unavailable",
            "service temporarily unavailable",
            "service_unavailable"
        ]
        
        error_message = str(error).lower()
        if any(recoverable_error in error_message for recoverable_error in recoverable_errors):
            return True
        
        # Check for specific error types that are always recoverable
        recoverable_types = [ValueError, TypeError, ConnectionError, TimeoutError]
        return any(isinstance(error, error_type) for error_type in recoverable_types)
    
    def recover_from_parser_failure(self, parser_name: str, error: Exception) -> RecoveryDecision:
        """Determine recovery action for parser failure."""
        retry_count = self.retry_counts.get(parser_name, 0)
        
        # Check if we've exceeded max retries
        if retry_count >= self.config.max_retries:
            return RecoveryDecision(
                action=RecoveryAction.SKIP,
                should_retry=False,
                retry_delay=0.0,
                max_retries=self.config.max_retries,
                reason=f"Max retries exceeded for {parser_name}"
            )
        
        # Check if error is recoverable
        if not self.is_recoverable(error):
            # For non-recoverable errors, check if we should skip or fail
            if self.config.graceful_degradation:
                return RecoveryDecision(
                    action=RecoveryAction.SKIP,
                    should_retry=False,
                    retry_delay=0.0,
                    max_retries=self.config.max_retries,
                    reason=f"Non-recoverable error in {parser_name}: {str(error)}"
                )
            else:
                return RecoveryDecision(
                    action=RecoveryAction.FAIL,
                    should_retry=False,
                    retry_delay=0.0,
                    max_retries=self.config.max_retries,
                    reason=f"Non-recoverable error in {parser_name}: {str(error)}"
                )
        
        # Calculate retry delay with exponential backoff
        retry_delay = self._calculate_retry_delay(retry_count)
        
        # Increment retry count
        self.retry_counts[parser_name] = retry_count + 1
        
        return RecoveryDecision(
            action=RecoveryAction.RETRY,
            should_retry=True,
            retry_delay=retry_delay,
            max_retries=self.config.max_retries,
            reason=f"Retrying {parser_name} after {retry_delay}s (attempt {retry_count + 1})"
        )
    
    def recover_from_llm_failure(self, field_name: str, error: Exception) -> RecoveryDecision:
        """Determine recovery action for LLM failure."""
        retry_count = self.retry_counts.get(f"llm_{field_name}", 0)
        
        # Check if we've exceeded max retries
        if retry_count >= self.config.max_retries:
            return RecoveryDecision(
                action=RecoveryAction.SKIP,
                should_retry=False,
                retry_delay=0.0,
                max_retries=self.config.max_retries,
                reason=f"Max retries exceeded for LLM field {field_name}"
            )
        
        # Check if error is recoverable
        if not self.is_recoverable(error):
            return RecoveryDecision(
                action=RecoveryAction.FAIL,
                should_retry=False,
                retry_delay=0.0,
                max_retries=self.config.max_retries,
                reason=f"Non-recoverable LLM error for {field_name}: {str(error)}"
            )
        
        # Calculate retry delay with exponential backoff
        retry_delay = self._calculate_retry_delay(retry_count)
        
        # Increment retry count
        self.retry_counts[f"llm_{field_name}"] = retry_count + 1
        
        return RecoveryDecision(
            action=RecoveryAction.RETRY,
            should_retry=True,
            retry_delay=retry_delay,
            max_retries=self.config.max_retries,
            reason=f"Retrying LLM field {field_name} after {retry_delay}s (attempt {retry_count + 1})"
        )
    
    def recover_from_pipeline_failure(self, state: PipelineState, error: Exception) -> RecoveryDecision:
        """Determine recovery action for overall pipeline failure."""
        # Check if we have partial results
        if state.deterministic_results:
            return RecoveryDecision(
                action=RecoveryAction.FALLBACK,
                should_retry=False,
                retry_delay=0.0,
                max_retries=0,
                reason="Pipeline failed but partial results available",
                fallback_strategy="use_partial_results"
            )
        
        # Check if error is recoverable
        if not self.is_recoverable(error):
            return RecoveryDecision(
                action=RecoveryAction.FAIL,
                should_retry=False,
                retry_delay=0.0,
                max_retries=0,
                reason=f"Non-recoverable pipeline error: {str(error)}"
            )
        
        # Try to recover with graceful degradation
        return RecoveryDecision(
            action=RecoveryAction.FALLBACK,
            should_retry=False,
            retry_delay=0.0,
            max_retries=0,
            reason="Pipeline failed, attempting graceful degradation",
            fallback_strategy="graceful_degradation"
        )
    
    def _calculate_retry_delay(self, retry_count: int) -> float:
        """Calculate retry delay with exponential backoff."""
        if not self.config.exponential_backoff:
            return self.config.retry_delay_seconds
        
        delay = self.config.retry_delay_seconds * (2 ** retry_count)
        return min(delay, self.config.max_delay_seconds)
    
    def reset_retry_counts(self):
        """Reset retry counts for all parsers."""
        self.retry_counts.clear()
        logger.info("Retry counts reset")
    
    def get_retry_count(self, parser_name: str) -> int:
        """Get retry count for specific parser."""
        return self.retry_counts.get(parser_name, 0)
    
    def record_error(self, error: PipelineError):
        """Record error for analysis."""
        self.error_history.append(error)
        logger.warning("Error recorded", error=error.to_dict())
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Get summary of recorded errors."""
        if not self.error_history:
            return {"total_errors": 0, "error_types": {}, "recoverable_errors": 0}
        
        error_types = {}
        recoverable_count = 0
        
        for error in self.error_history:
            error_type = error.error_type
            error_types[error_type] = error_types.get(error_type, 0) + 1
            
            if error.recoverable:
                recoverable_count += 1
        
        return {
            "total_errors": len(self.error_history),
            "error_types": error_types,
            "recoverable_errors": recoverable_count,
            "recovery_rate": recoverable_count / len(self.error_history) if self.error_history else 0
        }
    
    def should_continue_processing(self, state: PipelineState) -> bool:
        """Determine if processing should continue despite errors."""
        if not self.config.graceful_degradation:
            return not state.has_errors()
        
        # Continue if we have some successful results
        successful_parsers = sum(1 for result in state.deterministic_results.values() if result.success)
        total_parsers = len(state.deterministic_results)
        
        # Continue if at least 50% of parsers succeeded
        return successful_parsers >= (total_parsers * 0.5) if total_parsers > 0 else False
    
    def get_fallback_strategy(self, state: PipelineState) -> Optional[str]:
        """Get fallback strategy for partial failures."""
        if not state.has_errors():
            return None
        
        # Check if we have enough successful results to continue
        successful_parsers = sum(1 for result in state.deterministic_results.values() if result.success)
        total_parsers = len(state.deterministic_results)
        
        if successful_parsers >= (total_parsers * 0.5):
            return "use_partial_results"
        elif successful_parsers > 0:
            return "minimal_processing"
        else:
            return "skip_processing"

