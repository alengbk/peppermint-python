#!/usr/bin/env python3
"""Test script for Peppermint Python API"""

import requests
import json
import sys

BASE_URL = "http://localhost:5003/api/v1"

def test_first_setup():
    """Check first time setup"""
    print("\n=== Testing GET /api/v1/auth/check-first-setup ===")
    response = requests.get(f"{BASE_URL}/auth/check-first-setup")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")

def test_login():
    """Test POST /api/v1/auth/login"""
    print("\n=== Testing POST /api/v1/auth/login ===")
    # First we need to create a user. The first_time_setup should allow creating first admin
    payload = {
        "email": "admin@test.com",
        "password": "admin123"
    }
    
    # Try OAuth2 form login
    response = requests.post(f"{BASE_URL}/auth/login", data={"username": "Admin User", "password": "admin123"})
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    
    if response.status_code == 200:
        return response.json()["access_token"]
    return None

def test_register(token):
    """Test POST /api/v1/auth/user/register (requires admin)"""
    print("\n=== Testing POST /api/v1/auth/user/register ===")
    
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "email": "user@test.com",
        "password": "user123",
        "name": "Test User",
        "admin": False
    }
    
    response = requests.post(f"{BASE_URL}/auth/user/register", json=payload, headers=headers)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")

def test_get_me(token):
    """Test GET /api/v1/auth/me"""
    print("\n=== Testing GET /api/v1/auth/me ===")
    
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/auth/me", headers=headers)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")

def test_create_client(token):
    """Test POST /api/v1/client"""
    print("\n=== Testing POST /api/v1/client ===")
    
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "name": "Test Company",
        "email": "company@test.com",
        "contactName": "John Doe",
        "number": "+1234567890",
        "notes": "Test client"
    }
    
    response = requests.post(f"{BASE_URL}/client", json=payload, headers=headers)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    
    if response.status_code == 200:
        return response.json()["id"]
    return None

def test_create_ticket_authenticated(token, client_id=None):
    """Test POST /api/v1/ticket (authenticated)"""
    print("\n=== Testing POST /api/v1/ticket (authenticated) ===")
    
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "title": "Authenticated Ticket",
        "detail": "Created by authenticated user",
        "priority": "medium",
        "type": "feature"
    }
    
    if client_id:
        payload["company"] = {"id": client_id}
    
    response = requests.post(f"{BASE_URL}/ticket", json=payload, headers=headers)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    
    if response.status_code == 200:
        return response.json()["id"]
    return None

def test_list_tickets(token):
    """Test GET /api/v1/ticket"""
    print("\n=== Testing GET /api/v1/ticket ===")
    
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/ticket", headers=headers)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")

def test_get_ticket(token, ticket_id):
    """Test GET /api/v1/ticket/{id}"""
    print(f"\n=== Testing GET /api/v1/ticket/{ticket_id} ===")
    
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/ticket/{ticket_id}", headers=headers)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")

def test_update_ticket(token, ticket_id):
    """Test PUT /api/v1/ticket/{id}"""
    print(f"\n=== Testing PUT /api/v1/ticket/{ticket_id} ===")
    
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "status": "in_progress",
        "priority": "high"
    }
    
    response = requests.put(f"{BASE_URL}/ticket/{ticket_id}", json=payload, headers=headers)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")

def test_comment_create(token, ticket_id):
    """Test POST /api/v1/comment"""
    print(f"\n=== Testing POST /api/v1/comment (ticket: {ticket_id}) ===")
    
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "text": "This is a test comment from API",
        "public": False
    }
    
    response = requests.post(f"{BASE_URL}/comment?ticketId={ticket_id}", json=payload, headers=headers)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")

def test_comment_list(token, ticket_id):
    """Test GET /api/v1/comment/ticket/{id}"""
    print(f"\n=== Testing GET /api/v1/comment/ticket/{ticket_id} ===")
    
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/comment/ticket/{ticket_id}", headers=headers)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")

def test_config(token):
    """Test GET /api/v1/config"""
    print("\n=== Testing GET /api/v1/config ===")
    
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/config", headers=headers)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")

def test_complete_setup(token):
    """Test POST /api/v1/config/complete-setup"""
    print("\n=== Testing POST /api/v1/config/complete-setup ===")
    
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.post(f"{BASE_URL}/config/complete-setup", headers=headers)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")

def main():
    print("=" * 50)
    print("Peppermint Python API Test Suite")
    print("=" * 50)
    
    # Check first setup
    test_first_setup()
    
    # Complete setup first (since first_time_setup is true)
    # We need to do this before login
    print("\n=== Completing first time setup ===")
    # We'll need to register first user somehow
    # The first_time_setup = true means no users exist yet
    
    # Try to complete setup without auth (should fail)
    response = requests.post(f"{BASE_URL}/config/complete-setup")
    print(f"Complete setup without auth: {response.status_code}")
    
    # The system should allow creating first admin when first_time_setup is true
    # Let's try registering a user
    print("\n=== Creating first admin user ===")
    payload = {
        "email": "admin@test.com",
        "password": "admin123",
        "name": "Admin User",
        "admin": True
    }
    response = requests.post(f"{BASE_URL}/auth/user/register", json=payload)
    print(f"Register status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    
    # Now try login
    token = test_login()
    
    if not token:
        print("\n❌ Login failed - cannot continue tests")
        return
    
    print(f"\n✅ Got token: {token[:20]}...")
    
    # Test authenticated endpoints
    test_get_me(token)
    test_complete_setup(token)
    test_config(token)
    
    # Create client
    client_id = test_create_client(token)
    
    # Create authenticated ticket
    auth_ticket_id = test_create_ticket_authenticated(token, client_id)
    
    # List tickets
    test_list_tickets(token)
    
    # Test ticket detail
    if auth_ticket_id:
        test_get_ticket(token, auth_ticket_id)
        test_update_ticket(token, auth_ticket_id)
        test_comment_create(token, auth_ticket_id)
        test_comment_list(token, auth_ticket_id)
    

    
    print("\n" + "=" * 50)
    print("All tests completed!")
    print("=" * 50)

if __name__ == "__main__":
    main()