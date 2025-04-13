# API Prompts for Filesystem Service

This document provides ready-to-use prompts for interacting with the Filesystem Service API via an LLM chat interface. Copy and modify these prompts as needed.

## Metadata API Endpoints

These endpoints are for working with file metadata, indexing, and the file watcher service.

### Search Metadata

```
Search for files with extension ".txt" in the /app/testdir directory.

Endpoint: POST /metadata/search
{
  "query": "",
  "extensions": [".txt"],
  "is_directory": false,
  "path_prefix": "/app/testdir",
  "limit": 50
}
```

### Get Metadata for Path

```
Get metadata for the file /app/testdir/test1.txt

Endpoint: GET /metadata/path/app/testdir/test1.txt
```

### Watch Directory

```
Start watching a directory for file changes.

Endpoint: POST /metadata/watch
{
  "path": "/app/testdir"
}
```

### Unwatch Directory

```
Stop watching a directory for file changes.

Endpoint: POST /metadata/unwatch
{
  "path": "/app/testdir"
}
```

### Force Reindex Directory

```
Force a complete reindex of the directory /app/testdir

Endpoint: POST /metadata/reindex
{
  "path": "/app/testdir"
}
```

### Scan Watched Directories

```
Trigger a manual scan of all watched directories to update the index.

Endpoint: POST /metadata/scan
{
  "force": true
}
```

### Get Watcher Status

```
Check the status of the file watcher service.

Endpoint: GET /metadata/status
```

### Execute Database Query

```
Run a SQL query to find all Python files in the database.

Endpoint: POST /metadata/database_query
{
  "query": "SELECT * FROM file_metadata WHERE extension = '.py' ORDER BY size_bytes DESC",
  "limit": 20
}
```


## File Operation Endpoints

These endpoints are for basic file system operations like reading, writing, and manipulating files.

### Read File

```
Read the content of file /app/testdir/test1.txt

Endpoint: POST /read_file
{
  "path": "/app/testdir/test1.txt",
  "stream": false
}
```

### Write File

```
Write content to a file, creating it if it doesn't exist.

Endpoint: POST /write_file
{
  "path": "/app/testdir/new_file.txt",
  "content": "This is a new file created via the API."
}
```

### Edit File

```
Replace specific text in a file.

Endpoint: POST /edit_file
{
  "path": "/app/testdir/test1.txt",
  "edits": [
    {
      "oldText": "original text",
      "newText": "replacement text"
    }
  ],
  "dryRun": false
}
```

### Create Directory

```
Create a new directory.

Endpoint: POST /create_directory
{
  "path": "/app/testdir/new_directory"
}
```

### List Directory Contents

```
List all files and directories in /app/testdir

Endpoint: POST /list_directory
{
  "path": "/app/testdir",
  "include_hidden": false,
  "sort_by": "name",
  "sort_order": "asc"
}
```

### Get Directory Tree

```
Get a recursive directory tree for /app/testdir with a depth of 3 levels.

Endpoint: POST /directory_tree
{
  "path": "/app/testdir",
  "max_depth": 3,
  "include_hidden": false
}
```

### Search File Content

```
Search for the text "example" in all files in /app/testdir

Endpoint: POST /search_content
{
  "path": "/app/testdir",
  "search_query": "example",
  "recursive": true,
  "file_pattern": "*",
  "pagination": {
    "offset": 0,
    "limit": 100
  }
}
```

### Delete File or Directory

```
Delete a file. Set recursive to true for directories.

Endpoint: POST /delete_path
{
  "path": "/app/testdir/file_to_delete.txt",
  "recursive": false,
  "confirm_delete": true
}
```

### Move or Rename File/Directory

```
Move a file from one location to another.

Endpoint: POST /move_path
{
  "source_path": "/app/testdir/old_file.txt",
  "destination_path": "/app/testdir/new_file.txt"
}
```

### Get File/Directory Metadata

```
Get detailed metadata for a file.

Endpoint: POST /get_metadata
{
  "path": "/app/testdir/test1.txt"
}
```

### List Allowed Directories

```
Get a list of all directories that the API is allowed to access.

Endpoint: GET /list_allowed_directories
```

### Search Files

```
Search for files by name, type, size, and other criteria.

Endpoint: POST /search_files
{
  "path": "/app/testdir",
  "pattern": "*.txt",
  "recursive": true,
  "excludePatterns": ["*.tmp", "*.log"],
  "pagination": {
    "offset": 0,
    "limit": 50
  }
}
```

## Using These Prompts

1. Copy the prompt for the API endpoint you want to use
2. Modify the parameters as needed for your specific use case
3. Pass the prompt to the LLM chat interface
4. The LLM will generate the appropriate API call for you to execute

For endpoints that accept file paths, make sure the paths are within the allowed directories of the service.