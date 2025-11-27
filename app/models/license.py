from datetime import datetime, timedelta
from app import db
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean, ForeignKey, Enum
from sqlalchemy.orm import relationship
import enum

class LicenseType(enum.Enum):
    SOFTWARE = "software"
    HARDWARE = "hardware"
    USER = "user"
    DEVICE = "device"

class LicenseStatus(enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    EXPIRED = "expired"
    CANCELLED = "cancelled"

class License(db.Model):
    """License management for restaurants and users"""
    __tablename__ = 'licenses'
    
    id = Column(Integer, primary_key=True)
    license_key = Column(String(255), unique=True, nullable=False, index=True)
    license_type = Column(Enum(LicenseType), nullable=False)
    product_name = Column(String(100), nullable=False)
    product_version = Column(String(20))
    restaurant_id = Column(Integer, ForeignKey('restaurants.id'), nullable=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    device_id = Column(String(100))  # For hardware/device licenses
    status = Column(Enum(LicenseStatus), default=LicenseStatus.ACTIVE)
    issued_date = Column(DateTime, default=datetime.utcnow)
    expiry_date = Column(DateTime)
    last_verified = Column(DateTime)
    verification_count = Column(Integer, default=0)
    max_activations = Column(Integer, default=1)  # Max devices/users for this license
    current_activations = Column(Integer, default=0)  # Current active activations
    features = Column(Text)  # JSON string of licensed features
    restrictions = Column(Text)  # JSON string of usage restrictions
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    restaurant = relationship('Restaurant')
    user = relationship('User')
    activations = relationship('LicenseActivation', back_populates='license')
    
    def __repr__(self):
        return f'<License {self.license_key}>'
    
    def is_valid(self):
        """Check if license is currently valid"""
        if self.status.value != LicenseStatus.ACTIVE.value:
            return False
        if self.expiry_date is not None and datetime.utcnow() > self.expiry_date:
            return False
        return True
    
    def is_expired(self):
        """Check if license has expired"""
        return self.expiry_date is not None and datetime.utcnow() > self.expiry_date
    
    def days_until_expiry(self):
        """Get days until license expires"""
        if self.expiry_date is None:
            return None
        delta = self.expiry_date - datetime.utcnow()
        return max(0, delta.days)
    
    def can_activate(self):
        """Check if license can be activated on new device/user"""
        return self.current_activations < self.max_activations
    
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
    
    def get_restrictions_list(self):
        """Parse restrictions JSON string to list"""
        if self.restrictions is not None:
            import json
            return json.loads(str(self.restrictions))
        return []
    
    def verify_license(self):
        """Verify license and update verification details"""
        self.last_verified = datetime.utcnow()
        self.verification_count += 1
        db.session.commit()
    
    def activate(self, device_id=None, user_id=None):
        """Activate license on device/user"""
        if not self.can_activate():
            return False, "Maximum activations reached"
        
        activation = LicenseActivation(
            license_id=self.id,
            device_id=device_id,
            user_id=user_id,
            activated_at=datetime.utcnow()
        )
        
        self.current_activations += 1
        db.session.add(activation)
        db.session.commit()
        
        return True, "License activated successfully"
    
    def deactivate(self, device_id=None, user_id=None):
        """Deactivate license on device/user"""
        activation = LicenseActivation.query.filter_by(
            license_id=self.id,
            device_id=device_id,
            user_id=user_id,
            is_active=True
        ).first()
        
        if activation:
            activation.is_active = False
            activation.deactivated_at = datetime.utcnow()
            self.current_activations = max(0, self.current_activations - 1)
            db.session.commit()
            
            return True, "License deactivated successfully"
        
        return False, "Activation not found"

class LicenseActivation(db.Model):
    """Track license activations on devices/users"""
    __tablename__ = 'license_activations'
    
    id = Column(Integer, primary_key=True)
    license_id = Column(Integer, ForeignKey('licenses.id'), nullable=False)
    device_id = Column(String(100))
    user_id = Column(Integer, ForeignKey('users.id'))
    activated_at = Column(DateTime, default=datetime.utcnow)
    deactivated_at = Column(DateTime)
    is_active = Column(Boolean, default=True)
    ip_address = Column(String(45))
    user_agent = Column(Text)
    location = Column(String(255))  # Geographic location
    hardware_fingerprint = Column(String(255))  # Hardware identifier
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    license = relationship('License', back_populates='activations')
    user = relationship('User')
    
    def __repr__(self):
        return f'<LicenseActivation {self.device_id}>'

class LicenseTemplate(db.Model):
    """License templates for generating new licenses"""
    __tablename__ = 'license_templates'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    license_type = Column(Enum(LicenseType), nullable=False)
    product_name = Column(String(100), nullable=False)
    default_duration_days = Column(Integer, default=365)
    max_activations = Column(Integer, default=1)
    features = Column(Text)  # JSON string of default features
    restrictions = Column(Text)  # JSON string of default restrictions
    is_active = Column(Boolean, default=True)
    created_by = Column(Integer, ForeignKey('users.id'))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<LicenseTemplate {self.name}>'
    
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

class LicenseUsage(db.Model):
    """Track license usage statistics"""
    __tablename__ = 'license_usage'
    
    id = Column(Integer, primary_key=True)
    license_id = Column(Integer, ForeignKey('licenses.id'), nullable=False)
    usage_date = Column(DateTime, default=datetime.utcnow)
    usage_count = Column(Integer, default=0)
    feature_usage = Column(Text)  # JSON string of feature usage data
    user_id = Column(Integer, ForeignKey('users.id'))
    device_id = Column(String(100))
    api_calls = Column(Integer, default=0)
    data_transferred_mb = Column(Float, default=0.0)
    active_sessions = Column(Integer, default=0)
    peak_concurrent_users = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    license = relationship('License')
    user = relationship('User')
    
    def __repr__(self):
        return f'<LicenseUsage {self.usage_date}>'

class LicenseViolation(db.Model):
    """Track license violations and compliance issues"""
    __tablename__ = 'license_violations'
    
    id = Column(Integer, primary_key=True)
    license_id = Column(Integer, ForeignKey('licenses.id'), nullable=False)
    violation_type = Column(String(50), nullable=False)  # overuse, unauthorized_access, etc.
    description = Column(Text)
    severity = Column(String(20), default='medium')  # low, medium, high, critical
    detected_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime)
    is_resolved = Column(Boolean, default=False)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    license = relationship('License')
    
    def __repr__(self):
        return f'<LicenseViolation {self.violation_type}>'