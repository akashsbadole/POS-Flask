from flask import render_template, redirect, url_for, flash, request, current_app, jsonify
from flask_login import login_required, current_user
from sqlalchemy import desc, func
from flask_wtf.csrf import CSRFError
from app.main import bp
from app import csrf
from app.models.user import User
from app.models.order import Order, OrderStatus
from app.models.table import Table, TableStatus
from app.models.menu import MenuItem, Category
from app.models.inventory import Ingredient
from app.models.restaurant import Restaurant
from app import db
from datetime import datetime, timedelta

@bp.route('/')
def index():
    """Main landing page - redirect to login or appropriate dashboard"""
    if current_user.is_authenticated:
        if current_user.role == 'cashier':
            # Cashier functionality not yet implemented, redirect to orders list
            return redirect(url_for('orders.list_orders'))
        elif current_user.role == 'kitchen':
            return redirect(url_for('kitchen.display'))
        elif current_user.role in ['manager', 'admin', 'super_admin']:
            return redirect(url_for('main.system_status'))
    return redirect(url_for('auth.login'))

@bp.route('/dashboard')
@login_required
def dashboard():
    """Role-based dashboard redirect"""
    if current_user.role == 'cashier':
        # Cashier functionality not yet implemented, redirect to orders list
        return redirect(url_for('orders.list_orders'))
    elif current_user.role == 'kitchen':
        return redirect(url_for('kitchen.display'))
    elif current_user.role in ['manager', 'admin', 'super_admin']:
        return redirect(url_for('main.system_status'))
    else:
        flash('Invalid user role', 'error')
        return redirect(url_for('auth.logout'))

@bp.route('/system-status')
@login_required
def system_status():
    """System status page for admin/manager"""
    if not current_user.can_access_manager_features():
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    # Get system statistics
    stats = {
        'total_users': User.query.count(),
        'active_users': User.query.filter_by(is_active=True).count(),
        'total_orders_today': Order.query.filter(
            Order.created_at >= datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        ).count(),
        'pending_orders': Order.query.filter_by(status=OrderStatus.PENDING).count(),
        'total_tables': Table.query.count(),
        'occupied_tables': Table.query.filter_by(status=TableStatus.OCCUPIED).count(),
        'available_tables': Table.query.filter_by(status=TableStatus.FREE, is_active=True).count()
    }
    
    # Get recent orders
    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(10).all()
    
    # Get active users (logged in recently)
    active_users = User.query.filter(
        User.last_login >= datetime.utcnow() - timedelta(hours=1)
    ).limit(10).all()
    
    return render_template('main/system_status.html',
                         stats=stats,
                         recent_orders=recent_orders,
                         active_users=active_users)

# Dashboard Routes
@bp.route('/menu-dashboard')
@login_required
def menu_dashboard():
    """Menu Management Dashboard"""
    if not current_user.can_access_manager_features():
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    stats = {
        'total_items': MenuItem.query.count(),
        'available_items': MenuItem.query.filter_by(is_available=True).count(),
        'unavailable_items': MenuItem.query.filter_by(is_available=False).count(),
        'total_categories': Category.query.count()
    }
    
    return render_template('menu/dashboard.html', stats=stats)

@bp.route('/tables-dashboard')
@login_required
def tables_dashboard():
    """Table Management Dashboard"""
    if not current_user.can_access_manager_features():
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    stats = {
        'total_tables': Table.query.count(),
        'free_tables': Table.query.filter_by(status=TableStatus.FREE).count(),
        'occupied_tables': Table.query.filter_by(status=TableStatus.OCCUPIED).count(),
        'reserved_tables': Table.query.filter_by(status=TableStatus.RESERVED).count(),
        'cleaning_tables': Table.query.filter_by(status=TableStatus.CLEANING).count(),
        'maintenance_tables': Table.query.filter_by(status=TableStatus.MAINTENANCE).count()
    }
    
    return render_template('tables/dashboard.html', stats=stats)

