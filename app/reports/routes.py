from flask import render_template, request, redirect, url_for, flash, jsonify, make_response
from flask_login import login_required, current_user
from app.reports import bp
from app.models.order import Order, OrderStatus, Payment, SplitBill
from app.models.menu import MenuItem, Category
from app.models.user import User
from app.models.table import Table
from app.models.gst import GSTSetting
from app.models.accounting import Transaction, Account, Expense
from app.models.restaurant import Restaurant
from app.models.report_schedule import ReportSchedule, ReportExecution, ReportType, ScheduleFrequency, DeliveryMethod
from app import db
from datetime import datetime, timedelta
import csv
import json
from io import StringIO
from sqlalchemy import func, and_
import os
import tempfile

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
    
    # Process chart data for initial display
    revenue_data = []
    max_revenue = 0
    
    for date_str, day_stats in (stats.get('daily_stats') or {}).items():
        revenue = day_stats.get('revenue', 0)
        revenue_data.append({
            'date': datetime.strptime(date_str, '%Y-%m-%d').strftime('%b %d'),
            'revenue': revenue
        })
        max_revenue = max(max_revenue, revenue)
    
    if max_revenue == 0:
        max_revenue = 1
    
    payment_breakdown = stats.get('payment_breakdown', {})
    total_payments = sum(payment_breakdown.values()) or 1
    
    return render_template('reports/dashboard.html',
                         stats=stats,
                         days=days,
                         revenue_data=revenue_data,
                         max_revenue=max_revenue,
                         payment_breakdown=payment_breakdown,
                         total_payments=total_payments)

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
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    if start_date:
        start_date = datetime.strptime(start_date, '%Y-%m-%d')
    else:
        start_date = datetime.now() - timedelta(days=days)
    
    if end_date:
        end_date = datetime.strptime(end_date, '%Y-%m-%d')
    else:
        end_date = datetime.now()
    
    stats = calculate_report_stats(start_date, end_date)
    
    # Return partial template for HTMX
    return render_template('reports/partials/stats.html', stats=stats)

@bp.route('/api/charts')
@login_required
def get_api_charts():
    """API endpoint to get charts data"""
    if not current_user.can_access_manager_features():
        return jsonify({'error': 'Access denied'}), 403
    
    days = request.args.get('days', 7, type=int)
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    if start_date:
        start_date = datetime.strptime(start_date, '%Y-%m-%d')
    else:
        start_date = datetime.now() - timedelta(days=days)
    
    if end_date:
        end_date = datetime.strptime(end_date, '%Y-%m-%d')
    else:
        end_date = datetime.now()
    
    stats = calculate_report_stats(start_date, end_date)
    
    # Process chart data for API response
    revenue_data = []
    max_revenue = 0
    
    for date_str, day_stats in (stats.get('daily_stats') or {}).items():
        revenue = day_stats.get('revenue', 0)
        revenue_data.append({
            'date': datetime.strptime(date_str, '%Y-%m-%d').strftime('%b %d'),
            'revenue': revenue
        })
        max_revenue = max(max_revenue, revenue)
    
    if max_revenue == 0:
        max_revenue = 1
    
    payment_breakdown = stats.get('payment_breakdown', {})
    total_payments = sum(payment_breakdown.values()) or 1
    
    return render_template('reports/partials/charts.html',
                         revenue_data=revenue_data,
                         max_revenue=max_revenue,
                         payment_breakdown=payment_breakdown,
                         total_payments=total_payments)

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

@bp.route('/split-bills')
@login_required
def split_bills_report():
    """Split bills report"""
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
    
    # Get split bills data
    split_bills_data = get_split_bills_report_data(start_date, end_date)
    
    return render_template('reports/split_bills.html',
                         split_bills_data=split_bills_data,
                         start_date=start_date,
                         end_date=end_date)

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

