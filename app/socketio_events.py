from flask_socketio import emit, join_room, leave_room
from flask_login import current_user
from app import socketio
from app.models.order import Order, OrderStatus
from app.models.kitchen_order import KitchenOrder, KitchenOrderStatus, KitchenStation, KitchenPerformance
from app.models.user import User
from app import db
from datetime import datetime

# Room constants
KITCHEN_ROOM = 'kitchen'
MANAGER_ROOM = 'managers'

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    if current_user.is_authenticated:
        # Join role-based rooms
        if current_user.role == 'kitchen':
            join_room(KITCHEN_ROOM)
            emit('status', {'msg': f'Connected to kitchen updates as {current_user.name}'})
        
        if current_user.can_access_manager_features():
            join_room(MANAGER_ROOM)
            emit('status', {'msg': f'Connected to manager updates as {current_user.name}'})
        
        # Join user-specific room
        join_room(f'user_{current_user.id}')
        
        print(f"User {current_user.name} connected with role {current_user.role}")
    else:
        emit('status', {'msg': 'Connected anonymously'})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    if current_user.is_authenticated:
        print(f"User {current_user.name} disconnected")

@socketio.on('join_kitchen')
def handle_join_kitchen():
    """Allow user to join kitchen room"""
    if current_user.is_authenticated and (current_user.role == 'kitchen' or current_user.can_access_manager_features()):
        join_room(KITCHEN_ROOM)
        emit('status', {'msg': 'Joined kitchen room'})
        
        # Send current kitchen stats
        emit_kitchen_stats()
    else:
        emit('error', {'msg': 'Access denied to kitchen room'})

@socketio.on('leave_kitchen')
def handle_leave_kitchen():
    """Allow user to leave kitchen room"""
    if current_user.is_authenticated:
        leave_room(KITCHEN_ROOM)
        emit('status', {'msg': 'Left kitchen room'})

def emit_new_order(order):
    """Emit new order notification to kitchen"""
    try:
        order_data = order.to_dict(include_items=True)
        
        # Send to kitchen room
        socketio.emit('new_order', {
            'order': order_data,
            'timestamp': datetime.utcnow().isoformat(),
            'message': f'New order {order.order_number} received'
        }, to=KITCHEN_ROOM)
        
        # Send to managers
        socketio.emit('new_order', {
            'order': order_data,
            'timestamp': datetime.utcnow().isoformat(),
            'message': f'New order {order.order_number} received'
        }, to=MANAGER_ROOM)
        
        print(f"Emitted new order {order.order_number} to kitchen")
    except Exception as e:
        print(f"Error emitting new order notification: {str(e)}")

def emit_order_status_update(order, old_status=None):
    """Emit order status update to relevant rooms"""
    try:
        order_data = order.to_dict(include_items=True)
        
        # Prepare update data
        update_data = {
            'order': order_data,
            'old_status': old_status.value if old_status else None,
            'new_status': order.status.value,
            'timestamp': datetime.utcnow().isoformat(),
            'message': f'Order {order.order_number} status updated to {order.status.value}'
        }
        
        # Send to kitchen room
        socketio.emit('order_status_update', update_data, to=KITCHEN_ROOM)
        
        # Send to managers
        socketio.emit('order_status_update', update_data, to=MANAGER_ROOM)
        
        # Send to the user who created the order
        if order.user_id:
            socketio.emit('order_status_update', update_data, to=f'user_{order.user_id}')
        
        print(f"Emitted order status update for {order.order_number}: {old_status} -> {order.status.value}")
    except Exception as e:
        print(f"Error emitting order status update: {str(e)}")

def emit_kitchen_stats():
    """Emit current kitchen statistics"""
    try:
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
            'timestamp': datetime.utcnow().isoformat()
        }
        
        socketio.emit('kitchen_stats', stats, to=KITCHEN_ROOM)
        socketio.emit('kitchen_stats', stats, to=MANAGER_ROOM)
    except Exception as e:
        print(f"Error emitting kitchen stats: {str(e)}")

