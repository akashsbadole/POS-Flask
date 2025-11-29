"""
Delivery Management Module for Restaurant POS System
Handles driver management, delivery tracking, and route optimization
"""

from flask import Blueprint

bp = Blueprint('delivery', __name__, url_prefix='/delivery')

from app.delivery import routes
from app.delivery import api_routes