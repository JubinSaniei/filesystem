"""
File watcher module for monitoring filesystem changes and updating the metadata index.
Uses a combination of scheduled scans and filesystem event triggers.
"""
import asyncio
import pathlib
import os
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, Set, List, Optional, Union, Any
from src.db import db  # Database operations module

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global state
watched_directories: Set[str] = set()
last_scan_times: Dict[str, datetime] = {}
modified_paths: Set[str] = set()
watcher_running = False
watcher_task = None

# Configuration
SCAN_INTERVAL = 300  # seconds between full scans
BATCH_SIZE = 100    # number of files to process in one batch

async def watch_directory(directory: Union[str, pathlib.Path]) -> None:
    """
    Start watching a directory for changes.
    
    Args:
        directory: Path to the directory to watch
    """
    if isinstance(directory, str):
        directory = pathlib.Path(directory)
        
    if not directory.is_dir():
        raise NotADirectoryError(f"Not a directory: {directory}")
        
    dir_str = str(directory)
    watched_directories.add(dir_str)
    
    # Initial scan - only index the immediate directory, not recursively
    # to prevent blocking on large directory structures
    logger.info(f"Starting initial scan of {dir_str} (directory only)")
    try:
        # Just index the directory itself for now
        await db.index_file(directory)
        logger.info(f"Initial directory scan complete for {dir_str}")
        
        # Schedule a background task to scan files
        asyncio.create_task(delayed_recursive_scan(directory))
        
        last_scan_times[dir_str] = datetime.now()
    except Exception as e:
        logger.error(f"Error during initial scan of {dir_str}: {e}")
        
    # Ensure watcher is running
    start_watcher_if_needed()
    
async def delayed_recursive_scan(directory: pathlib.Path) -> None:
    """
    Perform a delayed recursive scan of a directory.
    This runs in the background to prevent blocking the application startup.
    
    Args:
        directory: Path to the directory to scan recursively
    """
    try:
        # Add a small delay to let the app start up first
        await asyncio.sleep(10)
        
        logger.info(f"Starting background recursive scan of {directory}")
        
        # Check if directory still exists
        if not directory.exists() or not directory.is_dir():
            logger.warning(f"Directory {directory} no longer exists or is not a directory")
            return
            
        # Scan only up to 1000 files at first for performance reasons
        file_count = 0
        max_files = 1000
        
        # Walk directory manually with limits
        async with db.async_session() as session:
            # Add the directory
            await db.index_file(directory, session)
            file_count += 1
            
            # Process immediate children first
            try:
                for entry in os.scandir(directory):
                    if not os.path.exists(entry.path):
                        continue
                        
                    try:
                        path = pathlib.Path(entry.path)
                        await db.index_file(path, session)
                        file_count += 1
                        
                        if file_count >= max_files:
                            break
                    except Exception as e:
                        logger.error(f"Error indexing {entry.path}: {e}")
                        continue
            except Exception as e:
                logger.error(f"Error scanning directory {directory}: {e}")
                
            await session.commit()
            
        logger.info(f"Background scan complete. Indexed {file_count} files in {directory}")
    except Exception as e:
        logger.error(f"Error during background scan of {directory}: {e}")
    
async def unwatch_directory(directory: Union[str, pathlib.Path]) -> None:
    """
    Stop watching a directory for changes.
    
    Args:
        directory: Path to the directory to stop watching
    """
    if isinstance(directory, str):
        directory = pathlib.Path(directory)
        
    dir_str = str(directory)
    
    if dir_str in watched_directories:
        watched_directories.remove(dir_str)
        if dir_str in last_scan_times:
            del last_scan_times[dir_str]
            
        logger.info(f"Stopped watching directory: {dir_str}")
        
    # If no more directories to watch, stop the watcher
    if not watched_directories and watcher_running:
        stop_watcher()
        
def notify_change(path: Union[str, pathlib.Path]) -> None:
    """
    Notify the watcher of a file change from external operations.
    
    Args:
        path: Path that was modified
    """
    if isinstance(path, str):
        path = pathlib.Path(path)
        
    # Add to modified paths for processing in next scan
    modified_paths.add(str(path))
    
    # If it's a directory, also mark it as a directory
    if path.is_dir():
        for parent in path.parents:
            modified_paths.add(str(parent))
            
    logger.debug(f"Change notification received for: {path}")
    
