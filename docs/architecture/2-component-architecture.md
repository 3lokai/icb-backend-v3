# 2. Component Architecture

### 2.1 Scheduler
- **Primary**: GitHub Actions scheduled workflows
- **Fallback**: Small Fly machine with cron
- **Configuration**: Per-roaster cadence overrides in database
- **Default Schedules**:
  - Full refresh: `0 3 1 * *` (monthly at 03:00 UTC on 1st)
  - Price-only: `0 4 * * 0` (weekly Sunday at 04:00 UTC)

### 2.2 Orchestrator & Job Queue
- **Technology**: Redis/Bull or Cloud Tasks
- **Features**: Job state, retries, backoff, per-roaster concurrency
- **Concurrency**: Default 3 workers per roaster (configurable)
- **Backoff**: Exponential retry (1s, 2s, 4s, 8s, 16s) with jitter

### 2.3 Fetcher Pool
- **Technology**: Async `httpx` workers with semaphores
- **Primary Sources**: Shopify JSON, WooCommerce REST API
- **Fallback**: Firecrawl map/extract for JS-heavy sites
- **Politeness**: 250ms ± 100ms jitter, respect robots.txt
- **Caching**: ETag/Last-Modified support for bandwidth efficiency
- **Source Configuration**: Read from `product_sources` table for endpoint configuration

### 2.4 Validator
- **Technology**: Pydantic v2 models from canonical JSON schema
- **Validation**: Strict schema compliance with detailed error reporting
- **Persistence**: Raw artifacts to S3/Supabase Storage for replay
- **Error Handling**: Invalid artifacts marked for manual review
- **Artifact Storage**: Store in `scrape_artifacts` table with run tracking

### 2.5 Normalizer Service
- **Deterministic Parsing**: Weight conversion, currency normalization, roast level mapping
- **LLM Fallback**: Rate-limited enrichment for ambiguous fields only
- **Confidence Scoring**: Auto-apply only if `llm_confidence >= 0.70`
- **Change Detection**: Content hash comparison for efficient processing

### 2.6 Transformer & RPCs
- **Atomic Operations**: All writes through server-side RPCs
- **Idempotency**: Composite keys for safe retries
- **Data Storage Strategy**: 
  - Raw scraping data → `coffees.source_raw` (JSON)
  - LLM enrichment → `coffees.notes_raw` (JSON)
  - Sensory analysis → `sensory_params` table (existing)
- **RPC Functions** (using existing schema):
  - `rpc_upsert_coffee`: Product metadata with parameters: `p_bean_species`, `p_name`, `p_slug`, `p_roaster_id`, `p_process`, `p_roast_level`, `p_description_md`, `p_platform_product_id`, `p_source_raw`, `p_notes_raw`
  - `rpc_upsert_variant`: Single variant upsert with parameters: `p_coffee_id`, `p_platform_variant_id`, `p_sku`, `p_weight_g`, `p_grind`, `p_currency`, `p_in_stock`, `p_source_raw`
  - `rpc_insert_price`: Price time-series insert with parameters: `p_variant_id`, `p_price`, `p_currency`, `p_is_sale`, `p_scraped_at`, `p_source_url`, `p_source_raw`
  - `rpc_upsert_coffee_image`: Image record with parameters: `p_coffee_id`, `p_url`, `p_alt`, `p_width`, `p_height`, `p_sort_order`, `p_source_raw`

### 2.7 ImageKit Integration
- **Upload Strategy**: New/changed images only (hash-based deduplication)
- **CDN**: ImageKit CDN URLs for performance
- **Fallback**: Remote fetch for problematic image hosts
- **Storage**: Both source URL and ImageKit URL stored in `coffee_images` table
