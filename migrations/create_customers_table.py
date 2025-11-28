"""
Migration script to create customers table
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db

def create_customers_table():
    """Create customers table"""
    app = create_app()
    
    with app.app_context():
        try:
            # Check if table already exists
            inspector = db.inspect(db.engine)
            tables = inspector.get_table_names()
            
            if 'customers' not in tables:
                print("Creating customers table...")
                
                # Create the table using SQLAlchemy
                from app.models.customer import Customer
                Customer.__table__.create(db.engine)
                
                print("SUCCESS: customers table created successfully")
            else:
                print("SUCCESS: customers table already exists")
                
        except Exception as e:
            print(f"ERROR: Failed to create customers table: {e}")
            sys.exit(1)

if __name__ == "__main__":
    create_customers_table()