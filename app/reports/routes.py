from flask import render_template, request, redirect, url_for, flash, jsonify, make_response
from flask_login import login_required, current_user
from app.reports import bp
from app.models.order import Order, OrderStatus, Payment
from app.models.menu import MenuItem, Category
from app.models.user import User
from app.models.table import Table
from app.models.gst import GSTSetting
from app.models.accounting import Transaction, Account, Expense
from app.models.restaurant import Restaurant
from app import db
from datetime import datetime, timedelta
import csv
from io import StringIO
from sqlalchemy import func, and_

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
        payments_list = list(order.payments) if order.payments else []
        for payment in payments_list:
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
        payments_list = list(order.payments) if order.payments else []
        for payment in payments_list:
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
        items_list = list(order.items) if order.items else []
        for order_item in items_list:
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

# Enhanced Reporting Routes

@bp.route('/gst')
@login_required
def gst_report():
    """GST compliance report"""
    if not current_user.can_access_manager_features():
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    # Get date range
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    restaurant_id = request.args.get('restaurant_id', type=int)
    
    if start_date:
        start_date = datetime.strptime(start_date, '%Y-%m-%d')
    else:
        start_date = datetime.now() - timedelta(days=30)
    
    if end_date:
        end_date = datetime.strptime(end_date, '%Y-%m-%d')
    else:
        end_date = datetime.now()
    
    # Get GST data
    gst_data = get_gst_report_data(start_date, end_date, restaurant_id)
    restaurants = Restaurant.query.all() if current_user.is_super_admin() else [current_user.restaurant]
    
    return render_template('reports/gst.html',
                         gst_data=gst_data,
                         restaurants=restaurants,
                         start_date=start_date,
                         end_date=end_date,
                         selected_restaurant=restaurant_id)

@bp.route('/accounting')
@login_required
def accounting_report():
    """Accounting and financial reports"""
    if not current_user.can_access_manager_features():
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    # Get date range
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    report_type = request.args.get('type', 'profit_loss')
    
    if start_date:
        start_date = datetime.strptime(start_date, '%Y-%m-%d')
    else:
        start_date = datetime.now() - timedelta(days=30)
    
    if end_date:
        end_date = datetime.strptime(end_date, '%Y-%m-%d')
    else:
        end_date = datetime.now()
    
    # Get accounting data
    accounting_data = get_accounting_report_data(start_date, end_date, report_type)
    
    return render_template('reports/accounting.html',
                         accounting_data=accounting_data,
                         report_type=report_type,
                         start_date=start_date,
                         end_date=end_date)

@bp.route('/expenses')
@login_required
def expenses_report():
    """Expense management report"""
    if not current_user.can_access_manager_features():
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    # Get date range
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    category = request.args.get('category')
    
    if start_date:
        start_date = datetime.strptime(start_date, '%Y-%m-%d')
    else:
        start_date = datetime.now() - timedelta(days=30)
    
    if end_date:
        end_date = datetime.strptime(end_date, '%Y-%m-%d')
    else:
        end_date = datetime.now()
    
    # Get expense data
    expenses = get_expense_report_data(start_date, end_date, category)
    
    return render_template('reports/expenses.html',
                         expenses=expenses,
                         selected_category=category,
                         start_date=start_date,
                         end_date=end_date)

@bp.route('/restaurant-performance')
@login_required
def restaurant_performance():
    """Restaurant performance report (for super admin)"""
    if not current_user.is_super_admin():
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    # Get date range
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    restaurant_id = request.args.get('restaurant_id', type=int)
    
    if start_date:
        start_date = datetime.strptime(start_date, '%Y-%m-%d')
    else:
        start_date = datetime.now() - timedelta(days=30)
    
    if end_date:
        end_date = datetime.strptime(end_date, '%Y-%m-%d')
    else:
        end_date = datetime.now()
    
    # Get performance data
    performance_data = get_restaurant_performance_data(start_date, end_date, restaurant_id)
    restaurants = Restaurant.query.all()
    
    return render_template('reports/restaurant_performance.html',
                         performance_data=performance_data,
                         restaurants=restaurants,
                         start_date=start_date,
                         end_date=end_date,
                         selected_restaurant=restaurant_id)

@bp.route('/export/gst')
@login_required
def export_gst():
    """Export GST report as CSV"""
    if not current_user.can_access_manager_features():
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    # Get date range
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    restaurant_id = request.args.get('restaurant_id', type=int)
    
    if start_date:
        start_date = datetime.strptime(start_date, '%Y-%m-%d')
    else:
        start_date = datetime.now() - timedelta(days=30)
    
    if end_date:
        end_date = datetime.strptime(end_date, '%Y-%m-%d')
    else:
        end_date = datetime.now()
    
    # Get GST data
    gst_data = get_gst_report_data(start_date, end_date, restaurant_id)
    
    # Create CSV
    output = StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow(['Date', 'Order Number', 'Subtotal', 'CGST', 'SGST', 'IGST', 'CESS', 'Total GST', 'Total'])
    
    # Write data
    for order in gst_data['orders']:
        writer.writerow([
            order.created_at.strftime('%Y-%m-%d'),
            order.order_number,
            order.subtotal,
            order.cgst_amount,
            order.sgst_amount,
            order.igst_amount,
            order.cess_amount,
            order.tax_amount,
            order.total
        ])
    
    # Create response
    output.seek(0)
    response = make_response(output.getvalue())
    response.headers['Content-Disposition'] = f'attachment; filename=gst_report_{start_date.strftime("%Y%m%d")}_to_{end_date.strftime("%Y%m%d")}.csv'
    response.headers['Content-type'] = 'text/csv'
    
    return response

@bp.route('/export/accounting')
@login_required
def export_accounting():
    """Export accounting report as CSV"""
    if not current_user.can_access_manager_features():
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    # Get date range
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    report_type = request.args.get('type', 'profit_loss')
    
    if start_date:
        start_date = datetime.strptime(start_date, '%Y-%m-%d')
    else:
        start_date = datetime.now() - timedelta(days=30)
    
    if end_date:
        end_date = datetime.strptime(end_date, '%Y-%m-%d')
    else:
        end_date = datetime.now()
    
    # Get accounting data
    accounting_data = get_accounting_report_data(start_date, end_date, report_type)
    
    # Create CSV
    output = StringIO()
    writer = csv.writer(output)
    
    if report_type == 'profit_loss':
        writer.writerow(['Category', 'Amount', 'Type'])
        for item in accounting_data['profit_loss_items']:
            writer.writerow([item['name'], item['amount'], item['type']])
    elif report_type == 'balance_sheet':
        writer.writerow(['Account', 'Balance', 'Type'])
        for item in accounting_data['balance_sheet_items']:
            writer.writerow([item['name'], item['balance'], item['type']])
    
    # Create response
    output.seek(0)
    response = make_response(output.getvalue())
    response.headers['Content-Disposition'] = f'attachment; filename=accounting_{report_type}_{start_date.strftime("%Y%m%d")}_to_{end_date.strftime("%Y%m%d")}.csv'
    response.headers['Content-type'] = 'text/csv'
    
    return response

# Enhanced Helper Functions

def get_gst_report_data(start_date, end_date, restaurant_id=None):
    """Get GST compliance report data"""
    query = Order.query.filter(
        Order.created_at >= start_date,
        Order.created_at <= end_date,
        Order.status == OrderStatus.SERVED
    )
    
    if restaurant_id:
        query = query.filter_by(restaurant_id=restaurant_id)
    
    orders = query.all()
    
    # Calculate GST totals
    total_subtotal = sum(float(order.subtotal) for order in orders)
    total_cgst = sum(float(order.cgst_amount) for order in orders)
    total_sgst = sum(float(order.sgst_amount) for order in orders)
    total_igst = sum(float(order.igst_amount) for order in orders)
    total_cess = sum(float(order.cess_amount) for order in orders)
    total_gst = sum(float(order.tax_amount) for order in orders)
    total_amount = sum(float(order.total) for order in orders)
    
    return {
        'orders': orders,
        'total_subtotal': total_subtotal,
        'total_cgst': total_cgst,
        'total_sgst': total_sgst,
        'total_igst': total_igst,
        'total_cess': total_cess,
        'total_gst': total_gst,
        'total_amount': total_amount,
        'order_count': len(orders)
    }

