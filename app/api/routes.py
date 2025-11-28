from flask import jsonify, request, session, render_template
from flask_login import login_required, current_user
from sqlalchemy import func
from app.api import bp
from app.api.offline import bp as offline_bp
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
def get_cart_count():
    """Get cart item count"""
    # Allow unauthenticated access to prevent HTML error responses
    if not current_user.is_authenticated:
        return jsonify({'count': 0})
    
    cart = session.get('cart', {})
    return jsonify({'count': len(cart)})

@bp.route('/auth/status')
def api_auth_status():
    """API endpoint for authentication status"""
    from app.auth.routes import auth_status
    return auth_status()

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

@bp.route('/item/<int:item_id>/variants')
@login_required
def get_item_variants(item_id):
    """Get variants for a specific menu item"""
    from app.models.menu import MenuItem, ItemVariant
    
    item = MenuItem.query.get_or_404(item_id)
    variants = ItemVariant.query.filter_by(item_id=item_id, is_available=True).order_by(ItemVariant.display_order).all()
    
    return jsonify({
        'item': {
            'id': item.id,
            'name': item.name,
            'price': float(item.price)
        },
        'variants': [
            {
                'id': v.id,
                'name': v.name,
                'price_modifier': float(v.price_modifier),
                'total_price': float(item.price) + float(v.price_modifier)
            } for v in variants
        ]
    })

# Note: The offline blueprint is registered in app/__init__.py

# Live Polling Endpoints for Dashboards
@bp.route('/live/billing-stats')
@login_required
def get_live_billing_stats():
    """Get live billing statistics for dashboard polling"""
    if not current_user.can_access_manager_features():
        return jsonify({'error': 'Access denied'}), 403
    
    from app.models.billing import Invoice
    
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    stats = {
        'total_invoices': Invoice.query.count(),
        'total_amount': float(db.session.query(func.sum(Invoice.total_amount)).scalar() or 0),
        'outstanding_amount': float(db.session.query(func.sum(Invoice.balance_amount)).scalar() or 0),
        'overdue_invoices': Invoice.query.filter(
            Invoice.due_date < datetime.now(),
            Invoice.status.in_(['sent', 'partially_paid'])
        ).count(),
        'today_invoices': Invoice.query.filter(Invoice.created_at >= today).count(),
        'today_revenue': float(db.session.query(func.sum(Invoice.total_amount))
                           .filter(Invoice.created_at >= today).scalar() or 0),
        'last_updated': datetime.now().isoformat()
    }
    
    return render_template('partials/billing_stats_live.html', stats=stats)

@bp.route('/live/inventory-alerts')
@login_required
def get_live_inventory_alerts():
    """Get live inventory alerts for dashboard polling"""
    if not current_user.can_access_manager_features():
        return jsonify({'error': 'Access denied'}), 403
    
    from app.models.inventory import Ingredient
    
    # Get low stock and out of stock items
    low_stock_items = Ingredient.query.filter(
        Ingredient.current_stock <= Ingredient.minimum_stock,
        Ingredient.current_stock > 0
    ).limit(10).all()
    
    out_of_stock_items = Ingredient.query.filter(
        Ingredient.current_stock == 0
    ).limit(10).all()
    
    # Calculate total inventory value
    total_value = db.session.query(
        func.sum(Ingredient.current_stock * Ingredient.unit_cost)
    ).scalar() or 0
    
    stats = {
        'total_ingredients': Ingredient.query.count(),
        'low_stock_count': len(low_stock_items),
        'out_of_stock_count': len(out_of_stock_items),
        'total_value': float(total_value),
        'low_stock_items': [item.to_dict() for item in low_stock_items],
        'out_of_stock_items': [item.to_dict() for item in out_of_stock_items],
        'last_updated': datetime.now().isoformat()
    }
    
    return render_template('partials/inventory_alerts_live.html', stats=stats)

@bp.route('/live/financial-metrics')
@login_required
def get_live_financial_metrics():
    """Get live financial metrics for accounting dashboard"""
    if not current_user.can_access_manager_features():
        return jsonify({'error': 'Access denied'}), 403
    
    from app.models.order import Order, OrderStatus
    # Import accounting transaction if available
    accounting_available = False
    AccountingTransaction = None
    try:
        # Import accounting transaction if available
        try:
            from app.models.accounting import Transaction
            AccountingTransaction = Transaction  # Use Transaction as AccountingTransaction
        except ImportError:
            AccountingTransaction = None
        accounting_available = True
    except ImportError:
        accounting_available = False
        AccountingTransaction = None
    
    # Get date range (last 24 hours)
    end_date = datetime.now()
    start_date = end_date - timedelta(hours=24)
    
    # Calculate metrics
    orders = Order.query.filter(
        Order.created_at >= start_date,
        Order.created_at <= end_date
    ).all()
    
    total_orders = len(orders)
    total_revenue = sum(float(order.total) for order in orders)
    total_tax = sum(float(order.tax_amount) for order in orders)
    
    # Get payment method breakdown
    payment_breakdown = {}
    for order in orders:
        if order.payments:
            for payment in order.payments:
                method = payment.method.value
                if method not in payment_breakdown:
                    payment_breakdown[method] = 0
                payment_breakdown[method] += float(payment.amount)
    
    # Get recent transactions if accounting is available
    recent_transactions = []
    if accounting_available and AccountingTransaction:
        recent_transactions = AccountingTransaction.query.filter(
            AccountingTransaction.created_at >= start_date
        ).order_by(AccountingTransaction.created_at.desc()).limit(10).all()
    
    stats = {
        'total_orders_24h': total_orders,
        'total_revenue_24h': total_revenue,
        'total_tax_24h': total_tax,
        'average_order_value': total_revenue / total_orders if total_orders > 0 else 0,
        'payment_breakdown': payment_breakdown,
        'recent_transactions': [tx.to_dict() for tx in recent_transactions] if recent_transactions else [],
        'last_updated': datetime.now().isoformat()
    }
    
    return render_template('partials/financial_metrics_live.html', stats=stats)

@bp.route('/live/system-status')
@login_required
def get_live_system_status():
    """Get live system status for monitoring"""
    if not current_user.can_access_manager_features():
        return jsonify({'error': 'Access denied'}), 403
    
    # Get current system metrics
    stats = {
        'total_users': User.query.count(),
        'active_users': User.query.filter_by(is_active=True).count(),
        'total_orders_today': Order.query.filter(
            Order.created_at >= datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        ).count(),
        'pending_orders': Order.query.filter_by(status=OrderStatus.PENDING).count(),
        'total_tables': Table.query.count(),
        'occupied_tables': Table.query.filter_by(status=TableStatus.OCCUPIED).count(),
        'available_tables': Table.query.filter_by(status=TableStatus.FREE, is_active=True).count(),
        'system_uptime': '99.9%',  # TODO: Calculate actual uptime
        'database_size': '125 MB',  # TODO: Calculate actual DB size
        'last_updated': datetime.now().isoformat()
    }
    
    return render_template('partials/system_status_live.html', stats=stats)