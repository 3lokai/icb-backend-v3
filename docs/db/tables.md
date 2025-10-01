# Database Tables

This document describes all tables in the database schema with their columns, relationships, and usage.

## Core Tables

### coffees
Main table storing coffee product information.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | string | No | Primary key (UUID) |
| name | string | No | Coffee name |
| slug | string | No | URL-friendly identifier |
| roaster_id | string | No | Foreign key to roasters table |
| description_md | string | Yes | Markdown description |
| direct_buy_url | string | Yes | Direct purchase URL |
| platform_product_id | string | Yes | Platform-specific product ID |
| vendor_sku | string | Yes | Vendor SKU |
| status | coffee_status_enum | No | Coffee status |
| is_coffee | boolean | Yes | Whether this is actually coffee |
| is_limited | boolean | No | Whether this is a limited edition |
| decaf | boolean | No | Whether this is decaffeinated |
| crop_year | number | Yes | Harvest year |
| harvest_window | string | Yes | Harvest time window |
| first_seen_at | string | Yes | When first discovered |
| created_at | string | No | Creation timestamp |
| updated_at | string | No | Last update timestamp |
| seo_title | string | Yes | SEO title |
| seo_desc | string | Yes | SEO description |
| notes_lang | string | Yes | Language of notes |
| notes_raw | Json | Yes | Raw notes data |
| source_raw | Json | Yes | Raw source data |
| roast_level | roast_level_enum | Yes | Roast level |
| roast_level_raw | string | Yes | Raw roast level text |
| roast_style_raw | string | Yes | Raw roast style text |
| process | process_enum | Yes | Processing method |
| process_raw | string | Yes | Raw process text |
| bean_species | species_enum | Yes | Coffee species |
| default_grind | grind_enum | Yes | Default grind recommendation |
| varieties | string[] | Yes | Coffee varieties |
| tags | string[] | Yes | Product tags |
| rating_avg | number | Yes | Average rating |
| rating_count | number | No | Number of ratings |

**Relationships:**
- `roaster_id` → `roasters.id`

### roasters
Table storing roaster information.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | string | No | Primary key (UUID) |
| name | string | No | Roaster name |
| slug | string | No | URL-friendly identifier |
| website | string | Yes | Roaster website |
| platform | platform_enum | Yes | E-commerce platform |
| is_active | boolean | No | Whether roaster is active |
| hq_city | string | Yes | Headquarters city |
| hq_state | string | Yes | Headquarters state |
| hq_country | string | Yes | Headquarters country |
| lat | number | Yes | Latitude |
| lon | number | Yes | Longitude |
| phone | string | Yes | Contact phone |
| support_email | string | Yes | Support email |
| instagram_handle | string | Yes | Instagram handle |
| social_json | Json | Yes | Social media data |
| created_at | string | No | Creation timestamp |
| updated_at | string | No | Last update timestamp |
| last_modified | string | Yes | Last modification timestamp |
| last_etag | string | Yes | Last ETag |
| robots_allow | boolean | Yes | Robots.txt allows scraping |
| robots_checked_at | string | Yes | When robots.txt was checked |
| use_llm | boolean | Yes | Whether to use LLM processing |
| use_firecrawl_fallback | boolean | Yes | Whether to use Firecrawl fallback |
| firecrawl_budget_limit | number | Yes | Firecrawl budget limit |
| default_concurrency | number | Yes | Default concurrency setting |
| full_cadence | string | Yes | Full scraping cadence |
| price_cadence | string | Yes | Price scraping cadence |
| alert_price_delta_pct | number | Yes | Price change alert threshold |

### variants
Table storing coffee variant information (different sizes, grinds, etc.).

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | string | No | Primary key (UUID) |
| coffee_id | string | No | Foreign key to coffees table |
| platform_variant_id | string | Yes | Platform-specific variant ID |
| sku | string | Yes | SKU |
| barcode | string | Yes | Barcode |
| weight_g | number | No | Weight in grams |
| grind | grind_enum | No | Grind type |
| pack_count | number | No | Number of packs |
| currency | string | No | Currency code |
| price_current | number | Yes | Current price |
| compare_at_price | number | Yes | Compare at price |
| in_stock | boolean | No | Whether in stock |
| stock_qty | number | Yes | Stock quantity |
| subscription_available | boolean | No | Whether subscription available |
| status | string | Yes | Variant status |
| source_raw | Json | Yes | Raw source data |
| created_at | string | No | Creation timestamp |
| updated_at | string | No | Last update timestamp |
| last_seen_at | string | Yes | When last seen |
| price_last_checked_at | string | Yes | When price was last checked |

**Relationships:**
- `coffee_id` → `coffees.id`

