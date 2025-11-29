"""
AI Dynamic Pricing Service
Provides intelligent pricing adjustments based on:
- Demand patterns
- Time of day
- Inventory levels
- Competitor pricing
- Weather conditions
- Events and special occasions
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestRegressor
import json
import logging
import requests

from app import db
from app.models.menu import MenuItem, Category
from app.models.order import Order, OrderItem
from app.models.inventory import Ingredient
from app.models.ai_models import AIModel, AIPriceOptimization, AIPredictionLog
from app.models.user import User


class DynamicPricingService:
    """AI-powered dynamic pricing engine"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.model = None
        self.scaler = None
        self.load_models()
    
    def load_models(self):
        """Load trained pricing models"""
        try:
            # Get active pricing model
            active_model = AIModel.query.filter_by(
                model_type='pricing', 
                is_active=True, 
                is_production=True
            ).first()
            
            if active_model:
                # In a real implementation, load the actual ML model
                # self.model = joblib.load(active_model.model_path)
                # self.scaler = joblib.load(active_model.metadata_path)
                self.logger.info(f"Loaded pricing model: {active_model.name}")
            else:
                self.logger.warning("No active pricing model found")
                
        except Exception as e:
            self.logger.error(f"Error loading pricing model: {str(e)}")
    
    def calculate_optimal_price(self, item_id, context=None):
        """
        Calculate optimal price for an item based on various factors
        
        Args:
            item_id: ID of the menu item
            context: Dictionary containing context (time, weather, demand, etc.)
            
        Returns:
            Dictionary with optimal price and factors
        """
        try:
            menu_item = MenuItem.query.get(item_id)
            if not menu_item:
                return None
            
            # Get base price
            base_price = float(menu_item.price)
            
            # Calculate pricing factors
            factors = self._calculate_pricing_factors(item_id, context)
            
            # Apply ML model if available
            if self.model:
                ml_price = self._predict_with_model(item_id, factors)
                if ml_price:
                    base_price = ml_price
            
            # Apply business rules and constraints
            optimized_price = self._apply_pricing_constraints(
                base_price, factors, menu_item
            )
            
            # Calculate confidence score
            confidence = self._calculate_price_confidence(factors)
            
            result = {
                'item_id': item_id,
                'item_name': menu_item.name,
                'base_price': base_price,
                'optimized_price': optimized_price,
                'price_change_percent': ((optimized_price - base_price) / base_price) * 100,
                'factors': factors,
                'confidence_score': confidence,
                'reasoning': self._generate_pricing_reasoning(factors, optimized_price, base_price)
            }
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error calculating optimal price: {str(e)}")
            return None
    
    def _calculate_pricing_factors(self, item_id, context=None):
        """Calculate various pricing factors"""
        try:
            factors = {}
            current_time = datetime.now()
            
            # Time-based factors
            factors['time_factor'] = self._get_time_factor(current_time)
            factors['day_factor'] = self._get_day_factor(current_time)
            
            # Demand-based factors
            factors['demand_factor'] = self._get_demand_factor(item_id, current_time)
            
            # Inventory-based factors
            factors['inventory_factor'] = self._get_inventory_factor(item_id)
            
            # Weather-based factors
            factors['weather_factor'] = self._get_weather_factor(context)
            
            # Event-based factors
            factors['event_factor'] = self._get_event_factor(context)
            
            # Competitor-based factors
            factors['competitor_factor'] = self._get_competitor_factor(item_id)
            
            # Historical performance factors
            factors['performance_factor'] = self._get_performance_factor(item_id)
            
            return factors
            
        except Exception as e:
            self.logger.error(f"Error calculating pricing factors: {str(e)}")
            return {}
    
    def _get_time_factor(self, current_time):
        """Calculate time-based pricing factor"""
        hour = current_time.hour
        
        # Peak hours pricing
        if 11 <= hour <= 14:  # Lunch peak
            return 1.15
        elif 18 <= hour <= 21:  # Dinner peak
            return 1.20
        elif 22 <= hour <= 23:  # Late night
            return 1.10
        else:  # Off-peak
            return 1.0
    
    def _get_day_factor(self, current_time):
        """Calculate day-based pricing factor"""
        day_of_week = current_time.weekday()
        
        # Weekend premium
        if day_of_week >= 5:  # Friday, Saturday, Sunday
            return 1.12
        elif day_of_week == 3:  # Wednesday (often slower day)
            return 0.95  # Discount to boost sales
        else:
            return 1.0
    
    def _get_demand_factor(self, item_id, current_time):
        """Calculate demand-based pricing factor"""
        try:
            # Get recent orders for this item
            recent_orders = db.session.query(
                db.func.count(OrderItem.id).label('order_count')
            ).join(Order).filter(
                OrderItem.menu_item_id == item_id,
                Order.created_at >= current_time - timedelta(days=7)
            ).scalar() or 0
            
            # Get historical average for comparison
            historical_avg = db.session.query(
                db.func.count(OrderItem.id).label('order_count')
            ).join(Order).filter(
                OrderItem.menu_item_id == item_id,
                Order.created_at >= current_time - timedelta(days=30)
            ).scalar() or 0
            
            # Calculate demand multiplier
            if historical_avg > 0:
                demand_ratio = recent_orders / historical_avg
                if demand_ratio > 1.5:  # High demand
                    return 1.25
                elif demand_ratio > 1.2:  # Moderate demand
                    return 1.15
                elif demand_ratio < 0.7:  # Low demand
                    return 0.90
            
            return 1.0
            
        except Exception as e:
            self.logger.error(f"Error calculating demand factor: {str(e)}")
            return 1.0
    
    def _get_inventory_factor(self, item_id):
        """Calculate inventory-based pricing factor"""
        try:
            # Get ingredients for the item
            from app.models.inventory import MenuItemIngredient
            
            ingredients = db.session.query(
                Ingredient.current_stock,
                MenuItemIngredient.quantity,
                Ingredient.minimum_stock
            ).join(MenuItemIngredient).join(Ingredient).filter(
                MenuItemIngredient.menu_item_id == item_id
            ).all()
            
            if not ingredients:
                return 1.0
            
            # Calculate stock levels
            stock_ratios = []
            for current_stock, required_qty, min_stock in ingredients:
                if required_qty > 0:
                    ratio = current_stock / required_qty
                    stock_ratios.append(ratio)
            
            if not stock_ratios:
                return 1.0
            
            avg_stock_ratio = np.mean(stock_ratios)
            
            # Apply pricing based on inventory
            if avg_stock_ratio > 2.0:  # Excess inventory
                return 0.85  # Discount to move inventory
            elif avg_stock_ratio < 0.5:  # Low inventory
                return 1.30  # Premium pricing for scarcity
            elif avg_stock_ratio < 1.0:  # Moderate shortage
                return 1.15
            
            return 1.0
            
        except Exception as e:
            self.logger.error(f"Error calculating inventory factor: {str(e)}")
            return 1.0
    
    def _get_weather_factor(self, context):
        """Calculate weather-based pricing factor"""
        try:
            if not context or not context.get('weather'):
                return 1.0
            
            weather = context.get('weather', {})
            condition = weather.get('condition', '').lower()
            temperature = weather.get('temperature', 20)
            
            # Hot weather - increase cold beverage prices
            if temperature > 30 and 'hot' in condition:
                return 1.20
            elif temperature > 30 and 'cold' in condition:
                return 0.90
            
            # Rainy weather - increase comfort food prices
            if 'rain' in condition:
                return 1.15
            
            # Special conditions
            if 'storm' in condition:
                return 1.10  # Slight increase due to potential delivery issues
            
            return 1.0
            
        except Exception as e:
            self.logger.error(f"Error calculating weather factor: {str(e)}")
            return 1.0
    
    def _get_event_factor(self, context):
        """Calculate event-based pricing factor"""
        try:
            if not context or not context.get('events'):
                return 1.0
            
            events = context.get('events', [])
            total_factor = 1.0
            
            for event in events:
                event_type = event.get('type', '').lower()
                impact = event.get('impact', 'medium').lower()
                
                if event_type == 'holiday':
                    if impact == 'high':
                        total_factor *= 1.25
                    elif impact == 'medium':
                        total_factor *= 1.15
                    else:
                        total_factor *= 1.10
                
                elif event_type == 'local_event':
                    if impact == 'high':
                        total_factor *= 1.20
                    elif impact == 'medium':
                        total_factor *= 1.10
                
                elif event_type == 'sports_event':
                    total_factor *= 1.15
            
            return total_factor
            
        except Exception as e:
            self.logger.error(f"Error calculating event factor: {str(e)}")
            return 1.0
    
    def _get_competitor_factor(self, item_id):
        """Calculate competitor-based pricing factor"""
        try:
            # In a real implementation, this would integrate with competitor pricing APIs
            # For now, simulate competitor analysis
            
            menu_item = MenuItem.query.get(item_id)
            if not menu_item:
                return 1.0
            
            # Simulate competitor price comparison
            base_price = float(menu_item.price)
            
            # Simulate finding lower competitor prices (30% chance)
            import random
            if random.random() < 0.3:
                competitor_price = base_price * 0.9  # Competitor is 10% cheaper
                return 0.95  # Adjust our price to be competitive
            elif random.random() < 0.2:
                competitor_price = base_price * 1.1  # Competitor is 10% more expensive
                return 1.05  # Slight premium
            
            return 1.0
            
        except Exception as e:
            self.logger.error(f"Error calculating competitor factor: {str(e)}")
            return 1.0
    
    def _get_performance_factor(self, item_id):
        """Calculate performance-based pricing factor"""
        try:
            # Get item performance metrics
            recent_orders = db.session.query(
                OrderItem.id,
                Order.created_at,
                Order.total_amount
            ).join(Order).filter(
                OrderItem.menu_item_id == item_id,
                Order.created_at >= datetime.now() - timedelta(days=30)
            ).all()
            
            if not recent_orders:
                return 1.0
            
            # Calculate performance metrics
            total_orders = len(recent_orders)
            avg_rating = 4.0  # Default rating
            
            # Calculate customer satisfaction (if rating data available)
            # This would come from customer feedback in a real implementation
            
            # Performance factor based on popularity and satisfaction
            if total_orders > 100 and avg_rating > 4.5:
                return 1.20  # Popular and well-liked
            elif total_orders > 50:
                return 1.10  # Moderately popular
            elif total_orders < 10:
                return 0.90  # Unpopular - discount to boost sales
            
            return 1.0
            
        except Exception as e:
            self.logger.error(f"Error calculating performance factor: {str(e)}")
            return 1.0
    
    def _predict_with_model(self, item_id, factors):
        """Use ML model to predict optimal price"""
        try:
            if not self.model:
                return None
            
            # Prepare features for model prediction
            features = [
                factors.get('time_factor', 1.0),
                factors.get('day_factor', 1.0),
                factors.get('demand_factor', 1.0),
                factors.get('inventory_factor', 1.0),
                factors.get('weather_factor', 1.0),
                factors.get('event_factor', 1.0),
                factors.get('competitor_factor', 1.0),
                factors.get('performance_factor', 1.0)
            ]
            
            # Scale features
            if self.scaler:
                features = self.scaler.transform([features])
            
            # Make prediction
            predicted_price = self.model.predict(features)[0]
            
            return predicted_price
            
        except Exception as e:
            self.logger.error(f"Error predicting with model: {str(e)}")
            return None
    
    def _apply_pricing_constraints(self, base_price, factors, menu_item):
        """Apply business constraints to pricing"""
        try:
            # Calculate combined multiplier
            multiplier = (
                factors.get('time_factor', 1.0) *
                factors.get('day_factor', 1.0) *
                factors.get('demand_factor', 1.0) *
                factors.get('inventory_factor', 1.0) *
                factors.get('weather_factor', 1.0) *
                factors.get('event_factor', 1.0) *
                factors.get('competitor_factor', 1.0) *
                factors.get('performance_factor', 1.0)
            )
            
            # Apply business constraints
            max_multiplier = 2.5  # Maximum 150% increase
            min_multiplier = 0.7   # Maximum 30% decrease
            
            multiplier = max(min_multiplier, min(max_multiplier, multiplier))
            
            # Apply category-specific constraints
            category_name = menu_item.category.name.lower() if menu_item.category else ''
            
            # Essential items have lower maximum
            if 'beverage' in category_name:
                max_multiplier = 1.5
            elif 'essential' in category_name:
                max_multiplier = 1.3
            
            multiplier = min(max_multiplier, multiplier)
            
            # Calculate final price
            optimized_price = base_price * multiplier
            
            # Round to appropriate precision
            optimized_price = round(optimized_price, 2)
            
            return optimized_price
            
        except Exception as e:
            self.logger.error(f"Error applying pricing constraints: {str(e)}")
            return base_price
    
    def _calculate_price_confidence(self, factors):
        """Calculate confidence score for price prediction"""
        try:
            # Base confidence on factor variance
            factor_values = [
                factors.get('time_factor', 1.0),
                factors.get('day_factor', 1.0),
                factors.get('demand_factor', 1.0),
                factors.get('inventory_factor', 1.0),
                factors.get('weather_factor', 1.0),
                factors.get('event_factor', 1.0),
                factors.get('competitor_factor', 1.0),
                factors.get('performance_factor', 1.0)
            ]
            
            # Calculate variance (higher variance = lower confidence)
            variance = np.var(factor_values)
            
            # Base confidence
            base_confidence = 0.8
            
            # Adjust based on variance
            if variance < 0.1:
                confidence = base_confidence + 0.2
            elif variance < 0.3:
                confidence = base_confidence + 0.1
            elif variance < 0.5:
                confidence = base_confidence
            else:
                confidence = base_confidence - 0.1
            
            # Ensure confidence is within bounds
            confidence = max(0.3, min(1.0, confidence))
            
            return confidence
            
        except Exception as e:
            self.logger.error(f"Error calculating price confidence: {str(e)}")
            return 0.5
    
    def _generate_pricing_reasoning(self, factors, optimized_price, base_price):
        """Generate human-readable reasoning for price change"""
        try:
            reasons = []
            
            change_percent = ((optimized_price - base_price) / base_price) * 100
            
            if abs(change_percent) < 1:
                return "Price maintained at optimal level"
            
            # Analyze significant factors
            for factor_name, factor_value in factors.items():
                if abs(factor_value - 1.0) > 0.1:  # Significant deviation
                    if factor_name == 'demand_factor':
                        if factor_value > 1.0:
                            reasons.append("High demand detected")
                        else:
                            reasons.append("Low demand - discount applied")
                    elif factor_name == 'time_factor':
                        if factor_value > 1.0:
                            reasons.append("Peak hours pricing")
                    elif factor_name == 'inventory_factor':
                        if factor_value < 1.0:
                            reasons.append("Excess inventory - discount applied")
                        else:
                            reasons.append("Low inventory - premium applied")
                    elif factor_name == 'weather_factor':
                        if factor_value > 1.0:
                            reasons.append("Weather-based price adjustment")
                    elif factor_name == 'event_factor':
                        if factor_value > 1.0:
                            reasons.append("Special event pricing")
            
            if not reasons:
                if change_percent > 0:
                    reasons.append("Multiple factors indicate price increase")
                else:
                    reasons.append("Multiple factors indicate discount")
            
            return "; ".join(reasons)
            
        except Exception as e:
            self.logger.error(f"Error generating pricing reasoning: {str(e)}")
            return "Price optimized based on multiple factors"
    
    def update_item_price(self, item_id, new_price, user_id, reasoning=None):
        """Update item price in the database"""
        try:
            menu_item = MenuItem.query.get(item_id)
            if not menu_item:
                return False
            
            old_price = float(menu_item.price)
            
            # Log the price optimization
            optimization = AIPriceOptimization(
                item_id=item_id,
                source_model_id=self.model.id if self.model else None,
                original_price=old_price,
                optimized_price=new_price,
                optimization_factors=self._calculate_pricing_factors(item_id),
                confidence_score=self._calculate_price_confidence({}),
                is_active=True,
                start_time=datetime.now(),
                created_by=user_id
            )
            
            db.session.add(optimization)
            
            # Update the item price
            menu_item.price = new_price
            db.session.commit()
            
            self.logger.info(f"Updated price for item {item_id}: {old_price} -> {new_price}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error updating item price: {str(e)}")
            db.session.rollback()
            return False
    
    def get_pricing_analytics(self, item_id=None, date_range=None):
        """Get pricing analytics and insights"""
        try:
            query = db.session.query(AIPriceOptimization)
            
            if item_id:
                query = query.filter(AIPriceOptimization.item_id == item_id)
            
            if date_range:
                start_date, end_date = date_range
                query = query.filter(
                    AIPriceOptimization.created_at >= start_date,
                    AIPriceOptimization.created_at <= end_date
                )
            
            optimizations = query.order_by(AIPriceOptimization.created_at.desc()).all()
            
            analytics = {
                'total_optimizations': len(optimizations),
                'avg_price_change': 0,
                'confidence_distribution': {},
                'factor_impact': {},
                'recent_optimizations': []
            }
            
            if optimizations:
                # Calculate average price change
                price_changes = [
                    ((opt.optimized_price - opt.original_price) / opt.original_price) * 100
                    for opt in optimizations
                ]
                analytics['avg_price_change'] = np.mean(price_changes)
                
                # Analyze confidence distribution
                confidences = [opt.confidence_score for opt in optimizations]
                analytics['confidence_distribution'] = {
                    'high': len([c for c in confidences if c > 0.8]),
                    'medium': len([c for c in confidences if 0.5 <= c <= 0.8]),
                    'low': len([c for c in confidences if c < 0.5])
                }
                
                # Factor impact analysis
                for opt in optimizations[-10:]:  # Last 10 optimizations
                    factors = opt.optimization_factors or {}
                    for factor_name, factor_value in factors.items():
                        if factor_name not in analytics['factor_impact']:
                            analytics['factor_impact'][factor_name] = []
                        analytics['factor_impact'][factor_name].append(factor_value)
                
                # Recent optimizations
                analytics['recent_optimizations'] = [
                    {
                        'item_id': opt.item_id,
                        'item_name': opt.item.name if opt.item else 'Unknown',
                        'original_price': float(opt.original_price),
                        'optimized_price': float(opt.optimized_price),
                        'change_percent': ((opt.optimized_price - opt.original_price) / opt.original_price) * 100,
                        'confidence': opt.confidence_score,
                        'created_at': opt.created_at.isoformat()
                    }
                    for opt in optimizations[:5]
                ]
            
            return analytics
            
        except Exception as e:
            self.logger.error(f"Error getting pricing analytics: {str(e)}")
            return {}