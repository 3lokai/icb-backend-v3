# 7. Performance & Scalability

### 7.1 Non-Functional Requirements
- **Throughput**: 500 products/minute across pool
- **Latency**: Per-artifact pipeline < 5s (excluding image upload & LLM)
- **Availability**: 99.5% for pipeline scheduler and worker execution
- **Error Budget**: <1% failed artifacts/week (excluding malformed roasters)

### 7.2 Scaling Strategy
- **Horizontal Scaling**: Increase worker machine count
- **Per-Roaster Concurrency**: Configure via worker settings, not machine count
- **Auto-scaling**: Fly autoscaling features for autostop/autostart
- **Backpressure**: Pause queue on Supabase RPC rate limits
