"""
Configuration module for the filesystem API application.
Centralizes configuration values used across the application.
"""
import os
import dotenv
import pathlib

# Load environment variables from .env file
# Find the project root directory (2 levels up from this file)
project_root = pathlib.Path(__file__).parent.parent.parent
env_file = project_root / ".env"

# Load .env file if it exists
if env_file.exists():
    dotenv.load_dotenv(env_file)

# Base API URL with configurable host and port
API_HOST = os.environ.get("API_HOST", "localhost")
API_PORT = int(os.environ.get("API_PORT", "8010"))
API_URL = f"http://{API_HOST}:{API_PORT}"

# Database configuration
DB_PATH = os.environ.get("DB_PATH", None)  # If None, default path will be used

# File caching configuration
CACHE_SIZE_MB = int(os.environ.get("CACHE_SIZE_MB", "100"))  # 100MB default

# Worker thread configuration
THREAD_POOL_SIZE = int(os.environ.get("THREAD_POOL_SIZE", "10"))  # 10 threads default

# Allowed directories
def get_allowed_directories():
    """Get allowed directories from environment or use defaults."""
    allowed_dirs_env = os.environ.get("ALLOWED_DIRECTORIES", None)
    if allowed_dirs_env:
        return allowed_dirs_env.split(":")
    return ["/mnt/c/Sandboxes", "/app/testdir"]  # Default directories