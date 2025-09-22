"""
Price-only parser for extracting minimal fields from product data.
Handles price delta detection and currency normalization.
"""

from typing import Any, Dict, List, Optional, Tuple
from decimal import Decimal
from datetime import datetime, timezone
from structlog import get_logger

logger = get_logger(__name__)


class PriceDelta:
    """Represents a price change for a variant."""
    
    def __init__(
        self,
        variant_id: str,
        old_price: Optional[Decimal],
        new_price: Decimal,
        currency: str,
        in_stock: bool,
        sku: Optional[str] = None,
    ):
        self.variant_id = variant_id
        self.old_price = old_price
        self.new_price = new_price
        self.currency = currency
        self.in_stock = in_stock
        self.sku = sku
        self.detected_at = datetime.now(timezone.utc)
    
    def has_price_change(self) -> bool:
        """Check if there's a price change."""
        if self.old_price is None:
            return True  # New price
        return self.old_price != self.new_price
    
    def has_availability_change(self) -> bool:
        """Check if availability changed (placeholder for future implementation)."""
        # This would need to be implemented with existing stock data
        return False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            'variant_id': self.variant_id,
            'old_price': float(self.old_price) if self.old_price else None,
            'new_price': float(self.new_price),
            'currency': self.currency,
            'in_stock': self.in_stock,
            'sku': self.sku,
            'detected_at': self.detected_at.isoformat(),
        }


