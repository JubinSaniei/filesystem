"""
Module for parsing and applying ignore patterns from ignore files.
Provides functionality similar to .gitignore processing.
"""
import pathlib
import fnmatch
import re
from typing import List, Set, Optional, Union

# Default path to ignore file
import os
DEFAULT_IGNORE_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "src", "docs", "ignore.md")


class IgnorePatternMatcher:
    """
    Class to parse and match ignore patterns from a file.
    Supports glob patterns similar to .gitignore format.
    """
    def __init__(self, ignore_file: Optional[str] = None):
        """
        Initialize with patterns from the specified ignore file.
        
        Args:
            ignore_file: Path to the ignore file (default: "ignore.md")
        """
        self.patterns: List[str] = []
        self.regex_patterns: List[re.Pattern] = []
        
        # Common directory patterns that should always be ignored
        self.common_ignored_dirs = [
            "node_modules",
            ".git",
            ".svn",
            ".hg",
            "__pycache__",
            ".vs",
            ".vscode",
            "bin",
            "obj",
            "build",
            "dist",
            "out"
        ]
        
        # Use default file if none specified
        if ignore_file is None:
            ignore_file = DEFAULT_IGNORE_FILE
            
        self.ignore_file = ignore_file
        self.load_patterns()
    
    def load_patterns(self) -> None:
        """
        Load patterns from the ignore file.
        Skips comments and empty lines.
        Adds common directory patterns automatically.
        """
        try:
            path = pathlib.Path(self.ignore_file)
            if not path.exists():
                print(f"Warning: Ignore file not found at {self.ignore_file}")
                return
                
            with open(path, 'r') as f:
                lines = f.readlines()
                
            self.patterns = []
            self.regex_patterns = []
            
            # Add common directory patterns if not already in the ignore file
            for common_dir in self.common_ignored_dirs:
                base_pattern = f"**/{common_dir}/**"
                dir_pattern = f"**/{common_dir}/"
                self.patterns.append(base_pattern)
                self.patterns.append(dir_pattern)
                
                # Add regex versions too
                self.regex_patterns.append(re.compile(fnmatch.translate(base_pattern)))
                self.regex_patterns.append(re.compile(fnmatch.translate(dir_pattern)))
            
            for line in lines:
                # Skip comments, empty lines, and syntax markers
                line = line.strip()
                if not line or line.startswith('#') or line.startswith('syntax:'):
                    continue
                    
                # Skip section headers marked with ###
                if line.startswith('###'):
                    continue
                    
                # Add pattern to the list
                if line not in self.patterns:  # avoid duplicates
                    self.patterns.append(line)
                    
                    # Convert glob pattern to regex
                    regex = fnmatch.translate(line)
                    
                    # Make the regex match anywhere in the path for more aggressive matching
                    if not line.startswith('**/'):
                        regex = regex.replace(r'\A', r'')
                    if not line.endswith('/**'):
                        regex = regex.replace(r'\Z', r'')
                        
                    # Add specific handling for directory patterns
                    if line.endswith('/'):
                        # Match any path that contains this directory
                        dir_name = line.rstrip('/')
                        dir_pattern = f"**/{dir_name}/**"
                        if dir_pattern not in self.patterns:
                            self.patterns.append(dir_pattern)
                            self.regex_patterns.append(re.compile(fnmatch.translate(dir_pattern)))
                    
                    self.regex_patterns.append(re.compile(regex))
                    
            print(f"Loaded {len(self.patterns)} ignore patterns (including common directories)")
        except Exception as e:
            print(f"Error loading ignore patterns: {e}")
            # Initialize with empty patterns
            self.patterns = []
            self.regex_patterns = []
    
    def should_ignore(self, path: Union[str, pathlib.Path]) -> bool:
        """
        Check if a path should be ignored based on the loaded patterns.
        Improved with more aggressive path matching and common directory detection.
        
        Args:
            path: Path to check
            
        Returns:
            True if the path should be ignored, False otherwise
        """
        if isinstance(path, pathlib.Path):
            path_str = str(path)
        else:
            path_str = path
            path = pathlib.Path(path_str)
            
        # Quick check for common ignored directories
        path_parts = path_str.split('/')
        for part in path_parts:
            if part in self.common_ignored_dirs:
                return True
                
        # Handle negation patterns first (patterns starting with !)
        for pattern in self.patterns:
            if pattern.startswith('!'):
                # Negation means explicitly don't ignore
                negate_pattern = pattern[1:]
                if fnmatch.fnmatch(path_str, negate_pattern):
                    return False
        
        # Check direct pattern matches
        for pattern in self.patterns:
            if pattern.startswith('!'):
                continue  # Skip negation patterns, already handled
                
            # Standard matching
            if fnmatch.fnmatch(path_str, pattern):
                return True
        
        # Special case for node_modules and other common directories
        # More aggressive check that looks for these anywhere in the path
        for common_dir in self.common_ignored_dirs:
            if f"/{common_dir}/" in path_str or path_str.endswith(f"/{common_dir}"):
                return True
        
        # Check path components (parent directories)
        path_parts = list(path.parts)
        for i in range(1, len(path_parts) + 1):
            # Check each parent directory
            partial_path = str(pathlib.Path(*path_parts[:i]))
            
            for pattern in self.patterns:
                if pattern.startswith('!'):
                    continue  # Skip negation patterns, already handled
                    
                if fnmatch.fnmatch(partial_path, pattern):
                    return True
                    
        return False


# Create a singleton instance for easy access
_default_matcher = None

def get_matcher() -> IgnorePatternMatcher:
    """Get the default IgnorePatternMatcher instance."""
    global _default_matcher
    if _default_matcher is None:
        _default_matcher = IgnorePatternMatcher()
    return _default_matcher

def should_ignore(path: Union[str, pathlib.Path]) -> bool:
    """
    Check if a path should be ignored based on the loaded patterns.
    
    Args:
        path: Path to check
        
    Returns:
        True if the path should be ignored, False otherwise
    """
    return get_matcher().should_ignore(path)

def reload_patterns() -> None:
    """Reload the ignore patterns from the file."""
    get_matcher().load_patterns()