from datetime import datetime
from app import db
from .user import User

class Setting(db.Model):
    __tablename__ = 'settings'
    
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(50), nullable=False)
    key = db.Column(db.String(100), nullable=False)
    value = db.Column(db.Text)
    data_type = db.Column(db.String(20), default='string')  # string, integer, boolean, float
    is_system = db.Column(db.Boolean, default=False)  # System settings cannot be modified
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Unique constraint on category + key
    __table_args__ = (db.UniqueConstraint('category', 'key'),)
    
    # Relationships
    updater = db.relationship('User', foreign_keys=[updated_by])
    
    def __init__(self, category, key, value=None, data_type='string', is_system=False, description=None):
        self.category = category
        self.key = key
        self.value = str(value) if value is not None else None
        self.data_type = data_type
        self.is_system = is_system
        self.description = description
    
    def get_typed_value(self):
        """Get value converted to appropriate type"""
        if self.value is None:
            return None
        
        if self.data_type == 'boolean':
            return self.value.lower() in ('true', '1', 'yes', 'on')
        elif self.data_type == 'integer':
            return int(self.value)
        elif self.data_type == 'float':
            return float(self.value)
        else:
            return self.value
    
    def set_typed_value(self, value):
        """Set value with type conversion"""
        if value is None:
            self.value = None
        else:
            self.value = str(value)
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'category': self.category,
            'key': self.key,
            'value': self.get_typed_value(),
            'data_type': self.data_type,
            'is_system': self.is_system,
            'description': self.description,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class SettingsChangeLog(db.Model):
    __tablename__ = 'settings_change_log'
    
    id = db.Column(db.Integer, primary_key=True)
    setting_id = db.Column(db.Integer, db.ForeignKey('settings.id'), nullable=False)
    old_value = db.Column(db.Text)
    new_value = db.Column(db.Text)
    changed_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    changed_at = db.Column(db.DateTime, default=datetime.utcnow)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.Text)
    
    # Relationships
    setting = db.relationship('Setting')
    changer = db.relationship('User', foreign_keys=[changed_by])
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'setting_key': f"{self.setting.category}.{self.setting.key}" if self.setting else None,
            'old_value': self.old_value,
            'new_value': self.new_value,
            'changed_by': self.changer.name if self.changer else None,
            'changed_at': self.changed_at.isoformat() if self.changed_at else None,
            'ip_address': self.ip_address
        }