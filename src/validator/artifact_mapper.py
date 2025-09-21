"""
Artifact transformation logic for mapping canonical artifacts to RPC payloads.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

from structlog import get_logger

from .models import ArtifactModel, VariantModel, ProductModel, NormalizationModel

logger = get_logger(__name__)


class ArtifactMapper:
    """
    Maps canonical artifacts to RPC payloads for database persistence.
    
    Features:
    - Transform artifact data to RPC parameters
    - Handle metadata-only flag for price-only updates
    - Support for all RPC functions (coffee, variant, price, image)
    - Currency validation and normalization
    """
    
    def __init__(self):
        """Initialize artifact mapper."""
        self.mapping_stats = {
            'total_mapped': 0,
            'coffee_mapped': 0,
            'variants_mapped': 0,
            'prices_mapped': 0,
            'images_mapped': 0,
            'mapping_errors': 0
        }
    
    def map_artifact_to_rpc_payloads(
        self,
        artifact: ArtifactModel,
        roaster_id: str,
        metadata_only: bool = False
    ) -> Dict[str, Any]:
        """
        Map canonical artifact to RPC payloads.
        
        Args:
            artifact: Canonical artifact model
            roaster_id: Roaster ID for the artifact
            metadata_only: Whether this is a metadata-only update
            
        Returns:
            Dictionary with RPC payloads for coffee, variants, prices, and images
        """
        try:
            self.mapping_stats['total_mapped'] += 1
            
            # Map coffee data
            coffee_payload = self._map_coffee_data(artifact, roaster_id)
            
            # Map variants data
            variants_payloads = self._map_variants_data(artifact, metadata_only)
            
            # Map prices data
            prices_payloads = self._map_prices_data(artifact, metadata_only)
            
            # Map images data (only if not metadata-only)
            images_payloads = []
            if not metadata_only:
                images_payloads = self._map_images_data(artifact)
            
            result = {
                'coffee': coffee_payload,
                'variants': variants_payloads,
                'prices': prices_payloads,
                'images': images_payloads,
                'metadata_only': metadata_only,
                'roaster_id': roaster_id,
                'platform_product_id': artifact.product.platform_product_id
            }
            
            logger.info(
                "Successfully mapped artifact to RPC payloads",
                platform_product_id=artifact.product.platform_product_id,
                roaster_id=roaster_id,
                metadata_only=metadata_only,
                variants_count=len(variants_payloads),
                prices_count=len(prices_payloads),
                images_count=len(images_payloads)
            )
            
            return result
            
        except Exception as e:
            self.mapping_stats['mapping_errors'] += 1
            
            logger.error(
                "Failed to map artifact to RPC payloads",
                platform_product_id=artifact.product.platform_product_id,
                roaster_id=roaster_id,
                error=str(e)
            )
            
            raise
    
    def _map_coffee_data(self, artifact: ArtifactModel, roaster_id: str) -> Dict[str, Any]:
        """
        Map artifact to coffee RPC payload.
        
        Args:
            artifact: Canonical artifact model
            roaster_id: Roaster ID
            
        Returns:
            Coffee RPC payload
        """
        product = artifact.product
        normalization = artifact.normalization
        
        # Map required fields
        coffee_payload = {
            'p_bean_species': self._map_bean_species(normalization),
            'p_name': self._map_coffee_name(product, normalization),
            'p_slug': self._map_coffee_slug(product),
            'p_roaster_id': roaster_id,
            'p_process': self._map_process(normalization),
            'p_process_raw': self._map_process_raw(normalization),
            'p_roast_level': self._map_roast_level(normalization),
            'p_roast_level_raw': self._map_roast_level_raw(normalization),
            'p_roast_style_raw': self._map_roast_style_raw(normalization),
            'p_description_md': self._map_description_md(product, normalization),
            'p_direct_buy_url': product.source_url,
            'p_platform_product_id': product.platform_product_id
        }
        
        # Map optional fields
        if normalization and normalization.bean_species:
            coffee_payload['p_bean_species'] = normalization.bean_species.value
        
        # Map decaf flag (infer from product title/description)
        decaf = self._infer_decaf_flag(product)
        if decaf is not None:
            coffee_payload['p_decaf'] = decaf
        
        # Map raw data
        coffee_payload['p_source_raw'] = self._build_source_raw(artifact)
        coffee_payload['p_notes_raw'] = self._build_notes_raw(normalization)
        
        self.mapping_stats['coffee_mapped'] += 1
        
        return coffee_payload
    
    def _map_variants_data(self, artifact: ArtifactModel, metadata_only: bool) -> List[Dict[str, Any]]:
        """
        Map artifact variants to RPC payloads.
        
        Args:
            artifact: Canonical artifact model
            metadata_only: Whether this is metadata-only update
            
        Returns:
            List of variant RPC payloads
        """
        variants_payloads = []
        
        for variant in artifact.product.variants:
            try:
                variant_payload = {
                    'p_platform_variant_id': variant.platform_variant_id,
                    'p_sku': variant.sku or '',
                    'p_weight_g': self._map_weight_grams(variant),
                    'p_currency': self._normalize_currency(variant.currency),
                    'p_in_stock': variant.in_stock,
                    'p_source_raw': variant.raw_variant_json or {}
                }
                
                # Add optional fields
                if variant.compare_at_price_decimal is not None:
                    variant_payload['p_compare_at_price'] = variant.compare_at_price_decimal
                
                # Map grind type from variant options
                grind = self._map_grind_from_options(variant.options)
                if grind:
                    variant_payload['p_grind'] = grind
                
                # Map pack count from weight
                pack_count = self._map_pack_count(variant)
                if pack_count:
                    variant_payload['p_pack_count'] = pack_count
                
                variants_payloads.append(variant_payload)
                self.mapping_stats['variants_mapped'] += 1
                
            except Exception as e:
                logger.warning(
                    "Failed to map variant",
                    platform_variant_id=variant.platform_variant_id,
                    error=str(e)
                )
                continue
        
        return variants_payloads
    
    def _map_prices_data(self, artifact: ArtifactModel, metadata_only: bool) -> List[Dict[str, Any]]:
        """
        Map artifact prices to RPC payloads.
        
        Args:
            artifact: Canonical artifact model
            metadata_only: Whether this is metadata-only update
            
        Returns:
            List of price RPC payloads
        """
        prices_payloads = []
        
        for variant in artifact.product.variants:
            try:
                # Map current price
                if variant.price_decimal is not None:
                    price_payload = {
                        'p_price': variant.price_decimal,
                        'p_currency': self._normalize_currency(variant.currency),
                        'p_is_sale': self._determine_sale_status(variant),
                        'p_scraped_at': artifact.scraped_at.isoformat(),
                        'p_source_url': artifact.product.source_url,
                        'p_source_raw': {
                            'variant_id': variant.platform_variant_id,
                            'scraped_at': artifact.scraped_at.isoformat(),
                            'artifact_id': artifact.audit.artifact_id if artifact.audit else None
                        }
                    }
                    
                    prices_payloads.append(price_payload)
                    self.mapping_stats['prices_mapped'] += 1
                
            except Exception as e:
                logger.warning(
                    "Failed to map price for variant",
                    platform_variant_id=variant.platform_variant_id,
                    error=str(e)
                )
                continue
        
        return prices_payloads
    
    def _map_images_data(self, artifact: ArtifactModel) -> List[Dict[str, Any]]:
        """
        Map artifact images to RPC payloads.
        
        Args:
            artifact: Canonical artifact model
            
        Returns:
            List of image RPC payloads
        """
        images_payloads = []
        
        if artifact.product.images:
            for i, image in enumerate(artifact.product.images):
                try:
                    image_payload = {
                        'p_url': image.url,
                        'p_alt': image.alt_text or '',
                        'p_sort_order': image.order or i,
                        'p_source_raw': {
                            'source_id': image.source_id,
                            'scraped_at': artifact.scraped_at.isoformat()
                        }
                    }
                    
                    # Add dimensions if available
                    if hasattr(image, 'width') and image.width:
                        image_payload['p_width'] = image.width
                    if hasattr(image, 'height') and image.height:
                        image_payload['p_height'] = image.height
                    
                    images_payloads.append(image_payload)
                    self.mapping_stats['images_mapped'] += 1
                    
                except Exception as e:
                    logger.warning(
                        "Failed to map image",
                        image_url=image.url,
                        error=str(e)
                    )
                    continue
        
        return images_payloads
    
    def _map_bean_species(self, normalization: Optional[NormalizationModel]) -> str:
        """Map bean species from normalization data."""
        if normalization and normalization.bean_species:
            return normalization.bean_species.value
        return 'arabica'  # Default to arabica
    
    def _map_coffee_name(self, product: ProductModel, normalization: Optional[NormalizationModel]) -> str:
        """Map coffee name from product and normalization data."""
        if normalization and normalization.name_clean:
            return normalization.name_clean
        return product.title
    
    def _map_coffee_slug(self, product: ProductModel) -> str:
        """Map coffee slug from product data."""
        if product.slug:
            return product.slug
        elif product.handle:
            return product.handle
        else:
            # Generate slug from title
            return product.title.lower().replace(' ', '-').replace('_', '-')
    
    def _map_process(self, normalization: Optional[NormalizationModel]) -> str:
        """Map process method from normalization data."""
        if normalization and normalization.process_enum:
            return normalization.process_enum.value
        return 'other'  # Default to other
    
    def _map_process_raw(self, normalization: Optional[NormalizationModel]) -> str:
        """Map raw process description from normalization data."""
        if normalization and normalization.process_raw:
            return normalization.process_raw
        return 'Unknown'  # Default
    
    def _map_roast_level(self, normalization: Optional[NormalizationModel]) -> str:
        """Map roast level from normalization data."""
        if normalization and normalization.roast_level_enum:
            return normalization.roast_level_enum.value
        return 'unknown'  # Default
    
    def _map_roast_level_raw(self, normalization: Optional[NormalizationModel]) -> str:
        """Map raw roast level description from normalization data."""
        if normalization and normalization.roast_level_raw:
            return normalization.roast_level_raw
        return 'Unknown'  # Default
    
    def _map_roast_style_raw(self, normalization: Optional[NormalizationModel]) -> str:
        """Map roast style description from normalization data."""
        if normalization and normalization.roast_level_raw:
            return normalization.roast_level_raw
        return 'Unknown'  # Default
    
    def _map_description_md(self, product: ProductModel, normalization: Optional[NormalizationModel]) -> str:
        """Map description from product and normalization data."""
        if normalization and normalization.description_md_clean:
            return normalization.description_md_clean
        elif product.description_md:
            return product.description_md
        elif product.description_html:
            # Convert HTML to markdown (basic conversion)
            return self._html_to_markdown(product.description_html)
        else:
            return 'No description available'
    
    def _map_weight_grams(self, variant: VariantModel) -> int:
        """Map variant weight to grams."""
        if variant.grams:
            return variant.grams
        elif variant.weight_unit and variant.weight_unit.value == 'kg':
            # Convert kg to grams (assuming we have a weight value)
            return 1000  # Default 1kg
        else:
            return 250  # Default 250g
    
    def _normalize_currency(self, currency: Optional[str]) -> str:
        """Normalize currency code."""
        if not currency:
            return 'USD'  # Default currency
        
        # Normalize common currency codes
        currency_map = {
            'usd': 'USD',
            'cad': 'CAD',
            'eur': 'EUR',
            'gbp': 'GBP',
            'aud': 'AUD'
        }
        
        return currency_map.get(currency.lower(), currency.upper())
    
    def _map_grind_from_options(self, options: Optional[List[str]]) -> Optional[str]:
        """Map grind type from variant options."""
        if not options:
            return None
        
        # Look for grind-related options
        grind_keywords = ['whole', 'ground', 'espresso', 'filter', 'coarse', 'fine']
        for option in options:
            option_lower = option.lower()
            for keyword in grind_keywords:
                if keyword in option_lower:
                    if 'whole' in option_lower:
                        return 'whole'
                    elif 'espresso' in option_lower:
                        return 'espresso'
                    elif 'filter' in option_lower:
                        return 'filter'
                    else:
                        return 'ground'
        
        return None
    
    def _map_pack_count(self, variant: VariantModel) -> Optional[int]:
        """Map pack count from variant data."""
        # This would need to be inferred from variant title or options
        # For now, return None (single pack)
        return None
    
    def _determine_sale_status(self, variant: VariantModel) -> bool:
        """Determine if price is a sale price."""
        if variant.compare_at_price_decimal and variant.price_decimal:
            return variant.price_decimal < variant.compare_at_price_decimal
        return False
    
    def _infer_decaf_flag(self, product: ProductModel) -> Optional[bool]:
        """Infer decaf flag from product title/description."""
        text_to_check = f"{product.title} {product.description_md or ''}".lower()
        decaf_keywords = ['decaf', 'decaffeinated', 'caffeine-free']
        
        for keyword in decaf_keywords:
            if keyword in text_to_check:
                return True
        
        return None
    
    def _build_source_raw(self, artifact: ArtifactModel) -> Dict[str, Any]:
        """Build source_raw JSON from artifact data."""
        return {
            'artifact_id': artifact.audit.artifact_id if artifact.audit else None,
            'scraped_at': artifact.scraped_at.isoformat(),
            'source': artifact.source.value,
            'roaster_domain': artifact.roaster_domain,
            'collector_meta': artifact.collector_meta.dict() if artifact.collector_meta else None,
            'collector_signals': artifact.collector_signals.dict() if artifact.collector_signals else None,
            'content_hash': artifact.normalization.content_hash if artifact.normalization else None,
            'raw_payload_hash': artifact.normalization.raw_payload_hash if artifact.normalization else None
        }
    
    def _build_notes_raw(self, normalization: Optional[NormalizationModel]) -> Optional[Dict[str, Any]]:
        """Build notes_raw JSON from normalization data."""
        if not normalization:
            return None
        
        notes_data = {}
        
        # Add LLM enrichment data
        if normalization.llm_enrichment:
            notes_data['llm_enrichment'] = normalization.llm_enrichment
        if normalization.llm_confidence is not None:
            notes_data['llm_confidence'] = normalization.llm_confidence
        
        # Add parsing warnings
        if normalization.parsing_warnings:
            notes_data['parsing_warnings'] = normalization.parsing_warnings
        
        # Add geographic data
        if normalization.region:
            notes_data['region'] = normalization.region
        if normalization.country:
            notes_data['country'] = normalization.country
        if normalization.altitude_m is not None:
            notes_data['altitude_m'] = normalization.altitude_m
        
        # Add varieties
        if normalization.varieties:
            notes_data['varieties'] = normalization.varieties
        
        # Add sensory parameters
        if normalization.sensory_params:
            notes_data['sensory_params'] = normalization.sensory_params.dict()
        
        return notes_data if notes_data else None
    
    def _html_to_markdown(self, html: str) -> str:
        """Basic HTML to markdown conversion."""
        # This is a very basic conversion - in production, use a proper HTML to markdown library
        import re
        
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', html)
        
        # Decode HTML entities
        text = text.replace('&amp;', '&')
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')
        text = text.replace('&quot;', '"')
        text = text.replace('&#39;', "'")
        
        return text.strip()
    
    def get_mapping_stats(self) -> Dict[str, Any]:
        """
        Get mapping statistics.
        
        Returns:
            Dictionary with mapping statistics
        """
        stats = self.mapping_stats.copy()
        
        # Calculate success rate
        if stats['total_mapped'] > 0:
            stats['success_rate'] = (stats['total_mapped'] - stats['mapping_errors']) / stats['total_mapped']
            stats['error_rate'] = stats['mapping_errors'] / stats['total_mapped']
        else:
            stats['success_rate'] = 0.0
            stats['error_rate'] = 0.0
        
        return stats
    
    def reset_stats(self):
        """Reset mapping statistics."""
        self.mapping_stats = {
            'total_mapped': 0,
            'coffee_mapped': 0,
            'variants_mapped': 0,
            'prices_mapped': 0,
            'images_mapped': 0,
            'mapping_errors': 0
        }
