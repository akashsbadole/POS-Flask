from datetime import datetime, timedelta
from enum import Enum
from typing import TYPE_CHECKING
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import and_
from app import db

if TYPE_CHECKING:
    from app.models.order import Order, OrderItem
    from app.models.menu import MenuItem
    from app.models.user import User

class KitchenOrderStatus(Enum):
    PENDING = 'pending'
    PREPARING = 'preparing'
    READY = 'ready'
    SERVED = 'served'
    CANCELLED = 'cancelled'
    
    def __eq__(self, other):
        if isinstance(other, KitchenOrderStatus):
            return self.value == other.value
        return False
    
    def __hash__(self):
        return hash(self.value)

class KitchenStation(Enum):
    GRILL = 'grill'
    FRY = 'fry'
    BAR = 'bar'
    PREP = 'prep'
    PIZZA = 'pizza'
    DESSERT = 'dessert'
    SALAD = 'salad'
    BEVERAGE = 'beverage'
    SAUCE = 'sauce'
    GENERAL = 'general'
    
    def __eq__(self, other):
        if isinstance(other, KitchenStation):
            return self.value == other.value
        return False
    
    def __hash__(self):
        return hash(self.value)

class PriorityLevel(Enum):
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4
    
    def __eq__(self, other):
        if isinstance(other, PriorityLevel):
            return self.value == other.value
        return False
    
    def __hash__(self):
        return hash(self.value)
    
    def desc(self):
        """Return descending order for sorting"""
        return self
    
    def nullslast(self):
        """Return nulls last ordering"""
        return self

