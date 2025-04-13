#!/bin/bash
# Reset database script
# Run this script from inside the container to reset the metadata database

echo "==========================================="
echo "       METADATA DATABASE RESET TOOL        "
echo "==========================================="
echo
echo "This script will COMPLETELY ERASE all indexed file metadata."
echo "The database will be recreated with empty tables."
echo "After reset, the watcher will reindex files as needed."
echo
echo "TO USE: Run this script from inside the container with:"
echo "  docker exec -it filesystem_server /app/reset_database.sh"
echo

# Check if we're in a terminal for interactive use
if [ -t 0 ]; then
    # Interactive mode
    read -p "Are you sure you want to reset the metadata database? (y/N): " response
    if [[ ! "$response" =~ ^[yY]$ ]]; then
        echo "Database reset cancelled."
        exit 0
    fi
    # Run the reset utility
    python -m src.utils.reset_db
else
    # Non-interactive mode (e.g., script piped in)
    echo "Running in non-interactive mode. Use --force to bypass confirmation."
    python -m src.utils.reset_db --force
fi