@bp.route('/inventory-dashboard')
@login_required
def inventory_dashboard():
    """Inventory Management Dashboard"""
    if not current_user.can_access_manager_features():
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    total_ingredients = Ingredient.query.count()
    out_of_stock = Ingredient.query.filter(Ingredient.current_stock == 0).count()
    low_stock = Ingredient.query.filter(
        Ingredient.current_stock <= Ingredient.minimum_stock,
        Ingredient.current_stock > 0
    ).count()
    
    # Calculate total inventory value
    total_value = db.session.query(
        func.sum(Ingredient.current_stock * Ingredient.unit_cost)
    ).scalar() or 0
    
    stats = {
        'total_ingredients': total_ingredients,
        'out_of_stock': out_of_stock,
        'low_stock_count': low_stock,
        'total_value': total_value,
        'recent_adjustments': 0  # TODO: Implement adjustment tracking
    }
    
    return render_template('inventory/dashboard.html', stats=stats)

@bp.route('/reports-dashboard')
@login_required
def reports_dashboard():
    """Reports Dashboard"""
    if not current_user.can_access_manager_features():
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    # Get date range (default to last 7 days)
    days = request.args.get('days', 7, type=int)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    # Calculate statistics
    orders = Order.query.filter(
        Order.created_at >= start_date,
        Order.created_at <= end_date
    ).all()
    
    total_orders = len(orders)
    total_revenue = sum(float(order.total) for order in orders)
    total_tax = sum(float(order.tax_amount) for order in orders)
    average_order_value = total_revenue / total_orders if total_orders > 0 else 0
    
    # Payment method breakdown
    payment_breakdown = {}
    for order in orders:
        if order.payments:
            for payment in order.payments:
                method = payment.method.value
                if method not in payment_breakdown:
                    payment_breakdown[method] = 0
                payment_breakdown[method] += float(payment.amount)
    
    # Daily breakdown
    daily_stats = {}
    current_date = start_date
    while current_date <= end_date:
        day_orders = [o for o in orders if o.created_at.date() == current_date.date()]
        daily_revenue = sum(float(order.total) for order in day_orders)
        
        daily_stats[current_date.strftime('%Y-%m-%d')] = {
            'orders': len(day_orders),
            'revenue': daily_revenue
        }
        current_date += timedelta(days=1)
    
    stats = {
        'total_orders': total_orders,
        'total_revenue': total_revenue,
        'total_tax': total_tax,
        'average_order_value': average_order_value,
        'payment_breakdown': payment_breakdown,
        'daily_stats': daily_stats,
        'revenue_growth': 12.5,  # TODO: Calculate actual growth
        'orders_growth': 8.3,
        'customers_growth': 15.2,
        'aov_growth': 4.1,
        'total_customers': User.query.filter_by(is_active=True).count()
    }
    
    return render_template('reports/dashboard.html', stats=stats)

@bp.route('/settings-dashboard')
@login_required
def settings_dashboard():
    """System Settings Dashboard"""
    if not current_user.can_access_manager_features():
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    # Get restaurant info
    restaurant = Restaurant.query.first()
    
    return render_template('settings/dashboard.html', restaurant=restaurant)

# API Endpoints for Dashboards
@bp.route('/api/menu/stats')
@login_required
def api_menu_stats():
    """API endpoint for menu statistics"""
    if not current_user.can_access_manager_features():
        return jsonify({'error': 'Access denied'}), 403
    
    stats = {
        'total_items': MenuItem.query.count(),
        'available_items': MenuItem.query.filter_by(is_available=True).count(),
        'unavailable_items': MenuItem.query.filter_by(is_available=False).count(),
        'total_categories': Category.query.count()
    }
    
    return jsonify(stats)