@bp.route('/export/split-bills')
@login_required
def export_split_bills():
    """Export split bills data as CSV"""
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
    
    # Get split bills data
    split_bills_data = get_split_bills_report_data(start_date, end_date)
    
    # Create CSV
    output = StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow(['Date', 'Order Number', 'Split Type', 'Amount', 'Payment Method', 'Staff', 'Details'])
    
    # Write data
    for split_bill in split_bills_data['split_bills']:
        writer.writerow([
            split_bill.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            split_bill.order.order_number if split_bill.order else 'N/A',
            split_bill.split_type,
            split_bill.amount,
            split_bill.payment_method,
            split_bill.user.name if split_bill.user else 'N/A',
            split_bill.details
        ])
    
    # Create response
    output.seek(0)
    response = make_response(output.getvalue())
    response.headers['Content-Disposition'] = f'attachment; filename=split_bills_{start_date.strftime("%Y%m%d")}_to_{end_date.strftime("%Y%m%d")}.csv'
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

def get_split_bills_report_data(start_date, end_date):
    """Get split bills report data"""
    # Get split bills in date range
    split_bills = SplitBill.query.filter(
        SplitBill.created_at >= start_date,
        SplitBill.created_at <= end_date
    ).order_by(SplitBill.created_at.desc()).all()
    
    # Calculate statistics
    total_split_bills = len(split_bills)
    total_split_amount = sum(float(sb.amount) for sb in split_bills)
    
    # Split type breakdown
    split_type_counts = {}
    split_type_amounts = {}
    for sb in split_bills:
        split_type = sb.split_type
        if split_type not in split_type_counts:
            split_type_counts[split_type] = 0
            split_type_amounts[split_type] = 0
        split_type_counts[split_type] += 1
        split_type_amounts[split_type] += float(sb.amount)
    
    # Payment method breakdown
    payment_method_counts = {}
    payment_method_amounts = {}
    for sb in split_bills:
        payment_method = sb.payment_method
        if payment_method not in payment_method_counts:
            payment_method_counts[payment_method] = 0
            payment_method_amounts[payment_method] = 0
        payment_method_counts[payment_method] += 1
        payment_method_amounts[payment_method] += float(sb.amount)
    
    # Daily breakdown
    daily_stats = {}
    current_date = start_date
    while current_date <= end_date:
        day_splits = [sb for sb in split_bills if sb.created_at.date() == current_date.date()]
        daily_amount = sum(float(sb.amount) for sb in day_splits)
        
        daily_stats[current_date.strftime('%Y-%m-%d')] = {
            'count': len(day_splits),
            'amount': daily_amount
        }
        current_date += timedelta(days=1)
    
    return {
        'split_bills': split_bills,
        'total_split_bills': total_split_bills,
        'total_split_amount': total_split_amount,
        'split_type_counts': split_type_counts,
        'split_type_amounts': split_type_amounts,
        'payment_method_counts': payment_method_counts,
        'payment_method_amounts': payment_method_amounts,
        'daily_stats': daily_stats
    }

# Report Scheduling Routes

@bp.route('/schedule')
@login_required
def schedule_list():
    """List all report schedules"""
    if not current_user.can_access_manager_features():
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    schedules = ReportSchedule.query.filter_by(created_by=current_user.id).order_by(ReportSchedule.created_at.desc()).all()
    
    return render_template('reports/schedule_list.html', schedules=schedules)

@bp.route('/schedule/new')
@login_required
def schedule_new():
    """Create new report schedule"""
    if not current_user.can_access_manager_features():
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    return render_template('reports/schedule_form.html',
                         report_types=ReportType,
                         frequencies=ScheduleFrequency,
                         delivery_methods=DeliveryMethod)

