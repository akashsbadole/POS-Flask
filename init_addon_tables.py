#!/usr/bin/env python3
"""
Initialize database with add-on and add-on category tables
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db

def init_addon_tables():
    """Create the new add-on related tables"""
    app = create_app()
    
    with app.app_context():
        print("Creating add-on related tables...")
        
        # Import the models to ensure they're registered with SQLAlchemy
        from app.models.menu import AddOn, AddOnCategory
        
        # Create all tables
        db.create_all()
        
        print("Database tables created successfully!")
        print("\nYou can now:")
        print("1. Run 'python test_addons.py' to test the add-on system")
        print("2. Start the Flask application to use the add-on system")

if __name__ == "__main__":
    init_addon_tables()