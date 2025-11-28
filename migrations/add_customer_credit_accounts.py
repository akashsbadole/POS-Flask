"""
Add customer credit accounts functionality
This migration adds credit account fields to customers table and creates credit_transactions table
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from sqlalchemy import text

def upgrade():
    """Add credit account fields to customers table and create credit_transactions table"""
    
    # Create credit_transactions table
    db.session.execute(text("""
        CREATE TABLE IF NOT EXISTS credit_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            transaction_type VARCHAR(20) NOT NULL,
            amount DECIMAL(12, 2) NOT NULL,
            balance_before DECIMAL(12, 2) NOT NULL,
            balance_after DECIMAL(12, 2) NOT NULL,
            description TEXT,
            reference_type VARCHAR(50),
            reference_id INTEGER,
            created_by INTEGER,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (customer_id) REFERENCES customers (id),
            FOREIGN KEY (created_by) REFERENCES users (id)
        )
    """))
    
    # Add credit account fields to customers table (one at a time for SQLite compatibility)
    db.session.execute(text("ALTER TABLE customers ADD COLUMN credit_limit DECIMAL(12, 2) DEFAULT 0.00"))
    db.session.execute(text("ALTER TABLE customers ADD COLUMN current_balance DECIMAL(12, 2) DEFAULT 0.00"))
    db.session.execute(text("ALTER TABLE customers ADD COLUMN available_credit DECIMAL(12, 2) DEFAULT 0.00"))
    db.session.execute(text("ALTER TABLE customers ADD COLUMN credit_account_active BOOLEAN DEFAULT FALSE"))
    db.session.execute(text("ALTER TABLE customers ADD COLUMN credit_terms INTEGER DEFAULT 30"))
    db.session.execute(text("ALTER TABLE customers ADD COLUMN last_credit_activity DATETIME"))
    
    # Create index for credit transactions
    db.session.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_credit_transactions_customer_id 
        ON credit_transactions (customer_id)
    """))
    
    db.session.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_credit_transactions_created_at 
        ON credit_transactions (created_at)
    """))
    
    db.session.commit()
    print("Customer credit accounts migration completed successfully")

def downgrade():
    """Remove credit account fields and tables"""
    
    # Drop credit_transactions table
    db.session.execute(text("DROP TABLE IF EXISTS credit_transactions"))
    
    # Remove credit account fields from customers table (SQLite doesn't support DROP COLUMN)
    # Create backup and recreate table without credit fields
    db.session.execute(text("CREATE TABLE customers_backup AS SELECT * FROM customers"))
    db.session.execute(text("DROP TABLE customers"))
    
    db.session.execute(text("""
        CREATE TABLE customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(100) NOT NULL,
            email VARCHAR(120),
            phone VARCHAR(20),
            address TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """))
    
    db.session.execute(text("""
        INSERT INTO customers (id, name, email, phone, address, created_at, updated_at)
        SELECT id, name, email, phone, address, created_at, updated_at FROM customers_backup
    """))
    
    db.session.execute(text("DROP TABLE customers_backup"))
    
    db.session.commit()
    print("Customer credit accounts migration rolled back successfully")

if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        upgrade()