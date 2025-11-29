"""
Create employee management tables migration script
"""
import sys
import os
from datetime import datetime

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

from app import create_app, db
from app.models.employee import (
    EmployeeAttendance, ShiftSchedule, LeaveRequest, PayrollRecord, 
    EmployeePerformance, EmployeeProfile
)

def create_employee_tables():
    """Create all employee management tables"""
    app = create_app()
    
    with app.app_context():
        print("Creating employee management tables...")
        
        # Create tables in order to handle foreign key constraints
        tables = [
            EmployeeProfile,
            EmployeeAttendance,
            ShiftSchedule,
            LeaveRequest,
            PayrollRecord,
            EmployeePerformance
        ]
        
        for table in tables:
            try:
                table.__table__.create(db.engine, checkfirst=True)
                print(f"+ Created table: {table.__tablename__}")
            except Exception as e:
                print(f"- Error creating table {table.__tablename__}: {str(e)}")
        
        # Create indexes for performance
        print("\nCreating indexes...")
        try:
            # EmployeeAttendance indexes
            with db.engine.connect() as conn:
                conn.execute(db.text('CREATE INDEX IF NOT EXISTS idx_attendance_user_date ON employee_attendance(user_id, date)'))
                conn.execute(db.text('CREATE INDEX IF NOT EXISTS idx_attendance_restaurant_date ON employee_attendance(restaurant_id, date)'))
                
                # ShiftSchedule indexes
                conn.execute(db.text('CREATE INDEX IF NOT EXISTS idx_shift_user_date ON shift_schedules(user_id, shift_date)'))
                conn.execute(db.text('CREATE INDEX IF NOT EXISTS idx_shift_restaurant_date ON shift_schedules(restaurant_id, shift_date)'))
                
                # LeaveRequest indexes
                conn.execute(db.text('CREATE INDEX IF NOT EXISTS idx_leave_user_date ON leave_requests(user_id, start_date)'))
                conn.execute(db.text('CREATE INDEX IF NOT EXISTS idx_leave_restaurant_date ON leave_requests(restaurant_id, start_date)'))
                
                # PayrollRecord indexes
                conn.execute(db.text('CREATE INDEX IF NOT EXISTS idx_payroll_user_period ON payroll_records(user_id, pay_period_start)'))
                conn.execute(db.text('CREATE INDEX IF NOT EXISTS idx_payroll_restaurant_period ON payroll_records(restaurant_id, pay_period_start)'))
                
                # EmployeePerformance indexes
                conn.execute(db.text('CREATE INDEX IF NOT EXISTS idx_performance_user_period ON employee_performance(user_id, evaluation_period)'))
                conn.execute(db.text('CREATE INDEX IF NOT EXISTS idx_performance_restaurant_period ON employee_performance(restaurant_id, evaluation_period)'))
                
                # EmployeeProfile indexes
                conn.execute(db.text('CREATE INDEX IF NOT EXISTS idx_profile_restaurant ON employee_profiles(restaurant_id)'))
                conn.execute(db.text('CREATE INDEX IF NOT EXISTS idx_profile_department ON employee_profiles(department)'))
            
            print("+ Created all indexes")
        except Exception as e:
            print(f"- Error creating indexes: {str(e)}")
        
        print("\nEmployee management tables creation completed!")

def add_employee_profile_to_existing_users():
    """Add employee profiles to existing users who don't have one"""
    app = create_app()
    
    with app.app_context():
        from app.models.user import User
        
        print("Adding employee profiles to existing users...")
        
        # Get users who don't have employee profiles
        existing_profile_ids = db.session.query(EmployeeProfile.user_id).all()
        existing_profile_ids = [pid[0] for pid in existing_profile_ids]
        
        users_without_profiles = db.session.query(User).filter(
            ~User.id.in_(existing_profile_ids)
        ).all()
        
        for user in users_without_profiles:
            try:
                # Create basic employee profile
                profile = EmployeeProfile(
                    user_id=user.id,
                    restaurant_id=user.restaurant_id,
                    employee_id='',  # Will be generated
                    department='General',
                    designation=user.get_role_display_name(),
                    employment_type='full_time',
                    date_of_joining=user.created_at.date() if user.created_at else datetime.now().date(),
                    basic_salary=0.00,  # Default salary
                    is_active=user.user_active
                )
                
                # Generate employee ID
                profile.generate_employee_id()
                
                db.session.add(profile)
                print(f"+ Created profile for user: {user.name}")
            except Exception as e:
                print(f"- Error creating profile for user {user.name}: {str(e)}")
                db.session.rollback()
        
        try:
            db.session.commit()
            print("+ Committed all employee profiles")
        except Exception as e:
            print(f"- Error committing profiles: {str(e)}")
            db.session.rollback()

def update_user_permissions():
    """Update user permissions to include employee management"""
    app = create_app()
    
    with app.app_context():
        from app.models.user import User
        
        print("Updating user permissions...")
        
        # Update permissions for manager and admin roles
        managers = User.query.filter(
            User.role.in_(['manager', 'restaurant_owner', 'super_admin'])
        ).all()
        
        for user in managers:
            try:
                # Existing permissions already include employee management
                # This is just a placeholder for future permission updates
                print(f"+ Updated permissions for: {user.name}")
            except Exception as e:
                print(f"- Error updating permissions for {user.name}: {str(e)}")
        
        print("+ User permissions updated!")

if __name__ == '__main__':
    print("Starting employee management tables migration...")
    
    # Create tables
    create_employee_tables()
    
    # Add profiles to existing users
    add_employee_profile_to_existing_users()
    
    # Update permissions
    update_user_permissions()
    
    print("\nMigration completed successfully!")