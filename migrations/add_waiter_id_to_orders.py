"""
Add waiter_id column to orders table for table order management
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import db
from app.models.order import Order


def upgrade():
    """Add waiter_id column to orders table"""
    from sqlalchemy import text
    # Add waiter_id column to orders table
    db.session.execute(text('ALTER TABLE orders ADD COLUMN waiter_id INTEGER'))
    
    # Add foreign key constraint if it doesn't exist
    try:
        db.session.execute(text('''
            ALTER TABLE orders 
            ADD CONSTRAINT fk_orders_waiter_id 
            FOREIGN KEY (waiter_id) REFERENCES users (id)
        '''))
    except Exception:
        # Constraint might already exist or table might be empty
        pass
    
    db.session.commit()


def downgrade():
    """Remove waiter_id column from orders table"""
    from sqlalchemy import text
    
    # Remove foreign key constraint first
    try:
        db.session.execute(text('ALTER TABLE orders DROP CONSTRAINT fk_orders_waiter_id'))
    except Exception:
        pass
    
    # Remove column
    db.session.execute(text('ALTER TABLE orders DROP COLUMN waiter_id'))
    db.session.commit()