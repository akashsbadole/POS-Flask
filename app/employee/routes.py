from datetime import datetime, date, time, timedelta
from flask import render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
from sqlalchemy import and_, or_, func, desc, asc
from app import db
from app.employee import bp
from app.models.user import User
from app.models.employee import (
    EmployeeAttendance, ShiftSchedule, LeaveRequest, PayrollRecord, 
    EmployeePerformance, EmployeeProfile
)
from app.models.restaurant import Restaurant
from decimal import Decimal
import json
import logging

# Configure logging
logger = logging.getLogger(__name__)

# Helper function to check permissions
def require_manager_permission():
    """Check if user has manager or higher permissions"""
    if not current_user.is_authenticated:
        return False
    return current_user.can_access_manager_features()

def require_admin_permission():
    """Check if user has admin or higher permissions"""
    if not current_user.is_authenticated:
        return False
    return current_user.can_access_admin_features()

# Dashboard
@bp.route('/')
@login_required
def dashboard():
    """Employee management dashboard"""
    if not require_manager_permission():
        flash('You do not have permission to access employee management', 'error')
        return redirect(url_for('main.dashboard'))
    
    # Get restaurant scope
    restaurant_ids = current_user.get_restaurant_scope()
    
    # Get dashboard statistics
    today = date.today()
    current_month_start = today.replace(day=1)
    
    # Employee count
    total_employees = User.query.filter(
        User.restaurant_id.in_(restaurant_ids),
        User.user_active == True
    ).count()
    
    # Today's attendance
    present_today = EmployeeAttendance.query.filter(
        EmployeeAttendance.restaurant_id.in_(restaurant_ids),
        EmployeeAttendance.date == today,
        EmployeeAttendance.attendance_status.in_(['present', 'late'])
    ).count()
    
    # Pending leave requests
    pending_leaves = LeaveRequest.query.filter(
        LeaveRequest.restaurant_id.in_(restaurant_ids),
        LeaveRequest.status == 'pending'
    ).count()
    
    # Current month payroll
    payroll_processed = PayrollRecord.query.filter(
        PayrollRecord.restaurant_id.in_(restaurant_ids),
        PayrollRecord.pay_period_start >= current_month_start,
        PayrollRecord.payment_status == 'paid'
    ).count()
    
    # Recent activities
    recent_attendances = EmployeeAttendance.query.filter(
        EmployeeAttendance.restaurant_id.in_(restaurant_ids)
    ).order_by(desc(EmployeeAttendance.created_at)).limit(5).all()
    
    recent_leave_requests = LeaveRequest.query.filter(
        LeaveRequest.restaurant_id.in_(restaurant_ids)
    ).order_by(desc(LeaveRequest.created_at)).limit(5).all()
    
    return render_template('employee/dashboard.html',
                         total_employees=total_employees,
                         present_today=present_today,
                         pending_leaves=pending_leaves,
                         payroll_processed=payroll_processed,
                         recent_attendances=recent_attendances,
                         recent_leave_requests=recent_leave_requests)

# Employee Profile Management
@bp.route('/profiles')
@login_required
def profiles():
    """List all employee profiles"""
    if not require_manager_permission():
        flash('You do not have permission to access employee profiles', 'error')
        return redirect(url_for('main.dashboard'))
    
    restaurant_ids = current_user.get_restaurant_scope()
    
    # Get filters from request
    department = request.args.get('department')
    employment_type = request.args.get('employment_type')
    status = request.args.get('status')
    
    # Build query
    query = EmployeeProfile.query.filter(
        EmployeeProfile.restaurant_id.in_(restaurant_ids)
    ).join(User, EmployeeProfile.user_id == User.id)
    
    # Apply filters
    if department:
        query = query.filter(EmployeeProfile.department == department)
    if employment_type:
        query = query.filter(EmployeeProfile.employment_type == employment_type)
    if status:
        query = query.filter(EmployeeProfile.is_active == (status == 'active'))
    
    profiles = query.order_by(EmployeeProfile.created_at.desc()).all()
    
    return render_template('employee/profiles.html', profiles=profiles)

