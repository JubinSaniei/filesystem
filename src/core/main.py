from fastapi import FastAPI, HTTPException, Body
from fastapi.responses import PlainTextResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from pydantic import BaseModel, Field
import os
import pathlib
import asyncio
import aiofiles
from typing import List, Optional, Literal, Union, Dict, Any
import difflib
import shutil
from datetime import datetime, timezone
import functools
import threading
from concurrent.futures import ThreadPoolExecutor
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
import time
from datetime import timedelta
import re
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import database and watcher modules properly
try:
    from src.db import db
    METADATA_API_AVAILABLE = True
    from src.utils import watcher
    WATCHER_AVAILABLE = True
except ImportError:
    METADATA_API_AVAILABLE = False
    WATCHER_AVAILABLE = False
    
# Import ignore pattern functionality
try:
    from src.utils import ignore_patterns
    IGNORE_PATTERNS_AVAILABLE = True
except ImportError:
    IGNORE_PATTERNS_AVAILABLE = False
    
# Import metadata API router
try:
    from src.api import metadata_api
    METADATA_API_ROUTER_AVAILABLE = True
except ImportError:
    METADATA_API_ROUTER_AVAILABLE = False

# Constants
ALLOWED_DIRECTORIES = [
    "/mnt/c/Sandboxes",
    "/app/testdir"  # Add our test directory
]  # 👈 Replace with your paths

# Pre-compute resolved allowed paths
ALLOWED_PATHS = [pathlib.Path(path).resolve() for path in ALLOWED_DIRECTORIES]

# Configure thread pool for CPU-bound operations with proper cleanup
# Use a more conservative number of workers to prevent system overload
THREAD_POOL = ThreadPoolExecutor(max_workers=10)

# File content cache with 100 MB max size, per file limit 10 MB
FILE_CACHE_MAX_ENTRIES = 100
FILE_CACHE_MAX_SIZE = 100 * 1024 * 1024  # 100 MB
FILE_CACHE_ENTRY_MAX_SIZE = 10 * 1024 * 1024  # 10 MB
file_cache: Dict[str, Dict[str, Any]] = {}
file_cache_size = 0

# Thread lock for cache operations to ensure thread safety
cache_lock = threading.RLock()

# Last cache cleanup time
last_cache_cleanup = datetime.now().timestamp()
CACHE_CLEANUP_INTERVAL = 300  # seconds (5 minutes)

# Try to import psutil at module level
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

