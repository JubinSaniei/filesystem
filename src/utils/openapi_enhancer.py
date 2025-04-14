"""
OpenAPI schema enhancement utilities
"""
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from typing import Dict, Any
import inspect
import logging

# Set up logging
logger = logging.getLogger(__name__)

def enhance_openapi_schema(app: FastAPI) -> None:
    """
    Enhance the FastAPI app's OpenAPI schema with natural language mappings
    
    Args:
        app: The FastAPI application instance
    """
    # Store the original openapi method
    original_openapi = app.openapi
    
    def custom_openapi():
        # Clear existing schema to force regeneration
        app.openapi_schema = None
        
        # Get the schema using the original method
        openapi_schema = original_openapi()
        
        # Enhance schema with additional metadata
        openapi_schema["info"]["x-natural-language-enabled"] = True
        openapi_schema["info"]["x-mcp-compatible"] = True
        
        # Process all routes to extract natural language mappings
        for route in app.routes:
            if hasattr(route, "endpoint") and inspect.isfunction(route.endpoint):
                endpoint = route.endpoint
                
                # Get the path and methods for this route
                path = getattr(route, "path", None)
                methods = getattr(route, "methods", [])
                
                if not path or not methods:
                    continue
                
                # Check for openapi_extra in endpoint parameters
                endpoint_params = inspect.signature(endpoint).parameters
                for param_name, param in endpoint_params.items():
                    if param.default is not inspect.Parameter.empty:
                        if hasattr(param.default, "openapi_extra") and "x-natural-language-queries" in param.default.openapi_extra:
                            # Add the natural language mappings to all methods for this path
                            for method in methods:
                                method = method.lower()
                                if path in openapi_schema["paths"] and method in openapi_schema["paths"][path]:
                                    operation = openapi_schema["paths"][path][method]
                                    operation["x-natural-language-queries"] = param.default.openapi_extra["x-natural-language-queries"]
                                    logger.info(f"Added NL mapping to {method.upper()} {path}")
                
                # Check for openapi_extra in function decorators
                if hasattr(endpoint, "openapi_extra") and "x-natural-language-queries" in endpoint.openapi_extra:
                    for method in methods:
                        method = method.lower()
                        if path in openapi_schema["paths"] and method in openapi_schema["paths"][path]:
                            operation = openapi_schema["paths"][path][method]
                            operation["x-natural-language-queries"] = endpoint.openapi_extra["x-natural-language-queries"]
                            logger.info(f"Added NL mapping from decorator to {method.upper()} {path}")
        
        # Also check for openapi_extra in the schema itself
        for path in openapi_schema["paths"]:
            for method in openapi_schema["paths"][path]:
                operation = openapi_schema["paths"][path][method]
                if "openapi_extra" in operation and "x-natural-language-queries" in operation["openapi_extra"]:
                    operation["x-natural-language-queries"] = operation["openapi_extra"]["x-natural-language-queries"]
                    logger.info(f"Added NL mapping from schema to {method.upper()} {path}")
        
        return openapi_schema
    
    # Replace the app's openapi function with our custom one
    app.openapi = custom_openapi