@bp.route('/profiles/create', methods=['GET', 'POST'])
@login_required
def create_profile():
    """Create new employee profile"""
    if not require_admin_permission():
        flash('You do not have permission to create employee profiles', 'error')
        return redirect(url_for('employee.profiles'))
    
    if request.method == 'POST':
        try:
            # Get user data
            user_data = {
                'name': request.form.get('name'),
                'email': request.form.get('email'),
                'phone': request.form.get('phone'),
                'role': request.form.get('role'),
                'restaurant_id': int(request.form.get('restaurant_id') or 0),
                'user_active': True
            }
            
            # Check if user already exists
            existing_user = User.query.filter_by(email=user_data['email']).first()
            if existing_user:
                flash('User with this email already exists', 'error')
                return render_template('employee/create_profile.html')
            
            # Create user
            user = User(**user_data)
            user.set_password('temp123')  # Default password
            db.session.add(user)
            db.session.flush()  # Get user ID
            
            # Create employee profile
            profile_data = {
                'user_id': user.id,
                'restaurant_id': user.restaurant_id,
                'department': request.form.get('department'),
                'designation': request.form.get('designation'),
                'employment_type': request.form.get('employment_type'),
                'date_of_joining': datetime.strptime(request.form.get('date_of_joining') or '', '%Y-%m-%d').date(),
                'basic_salary': Decimal(request.form.get('basic_salary') or '0'),
                'bank_account_number': request.form.get('bank_account_number'),
                'bank_name': request.form.get('bank_name'),
                'ifsc_code': request.form.get('ifsc_code'),
                'emergency_contact_name': request.form.get('emergency_contact_name'),
                'emergency_contact_number': request.form.get('emergency_contact_number'),
                'address': request.form.get('address'),
                'is_active': True
            }
            
            profile = EmployeeProfile(**profile_data)
            profile.generate_employee_id()
            db.session.add(profile)
            
            db.session.commit()
            
            flash(f'Employee profile created successfully. Employee ID: {profile.employee_id}', 'success')
            return redirect(url_for('employee.profiles'))
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating employee profile: {str(e)}")
            flash('Error creating employee profile', 'error')
    
    # Get available restaurants
    restaurant_ids = current_user.get_restaurant_scope()
    restaurants = Restaurant.query.filter(Restaurant.id.in_(restaurant_ids)).all()
    
    return render_template('employee/create_profile.html', restaurants=restaurants)

@bp.route('/profiles/<int:profile_id>')
@login_required
def view_profile(profile_id):
    """View employee profile details"""
    if not require_manager_permission():
        flash('You do not have permission to view employee profiles', 'error')
        return redirect(url_for('main.dashboard'))
    
    restaurant_ids = current_user.get_restaurant_scope()
    profile = EmployeeProfile.query.filter(
        EmployeeProfile.id == profile_id,
        EmployeeProfile.restaurant_id.in_(restaurant_ids)
    ).first_or_404()
    
    # Get related data
    attendances = EmployeeAttendance.query.filter_by(user_id=profile.user_id).order_by(desc(EmployeeAttendance.date)).limit(10).all()
    leave_requests = LeaveRequest.query.filter_by(user_id=profile.user_id).order_by(desc(LeaveRequest.created_at)).limit(5).all()
    payroll_records = PayrollRecord.query.filter_by(user_id=profile.user_id).order_by(desc(PayrollRecord.created_at)).limit(5).all()
    performance_records = EmployeePerformance.query.filter_by(user_id=profile.user_id).order_by(desc(EmployeePerformance.created_at)).limit(3).all()
    
    return render_template('employee/view_profile.html', 
                         profile=profile,
                         attendances=attendances,
                         leave_requests=leave_requests,
                         payroll_records=payroll_records,
                         performance_records=performance_records)

