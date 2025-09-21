# 17. Indexes & performance (final)

Add these indexes to keep queries fast:

```sql
CREATE INDEX IF NOT EXISTS idx_prices_variant_scraped_at ON prices(variant_id, scraped_at DESC);
CREATE INDEX IF NOT EXISTS idx_variants_status ON variants(status);
CREATE INDEX IF NOT EXISTS idx_coffees_content_hash ON coffees(content_hash);
```
