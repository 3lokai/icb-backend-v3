# 21. Pseudocode: orchestrator & worker

Scheduler (high level):

```
for each roaster in active_roasters:
  if now matches roaster.full_cadence and last_full_run older than cadence:
      enqueue Job(roaster.id, job_type='full')
  if now matches roaster.price_cadence:
      enqueue Job(roaster.id, job_type='price_only')
```

Worker (per job):

```
job = queue.get()
with roaster_semaphore(job.roaster_id):
  if job.type == 'price_only':
     run price_only_for_roaster(job.roaster_id)
  else:
     run full_refresh_for_roaster(job.roaster_id)
```

Full refresh flow:

```
pages = discover_list_pages(roaster)
for page in pages:
   resp = fetch_json(page.url)
   save_raw(resp)
   for product in resp.products:
      artifact = build_artifact(product, collector_meta)
      validate(artifact) -> pydantic
      if valid:
         normalize(artifact)
         if content_hash == db.content_hash:
            handle_price_deltas_only_if_price_changed()
         else:
            maybe_call_llm_if_needed()
            upload_images_if_changed()
            call rpc_upsert_coffee() + rpc_upsert_variant() + rpc_insert_price()
      else:
         mark_review(artifact)
```

Price-only flow:

```
pages = discover_list_pages(roaster)
for page in pages:
   resp = fetch_json(page.url)
   for product in resp.products:
      for variant in product.variants:
         if variant.price != db.variant.price_current:
            rpc_insert_price(...)
         update variant.price_last_checked_at
```
