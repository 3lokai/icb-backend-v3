# 20. Acceptance criteria (final)

* **Monthly full run (sample 100 products)**: ≥95% products have `name_clean`, `description_md_clean`, and `default_pack_weight_g` populated; images uploaded to ImageKit; ≤3% artifacts `processing_status='review'`.
* **Weekly price run (sample 100 products)**: ≥99% reachable variants updated `price_last_checked_at`; price deltas recorded in `prices` table; job completes within operational window without DB rate-limit.
