"""
Rate limit backoff service with exponential retry logic.

This module provides intelligent rate limit handling with exponential backoff,
jitter, and circuit breaker patterns for database and API operations.
"""

import asyncio
import random
import time
from typing import Callable, Any, Optional, Dict
from enum import Enum


class RateLimitError(Exception):
    """Rate limit exceeded error."""
    pass


class CircuitBreakerOpenError(Exception):
    """Circuit breaker is open error."""
    pass


class CircuitBreakerState(Enum):
    """Circuit breaker states."""
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class RateLimitBackoff:
    """Rate limit backoff service with exponential retry logic."""
    
    def __init__(
        self,
        base_delay: float = 1.0,
        max_delay: float = 300.0,
        multiplier: float = 2.0,
        jitter_range: float = 0.1,
        max_attempts: int = 5
    ):
        """Initialize rate limit backoff service."""
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.multiplier = multiplier
        self.jitter_range = jitter_range
        self.max_attempts = max_attempts
    
    async def execute_with_backoff(self, operation: Callable) -> Any:
        """Execute operation with exponential backoff on rate limits."""
        delay = self.base_delay
        attempt = 0
        
        while attempt < self.max_attempts:
            try:
                return await operation()
            except RateLimitError as e:
                if attempt >= self.max_attempts - 1:
                    raise
                
                # Calculate delay with jitter
                jitter = random.uniform(-self.jitter_range, self.jitter_range)
                actual_delay = delay * (1 + jitter)
                
                await asyncio.sleep(actual_delay)
                delay = min(delay * self.multiplier, self.max_delay)
                attempt += 1
        
        raise RateLimitError(f"Operation failed after {self.max_attempts} attempts")


class CircuitBreaker:
    """Circuit breaker pattern for rate limit protection."""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        timeout: int = 60,
        success_threshold: int = 3
    ):
        """Initialize circuit breaker."""
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.success_threshold = success_threshold
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.state = CircuitBreakerState.CLOSED
    
    async def call(self, operation: Callable) -> Any:
        """Execute operation through circuit breaker."""
        if self.state == CircuitBreakerState.OPEN:
            if time.time() - self.last_failure_time > self.timeout:
                self.state = CircuitBreakerState.HALF_OPEN
                self.success_count = 0
            else:
                raise CircuitBreakerOpenError("Circuit breaker is OPEN")
        
        try:
            result = await operation()
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise
    
    def _on_success(self):
        """Handle successful operation."""
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.success_threshold:
                self.state = CircuitBreakerState.CLOSED
                self.failure_count = 0
        elif self.state == CircuitBreakerState.CLOSED:
            self.failure_count = max(0, self.failure_count - 1)
    
    def _on_failure(self):
        """Handle failed operation."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitBreakerState.OPEN
    
    def get_state(self) -> Dict[str, Any]:
        """Get circuit breaker state information."""
        return {
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure_time": self.last_failure_time,
            "is_open": self.state == CircuitBreakerState.OPEN
        }


class DatabaseRateLimitHandler:
    """Database-specific rate limit handler."""
    
    def __init__(self, backoff: RateLimitBackoff, circuit_breaker: CircuitBreaker):
        """Initialize database rate limit handler."""
        self.backoff = backoff
        self.circuit_breaker = circuit_breaker
    
    async def execute_database_operation(self, operation: Callable) -> Any:
        """Execute database operation with rate limit protection."""
        try:
            return await self.circuit_breaker.call(
                lambda: self.backoff.execute_with_backoff(operation)
            )
        except CircuitBreakerOpenError:
            # Log circuit breaker open
            print("Database circuit breaker is OPEN - operation blocked")
            raise
        except RateLimitError:
            # Log rate limit error
            print("Database rate limit exceeded - operation failed")
            raise
    
    def is_healthy(self) -> bool:
        """Check if database rate limit handler is healthy."""
        return not self.circuit_breaker.get_state()["is_open"]
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get health status of rate limit handler."""
        return {
            "handler_healthy": self.is_healthy(),
            "circuit_breaker": self.circuit_breaker.get_state(),
            "backoff_config": {
                "base_delay": self.backoff.base_delay,
                "max_delay": self.backoff.max_delay,
                "max_attempts": self.backoff.max_attempts
            }
        }
