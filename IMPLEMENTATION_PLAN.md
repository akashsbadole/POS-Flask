# Restaurant POS System - Implementation Plan

## Phase 1: Fix Workspace Problems

### 1.1 Login Manager Error Fix
**Problem**: Cannot assign to attribute "login_view" for class "LoginManager"
**Location**: `app/__init__.py:32`
**Solution**: Update Flask-Login initialization pattern
```python
# Current problematic code:
login_manager.login_view = 'auth.login'

# Fixed version:
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'
```

### 1.2 Receipt Printer ESC/POS Errors
**Problem**: Multiple parameter errors with ESC/POS printer methods
**Location**: `app/receipt_printer.py`
**Solution**: Update ESC/POS API calls to match current library version
```python
# Current problematic code:
self.printer.set(align='center', font='a', text_type='normal')
self.printer.set(text='RESTAURANT POS', bold=True, double_height=True)

# Fixed version:
self.printer.set(align='center', font='a', text_type='normal')
self.printer.text('RESTAURANT POS', bold=True, double_height=True)
```

### 1.3 Order Items Relationship Error
**Problem**: "RelationshipProperty[Any]" is not iterable
**Location**: `app/orders/routes.py:153`
**Solution**: Fix relationship property access
```python
# Current problematic code:
for order_item in order.items:

# Fixed version:
for order_item in order.items:
```

## Phase 2: Enhanced User Role System

### 2.1 New User Model Structure
Create enhanced user model with restaurant associations:
```python
class Restaurant(db.Model):
    __tablename__ = 'restaurants'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.Text)
    phone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    gst_number = db.Column(db.String(15))
    license_number = db.Column(db.String(50))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class User(UserMixin, db.Model):
    # Existing fields...
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurants.id'), nullable=True)
    role = db.Column(db.Enum('super_admin', 'restaurant_owner', 'manager', 'cashier', 'kitchen', 'staff', name='user_role'), nullable=False)
    
    # Relationships
    restaurant = db.relationship('Restaurant', backref='users')
```

### 2.2 Role-based Permission System
Create permission decorators and middleware:
```python
from functools import wraps
from flask import abort, flash, redirect, url_for

def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login'))
            if current_user.role not in roles:
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Usage:
@bp.route('/admin/dashboard')
@role_required('super_admin')
def admin_dashboard():
    pass
```

## Phase 3: GST Calculation System

### 3.1 GST Configuration Model
```python
class GSTSetting(db.Model):
    __tablename__ = 'gst_settings'
    id = db.Column(db.Integer, primary_key=True)
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurants.id'), nullable=False)
    cgst_rate = db.Column(db.Numeric(5, 4), default=0.09)  # 9%
    sgst_rate = db.Column(db.Numeric(5, 4), default=0.09)  # 9%
    is_active = db.Column(db.Boolean, default=True)
    effective_date = db.Column(db.DateTime, default=datetime.utcnow)
```

### 3.2 Enhanced Order Model for GST
```python
class Order(db.Model):
    # Existing fields...
    cgst_amount = db.Column(db.Numeric(10, 2), default=0.00)
    sgst_amount = db.Column(db.Numeric(10, 2), default=0.00)
    gst_rate = db.Column(db.Numeric(5, 4), default=0.18)  # 18% total
    
    def calculate_gst(self):
        """Calculate GST amounts"""
        self.cgst_amount = float(self.subtotal) * float(self.cgst_rate)
        self.sgst_amount = float(self.subtotal) * float(self.sgst_rate)
        self.gst_rate = float(self.cgst_rate) + float(self.sgst_rate)
        self.tax_amount = self.cgst_amount + self.sgst_amount
        self.total = float(self.subtotal) + float(self.tax_amount) + float(self.service_charge) - float(self.discount_amount)
```

## Phase 4: Accounting Module

### 4.1 Chart of Accounts Model
```python
class Account(db.Model):
    __tablename__ = 'accounts'
    id = db.Column(db.Integer, primary_key=True)
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurants.id'), nullable=False)
    account_number = db.Column(db.String(20), unique=True, nullable=False)
    account_name = db.Column(db.String(100), nullable=False)
    account_type = db.Column(db.Enum('asset', 'liability', 'equity', 'revenue', 'expense'), nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('accounts.id'))
    opening_balance = db.Column(db.Numeric(15, 2), default=0.00)
    is_active = db.Column(db.Boolean, default=True)
```

### 4.2 Transaction Model
```python
class Transaction(db.Model):
    __tablename__ = 'transactions'
    id = db.Column(db.Integer, primary_key=True)
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurants.id'), nullable=False)
    transaction_date = db.Column(db.DateTime, default=datetime.utcnow)
    reference_number = db.Column(db.String(50))
    description = db.Column(db.Text)
    total_amount = db.Column(db.Numeric(15, 2), nullable=False)
    
    # Relationships
    entries = db.relationship('TransactionEntry', backref='transaction', lazy=True, cascade='all, delete-orphan')

class TransactionEntry(db.Model):
    __tablename__ = 'transaction_entries'
    id = db.Column(db.Integer, primary_key=True)
    transaction_id = db.Column(db.Integer, db.ForeignKey('transactions.id'), nullable=False)
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=False)
    debit_amount = db.Column(db.Numeric(15, 2), default=0.00)
    credit_amount = db.Column(db.Numeric(15, 2), default=0.00)
```

