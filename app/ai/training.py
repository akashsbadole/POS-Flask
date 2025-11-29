"""
AI Model Training and Evaluation Pipelines
Handles training, evaluation, and deployment of AI models including:
- Model training automation
- Performance evaluation
- Model versioning and deployment
- Hyperparameter optimization
- Cross-validation
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from sklearn.model_selection import train_test_split, cross_val_score, GridSearchCV
from sklearn.metrics import classification_report, confusion_matrix, mean_squared_error, mean_absolute_error
import joblib
import json
import logging
import os
from typing import Dict, Any, List, Tuple, Optional

from app import db
from app.models.ai_models import AIModel, AITrainingJob, AIPredictionLog, AIFeatureStore
from app.models.order import Order, OrderItem
from app.models.customer import Customer
from app.models.menu import MenuItem, Category
from app.models.inventory import Ingredient, StockTransaction


class AITrainingPipeline:
    """AI Model Training Pipeline"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.models_dir = os.path.join(os.path.dirname(__file__), 'models')
        os.makedirs(self.models_dir, exist_ok=True)
    
    def train_upselling_model(self, training_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Train the upselling recommendation model"""
        try:
            self.logger.info("Starting upselling model training...")
            
            # Create training job record
            training_job = AITrainingJob(
                model_type='upselling',
                status='running',
                started_at=datetime.now(),
                parameters=training_data or {}
            )
            db.session.add(training_job)
            db.session.commit()
            
            # Get training data
            if not training_data:
                training_data = self._get_upselling_training_data()
            
            if not training_data or len(training_data.get('features', [])) < 100:
                training_job.status = 'failed'
                training_job.error_message = 'Insufficient training data'
                training_job.completed_at = datetime.now()
                db.session.commit()
                return {'error': 'Insufficient training data'}
            
            # Prepare features and target
            X = np.array(training_data['features'])
            y = np.array(training_data['targets'])
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42
            )
            
            # Train model (using collaborative filtering approach)
            from sklearn.ensemble import RandomForestClassifier
            model = RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                random_state=42
            )
            
            model.fit(X_train, y_train)
            
            # Evaluate model
            y_pred = model.predict(X_test)
            accuracy = np.mean(y_pred == y_test)
            
            # Cross-validation
            cv_scores = cross_val_score(model, X, y, cv=5)
            
            # Save model
            model_path = os.path.join(self.models_dir, 'upselling_model_v1.joblib')
            joblib.dump(model, model_path)
            
            # Update or create AI model record
            ai_model = AIModel.query.filter_by(model_type='upselling').first()
            
            if not ai_model:
                ai_model = AIModel(
                    name='Upselling Recommendation Engine',
                    model_type='upselling',
                    algorithm='random_forest',
                    version='1.0.0',
                    description='Random Forest model for upselling recommendations',
                    model_path=model_path,
                    is_active=True,
                    is_production=True
                )
                db.session.add(ai_model)
            else:
                ai_model.version = self._increment_version(ai_model.version)
                ai_model.model_path = model_path
                ai_model.performance_metrics = {
                    'accuracy': float(accuracy),
                    'cv_mean': float(cv_scores.mean()),
                    'cv_std': float(cv_scores.std())
                }
                ai_model.last_trained_at = datetime.now()
            
            db.session.commit()
            
            # Update training job
            training_job.status = 'completed'
            training_job.completed_at = datetime.now()
            training_job.results = {
                'accuracy': float(accuracy),
                'cv_mean': float(cv_scores.mean()),
                'cv_std': float(cv_scores.std()),
                'model_path': model_path
            }
            db.session.commit()
            
            self.logger.info(f"Upselling model training completed with accuracy: {accuracy:.3f}")
            
            return {
                'success': True,
                'accuracy': float(accuracy),
                'cv_mean': float(cv_scores.mean()),
                'cv_std': float(cv_scores.std()),
                'model_path': model_path,
                'training_job_id': training_job.id
            }
            
        except Exception as e:
            self.logger.error(f"Error training upselling model: {str(e)}")
            
            if 'training_job' in locals():
                training_job.status = 'failed'
                training_job.error_message = str(e)
                training_job.completed_at = datetime.now()
                db.session.commit()
            
            return {'error': str(e)}
    
    def train_dynamic_pricing_model(self, training_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Train the dynamic pricing model"""
        try:
            self.logger.info("Starting dynamic pricing model training...")
            
            # Create training job record
            training_job = AITrainingJob(
                model_type='dynamic_pricing',
                status='running',
                started_at=datetime.now(),
                parameters=training_data or {}
            )
            db.session.add(training_job)
            db.session.commit()
            
            # Get training data
            if not training_data:
                training_data = self._get_pricing_training_data()
            
            if not training_data or len(training_data.get('features', [])) < 100:
                training_job.status = 'failed'
                training_job.error_message = 'Insufficient training data'
                training_job.completed_at = datetime.now()
                db.session.commit()
                return {'error': 'Insufficient training data'}
            
            # Prepare features and target
            X = np.array(training_data['features'])
            y = np.array(training_data['targets'])  # Price elasticity or optimal price
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42
            )
            
            # Train model (using regression for price optimization)
            from sklearn.ensemble import GradientBoostingRegressor
            model = GradientBoostingRegressor(
                n_estimators=100,
                learning_rate=0.1,
                max_depth=6,
                random_state=42
            )
            
            model.fit(X_train, y_train)
            
            # Evaluate model
            y_pred = model.predict(X_test)
            mse = mean_squared_error(y_test, y_pred)
            mae = mean_absolute_error(y_test, y_pred)
            rmse = np.sqrt(mse)
            
            # Cross-validation
            cv_scores = cross_val_score(model, X, y, cv=5, scoring='neg_mean_squared_error')
            cv_rmse = np.sqrt(-cv_scores)
            
            # Save model
            model_path = os.path.join(self.models_dir, 'pricing_model_v1.joblib')
            joblib.dump(model, model_path)
            
            # Update or create AI model record
            ai_model = AIModel.query.filter_by(model_type='dynamic_pricing').first()
            
            if not ai_model:
                ai_model = AIModel(
                    name='Dynamic Pricing Engine',
                    model_type='dynamic_pricing',
                    algorithm='gradient_boosting',
                    version='1.0.0',
                    description='Gradient Boosting model for dynamic pricing',
                    model_path=model_path,
                    is_active=True,
                    is_production=True
                )
                db.session.add(ai_model)
            else:
                ai_model.version = self._increment_version(ai_model.version)
                ai_model.model_path = model_path
                ai_model.performance_metrics = {
                    'mse': float(mse),
                    'mae': float(mae),
                    'rmse': float(rmse),
                    'cv_rmse_mean': float(cv_rmse.mean()),
                    'cv_rmse_std': float(cv_rmse.std())
                }
                ai_model.last_trained_at = datetime.now()
            
            db.session.commit()
            
            # Update training job
            training_job.status = 'completed'
            training_job.completed_at = datetime.now()
            training_job.results = {
                'mse': float(mse),
                'mae': float(mae),
                'rmse': float(rmse),
                'cv_rmse_mean': float(cv_rmse.mean()),
                'cv_rmse_std': float(cv_rmse.std()),
                'model_path': model_path
            }
            db.session.commit()
            
            self.logger.info(f"Dynamic pricing model training completed with RMSE: {rmse:.3f}")
            
            return {
                'success': True,
                'mse': float(mse),
                'mae': float(mae),
                'rmse': float(rmse),
                'cv_rmse_mean': float(cv_rmse.mean()),
                'cv_rmse_std': float(cv_rmse.std()),
                'model_path': model_path,
                'training_job_id': training_job.id
            }
            
        except Exception as e:
            self.logger.error(f"Error training dynamic pricing model: {str(e)}")
            
            if 'training_job' in locals():
                training_job.status = 'failed'
                training_job.error_message = str(e)
                training_job.completed_at = datetime.now()
                db.session.commit()
            
            return {'error': str(e)}
    
    def train_sales_forecast_model(self, training_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Train the sales forecasting model"""
        try:
            self.logger.info("Starting sales forecast model training...")
            
            # Create training job record
            training_job = AITrainingJob(
                model_type='predictive_analytics',
                status='running',
                started_at=datetime.now(),
                parameters=training_data or {}
            )
            db.session.add(training_job)
            db.session.commit()
            
            # Get training data
            if not training_data:
                training_data = self._get_sales_forecast_training_data()
            
            if not training_data or len(training_data.get('features', [])) < 30:
                training_job.status = 'failed'
                training_job.error_message = 'Insufficient training data'
                training_job.completed_at = datetime.now()
                db.session.commit()
                return {'error': 'Insufficient training data'}
            
            # Prepare time series data
            dates = training_data['dates']
            sales_data = training_data['sales']
            
            # Train ARIMA model (simplified approach)
            from sklearn.linear_model import LinearRegression
            
            # Create time features
            X = []
            y = sales_data
            
            for i, date in enumerate(dates):
                # Extract time features
                day_of_week = date.weekday()
                day_of_month = date.day
                month = date.month
                is_weekend = 1 if day_of_week >= 5 else 0
                
                # Add lag features
                lag_1 = sales_data[i-1] if i > 0 else 0
                lag_7 = sales_data[i-7] if i > 6 else 0
                
                features = [day_of_week, day_of_month, month, is_weekend, lag_1, lag_7]
                X.append(features)
            
            X = np.array(X)
            
            # Split data (time series split)
            split_idx = int(len(X) * 0.8)
            X_train, X_test = X[:split_idx], X[split_idx:]
            y_train, y_test = y[:split_idx], y[split_idx:]
            
            # Train model
            model = LinearRegression()
            model.fit(X_train, y_train)
            
            # Evaluate model
            y_pred = model.predict(X_test)
            mse = mean_squared_error(y_test, y_pred)
            mae = mean_absolute_error(y_test, y_pred)
            rmse = np.sqrt(mse)
            
            # Calculate MAPE (Mean Absolute Percentage Error)
            mape = np.mean(np.abs((y_test - y_pred) / y_test)) * 100
            
            # Save model
            model_path = os.path.join(self.models_dir, 'sales_forecast_model_v1.joblib')
            joblib.dump(model, model_path)
            
            # Update or create AI model record
            ai_model = AIModel.query.filter_by(model_type='predictive_analytics').first()
            
            if not ai_model:
                ai_model = AIModel(
                    name='Sales Forecast Model',
                    model_type='predictive_analytics',
                    algorithm='linear_regression',
                    version='1.0.0',
                    description='Linear Regression model for sales forecasting',
                    model_path=model_path,
                    is_active=True,
                    is_production=True
                )
                db.session.add(ai_model)
            else:
                ai_model.version = self._increment_version(ai_model.version)
                ai_model.model_path = model_path
                ai_model.performance_metrics = {
                    'mse': float(mse),
                    'mae': float(mae),
                    'rmse': float(rmse),
                    'mape': float(mape)
                }
                ai_model.last_trained_at = datetime.now()
            
            db.session.commit()
            
            # Update training job
            training_job.status = 'completed'
            training_job.completed_at = datetime.now()
            training_job.results = {
                'mse': float(mse),
                'mae': float(mae),
                'rmse': float(rmse),
                'mape': float(mape),
                'model_path': model_path
            }
            db.session.commit()
            
            self.logger.info(f"Sales forecast model training completed with MAPE: {mape:.2f}%")
            
            return {
                'success': True,
                'mse': float(mse),
                'mae': float(mae),
                'rmse': float(rmse),
                'mape': float(mape),
                'model_path': model_path,
                'training_job_id': training_job.id
            }
            
        except Exception as e:
            self.logger.error(f"Error training sales forecast model: {str(e)}")
            
            if 'training_job' in locals():
                training_job.status = 'failed'
                training_job.error_message = str(e)
                training_job.completed_at = datetime.now()
                db.session.commit()
            
            return {'error': str(e)}
    
    def train_customer_churn_model(self, training_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Train the customer churn prediction model"""
        try:
            self.logger.info("Starting customer churn model training...")
            
            # Create training job record
            training_job = AITrainingJob(
                model_type='customer_intelligence',
                status='running',
                started_at=datetime.now(),
                parameters=training_data or {}
            )
            db.session.add(training_job)
            db.session.commit()
            
            # Get training data
            if not training_data:
                training_data = self._get_churn_training_data()
            
            if not training_data or len(training_data.get('features', [])) < 50:
                training_job.status = 'failed'
                training_job.error_message = 'Insufficient training data'
                training_job.completed_at = datetime.now()
                db.session.commit()
                return {'error': 'Insufficient training data'}
            
            # Prepare features and target
            X = np.array(training_data['features'])
            y = np.array(training_data['targets'])  # 1 for churn, 0 for no churn
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42, stratify=y
            )
            
            # Train model
            from sklearn.ensemble import RandomForestClassifier
            model = RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                random_state=42,
                class_weight='balanced'
            )
            
            model.fit(X_train, y_train)
            
            # Evaluate model
            y_pred = model.predict(X_test)
            y_prob = model.predict_proba(X_test)[:, 1]
            
            accuracy = np.mean(y_pred == y_test)
            
            # Calculate ROC AUC
            from sklearn.metrics import roc_auc_score, precision_recall_curve, auc
            roc_auc = roc_auc_score(y_test, y_prob)
            
            # Calculate precision-recall AUC
            precision, recall, _ = precision_recall_curve(y_test, y_prob)
            pr_auc = auc(recall, precision)
            
            # Cross-validation
            cv_scores = cross_val_score(model, X, y, cv=5, scoring='roc_auc')
            
            # Save model
            model_path = os.path.join(self.models_dir, 'churn_model_v1.joblib')
            joblib.dump(model, model_path)
            
            # Update or create AI model record
            ai_model = AIModel.query.filter_by(model_type='customer_intelligence').first()
            
            if not ai_model:
                ai_model = AIModel(
                    name='Customer Churn Prediction',
                    model_type='customer_intelligence',
                    algorithm='random_forest',
                    version='1.0.0',
                    description='Random Forest model for customer churn prediction',
                    model_path=model_path,
                    is_active=True,
                    is_production=True
                )
                db.session.add(ai_model)
            else:
                ai_model.version = self._increment_version(ai_model.version)
                ai_model.model_path = model_path
                ai_model.performance_metrics = {
                    'accuracy': float(accuracy),
                    'roc_auc': float(roc_auc),
                    'pr_auc': float(pr_auc),
                    'cv_roc_auc_mean': float(cv_scores.mean()),
                    'cv_roc_auc_std': float(cv_scores.std())
                }
                ai_model.last_trained_at = datetime.now()
            
            db.session.commit()
            
            # Update training job
            training_job.status = 'completed'
            training_job.completed_at = datetime.now()
            training_job.results = {
                'accuracy': float(accuracy),
                'roc_auc': float(roc_auc),
                'pr_auc': float(pr_auc),
                'cv_roc_auc_mean': float(cv_scores.mean()),
                'cv_roc_auc_std': float(cv_scores.std()),
                'model_path': model_path
            }
            db.session.commit()
            
            self.logger.info(f"Customer churn model training completed with ROC AUC: {roc_auc:.3f}")
            
            return {
                'success': True,
                'accuracy': float(accuracy),
                'roc_auc': float(roc_auc),
                'pr_auc': float(pr_auc),
                'cv_roc_auc_mean': float(cv_scores.mean()),
                'cv_roc_auc_std': float(cv_scores.std()),
                'model_path': model_path,
                'training_job_id': training_job.id
            }
            
        except Exception as e:
            self.logger.error(f"Error training customer churn model: {str(e)}")
            
            if 'training_job' in locals():
                training_job.status = 'failed'
                training_job.error_message = str(e)
                training_job.completed_at = datetime.now()
                db.session.commit()
            
            return {'error': str(e)}
    
    def evaluate_model(self, model_type: str, test_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Evaluate a trained model"""
        try:
            self.logger.info(f"Evaluating {model_type} model...")
            
            # Get the model
            ai_model = AIModel.query.filter_by(model_type=model_type, is_production=True).first()
            
            if not ai_model or not ai_model.model_path:
                return {'error': 'No trained model found for evaluation'}
            
            # Load model
            model = joblib.load(ai_model.model_path)
            
            # Get test data
            if not test_data:
                test_data = self._get_test_data(model_type)
            
            if not test_data:
                return {'error': 'No test data available for evaluation'}
            
            # Prepare data
            X_test = np.array(test_data['features'])
            y_test = np.array(test_data['targets'])
            
            # Make predictions
            y_pred = model.predict(X_test)
            
            # Calculate metrics based on model type
            if model_type in ['upselling', 'customer_intelligence']:
                # Classification metrics
                from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
                
                accuracy = accuracy_score(y_test, y_pred)
                precision = precision_score(y_test, y_pred, average='weighted')
                recall = recall_score(y_test, y_pred, average='weighted')
                f1 = f1_score(y_test, y_pred, average='weighted')
                
                # ROC AUC for binary classification
                if len(np.unique(y_test)) == 2:
                    y_prob = model.predict_proba(X_test)[:, 1]
                    roc_auc = roc_auc_score(y_test, y_prob)
                else:
                    roc_auc = None
                
                metrics = {
                    'accuracy': float(accuracy),
                    'precision': float(precision),
                    'recall': float(recall),
                    'f1_score': float(f1)
                }
                
                if roc_auc is not None:
                    metrics['roc_auc'] = float(roc_auc)
                
            else:
                # Regression metrics
                mse = mean_squared_error(y_test, y_pred)
                mae = mean_absolute_error(y_test, y_pred)
                rmse = np.sqrt(mse)
                
                # MAPE for forecasting models
                mape = np.mean(np.abs((y_test - y_pred) / np.maximum(y_test, 1e-6))) * 100
                
                metrics = {
                    'mse': float(mse),
                    'mae': float(mae),
                    'rmse': float(rmse),
                    'mape': float(mape)
                }
            
            # Update model performance metrics
            ai_model.performance_metrics = metrics
            ai_model.last_evaluated_at = datetime.now()
            db.session.commit()
            
            self.logger.info(f"Model evaluation completed for {model_type}")
            
            return {
                'success': True,
                'model_type': model_type,
                'metrics': metrics,
                'evaluation_date': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error evaluating model: {str(e)}")
            return {'error': str(e)}
    
    def _get_upselling_training_data(self) -> Dict[str, Any]:
        """Get training data for upselling model"""
        try:
            # Get order items with customer information
            order_items = db.session.query(
                OrderItem.menu_item_id,
                OrderItem.quantity,
                OrderItem.price,
                Order.customer_id,
                Order.created_at
            ).join(Order).all()
            
            if not order_items:
                return {}
            
            # Create training data
            features = []
            targets = []
            
            for item in order_items:
                # Get customer order history
                customer_orders = Order.query.filter_by(customer_id=item.customer_id).all()
                
                # Customer features
                total_orders = len(customer_orders)
                total_spent = sum(o.total_amount for o in customer_orders)
                avg_order_value = total_spent / total_orders if total_orders > 0 else 0
                
                # Item features
                item_orders = OrderItem.query.filter_by(menu_item_id=item.menu_item_id).count()
                item_popularity = item_orders / len(order_items) if len(order_items) > 0 else 0
                
                # Time features
                hour = item.created_at.hour
                day_of_week = item.created_at.weekday()
                is_weekend = 1 if day_of_week >= 5 else 0
                
                # Target: whether this item was part of an upsell (simplified)
                # In a real implementation, this would be based on actual upsell data
                target = 1 if item.quantity > 1 or item.price > 50 else 0
                
                feature_vector = [
                    total_orders,
                    avg_order_value,
                    item_popularity,
                    hour,
                    day_of_week,
                    is_weekend
                ]
                
                features.append(feature_vector)
                targets.append(target)
            
            return {
                'features': features,
                'targets': targets
            }
            
        except Exception as e:
            self.logger.error(f"Error getting upselling training data: {str(e)}")
            return {}
    
    def _get_pricing_training_data(self) -> Dict[str, Any]:
        """Get training data for dynamic pricing model"""
        try:
            # Get historical order data with pricing
            orders = db.session.query(
                Order.total_amount,
                Order.created_at,
                Order.customer_id
            ).all()
            
            if not orders:
                return {}
            
            # Create training data
            features = []
            targets = []
            
            for order in orders:
                # Time features
                hour = order.created_at.hour
                day_of_week = order.created_at.weekday()
                is_weekend = 1 if day_of_week >= 5 else 0
                
                # Demand features (simplified)
                same_hour_orders = len([o for o in orders if o.created_at.hour == hour])
                demand_factor = same_hour_orders / len(orders) if len(orders) > 0 else 0
                
                # Customer value
                customer_orders = Order.query.filter_by(customer_id=order.customer_id).all()
                customer_value = sum(o.total_amount for o in customer_orders)
                
                # Target: optimal price factor (simplified)
                # In a real implementation, this would be based on price elasticity
                target = min(1.5, max(0.5, 1.0 + (demand_factor - 0.5) * 0.3))
                
                feature_vector = [
                    hour,
                    day_of_week,
                    is_weekend,
                    demand_factor,
                    customer_value
                ]
                
                features.append(feature_vector)
                targets.append(target)
            
            return {
                'features': features,
                'targets': targets
            }
            
        except Exception as e:
            self.logger.error(f"Error getting pricing training data: {str(e)}")
            return {}
    
    def _get_sales_forecast_training_data(self) -> Dict[str, Any]:
        """Get training data for sales forecasting model"""
        try:
            # Get daily sales data
            orders = db.session.query(
                Order.created_at,
                Order.total_amount
            ).all()
            
            if not orders:
                return {}
            
            # Aggregate by date
            daily_sales = {}
            for order in orders:
                date = order.created_at.date()
                if date not in daily_sales:
                    daily_sales[date] = 0
                daily_sales[date] += order.total_amount
            
            # Sort by date
            sorted_dates = sorted(daily_sales.keys())
            sales_data = [daily_sales[date] for date in sorted_dates]
            
            return {
                'dates': sorted_dates,
                'sales': sales_data
            }
            
        except Exception as e:
            self.logger.error(f"Error getting sales forecast training data: {str(e)}")
            return {}
    
    def _get_churn_training_data(self) -> Dict[str, Any]:
        """Get training data for customer churn model"""
        try:
            # Get customer data with order history
            customers = Customer.query.filter(Customer.is_active == True).all()
            
            if not customers:
                return {}
            
            # Create training data
            features = []
            targets = []
            
            for customer in customers:
                # Get customer order history
                orders = Order.query.filter_by(customer_id=customer.id).all()
                
                if not orders:
                    continue
                
                # RFM metrics
                total_orders = len(orders)
                total_spent = sum(o.total_amount for o in orders)
                avg_order_value = total_spent / total_orders if total_orders > 0 else 0
                
                # Recency
                last_order = max(orders, key=lambda o: o.created_at)
                recency_days = (datetime.now() - last_order.created_at).days
                
                # Frequency
                first_order = min(orders, key=lambda o: o.created_at)
                customer_age_days = (datetime.now() - first_order.created_at).days
                frequency = total_orders / (customer_age_days / 30) if customer_age_days > 0 else 0
                
                # Target: churn (simplified - customers with no orders in last 30 days)
                target = 1 if recency_days > 30 else 0
                
                feature_vector = [
                    total_orders,
                    total_spent,
                    avg_order_value,
                    recency_days,
                    frequency
                ]
                
                features.append(feature_vector)
                targets.append(target)
            
            return {
                'features': features,
                'targets': targets
            }
            
        except Exception as e:
            self.logger.error(f"Error getting churn training data: {str(e)}")
            return {}
    
    def _get_test_data(self, model_type: str) -> Dict[str, Any]:
        """Get test data for model evaluation"""
        if model_type == 'upselling':
            return self._get_upselling_training_data()
        elif model_type == 'dynamic_pricing':
            return self._get_pricing_training_data()
        elif model_type == 'predictive_analytics':
            return self._get_sales_forecast_training_data()
        elif model_type == 'customer_intelligence':
            return self._get_churn_training_data()
        else:
            return {}
    
    def _increment_version(self, version: str) -> str:
        """Increment version number"""
        try:
            parts = version.split('.')
            if len(parts) >= 3:
                # Increment patch version
                parts[-1] = str(int(parts[-1]) + 1)
                return '.'.join(parts)
            else:
                return version + '.1'
        except:
            return version + '.1'


# Global training pipeline instance
training_pipeline = AITrainingPipeline()


def get_training_pipeline() -> AITrainingPipeline:
    """Get the global training pipeline instance"""
    return training_pipeline