@bp.route('/schedule/create', methods=['POST'])
@login_required
def schedule_create():
    """Create a new report schedule"""
    if not current_user.can_access_manager_features():
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    try:
        schedule = ReportSchedule(
            name=request.form.get('name'),
            description=request.form.get('description'),
            report_type=ReportType(request.form.get('report_type')),
            frequency=ScheduleFrequency(request.form.get('frequency')),
            delivery_method=DeliveryMethod(request.form.get('delivery_method')),
            is_active='is_active' in request.form,
            email_subject=request.form.get('email_subject'),
            email_message=request.form.get('email_message'),
            created_by=current_user.id
        )
        
        # Set parameters
        params = {}
        if request.form.get('start_date'):
            params['start_date'] = request.form.get('start_date')
        if request.form.get('end_date'):
            params['end_date'] = request.form.get('end_date')
        category_id = request.form.get('category_id')
        if category_id and category_id.strip():
            params['category_id'] = int(category_id)
        user_id = request.form.get('user_id')
        if user_id and user_id.strip():
            params['user_id'] = int(user_id)
        restaurant_id = request.form.get('restaurant_id')
        if restaurant_id and restaurant_id.strip():
            params['restaurant_id'] = int(restaurant_id)
        
        schedule.set_parameters(params)
        
        # Set email recipients
        recipients = [email.strip() for email in request.form.get('email_recipients', '').split(',') if email.strip()]
        schedule.set_email_recipients(recipients)
        
        # Calculate next run time
        schedule.next_run = schedule.calculate_next_run()
        
        db.session.add(schedule)
        db.session.commit()
        
        flash('Report schedule created successfully!', 'success')
        return redirect(url_for('reports.schedule_list'))
        
    except Exception as e:
        flash(f'Error creating schedule: {str(e)}', 'error')
        return redirect(url_for('reports.schedule_new'))

@bp.route('/schedule/<int:id>/edit')
@login_required
def schedule_edit(id):
    """Edit report schedule"""
    if not current_user.can_access_manager_features():
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    schedule = ReportSchedule.query.get_or_404(id)
    
    # Check ownership
    if schedule.created_by != current_user.id and not current_user.is_admin():
        flash('Access denied', 'error')
        return redirect(url_for('reports.schedule_list'))
    
    return render_template('reports/schedule_form.html',
                         schedule=schedule,
                         report_types=ReportType,
                         frequencies=ScheduleFrequency,
                         delivery_methods=DeliveryMethod)

@bp.route('/schedule/<int:id>/update', methods=['POST'])
@login_required
def schedule_update(id):
    """Update report schedule"""
    if not current_user.can_access_manager_features():
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    schedule = ReportSchedule.query.get_or_404(id)
    
    # Check ownership
    if schedule.created_by != current_user.id and not current_user.is_admin():
        flash('Access denied', 'error')
        return redirect(url_for('reports.schedule_list'))
    
    try:
        schedule.name = request.form.get('name')
        schedule.description = request.form.get('description')
        schedule.report_type = ReportType(request.form.get('report_type'))
        schedule.frequency = ScheduleFrequency(request.form.get('frequency'))
        schedule.delivery_method = DeliveryMethod(request.form.get('delivery_method'))
        schedule.is_active = 'is_active' in request.form
        schedule.email_subject = request.form.get('email_subject')
        schedule.email_message = request.form.get('email_message')
        
        # Set parameters
        params = {}
        if request.form.get('start_date'):
            params['start_date'] = request.form.get('start_date')
        if request.form.get('end_date'):
            params['end_date'] = request.form.get('end_date')
        category_id = request.form.get('category_id')
        if category_id and category_id.strip():
            params['category_id'] = int(category_id)
        user_id = request.form.get('user_id')
        if user_id and user_id.strip():
            params['user_id'] = int(user_id)
        restaurant_id = request.form.get('restaurant_id')
        if restaurant_id and restaurant_id.strip():
            params['restaurant_id'] = int(restaurant_id)
        
        schedule.set_parameters(params)
        
        # Set email recipients
        recipients = [email.strip() for email in request.form.get('email_recipients', '').split(',') if email.strip()]
        schedule.set_email_recipients(recipients)
        
        # Recalculate next run time
        schedule.next_run = schedule.calculate_next_run()
        
        db.session.commit()
        
        flash('Report schedule updated successfully!', 'success')
        return redirect(url_for('reports.schedule_list'))
        
    except Exception as e:
        flash(f'Error updating schedule: {str(e)}', 'error')
        return redirect(url_for('reports.schedule_edit', id=id))

