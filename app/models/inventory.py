from datetime import datetime
from app import db

class Ingredient(db.Model):
    __tablename__ = 'ingredients'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text)
    unit = db.Column(db.String(20), nullable=False)  # kg, g, l, ml, pcs, etc.
    current_stock = db.Column(db.Numeric(10, 3), default=0.000)
    minimum_stock = db.Column(db.Numeric(10, 3), default=0.000)
    unit_cost = db.Column(db.Numeric(10, 2), default=0.00)
    supplier = db.Column(db.String(100))
    category = db.Column(db.String(50), default='other')  # vegetable, meat, dairy, grain, spice, liquid, other
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    stock_adjustments = db.relationship('StockAdjustment', backref='ingredient', lazy=True)
    menu_item_ingredients = db.relationship('MenuItemIngredient', backref='ingredient', lazy=True)
    
    def is_low_stock(self):
        """Check if ingredient is below minimum stock level"""
        return float(self.current_stock) <= float(self.minimum_stock)
    
    def get_stock_status(self):
        """Get stock status as text"""
        if float(self.current_stock) == 0:
            return "Out of Stock"
        elif self.is_low_stock():
            return "Low Stock"
        else:
            return "In Stock"
    
    def adjust_stock(self, quantity, reason, user_id):
        """Adjust stock quantity"""
        adjustment = StockAdjustment(
            ingredient_id=self.id,
            quantity=quantity,
            previous_quantity=self.current_stock,
            new_quantity=float(self.current_stock) + float(quantity),
            reason=reason,
            user_id=user_id
        )
        
        self.current_stock = adjustment.new_quantity
        db.session.add(adjustment)
        
        return adjustment
    
    def to_dict(self):
        """Convert ingredient to dictionary for API responses"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'unit': self.unit,
            'current_stock': float(self.current_stock),
            'minimum_stock': float(self.minimum_stock),
            'unit_cost': float(self.unit_cost),
            'supplier': self.supplier,
            'category': self.category or 'other',
            'stock_status': self.get_stock_status(),
            'is_low_stock': self.is_low_stock(),
            'last_updated': self.last_updated.isoformat() if self.last_updated else None
        }
    
    def __repr__(self):
        return f'<Ingredient {self.name} ({self.current_stock} {self.unit})>'

class StockAdjustment(db.Model):
    __tablename__ = 'stock_adjustments'
    
    id = db.Column(db.Integer, primary_key=True)
    ingredient_id = db.Column(db.Integer, db.ForeignKey('ingredients.id'), nullable=False)
    quantity = db.Column(db.Numeric(10, 3), nullable=False)  # Positive for addition, negative for subtraction
    previous_quantity = db.Column(db.Numeric(10, 3), nullable=False)
    new_quantity = db.Column(db.Numeric(10, 3), nullable=False)
    reason = db.Column(db.String(255))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='stock_adjustments')
    
    def get_adjustment_type(self):
        """Get adjustment type as text"""
        if float(self.quantity) > 0:
            return "Stock In"
        elif float(self.quantity) < 0:
            return "Stock Out"
        else:
            return "Adjustment"
    
    def to_dict(self):
        """Convert stock adjustment to dictionary for API responses"""
        return {
            'id': self.id,
            'ingredient_id': self.ingredient_id,
            'ingredient_name': self.ingredient.name if self.ingredient else None,
            'quantity': float(self.quantity),
            'previous_quantity': float(self.previous_quantity),
            'new_quantity': float(self.new_quantity),
            'reason': self.reason,
            'adjustment_type': self.get_adjustment_type(),
            'user_id': self.user_id,
            'user_name': self.user.name if self.user else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def __repr__(self):
        return f'<StockAdjustment {self.ingredient.name}: {self.quantity} {self.ingredient.unit}>'

class MenuItemIngredient(db.Model):
    __tablename__ = 'menu_item_ingredients'
    
    id = db.Column(db.Integer, primary_key=True)
    menu_item_id = db.Column(db.Integer, db.ForeignKey('menu_items.id'), nullable=False)
    ingredient_id = db.Column(db.Integer, db.ForeignKey('ingredients.id'), nullable=False)
    quantity_required = db.Column(db.Numeric(10, 3), nullable=False)  # Amount of ingredient per menu item
    
    # Relationships
    menu_item = db.relationship('MenuItem', backref='menu_item_ingredients')
    
    def check_availability(self, quantity_needed=1):
        """Check if enough ingredient is available for the given quantity of menu items"""
        required_total = float(self.quantity_required) * quantity_needed
        return float(self.ingredient.current_stock) >= required_total
    
    def deduct_from_stock(self, quantity_deducted=1):
        """Deduct ingredient from stock when menu item is sold"""
        required_total = float(self.quantity_required) * quantity_deducted
        return self.ingredient.adjust_stock(-required_total, f"Used for {self.menu_item.name}", None)
    
    def to_dict(self):
        """Convert menu item ingredient to dictionary for API responses"""
        return {
            'id': self.id,
            'menu_item_id': self.menu_item_id,
            'menu_item_name': self.menu_item.name if self.menu_item else None,
            'ingredient_id': self.ingredient_id,
            'ingredient_name': self.ingredient.name if self.ingredient else None,
            'quantity_required': float(self.quantity_required),
            'unit': self.ingredient.unit if self.ingredient else None,
            'current_stock': float(self.ingredient.current_stock) if self.ingredient else 0,
            'is_available': self.check_availability(),
            'can_make_quantity': int(float(self.ingredient.current_stock) / float(self.quantity_required)) if self.ingredient and float(self.quantity_required) > 0 else 0
        }
    
    def __repr__(self):
        return f'<MenuItemIngredient {self.menu_item.name if self.menu_item else "Unknown"} requires {self.quantity_required} {self.ingredient.unit if self.ingredient else ""} of {self.ingredient.name if self.ingredient else "Unknown"}>'