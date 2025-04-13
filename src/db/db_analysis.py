#!/usr/bin/env python3
"""
Database Analysis Tool

This script provides examples of how to use the database query API
for analyzing the metadata database.
"""
import requests
import json
import time
import sys
import os
from datetime import datetime, timedelta

# Add the project root to the path so modules can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from src.utils.config import API_URL

def run_query(query, params=None, description=None):
    """Run a SQL query via the API"""
    if description:
        print(f"\n=== {description} ===")
        print(f"Query: {query}")
    
    try:
        response = requests.post(
            f"{API_URL}/database_query",
            json={
                "query": query,
                "params": params,
                "limit": 1000
            }
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error {response.status_code}: {response.text}")
            return None
    except Exception as e:
        print(f"Error executing query: {e}")
        return None

def print_results(result, max_rows=10):
    """Print query results in a formatted way"""
    if not result:
        print("No results or query failed")
        return
    
    rows = result.get("rows", [])
    if not rows:
        print("Query returned 0 rows")
        return
    
    # Get headers from first row
    headers = list(rows[0].keys())
    
    # Format header row
    header_str = " | ".join(headers)
    print(header_str)
    print("-" * len(header_str))
    
    # Print rows
    row_count = len(rows)
    for i, row in enumerate(rows):
        if i >= max_rows:
            print(f"... {row_count - max_rows} more rows ...")
            break
        values = [str(row.get(header, "")) for header in headers]
        print(" | ".join(values))
    
    # Print summary
    print(f"\nTotal: {row_count} rows")
    print(f"Query time: {result.get('execution_time_ms', 0)}ms")

def analyze_database():
    """Run various analyses on the database"""
    
    # Get table schema
    schema = run_query(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='file_metadata'",
        description="Database Schema"
    )
    if schema and schema.get("rows"):
        print(f"Table Definition:\n{schema['rows'][0]['sql']}")
    
    # Get basic stats
    total_stats = run_query(
        """
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN is_directory = 1 THEN 1 ELSE 0 END) as directories,
            SUM(CASE WHEN is_directory = 0 THEN 1 ELSE 0 END) as files,
            COUNT(DISTINCT parent_dir) as unique_dirs
        FROM file_metadata
        """,
        description="Basic Statistics"
    )
    if total_stats and total_stats.get("rows"):
        print_results(total_stats)
    
    # File extensions
    extensions = run_query(
        """
        SELECT 
            extension, 
            COUNT(*) as count,
            ROUND(SUM(size_bytes) / 1024.0, 2) as total_kb
        FROM file_metadata
        WHERE extension IS NOT NULL
        GROUP BY extension
        ORDER BY count DESC
        """,
        description="File Extensions"
    )
    print_results(extensions)
    
    # File sizes
    sizes = run_query(
        """
        SELECT 
            CASE
                WHEN size_bytes IS NULL THEN 'Unknown'
                WHEN size_bytes < 1024 THEN '< 1 KB'
                WHEN size_bytes < 10240 THEN '1-10 KB'
                WHEN size_bytes < 102400 THEN '10-100 KB'
                WHEN size_bytes < 1048576 THEN '100 KB-1 MB'
                WHEN size_bytes < 10485760 THEN '1-10 MB'
                WHEN size_bytes < 104857600 THEN '10-100 MB'
                ELSE '> 100 MB'
            END as size_range,
            COUNT(*) as count
        FROM file_metadata
        WHERE is_directory = 0
        GROUP BY size_range
        ORDER BY CASE
            WHEN size_range = 'Unknown' THEN 0
            WHEN size_range = '< 1 KB' THEN 1
            WHEN size_range = '1-10 KB' THEN 2
            WHEN size_range = '10-100 KB' THEN 3
            WHEN size_range = '100 KB-1 MB' THEN 4
            WHEN size_range = '1-10 MB' THEN 5
            WHEN size_range = '10-100 MB' THEN 6
            ELSE 7
        END
        """,
        description="File Size Distribution"
    )
    print_results(sizes)
    
    # Most recent files
    recent = run_query(
        """
        SELECT 
            path, 
            modified_time, 
            size_bytes,
            extension
        FROM file_metadata
        WHERE is_directory = 0
        ORDER BY modified_time DESC
        LIMIT 10
        """,
        description="Most Recently Modified Files"
    )
    print_results(recent)
    
    # Files not being filtered by ignore patterns
    should_be_ignored = run_query(
        """
        SELECT 
            path
        FROM file_metadata
        WHERE path LIKE '%node_modules%'
           OR path LIKE '%.git%'
           OR path LIKE '%__pycache__%'
           OR path LIKE '%.vs%'
           OR path LIKE '%bin/Debug%'
           OR path LIKE '%bin/Release%'
        LIMIT 20
        """,
        description="Files that should be ignored"
    )
    print_results(should_be_ignored)

def main():
    analyze_database()

if __name__ == "__main__":
    main()