class KitchenOrder(db.Model):
    __tablename__ = 'kitchen_orders'
    
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('order_items.id'), nullable=False)
    status = db.Column(db.Enum(KitchenOrderStatus), default=KitchenOrderStatus.PENDING)
    preparation_time = db.Column(db.Integer)  # seconds
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    station = db.Column(db.Enum(KitchenStation), nullable=False)
    priority_level = db.Column(db.Enum(PriorityLevel), default=PriorityLevel.NORMAL)
    notes = db.Column(db.Text)
    estimated_completion_time = db.Column(db.DateTime)
    actual_completion_time = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    assigned_to = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # Kitchen staff assigned
    
    # Relationships
    order = db.relationship('Order', backref='kitchen_orders')
    order_item = db.relationship('OrderItem', backref='kitchen_orders')
    assigned_staff = db.relationship('User', foreign_keys=[assigned_to], backref='assigned_kitchen_orders')
    
    def __init__(self, **kwargs):
        super(KitchenOrder, self).__init__(**kwargs)
        if not self.station:
            self.station = self.determine_station()
        if not self.priority_level:
            self.priority_level = self.determine_priority()
        if not self.estimated_completion_time:
            self.calculate_estimated_completion_time()
    
    def determine_station(self):
        """Determine kitchen station based on menu item"""
        if not self.order_item or not self.order_item.menu_item:
            return KitchenStation.GENERAL
        
        menu_item = self.order_item.menu_item
        item_name = menu_item.name.lower()
        category_name = menu_item.category.name.lower() if menu_item.category else ""
        
        # Station assignment logic based on item name and category
        if any(keyword in item_name for keyword in ['burger', 'steak', 'chicken', 'grill', 'kebab']):
            return KitchenStation.GRILL
        elif any(keyword in item_name for keyword in ['fries', 'fried', 'nuggets', 'wings']):
            return KitchenStation.FRY
        elif any(keyword in item_name for keyword in ['drink', 'cocktail', 'beer', 'wine', 'juice', 'coffee', 'tea']):
            return KitchenStation.BAR
        elif any(keyword in item_name for keyword in ['pizza']):
            return KitchenStation.PIZZA
        elif any(keyword in item_name for keyword in ['salad', 'fresh']):
            return KitchenStation.SALAD
        elif any(keyword in item_name for keyword in ['cake', 'ice cream', 'dessert', 'sweet']):
            return KitchenStation.DESSERT
        elif any(keyword in category_name for keyword in ['beverage', 'drink']):
            return KitchenStation.BEVERAGE
        elif any(keyword in category_name for keyword in ['appetizer', 'starter', 'soup']):
            return KitchenStation.PREP
        elif any(keyword in item_name for keyword in ['sauce', 'dip', 'gravy']):
            return KitchenStation.SAUCE
        else:
            return KitchenStation.GENERAL
    
    def determine_priority(self):
        """Determine priority level based on order type and other factors"""
        if not self.order:
            return PriorityLevel.NORMAL
        
        # High priority for dine-in orders during peak hours
        if self.order.order_type.value == 'dine_in':
            current_hour = datetime.now().hour
            if 12 <= current_hour <= 14 or 19 <= current_hour <= 21:  # Lunch/dinner peak
                return PriorityLevel.HIGH
        
        # Urgent for delivery orders
        if self.order.order_type.value == 'delivery':
            return PriorityLevel.URGENT
        
        # Normal for takeaway
        if self.order.order_type.value == 'takeaway':
            return PriorityLevel.NORMAL
        
        return PriorityLevel.NORMAL
    
    def calculate_estimated_completion_time(self):
        """Calculate estimated completion time based on preparation time and current workload"""
        if not self.preparation_time:
            # Default preparation time based on station
            station_times = {
                KitchenStation.GRILL: 900,  # 15 minutes
                KitchenStation.FRY: 600,    # 10 minutes
                KitchenStation.BAR: 300,    # 5 minutes
                KitchenStation.PREP: 600,   # 10 minutes
                KitchenStation.PIZZA: 720,  # 12 minutes
                KitchenStation.DESSERT: 480, # 8 minutes
                KitchenStation.SALAD: 300,  # 5 minutes
                KitchenStation.BEVERAGE: 180, # 3 minutes
                KitchenStation.SAUCE: 420,  # 7 minutes
                KitchenStation.GENERAL: 600 # 10 minutes
            }
            self.preparation_time = station_times.get(self.station, 600)
        
        # Simplified queue calculation - will be enhanced later
        queue_time = 300  # 5 minutes base queue time
        
        # Calculate estimated completion time
        now = datetime.utcnow()
        self.estimated_completion_time = now + timedelta(seconds=self.preparation_time + queue_time)
    
    def start_preparation(self, user_id=None):
        """Start preparation timer"""
        if self.status != KitchenOrderStatus.PENDING:
            return False, "Order is not in pending status"
        
        self.status = KitchenOrderStatus.PREPARING
        self.started_at = datetime.utcnow()
        if user_id:
            self.assigned_to = user_id
        
        db.session.commit()
        return True, "Preparation started"
    
    def mark_ready(self):
        """Mark order as ready"""
        if self.status != KitchenOrderStatus.PREPARING:
            return False, "Order is not being prepared"
        
        self.status = KitchenOrderStatus.READY
        self.completed_at = datetime.utcnow()
        self.actual_completion_time = datetime.utcnow()
        
        # Calculate actual preparation time
        if self.started_at:
            time_diff = self.completed_at - self.started_at
            self.preparation_time = int(time_diff.total_seconds())
        
        db.session.commit()
        return True, "Order marked as ready"
    
    def mark_served(self):
        """Mark order as served"""
        if self.status != KitchenOrderStatus.READY:
            return False, "Order is not ready"
        
        self.status = KitchenOrderStatus.SERVED
        db.session.commit()
        return True, "Order marked as served"
    
    def cancel(self, reason=None):
        """Cancel kitchen order"""
        if self.status in [KitchenOrderStatus.SERVED, KitchenOrderStatus.CANCELLED]:
            return False, "Cannot cancel served or already cancelled order"
        
        self.status = KitchenOrderStatus.CANCELLED
        if reason:
            self.notes = f"Cancelled: {reason}"
        db.session.commit()
        return True, "Order cancelled"
    
    def get_preparation_time_remaining(self):
        """Get remaining preparation time in seconds"""
        if self.status in [KitchenOrderStatus.READY, KitchenOrderStatus.SERVED, KitchenOrderStatus.CANCELLED]:
            return 0
        
        if self.status == KitchenOrderStatus.PREPARING and self.started_at:
            elapsed = (datetime.utcnow() - self.started_at).total_seconds()
            return max(0, self.preparation_time - elapsed)
        
        if self.estimated_completion_time:
            remaining = (self.estimated_completion_time - datetime.utcnow()).total_seconds()
            return max(0, remaining)
        
        return self.preparation_time or 0
    
    def is_overdue(self):
        """Check if order is overdue"""
        if self.status in [KitchenOrderStatus.READY, KitchenOrderStatus.SERVED, KitchenOrderStatus.CANCELLED]:
            return False
        
        if self.estimated_completion_time:
            return datetime.utcnow() > self.estimated_completion_time
        
        return False
    
    def get_time_overdue(self):
        """Get how long order is overdue in seconds"""
        if not self.is_overdue():
            return 0
        
        if self.estimated_completion_time:
            return int((datetime.utcnow() - self.estimated_completion_time).total_seconds())
        
        return 0
    
    def to_dict(self):
        """Convert kitchen order to dictionary for API responses"""
        return {
            'id': self.id,
            'order_id': self.order_id,
            'order_number': self.order.order_number if self.order else None,
            'item_id': self.item_id,
            'item_name': self.order_item.menu_item.name if self.order_item and self.order_item.menu_item else None,
            'item_quantity': self.order_item.quantity if self.order_item else None,
            'status': self.status.value if self.status else None,
            'preparation_time': self.preparation_time,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'station': self.station.value if self.station else None,
            'priority_level': self.priority_level.value if self.priority_level else None,
            'notes': self.notes,
            'estimated_completion_time': self.estimated_completion_time.isoformat() if self.estimated_completion_time else None,
            'actual_completion_time': self.actual_completion_time.isoformat() if self.actual_completion_time else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'assigned_to': self.assigned_to,
            'assigned_staff_name': self.assigned_staff.name if self.assigned_staff else None,
            'preparation_time_remaining': self.get_preparation_time_remaining(),
            'is_overdue': self.is_overdue(),
            'time_overdue': self.get_time_overdue(),
            'table_number': self.order.table.number if self.order and self.order.table else None,
            'order_type': self.order.order_type.value if self.order and self.order.order_type else None,
            'special_instructions': self.order_item.notes if self.order_item else None
        }
    
    def __repr__(self):
        return f'<KitchenOrder {self.id} - {self.order_item.menu_item.name if self.order_item and self.order_item.menu_item else "Unknown"} ({self.status.value if self.status else "Unknown"})>'

