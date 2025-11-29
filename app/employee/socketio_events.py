from flask_socketio import emit, join_room, leave_room
from flask_login import current_user
from app import socketio
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

@socketio.on('join_employee_room')
def on_join_employee_room(data):
    """Join employee management room for real-time updates"""
    try:
        if current_user.is_authenticated:
            room = data.get('room')
            if room:
                join_room(room)
                logger.info(f"User {current_user.id} joined room: {room}")
                emit('room_joined', {
                    'message': f'Joined {room} successfully',
                    'user_id': current_user.id
                }, to=room)
    except Exception as e:
        logger.error(f"Error joining room: {str(e)}")
        emit('error', {'message': 'Failed to join room'})

@socketio.on('leave_employee_room')
def on_leave_employee_room(data):
    """Leave employee management room"""
    try:
        if current_user.is_authenticated:
            room = data.get('room')
            if room:
                leave_room(room)
                logger.info(f"User {current_user.id} left room: {room}")
                emit('room_left', {
                    'message': f'Left {room} successfully',
                    'user_id': current_user.id
                }, to=room)
    except Exception as e:
        logger.error(f"Error leaving room: {str(e)}")
        emit('error', {'message': 'Failed to leave room'})

@socketio.on('request_attendance_update')
def on_request_attendance_update(data):
    """Request real-time attendance updates"""
    try:
        if current_user.is_authenticated and current_user.can_access_manager_features():
            restaurant_id = data.get('restaurant_id')
            if restaurant_id:
                # Broadcast attendance update request to restaurant room
                emit('attendance_update_requested', {
                    'requested_by': current_user.id,
                    'requested_by_name': current_user.name,
                    'restaurant_id': restaurant_id,
                    'timestamp': datetime.utcnow().isoformat()
                }, to=f"restaurant_{restaurant_id}")
    except Exception as e:
        logger.error(f"Error requesting attendance update: {str(e)}")
        emit('error', {'message': 'Failed to request attendance update'})

@socketio.on('request_shift_update')
def on_request_shift_update(data):
    """Request real-time shift updates"""
    try:
        if current_user.is_authenticated and current_user.can_access_manager_features():
            restaurant_id = data.get('restaurant_id')
            if restaurant_id:
                # Broadcast shift update request to restaurant room
                emit('shift_update_requested', {
                    'requested_by': current_user.id,
                    'requested_by_name': current_user.name,
                    'restaurant_id': restaurant_id,
                    'timestamp': datetime.utcnow().isoformat()
                }, to=f"restaurant_{restaurant_id}")
    except Exception as e:
        logger.error(f"Error requesting shift update: {str(e)}")
        emit('error', {'message': 'Failed to request shift update'})

@socketio.on('notify_shift_change')
def on_notify_shift_change(data):
    """Notify about shift changes"""
    try:
        if current_user.is_authenticated and current_user.can_access_manager_features():
            restaurant_id = data.get('restaurant_id')
            user_id = data.get('user_id')
            change_type = data.get('change_type')  # 'created', 'updated', 'deleted', 'moved'
            shift_data = data.get('shift_data', {})
            
            if restaurant_id:
                # Send notification to specific user if user_id is provided
                if user_id:
                    emit('shift_notification', {
                        'type': change_type,
                        'message': f'Your shift has been {change_type}',
                        'shift_data': shift_data,
                        'timestamp': datetime.utcnow().isoformat()
                    }, to=f"user_{user_id}")
                
                # Send general notification to restaurant room
                emit('shift_updated', {
                    'type': change_type,
                    'shift_data': shift_data,
                    'updated_by': current_user.name,
                    'timestamp': datetime.utcnow().isoformat()
                }, to=f"restaurant_{restaurant_id}")
    except Exception as e:
        logger.error(f"Error notifying shift change: {str(e)}")
        emit('error', {'message': 'Failed to notify shift change'})

