"""
Online Ordering Module for Restaurant POS System
Handles customer-facing web ordering interface
"""

from flask import Blueprint

bp = Blueprint('online_ordering', __name__, url_prefix='/online-ordering')

from app import online_ordering