# Define lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for the application.
    Handles startup and shutdown events.
    """
    # === Startup operations ===
    print(f"Starting Secure Filesystem API (v0.1.0)")
    print(f"Allowed directories: {ALLOWED_DIRECTORIES}")
    print(f"Cache size: {FILE_CACHE_MAX_SIZE / (1024*1024):.1f} MB")
    print(f"Thread pool workers: {THREAD_POOL._max_workers}")
    
    # Verify allowed directories exist and are accessible
    for directory in ALLOWED_DIRECTORIES:
        path = pathlib.Path(directory)
        try:
            if not path.exists() or not path.is_dir():
                print(f"WARNING: Allowed directory '{directory}' does not exist or is not a directory")
            elif not os.access(path, os.R_OK):
                print(f"WARNING: Allowed directory '{directory}' is not readable")
        except Exception as e:
            print(f"ERROR checking allowed directory '{directory}': {e}")
    
    # Initialize metadata database at startup
    if METADATA_API_AVAILABLE:
        try:
            print("Initializing metadata database...")
            await db.initialize_database()
            print("Metadata database initialized")
            
            # Wait a moment to ensure the database is ready
            await asyncio.sleep(1)
        except Exception as e:
            print(f"WARNING: Failed to initialize metadata database: {e}")
    
    # Initialize ignore patterns
    if IGNORE_PATTERNS_AVAILABLE:
        try:
            print("Loading ignore patterns...")
            matcher = ignore_patterns.get_matcher()
            pattern_count = len(matcher.patterns)
            print(f"Loaded {pattern_count} ignore patterns from {matcher.ignore_file}")
        except Exception as e:
            print(f"WARNING: Failed to load ignore patterns: {e}")
            
    # Initialize file watcher system but don't watch any directories by default
    if METADATA_API_AVAILABLE and WATCHER_AVAILABLE:
        try:
            print("Initializing file watcher system...")
            # Initialize watcher with empty list (no directories watched by default)
            await watcher.initialize_watcher([])
            print("File watcher system initialized - no directories being watched by default")
        except Exception as e:
            print(f"WARNING: Failed to initialize file watcher: {e}")
    
    # Start the application
    print("Application ready")
    yield
    
    # === Shutdown operations ===
    try:
        # Stop the file watcher if it was started
        if WATCHER_AVAILABLE:
            try:
                print("Stopping file watcher...")
                await watcher.cleanup_watcher()
                print("File watcher stopped")
            except Exception as e:
                print(f"Error stopping file watcher: {e}")
        
        # Close the database connection if it was opened
        if METADATA_API_AVAILABLE:
            try:
                print("Closing database connections...")
                await db.close_database()
            except Exception as e:
                print(f"Error closing database: {e}")
        
        # Clear the cache
        with cache_lock:
            file_cache.clear()
        
        # Shutdown the thread pool
        try:
            THREAD_POOL.shutdown(wait=True, cancel_futures=True)
        except (AttributeError, TypeError):
            # Fallback for older Python versions without cancel_futures
            THREAD_POOL.shutdown(wait=True)
            
        # Clear the path cache
        normalize_path.cache_clear()
        
        print("Application shutdown complete")
    except Exception as e:
        print(f"Error during shutdown: {e}")
        # Even if we have an error, try to shutdown the thread pool
        try:
            THREAD_POOL.shutdown(wait=False)
        except:
            pass

# Metadata API availability was already set up at the top of the file

# Import OpenAPI enhancer
from src.utils.openapi_enhancer import enhance_openapi_schema
from src.utils.nl_mapping import nl_mapping, COMMON_PATHS, COMMON_PARAMETER_MAPPINGS

# Initialize FastAPI app with lifespan
app = FastAPI(
    title="Secure Filesystem API",
    version="0.1.0",
    description="""
    A secure file manipulation server for reading, editing, writing, listing, and searching files with access restrictions.
    
    ## Dependencies
    
    - Python 3.10+
    - FastAPI 0.100.0+
    - aiofiles 23.1.0+
    - pydantic 2.0.0+
    - uvicorn[standard]
    - sqlalchemy 2.0.0+ (for metadata indexing)
    - aiosqlite 0.19.0+ (for async database operations)
    - psutil (optional, for improved performance monitoring)
    
    ## Performance Features
    
    - Asynchronous file operations with aiofiles
    - In-memory file caching with thread-safe access
    - Concurrent processing with ThreadPoolExecutor
    - Streaming responses for large files
    - Intelligent pagination for search results
    - SQLite metadata indexing for fast file searches
    - File system watcher for real-time metadata updates
    
    ## Natural Language Support
    
    This API supports natural language interactions through AI systems. The API endpoints
    have been enhanced with natural language mappings that help AI systems translate user
    queries into the appropriate API calls. For more information, see the
    [Natural Language Mapping Guide](src/docs/NATURAL_LANGUAGE_MAPPING.md).
    """,
    lifespan=lifespan
)

# Enhance the OpenAPI schema with natural language mappings
enhance_openapi_schema(app)

# Required implementation of normalize_path function (moved up from below)
@functools.lru_cache(maxsize=1024)
def normalize_path(requested_path: str) -> pathlib.Path:
    """
    Resolves the requested path and verifies it is within one of the allowed directories.
    This function is cached for better performance on repeated access.
    """
    requested = pathlib.Path(os.path.expanduser(requested_path)).resolve()
    for allowed_path in ALLOWED_PATHS:
        try:
            requested.relative_to(allowed_path)
            return requested
        except ValueError:
            continue
    raise HTTPException(
        status_code=403,
        detail={
            "error": "Access Denied",
            "requested_path": str(requested),
            "message": "Requested path is outside allowed directories.",
            "allowed_directories": ALLOWED_DIRECTORIES,
        },
    )

# Include the metadata API router if available
if METADATA_API_ROUTER_AVAILABLE:
    # Make the normalize_path function available to the router
    metadata_api.normalize_path = normalize_path
    # Include the router
    app.include_router(metadata_api.router)
    print("Metadata API router included")

# Other endpoints are now defined in the metadata_api module and included via the router above

# We need to add the rest of the original file here
# For simplicity, we'll just stub in a basic implementation
# This would normally be the rest of the main.py file

# normalize_path function moved above before the router inclusion

def cleanup_cache() -> None:
    """
    Periodically clean up the cache:
    1. Remove stale entries
    2. Check if cached files still exist
    3. Enforce size limits
    """
    global file_cache, file_cache_size, last_cache_cleanup
    
    with cache_lock:
        current_time = datetime.now().timestamp()
        
        # Only run cleanup occasionally to avoid excessive disk I/O
        if current_time - last_cache_cleanup < CACHE_CLEANUP_INTERVAL:
            return
        
        last_cache_cleanup = current_time
        paths_to_remove = []
        
        # Check all entries
        for path, entry in file_cache.items():
            file_path = pathlib.Path(path)
            
            # Check if file still exists
            if not file_path.exists():
                paths_to_remove.append(path)
                continue
                
            # Check if file has been modified
            try:
                current_modified_time = file_path.stat().st_mtime
                if current_modified_time > entry['modified_time']:
                    paths_to_remove.append(path)
                    continue
            except (FileNotFoundError, PermissionError):
                paths_to_remove.append(path)
                continue
                
            # Optional: remove entries not accessed for a long time (1 hour)
            if current_time - entry['last_access'] > 3600:
                paths_to_remove.append(path)
        
        # Remove invalid entries
        for path in paths_to_remove:
            content_size = file_cache[path]['size']
            del file_cache[path]
            file_cache_size -= content_size

def add_to_file_cache(path: str, content: str, modified_time: float) -> bool:
    """
    Add a file to the cache if it meets size criteria.
    Returns True if added, False otherwise.
    Thread-safe with lock protection.
    """
    global file_cache, file_cache_size
    
    content_size = len(content.encode('utf-8'))
    
    # Check if file is too large for cache
    if content_size > FILE_CACHE_ENTRY_MAX_SIZE:
        return False
    
    with cache_lock:
        # Periodically clean up the cache
        cleanup_cache()
        
        # If cache is full, remove least recently used entries
        while (len(file_cache) >= FILE_CACHE_MAX_ENTRIES or 
               file_cache_size + content_size > FILE_CACHE_MAX_SIZE) and file_cache:
            # Find oldest entry - combine recency and frequency for better eviction
            # (Time since last access × 1/access count) gives a weighted score
            oldest_path = min(
                file_cache.items(), 
                key=lambda x: (datetime.now().timestamp() - x[1]['last_access']) * (1 / (x[1].get('access_count', 1)))
            )[0]
            removed_size = file_cache[oldest_path]['size']
            del file_cache[oldest_path]
            file_cache_size -= removed_size
        
        # Add to cache
        file_cache[path] = {
            'content': content,
            'modified_time': modified_time,
            'last_access': datetime.now().timestamp(),
            'size': content_size,
            'access_count': 1
        }
        file_cache_size += content_size
        return True

def get_from_file_cache(path: str, modified_time: float) -> Optional[str]:
    """
    Get file content from cache if available and not modified.
    Returns None if not in cache or if cached version is stale.
    Thread-safe with lock protection.
    """
    global file_cache, file_cache_size
    
    with cache_lock:
        if path in file_cache:
            # Check if file has been modified since cached
            if file_cache[path]['modified_time'] >= modified_time:
                # Update access time and increment access count
                file_cache[path]['last_access'] = datetime.now().timestamp()
                file_cache[path]['access_count'] = file_cache[path].get('access_count', 1) + 1
                return file_cache[path]['content']
            
            # Remove stale entry
            content_size = file_cache[path]['size']
            del file_cache[path]
            file_cache_size -= content_size
        
        return None

def invalidate_cache_for_path(path: str) -> None:
    """
    Remove a specific path from the cache after modification.
    Also invalidates parent directory paths for moved/renamed files.
    Thread-safe with lock protection.
    """
    global file_cache, file_cache_size
    
    with cache_lock:
        # Exact path match
        if path in file_cache:
            content_size = file_cache[path]['size']
            del file_cache[path]
            file_cache_size -= content_size
            
        # Also check for moved files by removing paths that start with the directory path
        # This is for when a directory is moved or renamed
        path_with_slash = f"{path}/"
        paths_to_remove = [p for p in file_cache if p.startswith(path_with_slash)]
        
        for p in paths_to_remove:
            content_size = file_cache[p]['size']
            del file_cache[p]
            file_cache_size -= content_size

def secure_get_file_size(file_path):
    """
    Safely get a file size without following symlinks.
    Only returns size for files within allowed directories.
    
    Args:
        file_path: Path to check
        
    Returns:
        File size in bytes or raises an exception
    """
    # Convert to pathlib.Path if it's a string
    if isinstance(file_path, str):
        file_path = pathlib.Path(file_path)
    
    # Verify path is within allowed directories
    valid_path = False
    for allowed_path in ALLOWED_PATHS:
        try:
            file_path.relative_to(allowed_path)
            valid_path = True
            break
        except ValueError:
            continue
    
    if not valid_path:
        raise PermissionError(f"Path {file_path} is outside allowed directories")
        
    # Check that the file exists and is a regular file (not a symlink, etc.)
    if not file_path.exists():
        raise FileNotFoundError(f"File {file_path} not found")
    
    if not file_path.is_file():
        raise ValueError(f"Path {file_path} is not a regular file")
    
    # Get file stat without following symlinks
    stat_result = file_path.stat()
    return stat_result.st_size

# Helper function to run tasks in the thread pool
async def run_in_threadpool(func, *args, **kwargs):
    """
    Run a function in the thread pool and await its result.
    This centralizes thread pool usage for better resource management.
    """
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        THREAD_POOL, 
        lambda: func(*args, **kwargs)
    )

# Configure CORS middleware for cross-origin requests
# This is crucial for allowing web UIs to access our API
# Rate limiting middleware
class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, limit=100, window=60):
        super().__init__(app)
        self.limit = limit  # requests per window
        self.window = window  # window in seconds
        self.requests = {}
        self.lock = threading.RLock()
        
    async def dispatch(self, request: Request, call_next):
        # Get client IP
        client_ip = request.client.host if request.client else "unknown"
        
        # Check if rate limit exceeded
        with self.lock:
            now = time.time()
            # Clean up old requests
            self.requests = {ip: [ts for ts in timestamps if now - ts < self.window] 
                            for ip, timestamps in self.requests.items()}
            
            # Check current client's request count
            client_requests = self.requests.get(client_ip, [])
            
            if len(client_requests) >= self.limit:
                return Response(
                    content={"detail": "Rate limit exceeded. Try again later."}, 
                    status_code=429,
                    media_type="application/json"
                )
            
            # Add current request timestamp
            client_requests.append(now)
            self.requests[client_ip] = client_requests
        
        # Process the request
        return await call_next(request)

# Performance monitoring middleware
@app.middleware("http")
async def add_performance_headers(request, call_next):
    start_time = datetime.now()
    memory_before = 0
    
    if PSUTIL_AVAILABLE:
        memory_before = psutil.Process().memory_info().rss
        
    response = await call_next(request)
    process_time = (datetime.now() - start_time).total_seconds()
    
    # Add processing time to response headers
    response.headers["X-Process-Time"] = str(process_time)
    
    # Track memory usage if psutil is available
    if PSUTIL_AVAILABLE:
        memory_after = psutil.Process().memory_info().rss
        memory_diff = memory_after - memory_before
        memory_mb = memory_diff / (1024 * 1024)
        
        if memory_mb > 10:  # Log if memory increase is over 10MB
            logger.info(f"HIGH MEMORY USAGE: {request.method} {request.url.path} - {memory_mb:.2f}MB")
            
        response.headers["X-Memory-Usage-MB"] = f"{memory_mb:.2f}"
    
    # Log slow operations (more than 1 second)
    if process_time > 1.0:
        logger.info(f"SLOW OPERATION: {request.method} {request.url.path} - {process_time:.4f}s")
    
    return response

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins, or specify exact origins like "http://172.31.79.51:8080"
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)

# Rate limit middleware (disabled by default, uncomment to enable)
# app.add_middleware(RateLimitMiddleware, limit=100, window=60)

@app.get("/", 
    summary="API information",
    description="""
    Get basic information about the API.
    
    ## Natural Language Queries
    - "What is this API?"
    - "Tell me about this server"
    - "What can you do?"
    - "What are you?"
    - "How do I use this API?"
    """,
    openapi_extra=nl_mapping(
        queries=[
            "what is this api",
            "tell me about this server",
            "what can you do",
            "what are you",
            "how do i use this api"
        ],
        response_template="I'm a filesystem API that allows you to read, write, edit, and search files and directories."
    )
)
def root():
    """Root endpoint returns basic info"""
    return {"message": "Filesystem API with Database Query Support"}

# ------------------------------------------------------------------------------
# Pydantic Schemas
# ------------------------------------------------------------------------------

class ReadFileRequest(BaseModel):
    path: str = Field(..., description="Path to the file to read")
    stream: bool = Field(default=False, description="If true, stream the file content instead of loading it all in memory")
    chunk_size: int = Field(default=8192, description="Chunk size for streaming in bytes", ge=1024, le=1024*1024)


class WriteFileRequest(BaseModel):
    path: str = Field(..., description="Path to write to. Existing file will be overwritten, appended, or prepended based on mode.")
    content: str = Field(..., description="UTF-8 encoded text content to write.")
    mode: str = Field("overwrite", description="Write mode: 'overwrite' (default), 'append', or 'prepend'")


class EditOperation(BaseModel):
    oldText: str = Field(..., description="Text to find and replace (exact match required)")
    newText: str = Field(..., description="Replacement text")


class EditFileRequest(BaseModel):
    path: str = Field(..., description="Path to the file to edit.")
    edits: List[EditOperation] = Field(..., description="List of edits to apply.")
    dryRun: bool = Field(False, description="If true, only return diff without modifying file.")


class CreateDirectoryRequest(BaseModel):
    path: str = Field(
        ...,
        description="Directory path to create. Intermediate dirs are created automatically.",
    )


class ListDirectoryRequest(BaseModel):
    path: str = Field(..., description="Directory path to list contents for.")


class PaginationParams(BaseModel):
    offset: int = Field(default=0, description="Pagination offset", ge=0)
    limit: int = Field(default=100, description="Maximum number of results to return", ge=1, le=1000)


class DirectoryTreeRequest(BaseModel):
    path: str = Field(..., description="Directory path for which to return recursive tree.")
    max_depth: int = Field(default=5, description="Maximum recursion depth", ge=1, le=20)
    include_hidden: bool = Field(default=False, description="Whether to include hidden files and directories")


class SuccessResponse(BaseModel):
    message: str = Field(..., description="Success message indicating the operation was completed.")


class ReadFileResponse(BaseModel):
    content: str = Field(..., description="UTF-8 encoded text content of the file.")


class DiffResponse(BaseModel):
    diff: str = Field(..., description="Unified diff output comparing original and modified content.")
    
class PaginatedResponse(BaseModel):
    items: List[Any] = Field(..., description="List of items in the current page")
    total: int = Field(..., description="Total number of items available")
    offset: int = Field(..., description="Current offset in the result set")
    limit: int = Field(..., description="Maximum number of items per page")
    
class SearchContentResponse(PaginatedResponse):
    errors: List[Dict[str, str]] = Field(default_factory=list, description="List of errors encountered during search")
    stats: Dict[str, Any] = Field(default_factory=dict, description="Statistics about the search operation")

class SearchContentRequest(BaseModel):
    path: str = Field(..., description="Base directory to search within.")
    search_query: str = Field(..., description="Text content to search for (case-insensitive).")
    recursive: bool = Field(default=True, description="Whether to search recursively in subdirectories.")
    file_pattern: Optional[str] = Field(default="*", description="Glob pattern to filter files to search within (e.g., '*.py').")
    pagination: Optional[PaginationParams] = Field(default_factory=PaginationParams, description="Pagination parameters")

class DeletePathRequest(BaseModel):
    path: str = Field(..., description="Path to the file or directory to delete.")
    recursive: bool = Field(default=False, description="If true and path is a directory, delete recursively. Required if directory is not empty.")
    confirm_delete: bool = Field(..., description="Must be explicitly set to true to confirm deletion.")

class MovePathRequest(BaseModel):
    source_path: str = Field(..., description="The current path of the file or directory.")
    destination_path: str = Field(..., description="The new path for the file or directory.")

class GetMetadataRequest(BaseModel):
    path: str = Field(..., description="Path to the file or directory to get metadata for.")

class MetadataSearchRequest(BaseModel):
    """Request model for searching file metadata."""
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
    
# ------------------------------------------------------------------------------
# File Operations
# ------------------------------------------------------------------------------

def search_file_content(file_path, search_query_lower, max_results=1000):
    """
    Search a single file for the given query.
    This function is run in a thread pool to parallelize IO-bound operations.
    Note: This is a synchronous function that will be run in a separate thread.
    
    Args:
        file_path: Path to the file to search
        search_query_lower: Lowercase search query to find
        max_results: Maximum number of results to return per file
    
    Returns:
        List of results with file path, line number, and content
    """
    results = []
    error = None
    
    try:
        # Skip very large files to avoid out-of-memory issues
        try:
            file_size = secure_get_file_size(file_path)
            if file_size > 100 * 1024 * 1024:  # Skip files larger than 100MB
                return [{
                    "file_path": str(file_path),
                    "skipped": True,
                    "reason": f"File too large ({file_size / (1024*1024):.2f} MB)"
                }]
        except Exception as e:
            return [{
                "file_path": str(file_path),
                "error": f"Error checking file size: {str(e)}"
            }]
            
        # Check if file is likely binary based on extension
        if pathlib.Path(file_path).suffix.lower() in ('.exe', '.dll', '.bin', '.zip', '.tar', '.gz', 
                                                     '.jpg', '.jpeg', '.png', '.gif', '.mp3', '.mp4'):
            return [{
                "file_path": str(file_path),
                "skipped": True,
                "reason": "Binary file (by extension)"
            }]
        
        # Use aiofiles-compatible opening method but in sync mode for threadpool
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                # Check first few bytes for binary content
                try:
                    first_chunk = f.read(1024)
                    # If more than 10% of the first 1024 bytes are null or control chars, likely binary
                    null_count = sum(1 for c in first_chunk if c == '\0' or ord(c) < 32 and c not in '\r\n\t')
                    if null_count > 100:  # 10% threshold
                        return [{
                            "file_path": str(file_path),
                            "skipped": True,
                            "reason": "Binary file (content check)"
                        }]
                    
                    # Reset file pointer
                    f.seek(0)
                except Exception:
                    # If we can't check for binary content, continue anyway
                    f.seek(0)
                
                for line_num, line in enumerate(f, 1):
                    if search_query_lower in line.lower():
                        results.append({
                            "file_path": str(file_path),
                            "line_number": line_num,
                            "line_content": line.strip(),
                        })
                        
                        # Limit results per file to avoid excessive memory usage
                        if len(results) >= max_results:
                            results.append({
                                "file_path": str(file_path),
                                "truncated": True,
                                "message": f"Results truncated at {max_results} matches"
                            })
                            break
        except UnicodeDecodeError:
            return [{
                "file_path": str(file_path),
                "skipped": True,
                "reason": "Binary file or encoding error"
            }]
    except UnicodeDecodeError:
        error = "Binary file or encoding error"
    except PermissionError:
        error = "Permission denied"
    except FileNotFoundError:
        error = "File not found (deleted during search)"
    except Exception as e:
        error = f"Error: {str(e)}"
        
    if error and not results:
        results.append({
            "file_path": str(file_path),
            "error": error
        })
        
    return results

async def file_streamer(file_path, chunk_size, text_mode=False):
    """
    Generator function that yields chunks of a file.
    For text files, text_mode should be True to handle encoding properly.
    
    Args:
        file_path: Path to the file to stream
        chunk_size: Size of each chunk to read
        text_mode: Whether to read as text (True) or binary (False)
    """
    # Ensure path is secure - this is a defensive measure in case it wasn't checked by the caller
    if isinstance(file_path, str):
        file_path = pathlib.Path(file_path)
        
    # Additional security check - path should be within allowed directories 
    valid_path = False
    for allowed_path in ALLOWED_PATHS:
        try:
            file_path.relative_to(allowed_path)
            valid_path = True
            break
        except ValueError:
            continue
            
    if not valid_path:
        raise PermissionError(f"Path {file_path} is outside allowed directories")
        
    # Set correct mode based on file type
    mode = 'r' if text_mode else 'rb'
    encoding = 'utf-8' if text_mode else None
    errors = 'replace' if text_mode else None
    
    # Stream the file in chunks
    async with aiofiles.open(file_path, mode=mode, encoding=encoding, errors=errors) as f:
        while True:
            chunk = await f.read(chunk_size)
            if not chunk:
                break
            
            # For text mode, we need to encode the text before yielding
            if text_mode:
                yield chunk.encode('utf-8')
            else:
                yield chunk

@app.post(
    "/read_file", 
    response_model=ReadFileResponse, 
    summary="Read a file", 
    response_model_exclude_none=True,
    description="""
    Read the contents of a file and return as JSON or stream for large files.
    Uses caching for better performance and async file operations.
    Includes improved security checks and error handling.
    
    ## Natural Language Queries
    - "Show me the contents of [file]"
    - "What's in [file]?"
    - "Read [file]"
    - "Display the content of [file]"
    - "Open [file]"
    - "Show [file]"
    - "Let me see [file]"
    """,
    openapi_extra=nl_mapping(
        queries=[
            "show me the contents of file",
            "what's in file",
            "read file",
            "display the content of file",
            "open file",
            "show file",
            "let me see file"
        ],
        parameter_mappings={
            "path": ["file", "document", "text file", "path"],
            "stream": ["stream", "download", "continuously"]
        },
        response_template="Here's the content of {file_name}:\n\n{content}",
        common_paths=COMMON_PATHS
    )
)
async def read_file(data: ReadFileRequest = Body(...)):
    """
    Read the contents of a file and return as JSON or stream for large files.
    Uses caching for better performance and async file operations.
    Includes improved security checks and error handling.
    """
    path = normalize_path(data.path)
    path_str = str(path)
    
    try:
        # Verify path exists and is a file
        if not path.exists():
            raise FileNotFoundError(f"File not found: {data.path}")
            
        if not path.is_file():
            raise ValueError(f"Path is not a file: {data.path}")
            
        try:
            # Get file metadata without following symlinks for security
            stat_result = path.stat()
            modified_time = stat_result.st_mtime
            file_size = stat_result.st_size
        except (PermissionError, OSError) as e:
            # Handle specific file stat errors
            raise PermissionError(f"Cannot access file metadata: {str(e)}")
        
        # Use streaming response for large files if requested
        if data.stream:
            # Skip cache for streaming, but perform security checks
            if file_size > 500 * 1024 * 1024:  # 500MB limit for streaming
                raise HTTPException(
                    status_code=413, 
                    detail=f"File too large for streaming: {file_size / (1024*1024):.2f} MB (max 500MB)"
                )
                
            headers = {
                "Content-Disposition": f"attachment; filename={path.name}",
                "Content-Length": str(file_size)
            }
            
            # Set appropriate content type based on file extension
            is_text_file = path.suffix.lower() in ('.txt', '.md', '.py', '.js', '.css', '.html', '.json', '.xml')
            if is_text_file:
                headers["Content-Type"] = "text/plain; charset=utf-8"
            else:
                headers["Content-Type"] = "application/octet-stream"
                
            # Use the secure streamer which does additional checks
            return StreamingResponse(
                file_streamer(path, data.chunk_size, text_mode=is_text_file),
                headers=headers
            )
        
        # For normal file reads, use caching with locks
        with cache_lock:
            # Check cache first
            cached_content = get_from_file_cache(path_str, modified_time)
            if cached_content is not None:
                return ReadFileResponse(content=cached_content)
        
        # Not in cache, read from disk
        try:
            async with aiofiles.open(path, mode='r', encoding='utf-8', errors='replace') as file:
                file_content = await file.read()
        except UnicodeDecodeError:
            # Binary file but not streaming mode requested
            raise HTTPException(
                status_code=400, 
                detail="File appears to be binary. Please use stream=true for binary files."
            )
                
        # Add to cache if not too large
        if file_size <= FILE_CACHE_ENTRY_MAX_SIZE:
            with cache_lock:
                add_to_file_cache(path_str, file_content, modified_time)
        
        return ReadFileResponse(content=file_content)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"File not found: {data.path}")
    except PermissionError:
        raise HTTPException(status_code=403, detail=f"Permission denied for file: {data.path}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Log unexpected errors for troubleshooting
        logger.error(f"ERROR reading file {data.path}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to read file {data.path}: {str(e)}")

@app.post(
    "/write_file", 
    response_model=SuccessResponse, 
    summary="Write to a file",
    description="""
    Write content to a file, with options for overwriting, appending, or prepending text.
    Uses async file operations for better performance.
    Implements transaction-like semantics for cache operations.
    Also updates metadata index when a file is written.
    
    ## Natural Language Queries
    - "Create a file called [name] with content [content]"
    - "Write [content] to [file]"
    - "Save this content to [file]"
    - "Create a new file [name]"
    - "Make a file with [content]"
    - "Save [content] as [filename]"
    - "Append [content] to [file]"
    - "Add [content] to the end of [file]"
    - "Update [file] by adding [content] at the end"
    - "Prepend [content] to [file]"
    - "Add [content] to the beginning of [file]"
    """,
    openapi_extra=nl_mapping(
        queries=[
            "create a file called name with content",
            "write content to file",
            "save this content to file",
            "create a new file",
            "make a file with content",
            "save content as filename",
            "append content to file",
            "add content to the end of file",
            "update file by adding content at the end",
            "modify file and append content",
            "prepend content to file",
            "add content to the beginning of file"
        ],
        parameter_mappings={
            "path": ["file", "filename", "path", "location", "name"],
            "content": ["text", "content", "data", "information"],
            "mode": ["append", "overwrite", "prepend", "add to", "write to"]
        },
        response_template="I've updated the file '{file_name}' with the content you provided.",
        common_paths=COMMON_PATHS
    )
)
async def write_file(data: WriteFileRequest = Body(...)):
    """
    Write content to a file, with options for overwriting, appending, or prepending.
    Returns JSON success message.
    Uses async file operations for better performance.
    Implements transaction-like semantics for cache operations.
    Also updates metadata index when a file is written.
    """
    path = normalize_path(data.path)
    path_str = str(path)
    # Flag to track if we've invalidated the cache but failed to write
    cache_invalidated = False
    
    try:
        # Ensure the parent directory exists
        path.parent.mkdir(parents=True, exist_ok=True)
        
        # First, invalidate cache for the path before writing
        # This prevents stale reads during file operation
        with cache_lock:
            invalidate_cache_for_path(path_str)
            cache_invalidated = True
        
        try:
            # Handle different write modes
            if data.mode == "append" and path.exists():
                # For append mode, we need to read current content first
                current_content = ""
                try:
                    # First read the content
                    current_content = ""
                    if path.exists():
                        async with aiofiles.open(path, mode='r', encoding='utf-8') as file:
                            current_content = await file.read()
                    
                    # For debugging
                    logger.info(f"Original content: {repr(current_content)}")
                    logger.info(f"Appending content: {repr(data.content)}")
                    
                    # Append new content to current content with proper line handling
                    # Check if the current content ends with a newline
                    if current_content and not current_content.endswith('\n'):
                        # If no newline at end of file, add one before appending
                        combined_content = current_content + '\n' + data.content
                    else:
                        # If already has newline or is empty, just append
                        combined_content = current_content + data.content
                    logger.info(f"Combined content: {repr(combined_content)}")
                    
                    # Write combined content
                    async with aiofiles.open(path, mode='w', encoding='utf-8') as file:
                        await file.write(combined_content)
                except UnicodeDecodeError:
                    # If we can't read the file as text, open it in binary mode
                    # This might happen for binary files
                    raise HTTPException(
                        status_code=422,
                        detail="Cannot append to binary file. Use overwrite mode instead."
                    )
            elif data.mode == "prepend" and path.exists():
                # For prepend mode, we need to read current content first
                current_content = ""
                try:
                    # First read the content
                    current_content = ""
                    if path.exists():
                        async with aiofiles.open(path, mode='r', encoding='utf-8') as file:
                            current_content = await file.read()
                    
                    # For debugging
                    logger.info(f"Original content: {repr(current_content)}")
                    logger.info(f"Prepending content: {repr(data.content)}")
                    
                    # Prepend new content to current content
                    combined_content = data.content + current_content
                    logger.info(f"Combined content: {repr(combined_content)}")
                    
                    # Write combined content
                    async with aiofiles.open(path, mode='w', encoding='utf-8') as file:
                        await file.write(combined_content)
                except UnicodeDecodeError:
                    # If we can't read the file as text, open it in binary mode
                    # This might happen for binary files
                    raise HTTPException(
                        status_code=422,
                        detail="Cannot prepend to binary file. Use overwrite mode instead."
                    )
            else:
                # Default: overwrite mode (or file doesn't exist)
                async with aiofiles.open(path, mode='w', encoding='utf-8') as file:
                    await file.write(data.content)
        except Exception as e:
            # If we failed to write but already invalidated cache, we can't
            # recover the old cache entry. Just pass the error up.
            raise e
        
        # If write succeeded, update cache with the correct content
        modified_time = path.stat().st_mtime
        
        # For append and prepend modes, we should cache the combined content, not just the new data
        if data.mode in ("append", "prepend") and path.exists():
            # Re-read the file to get the correct content for caching
            async with aiofiles.open(path, mode='r', encoding='utf-8') as file:
                cache_content = await file.read()
            add_to_file_cache(path_str, cache_content, modified_time)
        else:
            # For overwrite mode, we can just cache the provided content
            add_to_file_cache(path_str, data.content, modified_time)
        
        # Clear the normalize_path cache if this is a new file
        # This ensures new paths are recognized correctly
        if not path.exists():
            normalize_path.cache_clear()
        
        # Notify metadata watcher about the change
        if METADATA_API_AVAILABLE:
            try:
                if WATCHER_AVAILABLE:
                    watcher.notify_change(path)
            except Exception as e:
                # Log but don't fail if metadata update fails
                logger.warning(f"Failed to update metadata for {path_str}: {e}")
        
        return SuccessResponse(message=f"Successfully wrote to {data.path}")
    except PermissionError:
        raise HTTPException(status_code=403, detail=f"Permission denied to write to {data.path}")
    except Exception as e:
        # Note: We don't try to restore cache here as it's more reliable
        # to just let it be missing than to have a potentially stale entry
        raise HTTPException(status_code=500, detail=f"Failed to write to {data.path}: {str(e)}")


@app.post(
    "/edit_file",
    response_model=Union[SuccessResponse, DiffResponse],
    summary="Edit a file with diff",
    description="""
    Apply a list of edits to a text file.
    Returns JSON success message or JSON diff on dry-run.
    Uses async file operations and caching for better performance.
    Implements transaction-like semantics for cache operations.
    
    ## Natural Language Queries
    - "Change [old text] to [new text] in [file]"
    - "Replace [old text] with [new text] in [file]"
    - "Edit [file] to change [old text] to [new text]"
    - "Update [file] by replacing [old text] with [new text]"
    - "Modify [file] to say [new text] instead of [old text]"
    """,
    openapi_extra={
        "x-natural-language-queries": {
            "intents": [
                "change old text to new text in file",
                "replace old text with new text in file",
                "edit file to change old text to new text",
                "update file by replacing old text with new text",
                "modify file to say new text instead of old text"
            ],
            "parameter_mappings": {
                "path": ["file", "document", "text file"],
                "oldText": ["old text", "original text", "current text", "existing text"],
                "newText": ["new text", "replacement text", "updated text", "corrected text"],
                "dryRun": ["preview", "dry run", "show changes", "simulate", "don't apply"]
            },
            "response_template": "I've updated the file '{file_name}'. I replaced '{old_text}' with '{new_text}'.",
            "common_paths": {
                "my CodeGen project": "/mnt/c/Sandboxes/CodeGen",
                "the test directory": "/app/testdir"
            }
        }
    }
)
async def edit_file(data: EditFileRequest = Body(...)):
    """
    Apply a list of edits to a text file.
    Returns JSON success message or JSON diff on dry-run.
    Uses async file operations and caching for better performance.
    Implements transaction-like semantics for cache operations.
    """
    path = normalize_path(data.path)
    path_str = str(path)
    original = None
    cache_invalidated = False
    
    try:
        # Check if file exists and get modification time
        if not path.exists():
            raise FileNotFoundError(f"File not found: {data.path}")
            
        modified_time = path.stat().st_mtime
        
        # Check cache first
        with cache_lock:
            original = get_from_file_cache(path_str, modified_time)
            
        if original is None:
            # Read file asynchronously if not in cache
            async with aiofiles.open(path, mode='r', encoding='utf-8') as file:
                original = await file.read()
                
            # Cache the original content to avoid redundant reads
            with cache_lock:
                add_to_file_cache(path_str, original, modified_time)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"File not found: {data.path}")
    except PermissionError:
        raise HTTPException(status_code=403, detail=f"Permission denied to read file: {data.path}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read file {data.path} for editing: {str(e)}")

    modified = original
    try:
        # Apply all edits
        for edit in data.edits:
            if edit.oldText not in modified:
                raise HTTPException(
                    status_code=400,
                    detail=f"Edit failed: oldText not found in content: '{edit.oldText[:50]}...'",
                )
            # Replace only the first occurrence
            modified = modified.replace(edit.oldText, edit.newText, 1)

        # For dry runs, just return diff without modifying the file
        if data.dryRun:
            diff_output = difflib.unified_diff(
                original.splitlines(keepends=True),
                modified.splitlines(keepends=True),
                fromfile=f"a/{data.path}",
                tofile=f"b/{data.path}",
            )
            return DiffResponse(diff="".join(diff_output))

        # Transaction-like pattern for write operations
        with cache_lock:
            # First invalidate cache
            invalidate_cache_for_path(path_str)
            cache_invalidated = True
            
        try:
            # Write changes to disk
            async with aiofiles.open(path, mode='w', encoding='utf-8') as file:
                await file.write(modified)
        except Exception as e:
            # If write fails, we can't recover the cache entry
            # But at least we won't have stale data
            raise e
            
        # Update cache after successful write
        new_modified_time = path.stat().st_mtime
        with cache_lock:
            add_to_file_cache(path_str, modified, new_modified_time)
        
        # Notify metadata watcher about the change
        if METADATA_API_AVAILABLE and WATCHER_AVAILABLE:
            try:
                watcher.notify_change(path)
            except Exception as e:
                # Log but don't fail if metadata update fails
                logger.warning(f"Failed to update metadata for {path_str}: {e}")
        
        return SuccessResponse(message=f"Successfully edited file {data.path}")

    except PermissionError:
        raise HTTPException(status_code=403, detail=f"Permission denied to write edited file: {data.path}")
    except Exception as e:
        # We don't try to restore cache - better to have a cache miss than stale data
        raise HTTPException(status_code=500, detail=f"Failed to write edited file {data.path}: {str(e)}")

@app.post(
    "/create_directory", 
    response_model=SuccessResponse, 
    summary="Create a directory",
    description="""
    Create a new directory recursively. Returns JSON success message.
    Also updates the metadata index with the new directory.
    
    ## Natural Language Queries
    - "Create a directory called [name]"
    - "Make a new folder at [path]"
    - "Create directory [name]"
    - "Make folder [name]"
    - "Create a new directory at [path]"
    - "Add folder [name]"
    """,
    openapi_extra={
        "x-natural-language-queries": {
            "intents": [
                "create a directory called name",
                "make a new folder at path",
                "create directory name",
                "make folder name",
                "create a new directory at path",
                "add folder name"
            ],
            "parameter_mappings": {
                "path": ["directory", "folder", "location", "path", "name"]
            },
            "response_template": "I've created a new folder called '{directory_name}' at '{path}'.",
            "common_paths": {
                "my CodeGen project": "/mnt/c/Sandboxes/CodeGen",
                "the test directory": "/app/testdir"
            }
        }
    }
)
async def create_directory(data: CreateDirectoryRequest = Body(...)):
    """
    Create a new directory recursively. Returns JSON success message.
    Also updates the metadata index with the new directory.
    """
    dir_path = normalize_path(data.path)
    try:
        dir_path.mkdir(parents=True, exist_ok=True)
        
        # Notify metadata watcher about the change
        if METADATA_API_AVAILABLE and WATCHER_AVAILABLE:
            try:
                watcher.notify_change(dir_path)
            except Exception as e:
                # Log but don't fail if metadata update fails
                logger.warning(f"Failed to update metadata for {dir_path}: {e}")
        
        return SuccessResponse(message=f"Successfully created directory {data.path}")
    except PermissionError:
        raise HTTPException(status_code=403, detail=f"Permission denied to create directory {data.path}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create directory {data.path}: {str(e)}")

@app.post(
    "/directory_tree",
    summary="Recursive directory tree with depth limit",
    description="""
    Return a tree structure of a directory using an iterative approach with depth limit.
    Uses a non-recursive implementation to avoid stack overflow on large directories.
    
    ## Natural Language Queries
    - "Show the directory structure of [path]"
    - "Get a tree view of [directory]"
    - "Show me the file tree for [path]"
    - "What's the structure of [directory]?"
    - "List the directory tree for [path]"
    - "Show nested folders in [directory]"
    """,
    openapi_extra={
        "x-natural-language-queries": {
            "intents": [
                "show the directory structure of path",
                "get a tree view of directory",
                "show me the file tree for path",
                "what's the structure of directory",
                "list the directory tree for path",
                "show nested folders in directory"
            ],
            "parameter_mappings": {
                "path": ["directory", "folder", "location"],
                "max_depth": ["depth", "levels", "how deep", "nested level"],
                "include_hidden": ["show hidden", "include hidden", "hidden files"]
            },
            "response_template": "Here's the directory structure of '{path}':",
            "common_paths": {
                "my CodeGen project": "/mnt/c/Sandboxes/CodeGen",
                "the test directory": "/app/testdir"
            }
        }
    }
)
async def directory_tree(data: DirectoryTreeRequest = Body(...)):
    """
    Return a tree structure of a directory using an iterative approach with depth limit.
    Uses a non-recursive implementation to avoid stack overflow on large directories.
    """
    base_path = normalize_path(data.path)

    if not base_path.is_dir():
        raise HTTPException(status_code=400, detail=f"Path is not a directory: {data.path}")

    # Iterative approach to avoid recursion depth issues
    def build_tree_iterative(root_path, max_depth):
        result = []
        # Queue items contain (path, depth, parent_dict)
        queue = [(root_path, 0, None)]
        
        while queue:
            current_path, current_depth, parent = queue.pop(0)
            
            # Skip hidden files/dirs if not included
            if not data.include_hidden and current_path.name.startswith('.'):
                continue
                
            # Create entry for current item
            is_dir = current_path.is_dir()
            entry = {
                "name": current_path.name,
                "type": "directory" if is_dir else "file",
                "path": str(current_path),
                "size": current_path.stat().st_size if current_path.is_file() else None
            }
            
            # If this is a directory and we haven't reached max depth, process children
            if is_dir and current_depth < max_depth:
                entry["children"] = []
                
                try:
                    # Add children to the queue, sorting directories first
                    for child in sorted(current_path.iterdir(), key=lambda p: (not p.is_dir(), p.name)):
                        queue.append((child, current_depth + 1, entry))
                except PermissionError:
                    entry["error"] = "Permission denied"
                except Exception as e:
                    entry["error"] = str(e)
            
            # Add the entry to parent's children or to result if it's root
            if parent:
                parent["children"].append(entry)
            else:
                result.append(entry)
                
        return result

    # Process in a thread to avoid blocking the event loop
    tree = await run_in_threadpool(build_tree_iterative, base_path, data.max_depth)
    return {"tree": tree}

@app.post(
    "/search_content", 
    response_model=SearchContentResponse, 
    summary="Search for content within files",
    description="""
    Search for text content within files in a specified directory.
    Uses thread pool for parallel file processing and supports pagination.
    
    Features:
    - Robust error handling for individual file failures
    - Parallel processing of files for better performance
    - Pagination to handle large result sets
    - Statistics about the search operation
    - Smart file type detection to skip binary files
    
    ## Natural Language Queries
    - "Search for [text] in files"
    - "Find files containing [text]"
    - "Look for [text] inside files"
    - "Which files contain [text]?"
    - "Search content for [text]"
    - "Find occurrences of [text]"
    - "Search for [text] in the codebase"
    """,
    openapi_extra={
        "x-natural-language-queries": {
            "intents": [
                "search for text in files",
                "find files containing text",
                "look for text inside files",
                "which files contain text",
                "search content for text",
                "find occurrences of text",
                "search for text in the codebase"
            ],
            "parameter_mappings": {
                "path": ["directory", "folder", "location", "where to search"],
                "search_query": ["text", "content", "pattern", "string", "phrase"],
                "recursive": ["include subdirectories", "search subdirectories", "recursive"],
                "file_pattern": ["file type", "extension", "file filter"]
            },
            "response_template": "I found '{search_query}' in {total} files:",
            "common_paths": {
                "my CodeGen project": "/mnt/c/Sandboxes/CodeGen",
                "the test directory": "/app/testdir",
                "the codebase": "/mnt/c/Sandboxes/CodeGen"
            }
        }
    }
)
async def search_content(data: SearchContentRequest = Body(...)):
    """
    Search for text content within files in a specified directory.
    Uses thread pool for parallel file processing and supports pagination.
    
    Features:
    - Robust error handling for individual file failures
    - Parallel processing of files for better performance
    - Pagination to handle large result sets
    - Statistics about the search operation
    - Smart file type detection to skip binary files
    """
    start_time = datetime.now()
    base_path = normalize_path(data.path)
    search_query_lower = data.search_query.lower()
    all_results = []
    errors = []
    stats = {
        "total_files": 0,
        "processed_files": 0,
        "skipped_files": 0,
        "errors": 0,
        "search_time_ms": 0,
    }

    if not base_path.is_dir():
        raise HTTPException(status_code=400, detail="Provided path is not a directory")

    # Collect all files first to enable proper pagination
    try:
        if data.recursive:
            files = list(base_path.rglob(data.file_pattern))
        else:
            files = list(base_path.glob(data.file_pattern))
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Error collecting files to search: {str(e)}"
        )
    
    # Filter to only include files (not directories)
    files = [f for f in files if f.is_file()]
    stats["total_files"] = len(files)
    
    # Limit number of files to search to prevent resource exhaustion
    max_files = 10000  # Arbitrary limit to prevent abuse
    if len(files) > max_files:
        files = files[:max_files]
        errors.append({
            "type": "limit_exceeded",
            "message": f"Too many files to search. Limited to {max_files} files."
        })
    
    # Process files in parallel using thread pool, with concurrency control
    # This significantly speeds up IO-bound file operations
    search_tasks = []
    max_concurrency = min(100, len(files))  # Limit concurrency to avoid resource exhaustion
    
    # Create batches of files to process
    for i in range(0, len(files), max_concurrency):
        batch = files[i:i + max_concurrency]
        batch_tasks = []
        
        for file_path in batch:
            try:
                batch_tasks.append(
                    run_in_threadpool(search_file_content, file_path, search_query_lower)
                )
            except Exception as e:
                errors.append({
                    "file": str(file_path),
                    "error": f"Failed to create search task: {str(e)}"
                })
                
        if batch_tasks:
            # Process each batch with gather for concurrent execution
            try:
                batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
                
                for result in batch_results:
                    stats["processed_files"] += 1
                    
                    # Handle exceptions from gather
                    if isinstance(result, Exception):
                        errors.append({
                            "error": f"Search thread error: {str(result)}"
                        })
                        stats["errors"] += 1
                        continue
                        
                    # Check for skipped files
                    if result and len(result) == 1 and "skipped" in result[0]:
                        stats["skipped_files"] += 1
                    
                    # Add valid results
                    all_results.extend(result)
            except Exception as e:
                errors.append({
                    "error": f"Batch processing error: {str(e)}"
                })
                stats["errors"] += 1
    
    # Identify and group errors by type for cleaner reporting
    error_files = [r["file_path"] for r in all_results if "error" in r]
    if error_files:
        stats["error_files"] = len(error_files)
    
    # Calculate search time
    stats["search_time_ms"] = int((datetime.now() - start_time).total_seconds() * 1000)
    
    # Apply pagination
    offset = data.pagination.offset
    limit = data.pagination.limit
    total_matches = len(all_results)
    paginated_results = all_results[offset:offset + limit]
    
    return SearchContentResponse(
        items=paginated_results,
        total=total_matches,
        offset=offset,
        limit=limit,
        errors=errors[:100],  # Limit number of errors reported
        stats=stats
    )

@app.post("/delete_path", 
    response_model=SuccessResponse, 
    summary="Delete a file or directory", 
    description="""
    Delete a specified file or directory. Requires explicit confirmation.
    Use 'recursive=True' to delete non-empty directories.
    
    ## Natural Language Queries
    - "Delete the file [file_path]"
    - "Remove the directory [directory_path]"
    - "Delete all files in [directory_path]"
    - "Permanently remove [file_path]"
    - "Erase file [file_path]"
    - "Delete [file_path] recursively"
    - "Remove folder [directory_path]"
    """,
    openapi_extra={
        "x-natural-language-queries": {
            "intents": [
                "delete file",
                "remove directory",
                "delete all files in directory",
                "permanently remove file",
                "erase file",
                "delete directory recursively",
                "remove folder"
            ],
            "parameter_mappings": {
                "path": ["file path", "directory path", "folder path", "file", "folder", "directory"],
                "confirm": ["confirm deletion", "confirm", "i'm sure", "yes delete it"],
                "recursive": ["recursively", "delete everything inside", "including contents", "delete all files inside"]
            },
            "response_template": "I've deleted {path}. {additional_info}",
            "common_paths": {
                "my CodeGen project": "/mnt/c/Sandboxes/CodeGen",
                "the test directory": "/app/testdir"
            }
        }
    }
)
async def delete_path(data: DeletePathRequest = Body(...)):
    """
    Delete a specified file or directory. Requires explicit confirmation.
    Use 'recursive=True' to delete non-empty directories.
    Returns JSON success message.
    Also updates the metadata index by removing deleted entries.
    """
    if not data.confirm_delete:
        raise HTTPException(
            status_code=400,
            detail="Deletion not confirmed. Set 'confirm_delete' to true to proceed."
        )

    path = normalize_path(data.path)
    path_str = str(path)

    try:
        if not path.exists():
            raise HTTPException(status_code=404, detail=f"Path not found: {data.path}")

        # Store path info for metadata update after deletion
        is_file = path.is_file()
        
        if is_file:
            # Invalidate cache before deleting the file
            invalidate_cache_for_path(path_str)
            path.unlink()
            
            # Update metadata after deletion
            if METADATA_API_AVAILABLE:
                try:
                    await db.delete_metadata(path_str)
                except Exception as e:
                    # Log but don't fail if metadata update fails
                    logger.warning(f"Failed to update metadata for deleted file {path_str}: {e}")
                    
            return SuccessResponse(message=f"Successfully deleted file: {data.path}")
        elif path.is_dir():
            # For directories, invalidate all cached paths under this directory
            invalidate_cache_for_path(path_str)
            
            if data.recursive:
                shutil.rmtree(path)
                
                # Update metadata after deletion
                if METADATA_API_AVAILABLE:
                    try:
                        await db.delete_metadata(path_str)
                    except Exception as e:
                        # Log but don't fail if metadata update fails
                        logger.warning(f"Failed to update metadata for deleted directory {path_str}: {e}")
                        
                return SuccessResponse(message=f"Successfully deleted directory recursively: {data.path}")
            else:
                try:
                    path.rmdir()
                    
                    # Update metadata after deletion
                    if METADATA_API_AVAILABLE:
                        try:
                            await db.delete_metadata(path_str)
                        except Exception as e:
                            # Log but don't fail if metadata update fails
                            logger.warning(f"Failed to update metadata for deleted directory {path_str}: {e}")
                            
                    return SuccessResponse(message=f"Successfully deleted empty directory: {data.path}")
                except OSError as e:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Directory not empty. Use 'recursive=True' to delete non-empty directories. Original error: {e}"
                    )
        else:
            raise HTTPException(status_code=400, detail=f"Path is not a file or directory: {data.path}")

    except PermissionError:
        raise HTTPException(status_code=403, detail=f"Permission denied to delete {data.path}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete {data.path}: {e}")

@app.post("/move_path", 
    response_model=SuccessResponse, 
    summary="Move or rename a file or directory",
    description="""
    Move or rename a file or directory from source_path to destination_path.
    Both paths must be within the allowed directories.
    
    ## Natural Language Queries
    - "Move [source_path] to [destination_path]"
    - "Rename [source_path] to [destination_path]"
    - "Move file from [source_path] to [destination_path]"
    - "Move directory [source_path] to [destination_path]"
    - "Copy and delete [source_path] to [destination_path]"
    - "Relocate [source_path] to [destination_path]"
    - "Transfer [source_path] to [destination_path]"
    """,
    openapi_extra={
        "x-natural-language-queries": {
            "intents": [
                "move file to destination",
                "rename file to",
                "move file from source to destination",
                "move directory to destination",
                "copy and delete file to",
                "relocate file to",
                "transfer file to"
            ],
            "parameter_mappings": {
                "source_path": ["source file", "source path", "source", "old name", "current file", "old file", "from path", "original file"],
                "destination_path": ["destination", "destination path", "target location", "new name", "new file", "to path", "new location"]
            },
            "response_template": "I've moved {source_path} to {destination_path}.",
            "common_paths": {
                "my CodeGen project": "/mnt/c/Sandboxes/CodeGen",
                "the test directory": "/app/testdir"
            }
        }
    }
)
async def move_path(data: MovePathRequest = Body(...)):
    """
    Move or rename a file or directory from source_path to destination_path.
    Both paths must be within the allowed directories.
    Returns JSON success message.
    Also updates the metadata index with the moved entries.
    """
    source = normalize_path(data.source_path)
    destination = normalize_path(data.destination_path)
    
    try:
        if not source.exists():
            raise HTTPException(status_code=404, detail=f"Source path not found: {data.source_path}")

        # Invalidate source path in cache before moving
        invalidate_cache_for_path(str(source))
        
        # Perform the move operation
        shutil.move(str(source), str(destination))
        
        # Invalidate destination path in cache to ensure fresh reads
        invalidate_cache_for_path(str(destination))
        
        # Clear the normalize_path cache since path relationships may have changed
        normalize_path.cache_clear()
        
        # Update metadata index for the moved files/directories
        if METADATA_API_AVAILABLE:
            try:
                # For metadata, we need to:
                # 1. Remove the old entries
                # 2. Add the new entries
                
                # Delete old metadata entries
                await db.delete_metadata(str(source))
                
                # Notify watcher to add new entries if it's available
                if WATCHER_AVAILABLE:
                    watcher.notify_change(destination)
            except Exception as e:
                # Log but don't fail if metadata update fails
                logger.warning(f"Failed to update metadata for move operation: {e}")
        
        return SuccessResponse(message=f"Successfully moved '{data.source_path}' to '{data.destination_path}'")

    except PermissionError:
        raise HTTPException(status_code=403, detail=f"Permission denied for move operation involving '{data.source_path}' or '{data.destination_path}'")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to move '{data.source_path}' to '{data.destination_path}': {e}")
    
@app.post("/get_metadata", 
    summary="Get file or directory metadata",
    description="""
    Retrieve metadata for a specified file or directory path.
    
    ## Natural Language Queries
    - "Get metadata for [path]"
    - "Tell me about the file [path]"
    - "What do you know about [path]"
    - "Show file details for [path]"
    - "Get information about [path]"
    - "When was [path] last modified?"
    - "What is the size of [path]?"
    """,
    openapi_extra={
        "x-natural-language-queries": {
            "intents": [
                "get metadata for",
                "tell me about the file",
                "what do you know about",
                "show file details for",
                "get information about",
                "when was file last modified",
                "what is the size of"
            ],
            "parameter_mappings": {
                "path": ["file path", "file", "directory", "folder", "document"]
            },
            "response_template": "The file {path} is a {type}, {size_desc}, last modified on {modified_time}.",
            "common_paths": {
                "my CodeGen project": "/mnt/c/Sandboxes/CodeGen",
                "the test directory": "/app/testdir"
            }
        }
    }
)
async def get_metadata(data: GetMetadataRequest = Body(...)):
    """
    Retrieve metadata for a specified file or directory path.
    """
    path = normalize_path(data.path)
    try:
        if not path.exists():
            raise HTTPException(status_code=404, detail=f"Path not found: {data.path}")

        stat_result = path.stat()
        if path.is_file():
            file_type = "file"
        elif path.is_dir():
            file_type = "directory"
        else:
            file_type = "other"

        mod_time = datetime.fromtimestamp(stat_result.st_mtime, tz=timezone.utc).isoformat()
        try:
            create_time = datetime.fromtimestamp(stat_result.st_birthtime, tz=timezone.utc).isoformat()
        except AttributeError:
            create_time = datetime.fromtimestamp(stat_result.st_ctime, tz=timezone.utc).isoformat()

        metadata = {
            "path": str(path),
            "type": file_type,
            "size_bytes": stat_result.st_size,
            "modification_time_utc": mod_time,
            "creation_time_utc": create_time,
            "last_metadata_change_time_utc": datetime.fromtimestamp(stat_result.st_ctime, tz=timezone.utc).isoformat(),
        }
        return metadata

    except PermissionError:
        raise HTTPException(status_code=403, detail=f"Permission denied to access metadata for {data.path}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get metadata for {data.path}: {e}")

@app.post("/metadata_search", 
    summary="Search files using metadata",
    description="""
    Search for files and directories using metadata criteria.
    Results are paginated and can be filtered by various attributes.
    
    ## Natural Language Queries
    - "Find files with extension [ext]"
    - "Search for [file type] files"
    - "Find files modified [time period]"
    - "Search for files related to [topic]"
    - "Find files containing [term] in their name"
    - "Search for [size] files"
    - "Find all directories under [path]"
    """,
    openapi_extra={
        "x-natural-language-queries": {
            "intents": [
                "find files with extension",
                "search for file type files",
                "find files modified recently",
                "search for files related to topic",
                "find files containing term in their name",
                "search for large files",
                "search for small files",
                "find all directories under path"
            ],
            "parameter_mappings": {
                "query": ["search term", "keyword", "text", "name contains"],
                "extensions": ["file types", "file extensions", "types of files"],
                "is_directory": ["folders only", "files only", "just directories", "just files"],
                "min_size": ["larger than", "bigger than", "minimum size"],
                "max_size": ["smaller than", "maximum size", "not bigger than"],
                "path_prefix": ["in directory", "under path", "within folder"]
            },
            "response_template": "I found {total} files matching your search criteria.",
            "common_paths": {
                "my CodeGen project": "/mnt/c/Sandboxes/CodeGen",
                "the test directory": "/app/testdir"
            }
        }
    }
)
async def metadata_search(data: MetadataSearchRequest = Body(...)):
    """
    Search for files and directories using metadata criteria.
    Results are paginated and can be filtered by various attributes.
    """
    if not METADATA_API_AVAILABLE:
        raise HTTPException(status_code=501, detail="Metadata API is not available")
    
    try:
        # First, validate path_prefix if provided
        if data.path_prefix:
            try:
                normalize_path(data.path_prefix)
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Invalid path_prefix: {e}")
        
        # Execute search using db module
        results = await db.search_metadata(
            query=data.query,
            extensions=data.extensions,
            is_directory=data.is_directory,
            min_size=data.min_size,
            max_size=data.max_size,
            modified_after=data.modified_after,
            modified_before=data.modified_before,
            path_prefix=data.path_prefix,
            limit=data.limit,
            offset=data.offset
        )
        
        # Count total results (approximate)
        total_count = len(results) + data.offset
        if len(results) == data.limit:
            total_count += 1  # Indicate there are more results
            
        return {
            "items": results,
            "total": total_count,
            "offset": data.offset,
            "limit": data.limit
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to search metadata: {str(e)}"
        )
        
@app.get(
    "/list_allowed_directories", 
    summary="List access-permitted directories",
    description="""
    Get a list of all directories this server can access.
    
    ## Natural Language Queries
    - "What is the allowed directory"
    - "Which directories are allowed"
    - "What folders can I access"
    - "Show me allowed paths"
    - "What directories can I use"
    - "Where can I store files"
    - "What locations can I read from"
    """,
    openapi_extra={
        "x-natural-language-queries": {
            "intents": [
                "what is the allowed directory",
                "which directories are allowed",
                "what folders can I access",
                "show me allowed paths",
                "what directories can I use",
                "where can I store files",
                "what locations can I read from"
            ],
            "parameter_mappings": {},
            "response_template": "The allowed directories are: {allowed_directories}. These are the only directories the filesystem can access for security reasons."
        }
    }
)
async def list_allowed_directories():
    """
    Show all directories this server can access.
    """
    return {"allowed_directories": ALLOWED_DIRECTORIES}

# Metadata API endpoints have been moved to metadata_api.py and are now included via the router

# Commented out in favor of the modular approach using metadata_api router
# @app.get("/watcher_status", summary="Get file watcher status")
# async def watcher_status():
#     """
#     Get the current status of the file watcher system.
#     Shows which directories are being watched, when they were last scanned,
#     and if the watcher is actively running.
#     """
#     ...

