"""
Migration script to add timer-related fields to the orders table
Run this script to update your database schema for the countdown timer feature
"""

from app import create_app, db
from sqlalchemy import text

def add_timer_fields():
    """Add timer-related fields to the orders table"""
    app = create_app()
    
    with app.app_context():
        # Check if columns already exist
        inspector = db.inspect(db.engine)
        columns = [column['name'] for column in inspector.get_columns('orders')]
        
        # Fields to add
        fields_to_add = [
            ('estimated_preparation_time', 'INTEGER'),
            ('actual_preparation_time', 'INTEGER'),
            ('timer_started_at', 'DATETIME'),
            ('timer_completed_at', 'DATETIME')
        ]
        
        for field_name, field_type in fields_to_add:
            if field_name not in columns:
                print(f"Adding {field_name} field to orders table...")
                
                # Use raw SQL for compatibility with different database backends
                if 'sqlite' in app.config['SQLALCHEMY_DATABASE_URI']:
                    # SQLite syntax
                    db.session.execute(text(f"ALTER TABLE orders ADD COLUMN {field_name} {field_type}"))
                else:
                    # PostgreSQL/MySQL syntax
                    db.session.execute(text(f"ALTER TABLE orders ADD COLUMN {field_name} {field_type}"))
                
                print(f"Added {field_name} field successfully")
            else:
                print(f"{field_name} field already exists")
        
        # Commit changes
        db.session.commit()
        print("Migration completed successfully!")

if __name__ == '__main__':
    add_timer_fields()