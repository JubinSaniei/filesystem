import requests
import json
import time
import sys
import os

# Add the project root to the path so modules can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from src.utils.config import API_URL

def test_search(path):
    """Test searching files in a path"""
    print(f"Testing search on path: {path}")
    
    # Search for all files
    search_response = requests.post(
        f"{API_URL}/search_files",
        json={
            "path": path,
            "pattern": "",  # Empty pattern to match all files
            "excludePatterns": [],
            "pagination": {
                "offset": 0,
                "limit": 10  # Just get first 10 files
            },
            "timeout_seconds": 30
        }
    )
    
    if search_response.status_code != 200:
        print(f"Search failed with status code: {search_response.status_code}")
        print(search_response.text)
        return
    
    # Get the result
    result = search_response.json()
    print(f"Total files: {result.get('total', 0)}")
    
    # Show first few results
    items = result.get('items', [])
    if items:
        print("\nSample of indexed files:")
        for item in items[:10]:
            print(f"- {item.get('path')} ({item.get('type')})")
    
    # Try searching for node_modules which should be ignored
    print("\nSearching for 'node_modules' (should be ignored)...")
    search_node_response = requests.post(
        "http://localhost:8010/search_files",
        json={
            "path": path,
            "pattern": "node_modules",
            "excludePatterns": [],
            "pagination": {
                "offset": 0,
                "limit": 10
            },
            "timeout_seconds": 30
        }
    )
    
    node_result = search_node_response.json()
    node_items = node_result.get('items', [])
    
    if node_items:
        print(f"Found {node_result.get('total', 0)} node_modules items (should be 0 or very few if ignore patterns are working)")
        for item in node_items[:5]:
            print(f"- {item.get('path')} ({item.get('type')})")
    else:
        print("No node_modules found - ignore patterns are working correctly!")

if __name__ == "__main__":
    # Use command line arg or default to CodeGen
    path = sys.argv[1] if len(sys.argv) > 1 else "/mnt/c/Sandboxes/CodeGen"
    test_search(path)