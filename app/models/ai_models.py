"""
AI Models for Restaurant POS System
Contains database models for AI-powered features including:
- AI model storage and versioning
- Prediction logging
- Feature store for ML models
- Customer behavior tracking
- AI configuration and settings
"""

from datetime import datetime
from app import db
from sqlalchemy.dialects.postgresql import JSON
import json


class AIModel(db.Model):
    """AI Model storage and versioning"""
    __tablename__ = 'ai_models'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, index=True)
    version = db.Column(db.String(20), nullable=False)
    model_type = db.Column(db.String(50), nullable=False)  # recommendation, pricing, prediction, etc.
    algorithm = db.Column(db.String(50), nullable=False)  # collaborative_filtering, regression, etc.
    model_path = db.Column(db.String(255), nullable=False)
    metadata_path = db.Column(db.String(255))
    parameters = db.Column(db.JSON)
    performance_metrics = db.Column(db.JSON)
    is_active = db.Column(db.Boolean, default=False, nullable=False)
    is_production = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # Relationships
    creator = db.relationship('User', foreign_keys=[created_by], backref='created_ai_models')
    predictions = db.relationship('AIPredictionLog', backref='model', lazy='dynamic')
    training_jobs = db.relationship('AITrainingJob', backref='model', lazy='dynamic')

    __table_args__ = (db.Index('idx_ai_model_name_version', 'name', 'version'),)


class AIPredictionLog(db.Model):
    """AI prediction logging for monitoring and analysis"""
    __tablename__ = 'ai_prediction_logs'

    id = db.Column(db.Integer, primary_key=True)
    model_id = db.Column(db.Integer, db.ForeignKey('ai_models.id'), nullable=False)
    prediction_type = db.Column(db.String(50), nullable=False)  # upsell, pricing, inventory, etc.
    input_data = db.Column(db.JSON, nullable=False)
    output_data = db.Column(db.JSON, nullable=False)
    confidence_score = db.Column(db.Float)
    execution_time_ms = db.Column(db.Integer)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'))
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    feedback_score = db.Column(db.Float)  # User feedback on prediction quality
    feedback_comment = db.Column(db.Text)

    # Relationships
    user = db.relationship('User')
    customer = db.relationship('Customer')
    order = db.relationship('Order')

    __table_args__ = (db.Index('idx_ai_prediction_type_date', 'prediction_type', 'created_at'),)


class AIFeatureStore(db.Model):
    """Feature store for ML models"""
    __tablename__ = 'ai_feature_store'

    id = db.Column(db.Integer, primary_key=True)
    feature_name = db.Column(db.String(100), nullable=False, index=True)
    feature_type = db.Column(db.String(50), nullable=False)  # customer, item, order, temporal
    feature_data = db.Column(db.JSON, nullable=False)
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # Relationships
    creator = db.relationship('User')

    __table_args__ = (db.Index('idx_ai_feature_name_type', 'feature_name', 'feature_type'),)


class AICustomerBehavior(db.Model):
    """Customer behavior tracking for AI models"""
    __tablename__ = 'ai_customer_behavior'

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    behavior_type = db.Column(db.String(50), nullable=False)  # browsing, ordering, feedback, etc.
    behavior_data = db.Column(db.JSON, nullable=False)
    session_id = db.Column(db.String(100))
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    customer = db.relationship('Customer', backref='ai_behaviors')
    order = db.relationship('Order')

    __table_args__ = (db.Index('idx_customer_behavior_type_date', 'customer_id', 'behavior_type', 'created_at'),)


class AIConfiguration(db.Model):
    """AI configuration and settings"""
    __tablename__ = 'ai_configurations'

    id = db.Column(db.Integer, primary_key=True)
    config_key = db.Column(db.String(100), nullable=False, unique=True, index=True)
    config_value = db.Column(db.JSON, nullable=False)
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    updated_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # Relationships
    updater = db.relationship('User')


class AITrainingJob(db.Model):
    """AI model training and evaluation jobs"""
    __tablename__ = 'ai_training_jobs'

    id = db.Column(db.Integer, primary_key=True)
    model_id = db.Column(db.Integer, db.ForeignKey('ai_models.id'), nullable=False)
    job_type = db.Column(db.String(50), nullable=False)  # training, evaluation, retraining
    status = db.Column(db.String(20), nullable=False, default='pending')  # pending, running, completed, failed
    parameters = db.Column(db.JSON)
    training_data_path = db.Column(db.String(255))
    results = db.Column(db.JSON)
    error_message = db.Column(db.Text)
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # Relationships
    creator = db.relationship('User')

    __table_args__ = (db.Index('idx_ai_training_status', 'status', 'created_at'),)


class AIABTest(db.Model):
    """A/B testing framework for AI features"""
    __tablename__ = 'ai_ab_tests'

    id = db.Column(db.Integer, primary_key=True)
    test_name = db.Column(db.String(100), nullable=False, index=True)
    feature_name = db.Column(db.String(100), nullable=False)
    control_group_config = db.Column(db.JSON, nullable=False)
    test_group_config = db.Column(db.JSON, nullable=False)
    traffic_split_percentage = db.Column(db.Integer, default=50)  # Percentage for test group
    status = db.Column(db.String(20), default='active')  # active, paused, completed
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime)
    results = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # Relationships
    creator = db.relationship('User')
    test_participants = db.relationship('AIABTestParticipant', backref='test', lazy='dynamic')

    __table_args__ = (db.Index('idx_ai_ab_test_status', 'status', 'start_date'),)


