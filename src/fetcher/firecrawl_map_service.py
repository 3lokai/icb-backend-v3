"""
Firecrawl map service for product URL discovery.

This service integrates with the existing A.1-A.5 pipeline architecture:
- A.1 Worker Scaffolding: Firecrawl jobs integrated with existing job queue
- A.2 Fetcher Service: Firecrawl map as fallback when JSON endpoints fail
- A.3 Artifact Validation: Firecrawl output validated against existing schema
- A.4 RPC Integration: Firecrawl artifacts processed through existing RPC pipeline
- A.5 Coffee Classification: Firecrawl products classified using existing logic
"""

import asyncio
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone
import json

from structlog import get_logger

from .firecrawl_client import FirecrawlClient, FirecrawlError, FirecrawlBudgetExceededError
from ..config.firecrawl_config import FirecrawlConfig
from ..config.roaster_schema import RoasterConfigSchema

logger = get_logger(__name__)


class FirecrawlMapService:
    """
    Firecrawl map service for discovering product URLs.
    
    This service follows the A.1-A.5 pipeline patterns:
    - Integrates with existing job queue system
    - Provides fallback when standard fetchers fail
    - Validates output against existing schema
    - Integrates with RPC pipeline for data processing
    """
    
    def __init__(self, firecrawl_client: FirecrawlClient):
        self.client = firecrawl_client
        self.config = firecrawl_client.config
        
        logger.info(
            "FirecrawlMapService initialized",
            budget_limit=self.config.budget_limit,
            max_pages=self.config.max_pages
        )
    
    async def discover_roaster_products(
        self, 
        roaster_config: RoasterConfigSchema,
        search_terms: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Discover product URLs for a roaster using Firecrawl map.
        
        Args:
            roaster_config: Roaster configuration
            search_terms: Optional search terms to filter URLs
            
        Returns:
            Dictionary containing discovered URLs and metadata
        """
        if not roaster_config.use_firecrawl_fallback:
            logger.info(
                "Firecrawl fallback disabled for roaster",
                roaster_id=roaster_config.id
            )
            return {
                'roaster_id': roaster_config.id,
                'discovered_urls': [],
                'status': 'disabled',
                'message': 'Firecrawl fallback disabled for this roaster'
            }
        
        # Check budget limits
        if not self.client.budget_tracker.can_operate():
            logger.warning(
                "Budget limit exceeded, cannot discover products",
                roaster_id=roaster_config.id,
                current_usage=self.client.budget_tracker.current_usage,
                budget_limit=self.config.budget_limit
            )
            return {
                'roaster_id': roaster_config.id,
                'discovered_urls': [],
                'status': 'budget_exceeded',
                'message': 'Firecrawl budget limit exceeded'
            }
        
        # Prepare search terms
        if not search_terms:
            search_terms = self.config.coffee_keywords
        
        # Add roaster-specific terms if available
        if hasattr(roaster_config, 'name') and roaster_config.name:
            search_terms = search_terms + [roaster_config.name.lower()]
        
        logger.info(
            "Starting product discovery for roaster",
            roaster_id=roaster_config.id,
            roaster_name=getattr(roaster_config, 'name', 'Unknown'),
            search_terms=search_terms,
            budget_remaining=self.client.budget_tracker.get_usage_stats()['remaining_budget']
        )
        
        try:
            # Discover product URLs
            discovered_urls = await self.client.discover_product_urls(
                domain=roaster_config.base_url or f"https://{roaster_config.id}.com",
                search_terms=search_terms
            )
            
            # Validate and filter URLs
            validated_urls = self._validate_product_urls(discovered_urls, roaster_config)
            
            # Create result
            result = {
                'roaster_id': roaster_config.id,
                'roaster_name': getattr(roaster_config, 'name', 'Unknown'),
                'discovered_urls': validated_urls,
                'total_discovered': len(discovered_urls),
                'validated_count': len(validated_urls),
                'status': 'success',
                'discovery_timestamp': datetime.now(timezone.utc).isoformat(),
                'budget_used': self.client.budget_tracker.current_usage,
                'search_terms': search_terms
            }
            
            logger.info(
                "Product discovery completed",
                roaster_id=roaster_config.id,
                total_discovered=len(discovered_urls),
                validated_count=len(validated_urls),
                budget_used=self.client.budget_tracker.current_usage
            )
            
            return result
            
        except FirecrawlBudgetExceededError:
            logger.error(
                "Budget exceeded during product discovery",
                roaster_id=roaster_config.id
            )
            return {
                'roaster_id': roaster_config.id,
                'discovered_urls': [],
                'status': 'budget_exceeded',
                'message': 'Firecrawl budget limit exceeded during discovery'
            }
            
        except Exception as e:
            logger.error(
                "Product discovery failed",
                roaster_id=roaster_config.id,
                error=str(e),
                error_type=type(e).__name__
            )
            return {
                'roaster_id': roaster_config.id,
                'discovered_urls': [],
                'status': 'error',
                'message': f'Discovery failed: {str(e)}'
            }
    
    def _validate_product_urls(
        self, 
        urls: List[str], 
        roaster_config: RoasterConfigSchema
    ) -> List[str]:
        """Validate and filter product URLs."""
        validated_urls = []
        
        for url in urls:
            try:
                # Basic URL validation
                if not self._is_valid_url(url):
                    continue
                
                # Domain validation
                if not self._is_same_domain(url, roaster_config.base_url):
                    continue
                
                # Product URL validation
                if not self._is_likely_product_url(url):
                    continue
                
                validated_urls.append(url)
                
            except Exception as e:
                logger.warning(
                    "URL validation failed",
                    url=url,
                    error=str(e)
                )
                continue
        
        return validated_urls
    
    def _is_valid_url(self, url: str) -> bool:
        """Check if URL is valid."""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            return bool(parsed.scheme and parsed.netloc)
        except Exception:
            return False
    
    def _is_same_domain(self, url: str, base_url: str) -> bool:
        """Check if URL is from the same domain."""
        try:
            from urllib.parse import urlparse
            url_domain = urlparse(url).netloc
            base_domain = urlparse(base_url).netloc
            return url_domain == base_domain
        except Exception:
            return False
    
    def _is_likely_product_url(self, url: str) -> bool:
        """Check if URL is likely a product page."""
        import re
        
        # Product URL patterns
        product_patterns = [
            r'/product/', r'/products/', r'/shop/', r'/store/',
            r'/item/', r'/coffee/', r'/beans/', r'/roast/',
            r'\.html$', r'\.php$', r'\.asp$', r'\.aspx$'
        ]
        
        # Exclude non-product patterns
        exclude_patterns = [
            r'/about', r'/contact', r'/blog', r'/news',
            r'/help', r'/support', r'/faq', r'/terms',
            r'/privacy', r'/shipping', r'/returns',
            r'/cart', r'/checkout', r'/account'
        ]
        
        url_lower = url.lower()
        
        # Skip if matches exclude patterns
        if any(re.search(pattern, url_lower) for pattern in exclude_patterns):
            return False
        
        # Include if matches product patterns
        return any(re.search(pattern, url_lower) for pattern in product_patterns)
    
    async def batch_discover_products(
        self, 
        roaster_configs: List[RoasterConfigSchema],
        search_terms: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Discover product URLs for multiple roasters in batch.
        
        Args:
            roaster_configs: List of roaster configurations
            search_terms: Optional search terms to filter URLs
            
        Returns:
            Dictionary containing batch results
        """
        logger.info(
            "Starting batch product discovery",
            roaster_count=len(roaster_configs),
            search_terms=search_terms
        )
        
        results = []
        successful_discoveries = 0
        total_urls_discovered = 0
        
        for roaster_config in roaster_configs:
            try:
                result = await self.discover_roaster_products(roaster_config, search_terms)
                results.append(result)
                
                if result['status'] == 'success':
                    successful_discoveries += 1
                    total_urls_discovered += len(result['discovered_urls'])
                
            except Exception as e:
                logger.error(
                    "Batch discovery failed for roaster",
                    roaster_id=roaster_config.id,
                    error=str(e)
                )
                results.append({
                    'roaster_id': roaster_config.id,
                    'discovered_urls': [],
                    'status': 'error',
                    'message': f'Batch discovery failed: {str(e)}'
                })
        
        batch_result = {
            'batch_timestamp': datetime.now(timezone.utc).isoformat(),
            'total_roasters': len(roaster_configs),
            'successful_discoveries': successful_discoveries,
            'total_urls_discovered': total_urls_discovered,
            'results': results,
            'budget_usage': self.client.budget_tracker.get_usage_stats()
        }
        
        logger.info(
            "Batch product discovery completed",
            total_roasters=len(roaster_configs),
            successful_discoveries=successful_discoveries,
            total_urls_discovered=total_urls_discovered,
            budget_usage=self.client.budget_tracker.current_usage
        )
        
        return batch_result
    
    async def get_service_status(self) -> Dict[str, Any]:
        """Get service status and health information."""
        try:
            # Check client health
            is_healthy = await self.client.health_check()
            
            # Get usage statistics
            usage_stats = self.client.get_usage_stats()
            
            return {
                'service': 'FirecrawlMapService',
                'status': 'healthy' if is_healthy else 'unhealthy',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'budget_usage': usage_stats,
                'configuration': {
                    'max_pages': self.config.max_pages,
                    'include_subdomains': self.config.include_subdomains,
                    'sitemap_only': self.config.sitemap_only,
                    'coffee_keywords': self.config.coffee_keywords
                }
            }
            
        except Exception as e:
            logger.error("Failed to get service status", error=str(e))
            return {
                'service': 'FirecrawlMapService',
                'status': 'error',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'error': str(e)
            }
