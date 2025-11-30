"""
Online Ordering Routes for Restaurant POS System
Handles customer-facing web ordering interface
"""

from flask import render_template, request, redirect, url_for, flash, jsonify, session
from flask_login import login_user, logout_user, login_required, current_user
from datetime import datetime, timedelta
import json

from app.online_ordering import bp
from app.models.menu import MenuItem, ItemVariant, AddOn, Category
from app.models.order import Order, OrderItem, OrderStatus, OrderType
from app.models.customer import Customer
from app import db
from app.socketio_events import emit_new_order

# Guest customer session management
def get_or_create_guest_customer():
    """Get or create guest customer from session"""
    if 'guest_customer_id' not in session:
        # Create a temporary guest customer record
        guest_customer = Customer(
            first_name='Guest',
            last_name=f'Customer {datetime.now().strftime("%Y%m%d%H%M%S")}',
            email=None,
            phone=None,
            loyalty_member=False,
            is_guest=True
        )
        db.session.add(guest_customer)
        db.session.commit()
        session['guest_customer_id'] = guest_customer.id
        return guest_customer
    return Customer.query.get(session['guest_customer_id'])

@bp.route('/')
def index():
    """Online ordering main page - menu browsing"""
    # Get featured items and categories
    featured_items = MenuItem.query.filter_by(
        is_available=True, 
        is_featured=True
    ).limit(8).all()
    
    categories = Category.query.filter_by(is_active=True).order_by(Category.display_order).all()
    
    return render_template('online_ordering/index.html',
                         featured_items=featured_items,
                         categories=categories)

@bp.route('/menu')
def menu():
    """Full menu browsing page"""
    category_id = request.args.get('category', type=int)
    search_query = request.args.get('search', '').strip()
    
    # Build query
    query = MenuItem.query.filter_by(is_available=True)
    
    if category_id:
        query = query.filter_by(category_id=category_id)
    
    if search_query:
        query = query.filter(MenuItem.name.contains(search_query))
    
    menu_items = query.order_by(MenuItem.category_id, MenuItem.display_order).all()
    categories = Category.query.filter_by(is_active=True).order_by(Category.display_order).all()
    
    return render_template('online_ordering/menu.html',
                         menu_items=menu_items,
                         categories=categories,
                         selected_category=category_id,
                         search_query=search_query)

@bp.route('/item/<int:item_id>')
def item_detail(item_id):
    """Detailed item view with customization options"""
    item = MenuItem.query.get_or_404(item_id)
    
    if not item.is_available:
        flash('This item is currently unavailable', 'error')
        return redirect(url_for('online_ordering.menu'))
    
    variants = ItemVariant.query.filter_by(item_id=item_id, is_available=True).order_by(ItemVariant.display_order).all()
    add_ons = AddOn.query.filter_by(is_active=True).order_by(AddOn.display_order).all()
    
    return render_template('online_ordering/item_detail.html',
                         item=item,
                         variants=variants,
                         add_ons=add_ons)

@bp.route('/cart')
def view_cart():
    """View shopping cart"""
    cart = session.get('online_cart', {})
    
    if not cart:
        return render_template('online_ordering/empty_cart.html')
    
    # Calculate totals
    subtotal = sum(item['unit_price'] * item['quantity'] for item in cart.values())
    tax = subtotal * 0.0875  # 8.75% tax
    total = subtotal + tax
    
    return render_template('online_ordering/cart.html',
                         cart=cart,
                         subtotal=subtotal,
                         tax=tax,
                         total=total)

