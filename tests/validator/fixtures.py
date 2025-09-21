"""
Test fixtures for validator tests based on canonical artifact schema.
"""

from typing import Dict, Any


def get_valid_artifact_fixture() -> Dict[str, Any]:
    """
    Get valid artifact fixture based on canonical example.
    
    Returns:
        Valid artifact data dictionary
    """
    return {
        "source": "firecrawl",
        "roaster_domain": "bluetokaicoffee.com",
        "scraped_at": "2025-09-21T10:00:00Z",
        "collector_meta": {
            "collector": "firecrawl-extract-v1",
            "job_id": "fc-job-20250921-001",
            "collector_version": "1.3.0"
        },
        "product": {
            "platform_product_id": "987654321",
            "platform": "shopify",
            "title": "Blue Tokai Single Origin - 250g",
            "handle": "single-origin-250g",
            "slug": "blue-tokai-single-origin-250g",
            "description_html": "<p>Our single origin coffee... <strong>Tasting Notes:</strong> chocolate, orange, caramel.</p>",
            "description_md": "Our single origin coffee... **Tasting Notes:** chocolate, orange, caramel.",
            "source_url": "https://bluetokaicoffee.com/products/single-origin-250g",
            "product_type": "coffee",
            "tags": ["single-origin", "espresso", "roasted", "blue-tokai"],
            "images": [
                {
                    "url": "https://cdn.bluetokai.com/images/so-250-front.jpg",
                    "alt_text": "Blue Tokai 250g front",
                    "order": 0,
                    "source_id": "img-1"
                },
                {
                    "url": "https://cdn.bluetokai.com/images/so-250-back.jpg",
                    "alt_text": "Back label",
                    "order": 1,
                    "source_id": "img-2"
                }
            ],
            "variants": [
                {
                    "platform_variant_id": "v-1111",
                    "sku": "BT-SO-250",
                    "title": "250g - Whole Bean",
                    "price": "599.00",
                    "price_decimal": 599.00,
                    "currency": "INR",
                    "compare_at_price": "699.00",
                    "compare_at_price_decimal": 699.00,
                    "in_stock": True,
                    "grams": 250,
                    "weight_unit": "g",
                    "options": ["Whole Bean"],
                    "raw_variant_json": {"id": 1111, "grams": 250, "price": "599.00"}
                }
            ],
            "raw_meta": {
                "shopify": {"product_json_sample": {"id": 987654321}}
            }
        },
        "normalization": {
            "is_coffee": True,
            "content_hash": "c79b2f6c2d4a4f9aab2d3e7f8c9a3b4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0",
            "raw_payload_hash": "d1f3d2b8e1a8c9f0a7b6c5d4e3f2a1b0c9d8e7f6a5b4c3d2e1f0a9b8c7d6e5",
            "parsing_warnings": [],
            "name_clean": "Blue Tokai Single Origin - 250g",
            "description_md_clean": "Our single origin coffee... **Tasting Notes:** chocolate, orange, caramel.",
            "tags_normalized": ["single-origin", "espresso", "roasted", "blue-tokai"],
            "notes_raw": ["chocolate", "orange", "caramel"],
            "roast_level_raw": "City / Medium",
            "roast_level_enum": "medium",
            "process_raw": "washed",
            "process_enum": "washed",
            "varieties": ["SL28", "Bourbon"],
            "region": "Chikmagalur",
            "country": "IN",
            "altitude_m": 1400,
            "default_pack_weight_g": 250,
            "default_grind": "whole",
            "bean_species": "arabica",
            "sensory_params": {
                "acidity": 7.5,
                "sweetness": 6.0,
                "bitterness": 4.0,
                "body": 6.5,
                "clarity": 8.0,
                "aftertaste": 7.0,
                "confidence": "high",
                "source": "icb_inferred"
            },
            "llm_enrichment": None,
            "llm_confidence": None,
            "roast_inferred": False
        },
        "collector_signals": {
            "response_status": 200,
            "response_headers": {
                "content-type": "application/json; charset=utf-8"
            },
            "download_time_ms": 532,
            "size_bytes": 54321
        },
        "audit": {
            "artifact_id": "artifact-20250921-0001",
            "created_at": "2025-09-21T10:00:01Z",
            "collected_by": "firecrawl"
        }
    }


