"""
RPC client wrapper for Supabase RPC calls with error handling and retry logic.
"""

import time
import json
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from enum import Enum

from structlog import get_logger

# Import image processing guard
try:
    from ..images.processing_guard import ImageProcessingGuard
except ImportError:
    ImageProcessingGuard = None

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
    
    def __init__(self, supabase_client, max_retries: int = 3, base_delay: float = 1.0, metadata_only: bool = False):
        """
        Initialize RPC client.
        
        Args:
            supabase_client: Supabase client for RPC calls
            max_retries: Maximum number of retry attempts
            base_delay: Base delay in seconds for exponential backoff
            metadata_only: Whether this is a metadata-only (price-only) run
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
        
        # Initialize image processing guard
        self.metadata_only = metadata_only
        if ImageProcessingGuard:
            self.image_guard = ImageProcessingGuard(metadata_only=metadata_only)
            logger.info(
                "RPC client image processing guard initialized",
                metadata_only=metadata_only
            )
        else:
            self.image_guard = None
            logger.warning("RPC client image processing guard not available")
    
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
        status: Optional[str] = None,
        # Epic C.3: Tags & Notes parameters
        tags: Optional[List[str]] = None,
        # Epic C.4: Grind & Species parameters
        default_grind: Optional[str] = None,
        # Epic C.5: Varieties & Geographic parameters
        varieties: Optional[List[str]] = None,
        region: Optional[str] = None,
        country: Optional[str] = None,
        altitude: Optional[int] = None,
        # Epic C.6: Sensory & Hash parameters
        acidity: Optional[float] = None,
        body: Optional[float] = None,
        flavors: Optional[List[str]] = None,
        content_hash: Optional[str] = None,
        raw_hash: Optional[str] = None,
        # Epic C.7: Text Cleaning parameters
        title_cleaned: Optional[str] = None,
        description_cleaned: Optional[str] = None
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
            'p_roaster_id': roaster_id,  # Pass as string, database will handle UUID conversion
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
        
        # Epic C.3: Tags & Notes parameters
        if tags is not None:
            parameters['p_tags'] = tags
        
        # Epic C.4: Grind & Species parameters
        if default_grind is not None:
            parameters['p_default_grind'] = default_grind
        
        # Epic C.5: Varieties & Geographic parameters
        if varieties is not None:
            parameters['p_varieties'] = varieties
        if region is not None:
            parameters['p_region'] = region
        if country is not None:
            parameters['p_country'] = country
        if altitude is not None:
            parameters['p_altitude'] = altitude
        
        # Epic C.6: Sensory & Hash parameters
        if acidity is not None:
            parameters['p_acidity'] = acidity
        if body is not None:
            parameters['p_body'] = body
        if flavors is not None:
            parameters['p_flavors'] = flavors
        if content_hash is not None:
            parameters['p_content_hash'] = content_hash
        if raw_hash is not None:
            parameters['p_raw_hash'] = raw_hash
        
        # Epic C.7: Text Cleaning parameters
        if title_cleaned is not None:
            parameters['p_title_cleaned'] = title_cleaned
        if description_cleaned is not None:
            parameters['p_description_cleaned'] = description_cleaned
        
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
        source_raw: Optional[Dict[str, Any]] = None,
        content_hash: Optional[str] = None,
        imagekit_url: Optional[str] = None
    ) -> str:
        """
        Upsert coffee image using rpc_upsert_coffee_image with deduplication support.
        
        Args:
            coffee_id: Coffee ID
            url: Image URL
            alt: Alt text
            width: Image width
            height: Image height
            sort_order: Display order
            source_raw: Raw source data
            content_hash: SHA256 hash for deduplication
            imagekit_url: ImageKit CDN URL for optimized delivery
            
        Returns:
            Image ID
        """
        # Check if image processing is allowed (guard enforcement)
        if self.image_guard and not self.image_guard.check_image_processing_allowed("upsert_coffee_image"):
            logger.warning(
                "Image upsert blocked by guard for price-only run",
                operation="upsert_coffee_image",
                coffee_id=coffee_id,
                url=url,
                metadata_only=self.metadata_only
            )
            raise RPCError(
                f"Image processing blocked for price-only run: upsert_coffee_image for coffee {coffee_id}"
            )
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
        if content_hash is not None:
            parameters['p_content_hash'] = content_hash
        if imagekit_url is not None:
            parameters['p_imagekit_url'] = imagekit_url
        
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
    
    def check_content_hash(self, content_hash: str) -> Optional[str]:
        """
        Check if content hash already exists in database.
        
        Args:
            content_hash: SHA256 hash to check for duplicates
            
        Returns:
            Existing image ID if found, None if new
        """
        parameters = {
            'p_content_hash': content_hash
        }
        
        result = self._execute_rpc_with_retry(
            rpc_name='rpc_check_content_hash',
            parameters=parameters,
            operation_description=f"check content hash {content_hash[:8]}..."
        )
        
        # Return the image ID if found, None if not found
        if result and result != '':
            return result
        else:
            return None
    
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
    
    def upsert_coffee_with_raw_data(self, coffee_data: Dict[str, Any]) -> bool:
        """
        Upsert coffee record with raw artifact data.
        
        Args:
            coffee_data: Dictionary containing coffee data and raw artifact data
                - source_raw: Raw artifact JSON data
                - first_seen_at: First seen timestamp
                - Other coffee fields as needed
                
        Returns:
            True if successful, False otherwise
        """
        try:
            # Extract raw artifact data
            source_raw = coffee_data.get('source_raw', {})
            first_seen_at = coffee_data.get('first_seen_at')
            
            if not source_raw:
                logger.warning("No source_raw data provided")
                return False
            
            # Call the existing upsert_coffee method with raw data
            # We'll use minimal required fields and let the RPC handle the rest
            result = self.upsert_coffee(
                bean_species=coffee_data.get('bean_species', 'unknown'),
                name=coffee_data.get('name', 'Unknown Coffee'),
                slug=coffee_data.get('slug', 'unknown-coffee'),
                roaster_id=coffee_data.get('roaster_id', 'unknown'),
                process=coffee_data.get('process', 'unknown'),
                process_raw=coffee_data.get('process_raw', ''),
                roast_level=coffee_data.get('roast_level', 'unknown'),
                roast_level_raw=coffee_data.get('roast_level_raw', ''),
                roast_style_raw=coffee_data.get('roast_style_raw', ''),
                description_md=coffee_data.get('description_md', ''),
                direct_buy_url=coffee_data.get('direct_buy_url', ''),
                platform_product_id=coffee_data.get('platform_product_id', ''),
                decaf=coffee_data.get('decaf'),
                notes_raw=coffee_data.get('notes_raw'),
                source_raw=source_raw,
                status=coffee_data.get('status', 'active')
            )
            
            if result:
                logger.info(f"Successfully upserted coffee with raw data: {result}")
                return True
            else:
                logger.error("Failed to upsert coffee with raw data")
                return False
                
        except Exception as e:
            logger.error(f"Error upserting coffee with raw data: {e}")
            return False

    def update_variant_pricing(
        self,
        variant_id: str,
        price_current: Optional[float] = None,
        price_last_checked_at: Optional[str] = None,
        in_stock: Optional[bool] = None,
        currency: Optional[str] = None
    ) -> bool:
        """
        Update variant pricing fields using direct table update.
        
        Args:
            variant_id: Variant ID to update
            price_current: Current price value
            price_last_checked_at: Last price check timestamp
            in_stock: Stock availability status
            currency: Currency code
            
        Returns:
            True if successful, False otherwise
        """
        try:
            update_data = {}
            
            if price_current is not None:
                update_data['price_current'] = price_current
            if price_last_checked_at is not None:
                update_data['price_last_checked_at'] = price_last_checked_at
            if in_stock is not None:
                update_data['in_stock'] = in_stock
            if currency is not None:
                update_data['currency'] = currency
            
            if not update_data:
                logger.warning("No variant pricing fields to update", variant_id=variant_id)
                return True
            
            # Use direct table update instead of RPC
            result = self.supabase_client.table("variants").update(update_data).eq("id", variant_id).execute()
            
            if result.data:
                logger.info(
                    "Successfully updated variant pricing",
                    variant_id=variant_id,
                    updated_fields=list(update_data.keys())
                )
                return True
            else:
                logger.error(
                    "Failed to update variant pricing - no data returned",
                    variant_id=variant_id
                )
                return False
                
        except Exception as e:
            logger.error(
                "Failed to update variant pricing",
                variant_id=variant_id,
                error=str(e)
            )
            return False
    
    def batch_update_variant_pricing(
        self,
        variant_updates: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Batch update variant pricing for multiple variants.
        
        Args:
            variant_updates: List of variant update dictionaries with 'variant_id' and update fields
            
        Returns:
            Dictionary with batch update results
        """
        results = {
            'total_updates': len(variant_updates),
            'successful_updates': 0,
            'failed_updates': 0,
            'errors': []
        }
        
        for update in variant_updates:
            try:
                variant_id = update.get('variant_id')
                if not variant_id:
                    results['errors'].append("Missing variant_id in update")
                    results['failed_updates'] += 1
                    continue
                
                # Remove variant_id from update data
                update_data = {k: v for k, v in update.items() if k != 'variant_id'}
                
                success = self.update_variant_pricing(
                    variant_id=variant_id,
                    **update_data
                )
                
                if success:
                    results['successful_updates'] += 1
                else:
                    results['failed_updates'] += 1
                    results['errors'].append(f"Failed to update variant {variant_id}")
                    
            except Exception as e:
                results['failed_updates'] += 1
                results['errors'].append(f"Error updating variant {update.get('variant_id', 'unknown')}: {str(e)}")
        
        logger.info(
            "Completed batch variant pricing update",
            total_updates=results['total_updates'],
            successful=results['successful_updates'],
            failed=results['failed_updates']
        )
        
        return results

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
