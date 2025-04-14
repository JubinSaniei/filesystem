# Filesystem MCP

A secure, feature-rich filesystem API for reading, editing, writing, listing, and searching files with access restrictions, metadata indexing, and real-time file watching.

## Features

### Core Functionality
- **File Operations**: Read, write, edit, stream, and search file contents
- **Directory Operations**: Create, list, traverse, and watch directories
- **Metadata Indexing**: Store and query file metadata for fast searches
- **Database Queries**: Execute SQL queries against the metadata database
- **Persistent Metadata**: Database persists between container restarts 
- **Content Search**: Full-text search across files with pagination

### Advanced Features
- **Unlimited File Indexing**: No file count limits when indexing directories
- **Intelligent Ignore Patterns**: Skip directories like node_modules, .git, etc. using patterns similar to .gitignore
- **File System Watcher**: Efficiently track file changes and update the metadata index
  - On-demand directory watching (no auto-watching)
  - Throttled processing to prevent resource spikes
  - Batch processing for better performance
  - Queue system for handling high-volume changes
  - Automatic periodic scans of watched directories
- **Natural Language Support**: Enhanced OpenAPI schema with natural language mappings
  - Endpoint mapping for translating casual user queries to API calls
  - Parameter extraction from natural language requests
  - Common path reference resolution (e.g., "my project folder" → "/path/to/project")
  - Response formatting for user-friendly output
  - Support for both API and MCP tool call formats
- **File Content Caching**: Smart caching system with LRU eviction for better performance
- **Cross-Origin Support**: Properly configured CORS for web UI integration
- **Rate Limiting**: Optional request rate limiting to prevent abuse
- **Performance Monitoring**: Headers for tracking request processing time and memory usage

### Security & Performance
- **Path Normalization**: Prevents directory traversal attacks
- **SQL Injection Prevention**: Secure database query execution
- **Streaming Responses**: Handle large files efficiently
- **Concurrent Processing**: Thread pool for CPU-bound operations
- **Memory Management**: Configurable cache sizes and cleanup intervals

## Directory Structure

```
filesystem/
├── main.py                   # Main entry point that launches the app
├── set_api_url.py            # Script to set the API URL configuration
├── run_tests.py              # Script to run all tests
├── requirements.txt          # Python dependencies
├── Dockerfile                # Docker configuration
├── compose.yaml              # Docker Compose configuration
├── src/                      # Source code directory
│   ├── api/                  # API endpoint modules
│   ├── core/                 # Core application functionality
│   ├── db/                   # Database models and operations
│   ├── utils/                # Utility modules
│   ├── docs/                 # Documentation files
│   └── tests/                # Test files
└── testdir/                  # Test directory for examples and testing
```

## Quick Start

### With Docker

```bash
# Build and run the Docker container
docker build -t filesystem_server .
docker run -d -p 8010:8000 \
  -v /path/to/files:/mnt/c/Sandboxes \
  -v ./testdir:/app/testdir \
  -v ./src/db:/app/src/db \
  -v ./src/docs/ignore.md:/app/src/docs/ignore.md \
  --name filesystem_server filesystem_server
```

Note: The volume mount for `src/db` ensures your metadata database persists between container restarts.

### With Environment Variables

You can configure the Docker container by setting environment variables:

```bash
# Run with environment variables for configuration
docker run -d -p 8010:8000 \
  -e API_HOST=localhost \
  -e API_PORT=8010 \
  -e CACHE_SIZE_MB=200 \
  -e THREAD_POOL_SIZE=20 \
  -v /path/to/files:/mnt/c/Sandboxes \
  -v ./testdir:/app/testdir \
  -v ./src/db:/app/src/db \
  -v ./src/docs/ignore.md:/app/src/docs/ignore.md \
  --name filesystem_server \
  filesystem_server
```

### With Docker Compose

```bash
# Start the application
docker-compose up -d

# Stop the application
docker-compose down
```

The compose.yaml file includes volume mappings to ensure:
- File indexing permissions for mounted directories
- Persistence of metadata database between container restarts 
- Access to ignore patterns file for proper file filtering

### Without Docker

