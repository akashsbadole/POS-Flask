from datetime import datetime
from enum import Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Boolean, DateTime, String, Text, Integer, ForeignKey
from app import db

class ReportType(Enum):
    SALES = "sales"
    ITEMS = "items"
    STAFF = "staff"
    GST = "gst"
    ACCOUNTING = "accounting"
    EXPENSES = "expenses"
    RESTAURANT_PERFORMANCE = "restaurant_performance"

class ScheduleFrequency(Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"

class DeliveryMethod(Enum):
    EMAIL = "email"
    DOWNLOAD = "download"
    BOTH = "both"

class ReportSchedule(db.Model):
    __tablename__ = 'report_schedules'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    report_type = db.Column(db.Enum(ReportType), nullable=False)
    frequency = db.Column(db.Enum(ScheduleFrequency), nullable=False)
    delivery_method = db.Column(db.Enum(DeliveryMethod), nullable=False, default=DeliveryMethod.EMAIL)
    
    # Scheduling details
    is_active = db.Column(db.Boolean, default=True)
    next_run = db.Column(db.DateTime)
    last_run = db.Column(db.DateTime)
    
    # Report parameters (stored as JSON)
    parameters = db.Column(db.Text)  # JSON string for report parameters
    
    # Delivery details
    email_recipients = db.Column(db.Text)  # JSON array of email addresses
    email_subject = db.Column(db.String(200))
    email_message = db.Column(db.Text)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Relationships
    creator = db.relationship('User', backref='report_schedules')
    
    def __repr__(self):
        return f'<ReportSchedule {self.name} ({self.report_type.value})>'
    
    def calculate_next_run(self):
        """Calculate the next run time based on frequency"""
        from datetime import timedelta
        
        now = datetime.utcnow()
        
        if self.frequency == ScheduleFrequency.DAILY:
            return now + timedelta(days=1)
        elif self.frequency == ScheduleFrequency.WEEKLY:
            return now + timedelta(weeks=1)
        elif self.frequency == ScheduleFrequency.MONTHLY:
            # Simple monthly calculation (adds ~30 days)
            return now + timedelta(days=30)
        elif self.frequency == ScheduleFrequency.QUARTERLY:
            return now + timedelta(days=90)
        elif self.frequency == ScheduleFrequency.YEARLY:
            return now + timedelta(days=365)
        
        return now + timedelta(days=1)  # Default to daily
    
    def get_parameters(self):
        """Get report parameters as dictionary"""
        import json
        if self.parameters:
            try:
                return json.loads(self.parameters)
            except:
                return {}
        return {}
    
    def set_parameters(self, params_dict):
        """Set report parameters from dictionary"""
        import json
        self.parameters = json.dumps(params_dict)
    
    def get_email_recipients(self):
        """Get email recipients as list"""
        import json
        if self.email_recipients:
            try:
                return json.loads(self.email_recipients)
            except:
                return []
        return []
    
    def set_email_recipients(self, recipients_list):
        """Set email recipients from list"""
        import json
        self.email_recipients = json.dumps(recipients_list)
    
    def is_due(self):
        """Check if the report is due to run"""
        if not self.is_active:
            return False
        
        if not self.next_run:
            return True
        
        return datetime.utcnow() >= self.next_run
    
    def mark_as_run(self):
        """Mark the schedule as run and calculate next run time"""
        self.last_run = datetime.utcnow()
        self.next_run = self.calculate_next_run()
        self.updated_at = datetime.utcnow()

class ReportExecution(db.Model):
    __tablename__ = 'report_executions'
    
    id = db.Column(db.Integer, primary_key=True)
    schedule_id = db.Column(db.Integer, db.ForeignKey('report_schedules.id'), nullable=False)
    
    # Execution details
    status = db.Column(db.Enum('pending', 'running', 'completed', 'failed'), default='pending')
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    
    # Report details
    report_type = db.Column(db.Enum(ReportType), nullable=False)
    parameters = db.Column(db.Text)  # JSON string for parameters used
    
    # Output details
    file_path = db.Column(db.String(500))
    file_size = db.Column(db.Integer)
    delivery_status = db.Column(db.Enum('pending', 'sent', 'failed'), default='pending')
    
    # Error details
    error_message = db.Column(db.Text)
    retry_count = db.Column(db.Integer, default=0)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    schedule = db.relationship('ReportSchedule', backref='executions')
    
    def __repr__(self):
        return f'<ReportExecution {self.report_type.value} ({self.status})>'
    
    def get_parameters(self):
        """Get execution parameters as dictionary"""
        import json
        if self.parameters:
            try:
                return json.loads(self.parameters)
            except:
                return {}
        return {}
    
    def set_parameters(self, params_dict):
        """Set execution parameters from dictionary"""
        import json
        self.parameters = json.dumps(params_dict)
    
    def mark_as_started(self):
        """Mark execution as started"""
        self.status = 'running'
        self.started_at = datetime.utcnow()
    
    def mark_as_completed(self, file_path=None, file_size=None):
        """Mark execution as completed"""
        self.status = 'completed'
        self.completed_at = datetime.utcnow()
        if file_path:
            self.file_path = file_path
        if file_size:
            self.file_size = file_size
    
    def mark_as_failed(self, error_message):
        """Mark execution as failed"""
        self.status = 'failed'
        self.completed_at = datetime.utcnow()
        self.error_message = error_message
        self.retry_count += 1
    
    def execution_duration(self):
        """Get execution duration in seconds"""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return 0