"""
Firecrawl client service for map discovery and URL extraction.

This module provides:
- Firecrawl API client with authentication
- Map discovery functionality
- URL filtering and validation
- Error handling and retry logic
- Budget tracking and rate limiting
"""

import asyncio
import time
from typing import Dict, List, Optional, Any, Tuple
from urllib.parse import urlparse, urljoin
import re

from firecrawl import FirecrawlApp
from structlog import get_logger

from ..config.firecrawl_config import FirecrawlConfig, FirecrawlBudgetTracker
from ..monitoring.firecrawl_metrics import FirecrawlMetrics, FirecrawlAlertManager

logger = get_logger(__name__)


class FirecrawlError(Exception):
    """Base exception for Firecrawl operations."""
    pass


class FirecrawlAPIError(FirecrawlError):
    """Exception raised for Firecrawl API errors."""
    pass


class FirecrawlBudgetExceededError(FirecrawlError):
    """Exception raised when budget limit is exceeded."""
    pass


class FirecrawlRateLimitError(FirecrawlError):
    """Exception raised when rate limit is exceeded."""
    pass


class FirecrawlClient:
    """
    Firecrawl client service with authentication, rate limiting, and budget tracking.
    
    Features:
    - Map discovery for product URLs
    - URL filtering for coffee-related content
    - Budget tracking and rate limiting
    - Error handling and retry logic
    - Comprehensive logging and monitoring
    """
    
    def __init__(self, config: FirecrawlConfig):
        self.config = config
        self.budget_tracker = FirecrawlBudgetTracker(config)
        self.last_request_time = 0
        self.request_count = 0
        self.request_window_start = time.time()
        
        # Initialize monitoring
        self.metrics = FirecrawlMetrics()
        self.alert_manager = FirecrawlAlertManager(self.metrics)
        
        # Initialize Firecrawl app
        self.app = FirecrawlApp(api_key=config.api_key)
        
        logger.info(
            "Firecrawl client initialized",
            api_key_masked=config.api_key[:8] + "..." if config.api_key else "None",
            base_url=config.base_url,
            budget_limit=config.budget_limit,
            max_pages=config.max_pages
        )
    
    async def _apply_rate_limit(self):
        """Apply rate limiting between requests."""
        current_time = time.time()
        
        # Reset window if needed
        if current_time - self.request_window_start >= 60:  # 1 minute window
            self.request_count = 0
            self.request_window_start = current_time
        
        # Check if we're within rate limit
        if self.request_count >= self.config.rate_limit_per_minute:
            sleep_time = 60 - (current_time - self.request_window_start)
            if sleep_time > 0:
                logger.warning(
                    "Rate limit reached, sleeping",
                    sleep_time=sleep_time,
                    request_count=self.request_count,
                    rate_limit=self.config.rate_limit_per_minute
                )
                await asyncio.sleep(sleep_time)
                self.request_count = 0
                self.request_window_start = time.time()
        
        # Apply minimum delay between requests
        time_since_last = current_time - self.last_request_time
        min_delay = 60.0 / self.config.rate_limit_per_minute
        
        if time_since_last < min_delay:
            sleep_time = min_delay - time_since_last
            await asyncio.sleep(sleep_time)
        
        self.last_request_time = time.time()
        self.request_count += 1
    
    async def _make_request_with_retry(self, operation_name: str, operation_func, *args, **kwargs):
        """Make a request with retry logic and error handling."""
        for attempt in range(self.config.max_retries + 1):
            try:
                # Check budget before operation
                if not self.budget_tracker.can_operate():
                    raise FirecrawlBudgetExceededError(
                        f"Budget limit exceeded: {self.budget_tracker.current_usage}/{self.config.budget_limit}"
                    )
                
                # Apply rate limiting
                await self._apply_rate_limit()
                
                # Execute operation
                logger.debug(
                    f"Executing {operation_name}",
                    attempt=attempt + 1,
                    max_retries=self.config.max_retries
                )
                
                result = await operation_func(*args, **kwargs)
                
                # Record successful operation
                self.budget_tracker.record_operation()
                
                logger.info(
                    f"{operation_name} successful",
                    attempt=attempt + 1,
                    budget_usage=self.budget_tracker.current_usage
                )
                
                return result
                
            except FirecrawlBudgetExceededError:
                logger.error(f"{operation_name} failed: Budget exceeded")
                raise
                
            except Exception as e:
                logger.warning(
                    f"{operation_name} failed",
                    attempt=attempt + 1,
                    error=str(e),
                    error_type=type(e).__name__
                )
                
                if attempt < self.config.max_retries:
                    delay = self.config.retry_delay * (2 ** attempt)
                    logger.info(f"Retrying {operation_name} in {delay}s")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"{operation_name} failed after {self.config.max_retries} retries")
                    raise FirecrawlAPIError(f"{operation_name} failed: {e}")
    
    async def map_domain(self, domain: str, search_terms: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Map a domain to discover product URLs.
        
        Args:
            domain: Domain to map (e.g., "example.com")
            search_terms: Optional search terms to filter URLs
            
        Returns:
            Dictionary containing discovered URLs and metadata
        """
        start_time = time.time()
        operation_success = False
        urls_discovered = 0
        budget_used = 0
        error_type = None
        
        try:
            # Ensure domain has protocol
            if not domain.startswith(('http://', 'https://')):
                domain = f"https://{domain}"
            
            # Prepare search terms
            search_terms = search_terms or self.config.search_terms
            if not search_terms:
                search_terms = self.config.coffee_keywords
            
            # Prepare parameters
            params = {
                "max_pages": self.config.max_pages,
                "include_subdomains": self.config.include_subdomains,
                "sitemap_only": self.config.sitemap_only
            }
            
            if search_terms:
                params["search"] = " ".join(search_terms)
            
            logger.info(
                "Starting domain mapping",
                domain=domain,
                search_terms=search_terms,
                max_pages=self.config.max_pages,
                budget_remaining=self.budget_tracker.get_usage_stats()['remaining_budget']
            )
            
            async def _map_operation():
                return self.app.map_url(url=domain, params=params)
            
            result = await self._make_request_with_retry("map_domain", _map_operation)
            
            # Process and filter results
            processed_result = self._process_map_result(result, domain)
            
            # Update metrics
            operation_success = True
            urls_discovered = len(processed_result.get('filtered_urls', []))
            budget_used = self.budget_tracker.current_usage
            
            logger.info(
                "Domain mapping completed",
                domain=domain,
                total_links=len(result.get('links', [])),
                filtered_links=len(processed_result.get('filtered_urls', [])),
                coffee_links=len(processed_result.get('coffee_urls', []))
            )
            
            return processed_result
            
        except Exception as e:
            error_type = type(e).__name__
            logger.error(
                "Domain mapping failed",
                domain=domain,
                error=str(e),
                error_type=error_type
            )
            raise
            
        finally:
            # Record metrics
            operation_time = time.time() - start_time
            self.metrics.record_map_operation(
                roaster_id=domain,  # Using domain as roaster_id for now
                operation_type='map_domain',
                success=operation_success,
                urls_discovered=urls_discovered,
                budget_used=budget_used,
                operation_time=operation_time,
                error_type=error_type
            )
            
            # Check for alerts
            alerts = self.alert_manager.check_alerts()
            if alerts:
                logger.warning("Firecrawl alerts triggered", alerts=alerts)
    
    def _process_map_result(self, result: Dict[str, Any], domain: str) -> Dict[str, Any]:
        """Process and filter map results."""
        links = result.get('links', [])
        
        # Filter URLs by domain
        domain_urls = []
        for link in links:
            try:
                parsed = urlparse(link)
                if parsed.netloc == urlparse(domain).netloc:
                    domain_urls.append(link)
            except Exception as e:
                logger.warning("Invalid URL in map result", url=link, error=str(e))
        
        # Filter for coffee-related URLs
        coffee_urls = self._filter_coffee_urls(domain_urls)
        
        # Filter for product URLs
        product_urls = self._filter_product_urls(domain_urls)
        
        return {
            'domain': domain,
            'total_links': len(links),
            'domain_urls': domain_urls,
            'filtered_urls': domain_urls,
            'coffee_urls': coffee_urls,
            'product_urls': product_urls,
            'metadata': {
                'mapping_timestamp': time.time(),
                'budget_used': self.budget_tracker.current_usage,
                'search_terms': self.config.search_terms,
                'coffee_keywords': self.config.coffee_keywords
            }
        }
    
    def _filter_coffee_urls(self, urls: List[str]) -> List[str]:
        """Filter URLs for coffee-related content."""
        coffee_urls = []
        coffee_patterns = [
            r'coffee', r'bean', r'roast', r'brew', r'espresso',
            r'latte', r'cappuccino', r'mocha', r'americano',
            r'single.origin', r'blend', r'organic', r'fair.trade'
        ]
        
        for url in urls:
            url_lower = url.lower()
            if any(re.search(pattern, url_lower) for pattern in coffee_patterns):
                coffee_urls.append(url)
        
        return coffee_urls
    
    def _filter_product_urls(self, urls: List[str]) -> List[str]:
        """Filter URLs that appear to be product pages."""
        product_urls = []
        product_patterns = [
            r'/product/', r'/products/', r'/shop/', r'/store/',
            r'/item/', r'/coffee/', r'/beans/', r'/roast/',
            r'\.html$', r'\.php$', r'\.asp$', r'\.aspx$'
        ]
        
        # Exclude common non-product pages
        exclude_patterns = [
            r'/about', r'/contact', r'/blog', r'/news',
            r'/help', r'/support', r'/faq', r'/terms',
            r'/privacy', r'/shipping', r'/returns'
        ]
        
        for url in urls:
            url_lower = url.lower()
            
            # Skip if matches exclude patterns
            if any(re.search(pattern, url_lower) for pattern in exclude_patterns):
                continue
            
            # Include if matches product patterns
            if any(re.search(pattern, url_lower) for pattern in product_patterns):
                product_urls.append(url)
        
        return product_urls
    
    async def discover_product_urls(
        self, 
        domain: str, 
        search_terms: Optional[List[str]] = None
    ) -> List[str]:
        """
        Discover product URLs for a domain.
        
        Args:
            domain: Domain to discover URLs for
            search_terms: Optional search terms to filter URLs
            
        Returns:
            List of discovered product URLs
        """
        result = await self.map_domain(domain, search_terms)
        
        # Combine coffee URLs and product URLs, removing duplicates
        all_urls = list(set(result.get('coffee_urls', []) + result.get('product_urls', [])))
        
        logger.info(
            "Product URL discovery completed",
            domain=domain,
            total_discovered=len(all_urls),
            coffee_urls=len(result.get('coffee_urls', [])),
            product_urls=len(result.get('product_urls', []))
        )
        
        return all_urls
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """Get current usage statistics."""
        return self.budget_tracker.get_usage_stats()
    
    def reset_budget(self):
        """Reset budget tracking."""
        self.budget_tracker.reset()
        logger.info("Firecrawl budget reset")
    
    async def health_check(self) -> bool:
        """Check if Firecrawl service is healthy."""
        try:
            # Try a simple map operation with a known domain
            test_result = await self.map_domain("https://example.com", ["test"])
            return True
        except Exception as e:
            logger.error("Firecrawl health check failed", error=str(e))
            return False
    
    def get_monitoring_metrics(self) -> Dict[str, Any]:
        """Get comprehensive monitoring metrics."""
        return self.metrics.export_metrics()
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get health status with metrics."""
        health = self.metrics.get_health_status()
        budget_stats = self.budget_tracker.get_usage_stats()
        
        return {
            **health,
            'budget_usage': budget_stats,
            'configuration': {
                'max_pages': self.config.max_pages,
                'include_subdomains': self.config.include_subdomains,
                'sitemap_only': self.config.sitemap_only,
                'coffee_keywords': self.config.coffee_keywords
            }
        }
    
    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get currently active alerts."""
        return self.alert_manager.get_active_alerts()
    
    def reset_monitoring(self):
        """Reset monitoring metrics and alerts."""
        self.metrics.reset_metrics()
        self.alert_manager.clear_alerts()
        logger.info("Firecrawl monitoring reset")
