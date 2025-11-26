from datetime import datetime, date
from app import db

# Import models at the end to avoid circular imports

class Restaurant(db.Model):
    __tablename__ = 'restaurants'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.Text)
    phone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    gst_number = db.Column(db.String(15))
    license_number = db.Column(db.String(50))
    description = db.Column(db.Text)
    logo_url = db.Column(db.String(255))
    currency = db.Column(db.String(3), default='USD')  # ISO 4217 currency code
    timezone = db.Column(db.String(50), default='UTC')
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    users = db.relationship('User', backref='restaurant', lazy='select')
    orders = db.relationship('Order', backref='restaurant', lazy='select')
    tables = db.relationship('Table', backref='restaurant', lazy='select')
    menu_items = db.relationship('MenuItem', backref='restaurant', lazy='select')
    subscriptions = db.relationship('RestaurantSubscription', backref='restaurant', lazy='select')
    licenses = db.relationship('RestaurantLicense', backref='restaurant', lazy='select')
    
    def get_active_users_count(self):
        """Get count of active users"""
        # Use a direct query to avoid relationship iteration issues
        from .user import User
        return User.query.filter(
            User.restaurant_id == self.id,
            User.user_active == True
        ).count()
    
    def get_monthly_revenue(self, year, month):
        """Calculate monthly revenue"""
        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1)
        else:
            end_date = date(year, month + 1, 1)
        
        # Import here to avoid circular imports
        from .order import Order
        
        total = db.session.query(db.func.sum(Order.total)).filter(
            Order.restaurant_id == self.id,
            Order.created_at >= start_date,
            Order.created_at < end_date,
            Order.status.in_(['confirmed', 'served'])
        ).scalar()
        
        return float(total) if total else 0.0
    
    def is_subscription_active(self):
        """Check if restaurant has active subscription"""
        # Import here to avoid circular imports
        # These models will be created later
        
        # For now, return a placeholder
        return False
    
    def get_license_status(self):
        """Get overall license status"""
        # Import here to avoid circular imports
        # These models will be created later
        
        # For now, return a placeholder
        return 'No Licenses Configured'
    
    def to_dict(self, include_users=False, include_stats=False):
        """Convert restaurant to dictionary for API responses"""
        result = {
            'id': self.id,
            'name': self.name,
            'address': self.address,
            'phone': self.phone,
            'email': self.email,
            'gst_number': self.gst_number,
            'license_number': self.license_number,
            'description': self.description,
            'logo_url': self.logo_url,
            'currency': self.currency,
            'timezone': self.timezone,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
        
        if include_users:
            # Use a direct query to avoid relationship iteration issues
            from .user import User
            users = User.query.filter_by(restaurant_id=self.id).all()
            result['users'] = [user.to_dict() for user in users]
        
        if include_stats:
            result['active_users_count'] = self.get_active_users_count()
            result['subscription_active'] = self.is_subscription_active()
            result['license_status'] = self.get_license_status()
        
        return result
    
    def __repr__(self):
        return f'<Restaurant {self.name}>'