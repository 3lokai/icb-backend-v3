"""
Performance tests for ImageKit batch upload scenarios.

Tests the performance characteristics of ImageKit uploads
with various batch sizes and concurrency levels.
"""

import pytest
import time
import asyncio
from unittest.mock import Mock, patch, MagicMock
from concurrent.futures import ThreadPoolExecutor
from src.images.imagekit_config import ImageKitConfig
from src.images.imagekit_service import ImageKitService
from src.images.imagekit_integration import ImageKitIntegrationService
from src.validator.rpc_client import RPCClient


@pytest.fixture
def imagekit_config():
    """Create ImageKit configuration for testing."""
    return ImageKitConfig(
        public_key="test_public_key",
        private_key="test_private_key",
        url_endpoint="https://ik.imagekit.io/test"
    )


@pytest.fixture
def mock_rpc_client():
    """Create mock RPC client for testing."""
    return Mock(spec=RPCClient)


@pytest.fixture
def imagekit_service(imagekit_config):
    """Create ImageKit service for testing."""
    return ImageKitService(imagekit_config)


@pytest.fixture
def imagekit_integration_service(mock_rpc_client, imagekit_config):
    """Create ImageKit integration service for testing."""
    return ImageKitIntegrationService(
        rpc_client=mock_rpc_client,
        imagekit_config=imagekit_config,
        enable_deduplication=True,
        enable_imagekit=True
    )


def test_batch_upload_performance_small_batch(imagekit_service):
    """Test performance with small batch (5 images)."""
    # Mock successful uploads
    with patch('src.images.imagekit_service.ImageKit.upload_file') as mock_upload:
        mock_upload.return_value = MagicMock(
            url="https://ik.imagekit.io/test/uploaded.jpg",
            fileId="file_123"
        )
        
        # Test data
        images_data = [
            {'url': f'https://example.com/img{i}.jpg', 'content': b'fake_content'}
            for i in range(5)
        ]
        
        start_time = time.time()
        
        # Process batch
        results = []
        for image_data in images_data:
            result = imagekit_service.upload_image(
                image_data['url'], 
                image_data['content']
            )
            results.append(result)
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Verify all uploads succeeded
        assert all(result.success for result in results)
        assert len(results) == 5
        
        # Performance assertions
        assert processing_time < 1.0  # Should complete within 1 second
        assert imagekit_service.stats['uploads_attempted'] == 5
        assert imagekit_service.stats['uploads_successful'] == 5
        assert imagekit_service.stats['uploads_failed'] == 0


def test_batch_upload_performance_medium_batch(imagekit_service):
    """Test performance with medium batch (20 images)."""
    # Mock successful uploads
    with patch('src.images.imagekit_service.ImageKit.upload_file') as mock_upload:
        mock_upload.return_value = MagicMock(
            url="https://ik.imagekit.io/test/uploaded.jpg",
            fileId="file_123"
        )
        
        # Test data
        images_data = [
            {'url': f'https://example.com/img{i}.jpg', 'content': b'fake_content'}
            for i in range(20)
        ]
        
        start_time = time.time()
        
        # Process batch
        results = []
        for image_data in images_data:
            result = imagekit_service.upload_image(
                image_data['url'], 
                image_data['content']
            )
            results.append(result)
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Verify all uploads succeeded
        assert all(result.success for result in results)
        assert len(results) == 20
        
        # Performance assertions
        assert processing_time < 5.0  # Should complete within 5 seconds
        assert imagekit_service.stats['uploads_attempted'] == 20
        assert imagekit_service.stats['uploads_successful'] == 20
        assert imagekit_service.stats['uploads_failed'] == 0


def test_batch_upload_performance_large_batch(imagekit_service):
    """Test performance with large batch (100 images)."""
    # Mock successful uploads
    with patch('src.images.imagekit_service.ImageKit.upload_file') as mock_upload:
        mock_upload.return_value = MagicMock(
            url="https://ik.imagekit.io/test/uploaded.jpg",
            fileId="file_123"
        )
        
        # Test data
        images_data = [
            {'url': f'https://example.com/img{i}.jpg', 'content': b'fake_content'}
            for i in range(100)
        ]
        
        start_time = time.time()
        
        # Process batch
        results = []
        for image_data in images_data:
            result = imagekit_service.upload_image(
                image_data['url'], 
                image_data['content']
            )
            results.append(result)
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Verify all uploads succeeded
        assert all(result.success for result in results)
        assert len(results) == 100
        
        # Performance assertions
        assert processing_time < 30.0  # Should complete within 30 seconds
        assert imagekit_service.stats['uploads_attempted'] == 100
        assert imagekit_service.stats['uploads_successful'] == 100
        assert imagekit_service.stats['uploads_failed'] == 0


