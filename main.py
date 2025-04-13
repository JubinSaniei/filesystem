#!/usr/bin/env python3
"""
Main entry point for the Filesystem API application.
"""
import sys
import os
import uvicorn
import argparse

# Add the project root to the path so modules can be imported
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Filesystem API Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind the server to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind the server to")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload on file changes")
    parser.add_argument("--no-access-log", action="store_true", help="Disable access logs")
    parser.add_argument("--log-level", default="info", choices=["debug", "info", "warning", "error", "critical"], 
                        help="Logging level")
    args = parser.parse_args()
    
    # Import configuration 
    from src.utils.config import API_PORT
    
    # Start the application with uvicorn
    uvicorn.run(
        "src.core.main:app", 
        host=args.host, 
        port=args.port or API_PORT,  # Use argument port or config port
        reload=args.reload,
        log_level=args.log_level,
        access_log=not args.no_access_log
    )