@bp.route('/menu/api/stats')
@login_required
def api_menu_stats_alt():
    """Alternative API endpoint for menu statistics"""
    if not current_user.can_access_manager_features():
        return jsonify({'error': 'Access denied'}), 403
    
    stats = {
        'total_items': MenuItem.query.count(),
        'available_items': MenuItem.query.filter_by(is_available=True).count(),
        'unavailable_items': MenuItem.query.filter_by(is_available=False).count(),
        'total_categories': Category.query.count()
    }
    
    return jsonify(stats)

@bp.route('/menu/api/categories')
@login_required
def api_menu_categories():
    """API endpoint for menu categories"""
    if not current_user.can_access_manager_features():
        return jsonify({'error': 'Access denied'}), 403
    
    categories = Category.query.all()
    categories_data = []
    
    for category in categories:
        item_count = MenuItem.query.filter_by(category_id=category.id).count()
        categories_data.append({
            'id': category.id,
            'name': category.name,
            'description': category.description,
            'display_order': category.display_order,
            'item_count': item_count
        })
    
    return jsonify(categories_data)

@bp.route('/menu/api/items')
@login_required
def api_menu_items():
    """API endpoint for menu items"""
    if not current_user.can_access_manager_features():
        return jsonify({'error': 'Access denied'}), 403
    
    # Get query parameters
    category_id = request.args.get('category_id', type=int)
    availability = request.args.get('availability')
    search = request.args.get('search', '')
    
    # Build query
    query = MenuItem.query
    
    if category_id:
        query = query.filter_by(category_id=category_id)
    
    if availability == 'available':
        query = query.filter_by(is_available=True)
    elif availability == 'unavailable':
        query = query.filter_by(is_available=False)
    
    if search:
        query = query.filter(MenuItem.name.contains(search))
    
    items = query.all()
    items_data = []
    
    for item in items:
        items_data.append({
            'id': item.id,
            'name': item.name,
            'description': item.description,
            'price': float(item.price) if item.price else 0,
            'category_id': item.category_id,
            'category_name': item.category.name if item.category else 'Uncategorized',
            'is_available': item.is_available,
            'preparation_time': item.preparation_time or 0
        })
    
    return jsonify(items_data)

@bp.route('/api/tables/stats')
@login_required
def api_tables_stats():
    """API endpoint for table statistics"""
    if not current_user.can_access_manager_features():
        return jsonify({'error': 'Access denied'}), 403
    
    stats = {
        'total_tables': Table.query.count(),
        'free_tables': Table.query.filter_by(status=TableStatus.FREE).count(),
        'occupied_tables': Table.query.filter_by(status=TableStatus.OCCUPIED).count(),
        'reserved_tables': Table.query.filter_by(status=TableStatus.RESERVED).count(),
        'cleaning_tables': Table.query.filter_by(status=TableStatus.CLEANING).count(),
        'maintenance_tables': Table.query.filter_by(status=TableStatus.MAINTENANCE).count()
    }
    
    return jsonify(stats)

@bp.route('/api/tables/tables')
@login_required
def api_tables_list():
    """API endpoint for tables list"""
    if not current_user.can_access_manager_features():
        return jsonify({'error': 'Access denied'}), 403
    
    tables = Table.query.all()
    tables_data = []
    
    for table in tables:
        tables_data.append({
            'id': table.id,
            'number': table.number,
            'capacity': table.capacity,
            'floor_section': table.floor_section,
            'status': table.status.value if table.status else 'unknown',
            'is_active': table.is_active,
            'current_order': table.get_current_order().order_number if table.get_current_order() else None
        })
    
    return jsonify(tables_data)

