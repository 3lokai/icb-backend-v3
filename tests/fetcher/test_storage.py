"""
Tests for response storage functionality.
"""

import pytest
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from unittest.mock import patch

from src.fetcher.storage import ResponseStorage


class TestResponseStorage:
    """Test response storage functionality."""
    
    @pytest.fixture
    def temp_storage(self):
        """Create temporary storage directory for testing."""
        temp_dir = tempfile.mkdtemp()
        storage = ResponseStorage(temp_dir)
        yield storage
        shutil.rmtree(temp_dir)
    
    def test_storage_initialization(self, temp_storage):
        """Test storage initialization and directory creation."""
        assert temp_storage.base_storage_path.exists()
        assert (temp_storage.base_storage_path / "shopify").exists()
        assert (temp_storage.base_storage_path / "woocommerce").exists()
        assert (temp_storage.base_storage_path / "other").exists()
        assert (temp_storage.base_storage_path / "failed").exists()
        assert (temp_storage.base_storage_path / "metadata").exists()
    
    @pytest.mark.asyncio
    async def test_store_successful_response(self, temp_storage):
        """Test storing a successful response."""
        roaster_id = "test_roaster"
        platform = "shopify"
        response_data = {
            "products": [
                {"id": 1, "title": "Test Coffee", "price": "19.99"},
                {"id": 2, "title": "Another Coffee", "price": "24.99"}
            ],
            "total": 2
        }
        metadata = {"source_id": "test_source", "fetch_all": True}
        
        result = await temp_storage.store_response(
            roaster_id=roaster_id,
            platform=platform,
            response_data=response_data,
            metadata=metadata,
            status="success"
        )
        
        # Check return values
        assert "response_path" in result
        assert "metadata_path" in result
        assert "content_hash" in result
        assert "filename" in result
        assert "metadata_filename" in result
        
        # Check files were created
        response_path = Path(result["response_path"])
        metadata_path = Path(result["metadata_path"])
        
        assert response_path.exists()
        assert metadata_path.exists()
        
        # Check response file content
        with open(response_path, 'r') as f:
            stored_data = json.load(f)
        assert stored_data == response_data
        
        # Check metadata file content
        with open(metadata_path, 'r') as f:
            stored_metadata = json.load(f)
        
        assert stored_metadata["roaster_id"] == roaster_id
        assert stored_metadata["platform"] == platform
        assert stored_metadata["status"] == "success"
        assert stored_metadata["metadata"] == metadata
        assert "content_hash" in stored_metadata
        assert "timestamp" in stored_metadata
    
    @pytest.mark.asyncio
    async def test_store_failed_response(self, temp_storage):
        """Test storing a failed response."""
        roaster_id = "test_roaster"
        platform = "woocommerce"
        error_data = {
            "error": "Connection timeout",
            "error_type": "TimeoutError",
            "attempts": 3
        }
        metadata = {"source_id": "test_source", "fetch_all": True}
        
        result = await temp_storage.store_failed_response(
            roaster_id=roaster_id,
            platform=platform,
            error_data=error_data,
            metadata=metadata
        )
        
        # Check return values
        assert "response_path" in result
        assert "metadata_path" in result
        
        # Check files were created in failed directory
        response_path = Path(result["response_path"])
        assert response_path.exists()
        assert "failed" in str(response_path)
        
        # Check response file content
        with open(response_path, 'r') as f:
            stored_data = json.load(f)
        assert stored_data == error_data
    
    def test_filename_generation(self, temp_storage):
        """Test filename generation logic."""
        roaster_id = "test_roaster"
        platform = "shopify"
        timestamp = datetime(2025, 1, 12, 10, 30, 45)
        
        # Test successful response filename
        filename = temp_storage._generate_filename(
            roaster_id, platform, timestamp, "success"
        )
        expected = "test_roaster_shopify_20250112_103045_success.json"
        assert filename == expected
        
        # Test failed response filename
        filename = temp_storage._generate_filename(
            roaster_id, platform, timestamp, "failed"
        )
        expected = "test_roaster_shopify_20250112_103045_failed.json"
        assert filename == expected
    
    def test_metadata_filename_generation(self, temp_storage):
        """Test metadata filename generation."""
        roaster_id = "test_roaster"
        platform = "woocommerce"
        timestamp = datetime(2025, 1, 12, 10, 30, 45)
        
        filename = temp_storage._generate_metadata_filename(
            roaster_id, platform, timestamp
        )
        expected = "test_roaster_woocommerce_20250112_103045_metadata.json"
        assert filename == expected
    
    def test_content_hash_calculation(self, temp_storage):
        """Test content hash calculation for deduplication."""
        content1 = '{"products": [{"id": 1, "title": "Coffee"}]}'
        content2 = '{"products": [{"id": 1, "title": "Coffee"}]}'
        content3 = '{"products": [{"id": 2, "title": "Tea"}]}'
        
        hash1 = temp_storage._calculate_content_hash(content1)
        hash2 = temp_storage._calculate_content_hash(content2)
        hash3 = temp_storage._calculate_content_hash(content3)
        
        # Same content should produce same hash
        assert hash1 == hash2
        
        # Different content should produce different hash
        assert hash1 != hash3
        
        # Hash should be consistent
        assert len(hash1) == 64  # SHA-256 hex string length
    
    def test_storage_stats_empty(self, temp_storage):
        """Test storage stats with empty storage."""
        stats = temp_storage.get_storage_stats()
        
        assert stats["total_files"] == 0
        # Check that platform directories exist but are empty
        assert "shopify" in stats["by_platform"]
        assert "woocommerce" in stats["by_platform"]
        assert "failed" in stats["by_platform"]
        assert "other" in stats["by_platform"]
        assert "metadata" in stats["by_platform"]
        assert stats["by_status"] == {}
        assert stats["total_size_bytes"] == 0
        assert "storage_path" in stats
    
    @pytest.mark.asyncio
    async def test_storage_stats_with_files(self, temp_storage):
        """Test storage stats with files."""
        # Store some test responses
        await temp_storage.store_response(
            roaster_id="roaster1",
            platform="shopify",
            response_data={"products": []},
            status="success"
        )
        
        await temp_storage.store_response(
            roaster_id="roaster2",
            platform="woocommerce",
            response_data={"products": []},
            status="success"
        )
        
        await temp_storage.store_failed_response(
            roaster_id="roaster3",
            platform="shopify",
            error_data={"error": "test"}
        )
        
        stats = temp_storage.get_storage_stats()
        
        assert stats["total_files"] >= 3  # 2 success + 1 failed + metadata files
        assert "shopify" in stats["by_platform"]
        assert "woocommerce" in stats["by_platform"]
        assert "failed" in stats["by_platform"]
        assert stats["total_size_bytes"] > 0
    
    def test_cleanup_old_responses(self, temp_storage):
        """Test cleanup of old responses."""
        # This test would require mocking file timestamps
        # For now, just test that the method runs without error
        result = temp_storage.cleanup_old_responses(days_to_keep=30)
        
        assert "files_removed" in result
        assert "size_freed_bytes" in result
        assert isinstance(result["files_removed"], int)
        assert isinstance(result["size_freed_bytes"], int)
    
    @pytest.mark.asyncio
    async def test_storage_error_handling(self, temp_storage):
        """Test error handling in storage operations."""
        # Test with invalid data that might cause JSON serialization issues
        with patch('json.dump', side_effect=Exception("JSON serialization error")):
            with pytest.raises(Exception):
                await temp_storage.store_response(
                    roaster_id="test",
                    platform="shopify",
                    response_data={"invalid": object()},  # Non-serializable object
                    status="success"
                )
    
    @pytest.mark.asyncio
    async def test_metadata_inclusion(self, temp_storage):
        """Test that metadata is properly included in stored files."""
        roaster_id = "metadata_test"
        platform = "shopify"
        response_data = {"products": [{"id": 1, "title": "Test"}]}
        metadata = {
            "source_id": "test_source",
            "fetch_all": True,
            "custom_field": "custom_value"
        }
        
        result = await temp_storage.store_response(
            roaster_id=roaster_id,
            platform=platform,
            response_data=response_data,
            metadata=metadata,
            status="success"
        )
        
        # Check metadata file
        metadata_path = Path(result["metadata_path"])
        with open(metadata_path, 'r') as f:
            stored_metadata = json.load(f)
        
        assert stored_metadata["metadata"] == metadata
        assert stored_metadata["roaster_id"] == roaster_id
        assert stored_metadata["platform"] == platform
        assert stored_metadata["status"] == "success"
        assert "content_hash" in stored_metadata
        assert "timestamp" in stored_metadata
        assert "response_filename" in stored_metadata
        assert "response_path" in stored_metadata
