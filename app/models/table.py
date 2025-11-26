from datetime import datetime
from enum import Enum
from app import db
from .order import Order, OrderStatus

class TableStatus(Enum):
    FREE = 'free'
    OCCUPIED = 'occupied'
    RESERVED = 'reserved'
    CLEANING = 'cleaning'
    MAINTENANCE = 'maintenance'

class Table(db.Model):
    __tablename__ = 'tables'
    
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.String(10), nullable=False, unique=True)
    name = db.Column(db.String(50))  # Optional display name
    capacity = db.Column(db.Integer, default=4)
    status = db.Column(db.Enum(TableStatus), default=TableStatus.FREE)
    floor_position_x = db.Column(db.Integer, default=0)  # Position in floor plan
    floor_position_y = db.Column(db.Integer, default=0)
    floor_section = db.Column(db.String(50))  # e.g., "Patio", "Main Dining"
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    orders = db.relationship('Order', backref='table', lazy=True)
    
    def get_current_order(self):
        """Get the current active order for this table"""
        return Order.query.filter(
            Order.table_id == self.id,
            Order.status.in_([OrderStatus.PENDING, OrderStatus.CONFIRMED, OrderStatus.PREPARING, OrderStatus.READY])
        ).first()
    
    def get_current_session(self):
        """Get current table session information"""
        current_order = self.get_current_order()
        if current_order:
            return {
                'order_id': current_order.id,
                'order_number': current_order.order_number,
                'start_time': current_order.created_at,
                'duration_minutes': (datetime.utcnow() - current_order.created_at).total_seconds() / 60,
                'guests': sum(item.quantity for item in current_order.items),
                'total': float(current_order.total)
            }
        return None
    
    def is_available(self):
        """Check if table is available for new orders"""
        return self.status == TableStatus.FREE and self.is_active
    
    def occupy(self):
        """Mark table as occupied"""
        self.status = TableStatus.OCCUPIED
        self.updated_at = datetime.utcnow()
    
    def free(self):
        """Mark table as free"""
        self.status = TableStatus.FREE
        self.updated_at = datetime.utcnow()
    
    def set_cleaning(self):
        """Mark table as needing cleaning"""
        self.status = TableStatus.CLEANING
        self.updated_at = datetime.utcnow()
    
    def reserve(self):
        """Mark table as reserved"""
        self.status = TableStatus.RESERVED
        self.updated_at = datetime.utcnow()
    
    def get_status_color(self):
        """Get CSS color class for table status"""
        status_colors = {
            TableStatus.FREE: 'bg-green-500',
            TableStatus.OCCUPIED: 'bg-red-500',
            TableStatus.RESERVED: 'bg-yellow-500',
            TableStatus.CLEANING: 'bg-blue-500',
            TableStatus.MAINTENANCE: 'bg-gray-500'
        }
        return status_colors.get(self.status, 'bg-gray-500')
    
    def get_status_text(self):
        """Get human-readable status text"""
        status_texts = {
            TableStatus.FREE: 'Available',
            TableStatus.OCCUPIED: 'Occupied',
            TableStatus.RESERVED: 'Reserved',
            TableStatus.CLEANING: 'Cleaning',
            TableStatus.MAINTENANCE: 'Maintenance'
        }
        return status_texts.get(self.status, 'Unknown')
    
    def can_be_merged(self):
        """Check if table can be merged with another"""
        return self.status in [TableStatus.FREE, TableStatus.CLEANING] and self.is_active
    
    def get_occupancy_duration(self):
        """Get how long table has been occupied"""
        if self.status == TableStatus.OCCUPIED:
            current_order = self.get_current_order()
            if current_order:
                return (datetime.utcnow() - current_order.created_at).total_seconds() / 60
        return 0
    
    def to_dict(self, include_session=False):
        """Convert table to dictionary for API responses"""
        result = {
            'id': self.id,
            'number': self.number,
            'name': self.name,
            'capacity': self.capacity,
            'status': self.status.value if self.status else None,
            'status_text': self.get_status_text(),
            'status_color': self.get_status_color(),
            'floor_position_x': self.floor_position_x,
            'floor_position_y': self.floor_position_y,
            'floor_section': self.floor_section,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
        
        if include_session:
            result['current_session'] = self.get_current_session()
            result['occupancy_duration'] = self.get_occupancy_duration()
        
        return result
    
    def __repr__(self):
        return f'<Table {self.number} ({self.status.value if self.status else "Unknown"})>'

class TableSession(db.Model):
    __tablename__ = 'table_sessions'
    
    id = db.Column(db.Integer, primary_key=True)
    table_id = db.Column(db.Integer, db.ForeignKey('tables.id'), nullable=False)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    start_time = db.Column(db.DateTime, default=datetime.utcnow)
    end_time = db.Column(db.DateTime)
    guest_count = db.Column(db.Integer, default=1)
    notes = db.Column(db.Text)
    
    def get_duration_minutes(self):
        """Get session duration in minutes"""
        end = self.end_time or datetime.utcnow()
        return (end - self.start_time).total_seconds() / 60
    
    def end_session(self):
        """End the table session"""
        self.end_time = datetime.utcnow()
    
    def to_dict(self):
        """Convert table session to dictionary for API responses"""
        return {
            'id': self.id,
            'table_id': self.table_id,
            'table_number': self.table.number if self.table else None,
            'order_id': self.order_id,
            'order_number': self.order.order_number if self.order else None,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'duration_minutes': self.get_duration_minutes(),
            'guest_count': self.guest_count,
            'notes': self.notes
        }
    
    def __repr__(self):
        return f'<TableSession Table {self.table.number if self.table else "Unknown"} - Order {self.order.order_number if self.order else "Unknown"}>'