import requests
import os
import sys

# Add the project root to the path so modules can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from src.utils.config import API_URL

# Index a test directory
response = requests.post(
    f"{API_URL}/index_directory",
    json={"path": "/app/testdir"}
)

print(f"Status: {response.status_code}")
print(response.json())