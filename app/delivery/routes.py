"""
Delivery Management Routes for Restaurant POS System
Handles driver management, delivery tracking, and route optimization
"""

from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from datetime import datetime, timedelta
import json

from app.delivery import bp
from app.models.order import Order, OrderStatus, OrderType
from app.models.user import User
from app import db

@bp.route('/')
@login_required
def dashboard():
    """Delivery management dashboard"""
    if not current_user.can_access_manager_features():
        flash('Access denied', 'error')
        return redirect(url_for('main.index'))
    
    # Get delivery statistics
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Get active delivery orders
    active_deliveries = Order.query.filter(
        Order.order_type == OrderType.DELIVERY,
        Order.status.in_([OrderStatus.CONFIRMED, OrderStatus.PREPARING, OrderStatus.READY]),
        Order.created_at >= today
    ).order_by(Order.created_at.desc()).all()
    
    # Get completed deliveries today
    completed_deliveries = Order.query.filter(
        Order.order_type == OrderType.DELIVERY,
        Order.status == OrderStatus.SERVED,
        Order.completed_at >= today
    ).order_by(db.desc(Order.completed_at)).all()
    
    # Get delivery drivers
    drivers = User.query.filter_by(role='driver').all()
    
    return render_template('delivery/dashboard.html',
                         active_deliveries=active_deliveries,
                         completed_deliveries=completed_deliveries,
                         drivers=drivers)

