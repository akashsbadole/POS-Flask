"""
Online Ordering Module for Restaurant POS System
Handles customer-facing web ordering interface
"""

from flask import Blueprint

bp = Blueprint('online_ordering', __name__, url_prefix='/online-ordering')

# Import routes to register them with the blueprint
from app.online_ordering import routes
