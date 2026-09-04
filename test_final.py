#!/usr/bin/env python3
"""Final test script for Peppermint Python API"""

import subprocess
import time
import requests
import os

def main():
    print("Starting to test Peppermint Python API...")
    print("=" * 60)
    
    # Start the uvicorn server
    print("1. Starting uvicorn server...")
    proc = subprocess.Popen([
        'python', '-m', 'uvicorn', 'app.main:app',
        '--host', '0.0.0.0',
        '--port', '5003',
        '--log-level', 'warning'
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    # Wait for server to start
    time.sleep(5)
    
    # Check if server is running
    try:
        response = requests.get('http://localhost:5003/', timeout=5)
        print(f'✅ Server is running! Status: {response.status_code}')
        print(f'✅ Response: {response.json()}')
    except Exception as e:
        print(f'❌ Server is not running: {e}')
        print('Checking process...')
        subprocess.run(['pkill', '-f', 'uvicorn'], capture_output=True)
        return 1
    
    # Test the API endpoints
    print("\n2. Testing API endpoints...")
    tests_passed = 0
    total_tests = 0
    
    # Test health endpoint
    total_tests += 1
    try:
        response = requests.get('http://localhost:5003/api/v1/health', timeout=5)
        if response.status_code == 200:
            print(f'✅ Health endpoint: {response.json()}')
            tests_passed += 1
        else:
            print(f'❌ Health endpoint: {response.status_code}')
    except Exception as e:
        print(f'❌ Health endpoint: {e}')
    
    # Test root endpoint
    total_tests += 1
    try:
        response = requests.get('http://localhost:5003/', timeout=5)
        if response.status_code == 200:
            print(f'✅ Root endpoint: {response.json()}')
            tests_passed += 1
        else:
            print(f'❌ Root endpoint: {response.status_code}')
    except Exception as e:
        print(f'❌ Root endpoint: {e}')
    
    # Test ticket creation requires auth (no public endpoint)
    total_tests += 1
    payload = {
        'title': 'Test Ticket',
        'detail': 'Created via API',
        'priority': 'medium',
        'type': 'support'
    }
    try:
        response = requests.post('http://localhost:5003/api/v1/ticket', json=payload, timeout=5)
        if response.status_code in (401, 403):
            print(f'✅ Ticket creation properly requires auth: {response.status_code}')
            tests_passed += 1
        else:
            print(f'❌ Ticket creation unexpected status: {response.status_code} - {response.text}')
    except Exception as e:
        print(f'❌ Ticket creation test: {e}')
    
    print("=" * 60)
    print(f'Tests passed: {tests_passed}/{total_tests}')
    if tests_passed == total_tests:
        print('✅ Peppermint Python API is working correctly!')
    else:
        print('❌ Some tests failed!')
    print("=" * 60)
    
    # Clean up
    subprocess.run(['pkill', '-f', 'uvicorn'], capture_output=True)
    return 0 if tests_passed == total_tests else 1

if __name__ == "__main__":
    exit(main())
