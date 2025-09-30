"""Rate limiting service for LLM calls per roaster."""

import time
from typing import Dict, List
from datetime import datetime, timedelta
import structlog

logger = structlog.get_logger(__name__)


class RateLimiter:
    """Rate limiter for LLM calls with per-roaster limits"""
    
    def __init__(self, rate_limits: Dict[str, int]):
        """Initialize rate limiter
        
        Args:
            rate_limits: Dictionary with rate limit configuration
                - requests_per_minute: Limit per minute
                - requests_per_hour: Limit per hour  
                - requests_per_day: Limit per day
        """
        self.rate_limits = rate_limits
        self.request_counts: Dict[str, List[float]] = {}
        self.windows = {
            'minute': 60,
            'hour': 3600,
            'day': 86400
        }
    
    def can_make_request(self, roaster_id: str) -> bool:
        """Check if request can be made within rate limits
        
        Args:
            roaster_id: The roaster ID to check limits for
            
        Returns:
            True if request can be made, False if rate limited
        """
        current_time = time.time()
        
        # Get current request timestamps for this roaster
        if roaster_id not in self.request_counts:
            self.request_counts[roaster_id] = []
        
        roaster_requests = self.request_counts[roaster_id]
        
        # Check each time window
        for window_name, window_seconds in self.windows.items():
            window_start = current_time - window_seconds
            
            # Filter to requests within this window
            requests_in_window = [
                req_time for req_time in roaster_requests 
                if req_time > window_start
            ]
            
            # Get limit for this window
            limit_key = f'requests_per_{window_name}'
            limit = self.rate_limits.get(limit_key, float('inf'))
            
            # Check if over limit
            if len(requests_in_window) >= limit:
                logger.warning(
                    "rate_limit_exceeded",
                    roaster_id=roaster_id,
                    window=window_name,
                    count=len(requests_in_window),
                    limit=limit
                )
                return False
        
        # Record this request
        roaster_requests.append(current_time)
        
        # Cleanup old requests (older than 1 day)
        cutoff = current_time - self.windows['day']
        self.request_counts[roaster_id] = [
            req_time for req_time in roaster_requests 
            if req_time > cutoff
        ]
        
        return True
    
    def get_remaining_quota(self, roaster_id: str) -> Dict[str, int]:
        """Get remaining quota for roaster in each time window
        
        Args:
            roaster_id: The roaster ID to check
            
        Returns:
            Dictionary with remaining requests per window
        """
        current_time = time.time()
        
        if roaster_id not in self.request_counts:
            return {
                'minute': self.rate_limits.get('requests_per_minute', 0),
                'hour': self.rate_limits.get('requests_per_hour', 0),
                'day': self.rate_limits.get('requests_per_day', 0)
            }
        
        roaster_requests = self.request_counts[roaster_id]
        remaining = {}
        
        for window_name, window_seconds in self.windows.items():
            window_start = current_time - window_seconds
            requests_in_window = len([
                req_time for req_time in roaster_requests 
                if req_time > window_start
            ])
            
            limit_key = f'requests_per_{window_name}'
            limit = self.rate_limits.get(limit_key, 0)
            remaining[window_name] = max(0, limit - requests_in_window)
        
        return remaining
    
    def reset_roaster(self, roaster_id: str):
        """Reset rate limit counters for a roaster
        
        Args:
            roaster_id: The roaster ID to reset
        """
        if roaster_id in self.request_counts:
            del self.request_counts[roaster_id]
            logger.info("rate_limit_reset", roaster_id=roaster_id)
