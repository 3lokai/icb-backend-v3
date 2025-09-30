"""Unit tests for rate limiter."""

import pytest
import time

from src.llm.rate_limiter import RateLimiter


class TestRateLimiter:
    """Tests for rate limiter"""
    
    def test_initialization(self):
        """Test rate limiter initializes correctly"""
        limits = {
            'requests_per_minute': 60,
            'requests_per_hour': 1000,
            'requests_per_day': 10000
        }
        limiter = RateLimiter(limits)
        
        assert limiter.rate_limits == limits
        assert limiter.request_counts == {}
    
    def test_allows_request_within_limits(self):
        """Test that requests are allowed when within limits"""
        limiter = RateLimiter({
            'requests_per_minute': 10,
            'requests_per_hour': 100,
            'requests_per_day': 1000
        })
        
        # Should allow first request
        assert limiter.can_make_request('roaster1') is True
    
    def test_enforces_minute_limit(self):
        """Test that minute limit is enforced"""
        limiter = RateLimiter({
            'requests_per_minute': 2,
            'requests_per_hour': 100,
            'requests_per_day': 1000
        })
        
        # Make 2 requests (at limit)
        assert limiter.can_make_request('roaster1') is True
        assert limiter.can_make_request('roaster1') is True
        
        # Third request should be blocked
        assert limiter.can_make_request('roaster1') is False
    
    def test_enforces_hour_limit(self):
        """Test that hour limit is enforced"""
        limiter = RateLimiter({
            'requests_per_minute': 1000,
            'requests_per_hour': 2,
            'requests_per_day': 1000
        })
        
        # Make 2 requests (at limit)
        assert limiter.can_make_request('roaster1') is True
        assert limiter.can_make_request('roaster1') is True
        
        # Third request should be blocked
        assert limiter.can_make_request('roaster1') is False
    
    def test_separate_limits_per_roaster(self):
        """Test that each roaster has independent limits"""
        limiter = RateLimiter({
            'requests_per_minute': 2,
            'requests_per_hour': 100,
            'requests_per_day': 1000
        })
        
        # Roaster1 uses up its limit
        assert limiter.can_make_request('roaster1') is True
        assert limiter.can_make_request('roaster1') is True
        assert limiter.can_make_request('roaster1') is False
        
        # Roaster2 should still be able to make requests
        assert limiter.can_make_request('roaster2') is True
        assert limiter.can_make_request('roaster2') is True
        assert limiter.can_make_request('roaster2') is False
    
    def test_get_remaining_quota(self):
        """Test getting remaining quota for roaster"""
        limiter = RateLimiter({
            'requests_per_minute': 10,
            'requests_per_hour': 100,
            'requests_per_day': 1000
        })
        
        # Initially should have full quota
        remaining = limiter.get_remaining_quota('roaster1')
        assert remaining['minute'] == 10
        assert remaining['hour'] == 100
        assert remaining['day'] == 1000
        
        # After 3 requests
        limiter.can_make_request('roaster1')
        limiter.can_make_request('roaster1')
        limiter.can_make_request('roaster1')
        
        remaining = limiter.get_remaining_quota('roaster1')
        assert remaining['minute'] == 7
        assert remaining['hour'] == 97
        assert remaining['day'] == 997
    
    def test_reset_roaster(self):
        """Test resetting rate limits for a roaster"""
        limiter = RateLimiter({
            'requests_per_minute': 2,
            'requests_per_hour': 100,
            'requests_per_day': 1000
        })
        
        # Use up the limit
        limiter.can_make_request('roaster1')
        limiter.can_make_request('roaster1')
        assert limiter.can_make_request('roaster1') is False
        
        # Reset the roaster
        limiter.reset_roaster('roaster1')
        
        # Should be able to make requests again
        assert limiter.can_make_request('roaster1') is True
    
    def test_cleanup_old_requests(self):
        """Test that old requests are cleaned up"""
        limiter = RateLimiter({
            'requests_per_minute': 100,
            'requests_per_hour': 1000,
            'requests_per_day': 3
        })
        
        # Make 3 requests
        limiter.can_make_request('roaster1')
        limiter.can_make_request('roaster1')
        limiter.can_make_request('roaster1')
        
        # At day limit now
        assert limiter.can_make_request('roaster1') is False
        
        # Manually age the requests by modifying timestamps
        current_time = time.time()
        old_time = current_time - 86401  # Just over 1 day ago
        limiter.request_counts['roaster1'] = [old_time, old_time, old_time]
        
        # Should be able to make request again (old ones cleaned up)
        assert limiter.can_make_request('roaster1') is True
