"""
Add table order management columns to orders table
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import db
from sqlalchemy import text


def upgrade():
    """Add table order management columns to orders table"""
    from app import create_app
    app = create_app()
    with app.app_context():
        # Check existing columns
        result = db.session.execute(text('PRAGMA table_info(orders)'))
        existing_columns = [row[1] for row in result.fetchall()]
        
        # Add waiter_id column
        if 'waiter_id' not in existing_columns:
            print('Adding waiter_id column to orders table...')
            db.session.execute(text('ALTER TABLE orders ADD COLUMN waiter_id INTEGER'))
            print('waiter_id column added successfully')
        else:
            print('waiter_id column already exists')
        
        # Add seat_number column
        if 'seat_number' not in existing_columns:
            print('Adding seat_number column to orders table...')
            db.session.execute(text('ALTER TABLE orders ADD COLUMN seat_number INTEGER'))
            print('seat_number column added successfully')
        else:
            print('seat_number column already exists')
        
        # Add parent_order_id column
        if 'parent_order_id' not in existing_columns:
            print('Adding parent_order_id column to orders table...')
            db.session.execute(text('ALTER TABLE orders ADD COLUMN parent_order_id INTEGER'))
            print('parent_order_id column added successfully')
        else:
            print('parent_order_id column already exists')
        
        # Add course_number column
        if 'course_number' not in existing_columns:
            print('Adding course_number column to orders table...')
            db.session.execute(text('ALTER TABLE orders ADD COLUMN course_number INTEGER'))
            print('course_number column added successfully')
        else:
            print('course_number column already exists')
        
        # Add foreign key constraints
        try:
            db.session.execute(text('''
                ALTER TABLE orders
                ADD CONSTRAINT fk_orders_waiter_id
                FOREIGN KEY (waiter_id) REFERENCES users (id)
            '''))
            print('waiter_id foreign key constraint added')
        except Exception as e:
            print(f'waiter_id foreign key constraint already exists or failed: {e}')
        
        try:
            db.session.execute(text('''
                ALTER TABLE orders
                ADD CONSTRAINT fk_orders_parent_order_id
                FOREIGN KEY (parent_order_id) REFERENCES orders (id)
            '''))
            print('parent_order_id foreign key constraint added')
        except Exception as e:
            print(f'parent_order_id foreign key constraint already exists or failed: {e}')
        
        db.session.commit()
        print('All table order management columns added successfully')


def downgrade():
    """Remove table order management columns from orders table"""
    from app import create_app
    app = create_app()
    with app.app_context():
        # Remove foreign key constraints first
        try:
            db.session.execute(text('ALTER TABLE orders DROP CONSTRAINT fk_orders_waiter_id'))
            print('waiter_id foreign key constraint removed')
        except Exception:
            print('waiter_id foreign key constraint does not exist')
        
        try:
            db.session.execute(text('ALTER TABLE orders DROP CONSTRAINT fk_orders_parent_order_id'))
            print('parent_order_id foreign key constraint removed')
        except Exception:
            print('parent_order_id foreign key constraint does not exist')
        
        # Remove columns
        try:
            db.session.execute(text('ALTER TABLE orders DROP COLUMN waiter_id'))
            print('waiter_id column removed')
        except Exception:
            print('waiter_id column does not exist')
        
        try:
            db.session.execute(text('ALTER TABLE orders DROP COLUMN seat_number'))
            print('seat_number column removed')
        except Exception:
            print('seat_number column does not exist')
        
        try:
            db.session.execute(text('ALTER TABLE orders DROP COLUMN parent_order_id'))
            print('parent_order_id column removed')
        except Exception:
            print('parent_order_id column does not exist')
        
        try:
            db.session.execute(text('ALTER TABLE orders DROP COLUMN course_number'))
            print('course_number column removed')
        except Exception:
            print('course_number column does not exist')
        
        db.session.commit()
        print('All table order management columns removed successfully')


if __name__ == '__main__':
    upgrade()