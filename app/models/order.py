from datetime import datetime
from enum import Enum
from typing import List, TYPE_CHECKING
import json
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app import db

if TYPE_CHECKING:
    from app.models.menu import MenuItem, AddOn, ItemVariant
    from app.models.table import Table
    from app.models.user import User
    from app.models.customer import Customer

# Association table for many-to-many relationship between order items and add-ons
order_item_add_ons = db.Table('order_item_add_ons',
    db.Column('order_item_id', db.Integer, db.ForeignKey('order_items.id'), primary_key=True),
    db.Column('addon_id', db.Integer, db.ForeignKey('add_ons.id'), primary_key=True)
)

class OrderStatus(Enum):
    PENDING = 'pending'
    CONFIRMED = 'confirmed'
    PREPARING = 'preparing'
    READY = 'ready'
    SERVED = 'served'
    CANCELLED = 'cancelled'
    VOID = 'void'

class OrderType(Enum):
    DINE_IN = 'dine_in'
    TAKEAWAY = 'takeaway'
    DELIVERY = 'delivery'

class PaymentMethod(Enum):
    CASH = 'cash'
    CARD = 'card'
    UPI = 'upi'
    WALLET = 'wallet'
    GIFT_CARD = 'gift_card'
    CREDIT = 'credit'