@bp.route('/schedule/<int:id>/delete', methods=['POST'])
@login_required
def schedule_delete(id):
    """Delete report schedule"""
    if not current_user.can_access_manager_features():
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    schedule = ReportSchedule.query.get_or_404(id)
    
    # Check ownership
    if schedule.created_by != current_user.id and not current_user.is_admin():
        flash('Access denied', 'error')
        return redirect(url_for('reports.schedule_list'))
    
    try:
        db.session.delete(schedule)
        db.session.commit()
        
        flash('Report schedule deleted successfully!', 'success')
        
    except Exception as e:
        flash(f'Error deleting schedule: {str(e)}', 'error')
    
    return redirect(url_for('reports.schedule_list'))

@bp.route('/schedule/<int:id>/run', methods=['POST'])
@login_required
def schedule_run_now(id):
    """Run scheduled report immediately"""
    if not current_user.can_access_manager_features():
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    schedule = ReportSchedule.query.get_or_404(id)
    
    # Check ownership
    if schedule.created_by != current_user.id and not current_user.is_admin():
        flash('Access denied', 'error')
        return redirect(url_for('reports.schedule_list'))
    
    try:
        # Create execution record
        execution = ReportExecution(
            schedule_id=schedule.id,
            report_type=schedule.report_type,
            status='pending'
        )
        execution.set_parameters(schedule.get_parameters())
        
        db.session.add(execution)
        db.session.commit()
        
        # Process the report
        process_scheduled_report(execution.id)
        
        flash('Report execution started!', 'success')
        
    except Exception as e:
        flash(f'Error running report: {str(e)}', 'error')
    
    return redirect(url_for('reports.schedule_list'))

@bp.route('/schedule/executions')
@login_required
def schedule_executions():
    """View report execution history"""
    if not current_user.can_access_manager_features():
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    executions = ReportExecution.query.join(ReportSchedule).filter(
        ReportSchedule.created_by == current_user.id
    ).order_by(ReportExecution.created_at.desc()).all()
    
    return render_template('reports/executions.html', executions=executions)

# Print Summary Routes

@bp.route('/print-summary')
@login_required
def print_summary():
    """Generate print summary for reports"""
    if not current_user.can_access_manager_features():
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    # Get date range
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    report_type = request.args.get('type', 'sales')
    
    if start_date:
        start_date = datetime.strptime(start_date, '%Y-%m-%d')
    else:
        start_date = datetime.now() - timedelta(days=7)
    
    if end_date:
        end_date = datetime.strptime(end_date, '%Y-%m-%d')
    else:
        end_date = datetime.now()
    
    # Get report data based on type
    if report_type == 'sales':
        data = get_sales_summary_data(start_date, end_date)
    elif report_type == 'items':
        data = get_items_summary_data(start_date, end_date)
    elif report_type == 'staff':
        data = get_staff_summary_data(start_date, end_date)
    else:
        data = get_sales_summary_data(start_date, end_date)
    
    return render_template('reports/print_summary.html',
                         data=data,
                         start_date=start_date,
                         end_date=end_date,
                         report_type=report_type)

# Helper Functions for Report Scheduling

def process_scheduled_report(execution_id):
    """Process a scheduled report execution"""
    from flask import current_app
    import threading
    
    def run_report():
        with current_app.app_context():
            execution = ReportExecution.query.get(execution_id)
            if not execution:
                return
            
            try:
                execution.mark_as_started()
                db.session.commit()
                
                schedule = execution.schedule
                params = execution.get_parameters()
                
                # Generate report based on type
                if execution.report_type == ReportType.SALES:
                    file_path = generate_sales_report(params, execution.id)
                elif execution.report_type == ReportType.ITEMS:
                    file_path = generate_items_report(params, execution.id)
                elif execution.report_type == ReportType.STAFF:
                    file_path = generate_staff_report(params, execution.id)
                elif execution.report_type == ReportType.GST:
                    file_path = generate_gst_report(params, execution.id)
                elif execution.report_type == ReportType.ACCOUNTING:
                    file_path = generate_accounting_report(params, execution.id)
                elif execution.report_type == ReportType.EXPENSES:
                    file_path = generate_expenses_report(params, execution.id)
                elif execution.report_type == ReportType.RESTAURANT_PERFORMANCE:
                    file_path = generate_restaurant_performance_report(params, execution.id)
                else:
                    raise Exception(f"Unknown report type: {execution.report_type}")
                
                # Get file size
                file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
                
                execution.mark_as_completed(file_path=file_path, file_size=file_size)
                
                # Send email if needed
                if schedule.delivery_method in [DeliveryMethod.EMAIL, DeliveryMethod.BOTH]:
                    send_report_email(execution, file_path)
                
                # Update schedule
                schedule.mark_as_run()
                
                db.session.commit()
                
            except Exception as e:
                execution.mark_as_failed(str(e))
                db.session.commit()
    
    # Run in background thread
    thread = threading.Thread(target=run_report)
    thread.daemon = True
    thread.start()

