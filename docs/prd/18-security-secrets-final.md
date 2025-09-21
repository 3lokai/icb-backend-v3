# 18. Security & secrets (final)

* Supabase RPC credentials: use a **server-side** service role for RPC execution stored in Fly secrets. Do **not** embed in client code.
* ImageKit keys stored in Fly secrets / CI secrets.
* LLM keys stored and rotated; usage metered and capped.