class Order(db.Model):
    __tablename__ = 'orders'
    
    id = db.Column(db.Integer, primary_key=True)
    table_id = db.Column(db.Integer, db.ForeignKey('tables.id'), nullable=True)
    waiter_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    seat_number = db.Column(db.String(10), nullable=True)  # For multi-seat table management
    parent_order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=True)  # For split checks
    course_number = db.Column(db.Integer, default=1)  # For multi-course dining
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=True)
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurants.id'), nullable=True)
    order_number = db.Column(db.String(20), unique=True, nullable=False)
    order_type = db.Column(db.Enum(OrderType), default=OrderType.DINE_IN)
    status = db.Column(db.Enum(OrderStatus), default=OrderStatus.PENDING)
    subtotal = db.Column(db.Numeric(10, 2), nullable=False)
    tax_rate = db.Column(db.Numeric(5, 4), default=0.18)  # 18% GST default
    tax_amount = db.Column(db.Numeric(10, 2), default=0.00)
    cgst_amount = db.Column(db.Numeric(10, 2), default=0.00)
    sgst_amount = db.Column(db.Numeric(10, 2), default=0.00)
    igst_amount = db.Column(db.Numeric(10, 2), default=0.00)
    cess_amount = db.Column(db.Numeric(10, 2), default=0.00)
    discount_amount = db.Column(db.Numeric(10, 2), default=0.00)
    discount_type = db.Column(db.Enum('percentage', 'fixed'), nullable=True)
    discount_reason = db.Column(db.String(255))
    service_charge = db.Column(db.Numeric(10, 2), default=0.00)
    total = db.Column(db.Numeric(10, 2), nullable=False)
    notes = db.Column(db.Text)
    estimated_preparation_time = db.Column(db.Integer)  # in seconds
    actual_preparation_time = db.Column(db.Integer)  # in seconds
    timer_started_at = db.Column(db.DateTime)
    timer_completed_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    
    # Relationships
    restaurant = db.relationship('Restaurant', back_populates='orders')
    table = db.relationship('Table', back_populates='orders')
    waiter = db.relationship('User', foreign_keys=[waiter_id], backref='waiter_orders')
    parent_order = db.relationship('Order', remote_side=[id], backref='child_orders')
    user = db.relationship('User', foreign_keys=[user_id], back_populates='orders')
    customer = db.relationship('Customer', back_populates='orders')
    loyalty_transactions = db.relationship('LoyaltyTransaction', back_populates='order')
    items = db.relationship('OrderItem', backref='order', lazy='select', cascade='all, delete-orphan')
    payments = db.relationship('Payment', backref='order', lazy='select', cascade='all, delete-orphan')
    
    # Enhanced Customer Engagement Relationships
    reward_redemptions = db.relationship('RewardRedemption', back_populates='order', lazy='dynamic')
    # campaign_messages = db.relationship('CampaignMessage', back_populates='order', lazy='dynamic')  # Commented out until proper foreign key is added
    feedback = db.relationship('CustomerFeedback', back_populates='order', lazy='dynamic')
    communications = db.relationship('CustomerCommunication', back_populates='order', lazy='dynamic')
    
    def __init__(self, **kwargs):
        super(Order, self).__init__(**kwargs)
        if not self.order_number:
            self.order_number = self.generate_order_number()
    
    def generate_order_number(self):
        """Generate unique order number"""
        today = datetime.now().strftime('%Y%m%d')
        today_orders = Order.query.filter(
            Order.created_at >= datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        ).count()
        
        # Keep trying until we find a unique number
        attempts = 0
        while attempts < 100:  # Prevent infinite loop
            candidate = f"ORD{today}{today_orders + attempts + 1:03d}"
            existing = Order.query.filter_by(order_number=candidate).first()
            if not existing:
                return candidate
            attempts += 1
        
        # Fallback to timestamp-based number
        import time
        return f"ORD{today}{int(time.time()) % 1000:03d}"
    
    def calculate_totals(self):
        """Calculate order totals"""
        # Use direct query to get items
        from .order import OrderItem
        items_list = OrderItem.query.filter_by(order_id=self.id).all()
        self.subtotal = sum(item.get_total_price() for item in items_list)
        
        # Get GST settings for the restaurant
        if self.restaurant_id:
            from app.models.gst import GSTSetting
            gst_setting = GSTSetting.query.filter_by(
                restaurant_id=self.restaurant_id,
                is_active=True
            ).first()
            
            if gst_setting:
                gst_components = gst_setting.calculate_gst_components(self.subtotal)
                self.cgst_amount = gst_components['cgst']
                self.sgst_amount = gst_components['sgst']
                self.igst_amount = gst_components['igst']
                self.cess_amount = gst_components['cess']
                self.tax_amount = gst_components['total_gst']
            else:
                # Fallback to simple tax calculation
                self.cgst_amount = 0.00
                self.sgst_amount = 0.00
                self.igst_amount = 0.00
                self.cess_amount = 0.00
                self.tax_amount = float(self.subtotal) * float(self.tax_rate)
        else:
            # No restaurant set, use simple calculation
            self.cgst_amount = 0.00
            self.sgst_amount = 0.00
            self.igst_amount = 0.00
            self.cess_amount = 0.00
            tax_rate = float(self.tax_rate) if self.tax_rate is not None else 0.18
            self.tax_amount = float(self.subtotal) * tax_rate
        
        self.total = float(self.subtotal) + float(self.tax_amount or 0) + float(self.service_charge or 0) - float(self.discount_amount or 0)
    
    @property
    def cgst_rate(self):
        """Get CGST rate from GST settings"""
        if self.restaurant_id:
            from app.models.gst import GSTSetting
            gst_setting = GSTSetting.query.filter_by(
                restaurant_id=self.restaurant_id,
                is_active=True
            ).first()
            return float(gst_setting.cgst_rate) if gst_setting else 0.09
        return 0.09  # Default 9%
    
    @property
    def sgst_rate(self):
        """Get SGST rate from GST settings"""
        if self.restaurant_id:
            from app.models.gst import GSTSetting
            gst_setting = GSTSetting.query.filter_by(
                restaurant_id=self.restaurant_id,
                is_active=True
            ).first()
            return float(gst_setting.sgst_rate) if gst_setting else 0.09
        return 0.09  # Default 9%
    
    @property
    def igst_rate(self):
        """Get IGST rate from GST settings"""
        if self.restaurant_id:
            from app.models.gst import GSTSetting
            gst_setting = GSTSetting.query.filter_by(
                restaurant_id=self.restaurant_id,
                is_active=True
            ).first()
            return float(gst_setting.igst_rate) if gst_setting else 0.00
        return 0.00  # Default 0%
    
    @property
    def cess_rate(self):
        """Get CESS rate from GST settings"""
        if self.restaurant_id:
            from app.models.gst import GSTSetting
            gst_setting = GSTSetting.query.filter_by(
                restaurant_id=self.restaurant_id,
                is_active=True
            ).first()
            return float(gst_setting.cess_rate) if gst_setting else 0.00
        return 0.00  # Default 0%
    
    def get_total_paid(self):
        """Get total amount paid"""
        # Use direct query to get payments
        from .order import Payment
        payments_list = Payment.query.filter_by(order_id=self.id).all()
        return sum(float(payment.amount) for payment in payments_list if payment.is_successful())
    
    def get_balance_due(self):
        """Get remaining balance"""
        return float(self.total) - self.get_total_paid()
    
    def is_fully_paid(self):
        """Check if order is fully paid"""
        return self.get_balance_due() <= 0.01  # Small tolerance for floating point
    
    def update_status(self, new_status):
        """Update order status with timestamp"""
        old_status = self.status
        self.status = new_status
        self.updated_at = datetime.utcnow()
        
        # Handle timer tracking for preparation
        if new_status == OrderStatus.CONFIRMED and old_status != OrderStatus.CONFIRMED:
            # Calculate estimated preparation time when order is confirmed
            self.estimated_preparation_time = self.calculate_preparation_time()
        elif new_status == OrderStatus.PREPARING and not self.timer_started_at:
            # Start timer when preparation begins
            self.timer_started_at = datetime.utcnow()
        elif new_status == OrderStatus.READY and self.timer_started_at and not self.timer_completed_at:
            # Complete timer when order is ready
            self.timer_completed_at = datetime.utcnow()
            if self.timer_started_at:
                time_diff = self.timer_completed_at - self.timer_started_at
                self.actual_preparation_time = int(time_diff.total_seconds())
        
        if new_status in [OrderStatus.SERVED, OrderStatus.CANCELLED, OrderStatus.VOID]:
            self.completed_at = datetime.utcnow()
        
        # Update table status based on order status
        self._update_table_status(old_status, new_status)
        
        # Notify assigned waiters of order changes
        self._notify_waiter_status_change(old_status, new_status)
    
    def can_be_cancelled(self):
        """Check if order can be cancelled"""
        return self.status in [OrderStatus.PENDING, OrderStatus.CONFIRMED]
    
    def can_be_modified(self):
        """Check if order can be modified"""
        return self.status in [OrderStatus.PENDING, OrderStatus.CONFIRMED]
    
    def calculate_preparation_time(self):
        """Calculate estimated preparation time based on order complexity"""
        # Get order items using direct query
        from app.models.menu import MenuItem
        from app.models.recipe import Recipe
        
        order_items = OrderItem.query.filter_by(order_id=self.id).all()
        if not order_items:
            return 900  # Default 15 minutes
        
        base_time = 300  # 5 minutes base time
        complexity_multiplier = 1
        
        # Calculate based on number of items
        item_count = len(order_items)
        if item_count > 5:
            complexity_multiplier += 0.5
        if item_count > 10:
            complexity_multiplier += 0.5
        
        # Calculate based on item complexity
        for order_item in order_items:
            # Get menu item with preparation time
            menu_item = MenuItem.query.get(order_item.item_id)
            if menu_item and menu_item.preparation_time:
                base_time += menu_item.preparation_time * 60  # Convert to seconds
            
            # Check recipe difficulty
            recipe = Recipe.query.filter_by(menu_item_id=order_item.item_id).first()
            if recipe:
                if recipe.difficulty_level == 'Easy':
                    complexity_multiplier += 0.1
                elif recipe.difficulty_level == 'Medium':
                    complexity_multiplier += 0.2
                elif recipe.difficulty_level == 'Hard':
                    complexity_multiplier += 0.4
            
            # Add time for add-ons
            if order_item.add_ons and len(order_item.add_ons) > 0:
                base_time += len(order_item.add_ons) * 30  # 30 seconds per add-on
        
        # Consider current kitchen workload
        from datetime import datetime
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        current_orders = Order.query.filter(
            Order.status.in_([OrderStatus.CONFIRMED, OrderStatus.PREPARING]),
            Order.created_at >= today
        ).count()
        
        workload_multiplier = 1 + (current_orders * 0.1)  # 10% increase per active order
        
        return int(base_time * complexity_multiplier * workload_multiplier)
    
    def _update_table_status(self, old_status, new_status):
        """Update table status based on order status changes"""
        if not self.table_id:
            return
        
        from app.models.table import Table
        table = Table.query.get(self.table_id)
        if not table:
            return
        
        # Get all orders for this table to determine overall status
        table_orders = Order.query.filter_by(table_id=self.table_id).all()
        
        # Count orders by status
        pending_count = sum(1 for o in table_orders if o.status == OrderStatus.PENDING)
        confirmed_count = sum(1 for o in table_orders if o.status == OrderStatus.CONFIRMED)
        preparing_count = sum(1 for o in table_orders if o.status == OrderStatus.PREPARING)
        ready_count = sum(1 for o in table_orders if o.status == OrderStatus.READY)
        served_count = sum(1 for o in table_orders if o.status == OrderStatus.SERVED)
        
        # Determine table status based on order statuses
        if served_count == len(table_orders) and len(table_orders) > 0:
            # All orders served
            table.status = 'finished'
        elif ready_count > 0:
            # Some orders ready
            table.status = 'serving'
        elif preparing_count > 0:
            # Orders being prepared
            table.status = 'ordered'
        elif confirmed_count > 0:
            # Orders confirmed
            table.status = 'ordered'
        elif pending_count > 0:
            # Orders pending
            table.status = 'occupied'
        
        # If no active orders, free the table
        active_orders = sum(1 for o in table_orders if o.status in [
            OrderStatus.PENDING, OrderStatus.CONFIRMED,
            OrderStatus.PREPARING, OrderStatus.READY, OrderStatus.SERVED
        ])
        
        if active_orders == 0:
            table.status = 'available'
        
        db.session.commit()
    
    def _notify_waiter_status_change(self, old_status, new_status):
        """Notify assigned waiters of order status changes"""
        if not self.waiter_id:
            return
        
        # Import here to avoid circular imports
        from app.notifications.service import notification_service
        from flask import current_app
        
        try:
            # Create status change message
            status_messages = {
                OrderStatus.PENDING: "Order pending",
                OrderStatus.CONFIRMED: "Order confirmed - preparing",
                OrderStatus.PREPARING: "Order being prepared",
                OrderStatus.READY: "Order ready for serving",
                OrderStatus.SERVED: "Order served",
                OrderStatus.CANCELLED: "Order cancelled",
                OrderStatus.VOID: "Order voided"
            }
            
            message = status_messages.get(new_status, f"Order status changed to {new_status.value}")
            
            # Send notification to waiter
            notification_service.send_email(
                to=self.waiter.email if self.waiter else 'admin@restaurant.com',
                subject=f"Order {self.order_number} Status Update",
                template='notifications/email/order_status.html',
                context={
                    'order': self,
                    'message': message,
                    'old_status': old_status.value if old_status else None,
                    'new_status': new_status.value
                }
            )
            
            # If order is ready, also notify kitchen staff
            if new_status == OrderStatus.READY:
                from app.models.user import User
                kitchen_staff = User.query.filter_by(role='kitchen').all()
                for staff in kitchen_staff:
                    notification_service.send_email(
                        to=staff.email,
                        subject=f"Order Ready",
                        template='notifications/email/order_ready.html',
                        context={
                            'order': self,
                            'message': f"Order {self.order_number} is ready for serving"
                        }
                    )
            
            # Emit real-time update via WebSocket if available
            try:
                from app import socketio
                socketio.emit('order_status_update', {
                    'order_id': self.id,
                    'order_number': self.order_number,
                    'table_id': self.table_id,
                    'table_number': self.table.number if self.table else None,
                    'old_status': old_status.value if old_status else None,
                    'new_status': new_status.value,
                    'timestamp': datetime.utcnow().isoformat()
                }, to=f'table_{self.table_id}' if self.table_id else None)
            except Exception as e:
                # Log error but don't fail the status update
                import sys
                print(f"Error emitting WebSocket notification: {str(e)}", file=sys.stderr)
                
        except Exception as e:
            # Log error but don't fail the status update
            current_app.logger.error(f"Failed to send order status notification: {str(e)}")
    
    def get_table_orders(self):
        """Get all orders for the same table (including this one)"""
        if not self.table_id:
            return []
        return Order.query.filter_by(table_id=self.table_id).order_by(Order.created_at).all()
    
    def get_sibling_orders(self):
        """Get sibling orders (orders with same parent_order_id)"""
        if not self.parent_order_id:
            return []
        return Order.query.filter_by(parent_order_id=self.parent_order_id).filter(Order.id != self.id).all()
    
    def get_child_orders(self):
        """Get child orders (split checks)"""
        return Order.query.filter_by(parent_order_id=self.id).all()
    
    def can_be_split(self):
        """Check if order can be split into multiple checks"""
        # Use direct query to get items
        from .order import OrderItem
        items_count = OrderItem.query.filter_by(order_id=self.id).count()
        return (self.status in [OrderStatus.PENDING, OrderStatus.CONFIRMED] and
                not self.parent_order_id and
                items_count > 0)
    
    def can_be_merged(self):
        """Check if order can be merged with another order"""
        return (self.status in [OrderStatus.PENDING, OrderStatus.CONFIRMED] and
                not self.parent_order_id and
                not self.child_orders)
    
    def can_be_transferred(self):
        """Check if order can be transferred to another table"""
        return self.status in [OrderStatus.PENDING, OrderStatus.CONFIRMED]
    
    def transfer_to_table(self, new_table_id, transferred_by_user_id=None):
        """Transfer order to a different table"""
        if not self.can_be_transferred():
            return False, "Order cannot be transferred in current status"
        
        old_table_id = self.table_id
        self.table_id = new_table_id
        
        # Update table statuses
        if old_table_id:
            old_table = Table.query.get(old_table_id)
            if old_table and not old_table.get_current_order():
                old_table.free()
        
        new_table = Table.query.get(new_table_id)
        if new_table:
            new_table.occupy()
        
        db.session.commit()
        return True, f"Order transferred to table {new_table.number}"
    
    def split_by_seat(self, seat_assignments):
        """Split order by seat assignments
        seat_assignments: dict with seat_number as key and list of item_ids as value
        """
        if not self.can_be_split():
            return False, "Order cannot be split"
        
        try:
            child_orders = []
            
            for seat_number, item_ids in seat_assignments.items():
                if not item_ids:
                    continue
                
                # Create child order for this seat
                child_order = Order(
                    table_id=self.table_id,
                    waiter_id=self.waiter_id,
                    seat_number=seat_number,
                    parent_order_id=self.id,
                    course_number=self.course_number,
                    user_id=self.user_id,
                    customer_id=self.customer_id,
                    restaurant_id=self.restaurant_id,
                    order_type=self.order_type,
                    status=self.status,
                    notes=f"Split from order {self.order_number} - Seat {seat_number}"
                )
                
                # Move items to child order
                for item_id in item_ids:
                    item = OrderItem.query.filter_by(order_id=self.id, id=item_id).first()
                    if item:
                        child_order.items.append(item)
                
                child_order.calculate_totals()
                db.session.add(child_order)
                child_orders.append(child_order)
            
            # Remove moved items from parent order
            for seat_number, item_ids in seat_assignments.items():
                for item_id in item_ids:
                    item = OrderItem.query.filter_by(id=item_id).first()
                    if item and item.order_id == self.id:
                        db.session.delete(item)
            
            # Recalculate parent order totals
            self.calculate_totals()
            db.session.commit()
            
            return True, f"Order split into {len(child_orders)} checks"
            
        except Exception as e:
            db.session.rollback()
            return False, f"Error splitting order: {str(e)}"
    
    def merge_with_order(self, other_order_id, merged_by_user_id=None):
        """Merge this order with another order"""
        if not self.can_be_merged():
            return False, "Order cannot be merged in current status"
        
        other_order = Order.query.get(other_order_id)
        if not other_order:
            return False, "Other order not found"
        
        if not other_order.can_be_merged():
            return False, "Other order cannot be merged"
        
        try:
            # Move all items from other order to this order
            for item in other_order.items:
                item.order_id = self.id
                self.items.append(item)
            
            # Transfer payments from other order
            for payment in other_order.payments:
                payment.order_id = self.id
                self.payments.append(payment)
            
            # Update other order status to merged
            other_order.status = OrderStatus.VOID
            other_order.notes = f"Merged into order {self.order_number}"
            
            # Recalculate totals
            self.calculate_totals()
            db.session.commit()
            
            return True, f"Order {other_order.order_number} merged into {self.order_number}"
            
        except Exception as e:
            db.session.rollback()
            return False, f"Error merging orders: {str(e)}"
    
    def to_dict(self, include_items=True, include_payments=True):
        """Convert order to dictionary for API responses"""
        result = {
            'id': self.id,
            'order_number': self.order_number,
            'table_id': self.table_id,
            'table_number': self.table.number if self.table else None,
            'waiter_id': self.waiter_id,
            'waiter_name': self.waiter.name if self.waiter else None,
            'seat_number': self.seat_number,
            'parent_order_id': self.parent_order_id,
            'parent_order_number': self.parent_order.order_number if self.parent_order else None,
            'course_number': self.course_number,
            'user_id': self.user_id,
            'user_name': self.user.name if self.user else None,
            'customer_id': self.customer_id,
            'customer_name': f"{self.customer.first_name} {self.customer.last_name}" if self.customer else None,
            'customer_code': self.customer.customer_code if self.customer else None,
            'order_type': self.order_type.value if self.order_type else None,
            'status': self.status.value if self.status else None,
            'subtotal': float(self.subtotal),
            'tax_rate': float(self.tax_rate),
            'tax_amount': float(self.tax_amount),
            'cgst_amount': float(self.cgst_amount),
            'sgst_amount': float(self.sgst_amount),
            'igst_amount': float(self.igst_amount),
            'cess_amount': float(self.cess_amount),
            'discount_amount': float(self.discount_amount),
            'discount_type': self.discount_type,
            'discount_reason': self.discount_reason,
            'service_charge': float(self.service_charge),
            'total': float(self.total),
            'total_paid': self.get_total_paid(),
            'balance_due': self.get_balance_due(),
            'notes': self.notes,
            'estimated_preparation_time': self.estimated_preparation_time,
            'actual_preparation_time': self.actual_preparation_time,
            'timer_started_at': self.timer_started_at.isoformat() if self.timer_started_at else None,
            'timer_completed_at': self.timer_completed_at.isoformat() if self.timer_completed_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }
        
        if include_items:
            # Use direct query to get items
            from .order import OrderItem
            items_list = OrderItem.query.filter_by(order_id=self.id).all()
            result['items'] = [item.to_dict() for item in items_list]
        
        if include_payments:
            # Use direct query to get payments
            from .order import Payment
            payments_list = Payment.query.filter_by(order_id=self.id).all()
            result['payments'] = [payment.to_dict() for payment in payments_list]
        
        return result
    
    def __repr__(self):
        return f'<Order {self.order_number} ({self.status.value if self.status else "Unknown"})>'

