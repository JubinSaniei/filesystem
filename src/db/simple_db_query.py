#!/usr/bin/env python3
"""
Simple example script for database query API.
"""
import requests
import json
import time

import sys
import os

# Add the project root to the path so modules can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from src.utils.config import API_URL

def run_query(query, description=""):
    """Run a SQL query via the API"""
    print(f"\n--- {description} ---")
    print(f"Query: {query}")
    
    response = requests.post(
        f"{API_URL}/database_query",
        json={"query": query}
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"Query executed in {result.get('execution_time_ms', 0)}ms")
        print(f"Found {result.get('row_count', 0)} results")
        
        rows = result.get('rows', [])
        if rows:
            if len(rows) > 10:
                print("First 10 results:")
                for row in rows[:10]:
                    print(f"  {row}")
                print(f"  ... and {len(rows) - 10} more results")
            else:
                print("Results:")
                for row in rows:
                    print(f"  {row}")
        return result
    else:
        print(f"Error: {response.status_code} - {response.text}")
        return None

def main():
    # First, populate the database
    print("First, checking the database status...")
    response = requests.get(f"{API_URL}/metadata_status")
    if response.status_code == 200:
        data = response.json()
        print(f"Database status: {data.get('status')}")
        print(f"Indexed files: {data.get('indexed_files', 0)}")
    
    # Run basic queries
    run_query("SELECT COUNT(*) FROM file_metadata", "Count all files")
    
    run_query("""
        SELECT is_directory, COUNT(*) as count 
        FROM file_metadata 
        GROUP BY is_directory
    """, "Count files vs directories")
    
    run_query("""
        SELECT extension, COUNT(*) as count 
        FROM file_metadata 
        WHERE extension IS NOT NULL 
        GROUP BY extension 
        ORDER BY count DESC
    """, "Count files by extension")
    
    run_query("""
        SELECT path, size_bytes
        FROM file_metadata 
        WHERE is_directory = 0 AND size_bytes IS NOT NULL
        ORDER BY size_bytes DESC 
        LIMIT 10
    """, "Find largest files")
    
    run_query("""
        SELECT path 
        FROM file_metadata
        WHERE path LIKE '%node_modules%'
        LIMIT 5
    """, "Check for node_modules files")

if __name__ == "__main__":
    main()