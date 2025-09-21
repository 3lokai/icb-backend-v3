# ICB Worker - Coffee Scraping Orchestrator

A Python-based worker system for scraping coffee data from roasters with proper job management, scheduling, and concurrency control.

## Architecture

- **Worker**: Long-running processes that dequeue and execute scraping jobs
- **Orchestrator**: Manages job scheduling and queue distribution
- **Scheduler**: GitHub Actions-based job scheduling with per-roaster cadence
- **Queue**: Redis-based job queue with retry logic and backoff

## Quick Start

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Run locally**:
   ```bash
   python -m src.worker.main
   ```

## Development

- **Testing**: `pytest`
- **Linting**: `flake8 src/`
- **Type checking**: `mypy src/`
- **Formatting**: `black src/`

## Configuration

The worker uses roaster-specific configuration from the database:
- `full_cadence`: Cron expression for full refresh (monthly)
- `price_cadence`: Cron expression for price updates (weekly)
- `default_concurrency`: Worker concurrency per roaster
- `use_firecrawl_fallback`: Enable Firecrawl fallback
- `use_llm`: Enable LLM enrichment

## Deployment

- **Production**: Fly.io worker machines
- **Scheduling**: GitHub Actions workflows
- **Queue**: Redis on Fly.io
- **Database**: Supabase PostgreSQL
