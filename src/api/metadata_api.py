"""
Metadata API endpoints for querying and managing file metadata.
"""
from fastapi import APIRouter, Body, HTTPException, Depends, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
import pathlib
import os
import db
import watcher
from sqlalchemy.ext.asyncio import AsyncSession

# Create API router
router = APIRouter(
    prefix="/metadata",
    tags=["metadata"],
    responses={404: {"description": "Not found"}}
)

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
    path: str = Field(..., description="Directory path to watch")
    recursive: bool = Field(True, description="Whether to watch subdirectories recursively")

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

@router.post("/watch", response_model=IndexStatusResponse, summary="Watch a directory for changes")
async def watch_directory(data: WatchDirectoryRequest = Body(...)):
    """
    Start watching a directory for file changes.
    The directory will be initially indexed and then monitored for changes.
    """
    try:
        # Normalize path
        directory_path = pathlib.Path(os.path.abspath(data.path))
        
        # Check if directory exists
        if not directory_path.exists() or not directory_path.is_dir():
            raise HTTPException(status_code=404, detail=f"Directory not found: {data.path}")
            
        # Start watching
        await watcher.watch_directory(directory_path)
        
        # Get index status
        indexed_count = 0  # This is an estimate, could query DB for exact count
        
        return IndexStatusResponse(
            indexed_files=indexed_count,
            watched_directories=list(watcher.watched_directories),
            message=f"Successfully started watching directory: {data.path}"
        )
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"Error watching directory: {str(e)}")

@router.post("/unwatch", response_model=IndexStatusResponse, summary="Stop watching a directory")
async def unwatch_directory(data: WatchDirectoryRequest = Body(...)):
    """
    Stop watching a directory for file changes.
    """
    try:
        # Normalize path
        directory_path = pathlib.Path(os.path.abspath(data.path))
        
        # Stop watching
        await watcher.unwatch_directory(directory_path)
        
        return IndexStatusResponse(
            indexed_files=0,  # Not relevant for unwatching
            watched_directories=list(watcher.watched_directories),
            message=f"Successfully stopped watching directory: {data.path}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error unwatching directory: {str(e)}")

@router.post("/reindex", response_model=IndexStatusResponse, summary="Force reindexing of a directory")
async def reindex_directory(data: WatchDirectoryRequest = Body(...)):
    """
    Force reindexing of a directory and all its contents.
    """
    try:
        # Normalize path
        directory_path = pathlib.Path(os.path.abspath(data.path))
        
        # Check if directory exists
        if not directory_path.exists() or not directory_path.is_dir():
            raise HTTPException(status_code=404, detail=f"Directory not found: {data.path}")
            
        # Reindex the directory
        indexed_count = await db.index_directory_recursive(directory_path)
        
        return IndexStatusResponse(
            indexed_files=indexed_count,
            watched_directories=list(watcher.watched_directories),
            message=f"Successfully reindexed directory: {data.path}"
        )
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"Error reindexing directory: {str(e)}")

@router.get("/status", response_model=IndexStatusResponse, summary="Get indexing status")
async def get_index_status():
    """
    Get the current status of the metadata indexing service.
    """
    try:
        # Count indexed files (could be expensive for large databases)
        async with db.async_session() as session:
            result = await session.execute(db.select(db.func.count()).select_from(db.FileMetadata))
            indexed_count = result.scalar_one_or_none() or 0
            
        return IndexStatusResponse(
            indexed_files=indexed_count,
            watched_directories=list(watcher.watched_directories),
            message="Metadata indexing is active"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting indexing status: {str(e)}")

# --- Utility Functions ---

async def get_db_session():
    """Dependency to get a database session."""
    async for session in db.get_db_session():
        yield session