def emit_kitchen_ticket_update(order):
    """Emit kitchen ticket update"""
    try:
        order_data = order.to_dict(include_items=True)
        
        socketio.emit('kitchen_ticket', {
            'order': order_data,
            'timestamp': datetime.utcnow().isoformat(),
            'action': 'update',
            'message': f'Kitchen ticket updated for order {order.order_number}'
        }, to=KITCHEN_ROOM)
        
        print(f"Emitted kitchen ticket update for {order.order_number}")
    except Exception as e:
        print(f"Error emitting kitchen ticket update: {str(e)}")

def emit_order_assigned(order, station=None):
    """Emit order assignment to kitchen station"""
    try:
        order_data = order.to_dict(include_items=True)
        
        socketio.emit('order_assigned', {
            'order': order_data,
            'station': station,
            'timestamp': datetime.utcnow().isoformat(),
            'message': f'Order {order.order_number} assigned to {station or "kitchen"}'
        }, to=KITCHEN_ROOM)
        
        print(f"Emitted order assignment for {order.order_number} to {station}")
    except Exception as e:
        print(f"Error emitting order assignment: {str(e)}")

def emit_timer_update(order, action):
    """Emit timer update events"""
    try:
        order_data = order.to_dict(include_items=True)
        
        socketio.emit('timer_update', {
            'order': order_data,
            'action': action,
            'timestamp': datetime.utcnow().isoformat(),
            'message': f'Timer {action} for order {order.order_number}'
        }, to=KITCHEN_ROOM)
        
        print(f"Emitted timer update for {order.order_number}: {action}")
    except Exception as e:
        print(f"Error emitting timer update: {str(e)}")

def emit_timer_completed(order):
    """Emit timer completion event"""
    try:
        order_data = order.to_dict(include_items=True)
        
        socketio.emit('timer_completed', {
            'order': order_data,
            'timestamp': datetime.utcnow().isoformat(),
            'message': f'Preparation completed for order {order.order_number}'
        }, to=KITCHEN_ROOM)
        
        # Also send to managers
        socketio.emit('timer_completed', {
            'order': order_data,
            'timestamp': datetime.utcnow().isoformat(),
            'message': f'Preparation completed for order {order.order_number}'
        }, to=MANAGER_ROOM)
        
        print(f"Emitted timer completion for {order.order_number}")
    except Exception as e:
        print(f"Error emitting timer completion: {str(e)}")

# Kitchen-specific event handlers
@socketio.on('request_legacy_orders')
def handle_request_legacy_orders():
    """Handle request for current kitchen orders (legacy)"""
    if current_user.is_authenticated and (current_user.role == 'kitchen' or current_user.can_access_manager_features()):
        # Get active orders
        orders = Order.query.filter(
            Order.status.in_([OrderStatus.PENDING, OrderStatus.CONFIRMED, OrderStatus.PREPARING, OrderStatus.READY])
        ).order_by(Order.created_at.asc()).all()
        
        orders_data = [order.to_dict(include_items=True) for order in orders]
        
        emit('kitchen_orders', {
            'orders': orders_data,
            'timestamp': datetime.utcnow().isoformat()
        })
    else:
        emit('error', {'msg': 'Access denied'})

@socketio.on('request_order_details')
def handle_request_order_details(data):
    """Handle request for specific order details"""
    if current_user.is_authenticated:
        order_id = data.get('order_id')
        if order_id:
            order = Order.query.get(order_id)
            if order:
                # Check if user has permission to view this order
                if (current_user.role == 'kitchen' or 
                    current_user.can_access_manager_features() or
                    order.user_id == current_user.id):
                    
                    emit('order_details', {
                        'order': order.to_dict(include_items=True, include_payments=True),
                        'timestamp': datetime.utcnow().isoformat()
                    })
                else:
                    emit('error', {'msg': 'Access denied to this order'})
            else:
                emit('error', {'msg': 'Order not found'})
        else:
            emit('error', {'msg': 'Order ID required'})

