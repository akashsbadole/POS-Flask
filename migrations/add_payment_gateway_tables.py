#!/usr/bin/env python3
"""
Migration script to add payment gateway tables
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from sqlalchemy import text

def add_payment_gateway_tables():
    """Add payment gateway related tables"""
    app = create_app()
    
    with app.app_context():
        try:
            # Create payment_gateways table
            db.session.execute(text("""
                CREATE TABLE IF NOT EXISTS payment_gateways (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name VARCHAR(50) NOT NULL,
                    gateway_type VARCHAR(20) NOT NULL,
                    is_active BOOLEAN DEFAULT 1,
                    config TEXT,
                    supported_methods TEXT,
                    webhook_secret VARCHAR(255),
                    test_mode BOOLEAN DEFAULT 1,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """))
            
            # Create payment_transactions table
            db.session.execute(text("""
                CREATE TABLE IF NOT EXISTS payment_transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    subscription_id INTEGER,
                    user_id INTEGER NOT NULL,
                    gateway_id INTEGER NOT NULL,
                    transaction_id VARCHAR(100),
                    amount REAL NOT NULL,
                    currency VARCHAR(3) DEFAULT 'INR',
                    payment_method VARCHAR(20),
                    status VARCHAR(20) DEFAULT 'pending',
                    gateway_response TEXT,
                    error_code VARCHAR(50),
                    error_message TEXT,
                    processed_at DATETIME,
                    refunded_amount REAL DEFAULT 0,
                    refund_date DATETIME,
                    notes TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (subscription_id) REFERENCES subscriptions (id),
                    FOREIGN KEY (user_id) REFERENCES users (id),
                    FOREIGN KEY (gateway_id) REFERENCES payment_gateways (id)
                )
            """))
            
            # Create payment_method_configs table
            db.session.execute(text("""
                CREATE TABLE IF NOT EXISTS payment_method_configs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    gateway_id INTEGER NOT NULL,
                    method_type VARCHAR(20),
                    is_enabled BOOLEAN DEFAULT 1,
                    config TEXT,
                    min_amount REAL DEFAULT 0,
                    max_amount REAL DEFAULT 100000,
                    fee_percentage REAL DEFAULT 0,
                    fee_fixed REAL DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (gateway_id) REFERENCES payment_gateways (id)
                )
            """))
            
            # Create webhook_events table
            db.session.execute(text("""
                CREATE TABLE IF NOT EXISTS webhook_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    gateway_id INTEGER NOT NULL,
                    event_type VARCHAR(50),
                    event_data TEXT,
                    processed BOOLEAN DEFAULT 0,
                    processing_attempts INTEGER DEFAULT 0,
                    error_message TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (gateway_id) REFERENCES payment_gateways (id)
                )
            """))
            
            # Insert default payment gateways
            db.session.execute(text("""
                INSERT OR IGNORE INTO payment_gateways
                (name, gateway_type, is_active, test_mode, config, supported_methods)
                VALUES
                ('Razorpay', 'razorpay', 1, 1, '{"api_key": "", "api_secret": ""}',
                 '["card", "upi", "net_banking", "wallet"]'),
                ('Stripe', 'stripe', 1, 1, '{"publishable_key": "", "secret_key": ""}',
                 '["card"]'),
                ('Razorpay Test', 'razorpay', 1, 1, '{"api_key": "test_key", "api_secret": "test_secret"}',
                 '["card", "upi", "net_banking", "wallet"]'),
                ('Stripe Test', 'stripe', 1, 1, '{"publishable_key": "test_key", "secret_key": "test_secret"}',
                 '["card"]')
            """))
            
            # Insert default payment method configs for Razorpay
            db.session.execute(text("""
                INSERT OR IGNORE INTO payment_method_configs
                (gateway_id, method_type, is_enabled, min_amount, max_amount, fee_percentage, fee_fixed)
                SELECT g.id, m.method, 1, m.min_amount, m.max_amount, m.fee_percentage, m.fee_fixed
                FROM payment_gateways g,
                (SELECT 'card' as method, 1 as min_amount, 100000 as max_amount, 2.0 as fee_percentage, 0 as fee_fixed
                 UNION ALL
                 SELECT 'upi' as method, 1 as min_amount, 100000 as max_amount, 0.0 as fee_percentage, 0 as fee_fixed
                 UNION ALL
                 SELECT 'net_banking' as method, 100 as min_amount, 100000 as max_amount, 1.5 as fee_percentage, 0 as fee_fixed
                 UNION ALL
                 SELECT 'wallet' as method, 10 as min_amount, 10000 as max_amount, 2.5 as fee_percentage, 0 as fee_fixed) m
                WHERE g.gateway_type = 'razorpay'
            """))
            
            # Insert default payment method configs for Stripe
            db.session.execute(text("""
                INSERT OR IGNORE INTO payment_method_configs
                (gateway_id, method_type, is_enabled, min_amount, max_amount, fee_percentage, fee_fixed)
                SELECT g.id, m.method, 1, m.min_amount, m.max_amount, m.fee_percentage, m.fee_fixed
                FROM payment_gateways g,
                (SELECT 'card' as method, 50 as min_amount, 200000 as max_amount, 2.9 as fee_percentage, 3.0 as fee_fixed) m
                WHERE g.gateway_type = 'stripe'
            """))
            
            db.session.commit()
            print("Payment gateway tables created successfully!")
            
            # Print summary
            gateways = db.session.execute(text("SELECT * FROM payment_gateways")).fetchall()
            print(f"Created {len(gateways)} payment gateways:")
            for gateway in gateways:
                print(f"  - {gateway[1]} ({gateway[2]})")
                
            configs = db.session.execute(text("SELECT COUNT(*) FROM payment_method_configs")).fetchone()
            if configs:
                print(f"Created {configs[0]} payment method configurations")
            else:
                print("Created payment method configurations")
            
        except Exception as e:
            print(f"Error creating payment gateway tables: {e}")
            db.session.rollback()
            raise

if __name__ == "__main__":
    add_payment_gateway_tables()