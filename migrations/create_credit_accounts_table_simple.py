"""
Create credit_accounts table for the CreditAccount model
This migration creates the credit_accounts table that the CreditAccount model expects
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from sqlalchemy import text

def upgrade():
    """Create credit_accounts table"""
    
    # Create credit_accounts table
    db.session.execute(text("""
        CREATE TABLE IF NOT EXISTS credit_accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            credit_limit DECIMAL(12, 2) DEFAULT 0.00,
            current_balance DECIMAL(12, 2) DEFAULT 0.00,
            available_credit DECIMAL(12, 2) DEFAULT 0.00,
            is_active BOOLEAN DEFAULT FALSE,
            credit_terms INTEGER DEFAULT 30,
            approval_limit DECIMAL(12, 2) DEFAULT 0.00,
            last_activity DATETIME,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (customer_id) REFERENCES customers (id)
        )
    """))
    
    # Create indexes
    db.session.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_credit_accounts_customer_id 
        ON credit_accounts (customer_id)
    """))
    
    db.session.commit()
    print("Credit accounts table created successfully")

if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        upgrade()