# 8. Development & Testing

### 8.1 Local Development
- **Docker Compose**: Worker + local Supabase emulator + mock Firecrawl
- **Environment Variables**: Same as Fly to minimize surprises
- **Testing**: Unit tests for parsers, integration tests with staging DB

### 8.2 CI/CD Pipeline
- **GitHub Actions**: Tests, linting, Docker builds, deployment
- **Staging First**: Deploy to staging before production
- **Feature Flags**: Toggle LLM enrichment and Firecrawl fallback
- **Security Scanning**: Docker image vulnerability checks

### 8.3 Quality Assurance
- **Golden Fixtures**: Full example artifacts for testing
- **Integration Tests**: End-to-end pipeline against staging
- **Monitoring**: Dashboards and Slack alerts configured
- **Manual Review**: UI for triaging flagged artifacts
