"""
Storage reader for A.2 integration - reads stored raw responses from fetcher.
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

from structlog import get_logger

logger = get_logger(__name__)


class StorageReader:
    """
    Reads stored raw responses from A.2's ResponseStorage system.
    
    Features:
    - Integration with A.2's file-based storage
    - Support for metadata reading
    - Error handling for missing files
    - Batch reading capabilities
    """
    
    def __init__(self, base_storage_path: str = "data/fetcher"):
        """
        Initialize storage reader.
        
        Args:
            base_storage_path: Base path to A.2 storage directory
        """
        self.base_storage_path = Path(base_storage_path)
        
        if not self.base_storage_path.exists():
            logger.warning(
                "Storage path does not exist",
                path=str(self.base_storage_path)
            )
            # Create the directory if it doesn't exist
            self.base_storage_path.mkdir(parents=True, exist_ok=True)
            
            # Create expected subdirectories for A.2 storage structure
            subdirs = ["shopify", "woocommerce", "other", "failed", "metadata"]
            for subdir in subdirs:
                (self.base_storage_path / subdir).mkdir(exist_ok=True)
    
    def read_artifact(
        self,
        roaster_id: str,
        platform: str,
        response_filename: str
    ) -> Optional[Dict[str, Any]]:
        """
        Read artifact data from A.2 storage.
        
        Args:
            roaster_id: Roaster identifier
            platform: Platform type (shopify, woocommerce, etc.)
            response_filename: Response filename from storage
            
        Returns:
            Artifact data dictionary or None if not found
        """
        try:
            # Determine storage directory based on platform
            if "failed" in response_filename:
                storage_dir = self.base_storage_path / "failed"
            else:
                storage_dir = self.base_storage_path / platform.lower()
            
            response_path = storage_dir / response_filename
            
            if not response_path.exists():
                logger.error(
                    "Response file not found",
                    roaster_id=roaster_id,
                    platform=platform,
                    response_filename=response_filename,
                    path=str(response_path)
                )
                return None
            
            # Read and parse JSON data
            with open(response_path, 'r', encoding='utf-8') as f:
                artifact_data = json.load(f)
            
            logger.info(
                "Successfully read artifact from storage",
                roaster_id=roaster_id,
                platform=platform,
                response_filename=response_filename,
                data_size=len(str(artifact_data))
            )
            
            return artifact_data
            
        except json.JSONDecodeError as e:
            logger.error(
                "Failed to parse JSON from storage",
                roaster_id=roaster_id,
                platform=platform,
                response_filename=response_filename,
                error=str(e)
            )
            return None
            
        except Exception as e:
            logger.error(
                "Failed to read artifact from storage",
                roaster_id=roaster_id,
                platform=platform,
                response_filename=response_filename,
                error=str(e)
            )
            return None
    
    def read_metadata(
        self,
        roaster_id: str,
        platform: str,
        metadata_filename: str
    ) -> Optional[Dict[str, Any]]:
        """
        Read metadata from A.2 storage.
        
        Args:
            roaster_id: Roaster identifier
            platform: Platform type
            metadata_filename: Metadata filename
            
        Returns:
            Metadata dictionary or None if not found
        """
        try:
            metadata_path = self.base_storage_path / "metadata" / metadata_filename
            
            if not metadata_path.exists():
                logger.error(
                    "Metadata file not found",
                    roaster_id=roaster_id,
                    platform=platform,
                    metadata_filename=metadata_filename,
                    path=str(metadata_path)
                )
                return None
            
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            logger.info(
                "Successfully read metadata from storage",
                roaster_id=roaster_id,
                platform=platform,
                metadata_filename=metadata_filename
            )
            
            return metadata
            
        except json.JSONDecodeError as e:
            logger.error(
                "Failed to parse metadata JSON",
                roaster_id=roaster_id,
                platform=platform,
                metadata_filename=metadata_filename,
                error=str(e)
            )
            return None
            
        except Exception as e:
            logger.error(
                "Failed to read metadata from storage",
                roaster_id=roaster_id,
                platform=platform,
                metadata_filename=metadata_filename,
                error=str(e)
            )
            return None
    
    def list_available_artifacts(
        self,
        roaster_id: Optional[str] = None,
        platform: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        List available artifacts in storage.
        
        Args:
            roaster_id: Filter by roaster ID
            platform: Filter by platform
            status: Filter by status (success, failed)
            
        Returns:
            List of artifact information dictionaries
        """
        artifacts = []
        
        try:
            # Determine which directories to search
            if platform:
                search_dirs = [self.base_storage_path / platform.lower()]
            else:
                search_dirs = [
                    self.base_storage_path / "shopify",
                    self.base_storage_path / "woocommerce",
                    self.base_storage_path / "other",
                    self.base_storage_path / "failed"
                ]
            
            for search_dir in search_dirs:
                if not search_dir.exists():
                    continue
                
                for response_file in search_dir.glob("*.json"):
                    # Skip metadata files
                    if response_file.name.startswith("metadata"):
                        continue
                    
                    # Parse filename to extract information
                    filename_parts = response_file.stem.split('_')
                    if len(filename_parts) >= 3:
                        file_roaster_id = filename_parts[0]
                        file_platform = filename_parts[1]
                        file_status = "failed" if "failed" in response_file.name else "success"
                        
                        # Apply filters
                        if roaster_id and file_roaster_id != roaster_id:
                            continue
                        if status and file_status != status:
                            continue
                        
                        # Get file stats
                        stat = response_file.stat()
                        
                        artifacts.append({
                            'filename': response_file.name,
                            'roaster_id': file_roaster_id,
                            'platform': file_platform,
                            'status': file_status,
                            'size_bytes': stat.st_size,
                            'modified_at': datetime.fromtimestamp(stat.st_mtime),
                            'path': str(response_file)
                        })
            
            logger.info(
                "Listed available artifacts",
                total_count=len(artifacts),
                roaster_id=roaster_id,
                platform=platform,
                status=status
            )
            
        except Exception as e:
            logger.error(
                "Failed to list available artifacts",
                error=str(e)
            )
        
        return artifacts
    
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
                if platform_dir.is_dir() and platform_dir.name != "metadata":
                    platform_name = platform_dir.name
                    platform_files = list(platform_dir.glob("*.json"))
                    
                    stats['by_platform'][platform_name] = len(platform_files)
                    stats['total_files'] += len(platform_files)
                    
                    # Calculate total size and status counts
                    for file_path in platform_files:
                        file_size = file_path.stat().st_size
                        stats['total_size_bytes'] += file_size
                        
                        # Determine status from filename
                        if "_failed" in file_path.name:
                            status = "failed"
                        else:
                            status = "success"
                        
                        stats['by_status'][status] = stats['by_status'].get(status, 0) + 1
            
        except Exception as e:
            logger.error("Failed to calculate storage stats", error=str(e))
        
        return stats
