# 16. Backfill scripts (final)

* **Backfill `price_current`** from `prices`:

```sql
-- backfill_price_current.sql
WITH latest_price AS (
  SELECT DISTINCT ON (variant_id) variant_id, price
  FROM prices
  ORDER BY variant_id, scraped_at DESC
)
UPDATE variants v
SET price_current = lp.price
FROM latest_price lp
WHERE v.id = lp.variant_id
  AND (v.price_current IS NULL OR v.price_current <> lp.price);
```
