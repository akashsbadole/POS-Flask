"""
Chef's Special Service
Manages creation and optimization of special menu items from near-expiry ingredients
"""

from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Tuple
from sqlalchemy import and_, or_, func
import logging
import random

from app import db
from app.models.inventory import Ingredient
from app.models.menu import MenuItem
from app.models.recipe import Recipe, RecipeIngredient
from app.models.waste_to_profit import ExpiryTracking, ChefSpecial, WasteRecord
from app.ai.services.inventory_intelligence_service import InventoryIntelligenceService


class ChefSpecialService:
    """Service for managing Chef's Special items"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.inventory_service = InventoryIntelligenceService()
    
    def suggest_chef_specials(self, limit: int = 10) -> List[Dict]:
        """
        Generate AI-powered Chef's Special suggestions using near-expiry ingredients
        
        Args:
            limit: Maximum number of suggestions to generate
            
        Returns:
            List of Chef's Special suggestions
        """
        try:
            # Get near-expiry ingredients
            expiring_ingredients = self._get_expiring_ingredients(days_ahead=7)
            
            if not expiring_ingredients:
                return []
            
            suggestions = []
            
            # Generate different types of suggestions
            suggestions.extend(self._generate_combo_suggestions(expiring_ingredients))
            suggestions.extend(self._generate_soup_suggestions(expiring_ingredients))
            suggestions.extend(self._generate_special_dish_suggestions(expiring_ingredients))
            suggestions.extend(self._generate_beverage_suggestions(expiring_ingredients))
            
            # Sort by priority and return top suggestions
            suggestions.sort(key=lambda x: (x.get('priority_score', 0), x.get('potential_savings', 0)), reverse=True)
            
            return suggestions[:limit]
            
        except Exception as e:
            self.logger.error(f"Error generating Chef's Special suggestions: {str(e)}")
            return []
    
    def create_chef_special(self, name: str, description: str, ingredients_used: List[Dict],
                          special_price: float, preparation_instructions: str = None,
                          presentation_notes: str = None, spice_level: str = 'medium',
                          user_id: int = None) -> ChefSpecial:
        """
        Create a new Chef's Special item
        
        Args:
            name: Name of the special
            description: Description of the special
            ingredients_used: List of ingredient IDs and quantities
            special_price: Special selling price
            preparation_instructions: Preparation instructions
            presentation_notes: Presentation notes
            spice_level: Spice level
            user_id: User creating the special
            
        Returns:
            Created ChefSpecial record
        """
        try:
            # Calculate total ingredient cost
            total_ingredient_cost = self._calculate_ingredient_cost(ingredients_used)
            
            # Calculate profit margin
            profit_margin = ((special_price - total_ingredient_cost) / special_price) * 100
            
            # Calculate cost savings
            cost_savings = self._calculate_cost_savings(ingredients_used)
            
            # Create Chef's Special
            chef_special = ChefSpecial(
                name=name,
                description=description,
                special_price=special_price,
                ingredients_used=ingredients_used,
                total_ingredient_cost=total_ingredient_cost,
                profit_margin=profit_margin,
                cost_savings=cost_savings,
                preparation_instructions=preparation_instructions,
                presentation_notes=presentation_notes,
                spice_level=spice_level,
                status='draft',
                priority=self._calculate_priority(ingredients_used),
                created_by=user_id
            )
            
            db.session.add(chef_special)
            db.session.commit()
            
            self.logger.info(f"Created Chef's Special: {name} with {len(ingredients_used)} ingredients")
            return chef_special
            
        except Exception as e:
            self.logger.error(f"Error creating Chef's Special: {str(e)}")
            db.session.rollback()
            raise
    
    def activate_chef_special(self, special_id: int, max_quantity_per_day: int = None,
                           end_date: date = None, user_id: int = None) -> bool:
        """
        Activate a Chef's Special for sale
        
        Args:
            special_id: ID of the special to activate
            max_quantity_per_day: Maximum quantity per day
            end_date: End date for the special
            user_id: User activating the special
            
        Returns:
            True if successful, False otherwise
        """
        try:
            special = ChefSpecial.query.get(special_id)
            if not special:
                self.logger.error(f"Chef's Special {special_id} not found")
                return False
            
            # Check if ingredients are available
            if not self._check_ingredient_availability(special.ingredients_used):
                self.logger.error(f"Insufficient ingredients for Chef's Special {special_id}")
                return False
            
            # Update special status
            special.status = 'active'
            special.start_date = date.today()
            special.max_quantity_per_day = max_quantity_per_day
            special.end_date = end_date or (date.today() + timedelta(days=7))
            special.available_quantity = max_quantity_per_day or 999
            special.updated_at = datetime.utcnow()
            
            db.session.commit()
            
            self.logger.info(f"Activated Chef's Special: {special.name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error activating Chef's Special: {str(e)}")
            db.session.rollback()
            return False
    
    def update_chef_special_quantity(self, special_id: int, quantity_sold: int) -> bool:
        """
        Update available quantity when a Chef's Special is sold
        
        Args:
            special_id: ID of the special
            quantity_sold: Quantity sold
            
        Returns:
            True if successful, False otherwise
        """
        try:
            special = ChefSpecial.query.get(special_id)
            if not special:
                self.logger.error(f"Chef's Special {special_id} not found")
                return False
            
            # Update available quantity
            special.available_quantity = max(0, special.available_quantity - quantity_sold)
            
            # Check if sold out
            if special.available_quantity == 0:
                special.status = 'sold_out'
            
            # Deduct ingredients from inventory
            for ingredient in special.ingredients_used:
                self._deduct_ingredient_from_inventory(
                    ingredient['ingredient_id'],
                    ingredient['quantity'] * quantity_sold,
                    f"Used in Chef's Special: {special.name}"
                )
            
            db.session.commit()
            
            self.logger.info(f"Updated Chef's Special {special_id}: sold {quantity_sold}, remaining {special.available_quantity}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error updating Chef's Special quantity: {str(e)}")
            db.session.rollback()
            return False
    
    def get_active_chef_specials(self) -> List[ChefSpecial]:
        """
        Get all currently active Chef's Specials
        
        Returns:
            List of active ChefSpecial records
        """
        try:
            return ChefSpecial.query.filter(
                and_(
                    ChefSpecial.status == 'active',
                    ChefSpecial.start_date <= date.today(),
                    or_(
                        ChefSpecial.end_date >= date.today(),
                        ChefSpecial.end_date.is_(None)
                    )
                )
            ).order_by(ChefSpecial.priority.desc(), ChefSpecial.created_at.desc()).all()
            
        except Exception as e:
            self.logger.error(f"Error getting active Chef's Specials: {str(e)}")
            return []
    
    def get_chef_special_analytics(self, days_back: int = 30) -> Dict:
        """
        Get analytics for Chef's Specials performance
        
        Args:
            days_back: Number of days to analyze
            
        Returns:
            Dictionary with Chef's Special analytics
        """
        try:
            start_date = date.today() - timedelta(days=days_back)
            
            # Get all specials in the period
            specials = ChefSpecial.query.filter(
                ChefSpecial.created_at >= start_date
            ).all()
            
            if not specials:
                return {'error': 'No Chef\'s Special data found for the period'}
            
            # Calculate metrics
            total_specials = len(specials)
            active_specials = len([s for s in specials if s.status == 'active'])
            sold_out_specials = len([s for s in specials if s.status == 'sold_out'])
            
            total_cost_savings = sum(float(s.cost_savings or 0) for s in specials)
            total_revenue = sum(float(s.special_price or 0) * (999 - s.available_quantity) for s in specials)
            total_ingredient_cost = sum(float(s.total_ingredient_cost or 0) for s in specials)
            
            # Calculate profit
            total_profit = total_revenue - total_ingredient_cost
            
            # Average metrics
            avg_profit_margin = sum(float(s.profit_margin or 0) for s in specials) / total_specials if total_specials > 0 else 0
            avg_cost_savings = total_cost_savings / total_specials if total_specials > 0 else 0
            
            # Top performing specials
            top_specials = sorted(specials, key=lambda x: float(x.profit_margin or 0), reverse=True)[:5]
            
            return {
                'period_start': start_date.isoformat(),
                'period_end': date.today().isoformat(),
                'total_specials': total_specials,
                'active_specials': active_specials,
                'sold_out_specials': sold_out_specials,
                'total_cost_savings': total_cost_savings,
                'total_revenue': total_revenue,
                'total_ingredient_cost': total_ingredient_cost,
                'total_profit': total_profit,
                'average_profit_margin': avg_profit_margin,
                'average_cost_savings': avg_cost_savings,
                'roi': (total_profit / total_ingredient_cost * 100) if total_ingredient_cost > 0 else 0,
                'top_performing_specials': [s.to_dict() for s in top_specials],
                'ingredient_utilization': self._calculate_ingredient_utilization(specials)
            }
            
        except Exception as e:
            self.logger.error(f"Error getting Chef's Special analytics: {str(e)}")
            return {}
    
    def get_dynamic_pricing_recommendations(self, special_id: int) -> Dict:
        """
        Get dynamic pricing recommendations for a Chef's Special
        
        Args:
            special_id: ID of the Chef's Special
            
        Returns:
            Dictionary with pricing recommendations
        """
        try:
            special = ChefSpecial.query.get(special_id)
            if not special:
                return {'error': 'Chef\'s Special not found'}
            
            # Analyze ingredient costs and market factors
            ingredient_cost = float(special.total_ingredient_cost)
            current_price = float(special.special_price)
            current_margin = float(special.profit_margin or 0)
            
            # Get ingredient urgency
            urgency_factor = self._calculate_ingredient_urgency(special.ingredients_used)
            
            # Calculate recommended price ranges
            min_price = ingredient_cost * 1.2  # 20% minimum margin
            max_price = ingredient_cost * 3.0  # 200% maximum margin
            
            # Adjust for urgency
            if urgency_factor > 0.7:  # High urgency
                min_price = ingredient_cost * 1.1  # Lower margin to sell faster
                recommended_price = min(current_price, min_price * 1.3)
            elif urgency_factor < 0.3:  # Low urgency
                recommended_price = max(current_price, min_price * 1.8)
            else:
                recommended_price = current_price
            
            # Calculate discount if needed
            discount_percentage = 0
            if recommended_price < current_price:
                discount_percentage = ((current_price - recommended_price) / current_price) * 100
            
            return {
                'special_id': special_id,
                'current_price': current_price,
                'current_margin': current_margin,
                'ingredient_cost': ingredient_cost,
                'urgency_factor': urgency_factor,
                'recommended_price': recommended_price,
                'recommended_margin': ((recommended_price - ingredient_cost) / recommended_price) * 100,
                'price_range': {
                    'minimum': min_price,
                    'maximum': max_price
                },
                'discount_percentage': discount_percentage,
                'pricing_strategy': self._get_pricing_strategy(urgency_factor),
                'implementation_notes': self._get_pricing_notes(urgency_factor, discount_percentage)
            }
            
        except Exception as e:
            self.logger.error(f"Error getting pricing recommendations: {str(e)}")
            return {}
    
    def _get_expiring_ingredients(self, days_ahead: int = 7) -> List[Dict]:
        """Get ingredients expiring within specified days"""
        try:
            target_date = date.today() + timedelta(days=days_ahead)
            
            expiry_records = ExpiryTracking.query.filter(
                and_(
                    ExpiryTracking.expiry_date <= target_date,
                    ExpiryTracking.remaining_quantity > 0
                )
            ).all()
            
            expiring_ingredients = []
            for record in expiry_records:
                days_until_expiry = record.get_days_until_expiry()
                urgency = self._calculate_expiry_urgency(days_until_expiry, record.risk_level)
                
                expiring_ingredients.append({
                    'ingredient_id': record.ingredient_id,
                    'ingredient_name': record.ingredient.name if record.ingredient else 'Unknown',
                    'category': record.ingredient.category if record.ingredient else 'unknown',
                    'remaining_quantity': float(record.remaining_quantity),
                    'unit': record.ingredient.unit if record.ingredient else 'units',
                    'unit_cost': float(record.unit_cost),
                    'expiry_date': record.expiry_date.isoformat() if record.expiry_date else None,
                    'days_until_expiry': days_until_expiry,
                    'risk_level': record.risk_level,
                    'urgency': urgency,
                    'batch_number': record.batch_number,
                    'storage_location': record.storage_location
                })
            
            # Sort by urgency
            expiring_ingredients.sort(key=lambda x: x['urgency'], reverse=True)
            return expiring_ingredients
            
        except Exception as e:
            self.logger.error(f"Error getting expiring ingredients: {str(e)}")
            return []
    
    def _generate_combo_suggestions(self, ingredients: List[Dict]) -> List[Dict]:
        """Generate combo meal suggestions"""
        suggestions = []
        
        # Group ingredients by category
        categories = {}
        for ing in ingredients:
            category = ing['category']
            if category not in categories:
                categories[category] = []
            categories[category].append(ing)
        
        # Generate combos from different categories
        if len(categories) >= 2:
            # Create combos with protein + vegetable + carb
            protein = categories.get('meat', []) + categories.get('dairy', [])
            vegetables = categories.get('vegetable', [])
            carbs = categories.get('grain', [])
            
            if protein and vegetables and carbs:
                for i in range(min(2, len(protein))):
                    for j in range(min(2, len(vegetables))):
                        for k in range(min(1, len(carbs))):
                            combo_ingredients = [
                                protein[i], vegetables[j], carbs[k]
                            ]
                            
                            suggestion = self._create_suggestion(
                                'combo',
                                combo_ingredients,
                                f"Chef's Combo Plate",
                                f"Delicious combination of {protein[i]['ingredient_name']} with {vegetables[j]['ingredient_name']} and {carbs[k]['ingredient_name']}"
                            )
                            
                            if suggestion:
                                suggestions.append(suggestion)
        
        return suggestions[:3]  # Limit to 3 combo suggestions
    
    def _generate_soup_suggestions(self, ingredients: List[Dict]) -> List[Dict]:
        """Generate soup suggestions"""
        suggestions = []
        
        # Find suitable ingredients for soup
        soup_ingredients = [ing for ing in ingredients 
                          if ing['category'] in ['vegetable', 'meat', 'dairy']]
        
        if len(soup_ingredients) >= 2:
            for i in range(min(3, len(soup_ingredients))):
                for j in range(i+1, min(i+3, len(soup_ingredients))):
                    soup_mix = [soup_ingredients[i], soup_ingredients[j]]
                    
                    suggestion = self._create_suggestion(
                        'soup',
                        soup_mix,
                        f"Special Soup of the Day",
                        f"Hearty soup made with fresh {soup_ingredients[i]['ingredient_name']} and {soup_ingredients[j]['ingredient_name']}"
                    )
                    
                    if suggestion:
                        suggestions.append(suggestion)
        
        return suggestions[:3]  # Limit to 3 soup suggestions
    
    def _generate_special_dish_suggestions(self, ingredients: List[Dict]) -> List[Dict]:
        """Generate special dish suggestions"""
        suggestions = []
        
        # Find main ingredient (highest value)
        main_ingredients = sorted(ingredients, key=lambda x: x['unit_cost'], reverse=True)[:3]
        
        for main in main_ingredients:
            # Find complementary ingredients
            complementary = [ing for ing in ingredients 
                          if ing['ingredient_id'] != main['ingredient_id'] 
                          and ing['category'] != main['category']][:2]
            
            if complementary:
                dish_ingredients = [main] + complementary
                
                dish_names = [
                    f"Special {main['ingredient_name']} Delight",
                    f"Chef's {main['ingredient_name']} Creation",
                    f"Signature {main['ingredient_name']} Dish"
                ]
                
                suggestion = self._create_suggestion(
                    'special_dish',
                    dish_ingredients,
                    random.choice(dish_names),
                    f"Special chef's creation featuring {main['ingredient_name']} with complementary ingredients"
                )
                
                if suggestion:
                    suggestions.append(suggestion)
        
        return suggestions[:3]  # Limit to 3 special dish suggestions
    
    def _generate_beverage_suggestions(self, ingredients: List[Dict]) -> List[Dict]:
        """Generate beverage suggestions"""
        suggestions = []
        
        # Find suitable ingredients for beverages
        beverage_ingredients = [ing for ing in ingredients 
                              if ing['category'] in ['fruit', 'dairy', 'liquid']]
        
        if len(beverage_ingredients) >= 2:
            for i in range(min(2, len(beverage_ingredients))):
                for j in range(i+1, min(i+2, len(beverage_ingredients))):
                    beverage_mix = [beverage_ingredients[i], beverage_ingredients[j]]
                    
                    suggestion = self._create_suggestion(
                        'beverage',
                        beverage_mix,
                        f"Special Refreshing Drink",
                        f"Refreshing beverage made with {beverage_ingredients[i]['ingredient_name']} and {beverage_ingredients[j]['ingredient_name']}"
                    )
                    
                    if suggestion:
                        suggestions.append(suggestion)
        
        return suggestions[:2]  # Limit to 2 beverage suggestions
    
    def _create_suggestion(self, suggestion_type: str, ingredients: List[Dict], 
                         name: str, description: str) -> Optional[Dict]:
        """Create a suggestion dictionary"""
        try:
            # Calculate costs and quantities
            total_cost = sum(ing['unit_cost'] * ing['remaining_quantity'] * 0.5 for ing in ingredients)
            total_quantity = sum(ing['remaining_quantity'] * 0.5 for ing in ingredients)
            
            # Calculate potential servings
            avg_serving_size = 0.3  # Average serving size per ingredient
            potential_servings = int(total_quantity / avg_serving_size)
            
            # Calculate recommended price
            cost_multiplier = {
                'combo': 2.5,
                'soup': 2.0,
                'special_dish': 3.0,
                'beverage': 2.2
            }
            
            multiplier = cost_multiplier.get(suggestion_type, 2.5)
            recommended_price = total_cost * multiplier
            
            # Calculate priority score
            urgency_score = sum(ing['urgency'] for ing in ingredients) / len(ingredients)
            cost_savings = sum(ing['unit_cost'] * ing['remaining_quantity'] * 0.3 for ing in ingredients)
            priority_score = (urgency_score * 0.6) + (cost_savings * 0.4)
            
            return {
                'type': suggestion_type,
                'name': name,
                'description': description,
                'ingredients': ingredients,
                'total_ingredient_cost': total_cost,
                'potential_servings': potential_servings,
                'recommended_price': recommended_price,
                'estimated_profit_margin': ((recommended_price - total_cost) / recommended_price) * 100,
                'potential_savings': cost_savings,
                'priority_score': priority_score,
                'urgency_score': urgency_score,
                'preparation_time': self._estimate_preparation_time(suggestion_type, ingredients),
                'difficulty_level': self._estimate_difficulty(suggestion_type, ingredients),
                'dietary_info': self._estimate_dietary_info(ingredients),
                'spice_level': 'medium'  # Default spice level
            }
            
        except Exception as e:
            self.logger.error(f"Error creating suggestion: {str(e)}")
            return None
    
    def _calculate_ingredient_cost(self, ingredients_used: List[Dict]) -> float:
        """Calculate total cost of ingredients used"""
        total_cost = 0
        for ingredient in ingredients_used:
            ing_record = Ingredient.query.get(ingredient['ingredient_id'])
            if ing_record:
                total_cost += float(ing_record.unit_cost) * float(ingredient['quantity'])
        return total_cost
    
    def _calculate_cost_savings(self, ingredients_used: List[Dict]) -> float:
        """Calculate cost savings from using near-expiry ingredients"""
        # Assume 30% of ingredient value would have been wasted
        total_savings = 0
        for ingredient in ingredients_used:
            ing_record = Ingredient.query.get(ingredient['ingredient_id'])
            if ing_record:
                ingredient_value = float(ing_record.unit_cost) * float(ingredient['quantity'])
                total_savings += ingredient_value * 0.3
        return total_savings
    
    def _calculate_priority(self, ingredients_used: List[Dict]) -> str:
        """Calculate priority level based on ingredient urgency"""
        total_urgency = 0
        count = 0
        
        for ingredient in ingredients_used:
            expiry_record = ExpiryTracking.query.filter_by(
                ingredient_id=ingredient['ingredient_id']
            ).order_by(ExpiryTracking.expiry_date).first()
            
            if expiry_record:
                days_until = expiry_record.get_days_until_expiry()
                urgency = self._calculate_expiry_urgency(days_until, expiry_record.risk_level)
                total_urgency += urgency
                count += 1
        
        if count == 0:
            return 'low'
        
        avg_urgency = total_urgency / count
        
        if avg_urgency > 0.7:
            return 'urgent'
        elif avg_urgency > 0.4:
            return 'high'
        elif avg_urgency > 0.2:
            return 'medium'
        else:
            return 'low'
    
    def _check_ingredient_availability(self, ingredients_used: List[Dict]) -> bool:
        """Check if all ingredients are available"""
        for ingredient in ingredients_used:
            ing_record = Ingredient.query.get(ingredient['ingredient_id'])
            if not ing_record or float(ing_record.current_stock) < float(ingredient['quantity']):
                return False
        return True
    
    def _deduct_ingredient_from_inventory(self, ingredient_id: int, quantity: float, reason: str):
        """Deduct ingredient from inventory"""
        try:
            ing_record = Ingredient.query.get(ingredient_id)
            if ing_record:
                ing_record.adjust_stock(-quantity, reason, None)
                db.session.commit()
        except Exception as e:
            self.logger.error(f"Error deducting ingredient {ingredient_id}: {str(e)}")
    
    def _calculate_ingredient_urgency(self, ingredients_used: List[Dict]) -> float:
        """Calculate urgency factor for ingredients"""
        total_urgency = 0
        count = 0
        
        for ingredient in ingredients_used:
            expiry_record = ExpiryTracking.query.filter_by(
                ingredient_id=ingredient['ingredient_id']
            ).order_by(ExpiryTracking.expiry_date).first()
            
            if expiry_record:
                days_until = expiry_record.get_days_until_expiry()
                urgency = self._calculate_expiry_urgency(days_until, expiry_record.risk_level)
                total_urgency += urgency
                count += 1
        
        return total_urgency / count if count > 0 else 0
    
    def _calculate_expiry_urgency(self, days_until: int, risk_level: str) -> float:
        """Calculate urgency score based on days until expiry and risk level"""
        if days_until is None:
            return 0.1
        
        # Base urgency from days
        if days_until < 0:
            base_urgency = 1.0
        elif days_until <= 1:
            base_urgency = 0.9
        elif days_until <= 3:
            base_urgency = 0.7
        elif days_until <= 7:
            base_urgency = 0.5
        else:
            base_urgency = 0.2
        
        # Adjust for risk level
        risk_multiplier = {
            'critical': 1.2,
            'high': 1.1,
            'medium': 1.0,
            'low': 0.8
        }
        
        multiplier = risk_multiplier.get(risk_level, 1.0)
        return min(1.0, base_urgency * multiplier)
    
    def _calculate_ingredient_utilization(self, specials: List[ChefSpecial]) -> Dict:
        """Calculate ingredient utilization from Chef's Specials"""
        ingredient_usage = {}
        
        for special in specials:
            for ingredient in special.ingredients_used:
                ing_id = ingredient['ingredient_id']
                if ing_id not in ingredient_usage:
                    ingredient_usage[ing_id] = {
                        'name': ingredient.get('name', 'Unknown'),
                        'total_used': 0,
                        'total_cost_saved': 0
                    }
                
                ingredient_usage[ing_id]['total_used'] += ingredient['quantity']
                
                # Calculate cost saved (30% of value would have been wasted)
                ing_record = Ingredient.query.get(ing_id)
                if ing_record:
                    cost_saved = float(ing_record.unit_cost) * ingredient['quantity'] * 0.3
                    ingredient_usage[ing_id]['total_cost_saved'] += cost_saved
        
        return ingredient_usage
    
    def _get_pricing_strategy(self, urgency_factor: float) -> str:
        """Get pricing strategy based on urgency"""
        if urgency_factor > 0.7:
            return 'aggressive_sale'
        elif urgency_factor > 0.4:
            return 'competitive_pricing'
        else:
            return 'premium_pricing'
    
    def _get_pricing_notes(self, urgency_factor: float, discount_percentage: float) -> str:
        """Get pricing implementation notes"""
        if urgency_factor > 0.7:
            return "High urgency - recommend aggressive pricing to move inventory quickly"
        elif discount_percentage > 20:
            return "Significant discount recommended - highlight as special offer"
        elif discount_percentage > 10:
            return "Moderate discount recommended - good value proposition"
        else:
            return "Current pricing is appropriate - maintain premium positioning"
    
    def _estimate_preparation_time(self, suggestion_type: str, ingredients: List[Dict]) -> int:
        """Estimate preparation time in minutes"""
        base_times = {
            'combo': 15,
            'soup': 25,
            'special_dish': 20,
            'beverage': 10
        }
        
        base_time = base_times.get(suggestion_type, 20)
        
        # Adjust for number of ingredients
        ingredient_factor = min(1.5, 1 + (len(ingredients) - 2) * 0.1)
        
        return int(base_time * ingredient_factor)
    
    def _estimate_difficulty(self, suggestion_type: str, ingredients: List[Dict]) -> str:
        """Estimate preparation difficulty"""
        base_difficulty = {
            'combo': 'medium',
            'soup': 'easy',
            'special_dish': 'medium',
            'beverage': 'easy'
        }
        
        base = base_difficulty.get(suggestion_type, 'medium')
        
        # Adjust for number of ingredients
        if len(ingredients) > 4:
            return 'hard'
        elif len(ingredients) > 2:
            return base
        else:
            return 'easy' if base == 'easy' else 'medium'
    
    def _estimate_dietary_info(self, ingredients: List[Dict]) -> Dict:
        """Estimate dietary information"""
        dietary_info = {
            'vegetarian': True,
            'vegan': True,
            'gluten_free': True,
            'dairy_free': True
        }
        
        for ingredient in ingredients:
            ing_record = Ingredient.query.get(ingredient['ingredient_id'])
            if ing_record:
                # This would typically come from ingredient database
                # For now, make assumptions based on category
                category = ing_record.category
                
                if category in ['meat', 'poultry', 'fish']:
                    dietary_info['vegetarian'] = False
                    dietary_info['vegan'] = False
                elif category in ['dairy']:
                    dietary_info['vegan'] = False
                    dietary_info['dairy_free'] = False
                elif category in ['grain']:
                    dietary_info['gluten_free'] = False
        
        return dietary_info