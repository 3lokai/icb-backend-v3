"""
Task execution for scraping jobs.

This module implements:
- Placeholder task execution for scraping jobs
- Integration with roaster-specific configuration
- Error handling and retry logic
- Result processing and storage
"""

import asyncio
import httpx
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

import structlog

# Import Firecrawl services
from ..fetcher.firecrawl_client import FirecrawlClient
from ..fetcher.firecrawl_map_service import FirecrawlMapService
from ..fetcher.platform_fetcher_service import PlatformFetcherService
from ..config.firecrawl_config import (
    FirecrawlConfig, 
    FirecrawlConfigDefaults, 
    FirecrawlConfigValidator
)
from ..config.roaster_schema import RoasterConfigSchema, RoasterConfigValidator
from ..fetcher.base_fetcher import FetcherConfig

logger = structlog.get_logger(__name__)

# Default comprehensive coffee keywords - can be overridden via environment variables
DEFAULT_COFFEE_KEYWORDS = [
    # Basic coffee terms
    'coffee', 'bean', 'roast', 'brew', 'espresso',
    'latte', 'cappuccino', 'mocha', 'americano',
    
    # Species (from species_enum)
    'arabica', 'robusta', 'liberica', 'blend',
    'chicory', 'filter coffee mix',
    
    # Roast levels (from roast_level_enum)
    'light roast', 'light medium', 'medium roast', 
    'medium dark', 'dark roast',
    
    # Processing methods (from process_enum)
    'washed', 'natural', 'honey', 'pulped natural',
    'monsooned', 'wet hulled', 'anaerobic', 
    'carbonic maceration', 'double fermented', 'experimental',
    
    # Grind types (from grind_enum)
    'whole bean', 'filter grind', 'espresso grind', 'omni',
    'turkish', 'moka', 'cold brew', 'aeropress', 'channi',
    'french press', 'pour over', 'syphon', 'south indian filter',
    
    # Specialty coffee terms
    'specialty', 'speciality', 'single origin', 'micro lot',
    'green coffee', 'estate', 'plantation', 'organic',
    
    # Regional terms
    'coorg', 'karnataka', 'indian coffee', 'ethiopian',
    'colombian', 'brazilian', 'guatemalan', 'kenyan',
    
    # Product categories
    'ground coffee', 'coffee powder', 'instant coffee',
    'moka pot', 'turkish coffee', 'filter coffee',
    
    # Status terms (from coffee_status_enum)
    'active', 'seasonal', 'discontinued', 'coming soon',
    
    # Additional coffee terminology
    'cupping', 'tasting notes', 'flavor profile', 'aroma',
    'acidity', 'body', 'finish', 'aftertaste', 'balance'
]


