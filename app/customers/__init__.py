"""
Customer management module for Restaurant POS System
Handles customer information, loyalty programs, and order history
"""

from .routes import bp
from .engagement_routes import customer_engagement_bp

__all__ = ['bp', 'customer_engagement_bp']