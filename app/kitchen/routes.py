from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app.kitchen import bp
from app.models.order import Order, OrderStatus
from app.models.kitchen_order import KitchenOrder, KitchenOrderStatus, KitchenStation, PriorityLevel, KitchenStationConfig, KitchenPerformance
from app.models.user import User
from app.models.menu import MenuItem
from app.models.recipe import Recipe
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

@bp.route('/recipes')
@login_required
def recipes():
    """View recipes for scaling"""
    if current_user.role != 'kitchen' and not current_user.can_access_manager_features():
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    # Get all recipes with their menu items
    recipes = Recipe.query.join(MenuItem).filter(MenuItem.is_available == True).all()
    
    return render_template('kitchen/recipes.html', recipes=recipes)

@bp.route('/recipe/<int:recipe_id>/scale', methods=['GET', 'POST'])
@login_required
def scale_recipe(recipe_id):
    """Scale a recipe from kitchen interface"""
    if current_user.role != 'kitchen' and not current_user.can_access_manager_features():
        return jsonify({'error': 'Access denied'}), 403
    
    recipe = Recipe.query.get_or_404(recipe_id)
    
    if request.method == 'POST':
        target_servings = request.form.get('target_servings', type=int)
        
        if not target_servings or target_servings <= 0:
            if request.headers.get('HX-Request'):
                return jsonify({'error': 'Invalid serving size'}), 400
            flash('Invalid serving size', 'error')
            return render_template('kitchen/recipe_scale.html', recipe=recipe)
        
        # Scale the recipe
        scaled_recipe = recipe.scale_to(target_servings)
        
        if request.headers.get('HX-Request'):
            return render_template('kitchen/partials/scaled_recipe.html',
                                 original_recipe=recipe,
                                 scaled_recipe=scaled_recipe,
                                 target_servings=target_servings)
        
        return render_template('kitchen/recipe_scale.html',
                             recipe=recipe,
                             scaled_recipe=scaled_recipe,
                             target_servings=target_servings)
    
    return render_template('kitchen/recipe_scale.html', recipe=recipe)

@bp.route('/api/recipe/<int:recipe_id>/scale', methods=['POST'])
@login_required
def api_scale_recipe(recipe_id):
    """API endpoint to scale a recipe"""
    if current_user.role != 'kitchen' and not current_user.can_access_manager_features():
        return jsonify({'error': 'Access denied'}), 403
    
    recipe = Recipe.query.get_or_404(recipe_id)
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Invalid JSON data'}), 400
        
        target_servings = int(data.get('target_servings', 0)) if data.get('target_servings') else 0
    except (ValueError, TypeError) as e:
        return jsonify({'error': f'Invalid serving size: {str(e)}'}), 400
    except Exception as e:
        return jsonify({'error': f'Request error: {str(e)}'}), 400
    
    if not target_servings or target_servings <= 0:
        return jsonify({'error': 'Invalid serving size'}), 400
    
    # Scale the recipe
    scaled_recipe = recipe.scale_to(target_servings)
    
    return jsonify({
        'original_recipe': recipe.to_dict(),
        'scaled_recipe': scaled_recipe,
        'target_servings': target_servings
    })

# KDS Specific Routes

@bp.route('/kds/display')
@login_required
def kds_display():
    """Main KDS display with real-time updates"""
    if current_user.role != 'kitchen' and not current_user.can_access_manager_features():
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    station_filter = request.args.get('station')
    priority_filter = request.args.get('priority')
    
    # Get kitchen orders
    query = KitchenOrder.query
    if station_filter:
        try:
            station = KitchenStation(station_filter)
            query = query.filter_by(station=station)
        except ValueError:
            pass
    
    if priority_filter:
        try:
            priority = PriorityLevel(int(priority_filter))
            query = query.filter_by(priority_level=priority)
        except ValueError:
            pass
    
    # Get active orders (not served or cancelled)
    kitchen_orders = query.filter(
        KitchenOrder.status.in_([
            KitchenOrderStatus.PENDING,
            KitchenOrderStatus.PREPARING,
            KitchenOrderStatus.READY
        ])
    ).order_by(
        KitchenOrder.priority_level.desc(),
        KitchenOrder.created_at.asc()
    ).all()
    
    # Get station configurations
    stations = KitchenStationConfig.query.filter_by(is_active=True).order_by(KitchenStationConfig.display_order).all()
    
    if request.headers.get('HX-Request'):
        return render_template('kitchen/partials/kitchen_orders.html',
                           kitchen_orders=kitchen_orders,
                           stations=stations)
    
    return render_template('kitchen/display.html',
                         kitchen_orders=kitchen_orders,
                         stations=stations,
                         station_filter=station_filter,
                         priority_filter=priority_filter)