def test_batch_upload_performance_with_retries(imagekit_service):
    """Test performance with retry logic enabled."""
    # Mock uploads with some failures
    with patch('src.images.imagekit_service.ImageKit.upload_file') as mock_upload:
        # First call fails, second succeeds
        mock_upload.side_effect = [
            Exception("Network error"),
            MagicMock(url="https://ik.imagekit.io/test/uploaded.jpg", fileId="file_123")
        ]
        
        # Test data
        images_data = [
            {'url': f'https://example.com/img{i}.jpg', 'content': b'fake_content'}
            for i in range(10)
        ]
        
        start_time = time.time()
        
        # Process batch with retries
        results = []
        for image_data in images_data:
            result = imagekit_service.upload_image(
                image_data['url'], 
                image_data['content']
            )
            results.append(result)
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Verify all uploads succeeded after retries
        assert all(result.success for result in results)
        assert len(results) == 10
        
        # Performance assertions
        assert processing_time < 10.0  # Should complete within 10 seconds
        assert imagekit_service.stats['uploads_attempted'] == 10
        assert imagekit_service.stats['uploads_successful'] == 10
        assert imagekit_service.stats['uploads_failed'] == 0


def test_batch_upload_performance_with_failures(imagekit_service):
    """Test performance with some upload failures."""
    # Mock uploads with some failures
    with patch('src.images.imagekit_service.ImageKit.upload_file') as mock_upload:
        # Some uploads fail, some succeed
        mock_upload.side_effect = [
            MagicMock(url="https://ik.imagekit.io/test/uploaded1.jpg", fileId="file_1"),
            Exception("Network error"),
            MagicMock(url="https://ik.imagekit.io/test/uploaded3.jpg", fileId="file_3"),
            Exception("Timeout"),
            MagicMock(url="https://ik.imagekit.io/test/uploaded5.jpg", fileId="file_5")
        ]
        
        # Test data
        images_data = [
            {'url': f'https://example.com/img{i}.jpg', 'content': b'fake_content'}
            for i in range(5)
        ]
        
        start_time = time.time()
        
        # Process batch
        results = []
        for image_data in images_data:
            result = imagekit_service.upload_image(
                image_data['url'], 
                image_data['content']
            )
            results.append(result)
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Verify some uploads succeeded, some failed
        successful_results = [r for r in results if r.success]
        failed_results = [r for r in results if not r.success]
        
        assert len(successful_results) == 3
        assert len(failed_results) == 2
        
        # Performance assertions
        assert processing_time < 5.0  # Should complete within 5 seconds
        assert imagekit_service.stats['uploads_attempted'] == 5
        assert imagekit_service.stats['uploads_successful'] == 3
        assert imagekit_service.stats['uploads_failed'] == 2


def test_batch_upload_performance_concurrent(imagekit_service):
    """Test performance with concurrent uploads."""
    # Mock successful uploads
    with patch('src.images.imagekit_service.ImageKit.upload_file') as mock_upload:
        mock_upload.return_value = MagicMock(
            url="https://ik.imagekit.io/test/uploaded.jpg",
            fileId="file_123"
        )
        
        # Test data
        images_data = [
            {'url': f'https://example.com/img{i}.jpg', 'content': b'fake_content'}
            for i in range(20)
        ]
        
        start_time = time.time()
        
        # Process batch concurrently
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = []
            for image_data in images_data:
                future = executor.submit(
                    imagekit_service.upload_image,
                    image_data['url'],
                    image_data['content']
                )
                futures.append(future)
            
            # Wait for all uploads to complete
            results = [future.result() for future in futures]
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Verify all uploads succeeded
        assert all(result.success for result in results)
        assert len(results) == 20
        
        # Performance assertions
        assert processing_time < 3.0  # Should complete within 3 seconds
        assert imagekit_service.stats['uploads_attempted'] == 20
        assert imagekit_service.stats['uploads_successful'] == 20
        assert imagekit_service.stats['uploads_failed'] == 0


