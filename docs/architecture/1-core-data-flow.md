# 1. Core Data Flow

### 1.1 Full Pipeline (Monthly)
1. **Fetch** → Store JSON endpoints (Shopify/Woo) as primary source
2. **Validate** → Pydantic v2 validation against canonical artifact schema
3. **Persist** → Raw artifact pointer/hashes to S3/Supabase Storage
4. **Normalize** → Deterministic parsing (weights, roast levels, etc.)
5. **Enrich** → Optional LLM enrichment for ambiguous fields
6. **Upload** → ImageKit upload for new/changed images
7. **Upsert** → `rpc_upsert_coffee` + `rpc_upsert_variant` + `rpc_insert_price` (product + variants + latest prices)
8. **Mark** → Processed status and audit trail

### 1.2 Price-Only Pipeline (Weekly)
1. **Fetch** → Minimal product/variants JSON from list endpoints
2. **Compare** → `price_decimal` vs `variants.price_current`
3. **Update** → `rpc_insert_price` for changes
4. **Sync** → Update `variants.price_current`, `variants.price_last_checked_at`, `variants.in_stock`
