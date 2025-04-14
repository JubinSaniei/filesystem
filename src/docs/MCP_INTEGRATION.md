# MCP Integration Guide for Filesystem Server

This document provides guidance on integrating the Filesystem Server with AI chatbots using the Model Context Protocol (MCP), focusing on natural user interactions.

## Overview

The Filesystem Server acts as an MCP provider, allowing AI chatbots to interact with the filesystem through standardized API endpoints. Users will interact with the AI using natural language (like "what is the watcher status?" or "start watching my CodeGen folder"), and the AI should translate these requests into the appropriate tool calls.

## MCP Tool Definitions

When integrating with an AI system, the filesystem endpoints should be defined as MCP tools with the following format:

```json
{
  "name": "metadata_status",
  "description": "Get the current status of the file watcher system.",
  "input_schema": {},
  "authentication_required": false,
  "rate_limited": false
}
```

```json
{
  "name": "metadata_watch",
  "description": "Start watching a directory for file changes.",
  "input_schema": {
    "type": "object",
    "properties": {
      "path": {
        "type": "string",
        "description": "Directory path to watch for changes"
      }
    },
    "required": ["path"]
  },
  "authentication_required": false,
  "rate_limited": false
}
```

## Endpoint Naming Conventions

To avoid confusion, ensure that MCP tool names match the API endpoints with underscores instead of slashes:

| API Endpoint | MCP Tool Name |
|--------------|---------------|
| `/metadata/status` | `metadata_status` |
| `/metadata/watch` | `metadata_watch` |
| `/metadata/unwatch` | `metadata_unwatch` |
| `/metadata/scan` | `metadata_scan` |
| `/read_file` | `read_file` |
| `/write_file` | `write_file` |
| etc. | etc. |

## Tool Invocation Format

AI chatbots should invoke the filesystem tools using this format:

```
TOOL:metadata_watch
{"path": "/mnt/c/Sandboxes/CodeGen"}
```

NOT like this (incorrect):
```
TOOL:watch_directory_watch_directory_post
{"path": "/mnt/c/Sandboxes/CodeGen"}
```

## Client-Side Integration

When integrating with an AI chatbot, ensure that:

1. The client is configured with the correct base URL for the filesystem server
2. Tool names match the actual API endpoint names (with slashes replaced by underscores)
3. Parameters match the expected JSON structure for each endpoint

## Troubleshooting Common Issues

### "Not Found" errors (HTTP 404)

If you see errors like:
```
TOOL:watcher_status_watcher_status_get
{"error": "HTTP error! Status: 404. Message: {\"detail\":\"Not Found\"}"}
```

Check:
- The tool name should be `metadata_status`, not `watcher_status_watcher_status_get`
- The endpoint should be `/metadata/status`

### Parameter Structure Issues

If you see errors related to parameters, ensure:
- All required parameters are provided
- Parameter names match exactly (e.g., "path" not "dir" or "directory")
- Parameter types are correct (strings for paths, numbers for limits, etc.)

## Natural Language to MCP Tool Mapping

Users will interact with the AI using natural language. The AI should recognize these common patterns and convert them to the appropriate MCP tool calls.

### Common User Queries and Corresponding Tool Calls

| User Query | Expected AI Response | MCP Tool Call |
|------------|---------------------|---------------|
| "What is the watcher status?" | Display current watch status showing which directories are being monitored | `TOOL:metadata_status` |
| "What directories are being watched?" | Show list of watched directories | `TOOL:metadata_status` |
| "Start watching my CodeGen folder" | Acknowledge and start watching the CodeGen directory | `TOOL:metadata_watch` with path `/mnt/c/Sandboxes/CodeGen` |
| "Monitor changes in [directory]" | Confirm watching that directory | `TOOL:metadata_watch` with the specified path |
| "Stop watching [directory]" | Confirm unwatching the directory | `TOOL:metadata_unwatch` with the specified path |
| "Show me what's in [directory]" | Display directory contents | `TOOL:list_directory` with the specified path |
| "Read file [path]" | Show file contents | `TOOL:read_file` with the specified path |
| "Search for [text] in my files" | Show search results | `TOOL:search_content` with appropriate parameters |
| "Find all [file type] files" | Show matching files | `TOOL:search_files` or `TOOL:metadata_search` |

### Example User Interactions

#### Checking Watcher Status

**User**: "What directories am I currently watching?"