def test_batch_upload_performance_memory_usage(imagekit_service):
    """Test memory usage during batch uploads."""
    import psutil
    import os
    
    # Get initial memory usage
    process = psutil.Process(os.getpid())
    initial_memory = process.memory_info().rss / 1024 / 1024  # MB
    
    # Mock successful uploads
    with patch('src.images.imagekit_service.ImageKit.upload_file') as mock_upload:
        mock_upload.return_value = MagicMock(
            url="https://ik.imagekit.io/test/uploaded.jpg",
            fileId="file_123"
        )
        
        # Test data with larger content
        images_data = [
            {'url': f'https://example.com/img{i}.jpg', 'content': b'fake_content' * 1000}
            for i in range(50)
        ]
        
        # Process batch
        results = []
        for image_data in images_data:
            result = imagekit_service.upload_image(
                image_data['url'], 
                image_data['content']
            )
            results.append(result)
        
        # Get final memory usage
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Verify all uploads succeeded
        assert all(result.success for result in results)
        assert len(results) == 50
        
        # Memory usage assertions
        assert memory_increase < 100  # Should not increase memory by more than 100MB
        assert imagekit_service.stats['uploads_attempted'] == 50
        assert imagekit_service.stats['uploads_successful'] == 50
        assert imagekit_service.stats['uploads_failed'] == 0


def test_batch_upload_performance_statistics(imagekit_service):
    """Test performance statistics collection."""
    # Mock successful uploads
    with patch('src.images.imagekit_service.ImageKit.upload_file') as mock_upload:
        mock_upload.return_value = MagicMock(
            url="https://ik.imagekit.io/test/uploaded.jpg",
            fileId="file_123"
        )
        
        # Test data
        images_data = [
            {'url': f'https://example.com/img{i}.jpg', 'content': b'fake_content'}
            for i in range(10)
        ]
        
        # Process batch
        results = []
        for image_data in images_data:
            result = imagekit_service.upload_image(
                image_data['url'], 
                image_data['content']
            )
            results.append(result)
        
        # Get statistics
        stats = imagekit_service.get_stats()
        
        # Verify statistics
        assert stats['uploads_attempted'] == 10
        assert stats['uploads_successful'] == 10
        assert stats['uploads_failed'] == 0
        assert stats['success_rate'] == 1.0
        assert stats['failure_rate'] == 0.0
        assert stats['avg_upload_time'] > 0
        assert stats['total_upload_time'] > 0


def test_batch_upload_performance_reset_stats(imagekit_service):
    """Test statistics reset functionality."""
    # Mock successful uploads
    with patch('src.images.imagekit_service.ImageKit.upload_file') as mock_upload:
        mock_upload.return_value = MagicMock(
            url="https://ik.imagekit.io/test/uploaded.jpg",
            fileId="file_123"
        )
        
        # Process some uploads
        for i in range(5):
            imagekit_service.upload_image(
                f'https://example.com/img{i}.jpg',
                b'fake_content'
            )
        
        # Verify stats are set
        stats_before = imagekit_service.get_stats()
        assert stats_before['uploads_attempted'] == 5
        assert stats_before['uploads_successful'] == 5
        
        # Reset stats
        imagekit_service.reset_stats()
        
        # Verify stats are reset
        stats_after = imagekit_service.get_stats()
        assert stats_after['uploads_attempted'] == 0
        assert stats_after['uploads_successful'] == 0
        assert stats_after['uploads_failed'] == 0
        assert stats_after['success_rate'] == 0.0
        assert stats_after['failure_rate'] == 0.0
        assert stats_after['avg_upload_time'] == 0.0
        assert stats_after['total_upload_time'] == 0.0


def test_batch_upload_performance_integration_service(imagekit_integration_service):
    """Test performance with ImageKit integration service."""
    # Mock the integration service
    with patch.object(imagekit_integration_service, 'process_batch_with_imagekit') as mock_process:
        mock_process.return_value = [
            {
                'url': f'https://example.com/img{i}.jpg',
                'is_duplicate': False,
                'imagekit_url': f'https://ik.imagekit.io/test/img{i}.jpg',
                'imagekit_file_id': f'file_{i}',
                'imagekit_upload_time': 1.0,
                'integration_status': 'completed'
            }
            for i in range(20)
        ]
        
        # Test data
        images_data = [
            {'url': f'https://example.com/img{i}.jpg', 'content': b'fake_content'}
            for i in range(20)
        ]
        
        start_time = time.time()
        
        # Process batch
        results = imagekit_integration_service.process_batch_with_imagekit(
            images_data, 
            'coffee_123'
        )
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Verify all images were processed
        assert len(results) == 20
        assert all(r['integration_status'] == 'completed' for r in results)
        
        # Performance assertions
        assert processing_time < 2.0  # Should complete within 2 seconds
        assert imagekit_integration_service.stats['images_processed'] == 20
        assert imagekit_integration_service.stats['imagekit_uploads'] == 20
        assert imagekit_integration_service.stats['imagekit_failures'] == 0
        assert imagekit_integration_service.stats['duplicates_skipped'] == 0
        assert imagekit_integration_service.stats['fallback_used'] == 0