@bp.route('/kds/orders/<int:kitchen_order_id>/update-status', methods=['POST'])
@login_required
def update_kitchen_order_status(kitchen_order_id):
    """Update kitchen order status"""
    if current_user.role != 'kitchen' and not current_user.can_access_manager_features():
        return jsonify({'error': 'Access denied'}), 403
    
    kitchen_order = KitchenOrder.query.get_or_404(kitchen_order_id)
    new_status = request.form.get('status')
    notes = request.form.get('notes', '')
    
    if not new_status:
        return jsonify({'error': 'Status is required'}), 400
    
    try:
        status = KitchenOrderStatus(new_status)
        
        if status == KitchenOrderStatus.PREPARING:
            success, message = kitchen_order.start_preparation(current_user.id)
        elif status == KitchenOrderStatus.READY:
            success, message = kitchen_order.mark_ready()
        elif status == KitchenOrderStatus.SERVED:
            success, message = kitchen_order.mark_served()
        elif status == KitchenOrderStatus.CANCELLED:
            success, message = kitchen_order.cancel(notes)
        else:
            return jsonify({'error': 'Invalid status transition'}), 400
        
        if not success:
            return jsonify({'error': message}), 400
        
        # Update notes if provided
        if notes:
            kitchen_order.notes = notes
        
        # Create performance record
        if status in [KitchenOrderStatus.READY, KitchenOrderStatus.SERVED]:
            performance = KitchenPerformance(
                kitchen_order_id=kitchen_order.id,
                station=kitchen_order.station,
                staff_id=kitchen_order.assigned_to,
                preparation_time=kitchen_order.preparation_time or 0,
                estimated_time=kitchen_order.preparation_time or 0,
                on_time=not kitchen_order.is_overdue(),
                date=datetime.now().date()
            )
            db.session.add(performance)
        
        db.session.commit()
        
        # Emit real-time updates
        from app.socketio_events import emit_kitchen_order_update
        emit_kitchen_order_update(kitchen_order)
        
        return jsonify({
            'success': True,
            'message': message,
            'kitchen_order': kitchen_order.to_dict()
        })
        
    except ValueError:
        return jsonify({'error': 'Invalid status'}), 400

@bp.route('/kds/orders/<int:kitchen_order_id>/start-preparation', methods=['POST'])
@login_required
def start_preparation(kitchen_order_id):
    """Start preparation timer for kitchen order"""
    if current_user.role != 'kitchen' and not current_user.can_access_manager_features():
        return jsonify({'error': 'Access denied'}), 403
    
    kitchen_order = KitchenOrder.query.get_or_404(kitchen_order_id)
    
    success, message = kitchen_order.start_preparation(current_user.id)
    
    if success:
        # Emit real-time updates
        from app.socketio_events import emit_kitchen_order_update
        emit_kitchen_order_update(kitchen_order)
        
        return jsonify({
            'success': True,
            'message': message,
            'kitchen_order': kitchen_order.to_dict()
        })
    
    return jsonify({'error': message}), 400

@bp.route('/kds/orders/<int:kitchen_order_id>/mark-ready', methods=['POST'])
@login_required
def mark_ready(kitchen_order_id):
    """Mark kitchen order as ready"""
    if current_user.role != 'kitchen' and not current_user.can_access_manager_features():
        return jsonify({'error': 'Access denied'}), 403
    
    kitchen_order = KitchenOrder.query.get_or_404(kitchen_order_id)
    
    success, message = kitchen_order.mark_ready()
    
    if success:
        # Create performance record
        performance = KitchenPerformance(
            kitchen_order_id=kitchen_order.id,
            station=kitchen_order.station,
            staff_id=kitchen_order.assigned_to,
            preparation_time=kitchen_order.preparation_time or 0,
            estimated_time=kitchen_order.preparation_time or 0,
            on_time=not kitchen_order.is_overdue(),
            date=datetime.now().date()
        )
        db.session.add(performance)
        db.session.commit()
        
        # Emit real-time updates
        from app.socketio_events import emit_kitchen_order_update
        emit_kitchen_order_update(kitchen_order)
        
        return jsonify({
            'success': True,
            'message': message,
            'kitchen_order': kitchen_order.to_dict()
        })
    
    return jsonify({'error': message}), 400

