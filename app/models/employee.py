from datetime import datetime, time, date
from app import db
from app.models.user import User
from sqlalchemy import Enum, Index, CheckConstraint
from decimal import Decimal
import json

class EmployeeAttendance(db.Model):
    """Employee attendance tracking model"""
    __tablename__ = 'employee_attendance'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurants.id'), nullable=False)
    date = db.Column(db.Date, nullable=False, default=date.today)
    check_in_time = db.Column(db.DateTime, nullable=True)
    check_out_time = db.Column(db.DateTime, nullable=True)
    break_start_time = db.Column(db.DateTime, nullable=True)
    break_end_time = db.Column(db.DateTime, nullable=True)
    total_hours = db.Column(db.Numeric(5, 2), nullable=True)  # Total working hours
    overtime_hours = db.Column(db.Numeric(5, 2), nullable=True)
    attendance_status = db.Column(Enum('present', 'absent', 'late', 'half_day', 'leave', name='attendance_status'), 
                                 default='present')
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref=db.backref('attendances', lazy='dynamic'))
    restaurant = db.relationship('Restaurant', backref=db.backref('employee_attendances', lazy='dynamic'))
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_attendance_user_date', 'user_id', 'date'),
        Index('idx_attendance_restaurant_date', 'restaurant_id', 'date'),
        CheckConstraint('check_out_time > check_in_time', name='check_time_validation'),
    )
    
    def calculate_total_hours(self):
        """Calculate total working hours"""
        if self.check_in_time and self.check_out_time:
            total = (self.check_out_time - self.check_in_time).total_seconds() / 3600
            
            # Subtract break time if applicable
            if self.break_start_time and self.break_end_time:
                break_duration = (self.break_end_time - self.break_start_time).total_seconds() / 3600
                total -= break_duration
            
            self.total_hours = round(total, 2)
            
            # Calculate overtime (assuming 8 hours is standard)
            if self.total_hours > 8:
                self.overtime_hours = round(self.total_hours - 8, 2)
            else:
                self.overtime_hours = 0
            
            return self.total_hours
        return 0
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'user_name': self.user.name if self.user else None,
            'restaurant_id': self.restaurant_id,
            'date': self.date.isoformat() if self.date else None,
            'check_in_time': self.check_in_time.isoformat() if self.check_in_time else None,
            'check_out_time': self.check_out_time.isoformat() if self.check_out_time else None,
            'break_start_time': self.break_start_time.isoformat() if self.break_start_time else None,
            'break_end_time': self.break_end_time.isoformat() if self.break_end_time else None,
            'total_hours': float(self.total_hours) if self.total_hours else None,
            'overtime_hours': float(self.overtime_hours) if self.overtime_hours else None,
            'attendance_status': self.attendance_status,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class ShiftSchedule(db.Model):
    """Shift scheduling model"""
    __tablename__ = 'shift_schedules'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurants.id'), nullable=False)
    shift_name = db.Column(db.String(100), nullable=False)
    shift_date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    break_duration = db.Column(db.Integer, default=30)  # Break duration in minutes
    shift_type = db.Column(Enum('regular', 'overtime', 'holiday', 'weekend', name='shift_type'), 
                          default='regular')
    is_recurring = db.Column(db.Boolean, default=False)
    recurring_pattern = db.Column(db.JSON)  # Store recurring pattern as JSON
    status = db.Column(Enum('scheduled', 'confirmed', 'completed', 'cancelled', 'no_show', name='shift_status'), 
                       default='scheduled')
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref=db.backref('shift_schedules', lazy='dynamic'))
    restaurant = db.relationship('Restaurant', backref=db.backref('shift_schedules', lazy='dynamic'))
    
    # Indexes
    __table_args__ = (
        Index('idx_shift_user_date', 'user_id', 'shift_date'),
        Index('idx_shift_restaurant_date', 'restaurant_id', 'shift_date'),
        CheckConstraint('end_time > start_time', name='shift_time_validation'),
    )
    
    def get_duration_hours(self):
        """Get shift duration in hours"""
        if self.start_time and self.end_time:
            start_minutes = self.start_time.hour * 60 + self.start_time.minute
            end_minutes = self.end_time.hour * 60 + self.end_time.minute
            
            # Handle overnight shifts
            if end_minutes < start_minutes:
                end_minutes += 24 * 60
            
            duration = (end_minutes - start_minutes) / 60
            # Subtract break time
            duration -= self.break_duration / 60
            return round(duration, 2)
        return 0
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'user_name': self.user.name if self.user else None,
            'restaurant_id': self.restaurant_id,
            'shift_name': self.shift_name,
            'shift_date': self.shift_date.isoformat() if self.shift_date else None,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'break_duration': self.break_duration,
            'shift_type': self.shift_type,
            'is_recurring': self.is_recurring,
            'recurring_pattern': self.recurring_pattern,
            'status': self.status,
            'notes': self.notes,
            'duration_hours': self.get_duration_hours(),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class LeaveRequest(db.Model):
    """Leave request management model"""
    __tablename__ = 'leave_requests'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurants.id'), nullable=False)
    leave_type = db.Column(Enum('sick', 'casual', 'annual', 'maternity', 'paternity', 'unpaid', name='leave_type'), 
                          nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    total_days = db.Column(db.Numeric(3, 1), nullable=False)
    reason = db.Column(db.Text, nullable=True)
    status = db.Column(Enum('pending', 'approved', 'rejected', 'cancelled', name='leave_status'), 
                      default='pending')
    approved_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    approved_at = db.Column(db.DateTime, nullable=True)
    rejection_reason = db.Column(db.Text, nullable=True)
    attachments = db.Column(db.JSON)  # Store file paths or URLs
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', foreign_keys=[user_id], backref=db.backref('leave_requests', lazy='dynamic'))
    approver = db.relationship('User', foreign_keys=[approved_by])
    restaurant = db.relationship('Restaurant', backref=db.backref('leave_requests', lazy='dynamic'))
    
    # Indexes
    __table_args__ = (
        Index('idx_leave_user_date', 'user_id', 'start_date'),
        Index('idx_leave_restaurant_date', 'restaurant_id', 'start_date'),
        CheckConstraint('end_date >= start_date', name='leave_date_validation'),
    )
    
    def calculate_total_days(self):
        """Calculate total leave days"""
        if self.start_date and self.end_date:
            delta = self.end_date - self.start_date
            self.total_days = delta.days + 1
            return self.total_days
        return 0
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'user_name': self.user.name if self.user else None,
            'restaurant_id': self.restaurant_id,
            'leave_type': self.leave_type,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'total_days': float(self.total_days) if self.total_days else None,
            'reason': self.reason,
            'status': self.status,
            'approved_by': self.approved_by,
            'approved_by_name': self.approver.name if self.approver else None,
            'approved_at': self.approved_at.isoformat() if self.approved_at else None,
            'rejection_reason': self.rejection_reason,
            'attachments': self.attachments,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class PayrollRecord(db.Model):
    """Payroll management model"""
    __tablename__ = 'payroll_records'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurants.id'), nullable=False)
    pay_period_start = db.Column(db.Date, nullable=False)
    pay_period_end = db.Column(db.Date, nullable=False)
    basic_salary = db.Column(db.Numeric(10, 2), nullable=False)
    overtime_hours = db.Column(db.Numeric(5, 2), default=0)
    overtime_rate = db.Column(db.Numeric(5, 2), default=1.5)  # Overtime multiplier
    overtime_pay = db.Column(db.Numeric(10, 2), default=0)
    incentives = db.Column(db.Numeric(10, 2), default=0)
    bonuses = db.Column(db.Numeric(10, 2), default=0)
    deductions = db.Column(db.Numeric(10, 2), default=0)
    tax_deduction = db.Column(db.Numeric(10, 2), default=0)
    other_deductions = db.Column(db.Numeric(10, 2), default=0)
    gross_pay = db.Column(db.Numeric(10, 2), nullable=False)
    net_pay = db.Column(db.Numeric(10, 2), nullable=False)
    payment_status = db.Column(Enum('pending', 'processed', 'paid', 'failed', name='payment_status'), 
                              default='pending')
    payment_date = db.Column(db.DateTime, nullable=True)
    payment_method = db.Column(db.String(50), nullable=True)
    payslip_generated = db.Column(db.Boolean, default=False)
    payslip_path = db.Column(db.String(255), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref=db.backref('payroll_records', lazy='dynamic'))
    restaurant = db.relationship('Restaurant', backref=db.backref('payroll_records', lazy='dynamic'))
    
    # Indexes
    __table_args__ = (
        Index('idx_payroll_user_period', 'user_id', 'pay_period_start'),
        Index('idx_payroll_restaurant_period', 'restaurant_id', 'pay_period_start'),
        CheckConstraint('pay_period_end >= pay_period_start', name='payroll_period_validation'),
    )
    
    def calculate_gross_pay(self):
        """Calculate gross pay"""
        self.gross_pay = self.basic_salary + self.overtime_pay + self.incentives + self.bonuses
        return self.gross_pay
    
    def calculate_net_pay(self):
        """Calculate net pay after deductions"""
        total_deductions = self.deductions + self.tax_deduction + self.other_deductions
        self.net_pay = self.gross_pay - total_deductions
        return self.net_pay
    
    def calculate_overtime_pay(self):
        """Calculate overtime pay"""
        if self.overtime_hours and self.basic_salary:
            # Calculate hourly rate from basic salary (assuming 160 hours/month)
            hourly_rate = float(self.basic_salary) / 160
            self.overtime_pay = round(float(self.overtime_hours) * hourly_rate * float(self.overtime_rate), 2)
            return self.overtime_pay
        return 0
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'user_name': self.user.name if self.user else None,
            'restaurant_id': self.restaurant_id,
            'pay_period_start': self.pay_period_start.isoformat() if self.pay_period_start else None,
            'pay_period_end': self.pay_period_end.isoformat() if self.pay_period_end else None,
            'basic_salary': float(self.basic_salary) if self.basic_salary else None,
            'overtime_hours': float(self.overtime_hours) if self.overtime_hours else None,
            'overtime_rate': float(self.overtime_rate) if self.overtime_rate else None,
            'overtime_pay': float(self.overtime_pay) if self.overtime_pay else None,
            'incentives': float(self.incentives) if self.incentives else None,
            'bonuses': float(self.bonuses) if self.bonuses else None,
            'deductions': float(self.deductions) if self.deductions else None,
            'tax_deduction': float(self.tax_deduction) if self.tax_deduction else None,
            'other_deductions': float(self.other_deductions) if self.other_deductions else None,
            'gross_pay': float(self.gross_pay) if self.gross_pay else None,
            'net_pay': float(self.net_pay) if self.net_pay else None,
            'payment_status': self.payment_status,
            'payment_date': self.payment_date.isoformat() if self.payment_date else None,
            'payment_method': self.payment_method,
            'payslip_generated': self.payslip_generated,
            'payslip_path': self.payslip_path,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class EmployeePerformance(db.Model):
    """Employee performance tracking model"""
    __tablename__ = 'employee_performance'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurants.id'), nullable=False)
    evaluation_period = db.Column(db.String(50), nullable=False)  # e.g., "2024-01", "Q1-2024"
    customer_ratings = db.Column(db.Numeric(3, 2), default=0)  # Average customer rating (1-5)
    sales_performance = db.Column(db.Numeric(10, 2), default=0)  # Total sales amount
    order_accuracy = db.Column(db.Numeric(5, 2), default=0)  # Order accuracy percentage
    productivity_score = db.Column(db.Numeric(5, 2), default=0)  # Productivity score
    teamwork_score = db.Column(db.Numeric(5, 2), default=0)  # Teamwork evaluation
    punctuality_score = db.Column(db.Numeric(5, 2), default=0)  # Punctuality evaluation
    overall_score = db.Column(db.Numeric(5, 2), default=0)  # Overall performance score
    goals_achieved = db.Column(db.JSON)  # Store goals and achievements
    areas_for_improvement = db.Column(db.JSON)  # Store improvement areas
    feedback = db.Column(db.Text, nullable=True)
    evaluator_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    evaluated_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', foreign_keys=[user_id], backref=db.backref('performance_records', lazy='dynamic'))
    evaluator = db.relationship('User', foreign_keys=[evaluator_id])
    restaurant = db.relationship('Restaurant', backref=db.backref('employee_performances', lazy='dynamic'))
    
    # Indexes
    __table_args__ = (
        Index('idx_performance_user_period', 'user_id', 'evaluation_period'),
        Index('idx_performance_restaurant_period', 'restaurant_id', 'evaluation_period'),
    )
    
    def calculate_overall_score(self):
        """Calculate overall performance score"""
        weights = {
            'customer_ratings': 0.3,
            'order_accuracy': 0.2,
            'productivity_score': 0.2,
            'teamwork_score': 0.15,
            'punctuality_score': 0.15
        }
        
        total_score = 0
        total_weight = 0
        
        for metric, weight in weights.items():
            value = getattr(self, metric)
            if value and value > 0:
                # Normalize to 5-point scale if needed
                if metric == 'sales_performance':
                    # Normalize sales performance (this would need business logic)
                    normalized_value = min(float(value) / 10000 * 5, 5)  # Example normalization
                else:
                    normalized_value = float(value)
                
                total_score += normalized_value * weight
                total_weight += weight
        
        if total_weight > 0:
            self.overall_score = round(total_score / total_weight, 2)
        else:
            self.overall_score = 0
        
        return self.overall_score
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'user_name': self.user.name if self.user else None,
            'restaurant_id': self.restaurant_id,
            'evaluation_period': self.evaluation_period,
            'customer_ratings': float(self.customer_ratings) if self.customer_ratings else None,
            'sales_performance': float(self.sales_performance) if self.sales_performance else None,
            'order_accuracy': float(self.order_accuracy) if self.order_accuracy else None,
            'productivity_score': float(self.productivity_score) if self.productivity_score else None,
            'teamwork_score': float(self.teamwork_score) if self.teamwork_score else None,
            'punctuality_score': float(self.punctuality_score) if self.punctuality_score else None,
            'overall_score': float(self.overall_score) if self.overall_score else None,
            'goals_achieved': self.goals_achieved,
            'areas_for_improvement': self.areas_for_improvement,
            'feedback': self.feedback,
            'evaluator_id': self.evaluator_id,
            'evaluator_name': self.evaluator.name if self.evaluator else None,
            'evaluated_at': self.evaluated_at.isoformat() if self.evaluated_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class EmployeeProfile(db.Model):
    """Extended employee profile information"""
    __tablename__ = 'employee_profiles'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurants.id'), nullable=False)
    employee_id = db.Column(db.String(20), unique=True, nullable=False)  # Unique employee ID
    department = db.Column(db.String(100), nullable=True)
    designation = db.Column(db.String(100), nullable=True)
    employment_type = db.Column(Enum('full_time', 'part_time', 'contract', 'intern', name='employment_type'), 
                                nullable=False)
    date_of_joining = db.Column(db.Date, nullable=False)
    date_of_leaving = db.Column(db.Date, nullable=True)
    basic_salary = db.Column(db.Numeric(10, 2), nullable=False)
    bank_account_number = db.Column(db.String(50), nullable=True)
    bank_name = db.Column(db.String(100), nullable=True)
    ifsc_code = db.Column(db.String(20), nullable=True)
    pan_number = db.Column(db.String(20), nullable=True)
    aadhar_number = db.Column(db.String(20), nullable=True)
    emergency_contact_name = db.Column(db.String(100), nullable=True)
    emergency_contact_number = db.Column(db.String(20), nullable=True)
    address = db.Column(db.Text, nullable=True)
    qualifications = db.Column(db.JSON)  # Store educational qualifications
    experience = db.Column(db.JSON)  # Store work experience
    skills = db.Column(db.JSON)  # Store skills and competencies
    documents = db.Column(db.JSON)  # Store document paths
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref=db.backref('employee_profile', uselist=False))
    restaurant = db.relationship('Restaurant', backref=db.backref('employee_profiles', lazy='dynamic'))
    
    # Indexes
    __table_args__ = (
        Index('idx_employee_restaurant', 'restaurant_id'),
        Index('idx_employee_department', 'department'),
        CheckConstraint('date_of_leaving > date_of_joining', name='employment_dates_validation'),
    )
    
    def generate_employee_id(self):
        """Generate unique employee ID"""
        if not self.employee_id:
            # Get restaurant prefix and generate sequential ID
            restaurant_prefix = f"R{self.restaurant_id:03d}"
            last_employee = EmployeeProfile.query.filter(
                EmployeeProfile.employee_id.startswith(restaurant_prefix)
            ).order_by(EmployeeProfile.id.desc()).first()
            
            if last_employee:
                last_number = int(last_employee.employee_id.split('-')[1])
                new_number = last_number + 1
            else:
                new_number = 1
            
            self.employee_id = f"{restaurant_prefix}-{new_number:04d}"
        
        return self.employee_id
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'user_name': self.user.name if self.user else None,
            'user_email': self.user.email if self.user else None,
            'restaurant_id': self.restaurant_id,
            'employee_id': self.employee_id,
            'department': self.department,
            'designation': self.designation,
            'employment_type': self.employment_type,
            'date_of_joining': self.date_of_joining.isoformat() if self.date_of_joining else None,
            'date_of_leaving': self.date_of_leaving.isoformat() if self.date_of_leaving else None,
            'basic_salary': float(self.basic_salary) if self.basic_salary else None,
            'bank_account_number': self.bank_account_number,
            'bank_name': self.bank_name,
            'ifsc_code': self.ifsc_code,
            'pan_number': self.pan_number,
            'aadhar_number': self.aadhar_number,
            'emergency_contact_name': self.emergency_contact_name,
            'emergency_contact_number': self.emergency_contact_number,
            'address': self.address,
            'qualifications': self.qualifications,
            'experience': self.experience,
            'skills': self.skills,
            'documents': self.documents,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }