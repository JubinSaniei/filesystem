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
from typing import Dict, Set, List, Optional, Union, Any, Deque
from collections import deque
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
indexing_locks: Dict[str, asyncio.Lock] = {}  # Locks for specific directories
global_lock = asyncio.Lock()  # Global lock for state modifications

# Flag to indicate watcher functionality is available
WATCHER_AVAILABLE = True

# Change queue to handle throttling
path_change_queue: Deque[str] = deque(maxlen=10000)  # Limits the number of queued changes

# Configuration
SCAN_INTERVAL = 300  # seconds between full scans
BATCH_SIZE = 200     # increased number of files to process in one batch
THROTTLE_INTERVAL = 1.0  # seconds between processing batches of changes
MAX_INITIAL_FILES = 5000  # increased limit for initial scan

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
    # Use a background task for the coroutine
    asyncio.create_task(start_watcher_if_needed())
    
async def delayed_recursive_scan(directory: pathlib.Path) -> None:
    """
    Perform a delayed recursive scan of a directory.
    This runs in the background to prevent blocking the application startup.
    Uses a lock to prevent concurrent indexing of the same directory.
    
    Args:
        directory: Path to the directory to scan recursively
    """
    # Get or create lock for this directory
    dir_str = str(directory)
    lock = indexing_locks.get(dir_str)
    if lock is None:
        async with global_lock:
            # Check again in case another task created it while we were waiting
            lock = indexing_locks.get(dir_str)
            if lock is None:
                lock = asyncio.Lock()
                indexing_locks[dir_str] = lock
    
    # Use lock to prevent concurrent indexing of the same directory
    async with lock:
        try:
            # Add a small delay to let the app start up first
            await asyncio.sleep(10)
            
            logger.info(f"Starting background recursive scan of {directory}")
            
            # Check if directory still exists
            if not directory.exists() or not directory.is_dir():
                logger.warning(f"Directory {directory} no longer exists or is not a directory")
                return
                
            # Use db.index_directory_recursive with a reasonable limit to prevent excessive indexing
            try:
                # First process immediate children
                file_count = 0
                async with db.async_session() as session:
                    # Add the directory itself
                    await db.index_file(directory, session)
                    file_count += 1
                    
                    # Process immediate children first for better responsiveness
                    try:
                        for entry in os.scandir(directory):
                            if not os.path.exists(entry.path):
                                continue
                                
                            try:
                                path = pathlib.Path(entry.path)
                                await db.index_file(path, session)
                                file_count += 1
                            except Exception as e:
                                logger.error(f"Error indexing {entry.path}: {e}")
                                continue
                    except Exception as e:
                        logger.error(f"Error scanning directory {directory}: {e}")
                        
                    await session.commit()
                
                # Now do the deep recursive scan with a higher limit
                count = await db.index_directory_recursive(directory, max_files=MAX_INITIAL_FILES)
                logger.info(f"Background scan complete. Indexed {count} files in {directory}")
            except Exception as e:
                logger.error(f"Error during recursive scan of {directory}: {e}")
        except Exception as e:
            logger.error(f"Error during background scan of {directory}: {e}")
        finally:
            # Update last scan time even if there was an error, to prevent immediate rescanning
            last_scan_times[dir_str] = datetime.now()
    
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
        await stop_watcher()
        
