# API Reference

This document provides detailed reference for all API endpoints in the Filesystem API.

The API is organized into several functional areas:

- **Basic Endpoints**: Common operations like listing directories and searching files
- **File Operations**: Reading, writing, editing, and streaming file content
- **Directory Operations**: Creating, exploring, and managing directory structures
- **File Watcher Operations**: Real-time monitoring of file changes
- **Database and Metadata Operations**: Indexing, querying, and searching file metadata
- **Search Operations**: Finding files by name, content, and metadata criteria

All endpoints perform path normalization and validation to ensure security and proper access control.

## Basic Endpoints

### `GET /`

Root endpoint that returns basic API information.

**Response:**
```json
{
  "message": "Filesystem API with Database Query Support"
}
```

### `POST /list_directory`

List contents of a directory with detailed metadata.

**Request:**
```json
{
  "path": "/path/to/directory",
  "include_hidden": false,
  "sort_by": "name",
  "sort_order": "asc",
  "include_details": true
}
```

**Response:**
```json
{
  "path": "/path/to/directory",
  "items": [
    {
      "name": "file.txt",
      "path": "/path/to/directory/file.txt",
      "is_directory": false,
      "size_bytes": 1024,
      "modified_time": "2023-04-01T12:00:00+00:00",
      "created_time": "2023-04-01T10:30:00+00:00",
      "extension": ".txt",
      "mime_type": "text/plain"
    },
    {
      "name": "subdirectory",
      "path": "/path/to/directory/subdirectory",
      "is_directory": true
    }
  ],
  "item_count": 2,
  "parent_directory": "/path/to"
}
```

### `POST /search_files`

Search for files matching various criteria.

**Request:**
```json
{
  "path": "/path/to/search",
  "pattern": "example",
  "recursive": true,
  "excludePatterns": ["*.tmp", "node_modules/**"],
  "case_sensitive": false,
  "file_types": [".txt", ".md"],
  "max_size": 10485760,
  "min_size": 1024,
  "modified_after": "2023-01-01T00:00:00",
  "modified_before": "2023-12-31T23:59:59",
  "pagination": {
    "offset": 0,
    "limit": 100
  },
  "timeout_seconds": 30
}
```

**Response:**
```json
{
  "items": [
    {
      "name": "example.txt",
      "path": "/path/to/search/example.txt",
      "type": "file",
      "size_bytes": 2048,
      "modified_time": "2023-04-01T12:00:00"
    }
  ],
  "total": 1,
  "has_more": false,
  "execution_time_seconds": 0.123
}
```

## File Operations

### `POST /read_file`

Read the contents of a file with caching and streaming support.

**Request:**
```json
{
  "path": "/path/to/file.txt",
  "stream": false,
  "chunk_size": 8192
}
```

**Response:**
```json
{
  "content": "File content here..."
}
```

If `stream` is `true`, the response will be a streamed file download.

### `POST /write_file`

Write content to a file, creating it if it doesn't exist.

**Request:**
```json
{
  "path": "/path/to/file.txt",
  "content": "New file content here..."
}
```

**Response:**
```json
{
  "message": "Successfully wrote to /path/to/file.txt"
}
```

### `POST /edit_file`

Apply edits to a file with optional diff preview.

**Request:**
```json
{
  "path": "/path/to/file.txt",
  "edits": [
    {
      "oldText": "Text to replace",
      "newText": "Replacement text"
    }
  ],
  "dryRun": false
}
```

**Response:**
```json
{
  "message": "Successfully edited file /path/to/file.txt"
}
```

For `dryRun: true`, the response is a diff:
```json
{
  "diff": "--- a//path/to/file.txt\n+++ b//path/to/file.txt\n@@ -1,3 +1,3 @@\n Line 1\n-Text to replace\n+Replacement text\n Line 3"
}
```

### `POST /create_directory`

Create a new directory recursively.

**Request:**
```json
{
  "path": "/path/to/new/directory"
}
```

