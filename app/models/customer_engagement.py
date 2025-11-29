"""
Enhanced Customer Engagement Models
Extends the existing customer management system with comprehensive engagement features
including loyalty programs, marketing automation, feedback, and personalization.
"""

from datetime import datetime, timedelta
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import func, and_, or_
from app import db
import json

if TYPE_CHECKING:
    from app.models.customer import Customer
    from app.models.user import User
    from app.models.restaurant import Restaurant
    from app.models.order import Order
    from app.models.menu import MenuItem


# Advanced Loyalty Program Models
class LoyaltyProgram(db.Model):
    """Loyalty program configuration and management"""
    __tablename__ = 'loyalty_programs'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(db.String(100), nullable=False)
    description: Mapped[str] = mapped_column(db.Text, nullable=True)
    
    # Program Configuration
    points_per_currency: Mapped[float] = mapped_column(db.Numeric(5, 2), default=1.0)
    currency_per_point: Mapped[float] = mapped_column(db.Numeric(5, 2), default=0.01)
    welcome_bonus_points: Mapped[int] = mapped_column(db.Integer, default=0)
    referral_bonus_points: Mapped[int] = mapped_column(db.Integer, default=0)
    birthday_bonus_points: Mapped[int] = mapped_column(db.Integer, default=0)
    
    # Tier Configuration
    tier_thresholds: Mapped[str] = mapped_column(db.Text, nullable=True)  # JSON
    tier_benefits: Mapped[str] = mapped_column(db.Text, nullable=True)    # JSON
    
    # Gamification
    badges_enabled: Mapped[bool] = mapped_column(db.Boolean, default=True)
    achievements_enabled: Mapped[bool] = mapped_column(db.Boolean, default=True)
    leaderboard_enabled: Mapped[bool] = mapped_column(db.Boolean, default=False)
    
    # System Fields
    restaurant_id: Mapped[int] = mapped_column(db.Integer, db.ForeignKey('restaurants.id'), nullable=False)
    is_active: Mapped[bool] = mapped_column(db.Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(db.DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    restaurant = relationship('Restaurant', back_populates='loyalty_programs')
    tiers = relationship('LoyaltyTier', back_populates='program', lazy='dynamic')
    badges = relationship('LoyaltyBadge', back_populates='program', lazy='dynamic')
    rewards = relationship('LoyaltyReward', back_populates='program', lazy='dynamic')
    
    def get_tier_thresholds(self) -> dict:
        """Get tier thresholds as dictionary"""
        if self.tier_thresholds:
            return json.loads(self.tier_thresholds)
        return {
            'bronze': 0,
            'silver': 500,
            'gold': 1500,
            'platinum': 3000
        }
    
    def set_tier_thresholds(self, thresholds: dict):
        """Set tier thresholds from dictionary"""
        self.tier_thresholds = json.dumps(thresholds)
    
    def get_tier_benefits(self) -> dict:
        """Get tier benefits as dictionary"""
        if self.tier_benefits:
            return json.loads(self.tier_benefits)
        return {}
    
    def set_tier_benefits(self, benefits: dict):
        """Set tier benefits from dictionary"""
        self.tier_benefits = json.dumps(benefits)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'points_per_currency': float(self.points_per_currency),
            'currency_per_point': float(self.currency_per_point),
            'welcome_bonus_points': self.welcome_bonus_points,
            'referral_bonus_points': self.referral_bonus_points,
            'birthday_bonus_points': self.birthday_bonus_points,
            'tier_thresholds': self.get_tier_thresholds(),
            'tier_benefits': self.get_tier_benefits(),
            'badges_enabled': self.badges_enabled,
            'achievements_enabled': self.achievements_enabled,
            'leaderboard_enabled': self.leaderboard_enabled,
            'restaurant_id': self.restaurant_id,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class LoyaltyTier(db.Model):
    """Loyalty program tiers"""
    __tablename__ = 'loyalty_tiers'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    program_id: Mapped[int] = mapped_column(db.Integer, db.ForeignKey('loyalty_programs.id'), nullable=False)
    name: Mapped[str] = mapped_column(db.String(50), nullable=False)
    level: Mapped[int] = mapped_column(db.Integer, nullable=False)
    min_points: Mapped[int] = mapped_column(db.Integer, default=0)
    
    # Benefits
    points_multiplier: Mapped[float] = mapped_column(db.Numeric(3, 2), default=1.0)
    discount_percentage: Mapped[float] = mapped_column(db.Numeric(5, 2), default=0.0)
    free_delivery: Mapped[bool] = mapped_column(db.Boolean, default=False)
    exclusive_offers: Mapped[bool] = mapped_column(db.Boolean, default=False)
    priority_service: Mapped[bool] = mapped_column(db.Boolean, default=False)
    
    # Additional Benefits (JSON)
    additional_benefits: Mapped[str] = mapped_column(db.Text, nullable=True)
    
    # Visual Settings
    color: Mapped[str] = mapped_column(db.String(7), default='#808080')
    icon: Mapped[str] = mapped_column(db.String(50), nullable=True)
    
    # System Fields
    is_active: Mapped[bool] = mapped_column(db.Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    program = relationship('LoyaltyProgram', back_populates='tiers')
    
    def get_additional_benefits(self) -> list:
        """Get additional benefits as list"""
        if self.additional_benefits:
            return json.loads(self.additional_benefits)
        return []
    
    def set_additional_benefits(self, benefits: list):
        """Set additional benefits from list"""
        self.additional_benefits = json.dumps(benefits)


class LoyaltyBadge(db.Model):
    """Achievement badges for gamification"""
    __tablename__ = 'loyalty_badges'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    program_id: Mapped[int] = mapped_column(db.Integer, db.ForeignKey('loyalty_programs.id'), nullable=False)
    name: Mapped[str] = mapped_column(db.String(100), nullable=False)
    description: Mapped[str] = mapped_column(db.Text, nullable=True)
    
    # Badge Criteria
    criteria_type: Mapped[str] = mapped_column(db.Enum('orders', 'spending', 'visits', 'referrals', 'streak', 'special'), nullable=False)
    criteria_value: Mapped[int] = mapped_column(db.Integer, nullable=False)
    time_period: Mapped[str] = mapped_column(db.Enum('all_time', 'yearly', 'monthly', 'weekly'), default='all_time')
    
    # Rewards
    points_reward: Mapped[int] = mapped_column(db.Integer, default=0)
    discount_reward: Mapped[float] = mapped_column(db.Numeric(5, 2), default=0.0)
    
    # Visual
    icon: Mapped[str] = mapped_column(db.String(100), nullable=True)
    color: Mapped[str] = mapped_column(db.String(7), default='#FFD700')
    
    # System Fields
    is_active: Mapped[bool] = mapped_column(db.Boolean, default=True)
    is_secret: Mapped[bool] = mapped_column(db.Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    program = relationship('LoyaltyProgram', back_populates='badges')
    customer_badges = relationship('CustomerBadge', back_populates='badge')


class CustomerBadge(db.Model):
    """Customer earned badges"""
    __tablename__ = 'customer_badges'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    badge_id: Mapped[int] = mapped_column(db.Integer, db.ForeignKey('loyalty_badges.id'), nullable=False)
    earned_at: Mapped[datetime] = mapped_column(db.DateTime, default=datetime.utcnow)
    
    # Progress tracking
    progress_current: Mapped[int] = mapped_column(db.Integer, default=0)
    progress_target: Mapped[int] = mapped_column(db.Integer, default=0)
    
    # Relationships
    customer = relationship('Customer', back_populates='badges')
    badge = relationship('LoyaltyBadge', back_populates='customer_badges')


class LoyaltyReward(db.Model):
    """Redeemable rewards in loyalty program"""
    __tablename__ = 'loyalty_rewards'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    program_id: Mapped[int] = mapped_column(db.Integer, db.ForeignKey('loyalty_programs.id'), nullable=False)
    name: Mapped[str] = mapped_column(db.String(100), nullable=False)
    description: Mapped[str] = mapped_column(db.Text, nullable=True)
    
    # Reward Configuration
    reward_type: Mapped[str] = mapped_column(db.Enum('discount', 'free_item', 'free_delivery', 'upgrade', 'experience'), nullable=False)
    points_cost: Mapped[int] = mapped_column(db.Integer, nullable=False)
    discount_value: Mapped[float] = mapped_column(db.Numeric(5, 2), nullable=True)
    discount_type: Mapped[str] = mapped_column(db.Enum('percentage', 'fixed'), nullable=True)
    
    # Item restrictions
    applicable_items: Mapped[str] = mapped_column(db.Text, nullable=True)  # JSON list of item IDs
    applicable_categories: Mapped[str] = mapped_column(db.Text, nullable=True)  # JSON list of category IDs
    min_order_value: Mapped[float] = mapped_column(db.Numeric(10, 2), nullable=True)
    
    # Availability
    quantity_available: Mapped[int] = mapped_column(db.Integer, nullable=True)
    quantity_claimed: Mapped[int] = mapped_column(db.Integer, default=0)
    valid_from: Mapped[datetime] = mapped_column(db.DateTime, nullable=True)
    valid_until: Mapped[datetime] = mapped_column(db.DateTime, nullable=True)
    
    # System Fields
    is_active: Mapped[bool] = mapped_column(db.Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    program = relationship('LoyaltyProgram', back_populates='rewards')
    redemptions = relationship('RewardRedemption', back_populates='reward')
    
    def get_applicable_items(self) -> list:
        """Get applicable items as list"""
        if self.applicable_items:
            return json.loads(self.applicable_items)
        return []
    
    def set_applicable_items(self, items: list):
        """Set applicable items from list"""
        self.applicable_items = json.dumps(items)
    
    def get_applicable_categories(self) -> list:
        """Get applicable categories as list"""
        if self.applicable_categories:
            return json.loads(self.applicable_categories)
        return []
    
    def set_applicable_categories(self, categories: list):
        """Set applicable categories from list"""
        self.applicable_categories = json.dumps(categories)


class RewardRedemption(db.Model):
    """Customer reward redemptions"""
    __tablename__ = 'reward_redemptions'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    reward_id: Mapped[int] = mapped_column(db.Integer, db.ForeignKey('loyalty_rewards.id'), nullable=False)
    points_used: Mapped[int] = mapped_column(db.Integer, nullable=False)
    
    # Redemption Details
    redemption_code: Mapped[str] = mapped_column(db.String(20), unique=True, nullable=True)
    order_id: Mapped[int] = mapped_column(db.Integer, db.ForeignKey('orders.id'), nullable=True)
    used_at: Mapped[datetime] = mapped_column(db.DateTime, nullable=True)
    expires_at: Mapped[datetime] = mapped_column(db.DateTime, nullable=True)
    
    # System Fields
    status: Mapped[str] = mapped_column(db.Enum('pending', 'used', 'expired', 'cancelled'), default='pending')
    created_at: Mapped[datetime] = mapped_column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    customer = relationship('Customer', back_populates='reward_redemptions')
    reward = relationship('LoyaltyReward', back_populates='redemptions')
    order = relationship('Order', back_populates='reward_redemptions')


# Marketing Automation Models
class MarketingCampaign(db.Model):
    """Marketing campaigns for customer engagement"""
    __tablename__ = 'marketing_campaigns'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(db.String(100), nullable=False)
    description: Mapped[str] = mapped_column(db.Text, nullable=True)
    campaign_type: Mapped[str] = mapped_column(db.Enum('email', 'sms', 'whatsapp', 'push', 'multi_channel'), nullable=False)
    
    # Campaign Configuration
    target_audience: Mapped[str] = mapped_column(db.Text, nullable=True)  # JSON criteria
    message_template: Mapped[str] = mapped_column(db.Text, nullable=False)
    subject_template: Mapped[str] = mapped_column(db.String(200), nullable=True)
    
    # Scheduling
    schedule_type: Mapped[str] = mapped_column(db.Enum('immediate', 'scheduled', 'recurring', 'triggered'), default='immediate')
    scheduled_at: Mapped[datetime] = mapped_column(db.DateTime, nullable=True)
    recurring_pattern: Mapped[str] = mapped_column(db.Text, nullable=True)  # JSON recurrence rules
    trigger_conditions: Mapped[str] = mapped_column(db.Text, nullable=True)  # JSON trigger rules
    
    # A/B Testing
    is_ab_test: Mapped[bool] = mapped_column(db.Boolean, default=False)
    variant_a_template: Mapped[str] = mapped_column(db.Text, nullable=True)
    variant_b_template: Mapped[str] = mapped_column(db.Text, nullable=True)
    test_percentage: Mapped[float] = mapped_column(db.Numeric(5, 2), default=50.0)
    
    # Performance Tracking
    sent_count: Mapped[int] = mapped_column(db.Integer, default=0)
    delivered_count: Mapped[int] = mapped_column(db.Integer, default=0)
    opened_count: Mapped[int] = mapped_column(db.Integer, default=0)
    clicked_count: Mapped[int] = mapped_column(db.Integer, default=0)
    converted_count: Mapped[int] = mapped_column(db.Integer, default=0)
    
    # System Fields
    restaurant_id: Mapped[int] = mapped_column(db.Integer, db.ForeignKey('restaurants.id'), nullable=False)
    created_by: Mapped[int] = mapped_column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    status: Mapped[str] = mapped_column(db.Enum('draft', 'scheduled', 'active', 'paused', 'completed', 'cancelled'), default='draft')
    created_at: Mapped[datetime] = mapped_column(db.DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    restaurant = relationship('Restaurant', back_populates='marketing_campaigns')
    creator = relationship('User', back_populates='marketing_campaigns')
    messages = relationship('CampaignMessage', back_populates='campaign', lazy='dynamic')
    
    def get_target_audience(self) -> dict:
        """Get target audience criteria as dictionary"""
        if self.target_audience:
            return json.loads(self.target_audience)
        return {}
    
    def set_target_audience(self, audience: dict):
        """Set target audience criteria from dictionary"""
        self.target_audience = json.dumps(audience)
    
    def get_recurring_pattern(self) -> dict:
        """Get recurring pattern as dictionary"""
        if self.recurring_pattern:
            return json.loads(self.recurring_pattern)
        return {}
    
    def set_recurring_pattern(self, pattern: dict):
        """Set recurring pattern from dictionary"""
        self.recurring_pattern = json.dumps(pattern)
    
    def get_trigger_conditions(self) -> dict:
        """Get trigger conditions as dictionary"""
        if self.trigger_conditions:
            return json.loads(self.trigger_conditions)
        return {}
    
    def set_trigger_conditions(self, conditions: dict):
        """Set trigger conditions from dictionary"""
        self.trigger_conditions = json.dumps(conditions)


class CampaignMessage(db.Model):
    """Individual messages sent as part of campaigns"""
    __tablename__ = 'campaign_messages'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    campaign_id: Mapped[int] = mapped_column(db.Integer, db.ForeignKey('marketing_campaigns.id'), nullable=False)
    customer_id: Mapped[int] = mapped_column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    
    # Message Details
    recipient: Mapped[str] = mapped_column(db.String(200), nullable=False)
    subject: Mapped[str] = mapped_column(db.String(200), nullable=True)
    content: Mapped[str] = mapped_column(db.Text, nullable=False)
    
    # Tracking
    sent_at: Mapped[datetime] = mapped_column(db.DateTime, nullable=True)
    delivered_at: Mapped[datetime] = mapped_column(db.DateTime, nullable=True)
    opened_at: Mapped[datetime] = mapped_column(db.DateTime, nullable=True)
    clicked_at: Mapped[datetime] = mapped_column(db.DateTime, nullable=True)
    
    # A/B Testing
    variant: Mapped[str] = mapped_column(db.Enum('control', 'variant_a', 'variant_b'), default='control')
    
    # System Fields
    status: Mapped[str] = mapped_column(db.Enum('pending', 'sent', 'delivered', 'opened', 'clicked', 'bounced', 'failed'), default='pending')
    created_at: Mapped[datetime] = mapped_column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    campaign = relationship('MarketingCampaign', back_populates='messages')
    customer = relationship('Customer', back_populates='campaign_messages')


# Customer Feedback System Models
class CustomerFeedback(db.Model):
    """Customer feedback and reviews"""
    __tablename__ = 'customer_feedback'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(db.Integer, db.ForeignKey('customers.id'), nullable=True)
    order_id: Mapped[int] = mapped_column(db.Integer, db.ForeignKey('orders.id'), nullable=True)
    
    # Feedback Content
    feedback_type: Mapped[str] = mapped_column(db.Enum('rating', 'review', 'complaint', 'suggestion', 'compliment'), nullable=False)
    overall_rating: Mapped[int] = mapped_column(db.Integer, nullable=True)  # 1-5 scale
    food_rating: Mapped[int] = mapped_column(db.Integer, nullable=True)
    service_rating: Mapped[int] = mapped_column(db.Integer, nullable=True)
    ambiance_rating: Mapped[int] = mapped_column(db.Integer, nullable=True)
    value_rating: Mapped[int] = mapped_column(db.Integer, nullable=True)
    
    # Text Feedback
    title: Mapped[str] = mapped_column(db.String(200), nullable=True)
    comments: Mapped[str] = mapped_column(db.Text, nullable=True)
    
    # AI Analysis
    sentiment_score: Mapped[float] = mapped_column(db.Numeric(3, 2), nullable=True)
    sentiment_label: Mapped[str] = mapped_column(db.Enum('positive', 'negative', 'neutral'), nullable=True)
    topics: Mapped[str] = mapped_column(db.Text, nullable=True)  # JSON list of topics
    emotions: Mapped[str] = mapped_column(db.Text, nullable=True)  # JSON list of emotions
    
    # Resolution
    status: Mapped[str] = mapped_column(db.Enum('pending', 'acknowledged', 'investigating', 'resolved', 'closed'), default='pending')
    priority: Mapped[str] = mapped_column(db.Enum('low', 'medium', 'high', 'urgent'), default='medium')
    assigned_to: Mapped[int] = mapped_column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    resolution_notes: Mapped[str] = mapped_column(db.Text, nullable=True)
    resolved_at: Mapped[datetime] = mapped_column(db.DateTime, nullable=True)
    
    # System Fields
    restaurant_id: Mapped[int] = mapped_column(db.Integer, db.ForeignKey('restaurants.id'), nullable=False)
    created_at: Mapped[datetime] = mapped_column(db.DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    customer = relationship('Customer', back_populates='feedback')
    order = relationship('Order', back_populates='feedback')
    restaurant = relationship('Restaurant', back_populates='feedback')
    assignee = relationship('User', back_populates='assigned_feedback')
    responses = relationship('FeedbackResponse', back_populates='feedback', lazy='dynamic')
    
    def get_topics(self) -> list:
        """Get topics as list"""
        if self.topics:
            return json.loads(self.topics)
        return []
    
    def set_topics(self, topics: list):
        """Set topics from list"""
        self.topics = json.dumps(topics)
    
    def get_emotions(self) -> list:
        """Get emotions as list"""
        if self.emotions:
            return json.loads(self.emotions)
        return []
    
    def set_emotions(self, emotions: list):
        """Set emotions from list"""
        self.emotions = json.dumps(emotions)


class FeedbackResponse(db.Model):
    """Responses to customer feedback"""
    __tablename__ = 'feedback_responses'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    feedback_id: Mapped[int] = mapped_column(db.Integer, db.ForeignKey('customer_feedback.id'), nullable=False)
    responder_id: Mapped[int] = mapped_column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Response Details
    response_type: Mapped[str] = mapped_column(db.Enum('acknowledgment', 'investigation', 'resolution', 'follow_up'), nullable=False)
    message: Mapped[str] = mapped_column(db.Text, nullable=False)
    
    # Communication
    communication_channel: Mapped[str] = mapped_column(db.Enum('email', 'phone', 'sms', 'whatsapp', 'in_person'), nullable=False)
    communicated_at: Mapped[datetime] = mapped_column(db.DateTime, nullable=True)
    
    # System Fields
    created_at: Mapped[datetime] = mapped_column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    feedback = relationship('CustomerFeedback', back_populates='responses')
    responder = relationship('User', back_populates='feedback_responses')


# Personalization Engine Models
class CustomerPreference(db.Model):
    """Customer preferences for personalization"""
    __tablename__ = 'customer_preferences'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    
    # Preference Categories
    preference_type: Mapped[str] = mapped_column(db.Enum('dietary', 'cuisine', 'price_range', 'spice_level', 'portion_size', 'occasion', 'allergies'), nullable=False)
    preference_value: Mapped[str] = mapped_column(db.String(200), nullable=False)
    
    # Preference Strength
    strength: Mapped[float] = mapped_column(db.Numeric(3, 2), default=1.0)  # 0.0 to 1.0
    confidence: Mapped[float] = mapped_column(db.Numeric(3, 2), default=0.5)  # 0.0 to 1.0
    
    # Source
    source: Mapped[str] = mapped_column(db.Enum('explicit', 'inferred', 'behavioral', 'survey'), nullable=False)
    last_updated: Mapped[datetime] = mapped_column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    customer = relationship('Customer', back_populates='preferences')


class PersonalizedRecommendation(db.Model):
    """AI-powered personalized recommendations"""
    __tablename__ = 'personalized_recommendations'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    
    # Recommendation Details
    recommendation_type: Mapped[str] = mapped_column(db.Enum('menu_item', 'category', 'combo', 'promotion', 'experience'), nullable=False)
    item_id: Mapped[int] = mapped_column(db.Integer, db.ForeignKey('menu_items.id'), nullable=True)
    category_id: Mapped[int] = mapped_column(db.Integer, nullable=True)
    
    # Recommendation Logic
    score: Mapped[float] = mapped_column(db.Numeric(5, 2), nullable=False)
    reason: Mapped[str] = mapped_column(db.String(500), nullable=True)
    context: Mapped[str] = mapped_column(db.Text, nullable=True)  # JSON context data
    
    # Performance Tracking
    shown_count: Mapped[int] = mapped_column(db.Integer, default=0)
    clicked_count: Mapped[int] = mapped_column(db.Integer, default=0)
    converted_count: Mapped[int] = mapped_column(db.Integer, default=0)
    
    # Validity
    valid_from: Mapped[datetime] = mapped_column(db.DateTime, default=datetime.utcnow)
    valid_until: Mapped[datetime] = mapped_column(db.DateTime, nullable=True)
    
    # System Fields
    algorithm_version: Mapped[str] = mapped_column(db.String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    customer = relationship('Customer', back_populates='recommendations')
    item = relationship('MenuItem', back_populates='recommendations')
    
    def get_context(self) -> dict:
        """Get context as dictionary"""
        if self.context:
            return json.loads(self.context)
        return {}
    
    def set_context(self, context: dict):
        """Set context from dictionary"""
        self.context = json.dumps(context)


# Communication Hub Models
class CustomerCommunication(db.Model):
    """Centralized customer communication tracking"""
    __tablename__ = 'customer_communications'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    
    # Communication Details
    channel: Mapped[str] = mapped_column(db.Enum('email', 'sms', 'whatsapp', 'phone', 'in_person', 'push', 'social'), nullable=False)
    direction: Mapped[str] = mapped_column(db.Enum('inbound', 'outbound'), nullable=False)
    subject: Mapped[str] = mapped_column(db.String(200), nullable=True)
    content: Mapped[str] = mapped_column(db.Text, nullable=False)
    
    # Metadata
    communication_type: Mapped[str] = mapped_column(db.Enum('marketing', 'transactional', 'service', 'feedback', 'promotional', 'informational'), nullable=False)
    campaign_id: Mapped[int] = mapped_column(db.Integer, db.ForeignKey('marketing_campaigns.id'), nullable=True)
    order_id: Mapped[int] = mapped_column(db.Integer, db.ForeignKey('orders.id'), nullable=True)
    
    # Status Tracking
    status: Mapped[str] = mapped_column(db.Enum('pending', 'sent', 'delivered', 'read', 'responded', 'failed'), default='pending')
    sent_at: Mapped[datetime] = mapped_column(db.DateTime, nullable=True)
    delivered_at: Mapped[datetime] = mapped_column(db.DateTime, nullable=True)
    read_at: Mapped[datetime] = mapped_column(db.DateTime, nullable=True)
    
    # Response Tracking
    response_required: Mapped[bool] = mapped_column(db.Boolean, default=False)
    response_received: Mapped[bool] = mapped_column(db.Boolean, default=False)
    response_deadline: Mapped[datetime] = mapped_column(db.DateTime, nullable=True)
    
    # System Fields
    created_by: Mapped[int] = mapped_column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at: Mapped[datetime] = mapped_column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    customer = relationship('Customer', back_populates='communications')
    campaign = relationship('MarketingCampaign')
    order = relationship('Order')
    creator = relationship('User')


class CommunicationTemplate(db.Model):
    """Reusable communication templates"""
    __tablename__ = 'communication_templates'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(db.String(100), nullable=False)
    description: Mapped[str] = mapped_column(db.Text, nullable=True)
    
    # Template Configuration
    channel: Mapped[str] = mapped_column(db.Enum('email', 'sms', 'whatsapp', 'push'), nullable=False)
    communication_type: Mapped[str] = mapped_column(db.Enum('marketing', 'transactional', 'service', 'feedback', 'promotional', 'informational'), nullable=False)
    
    # Content Templates
    subject_template: Mapped[str] = mapped_column(db.String(200), nullable=True)
    content_template: Mapped[str] = mapped_column(db.Text, nullable=False)
    
    # Variables
    variables: Mapped[str] = mapped_column(db.Text, nullable=True)  # JSON list of available variables
    
    # System Fields
    restaurant_id: Mapped[int] = mapped_column(db.Integer, db.ForeignKey('restaurants.id'), nullable=False)
    is_active: Mapped[bool] = mapped_column(db.Boolean, default=True)
    created_by: Mapped[int] = mapped_column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at: Mapped[datetime] = mapped_column(db.DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    restaurant = relationship('Restaurant', back_populates='communication_templates')
    creator = relationship('User', back_populates='communication_templates')
    
    def get_variables(self) -> list:
        """Get variables as list"""
        if self.variables:
            return json.loads(self.variables)
        return []
    
    def set_variables(self, variables: list):
        """Set variables from list"""
        self.variables = json.dumps(variables)


# Customer Analytics Models
class CustomerBehavior(db.Model):
    """Customer behavior tracking for analytics"""
    __tablename__ = 'customer_behaviors'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    
    # Behavior Details
    behavior_type: Mapped[str] = mapped_column(db.Enum('page_view', 'item_view', 'search', 'add_to_cart', 'remove_from_cart', 'purchase', 'review', 'share', 'login', 'logout'), nullable=False)
    behavior_data: Mapped[str] = mapped_column(db.Text, nullable=True)  # JSON behavior data
    
    # Context
    session_id: Mapped[str] = mapped_column(db.String(100), nullable=True)
    device_type: Mapped[str] = mapped_column(db.Enum('web', 'mobile', 'tablet', 'pos'), nullable=True)
    location: Mapped[str] = mapped_column(db.String(200), nullable=True)
    
    # System Fields
    created_at: Mapped[datetime] = mapped_column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    customer = relationship('Customer', back_populates='behaviors')
    
    def get_behavior_data(self) -> dict:
        """Get behavior data as dictionary"""
        if self.behavior_data:
            return json.loads(self.behavior_data)
        return {}
    
    def set_behavior_data(self, data: dict):
        """Set behavior data from dictionary"""
        self.behavior_data = json.dumps(data)


class CustomerJourney(db.Model):
    """Customer journey mapping and analysis"""
    __tablename__ = 'customer_journeys'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    
    # Journey Details
    journey_name: Mapped[str] = mapped_column(db.String(100), nullable=False)
    journey_stage: Mapped[str] = mapped_column(db.Enum('awareness', 'consideration', 'conversion', 'retention', 'advocacy'), nullable=False)
    
    # Touchpoints
    touchpoints: Mapped[str] = mapped_column(db.Text, nullable=True)  # JSON list of touchpoints
    touchpoint_data: Mapped[str] = mapped_column(db.Text, nullable=True)  # JSON touchpoint details
    
    # Metrics
    duration_minutes: Mapped[int] = mapped_column(db.Integer, nullable=True)
    conversion_value: Mapped[float] = mapped_column(db.Numeric(10, 2), nullable=True)
    
    # System Fields
    started_at: Mapped[datetime] = mapped_column(db.DateTime, nullable=True)
    completed_at: Mapped[datetime] = mapped_column(db.DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    customer = relationship('Customer', back_populates='journeys')
    
    def get_touchpoints(self) -> list:
        """Get touchpoints as list"""
        if self.touchpoints:
            return json.loads(self.touchpoints)
        return []
    
    def set_touchpoints(self, touchpoints: list):
        """Set touchpoints from list"""
        self.touchpoints = json.dumps(touchpoints)
    
    def get_touchpoint_data(self) -> dict:
        """Get touchpoint data as dictionary"""
        if self.touchpoint_data:
            return json.loads(self.touchpoint_data)
        return {}
    
    def set_touchpoint_data(self, data: dict):
        """Set touchpoint data from dictionary"""
        self.touchpoint_data = json.dumps(data)


# Integration Models
class CustomerIntegration(db.Model):
    """Third-party service integrations for customer data"""
    __tablename__ = 'customer_integrations'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    
    # Integration Details
    integration_type: Mapped[str] = mapped_column(db.Enum('email_service', 'sms_gateway', 'crm', 'social_media', 'payment', 'delivery'), nullable=False)
    provider_name: Mapped[str] = mapped_column(db.String(50), nullable=False)
    
    # Integration Data
    external_id: Mapped[str] = mapped_column(db.String(100), nullable=True)
    integration_data: Mapped[str] = mapped_column(db.Text, nullable=True)  # JSON integration-specific data
    
    # Status
    is_active: Mapped[bool] = mapped_column(db.Boolean, default=True)
    last_sync: Mapped[datetime] = mapped_column(db.DateTime, nullable=True)
    sync_status: Mapped[str] = mapped_column(db.Enum('success', 'pending', 'failed'), nullable=True)
    
    # System Fields
    created_at: Mapped[datetime] = mapped_column(db.DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    customer = relationship('Customer', back_populates='integrations')
    
    def get_integration_data(self) -> dict:
        """Get integration data as dictionary"""
        if self.integration_data:
            return json.loads(self.integration_data)
        return {}
    
    def set_integration_data(self, data: dict):
        """Set integration data from dictionary"""
        self.integration_data = json.dumps(data)