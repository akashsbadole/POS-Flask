"""
Customer model for Restaurant POS System
Handles customer information, loyalty programs, and order history
"""

from datetime import datetime
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app import db

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.order import Order
    from app.models.restaurant import Restaurant
    from app.models.credit import CreditAccount, CreditTransaction

class Customer(db.Model):
    """Customer model for restaurant POS system"""
    __tablename__ = 'customers'
    
    # Basic Information
    id: Mapped[int] = mapped_column(primary_key=True)
    customer_code: Mapped[str] = mapped_column(db.String(20), unique=True, nullable=False, index=True)
    first_name: Mapped[str] = mapped_column(db.String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(db.String(100), nullable=False)
    email: Mapped[str] = mapped_column(db.String(120), unique=True, nullable=True, index=True)
    phone: Mapped[str] = mapped_column(db.String(20), unique=True, nullable=True, index=True)
    company_name: Mapped[str] = mapped_column(db.String(200), nullable=True)
    
    # Address Information
    address_line1: Mapped[str] = mapped_column(db.String(200), nullable=True)
    address_line2: Mapped[str] = mapped_column(db.String(200), nullable=True)
    city: Mapped[str] = mapped_column(db.String(100), nullable=True)
    state: Mapped[str] = mapped_column(db.String(50), nullable=True)
    postal_code: Mapped[str] = mapped_column(db.String(20), nullable=True)
    country: Mapped[str] = mapped_column(db.String(100), nullable=True)
    
    # Preferences and Notes
    preferred_contact_method: Mapped[str] = mapped_column(db.Enum('email', 'phone', 'sms', 'none'), default='email')
    dietary_restrictions: Mapped[str] = mapped_column(db.Text, nullable=True)
    allergies: Mapped[str] = mapped_column(db.Text, nullable=True)
    special_notes: Mapped[str] = mapped_column(db.Text, nullable=True)
    
    # Loyalty Program
    loyalty_member: Mapped[bool] = mapped_column(db.Boolean, default=False)
    loyalty_points: Mapped[int] = mapped_column(db.Integer, default=0)
    loyalty_tier: Mapped[str] = mapped_column(db.Enum('bronze', 'silver', 'gold', 'platinum'), nullable=True)
    loyalty_member_since: Mapped[datetime] = mapped_column(db.DateTime, nullable=True)
    
    # Order Statistics
    total_orders: Mapped[int] = mapped_column(db.Integer, default=0)
    total_spent: Mapped[float] = mapped_column(db.Numeric(12, 2), default=0.00)
    average_order_value: Mapped[float] = mapped_column(db.Numeric(10, 2), default=0.00)
    last_order_date: Mapped[datetime] = mapped_column(db.DateTime, nullable=True)
    favorite_items: Mapped[str] = mapped_column(db.Text, nullable=True)  # JSON string of favorite menu items
    
    # Marketing and Communication
    marketing_consent: Mapped[bool] = mapped_column(db.Boolean, default=True)
    email_verified: Mapped[bool] = mapped_column(db.Boolean, default=False)
    phone_verified: Mapped[bool] = mapped_column(db.Boolean, default=False)
    
    # System Fields
    restaurant_id: Mapped[int] = mapped_column(db.Integer, db.ForeignKey('restaurants.id'), nullable=False)
    created_by: Mapped[int] = mapped_column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    is_active: Mapped[bool] = mapped_column(db.Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(db.DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Credit Account Fields (for backward compatibility)
    credit_limit: Mapped[float] = mapped_column(db.Numeric(12, 2), default=0.00)
    current_balance: Mapped[float] = mapped_column(db.Numeric(12, 2), default=0.00)
    available_credit: Mapped[float] = mapped_column(db.Numeric(12, 2), default=0.00)
    credit_account_active: Mapped[bool] = mapped_column(db.Boolean, default=False)
    credit_terms: Mapped[int] = mapped_column(db.Integer, default=30)
    last_credit_activity: Mapped[Optional[datetime]] = mapped_column(db.DateTime, nullable=True)
    
    # Relationships
    restaurant = relationship('Restaurant', back_populates='customers')
    creator = relationship('User', back_populates='created_customers')
    orders = relationship('Order', back_populates='customer', lazy='dynamic')
    loyalty_transactions = relationship('LoyaltyTransaction', back_populates='customer', lazy='dynamic')
    credit_account = relationship('CreditAccount', back_populates='customer', uselist=False, lazy='joined')
    credit_transactions = relationship('CreditTransaction', secondary='credit_accounts',
                                    primaryjoin='Customer.id == CreditAccount.customer_id',
                                    secondaryjoin='CreditAccount.id == CreditTransaction.credit_account_id',
                                    viewonly=True, lazy='dynamic')
    
    def get_full_name(self) -> str:
        """Get customer's full name"""
        return f"{self.first_name} {self.last_name}".strip()
    
    def get_full_address(self) -> str:
        """Get formatted full address"""
        address_parts = [self.address_line1, self.address_line2, self.city, self.state, self.postal_code, self.country]
        address_parts = [part for part in address_parts if part and part.strip()]
        return ', '.join(address_parts)
    
    def add_loyalty_points(self, points: int, description: str | None = None, order_id: int | None = None):
        """Add loyalty points to customer"""
        if points <= 0:
            return False
        
        old_points = self.loyalty_points
        self.loyalty_points += points
        
        # Create loyalty transaction
        transaction = LoyaltyTransaction(
            customer_id=self.id,
            points=points,
            transaction_type='earned',
            description=description or f"Added {points} points",
            order_id=order_id,
            balance_before=old_points,
            balance_after=self.loyalty_points
        )
        
        db.session.add(transaction)
        
        # Update loyalty tier if needed
        self.update_loyalty_tier()
        
        return True
    
    def redeem_loyalty_points(self, points: int, description: str | None = None, order_id: int | None = None):
        """Redeem loyalty points from customer"""
        if points <= 0 or self.loyalty_points < points:
            return False
        
        old_points = self.loyalty_points
        self.loyalty_points -= points
        
        # Create loyalty transaction
        transaction = LoyaltyTransaction(
            customer_id=self.id,
            points=-points,
            transaction_type='redeemed',
            description=description or f"Redeemed {points} points",
            order_id=order_id,
            balance_before=old_points,
            balance_after=self.loyalty_points
        )
        
        db.session.add(transaction)
        return True
    
    def update_loyalty_tier(self):
        """Update loyalty tier based on points"""
        if not self.loyalty_member:
            self.loyalty_tier = None  # type: ignore
            return
        
        # Tier thresholds (can be configurable)
        tier_thresholds = {
            'bronze': 0,
            'silver': 500,
            'gold': 1500,
            'platinum': 3000
        }
        
        new_tier = 'bronze'
        for tier, threshold in sorted(tier_thresholds.items(), key=lambda x: x[1], reverse=True):
            if self.loyalty_points >= threshold:
                new_tier = tier
                break
        
        if new_tier != self.loyalty_tier:
            self.loyalty_tier = new_tier
    
    def update_order_statistics(self, order_amount: float):
        """Update customer order statistics"""
        self.total_orders += 1
        self.total_spent += order_amount
        self.last_order_date = datetime.utcnow()
        
        # Calculate new average
        if self.total_orders > 0:
            self.average_order_value = self.total_spent / self.total_orders
    
    def get_loyalty_benefits(self) -> List[str]:
        """Get benefits for current loyalty tier"""
        benefits = {
            'bronze': ['Point earning', 'Birthday discount'],
            'silver': ['Point earning (1.2x)', 'Birthday discount', 'Free item after 10 orders'],
            'gold': ['Point earning (1.5x)', 'Birthday discount', 'Free item after 5 orders', 'Exclusive offers'],
            'platinum': ['Point earning (2x)', 'Birthday discount', 'Free item after 3 orders', 'Exclusive offers', 'Priority service']
        }
        return benefits.get(self.loyalty_tier, [])
    
    def to_dict(self, include_orders: bool = False, include_loyalty: bool = False) -> dict:
        """Convert customer to dictionary for API responses"""
        result = {
            'id': self.id,
            'customer_code': self.customer_code,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'full_name': self.get_full_name(),
            'email': self.email,
            'phone': self.phone,
            'company_name': self.company_name,
            'address': {
                'line1': self.address_line1,
                'line2': self.address_line2,
                'city': self.city,
                'state': self.state,
                'postal_code': self.postal_code,
                'country': self.country,
                'full_address': self.get_full_address()
            },
            'preferences': {
                'preferred_contact_method': self.preferred_contact_method,
                'dietary_restrictions': self.dietary_restrictions,
                'allergies': self.allergies,
                'special_notes': self.special_notes
            },
            'loyalty': {
                'member': self.loyalty_member,
                'points': self.loyalty_points,
                'tier': self.loyalty_tier,
                'member_since': self.loyalty_member_since.isoformat() if self.loyalty_member_since else None,
                'benefits': self.get_loyalty_benefits() if self.loyalty_member else []
            },
            'statistics': {
                'total_orders': self.total_orders,
                'total_spent': float(self.total_spent),
                'average_order_value': float(self.average_order_value),
                'last_order_date': self.last_order_date.isoformat() if self.last_order_date else None,
                'favorite_items': self.favorite_items
            },
            'marketing': {
                'consent': self.marketing_consent,
                'email_verified': self.email_verified,
                'phone_verified': self.phone_verified
            },
            'restaurant_id': self.restaurant_id,
            'created_by': self.created_by,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
        
        if include_orders:
            result['recent_orders'] = [order.to_dict() for order in self.orders.limit(10).all()]
        
        if include_loyalty:
            result['loyalty_transactions'] = [tx.to_dict() for tx in self.loyalty_transactions.limit(20).all()]
        
        return result
    
    def get_credit_account(self):
        """Get or create credit account for this customer"""
        if not self.credit_account:
            from app.models.credit import CreditAccount
            self.credit_account = CreditAccount(
                customer_id=self.id,
                credit_limit=self.credit_limit,
                current_balance=self.current_balance,
                is_active=self.credit_account_active,
                credit_terms=self.credit_terms,
                last_activity=self.last_credit_activity
            )
            self.credit_account.update_available_credit()
            db.session.add(self.credit_account)
            db.session.commit()
        return self.credit_account
    
    def can_use_credit(self, amount: float) -> bool:
        """Check if customer can use credit for this amount"""
        credit_account = self.get_credit_account()
        if not credit_account:
            return False
        
        can_charge, message = credit_account.can_charge(amount)
        return can_charge
    
    def charge_to_credit(self, amount: float, order_id=None, notes=None, created_by=None) -> bool:
        """Charge amount to customer's credit account"""
        credit_account = self.get_credit_account()
        if not credit_account:
            return False
        
        try:
            transaction = credit_account.charge(amount, order_id=order_id, notes=notes, created_by=created_by)
            # Update customer fields for backward compatibility
            self.current_balance = credit_account.current_balance
            self.available_credit = credit_account.available_credit
            self.last_credit_activity = credit_account.last_activity
            db.session.commit()
            return True
        except ValueError as e:
            return False
    
    def make_credit_payment(self, amount: float, payment_method=None, notes=None, created_by=None) -> bool:
        """Make payment towards customer's credit account"""
        credit_account = self.get_credit_account()
        if not credit_account:
            return False
        
        try:
            transaction = credit_account.make_payment(amount, payment_method=payment_method, notes=notes, created_by=created_by)
            # Update customer fields for backward compatibility
            self.current_balance = credit_account.current_balance
            self.available_credit = credit_account.available_credit
            self.last_credit_activity = credit_account.last_activity
            db.session.commit()
            return True
        except ValueError as e:
            return False
    
    def activate_credit_account(self, credit_limit: float, credit_terms: int = 30, approval_limit: float = 0.0) -> bool:
        """Activate credit account for this customer"""
        credit_account = self.get_credit_account()
        if credit_account:
            credit_account.credit_limit = credit_limit
            credit_account.credit_terms = credit_terms
            credit_account.approval_limit = approval_limit
            credit_account.is_active = True
            credit_account.update_available_credit()
            
            # Update customer fields for backward compatibility
            self.credit_limit = credit_limit
            self.credit_terms = credit_terms
            self.credit_account_active = True
            self.available_credit = credit_account.available_credit
            
            db.session.commit()
            return True
        return False
    
    def deactivate_credit_account(self) -> bool:
        """Deactivate credit account for this customer"""
        credit_account = self.get_credit_account()
        if credit_account:
            credit_account.is_active = False
            # Update customer fields for backward compatibility
            self.credit_account_active = False
            db.session.commit()
            return True
        return False
    
    def get_credit_summary(self) -> dict:
        """Get credit account summary"""
        credit_account = self.get_credit_account()
        if credit_account:
            return {
                'has_credit_account': True,
                'is_active': credit_account.is_active,
                'credit_limit': float(credit_account.credit_limit),
                'current_balance': float(credit_account.current_balance),
                'available_credit': float(credit_account.available_credit),
                'overdue_amount': credit_account.get_overdue_amount(),
                'credit_terms': credit_account.credit_terms,
                'last_activity': credit_account.last_activity.isoformat() if credit_account.last_activity else None
            }
        return {
            'has_credit_account': False,
            'is_active': False,
            'credit_limit': 0.0,
            'current_balance': 0.0,
            'available_credit': 0.0,
            'overdue_amount': 0.0,
            'credit_terms': 0,
            'last_activity': None
        }
    
    def __repr__(self):
        return f'<Customer {self.get_full_name()} ({self.customer_code})>'


class LoyaltyTransaction(db.Model):
    """Loyalty points transaction history"""
    __tablename__ = 'loyalty_transactions'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    points: Mapped[int] = mapped_column(db.Integer, nullable=False)
    transaction_type: Mapped[str] = mapped_column(db.Enum('earned', 'redeemed', 'expired', 'adjusted'), nullable=False)
    description: Mapped[str] = mapped_column(db.String(200), nullable=True)
    order_id: Mapped[int] = mapped_column(db.Integer, db.ForeignKey('orders.id'), nullable=True)
    balance_before: Mapped[int] = mapped_column(db.Integer, nullable=False)
    balance_after: Mapped[int] = mapped_column(db.Integer, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(db.DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    customer = relationship('Customer', back_populates='loyalty_transactions')
    order = relationship('Order', back_populates='loyalty_transactions')
    
    def to_dict(self) -> dict:
        """Convert transaction to dictionary for API responses"""
        return {
            'id': self.id,
            'customer_id': self.customer_id,
            'points': self.points,
            'transaction_type': self.transaction_type,
            'description': self.description,
            'order_id': self.order_id,
            'balance_before': self.balance_before,
            'balance_after': self.balance_after,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def __repr__(self):
        return f'<LoyaltyTransaction {self.points} pts for Customer {self.customer_id}>'