@bp.route('/cart/add', methods=['POST'])
def add_to_cart():
    """Add item to cart"""
    item_id = request.form.get('item_id', type=int)
    quantity = request.form.get('quantity', type=int, default=1)
    variant_id = request.form.get('variant_id', type=int)
    add_on_ids = request.form.getlist('add_ons')
    notes = request.form.get('notes', '')
    
    # Get menu item
    menu_item = MenuItem.query.get_or_404(item_id)
    
    # Get cart from session
    cart = session.get('online_cart', {})
    
    # Create cart item key
    cart_key = f"{item_id}_{variant_id or '0'}_{'_'.join(map(str, add_on_ids))}"
    
    if cart_key in cart:
        cart[cart_key]['quantity'] += quantity
    else:
        # Calculate price
        unit_price = float(menu_item.price)
        variant_name = None
        variant_price_modifier = 0
        
        # Add variant price
        if variant_id:
            variant = ItemVariant.query.get(variant_id)
            if variant:
                unit_price += float(variant.price_modifier)
                variant_name = variant.name
                variant_price_modifier = float(variant.price_modifier)
        
        # Add add-on prices
        add_on_details = []
        for add_on_id in add_on_ids:
            add_on = AddOn.query.get(add_on_id)
            if add_on:
                unit_price += float(add_on.price)
                add_on_details.append({
                    'id': add_on.id,
                    'name': add_on.name,
                    'price': float(add_on.price)
                })
        
        cart[cart_key] = {
            'item_id': item_id,
            'item_name': menu_item.name,
            'quantity': quantity,
            'unit_price': unit_price,
            'base_price': float(menu_item.price),
            'variant_id': variant_id,
            'variant_name': variant_name,
            'variant_price_modifier': variant_price_modifier,
            'add_ons': add_on_details,
            'notes': notes,
            'image_url': menu_item.image_url
        }
    
    session['online_cart'] = cart
    flash(f'{menu_item.name} added to cart', 'success')
    
    # Return JSON for AJAX requests
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({
            'success': True,
            'message': f'{menu_item.name} added to cart',
            'cart_count': len(cart)
        })
    
    return redirect(url_for('online_ordering.view_cart'))

@bp.route('/cart/update', methods=['POST'])
def update_cart():
    """Update cart item quantity"""
    cart_key = request.form.get('cart_key')
    quantity = request.form.get('quantity', type=int, default=0)
    
    cart = session.get('online_cart', {})
    
    if quantity == 0 or quantity < 1:
        del cart[cart_key]
    else:
        cart[cart_key]['quantity'] = quantity
    
    session['online_cart'] = cart
    
    # Return JSON for AJAX requests
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True})
    
    return redirect(url_for('online_ordering.view_cart'))

@bp.route('/cart/clear', methods=['POST'])
def clear_cart():
    """Clear entire cart"""
    session.pop('online_cart', None)
    flash('Cart cleared', 'info')
    
    # Return JSON for AJAX requests
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True})
    
    return redirect(url_for('online_ordering.menu'))

@bp.route('/checkout')
def checkout():
    """Checkout process"""
    cart = session.get('online_cart', {})
    
    if not cart:
        flash('Your cart is empty', 'error')
        return redirect(url_for('online_ordering.menu'))
    
    # Calculate totals
    subtotal = sum(item['unit_price'] * item['quantity'] for item in cart.values())
    tax = subtotal * 0.0875  # 8.75% tax
    total = subtotal + tax
    
    # Get or create customer
    customer = get_or_create_guest_customer()
    
    return render_template('online_ordering/checkout.html',
                         cart=cart,
                         subtotal=subtotal,
                         tax=tax,
                         total=total,
                         customer=customer)

