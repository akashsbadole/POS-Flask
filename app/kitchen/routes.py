from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app.kitchen import bp
from app.models.order import Order, OrderStatus
from app.models.user import User
from app import db
from datetime import datetime, timedelta

@bp.route('/display')
@login_required
def display():
    """Kitchen display system"""
    if current_user.role != 'kitchen' and not current_user.can_access_manager_features():
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    # Get orders that need to be displayed
    orders = Order.query.filter(
        Order.status.in_([OrderStatus.PENDING, OrderStatus.CONFIRMED, OrderStatus.PREPARING, OrderStatus.READY])
    ).order_by(Order.created_at.asc()).all()
    
    if request.headers.get('HX-Request'):
        return render_template('kitchen/partials/order_list.html', orders=orders)
    
    return render_template('kitchen/display.html', orders=orders)

@bp.route('/orders')
@login_required
def list_orders():
    """List all orders with filtering"""
    if current_user.role != 'kitchen' and not current_user.can_access_manager_features():
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    status_filter = request.args.get('status')
    
    query = Order.query
    if status_filter:
        try:
            status = OrderStatus(status_filter)
            query = query.filter_by(status=status)
        except ValueError:
            pass
    
    orders = query.order_by(Order.created_at.desc()).limit(50).all()
    
    return render_template('kitchen/orders.html', orders=orders, status_filter=status_filter)

@bp.route('/order/<int:order_id>/update-status', methods=['POST'])
@login_required
def update_order_status(order_id):
    """Update order status"""
    if current_user.role != 'kitchen' and not current_user.can_access_manager_features():
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    order = Order.query.get_or_404(order_id)
    new_status = request.form.get('status')
    
    if new_status:
        try:
            order.update_status(OrderStatus(new_status))
            db.session.commit()
            
            flash(f'Order {order.order_number} status updated to {new_status}', 'success')
            
            # Broadcast update via WebSocket (handled by socketio_events.py)
            
        except ValueError:
            flash('Invalid status', 'error')
    
    if request.headers.get('HX-Request'):
        return render_template('kitchen/partials/order_card.html', order=order)
    
    return redirect(url_for('kitchen.display'))

@bp.route('/order/<int:order_id>/details')
@login_required
def order_details(order_id):
    """View order details"""
    if current_user.role != 'kitchen' and not current_user.can_access_manager_features():
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    order = Order.query.get_or_404(order_id)
    
    return render_template('kitchen/order_details.html', order=order)

@bp.route('/dashboard')
@login_required
def dashboard():
    """Kitchen dashboard with statistics"""
    if current_user.role != 'kitchen' and not current_user.can_access_manager_features():
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    # Get statistics
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    stats = {
        'pending_orders': Order.query.filter_by(status=OrderStatus.PENDING).count(),
        'preparing_orders': Order.query.filter_by(status=OrderStatus.PREPARING).count(),
        'ready_orders': Order.query.filter_by(status=OrderStatus.READY).count(),
        'completed_today': Order.query.filter(
            Order.status == OrderStatus.SERVED,
            Order.completed_at >= today
        ).count(),
        'total_today': Order.query.filter(Order.created_at >= today).count()
    }
    
    # Get recent orders
    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(10).all()
    
    return render_template('kitchen/dashboard.html', stats=stats, recent_orders=recent_orders)

# API endpoints
@bp.route('/api/orders')
@login_required
def api_orders():
    """API endpoint to get orders"""
    if current_user.role != 'kitchen' and not current_user.can_access_manager_features():
        return jsonify({'error': 'Access denied'}), 403
    
    status_filter = request.args.get('status')
    
    query = Order.query
    if status_filter:
        try:
            status = OrderStatus(status_filter)
            query = query.filter_by(status=status)
        except ValueError:
            pass
    
    orders = query.order_by(Order.created_at.asc()).all()
    return jsonify([order.to_dict(include_items=True) for order in orders])

@bp.route('/api/order/<int:order_id>')
@login_required
def api_order(order_id):
    """API endpoint to get specific order"""
    if current_user.role != 'kitchen' and not current_user.can_access_manager_features():
        return jsonify({'error': 'Access denied'}), 403
    
    order = Order.query.get_or_404(order_id)
    return jsonify(order.to_dict(include_items=True))

@bp.route('/api/stats')
@login_required
def api_stats():
    """API endpoint to get kitchen statistics"""
    if current_user.role != 'kitchen' and not current_user.can_access_manager_features():
        return jsonify({'error': 'Access denied'}), 403
    
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    stats = {
        'pending_orders': Order.query.filter_by(status=OrderStatus.PENDING).count(),
        'preparing_orders': Order.query.filter_by(status=OrderStatus.PREPARING).count(),
        'ready_orders': Order.query.filter_by(status=OrderStatus.READY).count(),
        'completed_today': Order.query.filter(
            Order.status == OrderStatus.SERVED,
            Order.completed_at >= today
        ).count(),
        'total_today': Order.query.filter(Order.created_at >= today).count(),
        'avg_preparation_time': 15  # TODO: Calculate actual average
    }
    
    return jsonify(stats)