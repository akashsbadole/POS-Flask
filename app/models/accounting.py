from datetime import datetime
from enum import Enum
from app import db

class AccountType(Enum):
    ASSET = 'asset'
    LIABILITY = 'liability'
    EQUITY = 'equity'
    REVENUE = 'revenue'
    EXPENSE = 'expense'

class Account(db.Model):
    __tablename__ = 'accounts'
    
    id = db.Column(db.Integer, primary_key=True)
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurants.id'), nullable=False)
    account_number = db.Column(db.String(20), unique=True, nullable=False)
    account_name = db.Column(db.String(100), nullable=False)
    account_type = db.Column(db.Enum(AccountType), nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=True)
    description = db.Column(db.Text)
    opening_balance = db.Column(db.Numeric(15, 2), default=0.00)
    current_balance = db.Column(db.Numeric(15, 2), default=0.00)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    restaurant = db.relationship('Restaurant', backref='accounts')
    parent = db.relationship('Account', remote_side=[id], backref='children')
    debit_entries = db.relationship('TransactionEntry', foreign_keys='TransactionEntry.debit_account_id', backref='debit_account', lazy='select')
    credit_entries = db.relationship('TransactionEntry', foreign_keys='TransactionEntry.credit_account_id', backref='credit_account', lazy='select')
    
    def get_balance(self):
        """Calculate current balance from transaction entries"""
        total_debits = db.session.query(db.func.sum(TransactionEntry.debit_amount)).filter_by(debit_account_id=self.id).scalar() or 0
        total_credits = db.session.query(db.func.sum(TransactionEntry.credit_amount)).filter_by(credit_account_id=self.id).scalar() or 0
        return float(total_credits) - float(total_debits)
    
    def get_account_type_display(self):
        """Get display name for account type"""
        type_names = {
            AccountType.ASSET: 'Asset',
            AccountType.LIABILITY: 'Liability',
            AccountType.EQUITY: 'Equity',
            AccountType.REVENUE: 'Revenue',
            AccountType.EXPENSE: 'Expense'
        }
        return type_names.get(self.account_type, self.account_type)
    
    def to_dict(self):
        """Convert account to dictionary for API responses"""
        return {
            'id': self.id,
            'restaurant_id': self.restaurant_id,
            'account_number': self.account_number,
            'account_name': self.account_name,
            'account_type': self.account_type.value if self.account_type else None,
            'account_type_display': self.get_account_type_display(),
            'parent_id': self.parent_id,
            'description': self.description,
            'opening_balance': float(self.opening_balance),
            'current_balance': float(self.current_balance),
            'calculated_balance': self.get_balance(),
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self):
        return f'<Account {self.account_number} - {self.account_name}>'

