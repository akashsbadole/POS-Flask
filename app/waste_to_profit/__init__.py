"""
Waste-to-Profit Module for Restaurant POS System
Provides comprehensive waste management and profit optimization features including:
- Expiry tracking system with alerts
- Waste reduction analytics
- Chef's Special creation from near-expiry ingredients
- Inventory optimization
- Sustainability reporting
- Staff training and engagement
"""

from flask import Blueprint

bp = Blueprint('waste_to_profit', __name__, url_prefix='/waste-to-profit')

from app.waste_to_profit import routes