@socketio.on('legacy_kitchen_heartbeat')
def handle_legacy_kitchen_heartbeat():
    """Handle kitchen heartbeat for connection monitoring (legacy)"""
    if current_user.is_authenticated and (current_user.role == 'kitchen' or current_user.can_access_manager_features()):
        emit('kitchen_heartbeat_response', {
            'timestamp': datetime.utcnow().isoformat(),
            'user_id': current_user.id,
            'user_name': current_user.name
        })

@socketio.on('timer_start')
def handle_timer_start(data):
    """Handle timer start event"""
    if current_user.is_authenticated and (current_user.role == 'kitchen' or current_user.can_access_manager_features()):
        order_id = data.get('order_id')
        if order_id:
            order = Order.query.get(order_id)
            if order:
                order.timer_started_at = datetime.utcnow()
                order.status = OrderStatus.PREPARING
                db.session.commit()
                
                emit_timer_update(order, 'started')
                emit_kitchen_stats()
            else:
                emit('error', {'msg': 'Order not found'})
        else:
            emit('error', {'msg': 'Order ID required'})
    else:
        emit('error', {'msg': 'Access denied'})

@socketio.on('timer_adjust')
def handle_timer_adjust(data):
    """Handle timer adjustment event"""
    if current_user.is_authenticated and (current_user.role == 'kitchen' or current_user.can_access_manager_features()):
        order_id = data.get('order_id')
        adjustment = data.get('adjustment')
        
        if order_id and adjustment is not None:
            order = Order.query.get(order_id)
            if order:
                if order.estimated_preparation_time:
                    order.estimated_preparation_time = max(60, order.estimated_preparation_time + adjustment)
                    db.session.commit()
                    
                    emit_timer_update(order, f'adjusted by {adjustment}s')
                else:
                    emit('error', {'msg': 'No timer to adjust'})
            else:
                emit('error', {'msg': 'Order not found'})
        else:
            emit('error', {'msg': 'Order ID and adjustment required'})
    else:
        emit('error', {'msg': 'Access denied'})

@socketio.on('timer_complete')
def handle_timer_complete(data):
    """Handle timer completion event"""
    if current_user.is_authenticated and (current_user.role == 'kitchen' or current_user.can_access_manager_features()):
        order_id = data.get('order_id')
        if order_id:
            order = Order.query.get(order_id)
            if order:
                if order.timer_started_at and not order.timer_completed_at:
                    order.timer_completed_at = datetime.utcnow()
                    order.status = OrderStatus.READY
                    
                    # Calculate actual preparation time
                    time_diff = order.timer_completed_at - order.timer_started_at
                    order.actual_preparation_time = int(time_diff.total_seconds())
                    
                    db.session.commit()
                    
                    emit_timer_completed(order)
                    emit_kitchen_stats()
                else:
                    emit('error', {'msg': 'Timer not running or already completed'})
            else:
                emit('error', {'msg': 'Order not found'})
        else:
            emit('error', {'msg': 'Order ID required'})
    else:
        emit('error', {'msg': 'Access denied'})

# KDS-Specific Events

def emit_kitchen_order_update(kitchen_order):
    """Emit kitchen order status update to relevant rooms"""
    try:
        kitchen_order_data = kitchen_order.to_dict()
        
        # Prepare update data
        update_data = {
            'kitchen_order': kitchen_order_data,
            'timestamp': datetime.utcnow().isoformat(),
            'message': f'Kitchen order {kitchen_order.id} status updated to {kitchen_order.status.value}'
        }
        
        # Send to kitchen room
        socketio.emit('kitchen_order_update', update_data, to=KITCHEN_ROOM)
        
        # Send to managers
        socketio.emit('kitchen_order_update', update_data, to=MANAGER_ROOM)
        
        # Send to station-specific room if applicable
        if kitchen_order.station:
            socketio.emit('kitchen_order_update', update_data, to=f'station_{kitchen_order.station.value}')
        
        print(f"Emitted kitchen order update for {kitchen_order.id}: {kitchen_order.status.value}")
    except Exception as e:
        print(f"Error emitting kitchen order update: {str(e)}")

