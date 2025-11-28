from typing import Dict, List, Any, Optional
from flask import current_app
from app import db
from app.models.setting import Setting, SettingsChangeLog
from flask_login import current_user
from datetime import datetime

class SettingsService:
    """Service for managing application settings"""
    
    # Default settings configuration
    DEFAULT_SETTINGS = {
        'general': {
            'restaurant_name': {'value': 'My Restaurant', 'type': 'string', 'desc': 'Display name for your restaurant'},
            'language': {'value': 'en', 'type': 'string', 'desc': 'Default language for system'},
            'timezone': {'value': 'Asia/Kolkata', 'type': 'string', 'desc': 'Set your local timezone'},
            'currency': {'value': 'INR', 'type': 'string', 'desc': 'Default currency for transactions'}
        },
        'business': {
            'gst_number': {'value': '', 'type': 'string', 'desc': 'Your GST registration number'},
            'tax_rate': {'value': 18.0, 'type': 'float', 'desc': 'Default tax rate for menu items'},
            'service_charge': {'value': 5.0, 'type': 'float', 'desc': 'Service charge percentage'}
        },
        'payment': {
            'cash_enabled': {'value': True, 'type': 'boolean', 'desc': 'Accept cash payments'},
            'card_enabled': {'value': True, 'type': 'boolean', 'desc': 'Accept credit/debit cards'},
            'upi_enabled': {'value': True, 'type': 'boolean', 'desc': 'Accept UPI payments'}
        },
        'notifications': {
            'low_stock_alerts': {'value': True, 'type': 'boolean', 'desc': 'Get notified when items are low in stock'},
            'order_notifications': {'value': True, 'type': 'boolean', 'desc': 'Get notified for new orders'},
            'email_notifications': {'value': True, 'type': 'boolean', 'desc': 'Receive email notifications'}
        },
        'security': {
            'two_factor_auth': {'value': False, 'type': 'boolean', 'desc': 'Add an extra layer of security'},
            'session_timeout': {'value': 30, 'type': 'integer', 'desc': 'Auto-logout after inactivity (minutes)'},
            'strong_passwords': {'value': True, 'type': 'boolean', 'desc': 'Enforce strong passwords'}
        },
        'advanced': {
            'auto_backup': {'value': True, 'type': 'boolean', 'desc': 'Automatically backup data daily'},
            'default_printer': {'value': '', 'type': 'string', 'desc': 'Select default receipt printer'},
            'debug_mode': {'value': False, 'type': 'boolean', 'desc': 'Enable detailed logging for troubleshooting'}
        }
    }
    
    @classmethod
    def initialize_default_settings(cls):
        """Initialize default settings if they don't exist"""
        for category, settings in cls.DEFAULT_SETTINGS.items():
            for key, config in settings.items():
                existing = Setting.query.filter_by(category=category, key=key).first()
                if not existing:
                    setting = Setting(
                        category=category,
                        key=key,
                        value=config['value'],
                        data_type=config['type'],
                        description=config['desc']
                    )
                    db.session.add(setting)
        db.session.commit()
    
    @classmethod
    def get_all_settings(cls) -> Dict[str, Any]:
        """Get all settings as a dictionary"""
        settings = Setting.query.all()
        result = {}
        
        for setting in settings:
            if setting.category not in result:
                result[setting.category] = {}
            result[setting.category][setting.key] = setting.get_typed_value()
        
        # Ensure all default settings exist
        for category, defaults in cls.DEFAULT_SETTINGS.items():
            if category not in result:
                result[category] = {}
            for key, config in defaults.items():
                if key not in result[category]:
                    result[category][key] = config['value']
        
        return result
    
    @classmethod
    def get_category_settings(cls, category: str) -> Dict[str, Any]:
        """Get settings for a specific category"""
        settings = Setting.query.filter_by(category=category).all()
        result = {}
        
        for setting in settings:
            result[setting.key] = setting.get_typed_value()
        
        # Ensure all default settings for this category exist
        if category in cls.DEFAULT_SETTINGS:
            for key, config in cls.DEFAULT_SETTINGS[category].items():
                if key not in result:
                    result[key] = config['value']
        
        return result
    
    @classmethod
    def get_setting(cls, category: str, key: str) -> Any:
        """Get a specific setting value"""
        setting = Setting.query.filter_by(category=category, key=key).first()
        if setting:
            return setting.get_typed_value()
        
        # Return default if not found
        if category in cls.DEFAULT_SETTINGS and key in cls.DEFAULT_SETTINGS[category]:
            return cls.DEFAULT_SETTINGS[category][key]['value']
        
        return None
    
    @classmethod
    def update_setting(cls, category: str, key: str, value: Any, user_id: Optional[int] = None, 
                     ip_address: Optional[str] = None, user_agent: Optional[str] = None) -> bool:
        """Update a specific setting"""
        try:
            # Get existing setting
            setting = Setting.query.filter_by(category=category, key=key).first()
            old_value = None
            
            if setting:
                # Check if it's a system setting
                if setting.is_system:
                    return False
                
                old_value = setting.value
                setting.set_typed_value(value)
                setting.updated_by = user_id
            else:
                # Create new setting
                default_config = cls.DEFAULT_SETTINGS.get(category, {}).get(key, {})
                setting = Setting(
                    category=category,
                    key=key,
                    value=value,
                    data_type=default_config.get('type', 'string'),
                    description=default_config.get('desc')
                )
                setting.updated_by = user_id
                db.session.add(setting)
            
            db.session.flush()  # Get the ID without committing
            
            # Log change only if we have a valid user ID
            if old_value != str(value):
                changed_by_id = user_id or (current_user.id if current_user and hasattr(current_user, 'is_authenticated') and current_user.is_authenticated else None)
                if changed_by_id is not None:
                    change_log = SettingsChangeLog(
                        setting_id=setting.id,
                        old_value=old_value,
                        new_value=str(value),
                        changed_by=changed_by_id,
                        ip_address=ip_address,
                        user_agent=user_agent
                    )
                    db.session.add(change_log)
            
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating setting {category}.{key}: {str(e)}")
            return False
    
    @classmethod
    def update_multiple_settings(cls, settings_data: Dict[str, Any], user_id: Optional[int] = None,
                              ip_address: Optional[str] = None, user_agent: Optional[str] = None) -> Dict[str, bool]:
        """Update multiple settings"""
        results = {}
        
        try:
            for category, category_settings in settings_data.items():
                for key, value in category_settings.items():
                    results[f"{category}.{key}"] = cls.update_setting(
                        category, key, value, user_id, ip_address, user_agent
                    )
            
            return results
        except Exception as e:
            current_app.logger.error(f"Error updating multiple settings: {str(e)}")
            return results
    
    @classmethod
    def reset_to_defaults(cls, category: Optional[str] = None) -> bool:
        """Reset settings to default values"""
        try:
            if category:
                # Reset specific category
                if category in cls.DEFAULT_SETTINGS:
                    for key, config in cls.DEFAULT_SETTINGS[category].items():
                        cls.update_setting(category, key, config['value'])
            else:
                # Reset all settings
                for cat, settings in cls.DEFAULT_SETTINGS.items():
                    for key, config in settings.items():
                        cls.update_setting(cat, key, config['value'])
            
            return True
        except Exception as e:
            current_app.logger.error(f"Error resetting settings: {str(e)}")
            return False
    
    @classmethod
    def get_change_log(cls, limit: int = 100) -> List[Dict[str, Any]]:
        """Get settings change log"""
        changes = SettingsChangeLog.query.order_by(SettingsChangeLog.changed_at.desc()).limit(limit).all()
        return [change.to_dict() for change in changes]
    
    @classmethod
    def export_settings(cls) -> Dict[str, Any]:
        """Export all settings"""
        return cls.get_all_settings()
    
    @classmethod
    def import_settings(cls, settings_data: Dict[str, Any], user_id: Optional[int] = None) -> Dict[str, bool]:
        """Import settings"""
        return cls.update_multiple_settings(settings_data, user_id)