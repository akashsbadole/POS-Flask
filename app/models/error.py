from datetime import datetime
from app import db
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Enum
from sqlalchemy.orm import relationship
import enum

class ErrorSeverity(enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ErrorStatus(enum.Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"

class ErrorCategory(enum.Enum):
    SYSTEM = "system"
    USER = "user"
    PAYMENT = "payment"
    ORDER = "order"
    INVENTORY = "inventory"
    LICENSE = "license"
    NETWORK = "network"
    DATABASE = "database"

class ErrorLog(db.Model):
    """Error logging and management system"""
    __tablename__ = 'error_logs'
    
    id = Column(Integer, primary_key=True)
    error_code = Column(String(50), unique=True, nullable=False, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    category = Column(Enum(ErrorCategory), nullable=False)
    severity = Column(Enum(ErrorSeverity), nullable=False, default=ErrorSeverity.MEDIUM)
    status = Column(Enum(ErrorStatus), nullable=False, default=ErrorStatus.OPEN)
    
    # User and context information
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    restaurant_id = Column(Integer, ForeignKey('restaurants.id'), nullable=True)
    session_id = Column(String(255))  # Browser session ID
    ip_address = Column(String(45))
    user_agent = Column(Text)
    request_url = Column(String(500))
    request_method = Column(String(10))
    request_data = Column(Text)
    
    # System information
    stack_trace = Column(Text)
    browser_info = Column(String(500))
    operating_system = Column(String(100))
    
    # Resolution information
    assigned_to = Column(Integer, ForeignKey('users.id'), nullable=True)
    resolution = Column(Text)
    resolution_notes = Column(Text)
    resolved_at = Column(DateTime)
    resolved_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    
    # Timestamps
    occurred_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship('User', foreign_keys=[user_id], backref='user_errors')
    restaurant = relationship('Restaurant', foreign_keys=[restaurant_id], backref='restaurant_errors')
    assigned_user = relationship('User', foreign_keys=[assigned_to], backref='assigned_errors')
    resolved_user = relationship('User', foreign_keys=[resolved_by], backref='resolved_errors')
    
    def to_dict(self, include_user=False, include_resolution=False):
        """Convert error to dictionary for API responses"""
        result = {
            'id': self.id,
            'error_code': self.error_code,
            'title': self.title,
            'description': self.description,
            'category': self.category.value if self.category is not None else None,
            'severity': self.severity.value if self.severity is not None else None,
            'status': self.status.value if self.status is not None else None,
            'occurred_at': self.occurred_at.isoformat() if self.occurred_at is not None else None,
            'created_at': self.created_at.isoformat() if self.created_at is not None else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at is not None else None
        }
        
        if include_user and self.user:
            result['user'] = self.user.to_dict()
        
        if include_resolution:
            result['assigned_to'] = self.assigned_user.to_dict() if self.assigned_user else None
            result['resolution'] = self.resolution
            result['resolution_notes'] = self.resolution_notes
            result['resolved_at'] = self.resolved_at.isoformat() if self.resolved_at is not None else None
            result['resolved_by'] = self.resolved_user.to_dict() if self.resolved_user else None
        
        return result
    
    def __repr__(self):
        return f'<ErrorLog {self.error_code}: {self.title}>'

class ErrorPattern(db.Model):
    """Track recurring error patterns for proactive monitoring"""
    __tablename__ = 'error_patterns'
    
    id = Column(Integer, primary_key=True)
    pattern_name = Column(String(100), nullable=False, unique=True)
    pattern_regex = Column(String(500), nullable=False)
    description = Column(Text)
    category = Column(Enum(ErrorCategory), nullable=False)
    severity = Column(Enum(ErrorSeverity), nullable=False)
    occurrence_threshold = Column(Integer, default=5)  # Alert after this many occurrences
    time_window_hours = Column(Integer, default=24)  # Within this time window
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'pattern_name': self.pattern_name,
            'description': self.description,
            'category': self.category.value if self.category is not None else None,
            'severity': self.severity.value if self.severity is not None else None,
            'occurrence_threshold': self.occurrence_threshold,
            'time_window_hours': self.time_window_hours,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self):
        return f'<ErrorPattern {self.pattern_name}>'

class ErrorNotification(db.Model):
    """Track error notifications sent to users"""
    __tablename__ = 'error_notifications'
    
    id = Column(Integer, primary_key=True)
    error_id = Column(Integer, ForeignKey('error_logs.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    notification_type = Column(String(50))  # email, sms, push, in_app
    recipient = Column(String(255))  # Email address, phone number, etc.
    sent_at = Column(DateTime, default=datetime.utcnow)
    delivered_at = Column(DateTime)
    read_at = Column(DateTime)
    is_delivered = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    error = relationship('ErrorLog', backref='notifications')
    user = relationship('User', backref='error_notifications')
    
    def to_dict(self):
        return {
            'id': self.id,
            'error_id': self.error_id,
            'notification_type': self.notification_type,
            'recipient': self.recipient,
            'sent_at': self.sent_at.isoformat() if self.sent_at is not None else None,
            'delivered_at': self.delivered_at.isoformat() if self.delivered_at is not None else None,
            'read_at': self.read_at.isoformat() if self.read_at is not None else None,
            'is_delivered': self.is_delivered,
            'created_at': self.created_at.isoformat() if self.created_at is not None else None
        }
    
    def __repr__(self):
        return f'<ErrorNotification {self.id}>'