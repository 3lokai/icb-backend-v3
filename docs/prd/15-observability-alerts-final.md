# 15. Observability & alerts (final)

* Metrics: per-run artifacts processed, parse\_warnings\_count, percent\_reviewed, average\_time\_per\_artifact, RPC error rate.
* Alerts:
  * > 5% artifacts flagged review per run → Slack alert.
  * DB RPC errors > threshold → pause queue + alert.
  * Price-change spike: if > X% of variants changed > `price_delta_alert_threshold`, notify ops.

### 15.1 Observability & metrics (per fetch)

Emit metrics:
* `fetch_requests_total{store,platform,result=success|fail|not_modified}`
* `fetch_latency_ms{store}`
* `fetch_size_bytes{store}`
* `artifacts_validated_total{valid|invalid}`
* `firecrawl_extracts_total{store}`
* `llm_calls_total{store}`
* Alert when:
  * `fetch_fail_rate > 5%` per run
  * `artifacts_invalid_ratio > 3%` per run
  * `firecrawl_budget_exhausted` event

Log at two levels:
* **Info**: roaster-level run start/end, number of artifacts processed, variant price updates count.
* **Error**: persistent 4xx/5xx, parser exceptions, LLM failures, DB RPC failures.

Persist raw responses to S3/Supabase storage with path: `s3://<bucket>/artifacts/<roaster>/<YYYY>/<MM>/<artifact_id>.json` and save link to `coffees.source_raw` (or to `scrape_artifacts` if you choose that later).
