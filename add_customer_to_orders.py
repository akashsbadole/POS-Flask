#!/usr/bin/env python3
"""
Database migration script to add customer_id column to orders table
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from sqlalchemy import text

def add_customer_column():
    """Add customer_id column to orders table"""
    app = create_app()
    
    with app.app_context():
        try:
            # Check if column already exists
            result = db.session.execute(text("""
                PRAGMA table_info(orders)
            """))
            
            columns = [row[1] for row in result.fetchall()]
            column_exists = 'customer_id' in columns
            
            if not column_exists:
                print("Adding customer_id column to orders table...")
                
                # Add the column
                db.session.execute(text("""
                    ALTER TABLE orders 
                    ADD COLUMN customer_id INTEGER REFERENCES customers(id)
                """))
                
                # Create index for performance
                db.session.execute(text("""
                    CREATE INDEX idx_orders_customer_id ON orders(customer_id)
                """))
                
                db.session.commit()
                print("customer_id column added successfully")
            else:
                print("customer_id column already exists")
                
        except Exception as e:
            print(f"Error adding customer_id column: {e}")
            db.session.rollback()
            return False
            
    return True

if __name__ == "__main__":
    print("Starting database migration: Add customer_id to orders table")
    success = add_customer_column()
    
    if success:
        print("Migration completed successfully!")
    else:
        print("Migration failed!")
        sys.exit(1)