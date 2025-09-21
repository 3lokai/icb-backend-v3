# 6. RPC contracts (finalized)

All writes to canonical tables should go through server-side RPCs for atomicity and access control.

### 6.1 `rpc_upsert_coffee` — product metadata + variants + optional images

* **Purpose:** Upsert coffee + variants + optionally prices and images in a single transaction.
* **Signature (Postgres function stub):**

```sql
-- Using existing rpc_upsert_coffee function with actual parameters:
CREATE OR REPLACE FUNCTION rpc_upsert_coffee(
  p_bean_species species_enum,
  p_name text,
  p_slug text,
  p_roaster_id uuid,
  p_process process_enum,
  p_process_raw text,
  p_roast_level roast_level_enum,
  p_roast_level_raw text,
  p_roast_style_raw text,
  p_description_md text,
  p_direct_buy_url text,
  p_platform_product_id text,
  p_status coffee_status_enum DEFAULT 'active',
  p_decaf boolean DEFAULT false,
  p_notes_raw jsonb DEFAULT NULL,
  p_source_raw jsonb DEFAULT NULL
) RETURNS uuid LANGUAGE plpgsql SECURITY DEFINER AS $$
  -- Implementation handles coffee upsert with existing schema
$$;
```

* **Notes:** This function handles coffee metadata upsert. For variants and prices, use separate `rpc_upsert_variant` and `rpc_insert_price` functions.

### 6.2 `rpc_upsert_variant` — single variant upsert

* **Signature:** Uses existing `rpc_upsert_variant` function with parameters: `p_coffee_id`, `p_platform_variant_id`, `p_sku`, `p_weight_g`, `p_grind`, `p_currency`, `p_in_stock`, `p_source_raw`. Returns variant id.

### 6.3 `rpc_insert_price` — price time-series insert

* **Signature:**

```sql
-- Using existing rpc_insert_price function with actual parameters:
CREATE OR REPLACE FUNCTION rpc_insert_price(
  p_variant_id uuid,
  p_price numeric,
  p_currency text DEFAULT 'USD',
  p_is_sale boolean DEFAULT false,
  p_scraped_at timestamptz DEFAULT now(),
  p_source_url text DEFAULT NULL,
  p_source_raw jsonb DEFAULT NULL
) RETURNS uuid LANGUAGE plpgsql SECURITY DEFINER AS $$ ... $$;
```

* **Behavior:** Insert price row, update `variants.price_current` and `variants.price_last_checked_at` atomically.

### 6.4 `rpc_upsert_image` — image record (called after ImageKit upload)

* **Signature:** Uses existing `rpc_upsert_coffee_image` function with parameters: `p_coffee_id`, `p_url`, `p_alt`, `p_width`, `p_height`, `p_sort_order`, `p_source_raw`. Returns image id.
