# 12. Image handling (final)

* Image detection: compare remote image URL hash vs stored image hash. Upload to ImageKit only on new/changed hash.
* Price-only job must **never** re-upload or transform images.
* Store both `images.source_url` (original) and `images.imagekit_url` (cdn). RPC `rpc_upsert_image` writes both.
