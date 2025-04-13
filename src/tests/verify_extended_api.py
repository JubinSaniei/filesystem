#!/usr/bin/env python3
"""
Verify that all extended API endpoints from old_main.py are working.
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
    print("\n=== TESTING EXTENDED API ENDPOINTS ===\n")
    
    # Test read_file endpoint
    test_endpoint("post", "/read_file", data={"path": "/app/testdir/test1.txt"}, 
                  description="Read file")
    
    # Test write_file endpoint
    test_endpoint("post", "/write_file", 
                  data={"path": "/app/testdir/new_file.txt", "content": "This is a test file created by the API."}, 
                  description="Write file")
                  
    # Test read_file again to verify the file was written
    test_endpoint("post", "/read_file", data={"path": "/app/testdir/new_file.txt"}, 
                  description="Read newly created file")
    
    # Test edit_file with dry run
    test_endpoint("post", "/edit_file", 
                  data={
                      "path": "/app/testdir/new_file.txt", 
                      "edits": [
                          {"oldText": "This is a test file", "newText": "This is an edited test file"}
                      ],
                      "dryRun": True
                  }, 
                  description="Edit file (dry run)")
    
    # Test edit_file for real
    test_endpoint("post", "/edit_file", 
                  data={
                      "path": "/app/testdir/new_file.txt", 
                      "edits": [
                          {"oldText": "This is a test file", "newText": "This is an edited test file"}
                      ],
                      "dryRun": False
                  }, 
                  description="Edit file")
    
    # Test read_file again to verify the edit
    test_endpoint("post", "/read_file", data={"path": "/app/testdir/new_file.txt"}, 
                  description="Read edited file")
    
    # Test create_directory
    test_endpoint("post", "/create_directory", 
                  data={"path": "/app/testdir/new_directory"}, 
                  description="Create directory")
    
    # Test directory_tree
    test_endpoint("post", "/directory_tree", 
                  data={"path": "/app/testdir", "max_depth": 2, "include_hidden": False}, 
                  description="Get directory tree")
    
    print("\n=== TEST COMPLETE ===")
    print("All extended API endpoints have been tested.")

if __name__ == "__main__":
    main()