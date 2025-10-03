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
```sql
rpc_upsert_coffee(
  p_bean_species: species_enum,
  p_process: process_enum,
  p_roast_level: roast_level_enum,
  p_roaster_id: string,
  p_platform_product_id: string,
  p_name: string,
  p_slug: string,
  p_description_md: string,
  p_direct_buy_url: string,
  p_process_raw: string,
  p_roast_level_raw: string,
  p_roast_style_raw: string,
  p_acidity?: number,
  p_altitude?: number,
  p_body?: number,
  p_content_hash?: string,
  p_country?: string,
  p_decaf?: boolean,
  p_default_grind?: grind_enum,
  p_description_cleaned?: string,
  p_flavors?: string[],
  p_notes_raw?: Json,
  p_raw_hash?: string,
  p_region?: string,
  p_source_raw?: Json,
  p_status?: coffee_status_enum,
  p_tags?: string[],
  p_title_cleaned?: string,
  p_varieties?: string[]
) -> string
```
Upserts a coffee record and returns the coffee ID. Now includes Epic C normalization parameters for tags, geographic data, sensory parameters, and text cleaning.

### rpc_upsert_coffee_flavor_note
```sql
rpc_upsert_coffee_flavor_note(
  p_coffee_id: string,
  p_flavor_note_id: string
) -> boolean
```
Associates a flavor note with a coffee.

### rpc_upsert_coffee_image
```sql
rpc_upsert_coffee_image(
  p_alt?: string,
  p_coffee_id: string,
  p_content_hash?: string,
  p_height?: number,
  p_imagekit_url?: string,
  p_sort_order?: number,
  p_source_raw?: Json,
  p_url: string,
  p_width?: number
) -> string
```
Upserts a coffee image and returns the image ID. Now includes ImageKit CDN URL support.

### rpc_upsert_flavor_note
```sql
rpc_upsert_flavor_note(
  p_group_key?: string,
  p_key: string,
  p_label: string
) -> string
```
Upserts a flavor note and returns the flavor note ID.

## Roaster Management Functions

### rpc_upsert_roaster
```sql
rpc_upsert_roaster(
  p_instagram_handle?: string,
  p_name: string,
  p_platform: platform_enum,
  p_slug: string,
  p_social_json?: Json,
  p_support_email?: string,
  p_website: string
) -> string
```
Upserts a roaster record and returns the roaster ID.

## Variant Management Functions

### rpc_upsert_variant
```sql
rpc_upsert_variant(
  p_coffee_id: string,
  p_compare_at_price?: number,
  p_currency?: string,
  p_grind?: grind_enum,
  p_in_stock?: boolean,
  p_pack_count?: number,
  p_platform_variant_id: string,
  p_sku: string,
  p_source_raw?: Json,
  p_stock_qty?: number,
  p_subscription_available?: boolean,
  p_weight_g: number
) -> string
```
Upserts a coffee variant and returns the variant ID.

## Price Management Functions

### rpc_insert_price
```sql
rpc_insert_price(
  p_currency?: string,
  p_is_sale?: boolean,
  p_price: number,
  p_scraped_at?: string,
  p_source_raw?: Json,
  p_source_url?: string,
  p_variant_id: string
) -> string
```
Inserts a new price record and returns the price ID.

## Scraping Functions

### rpc_scrape_run_start
```sql
rpc_scrape_run_start(
  p_source_id: string
) -> string
```
Starts a new scraping run and returns the run ID.

### rpc_scrape_run_finish
```sql
rpc_scrape_run_finish(
  p_run_id: string,
  p_stats: Json,
  p_status: run_status_enum
) -> undefined
```
Finishes a scraping run with statistics and status.

### rpc_record_artifact
```sql
rpc_record_artifact(
  p_body_len: number,
  p_http_status: number,
  p_run_id: string,
  p_saved_html_path?: string,
  p_saved_json?: Json,
  p_url: string
) -> string
```
Records a scraping artifact and returns the artifact ID.

## Image Management Functions

### rpc_check_content_hash
```sql
rpc_check_content_hash(
  p_content_hash: string
) -> string
```
Checks for existing content hash and returns the image ID if found.

### rpc_check_duplicate_image_hash
```sql
rpc_check_duplicate_image_hash(
  p_content_hash: string
) -> string
```
Checks for duplicate image content hash and returns the duplicate image ID if found.

## Cache Management Functions

### cleanup_expired_llm_cache
```sql
cleanup_expired_llm_cache() -> number
```
Cleans up expired entries from the LLM cache and returns the number of entries removed.

## User Management Functions

### get_user_role
```sql
get_user_role(user_uuid UUID DEFAULT auth.uid()) -> user_role_enum
```
Gets the role of a specific user. Defaults to the current authenticated user.

### has_permission
```sql
has_permission(required_role user_role_enum) -> boolean
```
Checks if the current user has the required permission level based on role hierarchy:
- admin: All permissions
- operator: Admin and operator permissions
- user: Admin, operator, and user permissions  
- viewer: All permissions (read-only)

### assign_user_role
```sql
assign_user_role(
  target_user_id UUID,
  new_role user_role_enum,
  assigned_by UUID DEFAULT auth.uid()
) -> boolean
```
Assigns a role to a user. Only admins can assign roles. Returns true on success.

