#!/usr/bin/env python3
"""
Dashboard Runner Script

This script starts the operations dashboard with proper configuration.
"""

import os
import sys
from pathlib import Path

# Add the parent directory to the Python path so we can import from src
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
sys.path.insert(0, str(parent_dir))

# Set environment variables if not already set
os.environ.setdefault('FLASK_ENV', 'development')
os.environ.setdefault('FLASK_DEBUG', '1')

# Import and run the Flask app
from app import app

if __name__ == '__main__':
    print("🚀 Starting Coffee Scraping Operations Dashboard...")
    print("📊 Dashboard will be available at: http://localhost:5000")
    print("🔧 API endpoints available at: http://localhost:5000/api/")
    print("💡 Press Ctrl+C to stop the server")
    
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True,
        threaded=True
    )