# Attendance Management
@bp.route('/attendance')
@login_required
def attendance():
    """Attendance management page"""
    if not require_manager_permission():
        flash('You do not have permission to access attendance management', 'error')
        return redirect(url_for('main.dashboard'))
    
    restaurant_ids = current_user.get_restaurant_scope()
    
    # Get filters
    date_filter = request.args.get('date') or date.today().isoformat()
    status_filter = request.args.get('status')
    
    # Build query
    query = EmployeeAttendance.query.filter(
        EmployeeAttendance.restaurant_id.in_(restaurant_ids),
        EmployeeAttendance.date == datetime.strptime(date_filter, '%Y-%m-%d').date()
    ).join(User, EmployeeAttendance.user_id == User.id)
    
    if status_filter:
        query = query.filter(EmployeeAttendance.attendance_status == status_filter)
    
    attendances = query.order_by(EmployeeAttendance.check_in_time.desc()).all()
    
    return render_template('employee/attendance.html', 
                         attendances=attendances,
                         selected_date=date_filter,
                         status_filter=status_filter)

@bp.route('/attendance/check-in', methods=['POST'])
@login_required
def check_in():
    """Check in employee"""
    try:
        user_id = request.form.get('user_id')
        restaurant_id = request.form.get('restaurant_id')
        
        # Validate permissions
        if str(current_user.id) != user_id and not require_manager_permission():
            return jsonify({'success': False, 'message': 'Permission denied'}), 403
        
        # Check if already checked in today
        today = date.today()
        existing_attendance = EmployeeAttendance.query.filter(
            EmployeeAttendance.user_id == user_id,
            EmployeeAttendance.date == today
        ).first()
        
        if existing_attendance and existing_attendance.check_in_time:
            return jsonify({'success': False, 'message': 'Already checked in today'}), 400
        
        # Create or update attendance record
        if not existing_attendance:
            attendance = EmployeeAttendance(
                user_id=user_id,
                restaurant_id=restaurant_id,
                date=today,
                check_in_time=datetime.utcnow(),
                attendance_status='present'
            )
            db.session.add(attendance)
        else:
            existing_attendance.check_in_time = datetime.utcnow()
            existing_attendance.attendance_status = 'present'
            attendance = existing_attendance
        
        db.session.commit()
        
        # Emit real-time update
        from flask_socketio import emit
        from app import socketio
        socketio.emit('attendance_updated', {
            'user_id': user_id,
            'action': 'check_in',
            'time': datetime.utcnow().isoformat()
        }, to=f"restaurant_{restaurant_id}")
        
        return jsonify({'success': True, 'message': 'Checked in successfully'})
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error during check-in: {str(e)}")
        return jsonify({'success': False, 'message': 'Check-in failed'}), 500

@bp.route('/attendance/check-out', methods=['POST'])
@login_required
def check_out():
    """Check out employee"""
    try:
        user_id = request.form.get('user_id')
        restaurant_id = request.form.get('restaurant_id')
        
        # Validate permissions
        if str(current_user.id) != user_id and not require_manager_permission():
            return jsonify({'success': False, 'message': 'Permission denied'}), 403
        
        # Find today's attendance record
        today = date.today()
        attendance = EmployeeAttendance.query.filter(
            EmployeeAttendance.user_id == user_id,
            EmployeeAttendance.date == today,
            EmployeeAttendance.check_in_time.isnot(None),
            EmployeeAttendance.check_out_time.is_(None)
        ).first()
        
        if not attendance:
            return jsonify({'success': False, 'message': 'No active check-in found'}), 400
        
        # Update check-out time
        attendance.check_out_time = datetime.utcnow()
        attendance.calculate_total_hours()
        
        db.session.commit()
        
        # Emit real-time update
        from flask_socketio import emit
        from app import socketio
        socketio.emit('attendance_updated', {
            'user_id': user_id,
            'action': 'check_out',
            'time': datetime.utcnow().isoformat(),
            'total_hours': float(attendance.total_hours) if attendance.total_hours else 0
        }, to=f"restaurant_{restaurant_id}")
        
        return jsonify({'success': True, 'message': 'Checked out successfully'})
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error during check-out: {str(e)}")
        return jsonify({'success': False, 'message': 'Check-out failed'}), 500