class OrderItem(db.Model):
    __tablename__ = 'order_items'
    
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('menu_items.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Numeric(10, 2), nullable=False)
    variant_id = db.Column(db.Integer, db.ForeignKey('item_variants.id'), nullable=True)
    notes = db.Column(db.Text)
    
    # Relationships
    variant = db.relationship('ItemVariant', backref='order_items')
    menu_item = db.relationship('MenuItem')
    add_ons = db.relationship('AddOn', secondary=order_item_add_ons, backref='order_items', lazy='select')
    
    def get_total_price(self):
        """Calculate total price for this order item"""
        unit_price = float(self.unit_price)
        
        # Add variant price modifier
        if self.variant:
            unit_price += float(self.variant.price_modifier)
        
        # Add add-on prices using direct query
        from app.models.menu import AddOn
        add_ons_query = db.session.query(AddOn).join(
            order_item_add_ons, order_item_add_ons.c.addon_id == AddOn.id
        ).filter(order_item_add_ons.c.order_item_id == self.id).all()
        for add_on in add_ons_query:
            unit_price += float(add_on.price)
        
        return unit_price * self.quantity
    
    def to_dict(self):
        """Convert order item to dictionary for API responses"""
        # Get add-ons using direct query
        from app.models.menu import AddOn
        add_ons_query = db.session.query(AddOn).join(
            order_item_add_ons, order_item_add_ons.c.addon_id == AddOn.id
        ).filter(order_item_add_ons.c.order_item_id == self.id).all()
        
        return {
            'id': self.id,
            'order_id': self.order_id,
            'item_id': self.item_id,
            'item_name': self.menu_item.name if self.menu_item else None,
            'quantity': self.quantity,
            'unit_price': float(self.unit_price),
            'variant_id': self.variant_id,
            'variant_name': self.variant.name if self.variant else None,
            'variant_price_modifier': float(self.variant.price_modifier) if self.variant else 0.0,
            'notes': self.notes,
            'add_ons': [addon.to_dict() for addon in add_ons_query],
            'total_price': self.get_total_price()
        }
    
    def __repr__(self):
        return f'<OrderItem {self.quantity}x {self.menu_item.name if self.menu_item else "Unknown"}>'

class Payment(db.Model):
    __tablename__ = 'payments'
    
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    method = db.Column(db.Enum(PaymentMethod), nullable=False)
    transaction_id = db.Column(db.String(100))
    reference_number = db.Column(db.String(100))
    status = db.Column(db.Enum('pending', 'completed', 'failed', 'refunded'), default='pending')
    tip_amount = db.Column(db.Numeric(10, 2), default=0.00)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    processed_at = db.Column(db.DateTime)
    
    def is_successful(self):
        """Check if payment was successful"""
        return self.status == 'completed'
    
    def mark_completed(self):
        """Mark payment as completed"""
        self.status = 'completed'
        self.processed_at = datetime.utcnow()
    
    def mark_failed(self):
        """Mark payment as failed"""
        self.status = 'failed'
        self.processed_at = datetime.utcnow()
    
    def to_dict(self):
        """Convert payment to dictionary for API responses"""
        return {
            'id': self.id,
            'order_id': self.order_id,
            'amount': float(self.amount),
            'method': self.method.value if self.method else None,
            'transaction_id': self.transaction_id,
            'reference_number': self.reference_number,
            'status': self.status,
            'tip_amount': float(self.tip_amount),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'processed_at': self.processed_at.isoformat() if self.processed_at else None
        }
    
    def __repr__(self):
        return f'<Payment {self.method.value if self.method else "Unknown"} ${self.amount} ({self.status})>'

class SplitBill(db.Model):
    """Split bill tracking model"""
    __tablename__ = 'split_bills'
    
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    split_type = db.Column(db.Enum('equal', 'custom', 'items'), nullable=False)
    total_amount = db.Column(db.Numeric(10, 2), nullable=False)
    split_details = db.Column(db.Text)  # JSON string with split details
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    order = db.relationship('Order', backref='split_bills')
    creator = db.relationship('User', backref='created_split_bills')
    
    def get_split_details(self):
        """Get split details as dictionary"""
        if self.split_details:
            try:
                return json.loads(self.split_details)
            except (json.JSONDecodeError, TypeError):
                return []
        return []
    
    def set_split_details(self, details):
        """Set split details from dictionary"""
        self.split_details = json.dumps(details)
    
    def get_split_count(self):
        """Get number of splits"""
        details = self.get_split_details()
        return len(details)
    
    def get_payment_methods(self):
        """Get unique payment methods used"""
        details = self.get_split_details()
        methods = [detail.get('payment_method') for detail in details if detail.get('payment_method')]
        return list(set(methods))
    
    def to_dict(self):
        """Convert split bill to dictionary for API responses"""
        return {
            'id': self.id,
            'order_id': self.order_id,
            'split_type': self.split_type,
            'total_amount': float(self.total_amount),
            'split_details': self.get_split_details(),
            'split_count': self.get_split_count(),
            'payment_methods': self.get_payment_methods(),
            'created_by': self.created_by,
            'creator_name': self.creator.name if self.creator else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def __repr__(self):
        return f'<SplitBill {self.split_type} for Order {self.order_id} ({self.get_split_count()} splits)>'