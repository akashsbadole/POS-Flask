from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app.kitchen import bp
from app.models.order import Order, OrderStatus
from app.models.user import User
from app import db
from app.socketio_events import emit_order_status_update, emit_kitchen_stats, emit_kitchen_ticket_update
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
    old_status = order.status
    new_status = request.form.get('status')
    
    if new_status:
        try:
            order.update_status(OrderStatus(new_status))
            db.session.commit()
            
            flash(f'Order {order.order_number} status updated to {new_status}', 'success')
            
            # Broadcast update via WebSocket
            emit_order_status_update(order, old_status)
            
            # Update kitchen stats
            emit_kitchen_stats()
            
            # Emit kitchen ticket update for status changes
            emit_kitchen_ticket_update(order)
            
        except ValueError:
            flash('Invalid status', 'error')
    
    if request.headers.get('HX-Request'):
        return render_template('kitchen/partials/order_card.html', order=order)
    
    return redirect(url_for('kitchen.display'))

@bp.route('/order/<int:order_id>/timer/start', methods=['POST'])
@login_required
def start_timer(order_id):
    """Start preparation timer for an order"""
    if current_user.role != 'kitchen' and not current_user.can_access_manager_features():
        return jsonify({'error': 'Access denied'}), 403
    
    order = Order.query.get_or_404(order_id)
    
    # Start timer when preparation begins
    if not order.timer_started_at:
        order.timer_started_at = datetime.utcnow()
        order.status = OrderStatus.PREPARING
        db.session.commit()
        
        # Broadcast update via WebSocket
        emit_order_status_update(order, OrderStatus.CONFIRMED)
        emit_kitchen_stats()
        
        return jsonify({'success': True, 'message': 'Timer started'})
    
    return jsonify({'error': 'Timer already started'}), 400

@bp.route('/order/<int:order_id>/timer/adjust', methods=['POST'])
@login_required
def adjust_timer(order_id):
    """Adjust preparation timer for an order"""
    if current_user.role != 'kitchen' and not current_user.can_access_manager_features():
        return jsonify({'error': 'Access denied'}), 403
    
    order = Order.query.get_or_404(order_id)
    adjustment = request.form.get('adjustment', type=int)
    reason = request.form.get('reason', '')
    
    if not adjustment:
        return jsonify({'error': 'Adjustment amount required'}), 400
    
    # Adjust estimated preparation time
    if order.estimated_preparation_time:
        order.estimated_preparation_time = max(60, order.estimated_preparation_time + adjustment)
        db.session.commit()
        
        # Broadcast update via WebSocket
        emit_order_status_update(order, order.status)
        
        return jsonify({
            'success': True,
            'message': f'Timer adjusted by {adjustment} seconds',
            'new_duration': order.estimated_preparation_time
        })
    
    return jsonify({'error': 'No timer to adjust'}), 400

@bp.route('/order/<int:order_id>/timer/complete', methods=['POST'])
@login_required
def complete_timer(order_id):
    """Mark preparation timer as complete"""
    if current_user.role != 'kitchen' and not current_user.can_access_manager_features():
        return jsonify({'error': 'Access denied'}), 403
    
    order = Order.query.get_or_404(order_id)
    
    # Complete timer when order is ready
    if order.timer_started_at and not order.timer_completed_at:
        order.timer_completed_at = datetime.utcnow()
        order.status = OrderStatus.READY
        
        # Calculate actual preparation time
        time_diff = order.timer_completed_at - order.timer_started_at
        order.actual_preparation_time = int(time_diff.total_seconds())
        
        db.session.commit()
        
        # Broadcast update via WebSocket
        emit_order_status_update(order, OrderStatus.PREPARING)
        emit_kitchen_stats()
        
        return jsonify({
            'success': True,
            'message': 'Timer completed',
            'actual_time': order.actual_preparation_time
        })
    
    return jsonify({'error': 'Timer not running or already completed'}), 400

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
    
    # Include preparation time calculations
    result = []
    for order in orders:
        order_dict = order.to_dict(include_items=True)
        
        # Calculate estimated preparation time if not set
        if not order.estimated_preparation_time:
            order_dict['estimated_preparation_time'] = order.calculate_preparation_time()
        
        result.append(order_dict)
    
    return jsonify(result)

@bp.route('/api/order/<int:order_id>')
@login_required
def api_order(order_id):
    """API endpoint to get specific order"""
    if current_user.role != 'kitchen' and not current_user.can_access_manager_features():
        return jsonify({'error': 'Access denied'}), 403
    
    order = Order.query.get_or_404(order_id)
    order_dict = order.to_dict(include_items=True)
    
    # Calculate estimated preparation time if not set
    if not order.estimated_preparation_time:
        order_dict['estimated_preparation_time'] = order.calculate_preparation_time()
    
    return jsonify(order_dict)

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

@bp.route('/order/<int:order_id>/assign', methods=['POST'])
@login_required
def assign_order(order_id):
    """Assign order to a kitchen station"""
    if current_user.role != 'kitchen' and not current_user.can_access_manager_features():
        return jsonify({'error': 'Access denied'}), 403
    
    order = Order.query.get_or_404(order_id)
    station = request.form.get('station')
    
    if not station:
        return jsonify({'error': 'Station is required'}), 400
    
    # Update order with station assignment (you might need to add a station field to the Order model)
    # For now, we'll just emit the assignment event
    from app.socketio_events import emit_order_assigned
    emit_order_assigned(order, station)
    
    flash(f'Order {order.order_number} assigned to {station}', 'success')
    
    return jsonify({'success': True, 'message': f'Order assigned to {station}'})

@bp.route('/order/<int:order_id>/print-ticket', methods=['POST'])
@login_required
def print_kitchen_ticket(order_id):
    """Print kitchen ticket for an order"""
    if current_user.role != 'kitchen' and not current_user.can_access_manager_features():
        return jsonify({'error': 'Access denied'}), 403
    
    order = Order.query.get_or_404(order_id)
    
    try:
        from app.receipt_printer import print_kitchen_ticket
        print_kitchen_ticket(order)
        
        # Emit kitchen ticket update
        emit_kitchen_ticket_update(order)
        
        flash(f'Kitchen ticket printed for order {order.order_number}', 'success')
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500