async def _scan_directories() -> None:
    """Scan watched directories for changes."""
    now = datetime.now()
    directories_to_scan = []
    
    # Find directories due for scanning
    for dir_str in watched_directories:
        last_scan = last_scan_times.get(dir_str)
        if last_scan is None or (now - last_scan).total_seconds() >= SCAN_INTERVAL:
            directories_to_scan.append(dir_str)
            
    # Process each directory
    for dir_str in directories_to_scan:
        logger.info(f"Scanning directory: {dir_str}")
        
        try:
            directory = pathlib.Path(dir_str)
            
            # Check for deleted files by comparing database entries with actual files
            async with db.async_session() as session:
                # Get all files in the database for this directory
                stmt = db.select(db.FileMetadata).where(
                    (db.FileMetadata.path == dir_str) | 
                    (db.FileMetadata.path.startswith(f"{dir_str}/"))
                )
                result = await session.execute(stmt)
                db_files = result.scalars().all()
                
                # Check each file to see if it still exists
                for metadata in db_files:
                    file_path = pathlib.Path(metadata.path)
                    if not file_path.exists():
                        logger.debug(f"File no longer exists, removing from index: {metadata.path}")
                        await db.delete_metadata(file_path, session)
                
                await session.commit()
            
            # Scan for new and modified files
            count = await db.index_directory_recursive(directory)
            logger.info(f"Scan complete. Processed {count} files in {dir_str}")
            
            # Update scan time
            last_scan_times[dir_str] = now
            
        except Exception as e:
            logger.error(f"Error scanning directory {dir_str}: {e}")
    
async def _process_modified_paths() -> None:
    """Process paths that have been explicitly marked as modified."""
    if not modified_paths:
        return
        
    # Create a local copy of the global set to avoid concurrent modification issues
    # Use a list to ensure consistent processing order
    paths_to_process = list(modified_paths)
    
    # Clear the global set only after we've made a copy
    modified_paths.clear()
    
    logger.info(f"Processing {len(paths_to_process)} modified paths")
    
    # Process in batches to avoid memory issues
    for i in range(0, len(paths_to_process), BATCH_SIZE):
        batch = paths_to_process[i:i + BATCH_SIZE]
        
        async with db.async_session() as session:
            for path_str in batch:
                # Skip if the path_str is None or empty
                if not path_str:
                    continue
                    
                path = pathlib.Path(path_str)
                
                try:
                    if path.exists():
                        # Update metadata
                        await db.index_file(path, session)
                        
                        # If it's a directory, update all children (might be inefficient)
                        if path.is_dir():
                            await db.index_directory_recursive(path)
                    else:
                        # File or directory no longer exists
                        await db.delete_metadata(path, session)
                except Exception as e:
                    logger.error(f"Error processing modified path {path}: {e}")
                    
            await session.commit()
    
async def _watcher_loop() -> None:
    """Main watcher loop that periodically checks for changes."""
    global watcher_running
    
    watcher_running = True
    logger.info("File watcher started")
    
    try:
        while watcher_running and watched_directories:
            # Process explicitly modified paths
            await _process_modified_paths()
            
            # Scan directories for changes
            await _scan_directories()
            
            # Sleep before next scan
            await asyncio.sleep(5)
    except asyncio.CancelledError:
        logger.info("File watcher task cancelled")
    except Exception as e:
        logger.error(f"Error in watcher loop: {e}")
    finally:
        watcher_running = False
        logger.info("File watcher stopped")
        
def start_watcher_if_needed() -> None:
    """Start the file watcher task if it's not already running."""
    global watcher_task, watcher_running
    
    if not watcher_running and watched_directories:
        watcher_task = asyncio.create_task(_watcher_loop())
        logger.info("File watcher task started")
        
def stop_watcher() -> None:
    """Stop the file watcher task."""
    global watcher_task, watcher_running
    
    if watcher_running and watcher_task:
        watcher_running = False
        if not watcher_task.done():
            watcher_task.cancel()
        logger.info("File watcher task stopping")
        
# Initialize and cleanup functions

async def initialize_watcher(directories: List[str] = None) -> None:
    """
    Initialize the file watcher system.
    
    Args:
        directories: List of directories to watch
    """
    # Initialize database first
    await db.initialize_database()
    
    # Start watching specified directories
    if directories:
        for directory in directories:
            await watch_directory(directory)
    
async def cleanup_watcher() -> None:
    """Clean up watcher resources."""
    # Stop watcher task
    stop_watcher()
    
    # Close database connections
    await db.close_database()