# Metadata request models are now defined in metadata_api.py
# class WatchDirectoryRequest(BaseModel):
#     """Request for watching a directory."""
#     path: str = Field(..., description="Directory path to watch for changes")

# @app.post("/watch_directory", summary="Start watching a directory")
# async def watch_directory(data: WatchDirectoryRequest = Body(...)):
#     """
#     Start watching a directory for file changes.
#     The watcher will automatically update the metadata index when files change in this directory.
#     """
#     ...

# class UnwatchDirectoryRequest(BaseModel):
#     """Request for unwatching a directory."""
#     path: str = Field(..., description="Directory path to stop watching")

# @app.post("/unwatch_directory", summary="Stop watching a directory")
# async def unwatch_directory(data: UnwatchDirectoryRequest = Body(...)):
#     """
#     Stop watching a directory for file changes.
#     """
#     ...

# class ScanDirectoryRequest(BaseModel):
#     """Request for scanning a specific directory or all watched directories."""
#     path: Optional[str] = Field(None, description="Optional specific directory path to scan. If not provided, all watched directories will be scanned.")
#     force: bool = Field(False, description="Force full scan even if last scan was recent")

# @app.post("/scan_watched_directories", summary="Trigger manual scan of watched directories")
# async def scan_watched_directories(data: ScanDirectoryRequest = Body(...)):
#     """
#     Manually trigger a scan of watched directories to update the metadata index.
#     Useful when you've made changes outside the API and want to update the index immediately.
#     """
#     ...

