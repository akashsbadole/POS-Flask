"""
Migration script for enhanced reporting tables
Creates tables for comprehensive analytics and reporting
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models.enhanced_reports import (
    DailySalesSummary, InventoryMovement, WasteTracking, 
    EmployeePerformance, CustomerAnalytics, OperationalMetrics, ReportCache
)

def create_enhanced_reports_tables():
    """Create enhanced reporting tables"""
    app = create_app()
    
    with app.app_context():
        print("Creating enhanced reporting tables...")
        
        # Create all tables
        db.create_all()
        
        # Create indexes for performance
        create_indexes()
        
        print("Enhanced reporting tables created successfully!")

def create_indexes():
    """Create performance indexes for reporting tables"""
    print("Creating performance indexes...")
    
    # Use SQLAlchemy's Index creation instead of raw SQL
    from sqlalchemy import Index
    
    # These indexes will be created automatically by SQLAlchemy based on the model definitions
    # The models already have index=True on key columns
    
    print("Performance indexes will be created automatically by SQLAlchemy!")

if __name__ == '__main__':
    create_enhanced_reports_tables()