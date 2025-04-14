"""
Natural language mapping utilities for enhancing the OpenAPI documentation
"""
from typing import List, Dict, Optional, Any


def nl_mapping(
    queries: Optional[List[str]] = None,
    parameter_mappings: Optional[Dict[str, List[str]]] = None,
    response_template: Optional[str] = None,
    common_paths: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Helper function to add natural language mapping to endpoints.
    
    Args:
        queries: List of natural language queries that map to this endpoint
        parameter_mappings: Dictionary mapping parameter names to natural language alternatives
        response_template: Template for formatting the response in natural language
        common_paths: Dictionary mapping natural language references to filesystem paths
        
    Returns:
        Dictionary with OpenAPI extension for natural language mapping
    """
    return {
        "x-natural-language-queries": {
            "intents": queries or [],
            "parameter_mappings": parameter_mappings or {},
            "response_template": response_template,
            "common_paths": common_paths or {}
        }
    }


# Common path references that can be reused across endpoints
COMMON_PATHS = {
    "my CodeGen folder": "/mnt/c/Sandboxes/CodeGen",
    "the CodeGen project": "/mnt/c/Sandboxes/CodeGen",
    "my project": "/mnt/c/Sandboxes/CodeGen",
    "the test directory": "/app/testdir",
    "test folder": "/app/testdir"
}


# Mappings from natural language to parameter values
COMMON_PARAMETER_MAPPINGS = {
    "directory": ["folder", "path", "location", "directory"],
    "file": ["document", "text file", "file"],
    "recursive": ["include subdirectories", "search recursively", "look in subfolders"]
}