import pytest
from unittest.mock import Mock, patch
from src.validator.database_integration import DatabaseIntegration
from src.validator.artifact_validator import ValidationResult
from datetime import datetime, timezone

class TestDatabaseIntegrationSimple:
    """Simple tests for DatabaseIntegration functionality"""

    def setup_method(self):
        """Set up test fixtures."""
        self.db_integration = DatabaseIntegration()

    def test_initialization(self):
        """Test that DatabaseIntegration initializes correctly."""
        assert self.db_integration.supabase_client is None
        assert self.db_integration.rpc_client is not None
        assert self.db_integration.artifact_mapper is not None
        assert self.db_integration.validation_stats['total_stored'] == 0
        assert self.db_integration.validation_stats['valid_stored'] == 0
        assert self.db_integration.validation_stats['invalid_stored'] == 0
        assert self.db_integration.validation_stats['error_count'] == 0

    def test_get_validation_stats(self):
        """Test getting validation statistics."""
        stats = self.db_integration.get_validation_stats()
        assert 'total_stored' in stats
        assert 'valid_stored' in stats
        assert 'invalid_stored' in stats
        assert 'error_count' in stats
        assert 'valid_rate' in stats
        assert 'invalid_rate' in stats
        assert 'error_rate' in stats

    def test_reset_stats(self):
        """Test resetting validation statistics."""
        # Set some stats
        self.db_integration.validation_stats['total_stored'] = 5
        self.db_integration.validation_stats['valid_stored'] = 3
        
        # Reset stats
        self.db_integration.reset_stats()
        
        # Verify stats are reset
        assert self.db_integration.validation_stats['total_stored'] == 0
        assert self.db_integration.validation_stats['valid_stored'] == 0
        assert self.db_integration.validation_stats['invalid_stored'] == 0
        assert self.db_integration.validation_stats['error_count'] == 0

    def test_validation_stats_calculation(self):
        """Test validation statistics calculation."""
        # Set some stats
        self.db_integration.validation_stats['total_stored'] = 10
        self.db_integration.validation_stats['valid_stored'] = 7
        self.db_integration.validation_stats['invalid_stored'] = 2
        self.db_integration.validation_stats['error_count'] = 1
        
        stats = self.db_integration.get_validation_stats()
        
        # Test rate calculations
        assert stats['valid_rate'] == 0.7  # 7/10
        assert stats['invalid_rate'] == 0.2  # 2/10
        assert stats['error_rate'] == 0.1  # 1/10
        
        # Test with no validations
        self.db_integration.validation_stats['total_stored'] = 0
        self.db_integration.validation_stats['valid_stored'] = 0
        self.db_integration.validation_stats['invalid_stored'] = 0
        self.db_integration.validation_stats['error_count'] = 0
        
        stats = self.db_integration.get_validation_stats()
        assert stats['valid_rate'] == 0.0
        assert stats['invalid_rate'] == 0.0
        assert stats['error_rate'] == 0.0

    def test_store_validation_result_mock(self):
        """Test storing validation result with mock database."""
        # Create mock validation result
        validation_result = Mock()
        validation_result.is_valid = True
        validation_result.artifact_data = {"test": "data"}
        validation_result.errors = []
        validation_result.validated_at = datetime.now(timezone.utc)
        validation_result.artifact_id = "test-artifact-123"
        
        # Test storing valid result
        artifact_id = self.db_integration.store_validation_result(
            validation_result=validation_result,
            scrape_run_id="test-run-123",
            roaster_id="test-roaster",
            platform="test-platform",
            response_filename="test-response.json"
        )
        
        # Should return mock artifact ID
        assert artifact_id == "artifact_test-run-123_test-artifact-123"
        assert self.db_integration.validation_stats['total_stored'] == 1
        assert self.db_integration.validation_stats['valid_stored'] == 1
        assert self.db_integration.validation_stats['invalid_stored'] == 0

    def test_store_validation_result_invalid(self):
        """Test storing invalid validation result."""
        # Create mock validation result
        validation_result = Mock()
        validation_result.is_valid = False
        validation_result.artifact_data = {"test": "data"}
        validation_result.errors = ["Error 1", "Error 2"]
        validation_result.validated_at = datetime.now(timezone.utc)
        validation_result.artifact_id = "test-artifact-456"
        
        # Test storing invalid result
        artifact_id = self.db_integration.store_validation_result(
            validation_result=validation_result,
            scrape_run_id="test-run-456",
            roaster_id="test-roaster",
            platform="test-platform",
            response_filename="test-response.json"
        )
        
        # Should return mock artifact ID
        assert artifact_id == "artifact_test-run-456_test-artifact-456"
        assert self.db_integration.validation_stats['total_stored'] == 1
        assert self.db_integration.validation_stats['valid_stored'] == 0
        assert self.db_integration.validation_stats['invalid_stored'] == 1

    def test_store_batch_validation_results(self):
        """Test storing batch validation results."""
        # Create mock validation results
        validation_results = []
        for i in range(3):
            result = Mock()
            result.is_valid = i % 2 == 0  # Alternate valid/invalid
            result.artifact_data = {"test": f"data-{i}"}
            result.errors = [] if result.is_valid else [f"Error {i}"]
            result.validated_at = datetime.now(timezone.utc)
            result.artifact_id = f"test-artifact-{i}"
            validation_results.append(result)
        
        # Test storing batch results
        artifact_ids = self.db_integration.store_batch_validation_results(
            validation_results=validation_results,
            scrape_run_id="test-run-batch",
            roaster_id="test-roaster",
            platform="test-platform",
            response_filenames=["file1.json", "file2.json", "file3.json"]
        )
        
        # Should return 3 artifact IDs
        assert len(artifact_ids) == 3
        assert all(aid is not None for aid in artifact_ids)
        assert self.db_integration.validation_stats['total_stored'] == 3
        assert self.db_integration.validation_stats['valid_stored'] == 2  # 0, 2 are valid
        assert self.db_integration.validation_stats['invalid_stored'] == 1  # 1 is invalid

    def test_get_validation_results_mock(self):
        """Test getting validation results with mock database."""
        # Test with no filters
        results = self.db_integration.get_validation_results()
        assert results == []
        
        # Test with filters
        results = self.db_integration.get_validation_results(
            scrape_run_id="test-run",
            validation_status="valid",
            roaster_id="test-roaster",
            limit=50
        )
        assert results == []

    def test_update_validation_status_mock(self):
        """Test updating validation status with mock database."""
        # Test successful update
        result = self.db_integration.update_validation_status(
            artifact_id="test-artifact-123",
            new_status="approved",
            manual_review_notes="Looks good"
        )
        assert result == True

    def test_check_idempotency_mock(self):
        """Test idempotency check with mock database."""
        # Test idempotency check
        result = self.db_integration.check_idempotency(
            artifact_id="test-artifact-123",
            roaster_id="test-roaster",
            platform="test-platform"
        )
        assert result == False  # Mock always returns False

    def test_get_integration_stats(self):
        """Test getting comprehensive integration statistics."""
        stats = self.db_integration.get_integration_stats()
        
        # Should contain all three stat types
        assert 'validation' in stats
        assert 'rpc' in stats
        assert 'mapping' in stats
        
        # Test validation stats structure
        validation_stats = stats['validation']
        assert 'total_stored' in validation_stats
        assert 'valid_stored' in validation_stats
        assert 'invalid_stored' in validation_stats
        assert 'error_count' in validation_stats
        assert 'valid_rate' in validation_stats
        assert 'invalid_rate' in validation_stats
        assert 'error_rate' in validation_stats

    def test_upsert_artifact_via_rpc_invalid(self):
        """Test upserting invalid artifact via RPC."""
        # Create invalid validation result
        validation_result = Mock()
        validation_result.is_valid = False
        validation_result.artifact_id = "test-artifact-invalid"
        
        # Test upserting invalid artifact
        result = self.db_integration.upsert_artifact_via_rpc(
            validation_result=validation_result,
            roaster_id="test-roaster",
            metadata_only=False
        )
        
        # Should return failure
        assert result['success'] == False
        assert 'error' in result
        assert result['artifact_id'] == "test-artifact-invalid"

    def test_upsert_artifact_via_rpc_valid(self):
        """Test upserting valid artifact via RPC."""
        # Create valid validation result
        validation_result = Mock()
        validation_result.is_valid = True
        validation_result.artifact_id = "test-artifact-valid"
        validation_result.artifact_data = Mock()
        
        # Mock the artifact mapper
        with patch.object(self.db_integration.artifact_mapper, 'map_artifact_to_rpc_payloads') as mock_map:
            mock_map.return_value = {
                'coffee': {'p_name': 'Test Coffee'},
                'variants': [{'p_platform_variant_id': 'var1'}],
                'prices': [{'p_price': 10.0}],
                'images': [{'p_url': 'test.jpg'}]
            }
            
            # Mock the RPC client
            with patch.object(self.db_integration.rpc_client, 'upsert_coffee') as mock_coffee, \
                 patch.object(self.db_integration.rpc_client, 'upsert_variant') as mock_variant, \
                 patch.object(self.db_integration.rpc_client, 'insert_price') as mock_price, \
                 patch.object(self.db_integration.rpc_client, 'upsert_coffee_image') as mock_image:
                
                mock_coffee.return_value = "coffee-123"
                mock_variant.return_value = "variant-123"
                mock_price.return_value = "price-123"
                mock_image.return_value = "image-123"
                
                # Test upserting valid artifact
                result = self.db_integration.upsert_artifact_via_rpc(
                    validation_result=validation_result,
                    roaster_id="test-roaster",
                    metadata_only=False
                )
                
                # Should return success
                assert result['success'] == True
                assert result['coffee_id'] == "coffee-123"
                assert len(result['variant_ids']) == 1
                assert len(result['price_ids']) == 1
                assert len(result['image_ids']) == 1
                assert result['variant_ids'][0] == "variant-123"
                assert result['price_ids'][0] == "price-123"
                assert result['image_ids'][0] == "image-123"

    def test_upsert_artifact_via_rpc_metadata_only(self):
        """Test upserting artifact with metadata-only flag."""
        # Create valid validation result
        validation_result = Mock()
        validation_result.is_valid = True
        validation_result.artifact_id = "test-artifact-metadata"
        validation_result.artifact_data = Mock()
        
        # Mock the artifact mapper
        with patch.object(self.db_integration.artifact_mapper, 'map_artifact_to_rpc_payloads') as mock_map:
            mock_map.return_value = {
                'coffee': {'p_name': 'Test Coffee'},
                'variants': [{'p_platform_variant_id': 'var1'}],
                'prices': [{'p_price': 10.0}],
                'images': [{'p_url': 'test.jpg'}]
            }
            
            # Mock the RPC client
            with patch.object(self.db_integration.rpc_client, 'upsert_coffee') as mock_coffee, \
                 patch.object(self.db_integration.rpc_client, 'upsert_variant') as mock_variant, \
                 patch.object(self.db_integration.rpc_client, 'insert_price') as mock_price, \
                 patch.object(self.db_integration.rpc_client, 'upsert_coffee_image') as mock_image:
                
                mock_coffee.return_value = "coffee-123"
                mock_variant.return_value = "variant-123"
                mock_price.return_value = "price-123"
                mock_image.return_value = "image-123"
                
                # Test upserting with metadata_only=True
                result = self.db_integration.upsert_artifact_via_rpc(
                    validation_result=validation_result,
                    roaster_id="test-roaster",
                    metadata_only=True
                )
                
                # Should return success but no images processed
                assert result['success'] == True
                assert result['coffee_id'] == "coffee-123"
                assert len(result['variant_ids']) == 1
                assert len(result['price_ids']) == 1
                assert len(result['image_ids']) == 0  # No images for metadata-only
