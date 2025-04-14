# Using Natural Language Mappings in OpenAPI Schema

This document explains how to use the enhanced OpenAPI schema with natural language mappings.

## Overview

The Filesystem API's OpenAPI schema has been enhanced with natural language mappings that help AI systems translate user queries into the appropriate API calls. These mappings are provided through custom OpenAPI extensions:

- `x-natural-language-queries`: Contains natural language information for each endpoint
- `x-natural-language-enabled`: Flag in the schema info section indicating NL support

## Schema Structure

Each enhanced endpoint includes an `openapi_extra` field with the following structure:

```json
"openapi_extra": {
  "x-natural-language-queries": {
    "intents": [
      "what are you watching",
      "what directories are being monitored",
      "check watcher status"
    ],
    "parameter_mappings": {
      "path": ["directory", "folder", "location"]
    },
    "response_template": "I'm currently watching {directory_count} directories: {watched_directories}. The watcher is {status}.",
    "common_paths": {
      "my CodeGen folder": "/mnt/c/Sandboxes/CodeGen"
    }
  }
}
```

## Components

1. **Intents**: Array of natural language phrases that map to this endpoint
2. **Parameter Mappings**: Dictionary mapping parameter names to natural language alternatives
3. **Response Template**: Template for formatting the response in natural language
4. **Common Paths**: Dictionary mapping natural language references to filesystem paths

## How AI Systems Should Use This Information

When an AI system accesses the OpenAPI schema at `/openapi.json`, it should:

1. **Extract Intents**: For each endpoint, extract the list of intents to build a mapping between natural language queries and API endpoints

2. **Analyze User Queries**: When receiving a user query, compare it against the intents for each endpoint to determine the most appropriate endpoint to call

3. **Parameter Extraction**: 
   - Use the parameter mappings to identify parameter values in the user query
   - Check for common path references and replace them with the actual filesystem paths

4. **Response Formatting**:
   - Use the response template to format the API response in a user-friendly way
   - Substitute values from the API response into the template placeholders

## Example Flow

1. User asks: "What directories are you watching?"

2. AI system:
   - Fetches OpenAPI schema from `/openapi.json`
   - Matches query against intents for all endpoints
   - Finds a match with `/metadata/status` endpoint intents
   - Makes a GET request to `/metadata/status`
   - Receives JSON response
   - Uses response template to format a natural language response:
     "I'm currently watching 2 directories: /app/testdir and /mnt/c/Sandboxes/CodeGen. The watcher is active."

## Testing and Validation

To verify that your OpenAPI schema includes the natural language mappings, you can:

1. Access the `/openapi.json` endpoint and check for the presence of `x-natural-language-queries` extensions
2. Run the provided test script: `python -m src.tests.test_openapi_nl_mappings`

## Important Endpoints with NL Mappings

The following key endpoints have been enhanced with natural language mappings:

- `GET /metadata/status`: Get watcher status
- `POST /metadata/watch`: Start watching a directory
- `POST /metadata/unwatch`: Stop watching a directory
- `POST /metadata/scan`: Trigger manual scan of watched directories
- `GET /list_allowed_directories`: List access-permitted directories

Additional endpoints can be enhanced following the same pattern.