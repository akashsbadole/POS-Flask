"""
AI Predictive Analytics Service
Provides predictive insights for:
- Sales forecasting
- Inventory demand prediction
- Staff scheduling optimization
- Customer visit frequency prediction
- Menu item popularity forecasting
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error
import json
import logging

from app import db
from app.models.order import Order, OrderItem
from app.models.menu import MenuItem, Category
from app.models.inventory import Ingredient
from app.models.employee import EmployeeProfile, EmployeeAttendance
from app.models.customer import Customer
from app.models.ai_models import AIModel, AIPredictionLog, AIInventoryPrediction


class PredictiveAnalyticsService:
    """AI-powered predictive analytics engine"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.models = {}
        self.scalers = {}
        self.load_models()
    
    def load_models(self):
        """Load trained prediction models"""
        try:
            # Get all active models
            active_models = AIModel.query.filter_by(is_active=True, is_production=True).all()
            
            for model in active_models:
                # In a real implementation, load the actual ML models
                # self.models[model.model_type] = joblib.load(model.model_path)
                # self.scalers[model.model_type] = joblib.load(model.metadata_path)
                self.logger.info(f"Loaded {model.model_type} model: {model.name}")
                
        except Exception as e:
            self.logger.error(f"Error loading prediction models: {str(e)}")
    
    def forecast_sales(self, days_ahead=7, category_id=None, item_id=None):
        """
        Forecast sales for the next N days
        
        Args:
            days_ahead: Number of days to forecast
            category_id: Optional category filter
            item_id: Optional item filter
            
        Returns:
            Dictionary with forecast data and confidence intervals
        """
        try:
            # Get historical sales data
            historical_data = self._get_sales_history(category_id, item_id)
            
            if len(historical_data) < 14:  # Need at least 2 weeks of data
                return {'error': 'Insufficient historical data'}
            
            # Prepare features for prediction
            X, y = self._prepare_sales_features(historical_data)
            
            # Use appropriate model
            model_type = 'sales_forecast'
            if model_type in self.models:
                model = self.models[model_type]
                scaler = self.scalers.get(model_type)
                
                # Make predictions
                predictions = []
                current_features = X[-1:]  # Use recent features
                
                for i in range(days_ahead):
                    # Update features for next day
                    if i == 0:
                        next_features = current_features
                    else:
                        # In a real implementation, update features based on previous predictions
                        next_features = current_features.copy()
                    
                    # Scale features
                    if scaler:
                        next_features_scaled = scaler.transform([next_features])
                    else:
                        next_features_scaled = [next_features]
                    
                    # Predict
                    pred = model.predict(next_features_scaled)[0]
                    predictions.append(max(0, pred))  # Ensure non-negative
                
                # Calculate confidence intervals
                confidence_intervals = self._calculate_confidence_intervals(predictions, y)
                
                # Generate forecast dates
                forecast_dates = [
                    (datetime.now() + timedelta(days=i+1)).strftime('%Y-%m-%d')
                    for i in range(days_ahead)
                ]
                
                return {
                    'forecast_dates': forecast_dates,
                    'predicted_sales': predictions,
                    'confidence_intervals': confidence_intervals,
                    'historical_accuracy': self._calculate_model_accuracy(y, model.predict(X)),
                    'data_points': len(historical_data)
                }
            else:
                # Fallback to simple trend analysis
                return self._simple_sales_forecast(historical_data, days_ahead)
                
        except Exception as e:
            self.logger.error(f"Error forecasting sales: {str(e)}")
            return {'error': str(e)}
    
    def predict_inventory_demand(self, days_ahead=14, ingredient_id=None):
        """
        Predict inventory demand for ingredients
        
        Args:
            days_ahead: Number of days to predict
            ingredient_id: Optional specific ingredient
            
        Returns:
            Dictionary with demand predictions and alerts
        """
        try:
            # Get historical inventory usage
            historical_usage = self._get_inventory_history(ingredient_id)
            
            if len(historical_usage) < 14:
                return {'error': 'Insufficient historical data'}
            
            # Prepare features for prediction
            X, y = self._prepare_inventory_features(historical_usage)
            
            # Use inventory prediction model
            model_type = 'inventory_demand'
            if model_type in self.models:
                model = self.models[model_type]
                scaler = self.scalers.get(model_type)
                
                # Make predictions
                predictions = []
                current_features = X[-1:] if len(X) > 0 else []
                
                for i in range(days_ahead):
                    if i == 0 and current_features:
                        next_features = current_features
                    else:
                        next_features = self._update_inventory_features(
                            current_features, predictions[-1] if predictions else 0
                        )
                    
                    # Scale and predict
                    if scaler:
                        next_features_scaled = scaler.transform([next_features])
                    else:
                        next_features_scaled = [next_features]
                    
                    pred = model.predict(next_features_scaled)[0]
                    predictions.append(max(0, pred))
                
                # Calculate reorder points and alerts
                alerts = self._calculate_inventory_alerts(predictions, ingredient_id)
                
                return {
                    'prediction_dates': [
                        (datetime.now() + timedelta(days=i+1)).strftime('%Y-%m-%d')
                        for i in range(days_ahead)
                    ],
                    'predicted_demand': predictions,
                    'alerts': alerts,
                    'reorder_recommendations': self._calculate_reorder_points(predictions, ingredient_id),
                    'data_points': len(historical_usage)
                }
            else:
                # Fallback to simple average calculation
                return self._simple_inventory_forecast(historical_usage, days_ahead)
                
        except Exception as e:
            self.logger.error(f"Error predicting inventory demand: {str(e)}")
            return {'error': str(e)}
    
    def optimize_staff_scheduling(self, days_ahead=7, role_id=None):
        """
        Optimize staff scheduling based on predicted demand
        
        Args:
            days_ahead: Number of days to schedule
            role_id: Optional role filter
            
        Returns:
            Dictionary with scheduling recommendations
        """
        try:
            # Get historical sales and staff data
            sales_data = self._get_sales_by_day_of_week()
            staff_data = self._get_staff_availability(role_id)
            
            if len(sales_data) < 7:
                return {'error': 'Insufficient historical data'}
            
            # Predict demand for each day
            daily_demand = self._predict_daily_demand(sales_data, days_ahead)
            
            # Optimize staff allocation
            schedule_recommendations = []
            
            for i, (date, predicted_sales) in enumerate(daily_demand.items()):
                day_name = datetime.strptime(date, '%Y-%m-%d').strftime('%A')
                
                # Calculate required staff based on predicted sales
                required_staff = self._calculate_staff_requirements(predicted_sales, role_id)
                
                # Get available staff for that day
                available_staff = [s for s in staff_data if self._is_staff_available(s, date)]
                
                # Optimize assignment
                optimal_assignment = self._optimize_staff_assignment(
                    required_staff, available_staff
                )
                
                schedule_recommendations.append({
                    'date': date,
                    'day_name': day_name,
                    'predicted_sales': predicted_sales,
                    'required_staff': required_staff,
                    'available_staff': len(available_staff),
                    'optimal_assignment': optimal_assignment,
                    'coverage_score': len(available_staff) / required_staff if required_staff > 0 else 1
                })
            
            return {
                'schedule_recommendations': schedule_recommendations,
                'overall_coverage': np.mean([r['coverage_score'] for r in schedule_recommendations]),
                'peak_days': [r['date'] for r in schedule_recommendations if r['coverage_score'] < 1.0],
                'staff_utilization': self._calculate_staff_utilization(schedule_recommendations)
            }
            
        except Exception as e:
            self.logger.error(f"Error optimizing staff scheduling: {str(e)}")
            return {'error': str(e)}
    
    def predict_customer_visits(self, customer_id=None, days_ahead=30):
        """
        Predict customer visit frequency and next visit date
        
        Args:
            customer_id: Customer to analyze
            days_ahead: Prediction horizon
            
        Returns:
            Dictionary with visit predictions and insights
        """
        try:
            if not customer_id:
                return {'error': 'Customer ID required'}
            
            # Get customer visit history
            visit_history = self._get_customer_visit_history(customer_id)
            
            if len(visit_history) < 5:
                return {'error': 'Insufficient visit history'}
            
            # Analyze visit patterns
            visit_patterns = self._analyze_visit_patterns(visit_history)
            
            # Predict next visits
            next_visits = self._predict_next_visits(visit_patterns, days_ahead)
            
            # Calculate customer metrics
            metrics = {
                'avg_days_between_visits': np.mean([
                    (visit_history[i] - visit_history[i-1]).days
                    for i in range(1, len(visit_history))
                ]) if len(visit_history) > 1 else 0,
                'visit_frequency_score': len(visit_history) / 30,  # Visits per month
                'preferred_days': visit_patterns.get('preferred_days', []),
                'preferred_times': visit_patterns.get('preferred_times', [])
            }
            
            return {
                'customer_id': customer_id,
                'predicted_visits': next_visits,
                'visit_metrics': metrics,
                'loyalty_score': self._calculate_loyalty_score(metrics),
                'churn_risk': self._calculate_churn_risk(visit_patterns),
                'next_visit_probability': self._calculate_visit_probability(visit_patterns)
            }
            
        except Exception as e:
            self.logger.error(f"Error predicting customer visits: {str(e)}")
            return {'error': str(e)}
    
    def forecast_menu_popularity(self, days_ahead=30):
        """
        Forecast menu item popularity trends
        
        Args:
            days_ahead: Number of days to forecast
            
        Returns:
            Dictionary with popularity predictions and trends
        """
        try:
            # Get historical item sales data
            item_sales = self._get_item_sales_history()
            
            if len(item_sales) < 30:
                return {'error': 'Insufficient historical data'}
            
            # Analyze trends and make predictions
            popularity_forecast = []
            
            for item_id, sales_data in item_sales.items():
                # Calculate trend
                trend = self._calculate_sales_trend(sales_data)
                
                # Predict future popularity
                predicted_popularity = self._predict_item_popularity(sales_data, days_ahead)
                
                popularity_forecast.append({
                    'item_id': item_id,
                    'current_trend': trend,
                    'predicted_popularity': predicted_popularity,
                    'trend_direction': 'increasing' if trend > 0 else 'decreasing' if trend < 0 else 'stable',
                    'confidence': self._calculate_popularity_confidence(sales_data)
                })
            
            # Sort by predicted popularity
            popularity_forecast.sort(key=lambda x: x['predicted_popularity'], reverse=True)
            
            return {
                'popularity_forecast': popularity_forecast,
                'trending_items': [p for p in popularity_forecast if p['trend_direction'] == 'increasing'][:10],
                'declining_items': [p for p in popularity_forecast if p['trend_direction'] == 'decreasing'][:10],
                'stable_items': [p for p in popularity_forecast if p['trend_direction'] == 'stable'][:10]
            }
            
        except Exception as e:
            self.logger.error(f"Error forecasting menu popularity: {str(e)}")
            return {'error': str(e)}
    
    def _get_sales_history(self, category_id=None, item_id=None):
        """Get historical sales data for ML training"""
        try:
            query = db.session.query(
                Order.created_at,
                Order.total_amount,
                OrderItem.menu_item_id,
                db.func.count(OrderItem.id).label('item_count'),
                db.func.sum(OrderItem.quantity).label('total_quantity')
            ).join(OrderItem).join(Order)
            
            if item_id:
                query = query.filter(OrderItem.menu_item_id == item_id)
            elif category_id:
                query = query.join(MenuItem).filter(MenuItem.category_id == category_id)
            
            # Get last 90 days of sales
            start_date = datetime.now() - timedelta(days=90)
            query = query.filter(Order.created_at >= start_date)
            
            # Group by day
            daily_sales = query.group_by(
                db.func.date(Order.created_at)
            ).order_by(db.func.date(Order.created_at)).all()
            
            return daily_sales
            
        except Exception as e:
            self.logger.error(f"Error getting sales history: {str(e)}")
            return []
    
    def _prepare_sales_features(self, historical_data):
        """Prepare features for sales forecasting model"""
        try:
            features = []
            targets = []
            
            for i, day_data in enumerate(historical_data):
                # Extract features from date
                date = day_data.created_at.date()
                
                feature_row = [
                    date.day,  # Day of month
                    date.weekday(),  # Day of week
                    date.month,  # Month
                    self._is_holiday(date),  # Holiday indicator
                    self._get_season(date),  # Season
                    len(historical_data) - i,  # Days since start
                ]
                
                features.append(feature_row)
                targets.append(float(day_data.total_amount))
            
            return np.array(features), np.array(targets)
            
        except Exception as e:
            self.logger.error(f"Error preparing sales features: {str(e)}")
            return np.array([]), np.array([])
    
    def _calculate_confidence_intervals(self, predictions, actual_values):
        """Calculate confidence intervals for predictions"""
        try:
            if len(actual_values) < 10:
                # Default confidence intervals
                return {
                    'upper_95': [p * 1.2 for p in predictions],
                    'lower_95': [p * 0.8 for p in predictions],
                    'upper_80': [p * 1.1 for p in predictions],
                    'lower_80': [p * 0.9 for p in predictions]
                }
            
            # Calculate prediction error from historical data
            errors = []
            for i in range(min(len(predictions), len(actual_values))):
                error = abs(predictions[i] - actual_values[i])
                errors.append(error)
            
            if not errors:
                return {'upper_95': [], 'lower_95': [], 'upper_80': [], 'lower_80': []}
            
            # Calculate error statistics
            mean_error = np.mean(errors)
            std_error = np.std(errors)
            
            # Calculate confidence intervals
            return {
                'upper_95': [p + 1.96 * std_error for p in predictions],
                'lower_95': [p - 1.96 * std_error for p in predictions],
                'upper_80': [p + 1.28 * std_error for p in predictions],
                'lower_80': [p - 1.28 * std_error for p in predictions]
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating confidence intervals: {str(e)}")
            return {'upper_95': [], 'lower_95': [], 'upper_80': [], 'lower_80': []}
    
    def _calculate_model_accuracy(self, actual_values, predicted_values):
        """Calculate model accuracy metrics"""
        try:
            if len(actual_values) == 0 or len(predicted_values) == 0:
                return {'mae': 0, 'rmse': 0, 'mape': 0}
            
            mae = mean_absolute_error(actual_values, predicted_values)
            rmse = np.sqrt(mean_squared_error(actual_values, predicted_values))
            
            # Calculate MAPE (Mean Absolute Percentage Error)
            mape = np.mean([
                abs((a - p) / a) * 100 
                for a, p in zip(actual_values, predicted_values) 
                if a != 0
            ]) if any(a != 0 for a in actual_values) else 0
            
            return {
                'mae': mae,
                'rmse': rmse,
                'mape': mape
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating model accuracy: {str(e)}")
            return {'mae': 0, 'rmse': 0, 'mape': 0}
    
    def _simple_sales_forecast(self, historical_data, days_ahead):
        """Simple fallback sales forecast using trend analysis"""
        try:
            if len(historical_data) < 7:
                return {'error': 'Insufficient data for forecast'}
            
            # Calculate simple trend
            recent_sales = [float(d.total_amount) for d in historical_data[-7:]]
            trend = np.polyfit(range(len(recent_sales)), recent_sales, 1)[0]
            
            # Use last week's average as base
            base_sales = np.mean(recent_sales)
            
            # Generate forecast
            forecast = []
            for i in range(days_ahead):
                predicted_sales = max(0, base_sales + (trend * (i + 1)))
                forecast.append(predicted_sales)
            
            return {
                'forecast_dates': [
                    (datetime.now() + timedelta(days=i+1)).strftime('%Y-%m-%d')
                    for i in range(days_ahead)
                ],
                'predicted_sales': forecast,
                'method': 'simple_trend',
                'confidence': 'low'
            }
            
        except Exception as e:
            self.logger.error(f"Error in simple sales forecast: {str(e)}")
            return {'error': str(e)}
    
    def _is_holiday(self, date):
        """Check if date is a holiday"""
        # In a real implementation, this would check against a holiday calendar
        # For now, just check weekends
        return date.weekday() >= 5  # Friday, Saturday, Sunday
    
    def _get_season(self, date):
        """Get season for date"""
        month = date.month
        if month in [12, 1, 2]:
            return 'winter'
        elif month in [3, 4, 5]:
            return 'spring'
        elif month in [6, 7, 8]:
            return 'summer'
        else:
            return 'fall'
    
    def log_prediction(self, prediction_type, input_data, output_data, confidence_score, user_id=None):
        """Log AI predictions for monitoring"""
        try:
            log_entry = AIPredictionLog(
                model_id=self.models.get(prediction_type).id if prediction_type in self.models else None,
                prediction_type=prediction_type,
                input_data=input_data,
                output_data=output_data,
                confidence_score=confidence_score,
                user_id=user_id,
                execution_time_ms=0  # Would be measured in real implementation
            )
            
            db.session.add(log_entry)
            db.session.commit()
            
        except Exception as e:
            self.logger.error(f"Error logging prediction: {str(e)}")
            db.session.rollback()