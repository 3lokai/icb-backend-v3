"""
Artifact transformation logic for mapping canonical artifacts to RPC payloads.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

from structlog import get_logger

from .models import ArtifactModel, VariantModel, ProductModel, NormalizationModel

# Import weight parser for enhanced weight parsing
try:
    from ..parser.weight_parser import WeightParser
except ImportError:
    # Fallback for when weight parser is not available
    WeightParser = None

# Import roast and process parsers for enhanced parsing
try:
    from ..parser.roast_parser import RoastLevelParser
    from ..parser.process_parser import ProcessMethodParser
except ImportError:
    # Fallback for when parsers are not available
    RoastLevelParser = None
    ProcessMethodParser = None

# Import grind/brewing parser for enhanced grind parsing
try:
    from ..parser.grind_brewing_parser import GrindBrewingParser
except ImportError:
    # Fallback for when grind/brewing parser is not available
    GrindBrewingParser = None

# Import image deduplication service
from ..config.imagekit_config import ImageKitConfig
from .type_utils import assert_imagekit_config

try:
    from ..images.deduplication_service import ImageDeduplicationService
    from ..images.hash_computation import ImageHashComputer
    from ..images.imagekit_integration import ImageKitIntegrationService
    from ..images.processing_guard import ImageProcessingGuard, guard_image_operation
except ImportError:
    # Fallback for when image services are not available
    ImageDeduplicationService = None
    ImageHashComputer = None
    ImageProcessingGuard = None
    guard_image_operation = None

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
    
    def __init__(
        self, 
        rpc_client=None, 
        enable_image_deduplication=True,
        enable_imagekit=True,
        imagekit_config: Optional[ImageKitConfig] = None,
        integration_service=None,
        metadata_only=False,
        normalizer_pipeline=None
    ) -> None:
        """
        Initialize artifact mapper.
        
        Args:
            rpc_client: RPC client for database operations (required for deduplication)
            enable_image_deduplication: Whether to enable image deduplication
            enable_imagekit: Whether to enable ImageKit CDN upload (default: True)
            imagekit_config: ImageKit configuration (required if enable_imagekit=True)
            integration_service: ValidatorIntegrationService instance (preferred over individual params)
            metadata_only: Whether this is a metadata-only (price-only) run
        """
        self.mapping_stats = {
            'total_mapped': 0,
            'coffee_mapped': 0,
            'variants_mapped': 0,
            'prices_mapped': 0,
            'images_mapped': 0,
            'mapping_errors': 0
        }
        
        # Store integration service for access to all services
        self.integration_service = integration_service
        
        # Store normalizer pipeline for C.8 integration
        self.normalizer_pipeline = normalizer_pipeline
        
        # Initialize weight parser for enhanced weight parsing
        if integration_service and hasattr(integration_service, 'weight_parser'):
            # Use weight parser from integration service
            self.weight_parser = integration_service.weight_parser
        else:
            # Fallback to individual initialization (legacy support)
            self.weight_parser = WeightParser() if WeightParser else None
        
        # Initialize roast and process parsers for enhanced parsing
        self.roast_parser = RoastLevelParser() if RoastLevelParser else None
        self.process_parser = ProcessMethodParser() if ProcessMethodParser else None
        
        # Initialize grind/brewing parser for enhanced grind parsing
        if integration_service and hasattr(integration_service, 'grind_brewing_parser'):
            # Use grind/brewing parser from integration service
            self.grind_brewing_parser = integration_service.grind_brewing_parser
        else:
            # Fallback to individual initialization (legacy support)
            self.grind_brewing_parser = GrindBrewingParser() if GrindBrewingParser else None
        
        # Initialize parser services from integration service
        if integration_service:
            # Store individual parser services for direct access
            self.tag_normalization_service = getattr(integration_service, 'tag_normalization_service', None)
            self.notes_extraction_service = getattr(integration_service, 'notes_extraction_service', None)
            
            # Use services from integration service
            self.deduplication_service = getattr(integration_service, 'image_deduplication_service', None)
            self.imagekit_integration = getattr(integration_service, 'imagekit_integration', None)
            self.enable_image_deduplication = getattr(integration_service.config, 'enable_image_deduplication', False)
            self.enable_imagekit = getattr(integration_service.config, 'enable_imagekit_upload', False)
        else:
            # Initialize parser services as None when no integration service
            self.tag_normalization_service = None
            self.notes_extraction_service = None
            
            # Initialize image deduplication service
            self.enable_image_deduplication = enable_image_deduplication
            self.deduplication_service = None
            
            if enable_image_deduplication and rpc_client and ImageDeduplicationService:
                try:
                    self.deduplication_service = ImageDeduplicationService(rpc_client)
                    logger.info("Image deduplication service initialized")
                except Exception as e:
                    logger.warning(
                        "Failed to initialize image deduplication service",
                        error=str(e)
                    )
                    self.deduplication_service = None
            
            # Initialize ImageKit integration service
            self.enable_imagekit = enable_imagekit
            self.imagekit_config = imagekit_config
            self.imagekit_integration = None
            
            if enable_imagekit and rpc_client and imagekit_config and ImageKitIntegrationService:
                # Validate ImageKit configuration type at runtime
                assert_imagekit_config(
                    imagekit_config, 
                    "ImageKit configuration validation in ArtifactMapper"
                )
                try:
                    self.imagekit_integration = ImageKitIntegrationService(
                        rpc_client=rpc_client,
                        imagekit_config=imagekit_config,
                        enable_deduplication=enable_image_deduplication,
                        enable_imagekit=True
                    )
                    logger.info("ImageKit integration service initialized")
                except Exception as e:
                    logger.warning(
                        "Failed to initialize ImageKit integration service",
                        error=str(e)
                    )
                    self.imagekit_integration = None
        
        # Initialize image processing guard
        self.metadata_only = metadata_only
        if ImageProcessingGuard:
            self.image_guard = ImageProcessingGuard(metadata_only=metadata_only)
            logger.info(
                "Image processing guard initialized",
                metadata_only=metadata_only
            )
        else:
            self.image_guard = None
            logger.warning("Image processing guard not available")
    
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
                # Note: coffee_id will be available after coffee upsert in the pipeline
                # For now, we'll process images without coffee_id (deduplication will work at image level)
                # Use a temporary coffee_id for deduplication or ImageKit integration if service is available
                temp_coffee_id = f"temp-{artifact.product.platform_product_id}" if (self.deduplication_service or self.imagekit_integration) else None
                images_payloads = self._map_images_data(artifact, coffee_id=temp_coffee_id)
            
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
        
        # Use C.8 normalizer pipeline if available
        if self.normalizer_pipeline:
            return self._map_coffee_data_with_pipeline(artifact, roaster_id)
        
        # Fallback to individual parsers (legacy behavior)
        return self._map_coffee_data_legacy(artifact, roaster_id)
    
    def _map_coffee_data_with_pipeline(self, artifact: ArtifactModel, roaster_id: str) -> Dict[str, Any]:
        """
        Map artifact to coffee RPC payload using C.8 normalizer pipeline.
        
        Args:
            artifact: Canonical artifact model
            roaster_id: Roaster ID
            
        Returns:
            Coffee RPC payload
        """
        product = artifact.product
        normalization = artifact.normalization
        
        # Convert artifact to dictionary for pipeline processing
        artifact_dict = {
            'product': {
                'title': product.title,
                'description_html': product.description_html,
                'platform_product_id': product.platform_product_id,
                'source_url': product.source_url
            },
            'variants': [
                {
                    'weight': variant.weight,
                    'price': variant.price,
                    'currency': variant.currency,
                    'grind': variant.grind,
                    'availability': variant.availability
                } for variant in product.variants
            ],
            'roaster_id': roaster_id
        }
        
        # Process through normalizer pipeline
        try:
            pipeline_result = self.normalizer_pipeline.process_artifact(artifact_dict)
            
            # Extract normalized data from pipeline result
            normalized_data = pipeline_result.get('normalized_data', {})
            pipeline_warnings = pipeline_result.get('warnings', [])
            pipeline_errors = pipeline_result.get('errors', [])
            
            # Log pipeline processing results
            if pipeline_warnings:
                logger.warning("Normalizer pipeline warnings", 
                              warnings=pipeline_warnings,
                              artifact_id=product.platform_product_id)
            
            if pipeline_errors:
                logger.error("Normalizer pipeline errors", 
                            errors=pipeline_errors,
                            artifact_id=product.platform_product_id)
            
        except Exception as e:
            logger.error("Normalizer pipeline failed, falling back to legacy parsing", 
                        error=str(e),
                        artifact_id=product.platform_product_id)
            # Fallback to legacy parsing
            return self._map_coffee_data_legacy(artifact, roaster_id)
        
        # Map required fields using pipeline results
        coffee_payload = {
            'p_bean_species': normalized_data.get('bean_species'),
            'p_name': normalized_data.get('coffee_name', product.title),
            'p_slug': self._map_coffee_slug(product),
            'p_roaster_id': roaster_id,
            'p_process': normalized_data.get('process_method'),
            'p_process_raw': normalized_data.get('process_method_raw'),
            'p_roast_level': normalized_data.get('roast_level'),
            'p_roast_level_raw': normalized_data.get('roast_level_raw'),
            'p_roast_style_raw': normalized_data.get('roast_style_raw'),
            'p_description_md': normalized_data.get('description_cleaned', product.description_html),
            'p_direct_buy_url': product.source_url,
            'p_platform_product_id': product.platform_product_id
        }
        
        # Map cleaned text fields (Epic C.7)
        coffee_payload['p_title_cleaned'] = normalized_data.get('title_cleaned', product.title)
        coffee_payload['p_description_cleaned'] = normalized_data.get('description_cleaned', product.description_html)
        
        # Map optional fields from pipeline results
        if normalized_data.get('bean_species'):
            coffee_payload['p_bean_species'] = normalized_data['bean_species']
        
        # Map decaf flag (infer from product title/description)
        decaf = self._infer_decaf_flag(product)
        if decaf is not None:
            coffee_payload['p_decaf'] = decaf
        
        # Map raw data with pipeline results
        coffee_payload['p_source_raw'] = self._build_source_raw_with_pipeline(artifact, normalized_data)
        coffee_payload['p_notes_raw'] = self._build_notes_raw_with_pipeline(normalized_data)
        
        # Map tags from pipeline results
        if normalized_data.get('tags'):
            coffee_payload['p_tags'] = normalized_data['tags']
        
        # Map notes from pipeline results
        if normalized_data.get('notes'):
            coffee_payload['p_notes_raw'] = normalized_data['notes']
        
        # Map varieties from pipeline results
        if normalized_data.get('varieties'):
            coffee_payload['p_varieties'] = normalized_data['varieties']
        
        # Map geographic data from pipeline results
        if normalized_data.get('geographic_data'):
            geo_data = normalized_data['geographic_data']
            if geo_data.get('region'):
                coffee_payload['p_region'] = geo_data['region']
            if geo_data.get('country'):
                coffee_payload['p_country'] = geo_data['country']
            if geo_data.get('altitude'):
                coffee_payload['p_altitude'] = geo_data['altitude']
        
        # Map sensory data from pipeline results
        if normalized_data.get('sensory_data'):
            sensory_data = normalized_data['sensory_data']
            if sensory_data.get('acidity') is not None:
                coffee_payload['p_acidity'] = sensory_data['acidity']
            if sensory_data.get('body') is not None:
                coffee_payload['p_body'] = sensory_data['body']
        
        # Map hash data from pipeline results
        if normalized_data.get('content_hash'):
            coffee_payload['p_content_hash'] = normalized_data['content_hash']
        
        # Map default grind from variant grind data
        default_grind = self._determine_default_grind(artifact.product.variants)
        if default_grind:
            coffee_payload['p_default_grind'] = default_grind
        
        self.mapping_stats['coffee_mapped'] += 1
        
        return coffee_payload
    
    def _build_source_raw_with_pipeline(self, artifact: ArtifactModel, normalized_data: Dict[str, Any]) -> Dict[str, Any]:
        """Build source_raw data with pipeline results."""
        source_raw = {
            'original_title': artifact.product.title,
            'original_description': artifact.product.description_html,
            'platform_product_id': artifact.product.platform_product_id,
            'source_url': artifact.product.source_url,
            'pipeline_processed': True,
            'pipeline_timestamp': normalized_data.get('pipeline_timestamp'),
            'pipeline_confidence': normalized_data.get('overall_confidence'),
            'pipeline_warnings': normalized_data.get('pipeline_warnings', []),
            'pipeline_errors': normalized_data.get('pipeline_errors', [])
        }
        
        # Add pipeline-specific data
        if normalized_data.get('llm_fallback_used'):
            source_raw['llm_fallback_used'] = normalized_data['llm_fallback_used']
            source_raw['llm_fallback_fields'] = normalized_data.get('llm_fallback_fields', [])
        
        return source_raw
    
    def _build_notes_raw_with_pipeline(self, normalized_data: Dict[str, Any]) -> Dict[str, Any]:
        """Build notes_raw data with pipeline results."""
        notes_raw = {
            'pipeline_processed': True,
            'pipeline_timestamp': normalized_data.get('pipeline_timestamp'),
            'pipeline_confidence': normalized_data.get('overall_confidence')
        }
        
        # Add extracted notes from pipeline
        if normalized_data.get('notes'):
            notes_raw['extracted_notes'] = normalized_data['notes']
        
        # Add processing warnings and errors
        if normalized_data.get('pipeline_warnings'):
            notes_raw['processing_warnings'] = normalized_data['pipeline_warnings']
        
        if normalized_data.get('pipeline_errors'):
            notes_raw['processing_errors'] = normalized_data['pipeline_errors']
        
        return notes_raw
    
    def _map_coffee_data_legacy(self, artifact: ArtifactModel, roaster_id: str) -> Dict[str, Any]:
        """
        Map artifact to coffee RPC payload using legacy individual parsers.
        
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
            'p_bean_species': self._map_bean_species(normalization, product),
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
        
        # Map cleaned text fields (Epic C.7)
        title_cleaned = self._map_coffee_name(product, normalization)
        description_cleaned = self._map_description_md(product, normalization)
        coffee_payload['p_title_cleaned'] = title_cleaned
        coffee_payload['p_description_cleaned'] = description_cleaned
        
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
        
        # Map tags using tag normalization service
        if self.integration_service and self.integration_service.tag_normalization_service:
            tags = self._extract_and_normalize_tags(product)
            if tags:
                coffee_payload['p_tags'] = tags
        
        # Map notes using notes extraction service
        if self.notes_extraction_service:
            notes = self._extract_notes_from_description(product)
            if notes:
                # Add notes to existing notes_raw or create new structure
                existing_notes = coffee_payload.get('p_notes_raw', {})
                if not isinstance(existing_notes, dict):
                    existing_notes = {}
                existing_notes['extracted_notes'] = notes
                coffee_payload['p_notes_raw'] = existing_notes
        
        self.mapping_stats['coffee_mapped'] += 1
        
        # Map default grind from variant grind data
        default_grind = self._determine_default_grind(artifact.product.variants)
        if default_grind:
            coffee_payload['p_default_grind'] = default_grind
        
        # Map varieties using variety extraction service
        if self.integration_service and self.integration_service.variety_parser:
            varieties = self._extract_varieties_from_description(product)
            if varieties:
                coffee_payload['p_varieties'] = varieties
        
        # Map geographic data using geographic parser service
        if self.integration_service and self.integration_service.geographic_parser:
            geographic_data = self._extract_geographic_from_description(product)
            if geographic_data:
                if geographic_data.get('region'):
                    coffee_payload['p_region'] = geographic_data['region']
                if geographic_data.get('country'):
                    coffee_payload['p_country'] = geographic_data['country']
                if geographic_data.get('altitude'):
                    coffee_payload['p_altitude'] = geographic_data['altitude']
        
        # Map sensory data using sensory parser service
        if self.integration_service and self.integration_service.sensory_parser:
            sensory_data = self._extract_sensory_from_description(product)
            if sensory_data:
                if sensory_data.get('acidity') is not None:
                    coffee_payload['p_acidity'] = sensory_data['acidity']
                if sensory_data.get('body') is not None:
                    coffee_payload['p_body'] = sensory_data['body']
        
        # Map hash data using hash generation service
        if self.integration_service and self.integration_service.hash_service:
            hash_data = self._generate_hashes_for_artifact(artifact)
            if hash_data:
                if hash_data.get('content_hash'):
                    coffee_payload['p_content_hash'] = hash_data['content_hash']
                if hash_data.get('raw_hash'):
                    coffee_payload['p_raw_hash'] = hash_data['raw_hash']
        
        return coffee_payload
    
    def _determine_default_grind(self, variants: List[VariantModel]) -> Optional[str]:
        """
        Determine the default grind for a coffee from its variants.
        
        Uses heuristics:
        1. If any variant is "whole bean", use that (highest priority)
        2. Otherwise, use the most common grind type
        3. If tied, prefer more specific grinds over generic ones
        
        Args:
            variants: List of product variants
            
        Returns:
            Default grind type or None if no grind data available
        """
        if not self.grind_brewing_parser or not variants:
            return None
        
        grind_counts = {}
        grind_confidence = {}
        
        # Parse grind types from all variants
        for variant in variants:
            try:
                # Convert variant to dict format for parser
                variant_dict = {
                    'title': variant.title or '',
                    'options': variant.options or [],
                    'attributes': getattr(variant, 'attributes', [])
                }
                
                grind_result = self.grind_brewing_parser.parse_grind_brewing(variant_dict)
                
                if grind_result.grind_type != 'unknown' and grind_result.confidence > 0.5:
                    grind_type = grind_result.grind_type
                    
                    # Count occurrences
                    grind_counts[grind_type] = grind_counts.get(grind_type, 0) + 1
                    
                    # Track confidence (use highest confidence for each type)
                    if grind_type not in grind_confidence or grind_result.confidence > grind_confidence[grind_type]:
                        grind_confidence[grind_type] = grind_result.confidence
                        
            except Exception as e:
                logger.warning(
                    "Failed to parse grind for default determination",
                    platform_variant_id=variant.platform_variant_id,
                    error=str(e)
                )
                continue
        
        if not grind_counts:
            return None
        
        # Priority 1: If "whole" bean is available, use it (highest priority)
        if 'whole' in grind_counts:
            return 'whole'
        
        # Priority 2: Find the most common grind type
        max_count = max(grind_counts.values())
        most_common_grinds = [grind for grind, count in grind_counts.items() if count == max_count]
        
        if len(most_common_grinds) == 1:
            return most_common_grinds[0]
        
        # Priority 3: If tied, prefer more specific grinds over generic ones
        # Order of preference (more specific to less specific)
        preference_order = [
            'south_indian_filter', 'turkish', 'cold_brew', 'aeropress', 'moka_pot',
            'french_press', 'pour_over', 'syphon', 'espresso', 'filter', 'omni'
        ]
        
        for preferred_grind in preference_order:
            if preferred_grind in most_common_grinds:
                return preferred_grind
        
        # Fallback: return the first most common grind
        return most_common_grinds[0]
    
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
                
                # Map grind type using enhanced grind/brewing parser
                if self.grind_brewing_parser:
                    try:
                        # Convert variant to dict format for parser
                        variant_dict = {
                            'title': variant.title or '',
                            'options': variant.options or [],
                            'attributes': getattr(variant, 'attributes', [])
                        }
                        
                        grind_result = self.grind_brewing_parser.parse_grind_brewing(variant_dict)
                        
                        if grind_result.grind_type != 'unknown':
                            variant_payload['p_grind'] = grind_result.grind_type
                            
                            # Add parsing metadata to source_raw
                            if 'p_source_raw' not in variant_payload:
                                variant_payload['p_source_raw'] = {}
                            
                            variant_payload['p_source_raw']['grind_brewing_parsing'] = grind_result.to_dict()
                            
                            # Log parsing warnings if any
                            if grind_result.warnings:
                                logger.warning(
                                    "Grind/brewing parsing warnings",
                                    platform_variant_id=variant.platform_variant_id,
                                    warnings=grind_result.warnings,
                                    grind_type=grind_result.grind_type,
                                    confidence=grind_result.confidence
                                )
                    except Exception as e:
                        logger.warning(
                            "Failed to parse grind/brewing for variant",
                            platform_variant_id=variant.platform_variant_id,
                            error=str(e)
                        )
                
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
    
    def _map_images_data(self, artifact: ArtifactModel, coffee_id: str = None) -> List[Dict[str, Any]]:
        """
        Map artifact images to RPC payloads with deduplication support.
        
        Args:
            artifact: Canonical artifact model
            coffee_id: Coffee ID for deduplication (optional)
            
        Returns:
            List of image RPC payloads
        """
        # Check if image processing is allowed (guard enforcement)
        if self.image_guard and not self.image_guard.check_image_processing_allowed("map_images_data"):
            logger.info(
                "Image processing blocked by guard for price-only run",
                operation="map_images_data",
                metadata_only=self.metadata_only
            )
            return []
        images_payloads = []
        
        if artifact.product.images:
            # Process images with deduplication service if available and enabled
            if self.deduplication_service and self.enable_image_deduplication and coffee_id:
                try:
                    # Prepare image data for deduplication
                    images_data = []
                    for i, image in enumerate(artifact.product.images):
                        image_data = {
                            'url': image.url,
                            'alt': image.alt_text or '',
                            'width': getattr(image, 'width', None),
                            'height': getattr(image, 'height', None),
                            'sort_order': image.order or i,
                            'source_raw': {
                                'source_id': image.source_id,
                                'scraped_at': artifact.scraped_at.isoformat()
                            }
                        }
                        images_data.append(image_data)
                    
                    # Process images with deduplication
                    processed_images = self.deduplication_service.process_batch_with_deduplication(
                        images_data, coffee_id
                    )
                    
                    # Convert processed results to RPC payloads
                    for processed_image in processed_images:
                        if 'error' in processed_image:
                            logger.warning(
                                "Failed to process image with deduplication",
                                image_url=processed_image.get('url'),
                                error=processed_image['error']
                            )
                            continue
                        
                        # Create RPC payload for image
                        image_payload = {
                            'p_url': processed_image['url'],
                            'p_alt': processed_image.get('alt', ''),
                            'p_sort_order': processed_image.get('sort_order', 0),
                            'p_source_raw': processed_image.get('source_raw', {}),
                            'p_content_hash': processed_image.get('content_hash'),
                            'p_deduplication_status': processed_image.get('deduplication_status', 'unknown')
                        }
                        
                        # Add existing image ID if it's a duplicate
                        if processed_image.get('is_duplicate') and processed_image.get('image_id'):
                            image_payload['p_existing_image_id'] = processed_image['image_id']
                        
                        # Add dimensions if available
                        if processed_image.get('width'):
                            image_payload['p_width'] = processed_image['width']
                        if processed_image.get('height'):
                            image_payload['p_height'] = processed_image['height']
                        
                        images_payloads.append(image_payload)
                        self.mapping_stats['images_mapped'] += 1
                    
                    logger.info(
                        "Processed images with deduplication",
                        total_images=len(artifact.product.images),
                        processed_count=len(images_payloads)
                    )
                    
                except Exception as e:
                    logger.error(
                        "Failed to process images with deduplication service",
                        error=str(e)
                    )
                    # Fall back to standard processing
                    images_payloads = self._map_images_data_standard(artifact)
            # Process images with ImageKit integration if service is available and enabled
            elif self.imagekit_integration and self.enable_imagekit and coffee_id:
                try:
                    # Prepare image data for deduplication
                    images_data = []
                    for i, image in enumerate(artifact.product.images):
                        image_data = {
                            'url': image.url,
                            'alt': image.alt_text or '',
                            'width': getattr(image, 'width', None),
                            'height': getattr(image, 'height', None),
                            'sort_order': image.order or i,
                            'source_raw': {
                                'source_id': image.source_id,
                                'scraped_at': artifact.scraped_at.isoformat()
                            }
                        }
                        images_data.append(image_data)
                    
                    # Process images with ImageKit integration
                    processed_images = self.imagekit_integration.process_batch_with_imagekit(
                        images_data, coffee_id
                    )
                    
                    # Convert processed results to RPC payloads
                    for processed_image in processed_images:
                        if 'integration_error' in processed_image:
                            logger.warning(
                                "Failed to process image with ImageKit integration",
                                image_url=processed_image.get('url'),
                                error=processed_image['integration_error']
                            )
                            continue
                        
                        # Create RPC payload
                        image_payload = {
                            'p_url': processed_image['url'],
                            'p_alt': processed_image.get('alt', ''),
                            'p_sort_order': processed_image.get('sort_order', 0),
                            'p_source_raw': processed_image.get('source_raw', {})
                        }
                        
                        # Add dimensions if available
                        if processed_image.get('width'):
                            image_payload['p_width'] = processed_image['width']
                        if processed_image.get('height'):
                            image_payload['p_height'] = processed_image['height']
                        
                        # Add content hash for deduplication
                        if processed_image.get('content_hash'):
                            image_payload['p_content_hash'] = processed_image['content_hash']
                        
                        # Add ImageKit URL if available
                        if processed_image.get('imagekit_url'):
                            image_payload['p_imagekit_url'] = processed_image['imagekit_url']
                        
                        # Add processing metadata
                        if processed_image.get('imagekit_upload_skipped'):
                            image_payload['p_processing_status'] = 'skipped_duplicate'
                            image_payload['p_existing_image_id'] = processed_image.get('existing_image_id')
                        elif processed_image.get('imagekit_upload_failed'):
                            image_payload['p_processing_status'] = 'imagekit_failed'
                            image_payload['p_fallback_url'] = processed_image.get('fallback_url')
                        else:
                            image_payload['p_processing_status'] = 'processed'
                        
                        images_payloads.append(image_payload)
                        self.mapping_stats['images_mapped'] += 1
                        
                        # Log processing result
                        if processed_image.get('imagekit_upload_skipped'):
                            logger.info(
                                "ImageKit integration: duplicate skipped",
                                image_url=processed_image['url'],
                                existing_image_id=processed_image.get('existing_image_id')
                            )
                        elif processed_image.get('imagekit_upload_failed'):
                            logger.warning(
                                "ImageKit integration: upload failed, using fallback",
                                image_url=processed_image['url'],
                                fallback_url=processed_image.get('fallback_url'),
                                error=processed_image.get('imagekit_error')
                            )
                        else:
                            logger.info(
                                "ImageKit integration: image processed successfully",
                                image_url=processed_image['url'],
                                imagekit_url=processed_image.get('imagekit_url'),
                                content_hash=processed_image.get('content_hash')
                            )
                    
                except Exception as e:
                    logger.error(
                        "Failed to process images with ImageKit integration, falling back to standard processing",
                        error=str(e)
                    )
                    # Fall back to standard processing
                    images_payloads = self._map_images_data_standard(artifact)
            else:
                # Standard processing without ImageKit integration
                images_payloads = self._map_images_data_standard(artifact)
        
        return images_payloads
    
    def _map_images_data_standard(self, artifact: ArtifactModel) -> List[Dict[str, Any]]:
        """
        Standard image mapping without deduplication.
        
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
    
    def _map_bean_species(self, normalization: Optional[NormalizationModel], product: Optional[ProductModel] = None) -> Optional[str]:
        """Map bean species from normalization data or parse from product content."""
        # First check if species is already in normalization data
        if normalization and normalization.bean_species:
            return normalization.bean_species.value
        
        # If not found and species parser is available, try parsing from product content
        if (self.integration_service and 
            self.integration_service.species_parser and 
            product):
            try:
                species_result = self.integration_service.species_parser.parse_species(
                    title=product.title,
                    description=product.description or ''
                )
                
                # Only use parsed species if confidence is above threshold
                if (species_result.species != 'unknown' and 
                    species_result.confidence >= self.integration_service.species_parser.config.confidence_threshold):
                    return species_result.species
                    
            except Exception as e:
                logger.warning(
                    "Species parsing failed during mapping",
                    product_title=product.title,
                    error=str(e)
                )
        
        return None  # Return None when not defined
    
    def _map_coffee_name(self, product: ProductModel, normalization: Optional[NormalizationModel]) -> str:
        """Map coffee name from product and normalization data."""
        if normalization and normalization.name_clean:
            return normalization.name_clean
        
        # Use original title as base
        title = product.title
        
        # Apply text cleaning if service is available
        if self.integration_service and self.integration_service.text_cleaning_service:
            try:
                cleaning_result = self.integration_service.text_cleaning_service.clean_text(title)
                title = cleaning_result.cleaned_text
                logger.debug(
                    "Applied text cleaning to coffee name",
                    original=product.title,
                    cleaned=title,
                    confidence=cleaning_result.confidence,
                    changes=cleaning_result.changes_made
                )
            except Exception as e:
                logger.warning(
                    "Text cleaning failed for coffee name, using original",
                    title=title,
                    error=str(e)
                )
        
        # Apply text normalization if service is available
        if self.integration_service and self.integration_service.text_normalization_service:
            try:
                normalization_result = self.integration_service.text_normalization_service.normalize_text(title)
                title = normalization_result.normalized_text
                logger.debug(
                    "Applied text normalization to coffee name",
                    original=product.title,
                    normalized=title,
                    confidence=normalization_result.confidence,
                    changes=normalization_result.changes_made
                )
            except Exception as e:
                logger.warning(
                    "Text normalization failed for coffee name, using cleaned text",
                    title=title,
                    error=str(e)
                )
        
        return title
    
    def _map_coffee_slug(self, product: ProductModel) -> str:
        """Map coffee slug from product data."""
        if product.slug:
            return product.slug
        elif product.handle:
            return product.handle
        else:
            # Generate slug from title
            return product.title.lower().replace(' ', '-').replace('_', '-')
    
    def _map_process(self, normalization: Optional[NormalizationModel]) -> Optional[str]:
        """Map process method from normalization data."""
        if normalization and normalization.process_enum:
            return normalization.process_enum.value
        return None  # Return None when not defined
    
    def _map_process_raw(self, normalization: Optional[NormalizationModel]) -> Optional[str]:
        """Map raw process description from normalization data."""
        if normalization and normalization.process_raw:
            return normalization.process_raw
        return None  # Return None when not defined
    
    def _map_roast_level(self, normalization: Optional[NormalizationModel]) -> Optional[str]:
        """Map roast level from normalization data."""
        if normalization and normalization.roast_level_enum:
            return normalization.roast_level_enum.value
        return None  # Return None when not defined
    
    def _map_roast_level_raw(self, normalization: Optional[NormalizationModel]) -> Optional[str]:
        """Map raw roast level description from normalization data."""
        if normalization and normalization.roast_level_raw:
            return normalization.roast_level_raw
        return None  # Return None when not defined
    
    def _map_roast_style_raw(self, normalization: Optional[NormalizationModel]) -> str:
        """Map roast style description from normalization data."""
        if normalization and normalization.roast_level_raw:
            return normalization.roast_level_raw
        return 'Unknown'  # Default
    
    def _map_description_md(self, product: ProductModel, normalization: Optional[NormalizationModel]) -> str:
        """Map description from product and normalization data."""
        if normalization and normalization.description_md_clean:
            return normalization.description_md_clean
        
        # Determine base description
        description = None
        if product.description_md:
            description = product.description_md
        elif product.description_html:
            # Convert HTML to markdown (basic conversion)
            description = self._html_to_markdown(product.description_html)
        else:
            return 'No description available'
        
        # Apply text cleaning if service is available
        if self.integration_service and self.integration_service.text_cleaning_service:
            try:
                cleaning_result = self.integration_service.text_cleaning_service.clean_text(description)
                description = cleaning_result.cleaned_text
                logger.debug(
                    "Applied text cleaning to description",
                    original=product.description_md or product.description_html,
                    cleaned=description,
                    confidence=cleaning_result.confidence,
                    changes=cleaning_result.changes_made
                )
            except Exception as e:
                logger.warning(
                    "Text cleaning failed for description, using original",
                    description=description,
                    error=str(e)
                )
        
        # Apply text normalization if service is available
        if self.integration_service and self.integration_service.text_normalization_service:
            try:
                normalization_result = self.integration_service.text_normalization_service.normalize_text(description)
                description = normalization_result.normalized_text
                logger.debug(
                    "Applied text normalization to description",
                    original=product.description_md or product.description_html,
                    normalized=description,
                    confidence=normalization_result.confidence,
                    changes=normalization_result.changes_made
                )
            except Exception as e:
                logger.warning(
                    "Text normalization failed for description, using cleaned text",
                    description=description,
                    error=str(e)
                )
        
        return description
    
    def _map_weight_grams(self, variant: VariantModel) -> int:
        """Map variant weight to grams using enhanced weight parser."""
        try:
            # If we already have grams, use them
            if variant.grams:
                return variant.grams
            
            # Try to parse weight from variant title using weight parser
            if self.weight_parser and variant.title:
                weight_result = self.weight_parser.parse_weight(variant.title)
                if weight_result.grams > 0:
                    logger.debug(
                        "Parsed weight from variant title",
                        variant_id=variant.platform_variant_id,
                        title=variant.title,
                        parsed_grams=weight_result.grams,
                        confidence=weight_result.confidence
                    )
                    return weight_result.grams
            
            # Fallback to weight unit conversion if available
            if variant.weight_unit and variant.weight_unit.value == 'kg':
                # Convert kg to grams (assuming we have a weight value)
                return 1000  # Default 1kg
            else:
                return 250  # Default 250g
                
        except Exception as e:
            logger.warning(
                "Failed to parse weight from variant",
                variant_id=variant.platform_variant_id,
                title=variant.title,
                error=str(e)
            )
            # Return default weight
            return 250
    
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
    
    def _extract_and_normalize_tags(self, product) -> Optional[List[str]]:
        """
        Extract and normalize tags from product data.
        
        Args:
            product: Product model
            
        Returns:
            List of normalized tags or None if no tags found
        """
        try:
            if not self.tag_normalization_service:
                return None
            
            # Extract tags from product data
            raw_tags = []
            
            # Get tags from product title and description
            if product.title:
                # Split title into potential tags
                title_words = product.title.lower().split()
                raw_tags.extend(title_words)
            
            if product.description_html:
                # Extract potential tags from description
                description_text = self._html_to_markdown(product.description_html)
                description_words = description_text.lower().split()
                raw_tags.extend(description_words)
            
            if product.description_md:
                # Extract potential tags from markdown description
                md_words = product.description_md.lower().split()
                raw_tags.extend(md_words)
            
            # Remove duplicates and filter
            raw_tags = list(set([tag.strip() for tag in raw_tags if len(tag.strip()) > 2]))
            
            if not raw_tags:
                return None
            
            # Normalize tags using the service
            result = self.tag_normalization_service.normalize_tags(raw_tags)
            
            # Return normalized tags as a flat list
            normalized_tags = []
            for category, tags in result.normalized_tags.items():
                normalized_tags.extend(tags)
            
            logger.info(
                "Tag normalization completed",
                product_id=product.platform_product_id,
                raw_tags_count=len(raw_tags),
                normalized_tags_count=len(normalized_tags),
                categories=len(result.normalized_tags)
            )
            
            return normalized_tags if normalized_tags else None
            
        except Exception as e:
            logger.warning(
                "Tag normalization failed",
                product_id=product.platform_product_id,
                error=str(e)
            )
            return None
    
    def _extract_notes_from_description(self, product) -> Optional[List[str]]:
        """
        Extract tasting notes from product description.
        
        Args:
            product: Product model
            
        Returns:
            List of extracted notes or None if no notes found
        """
        try:
            if not self.notes_extraction_service:
                return None
            
            # Combine all description sources
            description_text = ""
            
            if product.description_html:
                description_text += self._html_to_markdown(product.description_html)
            
            if product.description_md:
                description_text += " " + product.description_md
            
            if not description_text.strip():
                return None
            
            # Extract notes using the service
            result = self.notes_extraction_service.extract_notes(description_text)
            
            logger.info(
                "Notes extraction completed",
                product_id=product.platform_product_id,
                description_length=len(description_text),
                notes_count=len(result.notes_raw),
                extraction_success=result.extraction_success
            )
            
            return result.notes_raw if result.notes_raw else None
            
        except Exception as e:
            logger.warning(
                "Notes extraction failed",
                product_id=product.platform_product_id,
                error=str(e)
            )
            return None
    
    def _extract_varieties_from_description(self, product) -> Optional[List[str]]:
        """
        Extract coffee varieties from product description.
        
        Args:
            product: Product model
            
        Returns:
            List of extracted varieties or None if no varieties found
        """
        try:
            if not self.integration_service or not self.integration_service.variety_parser:
                return None
            
            # Combine all description sources
            description_text = ""
            
            if product.description_html:
                description_text += self._html_to_markdown(product.description_html)
            
            if product.description_md:
                description_text += " " + product.description_md
            
            if not description_text.strip():
                return None
            
            # Extract varieties using the service
            result = self.integration_service.variety_parser.extract_varieties(description_text)
            
            logger.info(
                "Variety extraction completed",
                product_id=product.platform_product_id,
                description_length=len(description_text),
                varieties_found=len(result.varieties),
                warnings_count=len(result.warnings)
            )
            
            return result.varieties if result.varieties else None
            
        except Exception as e:
            logger.warning(
                "Variety extraction failed",
                product_id=product.platform_product_id,
                error=str(e)
            )
            return None
    
    def _extract_geographic_from_description(self, product) -> Optional[Dict[str, Any]]:
        """
        Extract geographic data from product description.
        
        Args:
            product: Product model
            
        Returns:
            Dictionary with geographic data or None if no geographic data found
        """
        try:
            if not self.integration_service or not self.integration_service.geographic_parser:
                return None
            
            # Combine all description sources
            description_text = ""
            
            if product.description_html:
                description_text += self._html_to_markdown(product.description_html)
            
            if product.description_md:
                description_text += " " + product.description_md
            
            if not description_text.strip():
                return None
            
            # Extract geographic data using the service
            result = self.integration_service.geographic_parser.parse_geographic(description_text)
            
            logger.info(
                "Geographic parsing completed",
                product_id=product.platform_product_id,
                description_length=len(description_text),
                region=result.region,
                country=result.country,
                state=result.state,
                estate=result.estate,
                altitude=result.altitude,
                confidence=result.confidence,
                warnings_count=len(result.warnings)
            )
            
            # Return only non-unknown values
            geographic_data = {}
            if result.region != 'unknown':
                geographic_data['region'] = result.region
            if result.country != 'unknown':
                geographic_data['country'] = result.country
            if result.state != 'unknown':
                geographic_data['state'] = result.state
            if result.estate != 'unknown':
                geographic_data['estate'] = result.estate
            if result.altitude is not None:
                geographic_data['altitude'] = result.altitude
            
            return geographic_data if geographic_data else None
            
        except Exception as e:
            logger.warning(
                "Geographic parsing failed",
                product_id=product.platform_product_id,
                error=str(e)
            )
            return None
    
    def _extract_sensory_from_description(self, product: ProductModel) -> Optional[Dict[str, Any]]:
        """
        Extract sensory parameters from product description.
        
        Args:
            product: Product model
            
        Returns:
            Dictionary with sensory data or None if no data found
        """
        try:
            if not self.integration_service or not self.integration_service.sensory_parser:
                return None
            
            # Combine all description sources
            description_text = ""
            
            if product.description_html:
                description_text += self._html_to_markdown(product.description_html)
            
            if product.description_md:
                description_text += " " + product.description_md
            
            if not description_text.strip():
                return None
            
            # Parse sensory parameters
            result = self.integration_service.sensory_parser.parse_sensory(description_text)
            
            logger.debug(
                "Sensory parsing completed",
                product_id=product.platform_product_id,
                acidity=result.acidity,
                body=result.body,
                confidence=result.confidence
            )
            
            # Return only non-None values
            sensory_data = {}
            if result.acidity is not None:
                sensory_data['acidity'] = result.acidity
            if result.body is not None:
                sensory_data['body'] = result.body
            
            return sensory_data if sensory_data else None
            
        except Exception as e:
            logger.warning(
                "Sensory parsing failed",
                product_id=product.platform_product_id,
                error=str(e)
            )
            return None
    
    def _generate_hashes_for_artifact(self, artifact: ArtifactModel) -> Optional[Dict[str, str]]:
        """
        Generate content and raw hashes for artifact.
        
        Args:
            artifact: Artifact model
            
        Returns:
            Dictionary with hash data or None if generation failed
        """
        try:
            if not self.integration_service or not self.integration_service.hash_service:
                return None
            
            # Convert artifact to dictionary for hash generation
            artifact_dict = {
                'title': artifact.product.name,
                'description': artifact.product.description_md or '',
                'weight_g': getattr(artifact.normalization, 'weight_g', None) if artifact.normalization else None,
                'roast_level': artifact.normalization.roast_level.value if artifact.normalization and artifact.normalization.roast_level else None,
                'process': artifact.normalization.process.value if artifact.normalization and artifact.normalization.process else None,
                'grind_type': getattr(artifact.normalization, 'grind_type', None) if artifact.normalization else None,
                'species': artifact.normalization.bean_species.value if artifact.normalization and artifact.normalization.bean_species else None
            }
            
            # Generate hashes
            result = self.integration_service.hash_service.generate_hashes(artifact_dict)
            
            logger.debug(
                "Hash generation completed",
                product_id=artifact.product.platform_product_id,
                content_hash=result.content_hash[:16] + "..." if result.content_hash else None,
                raw_hash=result.raw_hash[:16] + "..." if result.raw_hash else None
            )
            
            # Return hash data
            hash_data = {}
            if result.content_hash:
                hash_data['content_hash'] = result.content_hash
            if result.raw_hash:
                hash_data['raw_hash'] = result.raw_hash
            
            return hash_data if hash_data else None
            
        except Exception as e:
            logger.warning(
                "Hash generation failed",
                product_id=artifact.product.platform_product_id,
                error=str(e)
            )
            return None
    
