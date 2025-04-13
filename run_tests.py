#!/usr/bin/env python3
"""
Run all verification tests for the Filesystem API.
"""
import subprocess
import time
import os
import sys

def run_test(script_path, description=""):
    """Run a test script and print results"""
    script_name = os.path.basename(script_path)
    print(f"\n=== Running {script_name} - {description} ===\n")
    
    try:
        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            text=True,
            check=False
        )
        
        print(f"Return code: {result.returncode}")
        
        if result.stdout:
            print("\nOutput:")
            print(result.stdout)
            
        if result.stderr:
            print("\nErrors:")
            print(result.stderr)
            
        return result.returncode == 0
    except Exception as e:
        print(f"Error running test: {e}")
        return False

def main():
    # Define test scripts to run
    test_scripts = [
        {"path": "src/tests/verify_api.py", "description": "Basic API functionality"},
        {"path": "src/tests/verify_extended_api.py", "description": "Extended API functionality"},
        {"path": "src/tests/verify_remaining_api.py", "description": "Remaining API functionality"}
    ]
    
    # Run each test
    success_count = 0
    total_tests = len(test_scripts)
    
    for test in test_scripts:
        if run_test(test["path"], test["description"]):
            success_count += 1
            
    # Print summary
    print(f"\n=== Test Summary ===")
    print(f"Passed: {success_count}/{total_tests}")
    print(f"Failed: {total_tests - success_count}/{total_tests}")
    print(f"Success rate: {success_count / total_tests * 100:.1f}%")
    
    # Return exit code based on test results
    return 0 if success_count == total_tests else 1

if __name__ == "__main__":
    sys.exit(main())