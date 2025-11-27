from flask_socketio import emit, join_room, leave_room
from flask_login import current_user
from app import socketio
from app.models.order import Order, OrderStatus
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

def emit_order_status_update(order, old_status=None):
    """Emit order status update to relevant rooms"""
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

def emit_kitchen_stats():
    """Emit current kitchen statistics"""
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

def emit_kitchen_ticket_update(order):
    """Emit kitchen ticket update"""
    order_data = order.to_dict(include_items=True)
    
    socketio.emit('kitchen_ticket', {
        'order': order_data,
        'timestamp': datetime.utcnow().isoformat(),
        'action': 'update',
        'message': f'Kitchen ticket updated for order {order.order_number}'
    }, to=KITCHEN_ROOM)
    
    print(f"Emitted kitchen ticket update for {order.order_number}")

def emit_order_assigned(order, station=None):
    """Emit order assignment to kitchen station"""
    order_data = order.to_dict(include_items=True)
    
    socketio.emit('order_assigned', {
        'order': order_data,
        'station': station,
        'timestamp': datetime.utcnow().isoformat(),
        'message': f'Order {order.order_number} assigned to {station or "kitchen"}'
    }, to=KITCHEN_ROOM)
    
    print(f"Emitted order assignment for {order.order_number} to {station}")

def emit_timer_update(order, action):
    """Emit timer update events"""
    order_data = order.to_dict(include_items=True)
    
    socketio.emit('timer_update', {
        'order': order_data,
        'action': action,
        'timestamp': datetime.utcnow().isoformat(),
        'message': f'Timer {action} for order {order.order_number}'
    }, to=KITCHEN_ROOM)
    
    print(f"Emitted timer update for {order.order_number}: {action}")

def emit_timer_completed(order):
    """Emit timer completion event"""
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

# Kitchen-specific event handlers
@socketio.on('request_kitchen_orders')
def handle_request_kitchen_orders():
    """Handle request for current kitchen orders"""
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

@socketio.on('kitchen_heartbeat')
def handle_kitchen_heartbeat():
    """Handle kitchen heartbeat for connection monitoring"""
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