@bp.route('/checkout/process', methods=['POST'])
def process_checkout():
    """Process checkout and create order"""
    cart = session.get('online_cart', {})
    
    if not cart:
        flash('Your cart is empty', 'error')
        return redirect(url_for('online_ordering.menu'))
    
    try:
        # Get or create customer
        customer = get_or_create_guest_customer()
        
        # Update customer information if provided
        customer.first_name = request.form.get('first_name', customer.first_name).strip()
        customer.last_name = request.form.get('last_name', customer.last_name).strip()
        customer.email = request.form.get('email', customer.email)
        customer.phone = request.form.get('phone', customer.phone)
        
        # Delivery information
        delivery_type = request.form.get('delivery_type', 'pickup')
        address_line1 = request.form.get('address_line1', '').strip()
        address_line2 = request.form.get('address_line2', '').strip()
        city = request.form.get('city', '').strip()
        postal_code = request.form.get('postal_code', '').strip()
        
        if address_line1:
            customer.address_line1 = address_line1
            customer.address_line2 = address_line2
            customer.city = city
            customer.postal_code = postal_code
        
        db.session.commit()
        
        # Create order
        # Map delivery_type to OrderType enum
        order_type_mapping = {
            'pickup': OrderType.TAKEAWAY,
            'delivery': OrderType.DELIVERY
        }
        order_type = order_type_mapping.get(delivery_type, OrderType.TAKEAWAY)
        
        order = Order(
            customer_id=customer.id,
            status=OrderStatus.PENDING,
            order_type=order_type,
            notes=request.form.get('order_notes', '').strip()
        )
        
        # Add items to order
        for cart_key, cart_item in cart.items():
            order_item = OrderItem(
                item_id=cart_item['item_id'],
                quantity=cart_item['quantity'],
                unit_price=cart_item['unit_price'],
                variant_id=cart_item['variant_id'],
                notes=cart_item['notes']
            )
            
            # Add add-ons
            for add_on_detail in cart_item['add_ons']:
                add_on = AddOn.query.get(add_on_detail['id'])
                if add_on:
                    order_item.add_ons.append(add_on)
            
            order.items.append(order_item)
        
        # Calculate totals
        order.calculate_totals()
        
        db.session.add(order)
        db.session.commit()
        
        # Clear cart and guest session
        session.pop('online_cart', None)
        session.pop('guest_customer_id', None)
        
        # Emit new order notification to kitchen
        emit_new_order(order)
        
        # Redirect to confirmation page
        flash(f'Order {order.order_number} placed successfully!', 'success')
        return redirect(url_for('online_ordering.order_confirmation', order_id=order.id))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error processing order: {str(e)}', 'error')
        return redirect(url_for('online_ordering.checkout'))

@bp.route('/confirmation/<int:order_id>')
def order_confirmation(order_id):
    """Order confirmation page"""
    order = Order.query.get_or_404(order_id)
    
    return render_template('online_ordering/confirmation.html', order=order)

@bp.route('/track/<string:order_number>')
def track_order(order_number):
    """Order tracking page"""
    order = Order.query.filter_by(order_number=order_number).first()
    
    if not order:
        flash('Order not found', 'error')
        return redirect(url_for('online_ordering.index'))
    
    return render_template('online_ordering/tracking.html', order=order)

# API endpoints
@bp.route('/api/menu/categories')
def api_categories():
    """API endpoint to get menu categories"""
    categories = Category.query.filter_by(is_active=True).order_by(Category.display_order).all()
    
    return jsonify({
        'categories': [{
            'id': cat.id,
            'name': cat.name,
            'description': cat.description
        } for cat in categories]
    })

@bp.route('/api/menu/items')
def api_menu_items():
    """API endpoint to get menu items"""
    category_id = request.args.get('category_id', type=int)
    search_query = request.args.get('search', '').strip()
    
    query = MenuItem.query.filter_by(is_available=True)
    
    if category_id:
        query = query.filter_by(category_id=category_id)
    
    if search_query:
        query = query.filter(MenuItem.name.contains(search_query))
    
    menu_items = query.order_by(MenuItem.category_id, MenuItem.display_order).all()
    
    return jsonify({
        'items': [{
            'id': item.id,
            'name': item.name,
            'description': item.description,
            'price': float(item.price),
            'category_id': item.category_id,
            'image_url': item.image_url,
            'is_featured': item.is_featured,
            'variants': [{
                'id': v.id,
                'name': v.name,
                'price_modifier': float(v.price_modifier)
            } for v in item.variants.filter_by(is_available=True)],
            'add_ons': [{
                'id': a.id,
                'name': a.name,
                'price': float(a.price)
            } for a in AddOn.query.filter_by(is_active=True).order_by(AddOn.display_order).all()]
        } for item in menu_items]
    })

@bp.route('/api/cart')
def api_cart():
    """API endpoint to get cart contents"""
    cart = session.get('online_cart', {})
    
    # Calculate totals
    subtotal = sum(item['unit_price'] * item['quantity'] for item in cart.values())
    tax = subtotal * 0.0875
    total = subtotal + tax
    
    return jsonify({
        'items': list(cart.values()),
        'subtotal': subtotal,
        'tax': tax,
        'total': total,
        'item_count': len(cart)
    })
