"""
Migration script to add report scheduling tables
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models.report_schedule import ReportSchedule, ReportExecution
from datetime import datetime

def migrate():
    """Create report scheduling tables"""
    app = create_app()
    
    with app.app_context():
        # Create tables
        print("Creating report_schedules table...")
        ReportSchedule.__table__.create(db.engine, checkfirst=True)
        
        print("Creating report_executions table...")
        ReportExecution.__table__.create(db.engine, checkfirst=True)
        
        print("Report scheduling tables created successfully!")

if __name__ == '__main__':
    migrate()