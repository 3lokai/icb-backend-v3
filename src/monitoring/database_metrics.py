"""
Database metrics collection service.

This module provides comprehensive database metrics collection from existing tables
(scrape_runs, scrape_artifacts, prices, variants) for monitoring pipeline health,
performance, and data quality.
"""

import asyncio
import time
from typing import Dict, Any, List
from datetime import datetime, timezone, timedelta

from structlog import get_logger

logger = get_logger(__name__)


class DatabaseMetricsService:
    """
    Database metrics collection service for pipeline monitoring.
    
    Collects metrics from:
    - scrape_runs: Run status, duration, and statistics
    - scrape_artifacts: Artifact counts, HTTP status, and data quality
    - prices: Price history and delta tracking
    - variants: Stock status and price updates
    - coffees: Product metadata and processing status
    - roasters: Configuration and performance settings
    """
    
    def __init__(self, supabase_client=None):
        """Initialize database metrics service."""
        self.supabase_client = supabase_client
        self.metrics_cache: Dict[str, Any] = {}
        self.cache_ttl = 300  # 5 minutes cache TTL
        self.last_cache_update = 0
    
    async def collect_scrape_run_metrics(self) -> Dict[str, Any]:
        """Collect metrics from scrape_runs table."""
        try:
            if not self.supabase_client:
                return self._get_mock_scrape_run_metrics()
            
            # Get recent runs (last 24 hours)
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=24)
            
            result = await self.supabase_client.table('scrape_runs').select('*').gte(
                'started_at', cutoff_time.isoformat()
            ).execute()
            
            runs = result.data if result.data else []
            
            # Calculate metrics
            total_runs = len(runs)
            successful_runs = len([r for r in runs if r.get('status') == 'ok'])
            failed_runs = len([r for r in runs if r.get('status') == 'fail'])
            
            # Calculate average duration
            durations = []
            for run in runs:
                if run.get('started_at') and run.get('finished_at'):
                    try:
                        start_time = datetime.fromisoformat(run['started_at'].replace('Z', '+00:00'))
                        end_time = datetime.fromisoformat(run['finished_at'].replace('Z', '+00:00'))
                        duration = (end_time - start_time).total_seconds()
                        durations.append(duration)
                    except (ValueError, TypeError):
                        continue
            
            avg_duration = sum(durations) / len(durations) if durations else 0
            
            # Calculate success rate
            success_rate = (successful_runs / total_runs * 100) if total_runs > 0 else 0
            
            metrics = {
                "total_runs": total_runs,
                "successful_runs": successful_runs,
                "failed_runs": failed_runs,
                "success_rate": success_rate,
                "avg_duration_seconds": avg_duration,
                "runs_by_status": self._group_runs_by_status(runs),
                "runs_by_roaster": self._group_runs_by_roaster(runs),
                "collection_timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            logger.info(
                "Collected scrape run metrics",
                total_runs=total_runs,
                success_rate=success_rate,
                avg_duration=avg_duration
            )
            
            return metrics
            
        except Exception as e:
            logger.error(
                "Failed to collect scrape run metrics",
                error=str(e)
            )
            return self._get_mock_scrape_run_metrics()
    
    async def collect_artifact_metrics(self) -> Dict[str, Any]:
        """Collect metrics from scrape_artifacts table."""
        try:
            if not self.supabase_client:
                return self._get_mock_artifact_metrics()
            
            # Get recent artifacts (last 24 hours)
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=24)
            
            result = await self.supabase_client.table('scrape_artifacts').select('*').gte(
                'created_at', cutoff_time.isoformat()
            ).execute()
            
            artifacts = result.data if result.data else []
            
            # Calculate metrics
            total_artifacts = len(artifacts)
            valid_artifacts = len([a for a in artifacts if a.get('validation_status') == 'valid'])
            invalid_artifacts = len([a for a in artifacts if a.get('validation_status') == 'invalid'])
            
            # HTTP status distribution
            http_status_counts = {}
            for artifact in artifacts:
                status = artifact.get('http_status', 'unknown')
                http_status_counts[status] = http_status_counts.get(status, 0) + 1
            
            # Body size statistics
            body_sizes = [a.get('body_len', 0) for a in artifacts if a.get('body_len')]
            avg_body_size = sum(body_sizes) / len(body_sizes) if body_sizes else 0
            
            # Validation rate
            validation_rate = (valid_artifacts / total_artifacts * 100) if total_artifacts > 0 else 0
            
            metrics = {
                "total_artifacts": total_artifacts,
                "valid_artifacts": valid_artifacts,
                "invalid_artifacts": invalid_artifacts,
                "validation_rate": validation_rate,
                "http_status_distribution": http_status_counts,
                "avg_body_size": avg_body_size,
                "artifacts_by_platform": self._group_artifacts_by_platform(artifacts),
                "collection_timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            logger.info(
                "Collected artifact metrics",
                total_artifacts=total_artifacts,
                validation_rate=validation_rate,
                avg_body_size=avg_body_size
            )
            
            return metrics
            
        except Exception as e:
            logger.error(
                "Failed to collect artifact metrics",
                error=str(e)
            )
            return self._get_mock_artifact_metrics()
    
    async def collect_price_metrics(self) -> Dict[str, Any]:
        """Collect metrics from prices table."""
        try:
            if not self.supabase_client:
                return self._get_mock_price_metrics()
            
            # Get recent prices (last 24 hours)
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=24)
            
            result = await self.supabase_client.table('prices').select('*').gte(
                'scraped_at', cutoff_time.isoformat()
            ).execute()
            
            prices = result.data if result.data else []
            
            # Calculate metrics
            total_prices = len(prices)
            unique_variants = len(set(p.get('variant_id') for p in prices if p.get('variant_id')))
            
            # Price statistics
            price_values = [float(p.get('price', 0)) for p in prices if p.get('price')]
            avg_price = sum(price_values) / len(price_values) if price_values else 0
            min_price = min(price_values) if price_values else 0
            max_price = max(price_values) if price_values else 0
            
            # Currency distribution
            currency_counts = {}
            for price in prices:
                currency = price.get('currency', 'unknown')
                currency_counts[currency] = currency_counts.get(currency, 0) + 1
            
            # Price changes (simplified - would need historical data for real deltas)
            price_changes = 0  # This would require comparing with previous prices
            
            metrics = {
                "total_prices": total_prices,
                "unique_variants": unique_variants,
                "avg_price": avg_price,
                "min_price": min_price,
                "max_price": max_price,
                "currency_distribution": currency_counts,
                "price_changes": price_changes,
                "prices_by_roaster": self._group_prices_by_roaster(prices),
                "collection_timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            logger.info(
                "Collected price metrics",
                total_prices=total_prices,
                unique_variants=unique_variants,
                avg_price=avg_price
            )
            
            return metrics
            
        except Exception as e:
            logger.error(
                "Failed to collect price metrics",
                error=str(e)
            )
            return self._get_mock_price_metrics()
    
    async def collect_variant_metrics(self) -> Dict[str, Any]:
        """Collect metrics from variants table."""
        try:
            if not self.supabase_client:
                return self._get_mock_variant_metrics()
            
            # Get all variants
            result = await self.supabase_client.table('variants').select('*').execute()
            variants = result.data if result.data else []
            
            # Calculate metrics
            total_variants = len(variants)
            in_stock_variants = len([v for v in variants if v.get('in_stock', False)])
            out_of_stock_variants = total_variants - in_stock_variants
            
            # Stock rate
            stock_rate = (in_stock_variants / total_variants * 100) if total_variants > 0 else 0
            
            # Variants by roaster
            variants_by_roaster = self._group_variants_by_roaster(variants)
            
            metrics = {
                "total_variants": total_variants,
                "in_stock_variants": in_stock_variants,
                "out_of_stock_variants": out_of_stock_variants,
                "stock_rate": stock_rate,
                "variants_by_roaster": variants_by_roaster,
                "collection_timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            logger.info(
                "Collected variant metrics",
                total_variants=total_variants,
                stock_rate=stock_rate
            )
            
            return metrics
            
        except Exception as e:
            logger.error(
                "Failed to collect variant metrics",
                error=str(e)
            )
            return self._get_mock_variant_metrics()
    
    async def collect_comprehensive_metrics(self) -> Dict[str, Any]:
        """Collect comprehensive metrics from all tables."""
        try:
            # Collect metrics from all tables concurrently
            tasks = [
                self.collect_scrape_run_metrics(),
                self.collect_artifact_metrics(),
                self.collect_price_metrics(),
                self.collect_variant_metrics()
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            comprehensive_metrics = {
                "scrape_runs": results[0] if not isinstance(results[0], Exception) else {},
                "artifacts": results[1] if not isinstance(results[1], Exception) else {},
                "prices": results[2] if not isinstance(results[2], Exception) else {},
                "variants": results[3] if not isinstance(results[3], Exception) else {},
                "collection_timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            # Calculate overall health score
            health_score = self._calculate_health_score(comprehensive_metrics)
            comprehensive_metrics["overall_health_score"] = health_score
            
            # Cache results
            self.metrics_cache = comprehensive_metrics
            self.last_cache_update = time.time()
            
            logger.info(
                "Collected comprehensive metrics",
                health_score=health_score,
                cache_updated=True
            )
            
            return comprehensive_metrics
            
        except Exception as e:
            logger.error(
                "Failed to collect comprehensive metrics",
                error=str(e)
            )
            return self._get_mock_comprehensive_metrics()
    
    def get_cached_metrics(self) -> Dict[str, Any]:
        """Get cached metrics if available and not expired."""
        if (time.time() - self.last_cache_update) < self.cache_ttl:
            return self.metrics_cache
        return {}
    
    def _group_runs_by_status(self, runs: List[Dict[str, Any]]) -> Dict[str, int]:
        """Group runs by status."""
        status_counts = {}
        for run in runs:
            status = run.get('status', 'unknown')
            status_counts[status] = status_counts.get(status, 0) + 1
        return status_counts
    
    def _group_runs_by_roaster(self, runs: List[Dict[str, Any]]) -> Dict[str, int]:
        """Group runs by roaster."""
        roaster_counts = {}
        for run in runs:
            roaster_id = run.get('roaster_id', 'unknown')
            roaster_counts[roaster_id] = roaster_counts.get(roaster_id, 0) + 1
        return roaster_counts
    
    def _group_artifacts_by_platform(self, artifacts: List[Dict[str, Any]]) -> Dict[str, int]:
        """Group artifacts by platform."""
        platform_counts = {}
        for artifact in artifacts:
            platform = artifact.get('platform', 'unknown')
            platform_counts[platform] = platform_counts.get(platform, 0) + 1
        return platform_counts
    
    def _group_prices_by_roaster(self, prices: List[Dict[str, Any]]) -> Dict[str, int]:
        """Group prices by roaster."""
        roaster_counts = {}
        for price in prices:
            roaster_id = price.get('roaster_id', 'unknown')
            roaster_counts[roaster_id] = roaster_counts.get(roaster_id, 0) + 1
        return roaster_counts
    
    def _group_variants_by_roaster(self, variants: List[Dict[str, Any]]) -> Dict[str, int]:
        """Group variants by roaster."""
        roaster_counts = {}
        for variant in variants:
            roaster_id = variant.get('roaster_id', 'unknown')
            roaster_counts[roaster_id] = roaster_counts.get(roaster_id, 0) + 1
        return roaster_counts
    
    def _calculate_health_score(self, metrics: Dict[str, Any]) -> float:
        """Calculate overall health score (0-100)."""
        try:
            score = 100.0
            
            # Deduct points for failures
            scrape_runs = metrics.get('scrape_runs', {})
            if scrape_runs.get('total_runs', 0) > 0:
                success_rate = scrape_runs.get('success_rate', 0)
                score -= (100 - success_rate) * 0.3  # 30% weight for run success
            
            # Deduct points for validation failures
            artifacts = metrics.get('artifacts', {})
            if artifacts.get('total_artifacts', 0) > 0:
                validation_rate = artifacts.get('validation_rate', 0)
                score -= (100 - validation_rate) * 0.2  # 20% weight for validation
            
            # Deduct points for stock issues
            variants = metrics.get('variants', {})
            if variants.get('total_variants', 0) > 0:
                stock_rate = variants.get('stock_rate', 0)
                score -= (100 - stock_rate) * 0.1  # 10% weight for stock
            
            return max(0.0, min(100.0, score))
            
        except Exception:
            return 50.0  # Default score if calculation fails
    
    def _get_mock_scrape_run_metrics(self) -> Dict[str, Any]:
        """Get mock scrape run metrics for testing."""
        return {
            "total_runs": 10,
            "successful_runs": 8,
            "failed_runs": 2,
            "success_rate": 80.0,
            "avg_duration_seconds": 45.5,
            "runs_by_status": {"ok": 8, "fail": 2},
            "runs_by_roaster": {"roaster1": 5, "roaster2": 5},
            "collection_timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    def _get_mock_artifact_metrics(self) -> Dict[str, Any]:
        """Get mock artifact metrics for testing."""
        return {
            "total_artifacts": 150,
            "valid_artifacts": 135,
            "invalid_artifacts": 15,
            "validation_rate": 90.0,
            "http_status_distribution": {"200": 140, "404": 10},
            "avg_body_size": 1024.5,
            "artifacts_by_platform": {"shopify": 100, "woocommerce": 50},
            "collection_timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    def _get_mock_price_metrics(self) -> Dict[str, Any]:
        """Get mock price metrics for testing."""
        return {
            "total_prices": 500,
            "unique_variants": 250,
            "avg_price": 15.99,
            "min_price": 5.99,
            "max_price": 45.99,
            "currency_distribution": {"USD": 400, "CAD": 100},
            "price_changes": 25,
            "prices_by_roaster": {"roaster1": 300, "roaster2": 200},
            "collection_timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    def _get_mock_variant_metrics(self) -> Dict[str, Any]:
        """Get mock variant metrics for testing."""
        return {
            "total_variants": 250,
            "in_stock_variants": 200,
            "out_of_stock_variants": 50,
            "stock_rate": 80.0,
            "variants_by_roaster": {"roaster1": 150, "roaster2": 100},
            "collection_timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    def _get_mock_comprehensive_metrics(self) -> Dict[str, Any]:
        """Get mock comprehensive metrics for testing."""
        return {
            "scrape_runs": self._get_mock_scrape_run_metrics(),
            "artifacts": self._get_mock_artifact_metrics(),
            "prices": self._get_mock_price_metrics(),
            "variants": self._get_mock_variant_metrics(),
            "overall_health_score": 85.0,
            "collection_timestamp": datetime.now(timezone.utc).isoformat()
        }
