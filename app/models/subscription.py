from datetime import datetime, timedelta
from app import db
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean, ForeignKey, Enum
from sqlalchemy.orm import relationship
import enum

class SubscriptionPlanType(enum.Enum):
    BASIC = "basic"
    STANDARD = "standard"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"

class SubscriptionStatus(enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    TRIAL = "trial"

class SubscriptionPlan(db.Model):
    """Subscription plans for restaurants"""
    __tablename__ = 'subscription_plans'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    plan_type = Column(Enum(SubscriptionPlanType), nullable=False)
    description = Column(Text)
    price_monthly = Column(Float, nullable=False)
    price_yearly = Column(Float, nullable=False)
    currency = Column(String(3), default='INR')
    features = Column(Text)  # JSON string of features
    max_users = Column(Integer, default=1)
    max_restaurants = Column(Integer, default=1)
    max_orders_per_month = Column(Integer, default=1000)
    api_access = Column(Boolean, default=False)
    advanced_reporting = Column(Boolean, default=False)
    priority_support = Column(Boolean, default=False)
    custom_branding = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    subscriptions = relationship('Subscription', back_populates='plan')
    
    def __repr__(self):
        return f'<SubscriptionPlan {self.name}>'
    
    def get_features_list(self):
        """Parse features JSON string to list"""
        if self.features is not None:
            import json
            return json.loads(str(self.features))
        return []
    
    def set_features_list(self, features_list):
        """Set features from list to JSON string"""
        import json
        self.features = json.dumps(features_list)

class Subscription(db.Model):
    """Restaurant subscriptions"""
    __tablename__ = 'subscriptions'
    
    id = Column(Integer, primary_key=True)
    restaurant_id = Column(Integer, ForeignKey('restaurants.id'), nullable=False)
    plan_id = Column(Integer, ForeignKey('subscription_plans.id'), nullable=False)
    status = Column(Enum(SubscriptionStatus), default=SubscriptionStatus.TRIAL)
    billing_cycle = Column(String(20), default='monthly')  # monthly, yearly
    start_date = Column(DateTime, default=datetime.utcnow)
    end_date = Column(DateTime)
    trial_end_date = Column(DateTime)
    auto_renew = Column(Boolean, default=True)
    cancelled_at = Column(DateTime)
    cancellation_reason = Column(Text)
    next_billing_date = Column(DateTime)
    last_billing_date = Column(DateTime)
    amount = Column(Float, nullable=False)
    currency = Column(String(3), default='INR')
    payment_method = Column(String(50))
    payment_method_details = Column(Text)  # JSON string
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    restaurant = relationship('Restaurant', back_populates='subscriptions')
    plan = relationship('SubscriptionPlan', back_populates='subscriptions')
    payments = relationship('SubscriptionPayment', back_populates='subscription')
    usage_logs = relationship('SubscriptionUsage', back_populates='subscription')
    
    def __repr__(self):
        return f'<Subscription {self.restaurant.name} - {self.plan.name}>'
    
    def is_active(self):
        """Check if subscription is currently active"""
        if self.status != SubscriptionStatus.ACTIVE:
            return False
        if self.end_date is not None and datetime.utcnow() > self.end_date:
            return False
        return True
    
    def is_trial(self):
        """Check if subscription is in trial period"""
        return self.status == SubscriptionStatus.TRIAL and (
            self.trial_end_date is None or (self.trial_end_date is not None and datetime.utcnow() <= self.trial_end_date)
        )
    
    def days_remaining(self):
        """Get days remaining in current billing period"""
        if self.end_date is None:
            return None
        delta = self.end_date - datetime.utcnow()
        return max(0, delta.days)
    
    def get_usage_stats(self):
        """Get current usage statistics"""
        current_month = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Get usage logs for current month
        usage_logs = SubscriptionUsage.query.filter(
            SubscriptionUsage.subscription_id == self.id,
            SubscriptionUsage.log_date >= current_month
        ).all()
        
        total_orders = sum(log.orders_count for log in usage_logs)
        total_api_calls = sum(log.api_calls for log in usage_logs)
        active_users = len(set(log.user_id for log in usage_logs if log.user_id))
        
        return {
            'orders_count': total_orders,
            'api_calls': total_api_calls,
            'active_users': active_users,
            'limits': {
                'max_orders_per_month': self.plan.max_orders_per_month,
                'max_users': self.plan.max_users
            }
        }
    
    def extend_subscription(self, days=30):
        """Extend subscription by specified days"""
        if self.end_date is not None:
            self.end_date = self.end_date + timedelta(days=days)
        else:
            self.end_date = datetime.utcnow() + timedelta(days=days)
        
        self.next_billing_date = self.end_date
        self.status = SubscriptionStatus.ACTIVE
    
    def cancel_subscription(self, reason=None):
        """Cancel subscription"""
        self.status = SubscriptionStatus.CANCELLED
        self.cancelled_at = datetime.utcnow()
        self.cancellation_reason = reason
        self.auto_renew = False

class SubscriptionPayment(db.Model):
    """Payment records for subscriptions"""
    __tablename__ = 'subscription_payments'
    
    id = Column(Integer, primary_key=True)
    subscription_id = Column(Integer, ForeignKey('subscriptions.id'), nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String(3), default='INR')
    payment_method = Column(String(50))
    transaction_id = Column(String(100))
    status = Column(String(20), default='pending')  # pending, completed, failed, refunded
    payment_date = Column(DateTime, default=datetime.utcnow)
    billing_period_start = Column(DateTime)
    billing_period_end = Column(DateTime)
    invoice_url = Column(String(500))
    refund_amount = Column(Float)
    refund_date = Column(DateTime)
    refund_reason = Column(Text)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    subscription = relationship('Subscription', back_populates='payments')
    
    def __repr__(self):
        return f'<SubscriptionPayment {self.amount} {self.currency}>'

class SubscriptionUsage(db.Model):
    """Usage tracking for subscriptions"""
    __tablename__ = 'subscription_usage'
    
    id = Column(Integer, primary_key=True)
    subscription_id = Column(Integer, ForeignKey('subscriptions.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'))
    log_date = Column(DateTime, default=datetime.utcnow)
    orders_count = Column(Integer, default=0)
    api_calls = Column(Integer, default=0)
    storage_used = Column(Float, default=0)  # in MB
    bandwidth_used = Column(Float, default=0)  # in MB
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    subscription = relationship('Subscription', back_populates='usage_logs')
    user = relationship('User')
    
    def __repr__(self):
        return f'<SubscriptionUsage {self.orders_count} orders>'

class SubscriptionFeature(db.Model):
    """Additional features that can be added to subscriptions"""
    __tablename__ = 'subscription_features'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    feature_type = Column(String(50))  # addon, module, integration
    price_monthly = Column(Float, default=0)
    price_yearly = Column(Float, default=0)
    currency = Column(String(3), default='INR')
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<SubscriptionFeature {self.name}>'

class SubscriptionAddon(db.Model):
    """Add-ons purchased for subscriptions"""
    __tablename__ = 'subscription_addons'
    
    id = Column(Integer, primary_key=True)
    subscription_id = Column(Integer, ForeignKey('subscriptions.id'), nullable=False)
    feature_id = Column(Integer, ForeignKey('subscription_features.id'), nullable=False)
    status = Column(String(20), default='active')  # active, inactive, cancelled
    start_date = Column(DateTime, default=datetime.utcnow)
    end_date = Column(DateTime)
    auto_renew = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    subscription = relationship('Subscription')
    feature = relationship('SubscriptionFeature')
    
    def __repr__(self):
        return f'<SubscriptionAddon {self.feature.name}>'