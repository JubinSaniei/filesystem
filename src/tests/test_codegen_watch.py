#!/usr/bin/env python3
"""
Simple test for watching the CodeGen directory
"""
import requests
import json
import sys
import os

# Add the project root to the path so modules can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.utils.config import API_URL

def main():
    """Test watching the CodeGen directory"""
    codegen_path = "/mnt/c/Sandboxes/CodeGen"
    
    print(f"\n=== Testing watching {codegen_path} ===\n")
    
    # Test API endpoint
    url = f"{API_URL}/metadata/watch"
    data = {"path": codegen_path}
    
    print(f"Making request to {url} with data: {data}\n")
    
    try:
        response = requests.post(url, json=data)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"Success! Response: {json.dumps(result, indent=2)}")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    main()