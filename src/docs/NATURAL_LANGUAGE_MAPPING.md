# Natural Language Mapping Guide for API Endpoints

This guide provides comprehensive mapping between natural language queries and API endpoints for AI chatbot integration using MCP.

## Core Concepts

Users will interact with the AI using natural language, not technical terminology. This guide helps translate between:
1. Natural language queries users will ask
2. The correct MCP tool calls to make
3. How to present the technical responses in user-friendly language

## Complete Endpoint Mapping

### Watcher Status Endpoint

**MCP Tool Call**: `TOOL:metadata_status`

**Natural Language Variants**:
- "What are you watching?"
- "What directories are being monitored?"
- "Check watcher status"
- "Is the file watcher active?"
- "Show me all watched directories"
- "What folders are you tracking?"
- "Are you watching any directories now?"

**Parameter Structure**:
```json
{}
```

**Response Transformation**:
```
Example technical response:
{
  "status": "active",
  "watched_directories": ["/app/testdir", "/mnt/c/Sandboxes/CodeGen"],
  "directory_count": 2,
  "last_scans": {
    "/app/testdir": {
      "timestamp": "2025-04-13T21:51:56.957596",
      "seconds_ago": 20,
      "next_scan_in": 279
    }
  },
  "scan_interval_seconds": 300
}

User-friendly response:
"I'm currently watching 2 directories for changes:
- Your CodeGen project folder
- The test directory

These directories are automatically scanned every 5 minutes. The last scan of the test directory was 20 seconds ago, and the next scan will happen in about 4 minutes."
```

### Watch Directory Endpoint

**MCP Tool Call**: `TOOL:metadata_watch`

**Natural Language Variants**:
- "Watch my CodeGen folder"
- "Start monitoring my project directory"
- "Track changes in [directory]"
- "Keep an eye on the files in [folder]"
- "Watch for changes in [path]"
- "Start watching [directory]"
- "Monitor [folder]"

**Parameter Structure**:
```json
{"path": "/path/to/directory"}
```

**Common Directory Mappings**:
- "my CodeGen folder" → "/mnt/c/Sandboxes/CodeGen"
- "the test directory" → "/app/testdir"
- "the project folder" → "/mnt/c/Sandboxes/CodeGen"

**Response Transformation**:
```
Example technical response:
{
  "status": "success",
  "message": "Now watching directory: /mnt/c/Sandboxes/CodeGen",
  "watched_directory_count": 2
}

User-friendly response:
"I'm now watching your CodeGen folder for changes. I'll automatically detect when files are added, modified, or deleted."
```

### Unwatch Directory Endpoint

**MCP Tool Call**: `TOOL:metadata_unwatch`

**Natural Language Variants**:
- "Stop watching [directory]"
- "Don't monitor [folder] anymore"
- "Remove [directory] from watched list"
- "Unwatch [folder]"
- "Stop tracking changes in [path]"
- "Disable watcher for [directory]"

**Parameter Structure**:
```json
{"path": "/path/to/directory"}
```

**Response Transformation**:
```
Example technical response:
{
  "status": "success",
  "message": "Stopped watching directory: /app/testdir",
  "watched_directory_count": 1
}

User-friendly response:
"I've stopped watching the test directory. I'm still watching 1 other directory."
```

### Scan Directories Endpoint

**MCP Tool Call**: `TOOL:metadata_scan`

**Natural Language Variants**:
- "Scan the watched directories"
- "Update the file index"
- "Check for new files now"
- "Run a manual scan"
- "Scan for changes"
- "Update the file database"
- "Rescan watched folders"

**Parameter Structure**:
```json
{"force": true}
```

**Response Transformation**:
```
Example technical response:
{
  "status": "success",
  "message": "Successfully scanned 2 directories",
  "scanned_directories": ["/app/testdir", "/mnt/c/Sandboxes/CodeGen"]
}

User-friendly response:
"I've completed a scan of all watched directories. The file database has been updated with any recent changes."
```

### Read File Endpoint

**MCP Tool Call**: `TOOL:read_file`

**Natural Language Variants**:
- "Show me the contents of [file]"
- "What's in [file]?"
- "Read [file]"
- "Display the content of [file]"
- "Open [file]"
- "Show [file]"
- "Let me see [file]"

