"""
Raw response storage module for fetcher service.
Handles storing raw API responses with metadata for validation and replay.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime, timezone
import hashlib

from structlog import get_logger

logger = get_logger(__name__)


class ResponseStorage:
    """
    Handles storage of raw API responses with metadata.
    
    Features:
    - File-based storage with organized directory structure
    - Metadata tracking (timestamp, roaster, platform, status)
    - Response deduplication using content hashing
    - Error handling and logging
    """
    
    def __init__(self, base_storage_path: str = "data/fetcher"):
        """
        Initialize response storage.
        
        Args:
            base_storage_path: Base directory for storing raw responses
        """
        self.base_storage_path = Path(base_storage_path)
        self.base_storage_path.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories for organization
        self._create_directory_structure()
    
    def _create_directory_structure(self):
        """Create organized directory structure for storage."""
        directories = [
            "shopify",
            "woocommerce", 
            "other",
            "failed",
            "metadata"
        ]
        
        for directory in directories:
            (self.base_storage_path / directory).mkdir(exist_ok=True)
    
    def _generate_filename(
        self,
        roaster_id: str,
        platform: str,
        timestamp: datetime,
        status: str = "success"
    ) -> str:
        """
        Generate organized filename for storage.
        
        Args:
            roaster_id: Roaster identifier
            platform: Platform type (shopify, woocommerce, etc.)
            timestamp: Response timestamp
            status: Response status (success, failed, etc.)
            
        Returns:
            Generated filename
        """
        # Format: {roaster_id}_{platform}_{timestamp}_{status}.json
        timestamp_str = timestamp.strftime("%Y%m%d_%H%M%S")
        return f"{roaster_id}_{platform}_{timestamp_str}_{status}.json"
    
    def _generate_metadata_filename(
        self,
        roaster_id: str,
        platform: str,
        timestamp: datetime
    ) -> str:
        """
        Generate metadata filename.
        
        Args:
            roaster_id: Roaster identifier
            platform: Platform type
            timestamp: Response timestamp
            
        Returns:
            Generated metadata filename
        """
        timestamp_str = timestamp.strftime("%Y%m%d_%H%M%S")
        return f"{roaster_id}_{platform}_{timestamp_str}_metadata.json"
    
    def _calculate_content_hash(self, content: str) -> str:
        """
        Calculate SHA-256 hash of content for deduplication.
        
        Args:
            content: Content to hash
            
        Returns:
            SHA-256 hash as hex string
        """
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    async def store_response(
        self,
        roaster_id: str,
        platform: str,
        response_data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
        status: str = "success"
    ) -> Dict[str, str]:
        """
        Store raw API response with metadata.
        
        Args:
            roaster_id: Roaster identifier
            platform: Platform type (shopify, woocommerce, etc.)
            response_data: Raw response data to store
            metadata: Additional metadata to store
            status: Response status (success, failed, etc.)
            
        Returns:
            Dictionary with storage information
        """
        timestamp = datetime.now(timezone.utc)
        
        try:
            # Generate filenames
            response_filename = self._generate_filename(
                roaster_id, platform, timestamp, status
            )
            metadata_filename = self._generate_metadata_filename(
                roaster_id, platform, timestamp
            )
            
            # Determine storage directory based on platform and status
            if status == "failed":
                storage_dir = self.base_storage_path / "failed"
            else:
                storage_dir = self.base_storage_path / platform.lower()
            
            # Ensure directory exists
            storage_dir.mkdir(parents=True, exist_ok=True)
            
            # Store response data
            response_path = storage_dir / response_filename
            with open(response_path, 'w', encoding='utf-8') as f:
                json.dump(response_data, f, indent=2, ensure_ascii=False)
            
            # Calculate content hash for deduplication
            content_str = json.dumps(response_data, sort_keys=True)
            content_hash = self._calculate_content_hash(content_str)
            
            # Prepare metadata
            storage_metadata = {
                'roaster_id': roaster_id,
                'platform': platform,
                'timestamp': timestamp.isoformat(),
                'status': status,
                'response_filename': response_filename,
                'response_path': str(response_path),
                'content_hash': content_hash,
                'content_size': len(content_str),
                'product_count': response_data.get('products', []) if isinstance(response_data, dict) else [],
                'metadata': metadata or {}
            }
            
            # Store metadata
            metadata_path = self.base_storage_path / "metadata" / metadata_filename
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(storage_metadata, f, indent=2, ensure_ascii=False)
            
            logger.info(
                "Stored raw response",
                roaster_id=roaster_id,
                platform=platform,
                status=status,
                response_path=str(response_path),
                metadata_path=str(metadata_path),
                content_hash=content_hash,
                content_size=len(content_str),
            )
            
            return {
                'response_path': str(response_path),
                'metadata_path': str(metadata_path),
                'content_hash': content_hash,
                'filename': response_filename,
                'metadata_filename': metadata_filename
            }
            
        except Exception as e:
            logger.error(
                "Failed to store response",
                roaster_id=roaster_id,
                platform=platform,
                status=status,
                error=str(e),
            )
            raise
    
    async def store_failed_response(
        self,
        roaster_id: str,
        platform: str,
        error_data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, str]:
        """
        Store failed response data for debugging.
        
        Args:
            roaster_id: Roaster identifier
            platform: Platform type
            error_data: Error information to store
            metadata: Additional metadata
            
        Returns:
            Dictionary with storage information
        """
        return await self.store_response(
            roaster_id=roaster_id,
            platform=platform,
            response_data=error_data,
            metadata=metadata,
            status="failed"
        )
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """
        Get storage statistics.
        
        Returns:
            Dictionary with storage statistics
        """
        stats = {
            'total_files': 0,
            'by_platform': {},
            'by_status': {},
            'total_size_bytes': 0,
            'storage_path': str(self.base_storage_path)
        }
        
        try:
            for platform_dir in self.base_storage_path.iterdir():
                if platform_dir.is_dir():
                    platform_name = platform_dir.name
                    platform_files = list(platform_dir.glob("*.json"))
                    
                    stats['by_platform'][platform_name] = len(platform_files)
                    stats['total_files'] += len(platform_files)
                    
                    # Calculate total size
                    for file_path in platform_files:
                        stats['total_size_bytes'] += file_path.stat().st_size
            
            # Count by status (based on filename)
            for platform_dir in self.base_storage_path.iterdir():
                if platform_dir.is_dir() and platform_dir.name != "metadata":
                    for file_path in platform_dir.glob("*.json"):
                        filename = file_path.name
                        if "_failed" in filename:
                            status = "failed"
                        else:
                            status = "success"
                        
                        stats['by_status'][status] = stats['by_status'].get(status, 0) + 1
            
        except Exception as e:
            logger.error("Failed to calculate storage stats", error=str(e))
        
        return stats
    
    def cleanup_old_responses(self, days_to_keep: int = 30) -> Dict[str, int]:
        """
        Clean up old response files.
        
        Args:
            days_to_keep: Number of days to keep files
            
        Returns:
            Dictionary with cleanup statistics
        """
        cutoff_date = datetime.now(timezone.utc).timestamp() - (days_to_keep * 24 * 60 * 60)
        cleaned_files = 0
        total_size_freed = 0
        
        try:
            for platform_dir in self.base_storage_path.iterdir():
                if platform_dir.is_dir() and platform_dir.name != "metadata":
                    for file_path in platform_dir.glob("*.json"):
                        if file_path.stat().st_mtime < cutoff_date:
                            file_size = file_path.stat().st_size
                            file_path.unlink()
                            cleaned_files += 1
                            total_size_freed += file_size
            
            logger.info(
                "Cleaned up old response files",
                files_removed=cleaned_files,
                size_freed_bytes=total_size_freed,
                days_kept=days_to_keep
            )
            
        except Exception as e:
            logger.error("Failed to cleanup old responses", error=str(e))
        
        return {
            'files_removed': cleaned_files,
            'size_freed_bytes': total_size_freed
        }
