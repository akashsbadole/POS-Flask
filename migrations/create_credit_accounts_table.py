"""
Create credit_accounts table for the new credit system structure
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
    
    # Update existing credit_transactions table to reference credit_accounts instead of customers
    # First, add the credit_account_id column if it doesn't exist
    try:
        db.session.execute(text("""
            ALTER TABLE credit_transactions ADD COLUMN credit_account_id INTEGER
        """))
    except:
        # Column might already exist
        pass
    
    # Add missing columns that the CreditTransaction model expects
    try:
        db.session.execute(text("""
            ALTER TABLE credit_transactions ADD COLUMN payment_method VARCHAR(50)
        """))
    except:
        pass
    
    try:
        db.session.execute(text("""
            ALTER TABLE credit_transactions ADD COLUMN notes TEXT
        """))
    except:
        pass
    
    # Remove columns that are no longer needed (SQLite doesn't support DROP COLUMN, so we'll handle this differently)
    # The old customer_id column will remain but won't be used by the new model
    
    # Create foreign key constraint
    try:
        db.session.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_credit_transactions_credit_account_id 
            ON credit_transactions (credit_account_id)
        """))
    except:
        pass
    
    # Migrate existing data: create credit accounts for customers that have credit data
    db.session.execute(text("""
        INSERT OR IGNORE INTO credit_accounts (customer_id, credit_limit, current_balance, 
                                                available_credit, is_active, credit_terms, last_activity)
        SELECT id, credit_limit, current_balance, available_credit, 
               credit_account_active, credit_terms, last_credit_activity
        FROM customers 
        WHERE credit_limit > 0 OR current_balance != 0 OR credit_account_active = 1
    """))
    
    # Update credit_transactions to reference the new credit_accounts
    db.session.execute(text("""
        UPDATE credit_transactions 
        SET credit_account_id = (
            SELECT ca.id FROM credit_accounts ca 
            WHERE ca.customer_id = credit_transactions.customer_id
        )
        WHERE credit_account_id IS NULL
    """))
    
    db.session.commit()
    print("Credit accounts table migration completed successfully")

def downgrade():
    """Remove credit_accounts table"""
    
    # Drop credit_accounts table
    db.session.execute(text("DROP TABLE IF EXISTS credit_accounts"))
    
    db.session.commit()
    print("Credit accounts table migration rolled back successfully")

if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        upgrade()