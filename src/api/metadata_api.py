"""
Metadata API endpoints for querying and managing file metadata.
"""
from fastapi import APIRouter, Body, HTTPException, Depends, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Union
from datetime import datetime, timedelta
import pathlib
import os
import logging
from src.db import db
from src.utils import watcher
from sqlalchemy.ext.asyncio import AsyncSession

# Set up logging
logger = logging.getLogger(__name__)

# Create API router
router = APIRouter(
    prefix="/metadata",
    tags=["metadata"],
    responses={404: {"description": "Not found"}}
)

# Function to normalize paths (will be defined by main.py)
# This is just a placeholder that will be replaced
def normalize_path(requested_path: str) -> pathlib.Path:
    """
    Placeholder for normalize_path function that will be defined in main.py.
    This prevents the startup error when main.py tries to assign the real function.
    """
    requested = pathlib.Path(os.path.abspath(requested_path))
    return requested

# --- Pydantic Models ---

class MetadataResponse(BaseModel):
    """Response model for metadata queries."""
    path: str = Field(..., description="Absolute path of the file or directory")
    name: str = Field(..., description="File or directory name")
    extension: Optional[str] = Field(None, description="File extension (None for directories)")
    is_directory: bool = Field(..., description="True if this is a directory")
    size_bytes: Optional[int] = Field(None, description="File size in bytes (None for directories)")
    created_time: Optional[str] = Field(None, description="ISO formatted creation time")
    modified_time: Optional[str] = Field(None, description="ISO formatted modification time")
    last_indexed: Optional[str] = Field(None, description="ISO formatted indexing time")
    mime_type: Optional[str] = Field(None, description="MIME type")

class MetadataSearchRequest(BaseModel):
    """Request model for searching metadata."""
    query: Optional[str] = Field(None, description="Text to search in filenames")
    extensions: Optional[List[str]] = Field(None, description="File extensions to include")
    is_directory: Optional[bool] = Field(None, description="Filter by file or directory")
    min_size: Optional[int] = Field(None, description="Minimum file size in bytes")
    max_size: Optional[int] = Field(None, description="Maximum file size in bytes")
    modified_after: Optional[datetime] = Field(None, description="Files modified after this time")
    modified_before: Optional[datetime] = Field(None, description="Files modified before this time")
    path_prefix: Optional[str] = Field(None, description="Only include files under this path")
    limit: int = Field(100, description="Maximum number of results", ge=1, le=1000)
    offset: int = Field(0, description="Pagination offset", ge=0)

class WatchDirectoryRequest(BaseModel):
    """Request model for watching a directory."""
    path: str = Field(..., description="Directory path to watch for changes")

class UnwatchDirectoryRequest(BaseModel):
    """Request for unwatching a directory."""
    path: str = Field(..., description="Directory path to stop watching")

class ScanDirectoryRequest(BaseModel):
    """Request for scanning a specific directory or all watched directories."""
    path: Optional[str] = Field(None, description="Optional specific directory path to scan. If not provided, all watched directories will be scanned.")
    force: bool = Field(False, description="Force full scan even if last scan was recent")

class DatabaseQueryRequest(BaseModel):
    """Request for executing SQL queries on the metadata database"""
    query: str = Field(..., description="SQL query to execute (SELECT only)")
    params: Optional[Dict[str, Any]] = Field(None, description="Parameters for the SQL query")
    limit: int = Field(1000, description="Maximum number of results to return", ge=1, le=10000)

class PaginatedMetadataResponse(BaseModel):
    """Response model with pagination for metadata queries."""
    items: List[Dict[str, Any]] = Field(..., description="List of metadata items")
    total: int = Field(..., description="Total number of matching items")
    offset: int = Field(..., description="Current pagination offset")
    limit: int = Field(..., description="Maximum items per page")

class IndexStatusResponse(BaseModel):
    """Response model for indexing status."""
    indexed_files: int = Field(..., description="Number of files indexed")
    watched_directories: List[str] = Field(..., description="List of directories being watched")
    message: str = Field(..., description="Status message")

# --- API Endpoints ---

