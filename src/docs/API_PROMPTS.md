# API Prompts for Filesystem Service with MCP Integration

This document provides ready-to-use prompts for interacting with the Filesystem Service API via an LLM chat interface. These prompts are designed to work with AI chatbots using the Model Context Protocol (MCP).

**Important**: When using these prompts with an AI, make sure the tool names match the endpoint paths with slashes replaced by underscores. For example, the `/metadata/status` endpoint would be invoked as `TOOL:metadata_status`. See the [MCP Integration Guide](MCP_INTEGRATION.md) for more details.

## Natural Language Mapping

This API supports natural language interactions through AI chatbot interfaces. Each endpoint has been enhanced with natural language mappings that help translate everyday user queries into the appropriate API calls.

### Common Natural Language Patterns

Each endpoint supports multiple natural language variations. For example:

| Endpoint | Natural Language Variations |
|----------|----------------------------|
| `/metadata/status` | "What are you watching?", "Check watcher status", "What folders are you tracking?" |
| `/read_file` | "Show me the contents of [file]", "What's in [file]?", "Read [file]" |
| `/list_directory` | "What's in [directory]?", "List files in [folder]", "Show contents of [directory]" |
| `/search_content` | "Search for [text] in files", "Find files containing [text]", "Which files contain [text]?" |

### Common Path References

Users often use natural language references to paths. These should be translated to the actual filesystem paths:

| User Reference | Filesystem Path |
|----------------|----------------|
| "my CodeGen project" | "/mnt/c/Sandboxes/CodeGen" |
| "CodeGen folder" | "/mnt/c/Sandboxes/CodeGen" |
| "the test directory" | "/app/testdir" |
| "test folder" | "/app/testdir" |

### Parameter Mapping

Parameters can also be expressed in natural language:

| Natural Language | API Parameter |
|------------------|--------------|
| "large files" | `"min_size": 1048576` (1MB) |
| "small files" | `"max_size": 1024` (1KB) |
| "text files" | `"extensions": [".txt"]` |
| "document files" | `"extensions": [".docx", ".pdf", ".md", ".txt"]` |
| "media files" | `"extensions": [".jpg", ".png", ".mp3", ".mp4"]` |
| "code files" | `"extensions": [".py", ".js", ".java", ".cpp", ".h"]` |

### Response Formatting

For better user experience, API responses should be converted into natural language:

```
Technical response:
{
  "watched_directories": ["/app/testdir", "/mnt/c/Sandboxes/CodeGen"],
  "directory_count": 2,
  "status": "active"
}

User-friendly response:
"I'm currently watching 2 directories:
- Your CodeGen project folder
- The test directory

These directories are automatically scanned every 5 minutes."
```

For more details on natural language mappings, see the [Natural Language Mapping Guide](NATURAL_LANGUAGE_MAPPING.md).

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

For MCP AI integration use:
```
TOOL:metadata_watch
{"path": "/app/testdir"}
```

To watch the CodeGen directory:
```
TOOL:metadata_watch
{"path": "/mnt/c/Sandboxes/CodeGen"}
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

For MCP AI integration use:
```
TOOL:metadata_status
{}
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

## Handling Ambiguous Natural Language Queries

When users provide ambiguous or incomplete natural language requests, the AI should ask clarifying questions before making tool calls.

### Example 1: Ambiguous Query - "Find test files"

**Clarification Questions**:
1. "Would you like me to find files with 'test' in their name, or files that contain the word 'test'?"
2. "Which directory should I search in? Your CodeGen project or the test directory?"

### Example 2: Ambiguous Query - "Create a new file"

**Clarification Questions**:
1. "What should I name the new file?"
2. "Where would you like me to create this file? In your CodeGen project or the test directory?"
3. "What content should I put in the file?"

### Best Practices for Response Design

When presenting API responses to users:

1. **Use friendly, conversational language** instead of technical terms
2. **Simplify technical details** but provide them if they're relevant
3. **Use emojis or formatting** to make file listings more scannable (📁 for folders, 📄 for files)
4. **Round timestamps** to human-friendly formats ("2 hours ago" rather than exact timestamps)
5. **Present file sizes in appropriate units** (KB/MB instead of bytes)
6. **Offer follow-up actions** based on the current context
7. **Handle errors gracefully** with suggestions for remediation

## Using These Prompts with AI Chatbots

### For MCP-Integrated AI Systems:

1. For AI systems using MCP, use the format:
   ```
   TOOL:tool_name
   {"parameter": "value"}
   ```

2. Make sure the tool name matches the endpoint path with slashes replaced by underscores:
   - `/metadata/status` → `TOOL:metadata_status`
   - `/metadata/watch` → `TOOL:metadata_watch`

3. Always include a complete, valid JSON object as the parameter, even for endpoints that don't require parameters (use empty `{}`).

4. For directories and files, always use absolute paths that are within the allowed directories.

### Common MCP Integration Issues:

- **404 Not Found errors**: Check if you're using the correct tool name (e.g., `metadata_status` not `watcher_status`).
- **Parameter errors**: Ensure your JSON is valid and includes all required parameters.
- **Path issues**: Make sure paths are absolute and within allowed directories.

### Complete End-to-End Examples

#### Example 1: "What files are you watching right now?"

**User Query**: "What files are you watching right now?"

**Analysis**: User is asking about watcher status

**MCP Tool Call**:
```
TOOL:metadata_status
{}
```

**User-friendly Response**:
"I'm currently watching 2 directories:
- Your CodeGen project folder
- The test directory

Both directories are being automatically scanned every 5 minutes to detect file changes."

#### Example 2: "Find Python files modified in the last day"

**User Query**: "Find Python files modified in the last day"

**Analysis**: User wants to find files by extension and modification time

**MCP Tool Call**:
```
TOOL:metadata_search
{
  "extensions": [".py"],
  "modified_after": "2025-04-12T21:00:00",
  "path_prefix": "/mnt/c/Sandboxes/CodeGen",
  "limit": 20
}
```

**User-friendly Response**:
"I found 3 Python files modified in the last day:
- main.py (modified 2 hours ago, 245 KB)
- utils.py (modified 4 hours ago, 78 KB)
- test_api.py (modified yesterday at 10:15 PM, 56 KB)"

For more detailed integration guidance, see the [MCP Integration Guide](MCP_INTEGRATION.md).