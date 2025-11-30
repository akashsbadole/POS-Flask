"""
Migration script to add is_featured column to menu_items table
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from sqlalchemy import text

def upgrade():
    """Add is_featured column to menu_items table"""
    app = create_app()
    with app.app_context():
        try:
            # Check if column already exists
            result = db.session.execute(text("""
                SELECT COUNT(*) FROM pragma_table_info('menu_items') WHERE name = 'is_featured'
            """)).scalar()
            
            if result == 0:
                # Add the column
                db.session.execute(text("""
                    ALTER TABLE menu_items 
                    ADD COLUMN is_featured BOOLEAN DEFAULT 0
                """))
                db.session.commit()
                print("SUCCESS: Added is_featured column to menu_items table")
            else:
                print("INFO: is_featured column already exists in menu_items table")
                
        except Exception as e:
            db.session.rollback()
            print(f"ERROR: Failed to add is_featured column: {e}")
            return False
        
        return True

if __name__ == "__main__":
    print("Adding is_featured column to menu_items table...")
    upgrade()