## Phase 5: Recipe Management

### 5.1 Recipe Models
```python
class Recipe(db.Model):
    __tablename__ = 'recipes'
    id = db.Column(db.Integer, primary_key=True)
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurants.id'), nullable=False)
    menu_item_id = db.Column(db.Integer, db.ForeignKey('menu_items.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    instructions = db.Column(db.Text)
    preparation_time = db.Column(db.Integer)  # minutes
    serving_size = db.Column(db.Integer, default=1)
    cost_per_serving = db.Column(db.Numeric(10, 2), default=0.00)
    selling_price = db.Column(db.Numeric(10, 2), default=0.00)
    is_active = db.Column(db.Boolean, default=True)

class RecipeIngredient(db.Model):
    __tablename__ = 'recipe_ingredients'
    id = db.Column(db.Integer, primary_key=True)
    recipe_id = db.Column(db.Integer, db.ForeignKey('recipes.id'), nullable=False)
    ingredient_id = db.Column(db.Integer, db.ForeignKey('ingredients.id'), nullable=False)
    quantity = db.Column(db.Numeric(10, 3), nullable=False)
    unit = db.Column(db.String(20), nullable=False)
    cost = db.Column(db.Numeric(10, 2), default=0.00)
```

## Phase 6: Subscription Management

### 6.1 Subscription Models
```python
class SubscriptionPlan(db.Model):
    __tablename__ = 'subscription_plans'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    price_monthly = db.Column(db.Numeric(10, 2), nullable=False)
    price_yearly = db.Column(db.Numeric(10, 2), nullable=False)
    max_restaurants = db.Column(db.Integer, default=1)
    max_users = db.Column(db.Integer, default=5)
    features = db.Column(db.Text)  # JSON string of features
    is_active = db.Column(db.Boolean, default=True)

class RestaurantSubscription(db.Model):
    __tablename__ = 'restaurant_subscriptions'
    id = db.Column(db.Integer, primary_key=True)
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurants.id'), nullable=False)
    plan_id = db.Column(db.Integer, db.ForeignKey('subscription_plans.id'), nullable=False)
    start_date = db.Column(db.DateTime, default=datetime.utcnow)
    end_date = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)
    billing_cycle = db.Column(db.Enum('monthly', 'yearly'), default='monthly')
```

## Phase 7: License Management

### 7.1 License Models
```python
class LicenseType(db.Model):
    __tablename__ = 'license_types'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    validity_period_months = db.Column(db.Integer, default=12)
    required_documents = db.Column(db.Text)  # JSON string of required documents

class RestaurantLicense(db.Model):
    __tablename__ = 'restaurant_licenses'
    id = db.Column(db.Integer, primary_key=True)
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurants.id'), nullable=False)
    license_type_id = db.Column(db.Integer, db.ForeignKey('license_types.id'), nullable=False)
    license_number = db.Column(db.String(100), nullable=False)
    issue_date = db.Column(db.DateTime, nullable=False)
    expiry_date = db.Column(db.DateTime, nullable=False)
    issuing_authority = db.Column(db.String(200))
    document_path = db.Column(db.String(255))  # Path to uploaded document
    status = db.Column(db.Enum('active', 'expired', 'pending', 'suspended'), default='active')
```

## Phase 8: Enhanced Offline Capabilities

### 8.1 Service Worker Enhancement
Update service worker for better offline functionality:
```javascript
// Enhanced service worker for offline capabilities
const CACHE_NAME = 'pos-v2';
const urlsToCache = [
    '/',
    '/static/css/app.css',
    '/static/js/app.js',
    '/static/manifest.json',
    '/api/menu/items',
    '/api/tables/list'
];

// Cache first strategy for static assets
// Network first strategy for dynamic data
// Background sync for offline transactions
```

### 8.2 Offline Data Storage
Implement IndexedDB for client-side storage:
```javascript
// Offline data management
class OfflineDataManager {
    constructor() {
        this.dbName = 'POSOfflineDB';
        this.version = 1;
    }
    
    async storeOrder(orderData) {
        // Store order locally when offline
    }
    
    async syncOrders() {
        // Sync orders when back online
    }
}
```

## Implementation Priority

1. **Immediate (Week 1)**: Fix workspace problems
2. **High Priority (Week 2-3)**: Enhanced user role system, GST calculation
3. **Medium Priority (Week 4-5)**: Accounting module, Recipe management
4. **Lower Priority (Week 6-8)**: Subscription management, License management, Enhanced offline

## Testing Strategy

1. **Unit Tests**: Model validation and business logic
2. **Integration Tests**: API endpoints and database operations
3. **End-to-End Tests**: Complete user workflows
4. **Offline Tests**: Verify offline functionality
5. **Performance Tests**: Load testing for concurrent users

## Deployment Considerations

1. **Database Migrations**: Proper migration scripts for schema changes
2. **Backward Compatibility**: Ensure existing data is preserved
3. **Feature Flags**: Enable/disable features during rollout
4. **Monitoring**: Track performance and errors
5. **Rollback Plan**: Quick rollback if issues arise