from datetime import datetime
from typing import List, TYPE_CHECKING
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app import db

if TYPE_CHECKING:
    from app.models.menu import MenuItem
    from app.models.inventory import Ingredient

class Recipe(db.Model):
    """Recipe model for menu items"""
    __tablename__ = 'recipes'
    
    id = db.Column(db.Integer, primary_key=True)
    menu_item_id = db.Column(db.Integer, db.ForeignKey('menu_items.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    instructions = db.Column(db.Text)
    prep_time = db.Column(db.Integer)  # in minutes
    cook_time = db.Column(db.Integer)  # in minutes
    serving_size = db.Column(db.Integer, default=1)
    difficulty_level = db.Column(db.Enum('Easy', 'Medium', 'Hard'), default='Medium')
    cost_per_serving = db.Column(db.Numeric(10, 2), default=0.00)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    menu_item = relationship('MenuItem', backref='recipe')
    ingredients = relationship('RecipeIngredient', backref='recipe', cascade='all, delete-orphan')
    
    def calculate_total_cost(self):
        """Calculate total cost of recipe"""
        total_cost = 0.0
        for recipe_ingredient in self.ingredients:
            total_cost += float(recipe_ingredient.total_cost)
        return total_cost
    
    def calculate_cost_per_serving(self):
        """Calculate cost per serving"""
        total_cost = self.calculate_total_cost()
        return total_cost / self.serving_size if self.serving_size > 0 else 0
    
    def update_cost(self):
        """Update recipe cost based on current ingredient prices"""
        self.cost_per_serving = self.calculate_cost_per_serving()
    
    def get_ingredient_list(self):
        """Get formatted ingredient list"""
        ingredients = []
        for recipe_ingredient in self.ingredients:
            ingredients.append({
                'name': recipe_ingredient.ingredient.name,
                'quantity': recipe_ingredient.quantity,
                'unit': recipe_ingredient.ingredient.unit,
                'cost': float(recipe_ingredient.total_cost)
            })
        return ingredients
    
    def to_dict(self):
        """Convert recipe to dictionary for API responses"""
        return {
            'id': self.id,
            'menu_item_id': self.menu_item_id,
            'menu_item_name': self.menu_item.name if self.menu_item else None,
            'name': self.name,
            'description': self.description,
            'instructions': self.instructions,
            'prep_time': self.prep_time,
            'cook_time': self.cook_time,
            'serving_size': self.serving_size,
            'difficulty_level': self.difficulty_level,
            'cost_per_serving': float(self.cost_per_serving),
            'total_cost': self.calculate_total_cost(),
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'ingredients': self.get_ingredient_list()
        }
    
    def __repr__(self):
        return f'<Recipe {self.name} for {self.menu_item.name if self.menu_item else "Unknown"}>'

class RecipeIngredient(db.Model):
    """Association table for recipes and ingredients"""
    __tablename__ = 'recipe_ingredients'
    
    id = db.Column(db.Integer, primary_key=True)
    recipe_id = db.Column(db.Integer, db.ForeignKey('recipes.id'), nullable=False)
    ingredient_id = db.Column(db.Integer, db.ForeignKey('ingredients.id'), nullable=False)
    quantity = db.Column(db.Numeric(10, 3), nullable=False)
    notes = db.Column(db.String(255))
    
    # Relationships
    ingredient = relationship('Ingredient', backref='recipe_ingredients')
    
    @property
    def total_cost(self):
        """Calculate total cost for this ingredient in the recipe"""
        if self.ingredient and self.ingredient.unit_cost:
            return float(self.quantity) * float(self.ingredient.unit_cost)
        return 0.0
    
    def to_dict(self):
        """Convert recipe ingredient to dictionary for API responses"""
        return {
            'id': self.id,
            'recipe_id': self.recipe_id,
            'ingredient_id': self.ingredient_id,
            'ingredient_name': self.ingredient.name if self.ingredient else None,
            'quantity': float(self.quantity),
            'unit': self.ingredient.unit if self.ingredient else None,
            'unit_cost': float(self.ingredient.unit_cost) if self.ingredient else 0.0,
            'total_cost': self.total_cost,
            'notes': self.notes
        }
    
    def __repr__(self):
        return f'<RecipeIngredient {self.quantity} {self.ingredient.name if self.ingredient else "Unknown"}>'

class RecipeCategory(db.Model):
    """Recipe categories for organization"""
    __tablename__ = 'recipe_categories'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.Text)
    color = db.Column(db.String(7), default='#6B7280')  # Hex color code
    display_order = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    
    def to_dict(self):
        """Convert recipe category to dictionary for API responses"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'color': self.color,
            'display_order': self.display_order,
            'is_active': self.is_active
        }
    
    def __repr__(self):
        return f'<RecipeCategory {self.name}>'

class RecipeTag(db.Model):
    """Tags for recipes"""
    __tablename__ = 'recipe_tags'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    color = db.Column(db.String(7), default='#6B7280')  # Hex color code
    
    def to_dict(self):
        """Convert recipe tag to dictionary for API responses"""
        return {
            'id': self.id,
            'name': self.name,
            'color': self.color
        }
    
    def __repr__(self):
        return f'<RecipeTag {self.name}>'

# Association table for recipes and tags
recipe_tags = db.Table('recipe_tag_associations',
    db.Column('recipe_id', db.Integer, db.ForeignKey('recipes.id'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('recipe_tags.id'), primary_key=True)
)