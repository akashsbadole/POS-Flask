from datetime import datetime
from typing import TYPE_CHECKING, Union, Optional
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean, ForeignKey, Enum
from sqlalchemy.orm import relationship
from app import db
import enum

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.subscription import Subscription

class PaymentGatewayType(enum.Enum):
    """Payment gateway providers"""
    STRIPE = "stripe"
    RAZORPAY = "razorpay"
    PAYPAL = "paypal"
    SQUARE = "square"
    PAYU = "payu"

class PaymentMethod(enum.Enum):
    """Payment method types"""
    CARD = "card"
    BANK_TRANSFER = "bank_transfer"
    UPI = "upi"
    NET_BANKING = "net_banking"
    WALLET = "wallet"

class TransactionStatus(enum.Enum):
    """Payment transaction statuses"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"
    CANCELLED = "cancelled"

class PaymentGateway(db.Model):
    """Payment gateway configurations"""
    __tablename__ = 'payment_gateways'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(50), nullable=False)
    gateway_type = Column(String(20), nullable=False)
    is_active = Column(Boolean, default=True)
    config = Column(Text)  # JSON configuration
    supported_methods = Column(Text)  # JSON array of supported payment methods
    webhook_secret = Column(String(255))  # For webhook verification
    test_mode = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def get_config_dict(self):
        """Get configuration as dictionary"""
        if self.config is not None:
            import json
            return json.loads(str(self.config))
        return {}
    
    def set_config(self, config_dict):
        """Set configuration from dictionary"""
        import json
        self.config = json.dumps(config_dict)
    
    def is_test_mode(self):
        """Check if gateway is in test mode"""
        return self.test_mode
    
    def __repr__(self):
        return f'<PaymentGateway {self.name}>'

class PaymentTransaction(db.Model):
    """Payment transaction records"""
    __tablename__ = 'payment_transactions'
    
    id = Column(Integer, primary_key=True)
    subscription_id = Column(Integer, ForeignKey('subscriptions.id'), nullable=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    gateway_id = Column(Integer, ForeignKey('payment_gateways.id'), nullable=False)
    transaction_id = Column(String(100))  # Gateway-specific transaction ID
    amount = Column(Float, nullable=False)
    currency = Column(String(3), default='INR')
    payment_method = Column(String(20))
    status = Column(String(20), default='pending')
    gateway_response = Column(Text)  # Full response from gateway
    error_code = Column(String(50))
    error_message = Column(Text)
    processed_at = Column(DateTime)
    refunded_amount = Column(Float, default=0)
    refund_date = Column(DateTime)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    subscription = relationship('Subscription', back_populates='payment_transactions')
    user = relationship('User')
    gateway = relationship('PaymentGateway', back_populates='transactions')
    
    def mark_completed(self, gateway_response=None):
        """Mark transaction as completed"""
        self.status = 'completed'
        self.processed_at = datetime.utcnow()
        if gateway_response:
            self.gateway_response = str(gateway_response)
        db.session.commit()
    
    def mark_failed(self, error_code=None, error_message=None, gateway_response=None):
        """Mark transaction as failed"""
        self.status = 'failed'
        self.error_code = error_code
        self.error_message = error_message
        if gateway_response:
            self.gateway_response = str(gateway_response)
        db.session.commit()
    
    def refund(self, amount=None, reason=None):
        """Process refund for transaction"""
        if amount and amount > 0:
            self.status = 'refunded'
            self.refunded_amount = amount
            self.refund_date = datetime.utcnow()
            self.notes = f"Refunded: {reason}" if reason else "Refunded"
            db.session.commit()
            return True
        return False
    
    def get_amount(self):
        """Get amount as float"""
        amount_value = getattr(self, 'amount', None)
        return float(amount_value) if amount_value is not None else 0.0
    
    def get_refunded_amount(self):
        """Get refunded amount as float"""
        refunded_value = getattr(self, 'refunded_amount', None)
        return float(refunded_value) if refunded_value is not None else 0.0
    
    def __repr__(self):
        return f'<PaymentTransaction {self.transaction_id} {self.amount} {self.currency}>'

class PaymentMethodConfig(db.Model):
    """Payment method configurations for gateways"""
    __tablename__ = 'payment_method_configs'
    
    id = Column(Integer, primary_key=True)
    gateway_id = Column(Integer, ForeignKey('payment_gateways.id'), nullable=False)
    method_type = Column(String(20))
    is_enabled = Column(Boolean, default=True)
    config = Column(Text)  # Method-specific configuration
    min_amount = Column(Float, default=0)
    max_amount = Column(Float, default=100000)
    fee_percentage = Column(Float, default=0)
    fee_fixed = Column(Float, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    gateway = relationship('PaymentGateway', back_populates='method_configs')
    
    def calculate_fee(self, amount):
        """Calculate processing fee for given amount"""
        fee = 0
        fee_percentage = getattr(self, 'fee_percentage', None)
        fee_fixed = getattr(self, 'fee_fixed', None)
        
        if fee_percentage and float(fee_percentage) > 0:
            fee += amount * (float(fee_percentage) / 100)
        if fee_fixed and float(fee_fixed) > 0:
            fee += float(fee_fixed)
        return fee
    
    def get_min_amount(self):
        """Get minimum amount as float"""
        min_value = getattr(self, 'min_amount', None)
        return float(min_value) if min_value is not None else 0.0
    
    def get_max_amount(self):
        """Get maximum amount as float"""
        max_value = getattr(self, 'max_amount', None)
        return float(max_value) if max_value is not None else 0.0
    
    def get_fee_percentage(self):
        """Get fee percentage as float"""
        fee_value = getattr(self, 'fee_percentage', None)
        return float(fee_value) if fee_value is not None else 0.0
    
    def get_fee_fixed(self):
        """Get fixed fee as float"""
        fixed_value = getattr(self, 'fee_fixed', None)
        return float(fixed_value) if fixed_value is not None else 0.0
    
    def __repr__(self):
        return f'<PaymentMethodConfig {self.method_type}>'

class WebhookEvent(db.Model):
    """Webhook event logs for payment gateways"""
    __tablename__ = 'webhook_events'
    
    id = Column(Integer, primary_key=True)
    gateway_id = Column(Integer, ForeignKey('payment_gateways.id'), nullable=False)
    event_type = Column(String(50))  # payment.created, payment.succeeded, etc.
    event_data = Column(Text)  # JSON payload from gateway
    processed = Column(Boolean, default=False)
    processing_attempts = Column(Integer, default=0)
    error_message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    gateway = relationship('PaymentGateway', back_populates='webhook_events')
    
    def mark_processed(self):
        """Mark webhook event as processed"""
        self.processed = True
        db.session.commit()
    
    def __repr__(self):
        return f'<WebhookEvent {self.event_type}>'

# Add relationships to PaymentGateway
PaymentGateway.transactions = relationship('PaymentTransaction', back_populates='gateway')
PaymentGateway.method_configs = relationship('PaymentMethodConfig', back_populates='gateway')
PaymentGateway.webhook_events = relationship('WebhookEvent', back_populates='gateway')