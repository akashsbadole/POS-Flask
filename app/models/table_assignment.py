from datetime import datetime
from app import db

class TableAssignment(db.Model):
    __tablename__ = 'table_assignments'
    
    id = db.Column(db.Integer, primary_key=True)
    table_id = db.Column(db.Integer, db.ForeignKey('tables.id'), nullable=False)
    waiter_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    assigned_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    relieved_at = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    
    # Performance tracking fields
    orders_served = db.Column(db.Integer, default=0)  # Number of orders served during this assignment
    total_revenue = db.Column(db.Float, default=0.0)  # Total revenue generated during assignment
    customer_rating = db.Column(db.Float, nullable=True)  # Average customer rating (1-5)
    tip_amount = db.Column(db.Float, default=0.0)  # Total tips received
    assignment_notes = db.Column(db.Text, nullable=True)  # Notes about the assignment
    
    # Additional metadata
    assigned_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # Who made the assignment
    relieved_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # Who relieved the waiter
    
    # Relationships
    table = db.relationship('Table', back_populates='assignments')
    waiter = db.relationship('User', foreign_keys=[waiter_id], back_populates='table_assignments')
    assigned_by_user = db.relationship('User', foreign_keys=[assigned_by])
    relieved_by_user = db.relationship('User', foreign_keys=[relieved_by])
    
    def get_duration_minutes(self):
        """Get assignment duration in minutes"""
        end_time = self.relieved_at or datetime.utcnow()
        return (end_time - self.assigned_at).total_seconds() / 60
    
    def get_hours_worked(self):
        """Get assignment duration in hours"""
        return self.get_duration_minutes() / 60
    
    def relieve_assignment(self, relieved_by_user_id=None, notes=None):
        """Mark assignment as relieved"""
        self.relieved_at = datetime.utcnow()
        self.is_active = False
        if relieved_by_user_id:
            self.relieved_by = relieved_by_user_id
        if notes:
            self.assignment_notes = notes
        db.session.commit()
    
    def update_performance_metrics(self, orders_served=None, total_revenue=None, 
                                 customer_rating=None, tip_amount=None):
        """Update performance metrics for the assignment"""
        if orders_served is not None:
            self.orders_served = orders_served
        if total_revenue is not None:
            self.total_revenue = total_revenue
        if customer_rating is not None:
            self.customer_rating = customer_rating
        if tip_amount is not None:
            self.tip_amount = tip_amount
        db.session.commit()
    
    def get_performance_summary(self):
        """Get a summary of performance metrics"""
        return {
            'orders_served': self.orders_served,
            'total_revenue': self.total_revenue,
            'customer_rating': self.customer_rating,
            'tip_amount': self.tip_amount,
            'hours_worked': self.get_hours_worked(),
            'orders_per_hour': self.orders_served / max(self.get_hours_worked(), 0.01),
            'revenue_per_hour': self.total_revenue / max(self.get_hours_worked(), 0.01),
            'tip_percentage': (self.tip_amount / max(self.total_revenue, 0.01)) * 100 if self.total_revenue > 0 else 0
        }
    
    def to_dict(self, include_performance=False):
        """Convert table assignment to dictionary for API responses"""
        result = {
            'id': self.id,
            'table_id': self.table_id,
            'table_number': self.table.number if self.table else None,
            'waiter_id': self.waiter_id,
            'waiter_name': self.waiter.name if self.waiter else None,
            'assigned_at': self.assigned_at.isoformat() if self.assigned_at else None,
            'relieved_at': self.relieved_at.isoformat() if self.relieved_at else None,
            'is_active': self.is_active,
            'duration_minutes': self.get_duration_minutes(),
            'assigned_by': self.assigned_by_user.name if self.assigned_by_user else None,
            'relieved_by': self.relieved_by_user.name if self.relieved_by_user else None,
            'assignment_notes': self.assignment_notes
        }
        
        if include_performance:
            result.update(self.get_performance_summary())
        
        return result
    
    @classmethod
    def get_active_assignment_for_table(cls, table_id):
        """Get the currently active assignment for a table"""
        return cls.query.filter_by(
            table_id=table_id,
            is_active=True
        ).first()
    
    @classmethod
    def get_active_assignments_for_waiter(cls, waiter_id):
        """Get all currently active assignments for a waiter"""
        return cls.query.filter_by(
            waiter_id=waiter_id,
            is_active=True
        ).all()
    
    @classmethod
    def get_assignment_history_for_table(cls, table_id, limit=50):
        """Get assignment history for a table"""
        return cls.query.filter_by(table_id=table_id)\
                       .order_by(cls.assigned_at.desc())\
                       .limit(limit).all()
    
    @classmethod
    def get_assignment_history_for_waiter(cls, waiter_id, limit=100):
        """Get assignment history for a waiter"""
        return cls.query.filter_by(waiter_id=waiter_id)\
                       .order_by(cls.assigned_at.desc())\
                       .limit(limit).all()
    
    def __repr__(self):
        status = "Active" if self.is_active else "Relieved"
        return f'<TableAssignment Table {self.table.number if self.table else "Unknown"} -> {self.waiter.name if self.waiter else "Unknown"} ({status})>'