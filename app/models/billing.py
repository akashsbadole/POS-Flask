from datetime import datetime, timedelta
from typing import List, TYPE_CHECKING
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app import db

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.restaurant import Restaurant

class Invoice(db.Model):
    """Invoice model for billing"""
    __tablename__ = 'invoices'
    
    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String(50), unique=True, nullable=False)
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurants.id'), nullable=False)
    customer_name = db.Column(db.String(100), nullable=False)
    customer_email = db.Column(db.String(120))
    customer_phone = db.Column(db.String(20))
    customer_address = db.Column(db.Text)
    
    # Invoice details
    issue_date = db.Column(db.DateTime, default=datetime.utcnow)
    due_date = db.Column(db.DateTime)
    status = db.Column(db.Enum('draft', 'sent', 'paid', 'overdue', 'cancelled'), default='draft')
    subtotal = db.Column(db.Numeric(12, 2), nullable=False)
    tax_amount = db.Column(db.Numeric(12, 2), default=0.00)
    cgst_amount = db.Column(db.Numeric(12, 2), default=0.00)
    sgst_amount = db.Column(db.Numeric(12, 2), default=0.00)
    igst_amount = db.Column(db.Numeric(12, 2), default=0.00)
    cess_amount = db.Column(db.Numeric(12, 2), default=0.00)
    discount_amount = db.Column(db.Numeric(12, 2), default=0.00)
    total_amount = db.Column(db.Numeric(12, 2), nullable=False)
    paid_amount = db.Column(db.Numeric(12, 2), default=0.00)
    balance_amount = db.Column(db.Numeric(12, 2), nullable=False)
    
    # Additional fields
    notes = db.Column(db.Text)
    terms = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    paid_at = db.Column(db.DateTime)
    
    # Relationships
    restaurant = relationship('Restaurant', backref='invoices')
    items = relationship('InvoiceItem', backref='invoice', cascade='all, delete-orphan')
    payments = relationship('InvoicePayment', backref='invoice', cascade='all, delete-orphan')
    
    def calculate_totals(self):
        """Calculate invoice totals"""
        from decimal import Decimal
        self.subtotal = sum(Decimal(str(item.total_price)) for item in self.items)
        self.tax_amount = sum(Decimal(str(item.tax_amount)) for item in self.items)
        self.total_amount = self.subtotal + self.tax_amount
        self.balance_amount = self.total_amount - Decimal(str(self.paid_amount))
    
    def mark_as_sent(self):
        """Mark invoice as sent"""
        self.status = 'sent'
        self.updated_at = datetime.utcnow()
        if not self.due_date:
            self.due_date = datetime.utcnow() + timedelta(days=30)
    
    def mark_as_paid(self, amount):
        """Mark invoice as paid"""
        self.paid_amount += amount
        if self.paid_amount >= self.total_amount:
            self.status = 'paid'
            self.paid_at = datetime.utcnow()
        else:
            self.status = 'partially_paid'
        self.balance_amount = self.total_amount - self.paid_amount
        self.updated_at = datetime.utcnow()
    
    def check_overdue(self):
        """Check if invoice is overdue"""
        if self.status in ['paid', 'cancelled']:
            return False
        return self.due_date and datetime.utcnow() > self.due_date
    
    def to_dict(self):
        """Convert invoice to dictionary for API responses"""
        return {
            'id': self.id,
            'invoice_number': self.invoice_number,
            'restaurant_id': self.restaurant_id,
            'restaurant_name': self.restaurant.name if self.restaurant else None,
            'customer_name': self.customer_name,
            'customer_email': self.customer_email,
            'customer_phone': self.customer_phone,
            'customer_address': self.customer_address,
            'issue_date': self.issue_date.isoformat() if self.issue_date else None,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'status': self.status,
            'subtotal': float(self.subtotal),
            'tax_amount': float(self.tax_amount),
            'cgst_amount': float(self.cgst_amount),
            'sgst_amount': float(self.sgst_amount),
            'igst_amount': float(self.igst_amount),
            'cess_amount': float(self.cess_amount),
            'discount_amount': float(self.discount_amount),
            'total_amount': float(self.total_amount),
            'paid_amount': float(self.paid_amount),
            'balance_amount': float(self.balance_amount),
            'notes': self.notes,
            'terms': self.terms,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'paid_at': self.paid_at.isoformat() if self.paid_at else None,
            'items': [item.to_dict() for item in self.items],
            'payments': [payment.to_dict() for payment in self.payments]
        }
    
    def __repr__(self):
        return f'<Invoice {self.invoice_number} ({self.status})>'

