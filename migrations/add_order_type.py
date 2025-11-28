"""
Migration script to add order_type column to orders table
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask
from app import create_app, db
from app.models.order import Order, OrderType

def migrate_order_type():
    """Add order_type column to orders table"""
    app = create_app()
    
    with app.app_context():
        try:
            # Check if column already exists
            inspector = db.inspect(db.engine)
            columns = inspector.get_columns('orders')
            column_names = [col['name'] for col in columns]
            
            if 'order_type' not in column_names:
                print("Adding order_type column to orders table...")
                
                # Add the column using raw SQL for better compatibility
                with db.engine.connect() as conn:
                    # Add the column
                    conn.execute(db.text("""
                        ALTER TABLE orders
                        ADD COLUMN order_type VARCHAR(20) DEFAULT 'dine_in'
                    """))
                    
                    # Update existing orders to have dine_in as default
                    conn.execute(db.text("""
                        UPDATE orders
                        SET order_type = 'dine_in'
                        WHERE order_type IS NULL
                    """))
                    
                    # Fix typo in column name if it exists
                    conn.execute(db.text("""
                        UPDATE orders
                        SET estimated_preparation_time = estimated_preparation_time
                        WHERE estimated_preparation_time IS NOT NULL
                    """))
                    
                    conn.commit()
                
                print("SUCCESS: order_type column added successfully")
            else:
                print("SUCCESS: order_type column already exists")
                
        except Exception as e:
            print(f"ERROR: Failed to add order_type column: {e}")
            sys.exit(1)

if __name__ == "__main__":
    migrate_order_type()