class PriceParser:
    """
    Lightweight parser for extracting price-only fields from product data.
    
    Features:
    - Extracts minimal fields: price, availability, SKU, weight
    - Handles currency normalization
    - Detects price deltas by comparing with existing data
    - Supports both Shopify and WooCommerce formats
    """
    
    def __init__(self, job_type: str = "price_only"):
        self.job_type = job_type
        self.price_fields = ["price", "availability", "sku", "weight"]
        
        logger.info(
            "Initialized price parser",
            job_type=job_type,
            price_fields=self.price_fields,
        )
    
    def extract_price_data(self, product: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract price-only data from a product.
        
        Args:
            product: Raw product data from platform
            
        Returns:
            Dictionary with minimal price-related fields
        """
        try:
            # Extract basic product info
            product_id = product.get('id')
            platform_product_id = str(product_id) if product_id else None
            
            # Extract variants with price data
            variants = []
            # Handle both 'variants' (Shopify) and 'variations' (WooCommerce)
            raw_variants = product.get('variants', []) or product.get('variations', [])
            
            # Special handling for WooCommerce simple products
            if not raw_variants and product.get('type') == 'simple':
                # Create a single variant from the main product data
                variant_data = self._extract_variant_price_data(product)
                if variant_data:
                    variants.append(variant_data)
            else:
                for variant in raw_variants:
                    # For WooCommerce variable products, variations inherit price from main product
                    if product.get('type') == 'variable' and not variant.get('price'):
                        # Create a variant with inherited price data
                        variant_with_price = variant.copy()
                        variant_with_price.update({
                            'price': product.get('prices', {}).get('price'),
                            'currency': product.get('prices', {}).get('currency_code'),
                            'available': product.get('is_in_stock', True),
                        })
                        variant_data = self._extract_variant_price_data(variant_with_price)
                    else:
                        variant_data = self._extract_variant_price_data(variant)
                    
                    if variant_data:
                        variants.append(variant_data)
            
            # Return minimal product structure
            return {
                'platform_product_id': platform_product_id,
                'variants': variants,
                'extracted_at': datetime.now(timezone.utc).isoformat(),
                'job_type': self.job_type,
            }
            
        except Exception as e:
            logger.error(
                "Failed to extract price data from product",
                product_id=product.get('id'),
                error=str(e),
            )
            return {
                'platform_product_id': str(product.get('id', 'unknown')),
                'variants': [],
                'error': str(e),
                'extracted_at': datetime.now(timezone.utc).isoformat(),
                'job_type': self.job_type,
            }
    
    def _extract_variant_price_data(self, variant: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Extract price data from a single variant.
        
        Args:
            variant: Raw variant data
            
        Returns:
            Dictionary with price fields or None if invalid
        """
        try:
            variant_id = variant.get('id')
            if not variant_id:
                return None
            
            # Extract price information
            price_decimal = self._extract_price_decimal(variant)
            if price_decimal is None:
                return None
            
            # Extract other required fields
            currency = self._extract_currency(variant)
            in_stock = self._extract_availability(variant)
            sku = variant.get('sku')
            weight_g = self._extract_weight(variant)
            
            return {
                'platform_variant_id': str(variant_id),
                'price_decimal': price_decimal,
                'currency': currency,
                'in_stock': in_stock,
                'sku': sku,
                'weight_g': weight_g,
            }
            
        except Exception as e:
            logger.warning(
                "Failed to extract variant price data",
                variant_id=variant.get('id'),
                error=str(e),
            )
            return None
    
    def _extract_price_decimal(self, variant: Dict[str, Any]) -> Optional[Decimal]:
        """Extract and normalize price as Decimal."""
        try:
            # Try different price field names
            price_fields = ['price', 'price_decimal', 'amount', 'value']
            
            for field in price_fields:
                price_value = variant.get(field)
                if price_value is not None:
                    # Handle string prices
                    if isinstance(price_value, str):
                        # Remove currency symbols and whitespace
                        price_value = price_value.replace('$', '').replace('€', '').replace('£', '').strip()
                    
                    # Convert to Decimal
                    return Decimal(str(price_value))
            
            # Handle WooCommerce nested price structure
            prices_obj = variant.get('prices', {})
            if prices_obj:
                price_value = prices_obj.get('price') or prices_obj.get('regular_price')
                if price_value is not None:
                    # WooCommerce prices are often in minor units (cents)
                    # Convert from minor units to major units
                    if isinstance(price_value, (int, str)):
                        try:
                            price_int = int(price_value)
                            # If price looks like it's in minor units (e.g., 49900 for 499.00)
                            if price_int > 1000:  # Heuristic: if > 1000, likely in minor units
                                return Decimal(str(price_int / 100))
                            else:
                                return Decimal(str(price_int))
                        except (ValueError, TypeError):
                            pass
                    return Decimal(str(price_value))
            
            return None
            
        except Exception as e:
            logger.warning(
                "Failed to extract price decimal",
                variant_id=variant.get('id'),
                error=str(e),
            )
            return None
    
    def _extract_currency(self, variant: Dict[str, Any]) -> str:
        """Extract currency code."""
        # Try variant-specific currency first
        currency = variant.get('currency')
        if currency:
            return currency.upper()
        
        # Handle WooCommerce nested currency structure
        prices_obj = variant.get('prices', {})
        if prices_obj:
            currency_code = prices_obj.get('currency_code')
            if currency_code:
                return currency_code.upper()
        
        # Fallback to common defaults
        return 'USD'
    
    def _extract_availability(self, variant: Dict[str, Any]) -> bool:
        """Extract availability status."""
        # Try different availability fields
        availability_fields = ['available', 'in_stock', 'inventory_quantity', 'stock_status']
        
        for field in availability_fields:
            value = variant.get(field)
            if value is not None:
                if isinstance(value, bool):
                    return value
                elif isinstance(value, (int, float)):
                    return value > 0
                elif isinstance(value, str):
                    # Handle positive and negative string values
                    positive_values = ['true', 'yes', 'available', 'in_stock', 'instock']
                    negative_values = ['false', 'no', 'unavailable', 'out_of_stock', 'outofstock']
                    
                    value_lower = value.lower()
                    if value_lower in positive_values:
                        return True
                    elif value_lower in negative_values:
                        return False
                    # If not recognized, default to True
                    return True
        
        # Default to available if no field found
        return True
    
    def _extract_weight(self, variant: Dict[str, Any]) -> Optional[float]:
        """Extract weight in grams."""
        try:
            weight = variant.get('weight')
            if weight is None:
                return None
            
            # Convert to float
            weight_float = float(weight)
            
            # Assume grams if no unit specified
            # This could be enhanced to detect units
            return weight_float
            
        except (ValueError, TypeError):
            return None
    
    def detect_price_deltas(
        self,
        fetched_products: List[Dict[str, Any]],
        existing_variants: List[Dict[str, Any]],
    ) -> List[PriceDelta]:
        """
        Detect price changes by comparing fetched data with existing variants.
        
        Args:
            fetched_products: Products with price data from fetch
            existing_variants: Existing variant data from database
            
        Returns:
            List of price deltas for changed variants
        """
        deltas = []
        
        # Create lookup for existing variants
        existing_lookup = {
            variant['platform_variant_id']: variant
            for variant in existing_variants
        }
        
        # Process each fetched product
        for product in fetched_products:
            variants = product.get('variants', [])
            
            for variant in variants:
                variant_id = variant.get('platform_variant_id')
                if not variant_id:
                    continue
                
                # Get existing variant data
                existing = existing_lookup.get(variant_id)
                
                # Create price delta
                delta = self._create_price_delta(variant, existing)
                if delta and (delta.has_price_change() or delta.has_availability_change()):
                    deltas.append(delta)
        
        logger.info(
            "Detected price deltas",
            total_deltas=len(deltas),
            price_changes=sum(1 for d in deltas if d.has_price_change()),
            availability_changes=sum(1 for d in deltas if d.has_availability_change()),
        )
        
        return deltas
    
    def _create_price_delta(
        self,
        fetched_variant: Dict[str, Any],
        existing_variant: Optional[Dict[str, Any]],
    ) -> Optional[PriceDelta]:
        """Create a price delta from fetched and existing variant data."""
        try:
            variant_id = fetched_variant.get('platform_variant_id')
            new_price = fetched_variant.get('price_decimal')
            currency = fetched_variant.get('currency', 'USD')
            in_stock = fetched_variant.get('in_stock', True)
            sku = fetched_variant.get('sku')
            
            if not variant_id or new_price is None:
                return None
            
            # Convert new price to Decimal
            new_price_decimal = Decimal(str(new_price))
            
            # Get existing price
            old_price = None
            if existing_variant:
                old_price_value = existing_variant.get('price_current')
                if old_price_value is not None:
                    old_price = Decimal(str(old_price_value))
            
            return PriceDelta(
                variant_id=variant_id,
                old_price=old_price,
                new_price=new_price_decimal,
                currency=currency,
                in_stock=in_stock,
                sku=sku,
            )
            
        except Exception as e:
            logger.warning(
                "Failed to create price delta",
                variant_id=fetched_variant.get('platform_variant_id'),
                error=str(e),
            )
            return None
    
    def normalize_currency(self, price: Decimal, from_currency: str, to_currency: str = 'USD') -> Decimal:
        """
        Normalize currency (placeholder for future implementation).
        
        Args:
            price: Price to normalize
            from_currency: Source currency
            to_currency: Target currency (default USD)
            
        Returns:
            Normalized price (currently returns original price)
        """
        # TODO: Implement actual currency conversion
        # For now, just return the original price
        return price
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for the parser."""
        return {
            'job_type': self.job_type,
            'price_fields': self.price_fields,
            'parser_version': '1.0.0',
        }
