"""
Database module for file metadata indexing.
Provides SQLAlchemy models and async database operations.
"""
from sqlalchemy import Column, String, Integer, Float, Boolean, Text, DateTime, func, select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base
import os
import pathlib
from datetime import datetime
import asyncio
from typing import List, Dict, Any, Optional, Union
import logging

# Import ignore pattern matching functionality
try:
    from src.utils import ignore_patterns
    IGNORE_PATTERNS_AVAILABLE = True
except ImportError:
    IGNORE_PATTERNS_AVAILABLE = False

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create SQLite database in the app directory
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "metadata.db")
DB_URL = f"sqlite+aiosqlite:///{DB_PATH}"

# Create SQLAlchemy async engine
engine = create_async_engine(
    DB_URL, 
    echo=False,  # Set to True for SQL debugging
    future=True
)

# Create async session factory
async_session = async_sessionmaker(
    engine, 
    class_=AsyncSession,
    expire_on_commit=False
)

# Declarative base for models
Base = declarative_base()

class FileMetadata(Base):
    """
    SQLAlchemy model for file metadata.
    Stores information about files for faster searching and indexing.
    """
    __tablename__ = "file_metadata"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    path = Column(String(1024), unique=True, index=True, nullable=False)
    parent_dir = Column(String(1024), index=True, nullable=False)
    name = Column(String(255), index=True, nullable=False)
    extension = Column(String(50), index=True)
    is_directory = Column(Boolean, index=True, default=False)
    size_bytes = Column(Integer)
    created_time = Column(DateTime, default=datetime.utcnow)
    modified_time = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_indexed = Column(DateTime, default=datetime.utcnow)
    # Content summary for text files (optional)
    content_summary = Column(Text, nullable=True)
    # Additional metadata as needed
    mime_type = Column(String(100))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the model to a dictionary."""
        return {
            "id": self.id,
            "path": self.path,
            "name": self.name,
            "extension": self.extension,
            "is_directory": self.is_directory,
            "size_bytes": self.size_bytes,
            "created_time": self.created_time.isoformat() if self.created_time else None,
            "modified_time": self.modified_time.isoformat() if self.modified_time else None,
            "last_indexed": self.last_indexed.isoformat() if self.last_indexed else None,
            "mime_type": self.mime_type
        }

async def create_tables():
    """Create database tables if they don't exist."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created.")

async def get_db_session():
    """Get a database session. Use as async context manager."""
    session = async_session()
    try:
        yield session
    finally:
        await session.close()

# File Metadata Operations

