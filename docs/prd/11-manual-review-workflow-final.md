# 11. Manual review workflow (final)

* `processing_status='review'` flags coffee for triage. UI/QA queries `coffees WHERE processing_status='review'`.
* `processing_warnings` contains detail: e.g., `["price missing", "weight ambiguous: '12oz'"]`.
* If human resolves, call `rpc_upsert_coffee` with corrected payload and set `processing_status='ok'` and populate `processing_warnings` with resolution notes.
