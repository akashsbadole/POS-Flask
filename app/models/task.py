"""
Task model for Restaurant POS System
Handles scheduled tasks including license renewal reminders
"""
from datetime import datetime
from app import db
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship


class ScheduledTask(db.Model):
    """Scheduled tasks for background processing"""
    __tablename__ = 'scheduled_tasks'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, index=True)
    description = Column(Text)
    task_type = Column(String(50), nullable=False)  # license_renewal, backup, report, etc.
    frequency = Column(String(20))  # daily, weekly, monthly, once
    next_run = Column(DateTime, nullable=False)
    last_run = Column(DateTime)
    is_active = Column(Boolean, default=True)
    parameters = Column(JSON)  # Task parameters as JSON
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<ScheduledTask {self.name}>'
    
    def mark_as_run(self):
        """Mark task as run and schedule next run"""
        from datetime import timedelta
        
        self.last_run = datetime.utcnow()
        
        # Calculate next run time based on frequency
        # Check if frequency is set and compare with string values
        frequency_value = getattr(self, 'frequency', None)
        if frequency_value == 'daily':
            self.next_run = self.last_run + timedelta(days=1)
        elif frequency_value == 'weekly':
            self.next_run = self.last_run + timedelta(weeks=1)
        elif frequency_value == 'monthly':
            self.next_run = self.last_run + timedelta(days=30)
        elif frequency_value == 'once':
            self.is_active = False
        
        db.session.commit()
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'task_type': self.task_type,
            'frequency': self.frequency,
            'next_run': self.next_run.isoformat() if getattr(self, 'next_run', None) else None,
            'last_run': self.last_run.isoformat() if getattr(self, 'last_run', None) else None,
            'is_active': self.is_active,
            'parameters': self.parameters,
            'created_at': self.created_at.isoformat() if getattr(self, 'created_at', None) else None,
            'updated_at': self.updated_at.isoformat() if getattr(self, 'updated_at', None) else None
        }


class TaskLog(db.Model):
    """Log of task executions"""
    __tablename__ = 'task_logs'
    
    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, ForeignKey('scheduled_tasks.id'), nullable=False)
    status = Column(String(20), nullable=False)  # success, error, running
    message = Column(Text)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    duration_seconds = Column(Integer)
    
    # Relationships
    task = relationship('ScheduledTask')
    
    def __repr__(self):
        return f'<TaskLog {self.task.name} - {self.status}>'
    
    def mark_completed(self, status='success', message=None):
        """Mark task as completed"""
        self.status = status
        self.completed_at = datetime.utcnow()
        if getattr(self, 'started_at', None):
            self.duration_seconds = int((self.completed_at - self.started_at).total_seconds())
        if message:
            self.message = message
        db.session.commit()
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'task_id': self.task_id,
            'task_name': self.task.name if self.task else None,
            'status': self.status,
            'message': self.message,
            'started_at': self.started_at.isoformat() if getattr(self, 'started_at', None) else None,
            'completed_at': self.completed_at.isoformat() if getattr(self, 'completed_at', None) else None,
            'duration_seconds': self.duration_seconds
        }