class InvoiceItem(db.Model):
    """Invoice items model"""
    __tablename__ = 'invoice_items'
    
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoices.id'), nullable=False)
    description = db.Column(db.String(255), nullable=False)
    quantity = db.Column(db.Numeric(10, 3), nullable=False)
    unit_price = db.Column(db.Numeric(10, 2), nullable=False)
    discount_amount = db.Column(db.Numeric(10, 2), default=0.00)
    tax_rate = db.Column(db.Numeric(5, 4), default=0.00)
    tax_amount = db.Column(db.Numeric(10, 2), default=0.00)
    total_price = db.Column(db.Numeric(12, 2), nullable=False)
    
    def calculate_totals(self):
        """Calculate item totals"""
        subtotal = float(self.quantity) * float(self.unit_price)
        self.total_price = subtotal - float(self.discount_amount) + float(self.tax_amount)
    
    def to_dict(self):
        """Convert invoice item to dictionary for API responses"""
        return {
            'id': self.id,
            'invoice_id': self.invoice_id,
            'description': self.description,
            'quantity': float(self.quantity),
            'unit_price': float(self.unit_price),
            'discount_amount': float(self.discount_amount),
            'tax_rate': float(self.tax_rate),
            'tax_amount': float(self.tax_amount),
            'total_price': float(self.total_price)
        }
    
    def __repr__(self):
        return f'<InvoiceItem {self.description} x{self.quantity}>'

