# Cross-Epic Tasks & Dependencies

* **DB migrations** (final migration SQL) must be applied on staging before RPC & pipeline integration stories run. (Dependency for A.4, A.5, B.2, F.1)
* **Secrets & Fly configuration**: create staging/prod Fly secrets for Supabase, ImageKit, LLM provider before deployments. (Dependency for D, F)
* **Feature flags**: implement global and per-roaster flags for `use_llm` and `use_firecrawl_fallback`. (Dependency for D & E)
* **Golden fixtures**: use `canonical_artifact.json` and `full_example.json` for unit & integration tests. (Dependency for C, H)

---
