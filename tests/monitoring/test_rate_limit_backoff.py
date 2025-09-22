"""
Tests for rate limit backoff and circuit breaker functionality.
"""

import pytest
import asyncio
from unittest.mock import patch

from src.monitoring.rate_limit_backoff import (
    RateLimitBackoff, 
    CircuitBreaker, 
    RateLimitError, 
    CircuitBreakerOpenError,
    DatabaseRateLimitHandler
)


class TestRateLimitBackoff:
    """Test rate limit backoff functionality."""
    
    @pytest.mark.asyncio
    async def test_successful_operation(self):
        """Test successful operation without retries."""
        backoff = RateLimitBackoff(max_attempts=3)
        
        async def success_operation():
            return "success"
        
        result = await backoff.execute_with_backoff(success_operation)
        assert result == "success"
    
    @pytest.mark.asyncio
    async def test_retry_on_rate_limit(self):
        """Test retry logic on rate limit errors."""
        backoff = RateLimitBackoff(
            base_delay=0.01,  # Fast for testing
            max_delay=0.1,
            max_attempts=3
        )
        call_count = 0
        
        async def failing_operation():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise RateLimitError("Rate limit exceeded")
            return "success"
        
        result = await backoff.execute_with_backoff(failing_operation)
        assert result == "success"
        assert call_count == 3
    
    @pytest.mark.asyncio
    async def test_max_attempts_exceeded(self):
        """Test failure after max attempts."""
        backoff = RateLimitBackoff(max_attempts=2)
        
        async def always_failing_operation():
            raise RateLimitError("Rate limit exceeded")
        
        with pytest.raises(RateLimitError):
            await backoff.execute_with_backoff(always_failing_operation)
    
    @pytest.mark.asyncio
    async def test_non_rate_limit_error(self):
        """Test that non-rate-limit errors are not retried."""
        backoff = RateLimitBackoff(max_attempts=3)
        
        async def failing_operation():
            raise ValueError("Non-rate-limit error")
        
        with pytest.raises(ValueError):
            await backoff.execute_with_backoff(failing_operation)


class TestCircuitBreaker:
    """Test circuit breaker functionality."""
    
    @pytest.mark.asyncio
    async def test_closed_state_success(self):
        """Test successful operation in closed state."""
        circuit_breaker = CircuitBreaker(failure_threshold=2, timeout=1)
        
        async def success_operation():
            return "success"
        
        result = await circuit_breaker.call(success_operation)
        assert result == "success"
        assert circuit_breaker.state.value == "CLOSED"
    
    @pytest.mark.asyncio
    async def test_failure_threshold(self):
        """Test circuit breaker opening after failure threshold."""
        circuit_breaker = CircuitBreaker(failure_threshold=2, timeout=1)
        
        async def failing_operation():
            raise Exception("Test failure")
        
        # First failure
        with pytest.raises(Exception):
            await circuit_breaker.call(failing_operation)
        
        # Second failure should open circuit
        with pytest.raises(Exception):
            await circuit_breaker.call(failing_operation)
        
        assert circuit_breaker.state.value == "OPEN"
    
    @pytest.mark.asyncio
    async def test_open_state_blocks_operations(self):
        """Test that open circuit breaker blocks operations."""
        circuit_breaker = CircuitBreaker(failure_threshold=1, timeout=1)
        
        async def failing_operation():
            raise Exception("Test failure")
        
        # Trigger failure to open circuit
        with pytest.raises(Exception):
            await circuit_breaker.call(failing_operation)
        
        # Circuit should be open
        assert circuit_breaker.state.value == "OPEN"
        
        # New operations should be blocked
        with pytest.raises(CircuitBreakerOpenError):
            await circuit_breaker.call(failing_operation)
    
    @pytest.mark.asyncio
    async def test_half_open_recovery(self):
        """Test circuit breaker recovery in half-open state."""
        circuit_breaker = CircuitBreaker(
            failure_threshold=1, 
            timeout=0.1,  # Short timeout for testing
            success_threshold=1
        )
        
        async def failing_operation():
            raise Exception("Test failure")
        
        async def success_operation():
            return "success"
        
        # Trigger failure to open circuit
        with pytest.raises(Exception):
            await circuit_breaker.call(failing_operation)
        
        assert circuit_breaker.state.value == "OPEN"
        
        # Wait for timeout to move to half-open
        await asyncio.sleep(0.2)
        
        # Successful operation should close circuit
        result = await circuit_breaker.call(success_operation)
        assert result == "success"
        assert circuit_breaker.state.value == "CLOSED"
    
    def test_get_state(self):
        """Test getting circuit breaker state."""
        circuit_breaker = CircuitBreaker()
        state = circuit_breaker.get_state()
        
        assert "state" in state
        assert "failure_count" in state
        assert "success_count" in state
        assert "is_open" in state
        assert state["state"] == "CLOSED"
        assert state["is_open"] == False


class TestDatabaseRateLimitHandler:
    """Test database rate limit handler."""
    
    def test_initialization(self):
        """Test handler initialization."""
        backoff = RateLimitBackoff()
        circuit_breaker = CircuitBreaker()
        handler = DatabaseRateLimitHandler(backoff, circuit_breaker)
        
        assert handler.backoff == backoff
        assert handler.circuit_breaker == circuit_breaker
    
    @pytest.mark.asyncio
    async def test_successful_operation(self):
        """Test successful database operation."""
        backoff = RateLimitBackoff()
        circuit_breaker = CircuitBreaker()
        handler = DatabaseRateLimitHandler(backoff, circuit_breaker)
        
        async def success_operation():
            return "success"
        
        result = await handler.execute_database_operation(success_operation)
        assert result == "success"
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_open(self):
        """Test operation when circuit breaker is open."""
        backoff = RateLimitBackoff()
        circuit_breaker = CircuitBreaker(failure_threshold=1, timeout=1)
        handler = DatabaseRateLimitHandler(backoff, circuit_breaker)
        
        # Trigger circuit breaker to open
        async def failing_operation():
            raise Exception("Test failure")
        
        with pytest.raises(Exception):
            await handler.execute_database_operation(failing_operation)
        
        # Circuit should be open
        assert not handler.is_healthy()
        
        # New operations should be blocked
        with pytest.raises(CircuitBreakerOpenError):
            await handler.execute_database_operation(failing_operation)
    
    def test_is_healthy(self):
        """Test health check functionality."""
        backoff = RateLimitBackoff()
        circuit_breaker = CircuitBreaker()
        handler = DatabaseRateLimitHandler(backoff, circuit_breaker)
        
        assert handler.is_healthy() == True
    
    def test_get_health_status(self):
        """Test getting health status."""
        backoff = RateLimitBackoff()
        circuit_breaker = CircuitBreaker()
        handler = DatabaseRateLimitHandler(backoff, circuit_breaker)
        
        status = handler.get_health_status()
        
        assert "handler_healthy" in status
        assert "circuit_breaker" in status
        assert "backoff_config" in status
        assert status["handler_healthy"] == True
