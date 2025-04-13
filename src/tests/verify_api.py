#!/usr/bin/env python3
"""
Verify that both the original API functionality and the database query functionality are working.
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
    # Test root endpoint
    test_endpoint("get", "/", description="Root endpoint")
    
    # Test indexing directory
    test_endpoint("post", "/index_directory", data={"path": "/app/testdir"}, 
                  description="Index directory")
    
    # Test list directory
    test_endpoint("post", "/list_directory", data={"path": "/app/testdir"}, 
                  description="List directory")
    
    # Test database query
    test_endpoint("post", "/database_query", 
                  data={"query": "SELECT COUNT(*) FROM file_metadata"}, 
                  description="Database query")
    
    # Test search files
    test_endpoint("post", "/search_files", 
                  data={
                      "path": "/app/testdir",
                      "pattern": "txt",
                      "excludePatterns": [],
                      "pagination": {"offset": 0, "limit": 10},
                      "timeout_seconds": 30
                  }, 
                  description="Search files")

if __name__ == "__main__":
    main()