"""
Fetcher configuration management.
Reads configuration from product_sources table and provides per-roaster settings.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
import asyncio
from supabase import create_client, Client
import os
from structlog import get_logger

logger = get_logger(__name__)


@dataclass
class SourceConfig:
    """Configuration for a product source."""
    id: str
    roaster_id: str
    base_url: str
    platform: str
    products_endpoint: str
    sitemap_url: Optional[str] = None
    robots_ok: bool = True
    last_ok_ping: Optional[str] = None


@dataclass
class RoasterConfig:
    """Configuration for a roaster's scraping behavior."""
    roaster_id: str
    default_concurrency: int = 3
    politeness_delay: float = 0.25
    timeout: float = 30.0
    max_retries: int = 3
    use_firecrawl_fallback: bool = False
    use_llm: bool = False


class FetcherConfigManager:
    """Manages fetcher configuration from database."""
    
    def __init__(self):
        self._supabase: Optional[Client] = None
        self._config_cache: Dict[str, SourceConfig] = {}
        self._roaster_cache: Dict[str, RoasterConfig] = {}
    
    def _get_supabase_client(self) -> Client:
        """Get Supabase client with environment configuration."""
        if self._supabase is None:
            supabase_url = os.getenv('SUPABASE_URL')
            supabase_key = os.getenv('SUPABASE_ANON_KEY')
            
            if not supabase_url or not supabase_key:
                raise ValueError(
                    "SUPABASE_URL and SUPABASE_ANON_KEY environment variables are required"
                )
            
            self._supabase = create_client(supabase_url, supabase_key)
        
        return self._supabase
    
    async def get_source_config(self, source_id: str) -> SourceConfig:
        """Get configuration for a specific product source."""
        if source_id in self._config_cache:
            return self._config_cache[source_id]
        
        supabase = self._get_supabase_client()
        
        try:
            response = supabase.table('product_sources').select('*').eq('id', source_id).execute()
            
            if not response.data:
                raise ValueError(f"Product source {source_id} not found")
            
            source_data = response.data[0]
            config = SourceConfig(
                id=source_data['id'],
                roaster_id=source_data['roaster_id'],
                base_url=source_data['base_url'],
                platform=source_data['platform'],
                products_endpoint=source_data['products_endpoint'],
                sitemap_url=source_data.get('sitemap_url'),
                robots_ok=source_data.get('robots_ok', True),
                last_ok_ping=source_data.get('last_ok_ping'),
            )
            
            self._config_cache[source_id] = config
            logger.info(
                "Loaded source configuration",
                source_id=source_id,
                roaster_id=config.roaster_id,
                platform=config.platform,
                base_url=config.base_url,
            )
            
            return config
            
        except Exception as e:
            logger.error(
                "Failed to load source configuration",
                source_id=source_id,
                error=str(e),
            )
            raise
    
    async def get_roaster_config(self, roaster_id: str) -> RoasterConfig:
        """Get configuration for a specific roaster."""
        if roaster_id in self._roaster_cache:
            return self._roaster_cache[roaster_id]
        
        supabase = self._get_supabase_client()
        
        try:
            response = supabase.table('roasters').select(
                'id, default_concurrency, use_firecrawl_fallback, use_llm'
            ).eq('id', roaster_id).execute()
            
            if not response.data:
                raise ValueError(f"Roaster {roaster_id} not found")
            
            roaster_data = response.data[0]
            config = RoasterConfig(
                roaster_id=roaster_id,
                default_concurrency=roaster_data.get('default_concurrency', 3),
                politeness_delay=0.25,  # Default value
                timeout=30.0,  # Default value
                max_retries=3,  # Default value
                use_firecrawl_fallback=roaster_data.get('use_firecrawl_fallback', False),
                use_llm=roaster_data.get('use_llm', False),
            )
            
            self._roaster_cache[roaster_id] = config
            logger.info(
                "Loaded roaster configuration",
                roaster_id=roaster_id,
                default_concurrency=config.default_concurrency,
                use_firecrawl_fallback=config.use_firecrawl_fallback,
                use_llm=config.use_llm,
            )
            
            return config
            
        except Exception as e:
            logger.error(
                "Failed to load roaster configuration",
                roaster_id=roaster_id,
                error=str(e),
            )
            raise
    
    async def get_all_active_sources(self) -> List[SourceConfig]:
        """Get all active product sources."""
        supabase = self._get_supabase_client()
        
        try:
            # Get all sources with their roasters
            response = supabase.table('product_sources').select(
                '*, roasters!inner(is_active)'
            ).eq('roasters.is_active', True).execute()
            
            sources = []
            for source_data in response.data:
                config = SourceConfig(
                    id=source_data['id'],
                    roaster_id=source_data['roaster_id'],
                    base_url=source_data['base_url'],
                    platform=source_data['platform'],
                    products_endpoint=source_data['products_endpoint'],
                    sitemap_url=source_data.get('sitemap_url'),
                    robots_ok=source_data.get('robots_ok', True),
                    last_ok_ping=source_data.get('last_ok_ping'),
                )
                sources.append(config)
                self._config_cache[config.id] = config
            
            logger.info(
                "Loaded active sources",
                count=len(sources),
                platforms=[s.platform for s in sources],
            )
            
            return sources
            
        except Exception as e:
            logger.error(
                "Failed to load active sources",
                error=str(e),
            )
            raise
    
    async def update_source_ping(self, source_id: str, success: bool):
        """Update the last ping status for a source."""
        supabase = self._get_supabase_client()
        
        try:
            update_data = {
                'last_ok_ping': 'now()' if success else None,
            }
            
            supabase.table('product_sources').update(update_data).eq('id', source_id).execute()
            
            logger.info(
                "Updated source ping status",
                source_id=source_id,
                success=success,
            )
            
        except Exception as e:
            logger.error(
                "Failed to update source ping status",
                source_id=source_id,
                success=success,
                error=str(e),
            )
            raise


# Global config manager instance
config_manager = FetcherConfigManager()
