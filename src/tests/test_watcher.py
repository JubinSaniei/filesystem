#!/usr/bin/env python3
"""
Comprehensive tests for the file watcher API endpoints.
Tests watch, unwatch, status, and scan operations.
"""
import requests
import json
import time
import os
import sys

# Add the project root to the path so modules can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.utils.config import API_URL, get_allowed_directories

def test_endpoint(method, endpoint, data=None, description=""):
    """Test an API endpoint"""
    print(f"\n=== Testing {method.upper()} {endpoint} - {description} ===")
    
    try:
        if method.lower() == "get":
            response = requests.get(f"{API_URL}{endpoint}")
        elif method.lower() == "post":
            response = requests.post(f"{API_URL}{endpoint}", json=data)
        else:
            print(f"Unsupported method: {method}")
            return None
            
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            try:
                result = response.json()
                print(f"Response: {json.dumps(result, indent=2)[:500]}...")
                return result
            except:
                print(f"Response: {response.text[:500]}...")
                return response.text
        else:
            print(f"Error: {response.text}")
            return None
    except Exception as e:
        print(f"Error testing endpoint: {e}")
        return None

def main():
    print("\n=== TESTING FILE WATCHER API ENDPOINTS ===\n")
    
    # Get allowed directories from config
    allowed_dirs = get_allowed_directories()
    print(f"Allowed directories: {allowed_dirs}")
    
    # First, check current watcher status
    status = test_endpoint("get", "/metadata/status", description="Initial watcher status")
    
    # Then unwatch any currently watched directories
    if status and status.get("watched_directories"):
        for dir_path in status["watched_directories"]:
            test_endpoint("post", "/metadata/unwatch", 
                         data={"path": dir_path}, 
                         description=f"Unwatch directory {dir_path}")
    
    # Test watching a test directory
    test_endpoint("post", "/metadata/watch", 
                 data={"path": "/app/testdir"}, 
                 description="Watch test directory")
    
    # Verify directory is being watched
    test_endpoint("get", "/metadata/status", description="Verify test directory is watched")
    
    # Test scanning the watched directory
    test_endpoint("post", "/metadata/scan", 
                 data={"path": "/app/testdir", "force": True}, 
                 description="Scan test directory")
    
    # Test watching specific directories rather than all allowed directories
    # This is to keep the test runtime reasonable
    test_dirs = []
    for dir_path in allowed_dirs:
        # Skip if this is the test directory we already watched
        if dir_path == "/app/testdir":
            continue
        
        # Only add first additional directory to keep test short
        test_dirs.append(dir_path)
        if len(test_dirs) >= 1:
            break
    
    print(f"\nSelected test directories: {test_dirs}")
    
    for dir_path in test_dirs:
        # Try to watch the directory
        result = test_endpoint("post", "/metadata/watch", 
                              data={"path": dir_path}, 
                              description=f"Watch allowed directory {dir_path}")
        
        # If successfully watched, try scanning it
        if result and result.get("status") == "success":
            test_endpoint("post", "/metadata/scan", 
                         data={"path": dir_path, "force": True}, 
                         description=f"Scan watched directory {dir_path}")
    
    # Check status after watching all directories
    test_endpoint("get", "/metadata/status", description="Status after watching all directories")
    
    # Create a test file to trigger a change
    test_endpoint("post", "/write_file", 
                 data={"path": "/app/testdir/watcher_test.txt", "content": "Testing file watcher change detection"}, 
                 description="Create test file for watcher")
    
    # Wait briefly for the watcher to detect the change
    print("\nWaiting 2 seconds for the watcher to detect changes...")
    time.sleep(2)
    
    # Trigger a manual scan
    test_endpoint("post", "/metadata/scan", 
                 data={"force": True}, 
                 description="Scan all watched directories")
    
    # Unwatch all directories
    status = test_endpoint("get", "/metadata/status", description="Get status before unwatching")
    
    if status and status.get("watched_directories"):
        for dir_path in status["watched_directories"]:
            test_endpoint("post", "/metadata/unwatch", 
                         data={"path": dir_path}, 
                         description=f"Unwatch directory {dir_path}")
    
    # Final status check
    test_endpoint("get", "/metadata/status", description="Final watcher status")
    
    print("\n=== TEST COMPLETE ===")
    print("All file watcher API endpoints have been tested.")

if __name__ == "__main__":
    main()