**Response:**
```json
{
  "message": "Successfully created directory /path/to/new/directory"
}
```

### `POST /directory_tree`

Get a recursive directory tree with depth limiting.

**Request:**
```json
{
  "path": "/path/to/directory",
  "max_depth": 3,
  "include_hidden": false
}
```

**Response:**
```json
{
  "tree": [
    {
      "name": "directory",
      "type": "directory",
      "path": "/path/to/directory",
      "size": null,
      "children": [
        {
          "name": "file.txt",
          "type": "file",
          "path": "/path/to/directory/file.txt",
          "size": 1024
        }
      ]
    }
  ]
}
```

## File Watcher Operations

The file watcher doesn't watch any directories by default - you must explicitly add directories to watch using the `/metadata/watch` endpoint. Once a directory is being watched, the system will automatically:

1. Detect new, modified, and deleted files
2. Update the metadata database accordingly
3. Scan the watched directories periodically (every 5 minutes by default)
4. Process changes in batches to minimize system resource usage

### `GET /metadata/status`

Get the current status of the file watcher system. Note that this is the correct endpoint path - not `/watcher_status` or similar variations.

**Example:**
```bash
curl -X GET http://localhost:8010/metadata/status
```

**Correct Python client code:**
```python
import requests
response = requests.get("http://localhost:8010/metadata/status")
status = response.json()
print(status)
```

**Response:**
```json
{
  "status": "active",
  "watched_directories": ["/app/testdir"],
  "directory_count": 1,
  "last_scans": {
    "/app/testdir": {
      "timestamp": "2025-04-13T19:06:48.993558",
      "seconds_ago": 2,
      "next_scan_in": 297
    }
  },
  "scan_interval_seconds": 300,
  "pending_changes": 0,
  "pending_queue": 0,
  "batch_size": 200
}
```

Possible status values:
- `"inactive"`: No directories are being watched or the watcher is stopped
- `"active"`: The watcher is running and monitoring directories

### `POST /metadata/watch`

Start watching a directory for file changes. This endpoint is used to explicitly add a directory to the watcher system. The watcher will then monitor this directory for file changes and update the metadata database accordingly.

**Important Note**: Make sure to use the correct path format and endpoint URL. The endpoint is at `/metadata/watch` (not at `/watch_directory` or other variations).

**Example for watching a specific CodeGen directory:**
```bash
curl -X POST http://localhost:8010/metadata/watch \
  -H "Content-Type: application/json" \
  -d '{"path": "/mnt/c/Sandboxes/CodeGen"}'
```

**Request:**
```json
{
  "path": "/path/to/watch"
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Now watching directory: /path/to/watch",
  "watched_directory_count": 1
}
```

**Troubleshooting:**
- If you get a 404 "Not Found" error, check that you're using the correct endpoint path (`/metadata/watch`) 
- If you get a 400 "Bad Request" error, check that your path exists and is a valid directory
- If you get a 403 "Forbidden" error, check that the directory is in one of the allowed directories

### `POST /metadata/unwatch`

Stop watching a directory for file changes.

**Example:**
```bash
curl -X POST http://localhost:8000/metadata/unwatch \
  -H "Content-Type: application/json" \
  -d '{"path": "/app/testdir"}'
```

**Request:**
```json
{
  "path": "/path/to/unwatch"
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Stopped watching directory: /path/to/unwatch",
  "watched_directory_count": 0
}
```

### `POST /metadata/scan`

Manually trigger a scan of watched directories.

**Example:**
```bash
curl -X POST http://localhost:8000/metadata/scan \
  -H "Content-Type: application/json" \
  -d '{"force": true}'
```

**Request - Scan All Watched Directories:**
```json
{
  "force": true
}
```

**Request - Scan a Specific Directory:**
```json
{
  "path": "/path/to/scan",
  "force": true
}
```

The `force` parameter ignores the last scan time and performs a full scan immediately.

**Response:**
```json
{
  "status": "success",
  "message": "Successfully scanned 1 directory",
  "scanned_directories": [
    "/app/testdir"
  ]
}
```

