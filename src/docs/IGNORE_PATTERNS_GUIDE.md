# Ignore Patterns Guide

The filesystem API supports ignoring specific files and directories during indexing and search operations, similar to how `.gitignore` works. This guide explains how to use this feature.

## How It Works

1. Patterns are defined in the `ignore.md` file at the root of the project
2. Common directories (node_modules, .git, etc.) are automatically ignored
3. The system checks files and directories against these patterns during indexing and searching
4. Ignored files are not included in search results or database queries

## Pattern Syntax

The syntax is similar to `.gitignore`:

- `*.txt` - Ignore all .txt files
- `node_modules/` - Ignore all node_modules directories
- `**/*.log` - Ignore all .log files in any directory
- `!important.log` - Don't ignore important.log (negation)
- `dist/**` - Ignore everything inside dist directories

## Default Ignored Directories

The following directories are automatically ignored:

- `node_modules`
- `.git`
- `.svn`
- `.hg`
- `__pycache__`
- `.vs`
- `.vscode`
- `bin`
- `obj`
- `build`
- `dist`
- `out`

## Creating/Editing ignore.md

Create an `ignore.md` file in the project root with your patterns:

```markdown
# Ignore patterns for filesystem indexing
# Similar to .gitignore format

# Build outputs
dist/
build/
out/

# Temporary files
*.tmp
*.temp
*.log
*.cache

# Large binary files
*.zip
*.tar.gz
*.iso
*.bin

# Project specific
.env
secrets/
```

## API Integration

When using the API, ignored files will be automatically excluded:

- `/index_directory` - Will not index ignored files
- `/search_files` - Will not return ignored files in results
- `/database_query` - Database will not contain ignored files

## Reloading Patterns

Patterns are loaded at startup. If you modify `ignore.md`, you'll need to:

1. Restart the server to load the new patterns
2. Re-index directories to apply the new patterns to the database

```bash
docker restart filesystem_server
```

Then use the API to re-index directories:

```json
POST /index_directory
{
  "path": "/path/to/reindex"
}
```

## Performance Impact

Using ignore patterns can significantly improve performance:

- Reduced disk I/O by skipping large directories like node_modules
- Smaller database size with fewer irrelevant files
- Faster search results by focusing on relevant files only

## Debugging

If files are unexpectedly ignored, check:

1. The loaded patterns at server startup (see logs)
2. Whether the file matches any pattern in `ignore.md`
3. Whether the file is in a common ignored directory

You can see which patterns are loaded in the server startup logs:

```
Loading ignore patterns...
Loaded 273 ignore patterns (including common directories)
```