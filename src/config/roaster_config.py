"""
Roaster configuration management.

This module handles:
- Loading roaster configuration from database
- Per-roaster cadence and concurrency settings
- Configuration validation and defaults
- Integration with Supabase database
"""

import os
from typing import Dict, Any, Optional
from datetime import datetime

import structlog
from supabase import create_client, Client

logger = structlog.get_logger(__name__)


class RoasterConfig:
    """Manages roaster-specific configuration."""
    
    def __init__(self):
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_KEY')
        self.client: Optional[Client] = None
        
        if not self.supabase_url or not self.supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set")
    
    async def connect(self):
        """Connect to Supabase."""
        if not self.client:
            self.client = create_client(self.supabase_url, self.supabase_key)
            logger.info("Connected to Supabase")
    
    async def get_roaster_config(self, roaster_id: str) -> Dict[str, Any]:
        """
        Get configuration for a specific roaster.
        
        Args:
            roaster_id: The roaster ID to get configuration for
            
        Returns:
            Dict containing roaster configuration
        """
        await self.connect()
        
        try:
            # Query roaster configuration from database
            response = self.client.table('roasters').select('*').eq('id', roaster_id).execute()
            
            if not response.data:
                logger.warning("Roaster not found", roaster_id=roaster_id)
                return self._get_default_config()
            
            roaster = response.data[0]
            
            # Extract configuration
            config = {
                'id': roaster['id'],
                'name': roaster['name'],
                'full_cadence': roaster.get('full_cadence', '0 3 1 * *'),
                'price_cadence': roaster.get('price_cadence', '0 4 * * 0'),
                'default_concurrency': roaster.get('default_concurrency', 3),
                'use_firecrawl_fallback': roaster.get('use_firecrawl_fallback', False),
                'firecrawl_budget_limit': roaster.get('firecrawl_budget_limit', 1000),
                'use_llm': roaster.get('use_llm', False),
                'alert_price_delta_pct': roaster.get('alert_price_delta_pct', 20.0),
                'last_etag': roaster.get('last_etag'),
                'last_modified': roaster.get('last_modified'),
                'base_url': roaster.get('base_url'),
                'api_endpoints': roaster.get('api_endpoints', {}),
            }
            
            logger.info("Loaded roaster config", 
                       roaster_id=roaster_id, 
                       concurrency=config['default_concurrency'])
            
            return config
            
        except Exception as e:
            logger.error("Failed to load roaster config", 
                        roaster_id=roaster_id, 
                        error=str(e), 
                        exc_info=True)
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration when roaster config is not available."""
        return {
            'id': 'unknown',
            'name': 'Unknown Roaster',
            'full_cadence': '0 3 1 * *',
            'price_cadence': '0 4 * * 0',
            'default_concurrency': 3,
            'use_firecrawl_fallback': False,
            'firecrawl_budget_limit': 1000,
            'use_llm': False,
            'alert_price_delta_pct': 20.0,
            'last_etag': None,
            'last_modified': None,
            'base_url': None,
            'api_endpoints': {},
        }
    
    async def update_roaster_metadata(self, roaster_id: str, etag: str = None, last_modified: str = None):
        """Update roaster metadata after successful scraping."""
        await self.connect()
        
        try:
            update_data = {}
            if etag:
                update_data['last_etag'] = etag
            if last_modified:
                update_data['last_modified'] = last_modified
            
            if update_data:
                self.client.table('roasters').update(update_data).eq('id', roaster_id).execute()
                logger.info("Updated roaster metadata", 
                           roaster_id=roaster_id, 
                           updates=update_data)
                
        except Exception as e:
            logger.error("Failed to update roaster metadata", 
                        roaster_id=roaster_id, 
                        error=str(e), 
                        exc_info=True)
    
    async def get_all_roasters(self) -> list[Dict[str, Any]]:
        """Get all active roasters for scheduling."""
        await self.connect()
        
        try:
            response = self.client.table('roasters').select('id,name,full_cadence,price_cadence').eq('active', True).execute()
            return response.data or []
            
        except Exception as e:
            logger.error("Failed to get roasters list", error=str(e), exc_info=True)
            return []
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate roaster configuration."""
        required_fields = ['id', 'name', 'full_cadence', 'price_cadence']
        
        for field in required_fields:
            if field not in config or not config[field]:
                logger.error("Missing required config field", field=field, config=config)
                return False
        
        # Validate concurrency
        concurrency = config.get('default_concurrency', 0)
        if not isinstance(concurrency, int) or concurrency < 1 or concurrency > 10:
            logger.error("Invalid concurrency value", concurrency=concurrency)
            return False
        
        return True