@bp.route('/kds/orders/<int:kitchen_order_id>/mark-served', methods=['POST'])
@login_required
def mark_served(kitchen_order_id):
    """Mark kitchen order as served"""
    if current_user.role != 'kitchen' and not current_user.can_access_manager_features():
        return jsonify({'error': 'Access denied'}), 403
    
    kitchen_order = KitchenOrder.query.get_or_404(kitchen_order_id)
    
    success, message = kitchen_order.mark_served()
    
    if success:
        # Emit real-time updates
        from app.socketio_events import emit_kitchen_order_update
        emit_kitchen_order_update(kitchen_order)
        
        return jsonify({
            'success': True,
            'message': message,
            'kitchen_order': kitchen_order.to_dict()
        })
    
    return jsonify({'error': message}), 400

@bp.route('/kds/performance')
@login_required
def performance():
    """Kitchen performance metrics"""
    if current_user.role != 'kitchen' and not current_user.can_access_manager_features():
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    # Get date range from request
    days = request.args.get('days', 7, type=int)
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days)
    
    # Get performance data
    performance_data = KitchenPerformance.query.filter(
        KitchenPerformance.date >= start_date,
        KitchenPerformance.date <= end_date
    ).all()
    
    # Calculate metrics
    total_orders = len(performance_data)
    on_time_orders = sum(1 for p in performance_data if p.on_time)
    avg_preparation_time = sum(p.preparation_time for p in performance_data) / total_orders if total_orders > 0 else 0
    
    # Group by station
    station_metrics = {}
    for performance in performance_data:
        station = performance.station.value if performance.station else 'unknown'
        if station not in station_metrics:
            station_metrics[station] = {
                'total': 0,
                'on_time': 0,
                'avg_time': 0,
                'efficiency': 0
            }
        
        station_metrics[station]['total'] += 1
        if performance.on_time:
            station_metrics[station]['on_time'] += 1
        station_metrics[station]['avg_time'] += performance.preparation_time
    
    # Calculate averages and efficiency for each station
    for station in station_metrics:
        if station_metrics[station]['total'] > 0:
            station_metrics[station]['avg_time'] //= station_metrics[station]['total']
            station_metrics[station]['efficiency'] = (station_metrics[station]['on_time'] / station_metrics[station]['total']) * 100
    
    # Get recent kitchen orders
    recent_orders = KitchenOrder.query.order_by(KitchenOrder.created_at.desc()).limit(20).all()
    
    return render_template('kitchen/performance.html',
                         performance_data=performance_data,
                         station_metrics=station_metrics,
                         total_orders=total_orders,
                         on_time_orders=on_time_orders,
                         avg_preparation_time=avg_preparation_time,
                         on_time_percentage=(on_time_orders / total_orders * 100) if total_orders > 0 else 0,
                         recent_orders=recent_orders,
                         days=days)

@bp.route('/kds/station/<station>')
@login_required
def station_view(station):
    """Station-specific view"""
    if current_user.role != 'kitchen' and not current_user.can_access_manager_features():
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    try:
        station_enum = KitchenStation(station)
    except ValueError:
        flash('Invalid station', 'error')
        return redirect(url_for('kitchen.kds_display'))
    
    # Get station configuration
    station_config = KitchenStationConfig.query.filter_by(station=station_enum).first()
    
    # Get orders for this station
    kitchen_orders = KitchenOrder.query.filter_by(station=station_enum).filter(
        KitchenOrder.status.in_([
            KitchenOrderStatus.PENDING,
            KitchenOrderStatus.PREPARING,
            KitchenOrderStatus.READY
        ])
    ).order_by(
        KitchenOrder.priority_level.desc(),
        KitchenOrder.created_at.asc()
    ).all()
    
    # Get station performance
    today = datetime.now().date()
    station_performance = KitchenPerformance.query.filter(
        KitchenPerformance.station == station_enum,
        KitchenPerformance.date == today
    ).all()
    
    return render_template('kitchen/station_view.html',
                         station=station_enum,
                         station_config=station_config,
                         kitchen_orders=kitchen_orders,
                         station_performance=station_performance)

@bp.route('/kds/api/orders')
@login_required
def api_kitchen_orders():
    """API endpoint to get kitchen orders"""
    if current_user.role != 'kitchen' and not current_user.can_access_manager_features():
        return jsonify({'error': 'Access denied'}), 403
    
    station_filter = request.args.get('station')
    status_filter = request.args.get('status')
    
    query = KitchenOrder.query
    
    if station_filter:
        try:
            station = KitchenStation(station_filter)
            query = query.filter_by(station=station)
        except ValueError:
            pass
    
    if status_filter:
        try:
            status = KitchenOrderStatus(status_filter)
            query = query.filter_by(status=status)
        except ValueError:
            pass
    
    kitchen_orders = query.order_by(
        KitchenOrder.priority_level.desc(),
        KitchenOrder.created_at.asc()
    ).all()
    
    return jsonify([order.to_dict() for order in kitchen_orders])

