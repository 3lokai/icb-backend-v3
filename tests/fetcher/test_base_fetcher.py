"""
Tests for base fetcher implementation.
"""

import pytest
import asyncio
import json
from unittest.mock import AsyncMock, patch, MagicMock

from src.fetcher.base_fetcher import BaseFetcher, FetcherConfig


class ConcreteFetcher(BaseFetcher):
    """Concrete implementation of BaseFetcher for testing."""
    
    async def fetch_products(self, **kwargs):
        """Dummy implementation."""
        return []
    
    async def fetch_all_products(self, **kwargs):
        """Dummy implementation."""
        return []


class TestBaseFetcher:
    """Test cases for BaseFetcher."""
    
    @pytest.fixture
    def fetcher_config(self):
        """Create a test fetcher configuration."""
        return FetcherConfig(
            timeout=10.0,
            max_retries=2,
            retry_delay=0.1,
            politeness_delay=0.1,
            jitter_range=0.05,
            max_concurrent=2,
        )
    
    @pytest.fixture
    def base_fetcher(self, fetcher_config):
        """Create a test base fetcher."""
        return ConcreteFetcher(
            config=fetcher_config,
            roaster_id="test-roaster",
            base_url="https://test-store.com",
            platform="test",
        )
    
    @pytest.mark.asyncio
    async def test_etag_caching(self, base_fetcher):
        """Test ETag caching functionality."""
        with patch.object(base_fetcher._client, 'request') as mock_request:
            # First request - no ETag
            mock_request.return_value = MagicMock(
                status_code=200,
                headers={'etag': '"abc123"', 'content-type': 'application/json'},
                content=json.dumps({"data": "test"}).encode()
            )
            
            status_code, headers, content = await base_fetcher._make_request("https://test.com/api")
            
            assert status_code == 200
            assert base_fetcher._etags["https://test.com/api"] == '"abc123"'
            
            # Second request - should include If-None-Match
            mock_request.return_value = MagicMock(
                status_code=304,
                headers={'content-type': 'application/json'},
                content=b''
            )
            
            status_code, headers, content = await base_fetcher._make_request("https://test.com/api")
            
            assert status_code == 304
            assert content == b''
            
            # Verify If-None-Match header was sent
            call_args = mock_request.call_args
            assert 'If-None-Match' in call_args[1]['headers']
            assert call_args[1]['headers']['If-None-Match'] == '"abc123"'
    
    @pytest.mark.asyncio
    async def test_last_modified_caching(self, base_fetcher):
        """Test Last-Modified caching functionality."""
        with patch.object(base_fetcher._client, 'request') as mock_request:
            # First request - no Last-Modified
            mock_request.return_value = MagicMock(
                status_code=200,
                headers={'last-modified': 'Wed, 21 Oct 2015 07:28:00 GMT', 'content-type': 'application/json'},
                content=json.dumps({"data": "test"}).encode()
            )
            
            status_code, headers, content = await base_fetcher._make_request("https://test.com/api")
            
            assert status_code == 200
            assert base_fetcher._last_modified["https://test.com/api"] == 'Wed, 21 Oct 2015 07:28:00 GMT'
            
            # Second request - should include If-Modified-Since
            mock_request.return_value = MagicMock(
                status_code=304,
                headers={'content-type': 'application/json'},
                content=b''
            )
            
            status_code, headers, content = await base_fetcher._make_request("https://test.com/api")
            
            assert status_code == 304
            assert content == b''
            
            # Verify If-Modified-Since header was sent
            call_args = mock_request.call_args
            assert 'If-Modified-Since' in call_args[1]['headers']
            assert call_args[1]['headers']['If-Modified-Since'] == 'Wed, 21 Oct 2015 07:28:00 GMT'
    
    @pytest.mark.asyncio
    async def test_304_not_modified_handling(self, base_fetcher):
        """Test handling of 304 Not Modified responses."""
        with patch.object(base_fetcher._client, 'request') as mock_request:
            mock_request.return_value = MagicMock(
                status_code=304,
                headers={'content-type': 'application/json'},
                content=b''
            )
            
            status_code, headers, content = await base_fetcher._make_request("https://test.com/api")
            
            assert status_code == 304
            assert content == b''
    
    @pytest.mark.asyncio
    async def test_politeness_delay(self, base_fetcher):
        """Test that politeness delay is applied."""
        with patch('asyncio.sleep') as mock_sleep:
            with patch.object(base_fetcher._client, 'request') as mock_request:
                mock_request.return_value = MagicMock(
                    status_code=200,
                    headers={'content-type': 'application/json'},
                    content=b'{"data": "test"}'
                )
                
                await base_fetcher._make_request("https://test.com/api")
                
                # Verify sleep was called for politeness delay
                mock_sleep.assert_called_once()
                # Check that the delay is within expected range (0.1 ± 0.05)
                call_args = mock_sleep.call_args[0][0]
                assert 0.05 <= call_args <= 0.15
    
    @pytest.mark.asyncio
    async def test_retry_logic(self, base_fetcher):
        """Test retry logic with exponential backoff."""
        with patch('asyncio.sleep') as mock_sleep:
            with patch.object(base_fetcher._client, 'request') as mock_request:
                # First two calls fail, third succeeds
                mock_request.side_effect = [
                    MagicMock(status_code=500, headers={}, content=b'Server Error'),
                    MagicMock(status_code=500, headers={}, content=b'Server Error'),
                    MagicMock(status_code=200, headers={}, content=b'{"data": "test"}'),
                ]
                
                status_code, headers, content = await base_fetcher._make_request("https://test.com/api")
                
                assert status_code == 200
                assert mock_request.call_count == 3
                
                # Verify exponential backoff delays
                sleep_calls = mock_sleep.call_args_list
                assert len(sleep_calls) >= 2  # At least two retries (politeness delay + retry delays)
                
                # Find the retry delays (exclude politeness delays which are < 0.1)
                retry_delays = [call[0][0] for call in sleep_calls if call[0][0] >= 0.1]
                assert len(retry_delays) >= 2
                # Check that retry delays are approximately correct (allowing for jitter)
                # First retry: 0.1 * (2^0) = 0.1, Second retry: 0.1 * (2^1) = 0.2
                assert 0.05 <= retry_delays[0] <= 0.15  # First retry delay (0.1 ± jitter)
                assert 0.15 <= retry_delays[1] <= 0.25  # Second retry delay (0.2 ± jitter)
    
    @pytest.mark.asyncio
    async def test_timeout_handling(self, base_fetcher):
        """Test timeout handling."""
        with patch.object(base_fetcher._client, 'request') as mock_request:
            mock_request.side_effect = Exception("Timeout")
            
            with pytest.raises(Exception, match="Timeout"):
                await base_fetcher._make_request("https://test.com/api")
    
    @pytest.mark.asyncio
    async def test_concurrency_control(self, base_fetcher):
        """Test that semaphore controls concurrency."""
        with patch.object(base_fetcher._client, 'request') as mock_request:
            mock_request.return_value = MagicMock(
                status_code=200,
                headers={'content-type': 'application/json'},
                content=b'{"data": "test"}'
            )
            
            # Create multiple concurrent requests
            tasks = [
                base_fetcher._make_request(f"https://test.com/api{i}")
                for i in range(5)
            ]
            
            results = await asyncio.gather(*tasks)
            
            # All requests should succeed
            assert all(result[0] == 200 for result in results)
            assert len(results) == 5
    
    def test_initialization(self, fetcher_config):
        """Test fetcher initialization."""
        fetcher = ConcreteFetcher(
            config=fetcher_config,
            roaster_id="test-roaster",
            base_url="https://test-store.com",
            platform="test",
        )
        
        assert fetcher.roaster_id == "test-roaster"
        assert fetcher.base_url == "https://test-store.com"
        assert fetcher.platform == "test"
        assert fetcher.config == fetcher_config
        assert fetcher._semaphore._value == fetcher_config.max_concurrent
    
    def test_build_url(self, base_fetcher):
        """Test URL building functionality."""
        # Test with endpoint starting with /
        url = base_fetcher._build_url("/api/products")
        assert url == "https://test-store.com/api/products"
        
        # Test with endpoint not starting with /
        url = base_fetcher._build_url("api/products")
        assert url == "https://test-store.com/api/products"
        
        # Test with base URL ending with /
        base_fetcher.base_url = "https://test-store.com/"
        url = base_fetcher._build_url("api/products")
        assert url == "https://test-store.com/api/products"
