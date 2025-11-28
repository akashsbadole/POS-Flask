from flask import render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from app.settings import bp
from app.models.restaurant import Restaurant
from app.services.settings_service import SettingsService
from app import db

@bp.route('/')
@login_required
def dashboard():
    """Settings dashboard page"""
    # Get restaurant information if available
    restaurant = None
    try:
        restaurant = Restaurant.query.first()
    except:
        # Restaurant model might not exist or table might not be created yet
        pass
    
    # Initialize default settings if they don't exist
    try:
        SettingsService.initialize_default_settings()
    except Exception as e:
        current_app.logger.error(f"Error initializing settings: {str(e)}")
    
    return render_template('settings/dashboard.html', 
                         restaurant=restaurant, 
                         config=current_app.config)