```bash
# Option 1: Run with system Python (if you have all dependencies)
pip install -r requirements.txt
python -m main

# Option 2: Create a virtual environment first (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
python -m main

# Run with additional options
python -m main --host=0.0.0.0 --port=8010 --reload --log-level=debug
```

## API Endpoints

All endpoints in this API support natural language mappings, allowing AI assistants to translate everyday language queries into appropriate API calls. For example, "Show me the contents of config.json" would map to the `/read_file` endpoint with the correct parameters. See the [Natural Language Mapping Guide](src/docs/NATURAL_LANGUAGE_MAPPING.md) for details.

### File Operations

- `POST /read_file` - Read file contents with caching and streaming support
- `POST /write_file` - Write content to a file
- `POST /edit_file` - Apply edits to a file with optional diff preview
- `POST /create_directory` - Create a new directory recursively
- `POST /directory_tree` - Get a recursive directory tree with optional depth limiting
- `POST /delete_path` - Delete a file or directory with option for recursive deletion
- `POST /move_path` - Move or rename a file or directory
- `POST /get_metadata` - Get detailed metadata for a file or directory

### Directory Listing

- `POST /list_directory` - List directory contents with detailed metadata
- `GET /list_allowed_directories` - List directories the API can access

### Search Operations

- `POST /search_content` - Search for text content within files
- `POST /search_files` - Search for files with various criteria
- `POST /metadata_search` - Search files using metadata criteria

### Database Operations

- `POST /database_query` - Execute SQL queries on the metadata database (SELECT only)
- `POST /index_directory` - Index a directory in the metadata database

### File Watcher Operations

- `GET /metadata/status` - Get the current status of the file watcher (correct endpoint; not `/watcher_status`)
- `POST /metadata/watch` - Start watching a directory for changes
- `POST /metadata/unwatch` - Stop watching a directory
- `POST /metadata/scan` - Trigger an immediate scan of watched directories

Note that the correct endpoint to watch a directory is:
```
POST /metadata/watch
Content-Type: application/json

{
  "path": "/path/to/directory"
}
```

Example using curl:
```bash
curl -X POST -H "Content-Type: application/json" -d '{"path": "/mnt/c/Sandboxes/CodeGen"}' http://localhost:8010/metadata/watch
```

Example using Python:
```python
import requests
response = requests.post(
    "http://localhost:8010/metadata/watch",
    json={"path": "/mnt/c/Sandboxes/CodeGen"}
)
print(response.json())
```

For complete examples, see the example scripts in the `examples/` directory:
- `watch_codegen.py` - Example specifically for watching the CodeGen directory
- `file_watcher_example.py` - Complete example of all file watcher operations

The file watcher doesn't watch any directories by default - you must explicitly add directories to watch using the `/metadata/watch` endpoint. Once a directory is being watched, the system will automatically:

1. Detect new, modified, and deleted files
2. Update the metadata database accordingly
3. Scan the watched directories periodically (every 5 minutes by default)
4. Process changes in batches to minimize system resource usage