@router.post("/search", response_model=PaginatedMetadataResponse, summary="Search file metadata")
async def search_metadata(data: MetadataSearchRequest = Body(...)):
    """
    Search for files and directories using metadata criteria.
    Results are paginated and can be filtered by various attributes.
    """
    try:
        # Execute search query
        results = await db.search_metadata(
            query=data.query,
            extensions=data.extensions,
            is_directory=data.is_directory,
            min_size=data.min_size,
            max_size=data.max_size,
            modified_after=data.modified_after,
            modified_before=data.modified_before,
            path_prefix=data.path_prefix,
            limit=data.limit + 1,  # Request one extra to check if there are more
            offset=data.offset
        )
        
        # Determine if there are more results
        has_more = len(results) > data.limit
        if has_more:
            results = results[:data.limit]
            
        # Get total count (this might be expensive for large datasets)
        # In a real system, we might want to optimize this or use an estimate
        total_count = len(results) + data.offset
        if has_more:
            total_count += 1  # At least one more
            
        return PaginatedMetadataResponse(
            items=results,
            total=total_count,
            offset=data.offset,
            limit=data.limit
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching metadata: {str(e)}")

@router.get("/path/{path:path}", response_model=Union[MetadataResponse, None], summary="Get metadata for a specific path")
async def get_path_metadata(path: str):
    """
    Get metadata for a specific file or directory path.
    Returns null if the path doesn't exist in the index.
    """
    try:
        # Normalize path
        full_path = os.path.abspath(path)
        
        # Query metadata
        metadata = await db.get_metadata_by_path(full_path)
        
        if metadata:
            return metadata
        return None
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving metadata: {str(e)}")

@router.post("/watch", response_model=Dict[str, Any], summary="Watch a directory for changes")
async def watch_directory(data: WatchDirectoryRequest = Body(...)):
    """
    Start watching a directory for file changes.
    The watcher will automatically update the metadata index when files change in this directory.
    """
    if not hasattr(watcher, 'WATCHER_AVAILABLE') or not hasattr(db, 'DB_PATH'):
        raise HTTPException(
            status_code=501,
            detail="File watcher functionality is not available"
        )
    
    # Normalize path - we'll need access to the normalize_path function from main
    try:
        # First ensure path is absolute (without normalize_path)
        directory_path = pathlib.Path(os.path.abspath(data.path))
        
        # Check if directory exists
        if not directory_path.exists() or not directory_path.is_dir():
            raise HTTPException(status_code=400, detail="Path is not a directory")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
        
    try:
        # Start watching the directory
        await watcher.watch_directory(directory_path)
        
        return {
            "status": "success",
            "message": f"Now watching directory: {data.path}",
            "watched_directory_count": len(watcher.watched_directories)
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to watch directory: {str(e)}"
        )

@router.post("/unwatch", response_model=Dict[str, Any], summary="Stop watching a directory")
async def unwatch_directory(data: UnwatchDirectoryRequest = Body(...)):
    """
    Stop watching a directory for file changes.
    """
    if not hasattr(watcher, 'WATCHER_AVAILABLE'):
        raise HTTPException(
            status_code=501,
            detail="File watcher functionality is not available"
        )
    
    try:
        # Normalize path - using absolute path for now
        directory_path = pathlib.Path(os.path.abspath(data.path))
        
        # Check if directory is currently being watched
        if str(directory_path) not in watcher.watched_directories:
            return {
                "status": "warning",
                "message": f"Directory {data.path} was not being watched"
            }
            
        # Stop watching the directory
        await watcher.unwatch_directory(directory_path)
        
        return {
            "status": "success",
            "message": f"Stopped watching directory: {data.path}",
            "watched_directory_count": len(watcher.watched_directories)
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to stop watching directory: {str(e)}"
        )

@router.post("/reindex", response_model=Dict[str, Any], summary="Force reindexing of a directory")
async def reindex_directory(data: WatchDirectoryRequest = Body(...)):
    """
    Force reindexing of a directory and all its contents.
    With no file limit for comprehensive indexing.
    """
    if not hasattr(db, 'DB_PATH'):
        raise HTTPException(status_code=501, detail="Metadata API is not available")
    
    # Normalize path - using absolute path for now
    try:
        directory_path = pathlib.Path(os.path.abspath(data.path))
        
        # Check if directory exists
        if not directory_path.exists() or not directory_path.is_dir():
            raise HTTPException(status_code=400, detail="Path is not a directory")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
        
    try:
        # Index the specified directory with no file limit
        logger.info(f"Starting unlimited indexing of directory: {data.path}")
        count = await db.index_directory_recursive(directory_path, max_files=None)
            
        return {
            "status": "success", 
            "message": f"Successfully indexed directory: {data.path}",
            "file_count": count
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to index directory: {str(e)}"
        )

@router.post("/scan", response_model=Dict[str, Any], summary="Trigger manual scan of watched directories")
async def scan_watched_directories(data: ScanDirectoryRequest = Body(...)):
    """
    Manually trigger a scan of watched directories to update the metadata index.
    Useful when you've made changes outside the API and want to update the index immediately.
    """
    if not hasattr(watcher, 'WATCHER_AVAILABLE'):
        raise HTTPException(
            status_code=501,
            detail="File watcher functionality is not available"
        )
    
    try:
        scanned_dirs = []
        
        # If a specific path is provided
        if data.path:
            try:
                # Use absolute path as normalize_path is in main.py
                dir_path = pathlib.Path(os.path.abspath(data.path))
                dir_str = str(dir_path)
                
                # Check if directory is being watched
                if dir_str not in watcher.watched_directories:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Directory {data.path} is not currently being watched. Use /watch first."
                    )
                
                # Force update of last scan time if needed
                if data.force:
                    # Set last scan time to a long time ago
                    watcher.last_scan_times[dir_str] = datetime.now() - timedelta(days=1)
                    
                # Manually trigger directory scan
                await watcher._scan_directories()
                
                # Also process any pending changes
                await watcher._process_modified_paths()
                
                scanned_dirs.append(dir_str)
            except Exception as e:
                if isinstance(e, HTTPException):
                    raise e
                raise HTTPException(
                    status_code=500,
                    detail=f"Error scanning directory {data.path}: {str(e)}"
                )
        else:
            # Scan all watched directories
            if not watcher.watched_directories:
                return {
                    "status": "warning",
                    "message": "No directories are currently being watched"
                }
                
            # Force update all last scan times if needed
            if data.force:
                old_time = datetime.now() - timedelta(days=1)
                for dir_str in watcher.watched_directories:
                    watcher.last_scan_times[dir_str] = old_time
            
            # Trigger scan
            await watcher._scan_directories()
            
            # Process any pending changes
            await watcher._process_modified_paths()
            
            scanned_dirs = list(watcher.watched_directories)
            
        return {
            "status": "success",
            "message": f"Successfully scanned {len(scanned_dirs)} directories",
            "scanned_directories": scanned_dirs
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error scanning directories: {str(e)}"
        )