def get_accounting_report_data(start_date, end_date, report_type='profit_loss'):
    """Get accounting report data"""
    if report_type == 'profit_loss':
        # Get revenue
        revenue_orders = Order.query.filter(
            Order.created_at >= start_date,
            Order.created_at <= end_date,
            Order.status == OrderStatus.SERVED
        ).all()
        
        total_revenue = sum(float(order.total) for order in revenue_orders)
        
        # Get expenses
        expenses = Expense.query.filter(
            Expense.created_at >= start_date,
            Expense.created_at <= end_date
        ).all()
        
        total_expenses = sum(float(expense.amount) for expense in expenses)
        
        # Get transactions
        transactions = Transaction.query.filter(
            Transaction.created_at >= start_date,
            Transaction.created_at <= end_date
        ).all()
        
        return {
            'profit_loss_items': [
                {'name': 'Total Revenue', 'amount': total_revenue, 'type': 'Revenue'},
                {'name': 'Total Expenses', 'amount': total_expenses, 'type': 'Expense'},
                {'name': 'Net Profit/Loss', 'amount': total_revenue - total_expenses, 'type': 'Profit'}
            ],
            'transactions': transactions
        }
    
    elif report_type == 'balance_sheet':
        # Get account balances
        accounts = Account.query.all()
        balance_sheet_items = []
        
        for account in accounts:
            # Calculate account balance from transactions
            debit_total = db.session.query(func.sum(Transaction.amount)).filter_by(
                debit_account_id=account.id
            ).scalar() or 0
            
            credit_total = db.session.query(func.sum(Transaction.amount)).filter_by(
                credit_account_id=account.id
            ).scalar() or 0
            
            balance = debit_total - credit_total
            
            balance_sheet_items.append({
                'name': account.name,
                'balance': balance,
                'type': account.account_type
            })
        
        return {
            'balance_sheet_items': balance_sheet_items
        }
    
    return {}

def get_expense_report_data(start_date, end_date, category=None):
    """Get expense report data"""
    query = Expense.query.filter(
        Expense.created_at >= start_date,
        Expense.created_at <= end_date
    )
    
    if category:
        query = query.filter_by(category=category)
    
    expenses = query.order_by(Expense.created_at.desc()).all()
    
    # Calculate totals by category
    category_totals = {}
    for expense in expenses:
        if expense.category not in category_totals:
            category_totals[expense.category] = 0
        category_totals[expense.category] += float(expense.amount)
    
    return {
        'expenses': expenses,
        'category_totals': category_totals,
        'total_expenses': sum(float(expense.amount) for expense in expenses)
    }

def get_restaurant_performance_data(start_date, end_date, restaurant_id=None):
    """Get restaurant performance data"""
    query = Restaurant.query
    
    if restaurant_id:
        query = query.filter_by(id=restaurant_id)
    
    restaurants = query.all()
    
    performance_data = []
    
    for restaurant in restaurants:
        # Get orders for this restaurant
        orders = Order.query.filter(
            Order.restaurant_id == restaurant.id,
            Order.created_at >= start_date,
            Order.created_at <= end_date
        ).all()
        
        # Calculate metrics
        total_orders = len(orders)
        total_revenue = sum(float(order.total) for order in orders)
        average_order_value = total_revenue / total_orders if total_orders > 0 else 0
        
        # Get staff count
        staff_count = User.query.filter_by(restaurant_id=restaurant.id, is_active=True).count()
        
        performance_data.append({
            'restaurant': restaurant,
            'total_orders': total_orders,
            'total_revenue': total_revenue,
            'average_order_value': average_order_value,
            'staff_count': staff_count
        })
    
    return performance_data