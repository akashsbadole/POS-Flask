"""
Migration script for creating table assignment tables
This script creates the table_assignments table to track waiter-to-table assignments
including performance metrics and assignment history.
"""

from app import create_app, db
from app.models.table_assignment import TableAssignment

def create_table_assignment_tables():
    """Create table assignment related tables"""
    app = create_app()
    
    with app.app_context():
        print("Creating table assignment tables...")
        
        # Create tables
        tables_to_create = [
            TableAssignment.__table__
        ]
        
        # Create tables
        for table in tables_to_create:
            try:
                table.create(db.engine, checkfirst=True)
                print(f"✓ Created table: {table.name}")
            except Exception as e:
                print(f"✗ Error creating table {table.name}: {str(e)}")
        
        print("Table assignment tables creation completed!")

if __name__ == '__main__':
    create_table_assignment_tables()
    print("Table assignment migration completed successfully!")