**Parameter Structure**:
```json
{"path": "/path/to/file", "stream": false}
```

**Response Transformation**:
```
Example technical response:
{
  "content": "This is a test file for searching\n"
}

User-friendly response:
"Here's the content of test1.txt:

This is a test file for searching"
```

### List Directory Endpoint

**MCP Tool Call**: `TOOL:list_directory`

**Natural Language Variants**:
- "What's in [directory]?"
- "List files in [folder]"
- "Show me all files in [directory]"
- "What files are in [folder]?"
- "Show contents of [directory]"
- "List everything in [folder]"
- "What's inside [directory]?"

**Parameter Structure**:
```json
{
  "path": "/path/to/directory",
  "include_hidden": false,
  "sort_by": "name",
  "sort_order": "asc"
}
```

**Response Transformation**:
```
Example technical response: (simplified for brevity)
{
  "path": "/app/testdir",
  "items": [
    {
      "name": "test1.txt",
      "path": "/app/testdir/test1.txt",
      "is_directory": false,
      "size_bytes": 34,
      "modified_time": "2025-04-12T20:20:08.579652+00:00"
    },
    ...more items...
  ],
  "item_count": 8
}

User-friendly response:
"The test directory contains 8 items:

📄 test1.txt (34 bytes, modified Apr 12)
📄 test2.txt (47 bytes, modified Apr 12)
📄 test3.txt (28 bytes, modified Apr 12)
📄 new_file.txt (47 bytes, modified Apr 12)
📄 metadata_test.txt (32 bytes, modified Apr 13)
📄 watcher_test.txt (37 bytes, modified Apr 13)
📄 moved_file.txt (23 bytes, modified Apr 12)
📁 new_directory (created Apr 12)"
```

### Get Metadata Endpoint

**MCP Tool Call**: `TOOL:get_metadata`

**Natural Language Variants**:
- "Get information about [file]"
- "Show details of [file]"
- "When was [file] last modified?"
- "What's the size of [file]?"
- "Tell me about [file]"
- "File info for [path]"
- "Get metadata for [file]"

**Parameter Structure**:
```json
{"path": "/path/to/file"}
```

**Response Transformation**:
```
Example technical response:
{
  "path": "/app/testdir/test1.txt",
  "type": "file",
  "size_bytes": 34,
  "modification_time_utc": "2025-04-12T20:20:08.579652+00:00",
  "creation_time_utc": "2025-04-12T20:20:08.579652+00:00"
}

User-friendly response:
"File: test1.txt
Type: Text file
Size: 34 bytes
Created: April 12, 2025
Last modified: April 12, 2025"
```

### Search Files Endpoint

**MCP Tool Call**: `TOOL:search_files`

**Natural Language Variants**:
- "Find files named [pattern]"
- "Search for files matching [pattern]"
- "Find [pattern] files"
- "Look for files called [pattern]"
- "List files matching [pattern]"
- "Show me files with names like [pattern]"

**Parameter Structure**:
```json
{
  "path": "/path/to/directory",
  "pattern": "*.txt",
  "recursive": true,
  "excludePatterns": [],
  "pagination": {"offset": 0, "limit": 20}
}
```

**Natural Language to Parameter Mapping**:
- "all text files" → `"pattern": "*.txt"`
- "Python files" → `"pattern": "*.py"`
- "files created today" → `"modified_after": "today's date in ISO format"`
- "files larger than 1MB" → `"min_size": 1048576`

**Response Transformation**:
```
Example technical response:
{
  "items": [
    {
      "name": "test1.txt",
      "path": "/app/testdir/test1.txt",
      "type": "file",
      "size_bytes": 34,
      "modified_time": "2025-04-12T20:20:08.579652"
    },
    ...more items...
  ],
  "total": 7,
  "has_more": false
}

User-friendly response:
"I found 7 text files:
- test1.txt
- test2.txt
- test3.txt
- new_file.txt
- metadata_test.txt
- watcher_test.txt
- moved_file.txt"
```

### Search Content Endpoint

**MCP Tool Call**: `TOOL:search_content`

