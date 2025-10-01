 below is the **full canonical artifact** you should use across Scraper → normalizer → Supbase RPCs. It’s exhaustive (not minimal) and maps directly to the DB fields we have. Use the **JSON Schema** for validation + the **example artifact** to build fixtures. I also included a compact **mapping table** showing where each artifact field should land in supabase / RPCs.

# Canonical artifact JSON Schema (concise, strict)

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "Coffee Product Artifact",
  "type": "object",
  "required": ["source", "roaster_domain", "scraped_at", "product"],
  "properties": {
    "source": {
      "type": "string",
      "enum": ["shopify", "woocommerce", "firecrawl", "manual", "other"],
      "description": "Origin of artifact"
    },
    "roaster_domain": { "type": "string", "format": "hostname" },
    "scraped_at": { "type": "string", "format": "date-time" },
    "collector_meta": {
      "type": "object",
      "description": "Optional metadata about collector (agent, job id, options)",
      "properties": {
        "collector": { "type": "string" },
        "collector_version": { "type": "string" },
        "job_id": { "type": "string" },
        "notes": { "type": "string" }
      },
      "additionalProperties": true
    },
    "product": {
      "type": "object",
      "required": ["platform_product_id", "title", "source_url", "variants"],
      "properties": {
        "platform_product_id": { "type": "string" },
        "platform": { "type": "string", "enum": ["shopify","woocommerce","other"] },
        "title": { "type": "string" },
        "slug": { "type": "string" },
        "description_html": { "type": "string" },
        "description_md": { "type": "string" },
        "source_url": { "type": "string", "format": "uri" },
        "is_coffee": { "type": "boolean" },
        "tags": { "type": "array", "items": { "type": "string" } },
        "images": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["url"],
            "properties": {
              "url": { "type": "string", "format": "uri" },
              "alt_text": { "type": "string" },
              "order": { "type": "integer" },
              "source_id": { "type": "string" }
            },
            "additionalProperties": true
          }
        },
        "variants": {
          "type": "array",
          "minItems": 1,
          "items": {
            "type": "object",
            "required": ["platform_variant_id", "price"],
            "properties": {
              "platform_variant_id": { "type": "string" },
              "sku": { "type": "string" },
              "title": { "type": "string" },
              "price": { "type": "string" },
              "price_decimal": { "type": "number" },
              "currency": { "type": "string" },
              "compare_at_price": { "type": "string" },
              "compare_at_price_decimal": { "type": "number" },
              "in_stock": { "type": "boolean" },
              "grams": { "type": ["integer", "null"] },
              "weight_unit": { "type": "string", "enum": ["g","kg","oz",null] },
              "options": { "type": "array", "items": { "type": "string" } },
              "raw_variant_json": { "type": "object" }
            },
            "additionalProperties": true
          }
        },
        "raw_meta": { "type": "object" }
      },
      "additionalProperties": true
    },
    "normalization": {
      "type": "object",
      "description": "Results of deterministic normalization (set by normalize step)",
      "properties": {
        "is_coffee": { "type": "boolean" },
        "content_hash": { "type": "string" },
        "raw_payload_hash": { "type": "string" },
        "parsing_warnings": { "type": "array", "items": { "type": "string" } },
        "name_clean": { "type": "string" },
        "description_md_clean": { "type": "string" },
        "tags_normalized": { "type": "array", "items": { "type": "string" } },
        "notes_raw": { "type": "array", "items": { "type": "string" } },
        "roast_level_raw": { "type": ["string","null"] },
        "roast_level_enum": { "type": ["string","null"], "enum": ["light","light-medium","medium","medium-dark","dark","unknown", null] },
        "process_raw": { "type": ["string","null"] },
        "process_enum": { "type": ["string","null"], "enum": ["washed","natural","honey","anaerobic","other", null] },
        "varieties": { "type": "array", "items": { "type": "string" } },
        "region": { "type": ["string","null"] },
        "country": { "type": ["string","null"] },
        "altitude_m": { "type": ["integer","null"] },
        "default_pack_weight_g": { "type": ["integer","null"] },
        "default_grind": { "type": ["string","null"], "enum": ["whole","espresso","filter","ground","unknown", null] },
        "bean_species": { "type": ["string","null"], "enum": ["arabica","robusta","liberica","blend", null] },
        "sensory_params": {
          "type": ["object","null"],
          "properties": {
            "acidity": { "type": ["number","null"], "minimum": 0, "maximum": 10 },
            "sweetness": { "type": ["number","null"], "minimum": 0, "maximum": 10 },
            "bitterness": { "type": ["number","null"], "minimum": 0, "maximum": 10 },
            "body": { "type": ["number","null"], "minimum": 0, "maximum": 10 },
            "clarity": { "type": ["number","null"], "minimum": 0, "maximum": 10 },
            "aftertaste": { "type": ["number","null"], "minimum": 0, "maximum": 10 },
            "confidence": { "type": ["string","null"], "enum": ["high","medium","low", null] },
            "source": { "type": ["string","null"], "enum": ["roaster","icb_inferred","icb_manual", null] }
          }
        },
        "llm_enrichment": { "type": ["object","null"] },
        "llm_confidence": { "type": ["number","null"] },
        "roast_inferred": { "type": "boolean" },
        "pipeline_processing": {
          "type": ["object","null"],
          "description": "C.8 normalizer pipeline processing metadata",
          "properties": {
            "pipeline_stage": { "type": ["string","null"], "enum": ["initialized","deterministic_parsing","llm_fallback","completed","failed", null] },
            "processing_status": { "type": ["string","null"], "enum": ["success","partial","failed","pending_review", null] },
            "overall_confidence": { "type": ["number","null"], "minimum": 0, "maximum": 1 },
            "pipeline_warnings": { "type": "array", "items": { "type": "string" } },
            "pipeline_errors": { "type": "array", "items": { "type": "string" } },
            "llm_fallback_used": { "type": "boolean" },
            "llm_fallback_fields": { "type": "array", "items": { "type": "string" } },
            "processing_timestamp": { "type": ["string","null"], "format": "date-time" },
            "execution_id": { "type": ["string","null"] }
          }
        }
      },
      "additionalProperties": true
    },
    "collector_signals": {
      "type": "object",
      "properties": {
        "response_status": { "type": ["integer","null"] },
        "response_headers": { "type": "object" },
        "download_time_ms": { "type": ["integer","null"] },
        "size_bytes": { "type": ["integer","null"] }
      }
    },
    "audit": {
      "type": "object",
      "properties": {
        "artifact_id": { "type": "string" },
        "created_at": { "type": "string", "format": "date-time" },
        "collected_by": { "type": "string" }
      }
    }
  },
  "additionalProperties": false
}
```

---

# Full example artifact (realistic, exhaustive)

```json
{
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
    "slug": "blue-tokai-single-origin-250g",
    "description_html": "<p>Our single origin coffee... <strong>Tasting Notes:</strong> chocolate, orange, caramel.</p>",
    "description_md": "Our single origin coffee... **Tasting Notes:** chocolate, orange, caramel.",
    "source_url": "https://bluetokaicoffee.com/products/single-origin-250g",
    "is_coffee": true,
    "tags": ["single-origin","espresso","roasted","blue-tokai"],
    "images": [
      { "url": "https://cdn.bluetokai.com/images/so-250-front.jpg", "alt_text": "Blue Tokai 250g front", "order": 0, "source_id": "img-1" },
      { "url": "https://cdn.bluetokai.com/images/so-250-back.jpg", "alt_text": "Back label", "order": 1, "source_id": "img-2" }
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
        "in_stock": true,
        "grams": 250,
        "weight_unit": "g",
        "options": ["Whole Bean"],
        "raw_variant_json": { "id": 1111, "grams": 250, "price": "599.00" }
      }
    ],
    "raw_meta": {
      "shopify": { "product_json_sample": { "id": 987654321 } }
    }
  },
  "normalization": {
    "is_coffee": true,
    "content_hash": "c79b2f6c2d4a4f9aab2d3e7f8c9a3b4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0",
    "raw_payload_hash": "d1f3d2b8e1a8c9f0a7b6c5d4e3f2a1b0c9d8e7f6a5b4c3d2e1f0a9b8c7d6e5",
    "parsing_warnings": [],
    "name_clean": "Blue Tokai Single Origin - 250g",
    "description_md_clean": "Our single origin coffee... **Tasting Notes:** chocolate, orange, caramel.",
    "tags_normalized": ["single-origin","espresso","roasted","blue-tokai"],
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
    "llm_enrichment": null,
    "llm_confidence": null,
    "roast_inferred": false,
    "pipeline_processing": {
      "pipeline_stage": "completed",
      "processing_status": "success",
      "overall_confidence": 0.85,
      "pipeline_warnings": ["Low confidence in roast level detection"],
      "pipeline_errors": [],
      "llm_fallback_used": false,
      "llm_fallback_fields": [],
      "processing_timestamp": "2025-09-21T10:00:05Z",
      "execution_id": "pipeline-exec-20250921-001"
    }
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
```

---

# Mapping table — artifact paths → Supabase tables / RPCs

Use this as a quick reference for your scraper → RPC wiring.

| Artifact path                                                   |                                       Supabase table / RPC | Column(s) / Notes                                          |
| --------------------------------------------------------------- | -----------------------------------------------------: | ---------------------------------------------------------- |
| `product.platform_product_id`                                   |                      `coffees` via `rpc_upsert_coffee` | `platform_product_id`                                      |
| `product.title` → normalization.name\_clean                     |                                         `coffees.name` | `name`                                                     |
| `product.slug`                                                  |                                         `coffees.slug` | `slug`                                                     |
| `product.description_md` / `normalization.description_md_clean` |                               `coffees.description_md` | `description_md`                                           |
| `product.is_coffee`                                             |                                    `coffees.is_coffee` | `is_coffee` (boolean - true for coffee, false for equipment) |
| `normalization.is_coffee`                                       |                                    `coffees.is_coffee` | `is_coffee` (NEW FIELD - add to migration)                |
| `product.tags` / `normalization.tags_normalized`                |                                         `coffees.tags` | `tags` (NEW FIELD - add to migration)                     |
| `normalization.notes_raw`                                       |                                    `coffees.notes_raw` | `notes_raw` (EXISTING FIELD)                              |
| `normalization.roast_level_raw`                                 |                              `coffees.roast_level_raw` | `roast_level_raw` (EXISTING FIELD)                        |
| `normalization.roast_level_enum`                                |                             `coffees.roast_level_enum` | `roast_level` (EXISTING FIELD)                             |
| `normalization.process_raw`                                     |                                  `coffees.process_raw` | `process_raw` (EXISTING FIELD)                            |
| `normalization.process_enum`                                    |                                 `coffees.process_enum` | `process` (EXISTING FIELD)                                |
| `normalization.varieties`                                       |                                    `coffees.varieties` | `varieties` (NEW FIELD - add to migration)                |
| `normalization.region/country/altitude_m`                       |                    `coffees.notes_raw` → normalize to `regions`/`estates` tables | Store in `notes_raw` JSON, normalize in second pass to existing `regions`/`estates` tables |
| `normalization.default_pack_weight_g`                           |                        `coffees.notes_raw` | Store in `notes_raw` JSON for second-pass normalization |
| `normalization.sensory_params`                                 |                                    `sensory_params` table | Direct mapping to existing `sensory_params` table via RPC |
| `variants[]` (each)                                             |                    `variants` via `rpc_upsert_variant` | `platform_variant_id`, `weight_g`, `currency`, `in_stock`  |
| `variants[].price_decimal`                                      |                        `prices` via `rpc_insert_price` | `price`, `currency`, `scraped_at`                          |
| `variants[].compare_at_price_decimal`                           |                              `prices.compare_at_price` | set `is_sale` accordingly                                  |
| `product.images[]` (after ImageKit upload)                      |                        `coffee_images` via `rpc_upsert_image` | `url`, `alt`, `width`, `height`, `sort_order` |
| `normalization.content_hash`                                    |                                 `coffees.source_raw` | `source_raw` (EXISTING FIELD - store as JSON)            |
| `normalization.raw_payload_hash`                                |                             `coffees.source_raw` | `source_raw` (EXISTING FIELD - store as JSON)            |
| `audit.artifact_id`                                             | `scrape_artifacts` / or store in `coffees.source_raw` | helpful for replay                                         |
| `collector_signals.*`                                           |                    `scrape_artifacts` or admin logging | debugging fields                                           |
| `normalization.llm_enrichment`                                  |                               `coffees.notes_raw` | `notes_raw` (EXISTING FIELD - store as JSON)             |
| `normalization.llm_confidence`                                  |                               `coffees.notes_raw` | `notes_raw` (EXISTING FIELD - store as JSON)             |
| `audit.created_at`                                              |        `coffees.first_seen_at` / `variants.created_at` | `first_seen_at` (NEW FIELD - add to migration)            |

## Repurposed Fields Strategy

To minimize database changes, we repurpose existing fields for scraping data:

### **Raw Data Storage**
- **`coffees.source_raw`** → Store complete raw scraping payload including:
  - `content_hash` and `raw_payload_hash` 
  - `artifact_id` for replay capability
  - `collector_signals` for debugging
  - Full raw product data from platform APIs

### **LLM and Processing Data**
- **`coffees.notes_raw`** → Store LLM enrichment and processing data including:
  - `llm_enrichment` (LLM-generated product data)
  - `llm_confidence` (confidence scores)
  - `processing_warnings` (parsing issues)
  - `parsing_warnings` (normalization issues)
  - `region`, `country`, `altitude_m` (for second-pass normalization to `regions`/`estates` tables)
  - `default_pack_weight_g` (for second-pass processing)

### **Sensory Analysis**
- **`sensory_params` table** → Already exists for sensory analysis
  - Maps directly to `normalization.sensory_params` in artifact
  - No changes needed to existing table structure

### **Scraping Infrastructure**
- **`scrape_runs` table** → Already exists for run tracking
- **`scrape_artifacts` table** → Already exists for raw data storage  
- **`product_sources` table** → Already exists for source configuration

This approach reduces new columns from 18 to just 2 (`tags` and `varieties`) while leveraging your existing infrastructure and normalized tables for geographic data. The `is_coffee` boolean field provides a cleaner approach than separate product type categorization.

## Important Processing Notes

### **Two-Pass Processing Strategy**
1. **First Pass (Scraper)**: Store raw data in `source_raw` and `notes_raw` JSON fields
2. **Second Pass (Normalizer)**: Extract and normalize geographic data to `regions`/`estates` tables

### **RPC Function Usage**
- Use `rpc_upsert_coffee()` for main coffee data
- Use `rpc_upsert_variant()` for variant data  
- Use `rpc_insert_price()` for price history
- Use `rpc_upsert_image()` for image data
- Use `rpc_upsert_sensory_params()` for sensory analysis

### **Data Storage Strategy**
- **Raw scraping data** → `coffees.source_raw` (complete artifact JSON)
- **LLM/processing data** → `coffees.notes_raw` (enrichment, warnings, geographic data)
- **Normalized data** → Direct column mapping for immediate use
- **Geographic data** → Second-pass normalization to existing `regions`/`estates` tables

---