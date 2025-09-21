# 4. Deployment Architecture (Fly.io)

### 4.1 Fly App Structure
Split into multiple Fly apps for isolation and scaling:

1. **api-web**: Web UI, health endpoints, status pages (publicly exposed)
2. **worker-ingest**: Long-running workers for fetch → validate → normalize → transform → RPC upsert
3. **worker-image**: Dedicated image download + ImageKit uploader (optional)
4. **scheduler**: Tiny machine or GitHub Actions for job scheduling
5. **dev/staging**: Mirrors with smaller machines and separate secrets/DB

### 4.2 Filesystem & Persistence
- **Ephemeral Rootfs**: Machine restarts replace root filesystem
- **External Storage**: S3/Supabase Storage for raw artifacts and image backups
- **Fly Volumes**: Only for low-latency, high-I/O needs where persistent local disk is required
- **Worker Design**: Idempotent workers that push results to external storage immediately

### 4.3 Secrets & Configuration
- **Runtime Secrets**: `fly secrets set` per environment
- **Service Role**: RPC-only service accounts in Supabase
- **Per-Roaster Config**: Rate limits, auth tokens in secure config table
- **Environment Separation**: Staging and prod with separate secrets/DB
