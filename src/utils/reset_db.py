"""
Database reset utility for clearing and reinitializing the metadata database.
Provides both programmatic function and command-line interface.
"""
import os
import sys
import argparse
import logging
import asyncio
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add the project root directory to the path so we can import our modules
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

async def reset_database(force=False):
    """
    Reset the metadata database by deleting and reinitializing it.
    
    Args:
        force: If True, skip confirmation prompt when run from command line
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Import db module from our project
        from src.db import db
        
        # Get the database path
        db_path = db.DB_PATH
        
        if not os.path.exists(db_path):
            logger.info(f"Database at {db_path} doesn't exist. Nothing to reset.")
            logger.info("A new database will be created when needed.")
            return True
            
        # Close any open database connections
        try:
            await db.close_database()
            logger.info("Closed existing database connections")
        except Exception as e:
            logger.warning(f"Could not close database connections: {e}")
            
        # Delete the existing database file
        try:
            os.remove(db_path)
            logger.info(f"Database at {db_path} has been deleted.")
        except Exception as e:
            logger.error(f"Error deleting database: {e}")
            return False
            
        # Reinitialize the database if needed
        try:
            await db.initialize_database()
            logger.info("Database has been reinitialized with empty tables.")
        except Exception as e:
            logger.error(f"Error reinitializing database: {e}")
            return False
            
        logger.info("Database reset complete. The watcher will reindex files as needed.")
        return True
    
    except ImportError:
        logger.error("Could not import database module. Make sure the project structure is intact.")
        return False
    except Exception as e:
        logger.error(f"Unexpected error resetting database: {e}")
        return False

def main():
    """Command-line interface for database reset."""
    parser = argparse.ArgumentParser(description="Reset the metadata database.")
    parser.add_argument("--force", "-f", action="store_true", 
                        help="Force reset without confirmation")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Show verbose output")
    
    args = parser.parse_args()
    
    # Set logging level based on verbosity
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Confirm reset if not forced
    if not args.force:
        response = input("Are you sure you want to reset the database? This will delete all indexed metadata. (y/N): ")
        if response.lower() not in ["y", "yes"]:
            print("Database reset cancelled.")
            return
    
    # Run the async reset function
    success = asyncio.run(reset_database(force=args.force))
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()