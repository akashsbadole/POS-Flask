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
    
    # Nutritional information (per serving)
    calories = db.Column(db.Integer, default=0)
    protein = db.Column(db.Numeric(8, 2), default=0.00)  # in grams
    carbohydrates = db.Column(db.Numeric(8, 2), default=0.00)  # in grams
    fat = db.Column(db.Numeric(8, 2), default=0.00)  # in grams
    saturated_fat = db.Column(db.Numeric(8, 2), default=0.00)  # in grams
    trans_fat = db.Column(db.Numeric(8, 2), default=0.00)  # in grams
    cholesterol = db.Column(db.Numeric(8, 2), default=0.00)  # in mg
    sodium = db.Column(db.Numeric(8, 2), default=0.00)  # in mg
    fiber = db.Column(db.Numeric(8, 2), default=0.00)  # in grams
    sugar = db.Column(db.Numeric(8, 2), default=0.00)  # in grams
    vitamin_a = db.Column(db.Integer, default=0)  # in IU
    vitamin_c = db.Column(db.Integer, default=0)  # in mg
    calcium = db.Column(db.Integer, default=0)  # in mg
    iron = db.Column(db.Integer, default=0)  # in mg
    potassium = db.Column(db.Integer, default=0)  # in mg
    
    # Scaling information
    base_serving_size = db.Column(db.Integer, default=1)  # Base serving size for scaling
    scaling_factor = db.Column(db.Numeric(5, 2), default=1.0)  # Current scaling factor
    is_scalable = db.Column(db.Boolean, default=True)  # Whether recipe can be scaled
    
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
    
    def scale_to(self, target_servings):
        """Scale recipe to target number of servings"""
        if not self.is_scalable or target_servings <= 0 or (self.base_serving_size or self.serving_size) <= 0:
            return None
        
        base_servings = self.base_serving_size or self.serving_size
        scaling_factor = target_servings / base_servings
        
        # Create scaled recipe data
        scaled_ingredients = []
        for recipe_ingredient in self.ingredients:
            scaled_quantity = float(recipe_ingredient.quantity) * scaling_factor
            scaled_ingredients.append({
                'name': recipe_ingredient.ingredient.name,
                'quantity': round(scaled_quantity, 3),
                'unit': recipe_ingredient.ingredient.unit,
                'notes': recipe_ingredient.notes,
                'original_quantity': float(recipe_ingredient.quantity),
                'unit_cost': float(recipe_ingredient.ingredient.unit_cost),
                'total_cost': round(scaled_quantity * float(recipe_ingredient.ingredient.unit_cost), 2),
                'original_total_cost': float(recipe_ingredient.total_cost)
            })
        
        # Calculate scaled costs
        original_total_cost = self.calculate_total_cost()
        scaled_total_cost = original_total_cost * scaling_factor
        
        return {
            'ingredients': scaled_ingredients,
            'total_cost': round(scaled_total_cost, 2),
            'cost_per_serving': round(scaled_total_cost / target_servings, 2),
            'nutrition': self.get_scaled_nutrition(target_servings),
            'target_servings': target_servings,
            'scaling_factor': round(scaling_factor, 2),
            'base_servings': base_servings
        }
    
    def get_scaled_nutrition(self, target_servings=None):
        """Get nutritional information scaled to target servings"""
        if target_servings is None:
            target_servings = self.serving_size
        
        if not self.is_scalable:
            scaling_factor = 1.0
        else:
            scaling_factor = target_servings / self.serving_size
        
        return {
            'calories': int(self.calories * scaling_factor) if self.calories else 0,
            'protein': round(float(self.protein) * scaling_factor, 2) if self.protein else 0.0,
            'carbohydrates': round(float(self.carbohydrates) * scaling_factor, 2) if self.carbohydrates else 0.0,
            'fat': round(float(self.fat) * scaling_factor, 2) if self.fat else 0.0,
            'saturated_fat': round(float(self.saturated_fat) * scaling_factor, 2) if self.saturated_fat else 0.0,
            'cholesterol': round(float(self.cholesterol) * scaling_factor, 2) if self.cholesterol else 0.0,
            'sodium': round(float(self.sodium) * scaling_factor, 2) if self.sodium else 0.0,
            'fiber': round(float(self.fiber) * scaling_factor, 2) if self.fiber else 0.0,
            'sugar': round(float(self.sugar) * scaling_factor, 2) if self.sugar else 0.0,
            'vitamin_a': int(self.vitamin_a * scaling_factor) if self.vitamin_a else 0,
            'vitamin_c': int(self.vitamin_c * scaling_factor) if self.vitamin_c else 0,
            'calcium': int(self.calcium * scaling_factor) if self.calcium else 0,
            'iron': int(self.iron * scaling_factor) if self.iron else 0,
            'potassium': int(self.potassium * scaling_factor) if self.potassium else 0,
            'servings': target_servings,
            'scaling_factor': scaling_factor
        }
    
    def get_nutrition_summary(self):
        """Get formatted nutritional summary"""
        return {
            'calories': self.calories or 0,
            'protein': round(float(self.protein), 1) if self.protein else 0.0,
            'carbohydrates': round(float(self.carbohydrates), 1) if self.carbohydrates else 0.0,
            'fat': round(float(self.fat), 1) if self.fat else 0.0,
            'saturated_fat': round(float(self.saturated_fat), 1) if self.saturated_fat else 0.0,
            'cholesterol': round(float(self.cholesterol), 1) if self.cholesterol else 0.0,
            'sodium': round(float(self.sodium), 1) if self.sodium else 0.0,
            'fiber': round(float(self.fiber), 1) if self.fiber else 0.0,
            'sugar': round(float(self.sugar), 1) if self.sugar else 0.0,
            'vitamin_a': self.vitamin_a or 0,
            'vitamin_c': self.vitamin_c or 0,
            'calcium': self.calcium or 0,
            'iron': self.iron or 0,
            'potassium': self.potassium or 0,
            'servings': self.serving_size
        }
    
    def get_daily_value_percentage(self, nutrient, daily_value):
        """Calculate daily value percentage for a nutrient"""
        if nutrient and daily_value and daily_value > 0:
            return round((nutrient / daily_value) * 100, 1)
        return 0
    
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
            'is_scalable': self.is_scalable,
            'base_serving_size': self.base_serving_size,
            'scaling_factor': float(self.scaling_factor) if self.scaling_factor else 1.0,
            'created_at': self.created_at.isoformat() if getattr(self, 'created_at', None) else None,
            'updated_at': self.updated_at.isoformat() if getattr(self, 'updated_at', None) else None,
            'ingredients': self.get_ingredient_list(),
            'nutrition': self.get_nutrition_summary()
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