async def index_file(file_path: Union[str, pathlib.Path], session: Optional[AsyncSession] = None) -> FileMetadata:
    """
    Index a file or directory by adding or updating its metadata in the database.
    Respects ignore patterns if available.
    
    Args:
        file_path: Path to the file or directory to index
        session: Optional database session (creates one if not provided)
        
    Returns:
        The FileMetadata object
    """
    if isinstance(file_path, str):
        file_path = pathlib.Path(file_path)
    
    # Check if the file should be ignored based on ignore patterns
    if IGNORE_PATTERNS_AVAILABLE and ignore_patterns.should_ignore(file_path):
        logger.debug(f"Skipping ignored path: {file_path}")
        raise ValueError(f"Path ignored due to ignore patterns: {file_path}")
    
    logger.debug(f"Indexing path: {file_path}")
    
    # Get file stats
    try:
        if not file_path.exists():
            logger.warning(f"Path not found: {file_path}")
            raise FileNotFoundError(f"Path not found: {file_path}")
    except (PermissionError, OSError) as e:
        logger.warning(f"Error checking if path exists: {file_path}: {e}")
        raise
    
    # Determine if it's a file or directory
    try:
        is_directory = file_path.is_dir()
    except (PermissionError, OSError) as e:
        logger.warning(f"Error checking if path is directory: {file_path}: {e}")
        raise
    
    # Get file details
    try:
        stat_result = file_path.stat()
        size_bytes = None if is_directory else stat_result.st_size
        
        # Get timestamps
        modified_time = datetime.fromtimestamp(stat_result.st_mtime)
        try:
            created_time = datetime.fromtimestamp(stat_result.st_birthtime)
        except AttributeError:
            created_time = datetime.fromtimestamp(stat_result.st_ctime)
    except (PermissionError, OSError) as e:
        logger.warning(f"Error getting file stats: {file_path}: {e}")
        raise
    
    # Get MIME type for files
    mime_type = None
    if not is_directory:
        # Simple MIME type detection based on extension
        extension_map = {
            '.txt': 'text/plain',
            '.pdf': 'application/pdf',
            '.py': 'text/x-python',
            '.js': 'application/javascript',
            '.html': 'text/html',
            '.css': 'text/css',
            '.json': 'application/json',
            '.xml': 'application/xml',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.md': 'text/markdown'
        }
        extension = file_path.suffix.lower()
        mime_type = extension_map.get(extension, 'application/octet-stream')
    
    # Create a FileMetadata object
    close_session = False
    if session is None:
        session = async_session()
        close_session = True
    
    try:
        # Check if file already exists in database
        try:
            query = select(FileMetadata).where(FileMetadata.path == str(file_path))
            result = await session.execute(query)
            metadata = result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Database query error for {file_path}: {e}")
            raise
        
        # If not exists, create new entry
        if metadata is None:
            try:
                metadata = FileMetadata(
                    path=str(file_path),
                    parent_dir=str(file_path.parent),
                    name=file_path.name,
                    extension=file_path.suffix.lower() if not is_directory else None,
                    is_directory=is_directory,
                    size_bytes=size_bytes,
                    created_time=created_time,
                    modified_time=modified_time,
                    last_indexed=datetime.utcnow(),
                    mime_type=mime_type
                )
                session.add(metadata)
                logger.debug(f"Added new metadata for {file_path}")
            except Exception as e:
                logger.error(f"Error creating metadata for {file_path}: {e}")
                raise
        else:
            # Update existing entry
            try:
                metadata.modified_time = modified_time
                metadata.size_bytes = size_bytes
                metadata.last_indexed = datetime.utcnow()
                metadata.mime_type = mime_type
                logger.debug(f"Updated metadata for {file_path}")
            except Exception as e:
                logger.error(f"Error updating metadata for {file_path}: {e}")
                raise
        
        try:
            await session.commit()
            return metadata
        except Exception as e:
            logger.error(f"Error committing metadata for {file_path}: {e}")
            await session.rollback()
            raise
    finally:
        if close_session:
            await session.close()

async def delete_metadata(file_path: Union[str, pathlib.Path], session: Optional[AsyncSession] = None) -> bool:
    """
    Delete metadata for a file or directory.
    
    Args:
        file_path: Path of the file or directory to delete
        session: Optional database session (creates one if not provided)
        
    Returns:
        True if metadata was deleted, False if not found
    """
    if isinstance(file_path, str):
        file_path = pathlib.Path(file_path)
    
    close_session = False
    if session is None:
        session = async_session()
        close_session = True
        
    try:
        # Find the metadata entry
        query = select(FileMetadata).where(FileMetadata.path == str(file_path))
        result = await session.execute(query)
        metadata = result.scalar_one_or_none()
        
        if metadata is None:
            return False
            
        # Delete the entry
        await session.delete(metadata)
        await session.commit()
        
        # If it's a directory, also delete all children
        if metadata.is_directory:
            # Find all entries with paths starting with this directory
            path_prefix = f"{metadata.path}/"
            query = select(FileMetadata).where(FileMetadata.path.startswith(path_prefix))
            result = await session.execute(query)
            children = result.scalars().all()
            
            # Delete all children
            for child in children:
                await session.delete(child)
            
            await session.commit()
            
        return True
    finally:
        if close_session:
            await session.close()

