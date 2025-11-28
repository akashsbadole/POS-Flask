#!/usr/bin/env python3
"""
Migration script to add timer fields to orders table
"""

import sqlite3
from app import create_app

def add_timer_fields_to_orders():
    """Add timer-related fields to orders table"""
    app = create_app()
    
    with app.app_context():
        # Connect to database
        conn = sqlite3.connect('instance/pos_dev.db')
        cursor = conn.cursor()
        
        error_occurred = False
        
        try:
            # Add estimated_preparation_time column
            cursor.execute('''
                ALTER TABLE orders ADD COLUMN estimated_preparation_time INTEGER
            ''')
            print("Added estimated_preparation_time column")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                print("estimated_preparation_time column already exists")
            else:
                print("Error adding estimated_preparation_time: {}".format(str(e)))
                error_occurred = True
        
        try:
            # Add actual_preparation_time column
            cursor.execute('''
                ALTER TABLE orders ADD COLUMN actual_preparation_time INTEGER
            ''')
            print("Added actual_preparation_time column")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                print("actual_preparation_time column already exists")
            else:
                print("Error adding actual_preparation_time: {}".format(str(e)))
                error_occurred = True
        
        try:
            # Add timer_started_at column
            cursor.execute('''
                ALTER TABLE orders ADD COLUMN timer_started_at DATETIME
            ''')
            print("Added timer_started_at column")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                print("timer_started_at column already exists")
            else:
                print("Error adding timer_started_at: {}".format(str(e)))
                error_occurred = True
        
        try:
            # Add timer_completed_at column
            cursor.execute('''
                ALTER TABLE orders ADD COLUMN timer_completed_at DATETIME
            ''')
            print("Added timer_completed_at column")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                print("timer_completed_at column already exists")
            else:
                print("Error adding timer_completed_at: {}".format(str(e)))
                error_occurred = True
        
        if not error_occurred:
            # Commit changes
            conn.commit()
            print("Migration completed successfully!")
        else:
            # Rollback changes if any error occurred
            try:
                conn.rollback()
            except:
                pass
        
        # Close connection
        try:
            conn.close()
        except:
            pass

if __name__ == '__main__':
    add_timer_fields_to_orders()