### get_users_with_roles
```sql
get_users_with_roles() -> TABLE (
  user_id UUID,
  email TEXT,
  role user_role_enum,
  created_at TIMESTAMP WITH TIME ZONE,
  last_sign_in TIMESTAMP WITH TIME ZONE
)
```
Returns all users with their roles and metadata. Only accessible by admins.

## Dashboard Analytics Functions

### get_price_trend_4w
```sql
get_price_trend_4w() -> TABLE (
  date DATE,
  price_updates BIGINT,
  avg_price NUMERIC
)
```
Returns price trend data for the last 4 weeks with daily aggregation.

### get_roaster_performance_30d
```sql
get_roaster_performance_30d() -> TABLE (
  roaster_id UUID,
  roaster_name TEXT,
  total_runs BIGINT,
  successful_runs BIGINT,
  success_rate NUMERIC,
  avg_duration_seconds NUMERIC
)
```
Returns roaster performance metrics for the last 30 days including success rates and average run duration.

### get_run_statistics_30d
```sql
get_run_statistics_30d() -> TABLE (
  date DATE,
  total_runs BIGINT,
  successful_runs BIGINT,
  failed_runs BIGINT,
  avg_duration_minutes NUMERIC
)
```
Returns daily run statistics for the last 30 days including success/failure counts and average duration.

## Epic C Functions

### get_epic_c_parameters
```sql
get_epic_c_parameters(
  p_coffee_id: string
) -> Json
```
Retrieves Epic C normalization parameters for a specific coffee.

## Legacy Functions

### map_roast_legacy
```sql
map_roast_legacy(
  raw: string
) -> roast_level_enum
```
Maps legacy roast level strings to the current roast level enum.

## GraphQL Functions

### graphql
```sql
graphql(
  extensions?: Json,
  operationName?: string,
  query?: string,
  variables?: Json
) -> Json
```
Executes GraphQL queries against the database.

## Function Usage Examples

### Creating a Coffee
```sql
SELECT rpc_upsert_coffee(
  p_bean_species := 'arabica',
  p_process := 'washed',
  p_roast_level := 'light',
  p_roaster_id := 'roaster_456',
  p_platform_product_id := 'prod_123',
  p_name := 'Ethiopian Yirgacheffe',
  p_slug := 'ethiopian-yirgacheffe',
  p_description_md := 'A bright and fruity Ethiopian coffee',
  p_direct_buy_url := 'https://roaster.com/coffee/ethiopian',
  p_process_raw := 'Washed Process',
  p_roast_level_raw := 'Light Roast',
  p_roast_style_raw := 'City Roast',
  p_decaf := false,
  p_tags := ARRAY['fruity', 'bright', 'ethiopian'],
  p_varieties := ARRAY['heirloom'],
  p_region := 'Yirgacheffe',
  p_country := 'Ethiopia',
  p_altitude := 2000,
  p_acidity := 8.5,
  p_body := 6.0,
  p_flavors := ARRAY['blueberry', 'lemon', 'jasmine']
);
```

### Creating a Variant
```sql
SELECT rpc_upsert_variant(
  p_coffee_id := 'coffee_789',
  p_currency := 'INR',
  p_grind := 'whole',
  p_in_stock := true,
  p_pack_count := 1,
  p_platform_variant_id := 'var_123',
  p_sku := 'ETH-WHOLE-250',
  p_weight_g := 250
);
```

### Recording a Price
```sql
SELECT rpc_insert_price(
  p_currency := 'INR',
  p_is_sale := false,
  p_price := 450.00,
  p_variant_id := 'variant_123'
);
```

### User Role Management
```sql
-- Check if current user has admin permissions
SELECT has_permission('admin');

-- Get current user's role
SELECT get_user_role();

-- Assign operator role to a user (admin only)
SELECT assign_user_role(
  target_user_id := 'user-uuid-here',
  new_role := 'operator'
);

-- Get all users with their roles (admin only)
SELECT * FROM get_users_with_roles();
```

### Dashboard Analytics
```sql
-- Get price trends for last 4 weeks
SELECT * FROM get_price_trend_4w();

-- Get roaster performance metrics
SELECT * FROM get_roaster_performance_30d();

-- Get daily run statistics
SELECT * FROM get_run_statistics_30d();
```

## Error Handling

All RPC functions return appropriate error messages for invalid inputs:

- **Invalid enum values**: Functions will reject invalid enum values
- **Missing required parameters**: Functions will return error for missing required fields
- **Foreign key violations**: Functions will return error for invalid foreign key references
- **Duplicate constraints**: Functions will handle duplicate key violations appropriately

## Performance Considerations

1. **Batch Operations**: Use batch operations when possible to reduce round trips
2. **Index Usage**: RPC functions leverage database indexes for optimal performance
3. **Transaction Safety**: All RPC functions are transaction-safe
4. **Concurrent Access**: Functions handle concurrent access appropriately

## Security

1. **Input Validation**: All inputs are validated before processing
2. **SQL Injection**: RPC functions are protected against SQL injection
3. **Access Control**: Functions respect database-level access controls
4. **Audit Trail**: All operations are logged for audit purposes