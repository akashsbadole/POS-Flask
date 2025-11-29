"""
AI Module Routes
Provides REST API endpoints for all AI-powered features including:
- Upselling recommendations
- Dynamic pricing
- Predictive analytics
- Customer intelligence
- Model management
"""

from flask import Blueprint, request, jsonify, current_app
from datetime import datetime, timedelta
import json
import logging

from app import db
from app.models.ai_models import (
    AIModel, AIPredictionLog, AIConfiguration, AITrainingJob,
    AIABTest, AIRecommendation, AIPriceOptimization
)
from app.ai.services.upselling_service import UpsellingService
from app.ai.services.dynamic_pricing_service import DynamicPricingService
from app.ai.services.predictive_analytics_service import PredictiveAnalyticsService
from app.ai.services.inventory_intelligence_service import InventoryIntelligenceService
from app.ai.services.customer_intelligence_service import CustomerIntelligenceService
from app.ai.config import get_ai_config, is_ai_enabled, is_feature_enabled

# Create blueprint
ai_bp = Blueprint('ai', __name__, url_prefix='/ai')

# Initialize services
upselling_service = UpsellingService()
pricing_service = DynamicPricingService()
analytics_service = PredictiveAnalyticsService()
inventory_service = InventoryIntelligenceService()
customer_service = CustomerIntelligenceService()

logger = logging.getLogger(__name__)


def ai_enabled_required(f):
    """Decorator to check if AI is enabled"""
    def decorated_function(*args, **kwargs):
        if not is_ai_enabled():
            return jsonify({'error': 'AI features are disabled'}), 403
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function


def feature_enabled_required(feature):
    """Decorator to check if a specific AI feature is enabled"""
    def decorator(f):
        def decorated_function(*args, **kwargs):
            if not is_feature_enabled(feature):
                return jsonify({'error': f'{feature} feature is disabled'}), 403
            return f(*args, **kwargs)
        decorated_function.__name__ = f.__name__
        return decorated_function
    return decorator


def log_prediction(model_type, prediction_data, confidence, metadata=None):
    """Log AI prediction for monitoring"""
    try:
        log_entry = AIPredictionLog(
            model_type=model_type,
            prediction_data=prediction_data,
            confidence_score=confidence,
            metadata=metadata or {}
        )
        
        db.session.add(log_entry)
        db.session.commit()
        
        return log_entry.id
        
    except Exception as e:
        logger.error(f"Error logging prediction: {str(e)}")
        db.session.rollback()
        return None