**Natural Language Variants**:
- "Search for [text] in files"
- "Find files containing [text]"
- "Look for [text] inside files"
- "Which files contain [text]?"
- "Search content for [text]"
- "Find occurrences of [text]"
- "Search for [text] in the codebase"

**Parameter Structure**:
```json
{
  "path": "/path/to/directory",
  "search_query": "search text",
  "recursive": true,
  "file_pattern": "*.txt",
  "pagination": {"offset": 0, "limit": 100}
}
```

**Response Transformation**:
```
Example technical response:
{
  "items": [
    {
      "file_path": "/app/testdir/test1.txt",
      "line_number": 1,
      "line_content": "This is a test file for searching"
    },
    ...more items...
  ],
  "total": 5
}

User-friendly response:
"I found 'test' in 5 files:

1. test1.txt (line 1): This is a test file for searching
2. new_file.txt (line 1): This is an edited test file created by the API.
3. watcher_test.txt (line 1): Testing file watcher change detection
4. metadata_test.txt (line 1): This file tests the metadata API
5. test3.txt (line 1): Testing a different pattern"
```

### Create Directory Endpoint

**MCP Tool Call**: `TOOL:create_directory`

**Natural Language Variants**:
- "Create a directory called [name]"
- "Make a new folder at [path]"
- "Create directory [name]"
- "Make folder [name]"
- "Create a new directory at [path]"
- "Add folder [name]"

**Parameter Structure**:
```json
{"path": "/path/to/new/directory"}
```

**Response Transformation**:
```
Example technical response:
{
  "message": "Successfully created directory /app/testdir/new_folder"
}

User-friendly response:
"I've created a new folder called 'new_folder' in the test directory."
```

### Write File Endpoint

**MCP Tool Call**: `TOOL:write_file`

**Natural Language Variants**:
- "Create a file called [name] with content [content]"
- "Write [content] to [file]"
- "Save this content to [file]"
- "Create a new file [name]"
- "Make a file with [content]"
- "Save [content] as [filename]"
- "Append [content] to [file]"
- "Add [content] to the end of [file]"
- "Update [file] by adding [content] at the end"
- "Modify [file] and append [content]"
- "Prepend [content] to [file]"
- "Add [content] to the beginning of [file]"

**Parameter Structure**:
```json
{
  "path": "/path/to/file.txt",
  "content": "Content to write to the file.",
  "mode": "overwrite"  // Options: "overwrite" (default), "append", or "prepend"
}
```

**Natural Language to Parameter Mapping**:
- "append to the file" → `"mode": "append"`
- "add to the end" → `"mode": "append"`
- "prepend to the file" → `"mode": "prepend"`
- "add to the beginning" → `"mode": "prepend"`
- "overwrite the file" → `"mode": "overwrite"`

**Special Handling**:
- When using append mode, the system automatically adds a newline if the file doesn't end with one, ensuring proper formatting.
- This means users can simply say "append 'text' to file" without worrying about newline handling.

**Response Transformation**:
```
Example technical response:
{
  "message": "Successfully wrote to /app/testdir/new_note.txt"
}

User-friendly responses:
1. For overwrite mode:
   "I've created a new file called 'new_note.txt' in the test directory with the content you provided."

2. For append mode:
   "I've appended the text to the end of 'existing_file.txt' in the test directory."

3. For prepend mode:
   "I've added the text to the beginning of 'existing_file.txt' in the test directory."
```

### Edit File Endpoint

**MCP Tool Call**: `TOOL:edit_file`

**Natural Language Variants**:
- "Change [old text] to [new text] in [file]"
- "Replace [old text] with [new text] in [file]"
- "Edit [file] to change [old text] to [new text]"
- "Update [file] by replacing [old text] with [new text]"
- "Modify [file] to say [new text] instead of [old text]"

**Parameter Structure**:
```json
{
  "path": "/path/to/file.txt",
  "edits": [
    {
      "oldText": "text to replace",
      "newText": "replacement text"
    }
  ],
  "dryRun": false
}
```

**Response Transformation**:
```
Example technical response:
{
  "message": "Successfully edited file /app/testdir/test1.txt"
}

User-friendly response:
"I've updated the file 'test1.txt'. I replaced 'text to replace' with 'replacement text'."
```