def notify_change(path: Union[str, pathlib.Path]) -> None:
    """
    Notify the watcher of a file change from external operations.
    Uses a queue system with deduplication for better handling of many changes.
    
    Args:
        path: Path that was modified
    """
    if isinstance(path, str):
        path = pathlib.Path(path)
        
    path_str = str(path)
    
    # Use a synchronized approach to update shared data
    if path_str not in modified_paths:
        # Add to modified paths for processing in next scan
        modified_paths.add(path_str)
        
        # Also add to our change queue for immediate processing
        path_change_queue.append(path_str)
            
        # If it's a directory, also mark parent directories (with deduplication)
        if path.is_dir():
            for parent in path.parents:
                parent_str = str(parent)
                if parent_str not in modified_paths:
                    modified_paths.add(parent_str)
                    # Don't queue parents for immediate processing to reduce duplicate work
                    
        logger.debug(f"Change notification received for: {path}")
        
        # Ensure watcher is running to process these changes
        # Since start_watcher_if_needed is async and we're in a sync context,
        # we can only check if it should be started
        if not watcher_running and watched_directories:
            # Create a synchronous function for starting the watcher
            def start_watcher_sync():
                """Synchronous wrapper to start the watcher task"""
                global watcher_task, watcher_running
                if not watcher_running and watched_directories:
                    watcher_task = asyncio.create_task(_watcher_loop())
                    watcher_running = True
                    logger.info("File watcher task started (from sync context)")
            
            # Call the sync function directly
            start_watcher_sync()
    
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
    """
    Process paths that have been explicitly marked as modified.
    Uses a throttling mechanism and locks to prevent excessive CPU/IO usage.
    """
    global modified_paths
    
    # Process paths from the change queue first (FIFO order for immediate changes)
    await _process_change_queue()
    
    # Check if there are any remaining paths in the modified_paths set
    if not modified_paths:
        return
    
    # Use a lock to safely modify the global set
    async with global_lock:
        # Create a local copy of the global set to avoid concurrent modification issues
        # Use a list to ensure consistent processing order
        paths_to_process = list(modified_paths)
        
        # Clear the global set only after we've made a copy
        modified_paths = set()
    
    # Group paths by parent directory to optimize directory scans
    dirs_to_process = {}
    files_to_process = []
    
    for path_str in paths_to_process:
        # Skip if the path_str is None or empty
        if not path_str:
            continue
            
        try:
            path = pathlib.Path(path_str)
            
            # If it's a directory, add it to the directory group
            if path.is_dir() or not path.exists():
                dirs_to_process[path_str] = path
            else:
                # It's a file, process individually
                files_to_process.append((path_str, path))
        except Exception as e:
            logger.error(f"Error checking path type {path_str}: {e}")
    
    if dirs_to_process or files_to_process:
        logger.info(f"Processing {len(files_to_process)} modified files and {len(dirs_to_process)} directories")
    
    # First process all individual files to provide faster updates for file changes
    if files_to_process:
        # Process in batches to avoid memory issues
        for i in range(0, len(files_to_process), BATCH_SIZE):
            batch = files_to_process[i:i + BATCH_SIZE]
            
            async with db.async_session() as session:
                for path_str, path in batch:
                    try:
                        if path.exists():
                            # Update metadata for the individual file
                            await db.index_file(path, session)
                        else:
                            # File no longer exists
                            await db.delete_metadata(path, session)
                    except Exception as e:
                        logger.error(f"Error processing modified file {path}: {e}")
                
                await session.commit()
            
            # Add a small delay between batches to reduce resource usage
            if i + BATCH_SIZE < len(files_to_process):
                await asyncio.sleep(THROTTLE_INTERVAL)
    
    # Then process directories - more efficiently by avoiding redundant sub-directory scans
    for dir_path_str, dir_path in dirs_to_process.items():
        # Get or create a lock for this directory
        lock = indexing_locks.get(dir_path_str)
        if lock is None:
            async with global_lock:
                # Check again in case another task created it while we were waiting
                lock = indexing_locks.get(dir_path_str)
                if lock is None:
                    lock = asyncio.Lock()
                    indexing_locks[dir_path_str] = lock
        
        # Use lock to prevent concurrent indexing of the same directory
        if not lock.locked():  # Only process if not already being processed
            async with lock:
                try:
                    if dir_path.exists():
                        # Update just the directory metadata first
                        async with db.async_session() as session:
                            await db.index_file(dir_path, session)
                            await session.commit()
                        
                        # Use a reasonable limit for recursive indexing
                        # Only scan recursively if this is a watched directory
                        if any(dir_path_str.startswith(wd) for wd in watched_directories) or dir_path_str in watched_directories:
                            # Use a smaller max_files limit for change processing to be more responsive
                            await db.index_directory_recursive(dir_path, max_files=1000)
                    else:
                        # Directory no longer exists, remove from database
                        await db.delete_metadata(dir_path)
                except Exception as e:
                    logger.error(f"Error processing modified directory {dir_path}: {e}")
        
        # Add a small delay between directory processing to reduce resource usage
        await asyncio.sleep(THROTTLE_INTERVAL)

async def _process_change_queue() -> None:
    """
    Process changes from the queue with throttling.
    This is used for immediate processing of file changes.
    """
    processed_count = 0
    
    # Process a limited number of items from the queue in each call
    # to ensure we don't block the event loop for too long
    max_queue_items = min(len(path_change_queue), BATCH_SIZE)
    
    if max_queue_items == 0:
        return
        
    logger.debug(f"Processing {max_queue_items} items from change queue")
    
    # Use a session for batch processing
    async with db.async_session() as session:
        for _ in range(max_queue_items):
            if not path_change_queue:
                break
                
            try:
                path_str = path_change_queue.popleft()
                path = pathlib.Path(path_str)
                
                # Skip directories, they'll be handled by the regular scan process
                if path.is_dir():
                    continue
                    
                # Process individual files immediately for better responsiveness
                if path.exists():
                    try:
                        await db.index_file(path, session)
                        processed_count += 1
                    except Exception as e:
                        logger.error(f"Error indexing file from queue {path}: {e}")
                else:
                    try:
                        await db.delete_metadata(path, session)
                        processed_count += 1
                    except Exception as e:
                        logger.error(f"Error deleting metadata from queue {path}: {e}")
            except Exception as e:
                logger.error(f"Error processing item from change queue: {e}")
                
        # Commit all changes at once
        if processed_count > 0:
            try:
                await session.commit()
                logger.debug(f"Processed {processed_count} items from change queue")
            except Exception as e:
                logger.error(f"Error committing changes from queue: {e}")
                await session.rollback()
    
