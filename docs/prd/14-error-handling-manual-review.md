# 14. Error handling & manual review

* Rules to push to manual review:
  * `parsing_warnings.length > 1`
  * `variant_count_change > 3`
  * `missing price` for all variants
  * LLM output below confidence threshold for core fields
  * > 10% price\_delta across roaster (suspicious)
* Manual review stores the raw payload in `coffees.source_raw` and sets `coffees.processing_status='review'` with reasons in `processing_warnings`.
