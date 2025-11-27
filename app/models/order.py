from datetime import datetime
from enum import Enum
from typing import List, TYPE_CHECKING
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app import db

if TYPE_CHECKING:
    from app.models.menu import MenuItem, AddOn, ItemVariant
    from app.models.table import Table
    from app.models.user import User

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

class PaymentMethod(Enum):
    CASH = 'cash'
    CARD = 'card'
    UPI = 'upi'
    WALLET = 'wallet'
    GIFT_CARD = 'gift_card'

class Order(db.Model):
    __tablename__ = 'orders'
    
    id = db.Column(db.Integer, primary_key=True)
    table_id = db.Column(db.Integer, db.ForeignKey('tables.id'), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurants.id'), nullable=True)
    order_number = db.Column(db.String(20), unique=True, nullable=False)
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
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    
    # Relationships
    restaurant = db.relationship('Restaurant', back_populates='orders')
    table = db.relationship('Table', back_populates='orders')
    user = db.relationship('User', back_populates='orders')
    items = db.relationship('OrderItem', backref='order', lazy='select', cascade='all, delete-orphan')
    payments = db.relationship('Payment', backref='order', lazy='select', cascade='all, delete-orphan')
    
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
        self.status = new_status
        self.updated_at = datetime.utcnow()
        
        if new_status in [OrderStatus.SERVED, OrderStatus.CANCELLED, OrderStatus.VOID]:
            self.completed_at = datetime.utcnow()
    
    def can_be_cancelled(self):
        """Check if order can be cancelled"""
        return self.status in [OrderStatus.PENDING, OrderStatus.CONFIRMED]
    
    def can_be_modified(self):
        """Check if order can be modified"""
        return self.status in [OrderStatus.PENDING, OrderStatus.CONFIRMED]
    
    def to_dict(self, include_items=True, include_payments=True):
        """Convert order to dictionary for API responses"""
        result = {
            'id': self.id,
            'order_number': self.order_number,
            'table_id': self.table_id,
            'table_number': self.table.number if self.table else None,
            'user_id': self.user_id,
            'user_name': self.user.name if self.user else None,
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