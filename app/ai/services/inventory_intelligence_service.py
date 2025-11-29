"""
AI Inventory Intelligence Service
Provides intelligent inventory management including:
- Stock level predictions
- Automated purchase order generation
- Spoilage prediction and prevention
- Cost optimization recommendations
- Supplier performance analysis
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
import json
import logging

from app import db
from app.models.inventory import Ingredient, StockAdjustment, MenuItemIngredient
from app.models.order import Order, OrderItem
# from app.models.purchase import PurchaseOrder, PurchaseOrderItem  # Models not implemented yet
from app.models.ai_models import AIModel, AIInventoryPrediction, AIPredictionLog


class InventoryIntelligenceService:
    """AI-powered inventory management system"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.models = {}
        self.scalers = {}
        self._models_loaded = False
    
    def load_models(self):
        """Load trained inventory models"""
        try:
            # Get active inventory models
            active_models = AIModel.query.filter_by(
                model_type='inventory', 
                is_active=True, 
                is_production=True
            ).all()
            
            for model in active_models:
                # In a real implementation, load the actual ML models
                # self.models[model.algorithm] = joblib.load(model.model_path)
                # self.scalers[model.algorithm] = joblib.load(model.metadata_path)
                self.logger.info(f"Loaded inventory model: {model.name}")
                
        except Exception as e:
            self.logger.error(f"Error loading inventory models: {str(e)}")
    
    def predict_stock_levels(self, days_ahead=30, ingredient_id=None):
        """
        Predict stock levels for ingredients
        
        Args:
            days_ahead: Number of days to predict
            ingredient_id: Optional specific ingredient
            
        Returns:
            Dictionary with stock predictions and recommendations
        """
        try:
            self._ensure_models_loaded()
            if ingredient_id:
                # Predict for specific ingredient
                prediction = self._predict_ingredient_stock(ingredient_id, days_ahead)
                return {'ingredient_predictions': [prediction]}
            else:
                # Predict for all ingredients
                ingredients = Ingredient.query.filter(Ingredient.is_active == True).all()
                predictions = []
                
                for ingredient in ingredients:
                    prediction = self._predict_ingredient_stock(ingredient.id, days_ahead)
                    predictions.append(prediction)
                
                return {'ingredient_predictions': predictions}
                
        except Exception as e:
            self.logger.error(f"Error predicting stock levels: {str(e)}")
            return {'error': str(e)}
    
    def predict_spoilage(self, days_ahead=14, ingredient_id=None):
        """
        Predict potential spoilage for ingredients
        
        Args:
            days_ahead: Prediction horizon
            ingredient_id: Optional specific ingredient
            
        Returns:
            Dictionary with spoilage predictions and alerts
        """
        try:
            self._ensure_models_loaded()
            spoilage_predictions = []
            
            if ingredient_id:
                # Predict for specific ingredient
                prediction = self._predict_ingredient_spoilage(ingredient_id, days_ahead)
                spoilage_predictions.append(prediction)
            else:
                # Predict for perishable ingredients
                ingredients = Ingredient.query.filter(
                    Ingredient.is_active == True,
                    Ingredient.perishable == True
                ).all()
                
                for ingredient in ingredients:
                    prediction = self._predict_ingredient_spoilage(ingredient.id, days_ahead)
                    spoilage_predictions.append(prediction)
            
            return {
                'spoilage_predictions': spoilage_predictions,
                'total_waste_value': sum(p.get('estimated_loss', 0) for p in spoilage_predictions),
                'high_risk_items': [p for p in spoilage_predictions if p.get('risk_level') == 'high']
            }
            
        except Exception as e:
            self.logger.error(f"Error predicting spoilage: {str(e)}")
            return {'error': str(e)}
    
    def generate_purchase_orders(self, supplier_id=None, days_ahead=30):
        """
        Generate automated purchase order recommendations
        
        Args:
            supplier_id: Optional supplier filter
            days_ahead: Planning horizon
            
        Returns:
            Dictionary with purchase order recommendations
        """
        try:
            self._ensure_models_loaded()
            # Get stock predictions
            stock_predictions = self.predict_stock_levels(days_ahead)
            
            # Analyze current inventory and predicted needs
            purchase_recommendations = []
            
            for pred in stock_predictions.get('ingredient_predictions', []):
                ingredient_id = pred.get('ingredient_id')
                if not ingredient_id:
                    continue
                
                ingredient = Ingredient.query.get(ingredient_id)
                if not ingredient:
                    continue
                
                # Calculate reorder requirements
                reorder_analysis = self._calculate_reorder_requirements(ingredient, pred)
                
                if reorder_analysis.get('should_reorder', False):
                    # Find best supplier
                    best_supplier = self._find_best_supplier(ingredient, supplier_id)
                    
                    if best_supplier:
                        purchase_recommendations.append({
                            'ingredient_id': ingredient_id,
                            'ingredient_name': ingredient.name,
                            'current_stock': pred.get('current_stock', 0),
                            'predicted_min_stock': pred.get('min_predicted_stock', 0),
                            'recommended_quantity': reorder_analysis.get('recommended_quantity', 0),
                            'estimated_cost': reorder_analysis.get('estimated_cost', 0),
                            'urgency': reorder_analysis.get('urgency', 'normal'),
                            'best_supplier': best_supplier,
                            'order_date': reorder_analysis.get('order_date'),
                            'confidence': pred.get('confidence', 0.5)
                        })
            
            # Group by supplier for efficiency
            supplier_groups = {}
            for rec in purchase_recommendations:
                supplier_id = rec['best_supplier'].get('id')
                if supplier_id not in supplier_groups:
                    supplier_groups[supplier_id] = {
                        'supplier': rec['best_supplier'],
                        'items': [],
                        'total_cost': 0
                    }
                supplier_groups[supplier_id]['items'].append(rec)
                supplier_groups[supplier_id]['total_cost'] += rec['estimated_cost']
            
            return {
                'purchase_recommendations': purchase_recommendations,
                'supplier_groups': supplier_groups,
                'total_estimated_cost': sum(rec['estimated_cost'] for rec in purchase_recommendations),
                'urgent_orders': [rec for rec in purchase_recommendations if rec['urgency'] == 'urgent']
            }
            
        except Exception as e:
            self.logger.error(f"Error generating purchase orders: {str(e)}")
            return {'error': str(e)}
    
    def optimize_costs(self, ingredient_id=None):
        """
        Provide cost optimization recommendations
        
        Args:
            ingredient_id: Optional specific ingredient
            
        Returns:
            Dictionary with cost optimization recommendations
        """
        try:
            self._ensure_models_loaded()
            optimization_recommendations = []
            
            if ingredient_id:
                # Optimize for specific ingredient
                recommendation = self._optimize_ingredient_cost(ingredient_id)
                optimization_recommendations.append(recommendation)
            else:
                # Optimize for high-cost ingredients
                ingredients = db.session.query(
                    Ingredient, StockAdjustment
                ).join(StockAdjustment).filter(
                    Ingredient.is_active == True
                ).order_by(
                    db.desc(StockAdjustment.unit_cost)
                ).limit(20).all()
                
                for ingredient, _ in ingredients:
                    recommendation = self._optimize_ingredient_cost(ingredient.id)
                    optimization_recommendations.append(recommendation)
            
            return {
                'optimization_recommendations': optimization_recommendations,
                'potential_savings': sum(rec.get('potential_savings', 0) for rec in optimization_recommendations),
                'implementation_priority': sorted(optimization_recommendations, 
                                         key=lambda x: x.get('potential_savings', 0), 
                                         reverse=True)
            }
            
        except Exception as e:
            self.logger.error(f"Error optimizing costs: {str(e)}")
            return {'error': str(e)}
    
    def analyze_supplier_performance(self, days_back=90):
        """
        Analyze supplier performance metrics
        
        Args:
            days_back: Analysis period
            
        Returns:
            Dictionary with supplier performance analysis
        """
        try:
            # Get purchase orders within analysis period
            start_date = datetime.now() - timedelta(days=days_back)
            
            # PurchaseOrder model not implemented yet - skipping supplier performance analysis
            return {'error': 'PurchaseOrder model not implemented'}
            
            supplier_analysis = {}
            
            # Group by supplier
            for po in purchase_orders:
                supplier_id = po.supplier_id if hasattr(po, 'supplier_id') else None
                if not supplier_id:
                    continue
                
                if supplier_id not in supplier_analysis:
                    supplier_analysis[supplier_id] = {
                        'supplier_id': supplier_id,
                        'supplier_name': getattr(po, 'supplier_name', 'Unknown'),
                        'total_orders': 0,
                        'on_time_deliveries': 0,
                        'late_deliveries': 0,
                        'total_cost': 0,
                        'quality_issues': 0,
                        'avg_delivery_time': 0,
                        'performance_score': 0
                    }
                
                # Update supplier metrics
                analysis = supplier_analysis[supplier_id]
                analysis['total_orders'] += 1
                analysis['total_cost'] += po.total_amount or 0
                
                # Check delivery performance
                if hasattr(po, 'delivered_at') and po.delivered_at:
                    expected_delivery = po.expected_delivery_date
                    actual_delivery = po.delivered_at
                    
                    if actual_delivery <= expected_delivery:
                        analysis['on_time_deliveries'] += 1
                    else:
                        analysis['late_deliveries'] += 1
                    
                    delivery_time = (actual_delivery - po.created_at).days
                    analysis['avg_delivery_time'] += delivery_time
                
                # Check quality issues (would come from quality inspections)
                if hasattr(po, 'quality_rating'):
                    if po.quality_rating < 3:  # Assuming 1-5 scale
                        analysis['quality_issues'] += 1
            
            # Calculate performance scores
            for supplier_id, analysis in supplier_analysis.items():
                if analysis['total_orders'] > 0:
                    # On-time delivery rate
                    on_time_rate = analysis['on_time_deliveries'] / analysis['total_orders']
                    
                    # Average delivery time
                    avg_delivery = analysis['avg_delivery_time'] / analysis['total_orders']
                    
                    # Quality score
                    quality_score = max(0, 5 - (analysis['quality_issues'] / analysis['total_orders']))
                    
                    # Overall performance score
                    analysis['performance_score'] = (
                        on_time_rate * 0.4 +  # 40% weight
                        (5 - min(avg_delivery / 7, 5)) * 0.3 +  # 30% weight (inverse of delivery time)
                        quality_score * 0.3  # 30% weight
                    )
                    
                    # Update other metrics
                    analysis['on_time_delivery_rate'] = on_time_rate
                    analysis['avg_delivery_time_days'] = avg_delivery
                    analysis['quality_score'] = quality_score
            
            # Rank suppliers
            ranked_suppliers = sorted(
                supplier_analysis.values(),
                key=lambda x: x['performance_score'],
                reverse=True
            )
            
            return {
                'supplier_analysis': supplier_analysis,
                'ranked_suppliers': ranked_suppliers,
                'top_performers': ranked_suppliers[:5],
                'needs_improvement': [s for s in ranked_suppliers if s['performance_score'] < 3.0]
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing supplier performance: {str(e)}")
            return {'error': str(e)}
    
    def _predict_ingredient_stock(self, ingredient_id, days_ahead):
        """Predict stock levels for a specific ingredient"""
        try:
            ingredient = Ingredient.query.get(ingredient_id)
            if not ingredient:
                return {}
            
            # Get historical usage data
            usage_data = self._get_ingredient_usage_history(ingredient_id)
            
            if len(usage_data) < 7:
                return {
                    'ingredient_id': ingredient_id,
                    'current_stock': ingredient.current_stock,
                    'min_stock': ingredient.minimum_stock,
                    'confidence': 0.3,
                    'error': 'Insufficient historical data'
                }
            
            # Calculate daily usage pattern
            daily_usage = self._calculate_daily_usage_pattern(usage_data)
            
            # Predict future usage
            predicted_usage = []
            for i in range(days_ahead):
                # Consider day of week and seasonality
                day_factor = self._get_day_usage_factor(i)
                predicted_daily = daily_usage * day_factor
                predicted_usage.append(predicted_daily)
            
            # Calculate predicted stock levels
            current_stock = ingredient.current_stock
            predicted_stocks = []
            
            for i, daily_usage in enumerate(predicted_usage):
                predicted_stock = max(0, current_stock - sum(predicted_usage[:i+1]))
                predicted_stocks.append(predicted_stock)
            
            # Find minimum stock and alert point
            min_predicted_stock = min(predicted_stocks)
            alert_threshold = ingredient.minimum_stock * 1.2
            
            return {
                'ingredient_id': ingredient_id,
                'ingredient_name': ingredient.name,
                'current_stock': current_stock,
                'predicted_daily_usage': predicted_usage,
                'predicted_stocks': predicted_stocks,
                'min_predicted_stock': min_predicted_stock,
                'alert_threshold': alert_threshold,
                'confidence': 0.8,
                'days_until_shortage': next(((i, stock) for i, stock in enumerate(predicted_stocks)
                                       if stock < alert_threshold), (None, None)),
                'is_alert': min_predicted_stock < alert_threshold
            }
            
        except Exception as e:
            self.logger.error(f"Error predicting ingredient stock: {str(e)}")
            return {}
    
    def _predict_ingredient_spoilage(self, ingredient_id, days_ahead):
        """Predict spoilage for an ingredient"""
        try:
            ingredient = Ingredient.query.get(ingredient_id)
            if not ingredient:
                return {}
            
            if not ingredient.perishable:
                return {
                    'ingredient_id': ingredient_id,
                    'spoilage_risk': 'low',
                    'confidence': 0.9
                }
            
            # Get historical spoilage data
            spoilage_data = self._get_spoilage_history(ingredient_id)
            
            if len(spoilage_data) < 5:
                return {
                    'ingredient_id': ingredient_id,
                    'spoilage_risk': 'medium',
                    'confidence': 0.5,
                    'estimated_loss': 0,
                    'reason': 'Insufficient historical data'
                }
            
            # Calculate spoilage rate
            total_usage = sum(s.get('usage', 0) for s in spoilage_data)
            total_spoilage = sum(s.get('spoilage', 0) for s in spoilage_data)
            
            if total_usage > 0:
                spoilage_rate = total_spoilage / total_usage
            else:
                spoilage_rate = 0
            
            # Predict future spoilage based on patterns
            predicted_spoilage = self._predict_future_spoilage(spoilage_data, days_ahead)
            
            # Assess risk level
            risk_level = 'low'
            if spoilage_rate > 0.15:
                risk_level = 'high'
            elif spoilage_rate > 0.08:
                risk_level = 'medium'
            
            estimated_loss = predicted_spoilage * ingredient.unit_cost if hasattr(ingredient, 'unit_cost') else 0
            
            return {
                'ingredient_id': ingredient_id,
                'ingredient_name': ingredient.name,
                'spoilage_rate': spoilage_rate,
                'predicted_spoilage': predicted_spoilage,
                'risk_level': risk_level,
                'estimated_loss': estimated_loss,
                'confidence': 0.7,
                'recommendations': self._generate_spoilage_recommendations(risk_level, ingredient)
            }
            
        except Exception as e:
            self.logger.error(f"Error predicting ingredient spoilage: {str(e)}")
            return {}
    
    def _calculate_reorder_requirements(self, ingredient, stock_prediction):
        """Calculate reorder requirements for an ingredient"""
        try:
            current_stock = stock_prediction.get('current_stock', 0)
            min_predicted_stock = stock_prediction.get('min_predicted_stock', 0)
            days_until_shortage = stock_prediction.get('days_until_shortage', 999)
            
            # Calculate safety stock (2 weeks of usage)
            daily_usage = np.mean(stock_prediction.get('predicted_daily_usage', [0]))
            safety_stock = daily_usage * 14
            
            # Calculate reorder point
            reorder_point = ingredient.minimum_stock + safety_stock
            
            # Determine if reorder is needed
            should_reorder = min_predicted_stock <= reorder_point or days_until_shortage <= 7
            
            if should_reorder:
                # Calculate recommended quantity
                lead_time = getattr(ingredient, 'lead_time_days', 7)  # Default 7 days
                usage_during_lead = daily_usage * lead_time
                recommended_quantity = (reorder_point - current_stock) + usage_during_lead + safety_stock
                
                # Determine urgency
                urgency = 'urgent' if days_until_shortage <= 3 else 'normal'
                
                # Calculate estimated cost
                unit_cost = getattr(ingredient, 'unit_cost', 0)
                estimated_cost = recommended_quantity * unit_cost
                
                # Calculate order date
                order_date = datetime.now() + timedelta(days=1) if urgency == 'normal' else datetime.now()
                
                return {
                    'should_reorder': True,
                    'recommended_quantity': recommended_quantity,
                    'urgency': urgency,
                    'order_date': order_date,
                    'estimated_cost': estimated_cost,
                    'reorder_point': reorder_point,
                    'safety_stock': safety_stock
                }
            else:
                return {
                    'should_reorder': False,
                    'recommended_quantity': 0,
                    'urgency': 'none',
                    'order_date': None,
                    'estimated_cost': 0
                }
                
        except Exception as e:
            self.logger.error(f"Error calculating reorder requirements: {str(e)}")
            return {}
    
    def _find_best_supplier(self, ingredient, supplier_id=None):
        """Find best supplier for an ingredient"""
        try:
            # In a real implementation, this would query supplier database
            # For now, simulate supplier selection
            
            suppliers = [
                {
                    'id': 1,
                    'name': 'Primary Supplier',
                    'unit_cost': getattr(ingredient, 'unit_cost', 0) * 1.0,
                    'lead_time_days': 5,
                    'quality_rating': 4.5,
                    'reliability_score': 4.2
                },
                {
                    'id': 2,
                    'name': 'Backup Supplier',
                    'unit_cost': getattr(ingredient, 'unit_cost', 0) * 1.1,
                    'lead_time_days': 7,
                    'quality_rating': 4.0,
                    'reliability_score': 3.8
                }
            ]
            
            # Filter by supplier_id if specified
            if supplier_id:
                suppliers = [s for s in suppliers if s['id'] == supplier_id]
            
            if not suppliers:
                return None
            
            # Calculate overall score (cost, quality, reliability)
            for supplier in suppliers:
                # Normalize scores (lower cost is better)
                cost_score = max(1, 10 - (supplier['unit_cost'] / getattr(ingredient, 'unit_cost', 1)))
                supplier['overall_score'] = (
                    cost_score * 0.4 +  # 40% weight to cost
                    supplier['quality_rating'] / 5 * 0.3 +  # 30% weight to quality
                    supplier['reliability_score'] / 5 * 0.3   # 30% weight to reliability
                )
            
            # Return best supplier
            best_supplier = max(suppliers, key=lambda x: x['overall_score'])
            return best_supplier
            
        except Exception as e:
            self.logger.error(f"Error finding best supplier: {str(e)}")
            return None
    
    def _optimize_ingredient_cost(self, ingredient_id):
        """Optimize cost for a specific ingredient"""
        try:
            ingredient = Ingredient.query.get(ingredient_id)
            if not ingredient:
                return {}
            
            # Get purchase history
            purchase_history = self._get_purchase_history(ingredient_id)
            
            if len(purchase_history) < 3:
                return {
                    'ingredient_id': ingredient_id,
                    'ingredient_name': ingredient.name,
                    'current_cost': getattr(ingredient, 'unit_cost', 0),
                    'recommendation': 'Insufficient purchase history',
                    'potential_savings': 0
                }
            
            # Analyze cost trends
            costs = [p.get('unit_cost', 0) for p in purchase_history]
            current_cost = getattr(ingredient, 'unit_cost', 0)
            avg_cost = np.mean(costs)
            min_cost = min(costs)
            
            # Calculate potential savings
            potential_savings = (current_cost - min_cost) if current_cost > min_cost else 0
            
            # Generate recommendations
            recommendations = []
            if current_cost > avg_cost * 1.1:
                recommendations.append("Current price is above average - consider negotiation")
            
            recent_trend = 0  # Initialize with default value
            if len(purchase_history) >= 5:
                recent_trend = np.polyfit(range(len(costs[-5:])), costs[-5:], 1)[0]
                cost_trend = 'increasing' if recent_trend > 0 else 'decreasing' if recent_trend < 0 else 'stable'
                if recent_trend > 0:
                    recommendations.append("Prices have been increasing - lock in long-term contract")
            
            return {
                'ingredient_id': ingredient_id,
                'ingredient_name': ingredient.name,
                'current_cost': current_cost,
                'average_cost': avg_cost,
                'min_cost': min_cost,
                'cost_trend': 'increasing' if recent_trend > 0 else 'decreasing' if recent_trend < 0 else 'stable',
                'recommendations': recommendations,
                'potential_savings': potential_savings,
                'confidence': 0.8
            }
            
        except Exception as e:
            self.logger.error(f"Error optimizing ingredient cost: {str(e)}")
            return {}
    
    def _get_ingredient_usage_history(self, ingredient_id):
        """Get ingredient usage history from orders"""
        try:
            # Get usage from order items
            usage_data = db.session.query(
                db.func.date(Order.created_at).label('date'),
                db.func.sum(OrderItem.quantity).label('usage')
            ).join(Order).join(MenuItemIngredient).filter(
                MenuItemIngredient.ingredient_id == ingredient_id,
                Order.created_at >= datetime.now() - timedelta(days=90)
            ).group_by(
                db.func.date(Order.created_at)
            ).order_by(db.func.date(Order.created_at)).all()
            
            return usage_data
            
        except Exception as e:
            self.logger.error(f"Error getting ingredient usage history: {str(e)}")
            return []
    
    def _calculate_daily_usage_pattern(self, usage_data):
        """Calculate daily usage patterns"""
        if not usage_data:
            return 1.0
        
        # Calculate average usage by day of week
        day_patterns = {}
        for date, usage in usage_data:
            if isinstance(date, str):
                date = datetime.strptime(date, '%Y-%m-%d').date()
            day_of_week = date.weekday()
            
            if day_of_week not in day_patterns:
                day_patterns[day_of_week] = []
            day_patterns[day_of_week].append(usage)
        
        # Calculate average for each day
        day_averages = {}
        for day, usages in day_patterns.items():
            day_averages[day] = np.mean(usages) if usages else 0
        
        # Return overall average
        return np.mean(list(day_averages.values())) if day_averages else 1.0
    
    def _get_day_usage_factor(self, days_ahead):
        """Get usage factor for specific day"""
        day_of_week = (datetime.now() + timedelta(days=days_ahead)).weekday()
        
        # Weekend usage is typically higher
        if day_of_week >= 5:  # Friday, Saturday, Sunday
            return 1.3
        elif day_of_week in [1, 2, 3]:  # Monday, Tuesday, Wednesday
            return 1.1
        else:  # Thursday
            return 1.0
    
    def _get_spoilage_history(self, ingredient_id):
        """Get spoilage history for an ingredient"""
        try:
            # In a real implementation, this would query spoilage records
            # For now, simulate based on stock adjustments
            
            # Get stock adjustments that might indicate spoilage
            adjustments = db.session.query(StockAdjustment).filter(
                StockAdjustment.ingredient_id == ingredient_id,
                StockAdjustment.adjustment_type == 'spoilage',
                StockAdjustment.created_at >= datetime.now() - timedelta(days=60)
            ).all()
            
            spoilage_data = []
            for adj in adjustments:
                # Estimate usage based on adjustment quantity
                spoilage_data.append({
                    'date': adj.created_at.date(),
                    'spoilage': abs(adj.quantity),
                    'usage': abs(adj.quantity) * 5  # Estimate usage
                })
            
            return spoilage_data
            
        except Exception as e:
            self.logger.error(f"Error getting spoilage history: {str(e)}")
            return []
    
    def _predict_future_spoilage(self, spoilage_data, days_ahead):
        """Predict future spoilage based on historical patterns"""
        if not spoilage_data:
            return 0
        
        # Calculate average spoilage rate
        total_spoilage = sum(s.get('spoilage', 0) for s in spoilage_data)
        total_usage = sum(s.get('usage', 0) for s in spoilage_data)
        
        if total_usage == 0:
            return 0
        
        spoilage_rate = total_spoilage / total_usage
        
        # Predict future spoilage (considering seasonality)
        current_month = datetime.now().month
        seasonal_factor = 1.0
        
        # Higher spoilage in summer months
        if current_month in [6, 7, 8]:
            seasonal_factor = 1.2
        
        return spoilage_rate * seasonal_factor * days_ahead
    
    def _generate_spoilage_recommendations(self, risk_level, ingredient):
        """Generate recommendations based on spoilage risk"""
        recommendations = []
        
        if risk_level == 'high':
            recommendations.append("Consider reducing order quantity")
            recommendations.append("Implement stricter inventory rotation")
            recommendations.append("Review supplier quality")
        elif risk_level == 'medium':
            recommendations.append("Monitor expiration dates closely")
            recommendations.append("Consider promotional pricing to move inventory faster")
        
        if hasattr(ingredient, 'storage_requirements'):
            storage = ingredient.storage_requirements
            if 'temperature' in storage:
                recommendations.append(f"Maintain storage temperature: {storage['temperature']}")
        
        return recommendations
    
    def _get_purchase_history(self, ingredient_id):
        """Get purchase history for an ingredient"""
        try:
            # In a real implementation, this would query purchase orders
            # For now, simulate from stock adjustments
            
            adjustments = db.session.query(StockAdjustment).filter(
                StockAdjustment.ingredient_id == ingredient_id,
                StockAdjustment.adjustment_type == 'purchase',
                StockAdjustment.created_at >= datetime.now() - timedelta(days=90)
            ).all()
            
            purchase_history = []
            for adj in adjustments:
                purchase_history.append({
                    'date': adj.created_at.date(),
                    'unit_cost': adj.unit_cost or 0,
                    'quantity': adj.quantity
                })
            
            return purchase_history
            
        except Exception as e:
            self.logger.error(f"Error getting purchase history: {str(e)}")
            return []
    
    def log_inventory_prediction(self, prediction_type, ingredient_id, prediction_data, confidence_score):
        """Log inventory predictions for monitoring"""
        try:
            log_entry = AIInventoryPrediction(
                ingredient_id=ingredient_id,
                source_model_id=getattr(self.models.get('inventory'), 'id', None) if 'inventory' in self.models else None,
                prediction_type=prediction_type,
                prediction_date=datetime.now().date(),
                predicted_quantity=prediction_data.get('predicted_quantity', 0),
                confidence_score=confidence_score,
                prediction_factors=prediction_data.get('factors', {}),
                is_alert=prediction_data.get('is_alert', False),
                alert_threshold=prediction_data.get('alert_threshold', 0)
            )
            
            db.session.add(log_entry)
            db.session.commit()
            
        except Exception as e:
            self.logger.error(f"Error logging inventory prediction: {str(e)}")
            db.session.rollback()