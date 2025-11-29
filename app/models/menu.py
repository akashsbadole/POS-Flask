from datetime import datetime
from app import db

# Association table for many-to-many relationship between menu items and add-ons
item_add_ons = db.Table('item_add_ons',
    db.Column('item_id', db.Integer, db.ForeignKey('menu_items.id'), primary_key=True),
    db.Column('addon_id', db.Integer, db.ForeignKey('add_ons.id'), primary_key=True)
)

class Category(db.Model):
    __tablename__ = 'categories'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text)
    display_order = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    items = db.relationship('MenuItem', backref='category', lazy='dynamic', order_by='MenuItem.display_order')
    
    def to_dict(self):
        """Convert category to dictionary for API responses"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'display_order': self.display_order,
            'is_active': self.is_active,
            'item_count': self.items.filter_by(is_available=True).count(),
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def __repr__(self):
        return f'<Category {self.name}>'

class MenuItem(db.Model):
    __tablename__ = 'menu_items'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurants.id'), nullable=True)
    hsn_code_id = db.Column(db.Integer, db.ForeignKey('hsn_codes.id'), nullable=True)
    image_url = db.Column(db.String(255))
    is_available = db.Column(db.Boolean, default=True)
    display_order = db.Column(db.Integer, default=0)
    preparation_time = db.Column(db.Integer)  # minutes
    allergens = db.Column(db.Text)  # JSON string of allergen information
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    restaurant = db.relationship('Restaurant', back_populates='menu_items')
    hsn_code = db.relationship('HSNCode', back_populates='menu_items')
    variants = db.relationship('ItemVariant', backref='menu_item', lazy='dynamic', cascade='all, delete-orphan')
    add_ons = db.relationship('AddOn', secondary=item_add_ons, lazy='dynamic', backref='menu_items')
    order_items = db.relationship('OrderItem', back_populates='menu_item')
    
    # Enhanced Customer Engagement Relationships
    recommendations = db.relationship('PersonalizedRecommendation', back_populates='item', lazy='dynamic')
    
    def get_effective_price(self, variant_id=None):
        """Get price including variant modifier"""
        base_price = float(self.price)
        if variant_id:
            variant = ItemVariant.query.get(variant_id)
            if variant:
                base_price += float(variant.price_modifier)
        return base_price
    
    def get_available_add_ons(self):
        """Get only available add-ons"""
        return self.add_ons.filter_by(is_active=True).all()
    
    def to_dict(self, include_variants=True, include_add_ons=True):
        """Convert menu item to dictionary for API responses"""
        result = {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'price': float(self.price),
            'category_id': self.category_id,
            'category_name': self.category.name if self.category else None,
            'image_url': self.image_url,
            'is_available': self.is_available,
            'display_order': self.display_order,
            'preparation_time': self.preparation_time,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
        
        if include_variants:
            result['variants'] = [variant.to_dict() for variant in self.variants.all()]
        
        if include_add_ons:
            result['add_ons'] = [addon.to_dict() for addon in self.get_available_add_ons()]
        
        return result
    
    def __repr__(self):
        return f'<MenuItem {self.name} (${self.price})>'

class ItemVariant(db.Model):
    __tablename__ = 'item_variants'
    
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('menu_items.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)  # e.g., "Small", "Large", "Extra Spicy"
    price_modifier = db.Column(db.Numeric(10, 2), default=0.00)
    display_order = db.Column(db.Integer, default=0)
    is_available = db.Column(db.Boolean, default=True)
    
    def get_total_price(self, base_price):
        """Calculate total price including modifier"""
        return float(base_price) + float(self.price_modifier)
    
    def to_dict(self):
        """Convert variant to dictionary for API responses"""
        return {
            'id': self.id,
            'name': self.name,
            'price_modifier': float(self.price_modifier),
            'display_order': self.display_order,
            'is_available': self.is_available
        }
    
    def __repr__(self):
        return f'<ItemVariant {self.name} (+${self.price_modifier})>'

class AddOnCategory(db.Model):
    __tablename__ = 'addon_categories'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text)
    display_order = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    add_ons = db.relationship('AddOn', backref='category', lazy='dynamic')
    
    def to_dict(self):
        """Convert add-on category to dictionary for API responses"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'display_order': self.display_order,
            'is_active': self.is_active,
            'addon_count': self.add_ons.filter_by(is_active=True).count()
        }
    
    def __repr__(self):
        return f'<AddOnCategory {self.name}>'

class AddOn(db.Model):
    __tablename__ = 'add_ons'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Numeric(10, 2), default=0.00)
    display_order = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    category_id = db.Column(db.Integer, db.ForeignKey('addon_categories.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        """Convert add-on to dictionary for API responses"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'price': float(self.price),
            'display_order': self.display_order,
            'is_active': self.is_active,
            'category_id': self.category_id,
            'category_name': self.category.name if self.category else None
        }
    
    def __repr__(self):
        return f'<AddOn {self.name} (${self.price})>'