### prices
Table storing price history for variants.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | string | No | Primary key (UUID) |
| variant_id | string | No | Foreign key to variants table |
| price | number | No | Price value |
| currency | string | No | Currency code |
| is_sale | boolean | No | Whether this is a sale price |
| scraped_at | string | No | When price was scraped |
| source_url | string | Yes | Source URL |
| source_raw | Json | Yes | Raw source data |

**Relationships:**
- `variant_id` → `variants.id`

## Geographic Tables

### regions
Table storing geographic region information.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | string | No | Primary key (UUID) |
| display_name | string | No | Display name |
| country | string | No | Country |
| state | string | Yes | State/Province |
| subregion | string | Yes | Subregion |

### estates
Table storing coffee estate information.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | string | No | Primary key (UUID) |
| name | string | No | Estate name |
| region_id | string | Yes | Foreign key to regions table |
| altitude_min_m | number | Yes | Minimum altitude in meters |
| altitude_max_m | number | Yes | Maximum altitude in meters |
| notes | string | Yes | Estate notes |

**Relationships:**
- `region_id` → `regions.id`

### coffee_regions
Junction table linking coffees to regions.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| coffee_id | string | No | Foreign key to coffees table |
| region_id | string | No | Foreign key to regions table |
| pct | number | Yes | Percentage of coffee from this region |

**Relationships:**
- `coffee_id` → `coffees.id`
- `region_id` → `regions.id`

### coffee_estates
Junction table linking coffees to estates.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| coffee_id | string | No | Foreign key to coffees table |
| estate_id | string | No | Foreign key to estates table |
| pct | number | Yes | Percentage of coffee from this estate |

**Relationships:**
- `coffee_id` → `coffees.id`
- `estate_id` → `estates.id`

## Sensory and Flavor Tables

### sensory_params
Table storing sensory analysis parameters.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| coffee_id | string | No | Foreign key to coffees table |
| acidity | number | Yes | Acidity rating (1-10) |
| sweetness | number | Yes | Sweetness rating (1-10) |
| bitterness | number | Yes | Bitterness rating (1-10) |
| body | number | Yes | Body rating (1-10) |
| aftertaste | number | Yes | Aftertaste rating (1-10) |
| clarity | number | Yes | Clarity rating (1-10) |
| confidence | sensory_confidence_enum | Yes | Confidence level |
| source | sensory_source_enum | Yes | Data source |
| notes | string | Yes | Additional notes |
| created_at | string | No | Creation timestamp |
| updated_at | string | No | Last update timestamp |

**Relationships:**
- `coffee_id` → `coffees.id` (one-to-one)

### flavor_notes
Table storing flavor note definitions.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | string | No | Primary key (UUID) |
| key | string | No | Flavor note key |
| label | string | No | Flavor note label |
| group_key | string | Yes | Group key for categorization |

### coffee_flavor_notes
Junction table linking coffees to flavor notes.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| coffee_id | string | No | Foreign key to coffees table |
| flavor_note_id | string | No | Foreign key to flavor_notes table |

**Relationships:**
- `coffee_id` → `coffees.id`
- `flavor_note_id` → `flavor_notes.id`

## Image Tables

### coffee_images
Table storing coffee image information.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | string | No | Primary key (UUID) |
| coffee_id | string | No | Foreign key to coffees table |
| url | string | No | Image URL |
| imagekit_url | string | Yes | ImageKit URL |
| alt | string | Yes | Alt text |
| width | number | Yes | Image width |
| height | number | Yes | Image height |
| sort_order | number | No | Sort order |
| content_hash | string | Yes | Content hash for deduplication |
| source_raw | Json | Yes | Raw source data |
| updated_at | string | No | Last update timestamp |

**Relationships:**
- `coffee_id` → `coffees.id`

## Brew Method Tables

### brew_methods
Table storing brew method definitions.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | string | No | Primary key (UUID) |
| key | string | No | Brew method key |
| label | string | No | Brew method label |

### coffee_brew_methods
Junction table linking coffees to brew methods.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| coffee_id | string | No | Foreign key to coffees table |
| brew_method_id | string | No | Foreign key to brew_methods table |

**Relationships:**
- `coffee_id` → `coffees.id`
- `brew_method_id` → `brew_methods.id`

## Scraping Tables

### product_sources
Table storing product source information for scraping.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | string | No | Primary key (UUID) |
| roaster_id | string | No | Foreign key to roasters table |
| base_url | string | No | Base URL for scraping |
| platform | platform_enum | Yes | E-commerce platform |
| products_endpoint | string | Yes | Products API endpoint |
| sitemap_url | string | Yes | Sitemap URL |
| robots_ok | boolean | Yes | Robots.txt allows scraping |
| last_ok_ping | string | Yes | Last successful ping |

