"""
Migration script to add nutritional information and scaling fields to recipes table
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from sqlalchemy import text

def migrate():
    """Add nutritional and scaling fields to recipes table"""
    app = create_app()
    
    with app.app_context():
        print("Adding nutritional and scaling fields to recipes table...")
        
        try:
            # Add nutritional fields
            nutritional_fields = [
                "calories INTEGER DEFAULT 0",
                "protein DECIMAL(8,2) DEFAULT 0.00",
                "carbohydrates DECIMAL(8,2) DEFAULT 0.00", 
                "fat DECIMAL(8,2) DEFAULT 0.00",
                "saturated_fat DECIMAL(8,2) DEFAULT 0.00",
                "trans_fat DECIMAL(8,2) DEFAULT 0.00",
                "cholesterol DECIMAL(8,2) DEFAULT 0.00",
                "sodium DECIMAL(8,2) DEFAULT 0.00",
                "fiber DECIMAL(8,2) DEFAULT 0.00",
                "sugar DECIMAL(8,2) DEFAULT 0.00",
                "vitamin_a INTEGER DEFAULT 0",
                "vitamin_c INTEGER DEFAULT 0",
                "calcium INTEGER DEFAULT 0",
                "iron INTEGER DEFAULT 0",
                "potassium INTEGER DEFAULT 0"
            ]
            
            # Add scaling fields
            scaling_fields = [
                "base_serving_size INTEGER DEFAULT 1",
                "scaling_factor DECIMAL(5,2) DEFAULT 1.0",
                "is_scalable BOOLEAN DEFAULT TRUE"
            ]
            
            # Execute ALTER TABLE statements
            for field in nutritional_fields + scaling_fields:
                try:
                    db.session.execute(text(f"ALTER TABLE recipes ADD COLUMN {field}"))
                    print(f"   Added field: {field}")
                except Exception as e:
                    if "duplicate column name" not in str(e).lower():
                        print(f"   Error adding {field}: {str(e)}")
                    else:
                        print(f"   Field {field} already exists")
            
            db.session.commit()
            print("Nutritional and scaling fields added successfully!")
            
        except Exception as e:
            print(f"Error during migration: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
        
        return True

if __name__ == '__main__':
    migrate()