@bp.route('/tables/api/stats')
@login_required
def api_tables_stats_alt():
    """Alternative API endpoint for table statistics"""
    if not current_user.can_access_manager_features():
        return jsonify({'error': 'Access denied'}), 403
    
    stats = {
        'total_tables': Table.query.count(),
        'free_tables': Table.query.filter_by(status=TableStatus.FREE).count(),
        'occupied_tables': Table.query.filter_by(status=TableStatus.OCCUPIED).count(),
        'reserved_tables': Table.query.filter_by(status=TableStatus.RESERVED).count(),
        'cleaning_tables': Table.query.filter_by(status=TableStatus.CLEANING).count(),
        'maintenance_tables': Table.query.filter_by(status=TableStatus.MAINTENANCE).count()
    }
    
    return jsonify(stats)

@bp.route('/tables/api/tables')
@login_required
def api_tables_list_alt():
    """Alternative API endpoint for tables list"""
    if not current_user.can_access_manager_features():
        return jsonify({'error': 'Access denied'}), 403
    
    # Get query parameters
    status = request.args.get('status')
    section = request.args.get('section')
    search = request.args.get('search', '')
    
    # Build query
    query = Table.query
    
    if status:
        query = query.filter_by(status=TableStatus(status))
    
    if section:
        query = query.filter_by(floor_section=section)
    
    if search:
        query = query.filter(Table.number.contains(search))
    
    tables = query.all()
    tables_data = []
    
    for table in tables:
        tables_data.append({
            'id': table.id,
            'number': table.number,
            'capacity': table.capacity,
            'floor_section': table.floor_section,
            'status': table.status.value if table.status else 'unknown',
            'is_active': table.is_active,
            'current_order': table.get_current_order().order_number if table.get_current_order() else None
        })
    
    return jsonify(tables_data)

@bp.route('/api/inventory/stats')
@login_required
def api_inventory_stats():
    """API endpoint for inventory statistics"""
    if not current_user.can_access_manager_features():
        return jsonify({'error': 'Access denied'}), 403
    
    total_ingredients = Ingredient.query.count()
    out_of_stock = Ingredient.query.filter(Ingredient.current_stock == 0).count()
    low_stock = Ingredient.query.filter(
        Ingredient.current_stock <= Ingredient.minimum_stock,
        Ingredient.current_stock > 0
    ).count()
    
    # Calculate total inventory value
    total_value = db.session.query(
        func.sum(Ingredient.current_stock * Ingredient.unit_cost)
    ).scalar() or 0
    
    stats = {
        'total_ingredients': total_ingredients,
        'out_of_stock': out_of_stock,
        'low_stock_count': low_stock,
        'total_value': total_value,
        'recent_adjustments': 0  # TODO: Implement adjustment tracking
    }
    
    return jsonify(stats)

@bp.route('/api/inventory/ingredients')
@login_required
def api_inventory_ingredients():
    """API endpoint for ingredients list"""
    if not current_user.can_access_manager_features():
        return jsonify({'error': 'Access denied'}), 403
    
    ingredients = Ingredient.query.all()
    ingredients_data = []
    
    for ingredient in ingredients:
        ingredients_data.append({
            'id': ingredient.id,
            'name': ingredient.name,
            'description': ingredient.description,
            'unit': ingredient.unit,
            'current_stock': float(ingredient.current_stock),
            'minimum_stock': float(ingredient.minimum_stock),
            'unit_cost': float(ingredient.unit_cost) if ingredient.unit_cost else 0,
            'supplier': ingredient.supplier,
            'category': ingredient.category or 'other'
        })
    
    return jsonify(ingredients_data)

@bp.route('/inventory/api/stats')
@login_required
def api_inventory_stats_alt():
    """Alternative API endpoint for inventory statistics"""
    if not current_user.can_access_manager_features():
        return jsonify({'error': 'Access denied'}), 403
    
    total_ingredients = Ingredient.query.count()
    out_of_stock = Ingredient.query.filter(Ingredient.current_stock == 0).count()
    low_stock = Ingredient.query.filter(
        Ingredient.current_stock <= Ingredient.minimum_stock,
        Ingredient.current_stock > 0
    ).count()
    
    # Calculate total inventory value
    total_value = db.session.query(
        func.sum(Ingredient.current_stock * Ingredient.unit_cost)
    ).scalar() or 0
    
    stats = {
        'total_ingredients': total_ingredients,
        'out_of_stock': out_of_stock,
        'low_stock_count': low_stock,
        'total_value': total_value,
        'recent_adjustments': 0  # TODO: Implement adjustment tracking
    }
    
    return jsonify(stats)

