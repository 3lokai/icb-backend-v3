# 9. Failure Modes & Mitigations

### 9.1 Common Failure Scenarios
- **Malformed JSON**: Persist raw blob, mark for review
- **DB Rate Limits**: Pause queue, exponential backoff, alert
- **Image Host Issues**: Use ImageKit remote fetch, flag failing domains
- **LLM Hallucination**: Store raw enrichment + confidence, don't auto-trust

### 9.2 Recovery Procedures
- **Queue Pause**: On DB rate limits, scale down workers
- **Worker OOMs**: Increase machine size or lower concurrency
- **Volume Failures**: Move to API-based persistence, restore from S3
- **Data Corruption**: Replay from raw artifacts in S3
