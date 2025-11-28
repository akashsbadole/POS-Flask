#!/usr/bin/env python3
"""
Simple migration script to add timer fields to orders table
"""

import sqlite3
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import create_app

def add_timer_fields_to_orders():
    """Add timer-related fields to orders table"""
    app = create_app()
    
    with app.app_context():
        # Connect to database
        conn = sqlite3.connect('instance/pos_dev.db')
        cursor = conn.cursor()
        
        # List of columns to add
        columns_to_add = [
            ('estimated_preparation_time', 'INTEGER'),
            ('actual_preparation_time', 'INTEGER'),
            ('timer_started_at', 'DATETIME'),
            ('timer_completed_at', 'DATETIME')
        ]
        
        for column_name, column_type in columns_to_add:
            try:
                cursor.execute(f'''
                    ALTER TABLE orders ADD COLUMN {column_name} {column_type}
                ''')
                print(f"Added {column_name} column")
            except sqlite3.OperationalError as e:
                if "duplicate column name" in str(e):
                    print(f"{column_name} column already exists")
                else:
                    print(f"Error adding {column_name}: {e}")
        
        # Commit changes
        conn.commit()
        print("Migration completed successfully!")
        
        conn.close()

if __name__ == '__main__':
    add_timer_fields_to_orders()