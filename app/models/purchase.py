from datetime import datetime
from decimal import Decimal
from app import db
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Enum, Numeric, JSON
from sqlalchemy.orm import relationship
import enum
import uuid

def safe_decimal_to_float(value):
    """Safely convert Decimal or Column to float"""
    if value is None:
        return 0.0
    if isinstance(value, Decimal):
        return float(value)
    return float(value) if value else 0.0

class PurchaseStatus(enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"

class PaymentMethod(enum.Enum):
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    BANK_TRANSFER = "bank_transfer"
    PAYPAL = "paypal"
    STRIPE = "stripe"
    CRYPTO = "crypto"

class Purchase(db.Model):
    """Purchase and payment processing for restaurant owners"""
    __tablename__ = 'purchases'
    
    id = Column(Integer, primary_key=True)
    purchase_number = Column(String(50), unique=True, nullable=False, index=True)
    customer_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    restaurant_id = Column(Integer, ForeignKey('restaurants.id'), nullable=True)
    
    # Purchase details
    subscription_plan_id = Column(Integer, ForeignKey('subscription_plans.id'), nullable=True)
    license_template_id = Column(Integer, ForeignKey('license_templates.id'), nullable=True)
    items = Column(JSON)  # List of purchased items with details
    
    # Financial details
    subtotal = Column(Numeric(10, 2), nullable=False)
    tax_amount = Column(Numeric(10, 2), nullable=False)
    discount_amount = Column(Numeric(10, 2), default=0)
    total_amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), default='USD')
    
    # Payment information
    payment_method = Column(Enum(PaymentMethod), nullable=False)
    payment_status = Column(String(50), default='pending')
    transaction_id = Column(String(100))  # External transaction ID
    payment_gateway_response = Column(JSON)
    
    # Status and timestamps
    status = Column(Enum(PurchaseStatus), nullable=False, default=PurchaseStatus.PENDING)
    purchased_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime)
    cancelled_at = Column(DateTime)
    refunded_at = Column(DateTime)
    
    # Customer information snapshot
    customer_name = Column(String(100))
    customer_email = Column(String(255))
    customer_phone = Column(String(20))
    billing_address = Column(JSON)
    shipping_address = Column(JSON)
    
    # Trial information
    is_trial = Column(Boolean, default=False)
    trial_days = Column(Integer, default=0)
    trial_ends_at = Column(DateTime)
    
    # Relationships
    customer = relationship('User', foreign_keys=[customer_id], backref='purchases')
    restaurant = relationship('Restaurant', foreign_keys=[restaurant_id], backref='purchases')
    subscription_plan = relationship('SubscriptionPlan', foreign_keys=[subscription_plan_id])
    license_template = relationship('LicenseTemplate', foreign_keys=[license_template_id])
    invoices = relationship('PurchaseInvoice', backref='purchase', cascade='all, delete-orphan')
    payments = relationship('PurchasePayment', backref='purchase', cascade='all, delete-orphan')
    
    def __init__(self, **kwargs):
        super(Purchase, self).__init__(**kwargs)
        # Check if purchase_number is not set or is None/empty
        if not kwargs.get('purchase_number'):
            self.purchase_number = self.generate_purchase_number()
    
    def generate_purchase_number(self):
        """Generate unique purchase number"""
        prefix = "PUR"
        timestamp = datetime.utcnow().strftime('%Y%m%d')
        random_suffix = str(uuid.uuid4())[:8].upper()
        return f"{prefix}{timestamp}{random_suffix}"
    
    def calculate_total(self):
        """Calculate total amount including tax and discounts"""
        self.subtotal = sum(item.get('price', 0) * item.get('quantity', 1) for item in (self.items or []))
        self.tax_amount = self.subtotal * 0.1  # 10% tax rate
        self.total_amount = self.subtotal + self.tax_amount - self.discount_amount
    
    def to_dict(self, include_customer=False, include_items=True):
        """Convert purchase to dictionary for API responses"""
        result = {
            'id': self.id,
            'purchase_number': self.purchase_number,
            'customer_id': self.customer_id,
            'restaurant_id': self.restaurant_id,
            'subscription_plan_id': self.subscription_plan_id,
            'license_template_id': self.license_template_id,
            'subtotal': safe_decimal_to_float(self.subtotal),
            'tax_amount': safe_decimal_to_float(self.tax_amount),
            'discount_amount': safe_decimal_to_float(self.discount_amount),
            'total_amount': safe_decimal_to_float(self.total_amount),
            'currency': self.currency,
            'payment_method': self.payment_method.value if self.payment_method is not None else None,
            'payment_status': self.payment_status,
            'transaction_id': self.transaction_id,
            'status': self.status.value if self.status is not None else None,
            'customer_name': self.customer_name,
            'customer_email': self.customer_email,
            'customer_phone': self.customer_phone,
            'is_trial': self.is_trial,
            'trial_days': self.trial_days,
            'purchased_at': self.purchased_at.isoformat() if self.purchased_at is not None else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at is not None else None,
            'trial_ends_at': self.trial_ends_at.isoformat() if self.trial_ends_at is not None else None
        }
        
        if include_items:
            result['items'] = self.items or []
        
        if include_customer and self.customer:
            result['customer'] = self.customer.to_dict()
        
        return result
    
    def __repr__(self):
        return f'<Purchase {self.purchase_number}: {self.total_amount} {self.currency}>'

