import requests
import json
import time
import sys
import os

# Add the project root to the path so modules can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from src.utils.config import API_URL

def test_indexing(path):
    """Test indexing a directory and print progress"""
    print(f"Testing indexing on path: {path}")
    
    # First check if ignore patterns are loaded
    ignore_response = requests.get(f"{API_URL}/ignore_patterns")
    ignore_data = ignore_response.json()
    print(f"Ignore patterns status: {ignore_data.get('status')}")
    print(f"Number of ignore patterns loaded: {ignore_data.get('pattern_count', 0)}")
    
    # Start indexing
    start_time = time.time()
    print(f"Starting indexing operation at {time.strftime('%H:%M:%S')}")
    
    index_response = requests.post(
        f"{API_URL}/index_directory",
        json={"path": path}
    )
    
    if index_response.status_code != 200:
        print(f"Indexing failed with status code: {index_response.status_code}")
        print(index_response.text)
        return
    
    # Get the result
    result = index_response.json()
    end_time = time.time()
    duration = end_time - start_time
    
    print(f"Indexing completed in {duration:.2f} seconds")
    print(f"Status: {result.get('status')}")
    print(f"Files indexed: {result.get('file_count', 0)}")
    print(f"Message: {result.get('message', '')}")
    
    # Check metadata status
    metadata_response = requests.get(f"{API_URL}/metadata_status")
    metadata_data = metadata_response.json()
    print(f"\nMetadata status: {metadata_data.get('status')}")
    print(f"Total indexed files in database: {metadata_data.get('indexed_files', 0)}")

if __name__ == "__main__":
    # Use command line arg or default to CodeGen
    path = sys.argv[1] if len(sys.argv) > 1 else "/mnt/c/Sandboxes/CodeGen"
    test_indexing(path)