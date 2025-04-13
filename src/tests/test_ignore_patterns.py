import requests
import os
import sys

# Add the project root to the path so modules can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from src.utils.config import API_URL

def check_ignore_patterns():
    """Check the loaded ignore patterns"""
    try:
        # Get ignore patterns
        response = requests.get(f"{API_URL}/ignore_patterns")
        data = response.json()
        
        if data.get("status") != "enabled":
            print(f"Ignore patterns are not enabled: {data.get('message', 'Unknown error')}")
            return
        
        patterns = data.get("patterns", [])
        print(f"Total ignore patterns loaded: {len(patterns)}")
        
        # Show pattern categories
        sections = {}
        current_section = "General"
        
        for pattern in patterns:
            if pattern.startswith("###"):
                current_section = pattern[4:].strip()
                sections[current_section] = []
            else:
                if current_section not in sections:
                    sections[current_section] = []
                sections[current_section].append(pattern)
        
        # Print section summary
        print("\nPattern categories:")
        for section, section_patterns in sections.items():
            print(f"- {section}: {len(section_patterns)} patterns")
        
        # Print example patterns from each section
        print("\nExample patterns from each category:")
        for section, section_patterns in sections.items():
            print(f"\n{section}:")
            for pattern in section_patterns[:3]:  # Show first 3 patterns in each section
                print(f"  - {pattern}")
            if len(section_patterns) > 3:
                print("  - ...")
        
    except Exception as e:
        print(f"Error checking ignore patterns: {e}")

if __name__ == "__main__":
    check_ignore_patterns()