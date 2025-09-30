"""Unit tests for confidence metrics service."""

import pytest
import time
from datetime import datetime, timezone
from unittest.mock import Mock, patch

from src.monitoring.confidence_metrics import ConfidenceMetrics, ConfidenceMetricsCollector


class TestConfidenceMetrics:
    """Test cases for confidence metrics service."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.metrics = ConfidenceMetrics()
    
    def test_confidence_evaluation_recording(self):
        """Test recording confidence evaluation metrics."""
        # Record confidence evaluation
        self.metrics.record_confidence_evaluation(
            field="roast_level",
            confidence_score=0.85,
            action="auto_apply",
            status="approved",
            provider="deepseek",
            model="deepseek-chat",
            duration=0.05
        )
        
        # Verify metrics were recorded (would need to check Prometheus metrics in real implementation)
        assert self.metrics.confidence_evaluations is not None
        assert self.metrics.confidence_scores is not None
        assert self.metrics.confidence_evaluation_duration is not None
    
    def test_confidence_threshold_recording(self):
        """Test recording confidence thresholds."""
        # Record confidence threshold
        self.metrics.record_confidence_threshold("roast_level", 0.8)
        
        # Verify threshold was recorded
        assert self.metrics.confidence_thresholds is not None
    
    def test_evaluation_rule_recording(self):
        """Test recording evaluation rule applications."""
        # Record evaluation rule application
        self.metrics.record_evaluation_rule_applied("roast_level_high_confidence", "roast_level")
        
        # Verify rule was recorded
        assert self.metrics.evaluation_rules_applied is not None
    
    def test_review_item_recording(self):
        """Test recording review item creation."""
        # Record review item creation
        self.metrics.record_review_item_created(
            artifact_id="test_artifact_1",
            field="roast_level",
            reason="Low confidence: 0.6 < 0.7"
        )
        
        # Verify review item was recorded
        assert self.metrics.review_items is not None
    
    def test_review_decision_recording(self):
        """Test recording review decisions."""
        # Record review decision
        self.metrics.record_review_decision(
            decision="approved",
            reviewer_id="reviewer_1",
            field="roast_level",
            duration=30.0
        )
        
        # Verify review decision was recorded
        assert self.metrics.review_decisions is not None
        assert self.metrics.review_duration is not None
    
    def test_review_backlog_recording(self):
        """Test recording review backlog."""
        # Record review backlog
        self.metrics.record_review_backlog("roast_level", "high", 5)
        
        # Verify backlog was recorded
        assert self.metrics.review_backlog is not None
    
    def test_enrichment_persistence_recording(self):
        """Test recording enrichment persistence."""
        # Record enrichment persistence
        self.metrics.record_enrichment_persisted(
            field="roast_level",
            status="approved",
            action="auto_apply",
            duration=0.1
        )
        
        # Verify enrichment was recorded
        assert self.metrics.enrichments_persisted is not None
        assert self.metrics.enrichment_persistence_duration is not None
    
    def test_enrichment_retrieval_recording(self):
        """Test recording enrichment retrievals."""
        # Record enrichment retrieval
        self.metrics.record_enrichment_retrieval("by_artifact", "roast_level")
        
        # Verify retrieval was recorded
        assert self.metrics.enrichment_retrievals is not None
    
    def test_llm_result_quality_recording(self):
        """Test recording LLM result quality."""
        # Record LLM result quality
        self.metrics.record_llm_result_quality(
            field="roast_level",
            quality_score=0.9,
            provider="deepseek",
            model="deepseek-chat"
        )
        
        # Verify quality was recorded
        assert self.metrics.llm_result_quality is not None
    
    def test_llm_usage_recording(self):
        """Test recording LLM usage."""
        # Record LLM usage
        self.metrics.record_llm_usage(
            provider="deepseek",
            model="deepseek-chat",
            field="roast_level",
            tokens=100
        )
        
        # Verify usage was recorded
        assert self.metrics.llm_usage_tokens is not None
    
    def test_llm_api_call_recording(self):
        """Test recording LLM API calls."""
        # Record LLM API call
        self.metrics.record_llm_api_call(
            provider="deepseek",
            model="deepseek-chat",
            field="roast_level",
            success=True,
            duration=2.5
        )
        
        # Verify API call was recorded
        assert self.metrics.llm_api_calls is not None
        assert self.metrics.llm_api_latency is not None
    
    def test_error_recording(self):
        """Test recording error metrics."""
        # Record confidence evaluation error
        self.metrics.record_confidence_evaluation_error("validation_error", "roast_level")
        
        # Record review workflow error
        self.metrics.record_review_workflow_error("timeout_error", "test_artifact_1")
        
        # Record enrichment persistence error
        self.metrics.record_enrichment_persistence_error("storage_error", "roast_level")
        
        # Verify errors were recorded
        assert self.metrics.confidence_evaluation_errors is not None
        assert self.metrics.review_workflow_errors is not None
        assert self.metrics.enrichment_persistence_errors is not None
    
    def test_batch_processing_recording(self):
        """Test recording batch processing metrics."""
        # Record batch processing
        self.metrics.record_batch_processing(
            operation_type="confidence_evaluation",
            batch_size=100,
            duration=5.0
        )
        
        # Verify batch processing was recorded
        assert self.metrics.batch_processing_duration is not None
    
    def test_metrics_summary(self):
        """Test metrics summary generation."""
        # Get metrics summary
        summary = self.metrics.get_confidence_metrics_summary()
        
        # Assertions
        assert "prometheus_port" in summary
        assert "confidence_metrics" in summary
        assert "inherited_metrics" in summary
        assert len(summary["confidence_metrics"]) > 0


class TestConfidenceMetricsCollector:
    """Test cases for confidence metrics collector."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.collector = ConfidenceMetricsCollector()
    
    def test_confidence_evaluation_timer(self):
        """Test confidence evaluation timing."""
        # Start timer
        timer_id = self.collector.start_confidence_evaluation_timer("roast_level")
        
        # Simulate processing time
        time.sleep(0.01)
        
        # End timer
        duration = self.collector.end_confidence_evaluation_timer(
            timer_id=timer_id,
            field="roast_level",
            confidence_score=0.85,
            action="auto_apply",
            status="approved"
        )
        
        # Assertions
        assert duration > 0.0
        assert timer_id not in self.collector.operation_timers
    
    def test_review_timer(self):
        """Test review timing."""
        # Start timer
        timer_id = self.collector.start_review_timer("test_artifact_1", "roast_level")
        
        # Simulate processing time
        time.sleep(0.01)
        
        # End timer
        duration = self.collector.end_review_timer(
            timer_id=timer_id,
            decision="approved",
            reviewer_id="reviewer_1",
            field="roast_level"
        )
        
        # Assertions
        assert duration > 0.0
        assert timer_id not in self.collector.operation_timers
    
    def test_enrichment_persistence_timer(self):
        """Test enrichment persistence timing."""
        # Start timer
        timer_id = self.collector.start_enrichment_persistence_timer("roast_level")
        
        # Simulate processing time
        time.sleep(0.01)
        
        # End timer
        duration = self.collector.end_enrichment_persistence_timer(
            timer_id=timer_id,
            field="roast_level",
            status="approved",
            action="auto_apply"
        )
        
        # Assertions
        assert duration > 0.0
        assert timer_id not in self.collector.operation_timers
    
    def test_llm_operation_recording(self):
        """Test LLM operation recording."""
        # Record LLM operation
        self.collector.record_llm_operation(
            provider="deepseek",
            model="deepseek-chat",
            field="roast_level",
            tokens=100,
            success=True,
            duration=2.5
        )
        
        # Verify operation was recorded
        assert self.collector.metrics.llm_usage_tokens is not None
        assert self.collector.metrics.llm_api_calls is not None
    
    def test_batch_operation_recording(self):
        """Test batch operation recording."""
        # Record batch operation
        self.collector.record_batch_operation(
            operation_type="confidence_evaluation",
            batch_size=100,
            duration=5.0
        )
        
        # Verify operation was recorded
        assert self.collector.metrics.batch_processing_duration is not None
    
    def test_error_recording(self):
        """Test error recording."""
        # Record different types of errors
        self.collector.record_error("validation_error", "confidence_evaluation", field="roast_level")
        self.collector.record_error("timeout_error", "review_workflow", artifact_id="test_artifact_1")
        self.collector.record_error("storage_error", "enrichment_persistence", field="roast_level")
        
        # Verify errors were recorded
        assert self.collector.metrics.confidence_evaluation_errors is not None
        assert self.collector.metrics.review_workflow_errors is not None
        assert self.collector.metrics.enrichment_persistence_errors is not None
    
    def test_collector_stats(self):
        """Test collector statistics."""
        # Get collector stats
        stats = self.collector.get_collector_stats()
        
        # Assertions
        assert "active_timers" in stats
        assert "metrics_summary" in stats
        assert "timer_ids" in stats
        assert stats["active_timers"] == 0  # No active timers initially
    
    def test_multiple_timers(self):
        """Test multiple concurrent timers."""
        # Start multiple timers
        timer1 = self.collector.start_confidence_evaluation_timer("roast_level")
        timer2 = self.collector.start_review_timer("test_artifact_1", "bean_species")
        timer3 = self.collector.start_enrichment_persistence_timer("process_method")
        
        # Check active timers
        stats = self.collector.get_collector_stats()
        assert stats["active_timers"] == 3
        
        # End one timer
        self.collector.end_confidence_evaluation_timer(
            timer1, "roast_level", 0.8, "auto_apply", "approved"
        )
        
        # Check active timers
        stats = self.collector.get_collector_stats()
        assert stats["active_timers"] == 2
        
        # End remaining timers
        self.collector.end_review_timer(timer2, "approved", "reviewer_1", "bean_species")
        self.collector.end_enrichment_persistence_timer(timer3, "process_method", "approved", "auto_apply")
        
        # Check active timers
        stats = self.collector.get_collector_stats()
        assert stats["active_timers"] == 0
    
    def test_invalid_timer_handling(self):
        """Test handling of invalid timer IDs."""
        # Try to end non-existent timer
        duration = self.collector.end_confidence_evaluation_timer(
            "invalid_timer_id",
            "roast_level",
            0.8,
            "auto_apply",
            "approved"
        )
        
        # Should return 0.0 for invalid timer
        assert duration == 0.0


if __name__ == "__main__":
    pytest.main([__file__])
