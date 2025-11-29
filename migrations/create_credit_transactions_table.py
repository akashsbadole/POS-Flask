"""
Create credit_transactions table for the CreditTransaction model
This migration creates the credit_transactions table that the CreditTransaction model expects
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from sqlalchemy import text

def upgrade():
    """Create credit_transactions table"""
    
    # Create credit_transactions table
    db.session.execute(text("""
        CREATE TABLE IF NOT EXISTS credit_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            credit_account_id INTEGER NOT NULL,
            transaction_type VARCHAR(20) NOT NULL,
            amount DECIMAL(12, 2) NOT NULL,
            reference_id INTEGER,
            payment_method VARCHAR(50),
            notes TEXT,
            created_by INTEGER,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (credit_account_id) REFERENCES credit_accounts (id),
            FOREIGN KEY (created_by) REFERENCES users (id)
        )
    """))
    
    # Create indexes
    db.session.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_credit_transactions_credit_account_id 
        ON credit_transactions (credit_account_id)
    """))
    
    db.session.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_credit_transactions_created_at 
        ON credit_transactions (created_at)
    """))
    
    db.session.commit()
    print("Credit transactions table created successfully")

if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        upgrade()