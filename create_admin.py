#!/usr/bin/env python3
"""
Script to create an admin user with the specified credentials
"""

from app import create_app, db
from app.models.user import User

def create_admin_user():
    """Create admin user with specified credentials"""
    app = create_app()
    
    with app.app_context():
        # Check if admin user already exists
        existing_user = User.query.filter_by(email='admin@restaurant.com').first()
        if existing_user:
            print("Admin user already exists with email admin@restaurant.com")
            print("Updating password...")
            existing_user.set_password('admin123')
            existing_user.set_pin('1234')
            db.session.commit()
            print("Password updated successfully!")
        else:
            # Create new admin user
            admin_user = User()
            admin_user.email = 'admin@restaurant.com'
            admin_user.name = 'Admin User'
            admin_user.role = 'super_admin'
            admin_user.set_password('admin123')
            admin_user.set_pin('1234')
            
            db.session.add(admin_user)
            db.session.commit()
            
            print("Admin user created successfully!")
            print("Email: admin@restaurant.com")
            print("Password: admin123")
            print("PIN: 1234")

if __name__ == '__main__':
    create_admin_user()