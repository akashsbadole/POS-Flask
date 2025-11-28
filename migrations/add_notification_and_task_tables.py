"""
Migration script to add notification and task tables for license renewal reminders
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models.notification import Notification, NotificationLog, NotificationPreference, EmailTemplate, SmsTemplate
from app.models.task import ScheduledTask, TaskLog

def migrate():
    """Create notification and task tables"""
    app = create_app()
    
    with app.app_context():
        print("Creating notification and task tables...")
        
        try:
            # Create tables
            Notification.__table__.create(db.engine, checkfirst=True)
            NotificationLog.__table__.create(db.engine, checkfirst=True)
            NotificationPreference.__table__.create(db.engine, checkfirst=True)
            EmailTemplate.__table__.create(db.engine, checkfirst=True)
            SmsTemplate.__table__.create(db.engine, checkfirst=True)
            ScheduledTask.__table__.create(db.engine, checkfirst=True)
            TaskLog.__table__.create(db.engine, checkfirst=True)
            
            print("Tables created successfully")
            
            # Create default scheduled task for license renewal reminders
            from datetime import datetime, timedelta
            
            existing_task = ScheduledTask.query.filter_by(
                task_type='license_renewal'
            ).first()
            
            if not existing_task:
                default_task = ScheduledTask(
                    name='License Renewal Reminders',
                    description='Send automated license renewal reminders',
                    task_type='license_renewal',
                    frequency='daily',
                    next_run=datetime.utcnow() + timedelta(days=1),
                    is_active=True
                )
                db.session.add(default_task)
                db.session.commit()
                print("Default license renewal task created")
            else:
                print("License renewal task already exists")
            
            print("\nMigration completed successfully!")
            
        except Exception as e:
            print(f"Error during migration: {str(e)}")
            sys.exit(1)

if __name__ == '__main__':
    migrate()