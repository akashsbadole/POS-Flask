#!/usr/bin/env python3
"""
Simple test for login functionality
"""

from app import create_app
from app.models.user import User

def test_login():
    """Test login functionality"""
    app = create_app()
    
    with app.test_client() as client:
        with app.app_context():
            # Test GET request to login page
            response = client.get('/auth/login')
            print(f"GET /auth/login - Status: {response.status_code}")
            
            # Extract CSRF token from response
            csrf_token = None
            if b'csrf_token' in response.data:
                import re
                csrf_match = re.search(b'name="csrf_token".*?value="([^"]+)"', response.data)
                if csrf_match:
                    csrf_token = csrf_match.group(1).decode('utf-8')
            
            print(f"CSRF token: {csrf_token}")
            
            # Test POST request with correct credentials
            login_data = {
                'email': 'admin@restaurant.com',
                'password': 'test123'  # Use the password that works
            }
            if csrf_token:
                login_data['csrf_token'] = csrf_token
            
            response = client.post('/auth/login', data=login_data, follow_redirects=False)
            
            print(f"POST /auth/login - Status: {response.status_code}")
            print(f"Response data: {response.data.decode()[:500]}...")
            
            # Test with HTMX headers
            hmx_data = login_data.copy()
            response = client.post('/auth/login', data=hmx_data, headers={
                'HX-Request': 'true'
            }, follow_redirects=False)
            
            print(f"POST /auth/login with HTMX - Status: {response.status_code}")
            print(f"Response data: {response.data.decode()[:500]}...")

if __name__ == '__main__':
    test_login()