from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.Enum('super_admin', 'restaurant_owner', 'manager', 'cashier', 'kitchen', 'staff', name='user_role'), nullable=False)
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurants.id'), nullable=True)
    pin_code = db.Column(db.String(4), nullable=True)  # For quick login
    user_active = db.Column('is_active', db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    phone = db.Column(db.String(20))
    profile_image = db.Column(db.String(255))
    
    # Relationships
    orders = db.relationship('Order', back_populates='user')
    created_customers = db.relationship('Customer', back_populates='creator')
    restaurant = db.relationship('Restaurant', back_populates='users')
    credit_transactions = db.relationship('CreditTransaction', back_populates='user')
    
    def set_password(self, password):
        """Set password hash"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check password against hash"""
        return check_password_hash(self.password_hash, password)
    
    def set_pin(self, pin):
        """Set PIN code for quick login"""
        if pin and len(pin) == 4:
            self.pin_code = generate_password_hash(pin)
        else:
            self.pin_code = None
    
    def check_pin(self, pin):
        """Check PIN code"""
        return self.pin_code and check_password_hash(self.pin_code, pin)
    
    def has_role(self, role):
        """Check if user has specific role"""
        return self.role == role
    
    def can_access_manager_features(self):
        """Check if user can access manager features"""
        return self.role in ['manager', 'restaurant_owner', 'super_admin']
    
    def can_access_admin_features(self):
        """Check if user can access admin features"""
        return self.role in ['restaurant_owner', 'super_admin']
    
    def can_access_super_admin_features(self):
        """Check if user can access super admin features"""
        return self.role == 'super_admin'
    
    def can_access_restaurant_features(self):
        """Check if user can access restaurant-specific features"""
        return self.role in ['restaurant_owner', 'manager', 'cashier', 'kitchen', 'staff']
    
    def can_manage_restaurant(self, restaurant_id):
        """Check if user can manage specific restaurant"""
        if self.role == 'super_admin':
            return True
        elif self.role == 'restaurant_owner':
            return self.restaurant_id == restaurant_id
        elif self.role in ['manager']:
            return self.restaurant_id == restaurant_id
        return False
    
    def get_restaurant_scope(self):
        """Get list of restaurant IDs user can access"""
        if self.role == 'super_admin':
            # Super admin can access all restaurants
            from app.models.restaurant import Restaurant
            return [r.id for r in Restaurant.query.filter_by(is_active=True).all()]
        elif self.restaurant_id:
            return [self.restaurant_id]
        return []
    
    def update_last_login(self):
        """Update last login timestamp"""
        self.last_login = datetime.utcnow()
        db.session.commit()
    
    def to_dict(self, include_restaurant=False):
        """Convert user to dictionary for API responses"""
        result = {
            'id': self.id,
            'email': self.email,
            'name': self.name,
            'role': self.role,
            'restaurant_id': self.restaurant_id,
            'phone': self.phone,
            'profile_image': self.profile_image,
            'is_active': self.user_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None
        }
        
        if include_restaurant and self.restaurant:
            result['restaurant'] = self.restaurant.to_dict()
        
        return result
    
    def get_role_display_name(self):
        """Get display name for user role"""
        role_names = {
            'super_admin': 'Super Admin',
            'restaurant_owner': 'Restaurant Owner',
            'manager': 'Manager',
            'cashier': 'Cashier',
            'kitchen': 'Kitchen Staff',
            'staff': 'Staff'
        }
        return role_names.get(self.role, self.role)
    
    def get_permissions(self):
        """Get permissions based on user role"""
        permissions = {
            'super_admin': [
                'manage_restaurants', 'manage_subscriptions', 'manage_licenses',
                'manage_all_users', 'view_global_reports', 'system_configuration'
            ],
            'restaurant_owner': [
                'manage_restaurant', 'manage_menu', 'manage_orders', 'manage_staff',
                'view_reports', 'manage_inventory', 'manage_accounting'
            ],
            'manager': [
                'manage_menu', 'manage_orders', 'manage_staff', 'view_reports',
                'manage_inventory', 'manage_tables'
            ],
            'cashier': [
                'take_orders', 'process_payments', 'view_order_history',
                'manage_tables', 'basic_inventory'
            ],
            'kitchen': [
                'view_orders', 'update_order_status', 'manage_kitchen_inventory',
                'print_kitchen_tickets'
            ],
            'staff': [
                'view_orders', 'basic_operations', 'view_reports'
            ]
        }
        return permissions.get(self.role, [])
    
    def __repr__(self):
        return f'<User {self.name} ({self.get_role_display_name()})>'