"""
Add missing credit columns to customers table
This migration adds the credit-related columns that the Customer model expects
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from sqlalchemy import text

def upgrade():
    """Add credit account fields to customers table"""
    
    # Add credit account fields to customers table (one at a time for SQLite compatibility)
    try:
        print("Adding credit_limit column...")
        db.session.execute(text("ALTER TABLE customers ADD COLUMN credit_limit DECIMAL(12, 2) DEFAULT 0.00"))
    except Exception as e:
        print(f"credit_limit column might already exist: {e}")
    
    try:
        print("Adding current_balance column...")
        db.session.execute(text("ALTER TABLE customers ADD COLUMN current_balance DECIMAL(12, 2) DEFAULT 0.00"))
    except Exception as e:
        print(f"current_balance column might already exist: {e}")
    
    try:
        print("Adding available_credit column...")
        db.session.execute(text("ALTER TABLE customers ADD COLUMN available_credit DECIMAL(12, 2) DEFAULT 0.00"))
    except Exception as e:
        print(f"available_credit column might already exist: {e}")
    
    try:
        print("Adding credit_account_active column...")
        db.session.execute(text("ALTER TABLE customers ADD COLUMN credit_account_active BOOLEAN DEFAULT FALSE"))
    except Exception as e:
        print(f"credit_account_active column might already exist: {e}")
    
    try:
        print("Adding credit_terms column...")
        db.session.execute(text("ALTER TABLE customers ADD COLUMN credit_terms INTEGER DEFAULT 30"))
    except Exception as e:
        print(f"credit_terms column might already exist: {e}")
    
    try:
        print("Adding last_credit_activity column...")
        db.session.execute(text("ALTER TABLE customers ADD COLUMN last_credit_activity DATETIME"))
    except Exception as e:
        print(f"last_credit_activity column might already exist: {e}")
    
    db.session.commit()
    print("Customer credit columns migration completed successfully")

if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        upgrade()