# Shift Management
@bp.route('/shifts')
@login_required
def shifts():
    """Shift scheduling page"""
    if not require_manager_permission():
        flash('You do not have permission to access shift management', 'error')
        return redirect(url_for('main.dashboard'))
    
    restaurant_ids = current_user.get_restaurant_scope()
    
    # Get filters
    week_start = request.args.get('week_start')
    if week_start:
        week_start = datetime.strptime(week_start, '%Y-%m-%d').date()
    else:
        # Default to current week
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
    
    week_end = week_start + timedelta(days=6)
    
    # Get shifts for the week
    shifts = ShiftSchedule.query.filter(
        ShiftSchedule.restaurant_id.in_(restaurant_ids),
        ShiftSchedule.shift_date >= week_start,
        ShiftSchedule.shift_date <= week_end
    ).join(User, ShiftSchedule.user_id == User.id).order_by(
        ShiftSchedule.shift_date, ShiftSchedule.start_time
    ).all()
    
    # Get all employees for scheduling
    employees = User.query.filter(
        User.restaurant_id.in_(restaurant_ids),
        User.user_active == True
    ).all()
    
    return render_template('employee/shifts.html', 
                         shifts=shifts,
                         employees=employees,
                         week_start=week_start,
                         week_end=week_end)

@bp.route('/shifts/create', methods=['POST'])
@login_required
def create_shift():
    """Create new shift"""
    if not require_manager_permission():
        return jsonify({'success': False, 'message': 'Permission denied'}), 403
    
    try:
        shift_data = {
            'user_id': request.form.get('user_id'),
            'restaurant_id': request.form.get('restaurant_id'),
            'shift_name': request.form.get('shift_name'),
            'shift_date': datetime.strptime(request.form.get('shift_date') or '', '%Y-%m-%d').date(),
            'start_time': datetime.strptime(request.form.get('start_time') or '', '%H:%M').time(),
            'end_time': datetime.strptime(request.form.get('end_time') or '', '%H:%M').time(),
            'break_duration': int(request.form.get('break_duration') or 30),
            'shift_type': request.form.get('shift_type', 'regular'),
            'notes': request.form.get('notes')
        }
        
        # Check for conflicts
        conflict = ShiftSchedule.query.filter(
            ShiftSchedule.user_id == shift_data['user_id'],
            ShiftSchedule.shift_date == shift_data['shift_date'],
            ShiftSchedule.status.in_(['scheduled', 'confirmed']),
            or_(
                and_(ShiftSchedule.start_time <= shift_data['start_time'], 
                     ShiftSchedule.end_time > shift_data['start_time']),
                and_(ShiftSchedule.start_time < shift_data['end_time'], 
                     ShiftSchedule.end_time >= shift_data['end_time'])
            )
        ).first()
        
        if conflict:
            return jsonify({'success': False, 'message': 'Shift conflicts with existing schedule'}), 400
        
        shift = ShiftSchedule(**shift_data)
        db.session.add(shift)
        db.session.commit()
        
        # Emit real-time update
        from flask_socketio import emit
        from app import socketio
        socketio.emit('shift_updated', {
            'action': 'created',
            'shift': shift.to_dict()
        }, to=f"restaurant_{shift_data['restaurant_id']}")
        
        return jsonify({'success': True, 'message': 'Shift created successfully'})
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating shift: {str(e)}")
        return jsonify({'success': False, 'message': 'Failed to create shift'}), 500

