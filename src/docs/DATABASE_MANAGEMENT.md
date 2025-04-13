# Database Management Guide

This guide explains how to manage the metadata database used by the Filesystem service.

## About metadata.db

The `metadata.db` file is an SQLite database created in the `/src/db/` directory that stores information about files and directories that the system has indexed. It contains metadata like:

- File paths
- File sizes
- Creation and modification times 
- File extensions
- MIME types
- Directory information

This database enables quick searching and filtering of files without having to scan the filesystem repeatedly, which greatly improves performance for search operations.

## Querying the Database

You can query the database using the API endpoint:

```
POST /metadata/database_query
{
  "query": "SELECT * FROM file_metadata LIMIT 10"
}
```

This endpoint only permits `SELECT` queries for security reasons.

### Useful Queries

```sql
-- Count files by extension
SELECT extension, COUNT(*) as count 
FROM file_metadata 
WHERE extension IS NOT NULL 
GROUP BY extension 
ORDER BY count DESC;

-- Find the largest files
SELECT path, size_bytes 
FROM file_metadata 
WHERE is_directory = 0 
ORDER BY size_bytes DESC 
LIMIT 20;

-- Find recently modified files
SELECT path, modified_time 
FROM file_metadata 
WHERE modified_time > datetime('now', '-1 day')
ORDER BY modified_time DESC;
```

## Resetting the Database

For security reasons, resetting the database is **only possible from within the container** and not through the API.

### Method 1: Using the reset_database.sh Script

The easiest way to reset the database is to use the provided script:

```bash
# From your host machine
docker exec -it filesystem_server /app/reset_database.sh
```

This will prompt for confirmation before resetting the database.

### Method 2: Using the Python Utility Directly

You can also run the Python utility directly:

```bash
# Get a shell in the container
docker exec -it filesystem_server /bin/bash

# Run the utility with interactive prompt
python -m src.utils.reset_db

# Or force reset without prompt
python -m src.utils.reset_db --force
```

### What Happens During Reset

1. All existing database connections are closed
2. The database file is deleted 
3. A new empty database is created with the correct schema
4. The next time the watcher runs, it will reindex watched directories

## Best Practices

1. **Backup Before Reset**: If you have valuable indexed data, consider backing up the database file before resetting:
   ```bash
   docker cp filesystem_server:/home/jubin/Containers/filesystem/src/db/metadata.db ./metadata.db.backup
   ```

2. **Schedule During Low Usage**: Database reset can cause temporary performance degradation as the system reindexes files.

3. **Monitor After Reset**: Check the logs after reset to ensure the indexing process completes successfully:
   ```bash
   docker logs filesystem_server
   ```