"""
Fetcher factory for creating platform-specific fetchers.
"""

from typing import Optional, Dict, Any
from structlog import get_logger

from .base_fetcher import BaseFetcher, FetcherConfig
from .shopify_fetcher import ShopifyFetcher
from .woocommerce_fetcher import WooCommerceFetcher
from ..config.fetcher_config import SourceConfig, RoasterConfig

logger = get_logger(__name__)


def create_fetcher(
    source_config: SourceConfig,
    roaster_config: RoasterConfig,
    auth_credentials: Optional[Dict[str, str]] = None,
) -> BaseFetcher:
    """
    Create a platform-specific fetcher based on configuration.
    
    Args:
        source_config: Product source configuration
        roaster_config: Roaster-specific configuration
        auth_credentials: Authentication credentials (API keys, tokens, etc.)
        
    Returns:
        Platform-specific fetcher instance
    """
    # Create base fetcher configuration
    fetcher_config = FetcherConfig(
        timeout=roaster_config.timeout,
        max_retries=roaster_config.max_retries,
        politeness_delay=roaster_config.politeness_delay,
        max_concurrent=roaster_config.default_concurrency,
    )
    
    # Extract authentication credentials
    auth_credentials = auth_credentials or {}
    
    if source_config.platform == "shopify":
        api_key = auth_credentials.get('api_key') or auth_credentials.get('access_token')
        
        fetcher = ShopifyFetcher(
            config=fetcher_config,
            roaster_id=source_config.roaster_id,
            base_url=source_config.base_url,
            api_key=api_key,
        )
        
        logger.info(
            "Created Shopify fetcher",
            roaster_id=source_config.roaster_id,
            base_url=source_config.base_url,
            has_api_key=bool(api_key),
        )
        
        return fetcher
    
    elif source_config.platform == "woocommerce":
        consumer_key = auth_credentials.get('consumer_key')
        consumer_secret = auth_credentials.get('consumer_secret')
        jwt_token = auth_credentials.get('jwt_token')
        
        fetcher = WooCommerceFetcher(
            config=fetcher_config,
            roaster_id=source_config.roaster_id,
            base_url=source_config.base_url,
            consumer_key=consumer_key,
            consumer_secret=consumer_secret,
            jwt_token=jwt_token,
        )
        
        logger.info(
            "Created WooCommerce fetcher",
            roaster_id=source_config.roaster_id,
            base_url=source_config.base_url,
            has_consumer_key=bool(consumer_key),
            has_jwt_token=bool(jwt_token),
        )
        
        return fetcher
    
    else:
        raise ValueError(
            f"Unsupported platform: {source_config.platform}. "
            f"Supported platforms: shopify, woocommerce"
        )


async def create_fetcher_from_source_id(
    source_id: str,
    auth_credentials: Optional[Dict[str, str]] = None,
) -> BaseFetcher:
    """
    Create a fetcher from a source ID by loading configuration from database.
    
    Args:
        source_id: Product source ID
        auth_credentials: Authentication credentials
        
    Returns:
        Configured fetcher instance
    """
    from ..config.fetcher_config import config_manager
    
    # Load source and roaster configuration
    source_config = await config_manager.get_source_config(source_id)
    roaster_config = await config_manager.get_roaster_config(source_config.roaster_id)
    
    # Create fetcher
    return create_fetcher(source_config, roaster_config, auth_credentials)
