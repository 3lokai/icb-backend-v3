# 10. Normalization & LLM fallback (brief)

* Run deterministic parsers first: weight parsing, currency normalization, roast level mapping, variety extraction. If deterministics pass and `llm_enrichment` not required → continue.
* If ambiguous fields remain (e.g., weight parsing fails or roast parsing ambiguous), **queue a limited LLM enrichment** call (rate-limited per minute and per-store). Cache result and only auto-apply if `llm_confidence >= 0.70`.
