# Database Query API Guide

The Database Query API allows you to execute SQL queries directly on the metadata database. This guide provides examples and best practices for using this powerful feature.

## Basic Usage

Send a POST request to `/database_query` with a JSON body containing your query:

```json
{
  "query": "SELECT * FROM file_metadata LIMIT 10",
  "limit": 100
}
```

## Query Parameters

- `query` (required): SQL query string (SELECT only)
- `params` (optional): Parameters for the query (for prepared statements)
- `limit` (optional): Maximum number of results to return (default: 1000, max: 10000)

## Security Restrictions

For security reasons:

- Only SELECT queries are allowed
- Dangerous keywords like INSERT, UPDATE, DELETE, DROP, etc. are blocked
- A LIMIT clause is automatically added if not present
- Maximum result limit is enforced

## Example Queries

### Get all files with a specific extension

```json
{
  "query": "SELECT * FROM file_metadata WHERE extension = '.py' LIMIT 100"
}
```

### Find the largest files

```json
{
  "query": "SELECT path, size_bytes FROM file_metadata WHERE is_directory = 0 ORDER BY size_bytes DESC LIMIT 20"
}
```

### Get files modified in the last day

```json
{
  "query": "SELECT path FROM file_metadata WHERE modified_time > datetime('now', '-1 day')"
}
```

### Count files by extension

```json
{
  "query": "SELECT extension, COUNT(*) as count FROM file_metadata WHERE extension IS NOT NULL GROUP BY extension ORDER BY count DESC"
}
```

### Find directories with the most files

```json
{
  "query": "SELECT parent_dir, COUNT(*) as file_count FROM file_metadata GROUP BY parent_dir ORDER BY file_count DESC LIMIT 20"
}
```

### Find files containing specific text in their path

```json
{
  "query": "SELECT * FROM file_metadata WHERE path LIKE '%config%' AND is_directory = 0"
}
```

### Search for files in a specific directory

```json
{
  "query": "SELECT * FROM file_metadata WHERE parent_dir = '/app/src' AND is_directory = 0"
}
```

## Database Schema

The `file_metadata` table has the following columns:

- `id`: Primary key
- `path`: Absolute file path (unique)
- `parent_dir`: Parent directory path
- `name`: File or directory name
- `extension`: File extension (NULL for directories)
- `is_directory`: Boolean flag (1 for directories, 0 for files)
- `size_bytes`: File size in bytes (NULL for directories)
- `created_time`: Creation timestamp
- `modified_time`: Last modification timestamp
- `last_indexed`: When the file was last indexed
- `content_summary`: Optional summary of file contents
- `mime_type`: MIME type of the file

## Using with JavaScript

Example of calling the API from JavaScript:

```javascript
async function queryDatabase(sqlQuery) {
  const API_URL = process.env.API_URL || 'http://localhost:8010';
  const response = await fetch(`${API_URL}/database_query`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      query: sqlQuery,
      limit: 1000
    })
  });
  
  return await response.json();
}

// Example usage
queryDatabase("SELECT extension, COUNT(*) as count FROM file_metadata GROUP BY extension")
  .then(result => {
    console.log(result.rows);
  });
```

## Response Format

The API returns a JSON object with the following properties:

- `status`: "success" or "error"
- `rows`: Array of result objects
- `row_count`: Number of rows returned
- `execution_time_ms`: Query execution time in milliseconds
- `query`: The executed query (including any modifications like added LIMIT)

## Pagination

For large result sets, use LIMIT and OFFSET in your query:

```json
{
  "query": "SELECT * FROM file_metadata LIMIT 100 OFFSET 200"
}
```

## Performance Tips

- Always include a WHERE clause for large tables
- Use indexes (path, name, extension, is_directory) in your queries
- Avoid SELECT * for large result sets, specify only needed columns
- Add ORDER BY only when needed as it affects performance