async def search_metadata(
    query: str = None,
    extensions: List[str] = None,
    is_directory: bool = None,
    min_size: int = None,
    max_size: int = None,
    modified_after: datetime = None,
    modified_before: datetime = None,
    path_prefix: str = None,
    limit: int = 100,
    offset: int = 0
) -> List[Dict[str, Any]]:
    """
    Search file metadata based on various criteria.
    
    Args:
        query: Text search in file name
        extensions: List of file extensions to filter by (e.g. ['.txt', '.md'])
        is_directory: True to show only directories, False for files
        min_size: Minimum file size in bytes
        max_size: Maximum file size in bytes
        modified_after: Files modified after this datetime
        modified_before: Files modified before this datetime
        path_prefix: Only include files under this path
        limit: Maximum number of results to return
        offset: Number of results to skip (for pagination)
        
    Returns:
        List of file metadata dictionaries
    """
    async with async_session() as session:
        # Start with a base query for all metadata
        stmt = select(FileMetadata)
        
        # Apply filters
        if query:
            stmt = stmt.where(FileMetadata.name.contains(query))
            
        if extensions:
            # Convert extensions to lowercase
            ext_list = [ext.lower() if ext.startswith('.') else f'.{ext.lower()}' for ext in extensions]
            stmt = stmt.where(FileMetadata.extension.in_(ext_list))
            
        if is_directory is not None:
            stmt = stmt.where(FileMetadata.is_directory == is_directory)
            
        if min_size is not None:
            stmt = stmt.where(FileMetadata.size_bytes >= min_size)
            
        if max_size is not None:
            stmt = stmt.where(FileMetadata.size_bytes <= max_size)
            
        if modified_after:
            stmt = stmt.where(FileMetadata.modified_time >= modified_after)
            
        if modified_before:
            stmt = stmt.where(FileMetadata.modified_time <= modified_before)
            
        if path_prefix:
            # Match exact path or paths that start with path_prefix/
            path_with_slash = f"{path_prefix}/"
            stmt = stmt.where(
                (FileMetadata.path == path_prefix) | 
                (FileMetadata.path.startswith(path_with_slash))
            )
            
        # Apply pagination
        stmt = stmt.offset(offset).limit(limit)
        
        # Execute the query
        result = await session.execute(stmt)
        metadata_list = result.scalars().all()
        
        # Convert to dictionaries
        return [metadata.to_dict() for metadata in metadata_list]

async def get_metadata_by_path(file_path: Union[str, pathlib.Path]) -> Optional[Dict[str, Any]]:
    """
    Get metadata for a single file or directory by path.
    
    Args:
        file_path: Path to the file or directory
        
    Returns:
        Metadata dictionary or None if not found
    """
    if isinstance(file_path, str):
        file_path = pathlib.Path(file_path)
        
    async with async_session() as session:
        query = select(FileMetadata).where(FileMetadata.path == str(file_path))
        result = await session.execute(query)
        metadata = result.scalar_one_or_none()
        
        if metadata:
            return metadata.to_dict()
        return None

