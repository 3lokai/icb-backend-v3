# 2. High-level flows

1. **Full pipeline (monthly)**
   * Fetch product artifact → Validate (Pydantic) → Persist raw artifact pointer/hashes → Normalize deterministic → (LLM enrichment if needed and enabled) → ImageKit upload (if new) → `rpc_upsert_coffee` (product + variants + latest prices) → mark processed.

2. **Price-only pipeline (weekly)**
   * Fetch minimal product/variants JSON → Compare `price_decimal` vs `variants.price_current` → `rpc_insert_price` for changes and update `variants.price_current`, `price_last_checked_at`, `in_stock`.