**AI should**:
1. Recognize this as a request for watcher status
2. Make this tool call (invisible to user):
```
TOOL:metadata_status
{}
```
3. Display results to user in a friendly format:
"You are currently watching these directories:
- /mnt/c/Sandboxes/CodeGen
- /app/testdir
The watcher is active and scanning every 5 minutes."

#### Watching a Directory

**User**: "Start watching my CodeGen folder for changes"

**AI should**:
1. Recognize the intent to watch a specific directory
2. Know the correct path for CodeGen
3. Make this tool call (invisible to user):
```
TOOL:metadata_watch
{"path": "/mnt/c/Sandboxes/CodeGen"}
```
4. Display a confirmation message:
"I've started watching your CodeGen folder for changes. I'll automatically track any new, modified, or deleted files."

## Best Practices for AI-User Interactions

1. **Recognize natural language intents**: The AI should understand common user queries like "check watcher status" or "start watching my project folder" without requiring exact endpoint names.

2. **Handle ambiguity**: If a user asks something like "watch my files," the AI should ask for clarification about which directory they want to watch.

3. **Remember common paths**: The AI should remember important paths like `/mnt/c/Sandboxes/CodeGen` when the user refers to them casually as "my CodeGen folder."

4. **Use user-friendly language**: Present API responses in natural language, not raw JSON.

5. **Handle errors gracefully**: When API errors occur, the AI should explain the issue in simple terms and suggest solutions.

6. **Verify operations**: After watching a directory, the AI should automatically show the updated status to confirm the action worked.

7. **Provide helpful contextual information**: When showing watcher status, the AI should also explain what that means (e.g., "This means any changes to files in these directories will be automatically detected").

8. **Maintain conversation context**: Remember previous actions in the conversation to provide continuity (e.g., "You're now watching 3 directories, including the CodeGen folder you just added").

9. **Suggest related actions**: After completing one task, suggest logical next steps (e.g., "Would you like me to scan these directories now to build the initial index?").

## Sample User Conversations

### Example 1: Watching the CodeGen Directory

**User**: "Can you monitor my CodeGen project for file changes?"

**AI**: "I'd be happy to monitor your CodeGen project for changes. Let me set that up for you."

[AI makes this tool call behind the scenes]
```
TOOL:metadata_watch
{"path": "/mnt/c/Sandboxes/CodeGen"}
```

**AI**: "I'm now watching your CodeGen project at `/mnt/c/Sandboxes/CodeGen`. I'll automatically detect when files are added, modified, or deleted. Would you like me to scan the directory now to build the initial index?"

**User**: "Yes, please do that."

[AI makes this tool call behind the scenes]
```
TOOL:metadata_scan
{"path": "/mnt/c/Sandboxes/CodeGen", "force": true}
```

**AI**: "I've completed the initial scan of your CodeGen project. The files have been indexed and I'll continue monitoring for changes. You can ask me to search or list files in this directory at any time."

### Example 2: Checking Watch Status

**User**: "What are you watching right now?"

[AI makes this tool call behind the scenes]
```
TOOL:metadata_status
{}
```

**AI**: "I'm currently watching these directories:
- `/mnt/c/Sandboxes/CodeGen`
- `/app/testdir`

The watcher is active and these directories are being automatically scanned every 5 minutes for changes. Would you like me to add another directory to watch?"

### Example 3: Handling Errors

**User**: "Start watching my Projects folder"

[AI makes this tool call behind the scenes]
```
TOOL:metadata_watch
{"path": "/mnt/c/Projects"}
```

[API returns error about path not being allowed or not existing]

**AI**: "I wasn't able to start watching your Projects folder because the path `/mnt/c/Projects` either doesn't exist or isn't in the list of allowed directories. The allowed directories are:
- `/mnt/c/Sandboxes`
- `/app/testdir`

Would you like me to watch a specific directory within these allowed locations instead?"

## Testing the Integration

To verify your MCP integration is working with natural language, try these user queries:

1. "What directories are you currently watching?"
2. "Start watching my CodeGen folder"
3. "Show me the status of the file watcher"
4. "Stop watching the test directory"

The AI should translate these into the appropriate MCP tool calls without the user needing to know any technical endpoint details.

## Additional Resources

For a comprehensive mapping of natural language queries to technical endpoints, see the [Natural Language Mapping Guide](NATURAL_LANGUAGE_MAPPING.md). This document provides detailed examples of:

- Common user questions and their MCP tool mappings
- How to translate technical responses into user-friendly language
- Handling ambiguous queries
- Common path references and their filesystem mappings

This guide is essential for setting up AI systems to properly interpret user intent and map it to the correct filesystem operations.