**Relationships:**
- `roaster_id` → `roasters.id`

### scrape_runs
Table storing scraping run information.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | string | No | Primary key (UUID) |
| source_id | string | Yes | Foreign key to product_sources table |
| started_at | string | No | Run start timestamp |
| finished_at | string | Yes | Run finish timestamp |
| status | run_status_enum | Yes | Run status |
| stats_json | Json | Yes | Run statistics |

**Relationships:**
- `source_id` → `product_sources.id`

### scrape_artifacts
Table storing scraping artifacts.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | string | No | Primary key (UUID) |
| run_id | string | Yes | Foreign key to scrape_runs table |
| url | string | Yes | Scraped URL |
| http_status | number | Yes | HTTP status code |
| body_len | number | Yes | Response body length |
| saved_html_path | string | Yes | Path to saved HTML |
| saved_json | Json | Yes | Saved JSON data |

**Relationships:**
- `run_id` → `scrape_runs.id`

## Database Views

### coffee_summary
View providing summarized coffee information.

| Column | Type | Description |
|--------|------|-------------|
| coffee_id | string | Coffee ID |
| name | string | Coffee name |
| roaster_id | string | Roaster ID |
| slug | string | Coffee slug |
| status | coffee_status_enum | Coffee status |
| process | process_enum | Processing method |
| process_raw | string | Raw process text |
| roast_level | roast_level_enum | Roast level |
| roast_level_raw | string | Raw roast level text |
| roast_style_raw | string | Raw roast style text |
| direct_buy_url | string | Direct buy URL |
| has_250g_bool | boolean | Whether 250g variant exists |
| has_sensory | boolean | Whether sensory data exists |
| in_stock_count | number | Number of in-stock variants |
| min_price_in_stock | number | Minimum in-stock price |
| best_variant_id | string | Best variant ID |
| best_normalized_250g | number | Best normalized 250g price |
| weights_available | number[] | Available weights |
| sensory_public | Json | Public sensory data |
| sensory_updated_at | string | Sensory data update timestamp |

### variant_computed
View providing computed variant information.

| Column | Type | Description |
|--------|------|-------------|
| variant_id | string | Variant ID |
| coffee_id | string | Coffee ID |
| weight_g | number | Weight in grams |
| grind | grind_enum | Grind type |
| pack_count | number | Pack count |
| currency | string | Currency |
| in_stock | boolean | Whether in stock |
| compare_at_price | number | Compare at price |
| price_one_time | number | One-time price |
| normalized_250g | number | Normalized 250g price |
| valid_for_best_value | boolean | Whether valid for best value |
| scraped_at_latest | string | Latest scrape timestamp |

### variant_latest_price
View providing latest price information for variants.

| Column | Type | Description |
|--------|------|-------------|
| variant_id | string | Variant ID |
| coffee_id | string | Coffee ID |
| weight_g | number | Weight in grams |
| grind | grind_enum | Grind type |
| pack_count | number | Pack count |
| currency | string | Currency |
| in_stock | boolean | Whether in stock |
| is_sale | boolean | Whether on sale |
| compare_at_price | number | Compare at price |
| price_one_time | number | One-time price |
| scraped_at_latest | string | Latest scrape timestamp |

## Indexes and Constraints

### Primary Keys
All tables have UUID primary keys.

### Foreign Key Constraints
- All foreign key relationships are enforced
- Cascade deletes are configured appropriately
- Referential integrity is maintained

### Unique Constraints
- `coffees.slug` is unique per roaster
- `roasters.slug` is unique
- `variants.platform_variant_id` is unique per coffee
- `prices` has unique constraint on variant_id + scraped_at

### Indexes
- Performance indexes on frequently queried columns
- Composite indexes for complex queries
- Full-text search indexes on text fields

## Data Types

### JSON Fields
- `notes_raw`: Raw notes data from various sources
- `source_raw`: Raw source data from scraping
- `social_json`: Social media information
- `stats_json`: Scraping run statistics

### Array Fields
- `varieties`: Array of coffee varieties
- `tags`: Array of product tags
- `weights_available`: Array of available weights

### Enum Fields
All enum fields use the database enum types defined in the schema.

## Best Practices

1. **Data Integrity**: Use foreign key constraints and check constraints
2. **Performance**: Create appropriate indexes for query patterns
3. **Scalability**: Use UUIDs for primary keys
4. **Flexibility**: Use JSON fields for extensible data
5. **Auditing**: Include created_at and updated_at timestamps
6. **Soft Deletes**: Use status fields instead of hard deletes where appropriate