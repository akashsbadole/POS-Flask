"""
Waste-to-Profit Models for Restaurant POS System
Contains database models for waste management and profit optimization including:
- Expiry tracking
- Waste analytics
- Chef's Special items
- Sustainability metrics
- Staff training
"""

from datetime import datetime, date
from app import db
from sqlalchemy.dialects.postgresql import JSON
import json


class ExpiryTracking(db.Model):
    """Expiry tracking for inventory items"""
    __tablename__ = 'expiry_tracking'

    id = db.Column(db.Integer, primary_key=True)
    ingredient_id = db.Column(db.Integer, db.ForeignKey('ingredients.id'), nullable=False)
    batch_number = db.Column(db.String(50))
    lot_number = db.Column(db.String(50))
    expiry_date = db.Column(db.Date, nullable=False)
    quantity = db.Column(db.Numeric(10, 3), nullable=False)
    remaining_quantity = db.Column(db.Numeric(10, 3), nullable=False)
    unit_cost = db.Column(db.Numeric(10, 2), nullable=False)
    # supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.id'), nullable=True)  # Commented out until Supplier model is implemented
    supplier_id = db.Column(db.Integer, nullable=True)
    storage_location = db.Column(db.String(100))
    storage_conditions = db.Column(db.JSON)  # Temperature, humidity, etc.
    risk_level = db.Column(db.Enum('low', 'medium', 'high', 'critical'), default='low')
    alert_sent = db.Column(db.Boolean, default=False)
    alert_threshold_days = db.Column(db.Integer, default=3)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # Relationships
    ingredient = db.relationship('Ingredient', backref='expiry_tracking')
    # supplier = db.relationship('Supplier', backref='expiry_tracking')  # Commented out until Supplier model is implemented
    creator = db.relationship('User', backref='created_expiry_tracking')

    def get_days_until_expiry(self):
        """Calculate days until expiry"""
        if self.expiry_date:
            today = date.today()
            delta = self.expiry_date - today
            return delta.days
        return None

    def get_expiry_status(self):
        """Get expiry status with color coding"""
        days_until = self.get_days_until_expiry()
        if days_until is None:
            return {'status': 'unknown', 'color': '#gray', 'text': 'Unknown'}
        elif days_until < 0:
            return {'status': 'expired', 'color': '#dc3545', 'text': f'Expired {abs(days_until)} days ago'}
        elif days_until <= self.alert_threshold_days:
            return {'status': 'critical', 'color': '#dc3545', 'text': f'Expires in {days_until} days'}
        elif days_until <= self.alert_threshold_days * 2:
            return {'status': 'warning', 'color': '#ffc107', 'text': f'Expires in {days_until} days'}
        else:
            return {'status': 'good', 'color': '#28a745', 'text': f'Expires in {days_until} days'}

    def update_risk_level(self):
        """Update risk level based on days until expiry"""
        days_until = self.get_days_until_expiry()
        if days_until is None:
            self.risk_level = 'low'
        elif days_until < 0:
            self.risk_level = 'critical'
        elif days_until <= self.alert_threshold_days:
            self.risk_level = 'high'
        elif days_until <= self.alert_threshold_days * 2:
            self.risk_level = 'medium'
        else:
            self.risk_level = 'low'

    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'ingredient_id': self.ingredient_id,
            'ingredient_name': self.ingredient.name if self.ingredient else None,
            'batch_number': self.batch_number,
            'lot_number': self.lot_number,
            'expiry_date': self.expiry_date.isoformat() if self.expiry_date else None,
            'quantity': float(self.quantity),
            'remaining_quantity': float(self.remaining_quantity),
            'unit_cost': float(self.unit_cost),
            'total_value': float(self.remaining_quantity * self.unit_cost),
            'supplier_id': self.supplier_id,
            'supplier_name': None,  # Supplier relationship commented out until Supplier model is implemented
            'storage_location': self.storage_location,
            'storage_conditions': self.storage_conditions,
            'risk_level': self.risk_level,
            'days_until_expiry': self.get_days_until_expiry(),
            'expiry_status': self.get_expiry_status(),
            'alert_sent': self.alert_sent,
            'alert_threshold_days': self.alert_threshold_days,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class WasteRecord(db.Model):
    """Record of wasted ingredients"""
    __tablename__ = 'waste_records'

    id = db.Column(db.Integer, primary_key=True)
    ingredient_id = db.Column(db.Integer, db.ForeignKey('ingredients.id'), nullable=False)
    expiry_tracking_id = db.Column(db.Integer, db.ForeignKey('expiry_tracking.id'))
    quantity_wasted = db.Column(db.Numeric(10, 3), nullable=False)
    unit_cost = db.Column(db.Numeric(10, 2), nullable=False)
    total_cost = db.Column(db.Numeric(10, 2), nullable=False)
    waste_reason = db.Column(db.String(100), nullable=False)  # expiry, spoilage, damage, preparation, etc.
    waste_category = db.Column(db.String(50))  # perishable, non-perishable, prepared, etc.
    department = db.Column(db.String(50))  # kitchen, bar, storage, etc.
    photo_path = db.Column(db.String(255))  # Photo proof of waste
    notes = db.Column(db.Text)
    prevention_measures = db.Column(db.Text)
    reported_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    approved_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    waste_date = db.Column(db.Date, nullable=False, default=date.today)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    ingredient = db.relationship('Ingredient', backref='waste_records')
    expiry_tracking = db.relationship('ExpiryTracking', backref='waste_records')
    reporter = db.relationship('User', foreign_keys=[reported_by], backref='reported_waste')
    approver = db.relationship('User', foreign_keys=[approved_by], backref='approved_waste')

    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'ingredient_id': self.ingredient_id,
            'ingredient_name': self.ingredient.name if self.ingredient else None,
            'expiry_tracking_id': self.expiry_tracking_id,
            'quantity_wasted': float(self.quantity_wasted),
            'unit_cost': float(self.unit_cost),
            'total_cost': float(self.total_cost),
            'waste_reason': self.waste_reason,
            'waste_category': self.waste_category,
            'department': self.department,
            'photo_path': self.photo_path,
            'notes': self.notes,
            'prevention_measures': self.prevention_measures,
            'reported_by': self.reported_by,
            'reporter_name': self.reporter.name if self.reporter else None,
            'approved_by': self.approved_by,
            'approver_name': self.approver.name if self.approver else None,
            'waste_date': self.waste_date.isoformat() if self.waste_date else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class ChefSpecial(db.Model):
    """Chef's Special items created from near-expiry ingredients"""
    __tablename__ = 'chef_specials'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    menu_item_id = db.Column(db.Integer, db.ForeignKey('menu_items.id'))
    original_price = db.Column(db.Numeric(10, 2))
    special_price = db.Column(db.Numeric(10, 2), nullable=False)
    discount_percentage = db.Column(db.Numeric(5, 2))
    cost_savings = db.Column(db.Numeric(10, 2))
    ingredients_used = db.Column(JSON, nullable=False)  # List of ingredient IDs and quantities
    total_ingredient_cost = db.Column(db.Numeric(10, 2), nullable=False)
    profit_margin = db.Column(db.Numeric(5, 2))
    preparation_instructions = db.Column(db.Text)
    presentation_notes = db.Column(db.Text)
    dietary_info = db.Column(db.JSON)  # Vegetarian, vegan, gluten-free, etc.
    allergen_info = db.Column(db.JSON)  # Allergen information
    spice_level = db.Column(db.Enum('mild', 'medium', 'hot', 'extra_hot'), default='medium')
    status = db.Column(db.Enum('draft', 'active', 'sold_out', 'expired'), default='draft')
    priority = db.Column(db.Enum('low', 'medium', 'high', 'urgent'), default='medium')
    available_quantity = db.Column(db.Integer, default=0)
    max_quantity_per_day = db.Column(db.Integer)
    start_date = db.Column(db.Date, nullable=False, default=date.today)
    end_date = db.Column(db.Date)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    menu_item = db.relationship('MenuItem', backref='chef_specials')
    creator = db.relationship('User', backref='created_chef_specials')

    def calculate_profit_margin(self):
        """Calculate profit margin percentage"""
        if self.special_price and self.total_ingredient_cost:
            margin = ((float(self.special_price) - float(self.total_ingredient_cost)) / float(self.special_price)) * 100
            self.profit_margin = margin
            return margin
        return 0

    def calculate_cost_savings(self):
        """Calculate cost savings from using near-expiry ingredients"""
        # This would be calculated based on the potential waste cost vs. utilization
        # For now, implement a simple calculation
        if self.total_ingredient_cost:
            # Assume 30% of ingredient cost would have been wasted
            potential_waste = float(self.total_ingredient_cost) * 0.3
            self.cost_savings = potential_waste
            return potential_waste
        return 0

    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'menu_item_id': self.menu_item_id,
            'menu_item_name': self.menu_item.name if self.menu_item else None,
            'original_price': float(self.original_price) if self.original_price else None,
            'special_price': float(self.special_price),
            'discount_percentage': float(self.discount_percentage) if self.discount_percentage else None,
            'cost_savings': float(self.cost_savings) if self.cost_savings else 0,
            'ingredients_used': self.ingredients_used,
            'total_ingredient_cost': float(self.total_ingredient_cost),
            'profit_margin': float(self.profit_margin) if self.profit_margin else 0,
            'preparation_instructions': self.preparation_instructions,
            'presentation_notes': self.presentation_notes,
            'dietary_info': self.dietary_info,
            'allergen_info': self.allergen_info,
            'spice_level': self.spice_level,
            'status': self.status,
            'priority': self.priority,
            'available_quantity': self.available_quantity,
            'max_quantity_per_day': self.max_quantity_per_day,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'created_by': self.created_by,
            'creator_name': self.creator.name if self.creator else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class SustainabilityMetric(db.Model):
    """Sustainability metrics and KPIs"""
    __tablename__ = 'sustainability_metrics'

    id = db.Column(db.Integer, primary_key=True)
    metric_type = db.Column(db.String(50), nullable=False)  # waste_reduction, cost_savings, carbon_footprint, etc.
    metric_name = db.Column(db.String(100), nullable=False)
    metric_value = db.Column(db.Numeric(15, 4), nullable=False)
    metric_unit = db.Column(db.String(20))  # kg, $, CO2, %, etc.
    baseline_value = db.Column(db.Numeric(15, 4))
    target_value = db.Column(db.Numeric(15, 4))
    period_start = db.Column(db.Date, nullable=False)
    period_end = db.Column(db.Date, nullable=False)
    department = db.Column(db.String(50))
    calculation_method = db.Column(db.Text)
    data_sources = db.Column(JSON)  # Sources used for calculation
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def get_percentage_change(self):
        """Calculate percentage change from baseline"""
        if self.baseline_value and self.baseline_value != 0:
            change = ((float(self.metric_value) - float(self.baseline_value)) / float(self.baseline_value)) * 100
            return change
        return 0

    def get_target_progress(self):
        """Calculate progress towards target"""
        if self.target_value and self.baseline_value:
            total_change = float(self.target_value) - float(self.baseline_value)
            current_change = float(self.metric_value) - float(self.baseline_value)
            if total_change != 0:
                progress = (current_change / total_change) * 100
                return max(0, min(100, progress))  # Clamp between 0-100%
        return 0

    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'metric_type': self.metric_type,
            'metric_name': self.metric_name,
            'metric_value': float(self.metric_value),
            'metric_unit': self.metric_unit,
            'baseline_value': float(self.baseline_value) if self.baseline_value else None,
            'target_value': float(self.target_value) if self.target_value else None,
            'percentage_change': self.get_percentage_change(),
            'target_progress': self.get_target_progress(),
            'period_start': self.period_start.isoformat() if self.period_start else None,
            'period_end': self.period_end.isoformat() if self.period_end else None,
            'department': self.department,
            'calculation_method': self.calculation_method,
            'data_sources': self.data_sources,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class StaffTraining(db.Model):
    """Staff training modules for waste reduction"""
    __tablename__ = 'staff_training'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    training_type = db.Column(db.Enum('waste_reduction', 'inventory_management', 'food_safety', 'sustainability'), nullable=False)
    content = db.Column(db.Text)  # Training content in markdown or HTML
    video_url = db.Column(db.String(255))
    quiz_questions = db.Column(JSON)  # Quiz questions and answers
    duration_minutes = db.Column(db.Integer)
    difficulty_level = db.Column(db.Enum('beginner', 'intermediate', 'advanced'), default='beginner')
    target_roles = db.Column(JSON)  # Roles that should take this training
    is_mandatory = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    completion_threshold = db.Column(db.Integer, default=80)  # Minimum score to pass
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    creator = db.relationship('User', backref='created_training_modules')
    completions = db.relationship('StaffTrainingCompletion', backref='training', lazy='dynamic')

    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'training_type': self.training_type,
            'content': self.content,
            'video_url': self.video_url,
            'quiz_questions': self.quiz_questions,
            'duration_minutes': self.duration_minutes,
            'difficulty_level': self.difficulty_level,
            'target_roles': self.target_roles,
            'is_mandatory': self.is_mandatory,
            'is_active': self.is_active,
            'completion_threshold': self.completion_threshold,
            'created_by': self.created_by,
            'creator_name': self.creator.name if self.creator else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class StaffTrainingCompletion(db.Model):
    """Staff training completion records"""
    __tablename__ = 'staff_training_completions'

    id = db.Column(db.Integer, primary_key=True)
    training_id = db.Column(db.Integer, db.ForeignKey('staff_training.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    started_at = db.Column(db.DateTime, nullable=False)
    completed_at = db.Column(db.DateTime)
    quiz_score = db.Column(db.Integer)
    passed = db.Column(db.Boolean, default=False)
    time_spent_minutes = db.Column(db.Integer)
    feedback = db.Column(db.Text)
    rating = db.Column(db.Integer)  # 1-5 rating
    certificate_issued = db.Column(db.Boolean, default=False)
    certificate_url = db.Column(db.String(255))

    # Relationships
    user = db.relationship('User', backref='training_completions')

    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'training_id': self.training_id,
            'training_title': self.training.title if self.training else None,
            'user_id': self.user_id,
            'user_name': self.user.name if self.user else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'quiz_score': self.quiz_score,
            'passed': self.passed,
            'time_spent_minutes': self.time_spent_minutes,
            'feedback': self.feedback,
            'rating': self.rating,
            'certificate_issued': self.certificate_issued,
            'certificate_url': self.certificate_url
        }


class WasteReductionChallenge(db.Model):
    """Gamification challenges for waste reduction"""
    __tablename__ = 'waste_reduction_challenges'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    challenge_type = db.Column(db.Enum('individual', 'team', 'department'), nullable=False)
    target_metric = db.Column(db.String(50), nullable=False)  # waste_reduction, cost_savings, etc.
    target_value = db.Column(db.Numeric(15, 4), nullable=False)
    metric_unit = db.Column(db.String(20))
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    reward_type = db.Column(db.Enum('points', 'bonus', 'recognition', 'prize'), nullable=False)
    reward_value = db.Column(db.String(100))
    participation_rules = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    creator = db.relationship('User', backref='created_challenges')
    participants = db.relationship('ChallengeParticipant', backref='challenge', lazy='dynamic')

    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'challenge_type': self.challenge_type,
            'target_metric': self.target_metric,
            'target_value': float(self.target_value),
            'metric_unit': self.metric_unit,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'reward_type': self.reward_type,
            'reward_value': self.reward_value,
            'participation_rules': self.participation_rules,
            'is_active': self.is_active,
            'created_by': self.created_by,
            'creator_name': self.creator.name if self.creator else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class ChallengeParticipant(db.Model):
    """Challenge participation records"""
    __tablename__ = 'challenge_participants'

    id = db.Column(db.Integer, primary_key=True)
    challenge_id = db.Column(db.Integer, db.ForeignKey('waste_reduction_challenges.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    team_id = db.Column(db.Integer)  # For team challenges
    current_value = db.Column(db.Numeric(15, 4), default=0)
    progress_percentage = db.Column(db.Numeric(5, 2), default=0)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    completed_at = db.Column(db.DateTime)
    reward_claimed = db.Column(db.Boolean, default=False)
    notes = db.Column(db.Text)

    # Relationships
    user = db.relationship('User', backref='challenge_participations')

    def update_progress(self):
        """Update progress percentage"""
        if self.challenge and self.challenge.target_value:
            progress = (float(self.current_value) / float(self.challenge.target_value)) * 100
            self.progress_percentage = min(100, progress)  # Cap at 100%
            return self.progress_percentage
        return 0

    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'challenge_id': self.challenge_id,
            'challenge_title': self.challenge.title if self.challenge else None,
            'user_id': self.user_id,
            'user_name': self.user.name if self.user else None,
            'team_id': self.team_id,
            'current_value': float(self.current_value),
            'progress_percentage': float(self.progress_percentage),
            'joined_at': self.joined_at.isoformat() if self.joined_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'reward_claimed': self.reward_claimed,
            'notes': self.notes
        }