def get_invalid_artifact_fixtures() -> Dict[str, Dict[str, Any]]:
    """
    Get invalid artifact fixtures for error testing.
    
    Returns:
        Dictionary of invalid artifact fixtures with error descriptions
    """
    return {
        "missing_required_fields": {
            "source": "shopify",
            # Missing roaster_domain, scraped_at, product
        },
        "invalid_source_enum": {
            "source": "invalid_platform",
            "roaster_domain": "example.com",
            "scraped_at": "2025-01-12T10:00:00Z",
            "product": {
                "platform_product_id": "123",
                "title": "Test Product",
                "source_url": "https://example.com/product",
                "variants": []
            }
        },
        "invalid_roaster_domain": {
            "source": "shopify",
            "roaster_domain": "",  # Empty domain
            "scraped_at": "2025-01-12T10:00:00Z",
            "product": {
                "platform_product_id": "123",
                "title": "Test Product",
                "source_url": "https://example.com/product",
                "variants": []
            }
        },
        "invalid_timestamp": {
            "source": "shopify",
            "roaster_domain": "example.com",
            "scraped_at": "invalid-timestamp",
            "product": {
                "platform_product_id": "123",
                "title": "Test Product",
                "source_url": "https://example.com/product",
                "variants": []
            }
        },
        "missing_product_required_fields": {
            "source": "shopify",
            "roaster_domain": "example.com",
            "scraped_at": "2025-01-12T10:00:00Z",
            "product": {
                # Missing platform_product_id, title, source_url, variants
                "description": "Test product"
            }
        },
        "invalid_variant_data": {
            "source": "shopify",
            "roaster_domain": "example.com",
            "scraped_at": "2025-01-12T10:00:00Z",
            "product": {
                "platform_product_id": "123",
                "title": "Test Product",
                "source_url": "https://example.com/product",
                "variants": [
                    {
                        # Missing required platform_variant_id and price
                        "sku": "TEST-001"
                    }
                ]
            }
        },
        "invalid_enum_values": {
            "source": "shopify",
            "roaster_domain": "example.com",
            "scraped_at": "2025-01-12T10:00:00Z",
            "product": {
                "platform_product_id": "123",
                "title": "Test Product",
                "source_url": "https://example.com/product",
                "variants": [
                    {
                        "platform_variant_id": "v-001",
                        "price": "10.00"
                    }
                ]
            },
            "normalization": {
                "roast_level_enum": "invalid_roast_level",
                "process_enum": "invalid_process",
                "default_grind": "invalid_grind",
                "bean_species": "invalid_species"
            }
        },
        "invalid_sensory_params": {
            "source": "shopify",
            "roaster_domain": "example.com",
            "scraped_at": "2025-01-12T10:00:00Z",
            "product": {
                "platform_product_id": "123",
                "title": "Test Product",
                "source_url": "https://example.com/product",
                "variants": [
                    {
                        "platform_variant_id": "v-001",
                        "price": "10.00"
                    }
                ]
            },
            "normalization": {
                "sensory_params": {
                    "acidity": 15.0,  # Invalid: > 10
                    "sweetness": -5.0,  # Invalid: < 0
                    "confidence": "invalid_confidence",
                    "source": "invalid_source"
                }
            }
        }
    }


def get_edge_case_fixtures() -> Dict[str, Dict[str, Any]]:
    """
    Get edge case fixtures for comprehensive testing.
    
    Returns:
        Dictionary of edge case fixtures
    """
    return {
        "null_values": {
            "source": "shopify",
            "roaster_domain": "example.com",
            "scraped_at": "2025-01-12T10:00:00Z",
            "product": {
                "platform_product_id": "123",
                "title": "Test Product",
                "source_url": "https://example.com/product",
                "variants": [
                    {
                        "platform_variant_id": "v-001",
                        "price": "10.00",
                        "grams": None,  # Null value
                        "weight_unit": None,  # Null value
                        "options": None  # Null value
                    }
                ]
            },
            "normalization": {
                "roast_level_enum": None,  # Null enum
                "process_enum": None,  # Null enum
                "region": None,  # Null string
                "country": None,  # Null string
                "altitude_m": None,  # Null integer
                "sensory_params": None  # Null object
            }
        },
        "empty_arrays": {
            "source": "shopify",
            "roaster_domain": "example.com",
            "scraped_at": "2025-01-12T10:00:00Z",
            "product": {
                "platform_product_id": "123",
                "title": "Test Product",
                "source_url": "https://example.com/product",
                "tags": [],  # Empty array
                "images": [],  # Empty array
                "variants": [
                    {
                        "platform_variant_id": "v-001",
                        "price": "10.00"
                    }
                ]
            },
            "normalization": {
                "parsing_warnings": [],  # Empty array
                "tags_normalized": [],  # Empty array
                "notes_raw": [],  # Empty array
                "varieties": []  # Empty array
            }
        },
        "type_coercion": {
            "source": "shopify",
            "roaster_domain": "example.com",
            "scraped_at": "2025-01-12T10:00:00Z",
            "product": {
                "platform_product_id": "123",
                "title": "Test Product",
                "source_url": "https://example.com/product",
                "variants": [
                    {
                        "platform_variant_id": "v-001",
                        "price": "10.00",
                        "price_decimal": "599.00",  # String that should be float
                        "in_stock": "true",  # String that should be boolean
                        "grams": "250"  # String that should be integer
                    }
                ]
            }
        }
    }