@bp.route('/inventory/api/ingredients')
@login_required
def api_inventory_ingredients_alt():
    """Alternative API endpoint for ingredients list"""
    if not current_user.can_access_manager_features():
        return jsonify({'error': 'Access denied'}), 403
    
    # Get query parameters
    stock_filter = request.args.get('stock_filter')
    category = request.args.get('category')
    search = request.args.get('search', '')
    
    # Build query
    query = Ingredient.query
    
    if stock_filter == 'low':
        query = query.filter(
            Ingredient.current_stock <= Ingredient.minimum_stock,
            Ingredient.current_stock > 0
        )
    elif stock_filter == 'out':
        query = query.filter(Ingredient.current_stock == 0)
    
    if category:
        query = query.filter_by(category=category)
    
    if search:
        query = query.filter(Ingredient.name.contains(search))
    
    ingredients = query.all()
    ingredients_data = []
    
    for ingredient in ingredients:
        ingredients_data.append({
            'id': ingredient.id,
            'name': ingredient.name,
            'description': ingredient.description,
            'unit': ingredient.unit,
            'current_stock': float(ingredient.current_stock),
            'minimum_stock': float(ingredient.minimum_stock),
            'unit_cost': float(ingredient.unit_cost) if ingredient.unit_cost else 0,
            'supplier': ingredient.supplier,
            'category': ingredient.category or 'other'
        })
    
    return jsonify(ingredients_data)

@bp.route('/api/reports/stats')
@login_required
def api_reports_stats():
    """API endpoint for reports statistics"""
    if not current_user.can_access_manager_features():
        return jsonify({'error': 'Access denied'}), 403
    
    days = request.args.get('days', 7, type=int)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    orders = Order.query.filter(
        Order.created_at >= start_date,
        Order.created_at <= end_date
    ).all()
    
    total_orders = len(orders)
    total_revenue = sum(float(order.total) for order in orders)
    total_tax = sum(float(order.tax_amount) for order in orders)
    average_order_value = total_revenue / total_orders if total_orders > 0 else 0
    
    # Payment method breakdown
    payment_breakdown = {}
    for order in orders:
        if order.payments:
            for payment in order.payments:
                method = payment.method.value
                if method not in payment_breakdown:
                    payment_breakdown[method] = 0
                payment_breakdown[method] += float(payment.amount)
    
    # Daily breakdown
    daily_stats = {}
    current_date = start_date
    while current_date <= end_date:
        day_orders = [o for o in orders if o.created_at.date() == current_date.date()]
        daily_revenue = sum(float(order.total) for order in day_orders)
        
        daily_stats[current_date.strftime('%Y-%m-%d')] = {
            'orders': len(day_orders),
            'revenue': daily_revenue
        }
        current_date += timedelta(days=1)
    
    stats = {
        'total_orders': total_orders,
        'total_revenue': total_revenue,
        'total_tax': total_tax,
        'average_order_value': average_order_value,
        'payment_breakdown': payment_breakdown,
        'daily_stats': daily_stats,
        'revenue_growth': 12.5,  # TODO: Calculate actual growth
        'orders_growth': 8.3,
        'customers_growth': 15.2,
        'aov_growth': 4.1,
        'total_customers': User.query.filter_by(is_active=True).count()
    }
    
    return jsonify(stats)

