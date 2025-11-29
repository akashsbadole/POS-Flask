#!/usr/bin/env python3
"""
Migration script to create settings and settings_change_log tables
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models.setting import Setting, SettingsChangeLog

def create_settings_tables():
    """Create settings and settings_change_log tables"""
    app = create_app()
    
    with app.app_context():
        print("Creating settings tables...")
        
        # Create tables
        Setting.__table__.create(db.engine, checkfirst=True)
        SettingsChangeLog.__table__.create(db.engine, checkfirst=True)
        
        print("Settings tables created successfully!")
        
        # Initialize default settings
        from app.services.settings_service import SettingsService
        try:
            SettingsService.initialize_default_settings()
            print("Default settings initialized successfully!")
        except Exception as e:
            print(f"Error initializing default settings: {e}")

if __name__ == "__main__":
    create_settings_tables()