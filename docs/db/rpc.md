# Database RPC Functions

This document describes all Remote Procedure Call (RPC) functions available in the database.

## Core Functions

### citext Functions
Case-insensitive text functions.

#### citext
```sql
citext(boolean) -> string
citext(string) -> string  
citext(unknown) -> string
```
Converts input to case-insensitive text.

#### citext_hash
```sql
citext_hash(string) -> number
```
Returns hash value for case-insensitive text.

#### citextin
```sql
citextin(unknown) -> string
```
Input function for case-insensitive text.

#### citextout
```sql
citextout(string) -> unknown
```
Output function for case-insensitive text.

#### citextrecv
```sql
citextrecv(unknown) -> string
```
Receive function for case-insensitive text.

#### citextsend
```sql
citextsend(string) -> string
```
Send function for case-insensitive text.

## Coffee Management Functions

### rpc_upsert_coffee
Creates or updates a coffee record.

**Parameters:**
- `p_bean_species` (species_enum): Coffee species
- `p_decaf` (boolean, optional): Whether coffee is decaffeinated
- `p_description_md` (string): Markdown description
- `p_direct_buy_url` (string): Direct purchase URL
- `p_name` (string): Coffee name
- `p_notes_raw` (Json, optional): Raw notes data
- `p_platform_product_id` (string): Platform product ID
- `p_process` (process_enum): Processing method
- `p_process_raw` (string): Raw process description
- `p_roast_level` (roast_level_enum): Roast level
- `p_roast_level_raw` (string): Raw roast level description
- `p_roast_style_raw` (string): Roast style description
- `p_roaster_id` (string): Roaster ID
- `p_slug` (string): URL-friendly slug
- `p_source_raw` (Json, optional): Raw source data
- `p_status` (coffee_status_enum, optional): Coffee status

**Returns:** string (coffee ID)

### rpc_upsert_coffee_flavor_note
Links a coffee to a flavor note.

**Parameters:**
- `p_coffee_id` (string): Coffee ID
- `p_flavor_note_id` (string): Flavor note ID

**Returns:** boolean (success status)

### rpc_upsert_coffee_image
Creates or updates a coffee image.

**Parameters:**
- `p_coffee_id` (string): Coffee ID
- `p_url` (string): Image URL
- `p_alt` (string, optional): Alt text
- `p_height` (number, optional): Image height
- `p_width` (number, optional): Image width
- `p_sort_order` (number, optional): Display order
- `p_source_raw` (Json, optional): Raw source data

**Returns:** string (image ID)

## Roaster Management Functions

### rpc_upsert_roaster
Creates or updates a roaster record.

**Parameters:**
- `p_name` (string): Roaster name
- `p_slug` (string): URL-friendly slug
- `p_platform` (platform_enum): Platform type
- `p_website` (string): Website URL
- `p_instagram_handle` (string, optional): Instagram handle
- `p_social_json` (Json, optional): Social media data
- `p_support_email` (string, optional): Support email

**Returns:** string (roaster ID)

## Flavor Notes Functions

### rpc_upsert_flavor_note
Creates or updates a flavor note.

**Parameters:**
- `p_key` (string): Unique identifier
- `p_label` (string): Human-readable name
- `p_group_key` (string, optional): Grouping key

**Returns:** string (flavor note ID)

## Variant Management Functions

### rpc_upsert_variant
Creates or updates a coffee variant.

**Parameters:**
- `p_coffee_id` (string): Coffee ID
- `p_platform_variant_id` (string): Platform variant ID
- `p_sku` (string): SKU
- `p_weight_g` (number): Weight in grams
- `p_grind` (grind_enum, optional): Grind type
- `p_pack_count` (number, optional): Number of packs
- `p_currency` (string, optional): Currency code
- `p_in_stock` (boolean, optional): Stock status
- `p_stock_qty` (number, optional): Stock quantity
- `p_subscription_available` (boolean, optional): Subscription availability
- `p_compare_at_price` (number, optional): Compare at price
- `p_source_raw` (Json, optional): Raw source data

**Returns:** string (variant ID)

**Note:** This function has two overloads - one with all parameters and one without `p_stock_qty` and `p_subscription_available`.

## Price Management Functions

### rpc_insert_price
Inserts a new price record.

**Parameters:**
- `p_variant_id` (string): Variant ID
- `p_price` (number): Price value
- `p_currency` (string, optional): Currency code
- `p_is_sale` (boolean, optional): Whether price is a sale
- `p_scraped_at` (string, optional): Scraping timestamp
- `p_source_url` (string, optional): Source URL
- `p_source_raw` (Json, optional): Raw source data

**Returns:** string (price ID)

**Note:** This function has two overloads with identical parameters.

## Scraping Functions

### rpc_scrape_run_start
Starts a new scraping run.

**Parameters:**
- `p_source_id` (string): Product source ID

**Returns:** string (run ID)

### rpc_scrape_run_finish
Finishes a scraping run.

**Parameters:**
- `p_run_id` (string): Run ID
- `p_status` (run_status_enum): Run status
- `p_stats` (Json): Run statistics

**Returns:** undefined

### rpc_record_artifact
Records a scraping artifact.

**Parameters:**
- `p_run_id` (string): Run ID
- `p_url` (string): Scraped URL
- `p_http_status` (number): HTTP status code
- `p_body_len` (number): Response body length
- `p_saved_html_path` (string, optional): Path to saved HTML
- `p_saved_json` (Json, optional): Saved JSON data

**Returns:** string (artifact ID)

## Utility Functions

### map_roast_legacy
Maps legacy roast level descriptions to enum values.

**Parameters:**
- `raw` (string): Raw roast level description

**Returns:** roast_level_enum (mapped roast level)

## GraphQL Functions

### graphql
Executes GraphQL queries.

**Parameters:**
- `query` (string, optional): GraphQL query
- `variables` (Json, optional): Query variables
- `operationName` (string, optional): Operation name
- `extensions` (Json, optional): Extensions

**Returns:** Json (query result)

## Function Usage Examples

### Creating a Coffee
```sql
SELECT rpc_upsert_coffee(
  p_bean_species := 'arabica',
  p_name := 'Ethiopian Yirgacheffe',
  p_slug := 'ethiopian-yirgacheffe',
  p_roaster_id := 'roaster-123',
  p_process := 'washed',
  p_process_raw := 'Fully Washed',
  p_roast_level := 'light',
  p_roast_level_raw := 'Light Roast',
  p_roast_style_raw := 'City Roast',
  p_description_md := '# Ethiopian Yirgacheffe\nA bright and floral coffee...',
  p_direct_buy_url := 'https://roaster.com/ethiopian-yirgacheffe',
  p_platform_product_id := 'prod-123'
);
```

### Adding a Flavor Note
```sql
SELECT rpc_upsert_coffee_flavor_note(
  p_coffee_id := 'coffee-123',
  p_flavor_note_id := 'flavor-456'
);
```

### Recording a Price
```sql
SELECT rpc_insert_price(
  p_variant_id := 'variant-123',
  p_price := 25.99,
  p_currency := 'USD',
  p_is_sale := false,
  p_scraped_at := '2024-01-01T12:00:00Z'
);
```

### Starting a Scrape Run
```sql
SELECT rpc_scrape_run_start(
  p_source_id := 'source-123'
);
```

### Finishing a Scrape Run
```sql
SELECT rpc_scrape_run_finish(
  p_run_id := 'run-123',
  p_status := 'ok',
  p_stats := '{"pages_scraped": 50, "products_found": 25}'::json
);
```