@router.get("/status", response_model=Dict[str, Any], summary="Get file watcher status")
async def watcher_status():
    """
    Get the current status of the file watcher system.
    Shows which directories are being watched, when they were last scanned,
    and if the watcher is actively running.
    """
    if not hasattr(watcher, 'WATCHER_AVAILABLE'):
        raise HTTPException(
            status_code=501,
            detail="File watcher functionality is not available"
        )
        
    try:
        # Get watched directories and their last scan times
        watched_dirs = list(watcher.watched_directories)
        
        # Format timestamps to be readable
        last_scans = {}
        for dir_path in watched_dirs:
            last_scan_time = watcher.last_scan_times.get(dir_path)
            if last_scan_time:
                time_diff = datetime.now() - last_scan_time
                last_scans[dir_path] = {
                    "timestamp": last_scan_time.isoformat(),
                    "seconds_ago": int(time_diff.total_seconds()),
                    "next_scan_in": max(0, int(watcher.SCAN_INTERVAL - time_diff.total_seconds()))
                }
            else:
                last_scans[dir_path] = None
        
        # Get information about modified paths awaiting processing
        pending_changes = len(watcher.modified_paths)
        pending_queue = len(watcher.path_change_queue) if hasattr(watcher, 'path_change_queue') else 0
        
        return {
            "status": "active" if watcher.watcher_running else "inactive",
            "watched_directories": watched_dirs,
            "directory_count": len(watched_dirs),
            "last_scans": last_scans,
            "scan_interval_seconds": watcher.SCAN_INTERVAL,
            "pending_changes": pending_changes,
            "pending_queue": pending_queue,
            "batch_size": watcher.BATCH_SIZE
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error getting watcher status: {str(e)}"
        )

