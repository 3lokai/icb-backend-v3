"""
RPC client wrapper for Supabase RPC calls with error handling and retry logic.
"""

import time
import json
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from enum import Enum

from structlog import get_logger

logger = get_logger(__name__)


class RPCError(Exception):
    """Base exception for RPC errors."""
    pass


class RPCConstraintError(RPCError):
    """Exception for database constraint violations."""
    pass


class RPCNetworkError(RPCError):
    """Exception for network-related RPC errors."""
    pass


class RPCValidationError(RPCError):
    """Exception for RPC parameter validation errors."""
    pass


class RPCClient:
    """
    RPC client wrapper for Supabase RPC calls.
    
    Features:
    - Error handling for RPC failures and database constraints
    - Retry logic with exponential backoff
    - Comprehensive logging for RPC call success/failure
    - Support for all coffee pipeline RPC functions
    """
    
    def __init__(self, supabase_client, max_retries: int = 3, base_delay: float = 1.0):
        """
        Initialize RPC client.
        
        Args:
            supabase_client: Supabase client for RPC calls
            max_retries: Maximum number of retry attempts
            base_delay: Base delay in seconds for exponential backoff
        """
        self.supabase_client = supabase_client
        self.max_retries = max_retries
        self.base_delay = base_delay
        
        # RPC call statistics
        self.rpc_stats = {
            'total_calls': 0,
            'successful_calls': 0,
            'failed_calls': 0,
            'retry_attempts': 0,
            'constraint_errors': 0,
            'network_errors': 0,
            'validation_errors': 0
        }
    
    def _execute_rpc_with_retry(
        self,
        rpc_name: str,
        parameters: Dict[str, Any],
        operation_description: str = "RPC call"
    ) -> Any:
        """
        Execute RPC call with retry logic and error handling.
        
        Args:
            rpc_name: Name of the RPC function
            parameters: Parameters for the RPC call
            operation_description: Description for logging
            
        Returns:
            RPC call result
            
        Raises:
            RPCError: For various RPC failures
        """
        self.rpc_stats['total_calls'] += 1
        
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                logger.info(
                    f"Executing {operation_description}",
                    rpc_name=rpc_name,
                    attempt=attempt + 1,
                    max_retries=self.max_retries,
                    parameters=parameters
                )
                
                # Execute RPC call
                result = self.supabase_client.rpc(rpc_name, parameters).execute()
                
                if result.data is not None:
                    self.rpc_stats['successful_calls'] += 1
                    
                    logger.info(
                        f"Successfully completed {operation_description}",
                        rpc_name=rpc_name,
                        attempt=attempt + 1,
                        result_count=len(result.data) if isinstance(result.data, list) else 1
                    )
                    
                    return result.data
                else:
                    # Handle case where RPC returns no data
                    error_msg = f"RPC {rpc_name} returned no data"
                    if hasattr(result, 'error') and result.error:
                        error_msg += f": {result.error}"
                    
                    raise RPCError(error_msg)
                    
            except Exception as e:
                last_exception = e
                
                # Classify error type (only on first attempt)
                if attempt == 0:
                    error_type = self._classify_error(e)
                    if error_type == 'constraint':
                        self.rpc_stats['constraint_errors'] += 1
                    elif error_type == 'network':
                        self.rpc_stats['network_errors'] += 1
                    elif error_type == 'validation':
                        self.rpc_stats['validation_errors'] += 1
                else:
                    # Use the same error type for retry attempts
                    error_type = self._classify_error(e)
                
                logger.warning(
                    f"RPC call failed for {operation_description}",
                    rpc_name=rpc_name,
                    attempt=attempt + 1,
                    max_retries=self.max_retries,
                    error_type=error_type,
                    error=str(e)
                )
                
                # Don't retry on constraint or validation errors
                if error_type in ['constraint', 'validation']:
                    self.rpc_stats['failed_calls'] += 1
                    break
                
                # Retry on network errors or other transient errors
                if attempt < self.max_retries:
                    delay = self.base_delay * (2 ** attempt)
                    self.rpc_stats['retry_attempts'] += 1
                    
                    logger.info(
                        f"Retrying {operation_description} after delay",
                        rpc_name=rpc_name,
                        attempt=attempt + 1,
                        delay_seconds=delay
                    )
                    
                    time.sleep(delay)
                else:
                    # Only count as failed call when all retries are exhausted
                    self.rpc_stats['failed_calls'] += 1
                    logger.error(
                        f"All retry attempts exhausted for {operation_description}",
                        rpc_name=rpc_name,
                        max_retries=self.max_retries,
                        final_error=str(e)
                    )
        
        # All retries exhausted, raise the last exception
        if isinstance(last_exception, RPCError):
            raise last_exception
        else:
            raise RPCError(f"RPC call failed after {self.max_retries} retries: {str(last_exception)}")
    
    def _classify_error(self, error: Exception) -> str:
        """
        Classify error type for appropriate handling.
        
        Args:
            error: Exception to classify
            
        Returns:
            Error type classification
        """
        error_str = str(error).lower()
        
        # Database constraint violations
        if any(keyword in error_str for keyword in [
            'constraint', 'violation', 'duplicate', 'unique', 'foreign key',
            'not null', 'check constraint'
        ]):
            return 'constraint'
        
        # Network-related errors
        if any(keyword in error_str for keyword in [
            'timeout', 'connection', 'network', 'unreachable', 'refused'
        ]):
            return 'network'
        
        # Validation errors
        if any(keyword in error_str for keyword in [
            'invalid', 'validation', 'type', 'format', 'required'
        ]):
            return 'validation'
        
        # Default to network for retry logic
        return 'network'
    
    def upsert_coffee(
        self,
        bean_species: str,
        name: str,
        slug: str,
        roaster_id: str,
        process: str,
        process_raw: str,
        roast_level: str,
        roast_level_raw: str,
        roast_style_raw: str,
        description_md: str,
        direct_buy_url: str,
        platform_product_id: str,
        decaf: Optional[bool] = None,
        notes_raw: Optional[Dict[str, Any]] = None,
        source_raw: Optional[Dict[str, Any]] = None,
        status: Optional[str] = None
    ) -> str:
        """
        Upsert coffee record using rpc_upsert_coffee.
        
        Args:
            bean_species: Coffee species
            name: Coffee name
            slug: URL-friendly slug
            roaster_id: Roaster ID
            process: Processing method
            process_raw: Raw process description
            roast_level: Roast level
            roast_level_raw: Raw roast level description
            roast_style_raw: Roast style description
            description_md: Markdown description
            direct_buy_url: Direct purchase URL
            platform_product_id: Platform product ID
            decaf: Whether coffee is decaffeinated
            notes_raw: Raw notes data
            source_raw: Raw source data
            status: Coffee status
            
        Returns:
            Coffee ID
        """
        parameters = {
            'p_bean_species': bean_species,
            'p_name': name,
            'p_slug': slug,
            'p_roaster_id': roaster_id,
            'p_process': process,
            'p_process_raw': process_raw,
            'p_roast_level': roast_level,
            'p_roast_level_raw': roast_level_raw,
            'p_roast_style_raw': roast_style_raw,
            'p_description_md': description_md,
            'p_direct_buy_url': direct_buy_url,
            'p_platform_product_id': platform_product_id
        }
        
        # Add optional parameters
        if decaf is not None:
            parameters['p_decaf'] = decaf
        if notes_raw is not None:
            parameters['p_notes_raw'] = notes_raw
        if source_raw is not None:
            parameters['p_source_raw'] = source_raw
        if status is not None:
            parameters['p_status'] = status
        
        result = self._execute_rpc_with_retry(
            rpc_name='rpc_upsert_coffee',
            parameters=parameters,
            operation_description=f"upsert coffee '{name}'"
        )
        
        # Extract coffee ID from result
        if isinstance(result, list) and len(result) > 0:
            return result[0]
        elif isinstance(result, str):
            return result
        else:
            raise RPCError(f"Unexpected result format from rpc_upsert_coffee: {result}")
    
    def upsert_variant(
        self,
        coffee_id: str,
        platform_variant_id: str,
        sku: str,
        weight_g: int,
        currency: Optional[str] = None,
        in_stock: Optional[bool] = None,
        stock_qty: Optional[int] = None,
        subscription_available: Optional[bool] = None,
        compare_at_price: Optional[float] = None,
        grind: Optional[str] = None,
        pack_count: Optional[int] = None,
        source_raw: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Upsert variant record using rpc_upsert_variant.
        
        Args:
            coffee_id: Coffee ID
            platform_variant_id: Platform variant ID
            sku: SKU
            weight_g: Weight in grams
            currency: Currency code
            in_stock: Stock status
            stock_qty: Stock quantity
            subscription_available: Subscription availability
            compare_at_price: Compare at price
            grind: Grind type
            pack_count: Number of packs
            source_raw: Raw source data
            
        Returns:
            Variant ID
        """
        parameters = {
            'p_coffee_id': coffee_id,
            'p_platform_variant_id': platform_variant_id,
            'p_sku': sku,
            'p_weight_g': weight_g
        }
        
        # Add optional parameters
        if currency is not None:
            parameters['p_currency'] = currency
        if in_stock is not None:
            parameters['p_in_stock'] = in_stock
        if stock_qty is not None:
            parameters['p_stock_qty'] = stock_qty
        if subscription_available is not None:
            parameters['p_subscription_available'] = subscription_available
        if compare_at_price is not None:
            parameters['p_compare_at_price'] = compare_at_price
        if grind is not None:
            parameters['p_grind'] = grind
        if pack_count is not None:
            parameters['p_pack_count'] = pack_count
        if source_raw is not None:
            parameters['p_source_raw'] = source_raw
        
        result = self._execute_rpc_with_retry(
            rpc_name='rpc_upsert_variant',
            parameters=parameters,
            operation_description=f"upsert variant '{sku}'"
        )
        
        # Extract variant ID from result
        if isinstance(result, list) and len(result) > 0:
            return result[0]
        elif isinstance(result, str):
            return result
        else:
            raise RPCError(f"Unexpected result format from rpc_upsert_variant: {result}")
    
    def insert_price(
        self,
        variant_id: str,
        price: float,
        currency: Optional[str] = None,
        is_sale: Optional[bool] = None,
        scraped_at: Optional[str] = None,
        source_url: Optional[str] = None,
        source_raw: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Insert price record using rpc_insert_price.
        
        Args:
            variant_id: Variant ID
            price: Price value
            currency: Currency code
            is_sale: Whether price is a sale
            scraped_at: Scraping timestamp
            source_url: Source URL
            source_raw: Raw source data
            
        Returns:
            Price ID
        """
        parameters = {
            'p_variant_id': variant_id,
            'p_price': price
        }
        
        # Add optional parameters
        if currency is not None:
            parameters['p_currency'] = currency
        if is_sale is not None:
            parameters['p_is_sale'] = is_sale
        if scraped_at is not None:
            parameters['p_scraped_at'] = scraped_at
        if source_url is not None:
            parameters['p_source_url'] = source_url
        if source_raw is not None:
            parameters['p_source_raw'] = source_raw
        
        result = self._execute_rpc_with_retry(
            rpc_name='rpc_insert_price',
            parameters=parameters,
            operation_description=f"insert price {price} for variant {variant_id}"
        )
        
        # Extract price ID from result
        if isinstance(result, list) and len(result) > 0:
            return result[0]
        elif isinstance(result, str):
            return result
        else:
            raise RPCError(f"Unexpected result format from rpc_insert_price: {result}")
    
    def upsert_coffee_image(
        self,
        coffee_id: str,
        url: str,
        alt: Optional[str] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
        sort_order: Optional[int] = None,
        source_raw: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Upsert coffee image using rpc_upsert_coffee_image.
        
        Args:
            coffee_id: Coffee ID
            url: Image URL
            alt: Alt text
            width: Image width
            height: Image height
            sort_order: Display order
            source_raw: Raw source data
            
        Returns:
            Image ID
        """
        parameters = {
            'p_coffee_id': coffee_id,
            'p_url': url
        }
        
        # Add optional parameters
        if alt is not None:
            parameters['p_alt'] = alt
        if width is not None:
            parameters['p_width'] = width
        if height is not None:
            parameters['p_height'] = height
        if sort_order is not None:
            parameters['p_sort_order'] = sort_order
        if source_raw is not None:
            parameters['p_source_raw'] = source_raw
        
        result = self._execute_rpc_with_retry(
            rpc_name='rpc_upsert_coffee_image',
            parameters=parameters,
            operation_description=f"upsert image for coffee {coffee_id}"
        )
        
        # Extract image ID from result
        if isinstance(result, list) and len(result) > 0:
            return result[0]
        elif isinstance(result, str):
            return result
        else:
            raise RPCError(f"Unexpected result format from rpc_upsert_coffee_image: {result}")
    
    def get_rpc_stats(self) -> Dict[str, Any]:
        """
        Get RPC client statistics.
        
        Returns:
            Dictionary with RPC statistics
        """
        stats = self.rpc_stats.copy()
        
        # Calculate success rate
        if stats['total_calls'] > 0:
            stats['success_rate'] = stats['successful_calls'] / stats['total_calls']
            stats['failure_rate'] = stats['failed_calls'] / stats['total_calls']
            stats['retry_rate'] = stats['retry_attempts'] / stats['total_calls']
        else:
            stats['success_rate'] = 0.0
            stats['failure_rate'] = 0.0
            stats['retry_rate'] = 0.0
        
        return stats
    
    def reset_stats(self):
        """Reset RPC client statistics."""
        self.rpc_stats = {
            'total_calls': 0,
            'successful_calls': 0,
            'failed_calls': 0,
            'retry_attempts': 0,
            'constraint_errors': 0,
            'network_errors': 0,
            'validation_errors': 0
        }
