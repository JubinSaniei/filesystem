#!/usr/bin/env python3
"""
Final test script to verify all our improvements are working.
Tests:
1. Unlimited file indexing (no 1000 file limit)
2. Ignore pattern functionality
3. Database query API
4. CORS support
5. Original API functionality
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
                print(f"Response (first 500 chars): {json.dumps(result, indent=2)[:500]}...")
                return result
            except:
                print(f"Response (first 500 chars): {response.text[:500]}...")
                return response.text
        else:
            print(f"Error: {response.text}")
            return None
    except Exception as e:
        print(f"Error testing endpoint: {e}")
        return None

def main():
    print("\n=== FILESYSTEM API FINAL TEST ===\n")
    
    # Test 1: Test root endpoint and API info
    test_endpoint("get", "/", description="Root endpoint")
    
    # Test 2: Test unlimited file indexing
    print("\n=== Testing unlimited file indexing ===")
    test_endpoint("post", "/index_directory", data={"path": "/app/testdir"}, 
                  description="Index directory without file limit")
                  
    # Test 3: Test ignore pattern functionality
    print("\n=== Testing ignore pattern functionality ===")
    # Check ignore patterns by querying the database
    test_endpoint("post", "/database_query", 
                  data={"query": "SELECT parent_dir, COUNT(*) as file_count FROM file_metadata GROUP BY parent_dir"}, 
                  description="Check indexed directories (should exclude ignored paths)")
                  
    # Test 4: Test database query API with various query types
    print("\n=== Testing database query API ===")
    # Basic count query
    test_endpoint("post", "/database_query", 
                  data={"query": "SELECT COUNT(*) FROM file_metadata"}, 
                  description="Count all files")
                  
    # Query by extension
    test_endpoint("post", "/database_query", 
                  data={"query": "SELECT extension, COUNT(*) as count FROM file_metadata WHERE extension IS NOT NULL GROUP BY extension"}, 
                  description="Count files by extension")
                  
    # Query by size
    test_endpoint("post", "/database_query", 
                  data={"query": "SELECT path, size_bytes FROM file_metadata WHERE is_directory = 0 ORDER BY size_bytes DESC LIMIT 5"}, 
                  description="Find largest files")
                  
    # Test 5: Test original API functionality (list_directory)
    print("\n=== Testing original API functionality ===")
    test_endpoint("post", "/list_directory", data={"path": "/app/testdir"}, 
                  description="List directory contents")
                  
    # Test search_files endpoint
    test_endpoint("post", "/search_files", 
                  data={
                      "path": "/app/testdir",
                      "pattern": "txt",
                      "recursive": True,
                      "excludePatterns": [],
                      "pagination": {"offset": 0, "limit": 10},
                      "timeout_seconds": 30
                  }, 
                  description="Search files")
                  
    print("\n=== TEST COMPLETE ===")
    print("All tests have been executed.")
    print("Please check the output above to verify that all functionality is working correctly.")

if __name__ == "__main__":
    main()