@bp.route('/api/settings/load')
@csrf.exempt
@login_required
def api_settings_load():
    """API endpoint to load settings"""
    # Check user permissions first
    if not current_user.can_access_manager_features():
        if request.headers.get('Accept') == 'application/json':
            return jsonify({'error': 'Access denied'}), 403
        else:
            # For web requests, redirect to login with proper flash message
            flash('You do not have permission to access settings.', 'error')
            return redirect(url_for('auth.login', next=request.url))
    
    try:
        from app.services.settings_service import SettingsService
        
        # Initialize default settings if they don't exist
        SettingsService.initialize_default_settings()
        
        # Get all settings from database
        all_settings = SettingsService.get_all_settings()
        
        # Flatten the nested structure to match frontend expectations
        flat_settings = {}
        for category, settings in all_settings.items():
            for key, value in settings.items():
                flat_settings[key] = value
        
        return jsonify({'settings': flat_settings})
    except Exception as e:
        current_app.logger.error(f"Error loading settings: {str(e)}")
        return jsonify({'error': 'Failed to load settings'}), 500

@bp.route('/api/settings/save', methods=['POST'])
@csrf.exempt
@login_required
def api_settings_save():
    """API endpoint to save settings"""
    # Check user permissions first
    if not current_user.can_access_manager_features():
        # Check if request is AJAX/JSON request
        if request.headers.get('Accept') == 'application/json' or request.headers.get('Content-Type') == 'application/json':
            return jsonify({'error': 'Access denied'}), 403
        else:
            # For web requests, redirect to login with proper flash message
            flash('You do not have permission to access settings.', 'error')
            return redirect(url_for('auth.login', next=request.url))
    
    try:
        settings_data = request.get_json()
        if not settings_data:
            return jsonify({'error': 'No settings data provided'}), 400
        
        from app.services.settings_service import SettingsService
        
        # Convert flat structure to nested structure expected by SettingsService
        nested_settings = {}
        for key, value in settings_data.items():
            # Determine category based on setting key
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
            
            if category not in nested_settings:
                nested_settings[category] = {}
            nested_settings[category][key] = value
        
        results = SettingsService.update_multiple_settings(
            nested_settings,
            user_id=current_user.id,
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        
        # Check if all updates were successful
        if all(results.values()):
            # Broadcast update to connected clients
            try:
                from flask_socketio import emit
                emit('settings_updated', {
                    'settings': SettingsService.get_all_settings(),
                    'updated_by': current_user.name
                }, broadcast=True)
            except ImportError:
                # SocketIO not available, skip broadcasting
                pass
            except Exception as e:
                current_app.logger.warning(f"Failed to broadcast settings update: {str(e)}")
            
            return jsonify({'success': True, 'results': results})
        else:
            failed = [k for k, v in results.items() if not v]
            return jsonify({'error': f'Failed to update: {", ".join(failed)}'}), 400
    
    except Exception as e:
        current_app.logger.error(f"Error saving settings: {str(e)}")
        return jsonify({'error': 'Failed to save settings'}), 500

@bp.route('/api/settings/reset', methods=['POST'])
@csrf.exempt
@login_required
def api_settings_reset():
    """API endpoint to reset settings"""
    # Check user permissions first
    if not current_user.can_access_manager_features():
        # Check if request is AJAX/JSON request
        if request.headers.get('Accept') == 'application/json' or request.headers.get('Content-Type') == 'application/json':
            return jsonify({'error': 'Access denied'}), 403
        else:
            # For web requests, redirect to login with proper flash message
            flash('You do not have permission to access settings.', 'error')
            return redirect(url_for('auth.login', next=request.url))
    
    try:
        category = request.get_json().get('category') if request.get_json() else None
        
        from app.services.settings_service import SettingsService
        success = SettingsService.reset_to_defaults(category)
        
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'Failed to reset settings'}), 500
    except Exception as e:
        current_app.logger.error(f"Error resetting settings: {str(e)}")
        return jsonify({'error': 'Failed to reset settings'}), 500

@bp.route('/api/settings/export')
@csrf.exempt
@login_required
def api_settings_export():
    """API endpoint to export settings"""
    # Check user permissions first
    if not current_user.can_access_manager_features():
        # Check if request is AJAX/JSON request
        if request.headers.get('Accept') == 'application/json':
            return jsonify({'error': 'Access denied'}), 403
        else:
            # For web requests, redirect to login with proper flash message
            flash('You do not have permission to access settings.', 'error')
            return redirect(url_for('auth.login', next=request.url))
    
    try:
        from app.services.settings_service import SettingsService
        settings = SettingsService.export_settings()
        return jsonify(settings)
    except Exception as e:
        current_app.logger.error(f"Error exporting settings: {str(e)}")
        return jsonify({'error': 'Failed to export settings'}), 500

@bp.route('/api/settings/import', methods=['POST'])
@csrf.exempt
@login_required
def api_settings_import():
    """API endpoint to import settings"""
    # Check user permissions first
    if not current_user.can_access_manager_features():
        # Check if request is AJAX/JSON request
        if request.headers.get('Accept') == 'application/json' or request.headers.get('Content-Type') == 'application/json':
            return jsonify({'error': 'Access denied'}), 403
        else:
            # For web requests, redirect to login with proper flash message
            flash('You do not have permission to access settings.', 'error')
            return redirect(url_for('auth.login', next=request.url))
    
    try:
        settings_data = request.get_json()
        if not settings_data:
            return jsonify({'error': 'No settings data provided'}), 400
        
        from app.services.settings_service import SettingsService
        results = SettingsService.import_settings(settings_data, current_user.id)
        
        return jsonify({'success': True, 'results': results})
    except Exception as e:
        current_app.logger.error(f"Error importing settings: {str(e)}")
        return jsonify({'error': 'Failed to import settings'}), 500

@bp.route('/api/settings/category/<category>')
@csrf.exempt
@login_required
def api_settings_category(category):
    """API endpoint to load specific category settings"""
    # Check user permissions first
    if not current_user.can_access_manager_features():
        # Check if request is AJAX/JSON request
        if request.headers.get('Accept') == 'application/json':
            return jsonify({'error': 'Access denied'}), 403
        else:
            # For web requests, redirect to login with proper flash message
            flash('You do not have permission to access settings.', 'error')
            return redirect(url_for('auth.login', next=request.url))
    
    try:
        from app.services.settings_service import SettingsService
        settings = SettingsService.get_category_settings(category)
        return jsonify({'settings': settings})
    except Exception as e:
        current_app.logger.error(f"Error loading category settings: {str(e)}")
        return jsonify({'error': 'Failed to load settings'}), 500

@bp.errorhandler(404)
def not_found_error(error):
    """Handle 404 errors"""
    if request.headers.get('HX-Request'):
        return render_template('errors/404.html'), 404
    return render_template('errors/404.html'), 404

@bp.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    db.session.rollback()
    if request.headers.get('HX-Request'):
        return render_template('errors/500.html'), 500
    return render_template('errors/500.html'), 500

@bp.context_processor
def utility_functions():
    """Add utility functions to templates"""
    def format_currency(amount):
        """Format amount as currency"""
        return f"${float(amount):.2f}"
    
    def format_datetime(dt, format='medium'):
        """Format datetime"""
        if not dt:
            return ''
        if format == 'short':
            return dt.strftime('%m/%d %H:%M')
        elif format == 'medium':
            return dt.strftime('%m/%d/%Y %H:%M')
        elif format == 'long':
            return dt.strftime('%B %d, %Y at %I:%M %p')
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    
    def time_ago(dt):
        """Get human readable time ago"""
        if not dt:
            return ''
        now = datetime.utcnow()
        diff = now - dt
        
        if diff.days > 0:
            return f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours} hour{'s' if hours > 1 else ''} ago"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
        else:
            return "Just now"
    
    return dict(
        format_currency=format_currency,
        format_datetime=format_datetime,
        time_ago=time_ago
    )