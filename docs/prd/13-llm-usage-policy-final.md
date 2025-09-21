# 13. LLM usage policy (final)

* LLM is **fallback-only**. Toggleable globally and per-roaster (`use_llm boolean` per roaster optional).
* Cache LLM outputs in `coffees.notes_raw` (JSON) and confidence scores.
* Auto-apply LLM outputs only if `llm_confidence >= 0.70`. Otherwise store result and mark `processing_status='review'` if the field is core (e.g., `roast_level_enum`).