class AIABTestParticipant(db.Model):
    """A/B test participants tracking"""
    __tablename__ = 'ai_ab_test_participants'

    id = db.Column(db.Integer, primary_key=True)
    test_id = db.Column(db.Integer, db.ForeignKey('ai_ab_tests.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'))
    group_assignment = db.Column(db.String(20), nullable=False)  # control, test
    assigned_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    conversion_event = db.Column(db.String(100))  # Type of conversion event
    conversion_value = db.Column(db.Float)  # Value of conversion
    converted_at = db.Column(db.DateTime)

    # Relationships
    user = db.relationship('User')
    customer = db.relationship('Customer')

    __table_args__ = (db.Index('idx_ab_test_participant', 'test_id', 'group_assignment'),)


class AIRecommendation(db.Model):
    """AI-generated recommendations"""
    __tablename__ = 'ai_recommendations'

    id = db.Column(db.Integer, primary_key=True)
    recommendation_type = db.Column(db.String(50), nullable=False)  # upsell, combo, pricing, etc.
    source_model_id = db.Column(db.Integer, db.ForeignKey('ai_models.id'), nullable=False)
    target_customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'))
    target_user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'))
    item_id = db.Column(db.Integer, db.ForeignKey('menu_items.id'))
    recommended_items = db.Column(db.JSON)  # List of recommended item IDs and metadata
    confidence_score = db.Column(db.Float, nullable=False)
    reasoning = db.Column(db.Text)  # AI reasoning for recommendation
    status = db.Column(db.String(20), default='pending')  # pending, shown, accepted, rejected
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    shown_at = db.Column(db.DateTime)
    responded_at = db.Column(db.DateTime)

    # Relationships
    source_model = db.relationship('AIModel', backref='recommendations')
    customer = db.relationship('Customer', backref='ai_recommendations')
    user = db.relationship('User', backref='received_recommendations')
    order = db.relationship('Order')
    item = db.relationship('MenuItem')

    __table_args__ = (db.Index('idx_ai_recommendation_type_status', 'recommendation_type', 'status'),)


class AIPriceOptimization(db.Model):
    """Dynamic pricing optimization records"""
    __tablename__ = 'ai_price_optimizations'

    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('menu_items.id'), nullable=False)
    source_model_id = db.Column(db.Integer, db.ForeignKey('ai_models.id'), nullable=False)
    original_price = db.Column(db.Numeric(10, 2), nullable=False)
    optimized_price = db.Column(db.Numeric(10, 2), nullable=False)
    optimization_factors = db.Column(db.JSON)  # Factors considered (demand, inventory, time, etc.)
    confidence_score = db.Column(db.Float, nullable=False)
    demand_multiplier = db.Column(db.Float, default=1.0)
    inventory_factor = db.Column(db.Float, default=1.0)
    time_factor = db.Column(db.Float, default=1.0)
    weather_factor = db.Column(db.Float, default=1.0)
    event_factor = db.Column(db.Float, default=1.0)
    is_active = db.Column(db.Boolean, default=False, nullable=False)
    start_time = db.Column(db.DateTime)
    end_time = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # Relationships
    item = db.relationship('MenuItem', backref='price_optimizations')
    source_model = db.relationship('AIModel', backref='price_optimizations')
    creator = db.relationship('User')

    __table_args__ = (db.Index('idx_ai_price_optimization_item', 'item_id', 'is_active'),)


class AIInventoryPrediction(db.Model):
    """AI-powered inventory predictions"""
    __tablename__ = 'ai_inventory_predictions'

    id = db.Column(db.Integer, primary_key=True)
    ingredient_id = db.Column(db.Integer, db.ForeignKey('ingredients.id'), nullable=False)
    source_model_id = db.Column(db.Integer, db.ForeignKey('ai_models.id'), nullable=False)
    prediction_type = db.Column(db.String(50), nullable=False)  # demand, spoilage, reorder
    prediction_date = db.Column(db.Date, nullable=False)
    predicted_quantity = db.Column(db.Float, nullable=False)
    actual_quantity = db.Column(db.Float)  # Filled when actual is known
    confidence_score = db.Column(db.Float, nullable=False)
    prediction_factors = db.Column(db.JSON)  # Factors used in prediction
    is_alert = db.Column(db.Boolean, default=False, nullable=False)  # Alert if prediction is critical
    alert_threshold = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    acknowledged_at = db.Column(db.DateTime)

    # Relationships
    ingredient = db.relationship('Ingredient', backref='predictions')
    source_model = db.relationship('AIModel', backref='inventory_predictions')

    __table_args__ = (db.Index('idx_ai_inventory_prediction_date', 'ingredient_id', 'prediction_date'),)