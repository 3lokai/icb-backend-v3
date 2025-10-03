"""
Firecrawl extract service for coffee product extraction with JavaScript rendering.

This module provides:
- Enhanced Firecrawl extract service with JavaScript rendering support
- Coffee product extraction with dropdown interaction for pricing variations
- Support for multiple size options and pricing variations
- Screenshot capture for debugging dropdown interactions
- Integration with existing normalizer pipeline
- Comprehensive error handling and retry logic
"""

import time
from typing import Dict, List, Optional, Any
from urllib.parse import urlparse
from datetime import datetime, timezone
from structlog import get_logger

from .firecrawl_client import FirecrawlClient, FirecrawlAPIError
from ..parser.normalizer_pipeline import NormalizerPipelineService

logger = get_logger(__name__)


class FirecrawlExtractService:
    """
    Enhanced Firecrawl extract service with JavaScript rendering and dropdown interaction.

    Features:
    - Coffee product extraction with dropdown interaction for pricing variations
    - JavaScript rendering support for complex e-commerce sites
    - Screenshot capture for debugging dropdown interactions
    - Integration with existing C.1-C.8 normalizer pipeline
    - Comprehensive error handling and retry logic
    - Budget tracking and rate limiting
    """

    def __init__(self, firecrawl_client: FirecrawlClient, normalizer_pipeline: NormalizerPipelineService):
        self.client = firecrawl_client
        self.normalizer_pipeline = normalizer_pipeline

        logger.info(
            "Firecrawl extract service initialized",
            client_available=firecrawl_client is not None,
            normalizer_available=normalizer_pipeline is not None
        )

    async def extract_coffee_product_with_pricing(
        self,
        url: str,
        size_options: List[str] = None,
        job_type: str = "full_refresh"
    ) -> Dict[str, Any]:
        """
        Extract coffee product with pricing from dropdowns using Firecrawl JavaScript rendering.

        Args:
            url: Product URL to extract
            size_options: List of size options to test (e.g., ['250g', '500g', '1kg'])
            job_type: Job type - "full_refresh" or "price_only" for Epic B integration

        Returns:
            Dictionary containing extracted product data and normalization results
        """
        start_time = time.time()
        operation_success = False
        error_type = None

        try:
            # Default size options for coffee products
            if not size_options:
                size_options = ['250g', '500g', '1kg', '2lb', '5lb']

            logger.info(
                "Starting coffee product extraction",
                url=url,
                size_options=size_options
            )

            # Build actions for dropdown interaction
            actions = self._build_dropdown_actions(size_options)

            # Coffee product extraction schema
            schema = self._get_coffee_extraction_schema()

            # Extract with JavaScript rendering and dropdown interaction
            raw_data = await self.client.extract_coffee_product(url, size_options, actions, schema)

            # Convert to canonical artifact format
            artifact = self._convert_coffee_artifact(raw_data, url)

            # Feed through existing normalizer pipeline
            normalized_result = self.normalizer_pipeline.process_artifact(artifact)

            operation_success = True
            processing_time = time.time() - start_time

            logger.info(
                "Coffee product extraction completed",
                url=url,
                processing_time=processing_time,
                success=operation_success
            )

            return {
                'raw_data': raw_data,
                'artifact': artifact,
                'normalized_result': normalized_result,
                'processing_time': processing_time,
                'success': operation_success
            }

        except Exception as e:
            error_type = type(e).__name__
            processing_time = time.time() - start_time

            logger.error(
                "Coffee product extraction failed",
                url=url,
                error=str(e),
                error_type=error_type,
                processing_time=processing_time
            )

            raise FirecrawlAPIError(f"Extraction failed: {str(e)}")

    def _build_dropdown_actions(self, size_options: List[str]) -> List[Dict[str, Any]]:
        """Build actions for dropdown interaction with different size options."""
        actions = []

        for size in size_options:
            actions.extend([
                {"type": "wait", "milliseconds": 1000},
                {"type": "click", "selector": "select, .size-selector, .weight-selector"},
                {"type": "wait", "milliseconds": 500},
                {"type": "click", "selector": f"option:contains('{size}')"},
                {"type": "wait", "milliseconds": 1500},
                {"type": "screenshot"}
            ])

        return actions

    def _get_coffee_extraction_schema(self) -> Dict[str, Any]:
        """Get coffee product extraction schema for Firecrawl."""
        return {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "roaster": {"type": "string"},
                "origin": {"type": "string"},
                "roast_level": {"type": "string"},
                "price_variations": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "size": {"type": "string"},
                            "price": {"type": "string"},
                            "currency": {"type": "string"},
                            "availability": {"type": "string"}
                        }
                    }
                },
                "description": {"type": "string"},
                "tasting_notes": {"type": "array", "items": {"type": "string"}},
                "images": {"type": "array", "items": {"type": "string"}}
            },
            "required": ["name", "price_variations"]
        }

    def _convert_coffee_artifact(self, raw_data: Dict[str, Any], source_url: str) -> Dict[str, Any]:
        """
        Convert Firecrawl output to canonical artifact format.

        Args:
            raw_data: Raw Firecrawl extraction data
            source_url: Original product URL

        Returns:
            Canonical artifact dictionary
        """
        try:
            # Extract domain from source URL
            parsed_url = urlparse(source_url)
            roaster_domain = parsed_url.netloc

            # Map Firecrawl product data to canonical format
            product_data = {
                "platform_product_id": self._extract_product_id(raw_data, source_url),
                "platform": "other",  # Firecrawl is not a platform
                "title": raw_data.get("name", ""),
                "source_url": source_url,
                "description_html": raw_data.get("description", ""),
                "description_md": raw_data.get("description", ""),
                "tags": self._extract_tags(raw_data),
                "images": self._convert_images(raw_data.get("images", [])),
                "variants": self._convert_variants(raw_data.get("price_variations", []))
            }

            # Create canonical artifact
            artifact = {
                "source": "firecrawl",
                "roaster_domain": roaster_domain,
                "scraped_at": datetime.now(timezone.utc).isoformat(),
                "product": product_data,
                "normalization": {
                    "is_coffee": True,
                    "parsing_warnings": []
                }
            }

            logger.info(
                "Artifact conversion completed",
                roaster_domain=roaster_domain,
                product_id=product_data["platform_product_id"],
                variants_count=len(product_data["variants"])
            )

            return artifact

        except Exception as e:
            logger.error("Artifact conversion failed", error=str(e))
            raise ValueError(f"Failed to convert Firecrawl data to canonical format: {str(e)}")

    def _extract_product_id(self, raw_data: Dict[str, Any], source_url: str) -> str:
        """Extract or generate product ID from Firecrawl data."""
        # Try to extract from raw data first
        if "id" in raw_data:
            return str(raw_data["id"])

        # Generate from URL path
        parsed_url = urlparse(source_url)
        path_parts = [p for p in parsed_url.path.split('/') if p]
        if path_parts:
            return path_parts[-1]

        # Fallback to URL hash
        return str(hash(source_url))

    def _extract_tags(self, raw_data: Dict[str, Any]) -> List[str]:
        """Extract tags from Firecrawl data."""
        tags = []

        # Add roaster if available
        if raw_data.get("roaster"):
            tags.append(f"roaster:{raw_data['roaster']}")

        # Add origin if available
        if raw_data.get("origin"):
            tags.append(f"origin:{raw_data['origin']}")

        # Add roast level if available
        if raw_data.get("roast_level"):
            tags.append(f"roast:{raw_data['roast_level']}")

        # Add tasting notes as tags
        tasting_notes = raw_data.get("tasting_notes", [])
        for note in tasting_notes:
            if isinstance(note, str):
                tags.append(f"tasting:{note}")

        return tags

    def _convert_images(self, image_urls: List[str]) -> List[Dict[str, Any]]:
        """Convert image URLs to canonical image format."""
        images = []

        for i, url in enumerate(image_urls):
            if isinstance(url, str) and url.strip():
                images.append({
                    "url": url.strip(),
                    "alt_text": f"Product image {i + 1}",
                    "order": i,
                    "source_id": f"firecrawl_{i}"
                })

        return images

    def _convert_variants(self, price_variations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert price variations to canonical variant format."""
        variants = []

        for i, variation in enumerate(price_variations):
            if isinstance(variation, dict):
                variant = {
                    "platform_variant_id": f"firecrawl_{i}",
                    "title": variation.get("size", f"Size {i + 1}"),
                    "price": variation.get("price", "0"),
                    "currency": variation.get("currency", "USD"),
                    "in_stock": variation.get("availability", "in_stock") == "in_stock",
                    "raw_variant_json": variation
                }

                # Try to extract weight from size
                size = variation.get("size", "")
                weight = self._extract_weight_from_size(size)
                if weight:
                    variant["grams"] = weight
                    variant["weight_unit"] = "g"

                variants.append(variant)

        return variants

    def _extract_weight_from_size(self, size: str) -> Optional[int]:
        """Extract weight in grams from size string."""
        if not isinstance(size, str):
            return None

        size_lower = size.lower()

        # Look for weight patterns
        import re

        # Pattern for grams (e.g., "250g", "500g")
        gram_match = re.search(r'(\d+)\s*g', size_lower)
        if gram_match:
            return int(gram_match.group(1))

        # Pattern for kilograms (e.g., "1kg", "2kg")
        kg_match = re.search(r'(\d+(?:\.\d+)?)\s*kg', size_lower)
        if kg_match:
            return int(float(kg_match.group(1)) * 1000)

        # Pattern for pounds (e.g., "1lb", "2lb")
        lb_match = re.search(r'(\d+(?:\.\d+)?)\s*lb', size_lower)
        if lb_match:
            return int(float(lb_match.group(1)) * 453.592)  # Convert pounds to grams

        return None

    async def extract_price_only_data(
        self,
        url: str,
        job_type: str = "price_only"
    ) -> Dict[str, Any]:
        """
        Extract price-only data for cost optimization.

        Args:
            url: Product URL to extract
            job_type: Job type - "price_only" for Epic B integration

        Returns:
            Dictionary containing price-only data
        """
        if job_type != "price_only":
            logger.warning(
                "extract_price_only_data called with non-price-only job type",
                job_type=job_type
            )
            return {}

        start_time = time.time()
        operation_success = False

        try:
            logger.info(
                "Starting price-only data extraction",
                url=url,
                job_type=job_type
            )

            # Price-only extraction schema - focus on price/availability data only
            schema = self._get_price_only_extraction_schema()

            # Extract with minimal JavaScript rendering for cost optimization
            raw_data = await self.client.extract_price_only_data(url, schema)

            # Convert to price-only artifact format
            artifact = self._convert_price_only_artifact(raw_data, url)

            # Process through normalizer pipeline for price data only
            normalized_result = self.normalizer_pipeline.process_price_only_artifact(artifact)

            operation_success = True
            processing_time = time.time() - start_time

            logger.info(
                "Price-only data extraction completed",
                url=url,
                processing_time=processing_time,
                success=operation_success
            )

            return {
                'raw_data': raw_data,
                'artifact': artifact,
                'normalized_result': normalized_result,
                'processing_time': processing_time,
                'success': operation_success,
                'job_type': job_type
            }

        except Exception as e:
            processing_time = time.time() - start_time

            logger.error(
                "Price-only data extraction failed",
                url=url,
                error=str(e),
                processing_time=processing_time
            )

            raise FirecrawlAPIError(f"Price-only extraction failed: {str(e)}")

    def _get_price_only_extraction_schema(self) -> Dict[str, Any]:
        """Get price-only extraction schema for cost optimization."""
        return {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "price_variations": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "size": {"type": "string"},
                            "price": {"type": "string"},
                            "currency": {"type": "string"},
                            "availability": {"type": "string"}
                        }
                    }
                }
            },
            "required": ["price_variations"]
        }

    def _convert_price_only_artifact(self, raw_data: Dict[str, Any], source_url: str) -> Dict[str, Any]:
        """
        Convert Firecrawl price-only output to canonical artifact format.

        Args:
            raw_data: Raw Firecrawl price-only extraction data
            source_url: Original product URL

        Returns:
            Price-only canonical artifact dictionary
        """
        try:
            # Extract domain from source URL
            parsed_url = urlparse(source_url)
            roaster_domain = parsed_url.netloc

            # Map Firecrawl price data to canonical format
            product_data = {
                "platform_product_id": self._extract_product_id(raw_data, source_url),
                "platform": "other",  # Firecrawl is not a platform
                "title": raw_data.get("name", ""),
                "source_url": source_url,
                "variants": self._convert_price_variants(raw_data.get("price_variations", []))
            }

            # Create price-only canonical artifact
            artifact = {
                "source": "firecrawl",
                "roaster_domain": roaster_domain,
                "scraped_at": datetime.now(timezone.utc).isoformat(),
                "product": product_data,
                "normalization": {
                    "is_coffee": True,
                    "price_only": True,
                    "parsing_warnings": []
                }
            }

            logger.info(
                "Price-only artifact conversion completed",
                roaster_domain=roaster_domain,
                product_id=product_data["platform_product_id"],
                variants_count=len(product_data["variants"])
            )

            return artifact

        except Exception as e:
            logger.error("Price-only artifact conversion failed", error=str(e))
            raise ValueError(f"Failed to convert Firecrawl price-only data to canonical format: {str(e)}")

    def _convert_price_variants(self, price_variations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert price variations to canonical variant format for price-only mode."""
        variants = []

        for i, variation in enumerate(price_variations):
            if isinstance(variation, dict):
                variant = {
                    "platform_variant_id": f"firecrawl_price_{i}",
                    "title": variation.get("size", f"Size {i + 1}"),
                    "price": variation.get("price", "0"),
                    "currency": variation.get("currency", "USD"),
                    "in_stock": variation.get("availability", "in_stock") == "in_stock",
                    "raw_variant_json": variation
                }

                # Try to extract weight from size
                size = variation.get("size", "")
                weight = self._extract_weight_from_size(size)
                if weight:
                    variant["grams"] = weight
                    variant["weight_unit"] = "g"

                variants.append(variant)

        return variants

    async def extract_batch_products(
        self,
        urls: List[str],
        size_options: List[str] = None,
        job_type: str = "full_refresh"
    ) -> List[Dict[str, Any]]:
        """
        Extract multiple coffee products in batch.

        Args:
            urls: List of product URLs to extract
            size_options: List of size options to test
            job_type: Job type - "full_refresh" or "price_only" for Epic B integration

        Returns:
            List of extraction results
        """
        results = []

        logger.info("Starting batch product extraction", url_count=len(urls))

        for i, url in enumerate(urls):
            try:
                if job_type == "price_only":
                    result = await self.extract_price_only_data(url, job_type)
                else:
                    result = await self.extract_coffee_product_with_pricing(url, size_options, job_type)
                
                results.append({
                    'url': url,
                    'success': True,
                    'result': result
                })

                logger.info(
                    "Product extraction completed",
                    url=url,
                    index=i + 1,
                    total=len(urls),
                    job_type=job_type
                )

            except Exception as e:
                logger.error(
                    "Product extraction failed",
                    url=url,
                    index=i + 1,
                    total=len(urls),
                    job_type=job_type,
                    error=str(e)
                )

                results.append({
                    'url': url,
                    'success': False,
                    'error': str(e)
                })

        success_count = sum(1 for r in results if r['success'])

        logger.info(
            "Batch extraction completed",
            total=len(urls),
            successful=success_count,
            failed=len(urls) - success_count
        )

        return results

    async def health_check(self) -> bool:
        """Check if extract service is healthy."""
        try:
            # Test with a simple extraction
            test_url = "https://example.com/test-product"
            await self.extract_coffee_product_with_pricing(test_url, ["250g"])
            return True
        except Exception as e:
            logger.error("Extract service health check failed", error=str(e))
            return False

    def get_usage_stats(self) -> Dict[str, Any]:
        """Get current usage statistics."""
        if hasattr(self.client, 'get_usage_stats'):
            return self.client.get_usage_stats()
        return {}

    def get_health_status(self) -> Dict[str, Any]:
        """Get health status with metrics."""
        if hasattr(self.client, 'get_health_status'):
            return self.client.get_health_status()
        return {}
