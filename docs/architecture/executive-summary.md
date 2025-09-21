# Executive Summary

This document defines the comprehensive architecture for a production-ready coffee product scraping pipeline that fetches, normalizes, and stores coffee product data from various e-commerce platforms. The system is designed for deployment on Fly.io with robust error handling, observability, and scalability.

**Key Goals:**
- Monthly full product refresh (metadata + normalization + images + optional LLM enrichment)
- Weekly price-only refresh (prices + availability) that is fast, cheap, and idempotent
- Minimal schema changes to existing database
- Production-ready deployment on Fly.io with comprehensive monitoring
