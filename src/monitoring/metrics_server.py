#!/usr/bin/env python3
"""
Metrics Server for ICB-Backend Monitoring

This module provides a Prometheus metrics server for the ICB-Backend application.
It exposes metrics at /metrics endpoint for Prometheus scraping.
"""

import os
import time
import threading
from typing import Optional
from prometheus_client import start_http_server, generate_latest, CONTENT_TYPE_LATEST
from prometheus_client.core import CollectorRegistry, REGISTRY
from prometheus_client.exposition import make_wsgi_app
from wsgiref.simple_server import make_server
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MetricsServer:
    """Prometheus metrics server for ICB-Backend."""
    
    def __init__(self, port: int = 8000, host: str = "0.0.0.0"):
        """Initialize metrics server."""
        self.port = port
        self.host = host
        self.server = None
        self.thread = None
        self.running = False
        
        # Create custom registry
        self.registry = CollectorRegistry()
        
        # Register default collectors
        from prometheus_client import PROCESS_COLLECTOR, PLATFORM_COLLECTOR, GC_COLLECTOR
        self.registry.register(PROCESS_COLLECTOR)
        self.registry.register(PLATFORM_COLLECTOR)
        self.registry.register(GC_COLLECTOR)
        
        logger.info(f"Metrics server initialized on {host}:{port}")
    
    def start(self):
        """Start the metrics server in a separate thread."""
        if self.running:
            logger.warning("Metrics server is already running")
            return
        
        try:
            # Create WSGI app for metrics endpoint
            app = make_wsgi_app(self.registry)
            
            # Start HTTP server
            self.server = make_server(self.host, self.port, app)
            
            # Start server in a separate thread
            self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
            self.thread.start()
            
            self.running = True
            logger.info(f"✅ Metrics server started on http://{self.host}:{self.port}/metrics")
            
        except Exception as e:
            logger.error(f"❌ Failed to start metrics server: {e}")
            raise
    
    def stop(self):
        """Stop the metrics server."""
        if not self.running:
            logger.warning("Metrics server is not running")
            return
        
        try:
            if self.server:
                self.server.shutdown()
                self.server.server_close()
            
            if self.thread:
                self.thread.join(timeout=5)
            
            self.running = False
            logger.info("✅ Metrics server stopped")
            
        except Exception as e:
            logger.error(f"❌ Error stopping metrics server: {e}")
    
    def get_metrics(self) -> str:
        """Get current metrics as Prometheus format."""
        try:
            return generate_latest(self.registry).decode('utf-8')
        except Exception as e:
            logger.error(f"❌ Error generating metrics: {e}")
            return ""
    
    def is_running(self) -> bool:
        """Check if metrics server is running."""
        return self.running
    
    def get_status(self) -> dict:
        """Get server status information."""
        return {
            "running": self.running,
            "host": self.host,
            "port": self.port,
            "metrics_url": f"http://{self.host}:{self.port}/metrics",
            "health_url": f"http://{self.host}:{self.port}/health"
        }

def create_metrics_server(port: int = None, host: str = None) -> MetricsServer:
    """Create and configure metrics server."""
    # Get configuration from environment
    port = port or int(os.getenv("METRICS_PORT", "8000"))
    host = host or os.getenv("METRICS_HOST", "0.0.0.0")
    
    return MetricsServer(port=port, host=host)

def start_metrics_server(port: int = None, host: str = None) -> MetricsServer:
    """Create, start, and return metrics server."""
    server = create_metrics_server(port, host)
    server.start()
    return server

if __name__ == "__main__":
    """Run metrics server standalone."""
    import argparse
    
    parser = argparse.ArgumentParser(description="ICB-Backend Metrics Server")
    parser.add_argument("--port", type=int, default=8000, help="Port to run metrics server on")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind metrics server to")
    
    args = parser.parse_args()
    
    # Create and start server
    server = start_metrics_server(port=args.port, host=args.host)
    
    try:
        logger.info("🚀 Metrics server is running. Press Ctrl+C to stop.")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("🛑 Stopping metrics server...")
        server.stop()
        logger.info("✅ Metrics server stopped.")
