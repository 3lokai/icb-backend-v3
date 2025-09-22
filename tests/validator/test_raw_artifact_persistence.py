"""
Tests for raw artifact persistence service.
"""

import pytest
import json
from datetime import datetime, timezone
from unittest.mock import Mock, patch

from src.validator.raw_artifact_persistence import RawArtifactPersistence, RawArtifactData
from src.validator.models import ArtifactModel, AuditModel, NormalizationModel, CollectorSignalsModel, ProductModel, VariantModel


class TestRawArtifactPersistence:
    """Test cases for raw artifact persistence service."""
    
    @pytest.fixture
    def mock_db_integration(self):
        """Mock database integration."""
        return Mock()
    
    @pytest.fixture
    def mock_rpc_client(self):
        """Mock RPC client."""
        return Mock()
    
    @pytest.fixture
    def persistence_service(self, mock_db_integration, mock_rpc_client):
        """Create persistence service with mocked dependencies."""
        return RawArtifactPersistence(
            db_integration=mock_db_integration,
            rpc_client=mock_rpc_client
        )
    
    @pytest.fixture
    def sample_artifact(self):
        """Create a sample canonical artifact for testing."""
        return ArtifactModel(
            source="shopify",
            roaster_domain="example.com",
            scraped_at="2025-01-12T10:00:00Z",
            collector_meta={"collector": "test", "job_id": "test-job"},
            product=ProductModel(
                platform_product_id="123",
                title="Test Coffee",
                source_url="https://example.com/coffee",
                variants=[
                    VariantModel(
                        platform_variant_id="var-123",
                        price="15.99"
                    )
                ]
            ),
            normalization=NormalizationModel(
                content_hash="content-hash-123",
                raw_payload_hash="raw-hash-456"
            ),
            collector_signals=CollectorSignalsModel(
                response_status=200,
                download_time_ms=100
            ),
            audit=AuditModel(
                artifact_id="artifact-123",
                created_at="2025-01-12T10:00:00Z",
                collected_by="test-collector"
            )
        )
    
    def test_extract_raw_artifact_data_success(self, persistence_service, sample_artifact):
        """Test successful extraction of raw artifact data."""
        raw_data = persistence_service.extract_raw_artifact_data(sample_artifact)
        
        assert isinstance(raw_data, RawArtifactData)
        assert raw_data.content_hash == "content-hash-123"
        assert raw_data.raw_payload_hash == "raw-hash-456"
        assert raw_data.artifact_id == "artifact-123"
        assert raw_data.created_at.isoformat() == "2025-01-12T10:00:00+00:00"
        assert raw_data.collected_by == "test-collector"
        assert raw_data.first_seen_at.isoformat() == "2025-01-12T10:00:00+00:00"
        assert "source" in raw_data.complete_artifact_json
        assert "product" in raw_data.complete_artifact_json
    
    def test_extract_raw_artifact_data_missing_fields(self, persistence_service):
        """Test extraction with missing required fields."""
        # Create artifact with missing normalization
        incomplete_artifact = ArtifactModel(
            source="shopify",
            roaster_domain="example.com",
            scraped_at="2025-01-12T10:00:00Z",
            collector_meta={"collector": "test"},
            product=ProductModel(
                platform_product_id="123",
                title="Test Coffee",
                source_url="https://example.com/coffee",
                variants=[
                    VariantModel(
                        platform_variant_id="var-123",
                        price="15.99"
                    )
                ]
            ),
            normalization=None,  # Missing normalization
            collector_signals=None,
            audit=AuditModel(
                artifact_id="artifact-123",
                created_at="2025-01-12T10:00:00Z",
                collected_by="test-collector"
            )
        )
        
        with pytest.raises(ValueError, match="Missing required field"):
            persistence_service.extract_raw_artifact_data(incomplete_artifact)
    
    def test_prepare_source_raw_json(self, persistence_service, sample_artifact):
        """Test preparation of source_raw JSON structure."""
        raw_data = persistence_service.extract_raw_artifact_data(sample_artifact)
        source_raw_json = persistence_service.prepare_source_raw_json(raw_data)
        
        assert "complete_artifact" in source_raw_json
        assert "content_hash" in source_raw_json
        assert "raw_payload_hash" in source_raw_json
        assert "artifact_id" in source_raw_json
        assert "created_at" in source_raw_json
        assert "collected_by" in source_raw_json
        assert "collector_signals" in source_raw_json
        assert "persisted_at" in source_raw_json
        assert "persistence_version" in source_raw_json
        
        assert source_raw_json["content_hash"] == "content-hash-123"
        assert source_raw_json["raw_payload_hash"] == "raw-hash-456"
        assert source_raw_json["artifact_id"] == "artifact-123"
    
    def test_persist_raw_artifact_success(self, persistence_service, sample_artifact):
        """Test successful raw artifact persistence."""
        persistence_service.rpc_client.upsert_coffee_with_raw_data.return_value = True
        
        success, error_msg = persistence_service.persist_raw_artifact(sample_artifact)
        
        assert success is True
        assert error_msg is None
        persistence_service.rpc_client.upsert_coffee_with_raw_data.assert_called_once()
    
    def test_persist_raw_artifact_failure(self, persistence_service, sample_artifact):
        """Test raw artifact persistence failure."""
        persistence_service.rpc_client.upsert_coffee_with_raw_data.return_value = False
        
        success, error_msg = persistence_service.persist_raw_artifact(sample_artifact)
        
        assert success is False
        assert "Failed to persist raw artifact" in error_msg
    
    def test_persist_raw_artifact_exception(self, persistence_service, sample_artifact):
        """Test raw artifact persistence with exception."""
        persistence_service.rpc_client.upsert_coffee_with_raw_data.side_effect = Exception("RPC Error")
        
        success, error_msg = persistence_service.persist_raw_artifact(sample_artifact)
        
        assert success is False
        assert "Unexpected error persisting raw artifact" in error_msg
    
    def test_verify_hash_integrity_valid(self, persistence_service, sample_artifact):
        """Test hash integrity verification with valid hashes."""
        result = persistence_service.verify_hash_integrity(sample_artifact)
        assert result is True
    
    def test_verify_hash_integrity_missing_hashes(self, persistence_service):
        """Test hash integrity verification with missing hashes."""
        artifact_without_hashes = ArtifactModel(
            source="shopify",
            roaster_domain="example.com",
            scraped_at="2025-01-12T10:00:00Z",
            collector_meta={"collector": "test"},
            product=ProductModel(
                platform_product_id="123",
                title="Test Coffee",
                source_url="https://example.com/coffee",
                variants=[
                    VariantModel(
                        platform_variant_id="var-123",
                        price="15.99"
                    )
                ]
            ),
            normalization=NormalizationModel(
                content_hash="",  # Empty hash
                raw_payload_hash="raw-hash-456"
            ),
            collector_signals=None,
            audit=AuditModel(
                artifact_id="artifact-123",
                created_at="2025-01-12T10:00:00Z",
                collected_by="test-collector"
            )
        )
        
        result = persistence_service.verify_hash_integrity(artifact_without_hashes)
        assert result is False
    
    def test_verify_hash_integrity_invalid_types(self, persistence_service):
        """Test hash integrity verification with invalid hash types."""
        # Create a valid artifact first
        artifact = ArtifactModel(
            source="shopify",
            roaster_domain="example.com",
            scraped_at="2025-01-12T10:00:00Z",
            collector_meta={"collector": "test"},
            product=ProductModel(
                platform_product_id="123",
                title="Test Coffee",
                source_url="https://example.com/coffee",
                variants=[
                    VariantModel(
                        platform_variant_id="var-123",
                        price="15.99"
                    )
                ]
            ),
            normalization=NormalizationModel(
                content_hash="content-hash-123",
                raw_payload_hash="raw-hash-456"
            ),
            collector_signals=None,
            audit=AuditModel(
                artifact_id="artifact-123",
                created_at="2025-01-12T10:00:00Z",
                collected_by="test-collector"
            )
        )
        
        # Manually modify the hash to an invalid type after creation
        artifact.normalization.content_hash = 123  # Invalid type
        
        result = persistence_service.verify_hash_integrity(artifact)
        assert result is False
    
    def test_get_audit_trail_success(self, persistence_service):
        """Test audit trail retrieval with mock database response."""
        # Mock database response
        mock_response = type('MockResponse', (), {
            'data': [{
                'id': 'coffee-123',
                'source_raw': {
                    'audit': {
                        'artifact_id': 'artifact-123',
                        'created_at': '2025-01-12T10:00:00Z',
                        'collected_by': 'test-collector'
                    },
                    'collector_signals': {
                        'response_status': 200,
                        'download_time_ms': 150
                    },
                    'normalization': {
                        'content_hash': 'content-hash-123',
                        'raw_payload_hash': 'raw-hash-456'
                    },
                    'source': 'shopify',
                    'roaster_domain': 'example.com',
                    'scraped_at': '2025-01-12T10:00:00Z'
                },
                'first_seen_at': '2025-01-12T10:00:00Z',
                'created_at': '2025-01-12T10:00:00Z',
                'updated_at': '2025-01-12T10:00:00Z'
            }]
        })()
        
        # Mock the database client
        persistence_service.db_integration.supabase_client.table.return_value.select.return_value.contains.return_value.execute.return_value = mock_response
        
        result = persistence_service.get_audit_trail("artifact-123")
        
        assert result is not None
        assert result['artifact_id'] == 'artifact-123'
        assert result['coffee_id'] == 'coffee-123'
        assert result['audit_data']['artifact_id'] == 'artifact-123'
        assert result['collector_signals']['response_status'] == 200
        assert result['source'] == 'shopify'
    
    def test_get_audit_trail_not_found(self, persistence_service):
        """Test audit trail retrieval when artifact not found."""
        # Mock empty database response
        mock_response = type('MockResponse', (), {'data': []})()
        persistence_service.db_integration.supabase_client.table.return_value.select.return_value.contains.return_value.execute.return_value = mock_response
        
        result = persistence_service.get_audit_trail("nonexistent-artifact")
        assert result is None
    
    def test_get_audit_trail_database_error(self, persistence_service):
        """Test audit trail retrieval with database error."""
        # Mock database error
        persistence_service.db_integration.supabase_client.table.side_effect = Exception("Database error")
        
        result = persistence_service.get_audit_trail("artifact-123")
        assert result is None
    
    def test_persist_raw_artifact_with_collector_signals(self, persistence_service):
        """Test persistence with collector signals data."""
        artifact_with_signals = ArtifactModel(
            source="shopify",
            roaster_domain="example.com",
            scraped_at="2025-01-12T10:00:00Z",
            collector_meta={"collector": "test"},
            product=ProductModel(
                platform_product_id="123",
                title="Test Coffee",
                source_url="https://example.com/coffee",
                variants=[
                    VariantModel(
                        platform_variant_id="var-123",
                        price="15.99"
                    )
                ]
            ),
            normalization=NormalizationModel(
                content_hash="content-hash-123",
                raw_payload_hash="raw-hash-456"
            ),
            collector_signals=CollectorSignalsModel(
                response_status=200,
                download_time_ms=150,
                cache_hit=False
            ),
            audit=AuditModel(
                artifact_id="artifact-123",
                created_at="2025-01-12T10:00:00Z",
                collected_by="test-collector"
            )
        )
        
        persistence_service.rpc_client.upsert_coffee_with_raw_data.return_value = True
        
        success, error_msg = persistence_service.persist_raw_artifact(artifact_with_signals)
        
        assert success is True
        assert error_msg is None
        
        # Verify the call was made with collector signals
        call_args = persistence_service.rpc_client.upsert_coffee_with_raw_data.call_args
        assert call_args is not None
        
        # The method is called with keyword arguments
        coffee_data = call_args.kwargs['coffee_data']
        assert "source_raw" in coffee_data
        assert "collector_signals" in coffee_data["source_raw"]
        assert coffee_data["source_raw"]["collector_signals"]["response_status"] == 200
        assert coffee_data["source_raw"]["collector_signals"]["download_time_ms"] == 150

