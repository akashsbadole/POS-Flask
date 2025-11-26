from flask import render_template, request, redirect, url_for, flash, jsonify, session
from flask_login import login_required, current_user
from app.orders import bp
from app.models.order import Order, OrderItem, Payment, PaymentMethod, OrderStatus
from app.models.menu import MenuItem, ItemVariant, AddOn
from app.models.table import Table
from app.models.inventory import MenuItemIngredient
from app.receipt_printer import ReceiptPrinter, print_kitchen_ticket, open_cash_drawer
from app import db
from datetime import datetime

@bp.route('/cart')
@login_required
def view_cart():
    """View current cart"""
    cart = session.get('cart', {})
    
    if request.headers.get('HX-Request'):
        return render_template('orders/partials/cart.html', cart=cart)
    
    return render_template('orders/cart.html', cart=cart)

@bp.route('/cart/add', methods=['POST'])
@login_required
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
    cart = session.get('cart', {})
    
    # Create cart item key
    cart_key = f"{item_id}_{variant_id or '0'}_{'_'.join(add_on_ids)}"
    
    if cart_key in cart:
        cart[cart_key]['quantity'] += quantity
    else:
        # Calculate price
        unit_price = float(menu_item.price)
        
        # Add variant price
        if variant_id:
            variant = ItemVariant.query.get(variant_id)
            if variant:
                unit_price += float(variant.price_modifier)
        
        # Add add-on prices
        for add_on_id in add_on_ids:
            add_on = AddOn.query.get(add_on_id)
            if add_on:
                unit_price += float(add_on.price)
        
        cart[cart_key] = {
            'item_id': item_id,
            'item_name': menu_item.name,
            'quantity': quantity,
            'unit_price': unit_price,
            'variant_id': variant_id,
            'variant_name': ItemVariant.query.get(variant_id).name if variant_id else None,
            'add_ons': add_on_ids,
            'notes': notes
        }
    
    session['cart'] = cart
    
    if request.headers.get('HX-Request'):
        return render_template('orders/partials/cart.html', cart=cart)
    
    flash(f'Added {menu_item.name} to cart', 'success')
    return redirect(url_for('orders.view_cart'))

@bp.route('/cart/update', methods=['POST'])
@login_required
def update_cart():
    """Update cart item quantity"""
    cart_key = request.form.get('cart_key')
    quantity = request.form.get('quantity', type=int, default=0)
    
    cart = session.get('cart', {})
    
    if quantity == 0 or quantity < 1:
        del cart[cart_key]
    else:
        cart[cart_key]['quantity'] = quantity
    
    session['cart'] = cart
    
    if request.headers.get('HX-Request'):
        return render_template('orders/partials/cart.html', cart=cart)
    
    return redirect(url_for('orders.view_cart'))

@bp.route('/cart/clear', methods=['POST'])
@login_required
def clear_cart():
    """Clear entire cart"""
    session.pop('cart', None)
    
    if request.headers.get('HX-Request'):
        return render_template('orders/partials/cart_empty.html')
    
    flash('Cart cleared', 'info')
    return redirect(url_for('orders.view_cart'))

