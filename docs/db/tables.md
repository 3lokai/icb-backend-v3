# Database Tables

This document describes all tables in the database schema.

## Core Tables

### brew_methods
Brewing methods available for coffee preparation.

| Column | Type | Description |
|--------|------|-------------|
| id | string | Primary key |
| key | string | Unique identifier for the brew method |
| label | string | Human-readable name |

### coffees
Main coffee products table.

| Column | Type | Description |
|--------|------|-------------|
| id | string | Primary key |
| name | string | Coffee name |
| slug | string | URL-friendly identifier |
| roaster_id | string | Foreign key to roasters table |
| bean_species | species_enum | Coffee species (arabica, robusta, liberica, blend) |
| process | process_enum | Processing method (washed, natural, honey, etc.) |
| process_raw | string | Original process description |
| roast_level | roast_level_enum | Roast level (light, medium, dark, etc.) |
| roast_level_raw | string | Original roast level description |
| roast_style_raw | string | Additional roast style information |
| decaf | boolean | Whether coffee is decaffeinated |
| is_limited | boolean | Whether coffee is limited edition |
| is_coffee | boolean | Whether this is actually coffee (vs other products) |
| crop_year | number | Year of coffee harvest |
| harvest_window | string | Harvest period description |
| description_md | string | Markdown description |
| notes_lang | string | Language of notes |
| notes_raw | Json | Raw notes data |
| direct_buy_url | string | Direct purchase URL |
| platform_product_id | string | Platform-specific product ID |
| vendor_sku | string | Vendor SKU |
| rating_avg | number | Average rating |
| rating_count | number | Number of ratings |
| status | coffee_status_enum | Coffee status (active, seasonal, discontinued, etc.) |
| seo_title | string | SEO title |
| seo_desc | string | SEO description |
| source_raw | Json | Raw source data |
| tags | string[] | Array of tags |
| varieties | string[] | Array of coffee varieties |
| first_seen_at | string | First time this coffee was seen |
| created_at | string | Creation timestamp |
| updated_at | string | Last update timestamp |

### roasters
Coffee roasters and companies.

| Column | Type | Description |
|--------|------|-------------|
| id | string | Primary key |
| name | string | Roaster name |
| slug | string | URL-friendly identifier |
| platform | platform_enum | Platform type (shopify, woocommerce, custom, other) |
| is_active | boolean | Whether roaster is active |
| website | string | Roaster website URL |
| support_email | string | Support email |
| phone | string | Phone number |
| instagram_handle | string | Instagram handle |
| social_json | Json | Social media data |
| hq_country | string | Headquarters country |
| hq_state | string | Headquarters state |
| hq_city | string | Headquarters city |
| lat | number | Latitude coordinate |
| lon | number | Longitude coordinate |
| alert_price_delta_pct | number | Price change alert threshold percentage |
| default_concurrency | number | Default scraping concurrency |
| firecrawl_budget_limit | number | Firecrawl budget limit |
| full_cadence | string | Full scraping cadence |
| price_cadence | string | Price scraping cadence |
| robots_allow | boolean | Whether robots.txt allows scraping |
| robots_checked_at | string | Last robots.txt check timestamp |
| use_firecrawl_fallback | boolean | Whether to use Firecrawl fallback |
| use_llm | boolean | Whether to use LLM processing |
| last_etag | string | Last ETag for caching |
| last_modified | string | Last modification timestamp |
| created_at | string | Creation timestamp |
| updated_at | string | Last update timestamp |

### variants
Coffee product variants (different sizes, grinds, etc.).

| Column | Type | Description |
|--------|------|-------------|
| id | string | Primary key |
| coffee_id | string | Foreign key to coffees table |
| grind | grind_enum | Grind type (whole, filter, espresso, etc.) |
| weight_g | number | Weight in grams |
| pack_count | number | Number of packs |
| currency | string | Currency code |
| in_stock | boolean | Whether variant is in stock |
| stock_qty | number | Stock quantity |
| subscription_available | boolean | Whether subscription is available |
| platform_variant_id | string | Platform-specific variant ID |
| sku | string | SKU |
| barcode | string | Barcode |
| compare_at_price | number | Compare at price |
| price_current | number | Current price |
| price_last_checked_at | string | Last price check timestamp |
| status | string | Variant status |
| last_seen_at | string | Last time variant was seen |
| source_raw | Json | Raw source data |
| created_at | string | Creation timestamp |
| updated_at | string | Last update timestamp |

### prices
Price history for coffee variants.

| Column | Type | Description |
|--------|------|-------------|
| id | string | Primary key |
| variant_id | string | Foreign key to variants table |
| price | number | Price value |
| currency | string | Currency code |
| is_sale | boolean | Whether price is a sale price |
| source_url | string | Source URL |
| source_raw | Json | Raw source data |
| scraped_at | string | Scraping timestamp |

## Junction Tables

### coffee_brew_methods
Links coffees to brew methods.

| Column | Type | Description |
|--------|------|-------------|
| coffee_id | string | Foreign key to coffees table |
| brew_method_id | string | Foreign key to brew_methods table |

### coffee_estates
Links coffees to estates with percentage.

| Column | Type | Description |
|--------|------|-------------|
| coffee_id | string | Foreign key to coffees table |
| estate_id | string | Foreign key to estates table |
| pct | number | Percentage of coffee from this estate |

### coffee_flavor_notes
Links coffees to flavor notes.

| Column | Type | Description |
|--------|------|-------------|
| coffee_id | string | Foreign key to coffees table |
| flavor_note_id | string | Foreign key to flavor_notes table |