## Database and Metadata Operations

### `POST /index_directory`

Index a directory and its contents in the metadata database.

**Request:**
```json
{
  "path": "/path/to/index"
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Successfully indexed directory: /path/to/index",
  "file_count": 42
}
```

### `POST /search_content`

Search for text content within files.

**Request:**
```json
{
  "path": "/path/to/search",
  "search_query": "example text",
  "recursive": true,
  "file_pattern": "*.txt",
  "pagination": {
    "offset": 0,
    "limit": 100
  }
}
```

**Response:**
```json
{
  "items": [
    {
      "file_path": "/path/to/search/file.txt",
      "line_number": 5,
      "line_content": "This is an example text line"
    }
  ],
  "total": 1,
  "offset": 0,
  "limit": 100,
  "errors": [],
  "stats": {
    "total_files": 10,
    "processed_files": 10,
    "skipped_files": 0,
    "errors": 0,
    "search_time_ms": 123
  }
}
```

### `POST /delete_path`

Delete a file or directory.

**Request:**
```json
{
  "path": "/path/to/delete",
  "recursive": true,
  "confirm_delete": true
}
```

**Response:**
```json
{
  "message": "Successfully deleted directory recursively: /path/to/delete"
}
```

### `POST /move_path`

Move or rename a file or directory.

**Request:**
```json
{
  "source_path": "/path/source",
  "destination_path": "/path/destination"
}
```

**Response:**
```json
{
  "message": "Successfully moved '/path/source' to '/path/destination'"
}
```

### `POST /get_metadata`

Get metadata for a file or directory.

**Request:**
```json
{
  "path": "/path/to/file.txt"
}
```

**Response:**
```json
{
  "path": "/path/to/file.txt",
  "type": "file",
  "size_bytes": 1024,
  "modification_time_utc": "2023-04-01T12:00:00+00:00",
  "creation_time_utc": "2023-04-01T10:30:00+00:00",
  "last_metadata_change_time_utc": "2023-04-01T12:00:00+00:00"
}
```

### `GET /list_allowed_directories`

List directories the API is allowed to access.

**Response:**
```json
{
  "allowed_directories": [
    "/path/one",
    "/path/two"
  ]
}
```

### `POST /metadata_search`

Search files using metadata database.

**Request:**
```json
{
  "query": "example",
  "extensions": [".txt", ".md"],
  "is_directory": false,
  "min_size": 1024,
  "max_size": 10485760,
  "modified_after": "2023-01-01T00:00:00",
  "modified_before": "2023-12-31T23:59:59",
  "path_prefix": "/path/to",
  "limit": 100,
  "offset": 0
}
```

**Response:**
```json
{
  "items": [
    {
      "id": 1,
      "path": "/path/to/example.txt",
      "name": "example.txt",
      "extension": ".txt",
      "is_directory": false,
      "size_bytes": 2048,
      "created_time": "2023-04-01T10:30:00",
      "modified_time": "2023-04-01T12:00:00",
      "last_indexed": "2023-04-01T12:30:00",
      "mime_type": "text/plain"
    }
  ],
  "total": 1,
  "offset": 0,
  "limit": 100
}
```

### `POST /database_query`

Execute SQL queries on the metadata database.

**Request:**
```json
{
  "query": "SELECT extension, COUNT(*) AS count FROM file_metadata WHERE is_directory = 0 GROUP BY extension ORDER BY count DESC",
  "params": null,
  "limit": 100
}
```

**Response:**
```json
{
  "status": "success",
  "rows": [
    {
      "extension": ".py",
      "count": 53
    },
    {
      "extension": ".txt",
      "count": 27
    }
  ],
  "row_count": 2,
  "execution_time_ms": 15,
  "query": "SELECT extension, COUNT(*) AS count FROM file_metadata WHERE is_directory = 0 GROUP BY extension ORDER BY count DESC LIMIT 100"
}
```