@router.post("/database_query", summary="Execute a database query")
async def database_query(request: DatabaseQueryRequest = Body(...)):
    """
    Execute a query on the metadata database.
    
    Only SELECT queries are allowed for security reasons.
    Results are limited to prevent excessive memory usage.
    
    Query examples:
    
    1. Get all files with a specific extension:
    ```
    SELECT * FROM file_metadata WHERE extension = '.py' LIMIT 100
    ```
    
    2. Find the largest files:
    ```
    SELECT path FROM file_metadata 
    WHERE is_directory = 0 
    ORDER BY size_bytes DESC LIMIT 20
    ```
    
    3. Get files modified in the last day:
    ```
    SELECT path FROM file_metadata 
    WHERE modified_time > datetime('now', '-1 day')
    LIMIT 100
    ```
    
    4. Count files by extension:
    ```
    SELECT extension, COUNT(*) as count 
    FROM file_metadata 
    WHERE extension IS NOT NULL 
    GROUP BY extension 
    ORDER BY count DESC
    ```
    
    5. Find directories with the most files:
    ```
    SELECT parent_dir, COUNT(*) as file_count
    FROM file_metadata
    GROUP BY parent_dir
    ORDER BY file_count DESC
    LIMIT 20
    ```
    """
    if not hasattr(db, 'DB_PATH'):
        raise HTTPException(
            status_code=501,
            detail="Metadata database is not available"
        )
    
    query = request.query.strip()
    
    # Security check - only allow SELECT queries
    if not query.lower().startswith("select"):
        raise HTTPException(
            status_code=403,
            detail="Only SELECT queries are allowed for security reasons"
        )
        
    # Check for dangerous keywords that might bypass our security
    dangerous_keywords = ["insert", "update", "delete", "drop", "alter", "create", 
                          "pragma", "attach", "detach", "vacuum", ";"]
    
    for keyword in dangerous_keywords:
        if keyword.lower() in query.lower():
            raise HTTPException(
                status_code=403,
                detail=f"Query contains disallowed keyword: {keyword}"
            )
    
    # Add LIMIT clause if not present
    if "limit " not in query.lower():
        if query.lower().endswith(";"):
            query = query[:-1]  # Remove trailing semicolon
        query = f"{query} LIMIT {request.limit}"
    else:
        # If LIMIT is already present, ensure it doesn't exceed our max
        import re
        limit_pattern = re.compile(r'limit\s+(\d+)', re.IGNORECASE)
        match = limit_pattern.search(query)
        if match:
            try:
                limit_value = int(match.group(1))
                if limit_value > request.limit:
                    # Replace with our limit
                    query = limit_pattern.sub(f"LIMIT {request.limit}", query)
            except ValueError:
                pass
    
    try:
        import time
        start_time = time.time()
        
        # Use SQLite's built-in connection for simplicity
        import sqlite3
        import json
        
        # Get the database path from our module
        db_path = db.DB_PATH
        
        # Connect to the database directly
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row  # This allows us to access columns by name
        
        # Execute the query
        cursor = conn.cursor()
        if request.params:
            cursor.execute(query, request.params)
        else:
            cursor.execute(query)
        
        # Get the results
        rows = []
        for row in cursor.fetchall():
            # Convert sqlite3.Row to dict
            row_dict = {key: row[key] for key in row.keys()}
            rows.append(row_dict)
        
        # Close the connection
        conn.close()
        
        execution_time = time.time() - start_time
        
        return {
            "status": "success",
            "rows": rows,
            "row_count": len(rows),
            "execution_time_ms": int(execution_time * 1000),
            "query": query
        }
    except sqlite3.Error as e:
        raise HTTPException(
            status_code=500,
            detail=f"SQLite error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database query error: {str(e)}"
        )

# Note: Database reset functionality is intentionally not exposed through the API
# Users must access the container directly and use the reset_db.py utility script

# --- Utility Functions ---

async def get_db_session():
    """Dependency to get a database session."""
    async for session in db.get_db_session():
        yield session