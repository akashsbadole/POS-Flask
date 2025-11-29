"""
Create AI Database Tables Migration Script
Creates all tables required for AI-powered features including:
- AI model storage and versioning
- Prediction logging
- Feature store for ML models
- Customer behavior tracking
- AI configuration and settings
- A/B testing framework
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models.ai_models import (
    AIModel, AIPredictionLog, AIFeatureStore, AICustomerBehavior,
    AIConfiguration, AITrainingJob, AIABTest, AIABTestParticipant,
    AIRecommendation, AIPriceOptimization, AIInventoryPrediction
)
from datetime import datetime


def create_ai_tables():
    """Create all AI-related database tables"""
    app = create_app()
    
    with app.app_context():
        print("Creating AI database tables...")
        
        try:
            # Create all AI model tables
            db.create_all()
            
            # Insert default AI configuration
            insert_default_ai_config()
            
            # Insert sample AI models
            insert_sample_ai_models()
            
            print("✅ AI database tables created successfully!")
            print("\nCreated tables:")
            print("- ai_models: ML model storage and versioning")
            print("- ai_prediction_logs: Prediction logging for monitoring")
            print("- ai_feature_store: Feature storage for ML models")
            print("- ai_customer_behavior: Customer behavior tracking")
            print("- ai_configurations: AI settings and configuration")
            print("- ai_training_jobs: Model training job tracking")
            print("- ai_ab_tests: A/B testing framework")
            print("- ai_ab_test_participants: A/B test participants")
            print("- ai_recommendations: AI-generated recommendations")
            print("- ai_price_optimizations: Dynamic pricing records")
            print("- ai_inventory_predictions: Inventory predictions")
            
        except Exception as e:
            print(f"❌ Error creating AI tables: {str(e)}")
            db.session.rollback()
            raise


def insert_default_ai_config():
    """Insert default AI configuration settings"""
    from app.ai.config import AIConfig
    
    config = AIConfig()
    
    # Insert all default settings
    for key, value in config.default_settings.items():
        from app.models.ai_models import AIConfiguration
        
        existing = AIConfiguration.query.filter_by(config_key=key).first()
        if not existing:
            config_entry = AIConfiguration(
                config_key=key,
                config_value=str(value) if not isinstance(value, (dict, list)) else str(value),
                config_type='setting',
                is_active=True
            )
            db.session.add(config_entry)
    
    db.session.commit()
    print("✅ Default AI configuration inserted")


def insert_sample_ai_models():
    """Insert sample AI models for demonstration"""
    sample_models = [
        {
            'name': 'Upselling Recommendation Engine',
            'model_type': 'upselling',
            'algorithm': 'collaborative_filtering',
            'version': '1.0.0',
            'description': 'Collaborative filtering model for upselling recommendations',
            'is_active': True,
            'is_production': True,
            'performance_metrics': {
                'accuracy': 0.82,
                'precision': 0.78,
                'recall': 0.85,
                'f1_score': 0.81
            }
        },
        {
            'name': 'Dynamic Pricing Engine',
            'model_type': 'dynamic_pricing',
            'algorithm': 'multi_factor_optimization',
            'version': '1.0.0',
            'description': 'Multi-factor optimization model for dynamic pricing',
            'is_active': True,
            'is_production': True,
            'performance_metrics': {
                'revenue_increase': 0.15,
                'demand_prediction_accuracy': 0.88,
                'price_elasticity_accuracy': 0.76
            }
        },
        {
            'name': 'Sales Forecast Model',
            'model_type': 'predictive_analytics',
            'algorithm': 'arima',
            'version': '1.0.0',
            'description': 'ARIMA time series model for sales forecasting',
            'is_active': True,
            'is_production': True,
            'performance_metrics': {
                'mape': 0.12,  # Mean Absolute Percentage Error
                'rmse': 45.5,  # Root Mean Square Error
                'r_squared': 0.89
            }
        },
        {
            'name': 'Customer Churn Prediction',
            'model_type': 'customer_intelligence',
            'algorithm': 'random_forest',
            'version': '1.0.0',
            'description': 'Random Forest model for customer churn prediction',
            'is_active': True,
            'is_production': True,
            'performance_metrics': {
                'accuracy': 0.86,
                'precision': 0.82,
                'recall': 0.79,
                'auc_roc': 0.91
            }
        },
        {
            'name': 'Inventory Demand Prediction',
            'model_type': 'inventory_intelligence',
            'algorithm': 'lstm',
            'version': '1.0.0',
            'description': 'LSTM neural network for inventory demand prediction',
            'is_active': True,
            'is_production': True,
            'performance_metrics': {
                'mae': 2.3,  # Mean Absolute Error
                'rmse': 3.8,
                'mape': 0.08
            }
        }
    ]
    
    for model_data in sample_models:
        existing = AIModel.query.filter_by(
            name=model_data['name'],
            model_type=model_data['model_type']
        ).first()
        
        if not existing:
            model = AIModel(
                name=model_data['name'],
                model_type=model_data['model_type'],
                algorithm=model_data['algorithm'],
                version=model_data['version'],
                description=model_data['description'],
                is_active=model_data['is_active'],
                is_production=model_data['is_production'],
                performance_metrics=model_data['performance_metrics'],
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            db.session.add(model)
    
    db.session.commit()
    print("✅ Sample AI models inserted")


def create_indexes():
    """Create performance indexes for AI tables"""
    from sqlalchemy import text
    
    indexes = [
        # AI Model indexes
        "CREATE INDEX IF NOT EXISTS idx_ai_models_type ON ai_models(model_type)",
        "CREATE INDEX IF NOT EXISTS idx_ai_models_active ON ai_models(is_active, is_production)",
        
        # Prediction log indexes
        "CREATE INDEX IF NOT EXISTS idx_ai_predictions_model_type ON ai_prediction_logs(model_type)",
        "CREATE INDEX IF NOT EXISTS idx_ai_predictions_created ON ai_prediction_logs(created_at)",
        "CREATE INDEX IF NOT EXISTS idx_ai_predictions_confidence ON ai_prediction_logs(confidence_score)",
        
        # Feature store indexes
        "CREATE INDEX IF NOT EXISTS idx_ai_features_model ON ai_feature_store(model_type, model_version)",
        "CREATE INDEX IF NOT EXISTS idx_ai_features_entity ON ai_feature_store(entity_type, entity_id)",
        
        # Customer behavior indexes
        "CREATE INDEX IF NOT EXISTS idx_ai_behavior_customer ON ai_customer_behavior(customer_id)",
        "CREATE INDEX IF NOT EXISTS idx_ai_behavior_type ON ai_customer_behavior(behavior_type)",
        "CREATE INDEX IF NOT EXISTS idx_ai_behavior_date ON ai_customer_behavior(created_at)",
        
        # Training job indexes
        "CREATE INDEX IF NOT EXISTS idx_ai_training_model ON ai_training_jobs(model_id)",
        "CREATE INDEX IF NOT EXISTS idx_ai_training_status ON ai_training_jobs(status)",
        
        # A/B test indexes
        "CREATE INDEX IF NOT EXISTS idx_ai_ab_test_active ON ai_ab_tests(is_active)",
        "CREATE INDEX IF NOT EXISTS idx_ai_ab_participant_test ON ai_ab_test_participants(test_id)",
        
        # Recommendation indexes
        "CREATE INDEX IF NOT EXISTS idx_ai_recommendations_customer ON ai_recommendations(customer_id)",
        "CREATE INDEX IF NOT EXISTS idx_ai_recommendations_type ON ai_recommendations(recommendation_type)",
        
        # Price optimization indexes
        "CREATE INDEX IF NOT EXISTS idx_ai_price_item ON ai_price_optimizations(menu_item_id)",
        "CREATE INDEX IF NOT EXISTS idx_ai_price_date ON ai_price_optimizations(created_at)",
        
        # Inventory prediction indexes
        "CREATE INDEX IF NOT EXISTS idx_ai_inventory_ingredient ON ai_inventory_predictions(ingredient_id)",
        "CREATE INDEX IF NOT EXISTS idx_ai_inventory_date ON ai_inventory_predictions(prediction_date)"
    ]
    
    try:
        for index_sql in indexes:
            db.session.execute(text(index_sql))
        
        db.session.commit()
        print("✅ AI table indexes created")
        
    except Exception as e:
        print(f"⚠️ Warning: Could not create some indexes: {str(e)}")
        db.session.rollback()


def verify_tables():
    """Verify that all AI tables were created successfully"""
    from sqlalchemy import inspect
    
    inspector = inspect(db.engine)
    tables = inspector.get_table_names()
    
    required_tables = [
        'ai_models',
        'ai_prediction_logs',
        'ai_feature_store',
        'ai_customer_behavior',
        'ai_configurations',
        'ai_training_jobs',
        'ai_ab_tests',
        'ai_ab_test_participants',
        'ai_recommendations',
        'ai_price_optimizations',
        'ai_inventory_predictions'
    ]
    
    missing_tables = [table for table in required_tables if table not in tables]
    
    if missing_tables:
        print(f"❌ Missing tables: {', '.join(missing_tables)}")
        return False
    else:
        print("✅ All AI tables verified successfully")
        return True


if __name__ == '__main__':
    print("🚀 Starting AI database table creation...")
    
    try:
        create_ai_tables()
        create_indexes()
        
        if verify_tables():
            print("\n🎉 AI database setup completed successfully!")
            print("\nNext steps:")
            print("1. Configure AI settings in the admin panel")
            print("2. Train AI models with your historical data")
            print("3. Enable AI features in your POS workflows")
            print("4. Monitor AI performance and recommendations")
        else:
            print("\n⚠️ AI database setup completed with warnings")
            
    except Exception as e:
        print(f"\n❌ AI database setup failed: {str(e)}")
        sys.exit(1)