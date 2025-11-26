from flask import render_template, request, redirect, url_for, flash, jsonify, make_response
from flask_login import login_required, current_user
from app.reports import bp
from app.models.order import Order, OrderStatus, Payment
from app.models.menu import MenuItem, Category
from app.models.user import User
from app.models.table import Table
from app import db
from datetime import datetime, timedelta
import csv
from io import StringIO

@bp.route('/dashboard')
@login_required
def dashboard():
    """Reports dashboard"""
    if not current_user.can_access_manager_features():
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    # Get date range
    days = request.args.get('days', 7, type=int)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    # Calculate statistics
    stats = calculate_report_stats(start_date, end_date)
    
    return render_template('reports/dashboard.html', stats=stats, days=days)

@bp.route('/sales')
@login_required
def sales_report():
    """Sales report"""
    if not current_user.can_access_manager_features():
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    # Get date range
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    if start_date:
        start_date = datetime.strptime(start_date, '%Y-%m-%d')
    else:
        start_date = datetime.now() - timedelta(days=7)
    
    if end_date:
        end_date = datetime.strptime(end_date, '%Y-%m-%d')
    else:
        end_date = datetime.now()
    
    # Get orders in date range
    orders = Order.query.filter(
        Order.created_at >= start_date,
        Order.created_at <= end_date
    ).order_by(Order.created_at.desc()).all()
    
    return render_template('reports/sales.html', orders=orders, start_date=start_date, end_date=end_date)

@bp.route('/items')
@login_required
def items_report():
    """Menu items performance report"""
    if not current_user.can_access_manager_features():
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    # Get date range
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    category_id = request.args.get('category_id', type=int)
    
    if start_date:
        start_date = datetime.strptime(start_date, '%Y-%m-%d')
    else:
        start_date = datetime.now() - timedelta(days=30)
    
    if end_date:
        end_date = datetime.strptime(end_date, '%Y-%m-%d')
    else:
        end_date = datetime.now()
    
    # Get items sold in date range
    items_sold = get_items_sold(start_date, end_date, category_id)
    
    categories = Category.query.order_by(Category.display_order).all()
    
    return render_template('reports/items.html', 
                         items_sold=items_sold, 
                         categories=categories,
                         start_date=start_date,
                         end_date=end_date,
                         selected_category=category_id)

@bp.route('/staff')
@login_required
def staff_report():
    """Staff performance report"""
    if not current_user.can_access_manager_features():
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    # Get date range
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    user_id = request.args.get('user_id', type=int)
    
    if start_date:
        start_date = datetime.strptime(start_date, '%Y-%m-%d')
    else:
        start_date = datetime.now() - timedelta(days=7)
    
    if end_date:
        end_date = datetime.strptime(end_date, '%Y-%m-%d')
    else:
        end_date = datetime.now()
    
    # Get staff performance data
    staff_stats = get_staff_performance(start_date, end_date, user_id)
    users = User.query.filter_by(is_active=True).all()
    
    return render_template('reports/staff.html', 
                         staff_stats=staff_stats,
                         users=users,
                         start_date=start_date,
                         end_date=end_date,
                         selected_user=user_id)

@bp.route('/export/sales')
@login_required
def export_sales():
    """Export sales data as CSV"""
    if not current_user.can_access_manager_features():
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    # Get date range
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    if start_date:
        start_date = datetime.strptime(start_date, '%Y-%m-%d')
    else:
        start_date = datetime.now() - timedelta(days=30)
    
    if end_date:
        end_date = datetime.strptime(end_date, '%Y-%m-%d')
    else:
        end_date = datetime.now()
    
    # Get orders
    orders = Order.query.filter(
        Order.created_at >= start_date,
        Order.created_at <= end_date
    ).order_by(Order.created_at.desc()).all()
    
    # Create CSV
    output = StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow(['Order Number', 'Date', 'Status', 'Subtotal', 'Tax', 'Total', 'Payment Method'])
    
    # Write data
    for order in orders:
        for payment in order.payments:
            writer.writerow([
                order.order_number,
                order.created_at.strftime('%Y-%m-%d %H:%M'),
                order.status.value,
                order.subtotal,
                order.tax_amount,
                order.total,
                payment.method.value
            ])
    
    # Create response
    output.seek(0)
    response = make_response(output.getvalue())
    response.headers['Content-Disposition'] = f'attachment; filename=sales_{start_date.strftime("%Y%m%d")}_to_{end_date.strftime("%Y%m%d")}.csv'
    response.headers['Content-type'] = 'text/csv'
    
    return response

