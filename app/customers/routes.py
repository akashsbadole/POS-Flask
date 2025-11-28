"""
Customer management routes for Restaurant POS System
Handles customer information, loyalty programs, and order history
"""

from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from sqlalchemy import or_, func
from app import db
from app.models.customer import Customer, LoyaltyTransaction
from app.models.order import Order
from app.models.user import User
from datetime import datetime, timedelta
import json

bp = Blueprint('customers', __name__, url_prefix='/customers')


@bp.route('/')
@login_required
def dashboard():
    """Customer management dashboard"""
    if not current_user.can_access_manager_features():
        flash('Access denied. Manager privileges required.', 'error')
        return redirect(url_for('main.dashboard'))
    
    # Get statistics
    total_customers = Customer.query.filter_by(is_active=True).count()
    new_customers_this_month = Customer.query.filter(
        Customer.created_at >= datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0),
        Customer.is_active == True
    ).count()
    
    loyalty_members = Customer.query.filter_by(loyalty_member=True, is_active=True).count()
    
    return render_template('customers/dashboard.html',
                         total_customers=total_customers,
                         new_customers_this_month=new_customers_this_month,
                         loyalty_members=loyalty_members)


@bp.route('/search')
@login_required
def search_customers():
    """Search customers API endpoint"""
    if not current_user.can_access_manager_features():
        return jsonify({'error': 'Access denied'}), 403
    
    query = request.args.get('q', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    if not query:
        return jsonify({'customers': [], 'total': 0, 'page': page})
    
    # Search in multiple fields
    customers = Customer.query.filter(
        or_(
            Customer.first_name.ilike(f'%{query}%'),
            Customer.last_name.ilike(f'%{query}%'),
            Customer.email.ilike(f'%{query}%'),
            Customer.phone.ilike(f'%{query}%'),
            Customer.customer_code.ilike(f'%{query}%')
        ),
        Customer.is_active == True
    ).order_by(Customer.last_name, Customer.first_name).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return jsonify({
        'customers': [customer.to_dict() for customer in customers.items],
        'total': customers.total,
        'page': page,
        'pages': customers.pages,
        'has_next': customers.has_next,
        'has_prev': customers.has_prev
    })


@bp.route('/<int:customer_id>')
@login_required
def view_customer(customer_id):
    """View customer details"""
    if not current_user.can_access_manager_features():
        flash('Access denied. Manager privileges required.', 'error')
        return redirect(url_for('main.dashboard'))
    
    customer = Customer.query.get_or_404(customer_id)
    recent_orders = Order.query.filter_by(customer_id=customer_id).order_by(Order.created_at.desc()).limit(10).all()
    loyalty_transactions = LoyaltyTransaction.query.filter_by(customer_id=customer_id).order_by(LoyaltyTransaction.created_at.desc()).limit(20).all()
    
    return render_template('customers/view.html',
                         customer=customer,
                         recent_orders=recent_orders,
                         loyalty_transactions=loyalty_transactions)


@bp.route('/new', methods=['GET', 'POST'])
@bp.route('/create', methods=['GET', 'POST'])
@login_required
def new_customer():
    """Create new customer"""
    if not current_user.can_access_manager_features():
        flash('Access denied. Manager privileges required.', 'error')
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        try:
            # Generate unique customer code
            last_customer = Customer.query.filter_by(restaurant_id=current_user.restaurant_id).order_by(Customer.id.desc()).first()
            if last_customer and last_customer.customer_code:
                # Extract numeric part and increment
                try:
                    code_num = int(last_customer.customer_code[3:]) + 1
                except ValueError:
                    code_num = 1
                customer_code = f"CUS{code_num:04d}"
            else:
                customer_code = "CUS0001"
            
            customer = Customer(
                customer_code=customer_code,
                first_name=request.form.get('first_name', '').strip(),
                last_name=request.form.get('last_name', '').strip(),
                email=request.form.get('email', '').strip() or None,
                phone=request.form.get('phone', '').strip() or None,
                company_name=request.form.get('company_name', '').strip() or None,
                address_line1=request.form.get('address_line1', '').strip() or None,
                address_line2=request.form.get('address_line2', '').strip() or None,
                city=request.form.get('city', '').strip() or None,
                state=request.form.get('state', '').strip() or None,
                postal_code=request.form.get('postal_code', '').strip() or None,
                country=request.form.get('country', '').strip() or None,
                preferred_contact_method=request.form.get('preferred_contact_method', 'email'),
                dietary_restrictions=request.form.get('dietary_restrictions', '').strip() or None,
                allergies=request.form.get('allergies', '').strip() or None,
                special_notes=request.form.get('special_notes', '').strip() or None,
                loyalty_member='loyalty_member' in request.form,
                marketing_consent='marketing_consent' in request.form,
                restaurant_id=current_user.restaurant_id,
                created_by=current_user.id
            )
            
            db.session.add(customer)
            db.session.commit()
            
            flash('Customer created successfully!', 'success')
            
            # Check if we should return to cart
            if request.form.get('return_to_cart') == 'true':
                return redirect(url_for('orders.view_cart'))
            
            return redirect(url_for('customers.view_customer', customer_id=customer.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating customer: {str(e)}', 'error')
    
    return render_template('customers/create.html')


@bp.route('/<int:customer_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_customer(customer_id):
    """Edit existing customer"""
    if not current_user.can_access_manager_features():
        flash('Access denied. Manager privileges required.', 'error')
        return redirect(url_for('main.dashboard'))
    
    customer = Customer.query.get_or_404(customer_id)
    
    if request.method == 'POST':
        try:
            # Update customer fields
            customer.first_name = request.form.get('first_name', '').strip()
            customer.last_name = request.form.get('last_name', '').strip()
            customer.email = request.form.get('email', '').strip() or None
            customer.phone = request.form.get('phone', '').strip() or None
            customer.company_name = request.form.get('company_name', '').strip() or None
            customer.address_line1 = request.form.get('address_line1', '').strip() or None
            customer.address_line2 = request.form.get('address_line2', '').strip() or None
            customer.city = request.form.get('city', '').strip() or None
            customer.state = request.form.get('state', '').strip() or None
            customer.postal_code = request.form.get('postal_code', '').strip() or None
            customer.country = request.form.get('country', '').strip() or None
            customer.preferred_contact_method = request.form.get('preferred_contact_method', 'email')
            customer.dietary_restrictions = request.form.get('dietary_restrictions', '').strip() or None
            customer.allergies = request.form.get('allergies', '').strip() or None
            customer.special_notes = request.form.get('special_notes', '').strip() or None
            customer.loyalty_member = 'loyalty_member' in request.form
            customer.marketing_consent = 'marketing_consent' in request.form
            customer.updated_at = datetime.utcnow()
            
            db.session.commit()
            
            flash('Customer updated successfully!', 'success')
            return redirect(url_for('customers.view_customer', customer_id=customer.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating customer: {str(e)}', 'error')
    
    return render_template('customers/form.html', customer=customer, action='Edit')


@bp.route('/<int:customer_id>/delete', methods=['POST'])
@login_required
def delete_customer(customer_id):
    """Delete customer (soft delete by setting inactive)"""
    if not current_user.can_access_manager_features():
        return jsonify({'error': 'Access denied'}), 403
    
    customer = Customer.query.get_or_404(customer_id)
    
    try:
        customer.is_active = False
        customer.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Customer deleted successfully'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})


@bp.route('/loyalty')
@login_required
def loyalty_program():
    """Loyalty program management"""
    if not current_user.can_access_manager_features():
        flash('Access denied. Manager privileges required.', 'error')
        return redirect(url_for('main.dashboard'))
    
    # Get loyalty statistics
    loyalty_stats = db.session.query(
        Customer.loyalty_tier,
        func.count(Customer.id).label('count'),
        func.sum(Customer.loyalty_points).label('total_points')
    ).filter(
        Customer.loyalty_member == True,
        Customer.is_active == True
    ).group_by(Customer.loyalty_tier).all()
    
    recent_transactions = LoyaltyTransaction.query.order_by(LoyaltyTransaction.created_at.desc()).limit(50).all()
    
    return render_template('customers/loyalty.html',
                         loyalty_stats=loyalty_stats,
                         recent_transactions=recent_transactions)


@bp.route('/loyalty/add-points', methods=['POST'])
@login_required
def add_loyalty_points():
    """Add loyalty points to customer"""
    if not current_user.can_access_manager_features():
        return jsonify({'error': 'Access denied'}), 403
    
    customer_id = request.form.get('customer_id', type=int)
    points = request.form.get('points', type=int)
    description = request.form.get('description', '').strip()
    order_id = request.form.get('order_id', type=int) or None
    
    customer = Customer.query.get_or_404(customer_id)
    
    if customer.add_loyalty_points(points, description, order_id):
        db.session.commit()
        return jsonify({
            'success': True,
            'message': f'Added {points} points to {customer.get_full_name()}',
            'new_balance': customer.loyalty_points
        })
    else:
        return jsonify({'success': False, 'error': 'Failed to add points'})


@bp.route('/loyalty/redeem-points', methods=['POST'])
@login_required
def redeem_loyalty_points():
    """Redeem loyalty points from customer"""
    if not current_user.can_access_manager_features():
        return jsonify({'error': 'Access denied'}), 403
    
    customer_id = request.form.get('customer_id', type=int)
    points = request.form.get('points', type=int)
    description = request.form.get('description', '').strip()
    order_id = request.form.get('order_id', type=int) or None
    
    customer = Customer.query.get_or_404(customer_id)
    
    if customer.redeem_loyalty_points(points, description, order_id):
        db.session.commit()
        return jsonify({
            'success': True,
            'message': f'Redeemed {points} points from {customer.get_full_name()}',
            'new_balance': customer.loyalty_points
        })
    else:
        return jsonify({'success': False, 'error': 'Failed to redeem points'})


@bp.route('/api/quick-lookup')
@login_required
def quick_lookup():
    """Quick customer lookup for POS"""
    if not current_user.can_access_manager_features():
        return jsonify({'error': 'Access denied'}), 403
    
    query = request.args.get('q', '').strip()
    if len(query) < 2:
        return jsonify({'customers': []})
    
    # Search by phone, email, or customer code
    customers = Customer.query.filter(
        or_(
            Customer.phone.ilike(f'%{query}%'),
            Customer.email.ilike(f'%{query}%'),
            Customer.customer_code.ilike(f'%{query}%'),
            Customer.first_name.ilike(f'%{query}%'),
            Customer.last_name.ilike(f'%{query}%')
        ),
        Customer.is_active == True
    ).limit(10).all()
    
    return jsonify({
        'customers': [{
            'id': customer.id,
            'name': customer.get_full_name(),
            'email': customer.email,
            'phone': customer.phone,
            'customer_code': customer.customer_code,
            'loyalty_points': customer.loyalty_points,
            'loyalty_tier': customer.loyalty_tier
        } for customer in customers]
    })


@bp.route('/api/<int:customer_id>/orders')
@login_required
def customer_orders_api(customer_id):
    """API endpoint for customer orders"""
    if not current_user.can_access_manager_features():
        return jsonify({'error': 'Access denied'}), 403
    
    customer = Customer.query.get_or_404(customer_id)
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    orders = Order.query.filter_by(customer_id=customer_id).order_by(Order.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return jsonify({
        'orders': [order.to_dict() for order in orders.items],
        'total': orders.total,
        'page': page,
        'pages': orders.pages,
        'has_next': orders.has_next,
        'has_prev': orders.has_prev
    })

@bp.route('/api/selected-customer')
@login_required
def api_selected_customer():
    """API endpoint to get the currently selected customer for cart"""
    from flask import session
    
    customer_id = session.get('selected_customer_id')
    if not customer_id:
        return jsonify({'success': False, 'message': 'No customer selected'})
    
    customer = Customer.query.get(customer_id)
    if not customer:
        return jsonify({'success': False, 'message': 'Customer not found'})
    
    return jsonify({
        'success': True,
        'customer': customer.to_dict()
    })

@bp.route('/api/search')
@login_required
def api_search():
    """API endpoint for customer search (simplified for cart)"""
    query = request.args.get('q', '').strip()
    if len(query) < 2:
        return jsonify({'customers': []})
    
    # Search by phone, email, or customer code
    customers = Customer.query.filter(
        or_(
            Customer.phone.ilike(f'%{query}%'),
            Customer.email.ilike(f'%{query}%'),
            Customer.customer_code.ilike(f'%{query}%'),
            Customer.first_name.ilike(f'%{query}%'),
            Customer.last_name.ilike(f'%{query}%')
        ),
        Customer.is_active == True
    ).limit(10).all()
    
    return jsonify({
        'customers': [customer.to_dict() for customer in customers]
    })