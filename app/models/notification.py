"""
Notification models for tracking email and SMS notifications
"""

from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app import db

class Notification(db.Model):
    """Main notification model for tracking sent notifications"""
    __tablename__ = 'notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.Enum('email', 'sms'), nullable=False)
    recipient = db.Column(db.String(255), nullable=False)
    subject = db.Column(db.String(255))
    content = db.Column(db.Text, nullable=False)
    context = db.Column(db.JSON)  # Store template context as JSON
    priority = db.Column(db.Enum('low', 'normal', 'high'), default='normal')
    status = db.Column(db.Enum('pending', 'sent', 'failed', 'retrying'), default='pending')
    error_message = db.Column(db.Text)
    retry_count = db.Column(db.Integer, default=0)
    max_retries = db.Column(db.Integer, default=3)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    sent_at = db.Column(db.DateTime)
    failed_at = db.Column(db.DateTime)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    logs = relationship('NotificationLog', backref='notification', cascade='all, delete-orphan')
    
    def to_dict(self):
        """Convert notification to dictionary for API responses"""
        return {
            'id': self.id,
            'type': self.type,
            'recipient': self.recipient,
            'subject': self.subject,
            'content': self.content,
            'context': self.context,
            'priority': self.priority,
            'status': self.status,
            'error_message': self.error_message,
            'retry_count': self.retry_count,
            'max_retries': self.max_retries,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'sent_at': self.sent_at.isoformat() if self.sent_at else None,
            'failed_at': self.failed_at.isoformat() if self.failed_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self):
        return f'<Notification {self.type} to {self.recipient} ({self.status})>'

class NotificationLog(db.Model):
    """Log of notification delivery attempts"""
    __tablename__ = 'notification_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    notification_id = db.Column(db.Integer, db.ForeignKey('notifications.id'), nullable=False)
    channel = db.Column(db.Enum('email', 'sms'), nullable=False)
    status = db.Column(db.Enum('pending', 'sent', 'failed'), nullable=False)
    error_message = db.Column(db.Text)
    attempt_at = db.Column(db.DateTime, default=datetime.utcnow)
    response_data = db.Column(db.JSON)  # Store response data from providers
    
    def to_dict(self):
        """Convert notification log to dictionary for API responses"""
        return {
            'id': self.id,
            'notification_id': self.notification_id,
            'channel': self.channel,
            'status': self.status,
            'error_message': self.error_message,
            'attempt_at': self.attempt_at.isoformat() if self.attempt_at else None,
            'response_data': self.response_data
        }
    
    def __repr__(self):
        return f'<NotificationLog {self.channel} {self.status}>'

class NotificationPreference(db.Model):
    """User preferences for different types of notifications"""
    __tablename__ = 'notification_preferences'
    
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=True)  # Per-order preferences
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # User preferences
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurants.id'), nullable=True)  # Restaurant defaults
    
    notification_type = db.Column(db.Enum('order_confirmation', 'order_receipt', 'order_status_update', 
                                        'low_stock_alert', 'license_renewal', 'marketing'), nullable=False)
    channel = db.Column(db.Enum('email', 'sms'), nullable=False)
    is_enabled = db.Column(db.Boolean, default=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    order = relationship('Order', backref='notification_preferences')
    user = relationship('User', backref='notification_preferences')
    restaurant = relationship('Restaurant', backref='notification_preferences')
    
    def to_dict(self):
        """Convert notification preference to dictionary for API responses"""
        return {
            'id': self.id,
            'order_id': self.order_id,
            'user_id': self.user_id,
            'restaurant_id': self.restaurant_id,
            'notification_type': self.notification_type,
            'channel': self.channel,
            'is_enabled': self.is_enabled,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self):
        return f'<NotificationPreference {self.notification_type} {self.channel} ({self.is_enabled})>'

class EmailTemplate(db.Model):
    """Email templates for different notification types"""
    __tablename__ = 'email_templates'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    subject = db.Column(db.String(255), nullable=False)
    html_content = db.Column(db.Text, nullable=False)
    text_content = db.Column(db.Text)
    variables = db.Column(db.JSON)  # Available template variables
    is_active = db.Column(db.Boolean, default=True)
    is_default = db.Column(db.Boolean, default=False)
    
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurants.id'), nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    restaurant = relationship('Restaurant', backref='email_templates')
    
    def to_dict(self):
        """Convert email template to dictionary for API responses"""
        return {
            'id': self.id,
            'name': self.name,
            'subject': self.subject,
            'html_content': self.html_content,
            'text_content': self.text_content,
            'variables': self.variables,
            'is_active': self.is_active,
            'is_default': self.is_default,
            'restaurant_id': self.restaurant_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self):
        return f'<EmailTemplate {self.name}>'

class SmsTemplate(db.Model):
    """SMS templates for different notification types"""
    __tablename__ = 'sms_templates'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    content = db.Column(db.Text, nullable=False)
    variables = db.Column(db.JSON)  # Available template variables
    is_active = db.Column(db.Boolean, default=True)
    is_default = db.Column(db.Boolean, default=False)
    
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurants.id'), nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    restaurant = relationship('Restaurant', backref='sms_templates')
    
    def to_dict(self):
        """Convert SMS template to dictionary for API responses"""
        return {
            'id': self.id,
            'name': self.name,
            'content': self.content,
            'variables': self.variables,
            'is_active': self.is_active,
            'is_default': self.is_default,
            'restaurant_id': self.restaurant_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self):
        return f'<SmsTemplate {self.name}>'