async def _watcher_loop() -> None:
    """
    Main watcher loop that periodically checks for changes.
    Enhanced with better change detection and resource management.
    """
    global watcher_running
    
    watcher_running = True
    logger.info("File watcher started")
    
    # Track health statistics
    stats = {
        "cycles": 0,
        "files_processed": 0,
        "errors": 0,
        "last_error": None
    }
    
    try:
        while watcher_running and watched_directories:
            cycle_start = time.time()
            stats["cycles"] += 1
            
            try:
                # First, check if we have any queued changes for immediate processing
                if path_change_queue:
                    await _process_change_queue()
                    
                # Then process any modified paths that were marked for update
                if modified_paths:
                    await _process_modified_paths()
                
                # Every few cycles, do a full scheduled scan of watched directories
                # This catches changes that might have been missed by explicit notifications
                if stats["cycles"] % 5 == 0:  # Do full scan every 5 cycles
                    await _scan_directories()
                
                # Adaptive sleep: sleep longer if system is idle, shorter if there are pending changes
                if path_change_queue or modified_paths:
                    # If we have pending work, sleep briefly
                    await asyncio.sleep(0.5)
                else:
                    # If no pending work, sleep longer
                    await asyncio.sleep(5)
                    
                # Record cycle time for performance monitoring
                cycle_time = time.time() - cycle_start
                # Only warn if it takes significantly longer than the sleep time
                if cycle_time > 6.0:
                    logger.warning(f"Watcher cycle took {cycle_time:.2f}s, which is longer than expected")
                    
            except Exception as e:
                stats["errors"] += 1
                stats["last_error"] = str(e)
                logger.error(f"Error in watcher cycle: {e}")
                # Continue running even after errors
                await asyncio.sleep(5)  # Sleep a bit longer after errors
                
    except asyncio.CancelledError:
        logger.info("File watcher task cancelled")
    except Exception as e:
        logger.error(f"Fatal error in watcher loop: {e}")
    finally:
        watcher_running = False
        logger.info(f"File watcher stopped. Stats: {stats}")
        
async def start_watcher_if_needed() -> None:
    """
    Start the file watcher task if it's not already running.
    Uses a lock to prevent race conditions when starting the watcher.
    """
    global watcher_task, watcher_running, global_lock
    
    async with global_lock:  # Use lock to prevent multiple starts
        if not watcher_running and watched_directories:
            # Clean up any existing task
            if watcher_task is not None and not watcher_task.done():
                watcher_task.cancel()
                try:
                    await watcher_task
                except asyncio.CancelledError:
                    pass  # Expected when cancelling
                except Exception as e:
                    logger.error(f"Error cancelling previous watcher task: {e}")
                    
            # Start a new task
            watcher_task = asyncio.create_task(_watcher_loop())
            logger.info("File watcher task started")
        
async def stop_watcher() -> None:
    """
    Stop the file watcher task.
    Uses a lock to prevent race conditions when stopping the watcher.
    """
    global watcher_task, watcher_running, global_lock
    
    async with global_lock:  # Use lock to prevent race conditions
        if watcher_running and watcher_task is not None and not watcher_task.done():
            watcher_running = False
            try:
                watcher_task.cancel()
                await watcher_task
            except asyncio.CancelledError:
                pass  # Expected when cancelling
            except Exception as e:
                logger.error(f"Error cancelling watcher task: {e}")
                
            logger.info("File watcher task stopped")
            
    # Clear any remaining queued changes
    path_change_queue.clear()
    
    # Reset the locks to release any held resources
    async with global_lock:
        indexing_locks.clear()
        
# Initialize and cleanup functions

async def initialize_watcher(directories: List[str] = None) -> None:
    """
    Initialize the file watcher system.
    
    Args:
        directories: List of directories to watch
    """
    # Initialize database first
    await db.initialize_database()
    
    # Reset global state
    async with global_lock:
        # Clear locks but keep global lock
        indexing_locks.clear()
        path_change_queue.clear()
    
    # Start watching specified directories
    if directories:
        logger.info(f"Starting to watch {len(directories)} directories")
        for directory in directories:
            # Validate directory before watching
            try:
                dir_path = pathlib.Path(directory)
                if dir_path.exists() and dir_path.is_dir():
                    await watch_directory(directory)
                else:
                    logger.warning(f"Skipping invalid directory: {directory}")
            except Exception as e:
                logger.error(f"Error adding directory to watch: {directory}: {e}")
    
async def cleanup_watcher() -> None:
    """
    Clean up watcher resources.
    Ensures proper shutdown of all background tasks and database connections.
    """
    # Stop watcher task - use the async version
    try:
        await stop_watcher()
    except Exception as e:
        logger.error(f"Error stopping watcher: {e}")
    
    # Clear all state
    async with global_lock:
        modified_paths.clear()
        path_change_queue.clear()
        watched_directories.clear()
        last_scan_times.clear()
        indexing_locks.clear()
    
    # Close database connections
    try:
        await db.close_database()
        logger.info("Database connections closed")
    except Exception as e:
        logger.error(f"Error closing database connections: {e}")
    
    logger.info("Watcher cleanup complete")