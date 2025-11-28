"""
Notification model for Restaurant POS System
Handles system notifications including license renewal reminders
"""
from datetime import datetime
from app import db
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship


class Notification(db.Model):
    """System notifications for users and restaurants"""
    __tablename__ = 'notifications'
    
    id = Column(Integer, primary_key=True)
    type = Column(String(50), nullable=False, index=True)  # license_renewal, system_alert, etc.
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    reference_id = Column(String(50))  # ID of related object (license_id, etc.)
    reference_type = Column(String(50))  # Type of reference (license, order, etc.)
    urgency = Column(String(20), default='info')  # urgent, warning, info
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    restaurant_id = Column(Integer, ForeignKey('restaurants.id'), nullable=True)
    is_read = Column(Boolean, default=False)
    is_email_sent = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    read_at = Column(DateTime)
    
    # Relationships
    user = relationship('User')
    restaurant = relationship('Restaurant')
    
    def __repr__(self):
        return f'<Notification {self.title}>'
    
    def mark_as_read(self):
        """Mark notification as read"""
        self.is_read = True
        self.read_at = datetime.utcnow()
        db.session.commit()
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'type': self.type,
            'title': self.title,
            'message': self.message,
            'reference_id': self.reference_id,
            'reference_type': self.reference_type,
            'urgency': self.urgency,
            'user_id': self.user_id,
            'restaurant_id': self.restaurant_id,
            'is_read': self.is_read,
            'is_email_sent': self.is_email_sent,
            'created_at': self.created_at.isoformat() if getattr(self, 'created_at', None) else None,
            'read_at': self.read_at.isoformat() if getattr(self, 'read_at', None) else None
        }


class NotificationLog(db.Model):
    """Log of sent notifications"""
    __tablename__ = 'notification_logs'
    
    id = Column(Integer, primary_key=True)
    notification_id = Column(Integer, ForeignKey('notifications.id'), nullable=False)
    channel = Column(String(20), nullable=False)  # email, sms, push
    recipient = Column(String(255), nullable=False)
    status = Column(String(20), nullable=False)  # sent, failed, pending
    error_message = Column(Text)
    sent_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    notification = relationship('Notification')
    
    def __repr__(self):
        return f'<NotificationLog {self.notification.title} - {self.channel}>'
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'notification_id': self.notification_id,
            'channel': self.channel,
            'recipient': self.recipient,
            'status': self.status,
            'error_message': self.error_message,
            'sent_at': self.sent_at.isoformat() if getattr(self, 'sent_at', None) else None
        }


class NotificationPreference(db.Model):
    """User notification preferences"""
    __tablename__ = 'notification_preferences'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    notification_type = Column(String(50), nullable=False)
    email_enabled = Column(Boolean, default=True)
    sms_enabled = Column(Boolean, default=False)
    push_enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship('User')
    
    def __repr__(self):
        return f'<NotificationPreference {self.user.username} - {self.notification_type}>'
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'notification_type': self.notification_type,
            'email_enabled': self.email_enabled,
            'sms_enabled': self.sms_enabled,
            'push_enabled': self.push_enabled,
            'created_at': self.created_at.isoformat() if getattr(self, 'created_at', None) else None,
            'updated_at': self.updated_at.isoformat() if getattr(self, 'updated_at', None) else None
        }


class EmailTemplate(db.Model):
    """Email templates for notifications"""
    __tablename__ = 'email_templates'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    subject = Column(String(200), nullable=False)
    html_content = Column(Text, nullable=False)
    text_content = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<EmailTemplate {self.name}>'
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'name': self.name,
            'subject': self.subject,
            'html_content': self.html_content,
            'text_content': self.text_content,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if getattr(self, 'created_at', None) else None,
            'updated_at': self.updated_at.isoformat() if getattr(self, 'updated_at', None) else None
        }


class SmsTemplate(db.Model):
    """SMS templates for notifications"""
    __tablename__ = 'sms_templates'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    content = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<SmsTemplate {self.name}>'
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'name': self.name,
            'content': self.content,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if getattr(self, 'created_at', None) else None,
            'updated_at': self.updated_at.isoformat() if getattr(self, 'updated_at', None) else None
        }