async def execute_scraping_job(job_data: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute a scraping job with platform-based fetcher selection.
    
    Args:
        job_data: Job data containing roaster_id and job parameters
        config: Roaster-specific configuration
        
    Returns:
        Dict containing job execution results
    """
    job_id = job_data.get('id')
    roaster_id = job_data.get('roaster_id')
    job_type = job_data.get('data', {}).get('job_type', 'full_refresh')
    
    logger.info("Executing scraping job with platform-based fetcher selection", 
               job_id=job_id, 
               roaster_id=roaster_id, 
               job_type=job_type)
    
    try:
        # Create roaster configuration from job data and config
        roaster_config = RoasterConfigSchema(
            id=roaster_id,
            name=config.get('roaster_name', roaster_id),
            base_url=config.get('base_url', f'https://{roaster_id}.com'),
            platform=config.get('platform'),  # Use existing platform if available
            use_firecrawl_fallback=config.get('use_firecrawl_fallback', True),
            firecrawl_budget_limit=config.get('firecrawl_budget_limit', 10)
        )
        
        # Create fetcher configuration
        fetcher_config = FetcherConfig(
            timeout=config.get('timeout', 30.0),
            max_retries=config.get('max_retries', 3),
            retry_delay=config.get('retry_delay', 1.0),
            politeness_delay=config.get('politeness_delay', 0.25),
            jitter_range=config.get('jitter_range', 0.1),
            max_concurrent=config.get('max_concurrent', 3)
        )
        
        # Create Firecrawl configuration if needed
        firecrawl_config = None
        if config.get('use_firecrawl_fallback', True):
            firecrawl_config = FirecrawlConfig(
                api_key=config.get('FIRECRAWL_API_KEY', ''),
                base_url=config.get('FIRECRAWL_BASE_URL', 'https://api.firecrawl.dev'),
                budget_limit=config.get('firecrawl_budget_limit', 10),
                max_pages=config.get('FIRECRAWL_MAX_PAGES', 50),
                include_subdomains=config.get('FIRECRAWL_INCLUDE_SUBDOMAINS', False),
                sitemap_only=config.get('FIRECRAWL_SITEMAP_ONLY', False),
                coffee_keywords=config.get('FIRECRAWL_COFFEE_KEYWORDS', DEFAULT_COFFEE_KEYWORDS),
                timeout=config.get('FIRECRAWL_TIMEOUT', 30.0),
                max_retries=config.get('FIRECRAWL_MAX_RETRIES', 3),
                retry_delay=config.get('FIRECRAWL_RETRY_DELAY', 1.0),
                enable_monitoring=config.get('FIRECRAWL_ENABLE_MONITORING', True),
                log_level=config.get('FIRECRAWL_LOG_LEVEL', 'INFO')
            )
        
        # Create platform fetcher service
        platform_service = PlatformFetcherService(
            roaster_config=roaster_config,
            fetcher_config=fetcher_config,
            firecrawl_config=firecrawl_config
        )
        
        try:
            # Execute platform-based fetcher cascade
            # Remove job_type from data to avoid duplicate keyword argument
            job_data_dict = job_data.get('data', {}).copy()
            job_data_dict.pop('job_type', None)
            
            result = await platform_service.fetch_products_with_cascade(
                job_type=job_type,
                **job_data_dict
            )
            
            if result.success:
                logger.info("Platform-based scraping completed successfully", 
                           job_id=job_id, 
                           roaster_id=roaster_id,
                           platform=result.platform,
                           products_count=len(result.products))
                
                # Update platform field if successful fetcher was determined
                if result.should_update_platform:
                    await _update_roaster_platform(roaster_id, result.platform)
                
                return {
                    "status": "completed",
                    "job_type": job_type,
                    "roaster_id": roaster_id,
                    "platform": result.platform,
                    "processed_at": datetime.now(timezone.utc).isoformat(),
                    "items_processed": len(result.products),
                    "errors": 0
                }
            else:
                logger.error("Platform-based scraping failed", 
                           job_id=job_id, 
                           roaster_id=roaster_id,
                           error=result.error)
                
                return {
                    "status": "failed",
                    "job_type": job_type,
                    "roaster_id": roaster_id,
                    "processed_at": datetime.now(timezone.utc).isoformat(),
                    "items_processed": 0,
                    "errors": 1,
                    "error": result.error
                }
                
        finally:
            # Clean up platform service
            await platform_service.close()
        
    except Exception as e:
        logger.error("Scraping job failed", 
                    job_id=job_id, 
                    roaster_id=roaster_id,
                    error=str(e), 
                    exc_info=True)
        raise


async def _update_roaster_platform(roaster_id: str, platform: str) -> bool:
    """
    Update roaster platform field using RPC.
    
    Args:
        roaster_id: Roaster ID
        platform: Detected platform (shopify, woocommerce, custom, other)
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Import RPC client and Supabase client
        from ..validator.rpc_client import RPCClient
        from supabase import create_client, Client
        import os
        
        logger.info(
            "Updating roaster platform via RPC",
            roaster_id=roaster_id,
            platform=platform
        )
        
        # Get Supabase configuration from environment variables
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_ANON_KEY')
        
        if not supabase_url or not supabase_key:
            logger.error(
                "Missing Supabase configuration",
                roaster_id=roaster_id,
                platform=platform
            )
            return False
        
        # Create Supabase client
        supabase_client = create_client(supabase_url, supabase_key)
        
        # Create RPC client
        rpc_client = RPCClient(supabase_client)
        
        # Update roaster platform
        success = rpc_client.update_roaster_platform(roaster_id, platform)
        
        if success:
            logger.info(
                "Roaster platform updated successfully via RPC",
                roaster_id=roaster_id,
                platform=platform
            )
        else:
            logger.error(
                "Failed to update roaster platform via RPC",
                roaster_id=roaster_id,
                platform=platform
            )
        
        return success
        
    except Exception as e:
        logger.error(
            "Failed to update roaster platform via RPC",
            roaster_id=roaster_id,
            platform=platform,
            error=str(e)
        )
        return False




async def _simulate_full_refresh(roaster_id: str, config: Dict[str, Any]):
    """Simulate a full refresh scraping job with platform-based fetcher selection."""
    logger.info("Simulating full refresh with platform-based fetcher selection", roaster_id=roaster_id)
    
    # Simulate platform-based fetcher cascade
    platforms_to_try = ["shopify", "woocommerce", "firecrawl"]
    current_platform = config.get('platform')
    
    # If platform is known, try it first
    if current_platform and current_platform in platforms_to_try:
        platforms_to_try = [current_platform] + [p for p in platforms_to_try if p != current_platform]
    
    for platform in platforms_to_try:
        try:
            # Simulate platform-specific endpoints
            if platform == "shopify":
                endpoints = ["/products.json", "/collections.json"]
            elif platform == "woocommerce":
                endpoints = ["/wp-json/wc/store/products", "/wp-json/wc/store/products/categories"]
            else:  # firecrawl
                endpoints = ["/sitemap.xml", "/robots.txt"]
            
            logger.info(f"Simulating {platform} fetcher", roaster_id=roaster_id, platform=platform)
            
            # Simulate API calls with politeness delay
            for endpoint in endpoints:
                await asyncio.sleep(0.25)  # 250ms politeness
                logger.debug("Simulated API call", 
                           roaster_id=roaster_id, 
                           platform=platform,
                           endpoint=endpoint)
            
            # Simulate successful fetch
            logger.info(f"Simulated {platform} fetch successful", roaster_id=roaster_id, platform=platform)
            break  # Stop at first successful platform
            
        except Exception as e:
            logger.warning(f"Simulated {platform} fetch failed", 
                         roaster_id=roaster_id, 
                         platform=platform,
                         error=str(e))
            continue


async def _simulate_price_update(roaster_id: str, config: Dict[str, Any]):
    """Simulate a price-only update job with platform-based fetcher selection."""
    logger.info("Simulating price update with platform-based fetcher selection", roaster_id=roaster_id)
    
    # Simulate platform-based fetcher cascade for price updates
    platforms_to_try = ["shopify", "woocommerce", "firecrawl"]
    current_platform = config.get('platform')
    
    # If platform is known, try it first
    if current_platform and current_platform in platforms_to_try:
        platforms_to_try = [current_platform] + [p for p in platforms_to_try if p != current_platform]
    
    for platform in platforms_to_try:
        try:
            # Simulate platform-specific price endpoints
            if platform == "shopify":
                endpoints = ["/products.json?fields=id,title,price"]
            elif platform == "woocommerce":
                endpoints = ["/wp-json/wc/store/products?per_page=100"]
            else:  # firecrawl
                endpoints = ["/products", "/shop"]
            
            logger.info(f"Simulating {platform} price update", roaster_id=roaster_id, platform=platform)
            
            # Simulate API calls with shorter politeness delay for price updates
            for endpoint in endpoints:
                await asyncio.sleep(0.1)  # Shorter delay for price updates
                logger.debug("Simulated price API call", 
                           roaster_id=roaster_id, 
                           platform=platform,
                           endpoint=endpoint)
            
            # Simulate successful price fetch
            logger.info(f"Simulated {platform} price update successful", roaster_id=roaster_id, platform=platform)
            break  # Stop at first successful platform
            
        except Exception as e:
            logger.warning(f"Simulated {platform} price update failed", 
                         roaster_id=roaster_id, 
                         platform=platform,
                         error=str(e))
            continue


async def _validate_job_data(job_data: Dict[str, Any]) -> bool:
    """Validate job data before execution."""
    required_fields = ['id', 'roaster_id']
    
    for field in required_fields:
        if field not in job_data:
            logger.error("Missing required field", field=field, job_data=job_data)
            return False
    
    return True



async def execute_firecrawl_map_job(job_data: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute a Firecrawl map discovery job as automatic fallback when standard fetchers fail.
    
    This job is now triggered automatically when Shopify/WooCommerce fetchers fail,
    providing intelligent fallback for roasters without standard API endpoints.
    
    Args:
        job_data: Job data containing roaster_id and job parameters
        config: Roaster-specific configuration
        
    Returns:
        Dict containing job execution results
    """
    job_id = job_data.get('id')
    roaster_id = job_data.get('roaster_id')
    job_type = job_data.get('data', {}).get('job_type', 'firecrawl_map')
    fallback_reason = job_data.get('data', {}).get('fallback_reason', 'standard_fetchers_failed')
    
    logger.info("Executing Firecrawl map job as automatic fallback", 
               job_id=job_id, 
               roaster_id=roaster_id, 
               job_type=job_type,
               fallback_reason=fallback_reason)
    
    try:
        # Create Firecrawl configuration with realistic budget limits
        # Use roaster-specific budget limit from config
        roaster_budget = config.get('firecrawl_budget_limit', 10)  # Realistic $5-10 budget
        
        firecrawl_config = FirecrawlConfig(
            api_key=config.get('FIRECRAWL_API_KEY', ''),
            base_url=config.get('FIRECRAWL_BASE_URL', 'https://api.firecrawl.dev'),
            budget_limit=roaster_budget,  # Use roaster-specific budget
            max_pages=config.get('FIRECRAWL_MAX_PAGES', 50),
            include_subdomains=config.get('FIRECRAWL_INCLUDE_SUBDOMAINS', False),
            sitemap_only=config.get('FIRECRAWL_SITEMAP_ONLY', False),
            coffee_keywords=config.get('FIRECRAWL_COFFEE_KEYWORDS', DEFAULT_COFFEE_KEYWORDS),
            timeout=config.get('FIRECRAWL_TIMEOUT', 30.0),
            max_retries=config.get('FIRECRAWL_MAX_RETRIES', 3),
            retry_delay=config.get('FIRECRAWL_RETRY_DELAY', 1.0),
            enable_monitoring=config.get('FIRECRAWL_ENABLE_MONITORING', True),
            log_level=config.get('FIRECRAWL_LOG_LEVEL', 'INFO')
        )
        
        # Initialize Firecrawl services
        firecrawl_client = FirecrawlClient(firecrawl_config)
        firecrawl_map_service = FirecrawlMapService(firecrawl_client)
        
        # Create roaster config with platform-aware settings
        roaster_config = RoasterConfigSchema(
            id=roaster_id,
            name=config.get('roaster_name', roaster_id),
            base_url=config.get('base_url', f'https://{roaster_id}.com'),
            platform=config.get('platform'),  # Include platform for context
            use_firecrawl_fallback=True,  # Always enabled for fallback jobs
            firecrawl_budget_limit=roaster_budget
        )
        
        # Execute Firecrawl map discovery as fallback with Epic B job type support
        result = await firecrawl_map_service.discover_roaster_products(
            roaster_config=roaster_config,
            search_terms=job_data.get('data', {}).get('search_terms'),
            job_type=job_data.get('data', {}).get('job_type', 'full_refresh')
        )
        
        # Log fallback success
        logger.info("Firecrawl fallback map job completed successfully", 
                   job_id=job_id, 
                   roaster_id=roaster_id,
                   discovered_urls=len(result.get('discovered_urls', [])),
                   status=result.get('status'),
                   fallback_reason=fallback_reason)
        
        return {
            "status": "completed",
            "job_type": job_type,
            "roaster_id": roaster_id,
            "fallback_reason": fallback_reason,
            "processed_at": datetime.now(timezone.utc).isoformat(),
            "discovered_urls": result.get('discovered_urls', []),
            "total_discovered": len(result.get('discovered_urls', [])),
            "firecrawl_status": result.get('status'),
            "budget_used": firecrawl_client.get_usage_stats()['current_usage'],
            "errors": 0 if result.get('status') == 'success' else 1
        }
        
    except Exception as e:
        logger.error("Firecrawl fallback map job failed", 
                    job_id=job_id, 
                    roaster_id=roaster_id,
                    fallback_reason=fallback_reason,
                    error=str(e), 
                    exc_info=True)
        raise


async def execute_firecrawl_batch_map_job(job_data: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute a Firecrawl batch map discovery job for multiple roasters as automatic fallback.
    
    This job is now triggered automatically when standard fetchers fail for multiple roasters,
    providing intelligent batch fallback for roasters without standard API endpoints.
    
    Args:
        job_data: Job data containing roaster_ids and job parameters
        config: Global configuration
        
    Returns:
        Dict containing batch job execution results
    """
    job_id = job_data.get('id')
    roaster_ids = job_data.get('data', {}).get('roaster_ids', [])
    job_type = job_data.get('data', {}).get('job_type', 'firecrawl_batch_map')
    fallback_reason = job_data.get('data', {}).get('fallback_reason', 'standard_fetchers_failed')
    
    logger.info("Executing Firecrawl batch map job as automatic fallback", 
               job_id=job_id, 
               roaster_ids=roaster_ids, 
               job_type=job_type,
               fallback_reason=fallback_reason)
    
    try:
        # Create Firecrawl configuration for batch fallback operations
        # Use realistic budget limits for batch fallback operations
        batch_budget = config.get('FIRECRAWL_BATCH_BUDGET_LIMIT', 50)  # Realistic batch budget
        
        firecrawl_config = FirecrawlConfig(
            api_key=config.get('FIRECRAWL_API_KEY', ''),
            base_url=config.get('FIRECRAWL_BASE_URL', 'https://api.firecrawl.dev'),
            budget_limit=batch_budget,  # Realistic batch budget
            max_pages=config.get('FIRECRAWL_MAX_PAGES', 100),  # Reasonable for batch
            include_subdomains=config.get('FIRECRAWL_INCLUDE_SUBDOMAINS', True),  # More comprehensive for fallback
            sitemap_only=config.get('FIRECRAWL_SITEMAP_ONLY', False),
            coffee_keywords=config.get('FIRECRAWL_COFFEE_KEYWORDS', DEFAULT_COFFEE_KEYWORDS),
            timeout=config.get('FIRECRAWL_TIMEOUT', 30.0),
            max_retries=config.get('FIRECRAWL_MAX_RETRIES', 3),
            retry_delay=config.get('FIRECRAWL_RETRY_DELAY', 1.0),
            enable_monitoring=config.get('FIRECRAWL_ENABLE_MONITORING', True),
            log_level=config.get('FIRECRAWL_LOG_LEVEL', 'INFO')
        )
        
        # Initialize Firecrawl services
        firecrawl_client = FirecrawlClient(firecrawl_config)
        firecrawl_map_service = FirecrawlMapService(firecrawl_client)
        
        # Create roaster configs with platform-aware settings for fallback
        roaster_configs = []
        for roaster_id in roaster_ids:
            # Get roaster-specific budget or use default
            roaster_budget = config.get('roaster_budgets', {}).get(roaster_id, 10)
            
            roaster_config = RoasterConfigSchema(
                id=roaster_id,
                name=config.get('roaster_names', {}).get(roaster_id, roaster_id),
                base_url=config.get('roaster_urls', {}).get(roaster_id, f'https://{roaster_id}.com'),
                platform=config.get('roaster_platforms', {}).get(roaster_id),  # Include platform context
                use_firecrawl_fallback=True,  # Always enabled for fallback jobs
                firecrawl_budget_limit=roaster_budget
            )
            roaster_configs.append(roaster_config)
        
        # Execute batch Firecrawl map discovery as fallback
        result = await firecrawl_map_service.batch_discover_products(
            roaster_configs=roaster_configs,
            search_terms=job_data.get('data', {}).get('search_terms')
        )
        
        # Log fallback batch success
        logger.info("Firecrawl fallback batch map job completed successfully", 
                   job_id=job_id, 
                   roaster_count=len(roaster_ids),
                   successful_discoveries=result.get('successful_discoveries', 0),
                   total_urls_discovered=result.get('total_urls_discovered', 0),
                   fallback_reason=fallback_reason)
        
        return {
            "status": "completed",
            "job_type": job_type,
            "roaster_count": len(roaster_ids),
            "fallback_reason": fallback_reason,
            "processed_at": datetime.now(timezone.utc).isoformat(),
            "successful_discoveries": result.get('successful_discoveries', 0),
            "total_urls_discovered": result.get('total_urls_discovered', 0),
            "batch_results": result.get('results', []),
            "budget_used": firecrawl_client.get_usage_stats()['current_usage'],
            "errors": len(roaster_ids) - result.get('successful_discoveries', 0)
        }
        
    except Exception as e:
        logger.error("Firecrawl fallback batch map job failed", 
                    job_id=job_id, 
                    roaster_ids=roaster_ids,
                    fallback_reason=fallback_reason,
                    error=str(e), 
                    exc_info=True)
        raise


async def queue_firecrawl_extract_jobs(discovered_urls: List[str], roaster_id: str, job_queue) -> List[str]:
    """
    Queue Firecrawl extract jobs for discovered URLs.
    
    Args:
        discovered_urls: List of URLs discovered by map operation
        roaster_id: Roaster ID for the URLs
        job_queue: Job queue instance
        
    Returns:
        List of queued job IDs
    """
    job_ids = []
    
    for url in discovered_urls:
        try:
            # Create extract job data
            extract_job_data = {
                'roaster_id': roaster_id,
                'url': url,
                'job_type': 'firecrawl_extract',
                'source': 'firecrawl_map_discovery',
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            
            # Queue the extract job
            job_id = await job_queue.enqueue('firecrawl_extract', extract_job_data)
            job_ids.append(job_id)
            
            logger.info("Queued Firecrawl extract job", 
                       job_id=job_id, 
                       roaster_id=roaster_id, 
                       url=url)
            
        except Exception as e:
            logger.error("Failed to queue Firecrawl extract job", 
                        roaster_id=roaster_id, 
                        url=url, 
                        error=str(e))
    
    logger.info("Queued Firecrawl extract jobs", 
               roaster_id=roaster_id, 
               total_urls=len(discovered_urls), 
               queued_jobs=len(job_ids))
    
    return job_ids