# Helper functions
def calculate_report_stats(start_date, end_date):
    """Calculate report statistics"""
    orders = Order.query.filter(
        Order.created_at >= start_date,
        Order.created_at <= end_date
    ).all()
    
    # Basic stats
    total_orders = len(orders)
    total_revenue = sum(float(order.total) for order in orders)
    total_tax = sum(float(order.tax_amount) for order in orders)
    
    # Status breakdown
    pending_orders = len([o for o in orders if o.status == OrderStatus.PENDING])
    confirmed_orders = len([o for o in orders if o.status == OrderStatus.CONFIRMED])
    completed_orders = len([o for o in orders if o.status == OrderStatus.SERVED])
    
    # Payment method breakdown
    payment_breakdown = {}
    for order in orders:
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
    
    return {
        'total_orders': total_orders,
        'total_revenue': total_revenue,
        'total_tax': total_tax,
        'pending_orders': pending_orders,
        'confirmed_orders': confirmed_orders,
        'completed_orders': completed_orders,
        'payment_breakdown': payment_breakdown,
        'daily_stats': daily_stats,
        'average_order_value': total_revenue / total_orders if total_orders > 0 else 0
    }

def get_items_sold(start_date, end_date, category_id=None):
    """Get items sold in date range"""
    # Query orders in date range
    orders = Order.query.filter(
        Order.created_at >= start_date,
        Order.created_at <= end_date,
        Order.status == OrderStatus.SERVED
    ).all()
    
    # Aggregate items sold
    items_sold = {}
    
    for order in orders:
        for order_item in order.items:
            item_key = order_item.item_id
            
            if item_key not in items_sold:
                items_sold[item_key] = {
                    'item': order_item.menu_item,
                    'quantity': 0,
                    'revenue': 0.0
                }
            
            items_sold[item_key]['quantity'] += order_item.quantity
            items_sold[item_key]['revenue'] += order_item.get_total_price()
    
    # Filter by category if specified
    if category_id:
        items_sold = {
            key: data for key, data in items_sold.items()
            if data['item'].category_id == category_id
        }
    
    return items_sold

def get_staff_performance(start_date, end_date, user_id=None):
    """Get staff performance statistics"""
    query = Order.query.filter(
        Order.created_at >= start_date,
        Order.created_at <= end_date
    )
    
    if user_id:
        query = query.filter_by(user_id=user_id)
    
    orders = query.all()
    
    # Aggregate by user
    staff_stats = {}
    
    for order in orders:
        user_key = order.user_id
        
        if user_key not in staff_stats:
            staff_stats[user_key] = {
                'user': order.user,
                'orders': 0,
                'revenue': 0.0
            }
        
        staff_stats[user_key]['orders'] += 1
        staff_stats[user_key]['revenue'] += float(order.total)
    
    return staff_stats

# API endpoints
@bp.route('/api/stats')
@login_required
def get_api_stats():
    """API endpoint to get statistics"""
    if not current_user.can_access_manager_features():
        return jsonify({'error': 'Access denied'}), 403
    
    days = request.args.get('days', 7, type=int)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    stats = calculate_report_stats(start_date, end_date)
    
    return jsonify(stats)

@bp.route('/api/items-sold')
@login_required
def get_api_items_sold():
    """API endpoint to get items sold"""
    if not current_user.can_access_manager_features():
        return jsonify({'error': 'Access denied'}), 403
    
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    category_id = request.args.get('category_id', type=int)
    
    if start_date:
        start_date = datetime.strptime(start_date, '%Y-%m-%d')
    else:
        start_date = datetime.now() - timedelta(days=30)
    
    if end_date:
        end_date = datetime.strptime(end_date, '%Y-%m-%d')
    else:
        end_date = datetime.now()
    
    items_sold = get_items_sold(start_date, end_date, category_id)
    
    # Convert to API format
    api_items = []
    for item_id, data in items_sold.items():
        api_items.append({
            'item_id': item_id,
            'item_name': data['item'].name,
            'category': data['item'].category.name if data['item'].category else None,
            'quantity_sold': data['quantity'],
            'revenue': data['revenue']
        })
    
    return jsonify({'items': api_items})