For detailed examples of file watcher API usage, see the [API Reference](src/docs/API_REFERENCE.md#file-watcher-operations) documentation. For AI chatbot integration using the Model Context Protocol (MCP), see the [MCP Integration Guide](src/docs/MCP_INTEGRATION.md).

## Configuration

The application can be configured in multiple ways:

### Environment Variables

Set these environment variables to configure the application:

- `API_HOST` - Host to bind the server to (default: localhost)
- `API_PORT` - Port to bind the server to (default: 8010)
- `ALLOWED_DIRECTORIES` - Colon-separated list of directories the API is allowed to access
- `CACHE_SIZE_MB` - Maximum size of the file cache in MB (default: 100)
- `THREAD_POOL_SIZE` - Number of worker threads for concurrent operations (default: 10)

### Using .env File

You can create a `.env` file in the project root with the same variables:

```
API_HOST=localhost
API_PORT=8010
ALLOWED_DIRECTORIES=/mnt/c/Sandboxes:/app/testdir
CACHE_SIZE_MB=100
THREAD_POOL_SIZE=10
```

### Configuration Script

For convenience, you can use the provided script to set the API URL by creating or updating the `.env` file:

```bash
# Change the API host and port
python set_api_url.py --host api.example.com --port 8020

# Reset to default values
python set_api_url.py --host localhost --port 8010

# The script will:
# 1. Create or update the .env file in the project root
# 2. Preserve any existing environment variables in the .env file
# 3. Override only the API_HOST and API_PORT variables
```

### Command Line Arguments

When running the application directly, you can use command line arguments:

```bash
python -m main --host 0.0.0.0 --port 8030 --reload --log-level debug
```

## Ignore Patterns

The system uses patterns specified in `src/docs/ignore.md` to exclude files and directories from indexing. This functionality is similar to `.gitignore`. Common directories like these are automatically ignored:

- node_modules
- .git
- __pycache__
- .vs
- .vscode
- build
- dist
- bin
- obj

## Database Management

### About the Metadata Database

The metadata database (`src/db/metadata.db`) persists between container restarts, allowing you to build up a comprehensive index of your files over time. This persistence enables efficient searches and reduces the need to re-index directories.

### Database Queries

You can query the database using the API endpoint `/database_query`. Example SQL query to find the largest files:

```sql
SELECT path, size_bytes FROM file_metadata 
WHERE is_directory = 0 
ORDER BY size_bytes DESC LIMIT 10
```

Example SQL query to count files by extension:

```sql
SELECT extension, COUNT(*) as count 
FROM file_metadata 
WHERE extension IS NOT NULL 
GROUP BY extension 
ORDER BY count DESC
```

### Resetting the Database

For security reasons, database reset is only available within the container and not through the API. To reset the database:

```bash
# Method 1: Using the shell script (recommended)
docker exec -it filesystem_server /app/reset_database.sh

# Method 2: Using the Python utility directly
docker exec -it filesystem_server python -m src.utils.reset_db
```

After resetting, the watcher will automatically reindex watched directories on the next scan.

## Security Considerations

- Only SELECT queries are allowed on the database for security
- Path traversal protections are in place via path normalization
- Rate limiting middleware can be enabled to prevent abuse
- CORS is properly configured for web UI integrations
- File operations are sandboxed to allowed directories only

## Development

### Dependencies

- Python 3.10+
- FastAPI 0.100.0+
- uvicorn[standard]
- pydantic 2.0.0+
- aiofiles 23.1.0+
- SQLAlchemy 2.0.0+
- aiosqlite 0.19.0+
- python-dotenv 1.0.0+
- psutil (optional, for improved performance monitoring)

### Testing

The project includes a comprehensive test suite that verifies all API endpoints:

```bash
# Run all API tests
python -m src.tests.test_all_apis

# Run specific test categories
python -m src.tests.test_all_apis --test basic     # Basic API endpoints
python -m src.tests.test_all_apis --test extended  # Extended API endpoints
python -m src.tests.test_all_apis --test remaining # Remaining API endpoints
python -m src.tests.test_all_apis --test metadata  # Metadata API endpoints

# Individual test scripts are also available
python -m src.tests.verify_api            # Basic API endpoints
python -m src.tests.verify_extended_api   # Extended API endpoints 
python -m src.tests.verify_remaining_api  # Remaining API endpoints
python -m src.tests.verify_metadata_api   # Metadata API endpoints

# Targeted component tests
python -m src.tests.test_ignore           # Tests for ignore patterns
python -m src.tests.test_index            # Tests for directory indexing
python -m src.tests.test_search           # Tests for file search functionality
```

### Documentation

For more detailed documentation, please see:

- [API Reference](src/docs/API_REFERENCE.md) - Detailed API documentation
- [Database Query Guide](src/docs/DATABASE_QUERY_GUIDE.md) - Guide for SQL queries
- [Database Management](src/docs/DATABASE_MANAGEMENT.md) - Database management and reset guide
- [Ignore Patterns Guide](src/docs/IGNORE_PATTERNS_GUIDE.md) - Guide for ignore patterns
- [API Prompts](src/docs/API_PROMPTS.md) - Example prompts for API usage
- [MCP Integration Guide](src/docs/MCP_INTEGRATION.md) - Guide for AI chatbot integration using MCP
- [Natural Language Mapping](src/docs/NATURAL_LANGUAGE_MAPPING.md) - Comprehensive guide for translating natural language to API calls
- [OpenAPI NL Usage](src/docs/OPENAPI_NL_USAGE.md) - How to use the enhanced OpenAPI schema with natural language mappings