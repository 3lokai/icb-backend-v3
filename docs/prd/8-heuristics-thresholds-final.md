# 8. Heuristics & thresholds (final)

* `price_delta_alert_threshold = 0.10` (10%) — configurable per roaster via a `roasters.alert_price_delta_pct` optional column (suggested).
* `max_parse_warnings_before_review = 1` — if `processing_warnings` array length > 1, set `processing_status='review'`.
* `max_variant_count_change = 3` — if number of variants added/removed > 3 in full run → `processing_status='review'`.
* `llm_confidence_threshold = 0.70` — only auto-commit llm\_enrichment if confidence >= 0.7; otherwise store enrichment JSON and mark for review if critical.