class KitchenStationConfig(db.Model):
    """Configuration for kitchen stations"""
    __tablename__ = 'kitchen_station_configs'
    
    id = db.Column(db.Integer, primary_key=True)
    station = db.Column(db.Enum(KitchenStation), nullable=False, unique=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    display_order = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    color_code = db.Column(db.String(7), default='#007bff')  # Hex color code
    default_preparation_time = db.Column(db.Integer, default=600)  # seconds
    max_concurrent_items = db.Column(db.Integer, default=10)
    notification_sound = db.Column(db.String(100), default='default')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        """Convert station config to dictionary for API responses"""
        return {
            'id': self.id,
            'station': self.station.value if self.station else None,
            'name': self.name,
            'description': self.description,
            'display_order': self.display_order,
            'is_active': self.is_active,
            'color_code': self.color_code,
            'default_preparation_time': self.default_preparation_time,
            'max_concurrent_items': self.max_concurrent_items,
            'notification_sound': self.notification_sound,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self):
        return f'<KitchenStationConfig {self.name}>'

class KitchenPerformance(db.Model):
    """Kitchen performance tracking"""
    __tablename__ = 'kitchen_performance'
    
    id = db.Column(db.Integer, primary_key=True)
    kitchen_order_id = db.Column(db.Integer, db.ForeignKey('kitchen_orders.id'), nullable=False)
    station = db.Column(db.Enum(KitchenStation), nullable=False)
    staff_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    preparation_time = db.Column(db.Integer, nullable=False)  # seconds
    estimated_time = db.Column(db.Integer, nullable=False)  # seconds
    on_time = db.Column(db.Boolean, default=True)
    quality_rating = db.Column(db.Integer)  # 1-5 scale
    date = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    kitchen_order = db.relationship('KitchenOrder', backref='performance_records')
    staff = db.relationship('User', backref='kitchen_performance')
    
    def calculate_efficiency(self):
        """Calculate preparation efficiency percentage"""
        if self.estimated_time == 0:
            return 100
        return min(100, int((self.estimated_time / self.preparation_time) * 100))
    
    def to_dict(self):
        """Convert performance record to dictionary for API responses"""
        return {
            'id': self.id,
            'kitchen_order_id': self.kitchen_order_id,
            'station': self.station.value if self.station else None,
            'staff_id': self.staff_id,
            'staff_name': self.staff.name if self.staff else None,
            'preparation_time': self.preparation_time,
            'estimated_time': self.estimated_time,
            'on_time': self.on_time,
            'efficiency': self.calculate_efficiency(),
            'quality_rating': self.quality_rating,
            'date': self.date.isoformat() if self.date else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def __repr__(self):
        return f'<KitchenPerformance {self.station.value if self.station else "Unknown"} - {self.date}>'