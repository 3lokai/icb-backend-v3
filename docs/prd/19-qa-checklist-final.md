# 19. QA checklist (final)

* [ ] Migrations applied to staging.
* [ ] Golden fixtures: `full_example.json` + `price_delta_example.json`.
* [ ] Unit tests for parser (weight, currency, price detection).
* [ ] Integration test: run monthly full pipeline against staging stores; verify `coffees.processing_status` behavior.
* [ ] Integration test: run weekly price-only pipeline; verify `rpc_insert_price` calls and `variants.price_current`.
* [ ] Feature flag tests: LLM off/on, Firecrawl fallback off/on.
* [ ] Monitor dashboards + Slack alerts configured before prod run.