### Metadata Search Endpoint

**MCP Tool Call**: `TOOL:metadata_search`

**Natural Language Variants**:
- "Find files with extension [ext]"
- "Search for [file type] files"
- "Find files modified [time period]"
- "Search for files related to [topic]"
- "Find files containing [term] in their name"
- "Search for [size] files"

**Parameter Structure**:
```json
{
  "query": "search term",
  "extensions": [".txt", ".md"],
  "is_directory": false,
  "min_size": null,
  "max_size": null,
  "modified_after": null,
  "modified_before": null,
  "path_prefix": "/app/testdir",
  "limit": 20,
  "offset": 0
}
```

**Natural Language to Parameter Mapping**:
- "large files" → `"min_size": 1048576` (1MB)
- "small files" → `"max_size": 1024` (1KB)
- "text files" → `"extensions": [".txt"]`
- "document files" → `"extensions": [".docx", ".pdf", ".md", ".txt"]`
- "media files" → `"extensions": [".jpg", ".png", ".mp3", ".mp4"]`
- "code files" → `"extensions": [".py", ".js", ".java", ".cpp", ".h"]`

**Response Transformation**:
```
Example technical response:
{
  "items": [
    {
      "id": 1,
      "path": "/app/testdir/test1.txt",
      "name": "test1.txt",
      "extension": ".txt",
      "is_directory": false,
      "size_bytes": 34,
      "modified_time": "2025-04-12T20:20:08.579652"
    },
    ...more items...
  ],
  "total": 5
}

User-friendly response:
"I found 5 text files with 'test' in their name or content:
- test1.txt (34 bytes)
- test2.txt (47 bytes)
- test3.txt (28 bytes)
- metadata_test.txt (32 bytes)
- watcher_test.txt (37 bytes)"
```

### Delete Path Endpoint

**MCP Tool Call**: `TOOL:delete_path`

**Natural Language Variants**:
- "Delete [file/folder]"
- "Remove [file/folder]"
- "Get rid of [file/folder]"
- "Delete the file at [path]"
- "Remove the directory [name]"
- "Delete all files in [directory]"

**Parameter Structure**:
```json
{
  "path": "/path/to/delete",
  "recursive": true,
  "confirm_delete": true
}
```

**Response Transformation**:
```
Example technical response:
{
  "message": "Successfully deleted file: /app/testdir/temp_file.txt"
}

User-friendly response:
"I've deleted the file 'temp_file.txt' from the test directory."
```

### Move Path Endpoint

**MCP Tool Call**: `TOOL:move_path`

**Natural Language Variants**:
- "Move [source] to [destination]"
- "Rename [source] to [destination]"
- "Move the file [source] to [destination]"
- "Relocate [source] to [destination]"
- "Change the name of [source] to [destination]"
- "Move files from [source] to [destination]"

**Parameter Structure**:
```json
{
  "source_path": "/path/to/source",
  "destination_path": "/path/to/destination"
}
```

**Response Transformation**:
```
Example technical response:
{
  "message": "Successfully moved '/app/testdir/source.txt' to '/app/testdir/destination.txt'"
}

User-friendly response:
"I've moved 'source.txt' to 'destination.txt' in the test directory."
```

## Common User Questions with Complete MCP Tool Flow

### Example 1: "What files are you watching right now?"

**Analysis**: User is asking about watcher status

**MCP Tool Call**:
```
TOOL:metadata_status
{}
```

**Response Processing**:
1. Check if status is "active" or "inactive"
2. Get list of watched directories
3. Format into user-friendly message
4. If no directories are watched, explain how to start watching

**User-friendly Response**:
"I'm currently watching 2 directories:
- Your CodeGen project folder
- The test directory

Both directories are being automatically scanned every 5 minutes to detect file changes."

### Example 2: "Find Python files modified in the last day"

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

**Response Processing**:
1. Extract list of files from items array
2. Format into concise list with relevant details
3. Mention total count

**User-friendly Response**:
"I found 3 Python files modified in the last day:
- main.py (modified 2 hours ago, 245 KB)
- utils.py (modified 4 hours ago, 78 KB)
- test_api.py (modified yesterday at 10:15 PM, 56 KB)"

