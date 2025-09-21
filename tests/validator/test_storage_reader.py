"""
Tests for storage reader.
"""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, mock_open
from datetime import datetime

from src.validator.storage_reader import StorageReader


class TestStorageReader:
    """Test cases for StorageReader."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.storage_reader = StorageReader(base_storage_path=self.temp_dir)
    
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_read_artifact_success(self):
        """Test successful artifact reading."""
        # Create test artifact data
        artifact_data = {
            "source": "shopify",
            "roaster_domain": "example.com",
            "scraped_at": "2025-01-12T10:00:00Z",
            "product": {
                "platform_product_id": "123",
                "title": "Test Product",
                "source_url": "https://example.com/product",
                "variants": [
                    {
                        "platform_variant_id": "v-001",
                        "price": "10.00"
                    }
                ]
            }
        }
        
        # Create test file
        test_file = Path(self.temp_dir) / "shopify" / "test_roaster_shopify_20250112_100000_success.json"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(test_file, 'w') as f:
            json.dump(artifact_data, f)
        
        # Test reading
        result = self.storage_reader.read_artifact(
            roaster_id="test_roaster",
            platform="shopify",
            response_filename="test_roaster_shopify_20250112_100000_success.json"
        )
        
        assert result is not None
        assert result["source"] == "shopify"
        assert result["roaster_domain"] == "example.com"
        assert result["product"]["platform_product_id"] == "123"
    
    def test_read_artifact_not_found(self):
        """Test reading non-existent artifact."""
        result = self.storage_reader.read_artifact(
            roaster_id="test_roaster",
            platform="shopify",
            response_filename="nonexistent.json"
        )
        
        assert result is None
    
    def test_read_artifact_invalid_json(self):
        """Test reading artifact with invalid JSON."""
        # Create test file with invalid JSON
        test_file = Path(self.temp_dir) / "shopify" / "invalid.json"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(test_file, 'w') as f:
            f.write("invalid json content")
        
        result = self.storage_reader.read_artifact(
            roaster_id="test_roaster",
            platform="shopify",
            response_filename="invalid.json"
        )
        
        assert result is None
    
    def test_read_artifact_failed_status(self):
        """Test reading artifact from failed directory."""
        artifact_data = {"error": "Failed to fetch"}
        
        # Create test file in failed directory
        test_file = Path(self.temp_dir) / "failed" / "test_roaster_shopify_20250112_100000_failed.json"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(test_file, 'w') as f:
            json.dump(artifact_data, f)
        
        result = self.storage_reader.read_artifact(
            roaster_id="test_roaster",
            platform="shopify",
            response_filename="test_roaster_shopify_20250112_100000_failed.json"
        )
        
        assert result is not None
        assert result["error"] == "Failed to fetch"
    
    def test_read_metadata_success(self):
        """Test successful metadata reading."""
        metadata = {
            "roaster_id": "test_roaster",
            "platform": "shopify",
            "timestamp": "2025-01-12T10:00:00Z",
            "status": "success",
            "content_hash": "abc123"
        }
        
        # Create test metadata file
        test_file = Path(self.temp_dir) / "metadata" / "test_roaster_shopify_20250112_100000_metadata.json"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(test_file, 'w') as f:
            json.dump(metadata, f)
        
        result = self.storage_reader.read_metadata(
            roaster_id="test_roaster",
            platform="shopify",
            metadata_filename="test_roaster_shopify_20250112_100000_metadata.json"
        )
        
        assert result is not None
        assert result["roaster_id"] == "test_roaster"
        assert result["platform"] == "shopify"
        assert result["content_hash"] == "abc123"
    
    def test_read_metadata_not_found(self):
        """Test reading non-existent metadata."""
        result = self.storage_reader.read_metadata(
            roaster_id="test_roaster",
            platform="shopify",
            metadata_filename="nonexistent_metadata.json"
        )
        
        assert result is None
    
    def test_list_available_artifacts(self):
        """Test listing available artifacts."""
        # Create test artifacts
        artifacts_data = [
            {
                "roaster_id": "roaster1",
                "platform": "shopify",
                "filename": "roaster1_shopify_20250112_100000_success.json"
            },
            {
                "roaster_id": "roaster2",
                "platform": "woocommerce",
                "filename": "roaster2_woocommerce_20250112_110000_success.json"
            },
            {
                "roaster_id": "roaster1",
                "platform": "shopify",
                "filename": "roaster1_shopify_20250112_120000_failed.json"
            }
        ]
        
        # Create test files
        for artifact in artifacts_data:
            platform_dir = Path(self.temp_dir) / artifact["platform"]
            platform_dir.mkdir(parents=True, exist_ok=True)
            
            test_file = platform_dir / artifact["filename"]
            with open(test_file, 'w') as f:
                json.dump({"test": "data"}, f)
        
        # Test listing all artifacts
        all_artifacts = self.storage_reader.list_available_artifacts()
        assert len(all_artifacts) == 3
        
        # Test filtering by roaster
        roaster1_artifacts = self.storage_reader.list_available_artifacts(roaster_id="roaster1")
        assert len(roaster1_artifacts) == 2
        
        # Test filtering by platform
        shopify_artifacts = self.storage_reader.list_available_artifacts(platform="shopify")
        assert len(shopify_artifacts) == 2
        
        # Test filtering by status
        success_artifacts = self.storage_reader.list_available_artifacts(status="success")
        assert len(success_artifacts) == 2
        
        failed_artifacts = self.storage_reader.list_available_artifacts(status="failed")
        assert len(failed_artifacts) == 1
    
    def test_get_storage_stats(self):
        """Test getting storage statistics."""
        # Create test files
        shopify_dir = Path(self.temp_dir) / "shopify"
        shopify_dir.mkdir(parents=True, exist_ok=True)
        
        woocommerce_dir = Path(self.temp_dir) / "woocommerce"
        woocommerce_dir.mkdir(parents=True, exist_ok=True)
        
        failed_dir = Path(self.temp_dir) / "failed"
        failed_dir.mkdir(parents=True, exist_ok=True)
        
        # Create test files with different sizes
        test_files = [
            (shopify_dir / "test1.json", '{"data": "test1"}'),
            (shopify_dir / "test2.json", '{"data": "test2"}'),
            (woocommerce_dir / "test3.json", '{"data": "test3"}'),
            (failed_dir / "test4_failed.json", '{"error": "failed"}')
        ]
        
        for file_path, content in test_files:
            with open(file_path, 'w') as f:
                f.write(content)
        
        stats = self.storage_reader.get_storage_stats()
        
        assert stats['total_files'] == 4
        assert stats['by_platform']['shopify'] == 2
        assert stats['by_platform']['woocommerce'] == 1
        assert stats['by_status']['success'] == 3
        assert stats['by_status']['failed'] == 1
        assert stats['total_size_bytes'] > 0
        assert stats['storage_path'] == self.temp_dir
    
    def test_get_storage_stats_empty(self):
        """Test getting storage statistics for empty storage."""
        stats = self.storage_reader.get_storage_stats()
        
        assert stats['total_files'] == 0
        assert stats['by_platform'] == {}
        assert stats['by_status'] == {}
        assert stats['total_size_bytes'] == 0
        assert stats['storage_path'] == self.temp_dir
    
    def test_storage_path_creation(self):
        """Test that storage paths are created if they don't exist."""
        # Create StorageReader with non-existent path
        new_temp_dir = Path(self.temp_dir) / "new_storage"
        storage_reader = StorageReader(base_storage_path=str(new_temp_dir))
        
        # Check that directories were created
        assert new_temp_dir.exists()
        assert (new_temp_dir / "shopify").exists()
        assert (new_temp_dir / "woocommerce").exists()
        assert (new_temp_dir / "other").exists()
        assert (new_temp_dir / "failed").exists()
        assert (new_temp_dir / "metadata").exists()
