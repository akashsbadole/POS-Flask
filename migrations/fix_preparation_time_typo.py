"""
Migration script to fix typo in preparation time column name
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db

def fix_preparation_time_typo():
    """Fix typo in preparation time column name"""
    app = create_app()
    
    with app.app_context():
        try:
            # Check if column with typo exists
            inspector = db.inspect(db.engine)
            columns = inspector.get_columns('orders')
            column_names = [col['name'] for col in columns]
            
            if 'estimated_preparation_time' in column_names:
                print("Fixing preparation time column typo...")
                
                # Add the correct column if it doesn't exist
                if 'estimated_preparation_time' not in column_names:
                    with db.engine.connect() as conn:
                        conn.execute(db.text("""
                            ALTER TABLE orders 
                            ADD COLUMN estimated_preparation_time INTEGER
                        """))
                        conn.commit()
                
                # Copy data from incorrect column to correct column
                with db.engine.connect() as conn:
                    conn.execute(db.text("""
                        UPDATE orders 
                        SET estimated_preparation_time = estimated_preparation_time 
                        WHERE estimated_preparation_time IS NOT NULL
                    """))
                    conn.commit()
                
                print("SUCCESS: Fixed preparation time column typo")
            else:
                print("SUCCESS: Preparation time column already correct")
                
        except Exception as e:
            print(f"ERROR: Failed to fix preparation time column: {e}")
            sys.exit(1)

if __name__ == "__main__":
    fix_preparation_time_typo()