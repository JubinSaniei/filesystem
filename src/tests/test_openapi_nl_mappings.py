#!/usr/bin/env python3
"""
Test script to verify that the OpenAPI schema includes natural language mappings.
"""
import requests
import json
import sys
import os

# Add the project root to the path so modules can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.utils.config import API_URL

def test_openapi_schema():
    """
    Fetch the OpenAPI schema and verify that it includes natural language mappings.
    """
    print("Testing OpenAPI schema for natural language mappings...")
    
    try:
        response = requests.get(f"{API_URL}/openapi.json")
        if response.status_code != 200:
            print(f"Error: Failed to fetch OpenAPI schema. Status code: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
        schema = response.json()
        
        # Check if the schema has the x-natural-language-enabled flag
        if "info" in schema and schema["info"].get("x-natural-language-enabled"):
            print("✓ Schema has x-natural-language-enabled flag")
        else:
            print("✗ Schema is missing x-natural-language-enabled flag")
            
        # Check for natural language mappings in endpoints
        endpoints_with_nl = []
        missing_nl = []
        
        for path, path_item in schema["paths"].items():
            for method, operation in path_item.items():
                if "x-natural-language-queries" in operation:
                    endpoints_with_nl.append(f"{method.upper()} {path}")
                else:
                    missing_nl.append(f"{method.upper()} {path}")
        
        print(f"\nEndpoints with natural language mappings ({len(endpoints_with_nl)}):")
        for endpoint in sorted(endpoints_with_nl):
            print(f"  ✓ {endpoint}")
            
        print(f"\nEndpoints without natural language mappings ({len(missing_nl)}):")
        for endpoint in sorted(missing_nl):
            print(f"  ✗ {endpoint}")
            
        # Check specific important endpoints
        key_endpoints = [
            ("/metadata/status", "get"),
            ("/metadata/watch", "post"),
            ("/metadata/unwatch", "post"),
            ("/metadata/scan", "post"),
            ("/list_allowed_directories", "get")
        ]
        
        print("\nChecking key endpoints:")
        for path, method in key_endpoints:
            if path in schema["paths"] and method in schema["paths"][path]:
                operation = schema["paths"][path][method]
                if "x-natural-language-queries" in operation:
                    intents = operation["x-natural-language-queries"]["intents"]
                    print(f"  ✓ {method.upper()} {path} has {len(intents)} natural language intents")
                else:
                    print(f"  ✗ {method.upper()} {path} is missing natural language mapping")
            else:
                print(f"  ? {method.upper()} {path} not found in schema")
                
        return True
    except Exception as e:
        print(f"Error testing OpenAPI schema: {e}")
        return False

if __name__ == "__main__":
    test_openapi_schema()