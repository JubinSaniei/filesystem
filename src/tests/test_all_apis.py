#!/usr/bin/env python3
"""
Master test script that runs all API verification tests in sequence.
This ensures all APIs are working correctly before deployment.
"""
import os
import sys
import time
import subprocess
import argparse

# Add the project root to the path so modules can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.utils.config import API_URL

def run_test(test_file, description):
    """Run a test file and print its output"""
    print(f"\n{'='*80}")
    print(f"RUNNING TEST: {description}")
    print(f"FILE: {test_file}")
    print(f"{'='*80}\n")
    
    try:
        # Run the test script as a subprocess
        result = subprocess.run([sys.executable, test_file], 
                                capture_output=True, text=True)
        
        # Print the output
        print("\nSTDOUT:")
        print(result.stdout)
        
        # Print any errors
        if result.stderr:
            print("\nSTDERR:")
            print(result.stderr)
            
        print(f"\n{'='*80}")
        print(f"TEST COMPLETED: {'SUCCESS' if result.returncode == 0 else 'FAILED'}")
        print(f"{'='*80}\n")
        
        return result.returncode == 0
    except Exception as e:
        print(f"Error running test: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Run all API tests')
    parser.add_argument('--test', type=str, help='Run specific test (basic, extended, remaining, metadata, all)')
    parser.add_argument('--api-url', type=str, help=f'Override API URL (default: {API_URL})')
    args = parser.parse_args()
    
    # Get the directory of this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Define the tests
    tests = {
        'basic': {
            'file': os.path.join(script_dir, 'verify_api.py'),
            'desc': 'Basic API Functionality'
        },
        'extended': {
            'file': os.path.join(script_dir, 'verify_extended_api.py'),
            'desc': 'Extended API Functionality'
        },
        'remaining': {
            'file': os.path.join(script_dir, 'verify_remaining_api.py'),
            'desc': 'Remaining API Endpoints'
        },
        'metadata': {
            'file': os.path.join(script_dir, 'verify_metadata_api.py'),
            'desc': 'Metadata API Endpoints'
        }
    }
    
    # Print info header
    print("\n" + "="*80)
    print(f"TESTING FILESYSTEM SERVER APIs")
    print(f"API URL: {API_URL}")
    print("="*80 + "\n")
    
    # Wait for the server to be fully initialized
    print("Waiting 3 seconds for server to be fully initialized...")
    time.sleep(3)

    # Track results
    results = {}
    
    if args.test == 'all' or args.test is None:
        # Run all tests
        for test_name, test_info in tests.items():
            results[test_name] = run_test(test_info['file'], test_info['desc'])
    elif args.test in tests:
        # Run a specific test
        test_info = tests[args.test]
        results[args.test] = run_test(test_info['file'], test_info['desc'])
    else:
        print(f"Unknown test: {args.test}")
        print(f"Available tests: {', '.join(tests.keys())}")
        return 1
    
    # Print summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    all_passed = True
    for test_name, passed in results.items():
        status = "PASSED" if passed else "FAILED"
        print(f"{test_name.ljust(15)}: {status}")
        if not passed:
            all_passed = False
    
    print("\nOVERALL RESULT: " + ("PASSED" if all_passed else "FAILED"))
    print("="*80 + "\n")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())