def generate_sales_report(params, execution_id):
    """Generate sales report CSV"""
    start_date = datetime.strptime(params.get('start_date'), '%Y-%m-%d') if params.get('start_date') else datetime.now() - timedelta(days=30)
    end_date = datetime.strptime(params.get('end_date'), '%Y-%m-%d') if params.get('end_date') else datetime.now()
    
    orders = Order.query.filter(
        Order.created_at >= start_date,
        Order.created_at <= end_date
    ).order_by(Order.created_at.desc()).all()
    
    # Create temporary file
    temp_dir = tempfile.gettempdir()
    filename = f"sales_report_{execution_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    file_path = os.path.join(temp_dir, filename)
    
    with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        
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
    
    return file_path

def generate_items_report(params, execution_id):
    """Generate items report CSV"""
    start_date = datetime.strptime(params.get('start_date'), '%Y-%m-%d') if params.get('start_date') else datetime.now() - timedelta(days=30)
    end_date = datetime.strptime(params.get('end_date'), '%Y-%m-%d') if params.get('end_date') else datetime.now()
    category_id = params.get('category_id')
    
    items_sold = get_items_sold(start_date, end_date, category_id)
    
    # Create temporary file
    temp_dir = tempfile.gettempdir()
    filename = f"items_report_{execution_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    file_path = os.path.join(temp_dir, filename)
    
    with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        
        # Write header
        writer.writerow(['Item Name', 'Category', 'Quantity Sold', 'Revenue'])
        
        # Write data
        for item_id, data in items_sold.items():
            writer.writerow([
                data['item'].name,
                data['item'].category.name if data['item'].category else 'N/A',
                data['quantity'],
                data['revenue']
            ])
    
    return file_path

def generate_staff_report(params, execution_id):
    """Generate staff report CSV"""
    start_date = datetime.strptime(params.get('start_date'), '%Y-%m-%d') if params.get('start_date') else datetime.now() - timedelta(days=30)
    end_date = datetime.strptime(params.get('end_date'), '%Y-%m-%d') if params.get('end_date') else datetime.now()
    user_id = params.get('user_id')
    
    staff_stats = get_staff_performance(start_date, end_date, user_id)
    
    # Create temporary file
    temp_dir = tempfile.gettempdir()
    filename = f"staff_report_{execution_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    file_path = os.path.join(temp_dir, filename)
    
    with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        
        # Write header
        writer.writerow(['Staff Name', 'Orders Processed', 'Total Revenue'])
        
        # Write data
        for user_id, data in staff_stats.items():
            writer.writerow([
                data['user'].name,
                data['orders'],
                data['revenue']
            ])
    
    return file_path

def generate_gst_report(params, execution_id):
    """Generate GST report CSV"""
    start_date = datetime.strptime(params.get('start_date'), '%Y-%m-%d') if params.get('start_date') else datetime.now() - timedelta(days=30)
    end_date = datetime.strptime(params.get('end_date'), '%Y-%m-%d') if params.get('end_date') else datetime.now()
    restaurant_id = params.get('restaurant_id')
    
    gst_data = get_gst_report_data(start_date, end_date, restaurant_id)
    
    # Create temporary file
    temp_dir = tempfile.gettempdir()
    filename = f"gst_report_{execution_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    file_path = os.path.join(temp_dir, filename)
    
    with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        
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
    
    return file_path

