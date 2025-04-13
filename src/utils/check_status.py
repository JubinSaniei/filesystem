import requests
import json
import time
import sys

def check_status():
    """Check the status of the indexing operation"""
    print("Checking metadata status...")
    
    # Check metadata status
    try:
        # Add the project root to the path so modules can be imported
        sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
        from src.utils.config import API_URL
        
        metadata_response = requests.get(f"{API_URL}/metadata_status")
        metadata_data = metadata_response.json()
        print(f"Metadata status: {metadata_data.get('status')}")
        print(f"Total indexed files in database: {metadata_data.get('indexed_files', 0)}")
        
        # Check ignore patterns
        ignore_response = requests.get(f"{API_URL}/ignore_patterns")
        ignore_data = ignore_response.json()
        print(f"Ignore patterns status: {ignore_data.get('status')}")
        print(f"Number of ignore patterns loaded: {ignore_data.get('pattern_count', 0)}")
        
        # Get some pattern examples
        patterns = ignore_data.get('patterns', [])
        if patterns:
            print("\nSome example ignore patterns:")
            for pattern in patterns[:10]:  # Show first 10 patterns
                print(f"- {pattern}")
            print("...")
    except Exception as e:
        print(f"Error checking status: {e}")

if __name__ == "__main__":
    check_status()