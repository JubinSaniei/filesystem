#!/usr/bin/env python3
"""
Example script showing how to use the database query API.
This will index a directory and then run several example queries.
"""
import requests
import json
import time
import sys
from pprint import pprint

# Add the project root to the path so modules can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from src.utils.config import API_URL

def format_json(data):
    """Format JSON data for pretty printing"""
    return json.dumps(data, indent=2)

def index_directory(path):
    """Index a directory to populate the database"""
    print(f"Indexing directory: {path}")
    
    response = requests.post(
        f"{API_URL}/index_directory",
        json={"path": path}
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"Indexing completed: {data.get('message')}")
        print(f"Files indexed: {data.get('file_count', 0)}")
        return True
    else:
        print(f"Error: {response.status_code} - {response.text}")
        return False

def run_query(query, params=None, limit=1000):
    """Run a SQL query via the API"""
    print(f"\n--- Running query: {query} ---")
    
    response = requests.post(
        f"{API_URL}/database_query",
        json={
            "query": query,
            "params": params,
            "limit": limit
        }
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

def demo_queries():
    """Run a series of example queries to demonstrate capabilities"""
    # Get database status
    print("\nFetching database status...")
    response = requests.get(f"{API_URL}/metadata_status")
    if response.status_code == 200:
        data = response.json()
        print(f"Database status: {data.get('status')}")
        print(f"Indexed files: {data.get('indexed_files', 0)}")
    
    # Example 1: Count all files
    run_query("SELECT COUNT(*) FROM file_metadata")
    
    # Example 2: Count files by type (directory vs file)
    run_query("""
        SELECT is_directory, COUNT(*) as count 
        FROM file_metadata 
        GROUP BY is_directory
    """)
    
    # Example 3: Get file extension distribution
    run_query("""
        SELECT extension, COUNT(*) as count 
        FROM file_metadata 
        WHERE extension IS NOT NULL 
        GROUP BY extension 
        ORDER BY count DESC
    """)
    
    # Example 4: Find the largest files
    run_query("""
        SELECT path, size_bytes, mime_type
        FROM file_metadata 
        WHERE is_directory = 0 AND size_bytes IS NOT NULL
        ORDER BY size_bytes DESC 
        LIMIT 10
    """)
    
    # Example 5: Find most recently modified files
    run_query("""
        SELECT path, modified_time
        FROM file_metadata
        WHERE is_directory = 0
        ORDER BY modified_time DESC
        LIMIT 10
    """)
    
    # Example 6: Find directories with most files
    run_query("""
        SELECT parent_dir, COUNT(*) as file_count
        FROM file_metadata
        GROUP BY parent_dir
        ORDER BY file_count DESC
        LIMIT 10
    """)
    
    # Example 7: Find files by extension
    extension = ".py"
    run_query("""
        SELECT path, size_bytes
        FROM file_metadata
        WHERE extension = :extension
        ORDER BY size_bytes DESC
    """, params={"extension": extension})
    
    # Example 8: Count files by parent directory
    run_query("""
        SELECT parent_dir, 
               COUNT(*) as total_files,
               SUM(CASE WHEN is_directory = 0 THEN 1 ELSE 0 END) as files,
               SUM(CASE WHEN is_directory = 1 THEN 1 ELSE 0 END) as directories
        FROM file_metadata
        GROUP BY parent_dir
        ORDER BY total_files DESC
        LIMIT 10
    """)
    
    # Example 9: Find ignored files (if any made it through)
    run_query("""
        SELECT path
        FROM file_metadata
        WHERE 
            path LIKE '%node_modules%' OR
            path LIKE '%.git%' OR
            path LIKE '%__pycache__%'
        LIMIT 20
    """)

def check_schema():
    """Get the database schema information"""
    print("\n--- Database Schema Information ---")
    
    # Get table schema
    schema_query = """
    SELECT 
        name, sql
    FROM 
        sqlite_master
    WHERE 
        type='table' AND 
        name='file_metadata'
    """
    
    schema_result = run_query(schema_query)
    if schema_result and schema_result.get('rows'):
        table_def = schema_result['rows'][0].get('sql', '')
        print(f"\nTable Definition:\n{table_def}")
    
    # Get column info
    columns_query = """
    PRAGMA table_info(file_metadata)
    """
    try:
        # This might fail since we block PRAGMA
        run_query(columns_query)
    except:
        print("Note: PRAGMA commands are blocked for security reasons")
        print("Column information based on table definition above")

if __name__ == "__main__":
    # Index a directory if provided as an argument
    if len(sys.argv) > 1:
        path = sys.argv[1]
        if index_directory(path):
            # Wait a bit for indexing to complete
            print("Waiting for indexing to finish...")
            time.sleep(3)
    
    # Run demo queries
    demo_queries()
    
    # Check schema 
    check_schema()