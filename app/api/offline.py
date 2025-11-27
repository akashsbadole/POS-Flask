from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from app.models.menu import MenuItem, Category as MenuCategory
from app.models.order import Order
from app.models.table import Table
from app import db
from datetime import datetime, timedelta

bp = Blueprint('offline', __name__)

@bp.route('/menu/items')
@login_required
def get_menu_items():
    """Get menu items for offline caching"""
    try:
        items = MenuItem.query.filter_by(is_available=True).all()
        return jsonify({
            'success': True,
            'data': [item.to_dict() for item in items],
            'cached_at': datetime.utcnow().isoformat()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/menu/categories')
@login_required
def get_menu_categories():
    """Get menu categories for offline caching"""
    try:
        categories = MenuCategory.query.filter_by(is_active=True).all()
        return jsonify({
            'success': True,
            'data': [category.to_dict() for category in categories],
            'cached_at': datetime.utcnow().isoformat()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/tables')
@login_required
def get_tables():
    """Get tables for offline caching"""
    try:
        tables = Table.query.all()
        return jsonify({
            'success': True,
            'data': [table.to_dict() for table in tables],
            'cached_at': datetime.utcnow().isoformat()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/orders/recent')
@login_required
def get_recent_orders():
    """Get recent orders for offline caching"""
    try:
        # Get orders from last 7 days
        week_ago = datetime.utcnow() - timedelta(days=7)
        orders = Order.query.filter(
            Order.created_at >= week_ago,
            Order.restaurant_id == current_user.restaurant_id
        ).order_by(Order.created_at.desc()).limit(50).all()
        
        return jsonify({
            'success': True,
            'data': [order.to_dict() for order in orders],
            'cached_at': datetime.utcnow().isoformat()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/sync/order', methods=['POST'])
@login_required
def sync_order():
    """Sync offline orders when back online"""
    try:
        order_data = request.get_json()
        
        # Check if this is an offline order
        if 'offline_created' in order_data:
            # Create new order from offline data
            order = Order(
                restaurant_id=current_user.restaurant_id,
                user_id=current_user.id,
                table_id=order_data.get('table_id'),
                status='confirmed',
                subtotal=order_data.get('subtotal', 0),
                tax_amount=order_data.get('tax_amount', 0),
                total=order_data.get('total', 0),
                created_at=datetime.fromtimestamp(order_data['offline_created'] / 1000)
            )
            
            db.session.add(order)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'order_id': order.id,
                'message': 'Order synced successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Invalid offline order data'
            }), 400
            
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/sync/cart', methods=['POST'])
@login_required
def sync_cart():
    """Sync offline cart when back online"""
    try:
        cart_data = request.get_json()
        
        # Process cart sync logic here
        # This would integrate with the existing cart system
        
        return jsonify({
            'success': True,
            'message': 'Cart synced successfully'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/storage/info')
@login_required
def get_storage_info():
    """Get storage usage information for offline data"""
    try:
        # This would typically be handled client-side with IndexedDB
        # But we can provide server-side quotas and limits
        
        return jsonify({
            'success': True,
            'data': {
                'max_cache_age_hours': 24,
                'max_offline_orders': 100,
                'max_menu_items': 1000,
                'sync_batch_size': 50,
                'retry_attempts': 3
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/status')
def get_offline_status():
    """Get offline capability status"""
    return jsonify({
        'success': True,
        'data': {
            'offline_enabled': True,
            'sync_enabled': True,
            'cache_version': '2.0',
            'features': [
                'menu_caching',
                'order_sync',
                'cart_offline',
                'table_status',
                'notifications'
            ]
        }
    })