@socketio.on('notify_leave_status')
def on_notify_leave_status(data):
    """Notify about leave request status changes"""
    try:
        if current_user.is_authenticated and current_user.can_access_manager_features():
            restaurant_id = data.get('restaurant_id')
            user_id = data.get('user_id')
            leave_data = data.get('leave_data', {})
            status = data.get('status')  # 'approved', 'rejected', 'cancelled'
            
            if restaurant_id and user_id:
                # Send notification to specific user
                emit('leave_notification', {
                    'type': 'status_change',
                    'status': status,
                    'message': f'Your leave request has been {status}',
                    'leave_data': leave_data,
                    'approved_by': current_user.name if status == 'approved' else None,
                    'timestamp': datetime.utcnow().isoformat()
                }, to=f"user_{user_id}")
                
                # Send general notification to restaurant room for managers
                emit('leave_updated', {
                    'type': 'status_change',
                    'status': status,
                    'leave_data': leave_data,
                    'updated_by': current_user.name,
                    'timestamp': datetime.utcnow().isoformat()
                }, to=f"restaurant_{restaurant_id}")
    except Exception as e:
        logger.error(f"Error notifying leave status: {str(e)}")
        emit('error', {'message': 'Failed to notify leave status'})

@socketio.on('notify_payroll_status')
def on_notify_payroll_status(data):
    """Notify about payroll status changes"""
    try:
        if current_user.is_authenticated and current_user.can_access_admin_features():
            restaurant_id = data.get('restaurant_id')
            user_id = data.get('user_id')
            payroll_data = data.get('payroll_data', {})
            status = data.get('status')  # 'processed', 'paid', 'failed'
            
            if restaurant_id and user_id:
                # Send notification to specific user
                emit('payroll_notification', {
                    'type': 'status_change',
                    'status': status,
                    'message': f'Your payroll has been {status}',
                    'payroll_data': payroll_data,
                    'timestamp': datetime.utcnow().isoformat()
                }, to=f"user_{user_id}")
                
                # Send general notification to restaurant room for admins
                emit('payroll_updated', {
                    'type': 'status_change',
                    'status': status,
                    'payroll_data': payroll_data,
                    'updated_by': current_user.name,
                    'timestamp': datetime.utcnow().isoformat()
                }, to=f"restaurant_{restaurant_id}")
    except Exception as e:
        logger.error(f"Error notifying payroll status: {str(e)}")
        emit('error', {'message': 'Failed to notify payroll status'})

@socketio.on('notify_performance_evaluation')
def on_notify_performance_evaluation(data):
    """Notify about performance evaluations"""
    try:
        if current_user.is_authenticated and current_user.can_access_manager_features():
            restaurant_id = data.get('restaurant_id')
            user_id = data.get('user_id')
            performance_data = data.get('performance_data', {})
            
            if restaurant_id and user_id:
                # Send notification to specific user
                emit('performance_notification', {
                    'type': 'evaluation_completed',
                    'message': 'Your performance evaluation has been completed',
                    'performance_data': performance_data,
                    'evaluated_by': current_user.name,
                    'timestamp': datetime.utcnow().isoformat()
                }, to=f"user_{user_id}")
                
                # Send general notification to restaurant room for managers
                emit('performance_updated', {
                    'type': 'evaluation_completed',
                    'performance_data': performance_data,
                    'evaluated_by': current_user.name,
                    'timestamp': datetime.utcnow().isoformat()
                }, to=f"restaurant_{restaurant_id}")
    except Exception as e:
        logger.error(f"Error notifying performance evaluation: {str(e)}")
        emit('error', {'message': 'Failed to notify performance evaluation'})

# Helper function to send notifications to specific users
def send_user_notification(user_id, notification_type, message, data=None):
    """Send notification to a specific user"""
    try:
        emit('user_notification', {
            'type': notification_type,
            'message': message,
            'data': data or {},
            'timestamp': datetime.utcnow().isoformat()
        }, to=f"user_{user_id}")
    except Exception as e:
        logger.error(f"Error sending user notification: {str(e)}")

# Helper function to send notifications to restaurant rooms
def send_restaurant_notification(restaurant_id, notification_type, message, data=None):
    """Send notification to all users in a restaurant"""
    try:
        emit('restaurant_notification', {
            'type': notification_type,
            'message': message,
            'data': data or {},
            'timestamp': datetime.utcnow().isoformat()
        }, to=f"restaurant_{restaurant_id}")
    except Exception as e:
        logger.error(f"Error sending restaurant notification: {str(e)}")

# Helper function to broadcast system-wide notifications (for super admins)
def broadcast_system_notification(notification_type, message, data=None):
    """Broadcast system-wide notification"""
    try:
        emit('system_notification', {
            'type': notification_type,
            'message': message,
            'data': data or {},
            'timestamp': datetime.utcnow().isoformat()
        }, broadcast=True)
    except Exception as e:
        logger.error(f"Error broadcasting system notification: {str(e)}")