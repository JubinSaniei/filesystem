#!/usr/bin/env python3
"""
Simple example script for testing database query API.
"""
import requests
import json
import time
import sys

# Add the project root to the path so modules can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from src.utils.config import API_URL

def run_query(query, description=""):
    """Run a SQL query via the API"""
    print(f"\n--- {description} ---")
    print(f"Query: {query}")
    
    try:
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
            print(f"Error: {response.status_code}")
            print(response.text)
            return None
    except Exception as e:
        print(f"Error executing query: {e}")
        return None

def main():
    # First, index our test directory
    print("Indexing test directory...")
    try:
        response = requests.post(
            f"{API_URL}/index_directory",
            json={"path": "/app/testdir"}
        )
        if response.status_code == 200:
            data = response.json()
            print(f"Indexing completed: {data.get('message')}")
            print(f"Files indexed: {data.get('file_count')}")
        else:
            print(f"Error indexing: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"Error indexing directory: {e}")

    # Wait a moment for indexing to complete
    time.sleep(1)
    
    # Run simple queries
    run_query("SELECT COUNT(*) FROM file_metadata", "Count all files")
    
    run_query("SELECT path, is_directory FROM file_metadata", "List all indexed files and directories")
    
    run_query("SELECT extension, COUNT(*) FROM file_metadata WHERE extension IS NOT NULL GROUP BY extension", 
              "Count files by extension")
    
    run_query("SELECT * FROM file_metadata WHERE path LIKE '%txt'", "Find text files")
    
    # Try a query that should fail (contains a banned keyword)
    run_query("SELECT * FROM file_metadata; DELETE FROM file_metadata", "This query should fail due to ;")
    
    # Example with parameterized query
    run_query("SELECT * FROM file_metadata WHERE extension = '.txt'", "Find all .txt files")

if __name__ == "__main__":
    main()