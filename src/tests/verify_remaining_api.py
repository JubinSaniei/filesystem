#!/usr/bin/env python3
"""
Verify the remaining API endpoints from old_main.py.
"""
import requests
import json
import time
import os

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
    print("\n=== TESTING REMAINING API ENDPOINTS ===\n")
    
    # Test get_metadata endpoint
    test_endpoint("post", "/get_metadata", data={"path": "/app/testdir/test1.txt"}, 
                  description="Get file metadata")
    
    # Test list_allowed_directories endpoint
    test_endpoint("get", "/list_allowed_directories", 
                  description="List allowed directories")
    
    # Test search_content endpoint
    test_endpoint("post", "/search_content", 
                  data={
                      "path": "/app/testdir",
                      "search_query": "test",
                      "recursive": True,
                      "file_pattern": "*.txt",
                      "pagination": {"offset": 0, "limit": 10}
                  }, 
                  description="Search content in files")
    
    # Test metadata_search endpoint
    test_endpoint("post", "/metadata_search", 
                  data={
                      "query": "test",
                      "extensions": [".txt"],
                      "path_prefix": "/app/testdir",
                      "limit": 10,
                      "offset": 0
                  }, 
                  description="Search using metadata")
    
    # Test delete_path endpoint - Create a test file first
    test_endpoint("post", "/write_file", 
                  data={
                      "path": "/app/testdir/to_delete.txt", 
                      "content": "This file will be deleted"
                  }, 
                  description="Create file for deletion")
    
    # Delete the file
    test_endpoint("post", "/delete_path", 
                  data={
                      "path": "/app/testdir/to_delete.txt",
                      "recursive": False,
                      "confirm_delete": True
                  }, 
                  description="Delete file")
    
    # Test move_path endpoint - Create a file first
    test_endpoint("post", "/write_file", 
                  data={
                      "path": "/app/testdir/to_move.txt", 
                      "content": "This file will be moved"
                  }, 
                  description="Create file for moving")
    
    # Move the file
    test_endpoint("post", "/move_path", 
                  data={
                      "source_path": "/app/testdir/to_move.txt",
                      "destination_path": "/app/testdir/moved_file.txt"
                  }, 
                  description="Move file")
    
    print("\n=== TEST COMPLETE ===")
    print("All remaining API endpoints have been tested.")

if __name__ == "__main__":
    main()