### coffee_regions
Links coffees to regions with percentage.

| Column | Type | Description |
|--------|------|-------------|
| coffee_id | string | Foreign key to coffees table |
| region_id | string | Foreign key to regions table |
| pct | number | Percentage of coffee from this region |

## Supporting Tables

### estates
Coffee estates and farms.

| Column | Type | Description |
|--------|------|-------------|
| id | string | Primary key |
| name | string | Estate name |
| region_id | string | Foreign key to regions table |
| altitude_min_m | number | Minimum altitude in meters |
| altitude_max_m | number | Maximum altitude in meters |
| notes | string | Additional notes |

### regions
Geographic regions.

| Column | Type | Description |
|--------|------|-------------|
| id | string | Primary key |
| display_name | string | Display name for the region |
| country | string | Country name |
| state | string | State/province name |
| subregion | string | Subregion name |

### flavor_notes
Coffee flavor notes and descriptors.

| Column | Type | Description |
|--------|------|-------------|
| id | string | Primary key |
| key | string | Unique identifier |
| label | string | Human-readable name |
| group_key | string | Grouping key for related notes |

### coffee_images
Images associated with coffees.

| Column | Type | Description |
|--------|------|-------------|
| id | string | Primary key |
| coffee_id | string | Foreign key to coffees table |
| url | string | Image URL |
| alt | string | Alt text |
| width | number | Image width |
| height | number | Image height |
| sort_order | number | Display order |
| source_raw | Json | Raw source data |

### sensory_params
Sensory analysis parameters for coffees.

| Column | Type | Description |
|--------|------|-------------|
| coffee_id | string | Foreign key to coffees table (one-to-one) |
| acidity | number | Acidity rating |
| sweetness | number | Sweetness rating |
| bitterness | number | Bitterness rating |
| body | number | Body rating |
| clarity | number | Clarity rating |
| aftertaste | number | Aftertaste rating |
| confidence | sensory_confidence_enum | Confidence level (high, medium, low) |
| source | sensory_source_enum | Source of data (roaster, icb_inferred, icb_manual) |
| notes | string | Additional notes |
| created_at | string | Creation timestamp |
| updated_at | string | Last update timestamp |

## System Tables

### product_sources
Data sources for product scraping.

| Column | Type | Description |
|--------|------|-------------|
| id | string | Primary key |
| roaster_id | string | Foreign key to roasters table |
| base_url | string | Base URL for scraping |
| platform | platform_enum | Platform type |
| products_endpoint | string | Products API endpoint |
| sitemap_url | string | Sitemap URL |
| robots_ok | boolean | Whether robots.txt allows scraping |
| last_ok_ping | string | Last successful ping timestamp |

### scrape_runs
Scraping run records.

| Column | Type | Description |
|--------|------|-------------|
| id | string | Primary key |
| source_id | string | Foreign key to product_sources table |
| started_at | string | Start timestamp |
| finished_at | string | End timestamp |
| status | run_status_enum | Run status (ok, partial, fail) |
| stats_json | Json | Run statistics |

### scrape_artifacts
Scraped data artifacts.

| Column | Type | Description |
|--------|------|-------------|
| id | string | Primary key |
| run_id | string | Foreign key to scrape_runs table |
| url | string | Scraped URL |
| http_status | number | HTTP response status |
| body_len | number | Response body length |
| saved_html_path | string | Path to saved HTML |
| saved_json | Json | Saved JSON data |

## Views

### coffee_summary
Summary view of coffees with computed fields.

| Column | Type | Description |
|--------|------|-------------|
| coffee_id | string | Coffee ID |
| name | string | Coffee name |
| slug | string | Coffee slug |
| roaster_id | string | Roaster ID |
| status | coffee_status_enum | Coffee status |
| process | process_enum | Process method |
| process_raw | string | Raw process description |
| roast_level | roast_level_enum | Roast level |
| roast_level_raw | string | Raw roast level |
| roast_style_raw | string | Roast style |
| direct_buy_url | string | Direct buy URL |
| has_250g_bool | boolean | Whether 250g variant exists |
| has_sensory | boolean | Whether sensory data exists |
| in_stock_count | number | Number of in-stock variants |
| min_price_in_stock | number | Minimum in-stock price |
| best_normalized_250g | number | Best normalized 250g price |
| best_variant_id | string | Best variant ID |
| weights_available | number[] | Available weights |
| sensory_public | Json | Public sensory data |
| sensory_updated_at | string | Sensory data update timestamp |

### variant_computed
Computed variant data.

| Column | Type | Description |
|--------|------|-------------|
| variant_id | string | Variant ID |
| coffee_id | string | Coffee ID |
| grind | grind_enum | Grind type |
| weight_g | number | Weight in grams |
| pack_count | number | Pack count |
| currency | string | Currency |
| in_stock | boolean | In stock status |
| price_one_time | number | One-time price |
| compare_at_price | number | Compare at price |
| normalized_250g | number | Normalized 250g price |
| valid_for_best_value | boolean | Valid for best value calculation |
| scraped_at_latest | string | Latest scraping timestamp |

### variant_latest_price
Latest price information for variants.

| Column | Type | Description |
|--------|------|-------------|
| variant_id | string | Variant ID |
| coffee_id | string | Coffee ID |
| grind | grind_enum | Grind type |
| weight_g | number | Weight in grams |
| pack_count | number | Pack count |
| currency | string | Currency |
| in_stock | boolean | In stock status |
| price_one_time | number | One-time price |
| compare_at_price | number | Compare at price |
| is_sale | boolean | Whether price is a sale |
| scraped_at_latest | string | Latest scraping timestamp |
