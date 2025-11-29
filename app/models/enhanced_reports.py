"""
Enhanced Reporting Models for Restaurant POS System
Provides comprehensive analytics and reporting capabilities
"""

from datetime import datetime, timedelta
from enum import Enum
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import func, and_, or_, desc, asc
import json
from app import db

# Analytics Data Aggregation Models

class DailySalesSummary(db.Model):
    """Daily sales summary for quick analytics"""
    __tablename__ = 'daily_sales_summaries'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    restaurant_id: Mapped[int] = mapped_column(db.Integer, db.ForeignKey('restaurants.id'), nullable=False)
    date: Mapped[datetime] = mapped_column(db.Date, nullable=False, index=True)
    
    # Sales Metrics
    total_orders: Mapped[int] = mapped_column(db.Integer, default=0)
    total_revenue: Mapped[float] = mapped_column(db.Numeric(12, 2), default=0.00)
    total_tax: Mapped[float] = mapped_column(db.Numeric(12, 2), default=0.00)
    total_discount: Mapped[float] = mapped_column(db.Numeric(12, 2), default=0.00)
    average_order_value: Mapped[float] = mapped_column(db.Numeric(10, 2), default=0.00)
    
    # Customer Metrics
    total_customers: Mapped[int] = mapped_column(db.Integer, default=0)
    new_customers: Mapped[int] = mapped_column(db.Integer, default=0)
    repeat_customers: Mapped[int] = mapped_column(db.Integer, default=0)
    
    # Hourly Breakdown (JSON)
    hourly_sales: Mapped[str] = mapped_column(db.Text)  # JSON object with hourly data
    
    # Payment Method Breakdown (JSON)
    payment_methods: Mapped[str] = mapped_column(db.Text)  # JSON object with payment data
    
    # Order Type Breakdown (JSON)
    order_types: Mapped[str] = mapped_column(db.Text)  # JSON object with order type data
    
    created_at: Mapped[datetime] = mapped_column(db.DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    restaurant = relationship('Restaurant', back_populates='daily_sales_summaries')
    
    def get_hourly_sales(self) -> Dict[str, Any]:
        """Get hourly sales data as dictionary"""
        if self.hourly_sales:
            try:
                return json.loads(self.hourly_sales)
            except (json.JSONDecodeError, TypeError):
                return {}
        return {}
    
    def set_hourly_sales(self, data: Dict[str, Any]) -> None:
        """Set hourly sales data from dictionary"""
        self.hourly_sales = json.dumps(data)
    
    def get_payment_methods(self) -> Dict[str, Any]:
        """Get payment methods data as dictionary"""
        if self.payment_methods:
            try:
                return json.loads(self.payment_methods)
            except (json.JSONDecodeError, TypeError):
                return {}
        return {}
    
    def set_payment_methods(self, data: Dict[str, Any]) -> None:
        """Set payment methods data from dictionary"""
        self.payment_methods = json.dumps(data)
    
    def get_order_types(self) -> Dict[str, Any]:
        """Get order types data as dictionary"""
        if self.order_types:
            try:
                return json.loads(self.order_types)
            except (json.JSONDecodeError, TypeError):
                return {}
        return {}
    
    def set_order_types(self, data: Dict[str, Any]) -> None:
        """Set order types data from dictionary"""
        self.order_types = json.dumps(data)

class InventoryMovement(db.Model):
    """Track inventory movements for analytics"""
    __tablename__ = 'inventory_movements'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    restaurant_id: Mapped[int] = mapped_column(db.Integer, db.ForeignKey('restaurants.id'), nullable=False)
    ingredient_id: Mapped[int] = mapped_column(db.Integer, db.ForeignKey('ingredients.id'), nullable=False)
    
    movement_type: Mapped[str] = mapped_column(db.Enum('purchase', 'sale', 'adjustment', 'waste', 'transfer', 'return'), nullable=False)
    quantity: Mapped[float] = mapped_column(db.Numeric(10, 3), nullable=False)
    unit_cost: Mapped[float] = mapped_column(db.Numeric(10, 2), default=0.00)
    total_cost: Mapped[float] = mapped_column(db.Numeric(12, 2), default=0.00)
    
    reference_id: Mapped[int] = mapped_column(db.Integer, nullable=True)  # Can reference order, purchase, etc.
    reference_type: Mapped[str] = mapped_column(db.Enum('order', 'purchase', 'adjustment', 'waste', 'transfer'), nullable=True)
    reason: Mapped[str] = mapped_column(db.String(255), nullable=True)
    
    user_id: Mapped[int] = mapped_column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at: Mapped[datetime] = mapped_column(db.DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    restaurant = relationship('Restaurant')
    ingredient = relationship('Ingredient', back_populates='movements')
    user = relationship('User', back_populates='inventory_movements')

class WasteTracking(db.Model):
    """Track food waste for analytics and cost control"""
    __tablename__ = 'waste_tracking'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    restaurant_id: Mapped[int] = mapped_column(db.Integer, db.ForeignKey('restaurants.id'), nullable=False)
    ingredient_id: Mapped[int] = mapped_column(db.Integer, db.ForeignKey('ingredients.id'), nullable=False)
    
    waste_type: Mapped[str] = mapped_column(db.Enum('spoilage', 'overportion', 'preparation', 'return', 'theft', 'other'), nullable=False)
    quantity: Mapped[float] = mapped_column(db.Numeric(10, 3), nullable=False)
    unit_cost: Mapped[float] = mapped_column(db.Numeric(10, 2), default=0.00)
    total_cost: Mapped[float] = mapped_column(db.Numeric(12, 2), default=0.00)
    
    reason: Mapped[str] = mapped_column(db.String(255), nullable=True)
    prevention_notes: Mapped[str] = mapped_column(db.Text, nullable=True)
    
    reported_by: Mapped[int] = mapped_column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    approved_by: Mapped[int] = mapped_column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    waste_date: Mapped[datetime] = mapped_column(db.DateTime, default=datetime.utcnow, index=True)
    created_at: Mapped[datetime] = mapped_column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    restaurant = relationship('Restaurant')
    ingredient = relationship('Ingredient', back_populates='waste_records')
    reporter = relationship('User', foreign_keys=[reported_by], back_populates='reported_waste')
    approver = relationship('User', foreign_keys=[approved_by], back_populates='approved_waste')

class EmployeePerformance(db.Model):
    """Track employee performance metrics"""
    __tablename__ = 'employee_performance'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    restaurant_id: Mapped[int] = mapped_column(db.Integer, db.ForeignKey('restaurants.id'), nullable=False)
    user_id: Mapped[int] = mapped_column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Performance Date
    performance_date: Mapped[datetime] = mapped_column(db.Date, nullable=False, index=True)
    
    # Sales Metrics
    orders_processed: Mapped[int] = mapped_column(db.Integer, default=0)
    revenue_generated: Mapped[float] = mapped_column(db.Numeric(12, 2), default=0.00)
    average_order_value: Mapped[float] = mapped_column(db.Numeric(10, 2), default=0.00)
    items_sold: Mapped[int] = mapped_column(db.Integer, default=0)
    
    # Efficiency Metrics
    average_order_time: Mapped[int] = mapped_column(db.Integer, default=0)  # in seconds
    upsell_revenue: Mapped[float] = mapped_column(db.Numeric(10, 2), default=0.00)
    discount_given: Mapped[float] = mapped_column(db.Numeric(10, 2), default=0.00)
    
    # Customer Service Metrics
    customer_rating: Mapped[float] = mapped_column(db.Numeric(3, 2), nullable=True)
    customer_complaints: Mapped[int] = mapped_column(db.Integer, default=0)
    customer_compliments: Mapped[int] = mapped_column(db.Integer, default=0)
    
    # Attendance Metrics
    shift_hours: Mapped[float] = mapped_column(db.Numeric(5, 2), default=0.00)
    overtime_hours: Mapped[float] = mapped_column(db.Numeric(5, 2), default=0.00)
    punctuality_score: Mapped[float] = mapped_column(db.Numeric(3, 2), default=100.00)
    
    created_at: Mapped[datetime] = mapped_column(db.DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    restaurant = relationship('Restaurant')
    employee = relationship('User', back_populates='performance_records')

class CustomerAnalytics(db.Model):
    """Customer behavior and analytics data"""
    __tablename__ = 'customer_analytics'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    restaurant_id: Mapped[int] = mapped_column(db.Integer, db.ForeignKey('restaurants.id'), nullable=False)
    customer_id: Mapped[int] = mapped_column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    
    # Analytics Date
    analytics_date: Mapped[datetime] = mapped_column(db.Date, nullable=False, index=True)
    
    # Visit Metrics
    visits_count: Mapped[int] = mapped_column(db.Integer, default=0)
    total_spent: Mapped[float] = mapped_column(db.Numeric(12, 2), default=0.00)
    average_visit_value: Mapped[float] = mapped_column(db.Numeric(10, 2), default=0.00)
    
    # Time Metrics
    visit_duration_avg: Mapped[int] = mapped_column(db.Integer, default=0)  # in minutes
    peak_visit_time: Mapped[str] = mapped_column(db.String(20), nullable=True)  # morning, afternoon, evening, night
    
    # Preferences (JSON)
    favorite_categories: Mapped[str] = mapped_column(db.Text)  # JSON array
    favorite_items: Mapped[str] = mapped_column(db.Text)  # JSON array
    preferred_payment_methods: Mapped[str] = mapped_column(db.Text)  # JSON array
    
    # Behavior Metrics
    return_frequency: Mapped[int] = mapped_column(db.Integer, default=0)  # days between visits
    loyalty_engagement: Mapped[float] = mapped_column(db.Numeric(3, 2), default=0.00)
    referral_count: Mapped[int] = mapped_column(db.Integer, default=0)
    
    created_at: Mapped[datetime] = mapped_column(db.DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    restaurant = relationship('Restaurant')
    customer = relationship('Customer', back_populates='analytics')
    
    def get_favorite_categories(self) -> List[str]:
        """Get favorite categories as list"""
        if self.favorite_categories:
            try:
                return json.loads(self.favorite_categories)
            except (json.JSONDecodeError, TypeError):
                return []
        return []
    
    def set_favorite_categories(self, categories: List[str]) -> None:
        """Set favorite categories from list"""
        self.favorite_categories = json.dumps(categories)
    
    def get_favorite_items(self) -> List[int]:
        """Get favorite items as list of IDs"""
        if self.favorite_items:
            try:
                return json.loads(self.favorite_items)
            except (json.JSONDecodeError, TypeError):
                return []
        return []
    
    def set_favorite_items(self, items: List[int]) -> None:
        """Set favorite items from list of IDs"""
        self.favorite_items = json.dumps(items)

class OperationalMetrics(db.Model):
    """Operational efficiency and performance metrics"""
    __tablename__ = 'operational_metrics'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    restaurant_id: Mapped[int] = mapped_column(db.Integer, db.ForeignKey('restaurants.id'), nullable=False)
    
    # Metrics Date
    metrics_date: Mapped[datetime] = mapped_column(db.Date, nullable=False, index=True)
    
    # Table Metrics
    table_turnover_rate: Mapped[float] = mapped_column(db.Numeric(5, 2), default=0.00)
    average_occupancy: Mapped[float] = mapped_column(db.Numeric(5, 2), default=0.00)
    peak_occupancy_time: Mapped[str] = mapped_column(db.String(20), nullable=True)
    
    # Kitchen Metrics
    average_prep_time: Mapped[int] = mapped_column(db.Integer, default=0)  # in seconds
    order_fulfillment_rate: Mapped[float] = mapped_column(db.Numeric(5, 2), default=0.00)
    kitchen_efficiency: Mapped[float] = mapped_column(db.Numeric(5, 2), default=0.00)
    
    # Staff Metrics
    staff_productivity: Mapped[float] = mapped_column(db.Numeric(5, 2), default=0.00)
    labor_cost_percentage: Mapped[float] = mapped_column(db.Numeric(5, 2), default=0.00)
    staff_satisfaction: Mapped[float] = mapped_column(db.Numeric(3, 2), nullable=True)
    
    # Equipment Metrics (JSON)
    equipment_usage: Mapped[str] = mapped_column(db.Text)  # JSON object
    maintenance_downtime: Mapped[int] = mapped_column(db.Integer, default=0)  # in minutes
    
    # Delivery Metrics (if applicable)
    delivery_performance: Mapped[str] = mapped_column(db.Text)  # JSON object
    average_delivery_time: Mapped[int] = mapped_column(db.Integer, default=0)  # in minutes
    
    created_at: Mapped[datetime] = mapped_column(db.DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    restaurant = relationship('Restaurant', back_populates='operational_metrics')
    
    def get_equipment_usage(self) -> Dict[str, Any]:
        """Get equipment usage data as dictionary"""
        if self.equipment_usage:
            try:
                return json.loads(self.equipment_usage)
            except (json.JSONDecodeError, TypeError):
                return {}
        return {}
    
    def set_equipment_usage(self, data: Dict[str, Any]) -> None:
        """Set equipment usage data from dictionary"""
        self.equipment_usage = json.dumps(data)
    
    def get_delivery_performance(self) -> Dict[str, Any]:
        """Get delivery performance data as dictionary"""
        if self.delivery_performance:
            try:
                return json.loads(self.delivery_performance)
            except (json.JSONDecodeError, TypeError):
                return {}
        return {}
    
    def set_delivery_performance(self, data: Dict[str, Any]) -> None:
        """Set delivery performance data from dictionary"""
        self.delivery_performance = json.dumps(data)

class ReportCache(db.Model):
    """Cache for complex report calculations"""
    __tablename__ = 'report_cache'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    cache_key: Mapped[str] = mapped_column(db.String(255), nullable=False, index=True)
    cache_data: Mapped[str] = mapped_column(db.Text, nullable=False)  # JSON data
    report_type: Mapped[str] = mapped_column(db.String(50), nullable=False)
    parameters: Mapped[str] = mapped_column(db.Text)  # JSON object with parameters
    
    expires_at: Mapped[datetime] = mapped_column(db.DateTime, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(db.DateTime, default=datetime.utcnow)
    hit_count: Mapped[int] = mapped_column(db.Integer, default=0)
    
    def get_cache_data(self) -> Any:
        """Get cached data"""
        if self.cache_data:
            try:
                return json.loads(self.cache_data)
            except (json.JSONDecodeError, TypeError):
                return None
        return None
    
    def set_cache_data(self, data: Any) -> None:
        """Set cached data"""
        self.cache_data = json.dumps(data)
    
    def get_parameters(self) -> Dict[str, Any]:
        """Get parameters as dictionary"""
        if self.parameters:
            try:
                return json.loads(self.parameters)
            except (json.JSONDecodeError, TypeError):
                return {}
        return {}
    
    def set_parameters(self, params: Dict[str, Any]) -> None:
        """Set parameters from dictionary"""
        self.parameters = json.dumps(params)
    
    def is_expired(self) -> bool:
        """Check if cache is expired"""
        return datetime.utcnow() > self.expires_at
    
    def increment_hit(self) -> None:
        """Increment hit count"""
        self.hit_count += 1

# Add relationships to existing models
# Note: These would need to be added to the respective model files

# For Ingredient model
# movements = relationship('InventoryMovement', back_populates='ingredient')
# waste_records = relationship('WasteTracking', back_populates='ingredient')

# For User model
# inventory_movements = relationship('InventoryMovement', back_populates='user')
# reported_waste = relationship('WasteTracking', foreign_keys=[WasteTracking.reported_by], back_populates='reporter')
# approved_waste = relationship('WasteTracking', foreign_keys=[WasteTracking.approved_by], back_populates='approver')
# performance_records = relationship('EmployeePerformance', back_populates='employee')

# For Customer model
# analytics = relationship('CustomerAnalytics', back_populates='customer')

# For Restaurant model
# daily_sales_summaries = relationship('DailySalesSummary', back_populates='restaurant')
# operational_metrics = relationship('OperationalMetrics', back_populates='restaurant')