# @app.post("/index_directory", summary="Index a directory")
# async def index_directory(path: str = Body(..., embed=True)):
#     """
#     Index a directory and its contents in the metadata database.
#     With no file limit for comprehensive indexing.
#     """
#     ...

# --- Directory and File APIs ---

class DirectoryRequest(BaseModel):
    """Request for listing directory contents."""
    path: str = Field(..., description="Directory path to list")
    include_hidden: bool = Field(False, description="Whether to include hidden files and directories")
    sort_by: Optional[str] = Field("name", description="Sort field (name, size, modified)")
    sort_order: Optional[str] = Field("asc", description="Sort order (asc, desc)")
    include_details: bool = Field(True, description="Include detailed file stats")

class FileItem(BaseModel):
    """File or directory entry model."""
    name: str
    path: str
    is_directory: bool
    size_bytes: Optional[int] = None
    modified_time: Optional[str] = None
    created_time: Optional[str] = None
    extension: Optional[str] = None
    mime_type: Optional[str] = None

class DirectoryResponse(BaseModel):
    """Response for directory listing."""
    path: str
    items: List[FileItem]
    item_count: int
    parent_directory: Optional[str]

@app.post("/list_directory", 
    summary="List directory contents",
    description="""
    List the contents of a directory.
    Returns files and subdirectories with metadata information.
    Hidden files are excluded by default.
    
    ## Natural Language Queries
    - "List contents of [path]"
    - "Show files in [path]"
    - "What's in [path]"
    - "Show me the contents of [path]"
    - "What files are in [path]"
    - "List files in [path]"
    - "Show directory contents for [path]"
    """,
    openapi_extra={
        "x-natural-language-queries": {
            "intents": [
                "list contents of directory",
                "show files in directory",
                "what's in directory",
                "show me the contents of directory",
                "what files are in directory",
                "list files in directory",
                "show directory contents for"
            ],
            "parameter_mappings": {
                "path": ["directory path", "folder path", "directory", "folder"],
                "include_hidden": ["include hidden files", "show hidden files", "show all files", "include dot files"],
                "recursive": ["include subdirectories", "search subdirectories", "show all nested files"]
            },
            "response_template": "The directory {path} contains {file_count} files and {dir_count} subdirectories.",
            "common_paths": {
                "my CodeGen project": "/mnt/c/Sandboxes/CodeGen",
                "the test directory": "/app/testdir"
            }
        }
    }
)
async def list_directory(request: DirectoryRequest = Body(...)):
    """
    List the contents of a directory.
    Returns files and subdirectories with metadata information.
    Hidden files are excluded by default.
    """
    try:
        # Validate and normalize path
        dir_path = normalize_path(request.path)
        
        if not dir_path.exists():
            raise HTTPException(
                status_code=404, 
                detail=f"Directory not found: {request.path}"
            )
            
        if not dir_path.is_dir():
            raise HTTPException(
                status_code=400, 
                detail=f"Path is not a directory: {request.path}"
            )
        
        # Prepare response
        items = []
        
        # Get directory entries
        try:
            entries = list(dir_path.iterdir())
                
            # Handle hidden files
            if not request.include_hidden:
                entries = [e for e in entries if not e.name.startswith('.')]
                
            # Process each entry
            for entry in entries:
                try:
                    is_dir = entry.is_dir()
                    item = {
                        "name": entry.name,
                        "path": str(entry),
                        "is_directory": is_dir
                    }
                    
                    # Include additional details if requested
                    if request.include_details:
                        try:
                            stat_result = entry.stat()
                            
                            # Size (zero for directories)
                            item["size_bytes"] = 0 if is_dir else stat_result.st_size
                            
                            # Timestamps
                            item["modified_time"] = datetime.fromtimestamp(
                                stat_result.st_mtime, timezone.utc
                            ).isoformat()
                            
                            try:
                                # This may not be available on all platforms
                                created_time = stat_result.st_birthtime
                            except AttributeError:
                                # Fallback to ctime if birthtime is not available
                                created_time = stat_result.st_ctime
                                
                            item["created_time"] = datetime.fromtimestamp(
                                created_time, timezone.utc
                            ).isoformat()
                            
                            # File type info (only for files)
                            if not is_dir:
                                item["extension"] = entry.suffix.lower() if entry.suffix else None
                                
                                # Simple mime type inference
                                mime_map = {
                                    '.txt': 'text/plain',
                                    '.html': 'text/html',
                                    '.htm': 'text/html',
                                    '.css': 'text/css',
                                    '.js': 'application/javascript',
                                    '.json': 'application/json',
                                    '.xml': 'application/xml',
                                    '.jpg': 'image/jpeg',
                                    '.jpeg': 'image/jpeg',
                                    '.png': 'image/png',
                                    '.gif': 'image/gif',
                                    '.pdf': 'application/pdf',
                                    '.zip': 'application/zip',
                                    '.md': 'text/markdown',
                                    '.py': 'text/x-python',
                                    '.csv': 'text/csv'
                                }
                                
                                ext = entry.suffix.lower() if entry.suffix else ''
                                item["mime_type"] = mime_map.get(ext, 'application/octet-stream')
                                
                        except (PermissionError, OSError) as e:
                            # Handle errors getting file stats
                            pass
                            
                    items.append(item)
                except Exception as e:
                    # Skip entries that cause errors
                    continue
            
            # Sort items
            if request.sort_by:
                # Default sort value if the field is missing
                default_values = {
                    "size_bytes": 0,
                    "modified_time": "1970-01-01T00:00:00+00:00",
                    "created_time": "1970-01-01T00:00:00+00:00",
                    "name": "",
                    "extension": ""
                }
                
                reverse = request.sort_order.lower() == "desc"
                
                def get_sort_key(item):
                    # Handle potential missing keys
                    return item.get(request.sort_by, default_values.get(request.sort_by, ""))
                    
                items.sort(key=get_sort_key, reverse=reverse)
                
                # Always put directories first regardless of sort
                if request.sort_by != "is_directory":
                    dir_items = [item for item in items if item["is_directory"]]
                    file_items = [item for item in items if not item["is_directory"]]
                    
                    if reverse:
                        items = dir_items + file_items
                    else:
                        items = dir_items + file_items
                
        except (PermissionError, OSError) as e:
            raise HTTPException(
                status_code=403,
                detail=f"Permission denied or error reading directory: {str(e)}"
            )
            
        # Calculate parent directory (if not at root)
        parent_dir = str(dir_path.parent) if str(dir_path) != "/" else None
        
        return DirectoryResponse(
            path=str(dir_path),
            items=items,
            item_count=len(items),
            parent_directory=parent_dir
        )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error listing directory: {str(e)}"
        )