def generate_accounting_report(params, execution_id):
    """Generate accounting report CSV"""
    start_date = datetime.strptime(params.get('start_date'), '%Y-%m-%d') if params.get('start_date') else datetime.now() - timedelta(days=30)
    end_date = datetime.strptime(params.get('end_date'), '%Y-%m-%d') if params.get('end_date') else datetime.now()
    report_type = params.get('report_type', 'profit_loss')
    
    accounting_data = get_accounting_report_data(start_date, end_date, report_type)
    
    # Create temporary file
    temp_dir = tempfile.gettempdir()
    filename = f"accounting_report_{execution_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    file_path = os.path.join(temp_dir, filename)
    
    with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        
        if report_type == 'profit_loss':
            writer.writerow(['Category', 'Amount', 'Type'])
            for item in accounting_data['profit_loss_items']:
                writer.writerow([item['name'], item['amount'], item['type']])
        elif report_type == 'balance_sheet':
            writer.writerow(['Account', 'Balance', 'Type'])
            for item in accounting_data['balance_sheet_items']:
                writer.writerow([item['name'], item['balance'], item['type']])
    
    return file_path

def generate_expenses_report(params, execution_id):
    """Generate expenses report CSV"""
    start_date = datetime.strptime(params.get('start_date'), '%Y-%m-%d') if params.get('start_date') else datetime.now() - timedelta(days=30)
    end_date = datetime.strptime(params.get('end_date'), '%Y-%m-%d') if params.get('end_date') else datetime.now()
    category = params.get('category')
    
    expenses_data = get_expense_report_data(start_date, end_date, category)
    
    # Create temporary file
    temp_dir = tempfile.gettempdir()
    filename = f"expenses_report_{execution_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    file_path = os.path.join(temp_dir, filename)
    
    with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        
        # Write header
        writer.writerow(['Date', 'Description', 'Category', 'Amount'])
        
        # Write data
        for expense in expenses_data['expenses']:
            writer.writerow([
                expense.created_at.strftime('%Y-%m-%d'),
                expense.description,
                expense.category,
                expense.amount
            ])
    
    return file_path

def generate_restaurant_performance_report(params, execution_id):
    """Generate restaurant performance report CSV"""
    start_date = datetime.strptime(params.get('start_date'), '%Y-%m-%d') if params.get('start_date') else datetime.now() - timedelta(days=30)
    end_date = datetime.strptime(params.get('end_date'), '%Y-%m-%d') if params.get('end_date') else datetime.now()
    restaurant_id = params.get('restaurant_id')
    
    performance_data = get_restaurant_performance_data(start_date, end_date, restaurant_id)
    
    # Create temporary file
    temp_dir = tempfile.gettempdir()
    filename = f"restaurant_performance_report_{execution_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    file_path = os.path.join(temp_dir, filename)
    
    with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        
        # Write header
        writer.writerow(['Restaurant Name', 'Total Orders', 'Total Revenue', 'Average Order Value', 'Staff Count'])
        
        # Write data
        for data in performance_data:
            writer.writerow([
                data['restaurant'].name,
                data['total_orders'],
                data['total_revenue'],
                data['average_order_value'],
                data['staff_count']
            ])
    
    return file_path

