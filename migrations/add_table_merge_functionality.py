#!/usr/bin/env python3
"""
Migration script to add table merge/split functionality
"""

import sys
import os
from datetime import datetime

# Add project directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models.table import table_merges, TableMerge


def upgrade():
    """Add table merge functionality to existing database"""
    app = create_app()
    
    with app.app_context():
        print("Creating table merge association table...")
        
        # Check if table_merges table already exists
        inspector = db.inspect(db.engine)
        if 'table_merges' not in inspector.get_table_names():
            # Create the association table for table merges
            table_merges.create(db.engine)
            print("Created table_merges association table")
        else:
            print("table_merges table already exists")
        
        # Check if table_merge_operations table already exists
        if 'table_merge_operations' not in inspector.get_table_names():
            # Create the table merge operations table
            TableMerge.__table__.create(db.engine)
            print("Created table_merge_operations table")
        else:
            print("table_merge_operations table already exists")
        
        # Commit changes
        db.session.commit()
        print("Table merge functionality added successfully")


def downgrade():
    """Remove table merge functionality from database"""
    app = create_app()
    
    with app.app_context():
        print("Removing table merge functionality...")
        
        # Drop tables in reverse order of creation
        inspector = db.inspect(db.engine)
        
        if 'table_merge_operations' in inspector.get_table_names():
            TableMerge.__table__.drop(db.engine)
            print("Dropped table_merge_operations table")
        
        if 'table_merges' in inspector.get_table_names():
            table_merges.drop(db.engine)
            print("Dropped table_merges table")
        
        # Commit changes
        db.session.commit()
        print("Table merge functionality removed successfully")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "downgrade":
        downgrade()
    else:
        upgrade()