@bp.route('/kds/api/order/<int:kitchen_order_id>')
@login_required
def api_kitchen_order(kitchen_order_id):
    """API endpoint to get specific kitchen order"""
    if current_user.role != 'kitchen' and not current_user.can_access_manager_features():
        return jsonify({'error': 'Access denied'}), 403
    
    kitchen_order = KitchenOrder.query.get_or_404(kitchen_order_id)
    return jsonify(kitchen_order.to_dict())

@bp.route('/kds/api/stations')
@login_required
def api_stations():
    """API endpoint to get kitchen stations"""
    if current_user.role != 'kitchen' and not current_user.can_access_manager_features():
        return jsonify({'error': 'Access denied'}), 403
    
    stations = KitchenStationConfig.query.filter_by(is_active=True).order_by(KitchenStationConfig.display_order).all()
    return jsonify([station.to_dict() for station in stations])

@bp.route('/kds/api/stats')
@login_required
def api_kitchen_stats():
    """API endpoint to get kitchen statistics"""
    if current_user.role != 'kitchen' and not current_user.can_access_manager_features():
        return jsonify({'error': 'Access denied'}), 403
    
    today = datetime.now().date()
    
    stats = {
        'pending_orders': KitchenOrder.query.filter_by(status=KitchenOrderStatus.PENDING).count(),
        'preparing_orders': KitchenOrder.query.filter_by(status=KitchenOrderStatus.PREPARING).count(),
        'ready_orders': KitchenOrder.query.filter_by(status=KitchenOrderStatus.READY).count(),
        'completed_today': KitchenPerformance.query.filter_by(date=today).count(),
        'overdue_orders': sum(1 for order in KitchenOrder.query.filter(
            KitchenOrder.status.in_([KitchenOrderStatus.PENDING, KitchenOrderStatus.PREPARING])
        ).all() if order.is_overdue()),
        'stations': {}
    }
    
    # Get stats by station
    stations = KitchenStationConfig.query.filter_by(is_active=True).all()
    for station_config in stations:
        station_orders = KitchenOrder.query.filter_by(station=station_config.station).filter(
            KitchenOrder.status.in_([KitchenOrderStatus.PENDING, KitchenOrderStatus.PREPARING, KitchenOrderStatus.READY])
        ).count()
        stats['stations'][station_config.station.value] = station_orders
    
    return jsonify(stats)

# Kitchen Station Management Routes

@bp.route('/stations/manage')
@login_required
def manage_stations():
    """Manage kitchen stations"""
    if not current_user.can_access_manager_features():
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    stations = KitchenStationConfig.query.order_by(KitchenStationConfig.display_order).all()
    
    return render_template('kitchen/manage_stations.html', stations=stations)

@bp.route('/stations/create', methods=['GET', 'POST'])
@login_required
def create_station():
    """Create new kitchen station"""
    if not current_user.can_access_manager_features():
        return jsonify({'error': 'Access denied'}), 403
    
    if request.method == 'POST':
        try:
            data = request.get_json()
            
            station_config = KitchenStationConfig(
                station=KitchenStation(data['station']),
                name=data['name'],
                description=data.get('description', ''),
                display_order=data.get('display_order', 0),
                is_active=data.get('is_active', True),
                color_code=data.get('color_code', '#007bff'),
                default_preparation_time=data.get('default_preparation_time', 600),
                max_concurrent_items=data.get('max_concurrent_items', 10),
                notification_sound=data.get('notification_sound', 'default')
            )
            
            db.session.add(station_config)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Station created successfully',
                'station': station_config.to_dict()
            })
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 400
    
    return render_template('kitchen/station_form.html', action='create')

@bp.route('/stations/<int:station_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_station(station_id):
    """Edit kitchen station"""
    if not current_user.can_access_manager_features():
        return jsonify({'error': 'Access denied'}), 403
    
    station_config = KitchenStationConfig.query.get_or_404(station_id)
    
    if request.method == 'POST':
        try:
            data = request.get_json()
            
            station_config.name = data['name']
            station_config.description = data.get('description', '')
            station_config.display_order = data.get('display_order', 0)
            station_config.is_active = data.get('is_active', True)
            station_config.color_code = data.get('color_code', '#007bff')
            station_config.default_preparation_time = data.get('default_preparation_time', 600)
            station_config.max_concurrent_items = data.get('max_concurrent_items', 10)
            station_config.notification_sound = data.get('notification_sound', 'default')
            
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Station updated successfully',
                'station': station_config.to_dict()
            })
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 400
    
    return render_template('kitchen/station_form.html',
                         action='edit',
                         station=station_config)