# Leave Management
@bp.route('/leaves')
@login_required
def leaves():
    """Leave management page"""
    if not require_manager_permission():
        flash('You do not have permission to access leave management', 'error')
        return redirect(url_for('main.dashboard'))
    
    restaurant_ids = current_user.get_restaurant_scope()
    
    # Get filters
    status_filter = request.args.get('status')
    leave_type_filter = request.args.get('leave_type')
    
    # Build query
    query = LeaveRequest.query.filter(
        LeaveRequest.restaurant_id.in_(restaurant_ids)
    ).join(User, LeaveRequest.user_id == User.id)
    
    if status_filter:
        query = query.filter(LeaveRequest.status == status_filter)
    if leave_type_filter:
        query = query.filter(LeaveRequest.leave_type == leave_type_filter)
    
    leave_requests = query.order_by(desc(LeaveRequest.created_at)).all()
    
    return render_template('employee/leaves.html', 
                         leave_requests=leave_requests,
                         status_filter=status_filter,
                         leave_type_filter=leave_type_filter)

@bp.route('/leaves/request', methods=['GET', 'POST'])
@login_required
def request_leave():
    """Request leave"""
    if request.method == 'POST':
        try:
            leave_data = {
                'user_id': current_user.id,
                'restaurant_id': current_user.restaurant_id,
                'leave_type': request.form.get('leave_type'),
                'start_date': datetime.strptime(request.form.get('start_date') or '', '%Y-%m-%d').date(),
                'end_date': datetime.strptime(request.form.get('end_date') or '', '%Y-%m-%d').date(),
                'reason': request.form.get('reason')
            }
            
            leave = LeaveRequest(**leave_data)
            leave.calculate_total_days()
            db.session.add(leave)
            db.session.commit()
            
            flash('Leave request submitted successfully', 'success')
            return redirect(url_for('employee.leaves'))
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error requesting leave: {str(e)}")
            flash('Error submitting leave request', 'error')
    
    return render_template('employee/request_leave.html')

@bp.route('/leaves/<int:leave_id>/approve', methods=['POST'])
@login_required
def approve_leave(leave_id):
    """Approve leave request"""
    if not require_manager_permission():
        return jsonify({'success': False, 'message': 'Permission denied'}), 403
    
    try:
        leave = LeaveRequest.query.get_or_404(leave_id)
        
        # Check restaurant permission
        restaurant_ids = current_user.get_restaurant_scope()
        if leave.restaurant_id not in restaurant_ids:
            return jsonify({'success': False, 'message': 'Permission denied'}), 403
        
        leave.status = 'approved'
        leave.approved_by = current_user.id
        leave.approved_at = datetime.utcnow()
        
        db.session.commit()
        
        # Emit real-time update
        from flask_socketio import emit
        from app import socketio
        socketio.emit('leave_updated', {
            'action': 'approved',
            'leave_id': leave_id,
            'approved_by': current_user.name
        }, to=f"restaurant_{leave.restaurant_id}")
        
        return jsonify({'success': True, 'message': 'Leave approved successfully'})
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error approving leave: {str(e)}")
        return jsonify({'success': False, 'message': 'Failed to approve leave'}), 500

# Payroll Management
@bp.route('/payroll')
@login_required
def payroll():
    """Payroll management page"""
    if not require_admin_permission():
        flash('You do not have permission to access payroll management', 'error')
        return redirect(url_for('main.dashboard'))
    
    restaurant_ids = current_user.get_restaurant_scope()
    
    # Get filters
    month_filter = request.args.get('month')
    status_filter = request.args.get('status')
    
    # Build query
    query = PayrollRecord.query.filter(
        PayrollRecord.restaurant_id.in_(restaurant_ids)
    ).join(User, PayrollRecord.user_id == User.id)
    
    if month_filter:
        year, month = map(int, month_filter.split('-'))
        query = query.filter(
            func.extract('year', PayrollRecord.pay_period_start) == year,
            func.extract('month', PayrollRecord.pay_period_start) == month
        )
    
    if status_filter:
        query = query.filter(PayrollRecord.payment_status == status_filter)
    
    payroll_records = query.order_by(desc(PayrollRecord.created_at)).all()
    
    return render_template('employee/payroll.html', 
                         payroll_records=payroll_records,
                         month_filter=month_filter,
                         status_filter=status_filter)

