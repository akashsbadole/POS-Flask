"""
AI Upselling Recommendation Service
Provides intelligent upselling recommendations based on:
- Customer behavior analysis
- Order history patterns
- Item popularity and combinations
- Real-time context
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import MinMaxScaler
from collections import defaultdict, Counter
import json
import logging

from app import db
from app.models.menu import MenuItem, Category
from app.models.order import OrderItem
from app.models.order import Order
from app.models.customer import Customer
from app.models.ai_models import AIModel, AIRecommendation, AIPredictionLog
from app.models.user import User


class UpsellingService:
    """AI-powered upselling recommendation engine"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.model = None
        self.item_features = None
        self.customer_features = None
        self.load_models()
    
    def load_models(self):
        """Load trained upselling models"""
        try:
            # Get active upselling model
            active_model = AIModel.query.filter_by(
                model_type='upselling', 
                is_active=True, 
                is_production=True
            ).first()
            
            if active_model:
                # In a real implementation, load the actual ML model
                # self.model = joblib.load(active_model.model_path)
                self.logger.info(f"Loaded upselling model: {active_model.name}")
            else:
                self.logger.warning("No active upselling model found")
                
        except Exception as e:
            self.logger.error(f"Error loading upselling model: {str(e)}")
    
    def get_recommendations(self, customer_id=None, user_id=None, current_items=None, 
                       order_context=None, limit=5):
        """
        Get upselling recommendations based on current order context
        
        Args:
            customer_id: ID of the customer (optional)
            user_id: ID of the user placing order
            current_items: List of current items in cart/order
            order_context: Order context (time, day, etc.)
            limit: Maximum number of recommendations
            
        Returns:
            List of recommendation dictionaries with items and scores
        """
        try:
            recommendations = []
            
            # Get customer behavior if available
            customer_profile = self._get_customer_profile(customer_id)
            
            # Analyze current cart items
            cart_analysis = self._analyze_cart_items(current_items)
            
            # Generate different types of recommendations
            recommendations.extend(
                self._get_complementary_items(current_items, customer_profile, limit//2)
            )
            
            recommendations.extend(
                self._get_popular_upsells(current_items, customer_profile, limit//2)
            )
            
            recommendations.extend(
                self._get_seasonal_recommendations(customer_profile, limit//3)
            )
            
            # Score and rank recommendations
            scored_recommendations = self._score_recommendations(
                recommendations, customer_profile, cart_analysis
            )
            
            # Apply business rules and filters
            filtered_recommendations = self._apply_business_rules(
                scored_recommendations, customer_id, user_id
            )
            
            # Return top recommendations
            return sorted(filtered_recommendations, key=lambda x: x['score'], reverse=True)[:limit]
            
        except Exception as e:
            self.logger.error(f"Error generating recommendations: {str(e)}")
            return []
    
    def _get_customer_profile(self, customer_id):
        """Build customer profile from order history"""
        if not customer_id:
            return None
            
        try:
            customer = Customer.query.get(customer_id)
            if not customer:
                return None
                
            # Get customer's order history
            orders = Order.query.filter_by(customer_id=customer_id).limit(50).all()
            
            profile = {
                'id': customer_id,
                'total_orders': len(orders),
                'avg_order_value': np.mean([o.total_amount for o in orders]) if orders else 0,
                'favorite_categories': self._get_favorite_categories(orders),
                'order_frequency': self._calculate_order_frequency(orders),
                'preferred_price_range': self._get_price_preference(orders),
                'last_order_date': max([o.created_at for o in orders]) if orders else None
            }
            
            return profile
            
        except Exception as e:
            self.logger.error(f"Error building customer profile: {str(e)}")
            return None
    
    def _analyze_cart_items(self, current_items):
        """Analyze current items in cart"""
        if not current_items:
            return {}
            
        try:
            item_ids = [item.get('id') for item in current_items]
            menu_items = MenuItem.query.filter(MenuItem.id.in_(item_ids)).all()
            
            cart_analysis = {
                'total_items': len(current_items),
                'total_value': sum(item.get('price', 0) for item in current_items),
                'categories': list(set([item.category.name for item in menu_items])),
                'avg_price': np.mean([item.price for item in menu_items]),
                'has_beverage': any(item.category.name.lower() == 'beverages' for item in menu_items),
                'has_main_course': any('main' in item.category.name.lower() for item in menu_items),
                'has_dessert': any('dessert' in item.category.name.lower() for item in menu_items)
            }
            
            return cart_analysis
            
        except Exception as e:
            self.logger.error(f"Error analyzing cart items: {str(e)}")
            return {}
    
    def _get_complementary_items(self, current_items, customer_profile, limit):
        """Get items that complement current cart items"""
        try:
            if not current_items:
                return []
                
            # Get item IDs from current cart
            current_item_ids = [item.get('id') for item in current_items]
            
            # Find frequently bought together items
            complementary_items = []
            
            # Get orders containing current items
            orders_with_current_items = db.session.query(Order.id).join(OrderItem).filter(
                OrderItem.menu_item_id.in_(current_item_ids)
            ).subquery()
            
            # Find items frequently bought with current items
            complementary_query = db.session.query(
                OrderItem.menu_item_id,
                db.func.count(OrderItem.id).label('frequency')
            ).filter(
                OrderItem.order_id.in_(orders_with_current_items),
                ~OrderItem.menu_item_id.in_(current_item_ids)
            ).group_by(OrderItem.menu_item_id).order_by(
                db.desc('frequency')
            ).limit(limit * 2)
            
            for item_id, frequency in complementary_query:
                menu_item = MenuItem.query.get(item_id)
                if menu_item and menu_item.is_available:
                    complementary_items.append({
                        'item_id': item_id,
                        'name': menu_item.name,
                        'price': float(menu_item.price),
                        'category': menu_item.category.name,
                        'recommendation_type': 'complementary',
                        'reason': f"Customers who bought these items also bought {menu_item.name}",
                        'frequency': frequency,
                        'score': frequency * 0.8  # Weight for complementary items
                    })
            
            return complementary_items[:limit]
            
        except Exception as e:
            self.logger.error(f"Error getting complementary items: {str(e)}")
            return []
    
    def _get_popular_upsells(self, current_items, customer_profile, limit):
        """Get popular upsell items based on current cart"""
        try:
            if not current_items:
                return []
                
            # Get categories in current cart
            current_categories = set()
            for item in current_items:
                menu_item = MenuItem.query.get(item.get('id'))
                if menu_item:
                    current_categories.add(menu_item.category.name)
            
            # Get popular items in same categories with higher price
            popular_upsells = []
            
            for category in current_categories:
                # Get average price in this category from current cart
                category_items = [item for item in current_items 
                               if MenuItem.query.get(item.get('id')) and 
                               MenuItem.query.get(item.get('id')).category.name == category]
                avg_price = np.mean([item.get('price', 0) for item in category_items]) if category_items else 0
                
                # Find popular items in same category with higher price
                popular_items = db.session.query(
                    MenuItem.id, MenuItem.name, MenuItem.price,
                    db.func.count(OrderItem.id).label('order_count')
                ).join(OrderItem).join(Category).filter(
                    Category.name == category,
                    MenuItem.price > avg_price * 1.2,  # 20% more expensive
                    MenuItem.is_available == True
                ).group_by(MenuItem.id).order_by(
                    db.desc('order_count')
                ).limit(limit)
                
                for item_id, name, price, order_count in popular_items:
                    popular_upsells.append({
                        'item_id': item_id,
                        'name': name,
                        'price': float(price),
                        'category': category,
                        'recommendation_type': 'popular_upsell',
                        'reason': f"Popular upgrade in {category}",
                        'order_count': order_count,
                        'score': order_count * 0.6  # Weight for popular items
                    })
            
            return popular_upsells[:limit]
            
        except Exception as e:
            self.logger.error(f"Error getting popular upsells: {str(e)}")
            return []
    
    def _get_seasonal_recommendations(self, customer_profile, limit):
        """Get seasonal/trending item recommendations"""
        try:
            current_month = datetime.now().month
            current_hour = datetime.now().hour
            
            # Define seasonal patterns
            seasonal_items = []
            
            # Winter items (Dec-Feb)
            if current_month in [12, 1, 2]:
                seasonal_query = db.session.query(
                    MenuItem.id, MenuItem.name, MenuItem.price,
                    db.func.count(OrderItem.id).label('order_count')
                ).join(OrderItem).join(Category).filter(
                    Category.name.in_(['Hot Beverages', 'Soups', 'Main Course']),
                    MenuItem.is_available == True
                ).group_by(MenuItem.id).order_by(db.desc('order_count')).limit(limit)
            
            # Summer items (Jun-Aug)
            elif current_month in [6, 7, 8]:
                seasonal_query = db.session.query(
                    MenuItem.id, MenuItem.name, MenuItem.price,
                    db.func.count(OrderItem.id).label('order_count')
                ).join(OrderItem).join(Category).filter(
                    Category.name.in_(['Cold Beverages', 'Salads', 'Desserts']),
                    MenuItem.is_available == True
                ).group_by(MenuItem.id).order_by(db.desc('order_count')).limit(limit)
            
            # Default to all-time popular
            else:
                seasonal_query = db.session.query(
                    MenuItem.id, MenuItem.name, MenuItem.price,
                    db.func.count(OrderItem.id).label('order_count')
                ).join(OrderItem).filter(
                    MenuItem.is_available == True
                ).group_by(MenuItem.id).order_by(db.desc('order_count')).limit(limit)
            
            for item_id, name, price, order_count in seasonal_query:
                seasonal_items.append({
                    'item_id': item_id,
                    'name': name,
                    'price': float(price),
                    'recommendation_type': 'seasonal',
                    'reason': f"Trending item for this season",
                    'order_count': order_count,
                    'score': order_count * 0.4  # Weight for seasonal items
                })
            
            return seasonal_items
            
        except Exception as e:
            self.logger.error(f"Error getting seasonal recommendations: {str(e)}")
            return []
    
    def _score_recommendations(self, recommendations, customer_profile, cart_analysis):
        """Score and rank recommendations based on multiple factors"""
        try:
            for rec in recommendations:
                base_score = rec.get('score', 1.0)
                
                # Customer preference bonus
                if customer_profile:
                    favorite_categories = customer_profile.get('favorite_categories', [])
                    if rec.get('category') in favorite_categories:
                        base_score *= 1.5
                    
                    # Price preference alignment
                    preferred_range = customer_profile.get('preferred_price_range', {})
                    min_price = preferred_range.get('min', 0)
                    max_price = preferred_range.get('max', 1000)
                    item_price = rec.get('price', 0)
                    
                    if min_price <= item_price <= max_price:
                        base_score *= 1.2
                
                # Cart compatibility bonus
                if cart_analysis:
                    # Avoid recommending items from already represented categories
                    if rec.get('category') not in cart_analysis.get('categories', []):
                        base_score *= 1.3
                    
                    # Price progression bonus (gradually increase price)
                    avg_cart_price = cart_analysis.get('avg_price', 0)
                    item_price = rec.get('price', 0)
                    
                    if avg_cart_price * 1.1 <= item_price <= avg_cart_price * 2.0:
                        base_score *= 1.1
                
                # Time-based adjustments
                current_hour = datetime.now().hour
                if 11 <= current_hour <= 14:  # Lunch hours
                    if 'lunch' in rec.get('name', '').lower() or 'combo' in rec.get('name', '').lower():
                        base_score *= 1.2
                elif 17 <= current_hour <= 21:  # Dinner hours
                    if 'dinner' in rec.get('name', '').lower() or 'special' in rec.get('name', '').lower():
                        base_score *= 1.2
                
                rec['final_score'] = base_score
                
            return recommendations
            
        except Exception as e:
            self.logger.error(f"Error scoring recommendations: {str(e)}")
            return recommendations
    
    def _apply_business_rules(self, recommendations, customer_id, user_id):
        """Apply business rules to filter recommendations"""
        try:
            filtered_recommendations = []
            
            for rec in recommendations:
                # Check item availability
                menu_item = MenuItem.query.get(rec.get('item_id'))
                if not menu_item or not menu_item.is_available:
                    continue
                
                # Check inventory for ingredients
                if not self._check_item_availability(rec.get('item_id')):
                    continue
                
                # Apply maximum price increase rules
                current_items = rec.get('current_items', [])
                if current_items:
                    max_increase = 2.5  # Maximum 2.5x increase
                    avg_current_price = np.mean([item.get('price', 0) for item in current_items])
                    
                    if rec.get('price', 0) > avg_current_price * max_increase:
                        continue
                
                # Customer-specific rules
                if customer_id:
                    customer = Customer.query.get(customer_id)
                    if customer and hasattr(customer, 'preferences'):
                        # Check for dietary restrictions
                        restrictions = customer.preferences.get('dietary_restrictions', [])
                        if any(restriction in menu_item.name.lower() for restriction in restrictions):
                            continue
                
                filtered_recommendations.append(rec)
            
            return filtered_recommendations
            
        except Exception as e:
            self.logger.error(f"Error applying business rules: {str(e)}")
            return recommendations
    
    def _check_item_availability(self, item_id):
        """Check if item can be made based on ingredient availability"""
        try:
            from app.models.inventory import MenuItemIngredient, Ingredient
            
            # Get ingredients for the item
            ingredients = db.session.query(
                Ingredient.id, Ingredient.name, Ingredient.current_stock,
                MenuItemIngredient.quantity
            ).join(MenuItemIngredient).join(Ingredient).filter(
                MenuItemIngredient.menu_item_id == item_id
            ).all()
            
            # Check if all ingredients are available
            for ingredient_id, name, stock, required_qty in ingredients:
                if stock < required_qty:
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking item availability: {str(e)}")
            return True  # Default to available if error
    
    def _get_favorite_categories(self, orders):
        """Extract customer's favorite categories from order history"""
        category_counts = Counter()
        for order in orders:
            for item in order.items:
                if item.menu_item and item.menu_item.category:
                    category_counts[item.menu_item.category.name] += 1
        
        # Return top 3 categories
        return [cat for cat, _ in category_counts.most_common(3)]
    
    def _calculate_order_frequency(self, orders):
        """Calculate how often customer orders"""
        if not orders:
            return 0
            
        dates = [order.created_at.date() for order in orders]
        unique_days = len(set(dates))
        total_days = (max(dates) - min(dates)).days + 1 if len(dates) > 1 else 1
        
        return unique_days / total_days if total_days > 0 else 0
    
    def _get_price_preference(self, orders):
        """Calculate customer's preferred price range"""
        if not orders:
            return {'min': 0, 'max': 1000}
            
        prices = []
        for order in orders:
            for item in order.items:
                if item.menu_item:
                    prices.append(float(item.menu_item.price))
        
        if not prices:
            return {'min': 0, 'max': 1000}
            
        return {
            'min': np.percentile(prices, 25),
            'max': np.percentile(prices, 75)
        }
    
    def log_recommendation(self, user_id, customer_id, recommendations, order_id=None):
        """Log recommendations for analytics and model improvement"""
        try:
            for rec in recommendations:
                log_entry = AIRecommendation(
                    recommendation_type=rec.get('recommendation_type'),
                    source_model_id=self.model.id if self.model else None,
                    target_customer_id=customer_id,
                    target_user_id=user_id,
                    order_id=order_id,
                    item_id=rec.get('item_id'),
                    recommended_items={'item_id': rec.get('item_id'), 'metadata': rec},
                    confidence_score=rec.get('final_score', rec.get('score', 0)),
                    reasoning=rec.get('reason'),
                    status='pending'
                )
                db.session.add(log_entry)
            
            db.session.commit()
            
        except Exception as e:
            self.logger.error(f"Error logging recommendations: {str(e)}")
            db.session.rollback()