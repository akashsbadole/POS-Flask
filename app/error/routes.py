from flask import Blueprint, jsonify, request, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from app.error import bp
from app.models.error import ErrorLog, ErrorPattern, ErrorNotification, ErrorSeverity, ErrorCategory, ErrorStatus
from app.models.user import User
from app import db
from datetime import datetime, timedelta
import json
import re
import traceback
from functools import wraps

def error_handler(category=ErrorCategory.SYSTEM, severity=ErrorSeverity.MEDIUM):
    """Decorator to automatically log function errors"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                return f(*args, **kwargs)
            except Exception as e:
                # Log the error automatically
                error_log = ErrorLog(
                    error_code=f"ERR_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
                    title=f"Error in {f.__name__}",
                    description=str(e),
                    category=category,
                    severity=severity,
                    user_id=current_user.id if current_user.is_authenticated else None,
                    restaurant_id=current_user.restaurant_id if current_user.is_authenticated else None,
                    request_url=request.url,
                    request_method=request.method,
                    request_data=json.dumps(dict(request.form) if request.form else {}),
                    stack_trace=traceback.format_exc(),
                    ip_address=request.remote_addr,
                    user_agent=request.headers.get('User-Agent', ''),
                    browser_info=request.headers.get('User-Agent', '')
                )
                
                db.session.add(error_log)
                db.session.commit()
                
                # Re-raise the exception
                raise
        return decorated_function
    return decorator

def send_error_notification(error_log):
    """Send error notification to relevant users"""
    try:
        # Find admin users to notify
        admin_users = User.query.filter_by(is_admin=True).all()
        
        for admin in admin_users:
            notification = ErrorNotification(
                error_id=error_log.id,
                user_id=admin.id,
                notification_type='email',
                recipient=admin.email,
                is_delivered=False
            )
            db.session.add(notification)
        
        db.session.commit()
        
        # In a real implementation, you would send actual emails here
        # For now, we'll just mark them as delivered for demo purposes
        for notification in error_log.notifications:
            notification.is_delivered = True
            notification.delivered_at = datetime.utcnow()
        
        db.session.commit()
        
    except Exception as e:
        # Don't let notification errors break the main flow
        print(f"Failed to send error notification: {e}")

def check_error_patterns(error_message):
    """Check if error matches any known patterns"""
    patterns = ErrorPattern.query.filter_by(is_active=True).all()
    
    for pattern in patterns:
        if re.search(pattern.pattern_regex, error_message, re.IGNORECASE):
            # Count recent occurrences
            time_window = datetime.utcnow() - timedelta(hours=pattern.time_window_hours)
            recent_count = ErrorLog.query.filter(
                ErrorLog.occurred_at >= time_window,
                ErrorLog.title.ilike(f'%{pattern.pattern_name}%')
            ).count()
            
            if recent_count >= pattern.occurrence_threshold:
                # Create a high-priority error for the pattern
                pattern_error = ErrorLog(
                    error_code=f"PATTERN_{pattern.pattern_name.upper()}",
                    title=f"Recurring Error Pattern: {pattern.pattern_name}",
                    description=f"Error pattern '{pattern.pattern_name}' has occurred {recent_count} times in the last {pattern.time_window_hours} hours",
                    category=pattern.category,
                    severity=pattern.severity,
                    status=ErrorStatus.OPEN
                )
                
                db.session.add(pattern_error)
                db.session.commit()
                
                # Send notification for pattern error
                send_error_notification(pattern_error)
                
                return pattern_error
    
    return None

@bp.route('/logs')
@login_required
def error_logs():
    """Get error logs with filtering"""
    if not current_user.can_access_admin_features():
        return jsonify({'error': 'Access denied'}), 403
    
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    severity_filter = request.args.get('severity', '')
    category_filter = request.args.get('category', '')
    status_filter = request.args.get('status', '')
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    
    query = ErrorLog.query
    
    # Apply filters
    if severity_filter:
        query = query.filter_by(severity=severity_filter)
    if category_filter:
        query = query.filter_by(category=category_filter)
    if status_filter:
        query = query.filter_by(status=status_filter)
    if date_from:
        try:
            date_from = datetime.strptime(date_from, '%Y-%m-%d')
            query = query.filter(ErrorLog.occurred_at >= date_from)
        except ValueError:
            pass
    if date_to:
        try:
            date_to = datetime.strptime(date_to, '%Y-%m-%d')
            query = query.filter(ErrorLog.occurred_at <= date_to)
        except ValueError:
            pass
    
    # Order by most recent
    logs = query.order_by(ErrorLog.occurred_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return jsonify({
        'logs': [log.to_dict(include_user=True, include_resolution=True) for log in logs.items],
        'pagination': {
            'page': logs.page,
            'pages': logs.pages,
            'per_page': logs.per_page,
            'total': logs.total,
            'has_next': logs.has_next,
            'has_prev': logs.has_prev
        }
    })

@bp.route('/patterns')
@login_required
def error_patterns():
    """Get error patterns for monitoring"""
    if not current_user.can_access_admin_features():
        return jsonify({'error': 'Access denied'}), 403
    
    patterns = ErrorPattern.query.filter_by(is_active=True).all()
    
    return jsonify({
        'patterns': [pattern.to_dict() for pattern in patterns]
    })

@bp.route('/log', methods=['POST'])
@login_required
@error_handler(category=ErrorCategory.USER, severity=ErrorSeverity.MEDIUM)
def create_error_log():
    """Create new error log entry"""
    if not current_user.can_access_admin_features():
        return jsonify({'error': 'Access denied'}), 403
    
    data = request.get_json()
    
    try:
        # Convert string enums to enum objects
        category = ErrorCategory(data.get('category', 'system')) if isinstance(data.get('category'), str) else data.get('category', ErrorCategory.SYSTEM)
        severity = ErrorSeverity(data.get('severity', 'medium')) if isinstance(data.get('severity'), str) else data.get('severity', ErrorSeverity.MEDIUM)
        
        error_log = ErrorLog(
            error_code=data.get('error_code', f"ERR_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"),
            title=data.get('title', 'Unknown Error'),
            description=data.get('description', ''),
            category=category,
            severity=severity,
            user_id=current_user.id,
            restaurant_id=current_user.restaurant_id,
            request_url=request.url,
            request_method=request.method,
            request_data=json.dumps(data.get('request_data', {})),
            stack_trace=data.get('stack_trace', ''),
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent', ''),
            browser_info=request.headers.get('User-Agent', '')
        )
        
        db.session.add(error_log)
        db.session.commit()
        
        # Check for error patterns
        pattern_error = check_error_patterns(error_log.title)
        
        # Send notification for critical errors
        if error_log.severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]:
            send_error_notification(error_log)
        
        return jsonify({
            'success': True,
            'message': 'Error logged successfully',
            'error_id': error_log.id,
            'pattern_detected': pattern_error is not None
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/log-frontend', methods=['POST'])
def log_frontend_error():
    """Log frontend errors from JavaScript"""
    data = request.get_json()
    
    try:
        # Convert string enums to enum objects
        category = ErrorCategory(data.get('category', 'system')) if isinstance(data.get('category'), str) else ErrorCategory.SYSTEM
        severity = ErrorSeverity(data.get('severity', 'medium')) if isinstance(data.get('severity'), str) else ErrorSeverity.MEDIUM
        
        error_log = ErrorLog(
            error_code=data.get('error_code', f"FRONTEND_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"),
            title=data.get('title', 'Frontend Error'),
            description=data.get('description', ''),
            category=category,
            severity=severity,
            user_id=current_user.id if current_user.is_authenticated else None,
            restaurant_id=current_user.restaurant_id if current_user.is_authenticated else None,
            session_id=data.get('session_id'),
            request_url=data.get('url', request.url),
            request_method='GET',  # Frontend errors are typically GET requests
            request_data=json.dumps(data.get('additional_data', {})),
            stack_trace=data.get('stack_trace', ''),
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent', ''),
            browser_info=data.get('browser_info', request.headers.get('User-Agent', ''))
        )
        
        db.session.add(error_log)
        db.session.commit()
        
        # Check for error patterns
        pattern_error = check_error_patterns(error_log.title)
        
        # Send notification for critical frontend errors
        if error_log.severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]:
            send_error_notification(error_log)
        
        return jsonify({
            'success': True,
            'message': 'Frontend error logged successfully',
            'error_id': error_log.id,
            'pattern_detected': pattern_error is not None
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/resolve/<int:error_id>', methods=['POST'])
@login_required
def resolve_error(error_id):
    """Resolve an error log entry"""
    if not current_user.can_access_admin_features():
        return jsonify({'error': 'Access denied'}), 403
    
    error_log = ErrorLog.query.get_or_404(error_id)
    data = request.get_json()
    
    try:
        error_log.status = ErrorStatus.RESOLVED
        error_log.resolution = data.get('resolution', 'Resolved by administrator')
        error_log.resolution_notes = data.get('resolution_notes', '')
        error_log.resolved_by = current_user.id
        error_log.resolved_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Error resolved successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/assign/<int:error_id>', methods=['POST'])
@login_required
def assign_error(error_id):
    """Assign error to a user"""
    if not current_user.can_access_admin_features():
        return jsonify({'error': 'Access denied'}), 403
    
    error_log = ErrorLog.query.get_or_404(error_id)
    data = request.get_json()
    
    try:
        assigned_to = data.get('assigned_to')
        if assigned_to:
            error_log.assigned_to = assigned_to
            error_log.status = ErrorStatus.IN_PROGRESS
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Error assigned successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/bulk-resolve', methods=['POST'])
@login_required
def bulk_resolve_errors():
    """Resolve multiple errors at once"""
    if not current_user.can_access_admin_features():
        return jsonify({'error': 'Access denied'}), 403
    
    data = request.get_json()
    error_ids = data.get('error_ids', [])
    resolution = data.get('resolution', 'Bulk resolved by administrator')
    
    try:
        errors = ErrorLog.query.filter(ErrorLog.id.in_(error_ids)).all()
        
        for error in errors:
            error.status = ErrorStatus.RESOLVED
            error.resolution = resolution
            error.resolved_by = current_user.id
            error.resolved_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'{len(errors)} errors resolved successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/patterns/create', methods=['POST'])
@login_required
def create_error_pattern():
    """Create new error pattern"""
    if not current_user.can_access_admin_features():
        return jsonify({'error': 'Access denied'}), 403
    
    data = request.get_json()
    
    try:
        pattern = ErrorPattern(
            pattern_name=data.get('pattern_name'),
            pattern_regex=data.get('pattern_regex'),
            description=data.get('description', ''),
            category=ErrorCategory(data.get('category', 'system')),
            severity=ErrorSeverity(data.get('severity', 'medium')),
            occurrence_threshold=data.get('occurrence_threshold', 5),
            time_window_hours=data.get('time_window_hours', 24)
        )
        
        db.session.add(pattern)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Error pattern created successfully',
            'pattern_id': pattern.id
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/export')
@login_required
def export_errors():
    """Export errors to CSV"""
    if not current_user.can_access_admin_features():
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        import csv
        from io import StringIO
        
        # Get all errors
        errors = ErrorLog.query.order_by(ErrorLog.occurred_at.desc()).all()
        
        # Create CSV
        output = StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow([
            'ID', 'Error Code', 'Title', 'Description', 'Category', 'Severity',
            'Status', 'User ID', 'Restaurant ID', 'Occurred At', 'Resolved At',
            'Resolution', 'IP Address'
        ])
        
        # Data
        for error in errors:
            writer.writerow([
                error.id,
                error.error_code,
                error.title,
                error.description,
                error.category.value if error.category else '',
                error.severity.value if error.severity else '',
                error.status.value if error.status else '',
                error.user_id,
                error.restaurant_id,
                error.occurred_at.isoformat() if error.occurred_at else '',
                error.resolved_at.isoformat() if error.resolved_at else '',
                error.resolution,
                error.ip_address
            ])
        
        output.seek(0)
        
        from flask import Response
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={'Content-Disposition': 'attachment; filename=errors_export.csv'}
        )
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/stats')
@login_required
def error_stats():
    """Get error statistics for dashboard"""
    if not current_user.can_access_admin_features():
        return jsonify({'error': 'Access denied'}), 403
    
    # Get date range
    days = request.args.get('days', 30, type=int)
    date_from = datetime.utcnow() - timedelta(days=days)
    
    stats = {
        'total_errors': ErrorLog.query.filter(ErrorLog.occurred_at >= date_from).count(),
        'by_severity': {},
        'by_category': {},
        'by_status': {},
        'recent_trends': []
    }
    
    # Get error counts by severity
    severities = ['low', 'medium', 'high', 'critical']
    for severity in severities:
        count = ErrorLog.query.filter(
            ErrorLog.occurred_at >= date_from,
            ErrorLog.severity == severity
        ).count()
        stats['by_severity'][severity] = count
    
    # Get error counts by category
    categories = ['system', 'user', 'payment', 'order', 'inventory', 'license', 'network', 'database']
    for category in categories:
        count = ErrorLog.query.filter(
            ErrorLog.occurred_at >= date_from,
            ErrorLog.category == category
        ).count()
        stats['by_category'][category] = count
    
    # Get error counts by status
    statuses = ['open', 'in_progress', 'resolved', 'closed']
    for status in statuses:
        count = ErrorLog.query.filter(
            ErrorLog.occurred_at >= date_from,
            ErrorLog.status == status
        ).count()
        stats['by_status'][status] = count
    
    # Get recent error trends (last 7 days)
    trend_date = datetime.utcnow() - timedelta(days=7)
    recent_errors = ErrorLog.query.filter(
        ErrorLog.occurred_at >= trend_date
    ).order_by(ErrorLog.occurred_at.desc()).limit(100).all()
    
    # Group by error code for trends
    error_trends = {}
    for error in recent_errors:
        if error.error_code not in error_trends:
            error_trends[error.error_code] = {
                'count': 1,
                'title': error.title,
                'severity': error.severity.value if error.severity else None,
                'last_occurred': error.occurred_at.isoformat()
            }
        else:
            error_trends[error.error_code]['count'] += 1
            error_trends[error.error_code]['last_occurred'] = error.occurred_at.isoformat()
    
    stats['recent_trends'] = list(error_trends.values())[:10]  # Top 10 errors
    
    return jsonify(stats)

@bp.route('/notifications')
@login_required
def error_notifications():
    """Get error notification history"""
    if not current_user.can_access_admin_features():
        return jsonify({'error': 'Access denied'}), 403
    
    notifications = ErrorNotification.query.filter_by(user_id=current_user.id).order_by(
        ErrorNotification.created_at.desc()
    ).limit(50).all()
    
    return jsonify({
        'notifications': [notification.to_dict() for notification in notifications]
    })

@bp.route('/dashboard')
@login_required
def error_dashboard():
    """Error management dashboard"""
    if not current_user.can_access_admin_features():
        return render_template('errors/403.html'), 403
    
    # Get recent error statistics
    stats_response = error_stats()
    if isinstance(stats_response, tuple) and len(stats_response) == 2:
        stats_data = stats_response[0].get_json()
    else:
        stats_data = stats_response.get_json()
    
    return render_template('errors/dashboard.html', stats=stats_data['data'])