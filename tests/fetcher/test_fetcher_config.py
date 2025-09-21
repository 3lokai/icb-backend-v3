"""
Tests for fetcher configuration management.
"""

import pytest
from unittest.mock import patch, MagicMock
import os

from src.config.fetcher_config import FetcherConfigManager, SourceConfig, RoasterConfig


class TestFetcherConfigManager:
    """Test cases for FetcherConfigManager."""
    
    @pytest.fixture
    def config_manager(self):
        """Create a test configuration manager."""
        return FetcherConfigManager()
    
    @pytest.fixture
    def mock_supabase_client(self):
        """Mock Supabase client."""
        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
            {
                'id': 'source-1',
                'roaster_id': 'roaster-1',
                'base_url': 'https://test-store.com',
                'platform': 'shopify',
                'products_endpoint': '/products.json',
                'sitemap_url': 'https://test-store.com/sitemap.xml',
                'robots_ok': True,
                'last_ok_ping': '2024-01-01T00:00:00Z'
            }
        ]
        return mock_client
    
    @pytest.fixture
    def mock_roaster_data(self):
        """Mock roaster data."""
        return [
            {
                'id': 'roaster-1',
                'default_concurrency': 5,
                'use_firecrawl_fallback': True,
                'use_llm': False
            }
        ]
    
    def test_source_config_creation(self):
        """Test SourceConfig creation."""
        config = SourceConfig(
            id='source-1',
            roaster_id='roaster-1',
            base_url='https://test-store.com',
            platform='shopify',
            products_endpoint='/products.json',
            sitemap_url='https://test-store.com/sitemap.xml',
            robots_ok=True,
            last_ok_ping='2024-01-01T00:00:00Z'
        )
        
        assert config.id == 'source-1'
        assert config.roaster_id == 'roaster-1'
        assert config.base_url == 'https://test-store.com'
        assert config.platform == 'shopify'
        assert config.products_endpoint == '/products.json'
        assert config.sitemap_url == 'https://test-store.com/sitemap.xml'
        assert config.robots_ok is True
        assert config.last_ok_ping == '2024-01-01T00:00:00Z'
    
    def test_roaster_config_creation(self):
        """Test RoasterConfig creation."""
        config = RoasterConfig(
            roaster_id='roaster-1',
            default_concurrency=5,
            politeness_delay=0.25,
            timeout=30.0,
            max_retries=3,
            use_firecrawl_fallback=True,
            use_llm=False
        )
        
        assert config.roaster_id == 'roaster-1'
        assert config.default_concurrency == 5
        assert config.politeness_delay == 0.25
        assert config.timeout == 30.0
        assert config.max_retries == 3
        assert config.use_firecrawl_fallback is True
        assert config.use_llm is False
    
    @patch.dict(os.environ, {
        'SUPABASE_URL': 'https://test.supabase.co',
        'SUPABASE_ANON_KEY': 'test-key'
    })
    @patch('src.config.fetcher_config.create_client')
    def test_get_supabase_client(self, mock_create_client, config_manager):
        """Test Supabase client creation."""
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client
        
        client = config_manager._get_supabase_client()
        
        assert client == mock_client
        mock_create_client.assert_called_once_with('https://test.supabase.co', 'test-key')
    
    @patch.dict(os.environ, {}, clear=True)
    def test_get_supabase_client_missing_env(self, config_manager):
        """Test Supabase client creation with missing environment variables."""
        with pytest.raises(ValueError, match="SUPABASE_URL and SUPABASE_ANON_KEY environment variables are required"):
            config_manager._get_supabase_client()
    
    @pytest.mark.asyncio
    @patch.object(FetcherConfigManager, '_get_supabase_client')
    async def test_get_source_config(self, mock_get_client, config_manager, mock_supabase_client):
        """Test getting source configuration."""
        mock_get_client.return_value = mock_supabase_client
        
        config = await config_manager.get_source_config('source-1')
        
        assert isinstance(config, SourceConfig)
        assert config.id == 'source-1'
        assert config.roaster_id == 'roaster-1'
        assert config.platform == 'shopify'
        assert config.base_url == 'https://test-store.com'
        
        # Verify cache was populated
        assert 'source-1' in config_manager._config_cache
    
    @pytest.mark.asyncio
    @patch.object(FetcherConfigManager, '_get_supabase_client')
    async def test_get_source_config_cached(self, mock_get_client, config_manager):
        """Test getting cached source configuration."""
        # Pre-populate cache
        config_manager._config_cache['source-1'] = SourceConfig(
            id='source-1',
            roaster_id='roaster-1',
            base_url='https://test-store.com',
            platform='shopify',
            products_endpoint='/products.json'
        )
        
        config = await config_manager.get_source_config('source-1')
        
        assert config.id == 'source-1'
        # Should not call Supabase
        mock_get_client.assert_not_called()
    
    @pytest.mark.asyncio
    @patch.object(FetcherConfigManager, '_get_supabase_client')
    async def test_get_source_config_not_found(self, mock_get_client, config_manager):
        """Test getting non-existent source configuration."""
        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
        mock_get_client.return_value = mock_client
        
        with pytest.raises(ValueError, match="Product source source-1 not found"):
            await config_manager.get_source_config('source-1')
    
    @pytest.mark.asyncio
    @patch.object(FetcherConfigManager, '_get_supabase_client')
    async def test_get_roaster_config(self, mock_get_client, config_manager, mock_roaster_data):
        """Test getting roaster configuration."""
        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = mock_roaster_data
        mock_get_client.return_value = mock_client
        
        config = await config_manager.get_roaster_config('roaster-1')
        
        assert isinstance(config, RoasterConfig)
        assert config.roaster_id == 'roaster-1'
        assert config.default_concurrency == 5
        assert config.use_firecrawl_fallback is True
        assert config.use_llm is False
        
        # Verify cache was populated
        assert 'roaster-1' in config_manager._roaster_cache
    
    @pytest.mark.asyncio
    @patch.object(FetcherConfigManager, '_get_supabase_client')
    async def test_get_roaster_config_cached(self, mock_get_client, config_manager):
        """Test getting cached roaster configuration."""
        # Pre-populate cache
        config_manager._roaster_cache['roaster-1'] = RoasterConfig(
            roaster_id='roaster-1',
            default_concurrency=3
        )
        
        config = await config_manager.get_roaster_config('roaster-1')
        
        assert config.roaster_id == 'roaster-1'
        # Should not call Supabase
        mock_get_client.assert_not_called()
    
    @pytest.mark.asyncio
    @patch.object(FetcherConfigManager, '_get_supabase_client')
    async def test_get_roaster_config_not_found(self, mock_get_client, config_manager):
        """Test getting non-existent roaster configuration."""
        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
        mock_get_client.return_value = mock_client
        
        with pytest.raises(ValueError, match="Roaster roaster-1 not found"):
            await config_manager.get_roaster_config('roaster-1')
    
    @pytest.mark.asyncio
    @patch.object(FetcherConfigManager, '_get_supabase_client')
    async def test_get_all_active_sources(self, mock_get_client, config_manager):
        """Test getting all active sources."""
        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
            {
                'id': 'source-1',
                'roaster_id': 'roaster-1',
                'base_url': 'https://test-store.com',
                'platform': 'shopify',
                'products_endpoint': '/products.json',
                'sitemap_url': 'https://test-store.com/sitemap.xml',
                'robots_ok': True,
                'last_ok_ping': '2024-01-01T00:00:00Z'
            },
            {
                'id': 'source-2',
                'roaster_id': 'roaster-2',
                'base_url': 'https://test-store2.com',
                'platform': 'woocommerce',
                'products_endpoint': '/wp-json/wc/store/products',
                'sitemap_url': None,
                'robots_ok': True,
                'last_ok_ping': None
            }
        ]
        mock_get_client.return_value = mock_client
        
        sources = await config_manager.get_all_active_sources()
        
        assert len(sources) == 2
        assert all(isinstance(source, SourceConfig) for source in sources)
        assert sources[0].id == 'source-1'
        assert sources[1].id == 'source-2'
        
        # Verify cache was populated
        assert 'source-1' in config_manager._config_cache
        assert 'source-2' in config_manager._config_cache
    
    @pytest.mark.asyncio
    @patch.object(FetcherConfigManager, '_get_supabase_client')
    async def test_update_source_ping_success(self, mock_get_client, config_manager):
        """Test updating source ping status for success."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        
        await config_manager.update_source_ping('source-1', True)
        
        # Verify update was called
        mock_client.table.assert_called_with('product_sources')
        mock_client.table.return_value.update.assert_called_once()
        mock_client.table.return_value.update.return_value.eq.assert_called_with('id', 'source-1')
        mock_client.table.return_value.update.return_value.eq.return_value.execute.assert_called_once()
    
    @pytest.mark.asyncio
    @patch.object(FetcherConfigManager, '_get_supabase_client')
    async def test_update_source_ping_failure(self, mock_get_client, config_manager):
        """Test updating source ping status for failure."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        
        await config_manager.update_source_ping('source-1', False)
        
        # Verify update was called with None for last_ok_ping
        update_call = mock_client.table.return_value.update.call_args[0][0]
        assert update_call['last_ok_ping'] is None