# Upselling Recommendations Endpoints
@ai_bp.route('/recommendations/upsell', methods=['POST'])
@ai_enabled_required
@feature_enabled_required('upselling')
def get_upsell_recommendations():
    """Get upselling recommendations for an order"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data or 'customer_id' not in data or 'order_items' not in data:
            return jsonify({'error': 'customer_id and order_items are required'}), 400
        
        customer_id = data['customer_id']
        order_items = data['order_items']
        
        # Get recommendations
        recommendations = upselling_service.get_recommendations(
            customer_id=customer_id,
            order_items=order_items,
            max_recommendations=data.get('max_recommendations', 3)
        )
        
        # Log prediction
        log_prediction(
            model_type='upselling',
            prediction_data={
                'customer_id': customer_id,
                'order_items': order_items,
                'recommendations': recommendations
            },
            confidence=recommendations.get('confidence', 0.5),
            metadata={'source': 'api'}
        )
        
        return jsonify({
            'success': True,
            'recommendations': recommendations,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting upsell recommendations: {str(e)}")
        return jsonify({'error': str(e)}), 500


@ai_bp.route('/recommendations/complementary', methods=['POST'])
@ai_enabled_required
@feature_enabled_required('upselling')
def get_complementary_recommendations():
    """Get complementary item recommendations"""
    try:
        data = request.get_json()
        
        if not data or 'item_id' not in data:
            return jsonify({'error': 'item_id is required'}), 400
        
        item_id = data['item_id']
        customer_id = data.get('customer_id')
        
        recommendations = upselling_service.get_complementary_items(
            item_id=item_id,
            customer_id=customer_id
        )
        
        return jsonify({
            'success': True,
            'recommendations': recommendations,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting complementary recommendations: {str(e)}")
        return jsonify({'error': str(e)}), 500


# Dynamic Pricing Endpoints
@ai_bp.route('/pricing/dynamic', methods=['POST'])
@ai_enabled_required
@feature_enabled_required('dynamic_pricing')
def get_dynamic_pricing():
    """Get dynamic pricing for menu items"""
    try:
        data = request.get_json()
        
        if not data or 'item_ids' not in data:
            return jsonify({'error': 'item_ids is required'}), 400
        
        item_ids = data['item_ids']
        
        pricing = pricing_service.get_dynamic_pricing(
            item_ids=item_ids,
            context=data.get('context', {})
        )
        
        # Log prediction
        log_prediction(
            model_type='dynamic_pricing',
            prediction_data={
                'item_ids': item_ids,
                'pricing': pricing
            },
            confidence=pricing.get('confidence', 0.5),
            metadata={'source': 'api'}
        )
        
        return jsonify({
            'success': True,
            'pricing': pricing,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting dynamic pricing: {str(e)}")
        return jsonify({'error': str(e)}), 500


@ai_bp.route('/pricing/optimize', methods=['POST'])
@ai_enabled_required
@feature_enabled_required('dynamic_pricing')
def optimize_prices():
    """Optimize prices for multiple items"""
    try:
        data = request.get_json()
        
        if not data or 'item_ids' not in data:
            return jsonify({'error': 'item_ids is required'}), 400
        
        item_ids = data['item_ids']
        
        optimization = pricing_service.optimize_prices(
            item_ids=item_ids,
            constraints=data.get('constraints', {}),
            objectives=data.get('objectives', ['revenue', 'demand'])
        )
        
        return jsonify({
            'success': True,
            'optimization': optimization,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error optimizing prices: {str(e)}")
        return jsonify({'error': str(e)}), 500


# Predictive Analytics Endpoints
@ai_bp.route('/analytics/sales-forecast', methods=['POST'])
@ai_enabled_required
@feature_enabled_required('predictive_analytics')
def get_sales_forecast():
    """Get sales forecast"""
    try:
        data = request.get_json()
        
        days_ahead = data.get('days_ahead', 30)
        item_ids = data.get('item_ids')
        category_ids = data.get('category_ids')
        
        forecast = analytics_service.get_sales_forecast(
            days_ahead=days_ahead,
            item_ids=item_ids,
            category_ids=category_ids
        )
        
        # Log prediction
        log_prediction(
            model_type='sales_forecast',
            prediction_data={
                'days_ahead': days_ahead,
                'item_ids': item_ids,
                'category_ids': category_ids,
                'forecast': forecast
            },
            confidence=forecast.get('confidence', 0.5),
            metadata={'source': 'api'}
        )
        
        return jsonify({
            'success': True,
            'forecast': forecast,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting sales forecast: {str(e)}")
        return jsonify({'error': str(e)}), 500


@ai_bp.route('/analytics/inventory-demand', methods=['POST'])
@ai_enabled_required
@feature_enabled_required('predictive_analytics')
def get_inventory_demand():
    """Get inventory demand predictions"""
    try:
        data = request.get_json()
        
        days_ahead = data.get('days_ahead', 14)
        ingredient_ids = data.get('ingredient_ids')
        
        demand = analytics_service.get_inventory_demand(
            days_ahead=days_ahead,
            ingredient_ids=ingredient_ids
        )
        
        return jsonify({
            'success': True,
            'demand': demand,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting inventory demand: {str(e)}")
        return jsonify({'error': str(e)}), 500


@ai_bp.route('/analytics/staff-scheduling', methods=['POST'])
@ai_enabled_required
@feature_enabled_required('predictive_analytics')
def get_staff_scheduling():
    """Get staff scheduling optimization"""
    try:
        data = request.get_json()
        
        days_ahead = data.get('days_ahead', 7)
        
        scheduling = analytics_service.get_staff_scheduling(days_ahead=days_ahead)
        
        return jsonify({
            'success': True,
            'scheduling': scheduling,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting staff scheduling: {str(e)}")
        return jsonify({'error': str(e)}), 500


# Inventory Intelligence Endpoints
@ai_bp.route('/inventory/stock-prediction', methods=['POST'])
@ai_enabled_required
@feature_enabled_required('predictive_analytics')
def get_stock_predictions():
    """Get stock level predictions"""
    try:
        data = request.get_json()
        
        days_ahead = data.get('days_ahead', 7)
        ingredient_ids = data.get('ingredient_ids')
        
        predictions = inventory_service.get_stock_predictions(
            days_ahead=days_ahead,
            ingredient_ids=ingredient_ids
        )
        
        return jsonify({
            'success': True,
            'predictions': predictions,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting stock predictions: {str(e)}")
        return jsonify({'error': str(e)}), 500


@ai_bp.route('/inventory/purchase-orders', methods=['POST'])
@ai_enabled_required
@feature_enabled_required('predictive_analytics')
def generate_purchase_orders():
    """Generate automated purchase orders"""
    try:
        data = request.get_json()
        
        days_ahead = data.get('days_ahead', 7)
        
        orders = inventory_service.generate_purchase_orders(days_ahead=days_ahead)
        
        return jsonify({
            'success': True,
            'purchase_orders': orders,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error generating purchase orders: {str(e)}")
        return jsonify({'error': str(e)}), 500


@ai_bp.route('/inventory/spoilage-prediction', methods=['POST'])
@ai_enabled_required
@feature_enabled_required('predictive_analytics')
def get_spoilage_predictions():
    """Get spoilage predictions"""
    try:
        data = request.get_json()
        
        days_ahead = data.get('days_ahead', 7)
        ingredient_ids = data.get('ingredient_ids')
        
        predictions = inventory_service.get_spoilage_predictions(
            days_ahead=days_ahead,
            ingredient_ids=ingredient_ids
        )
        
        return jsonify({
            'success': True,
            'predictions': predictions,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting spoilage predictions: {str(e)}")
        return jsonify({'error': str(e)}), 500


# Customer Intelligence Endpoints
@ai_bp.route('/customers/segmentation', methods=['POST'])
@ai_enabled_required
@feature_enabled_required('customer_intelligence')
def segment_customers():
    """Get customer segmentation"""
    try:
        data = request.get_json()
        
        segmentation_type = data.get('segmentation_type', 'behavioral')
        
        segmentation = customer_service.segment_customers(segmentation_type)
        
        return jsonify({
            'success': True,
            'segmentation': segmentation,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting customer segmentation: {str(e)}")
        return jsonify({'error': str(e)}), 500


@ai_bp.route('/customers/churn-prediction', methods=['POST'])
@ai_enabled_required
@feature_enabled_required('customer_intelligence')
def predict_churn():
    """Predict customer churn"""
    try:
        data = request.get_json()
        
        customer_id = data.get('customer_id')
        days_ahead = data.get('days_ahead', 30)
        
        churn = customer_service.predict_churn(customer_id, days_ahead)
        
        return jsonify({
            'success': True,
            'churn_prediction': churn,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error predicting churn: {str(e)}")
        return jsonify({'error': str(e)}), 500


@ai_bp.route('/customers/clv', methods=['POST'])
@ai_enabled_required
@feature_enabled_required('customer_intelligence')
def calculate_clv():
    """Calculate customer lifetime value"""
    try:
        data = request.get_json()
        
        customer_id = data.get('customer_id')
        
        clv = customer_service.calculate_lifetime_value(customer_id)
        
        return jsonify({
            'success': True,
            'clv': clv,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error calculating CLV: {str(e)}")
        return jsonify({'error': str(e)}), 500


@ai_bp.route('/customers/marketing-recommendations', methods=['POST'])
@ai_enabled_required
@feature_enabled_required('customer_intelligence')
def get_marketing_recommendations():
    """Get marketing recommendations"""
    try:
        data = request.get_json()
        
        customer_id = data.get('customer_id')
        campaign_type = data.get('campaign_type', 'retention')
        
        recommendations = customer_service.get_marketing_recommendations(
            customer_id=customer_id,
            campaign_type=campaign_type
        )
        
        return jsonify({
            'success': True,
            'recommendations': recommendations,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting marketing recommendations: {str(e)}")
        return jsonify({'error': str(e)}), 500


@ai_bp.route('/customers/sentiment-analysis', methods=['POST'])
@ai_enabled_required
@feature_enabled_required('customer_intelligence')
def analyze_sentiment():
    """Analyze customer sentiment from feedback"""
    try:
        data = request.get_json()
        
        feedback_data = data.get('feedback_data')
        
        sentiment = customer_service.analyze_feedback_sentiment(feedback_data)
        
        return jsonify({
            'success': True,
            'sentiment_analysis': sentiment,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error analyzing sentiment: {str(e)}")
        return jsonify({'error': str(e)}), 500


# Model Management Endpoints
@ai_bp.route('/models', methods=['GET'])
@ai_enabled_required
def list_models():
    """List all AI models"""
    try:
        models = AIModel.query.all()
        
        model_list = []
        for model in models:
            model_list.append({
                'id': model.id,
                'name': model.name,
                'model_type': model.model_type,
                'algorithm': model.algorithm,
                'version': model.version,
                'is_active': model.is_active,
                'is_production': model.is_production,
                'performance_metrics': model.performance_metrics,
                'created_at': model.created_at.isoformat(),
                'updated_at': model.updated_at.isoformat()
            })
        
        return jsonify({
            'success': True,
            'models': model_list,
            'count': len(model_list)
        })
        
    except Exception as e:
        logger.error(f"Error listing models: {str(e)}")
        return jsonify({'error': str(e)}), 500


@ai_bp.route('/models/<int:model_id>/train', methods=['POST'])
@ai_enabled_required
def train_model(model_id):
    """Train a specific AI model"""
    try:
        model = AIModel.query.get_or_404(model_id)
        
        # Create training job
        training_job = AITrainingJob(
            model_id=model_id,
            status='pending',
            parameters=request.get_json() or {}
        )
        
        db.session.add(training_job)
        db.session.commit()
        
        # In a real implementation, this would trigger an async training job
        # For now, just mark as started
        training_job.status = 'running'
        training_job.started_at = datetime.now()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'training_job_id': training_job.id,
            'status': 'started'
        })
        
    except Exception as e:
        logger.error(f"Error training model: {str(e)}")
        return jsonify({'error': str(e)}), 500


@ai_bp.route('/models/<int:model_id>/evaluate', methods=['POST'])
@ai_enabled_required
def evaluate_model(model_id):
    """Evaluate a specific AI model"""
    try:
        model = AIModel.query.get_or_404(model_id)
        
        # In a real implementation, this would run model evaluation
        # For now, return mock evaluation results
        evaluation_results = {
            'accuracy': 0.85,
            'precision': 0.82,
            'recall': 0.88,
            'f1_score': 0.85,
            'confusion_matrix': [[100, 15], [12, 98]],
            'evaluation_date': datetime.now().isoformat()
        }
        
        # Update model performance metrics
        model.performance_metrics = evaluation_results
        model.last_evaluated_at = datetime.now()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'evaluation_results': evaluation_results
        })
        
    except Exception as e:
        logger.error(f"Error evaluating model: {str(e)}")
        return jsonify({'error': str(e)}), 500


# Configuration Endpoints
@ai_bp.route('/config', methods=['GET'])
@ai_enabled_required
def get_config():
    """Get AI configuration"""
    try:
        config = get_ai_config()
        
        return jsonify({
            'success': True,
            'config': config.get_all()
        })
        
    except Exception as e:
        logger.error(f"Error getting AI config: {str(e)}")
        return jsonify({'error': str(e)}), 500


@ai_bp.route('/config', methods=['PUT'])
@ai_enabled_required
def update_config():
    """Update AI configuration"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No configuration data provided'}), 400
        
        config = get_ai_config()
        
        # Update each configuration value
        for key, value in data.items():
            is_valid, message = config.validate_config(key, value)
            if not is_valid:
                return jsonify({'error': f'Invalid value for {key}: {message}'}), 400
            
            config.set(key, value, save_to_db=False)
        
        # Save all changes to database
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Configuration updated successfully'
        })
        
    except Exception as e:
        logger.error(f"Error updating AI config: {str(e)}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@ai_bp.route('/config/reset', methods=['POST'])
@ai_enabled_required
def reset_config():
    """Reset AI configuration to defaults"""
    try:
        config = get_ai_config()
        config.reset_to_defaults()
        
        return jsonify({
            'success': True,
            'message': 'Configuration reset to defaults'
        })
        
    except Exception as e:
        logger.error(f"Error resetting AI config: {str(e)}")
        return jsonify({'error': str(e)}), 500


@ai_bp.route('/config/export', methods=['GET'])
@ai_enabled_required
def export_config():
    """Export AI configuration"""
    try:
        config = get_ai_config()
        config_json = config.export_config()
        
        return jsonify({
            'success': True,
            'config': json.loads(config_json)
        })
        
    except Exception as e:
        logger.error(f"Error exporting AI config: {str(e)}")
        return jsonify({'error': str(e)}), 500


@ai_bp.route('/config/import', methods=['POST'])
@ai_enabled_required
def import_config():
    """Import AI configuration"""
    try:
        data = request.get_json()
        
        if not data or 'config' not in data:
            return jsonify({'error': 'Configuration data is required'}), 400
        
        config = get_ai_config()
        config_json = json.dumps(data['config'])
        
        success, message = config.import_config(config_json, merge=data.get('merge', False))
        
        if success:
            return jsonify({
                'success': True,
                'message': message
            })
        else:
            return jsonify({'error': message}), 400
        
    except Exception as e:
        logger.error(f"Error importing AI config: {str(e)}")
        return jsonify({'error': str(e)}), 500


# Health Check Endpoint
@ai_bp.route('/health', methods=['GET'])
def health_check():
    """AI module health check"""
    try:
        health_status = {
            'status': 'healthy',
            'ai_enabled': is_ai_enabled(),
            'timestamp': datetime.now().isoformat(),
            'services': {
                'upselling': is_feature_enabled('upselling'),
                'dynamic_pricing': is_feature_enabled('dynamic_pricing'),
                'predictive_analytics': is_feature_enabled('predictive_analytics'),
                'customer_intelligence': is_feature_enabled('customer_intelligence')
            }
        }
        
        return jsonify(health_status)
        
    except Exception as e:
        logger.error(f"Error in health check: {str(e)}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500