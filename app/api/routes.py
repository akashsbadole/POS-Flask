from flask import jsonify, request, session, render_template
from flask_login import login_required, current_user
from sqlalchemy import func, or_, text
from flask_wtf.csrf import CSRFProtect
csrf = CSRFProtect()
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
        'overdue_invoices': db.session.query(Invoice).filter(
            text('due_date < :now AND status IN (:sent, :overdue)')
        ).params(now=datetime.now(), sent='sent', overdue='overdue').count(),
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
    
    # Check if this is an HTMX request (for HTML partial) or regular API request (for JSON)
    if request.headers.get('HX-Request'):
        return render_template('partials/inventory_alerts_live.html', stats=stats)
    
    return jsonify(stats)

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

# Settings API Endpoints
@bp.route('/settings/load')
@csrf.exempt  # Explicitly exempt from CSRF protection
@login_required
def load_settings():
    """Load all settings"""
    from app.services.settings_service import SettingsService
    
    # Flatten settings for frontend use
    all_settings = SettingsService.get_all_settings()
    flattened = {}
    
    for category, settings in all_settings.items():
        for key, value in settings.items():
            flattened[key] = value
    
    return jsonify({
        'success': True,
        'settings': flattened
    })

@bp.route('/settings/save', methods=['POST'])
@csrf.exempt  # Explicitly exempt from CSRF protection
@login_required
def save_settings():
    """Save settings"""
    from app.services.settings_service import SettingsService
    from flask import request
    
    try:
        settings_data = request.get_json()
        if not settings_data:
            return jsonify({'success': False, 'error': 'No settings data provided'})
        
        # Group settings by category
        categorized_settings = {}
        for key, value in settings_data.items():
            # Determine category based on key
            if key in ['restaurant_name', 'language', 'timezone', 'currency']:
                category = 'general'
            elif key in ['gst_number', 'tax_rate', 'service_charge']:
                category = 'business'
            elif key in ['cash_enabled', 'card_enabled', 'upi_enabled']:
                category = 'payment'
            elif key in ['low_stock_alerts', 'order_notifications', 'email_notifications']:
                category = 'notifications'
            elif key in ['two_factor_auth', 'session_timeout', 'strong_passwords']:
                category = 'security'
            elif key in ['auto_backup', 'default_printer', 'debug_mode']:
                category = 'advanced'
            else:
                category = 'general'  # Default category
            
            if category not in categorized_settings:
                categorized_settings[category] = {}
            categorized_settings[category][key] = value
        
        # Update settings
        results = SettingsService.update_multiple_settings(
            categorized_settings,
            user_id=current_user.id,
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        
        # Check if all updates were successful
        if all(results.values()):
            return jsonify({'success': True})
        else:
            failed_updates = [k for k, v in results.items() if not v]
            return jsonify({
                'success': False,
                'error': f'Failed to update settings: {", ".join(failed_updates)}'
            })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@bp.route('/settings/reset', methods=['POST'])
@csrf.exempt  # Explicitly exempt from CSRF protection
@login_required
def reset_settings():
    """Reset settings to defaults"""
    from app.services.settings_service import SettingsService
    
    try:
        success = SettingsService.reset_to_defaults()
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Failed to reset settings'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@bp.route('/settings/export')
@login_required
def export_settings():
    """Export settings"""
    from app.services.settings_service import SettingsService
    
    try:
        settings = SettingsService.export_settings()
        return jsonify(settings)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# Menu Reordering API Endpoints
@bp.route('/menu/reorder-items', methods=['POST'])
@login_required
def reorder_menu_items():
    """API endpoint to reorder menu items within a category"""
    if not current_user.can_access_manager_features():
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        data = request.get_json()
        items_data = data.get('items', [])
        category_id = data.get('category_id')
        
        if not items_data:
            return jsonify({'error': 'No items data provided'}), 400
        
        # Update display orders for each item
        for item_data in items_data:
            item_id = item_data.get('id')
            display_order = item_data.get('display_order', 0)
            
            if item_id:
                item = MenuItem.query.get(item_id)
                if item:
                    item.display_order = display_order
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'{len(items_data)} items reordered successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@bp.route('/menu/reorder-categories', methods=['POST'])
@login_required
def reorder_menu_categories():
    """API endpoint to reorder menu categories"""
    if not current_user.can_access_manager_features():
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        data = request.get_json()
        categories_data = data.get('categories', [])
        
        if not categories_data:
            return jsonify({'error': 'No categories data provided'}), 400
        
        # Update display orders for each category
        for category_data in categories_data:
            category_id = category_data.get('id')
            display_order = category_data.get('display_order', 0)
            
            if category_id:
                category = Category.query.get(category_id)
                if category:
                    category.display_order = display_order
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'{len(categories_data)} categories reordered successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@bp.route('/menu/bulk-reorder', methods=['POST'])
@login_required
def bulk_reorder_menu():
    """API endpoint for bulk reordering operations"""
    if not current_user.can_access_manager_features():
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        data = request.get_json()
        operation = data.get('operation')
        
        if operation == 'reset_alphabetical':
            # Reset items to alphabetical order within categories
            category_id = data.get('category_id')
            query = MenuItem.query
            
            if category_id:
                query = query.filter_by(category_id=category_id)
            
            items = query.order_by(MenuItem.name).all()
            for index, item in enumerate(items):
                item.display_order = index
                
            message = f'Items reset to alphabetical order'
            
        elif operation == 'sort_by_price':
            # Sort items by price within categories
            category_id = data.get('category_id')
            ascending = data.get('ascending', True)
            query = MenuItem.query
            
            if category_id:
                query = query.filter_by(category_id=category_id)
            
            if ascending:
                items = query.order_by(MenuItem.price).all()
            else:
                items = query.order_by(MenuItem.price.desc()).all()
                
            for index, item in enumerate(items):
                item.display_order = index
                
            message = f'Items sorted by price {"(ascending)" if ascending else "(descending)"}'
            
        elif operation == 'sort_categories_alphabetical':
            # Sort categories alphabetically
            categories = Category.query.order_by(Category.name).all()
            for index, category in enumerate(categories):
                category.display_order = index
                
            message = 'Categories sorted alphabetically'
            
        else:
            return jsonify({'error': 'Invalid operation'}), 400
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': message
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@bp.route('/settings/import', methods=['POST'])
@csrf.exempt  # Explicitly exempt from CSRF protection
@login_required
def import_settings():
    """Import settings"""
    from app.services.settings_service import SettingsService
    from flask import request
    
    try:
        settings_data = request.get_json()
        if not settings_data:
            return jsonify({'success': False, 'error': 'No settings data provided'})
        
        results = SettingsService.import_settings(
            settings_data,
            user_id=current_user.id
        )
        
        # Check if all imports were successful
        if all(results.values()):
            return jsonify({'success': True})
        else:
            failed_imports = [k for k, v in results.items() if not v]
            return jsonify({
                'success': False,
                'error': f'Failed to import settings: {", ".join(failed_imports)}'
            })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# Table Order Management API Endpoints
@bp.route('/tables/<int:table_id>/current-order')
@login_required
def get_table_current_order(table_id):
    """Get current order for a table"""
    from app.models.table import Table
    
    table = Table.query.get_or_404(table_id)
    current_order = table.get_current_order()
    
    if not current_order:
        return jsonify({
            'table_id': table_id,
            'table_number': table.number,
            'current_order': None,
            'message': 'No active order for this table'
        })
    
    return jsonify({
        'table_id': table_id,
        'table_number': table.number,
        'current_order': current_order.to_dict(include_items=True),
        'order_duration_minutes': current_order.get_duration_minutes(),
        'items_count': len(current_order.items),
        'can_be_modified': current_order.can_be_modified(),
        'can_be_transferred': current_order.can_be_transferred(),
        'can_be_split': current_order.can_be_split()
    })

@bp.route('/orders/table/<int:table_id>/add-item', methods=['POST'])
@login_required
def add_item_to_table_order_api(table_id):
    """Quick add item to table order"""
    from app.models.table import Table
    from app.models.menu import MenuItem, AddOn
    from app.models.order import OrderItem
    
    table = Table.query.get_or_404(table_id)
    current_order = table.get_current_order()
    
    if not current_order:
        return jsonify({
            'success': False,
            'error': 'No active order for this table'
        }), 400
    
    if not current_order.can_be_modified():
        return jsonify({
            'success': False,
            'error': 'Order cannot be modified in current status'
        }), 400
    
    try:
        data = request.get_json()
        item_id = data.get('item_id', type=int)
        quantity = data.get('quantity', 1, type=int)
        variant_id = data.get('variant_id', type=int)
        add_on_ids = data.get('add_ons', [])
        notes = data.get('notes', '')
        seat_number = data.get('seat_number')
        
        if not item_id:
            return jsonify({
                'success': False,
                'error': 'Menu item ID is required'
            }), 400
        
        menu_item = MenuItem.query.get_or_404(item_id)
        
        # Calculate price
        unit_price = float(menu_item.price)
        
        # Add variant price
        if variant_id:
            from app.models.menu import ItemVariant
            variant = ItemVariant.query.get(variant_id)
            if variant:
                unit_price += float(variant.price_modifier)
        
        # Add add-on prices
        for add_on_id in add_on_ids:
            add_on = AddOn.query.get(add_on_id)
            if add_on:
                unit_price += float(add_on.price)
        
        # Create order item
        order_item = OrderItem(
            order_id=current_order.id,
            item_id=item_id,
            quantity=quantity,
            unit_price=unit_price,
            variant_id=variant_id,
            notes=notes
        )
        
        # Add add-ons
        for add_on_id in add_on_ids:
            add_on = AddOn.query.get(add_on_id)
            if add_on:
                order_item.add_ons.append(add_on)
        
        db.session.add(order_item)
        
        # Update order totals
        current_order.calculate_totals()
        db.session.commit()
        
        # Emit order update to kitchen
        from app.socketio_events import emit_order_status_update
        emit_order_status_update(current_order, current_order.status)
        
        return jsonify({
            'success': True,
            'message': f'{menu_item.name} added to order {current_order.order_number}',
            'order_item': order_item.to_dict(),
            'order': current_order.to_dict(include_items=True)
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/orders/<int:order_id>/status')
@login_required
def get_order_status(order_id):
    """Get real-time order status"""
    order = Order.query.get_or_404(order_id)
    
    # Calculate additional status information
    status_info = {
        'order_id': order.id,
        'order_number': order.order_number,
        'status': order.status.value,
        'status_text': order.status.value.title(),
        'table_id': order.table_id,
        'table_number': order.table.number if order.table else None,
        'waiter_id': order.waiter_id,
        'waiter_name': order.waiter.name if order.waiter else None,
        'items_count': len(order.items),
        'subtotal': float(order.subtotal),
        'tax_amount': float(order.tax_amount),
        'total': float(order.total),
        'balance_due': order.get_balance_due(),
        'is_fully_paid': order.is_fully_paid(),
        'created_at': order.created_at.isoformat(),
        'updated_at': order.updated_at.isoformat(),
        'estimated_preparation_time': order.estimated_preparation_time,
        'actual_preparation_time': order.actual_preparation_time,
        'timer_started_at': order.timer_started_at.isoformat() if order.timer_started_at else None,
        'timer_completed_at': order.timer_completed_at.isoformat() if order.timer_completed_at else None,
        'can_be_cancelled': order.can_be_cancelled(),
        'can_be_modified': order.can_be_modified(),
        'can_be_transferred': order.can_be_transferred(),
        'can_be_split': order.can_be_split(),
        'can_be_merged': order.can_be_merged()
    }
    
    # Add table status information
    if order.table:
        status_info['table_status'] = order.table.status
        status_info['table_status_text'] = order.table.get_status_text()
    
    return jsonify(status_info)

@bp.route('/orders/<int:order_id>/update-status', methods=['POST'])
@login_required
def update_order_status_api(order_id):
    """Update order status via API"""
    order = Order.query.get_or_404(order_id)
    
    try:
        data = request.get_json()
        new_status = data.get('status')
        notes = data.get('notes', '')
        
        if not new_status:
            return jsonify({
                'success': False,
                'error': 'Status is required'
            }), 400
        
        # Validate status
        try:
            status = OrderStatus(new_status)
        except ValueError:
            return jsonify({
                'success': False,
                'error': f'Invalid status: {new_status}'
            }), 400
        
        old_status = order.status
        order.update_status(status)
        
        if notes:
            if not order.notes:
                order.notes = notes
            else:
                order.notes += f"\n\nStatus Update: {notes}"
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Order {order.order_number} status updated to {status.value}',
            'old_status': old_status.value,
            'new_status': status.value,
            'order': order.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/tables/api/stats')
@login_required
def get_table_stats():
    """Get table statistics for dashboard"""
    from app.models.table import Table, TableStatus
    
    stats = {
        'total_tables': Table.query.count(),
        'active_tables': Table.query.filter_by(is_active=True).count(),
        'free_tables': Table.query.filter_by(status=TableStatus.FREE, is_active=True).count(),
        'occupied_tables': Table.query.filter_by(status=TableStatus.OCCUPIED, is_active=True).count(),
        'reserved_tables': Table.query.filter_by(status=TableStatus.RESERVED, is_active=True).count(),
        'cleaning_tables': Table.query.filter_by(status=TableStatus.CLEANING, is_active=True).count(),
        'maintenance_tables': Table.query.filter_by(status=TableStatus.MAINTENANCE, is_active=True).count(),
        'tables_with_orders': db.session.query(Table.id).join(Order).filter(
            Order.status.in_([OrderStatus.PENDING, OrderStatus.CONFIRMED, OrderStatus.PREPARING, OrderStatus.READY])
        ).distinct().count()
    }
    
    return jsonify(stats)

@bp.route('/tables/api/table/<int:table_id>')
@login_required
def get_table_details_api(table_id):
    """Get detailed table information"""
    from app.models.table import Table
    
    table = Table.query.get_or_404(table_id)
    current_order = table.get_current_order()
    
    table_data = table.to_dict(include_session=True)
    
    # Add current order information
    if current_order:
        table_data['current_order'] = {
            'id': current_order.id,
            'order_number': current_order.order_number,
            'status': current_order.status.value,
            'items_count': len(current_order.items),
            'total': float(current_order.total),
            'duration_minutes': current_order.get_duration_minutes(),
            'can_be_modified': current_order.can_be_modified()
        }
    else:
        table_data['current_order'] = None
    
    # Add assigned waiter information
    if table.assigned_waiter:
        table_data['assigned_waiter'] = {
            'id': table.assigned_waiter.id,
            'name': table.assigned_waiter.name,
            'email': table.assigned_waiter.email
        }
    else:
        table_data['assigned_waiter'] = None
    
    return jsonify(table_data)

@bp.route('/orders/assign-to-table', methods=['POST'])
@login_required
def assign_order_to_table():
    """Assign existing order to a table"""
    from app.models.table import Table
    
    try:
        data = request.get_json()
        table_id = data.get('table_id', type=int)
        order_number = data.get('order_number', '').strip()
        
        if not table_id or not order_number:
            return jsonify({
                'success': False,
                'error': 'Table ID and order number are required'
            }), 400
        
        table = Table.query.get_or_404(table_id)
        order = Order.query.filter_by(order_number=order_number).first()
        
        if not order:
            return jsonify({
                'success': False,
                'error': f'Order {order_number} not found'
            }), 404
        
        if order.table_id:
            return jsonify({
                'success': False,
                'error': f'Order {order_number} is already assigned to table {order.table.number}'
            }), 400
        
        # Assign order to table
        order.table_id = table_id
        order.waiter_id = current_user.id
        
        # Update table status
        table.occupy()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Order {order_number} assigned to table {table.number}',
            'order': order.to_dict(),
            'table': table.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500