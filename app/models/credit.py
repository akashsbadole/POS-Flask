"""
Credit account models for customer credit management
"""
from datetime import datetime, date
from decimal import Decimal
from app import db

class CreditAccount(db.Model):
    """Credit account model for managing customer credit"""
    __tablename__ = 'credit_accounts'
    
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    credit_limit = db.Column(db.Numeric(12, 2), default=0.00)
    current_balance = db.Column(db.Numeric(12, 2), default=0.00)
    available_credit = db.Column(db.Numeric(12, 2), default=0.00)
    is_active = db.Column(db.Boolean, default=False)
    credit_terms = db.Column(db.Integer, default=30)  # Payment terms in days
    approval_limit = db.Column(db.Numeric(12, 2), default=0.00)  # Max transaction without approval
    last_activity = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    customer = db.relationship('Customer', back_populates='credit_account')
    transactions = db.relationship('CreditTransaction', back_populates='credit_account', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<CreditAccount {self.id} for Customer {self.customer_id}>'
    
    def update_available_credit(self):
        """Update available credit based on limit and balance"""
        self.available_credit = self.credit_limit - self.current_balance
        self.last_activity = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def can_charge(self, amount):
        """Check if account can charge the specified amount"""
        if not self.is_active:
            return False, "Credit account is not active"
        
        if amount > self.available_credit:
            return False, f"Insufficient credit. Available: ${self.available_credit:.2f}"
        
        if amount > self.approval_limit:
            return False, f"Amount exceeds approval limit of ${self.approval_limit:.2f}"
        
        return True, "Credit available"
    
    def charge(self, amount, order_id=None, notes=None, created_by=None):
        """Charge amount to credit account"""
        can_charge, message = self.can_charge(amount)
        if not can_charge:
            raise ValueError(message)
        
        # Create transaction
        transaction = CreditTransaction(
            credit_account_id=self.id,
            transaction_type='CHARGE',
            amount=amount,
            reference_id=order_id,
            notes=notes,
            created_by=created_by
        )
        
        # Update balance
        self.current_balance += amount
        self.update_available_credit()
        
        db.session.add(transaction)
        return transaction
    
    def make_payment(self, amount, payment_method=None, notes=None, created_by=None):
        """Make payment towards credit balance"""
        if amount <= 0:
            raise ValueError("Payment amount must be positive")
        
        if amount > self.current_balance:
            raise ValueError(f"Payment exceeds current balance of ${self.current_balance:.2f}")
        
        # Create transaction
        transaction = CreditTransaction(
            credit_account_id=self.id,
            transaction_type='PAYMENT',
            amount=-amount,  # Negative for payments
            payment_method=payment_method,
            notes=notes,
            created_by=created_by
        )
        
        # Update balance
        self.current_balance -= amount
        self.update_available_credit()
        
        db.session.add(transaction)
        return transaction
    
    def adjust_balance(self, amount, adjustment_type='MANUAL', notes=None, created_by=None):
        """Manually adjust account balance (for corrections, etc.)"""
        # Create transaction
        transaction = CreditTransaction(
            credit_account_id=self.id,
            transaction_type=adjustment_type,
            amount=amount,
            notes=notes,
            created_by=created_by
        )
        
        # Update balance
        self.current_balance += amount
        self.update_available_credit()
        
        db.session.add(transaction)
        return transaction
    
    def get_overdue_amount(self):
        """Calculate overdue amount based on credit terms"""
        if self.current_balance <= 0:
            return Decimal('0.00')
        
        # Find oldest unpaid charge
        oldest_charge = self.transactions.filter_by(transaction_type='CHARGE').order_by(CreditTransaction.created_at).first()
        if not oldest_charge:
            return Decimal('0.00')
        
        # Calculate due date
        due_date = oldest_charge.created_at.date()
        due_date = date.fromordinal(due_date.toordinal() + self.credit_terms)
        
        if date.today() > due_date:
            return self.current_balance
        
        return Decimal('0.00')
    
    def get_credit_summary(self):
        """Get summary of credit account status"""
        return {
            'credit_limit': float(self.credit_limit),
            'current_balance': float(self.current_balance),
            'available_credit': float(self.available_credit),
            'is_active': self.is_active,
            'credit_terms': self.credit_terms,
            'approval_limit': float(self.approval_limit),
            'last_activity': self.last_activity.isoformat() if self.last_activity else None,
            'overdue_amount': float(self.get_overdue_amount()),
            'transaction_count': self.transactions.count()
        }


class CreditTransaction(db.Model):
    """Credit transaction model for tracking all credit activity"""
    __tablename__ = 'credit_transactions'
    
    id = db.Column(db.Integer, primary_key=True)
    credit_account_id = db.Column(db.Integer, db.ForeignKey('credit_accounts.id'), nullable=False)
    transaction_type = db.Column(db.String(20), nullable=False)  # CHARGE, PAYMENT, ADJUSTMENT, MANUAL
    amount = db.Column(db.Numeric(12, 2), nullable=False)  # Positive for charges, negative for payments
    reference_id = db.Column(db.Integer)  # Order ID for charges
    payment_method = db.Column(db.String(50))  # For payments
    notes = db.Column(db.Text)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', back_populates='credit_transactions')
    credit_account = db.relationship('CreditAccount', back_populates='transactions')
    
    def __repr__(self):
        return f'<CreditTransaction {self.id}: {self.transaction_type} ${abs(self.amount)}>'
    
    def get_transaction_description(self):
        """Get human-readable description of transaction"""
        if self.transaction_type == 'CHARGE':
            return f"Charge for Order #{self.reference_id}" if self.reference_id else "Charge"
        elif self.transaction_type == 'PAYMENT':
            method = f" via {self.payment_method}" if self.payment_method else ""
            return f"Payment{method}"
        elif self.transaction_type == 'ADJUSTMENT':
            return "Balance Adjustment"
        elif self.transaction_type == 'MANUAL':
            return "Manual Adjustment"
        else:
            return self.transaction_type