@bp.route('/orders')
@login_required
def delivery_orders():
    """List all delivery orders"""
    if not current_user.can_access_manager_features():
        flash('Access denied', 'error')
        return redirect(url_for('main.index'))
    
    status_filter = request.args.get('status', 'all')
    page = request.args.get('page', 1, type=int)
    
    query = Order.query.filter_by(order_type=OrderType.DELIVERY)
    
    if status_filter != 'all':
        query = query.filter_by(status=status_filter)
    
    # Pagination
    per_page = 20
    orders = query.order_by(Order.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return render_template('delivery/orders.html',
                         orders=orders,
                         status_filter=status_filter)

@bp.route('/order/<int:order_id>')
@login_required
def delivery_order_detail(order_id):
    """View delivery order details"""
    if not current_user.can_access_manager_features():
        flash('Access denied', 'error')
        return redirect(url_for('delivery.delivery_orders'))
    
    order = Order.query.get_or_404(order_id)
    
    if order.order_type != OrderType.DELIVERY:
        flash('Not a delivery order', 'error')
        return redirect(url_for('delivery.delivery_orders'))
    
    return render_template('delivery/order_detail.html', order=order)

@bp.route('/map')
@login_required
def delivery_map():
    """Live delivery map with driver locations"""
    if not current_user.can_access_manager_features():
        flash('Access denied', 'error')
        return redirect(url_for('main.index'))
    
    # Get active delivery orders with locations
    active_orders = Order.query.filter(
        Order.order_type == OrderType.DELIVERY,
        Order.status.in_([OrderStatus.CONFIRMED, OrderStatus.PREPARING, OrderStatus.READY])
    ).all()
    
    # Mock driver locations (in real app, this would come from GPS tracking)
    drivers = User.query.filter_by(role='driver').all()
    driver_locations = []
    
    for driver in drivers:
        # In real implementation, this would come from GPS API
        driver_locations.append({
            'id': driver.id,
            'name': driver.name,
            'lat': 40.7128 + (driver.id * 0.01),  # Mock coordinates
            'lng': -74.0060 + (driver.id * 0.01),
            'status': 'active' if driver.id % 2 == 0 else 'busy'
        })
    
    return render_template('delivery/map.html',
                         active_orders=active_orders,
                         driver_locations=driver_locations)

@bp.route('/drivers')
@login_required
def manage_drivers():
    """Manage delivery drivers"""
    if not current_user.can_access_manager_features():
        flash('Access denied', 'error')
        return redirect(url_for('main.index'))
    
    drivers = User.query.filter_by(role='driver').all()
    
    return render_template('delivery/drivers.html', drivers=drivers)

@bp.route('/drivers/add', methods=['GET', 'POST'])
@login_required
def add_driver():
    """Add new delivery driver"""
    if not current_user.can_access_manager_features():
        flash('Access denied', 'error')
        return redirect(url_for('delivery.manage_drivers'))
    
    if request.method == 'POST':
        driver = User()
        driver.name = request.form.get('name')
        driver.email = request.form.get('email')
        driver.phone = request.form.get('phone')
        driver.role = 'driver'
        driver.user_active = True
        
        # Set temporary password (would be emailed)
        driver.set_password('temp123')
        
        db.session.add(driver)
        db.session.commit()
        
        flash(f'Driver {driver.name} added successfully', 'success')
        return redirect(url_for('delivery.manage_drivers'))
    
    return render_template('delivery/add_driver.html')

@bp.route('/drivers/<int:driver_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_driver(driver_id):
    """Edit delivery driver"""
    if not current_user.can_access_manager_features():
        flash('Access denied', 'error')
        return redirect(url_for('delivery.manage_drivers'))
    
    driver = User.query.get_or_404(driver_id)
    
    if driver.role != 'driver':
        flash('Not a delivery driver', 'error')
        return redirect(url_for('delivery.manage_drivers'))
    
    if request.method == 'POST':
        driver.name = request.form.get('name')
        driver.email = request.form.get('email')
        driver.phone = request.form.get('phone')
        
        db.session.commit()
        flash(f'Driver {driver.name} updated successfully', 'success')
        return redirect(url_for('delivery.manage_drivers'))
    
    return render_template('delivery/edit_driver.html', driver=driver)

@bp.route('/drivers/<int:driver_id>/delete', methods=['POST'])
@login_required
def delete_driver(driver_id):
    """Delete delivery driver"""
    if not current_user.can_access_manager_features():
        flash('Access denied', 'error')
        return redirect(url_for('delivery.manage_drivers'))
    
    driver = User.query.get_or_404(driver_id)
    
    if driver.role != 'driver':
        flash('Not a delivery driver', 'error')
        return redirect(url_for('delivery.manage_drivers'))
    
    db.session.delete(driver)
    db.session.commit()
    
    flash(f'Driver {driver.name} deleted successfully', 'success')
    return redirect(url_for('delivery.manage_drivers'))

@bp.route('/optimize')
@login_required
def route_optimization():
    """Route optimization for delivery drivers"""
    if not current_user.can_access_manager_features():
        flash('Access denied', 'error')
        return redirect(url_for('main.index'))
    
    # Get pending delivery orders
    pending_orders = Order.query.filter(
        Order.order_type == OrderType.DELIVERY,
        Order.status.in_([OrderStatus.CONFIRMED, OrderStatus.PREPARING])
    ).all()
    
    # Get available drivers
    drivers = User.query.filter_by(role='driver').all()
    
    # Mock optimization algorithm (in real app, this would use Google Maps API)
    optimized_routes = []
    
    if pending_orders and drivers:
        # Simple assignment: distribute orders among available drivers
        orders_per_driver = len(pending_orders) // len(drivers) or 1
        
        for i, driver in enumerate(drivers):
            start_idx = i * orders_per_driver
            end_idx = min((i + 1) * orders_per_driver, len(pending_orders))
            
            driver_orders = pending_orders[start_idx:end_idx]
            
            if driver_orders:
                optimized_routes.append({
                    'driver': driver,
                    'orders': driver_orders,
                    'estimated_time': sum(
                        [order.estimated_preparation_time or 900 for order in driver_orders]
                    ) + (len(driver_orders) * 300),  # 5 min per delivery
                    'total_distance': len(driver_orders) * 2.5  # Mock distance in miles
                })
    
    return render_template('delivery/optimize.html',
                         pending_orders=pending_orders,
                         drivers=drivers,
                         optimized_routes=optimized_routes)

@bp.route('/tracking/<string:order_number>')
def track_delivery(order_number):
    """Public delivery tracking page"""
    order = Order.query.filter_by(order_number=order_number).first()
    
    if not order or order.order_type != OrderType.DELIVERY:
        flash('Delivery order not found', 'error')
        return redirect(url_for('main.index'))
    
    return render_template('delivery/tracking.html', order=order)

# API endpoints
@bp.route('/api/drivers')
@login_required
def api_drivers():
    """API endpoint to get drivers"""
    if not current_user.can_access_manager_features():
        return jsonify({'error': 'Access denied'}), 403
    
    drivers = User.query.filter_by(role='driver').all()
    return jsonify({
        'drivers': [{
            'id': driver.id,
            'name': driver.name,
            'email': driver.email,
            'phone': driver.phone,
            'is_active': driver.user_active
        } for driver in drivers]
    })

@bp.route('/api/orders')
@login_required
def api_delivery_orders():
    """API endpoint to get delivery orders"""
    if not current_user.can_access_manager_features():
        return jsonify({'error': 'Access denied'}), 403
    
    status_filter = request.args.get('status')
    query = Order.query.filter_by(order_type=OrderType.DELIVERY)
    
    if status_filter:
        query = query.filter_by(status=status_filter)
    
    orders = query.order_by(Order.created_at.desc()).all()
    return jsonify({
        'orders': [order.to_dict(include_items=True) for order in orders]
    })

@bp.route('/api/order/<int:order_id>/status', methods=['POST'])
@login_required
def update_order_status(order_id):
    """API endpoint to update order status"""
    if not current_user.can_access_manager_features():
        return jsonify({'error': 'Access denied'}), 403
    
    # Get JSON data from request
    if not request.is_json:
        return jsonify({'error': 'Invalid request format'}), 400
    
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    order = Order.query.get_or_404(order_id)
    
    if order.order_type != OrderType.DELIVERY:
        return jsonify({'error': 'Not a delivery order'}), 400
    
    new_status = data.get('status')
    
    if new_status in [s.value for s in OrderStatus]:
        order.status = OrderStatus(new_status)
        order.updated_at = datetime.utcnow()
        
        if new_status == OrderStatus.SERVED.value:
            order.completed_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Order status updated to {new_status}'
        })
    
    return jsonify({'error': 'Invalid status'}), 400