@bp.route('/payroll/generate', methods=['POST'])
@login_required
def generate_payroll():
    """Generate payroll for a period"""
    if not require_admin_permission():
        return jsonify({'success': False, 'message': 'Permission denied'}), 403
    
    try:
        period_start = datetime.strptime(request.form.get('period_start') or '', '%Y-%m-%d').date()
        period_end = datetime.strptime(request.form.get('period_end') or '', '%Y-%m-%d').date()
        restaurant_id = int(request.form.get('restaurant_id') or 0)
        
        # Get all active employees for the restaurant
        employees = User.query.filter(
            User.restaurant_id == restaurant_id,
            User.user_active == True
        ).all()
        
        generated_count = 0
        for employee in employees:
            # Check if payroll already exists for this period
            existing = PayrollRecord.query.filter(
                PayrollRecord.user_id == employee.id,
                PayrollRecord.pay_period_start == period_start,
                PayrollRecord.pay_period_end == period_end
            ).first()
            
            if existing:
                continue
            
            # Get employee profile
            profile = EmployeeProfile.query.filter_by(user_id=employee.id).first()
            if not profile:
                continue
            
            # Calculate attendance data for the period
            attendances = EmployeeAttendance.query.filter(
                EmployeeAttendance.user_id == employee.id,
                EmployeeAttendance.date >= period_start,
                EmployeeAttendance.date <= period_end,
                EmployeeAttendance.attendance_status.in_(['present', 'late'])
            ).all()
            
            total_overtime_hours = sum([float(att.overtime_hours or 0) for att in attendances])
            
            # Create payroll record
            payroll = PayrollRecord(
                user_id=employee.id,
                restaurant_id=restaurant_id,
                pay_period_start=period_start,
                pay_period_end=period_end,
                basic_salary=profile.basic_salary,
                overtime_hours=total_overtime_hours,
                overtime_rate=1.5
            )
            
            payroll.calculate_overtime_pay()
            payroll.calculate_gross_pay()
            payroll.calculate_net_pay()
            
            db.session.add(payroll)
            generated_count += 1
        
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': f'Payroll generated for {generated_count} employees'
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error generating payroll: {str(e)}")
        return jsonify({'success': False, 'message': 'Failed to generate payroll'}), 500

# Performance Management
@bp.route('/performance')
@login_required
def performance():
    """Performance management page"""
    if not require_manager_permission():
        flash('You do not have permission to access performance management', 'error')
        return redirect(url_for('main.dashboard'))
    
    restaurant_ids = current_user.get_restaurant_scope()
    
    # Get filters
    period_filter = request.args.get('period')
    
    # Build query
    query = EmployeePerformance.query.filter(
        EmployeePerformance.restaurant_id.in_(restaurant_ids)
    ).join(User, EmployeePerformance.user_id == User.id)
    
    if period_filter:
        query = query.filter(EmployeePerformance.evaluation_period == period_filter)
    
    performance_records = query.order_by(desc(EmployeePerformance.created_at)).all()
    
    return render_template('employee/performance.html', 
                         performance_records=performance_records,
                         period_filter=period_filter)

