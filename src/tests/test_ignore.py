import requests
import json
import time
import sys
import os

# Add the project root to the path so modules can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from src.utils.config import API_URL

def test_ignore_extensions():
    """Test if specific file extensions are being ignored"""
    print("Testing if ignore patterns for file extensions are working correctly...")
    
    # List of extensions that should be ignored based on ignore.md
    ignored_extensions = [
        "*.pdb", "*.obj", "*.cache", "*.suo", "*.user", "*.dll", "*.exe"
    ]
    
    for ext in ignored_extensions:
        ext_pattern = ext.replace("*", "")  # Remove wildcard for search
        print(f"\nSearching for {ext_pattern} files (should be ignored)...")
        
        search_response = requests.post(
            f"{API_URL}/search_files",
            json={
                "path": "/mnt/c/Sandboxes/CodeGen",
                "pattern": ext_pattern,
                "excludePatterns": [],
                "pagination": {
                    "offset": 0,
                    "limit": 5
                },
                "timeout_seconds": 20
            }
        )
        
        if search_response.status_code != 200:
            print(f"Search failed with status code: {search_response.status_code}")
            continue
        
        result = search_response.json()
        total = result.get('total', 0)
        items = result.get('items', [])
        
        # Check if any of the items have the extension we're looking for
        matching_items = [item for item in items if item.get('path', '').endswith(ext_pattern)]
        
        if matching_items:
            print(f"Found {len(matching_items)} files with extension {ext_pattern} (should be 0 if ignore patterns are working)")
            for item in matching_items[:3]:  # Show a few examples
                print(f"- {item.get('path')}")
        else:
            print(f"No files with extension {ext_pattern} found - ignore patterns working correctly!")

if __name__ == "__main__":
    test_ignore_extensions()