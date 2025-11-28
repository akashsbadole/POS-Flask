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
    restaurant = db.relationship('Restaurant', back_populates='tables')
    orders = db.relationship('Order', back_populates='table')
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurants.id'), nullable=True)
    
    # Table merge/split relationships
    merged_tables = db.relationship('Table',
                                secondary='table_merges',
                                primaryjoin='Table.id == table_merges.c.parent_table_id',
                                secondaryjoin='Table.id == table_merges.c.child_table_id',
                                backref='parent_tables')
    parent_merges = db.relationship('TableMerge',
                                  foreign_keys='TableMerge.parent_table_id',
                                  back_populates='parent_table')
    child_merges = db.relationship('TableMerge',
                                 foreign_keys='TableMerge.child_table_id',
                                 back_populates='child_table')
    
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
    
    def merge_with(self, other_table, merged_by_user=None, notes=None):
        """Merge this table with another table"""
        if not self.can_be_merged() or not other_table.can_be_merged():
            return False, "Both tables must be free or cleaning to be merged"
        
        # Create merge record
        merge = TableMerge(
            operation_type='merge',
            parent_table_id=self.id,
            child_table_id=other_table.id,
            merged_by=merged_by_user.id if merged_by_user else None,
            notes=notes
        )
        db.session.add(merge)
        
        # Update table status
        other_table.status = TableStatus.MAINTENANCE  # Mark child table as unavailable
        other_table.updated_at = datetime.utcnow()
        
        # Transfer any active orders from child table to parent table
        child_order = other_table.get_current_order()
        if child_order:
            child_order.table_id = self.id
            self.occupy()
        
        db.session.commit()
        return True, f"Table {other_table.number} merged with {self.number}"
    
    def split_from(self, split_by_user=None, notes=None):
        """Split this table back to individual tables"""
        # Find most recent merge operation
        last_merge = TableMerge.query.filter_by(
            parent_table_id=self.id,
            operation_type='merge',
            split_at=None
        ).order_by(TableMerge.merged_at.desc()).first()
        
        if not last_merge:
            return False, "No merge operation found to split"
        
        # Mark merge as split
        last_merge.split_at = datetime.utcnow()
        last_merge.split_by = split_by_user.id if split_by_user else None
        if notes:
            last_merge.notes = notes
        
        # Reactivate child table
        child_table = Table.query.get(last_merge.child_table_id)
        if child_table:
            child_table.status = TableStatus.FREE
            child_table.updated_at = datetime.utcnow()
        
        db.session.commit()
        return True, f"Table {self.number} split successfully"
    
    def get_merged_tables(self):
        """Get all tables merged with this table"""
        # Query the association table to get merged tables
        merged = db.session.execute(
            db.select(table_merges.c.child_table_id)
            .where(table_merges.c.parent_table_id == self.id)
        ).scalars().all()
        
        return Table.query.filter(Table.id.in_(merged)).all() if merged else []
    
    def is_merged(self):
        """Check if this table is currently merged with others"""
        # Check if table is either a parent or child in any unsplit merge
        parent_count = db.session.execute(
            db.select(db.func.count(table_merges.c.child_table_id))
            .where(table_merges.c.parent_table_id == self.id)
        ).scalar()
        
        child_count = db.session.execute(
            db.select(db.func.count(table_merges.c.parent_table_id))
            .where(table_merges.c.child_table_id == self.id)
        ).scalar()
        
        return (parent_count or 0) > 0 or (child_count or 0) > 0
    
    def can_be_split(self):
        """Check if this table can be split"""
        return self.is_merged() and self.status != TableStatus.OCCUPIED
    
    def get_merge_info(self):
        """Get information about table merges"""
        merge_info = []
        
        # Get tables this table has merged (as parent)
        child_merges = db.session.execute(
            db.select(table_merges.c.child_table_id, table_merges.c.merged_at)
            .where(table_merges.c.parent_table_id == self.id)
        ).all()
        
        for child_id, merged_at in child_merges:
            child_table = Table.query.get(child_id)
            if child_table:
                merge_info.append({
                    'table_id': child_table.id,
                    'table_number': child_table.number,
                    'relationship': 'parent',
                    'merged_at': merged_at.isoformat() if merged_at else None
                })
        
        # Get tables this table is merged into (as child)
        parent_merges = db.session.execute(
            db.select(table_merges.c.parent_table_id, table_merges.c.merged_at)
            .where(table_merges.c.child_table_id == self.id)
        ).all()
        
        for parent_id, merged_at in parent_merges:
            parent_table = Table.query.get(parent_id)
            if parent_table:
                merge_info.append({
                    'table_id': parent_table.id,
                    'table_number': parent_table.number,
                    'relationship': 'child',
                    'merged_at': merged_at.isoformat() if merged_at else None
                })
        
        return merge_info
    
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


# Table merge association table
table_merges = db.Table('table_merges',
    db.Column('parent_table_id', db.Integer, db.ForeignKey('tables.id'), primary_key=True),
    db.Column('child_table_id', db.Integer, db.ForeignKey('tables.id'), primary_key=True),
    db.Column('merged_at', db.DateTime, default=datetime.utcnow),
    db.Column('merged_by', db.Integer, db.ForeignKey('users.id')),
    db.Column('notes', db.Text)
)


class TableMerge(db.Model):
    """Model to track table merge and split operations"""
    __tablename__ = 'table_merge_operations'
    
    id = db.Column(db.Integer, primary_key=True)
    operation_type = db.Column(db.Enum('merge', 'split', name='merge_operation_type'), nullable=False)
    parent_table_id = db.Column(db.Integer, db.ForeignKey('tables.id'), nullable=True)
    child_table_id = db.Column(db.Integer, db.ForeignKey('tables.id'), nullable=True)
    merged_at = db.Column(db.DateTime, default=datetime.utcnow)
    split_at = db.Column(db.DateTime, nullable=True)
    merged_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    split_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    notes = db.Column(db.Text)
    
    # Relationships
    parent_table = db.relationship('Table', foreign_keys=[parent_table_id], back_populates='parent_merges')
    child_table = db.relationship('Table', foreign_keys=[child_table_id], back_populates='child_merges')
    merged_by_user = db.relationship('User', foreign_keys=[merged_by])
    split_by_user = db.relationship('User', foreign_keys=[split_by])
    
    def to_dict(self):
        """Convert table merge operation to dictionary"""
        return {
            'id': self.id,
            'operation_type': self.operation_type,
            'parent_table_id': self.parent_table_id,
            'parent_table_number': self.parent_table.number if self.parent_table else None,
            'child_table_id': self.child_table_id,
            'child_table_number': self.child_table.number if self.child_table else None,
            'merged_at': self.merged_at.isoformat() if self.merged_at else None,
            'split_at': self.split_at.isoformat() if self.split_at else None,
            'merged_by': self.merged_by_user.name if self.merged_by_user else None,
            'split_by': self.split_by_user.name if self.split_by_user else None,
            'notes': self.notes
        }
    
    def __repr__(self):
        return f'<TableMerge {self.operation_type}: Table {self.parent_table_id} -> {self.child_table_id}>'