@bp.route('/create', methods=['POST'])
@login_required
def create_order():
    """Create order from cart"""
    cart = session.get('cart', {})
    
    if not cart:
        flash('Cart is empty', 'error')
        return redirect(url_for('orders.view_cart'))
    
    # Create order
    order = Order(
        user_id=current_user.id,
        status=OrderStatus.PENDING
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
        for add_on_id in cart_item['add_ons']:
            add_on = AddOn.query.get(add_on_id)
            if add_on:
                order_item.add_ons.append(add_on)
        
        order.items.append(order_item)
    
    # Calculate totals
    order.calculate_totals()
    
    db.session.add(order)
    db.session.commit()
    
    # Refresh order to load relationships
    db.session.refresh(order)
    
    # Ensure items are loaded
    if hasattr(order, 'items') and order.items:
        # Convert to list to handle SQLAlchemy relationship
        items_list = list(order.items) if order.items else []
        # Deduct ingredients from inventory
        for order_item in items_list:
            menu_item = MenuItem.query.get(order_item.item_id)
            if menu_item:
                for item_ingredient in menu_item.menu_item_ingredients:
                    try:
                        item_ingredient.deduct_from_stock(order_item.quantity)
                    except Exception as e:
                        # Log error but don't fail the order
                        print(f"Error deducting ingredient {item_ingredient.ingredient.name}: {e}")
    
    db.session.commit()
    
    # Clear cart
    session.pop('cart', None)
    
    flash(f'Order {order.order_number} created successfully', 'success')
    
    if request.headers.get('HX-Request'):
        return render_template('orders/partials/order_success.html', order=order)
    
    return redirect(url_for('orders.order_details', order_id=order.id))

@bp.route('/order/<int:order_id>')
@login_required
def order_details(order_id):
    """View order details"""
    order = Order.query.get_or_404(order_id)
    
    return render_template('orders/order_details.html', order=order)

@bp.route('/list')
@login_required
def list_orders():
    """List orders"""
    status_filter = request.args.get('status')
    
    query = Order.query
    
    if status_filter:
        try:
            status = OrderStatus(status_filter)
            query = query.filter_by(status=status)
        except ValueError:
            pass
    
    orders = query.order_by(Order.created_at.desc()).limit(50).all()
    
    return render_template('orders/order_list.html', orders=orders, status_filter=status_filter)

@bp.route('/checkout/<int:order_id>')
@login_required
def checkout(order_id):
    """Checkout process for an order"""
    order = Order.query.get_or_404(order_id)
    
    if order.status != OrderStatus.PENDING:
        flash('Order cannot be checked out', 'error')
        return redirect(url_for('orders.order_details', order_id=order_id))
    
    return render_template('orders/checkout.html', order=order)

@bp.route('/payment/<int:order_id>', methods=['POST'])
@login_required
def process_payment(order_id):
    """Process payment for an order"""
    order = Order.query.get_or_404(order_id)
    
    payment_method = request.form.get('payment_method')
    amount = request.form.get('amount', type=float)
    
    if not payment_method or not amount:
        flash('Payment details required', 'error')
        return redirect(url_for('orders.checkout', order_id=order_id))
    
    # Create payment
    payment = Payment(
        order_id=order_id,
        amount=amount,
        method=PaymentMethod(payment_method)
    )
    
    db.session.add(payment)
    db.session.commit()
    
    # Check if order is fully paid
    if order.is_fully_paid():
        order.status = OrderStatus.CONFIRMED
        db.session.commit()
        
        flash(f'Order {order.order_number} paid successfully', 'success')
        return redirect(url_for('orders.order_details', order_id=order_id))
    
    flash('Partial payment processed', 'success')
    return redirect(url_for('orders.checkout', order_id=order_id))

@bp.route('/discount/<int:order_id>', methods=['POST'])
@login_required
def apply_discount(order_id):
    """Apply discount to an order"""
    order = Order.query.get_or_404(order_id)
    
    discount_type = request.form.get('discount_type')  # 'percentage' or 'fixed'
    discount_value = request.form.get('discount_value', type=float)
    discount_reason = request.form.get('discount_reason', '')
    
    if not discount_type or not discount_value or discount_value <= 0:
        flash('Invalid discount details', 'error')
        return redirect(url_for('orders.checkout', order_id=order_id))
    
    # Calculate discount amount
    if discount_type == 'percentage':
        if discount_value > 100:
            flash('Percentage discount cannot exceed 100%', 'error')
            return redirect(url_for('orders.checkout', order_id=order_id))
        order.discount_amount = float(order.subtotal) * (discount_value / 100)
    else:  # fixed
        if discount_value > float(order.subtotal):
            flash('Fixed discount cannot exceed subtotal', 'error')
            return redirect(url_for('orders.checkout', order_id=order_id))
        order.discount_amount = discount_value
    
    order.discount_type = discount_type
    order.discount_reason = discount_reason
    
    # Recalculate totals
    order.calculate_totals()
    
    db.session.commit()
    
    flash(f'Discount applied: ${order.discount_amount}', 'success')
    
    if request.headers.get('HX-Request'):
        return render_template('orders/partials/order_totals.html', order=order)
    
    return redirect(url_for('orders.checkout', order_id=order_id))

@bp.route('/discount/<int:order_id>/remove', methods=['POST'])
@login_required
def remove_discount(order_id):
    """Remove discount from an order"""
    order = Order.query.get_or_404(order_id)
    
    order.discount_amount = 0.00
    order.discount_type = None
    order.discount_reason = None
    
    # Recalculate totals
    order.calculate_totals()
    
    db.session.commit()
    
    flash('Discount removed', 'info')
    
    if request.headers.get('HX-Request'):
        return render_template('orders/partials/order_totals.html', order=order)
    
    return redirect(url_for('orders.checkout', order_id=order_id))

@bp.route('/split-payment/<int:order_id>', methods=['POST'])
@login_required
def process_split_payment(order_id):
    """Process split payment for an order"""
    order = Order.query.get_or_404(order_id)
    
    # Get split payment data
    payment_methods = request.form.getlist('payment_method[]')
    payment_amounts = request.form.getlist('payment_amount[]')
    
    if not payment_methods or not payment_amounts or len(payment_methods) != len(payment_amounts):
        flash('Invalid split payment details', 'error')
        return redirect(url_for('orders.checkout', order_id=order_id))
    
    total_payment = 0.0
    payments_created = []
    
    # Create payments
    for i, method in enumerate(payment_methods):
        try:
            amount = float(payment_amounts[i])
            if amount <= 0:
                continue
                
            payment = Payment(
                order_id=order_id,
                amount=amount,
                method=PaymentMethod(method)
            )
            
            db.session.add(payment)
            payments_created.append(payment)
            total_payment += amount
            
        except (ValueError, TypeError):
            continue
    
    if total_payment <= 0:
        flash('No valid payment amounts provided', 'error')
        return redirect(url_for('orders.checkout', order_id=order_id))
    
    db.session.commit()
    
    # Check if order is fully paid
    if order.is_fully_paid():
        order.status = OrderStatus.CONFIRMED
        db.session.commit()
        
        flash(f'Order {order.order_number} paid successfully with split payment', 'success')
        return redirect(url_for('orders.order_details', order_id=order_id))
    
    flash(f'Split payment processed: ${total_payment:.2f}', 'success')
    return redirect(url_for('orders.checkout', order_id=order_id))

# API endpoints
@bp.route('/api/cart')
@login_required
def api_cart():
    """API endpoint to get cart contents"""
    cart = session.get('cart', {})
    
    # Calculate totals
    subtotal = sum(item['unit_price'] * item['quantity'] for item in cart.values())
    tax = subtotal * 0.0875  # 8.75% tax
    total = subtotal + tax
    
    return jsonify({
        'items': list(cart.values()),
        'subtotal': subtotal,
        'tax': tax,
        'total': total,
        'item_count': len(cart)
    })

@bp.route('/api/cart/count')
@login_required
def api_cart_count():
    """API endpoint to get cart item count"""
    cart = session.get('cart', {})
    return jsonify({'count': len(cart)})

@bp.route('/api/menu/search')
@login_required
def api_menu_search():
    """API endpoint to search menu items"""
    query = request.args.get('q', '')
    category_id = request.args.get('category_id', type=int)
    
    if not query:
        return jsonify({'items': []})
    
    # Build query
    menu_query = MenuItem.query.filter(
        MenuItem.is_available == True,
        MenuItem.name.contains(query)
    )
    
    if category_id:
        menu_query = menu_query.filter_by(category_id=category_id)
    
    menu_items = menu_query.limit(20).all()
    
    # Format for API response
    api_items = []
    for item in menu_items:
        api_items.append({
            'id': item.id,
            'name': item.name,
            'price': float(item.price),
            'description': item.description,
            'category': item.category.name if item.category else None,
            'image_url': item.image_url,
            'variants': [
                {'id': v.id, 'name': v.name, 'price_modifier': float(v.price_modifier)}
                for v in item.variants
            ],
            'add_ons': [
                {'id': a.id, 'name': a.name, 'price': float(a.price)}
                for a in item.add_ons
            ]
        })
    
    return jsonify({'items': api_items, 'query': query})

@bp.route('/print/receipt/<int:order_id>')
@login_required
def print_receipt(order_id):
    """Print receipt for an order"""
    order = Order.query.get_or_404(order_id)
    
    if not order.is_fully_paid():
        flash('Order must be fully paid before printing receipt', 'error')
        return redirect(url_for('orders.checkout', order_id=order_id))
    
    try:
        # Print receipt using thermal printer
        printer = ReceiptPrinter()
        printer.print_receipt(order)
        
        # Open cash drawer if cash payment was made
        cash_payment = next((p for p in order.payments if p.method == PaymentMethod.CASH and p.is_successful()), None)
        if cash_payment:
            open_cash_drawer()
        
        flash('Receipt printed successfully', 'success')
        
    except Exception as e:
        flash(f'Error printing receipt: {str(e)}', 'error')
        # Fallback to browser print
        return render_template('orders/receipt_print.html', order=order)
    
    return redirect(url_for('orders.order_details', order_id=order_id))

@bp.route('/print/kitchen-ticket/<int:order_id>')
@login_required
def print_kitchen_ticket_route(order_id):
    """Print kitchen ticket for an order"""
    order = Order.query.get_or_404(order_id)
    
    try:
        print_kitchen_ticket(order)
        flash('Kitchen ticket printed successfully', 'success')
    except Exception as e:
        flash(f'Error printing kitchen ticket: {str(e)}', 'error')
    
    return redirect(url_for('orders.order_details', order_id=order_id))