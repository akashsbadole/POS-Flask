"""
AI Services Module
Contains business logic services for AI-powered features
"""

from .upselling_service import UpsellingService
from .dynamic_pricing_service import DynamicPricingService
from .predictive_analytics_service import PredictiveAnalyticsService
from .inventory_intelligence_service import InventoryIntelligenceService
from .customer_intelligence_service import CustomerIntelligenceService

__all__ = [
    'UpsellingService',
    'DynamicPricingService', 
    'PredictiveAnalyticsService',
    'InventoryIntelligenceService',
    'CustomerIntelligenceService'
]