class PurchasePayment(db.Model):
    """Individual payment attempts and transactions"""
    __tablename__ = 'purchase_payments'
    
    id = Column(Integer, primary_key=True)
    purchase_id = Column(Integer, ForeignKey('purchases.id'), nullable=False)
    payment_method = Column(Enum(PaymentMethod), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), default='USD')
    status = Column(String(50), nullable=False)  # pending, completed, failed, refunded
    transaction_id = Column(String(100))
    gateway_response = Column(JSON)
    error_message = Column(Text)
    processed_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    def to_dict(self):
        return {
            'id': self.id,
            'purchase_id': self.purchase_id,
            'payment_method': self.payment_method.value if self.payment_method is not None else None,
            'amount': safe_decimal_to_float(self.amount),
            'currency': self.currency,
            'status': self.status,
            'transaction_id': self.transaction_id,
            'error_message': self.error_message,
            'processed_at': self.processed_at.isoformat() if self.processed_at is not None else None
        }
    
    def __repr__(self):
        return f'<PurchasePayment {self.id}: {self.amount} {self.currency}>'

class PurchaseInvoice(db.Model):
    """Invoices for purchases"""
    __tablename__ = 'purchase_invoices'
    
    id = Column(Integer, primary_key=True)
    purchase_id = Column(Integer, ForeignKey('purchases.id'), nullable=False)
    invoice_number = Column(String(50), unique=True, nullable=False, index=True)
    invoice_type = Column(String(20), default='invoice')  # invoice, receipt, credit_note
    
    # Invoice details
    due_date = Column(DateTime)
    issue_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    paid_date = Column(DateTime)
    
    # Amounts
    subtotal = Column(Numeric(10, 2), nullable=False)
    tax_amount = Column(Numeric(10, 2), nullable=False)
    discount_amount = Column(Numeric(10, 2), default=0)
    total_amount = Column(Numeric(10, 2), nullable=False)
    paid_amount = Column(Numeric(10, 2), default=0)
    outstanding_amount = Column(Numeric(10, 2))
    
    # Status
    status = Column(String(20), default='draft')  # draft, sent, paid, overdue, cancelled
    currency = Column(String(3), default='USD')
    
    # Customer information
    customer_name = Column(String(100))
    customer_email = Column(String(255))
    billing_address = Column(JSON)
    
    # PDF and email
    pdf_path = Column(String(500))
    email_sent = Column(Boolean, default=False)
    email_sent_at = Column(DateTime)
    
    def __init__(self, **kwargs):
        super(PurchaseInvoice, self).__init__(**kwargs)
        # Check if invoice_number is not set or is None/empty
        if not kwargs.get('invoice_number'):
            self.invoice_number = self.generate_invoice_number()
        if self.outstanding_amount is None:
            self.outstanding_amount = self.total_amount
    
    def generate_invoice_number(self):
        """Generate unique invoice number"""
        prefix = "INV"
        timestamp = datetime.utcnow().strftime('%Y%m%d')
        count_today = PurchaseInvoice.query.filter(
            PurchaseInvoice.issue_date >= datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        ).count()
        return f"{prefix}{timestamp}{count_today + 1:04d}"
    
    def to_dict(self):
        return {
            'id': self.id,
            'purchase_id': self.purchase_id,
            'invoice_number': self.invoice_number,
            'invoice_type': self.invoice_type,
            'due_date': self.due_date.isoformat() if self.due_date is not None else None,
            'issue_date': self.issue_date.isoformat() if self.issue_date is not None else None,
            'paid_date': self.paid_date.isoformat() if self.paid_date is not None else None,
            'subtotal': safe_decimal_to_float(self.subtotal),
            'tax_amount': safe_decimal_to_float(self.tax_amount),
            'discount_amount': safe_decimal_to_float(self.discount_amount),
            'total_amount': safe_decimal_to_float(self.total_amount),
            'paid_amount': safe_decimal_to_float(self.paid_amount),
            'outstanding_amount': safe_decimal_to_float(self.outstanding_amount),
            'status': self.status,
            'currency': self.currency,
            'customer_name': self.customer_name,
            'customer_email': self.customer_email,
            'email_sent': self.email_sent,
            'email_sent_at': self.email_sent_at.isoformat() if self.email_sent_at is not None else None
        }
    
    def __repr__(self):
        return f'<PurchaseInvoice {self.invoice_number}: {self.total_amount} {self.currency}>'

class PurchaseEmail(db.Model):
    """Email communications related to purchases"""
    __tablename__ = 'purchase_emails'
    
    id = Column(Integer, primary_key=True)
    purchase_id = Column(Integer, ForeignKey('purchases.id'), nullable=False)
    email_type = Column(String(50), nullable=False)  # order_confirmation, invoice, payment_confirmation, trial_reminder, etc.
    recipient_email = Column(String(255), nullable=False)
    recipient_name = Column(String(100))
    subject = Column(String(200))
    content = Column(Text)
    
    # Email status
    status = Column(String(20), default='pending')  # pending, sent, failed, bounced
    sent_at = Column(DateTime)
    error_message = Column(Text)
    
    # Tracking
    opened_at = Column(DateTime)
    clicked_at = Column(DateTime)
    
    def to_dict(self):
        return {
            'id': self.id,
            'purchase_id': self.purchase_id,
            'email_type': self.email_type,
            'recipient_email': self.recipient_email,
            'recipient_name': self.recipient_name,
            'subject': self.subject,
            'status': self.status,
            'sent_at': self.sent_at.isoformat() if self.sent_at is not None else None,
            'opened_at': self.opened_at.isoformat() if self.opened_at is not None else None,
            'clicked_at': self.clicked_at.isoformat() if self.clicked_at is not None else None
        }
    
    def __repr__(self):
        return f'<PurchaseEmail {self.id}: {self.email_type}>'