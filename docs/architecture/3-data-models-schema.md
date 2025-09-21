# 3. Data Models & Schema

### 3.1 Canonical Artifact Schema
The system uses a comprehensive JSON schema for all scraped data:

**Required Fields:**
- `source`: Origin (shopify, woocommerce, firecrawl, manual, other)
- `roaster_domain`: Store domain (hostname format)
- `scraped_at`: ISO 8601 timestamp
- `product`: Product object with platform identifiers and variants

**Key Product Fields:**
- `platform_product_id`: Unique identifier from source platform
- `title`, `handle`, `description_html/md`: Product information
- `source_url`: Original product URL
- `variants`: Array of product variants with pricing and inventory
- `images`: Array with url, alt_text, order, source_id

**Normalization Fields:**
- `is_coffee`: Boolean coffee classification
- `content_hash`: Hash of normalized content for change detection (stored in `source_raw`)
- `name_clean`, `description_md_clean`: Cleaned text fields
- `roast_level_enum`, `process_enum`: Standardized enums
- `varieties`, `region`, `country`, `altitude_m`: Geographic data
- `llm_enrichment`: LLM-generated data with confidence score (stored in `notes_raw`)
- `sensory_params`: Sensory analysis data (stored in `sensory_params` table)

### 3.2 Database Schema Changes
Minimal additions to existing tables with repurposed fields strategy:

```sql
-- Roaster configuration (roasters table)
ALTER TABLE roasters
  ADD COLUMN full_cadence text,               -- cron: '0 3 1 * *'
  ADD COLUMN price_cadence text,              -- cron: '0 4 * * 0'
  ADD COLUMN default_concurrency int DEFAULT 3,
  ADD COLUMN use_firecrawl_fallback boolean DEFAULT false,
  ADD COLUMN firecrawl_budget_limit int DEFAULT 0,
  -- Essential caching and LLM support
  ADD COLUMN last_etag text,                 -- ETag for 304 handling
  ADD COLUMN last_modified timestamptz,       -- Last-Modified for caching
  ADD COLUMN use_llm boolean DEFAULT false,  -- Per-roaster LLM opt-in
  ADD COLUMN alert_price_delta_pct numeric DEFAULT 0.10; -- Price spike threshold

-- Variant price tracking
ALTER TABLE variants
  ADD COLUMN price_last_checked_at timestamptz,
  ADD COLUMN price_current numeric,
  ADD COLUMN last_seen_at timestamptz,
  ADD COLUMN status text DEFAULT 'active';

-- Coffee minimal new fields (repurpose existing fields for scraping data)
ALTER TABLE coffees
  ADD COLUMN is_coffee boolean DEFAULT true,  -- Coffee classification
  ADD COLUMN tags text[],                     -- Product tags array
  ADD COLUMN varieties text[],                -- Coffee varieties array
  ADD COLUMN region text,                     -- Geographic region
  ADD COLUMN country text,                    -- Country
  ADD COLUMN altitude_m integer,              -- Altitude in meters
  ADD COLUMN default_pack_weight_g integer,   -- Standard pack weight
  ADD COLUMN default_grind grind_enum,        -- Default grind preference
  ADD COLUMN bean_species species_enum,       -- Coffee species (arabica, robusta, etc.)
  ADD COLUMN first_seen_at timestamptz;       -- First discovery timestamp
```

**Repurposed Fields Strategy:**
- **`coffees.source_raw`** → Store complete raw scraping payload (content_hash, raw_payload_hash, artifact_id, collector_signals)
- **`coffees.notes_raw`** → Store LLM enrichment and processing data (llm_enrichment, llm_confidence, processing_warnings)
- **`sensory_params` table** → Already exists for sensory analysis (no changes needed)
- **Existing scraping infrastructure** → `scrape_runs`, `scrape_artifacts`, `product_sources` tables already exist