def send_report_email(execution, file_path):
    """Send report email with attachment"""
    from flask import current_app
    import os
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    from email.mime.base import MIMEBase
    from email import encoders
    
    try:
        schedule = execution.schedule
        recipients = schedule.get_email_recipients()
        
        if not recipients:
            return
        
        # Create email message
        msg = MIMEMultipart()
        msg['From'] = current_app.config.get('MAIL_DEFAULT_SENDER', 'noreply@restaurant.com')
        msg['To'] = ', '.join(recipients)
        msg['Subject'] = schedule.email_subject or f"Report: {schedule.name}"
        
        # Email body
        body = schedule.email_message or f"Please find attached the {schedule.report_type.value} report."
        body += f"\n\nReport Details:\n"
        body += f"Name: {schedule.name}\n"
        body += f"Type: {schedule.report_type.value}\n"
        body += f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        body += f"Status: {execution.status}\n"
        
        msg.attach(MIMEText(body, 'plain'))
        
        # Attach file
        with open(file_path, 'rb') as attachment:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(attachment.read())
        
        encoders.encode_base64(part)
        part.add_header(
            'Content-Disposition',
            f'attachment; filename= {os.path.basename(file_path)}'
        )
        
        msg.attach(part)
        
        # Send email (using simple SMTP - would need proper mail configuration)
        try:
            server = smtplib.SMTP(current_app.config.get('MAIL_SERVER', 'localhost'),
                               current_app.config.get('MAIL_PORT', 587))
            server.starttls()
            mail_username = current_app.config.get('MAIL_USERNAME')
            mail_password = current_app.config.get('MAIL_PASSWORD')
            if mail_username and mail_password:
                server.login(mail_username, mail_password)
            server.send_message(msg)
            server.quit()
            
            # Update execution status
            execution.delivery_status = 'sent'
        except Exception as mail_error:
            # If mail sending fails, just log it but don't fail the whole process
            print(f"Mail sending failed: {str(mail_error)}")
            execution.delivery_status = 'failed'
            execution.error_message = f"Email failed: {str(mail_error)}"
        
    except Exception as e:
        # Update execution status
        execution.delivery_status = 'failed'
        execution.error_message = f"Email failed: {str(e)}"

# Helper Functions for Print Summary

def get_sales_summary_data(start_date, end_date):
    """Get sales summary data for print"""
    stats = calculate_report_stats(start_date, end_date)
    
    # Get recent orders
    recent_orders = Order.query.filter(
        Order.created_at >= start_date,
        Order.created_at <= end_date
    ).order_by(Order.created_at.desc()).limit(10).all()
    
    return {
        'stats': stats,
        'recent_orders': recent_orders,
        'title': 'Sales Report Summary',
        'type': 'sales'
    }

def get_items_summary_data(start_date, end_date):
    """Get items summary data for print"""
    items_sold = get_items_sold(start_date, end_date)
    
    # Sort by quantity
    sorted_items = sorted(items_sold.items(), key=lambda x: x[1]['quantity'], reverse=True)
    
    return {
        'items_sold': dict(sorted_items),
        'total_items': len(items_sold),
        'total_quantity': sum(data['quantity'] for data in items_sold.values()),
        'total_revenue': sum(data['revenue'] for data in items_sold.values()),
        'title': 'Menu Items Performance Summary',
        'type': 'items'
    }

def get_staff_summary_data(start_date, end_date):
    """Get staff summary data for print"""
    staff_stats = get_staff_performance(start_date, end_date)
    
    return {
        'staff_stats': staff_stats,
        'total_staff': len(staff_stats),
        'total_orders': sum(data['orders'] for data in staff_stats.values()),
        'total_revenue': sum(data['revenue'] for data in staff_stats.values()),
        'title': 'Staff Performance Summary',
        'type': 'staff'
    }

@bp.route('/download/<int:execution_id>')
@login_required
def download_report(execution_id):
    """Download generated report file"""
    if not current_user.can_access_manager_features():
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    execution = ReportExecution.query.get_or_404(execution_id)
    
    # Check ownership
    if execution.schedule.created_by != current_user.id and not current_user.is_admin():
        flash('Access denied', 'error')
        return redirect(url_for('reports.schedule_executions'))
    
    if not execution.file_path or execution.status != 'completed':
        flash('Report file not available', 'error')
        return redirect(url_for('reports.schedule_executions'))
    
    try:
        from flask import send_file
        
        if os.path.exists(execution.file_path):
            return send_file(
                execution.file_path,
                as_attachment=True,
                download_name=f"{execution.schedule.name}_{execution.created_at.strftime('%Y%m%d_%H%M%S')}.csv"
            )
        else:
            flash('Report file not found', 'error')
            return redirect(url_for('reports.schedule_executions'))
            
    except Exception as e:
        flash(f'Error downloading file: {str(e)}', 'error')
        return redirect(url_for('reports.schedule_executions'))