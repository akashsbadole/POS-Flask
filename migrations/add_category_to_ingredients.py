"""
Migration script to add category column to ingredients table
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models.inventory import Ingredient
from sqlalchemy import text

def add_category_column():
    """Add category column to ingredients table"""
    app = create_app()
    
    with app.app_context():
        # Check if column already exists
        inspector = db.inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('ingredients')]
        
        if 'category' not in columns:
            # Add the column
            try:
                with db.engine.connect() as conn:
                    conn.execute(text("ALTER TABLE ingredients ADD COLUMN category VARCHAR(50) DEFAULT 'other'"))
                    conn.commit()
                print("Successfully added 'category' column to ingredients table")
            except Exception as e:
                print(f"Error adding column: {e}")
        else:
            print("Column 'category' already exists in ingredients table")

if __name__ == '__main__':
    add_category_column()