class InvoicePayment(db.Model):
    """Invoice payments model"""
    __tablename__ = 'invoice_payments'
    
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoices.id'), nullable=False)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    payment_method = db.Column(db.Enum('cash', 'card', 'upi', 'bank_transfer', 'cheque'), nullable=False)
    transaction_id = db.Column(db.String(100))
    reference_number = db.Column(db.String(100))
    payment_date = db.Column(db.DateTime, default=datetime.utcnow)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        """Convert invoice payment to dictionary for API responses"""
        return {
            'id': self.id,
            'invoice_id': self.invoice_id,
            'amount': float(self.amount),
            'payment_method': self.payment_method,
            'transaction_id': self.transaction_id,
            'reference_number': self.reference_number,
            'payment_date': self.payment_date.isoformat() if self.payment_date else None,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def __repr__(self):
        return f'<InvoicePayment {self.payment_method} ${self.amount}>'

class BillingSetting(db.Model):
    """Billing settings for restaurants"""
    __tablename__ = 'billing_settings'
    
    id = db.Column(db.Integer, primary_key=True)
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurants.id'), nullable=False)
    
    # Invoice settings
    invoice_prefix = db.Column(db.String(10), default='INV')
    auto_generate_numbers = db.Column(db.Boolean, default=True)
    next_invoice_number = db.Column(db.Integer, default=1)
    
    # Payment settings
    default_payment_terms = db.Column(db.Integer, default=30)  # days
    allow_partial_payments = db.Column(db.Boolean, default=True)
    auto_send_reminders = db.Column(db.Boolean, default=True)
    reminder_days = db.Column(db.String(100), default='7,14,30')  # comma-separated days
    
    # Tax settings
    default_tax_rate = db.Column(db.Numeric(5, 4), default=0.18)
    tax_inclusive = db.Column(db.Boolean, default=True)
    
    # Currency settings
    currency_code = db.Column(db.String(3), default='INR')
    currency_symbol = db.Column(db.String(5), default='₹')
    
    # Email settings
    email_from_address = db.Column(db.String(120))
    email_from_name = db.Column(db.String(100))
    email_cc_addresses = db.Column(db.Text)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    restaurant = relationship('Restaurant', backref='billing_settings')
    
    def generate_invoice_number(self):
        """Generate next invoice number"""
        if self.auto_generate_numbers:
            invoice_number = f"{self.invoice_prefix}{self.next_invoice_number:06d}"
            self.next_invoice_number += 1
            return invoice_number
        return None
    
    def get_reminder_days(self):
        """Get reminder days as list"""
        return [int(day.strip()) for day in self.reminder_days.split(',') if day.strip()]
    
    def to_dict(self):
        """Convert billing settings to dictionary for API responses"""
        return {
            'id': self.id,
            'restaurant_id': self.restaurant_id,
            'invoice_prefix': self.invoice_prefix,
            'auto_generate_numbers': self.auto_generate_numbers,
            'next_invoice_number': self.next_invoice_number,
            'default_payment_terms': self.default_payment_terms,
            'allow_partial_payments': self.allow_partial_payments,
            'auto_send_reminders': self.auto_send_reminders,
            'reminder_days': self.get_reminder_days(),
            'default_tax_rate': float(self.default_tax_rate),
            'tax_inclusive': self.tax_inclusive,
            'currency_code': self.currency_code,
            'currency_symbol': self.currency_symbol,
            'email_from_address': self.email_from_address,
            'email_from_name': self.email_from_name,
            'email_cc_addresses': self.email_cc_addresses,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self):
        return f'<BillingSetting for Restaurant {self.restaurant_id}>'

class RecurringInvoice(db.Model):
    """Recurring invoice model"""
    __tablename__ = 'recurring_invoices'
    
    id = db.Column(db.Integer, primary_key=True)
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurants.id'), nullable=False)
    customer_name = db.Column(db.String(100), nullable=False)
    customer_email = db.Column(db.String(120))
    description = db.Column(db.String(255), nullable=False)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    
    # Recurrence settings
    frequency = db.Column(db.Enum('weekly', 'monthly', 'quarterly', 'yearly'), nullable=False)
    interval_count = db.Column(db.Integer, default=1)  # e.g., every 2 weeks, every 3 months
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime)
    last_generated_date = db.Column(db.DateTime)
    next_generation_date = db.Column(db.DateTime)
    
    # Status
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    restaurant = relationship('Restaurant', backref='recurring_invoices')
    
    def calculate_next_generation_date(self):
        """Calculate next generation date"""
        if not self.last_generated_date:
            return self.start_date
        
        if self.frequency == 'weekly':
            return self.last_generated_date + timedelta(weeks=self.interval_count)
        elif self.frequency == 'monthly':
            return self.last_generated_date + timedelta(days=30 * self.interval_count)
        elif self.frequency == 'quarterly':
            return self.last_generated_date + timedelta(days=90 * self.interval_count)
        elif self.frequency == 'yearly':
            return self.last_generated_date + timedelta(days=365 * self.interval_count)
        
        return self.last_generated_date + timedelta(days=30)
    
    def should_generate_invoice(self):
        """Check if invoice should be generated"""
        if not self.is_active or self.end_date:
            return False
        
        return datetime.utcnow() >= self.calculate_next_generation_date()
    
    def generate_invoice(self):
        """Generate invoice from recurring template"""
        if not self.should_generate_invoice():
            return None
        
        billing_settings = self.restaurant.billing_settings[0] if self.restaurant.billing_settings else None
        if not billing_settings:
            return None
        
        invoice = Invoice(
            invoice_number=billing_settings.generate_invoice_number(),
            restaurant_id=self.restaurant_id,
            customer_name=self.customer_name,
            customer_email=self.customer_email,
            subtotal=self.amount,
            tax_amount=self.amount * float(billing_settings.default_tax_rate),
            total_amount=self.amount * (1 + float(billing_settings.default_tax_rate)),
            due_date=datetime.utcnow() + timedelta(days=billing_settings.default_payment_terms)
        )
        
        # Add invoice item
        invoice_item = InvoiceItem(
            description=self.description,
            quantity=1,
            unit_price=self.amount,
            tax_rate=billing_settings.default_tax_rate,
            tax_amount=self.amount * float(billing_settings.default_tax_rate),
            total_price=self.amount * (1 + float(billing_settings.default_tax_rate))
        )
        invoice.items.append(invoice_item)
        
        # Update dates
        self.last_generated_date = datetime.utcnow()
        self.next_generation_date = self.calculate_next_generation_date()
        
        return invoice
    
    def to_dict(self):
        """Convert recurring invoice to dictionary for API responses"""
        return {
            'id': self.id,
            'restaurant_id': self.restaurant_id,
            'customer_name': self.customer_name,
            'customer_email': self.customer_email,
            'description': self.description,
            'amount': float(self.amount),
            'frequency': self.frequency,
            'interval_count': self.interval_count,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'last_generated_date': self.last_generated_date.isoformat() if self.last_generated_date else None,
            'next_generation_date': self.next_generation_date.isoformat() if self.next_generation_date else None,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self):
        return f'<RecurringInvoice {self.description} for {self.customer_name}>'