from flask import jsonify, request, session
from flask_login import login_required, current_user
from app.api import bp
from app.models.user import User
from app.models.menu import Category, MenuItem
from app.models.order import Order, OrderStatus
from app.models.table import Table, TableStatus
from app import db
from datetime import datetime, timedelta

@bp.route('/menu/categories')
@login_required
def get_categories():
    """Get all menu categories"""
    categories = Category.query.filter_by(is_active=True).order_by(Category.display_order).all()
    return jsonify([cat.to_dict() for cat in categories])

@bp.route('/menu/items')
@login_required
def get_menu_items():
    """Get all menu items"""
    category_id = request.args.get('category_id', type=int)
    
    query = MenuItem.query.filter_by(is_available=True)
    if category_id:
        query = query.filter_by(category_id=category_id)
    
    items = query.order_by(MenuItem.display_order).all()
    return jsonify([item.to_dict() for item in items])

@bp.route('/menu/item/<int:item_id>')
@login_required
def get_menu_item(item_id):
    """Get specific menu item"""
    item = MenuItem.query.get_or_404(item_id)
    return jsonify(item.to_dict())

@bp.route('/cart')
@login_required
def get_cart():
    """Get current cart contents"""
    cart = session.get('cart', {})
    
    # Calculate totals
    subtotal = sum(item['unit_price'] * item['quantity'] for item in cart.values())
    tax = subtotal * 0.0875  # 8.75% tax
    total = subtotal + tax
    
    return jsonify({
        'items': list(cart.values()),
        'subtotal': round(subtotal, 2),
        'tax': round(tax, 2),
        'total': round(total, 2),
        'item_count': len(cart)
    })

@bp.route('/cart/count')
@login_required
def get_cart_count():
    """Get cart item count"""
    cart = session.get('cart', {})
    return jsonify({'count': len(cart)})

@bp.route('/orders')
@login_required
def get_orders():
    """Get orders with filtering"""
    status_filter = request.args.get('status')
    limit = request.args.get('limit', 20, type=int)
    
    query = Order.query
    
    if status_filter:
        try:
            status = OrderStatus(status_filter)
            query = query.filter_by(status=status)
        except ValueError:
            pass
    
    orders = query.order_by(Order.created_at.desc()).limit(limit).all()
    return jsonify([order.to_dict(include_items=True) for order in orders])

@bp.route('/orders/<int:order_id>')
@login_required
def get_order(order_id):
    """Get specific order"""
    order = Order.query.get_or_404(order_id)
    return jsonify(order.to_dict(include_items=True, include_payments=True))

@bp.route('/tables')
@login_required
def get_tables():
    """Get all tables"""
    tables = Table.query.filter_by(is_active=True).all()
    return jsonify([table.to_dict(include_session=True) for table in tables])

@bp.route('/tables/<int:table_id>')
@login_required
def get_table(table_id):
    """Get specific table"""
    table = Table.query.get_or_404(table_id)
    return jsonify(table.to_dict(include_session=True))

@bp.route('/users/current')
@login_required
def get_current_user():
    """Get current user info"""
    return jsonify(current_user.to_dict())

@bp.route('/system/stats')
@login_required
def get_system_stats():
    """Get system statistics"""
    if not current_user.can_access_manager_features():
        return jsonify({'error': 'Access denied'}), 403
    
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    stats = {
        'total_users': User.query.count(),
        'active_users': User.query.filter_by(is_active=True).count(),
        'total_orders_today': Order.query.filter(Order.created_at >= today).count(),
        'pending_orders': Order.query.filter_by(status=OrderStatus.PENDING).count(),
        'total_tables': Table.query.count(),
        'occupied_tables': Table.query.filter_by(status=TableStatus.OCCUPIED).count(),
        'available_tables': Table.query.filter_by(status=TableStatus.FREE, is_active=True).count()
    }
    
    return jsonify(stats)

@bp.route('/search/menu')
@login_required
def search_menu():
    """Search menu items"""
    query = request.args.get('q', '').strip()
    
    if not query:
        return jsonify({'items': []})
    
    items = MenuItem.query.filter(
        MenuItem.is_available == True,
        MenuItem.name.contains(query)
    ).order_by(MenuItem.name).limit(20).all()
    
    return jsonify({
        'items': [item.to_dict() for item in items],
        'query': query
    })