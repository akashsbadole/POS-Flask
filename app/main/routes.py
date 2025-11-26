from flask import render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from sqlalchemy import desc
from app.main import bp
from app.models.user import User
from app.models.order import Order, OrderStatus
from app.models.table import Table, TableStatus
from app import db
from datetime import datetime, timedelta

@bp.route('/')
def index():
    """Main landing page - redirect to login or appropriate dashboard"""
    if current_user.is_authenticated:
        if current_user.role == 'cashier':
            return redirect(url_for('cashier.dashboard'))
        elif current_user.role == 'kitchen':
            return redirect(url_for('kitchen.display'))
        elif current_user.role in ['manager', 'admin']:
            return redirect(url_for('manager.dashboard'))
    return redirect(url_for('auth.login'))

@bp.route('/dashboard')
@login_required
def dashboard():
    """Role-based dashboard redirect"""
    if current_user.role == 'cashier':
        return redirect(url_for('cashier.dashboard'))
    elif current_user.role == 'kitchen':
        return redirect(url_for('kitchen.display'))
    elif current_user.role in ['manager', 'admin']:
        return redirect(url_for('manager.dashboard'))
    else:
        flash('Invalid user role', 'error')
        return redirect(url_for('auth.logout'))

@bp.route('/system-status')
@login_required
def system_status():
    """System status page for admin/manager"""
    if not current_user.can_access_manager_features():
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    # Get system statistics
    stats = {
        'total_users': User.query.count(),
        'active_users': User.query.filter_by(is_active=True).count(),
        'total_orders_today': Order.query.filter(
            Order.created_at >= datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        ).count(),
        'pending_orders': Order.query.filter_by(status=OrderStatus.PENDING).count(),
        'total_tables': Table.query.count(),
        'occupied_tables': Table.query.filter_by(status=TableStatus.OCCUPIED).count(),
        'available_tables': Table.query.filter_by(status=TableStatus.FREE, is_active=True).count()
    }
    
    # Get recent orders
    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(10).all()
    
    # Get active users (logged in recently)
    active_users = User.query.filter(
        User.last_login >= datetime.utcnow() - timedelta(hours=1)
    ).order_by(User.last_login.desc()).limit(10).all()
    
    return render_template('main/system_status.html', 
                         stats=stats, 
                         recent_orders=recent_orders,
                         active_users=active_users)

@bp.errorhandler(404)
def not_found_error(error):
    """Handle 404 errors"""
    if request.headers.get('HX-Request'):
        return render_template('errors/404.html'), 404
    return render_template('errors/404.html'), 404

@bp.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    db.session.rollback()
    if request.headers.get('HX-Request'):
        return render_template('errors/500.html'), 500
    return render_template('errors/500.html'), 500

@bp.context_processor
def utility_functions():
    """Add utility functions to templates"""
    def format_currency(amount):
        """Format amount as currency"""
        return f"${float(amount):.2f}"
    
    def format_datetime(dt, format='medium'):
        """Format datetime"""
        if not dt:
            return ''
        if format == 'short':
            return dt.strftime('%m/%d %H:%M')
        elif format == 'medium':
            return dt.strftime('%m/%d/%Y %H:%M')
        elif format == 'long':
            return dt.strftime('%B %d, %Y at %I:%M %p')
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    
    def time_ago(dt):
        """Get human readable time ago"""
        if not dt:
            return ''
        now = datetime.utcnow()
        diff = now - dt
        
        if diff.days > 0:
            return f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours} hour{'s' if hours > 1 else ''} ago"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
        else:
            return "Just now"
    
    return dict(
        format_currency=format_currency,
        format_datetime=format_datetime,
        time_ago=time_ago
    )