@bp.route('/stations/<int:station_id>/delete', methods=['POST'])
@login_required
def delete_station(station_id):
    """Delete kitchen station"""
    if not current_user.can_access_manager_features():
        return jsonify({'error': 'Access denied'}), 403
    
    station_config = KitchenStationConfig.query.get_or_404(station_id)
    
    try:
        # Check if there are active orders for this station
        active_orders = KitchenOrder.query.filter_by(station=station_config.station).filter(
            KitchenOrder.status.in_([KitchenOrderStatus.PENDING, KitchenOrderStatus.PREPARING, KitchenOrderStatus.READY])
        ).count()
        
        if active_orders > 0:
            return jsonify({
                'error': 'Cannot delete station with active orders',
                'active_orders': active_orders
            }), 400
        
        db.session.delete(station_config)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Station deleted successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@bp.route('/stations/<int:station_id>/toggle-status', methods=['POST'])
@login_required
def toggle_station_status(station_id):
    """Toggle station active status"""
    if not current_user.can_access_manager_features():
        return jsonify({'error': 'Access denied'}), 403
    
    station_config = KitchenStationConfig.query.get_or_404(station_id)
    
    try:
        station_config.is_active = not station_config.is_active
        db.session.commit()
        
        status = 'activated' if station_config.is_active else 'deactivated'
        
        return jsonify({
            'success': True,
            'message': f'Station {status} successfully',
            'is_active': station_config.is_active
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@bp.route('/stations/api/config')
@login_required
def api_station_config():
    """API endpoint to get station configurations"""
    if not current_user.can_access_manager_features():
        return jsonify({'error': 'Access denied'}), 403
    
    stations = KitchenStationConfig.query.order_by(KitchenStationConfig.display_order).all()
    return jsonify([station.to_dict() for station in stations])

@bp.route('/stations/api/<station_id>/config')
@login_required
def api_station_config_detail(station_id):
    """API endpoint to get specific station configuration"""
    if not current_user.can_access_manager_features():
        return jsonify({'error': 'Access denied'}), 403
    
    station_config = KitchenStationConfig.query.get_or_404(station_id)
    return jsonify(station_config.to_dict())

@bp.route('/stations/auto-assign', methods=['POST'])
@login_required
def auto_assign_orders():
    """Auto-assign orders to stations based on menu items"""
    if not current_user.can_access_manager_features():
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        # Get pending orders without station assignment
        pending_orders = KitchenOrder.query.filter_by(status=KitchenOrderStatus.PENDING).filter(
            KitchenOrder.station == None
        ).all()
        
        assigned_count = 0
        for kitchen_order in pending_orders:
            # Station is already determined by the model's determine_station method
            if kitchen_order.station:
                assigned_count += 1
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Auto-assigned {assigned_count} orders to stations',
            'assigned_count': assigned_count
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@bp.route('/stations/workload')
@login_required
def station_workload():
    """View current station workload"""
    if current_user.role != 'kitchen' and not current_user.can_access_manager_features():
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    # Get all active stations
    stations = KitchenStationConfig.query.filter_by(is_active=True).order_by(KitchenStationConfig.display_order).all()
    
    workload_data = {}
    for station_config in stations:
        # Count active orders for this station
        active_orders = KitchenOrder.query.filter_by(station=station_config.station).filter(
            KitchenOrder.status.in_([
                KitchenOrderStatus.PENDING,
                KitchenOrderStatus.PREPARING,
                KitchenOrderStatus.READY
            ])
        ).all()
        
        # Calculate workload metrics
        workload_data = {
            'station_config': station_config,
            'active_orders': len(active_orders),
            'pending_count': len([o for o in active_orders if o.status.value == 'pending']),
            'preparing_count': len([o for o in active_orders if o.status.value == 'preparing']),
            'ready_count': len([o for o in active_orders if o.status.value == 'ready']),
            'overdue_count': len([o for o in active_orders if o.is_overdue()]),
            'workload_percentage': (len(active_orders) / station_config.max_concurrent_items * 100) if station_config.max_concurrent_items > 0 else 0,
            'orders': active_orders
        }
        
        workload_data[station_config.station.value] = workload_data
    
    return render_template('kitchen/station_workload.html', workload_data=workload_data)