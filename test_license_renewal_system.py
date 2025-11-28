#!/usr/bin/env python3
"""
Test script for License Renewal Reminder System
Tests the automated renewal reminders functionality
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models.license import License
from app.models.user import User
from app.models.restaurant import Restaurant
from app.models.notification import Notification
from app.models.task import ScheduledTask, TaskLog
from app.services.license_renewal_service import LicenseRenewalService
from datetime import datetime, timedelta

def test_license_renewal_system():
    """Test the license renewal reminder system"""
    app = create_app()
    
    with app.app_context():
        print("Testing License Renewal Reminder System...")
        
        try:
            # 0. Clean up any existing test data first
            print("\n0. Cleaning up existing test data...")
            License.query.filter(License.license_key.like('TEST-%')).delete()
            Notification.query.filter_by(type='license_renewal').delete()
            TaskLog.query.filter(TaskLog.message.like('%Test execution%')).delete()
            db.session.commit()
            print("   Cleaned up existing test data")
            
            # 1. Test creating test licenses with different expiry dates
            print("\n1. Creating test licenses...")
            
            # Get or create test user
            test_user = User.query.filter_by(email='test@example.com').first()
            if not test_user:
                test_user = User()
                test_user.email = 'test@example.com'
                test_user.password_hash = 'test'
                test_user.name = 'Test User'
                test_user.role = 'super_admin'
                db.session.add(test_user)
                db.session.commit()
                print("   Created test user")
            
            # Get or create test restaurant
            test_restaurant = Restaurant.query.filter_by(name='Test Restaurant').first()
            if not test_restaurant:
                test_restaurant = Restaurant(
                    name='Test Restaurant',
                    address='123 Test St',
                    phone='555-1234',
                    email='test@restaurant.com'
                )
                db.session.add(test_restaurant)
                db.session.commit()
                print("   Created test restaurant")
            
            # Create test licenses with different expiry periods
            test_licenses = []
            
            # License expiring in 90 days
            license_90 = License(
                license_key='TEST-90-DAYS',
                license_type='SOFTWARE',
                product_name='Restaurant POS Pro',
                restaurant_id=test_restaurant.id,
                user_id=test_user.id,
                status='active',
                issued_date=datetime.utcnow(),
                expiry_date=datetime.utcnow() + timedelta(days=90),
                max_activations=1
            )
            test_licenses.append(license_90)
            
            # License expiring in 30 days
            license_30 = License(
                license_key='TEST-30-DAYS',
                license_type='SOFTWARE',
                product_name='Restaurant POS Pro',
                restaurant_id=test_restaurant.id,
                user_id=test_user.id,
                status='active',
                issued_date=datetime.utcnow(),
                expiry_date=datetime.utcnow() + timedelta(days=30),
                max_activations=1
            )
            test_licenses.append(license_30)
            
            # License expiring in 7 days
            license_7 = License(
                license_key='TEST-7-DAYS',
                license_type='SOFTWARE',
                product_name='Restaurant POS Pro',
                restaurant_id=test_restaurant.id,
                user_id=test_user.id,
                status='active',
                issued_date=datetime.utcnow(),
                expiry_date=datetime.utcnow() + timedelta(days=7),
                max_activations=1
            )
            test_licenses.append(license_7)
            
            # License expiring in 1 day
            license_1 = License(
                license_key='TEST-1-DAY',
                license_type='SOFTWARE',
                product_name='Restaurant POS Pro',
                restaurant_id=test_restaurant.id,
                user_id=test_user.id,
                status='active',
                issued_date=datetime.utcnow(),
                expiry_date=datetime.utcnow() + timedelta(days=1),
                max_activations=1
            )
            test_licenses.append(license_1)
            
            # Add licenses to database
            for license in test_licenses:
                existing = License.query.filter_by(license_key=license.license_key).first()
                if not existing:
                    db.session.add(license)
            
            db.session.commit()
            print(f"   Created {len(test_licenses)} test licenses")
            
            # 2. Test renewal statistics
            print("\n2. Testing renewal statistics...")
            renewal_service = LicenseRenewalService()
            stats = renewal_service.get_renewal_statistics()
            
            print(f"   Active licenses: {stats.get('active_licenses', 0)}")
            print(f"   Expiring in 30 days: {stats.get('expiring_30_days', 0)}")
            print(f"   Expiring in 7 days: {stats.get('expiring_7_days', 0)}")
            print(f"   Expired: {stats.get('expired', 0)}")
            
            # 3. Test sending renewal reminders
            print("\n3. Testing renewal reminder sending...")
            results = renewal_service.send_renewal_reminders()
            
            print(f"   Reminders sent: {results['sent']}")
            print(f"   Reminders skipped: {results['skipped']}")
            print(f"   Errors: {results['errors']}")
            
            # 4. Check created notifications
            print("\n4. Checking created notifications...")
            notifications = Notification.query.filter_by(
                type='license_renewal'
            ).all()
            
            print(f"   Total notifications: {len(notifications)}")
            
            for notification in notifications[:5]:  # Show first 5
                days_until = notification.title.split(' ')[0] if notification.title.split(' ')[0].isdigit() else 'N/A'
                print(f"   - {notification.title} (Urgency: {notification.urgency}, Days: {days_until})")
            
            # 5. Test scheduled task
            print("\n5. Testing scheduled task...")
            task = ScheduledTask.query.filter_by(
                task_type='license_renewal'
            ).first()
            
            if task:
                print(f"   Task found: {task.name}")
                print(f"   Frequency: {task.frequency}")
                print(f"   Next run: {task.next_run}")
                print(f"   Is active: {task.is_active}")
            else:
                print("   No scheduled task found")
            
            # 6. Test task execution logging
            print("\n6. Testing task execution logging...")
            log = TaskLog(
                task_id=task.id if task else 1,
                status='success',
                message='Test execution of license renewal reminders',
                started_at=datetime.utcnow(),
                completed_at=datetime.utcnow()
            )
            db.session.add(log)
            db.session.commit()
            
            print(f"   Created task log: {log.id}")
            
            print("\n✅ License renewal system test completed successfully!")
            
        except Exception as e:
            print(f"\nError during testing: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
        
        return True

def cleanup_test_data():
    """Clean up test data"""
    app = create_app()
    
    with app.app_context():
        print("\nCleaning up test data...")
        
        try:
            # Delete test notifications
            Notification.query.filter_by(type='license_renewal').delete()
            
            # Delete test licenses
            License.query.filter(License.license_key.like('TEST-%')).delete()
            
            # Delete test task logs
            TaskLog.query.filter(TaskLog.message.like('%Test execution%')).delete()
            
            db.session.commit()
            print("Test data cleaned up successfully")
            
        except Exception as e:
            print(f"Error cleaning up test data: {str(e)}")

if __name__ == '__main__':
    success = test_license_renewal_system()
    
    if success:
        print("\nDo you want to clean up test data? (y/n): ", end="")
        cleanup = input().lower().strip()
        if cleanup == 'y':
            cleanup_test_data()
    
    sys.exit(0 if success else 1)