# --- Search Functionality ---

class SearchRequest(BaseModel):
    """Request for searching files."""
    path: str = Field(..., description="Base directory to search in")
    pattern: str = Field("", description="Search pattern (glob or regex)")
    recursive: bool = Field(True, description="Whether to search recursively")
    excludePatterns: List[str] = Field([], description="Patterns to exclude (glob format)")
    case_sensitive: bool = Field(False, description="Whether search is case sensitive")
    file_types: Optional[List[str]] = Field(None, description="File types to include (extensions)")
    max_size: Optional[int] = Field(None, description="Maximum file size in bytes")
    min_size: Optional[int] = Field(None, description="Minimum file size in bytes")
    modified_after: Optional[datetime] = Field(None, description="Files modified after this date")
    modified_before: Optional[datetime] = Field(None, description="Files modified before this date")
    pagination: Dict[str, int] = Field({"offset": 0, "limit": 100}, description="Pagination parameters")
    timeout_seconds: int = Field(30, description="Search timeout in seconds", ge=1, le=120)

class SearchResponse(BaseModel):
    """Response for file search."""
    items: List[Dict[str, Any]]
    total: int
    has_more: bool
    execution_time_seconds: float

@app.post(
    "/search_files", 
    summary="Search for files",
    description="""
    Search for files matching various criteria.
    
    This endpoint supports:
    - Text pattern matching
    - Recursive directory traversal
    - Exclusion patterns
    - File type filtering
    - Size constraints
    - Modification date filtering
    - Pagination
    
    For large directories, the search is performed asynchronously
    with a configurable timeout.
    
    ## Natural Language Queries
    - "Find files named [pattern]"
    - "Search for files matching [pattern]"
    - "Find [pattern] files"
    - "Look for files called [pattern]"
    - "List files matching [pattern]"
    - "Show me files with names like [pattern]"
    """,
    openapi_extra={
        "x-natural-language-queries": {
            "intents": [
                "find files named pattern",
                "search for files matching pattern",
                "find pattern files",
                "look for files called pattern",
                "list files matching pattern",
                "show me files with names like pattern"
            ],
            "parameter_mappings": {
                "path": ["directory", "folder", "location", "where to search"],
                "pattern": ["name", "filename", "file pattern", "glob pattern"],
                "recursive": ["include subdirectories", "search subdirectories", "recursive"],
                "excludePatterns": ["exclude", "ignore", "skip", "except"],
                "file_types": ["types", "extensions", "file extensions"]
            },
            "response_template": "I found {total} files matching '{pattern}':",
            "common_paths": {
                "my CodeGen project": "/mnt/c/Sandboxes/CodeGen",
                "the test directory": "/app/testdir",
                "the codebase": "/mnt/c/Sandboxes/CodeGen"
            }
        }
    }
)
async def search_files(request: SearchRequest = Body(...)):
    """
    Search for files matching various criteria.
    
    This endpoint supports:
    - Text pattern matching
    - Recursive directory traversal
    - Exclusion patterns
    - File type filtering
    - Size constraints
    - Modification date filtering
    - Pagination
    
    For large directories, the search is performed asynchronously
    with a configurable timeout.
    """
    start_time = time.time()
    
    try:
        # Validate and normalize the base path
        base_path = normalize_path(request.path)
        
        if not base_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Path not found: {request.path}"
            )
            
        if not base_path.is_dir():
            raise HTTPException(
                status_code=400,
                detail=f"Path is not a directory: {request.path}"
            )
        
        # If we have a database, use it for more efficient searching
        if METADATA_API_AVAILABLE:
            # Prepare search parameters
            search_params = {
                "query": request.pattern if request.pattern else None,
                "path_prefix": str(base_path),
                "limit": request.pagination.get("limit", 100) + 1,  # +1 to check if more results
                "offset": request.pagination.get("offset", 0),
            }
            
            # Add file extensions filter
            if request.file_types:
                extensions = [
                    ext if ext.startswith('.') else f'.{ext}'
                    for ext in request.file_types
                ]
                search_params["extensions"] = extensions
                
            # Add size filters
            if request.min_size is not None:
                search_params["min_size"] = request.min_size
                
            if request.max_size is not None:
                search_params["max_size"] = request.max_size
                
            # Add date filters
            if request.modified_after:
                search_params["modified_after"] = request.modified_after
                
            if request.modified_before:
                search_params["modified_before"] = request.modified_before
                
            # Execute search
            results = await db.search_metadata(**search_params)
            
            # Check if we have more results
            has_more = len(results) > request.pagination.get("limit", 100)
            if has_more:
                results = results[:-1]  # Remove the extra item
                
            # Format results
            items = []
            for item in results:
                entry = {
                    "name": item["name"],
                    "path": item["path"],
                    "type": "directory" if item["is_directory"] else "file",
                    "size_bytes": item["size_bytes"],
                    "modified_time": item["modified_time"],
                }
                if not item["is_directory"]:
                    entry["extension"] = item["extension"]
                    entry["mime_type"] = item["mime_type"]
                    
                items.append(entry)
                
            return SearchResponse(
                items=items,
                total=len(items) + request.pagination.get("offset", 0) + (1 if has_more else 0),
                has_more=has_more,
                execution_time_seconds=time.time() - start_time
            )
            
        else:
            # Fallback to file system search if no database
            # Use concurrent.futures to handle file system searching in a thread pool
            # to avoid blocking the async event loop
            
            # Prepare the search results
            all_matches = []
            total_count = 0
            scan_complete = False
            
            # Define the search function to run in a thread
            def thread_search():
                nonlocal all_matches, total_count, scan_complete
                
                try:
                    matches = []
                    count = 0
                    
                    # Convert exclude patterns to use pathlib
                    import fnmatch
                    
                    def is_excluded(path_str):
                        # Check if path matches any exclude pattern
                        for pattern in request.excludePatterns:
                            if fnmatch.fnmatch(path_str, pattern):
                                return True
                        return False
                    
                    # Walk directory
                    for root, dirs, files in os.walk(base_path):
                        # Skip excluded directories
                        dirs_to_remove = []
                        for d in dirs:
                            if is_excluded(d) or d.startswith('.'):
                                dirs_to_remove.append(d)
                        
                        for d in dirs_to_remove:
                            dirs.remove(d)
                            
                        # Stop recursion if not recursive
                        if not request.recursive and root != str(base_path):
                            dirs.clear()
                            continue
                            
                        # Process directories
                        for d in dirs:
                            dir_path = pathlib.Path(root) / d
                            full_path = str(dir_path)
                            
                            # Skip if excluded
                            if is_excluded(full_path):
                                continue
                                
                            # Check if it matches pattern
                            if request.pattern and request.pattern not in full_path:
                                continue
                                
                            # Get directory stats
                            try:
                                stat_result = dir_path.stat()
                                modified_time = datetime.fromtimestamp(stat_result.st_mtime, timezone.utc)
                                
                                # Apply date filters
                                if request.modified_after and modified_time < request.modified_after:
                                    continue
                                    
                                if request.modified_before and modified_time > request.modified_before:
                                    continue
                                    
                                # Add to results
                                result = {
                                    "name": d,
                                    "path": full_path,
                                    "type": "directory",
                                    "modified_time": modified_time.isoformat(),
                                    "size_bytes": 0
                                }
                                
                                count += 1
                                matches.append(result)
                            except (PermissionError, OSError):
                                # Skip if error accessing directory
                                continue
                                
                        # Process files
                        for f in files:
                            file_path = pathlib.Path(root) / f
                            full_path = str(file_path)
                            
                            # Skip if excluded
                            if is_excluded(full_path):
                                continue
                                
                            # Check extension filter
                            if request.file_types:
                                ext = file_path.suffix.lower()
                                if not ext or ext[1:] not in [t.lstrip('.').lower() for t in request.file_types]:
                                    continue
                                    
                            # Check if it matches pattern
                            if request.pattern:
                                if not request.case_sensitive:
                                    if request.pattern.lower() not in full_path.lower():
                                        continue
                                else:
                                    if request.pattern not in full_path:
                                        continue
                            
                            # Get file stats
                            try:
                                stat_result = file_path.stat()
                                size = stat_result.st_size
                                modified_time = datetime.fromtimestamp(stat_result.st_mtime, timezone.utc)
                                
                                # Apply size filters
                                if request.min_size is not None and size < request.min_size:
                                    continue
                                    
                                if request.max_size is not None and size > request.max_size:
                                    continue
                                    
                                # Apply date filters
                                if request.modified_after and modified_time < request.modified_after:
                                    continue
                                    
                                if request.modified_before and modified_time > request.modified_before:
                                    continue
                                    
                                # Add to results
                                result = {
                                    "name": f,
                                    "path": full_path,
                                    "type": "file",
                                    "size_bytes": size,
                                    "modified_time": modified_time.isoformat(),
                                    "extension": file_path.suffix.lower() if file_path.suffix else None
                                }
                                
                                count += 1
                                matches.append(result)
                            except (PermissionError, OSError):
                                # Skip if error accessing file
                                continue
                                
                    # Update the shared results
                    all_matches = matches
                    total_count = count
                    
                except Exception as e:
                    logger.error(f"Error in file system search: {e}")
                finally:
                    scan_complete = True
            
            # Start the search in a thread
            future = THREAD_POOL.submit(thread_search)
            
            # Wait for results with timeout
            try:
                max_time = min(request.timeout_seconds, 60)  # Cap at 60 seconds max
                await asyncio.sleep(0.1)  # Short pause to allow immediate results
                
                start_wait = time.time()
                while not scan_complete and time.time() - start_wait < max_time:
                    await asyncio.sleep(0.1)
                    
                # Apply pagination to results
                offset = request.pagination.get("offset", 0)
                limit = request.pagination.get("limit", 100)
                
                # Get subset of results
                end_idx = offset + limit + 1  # +1 to check if more results
                if end_idx > len(all_matches):
                    end_idx = len(all_matches)
                    
                result_subset = all_matches[offset:end_idx]
                
                # Check if there are more results
                has_more = len(result_subset) > limit
                if has_more:
                    result_subset = result_subset[:-1]  # Remove the extra item
                    
                return SearchResponse(
                    items=result_subset,
                    total=total_count,
                    has_more=has_more,
                    execution_time_seconds=time.time() - start_time
                )
                
            except Exception as e:
                raise HTTPException(
                    status_code=500,
                    detail=f"Error during file search: {str(e)}"
                )
                
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Search error: {str(e)}"
        )