### Example 3: "Search for 'authentication' in the CodeGen project"

**Analysis**: User wants to search file content

**MCP Tool Call**:
```
TOOL:search_content
{
  "path": "/mnt/c/Sandboxes/CodeGen",
  "search_query": "authentication",
  "recursive": true,
  "pagination": {"offset": 0, "limit": 10}
}
```

**Response Processing**:
1. Extract matched lines with context
2. Group by file
3. Format into readable results

**User-friendly Response**:
"I found 'authentication' mentioned in 3 files:

📄 auth.py:
- Line 15: def validate_authentication(token):
- Line 42: class Authentication:
- Line 105: # TODO: Implement OAuth authentication

📄 api.py:
- Line 27: # Authentication middleware
- Line 145: if authentication_required and not user.is_authenticated:

📄 README.md:
- Line 53: ## Authentication

Would you like me to show more context around these matches?"

## Handling Ambiguity in Natural Language Queries

For ambiguous queries, the AI should ask for clarification before making tool calls.

### Ambiguous Query: "Find test files"

**Clarification Questions**:
1. "Would you like me to find files with 'test' in their name, or files that contain the word 'test'?"
2. "Which directory should I search in? Your CodeGen project or the test directory?"

### Ambiguous Query: "Create a new file"

**Clarification Questions**:
1. "What should I name the new file?"
2. "Where would you like me to create this file? In your CodeGen project or the test directory?"
3. "What content should I put in the file?"

## Common Path References

These are common ways users might refer to paths, which should be translated to actual filesystem paths:

| User Reference | Filesystem Path |
|----------------|----------------|
| "my CodeGen project" | "/mnt/c/Sandboxes/CodeGen" |
| "CodeGen folder" | "/mnt/c/Sandboxes/CodeGen" |
| "project directory" | "/mnt/c/Sandboxes/CodeGen" |
| "test directory" | "/app/testdir" |
| "test folder" | "/app/testdir" |
| "root directory" | "/" |

## Best Practices for AI Response Design

When presenting API responses to users:

1. **Use friendly, conversational language** instead of technical terms
2. **Simplify technical details** but provide them if they're relevant
3. **Use emojis or formatting** to make file listings more scannable (📁 for folders, 📄 for files)
4. **Round timestamps** to human-friendly formats ("2 hours ago" rather than exact timestamps)
5. **Present file sizes in appropriate units** (KB/MB instead of bytes)
6. **Offer follow-up actions** based on the current context
7. **Remember previous context** in the conversation
8. **Handle errors gracefully** with suggestions for remediation

## Using the nl_mapping Helper Function

For consistency when adding natural language mappings to API endpoints, use the `nl_mapping` helper function from `src/utils/nl_mapping.py`:

```python
from src.utils.nl_mapping import nl_mapping, COMMON_PATHS, COMMON_PARAMETER_MAPPINGS

@app.post("/example_endpoint", 
    summary="Example endpoint",
    description="""
    Description of the endpoint.
    
    ## Natural Language Queries
    - "Example query [parameter]"
    - "Another example query [parameter]"
    """,
    openapi_extra=nl_mapping(
        queries=[
            "example query",
            "another example query"
        ],
        parameter_mappings={
            "parameter_name": ["alternative name", "another way to say it"]
        },
        response_template="I have performed the action on {parameter_name}.",
        common_paths=COMMON_PATHS
    )
)
```

### Reusable Components

The `nl_mapping.py` module provides common reusable components:

#### COMMON_PATHS

```python
COMMON_PATHS = {
    "my CodeGen folder": "/mnt/c/Sandboxes/CodeGen",
    "the CodeGen project": "/mnt/c/Sandboxes/CodeGen",
    "my project": "/mnt/c/Sandboxes/CodeGen",
    "the test directory": "/app/testdir",
    "test folder": "/app/testdir"
}
```

#### COMMON_PARAMETER_MAPPINGS

```python
COMMON_PARAMETER_MAPPINGS = {
    "directory": ["folder", "path", "location", "directory"],
    "file": ["document", "text file", "file"],
    "recursive": ["include subdirectories", "search recursively", "look in subfolders"]
}
```

Use these to maintain consistency across all endpoint mappings.