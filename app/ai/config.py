"""
AI Configuration and Settings Management
Handles configuration for all AI-powered features including:
- Feature flags for AI components
- Model configuration parameters
- AI service settings
- Performance monitoring settings
"""

import os
import json
from datetime import datetime
from typing import Dict, Any, Optional

from app import db
from app.models.setting import Setting
from app.models.ai_models import AIConfiguration


class AIConfig:
    """AI Configuration Manager"""
    
    def __init__(self):
        self.default_settings = self._get_default_settings()
        self._load_settings()
    
    def _get_default_settings(self) -> Dict[str, Any]:
        """Get default AI configuration settings"""
        return {
            # General AI Settings
            'ai_enabled': True,
            'ai_debug_mode': False,
            'ai_confidence_threshold': 0.7,
            'ai_max_recommendations': 5,
            'ai_cache_ttl': 300,  # 5 minutes
            
            # Upselling Configuration
            'upselling_enabled': True,
            'upselling_algorithm': 'collaborative_filtering',
            'upselling_min_confidence': 0.6,
            'upselling_max_items': 3,
            'upselling_boost_popular': True,
            'upselling_seasonal_weight': 0.3,
            'upselling_personalization_weight': 0.7,
            
            # Dynamic Pricing Configuration
            'dynamic_pricing_enabled': True,
            'dynamic_pricing_algorithm': 'multi_factor',
            'dynamic_pricing_min_change': 0.05,  # 5% minimum change
            'dynamic_pricing_max_change': 0.25,  # 25% maximum change
            'dynamic_pricing_time_weight': 0.2,
            'dynamic_pricing_demand_weight': 0.3,
            'dynamic_pricing_inventory_weight': 0.2,
            'dynamic_pricing_weather_weight': 0.1,
            'dynamic_pricing_event_weight': 0.2,
            
            # Predictive Analytics Configuration
            'predictive_analytics_enabled': True,
            'sales_forecast_enabled': True,
            'sales_forecast_days': 30,
            'sales_forecast_algorithm': 'arima',
            'inventory_prediction_enabled': True,
            'inventory_prediction_days': 14,
            'staff_scheduling_enabled': True,
            'staff_scheduling_algorithm': 'optimization',
            
            # Customer Intelligence Configuration
            'customer_intelligence_enabled': True,
            'customer_segmentation_enabled': True,
            'churn_prediction_enabled': True,
            'churn_prediction_days': 30,
            'clv_calculation_enabled': True,
            'sentiment_analysis_enabled': True,
            'marketing_recommendations_enabled': True,
            
            # Model Training Configuration
            'auto_retrain_enabled': True,
            'retrain_frequency_days': 7,
            'min_training_samples': 100,
            'model_validation_split': 0.2,
            'model_performance_threshold': 0.8,
            
            # Performance Monitoring
            'performance_monitoring_enabled': True,
            'prediction_logging_enabled': True,
            'ab_testing_enabled': True,
            'ab_test_sample_size': 100,
            'ab_test_duration_days': 14,
            
            # API Configuration
            'ai_api_rate_limit': 100,  # requests per minute
            'ai_api_timeout': 10,  # seconds
            'ai_api_batch_size': 50,
            
            # UI Configuration
            'show_ai_recommendations': True,
            'show_dynamic_pricing': True,
            'show_prediction_confidence': True,
            'ai_recommendation_position': 'sidebar',  # sidebar, inline, popup
            'ai_ui_theme': 'default',
            
            # Integration Configuration
            'inventory_integration_enabled': True,
            'billing_integration_enabled': True,
            'customer_integration_enabled': True,
            'notification_integration_enabled': True,
            
            # External Services
            'weather_api_enabled': False,
            'weather_api_key': '',
            'weather_api_provider': 'openweathermap',
            'competitor_monitoring_enabled': False,
            'competitor_check_frequency_hours': 24,
        }
    
    def _load_settings(self):
        """Load settings from database"""
        try:
            # Load from AIConfiguration table
            ai_configs = AIConfiguration.query.all()
            
            for config in ai_configs:
                if hasattr(self, config.config_key):
                    try:
                        # Parse JSON value
                        value = json.loads(config.config_value)
                        setattr(self, config.config_key, value)
                    except (json.JSONDecodeError, TypeError):
                        # If not JSON, use as string
                        setattr(self, config.config_key, config.config_value)
            
            # Load from Settings table for backward compatibility
            settings = Setting.query.filter(Setting.key.like('ai_%')).all()
            
            for setting in settings:
                if hasattr(self, setting.key):
                    try:
                        value = json.loads(setting.value)
                        setattr(self, setting.key, value)
                    except (json.JSONDecodeError, TypeError):
                        setattr(self, setting.key, setting.value)
                        
        except Exception as e:
            print(f"Error loading AI settings: {str(e)}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value"""
        return getattr(self, key, default)
    
    def set(self, key: str, value: Any, save_to_db: bool = True) -> bool:
        """Set a configuration value"""
        try:
            # Update in memory
            setattr(self, key, value)
            
            if save_to_db:
                # Save to AIConfiguration table
                config = AIConfiguration.query.filter_by(config_key=key).first()
                
                if config:
                    config.config_value = json.dumps(value) if not isinstance(value, str) else value
                    config.updated_at = datetime.now()
                else:
                    config = AIConfiguration(
                        config_key=key,
                        config_value=json.dumps(value) if not isinstance(value, str) else value,
                        config_type='setting',
                        is_active=True
                    )
                    db.session.add(config)
                
                db.session.commit()
            
            return True
            
        except Exception as e:
            print(f"Error setting AI configuration {key}: {str(e)}")
            db.session.rollback()
            return False
    
    def get_all(self) -> Dict[str, Any]:
        """Get all configuration values"""
        config = {}
        
        for key in self.default_settings.keys():
            config[key] = getattr(self, key, self.default_settings[key])
        
        return config
    
    def reset_to_defaults(self, save_to_db: bool = True) -> bool:
        """Reset all settings to defaults"""
        try:
            for key, value in self.default_settings.items():
                setattr(self, key, value)
                
                if save_to_db:
                    config = AIConfiguration.query.filter_by(config_key=key).first()
                    
                    if config:
                        config.config_value = json.dumps(value) if not isinstance(value, str) else value
                        config.updated_at = datetime.now()
                    else:
                        config = AIConfiguration(
                            config_key=key,
                            config_value=json.dumps(value) if not isinstance(value, str) else value,
                            config_type='setting',
                            is_active=True
                        )
                        db.session.add(config)
            
            if save_to_db:
                db.session.commit()
            
            return True
            
        except Exception as e:
            print(f"Error resetting AI configuration: {str(e)}")
            db.session.rollback()
            return False
    
    def is_feature_enabled(self, feature: str) -> bool:
        """Check if an AI feature is enabled"""
        feature_key = f"{feature}_enabled"
        return self.get(feature_key, False)
    
    def get_model_config(self, model_type: str) -> Dict[str, Any]:
        """Get configuration for a specific model type"""
        model_configs = {
            'upselling': {
                'algorithm': self.get('upselling_algorithm'),
                'min_confidence': self.get('upselling_min_confidence'),
                'max_items': self.get('upselling_max_items'),
                'boost_popular': self.get('upselling_boost_popular'),
                'seasonal_weight': self.get('upselling_seasonal_weight'),
                'personalization_weight': self.get('upselling_personalization_weight')
            },
            'dynamic_pricing': {
                'algorithm': self.get('dynamic_pricing_algorithm'),
                'min_change': self.get('dynamic_pricing_min_change'),
                'max_change': self.get('dynamic_pricing_max_change'),
                'time_weight': self.get('dynamic_pricing_time_weight'),
                'demand_weight': self.get('dynamic_pricing_demand_weight'),
                'inventory_weight': self.get('dynamic_pricing_inventory_weight'),
                'weather_weight': self.get('dynamic_pricing_weather_weight'),
                'event_weight': self.get('dynamic_pricing_event_weight')
            },
            'predictive_analytics': {
                'sales_forecast_enabled': self.get('sales_forecast_enabled'),
                'sales_forecast_days': self.get('sales_forecast_days'),
                'sales_forecast_algorithm': self.get('sales_forecast_algorithm'),
                'inventory_prediction_enabled': self.get('inventory_prediction_enabled'),
                'inventory_prediction_days': self.get('inventory_prediction_days'),
                'staff_scheduling_enabled': self.get('staff_scheduling_enabled'),
                'staff_scheduling_algorithm': self.get('staff_scheduling_algorithm')
            },
            'customer_intelligence': {
                'segmentation_enabled': self.get('customer_segmentation_enabled'),
                'churn_prediction_enabled': self.get('churn_prediction_enabled'),
                'churn_prediction_days': self.get('churn_prediction_days'),
                'clv_calculation_enabled': self.get('clv_calculation_enabled'),
                'sentiment_analysis_enabled': self.get('sentiment_analysis_enabled'),
                'marketing_recommendations_enabled': self.get('marketing_recommendations_enabled')
            }
        }
        
        return model_configs.get(model_type, {})
    
    def get_ui_config(self) -> Dict[str, Any]:
        """Get UI configuration settings"""
        return {
            'show_recommendations': self.get('show_ai_recommendations'),
            'show_dynamic_pricing': self.get('show_dynamic_pricing'),
            'show_confidence': self.get('show_prediction_confidence'),
            'recommendation_position': self.get('ai_recommendation_position'),
            'theme': self.get('ai_ui_theme')
        }
    
    def get_api_config(self) -> Dict[str, Any]:
        """Get API configuration settings"""
        return {
            'rate_limit': self.get('ai_api_rate_limit'),
            'timeout': self.get('ai_api_timeout'),
            'batch_size': self.get('ai_api_batch_size')
        }
    
    def validate_config(self, key: str, value: Any) -> tuple[bool, str]:
        """Validate a configuration value"""
        try:
            # Type validation
            if key in self.default_settings:
                default_type = type(self.default_settings[key])
                
                if not isinstance(value, default_type):
                    try:
                        # Try to convert to expected type
                        value = default_type(value)
                    except (ValueError, TypeError):
                        return False, f"Expected {default_type.__name__}, got {type(value).__name__}"
            
            # Range validation for numeric values
            if key.endswith('_threshold') or key.endswith('_confidence'):
                if isinstance(value, (int, float)) and not (0 <= value <= 1):
                    return False, "Value must be between 0 and 1"
            
            if key.endswith('_weight'):
                if isinstance(value, (int, float)) and not (0 <= value <= 1):
                    return False, "Weight must be between 0 and 1"
            
            if key.endswith('_min_change') or key.endswith('_max_change'):
                if isinstance(value, (int, float)) and not (0 <= value <= 1):
                    return False, "Change percentage must be between 0 and 1"
            
            # Specific validations
            if key == 'ai_max_recommendations' and isinstance(value, int):
                if not (1 <= value <= 20):
                    return False, "Max recommendations must be between 1 and 20"
            
            if key == 'ai_cache_ttl' and isinstance(value, int):
                if not (60 <= value <= 3600):  # 1 minute to 1 hour
                    return False, "Cache TTL must be between 60 and 3600 seconds"
            
            if key == 'ai_api_rate_limit' and isinstance(value, int):
                if not (10 <= value <= 1000):
                    return False, "Rate limit must be between 10 and 1000 requests per minute"
            
            if key == 'ai_api_timeout' and isinstance(value, int):
                if not (1 <= value <= 60):
                    return False, "Timeout must be between 1 and 60 seconds"
            
            if key == 'ai_api_batch_size' and isinstance(value, int):
                if not (1 <= value <= 100):
                    return False, "Batch size must be between 1 and 100"
            
            if key.endswith('_days') and isinstance(value, int):
                if not (1 <= value <= 365):
                    return False, "Days must be between 1 and 365"
            
            return True, "Valid"
            
        except Exception as e:
            return False, f"Validation error: {str(e)}"
    
    def export_config(self) -> str:
        """Export configuration to JSON string"""
        config = self.get_all()
        return json.dumps(config, indent=2, default=str)
    
    def import_config(self, config_json: str, merge: bool = False) -> tuple[bool, str]:
        """Import configuration from JSON string"""
        try:
            imported_config = json.loads(config_json)
            
            if not merge:
                # Reset to defaults first
                self.reset_to_defaults(save_to_db=False)
            
            # Validate and set each configuration
            for key, value in imported_config.items():
                if key in self.default_settings:
                    is_valid, message = self.validate_config(key, value)
                    if not is_valid:
                        return False, f"Invalid value for {key}: {message}"
                    
                    self.set(key, value, save_to_db=False)
            
            # Save to database
            db.session.commit()
            
            return True, "Configuration imported successfully"
            
        except json.JSONDecodeError as e:
            return False, f"Invalid JSON: {str(e)}"
        except Exception as e:
            db.session.rollback()
            return False, f"Import error: {str(e)}"


# Global AI configuration instance
ai_config = AIConfig()


def get_ai_config() -> AIConfig:
    """Get the global AI configuration instance"""
    return ai_config


def is_ai_enabled() -> bool:
    """Check if AI is globally enabled"""
    return ai_config.get('ai_enabled', False)


def is_feature_enabled(feature: str) -> bool:
    """Check if a specific AI feature is enabled"""
    return ai_config.is_feature_enabled(feature)