class Transaction(db.Model):
    __tablename__ = 'transactions'
    
    id = db.Column(db.Integer, primary_key=True)
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurants.id'), nullable=False)
    transaction_date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    reference_number = db.Column(db.String(50))
    description = db.Column(db.Text, nullable=False)
    total_amount = db.Column(db.Numeric(15, 2), nullable=False)
    transaction_type = db.Column(db.Enum('sale', 'purchase', 'expense', 'income', 'adjustment'), nullable=False)
    status = db.Column(db.Enum('draft', 'posted', 'reversed'), default='draft')
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    approved_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    approved_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    restaurant = db.relationship('Restaurant', backref='transactions')
    entries = db.relationship('TransactionEntry', backref='transaction', lazy='select', cascade='all, delete-orphan')
    creator = db.relationship('User', foreign_keys=[created_by], backref='created_transactions')
    approver = db.relationship('User', foreign_keys=[approved_by], backref='approved_transactions')
    
    def get_total_debits(self):
        """Get total debit amount"""
        from app.models.accounting import TransactionEntry
        total_debits = db.session.query(db.func.sum(TransactionEntry.debit_amount)).filter_by(transaction_id=self.id).scalar() or 0
        return float(total_debits)
    
    def get_total_credits(self):
        """Get total credit amount"""
        from app.models.accounting import TransactionEntry
        total_credits = db.session.query(db.func.sum(TransactionEntry.credit_amount)).filter_by(transaction_id=self.id).scalar() or 0
        return float(total_credits)
    
    def is_balanced(self):
        """Check if transaction is balanced"""
        total_debits = self.get_total_debits()
        total_credits = self.get_total_credits()
        return abs(total_debits - total_credits) < 0.01  # Small tolerance for floating point
    
    def post_transaction(self, user_id):
        """Post transaction to ledger"""
        if not self.is_balanced():
            raise ValueError("Transaction is not balanced")
        
        self.status = 'posted'
        self.approved_by = user_id
        self.approved_at = datetime.utcnow()
    
    def to_dict(self, include_entries=True):
        """Convert transaction to dictionary for API responses"""
        result = {
            'id': self.id,
            'restaurant_id': self.restaurant_id,
            'transaction_date': self.transaction_date.isoformat() if self.transaction_date else None,
            'reference_number': self.reference_number,
            'description': self.description,
            'total_amount': float(self.total_amount),
            'transaction_type': self.transaction_type,
            'status': self.status,
            'total_debits': self.get_total_debits(),
            'total_credits': self.get_total_credits(),
            'is_balanced': self.is_balanced(),
            'created_by': self.created_by,
            'approved_by': self.approved_by,
            'approved_at': self.approved_at.isoformat() if self.approved_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
        
        if include_entries:
            from app.models.accounting import TransactionEntry
            entries = TransactionEntry.query.filter_by(transaction_id=self.id).all()
            result['entries'] = [entry.to_dict() for entry in entries]
        else:
            result['entries'] = []
        
        return result
    
    def __repr__(self):
        return f'<Transaction {self.reference_number} ({self.status})>'

class TransactionEntry(db.Model):
    __tablename__ = 'transaction_entries'
    
    id = db.Column(db.Integer, primary_key=True)
    transaction_id = db.Column(db.Integer, db.ForeignKey('transactions.id'), nullable=False)
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=False)
    debit_account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=True)
    credit_account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=True)
    description = db.Column(db.Text)
    debit_amount = db.Column(db.Numeric(15, 2), default=0.00)
    credit_amount = db.Column(db.Numeric(15, 2), default=0.00)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    account = db.relationship('Account', foreign_keys=[account_id], backref='account_entries', lazy='select')
    
    def get_entry_type(self):
        """Determine if this is a debit or credit entry"""
        if float(self.debit_amount) > 0:
            return 'debit'
        elif float(self.credit_amount) > 0:
            return 'credit'
        return 'neutral'
    
    def get_amount(self):
        """Get the amount (positive value)"""
        return max(float(self.debit_amount), float(self.credit_amount))
    
    def to_dict(self):
        """Convert transaction entry to dictionary for API responses"""
        return {
            'id': self.id,
            'transaction_id': self.transaction_id,
            'account_id': self.account_id,
            'account_name': self.account.account_name if self.account else None,
            'debit_account_id': self.debit_account_id,
            'credit_account_id': self.credit_account_id,
            'description': self.description,
            'debit_amount': float(self.debit_amount),
            'credit_amount': float(self.credit_amount),
            'entry_type': self.get_entry_type(),
            'amount': self.get_amount(),
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def __repr__(self):
        return f'<TransactionEntry {self.account.account_name if self.account else "Unknown"}: {self.get_amount()}>'

class Expense(db.Model):
    __tablename__ = 'expenses'
    
    id = db.Column(db.Integer, primary_key=True)
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurants.id'), nullable=False)
    category = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    amount = db.Column(db.Numeric(15, 2), nullable=False)
    expense_date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    receipt_number = db.Column(db.String(50))
    vendor = db.Column(db.String(200))
    payment_method = db.Column(db.Enum('cash', 'card', 'bank_transfer', 'check'))
    receipt_image = db.Column(db.String(255))
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    restaurant = db.relationship('Restaurant', backref='expenses')
    creator = db.relationship('User', foreign_keys=[created_by], backref='created_expenses')
    
    def to_dict(self):
        """Convert expense to dictionary for API responses"""
        return {
            'id': self.id,
            'restaurant_id': self.restaurant_id,
            'category': self.category,
            'description': self.description,
            'amount': float(self.amount),
            'expense_date': self.expense_date.isoformat() if self.expense_date else None,
            'receipt_number': self.receipt_number,
            'vendor': self.vendor,
            'payment_method': self.payment_method,
            'receipt_image': self.receipt_image,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self):
        return f'<Expense {self.category}: ${self.amount}>'