"""
Customer Engagement Services Package
Contains all services related to enhanced customer engagement features
including loyalty programs, marketing automation, feedback, personalization, analytics, communication, and integration.
"""

from .loyalty_service import LoyaltyService
from .marketing_service import MarketingService
from .feedback_service import FeedbackService
from .personalization_service import PersonalizationService
from .analytics_service import CustomerAnalyticsService
from .communication_service import CustomerCommunicationService
from .integration_service import CustomerEngagementIntegrationService

__all__ = [
    'LoyaltyService',
    'MarketingService',
    'FeedbackService',
    'PersonalizationService',
    'CustomerAnalyticsService',
    'CustomerCommunicationService',
    'CustomerEngagementIntegrationService'
]