"""
Advanced Delivery Management Models
Handles GPS tracking, driver management, route optimization, and delivery analytics
"""

from datetime import datetime, timedelta
from enum import Enum
from typing import List, Dict, Optional, TYPE_CHECKING
import json

from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey, Numeric, JSON
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
import uuid

from app import db

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.order import Order
    from app.models.customer import Customer

class DriverStatus(Enum):
    AVAILABLE = 'available'
    BUSY = 'busy'
    OFFLINE = 'offline'
    ON_BREAK = 'on_break'
    DELIVERING = 'delivering'

class DeliveryStatus(Enum):
    PENDING = 'pending'
    ASSIGNED = 'assigned'
    PICKED_UP = 'picked_up'
    IN_TRANSIT = 'in_transit'
    DELIVERED = 'delivered'
    CANCELLED = 'cancelled'
    FAILED = 'failed'

class RouteStatus(Enum):
    PLANNED = 'planned'
    ACTIVE = 'active'
    COMPLETED = 'completed'
    CANCELLED = 'cancelled'

class RatingType(Enum):
    DELIVERY_SPEED = 'delivery_speed'
    PROFESSIONALISM = 'professionalism'
    ORDER_ACCURACY = 'order_accuracy'
    OVERALL = 'overall'

class Driver(db.Model):
    """Enhanced driver model with GPS tracking and performance metrics"""
    __tablename__ = 'drivers'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id'), unique=True, nullable=False)
    employee_code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    license_number: Mapped[str] = mapped_column(String(50), nullable=False)
    license_expiry: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    vehicle_type: Mapped[str] = mapped_column(String(50), nullable=False)  # bike, car, scooter
    vehicle_number: Mapped[str] = mapped_column(String(20), nullable=False)
    vehicle_details: Mapped[Dict] = mapped_column(JSON, default={})  # make, model, year, color
    status: Mapped[str] = mapped_column(String(20), default=DriverStatus.OFFLINE.value)
    current_location_lat: Mapped[float] = mapped_column(Float, nullable=True)
    current_location_lng: Mapped[float] = mapped_column(Float, nullable=True)
    last_location_update: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    hire_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    base_salary: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    commission_rate: Mapped[float] = mapped_column(Numeric(5, 2), default=5.0)  # percentage
    max_deliveries_per_shift: Mapped[int] = mapped_column(Integer, default=20)
    shift_start_time: Mapped[str] = mapped_column(String(5), nullable=True)  # HH:MM
    shift_end_time: Mapped[str] = mapped_column(String(5), nullable=True)    # HH:MM
    working_days: Mapped[str] = mapped_column(String(20), default='mon,tue,wed,thu,fri,sat,sun')
    emergency_contact: Mapped[Dict] = mapped_column(JSON, default={})
    documents: Mapped[Dict] = mapped_column(JSON, default={})  # license, insurance, etc.
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship('User', backref='driver_profile')
    deliveries = relationship('Delivery', backref='driver', lazy='dynamic')
    routes = relationship('DeliveryRoute', backref='driver', lazy='dynamic')
    ratings = relationship('DriverRating', backref='driver', lazy='dynamic')
    performance_metrics = relationship('DriverPerformance', backref='driver', lazy='dynamic')
    earnings = relationship('DriverEarning', backref='driver', lazy='dynamic')
    location_history = relationship('DriverLocation', backref='driver', lazy='dynamic')
    
    def __repr__(self):
        return f'<Driver {self.user.name if self.user else "Unknown"} ({self.status})>'
    
    def get_current_location(self):
        """Get current driver location"""
        if self.current_location_lat and self.current_location_lng:
            return {
                'lat': self.current_location_lat,
                'lng': self.current_location_lng,
                'timestamp': self.last_location_update.isoformat() if self.last_location_update else None
            }
        return None
    
    def update_location(self, lat: float, lng: float):
        """Update driver location"""
        self.current_location_lat = lat
        self.current_location_lng = lng
        self.last_location_update = datetime.utcnow()
        
        # Add to location history
        location = DriverLocation(
            driver_id=self.id,
            latitude=lat,
            longitude=lng,
            timestamp=datetime.utcnow()
        )
        db.session.add(location)
    
    def get_average_rating(self, rating_type: Optional[RatingType] = None):
        """Get average rating for driver"""
        query = self.ratings
        if rating_type:
            query = query.filter_by(rating_type=rating_type.value)
        
        ratings = query.all()
        if not ratings:
            return 0.0
        
        return sum(r.rating for r in ratings) / len(ratings)
    
    def get_today_deliveries(self):
        """Get today's delivery count"""
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        return self.deliveries.filter(
            Delivery.created_at >= today,
            Delivery.status != DeliveryStatus.CANCELLED.value
        ).count()
    
    def get_monthly_earnings(self, year: Optional[int] = None, month: Optional[int] = None):
        """Get monthly earnings"""
        if not year:
            year = datetime.now().year
        if not month:
            month = datetime.now().month
            
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1)
        else:
            end_date = datetime(year, month + 1, 1)
        
        earnings = self.earnings.filter(
            DriverEarning.created_at >= start_date,
            DriverEarning.created_at < end_date
        ).all()
        
        return sum(e.amount for e in earnings)
    
    def is_available(self):
        """Check if driver is available for delivery"""
        return self.status == DriverStatus.AVAILABLE.value and self.is_active
    
    def to_dict(self):
        """Convert driver to dictionary"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.user.name if self.user else None,
            'email': self.user.email if self.user else None,
            'phone': self.user.phone if self.user else None,
            'employee_code': self.employee_code,
            'license_number': self.license_number,
            'license_expiry': self.license_expiry.isoformat() if self.license_expiry else None,
            'vehicle_type': self.vehicle_type,
            'vehicle_number': self.vehicle_number,
            'vehicle_details': self.vehicle_details,
            'status': self.status,
            'current_location': self.get_current_location(),
            'is_active': self.is_active,
            'hire_date': self.hire_date.isoformat() if self.hire_date else None,
            'base_salary': float(self.base_salary),
            'commission_rate': float(self.commission_rate),
            'max_deliveries_per_shift': self.max_deliveries_per_shift,
            'shift_start_time': self.shift_start_time,
            'shift_end_time': self.shift_end_time,
            'working_days': self.working_days,
            'emergency_contact': self.emergency_contact,
            'documents': self.documents,
            'average_rating': self.get_average_rating(),
            'today_deliveries': self.get_today_deliveries(),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class Delivery(db.Model):
    """Enhanced delivery model with GPS tracking and ETA"""
    __tablename__ = 'deliveries'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(Integer, ForeignKey('orders.id'), nullable=False)
    driver_id: Mapped[int] = mapped_column(Integer, ForeignKey('drivers.id'), nullable=True)
    delivery_number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default=DeliveryStatus.PENDING.value)
    pickup_address: Mapped[Dict] = mapped_column(JSON, default={})
    delivery_address: Mapped[Dict] = mapped_column(JSON, nullable=False)
    pickup_lat: Mapped[float] = mapped_column(Float, nullable=True)
    pickup_lng: Mapped[float] = mapped_column(Float, nullable=True)
    delivery_lat: Mapped[float] = mapped_column(Float, nullable=True)
    delivery_lng: Mapped[float] = mapped_column(Float, nullable=True)
    estimated_distance: Mapped[float] = mapped_column(Numeric(8, 2), nullable=True)  # in km
    estimated_duration: Mapped[int] = mapped_column(Integer, nullable=True)  # in minutes
    actual_distance: Mapped[float] = mapped_column(Numeric(8, 2), nullable=True)
    actual_duration: Mapped[int] = mapped_column(Integer, nullable=True)
    pickup_time: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    delivery_time: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    assigned_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    delivery_notes: Mapped[str] = mapped_column(Text, nullable=True)
    customer_contact: Mapped[str] = mapped_column(String(20), nullable=True)
    special_instructions: Mapped[str] = mapped_column(Text, nullable=True)
    contactless_delivery: Mapped[bool] = mapped_column(Boolean, default=False)
    delivery_photo_url: Mapped[str] = mapped_column(String(500), nullable=True)
    signature_url: Mapped[str] = mapped_column(String(500), nullable=True)
    route_id: Mapped[int] = mapped_column(Integer, ForeignKey('delivery_routes.id'), nullable=True)
    priority: Mapped[int] = mapped_column(Integer, default=1)  # 1=low, 2=medium, 3=high
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    order = relationship('Order', backref='delivery')
    route = relationship('DeliveryRoute', backref='deliveries')
    tracking_updates = relationship('DeliveryTracking', backref='delivery', lazy='dynamic')
    feedback = relationship('DeliveryFeedback', backref='delivery', lazy='dynamic')
    
    def __init__(self, **kwargs):
        super(Delivery, self).__init__(**kwargs)
        if not self.delivery_number:
            self.delivery_number = self.generate_delivery_number()
    
    def generate_delivery_number(self):
        """Generate unique delivery number"""
        today = datetime.now().strftime('%Y%m%d')
        today_deliveries = Delivery.query.filter(
            Delivery.created_at >= datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        ).count()
        
        attempts = 0
        while attempts < 100:
            candidate = f"DEL{today}{today_deliveries + attempts + 1:03d}"
            existing = Delivery.query.filter_by(delivery_number=candidate).first()
            if not existing:
                return candidate
            attempts += 1
        
        import time
        return f"DEL{today}{int(time.time()) % 1000:03d}"
    
    def assign_driver(self, driver_id: int):
        """Assign driver to delivery"""
        self.driver_id = driver_id
        self.status = DeliveryStatus.ASSIGNED.value
        self.assigned_at = datetime.utcnow()
        
        # Update driver status
        driver = Driver.query.get(driver_id)
        if driver:
            driver.status = DriverStatus.BUSY.value
    
    def update_status(self, new_status: DeliveryStatus):
        """Update delivery status with timestamps"""
        old_status = self.status
        self.status = new_status.value
        self.updated_at = datetime.utcnow()
        
        # Handle status transitions
        if new_status == DeliveryStatus.PICKED_UP and not self.pickup_time:
            self.pickup_time = datetime.utcnow()
        elif new_status == DeliveryStatus.DELIVERED and not self.delivery_time:
            self.delivery_time = datetime.utcnow()
            
            # Update driver status to available
            if self.driver:
                self.driver.status = DriverStatus.AVAILABLE.value
        
        # Add tracking update
        tracking = DeliveryTracking(
            delivery_id=self.id,
            status=new_status.value,
            timestamp=datetime.utcnow(),
            location_lat=self.driver.current_location_lat if self.driver else None,
            location_lng=self.driver.current_location_lng if self.driver else None
        )
        db.session.add(tracking)
    
    def get_eta(self):
        """Get estimated time of arrival"""
        if self.status in [DeliveryStatus.DELIVERED.value, DeliveryStatus.FAILED.value]:
            return None
        
        if self.delivery_time and self.status == DeliveryStatus.IN_TRANSIT.value:
            return self.delivery_time
        
        if self.estimated_duration and self.pickup_time:
            return self.pickup_time + timedelta(minutes=self.estimated_duration)
        
        return None
    
    def get_tracking_history(self):
        """Get delivery tracking history"""
        return self.tracking_updates.order_by(DeliveryTracking.timestamp.desc()).all()
    
    def to_dict(self):
        """Convert delivery to dictionary"""
        return {
            'id': self.id,
            'order_id': self.order_id,
            'order_number': self.order.order_number if self.order else None,
            'driver_id': self.driver_id,
            'driver_name': self.driver.user.name if self.driver and self.driver.user else None,
            'delivery_number': self.delivery_number,
            'status': self.status,
            'pickup_address': self.pickup_address,
            'delivery_address': self.delivery_address,
            'pickup_coordinates': {
                'lat': self.pickup_lat,
                'lng': self.pickup_lng
            } if self.pickup_lat and self.pickup_lng else None,
            'delivery_coordinates': {
                'lat': self.delivery_lat,
                'lng': self.delivery_lng
            } if self.delivery_lat and self.delivery_lng else None,
            'estimated_distance': float(self.estimated_distance) if self.estimated_distance else None,
            'estimated_duration': self.estimated_duration,
            'actual_distance': float(self.actual_distance) if self.actual_distance else None,
            'actual_duration': self.actual_duration,
            'pickup_time': self.pickup_time.isoformat() if self.pickup_time else None,
            'delivery_time': self.delivery_time.isoformat() if self.delivery_time else None,
            'assigned_at': self.assigned_at.isoformat() if self.assigned_at else None,
            'eta': self.get_eta().isoformat() if self.get_eta() is not None else None,
            'delivery_notes': self.delivery_notes,
            'customer_contact': self.customer_contact,
            'special_instructions': self.special_instructions,
            'contactless_delivery': self.contactless_delivery,
            'delivery_photo_url': self.delivery_photo_url,
            'signature_url': self.signature_url,
            'route_id': self.route_id,
            'priority': self.priority,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class DeliveryRoute(db.Model):
    """Route optimization model"""
    __tablename__ = 'delivery_routes'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    driver_id: Mapped[int] = mapped_column(Integer, ForeignKey('drivers.id'), nullable=False)
    route_name: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default=RouteStatus.PLANNED.value)
    start_location_lat: Mapped[float] = mapped_column(Float, nullable=True)
    start_location_lng: Mapped[float] = mapped_column(Float, nullable=True)
    end_location_lat: Mapped[float] = mapped_column(Float, nullable=True)
    end_location_lng: Mapped[float] = mapped_column(Float, nullable=True)
    total_distance: Mapped[float] = mapped_column(Numeric(8, 2), nullable=True)
    estimated_duration: Mapped[int] = mapped_column(Integer, nullable=True)
    actual_distance: Mapped[float] = mapped_column(Numeric(8, 2), nullable=True)
    actual_duration: Mapped[int] = mapped_column(Integer, nullable=True)
    fuel_cost_estimate: Mapped[float] = mapped_column(Numeric(8, 2), nullable=True)
    route_coordinates: Mapped[List[Dict]] = mapped_column(JSON, default=[])
    waypoints: Mapped[List[Dict]] = mapped_column(JSON, default=[])
    optimization_algorithm: Mapped[str] = mapped_column(String(50), default='google_maps')
    traffic_considered: Mapped[bool] = mapped_column(Boolean, default=True)
    weather_considered: Mapped[bool] = mapped_column(Boolean, default=False)
    planned_start_time: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    actual_start_time: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    completion_time: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<DeliveryRoute {self.route_name} ({self.status})>'
    
    def to_dict(self):
        """Convert route to dictionary"""
        return {
            'id': self.id,
            'driver_id': self.driver_id,
            'driver_name': self.driver.user.name if self.driver and self.driver.user else None,
            'route_name': self.route_name,
            'status': self.status,
            'start_coordinates': {
                'lat': self.start_location_lat,
                'lng': self.start_location_lng
            } if self.start_location_lat and self.start_location_lng else None,
            'end_coordinates': {
                'lat': self.end_location_lat,
                'lng': self.end_location_lng
            } if self.end_location_lat and self.end_location_lng else None,
            'total_distance': float(self.total_distance) if self.total_distance else None,
            'estimated_duration': self.estimated_duration,
            'actual_distance': float(self.actual_distance) if self.actual_distance else None,
            'actual_duration': self.actual_duration,
            'fuel_cost_estimate': float(self.fuel_cost_estimate) if self.fuel_cost_estimate else None,
            'route_coordinates': self.route_coordinates,
            'waypoints': self.waypoints,
            'optimization_algorithm': self.optimization_algorithm,
            'traffic_considered': self.traffic_considered,
            'weather_considered': self.weather_considered,
            'planned_start_time': self.planned_start_time.isoformat() if self.planned_start_time else None,
            'actual_start_time': self.actual_start_time.isoformat() if self.actual_start_time else None,
            'completion_time': self.completion_time.isoformat() if self.completion_time else None,
            'delivery_count': len(self.deliveries),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class DriverLocation(db.Model):
    """Driver location history for tracking"""
    __tablename__ = 'driver_locations'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    driver_id: Mapped[int] = mapped_column(Integer, ForeignKey('drivers.id'), nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    accuracy: Mapped[float] = mapped_column(Float, nullable=True)  # GPS accuracy in meters
    speed: Mapped[float] = mapped_column(Float, nullable=True)  # speed in km/h
    heading: Mapped[float] = mapped_column(Float, nullable=True)  # heading in degrees
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    location_source: Mapped[str] = mapped_column(String(20), default='gps')  # gps, network, manual
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<DriverLocation Driver:{self.driver_id} {self.latitude},{self.longitude}>'
    
    def to_dict(self):
        """Convert location to dictionary"""
        return {
            'id': self.id,
            'driver_id': self.driver_id,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'accuracy': self.accuracy,
            'speed': self.speed,
            'heading': self.heading,
            'timestamp': self.timestamp.isoformat(),
            'location_source': self.location_source,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class DeliveryTracking(db.Model):
    """Delivery tracking updates"""
    __tablename__ = 'delivery_tracking'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    delivery_id: Mapped[int] = mapped_column(Integer, ForeignKey('deliveries.id'), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    location_lat: Mapped[float] = mapped_column(Float, nullable=True)
    location_lng: Mapped[float] = mapped_column(Float, nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    update_source: Mapped[str] = mapped_column(String(20), default='driver')  # driver, system, customer
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<DeliveryTracking {self.delivery_id} {self.status}>'
    
    def to_dict(self):
        """Convert tracking update to dictionary"""
        return {
            'id': self.id,
            'delivery_id': self.delivery_id,
            'delivery_number': self.delivery.delivery_number if self.delivery else None,
            'status': self.status,
            'timestamp': self.timestamp.isoformat(),
            'location': {
                'lat': self.location_lat,
                'lng': self.location_lng
            } if self.location_lat and self.location_lng else None,
            'notes': self.notes,
            'update_source': self.update_source,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class DriverRating(db.Model):
    """Driver performance ratings"""
    __tablename__ = 'driver_ratings'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    driver_id: Mapped[int] = mapped_column(Integer, ForeignKey('drivers.id'), nullable=False)
    delivery_id: Mapped[int] = mapped_column(Integer, ForeignKey('deliveries.id'), nullable=True)
    customer_id: Mapped[int] = mapped_column(Integer, ForeignKey('customers.id'), nullable=True)
    rating_type: Mapped[str] = mapped_column(String(30), nullable=False)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)  # 1-5 stars
    comment: Mapped[str] = mapped_column(Text, nullable=True)
    rated_by: Mapped[str] = mapped_column(String(20), default='customer')  # customer, manager, system
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    customer = relationship('Customer', backref='driver_ratings')
    
    def __repr__(self):
        return f'<DriverRating Driver:{self.driver_id} {self.rating_type}:{self.rating}>'
    
    def to_dict(self):
        """Convert rating to dictionary"""
        return {
            'id': self.id,
            'driver_id': self.driver_id,
            'delivery_id': self.delivery_id,
            'customer_id': self.customer_id,
            'customer_name': f"{self.customer.first_name} {self.customer.last_name}" if self.customer else None,
            'rating_type': self.rating_type,
            'rating': self.rating,
            'comment': self.comment,
            'rated_by': self.rated_by,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class DriverPerformance(db.Model):
    """Driver performance metrics"""
    __tablename__ = 'driver_performance'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    driver_id: Mapped[int] = mapped_column(Integer, ForeignKey('drivers.id'), nullable=False)
    date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    total_deliveries: Mapped[int] = mapped_column(Integer, default=0)
    successful_deliveries: Mapped[int] = mapped_column(Integer, default=0)
    failed_deliveries: Mapped[int] = mapped_column(Integer, default=0)
    total_distance: Mapped[float] = mapped_column(Numeric(8, 2), default=0)
    total_duration: Mapped[int] = mapped_column(Integer, default=0)  # in minutes
    average_delivery_time: Mapped[int] = mapped_column(Integer, default=0)  # in minutes
    on_time_deliveries: Mapped[int] = mapped_column(Integer, default=0)
    customer_rating_average: Mapped[float] = mapped_column(Numeric(3, 2), default=0.0)
    fuel_efficiency: Mapped[float] = mapped_column(Numeric(5, 2), default=0.0)  # km/l
    earnings: Mapped[float] = mapped_column(Numeric(10, 2), default=0.0)
    tips: Mapped[float] = mapped_column(Numeric(8, 2), default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<DriverPerformance Driver:{self.driver_id} {self.date}>'
    
    def to_dict(self):
        """Convert performance metrics to dictionary"""
        return {
            'id': self.id,
            'driver_id': self.driver_id,
            'driver_name': self.driver.user.name if self.driver and self.driver.user else None,
            'date': self.date.isoformat(),
            'total_deliveries': self.total_deliveries,
            'successful_deliveries': self.successful_deliveries,
            'failed_deliveries': self.failed_deliveries,
            'success_rate': (self.successful_deliveries / max(1, self.total_deliveries)) * 100,
            'total_distance': float(self.total_distance),
            'total_duration': self.total_duration,
            'average_delivery_time': self.average_delivery_time,
            'on_time_deliveries': self.on_time_deliveries,
            'on_time_rate': (self.on_time_deliveries / max(1, self.successful_deliveries)) * 100,
            'customer_rating_average': float(self.customer_rating_average),
            'fuel_efficiency': float(self.fuel_efficiency),
            'earnings': float(self.earnings),
            'tips': float(self.tips),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class DriverEarning(db.Model):
    """Driver earnings and commissions"""
    __tablename__ = 'driver_earnings'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    driver_id: Mapped[int] = mapped_column(Integer, ForeignKey('drivers.id'), nullable=False)
    delivery_id: Mapped[int] = mapped_column(Integer, ForeignKey('deliveries.id'), nullable=True)
    earning_type: Mapped[str] = mapped_column(String(20), nullable=False)  # base, commission, tip, bonus, penalty
    amount: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False)
    description: Mapped[str] = mapped_column(String(200), nullable=True)
    reference_id: Mapped[str] = mapped_column(String(50), nullable=True)  # external reference
    payment_date: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    is_paid: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<DriverEarning Driver:{self.driver_id} {self.earning_type}:{self.amount}>'
    
    def to_dict(self):
        """Convert earning to dictionary"""
        return {
            'id': self.id,
            'driver_id': self.driver_id,
            'delivery_id': self.delivery_id,
            'delivery_number': self.delivery.delivery_number if self.delivery else None,
            'earning_type': self.earning_type,
            'amount': float(self.amount),
            'description': self.description,
            'reference_id': self.reference_id,
            'payment_date': self.payment_date.isoformat() if self.payment_date else None,
            'is_paid': self.is_paid,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class DeliveryFeedback(db.Model):
    """Customer feedback for deliveries"""
    __tablename__ = 'delivery_feedback'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    delivery_id: Mapped[int] = mapped_column(Integer, ForeignKey('deliveries.id'), nullable=False)
    customer_id: Mapped[int] = mapped_column(Integer, ForeignKey('customers.id'), nullable=True)
    overall_rating: Mapped[int] = mapped_column(Integer, nullable=False)  # 1-5 stars
    delivery_speed_rating: Mapped[int] = mapped_column(Integer, nullable=True)
    food_quality_rating: Mapped[int] = mapped_column(Integer, nullable=True)
    driver_professionalism_rating: Mapped[int] = mapped_column(Integer, nullable=True)
    packaging_quality_rating: Mapped[int] = mapped_column(Integer, nullable=True)
    comments: Mapped[str] = mapped_column(Text, nullable=True)
    issues: Mapped[List[str]] = mapped_column(JSON, default=[])  # list of issues
    would_order_again: Mapped[bool] = mapped_column(Boolean, nullable=True)
    feedback_source: Mapped[str] = mapped_column(String(20), default='app')  # app, email, sms, website
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    customer = relationship('Customer', backref='delivery_feedback')
    
    def __repr__(self):
        return f'<DeliveryFeedback Delivery:{self.delivery_id} Rating:{self.overall_rating}>'
    
    def to_dict(self):
        """Convert feedback to dictionary"""
        return {
            'id': self.id,
            'delivery_id': self.delivery_id,
            'delivery_number': self.delivery.delivery_number if self.delivery else None,
            'customer_id': self.customer_id,
            'customer_name': f"{self.customer.first_name} {self.customer.last_name}" if self.customer else None,
            'overall_rating': self.overall_rating,
            'delivery_speed_rating': self.delivery_speed_rating,
            'food_quality_rating': self.food_quality_rating,
            'driver_professionalism_rating': self.driver_professionalism_rating,
            'packaging_quality_rating': self.packaging_quality_rating,
            'comments': self.comments,
            'issues': self.issues,
            'would_order_again': self.would_order_again,
            'feedback_source': self.feedback_source,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class DeliveryZone(db.Model):
    """Delivery zones for geofencing"""
    __tablename__ = 'delivery_zones'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    zone_type: Mapped[str] = mapped_column(String(20), default='polygon')  # polygon, circle
    coordinates: Mapped[List[Dict]] = mapped_column(JSON, nullable=False)  # polygon coordinates or center point
    radius: Mapped[float] = mapped_column(Numeric(8, 2), nullable=True)  # for circle zones in km
    base_delivery_fee: Mapped[float] = mapped_column(Numeric(6, 2), default=0.0)
    fee_per_km: Mapped[float] = mapped_column(Numeric(6, 2), default=0.0)
    minimum_order_amount: Mapped[float] = mapped_column(Numeric(8, 2), default=0.0)
    free_delivery_above: Mapped[float] = mapped_column(Numeric(8, 2), nullable=True)
    estimated_delivery_time: Mapped[int] = mapped_column(Integer, default=30)  # in minutes
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    priority: Mapped[int] = mapped_column(Integer, default=1)  # for overlapping zones
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<DeliveryZone {self.name}>'
    
    def contains_point(self, lat: float, lng: float) -> bool:
        """Check if a point is within the delivery zone"""
        if self.zone_type == 'circle' and self.radius:
            # Simple distance calculation for circular zones
            center_lat = self.coordinates[0]['lat']
            center_lng = self.coordinates[0]['lng']
            
            from math import radians, cos, sin, asin, sqrt
            
            # Convert decimal degrees to radians
            lat1, lng1, lat2, lng2 = map(radians, [lat, lng, center_lat, center_lng])
            
            # Haversine formula
            dlat = lat2 - lat1
            dlng = lng2 - lng1
            a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlng/2)**2
            c = 2 * asin(sqrt(a))
            
            # Radius of earth in kilometers
            r = 6371
            
            distance = c * r
            return distance <= float(self.radius)
        
        elif self.zone_type == 'polygon' and len(self.coordinates) >= 3:
            # Point in polygon algorithm
            n = len(self.coordinates)
            inside = False
            
            p1x, p1y = self.coordinates[0]['lng'], self.coordinates[0]['lat']
            for i in range(1, n + 1):
                p2x, p2y = self.coordinates[i % n]['lng'], self.coordinates[i % n]['lat']
                if lng > min(p1x, p2x):
                    if lng <= max(p1x, p2x):
                        if lat <= max(p1y, p2y):
                            if p1x != p2x:
                                xinters = (lng - p1x) * (p2y - p1y) / (p2x - p1x) + p1y
                            if p1x == p2x or lat <= xinters:  # type: ignore
                                inside = not inside
                p1x, p1y = p2x, p2y
            
            return inside
        
        return False
    
    def calculate_delivery_fee(self, distance: float, order_amount: float) -> float:
        """Calculate delivery fee based on distance and order amount"""
        if self.free_delivery_above and order_amount >= float(self.free_delivery_above):
            return 0.0
        
        fee = float(self.base_delivery_fee)
        if self.fee_per_km:
            fee += float(self.fee_per_km) * distance
        
        return fee
    
    def to_dict(self):
        """Convert delivery zone to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'zone_type': self.zone_type,
            'coordinates': self.coordinates,
            'radius': float(self.radius) if self.radius else None,
            'base_delivery_fee': float(self.base_delivery_fee),
            'fee_per_km': float(self.fee_per_km),
            'minimum_order_amount': float(self.minimum_order_amount),
            'free_delivery_above': float(self.free_delivery_above) if self.free_delivery_above else None,
            'estimated_delivery_time': self.estimated_delivery_time,
            'is_active': self.is_active,
            'priority': self.priority,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }