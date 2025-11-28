"""
Analytics Routes for Restaurant POS System
Provides comprehensive analytics and reporting functionality
"""

from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from sqlalchemy import func, and_, or_
from decimal import Decimal

from app.analytics import bp
from app.models.order import Order, OrderStatus, OrderType, OrderItem
from app.models.menu import MenuItem, Category
from app.models.user import User
from app.models.customer import Customer
from app import db

@bp.route('/')
@login_required
def dashboard():
    """Analytics dashboard with overview statistics"""
    if not current_user.can_access_manager_features():
        flash('Access denied', 'error')
        return redirect(url_for('main.index'))
    
    # Get date range from request (default to last 30 days)
    days = request.args.get('days', 30, type=int)
    start_date = datetime.now() - timedelta(days=days)
    
    # Sales Analytics
    sales_data = get_sales_analytics(start_date)
    
    # Order Analytics
    order_data = get_order_analytics(start_date)
    
    # Menu Analytics
    menu_data = get_menu_analytics(start_date)
    
    # Customer Analytics
    customer_data = get_customer_analytics(start_date)
    
    return render_template('analytics/dashboard.html',
                         sales_data=sales_data,
                         order_data=order_data,
                         menu_data=menu_data,
                         customer_data=customer_data,
                         days=days)

@bp.route('/sales')
@login_required
def sales_analytics():
    """Detailed sales analytics"""
    if not current_user.can_access_manager_features():
        flash('Access denied', 'error')
        return redirect(url_for('main.index'))
    
    # Get date range
    days = request.args.get('days', 30, type=int)
    start_date = datetime.now() - timedelta(days=days)
    
    # Get detailed sales data
    sales_data = get_sales_analytics(start_date)
    
    return render_template('analytics/sales.html',
                         sales_data=sales_data,
                         days=days)

@bp.route('/orders')
@login_required
def orders_analytics():
    """Detailed order analytics"""
    if not current_user.can_access_manager_features():
        flash('Access denied', 'error')
        return redirect(url_for('main.index'))
    
    # Get date range
    days = request.args.get('days', 30, type=int)
    start_date = datetime.now() - timedelta(days=days)
    
    # Get detailed order data
    order_data = get_order_analytics(start_date)
    
    return render_template('analytics/orders.html',
                         order_data=order_data,
                         days=days)

@bp.route('/menu')
@login_required
def menu_analytics():
    """Menu performance analytics"""
    if not current_user.can_access_manager_features():
        flash('Access denied', 'error')
        return redirect(url_for('main.index'))
    
    # Get date range
    days = request.args.get('days', 30, type=int)
    start_date = datetime.now() - timedelta(days=days)
    
    # Get detailed menu data
    menu_data = get_menu_analytics(start_date)
    
    return render_template('analytics/menu.html',
                         menu_data=menu_data,
                         days=days)

@bp.route('/customers')
@login_required
def customers_analytics():
    """Customer analytics and insights"""
    if not current_user.can_access_manager_features():
        flash('Access denied', 'error')
        return redirect(url_for('main.index'))
    
    # Get date range
    days = request.args.get('days', 30, type=int)
    start_date = datetime.now() - timedelta(days=days)
    
    # Get detailed customer data
    customer_data = get_customer_analytics(start_date)
    
    return render_template('analytics/customers.html',
                         customer_data=customer_data,
                         days=days)

@bp.route('/reports')
@login_required
def reports():
    """Generate and view reports"""
    if not current_user.can_access_manager_features():
        flash('Access denied', 'error')
        return redirect(url_for('main.index'))
    
    return render_template('analytics/reports.html')

# API endpoints for analytics data
@bp.route('/api/sales')
@login_required
def api_sales_data():
    """API endpoint for sales analytics data"""
    if not current_user.can_access_manager_features():
        return jsonify({'error': 'Access denied'}), 403
    
    days = request.args.get('days', 30, type=int)
    start_date = datetime.now() - timedelta(days=days)
    
    sales_data = get_sales_analytics(start_date)
    return jsonify(sales_data)

@bp.route('/api/orders')
@login_required
def api_orders_data():
    """API endpoint for order analytics data"""
    if not current_user.can_access_manager_features():
        return jsonify({'error': 'Access denied'}), 403
    
    days = request.args.get('days', 30, type=int)
    start_date = datetime.now() - timedelta(days=days)
    
    order_data = get_order_analytics(start_date)
    return jsonify(order_data)

@bp.route('/api/menu')
@login_required
def api_menu_data():
    """API endpoint for menu analytics data"""
    if not current_user.can_access_manager_features():
        return jsonify({'error': 'Access denied'}), 403
    
    days = request.args.get('days', 30, type=int)
    start_date = datetime.now() - timedelta(days=days)
    
    menu_data = get_menu_analytics(start_date)
    return jsonify(menu_data)

@bp.route('/api/customers')
@login_required
def api_customers_data():
    """API endpoint for customer analytics data"""
    if not current_user.can_access_manager_features():
        return jsonify({'error': 'Access denied'}), 403
    
    days = request.args.get('days', 30, type=int)
    start_date = datetime.now() - timedelta(days=days)
    
    customer_data = get_customer_analytics(start_date)
    return jsonify(customer_data)

# Helper functions for analytics calculations
def get_sales_analytics(start_date):
    """Get sales analytics data"""
    # Total sales
    total_sales = db.session.query(func.sum(Order.total)).filter(
        Order.created_at >= start_date,
        Order.status.in_([OrderStatus.CONFIRMED, OrderStatus.PREPARING, OrderStatus.READY, OrderStatus.SERVED])
    ).scalar() or Decimal('0')
    
    # Sales by order type
    sales_by_type = db.session.query(
        Order.order_type,
        func.sum(Order.total).label('total_sales'),
        func.count(Order.id).label('order_count')
    ).filter(
        Order.created_at >= start_date,
        Order.status.in_([OrderStatus.CONFIRMED, OrderStatus.PREPARING, OrderStatus.READY, OrderStatus.SERVED])
    ).group_by(Order.order_type).all()
    
    # Daily sales trend
    daily_sales = db.session.query(
        func.date(Order.created_at).label('date'),
        func.sum(Order.total).label('daily_total'),
        func.count(Order.id).label('order_count')
    ).filter(
        Order.created_at >= start_date,
        Order.status.in_([OrderStatus.CONFIRMED, OrderStatus.PREPARING, OrderStatus.READY, OrderStatus.SERVED])
    ).group_by(func.date(Order.created_at)).order_by(func.date(Order.created_at)).all()
    
    # Top selling items (this would require joining with order_items table)
    # For now, return basic structure
    
    return {
        'total_sales': float(total_sales),
        'sales_by_type': [
            {
                'type': order_type.value if order_type else 'unknown',
                'total_sales': float(total_sales or 0),
                'order_count': order_count or 0
            } for order_type, total_sales, order_count in sales_by_type
        ],
        'daily_sales': [
            {
                'date': str(date),
                'total_sales': float(daily_total),
                'order_count': order_count
            } for date, daily_total, order_count in daily_sales
        ]
    }

def get_order_analytics(start_date):
    """Get order analytics data"""
    # Order status distribution
    status_counts = db.session.query(
        Order.status,
        func.count(Order.id).label('count')
    ).filter(Order.created_at >= start_date).group_by(Order.status).all()
    
    # Order type distribution
    type_counts = db.session.query(
        Order.order_type,
        func.count(Order.id).label('count')
    ).filter(Order.created_at >= start_date).group_by(Order.order_type).all()
    
    # Average order value
    avg_order_value = db.session.query(
        func.avg(Order.total)
    ).filter(
        Order.created_at >= start_date,
        Order.status.in_([OrderStatus.CONFIRMED, OrderStatus.PREPARING, OrderStatus.READY, OrderStatus.SERVED])
    ).scalar() or Decimal('0')
    
    # Peak hours
    peak_hours = db.session.query(
        func.extract('hour', Order.created_at).label('hour'),
        func.count(Order.id).label('order_count')
    ).filter(
        Order.created_at >= start_date,
        Order.status.in_([OrderStatus.CONFIRMED, OrderStatus.PREPARING, OrderStatus.READY, OrderStatus.SERVED])
    ).group_by(func.extract('hour', Order.created_at)).order_by(func.count(Order.id).desc()).limit(5).all()
    
    return {
        'status_distribution': [
            {
                'status': status.value if status else 'unknown',
                'count': count
            } for status, count in status_counts
        ],
        'type_distribution': [
            {
                'type': order_type.value if order_type else 'unknown',
                'count': count
            } for order_type, count in type_counts
        ],
        'average_order_value': float(avg_order_value),
        'peak_hours': [
            {
                'hour': hour,
                'order_count': order_count
            } for hour, order_count in peak_hours
        ]
    }

def get_menu_analytics(start_date):
    """Get menu analytics data"""
    # Top categories by sales
    top_categories = db.session.query(
        Category.name,
        func.sum(Order.total).label('total_sales')
    ).join(OrderItem).join(MenuItem).join(Category).filter(
        Order.created_at >= start_date,
        Order.status.in_([OrderStatus.CONFIRMED, OrderStatus.PREPARING, OrderStatus.READY, OrderStatus.SERVED])
    ).group_by(Category.name).order_by(func.sum(Order.total).desc()).limit(10).all()
    
    # Top items by sales
    top_items = db.session.query(
        MenuItem.name,
        func.sum(OrderItem.quantity * OrderItem.unit_price).label('total_sales'),
        func.count(OrderItem.id).label('order_count')
    ).select_from(MenuItem).join(OrderItem).join(Order).filter(
        Order.created_at >= start_date,
        Order.status.in_([OrderStatus.CONFIRMED, OrderStatus.PREPARING, OrderStatus.READY, OrderStatus.SERVED])
    ).group_by(MenuItem.name).order_by(func.sum(OrderItem.quantity * OrderItem.unit_price).desc()).limit(10).all()
    
    return {
        'top_categories': [
            {
                'category': name,
                'total_sales': float(total_sales)
            } for name, total_sales in top_categories
        ],
        'top_items': [
            {
                'item': name,
                'total_sales': float(total_sales),
                'order_count': order_count
            } for name, total_sales, order_count in top_items
        ]
    }

def get_customer_analytics(start_date):
    """Get customer analytics data"""
    # New customers
    new_customers = db.session.query(func.count(Customer.id)).filter(
        Customer.created_at >= start_date
    ).scalar() or 0
    
    # Total customers
    total_customers = db.session.query(func.count(Customer.id)).scalar() or 0
    
    # Customer order frequency
    customer_order_counts = db.session.query(
        Customer.id,
        Customer.first_name,
        Customer.last_name,
        func.count(Order.id).label('order_count'),
        func.sum(Order.total).label('total_spent')
    ).select_from(Customer).join(Order).filter(
        Order.created_at >= start_date,
        Order.status.in_([OrderStatus.CONFIRMED, OrderStatus.PREPARING, OrderStatus.READY, OrderStatus.SERVED])
    ).group_by(Customer.id).order_by(func.count(Order.id).desc()).limit(10).all()
    
    return {
        'new_customers': new_customers,
        'total_customers': total_customers,
        'top_customers': [
            {
                'id': customer_id,
                'name': f"{first_name} {last_name}",
                'order_count': order_count,
                'total_spent': float(total_spent)
            } for customer_id, first_name, last_name, order_count, total_spent in customer_order_counts
        ]
    }