@bp.route('/performance/evaluate', methods=['GET', 'POST'])
@login_required
def evaluate_performance():
    """Evaluate employee performance"""
    if not require_manager_permission():
        flash('You do not have permission to evaluate performance', 'error')
        return redirect(url_for('employee.performance'))
    
    if request.method == 'POST':
        try:
            performance_data = {
                'user_id': request.form.get('user_id'),
                'restaurant_id': request.form.get('restaurant_id'),
                'evaluation_period': request.form.get('evaluation_period'),
                'customer_ratings': Decimal(request.form.get('customer_ratings', 0)),
                'sales_performance': Decimal(request.form.get('sales_performance', 0)),
                'order_accuracy': Decimal(request.form.get('order_accuracy', 0)),
                'productivity_score': Decimal(request.form.get('productivity_score', 0)),
                'teamwork_score': Decimal(request.form.get('teamwork_score', 0)),
                'punctuality_score': Decimal(request.form.get('punctuality_score', 0)),
                'feedback': request.form.get('feedback'),
                'evaluator_id': current_user.id
            }
            
            performance = EmployeePerformance(**performance_data)
            performance.calculate_overall_score()
            
            # Parse JSON fields
            goals_achieved = request.form.get('goals_achieved')
            if goals_achieved:
                performance.goals_achieved = json.loads(goals_achieved)
            
            areas_for_improvement = request.form.get('areas_for_improvement')
            if areas_for_improvement:
                performance.areas_for_improvement = json.loads(areas_for_improvement)
            
            db.session.add(performance)
            db.session.commit()
            
            flash('Performance evaluation submitted successfully', 'success')
            return redirect(url_for('employee.performance'))
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error evaluating performance: {str(e)}")
            flash('Error submitting performance evaluation', 'error')
    
    # Get employees for evaluation
    restaurant_ids = current_user.get_restaurant_scope()
    employees = User.query.filter(
        User.restaurant_id.in_(restaurant_ids),
        User.user_active == True
    ).all()
    
    return render_template('employee/evaluate_performance.html', employees=employees)

# API endpoints for real-time updates
@bp.route('/api/attendance/stats')
@login_required
def attendance_stats():
    """Get attendance statistics for dashboard"""
    if not require_manager_permission():
        return jsonify({'error': 'Permission denied'}), 403
    
    restaurant_ids = current_user.get_restaurant_scope()
    today = date.today()
    
    # Today's stats
    present = EmployeeAttendance.query.filter(
        EmployeeAttendance.restaurant_id.in_(restaurant_ids),
        EmployeeAttendance.date == today,
        EmployeeAttendance.attendance_status.in_(['present', 'late'])
    ).count()
    
    absent = EmployeeAttendance.query.filter(
        EmployeeAttendance.restaurant_id.in_(restaurant_ids),
        EmployeeAttendance.date == today,
        EmployeeAttendance.attendance_status == 'absent'
    ).count()
    
    on_leave = LeaveRequest.query.filter(
        LeaveRequest.restaurant_id.in_(restaurant_ids),
        LeaveRequest.start_date <= today,
        LeaveRequest.end_date >= today,
        LeaveRequest.status == 'approved'
    ).count()
    
    return jsonify({
        'present': present,
        'absent': absent,
        'on_leave': on_leave,
        'total': present + absent + on_leave
    })

@bp.route('/api/shifts/week')
@login_required
def week_shifts():
    """Get shifts for a week"""
    if not require_manager_permission():
        return jsonify({'error': 'Permission denied'}), 403
    
    restaurant_ids = current_user.get_restaurant_scope()
    week_start = request.args.get('week_start')
    
    if not week_start:
        return jsonify({'error': 'Week start date required'}), 400
    
    week_start = datetime.strptime(week_start, '%Y-%m-%d').date()
    week_end = week_start + timedelta(days=6)
    
    shifts = ShiftSchedule.query.filter(
        ShiftSchedule.restaurant_id.in_(restaurant_ids),
        ShiftSchedule.shift_date >= week_start,
        ShiftSchedule.shift_date <= week_end
    ).join(User, ShiftSchedule.user_id == User.id).all()
    
    return jsonify([shift.to_dict() for shift in shifts])