# -----------------------------------------------------------------------
# Database Query API - For direct database interaction
# -----------------------------------------------------------------------

class DatabaseQueryRequest(BaseModel):
    """Request for executing SQL queries on the metadata database"""
    query: str = Field(..., description="SQL query to execute (SELECT only)")
    params: Optional[Dict[str, Any]] = Field(None, description="Parameters for the SQL query")
    limit: int = Field(1000, description="Maximum number of results to return", ge=1, le=10000)

@app.post("/database_query", 
    summary="Execute a database query",
    description="""
    Execute a query on the metadata database.
    Only SELECT queries are allowed for security reasons.
    Results are limited to prevent excessive memory usage.
    
    ## Natural Language Queries
    - "Query database for [query]"
    - "Run SQL query [query]"
    - "Search database with [query]"
    - "Execute custom database query [query]"
    - "Find database entries matching [query]"
    - "Get database results for [query]"
    - "Run a SQL search [query]"
    """,
    openapi_extra={
        "x-natural-language-queries": {
            "intents": [
                "query database for",
                "run sql query",
                "search database with",
                "execute custom database query",
                "find database entries matching",
                "get database results for",
                "run a sql search"
            ],
            "parameter_mappings": {
                "query": ["sql query", "database query", "query string", "sql statement", "select statement"],
                "params": ["parameters", "query parameters", "sql parameters"],
                "limit": ["result limit", "maximum results", "max rows"]
            },
            "response_template": "The query returned {row_count} results in {execution_time_ms} milliseconds."
        }
    }
)
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
    if not METADATA_API_AVAILABLE:
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