async def index_directory_recursive(
    directory_path: Union[str, pathlib.Path],
    max_files: int = None,  # Changed from 1000 to None (no limit)
    max_depth: int = 5      # Increased default depth from 3 to 5
) -> int:
    """
    Recursively index a directory and its contents.
    Respects ignore patterns from ignore.md if available.
    
    Args:
        directory_path: Path to the directory to index
        max_files: Maximum number of files to index (default: None, meaning no limit)
        max_depth: Maximum directory depth to traverse (default: 5)
        
    Returns:
        Number of files indexed
    """
    if isinstance(directory_path, str):
        directory_path = pathlib.Path(directory_path)
        
    if not directory_path.is_dir():
        raise NotADirectoryError(f"Not a directory: {directory_path}")
        
    # Check if the directory itself should be ignored
    if IGNORE_PATTERNS_AVAILABLE and ignore_patterns.should_ignore(directory_path):
        logger.info(f"Skipping ignored directory: {directory_path}")
        return 0
        
    # Count of indexed files
    count = 0
    skipped_count = 0
    
    # Index the directory itself
    async with async_session() as session:
        try:
            await index_file(directory_path, session)
            count += 1
            
            # Helper function to index files with depth limit
            def get_rel_depth(path, base_path):
                # Calculate relative path depth
                rel_path = str(path.relative_to(base_path))
                return rel_path.count('/') + 1 if rel_path != '.' else 0
                
            # Walk through contents with limits
            for root, dirs, files in os.walk(directory_path):
                root_path = pathlib.Path(root)
                current_depth = get_rel_depth(root_path, directory_path)
                
                # Skip if we've reached max depth
                if current_depth >= max_depth:
                    logger.info(f"Skipping deeper traversal at depth {current_depth}: {root_path}")
                    dirs.clear()  # Don't traverse deeper
                    continue
                
                # Filter directories based on ignore patterns (modifies dirs in-place)
                if IGNORE_PATTERNS_AVAILABLE:
                    dirs_to_remove = []
                    for dir_name in dirs:
                        dir_path = root_path / dir_name
                        if ignore_patterns.should_ignore(dir_path):
                            dirs_to_remove.append(dir_name)
                            skipped_count += 1
                            logger.debug(f"Skipping ignored directory: {dir_path}")
                    
                    # Remove ignored directories from the dirs list to prevent recursion into them
                    for dir_name in dirs_to_remove:
                        dirs.remove(dir_name)
                
                try:
                    # Index directories at this level
                    for dir_name in dirs[:]:  # Copy to avoid modification during iteration
                        try:
                            dir_path = root_path / dir_name
                            
                            # Skip if we should ignore this directory
                            if IGNORE_PATTERNS_AVAILABLE and ignore_patterns.should_ignore(dir_path):
                                logger.debug(f"Skipping ignored directory: {dir_path}")
                                continue
                                
                            await index_file(dir_path, session)
                            count += 1
                            
                            # Break if we've reached the file limit (if one is set)
                            if max_files is not None and count >= max_files:
                                logger.info(f"Reached file limit of {max_files}")
                                return count
                        except ValueError as e:
                            if "Path ignored" in str(e):
                                skipped_count += 1
                            else:
                                logger.error(f"Error indexing directory {dir_path}: {e}")
                        except Exception as e:
                            logger.error(f"Error indexing directory {dir_path}: {e}")
                    
                    # Index files at this level
                    for file_name in files:
                        try:
                            file_path = root_path / file_name
                            
                            # Skip if we should ignore this file
                            if IGNORE_PATTERNS_AVAILABLE and ignore_patterns.should_ignore(file_path):
                                logger.debug(f"Skipping ignored file: {file_path}")
                                skipped_count += 1
                                continue
                                
                            await index_file(file_path, session)
                            count += 1
                            
                            # Commit periodically
                            if count % 50 == 0:
                                await session.commit()
                                logger.info(f"Indexed {count} files so far, skipped {skipped_count} ignored files")
                                
                            # Break if we've reached the file limit (if one is set)
                            if max_files is not None and count >= max_files:
                                logger.info(f"Reached file limit of {max_files}")
                                return count
                        except ValueError as e:
                            if "Path ignored" in str(e):
                                skipped_count += 1
                            else:
                                logger.error(f"Error indexing file {file_path}: {e}")
                        except Exception as e:
                            logger.error(f"Error indexing file {file_path}: {e}")
                except Exception as e:
                    logger.error(f"Error processing directory content in {root_path}: {e}")
                    continue
                    
            # Final commit
            await session.commit()
            logger.info(f"Successfully indexed {count} files in {directory_path}, skipped {skipped_count} ignored files")
            
        except Exception as e:
            logger.error(f"Error in recursive indexing of {directory_path}: {e}")
            await session.rollback()
            raise
            
    return count

# Database initialization function to be called at startup
async def initialize_database():
    """Initialize the database and create tables if needed."""
    await create_tables()
    logger.info("Metadata database initialized.")

# Cleanup function for shutdown
async def close_database():
    """Close database connections on shutdown."""
    await engine.dispose()
    logger.info("Database connections closed.")