def emit_new_kitchen_order(kitchen_order):
    """Emit new kitchen order notification"""
    try:
        kitchen_order_data = kitchen_order.to_dict()
        
        # Send to kitchen room
        socketio.emit('new_kitchen_order', {
            'kitchen_order': kitchen_order_data,
            'timestamp': datetime.utcnow().isoformat(),
            'message': f'New kitchen order {kitchen_order.id} for {kitchen_order.station.value}'
        }, to=KITCHEN_ROOM)
        
        # Send to station-specific room
        if kitchen_order.station:
            socketio.emit('new_kitchen_order', {
                'kitchen_order': kitchen_order_data,
                'timestamp': datetime.utcnow().isoformat(),
                'message': f'New order for {kitchen_order.station.value}'
            }, to=f'station_{kitchen_order.station.value}')
        
        # Send to managers
        socketio.emit('new_kitchen_order', {
            'kitchen_order': kitchen_order_data,
            'timestamp': datetime.utcnow().isoformat(),
            'message': f'New kitchen order {kitchen_order.id}'
        }, to=MANAGER_ROOM)
        
        print(f"Emitted new kitchen order {kitchen_order.id} to kitchen")
    except Exception as e:
        print(f"Error emitting new kitchen order notification: {str(e)}")

def emit_kitchen_station_stats():
    """Emit kitchen station statistics"""
    try:
        today = datetime.now().date()
        
        # Get all active stations
        from app.models.kitchen_order import KitchenStation
        stations = [station for station in KitchenStation]
        
        station_stats = {}
        for station in stations:
            # Count active orders for this station
            active_orders = KitchenOrder.query.filter(
                KitchenOrder.station == station,
                KitchenOrder.status.in_([KitchenOrderStatus.PENDING, KitchenOrderStatus.PREPARING, KitchenOrderStatus.READY])
            ).count()
            
            station_stats[station.value] = {
                'active_orders': active_orders,
                'station_name': station.value.title()
            }
        
        stats_data = {
            'station_stats': station_stats,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        socketio.emit('kitchen_station_stats', stats_data, to=KITCHEN_ROOM)
        socketio.emit('kitchen_station_stats', stats_data, to=MANAGER_ROOM)
        
    except Exception as e:
        print(f"Error emitting kitchen station stats: {str(e)}")

def emit_performance_update(performance_record):
    """Emit performance update notification"""
    try:
        performance_data = performance_record.to_dict()
        
        socketio.emit('performance_update', {
            'performance': performance_data,
            'timestamp': datetime.utcnow().isoformat(),
            'message': f'New performance record for {performance_record.station.value if performance_record.station else "unknown"}'
        }, to=MANAGER_ROOM)
        
        print(f"Emitted performance update for {performance_record.id}")
    except Exception as e:
        print(f"Error emitting performance update: {str(e)}")

def emit_order_alert(kitchen_order, alert_type, message):
    """Emit order alert for priority or overdue items"""
    try:
        alert_data = {
            'kitchen_order': kitchen_order.to_dict(),
            'alert_type': alert_type,
            'message': message,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Send to kitchen room
        socketio.emit('order_alert', alert_data, to=KITCHEN_ROOM)
        
        # Send to station-specific room
        if kitchen_order.station:
            socketio.emit('order_alert', alert_data, to=f'station_{kitchen_order.station.value}')
        
        # Send to managers for urgent alerts
        if alert_type in ['urgent', 'overdue']:
            socketio.emit('order_alert', alert_data, to=MANAGER_ROOM)
        
        print(f"Emitted order alert: {alert_type} - {message}")
    except Exception as e:
        print(f"Error emitting order alert: {str(e)}")

# KDS Event Handlers

@socketio.on('join_station')
def handle_join_station(data):
    """Allow user to join station-specific room"""
    if current_user.is_authenticated and (current_user.role == 'kitchen' or current_user.can_access_manager_features()):
        station = data.get('station')
        if station:
            room_name = f'station_{station}'
            join_room(room_name)
            emit('status', {'msg': f'Joined {station} station room'})
        else:
            emit('error', {'msg': 'Station name required'})
    else:
        emit('error', {'msg': 'Access denied to station room'})

@socketio.on('leave_station')
def handle_leave_station(data):
    """Allow user to leave station-specific room"""
    if current_user.is_authenticated:
        station = data.get('station')
        if station:
            room_name = f'station_{station}'
            leave_room(room_name)
            emit('status', {'msg': f'Left {station} station room'})

@socketio.on('request_kitchen_orders')
def handle_request_kitchen_orders():
    """Handle request for current kitchen orders"""
    if current_user.is_authenticated and (current_user.role == 'kitchen' or current_user.can_access_manager_features()):
        try:
            # Get active kitchen orders
            kitchen_orders = KitchenOrder.query.filter(
                KitchenOrder.status.in_([KitchenOrderStatus.PENDING, KitchenOrderStatus.PREPARING, KitchenOrderStatus.READY])
            ).order_by(
                KitchenOrder.priority_level.desc(),
                KitchenOrder.created_at.asc()
            ).all()
            
            orders_data = [order.to_dict() for order in kitchen_orders]
            
            emit('kitchen_orders', {
                'orders': orders_data,
                'timestamp': datetime.utcnow().isoformat()
            })
        except Exception as e:
            emit('error', {'msg': f'Error loading orders: {str(e)}'})
    else:
        emit('error', {'msg': 'Access denied'})

@socketio.on('request_station_orders')
def handle_request_station_orders(data):
    """Handle request for station-specific orders"""
    if current_user.is_authenticated and (current_user.role == 'kitchen' or current_user.can_access_manager_features()):
        station = data.get('station')
        if station:
            try:
                station_enum = KitchenStation(station)
                kitchen_orders = KitchenOrder.query.filter_by(station=station_enum).filter(
                    KitchenOrder.status.in_([KitchenOrderStatus.PENDING, KitchenOrderStatus.PREPARING, KitchenOrderStatus.READY])
                ).order_by(
                    KitchenOrder.priority_level.desc(),
                    KitchenOrder.created_at.asc()
                ).all()
                
                orders_data = [order.to_dict() for order in kitchen_orders]
                
                emit('station_orders', {
                    'station': station,
                    'orders': orders_data,
                    'timestamp': datetime.utcnow().isoformat()
                })
            except ValueError:
                emit('error', {'msg': 'Invalid station'})
        else:
            emit('error', {'msg': 'Station required'})
    else:
        emit('error', {'msg': 'Access denied'})

@socketio.on('kds_heartbeat')
def handle_kds_heartbeat():
    """Handle kitchen heartbeat for connection monitoring"""
    if current_user.is_authenticated and (current_user.role == 'kitchen' or current_user.can_access_manager_features()):
        emit('kitchen_heartbeat_response', {
            'timestamp': datetime.utcnow().isoformat(),
            'user_id': current_user.id,
            'user_name': current_user.name,
            'role': current_user.role
        })

@socketio.on('request_kitchen_stats')
def handle_request_kitchen_stats():
    """Handle request for kitchen statistics"""
    if current_user.is_authenticated and (current_user.role == 'kitchen' or current_user.can_access_manager_features()):
        try:
            today = datetime.now().date()
            
            stats = {
                'pending_orders': KitchenOrder.query.filter_by(status=KitchenOrderStatus.PENDING).count(),
                'preparing_orders': KitchenOrder.query.filter_by(status=KitchenOrderStatus.PREPARING).count(),
                'ready_orders': KitchenOrder.query.filter_by(status=KitchenOrderStatus.READY).count(),
                'completed_today': KitchenPerformance.query.filter_by(date=today).count(),
                'overdue_orders': sum(1 for order in KitchenOrder.query.filter(
                    KitchenOrder.status.in_([KitchenOrderStatus.PENDING, KitchenOrderStatus.PREPARING])
                ).all() if order.is_overdue()),
                'timestamp': datetime.utcnow().isoformat()
            }
            
            emit('kitchen_stats', stats)
        except Exception as e:
            emit('error', {'msg': f'Error loading stats: {str(e)}'})
    else:
        emit('error', {'msg': 'Access denied'})