#!/usr/bin/env python3
"""
Verify that the metadata API endpoints are working properly.
This script tests all endpoints in the metadata_api.py module.
"""
import requests
import json
import time
import os
import sys

# Add the project root to the path so modules can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.utils.config import API_URL

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
    print("\n=== TESTING METADATA API ENDPOINTS ===\n")
    
    # Test status endpoint
    test_endpoint("get", "/metadata/status", description="Get file watcher status")
    
    # Test watch directory
    test_endpoint("post", "/metadata/watch", 
                  data={"path": "/app/testdir"}, 
                  description="Watch a directory for changes")
    
    # Test status again to verify the directory is being watched
    test_endpoint("get", "/metadata/status", description="Verify directory is being watched")
    
    # Test scan endpoint
    test_endpoint("post", "/metadata/scan", 
                  data={"path": "/app/testdir", "force": True}, 
                  description="Manually scan watched directory")
    
    # Test search endpoint
    test_endpoint("post", "/metadata/search", 
                  data={
                      "query": "test",
                      "extensions": [".txt"],
                      "is_directory": False,
                      "path_prefix": "/app/testdir",
                      "limit": 10,
                      "offset": 0
                  }, 
                  description="Search file metadata")
    
    # Test path endpoint
    test_endpoint("get", "/metadata/path/app/testdir/test1.txt", 
                  description="Get metadata for a specific path")
    
    # Test database query
    test_endpoint("post", "/metadata/database_query", 
                  data={
                      "query": "SELECT * FROM file_metadata WHERE path LIKE '/app/testdir/%' LIMIT 5",
                      "limit": 5
                  }, 
                  description="Query the metadata database")
    
    # Test reindex
    test_endpoint("post", "/metadata/reindex", 
                  data={"path": "/app/testdir"}, 
                  description="Force reindexing of directory")
    
    # Create a new file to test file change detection
    test_endpoint("post", "/write_file", 
                  data={"path": "/app/testdir/metadata_test.txt", "content": "This file tests the metadata API"}, 
                  description="Create test file for metadata indexing")
    
    # Trigger a scan to detect the new file
    test_endpoint("post", "/metadata/scan", 
                  data={"path": "/app/testdir", "force": True}, 
                  description="Scan to detect new file")
    
    # Search for the new file
    test_endpoint("post", "/metadata/search", 
                  data={
                      "query": "metadata_test",
                      "path_prefix": "/app/testdir",
                      "limit": 10,
                      "offset": 0
                  }, 
                  description="Search for the new file")
    
    # Test unwatch endpoint
    test_endpoint("post", "/metadata/unwatch", 
                  data={"path": "/app/testdir"}, 
                  description="Stop watching directory")
    
    # Test status again to verify directory is no longer watched
    test_endpoint("get", "/metadata/status", description="Verify directory is no longer watched")
    
    print("\n=== TEST COMPLETE ===")
    print("All metadata API endpoints have been tested.")

if __name__ == "__main__":
    main()