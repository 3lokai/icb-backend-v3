"""Integration tests for enrichment persistence service."""

import pytest
import time
from datetime import datetime, timezone
from unittest.mock import Mock, patch

from src.llm.enrichment_persistence import EnrichmentPersistence, EnrichmentData
from src.llm.llm_interface import LLMResult
from src.llm.confidence_evaluator import ConfidenceEvaluation


class TestEnrichmentPersistenceIntegration:
    """Integration tests for enrichment persistence service."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.persistence = EnrichmentPersistence()
    
    def test_complete_enrichment_persistence_workflow(self):
        """Test complete enrichment persistence workflow."""
        # Create test data
        artifact = {
            'id': 'test_artifact_1',
            'roaster_id': 'test_roaster',
            'name': 'Test Coffee'
        }
        
        llm_result = LLMResult(
            field="roast_level",
            value="medium",
            confidence=0.85,
            provider="deepseek",
            model="deepseek-chat",
            usage={"tokens": 100},
            created_at=datetime.now(timezone.utc)
        )
        
        evaluation = ConfidenceEvaluation(
            confidence_score=0.85,
            original_confidence=0.85,
            final_confidence=0.85,
            threshold=0.7,
            action='auto_apply',
            status='approved',
            evaluation_rules_applied=[],
            evaluation_time=0.01
        )
        
        # Persist enrichment
        enrichment_id = self.persistence.persist_enrichment(artifact, llm_result, evaluation)
        
        # Assertions
        assert enrichment_id is not None
        assert enrichment_id.startswith('enrich_test_artifact_1_roast_level_')
        assert artifact['processing_status'] == 'enriched'
        assert artifact['enrichment_applied'] == True
        
        # Retrieve enrichment
        enrichment = self.persistence.get_enrichment(enrichment_id)
        assert enrichment is not None
        assert enrichment.artifact_id == 'test_artifact_1'
        assert enrichment.field == 'roast_level'
        assert enrichment.processing_status == 'approved'
    
    def test_batch_enrichment_persistence(self):
        """Test batch enrichment persistence."""
        # Create multiple enrichments
        enrichments = []
        
        for i in range(5):
            artifact = {
                'id': f'test_artifact_{i}',
                'roaster_id': f'test_roaster_{i}',
                'name': f'Test Coffee {i}'
            }
            
            llm_result = LLMResult(
                field="roast_level",
                value="medium",
                confidence=0.8,
                provider="deepseek",
                model="deepseek-chat",
                usage={"tokens": 100},
                created_at=datetime.now(timezone.utc)
            )
            
            evaluation = ConfidenceEvaluation(
                confidence_score=0.8,
                original_confidence=0.8,
                final_confidence=0.8,
                threshold=0.7,
                action='auto_apply',
                status='approved',
                evaluation_rules_applied=[],
                evaluation_time=0.01
            )
            
            enrichments.append({
                'artifact': artifact,
                'llm_result': llm_result,
                'evaluation': evaluation
            })
        
        # Batch persist
        enrichment_ids = self.persistence.batch_persist_enrichments(enrichments)
        
        # Assertions
        assert len(enrichment_ids) == 5
        assert all(id.startswith('enrich_') for id in enrichment_ids)
        
        # Verify all enrichments were stored
        for enrichment_id in enrichment_ids:
            enrichment = self.persistence.get_enrichment(enrichment_id)
            assert enrichment is not None
            assert enrichment.processing_status == 'approved'
    
    def test_enrichment_retrieval_by_artifact(self):
        """Test retrieving enrichments by artifact ID."""
        # Create multiple enrichments for same artifact
        artifact = {'id': 'test_artifact'}
        
        for field in ['roast_level', 'bean_species', 'process_method']:
            llm_result = LLMResult(
                field=field,
                value="test_value",
                confidence=0.8,
                provider="deepseek",
                model="deepseek-chat",
                usage={"tokens": 100},
                created_at=datetime.now(timezone.utc)
            )
            
            evaluation = ConfidenceEvaluation(
                confidence_score=0.8,
                original_confidence=0.8,
                final_confidence=0.8,
                threshold=0.7,
                action='auto_apply',
                status='approved',
                evaluation_rules_applied=[],
                evaluation_time=0.01
            )
            
            self.persistence.persist_enrichment(artifact, llm_result, evaluation)
        
        # Retrieve enrichments
        enrichments = self.persistence.get_enrichments_by_artifact('test_artifact')
        
        # Assertions
        assert len(enrichments) == 3
        assert all(e.artifact_id == 'test_artifact' for e in enrichments)
        fields = [e.field for e in enrichments]
        assert 'roast_level' in fields
        assert 'bean_species' in fields
        assert 'process_method' in fields
    
    def test_enrichment_retrieval_by_status(self):
        """Test retrieving enrichments by status."""
        # Create enrichments with different statuses
        for i, status in enumerate(['approved', 'review', 'approved']):
            artifact = {'id': f'test_artifact_{i}_{status}'}
            llm_result = LLMResult(
                field="roast_level",
                value="medium",
                confidence=0.8,
                provider="deepseek",
                model="deepseek-chat",
                usage={"tokens": 100},
                created_at=datetime.now(timezone.utc)
            )
            
            evaluation = ConfidenceEvaluation(
                confidence_score=0.8,
                original_confidence=0.8,
                final_confidence=0.8,
                threshold=0.7,
                action='auto_apply' if status == 'approved' else 'manual_review',
                status=status,
                evaluation_rules_applied=[],
                evaluation_time=0.01
            )
            
            self.persistence.persist_enrichment(artifact, llm_result, evaluation)
        
        # Retrieve by status
        approved_enrichments = self.persistence.get_enrichments_by_status('approved')
        review_enrichments = self.persistence.get_enrichments_by_status('review')
        
        # Assertions
        assert len(approved_enrichments) == 2
        assert len(review_enrichments) == 1
        assert all(e.processing_status == 'approved' for e in approved_enrichments)
        assert all(e.processing_status == 'review' for e in review_enrichments)
    
    def test_enrichment_status_update(self):
        """Test updating enrichment status."""
        # Create and persist enrichment
        artifact = {'id': 'test_artifact'}
        llm_result = LLMResult(
            field="roast_level",
            value="medium",
            confidence=0.6,
            provider="deepseek",
            model="deepseek-chat",
            usage={"tokens": 100},
            created_at=datetime.now(timezone.utc)
        )
        
        evaluation = ConfidenceEvaluation(
            confidence_score=0.6,
            original_confidence=0.6,
            final_confidence=0.6,
            threshold=0.7,
            action='manual_review',
            status='review',
            evaluation_rules_applied=[],
            evaluation_time=0.01
        )
        
        enrichment_id = self.persistence.persist_enrichment(artifact, llm_result, evaluation)
        
        # Update status
        success = self.persistence.update_enrichment_status(enrichment_id, 'approved', 'reviewer_1')
        
        # Assertions
        assert success == True
        enrichment = self.persistence.get_enrichment(enrichment_id)
        assert enrichment.processing_status == 'approved'
    
    def test_enrichment_statistics(self):
        """Test enrichment statistics calculation."""
        # Create test enrichments
        enrichments = []
        for i, (field, confidence, status) in enumerate([
            ('roast_level', 0.8, 'approved'),
            ('bean_species', 0.7, 'approved'),
            ('process_method', 0.6, 'review')
        ]):
            enrichment = EnrichmentData(
                artifact_id=f'test_artifact_{i}',
                roaster_id=f'roaster_{i}',
                field=field,
                llm_result=Mock(),
                confidence_evaluation=Mock(),
                processing_status=status,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            enrichment.confidence_evaluation.final_confidence = confidence
            enrichments.append(enrichment)
        
        # Get stats
        stats = self.persistence.get_enrichment_stats(enrichments)
        
        # Assertions
        assert stats['total_enrichments'] == 3
        assert stats['status_distribution']['approved'] == 2
        assert stats['status_distribution']['review'] == 1
        assert stats['field_distribution']['roast_level'] == 1
        assert stats['field_distribution']['bean_species'] == 1
        assert stats['field_distribution']['process_method'] == 1
        assert abs(stats['average_confidence'] - 0.7) < 0.01
        assert stats['min_confidence'] == 0.6
        assert stats['max_confidence'] == 0.8
    
    def test_enrichment_persistence_performance(self):
        """Test enrichment persistence performance requirements."""
        # Create test data
        artifact = {'id': 'test_artifact'}
        llm_result = LLMResult(
            field="roast_level",
            value="medium",
            confidence=0.8,
            provider="deepseek",
            model="deepseek-chat",
            usage={"tokens": 100},
            created_at=datetime.now(timezone.utc)
        )
        
        evaluation = ConfidenceEvaluation(
            confidence_score=0.8,
            original_confidence=0.8,
            final_confidence=0.8,
            threshold=0.7,
            action='auto_apply',
            status='approved',
            evaluation_rules_applied=[],
            evaluation_time=0.01
        )
        
        # Measure persistence time
        start_time = time.time()
        enrichment_id = self.persistence.persist_enrichment(artifact, llm_result, evaluation)
        end_time = time.time()
        
        # Assertions
        assert enrichment_id is not None
        assert (end_time - start_time) < 0.5  # < 500ms requirement
    
    def test_enrichment_persistence_error_handling(self):
        """Test enrichment persistence error handling."""
        # Create invalid data
        artifact = None
        llm_result = Mock()
        evaluation = Mock()
        
        # Should handle error gracefully
        with pytest.raises(Exception):  # EnrichmentPersistenceError
            self.persistence.persist_enrichment(artifact, llm_result, evaluation)
    
    def test_enrichment_data_serialization(self):
        """Test enrichment data serialization."""
        # Create enrichment data
        llm_result = LLMResult(
            field="roast_level",
            value="medium",
            confidence=0.8,
            provider="deepseek",
            model="deepseek-chat",
            usage={"tokens": 100},
            created_at=datetime.now(timezone.utc)
        )
        
        evaluation = ConfidenceEvaluation(
            confidence_score=0.8,
            original_confidence=0.8,
            final_confidence=0.8,
            threshold=0.7,
            action='auto_apply',
            status='approved',
            evaluation_rules_applied=[],
            evaluation_time=0.01
        )
        
        enrichment_data = EnrichmentData(
            artifact_id='test_artifact',
            roaster_id='test_roaster',
            field='roast_level',
            llm_result=llm_result,
            confidence_evaluation=evaluation,
            processing_status='approved',
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            enrichment_id='test_enrichment_id'
        )
        
        # Convert to dict
        data_dict = enrichment_data.to_dict()
        
        # Assertions
        assert data_dict['enrichment_id'] == 'test_enrichment_id'
        assert data_dict['artifact_id'] == 'test_artifact'
        assert data_dict['field'] == 'roast_level'
        assert data_dict['processing_status'] == 'approved'
        assert 'llm_result' in data_dict
        assert 'confidence_evaluation' in data_dict


if __name__ == "__main__":
    pytest.main([__file__])
