"""
Main fetcher service that orchestrates product fetching from multiple sources.
Handles configuration loading, fetcher creation, and result storage.
"""

import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime
import json

from structlog import get_logger

from .fetcher_factory import create_fetcher_from_source_id
from ..config.fetcher_config import config_manager

logger = get_logger(__name__)


class FetcherService:
    """
    Main service for orchestrating product fetching.
    
    Features:
    - Loads configuration from product_sources table
    - Creates platform-specific fetchers
    - Handles concurrent fetching with proper rate limiting
    - Stores raw responses for validation
    - Updates source ping status
    """
    
    def __init__(self):
        self.results: Dict[str, Any] = {}
        self.errors: Dict[str, str] = {}
    
    async def fetch_from_source(
        self,
        source_id: str,
        auth_credentials: Optional[Dict[str, str]] = None,
        fetch_all: bool = True,
        **fetch_params
    ) -> Dict[str, Any]:
        """
        Fetch products from a specific source.
        
        Args:
            source_id: Product source ID
            auth_credentials: Authentication credentials
            fetch_all: Whether to fetch all products or just one page
            **fetch_params: Additional fetch parameters
            
        Returns:
            Dictionary with fetch results and metadata
        """
        start_time = datetime.utcnow()
        
        try:
            logger.info(
                "Starting fetch from source",
                source_id=source_id,
                fetch_all=fetch_all,
                fetch_params=fetch_params,
            )
            
            # Create fetcher
            async with create_fetcher_from_source_id(source_id, auth_credentials) as fetcher:
                # Test connection first
                if not await fetcher.test_connection():
                    raise Exception("Connection test failed")
                
                # Fetch products
                if fetch_all:
                    products = await fetcher.fetch_all_products(**fetch_params)
                else:
                    products = await fetcher.fetch_products(**fetch_params)
                
                # Store results
                result = {
                    'source_id': source_id,
                    'roaster_id': fetcher.roaster_id,
                    'platform': fetcher.platform,
                    'base_url': fetcher.base_url,
                    'products': products,
                    'product_count': len(products),
                    'fetch_all': fetch_all,
                    'fetch_params': fetch_params,
                    'started_at': start_time.isoformat(),
                    'completed_at': datetime.utcnow().isoformat(),
                    'success': True,
                }
                
                self.results[source_id] = result
                
                # Update source ping status
                await config_manager.update_source_ping(source_id, True)
                
                logger.info(
                    "Successfully fetched products",
                    source_id=source_id,
                    roaster_id=fetcher.roaster_id,
                    platform=fetcher.platform,
                    product_count=len(products),
                    duration_seconds=(datetime.utcnow() - start_time).total_seconds(),
                )
                
                return result
        
        except Exception as e:
            error_msg = str(e)
            self.errors[source_id] = error_msg
            
            # Update source ping status
            await config_manager.update_source_ping(source_id, False)
            
            logger.error(
                "Failed to fetch from source",
                source_id=source_id,
                error=error_msg,
                duration_seconds=(datetime.utcnow() - start_time).total_seconds(),
            )
            
            return {
                'source_id': source_id,
                'products': [],
                'product_count': 0,
                'success': False,
                'error': error_msg,
                'started_at': start_time.isoformat(),
                'completed_at': datetime.utcnow().isoformat(),
            }
    
    async def fetch_from_all_sources(
        self,
        auth_credentials_map: Optional[Dict[str, Dict[str, str]]] = None,
        fetch_all: bool = True,
        **fetch_params
    ) -> Dict[str, Any]:
        """
        Fetch products from all active sources concurrently.
        
        Args:
            auth_credentials_map: Mapping of source_id to auth credentials
            fetch_all: Whether to fetch all products or just one page
            **fetch_params: Additional fetch parameters
            
        Returns:
            Dictionary with results from all sources
        """
        logger.info(
            "Starting fetch from all sources",
            fetch_all=fetch_all,
            fetch_params=fetch_params,
        )
        
        # Load all active sources
        sources = await config_manager.get_all_active_sources()
        
        if not sources:
            logger.warning("No active sources found")
            return {
                'sources': [],
                'total_products': 0,
                'successful_sources': 0,
                'failed_sources': 0,
                'results': {},
                'errors': {},
            }
        
        # Create fetch tasks
        tasks = []
        for source in sources:
            auth_creds = auth_credentials_map.get(source.id) if auth_credentials_map else None
            task = self.fetch_from_source(
                source.id,
                auth_creds,
                fetch_all,
                **fetch_params
            )
            tasks.append(task)
        
        # Execute all fetches concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        successful_sources = 0
        failed_sources = 0
        total_products = 0
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                failed_sources += 1
                logger.error(
                    "Source fetch failed with exception",
                    source_id=sources[i].id,
                    error=str(result),
                )
            elif result.get('success', False):
                successful_sources += 1
                total_products += result.get('product_count', 0)
            else:
                failed_sources += 1
        
        summary = {
            'sources': [{'id': s.id, 'platform': s.platform, 'base_url': s.base_url} for s in sources],
            'total_products': total_products,
            'successful_sources': successful_sources,
            'failed_sources': failed_sources,
            'results': {r.get('source_id', f'unknown_{i}'): r for i, r in enumerate(results) if not isinstance(r, Exception)},
            'errors': {sources[i].id: str(r) for i, r in enumerate(results) if isinstance(r, Exception)},
        }
        
        logger.info(
            "Completed fetch from all sources",
            total_sources=len(sources),
            successful_sources=successful_sources,
            failed_sources=failed_sources,
            total_products=total_products,
        )
        
        return summary
    
    async def fetch_sample_roasters(
        self,
        sample_roasters: List[str],
        auth_credentials_map: Optional[Dict[str, Dict[str, str]]] = None,
        **fetch_params
    ) -> Dict[str, Any]:
        """
        Fetch products from sample roasters for testing.
        
        Args:
            sample_roasters: List of roaster IDs to fetch from
            auth_credentials_map: Mapping of roaster_id to auth credentials
            **fetch_params: Additional fetch parameters
            
        Returns:
            Dictionary with results from sample roasters
        """
        logger.info(
            "Starting fetch from sample roasters",
            sample_roasters=sample_roasters,
            fetch_params=fetch_params,
        )
        
        # Load all sources and filter by sample roasters
        all_sources = await config_manager.get_all_active_sources()
        sample_sources = [s for s in all_sources if s.roaster_id in sample_roasters]
        
        if not sample_sources:
            logger.warning("No sources found for sample roasters", sample_roasters=sample_roasters)
            return {
                'sample_roasters': sample_roasters,
                'sources_found': 0,
                'total_products': 0,
                'results': {},
                'errors': {},
            }
        
        # Create fetch tasks for sample sources
        tasks = []
        for source in sample_sources:
            auth_creds = auth_credentials_map.get(source.roaster_id) if auth_credentials_map else None
            task = self.fetch_from_source(
                source.id,
                auth_creds,
                fetch_all=True,  # Always fetch all for samples
                **fetch_params
            )
            tasks.append(task)
        
        # Execute fetches concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        total_products = 0
        successful_sources = 0
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(
                    "Sample source fetch failed",
                    source_id=sample_sources[i].id,
                    roaster_id=sample_sources[i].roaster_id,
                    error=str(result),
                )
            elif result.get('success', False):
                successful_sources += 1
                total_products += result.get('product_count', 0)
        
        summary = {
            'sample_roasters': sample_roasters,
            'sources_found': len(sample_sources),
            'successful_sources': successful_sources,
            'total_products': total_products,
            'results': {r.get('source_id', f'unknown_{i}'): r for i, r in enumerate(results) if not isinstance(r, Exception)},
            'errors': {sample_sources[i].id: str(r) for i, r in enumerate(results) if isinstance(r, Exception)},
        }
        
        logger.info(
            "Completed fetch from sample roasters",
            sample_roasters=sample_roasters,
            sources_found=len(sample_sources),
            successful_sources=successful_sources,
            total_products=total_products,
        )
        
        return summary
