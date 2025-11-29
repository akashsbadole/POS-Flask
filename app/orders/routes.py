from flask import render_template, request, redirect, url_for, flash, jsonify, session
from flask_login import login_required, current_user
import json
from app.orders import bp
from app.models.order import Order, OrderItem, Payment, PaymentMethod, OrderStatus, SplitBill
from app.models.menu import MenuItem, ItemVariant, AddOn, Category
from app.models.table import Table
from app.models.inventory import MenuItemIngredient
from app.models.user import User
from app.models.customer import Customer
from app.receipt_printer import ReceiptPrinter, print_kitchen_ticket, open_cash_drawer
from app.notifications.service import notification_service
from app import db
from app.socketio_events import emit_new_order, emit_kitchen_stats
from datetime import datetime

@bp.route('/cart')
@login_required
def view_cart():
    """View TPOS interface"""
    cart = session.get('cart', {})
    
    if request.headers.get('HX-Request'):
        return render_template('orders/partials/cart.html', cart=cart)
    
    # Check if TPOS template should be used
    if request.args.get('tpos') == '1':
        return render_template('orders/tpos.html', cart=cart)
    
    return render_template('orders/cart.html', cart=cart)

@bp.route('/cart/add', methods=['POST'])
@login_required
def add_to_cart():
    """Add item to cart"""
    # Handle both form data and JSON data
    if request.is_json:
        data = request.get_json()
        item_id = data.get('item_id', type=int)
        quantity = data.get('quantity', 1, type=int)
        variant_id = data.get('variant_id', type=int)
        add_on_ids = data.get('add_ons', [])
        notes = data.get('notes', '')
    else:
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
            'notes': notes
        }
    
    session['cart'] = cart
    
    if request.headers.get('HX-Request') or request.is_json:
        if request.is_json:
            return jsonify({'success': True, 'message': f'Added {menu_item.name} to cart'})
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

@bp.route('/create', methods=['GET', 'POST'])
@login_required
def create_order():
    """Create order from cart"""
    if request.method == 'GET':
        # For GET requests, redirect to cart page
        return redirect(url_for('orders.view_cart'))
    
    cart = session.get('cart', {})
    
    if not cart:
        flash('Cart is empty', 'error')
        return redirect(url_for('orders.view_cart'))
    
    # Get customer ID from form or session
    customer_id = None
    if request.method == 'POST':
        customer_id = request.form.get('customer_id', type=int) or session.get('selected_customer_id')
    
    # Create order
    order = Order(
        user_id=current_user.id,
        customer_id=customer_id,
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
        for add_on_detail in cart_item['add_ons']:
            # Handle both ID-only and detail objects
            if isinstance(add_on_detail, dict):
                add_on_id = add_on_detail.get('id')
            else:
                add_on_id = add_on_detail
                
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
        items_list = list(order.items.all()) if order.items else []
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
    
    # Emit new order notification to kitchen via WebSocket
    emit_new_order(order)
    
    # Update kitchen stats
    emit_kitchen_stats()
    
    # Print kitchen ticket if configured
    try:
        print_kitchen_ticket(order)
    except Exception as e:
        # Log error but don't fail the order
        print(f"Error printing kitchen ticket: {e}")
    
    # Clear cart and customer selection
    session.pop('cart', None)
    session.pop('selected_customer_id', None)
    
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
    customer_email = request.form.get('customer_email')
    customer_phone = request.form.get('customer_phone')
    send_receipt = request.form.get('send_receipt') == 'on'
    
    # Handle loyalty points redemption
    redeem_points = request.form.get('redeem_points', type=int) or 0
    points_discount = 0.0
    
    if redeem_points > 0 and order.customer:
        if order.customer.loyalty_points >= redeem_points:
            # Calculate points value (100 points = $1)
            points_discount = redeem_points / 100.0
            
            # Redeem points
            if order.customer.redeem_loyalty_points(redeem_points, f"Points redeemed for order {order.order_number}", order_id):
                db.session.commit()
        else:
            flash(f'Insufficient loyalty points. Customer has {order.customer.loyalty_points} points.', 'error')
            return redirect(url_for('orders.checkout', order_id=order_id))
    
    if not payment_method or not amount:
        flash('Payment details required', 'error')
        return redirect(url_for('orders.checkout', order_id=order_id))
    
    # Calculate final amount after points discount
    final_amount = amount - points_discount
    
    # Create payment
    payment = Payment(
        order_id=order_id,
        amount=final_amount,
        method=PaymentMethod(payment_method)
    )
    
    db.session.add(payment)
    
    # Handle credit payment
    if payment_method == 'credit':
        if not order.customer:
            flash('Customer must be selected for credit payment', 'error')
            return redirect(url_for('orders.checkout', order_id=order_id))
        
        # Check if customer has sufficient credit
        credit_summary = order.customer.get_credit_summary()
        if not credit_summary.get('has_credit_account') or not credit_summary.get('is_active'):
            flash('Customer does not have an active credit account', 'error')
            return redirect(url_for('orders.checkout', order_id=order_id))
        
        if credit_summary.get('available_credit', 0) < final_amount:
            flash(f'Insufficient credit. Available: ${credit_summary.get("available_credit", 0):.2f}', 'error')
            return redirect(url_for('orders.checkout', order_id=order_id))
        
        # Charge to credit account
        if not order.customer.charge_to_credit(final_amount, f"Order {order.order_number}", 'order', order_id, current_user.id):
            flash('Failed to charge credit account', 'error')
            return redirect(url_for('orders.checkout', order_id=order_id))
    
    # Create payment record
    payment = Payment(
        order_id=order_id,
        amount=final_amount,
        method=PaymentMethod(payment_method)
    )
    
    db.session.add(payment)
    
    # Apply points discount to order
    if points_discount > 0:
        order.discount_amount = points_discount
        order.discount_type = 'fixed'
        order.discount_reason = f'Loyalty points redemption ({redeem_points} points)'
        order.calculate_totals()
    
    db.session.commit()
    
    # Check if order is fully paid
    if order.is_fully_paid():
        old_status = order.status
        order.status = OrderStatus.CONFIRMED
        db.session.commit()
        
        # Emit order status update to kitchen
        from app.socketio_events import emit_order_status_update
        emit_order_status_update(order, old_status)
        
        # Update kitchen stats
        emit_kitchen_stats()
        
        # Send order confirmation notification
        try:
            notification_service.send_order_confirmation(
                order,
                email=customer_email or '',
                phone=customer_phone or ''
            )
        except Exception as e:
            # Log error but don't fail the payment
            print(f"Error sending order confirmation: {e}")
        
        success_message = f'Order {order.order_number} paid successfully'
        if points_discount > 0:
            success_message += f' (used {redeem_points} loyalty points = ${points_discount:.2f} discount)'
        flash(success_message, 'success')
        
        # If order is completed and receipt requested, send it
        if send_receipt and (customer_email or customer_phone):
            try:
                notification_service.send_order_receipt(
                    order,
                    email=customer_email or '',
                    phone=customer_phone or ''
                )
                flash('Receipt sent successfully', 'success')
            except Exception as e:
                # Log error but don't fail the payment
                print(f"Error sending receipt: {e}")
                flash('Receipt could not be sent', 'warning')
        
        return redirect(url_for('orders.order_details', order_id=order_id))
    
    flash('Partial payment processed', 'success')
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

@bp.route('/process-split-bill', methods=['POST'])
@login_required
def process_split_bill():
    """Process split bill from cart"""
    cart = session.get('cart', {})
    
    if not cart:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': 'Cart is empty'}), 400
        flash('Cart is empty', 'error')
        return redirect(url_for('orders.view_cart'))
    
    # Get split bill data
    split_type = request.form.get('split_type')
    total_amount = float(request.form.get('total_amount', 0))
    customer_id = None
    if request.method == 'POST':
        customer_id = request.form.get('customer_id') or session.get('selected_customer_id')
    
    # Validate split data
    if not split_type or total_amount <= 0:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': 'Invalid split bill data'}), 400
        flash('Invalid split bill data', 'error')
        return redirect(url_for('orders.view_cart'))
    
    # Create order from cart
    order = Order(
        user_id=current_user.id,
        customer_id=customer_id,
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
        for add_on_detail in cart_item['add_ons']:
            # Handle both ID-only and detail objects
            if isinstance(add_on_detail, dict):
                add_on_id = add_on_detail.get('id')
            else:
                add_on_id = add_on_detail
            
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
    
    # Process split payment
    if split_type == 'equal':
        number_of_splits = int(request.form.get('number_of_splits', 2))
        return process_equal_split_payment(order, number_of_splits)
    elif split_type == 'custom':
        split_names = request.form.getlist('split_name[]')
        split_amounts = request.form.getlist('split_amount[]')
        split_payment_methods = request.form.getlist('split_payment_method[]')
        return process_custom_split_payment(order, split_names, split_amounts, split_payment_methods)
    elif split_type == 'items':
        split_names = request.form.getlist('split_name[]')
        split_items = request.form.getlist('split_items[]')
        split_payment_methods = request.form.getlist('split_payment_method[]')
        return process_item_split_payment(order, split_names, split_items, split_payment_methods)
    else:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': 'Invalid split type'}), 400
        flash('Invalid split type', 'error')
        return redirect(url_for('orders.view_cart'))

def process_equal_split_payment(order, number_of_splits):
    """Process equal split payment"""
    balance_due = order.get_balance_due()
    equal_amount = balance_due / number_of_splits
    
    payments_created = []
    for i in range(number_of_splits):
        payment = Payment(
            order_id=order.id,
            amount=equal_amount,
            method=PaymentMethod.CASH  # Default to cash, can be customized
        )
        db.session.add(payment)
        payments_created.append(payment)
    
    # Create split bill record
    split_bill = SplitBill(
        order_id=order.id,
        split_type='equal',
        total_amount=balance_due,
        split_details=json.dumps([
            {
                'name': f'Person {i + 1}',
                'amount': equal_amount,
                'payment_method': 'cash'
            }
            for i in range(number_of_splits)
        ]),
        created_by=current_user.id
    )
    
    db.session.add(split_bill)
    db.session.commit()
    
    return finalize_split_payment(order, payments_created, split_bill)

def process_custom_split_payment(order, split_names, split_amounts, split_payment_methods):
    """Process custom amount split payment"""
    payments_created = []
    split_details = []
    
    for i, name in enumerate(split_names):
        try:
            amount = float(split_amounts[i])
            if amount <= 0:
                continue
            
            payment = Payment(
                order_id=order.id,
                amount=amount,
                method=PaymentMethod(split_payment_methods[i])
            )
            
            db.session.add(payment)
            payments_created.append(payment)
            
            split_details.append({
                'name': name,
                'amount': amount,
                'payment_method': split_payment_methods[i]
            })
            
        except (ValueError, TypeError, IndexError):
            continue
    
    # Create split bill record
    split_bill = SplitBill(
        order_id=order.id,
        split_type='custom',
        total_amount=sum(p.amount for p in payments_created),
        split_details=json.dumps(split_details),
        created_by=current_user.id
    )
    
    db.session.add(split_bill)
    db.session.commit()
    
    return finalize_split_payment(order, payments_created, split_bill)

def process_item_split_payment(order, split_names, split_items, split_payment_methods):
    """Process item-based split payment"""
    payments_created = []
    split_details = []
    
    # Get all order items for reference
    order_items = {item.id: item for item in order.items}
    
    for i, name in enumerate(split_names):
        try:
            # Parse items for this split
            items_data = []
            if i < len(split_items):
                try:
                    items_data = json.loads(split_items[i])
                except (json.JSONDecodeError, TypeError):
                    items_data = []
            
            # Calculate total for this split based on assigned items
            split_total = 0.0
            for item_id in items_data:
                if item_id in order_items:
                    item = order_items[item_id]
                    split_total += item.get_total_price()
            
            # Create payment record
            payment = Payment(
                order_id=order.id,
                amount=split_total,
                method=PaymentMethod(split_payment_methods[i] if i < len(split_payment_methods) else 'cash')
            )
            
            db.session.add(payment)
            payments_created.append(payment)
            
            split_details.append({
                'name': name,
                'amount': split_total,
                'payment_method': split_payment_methods[i] if i < len(split_payment_methods) else 'cash',
                'items': items_data
            })
            
        except (ValueError, TypeError, IndexError):
            continue
    
    # Create split bill record
    split_bill = SplitBill(
        order_id=order.id,
        split_type='items',
        total_amount=sum(p.amount for p in payments_created),
        split_details=json.dumps(split_details),
        created_by=current_user.id
    )
    
    db.session.add(split_bill)
    db.session.commit()
    
    return finalize_split_payment(order, payments_created, split_bill)

def finalize_split_payment(order, payments_created, split_bill):
    """Finalize split payment process"""
    # Clear cart and customer selection
    session.pop('cart', None)
    session.pop('selected_customer_id', None)
    session.pop('cart_discount', None)
    
    # Check if order is fully paid
    if order.is_fully_paid():
        old_status = order.status
        order.status = OrderStatus.CONFIRMED
        db.session.commit()
        
        # Emit order status update to kitchen
        from app.socketio_events import emit_order_status_update
        emit_order_status_update(order, old_status)
        
        # Update kitchen stats
        emit_kitchen_stats()
        
        # Send order confirmation notification
        try:
            notification_service.send_order_confirmation(order)
        except Exception as e:
            # Log error but don't fail payment
            print(f"Error sending order confirmation: {e}")
        
        response_data = {
            'success': True,
            'message': f'Split bill processed successfully for order {order.order_number}',
            'redirect': url_for('orders.order_details', order_id=order.id),
            'update_totals': True,
            'order_data': order.to_dict(),
            'split_bill_id': split_bill.id
        }
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify(response_data)
        
        flash(response_data['message'], 'success')
        return redirect(response_data['redirect'])
    
    response_data = {
        'success': True,
        'message': f'Split bill created for order {order.order_number}',
        'redirect': url_for('orders.checkout', order_id=order.id),
        'update_totals': True,
        'order_data': order.to_dict(),
        'split_bill_id': split_bill.id
    }
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify(response_data)
    
    flash(response_data['message'], 'success')
    return redirect(response_data['redirect'])

@bp.route('/split-payment/<int:order_id>', methods=['POST'])
@login_required
def process_split_payment(order_id):
    """Process split payment for an order"""
    order = Order.query.get_or_404(order_id)
    
    # Check if this is an advanced split bill or simple split payment
    split_type = request.form.get('split_type')
    
    if split_type in ['equal', 'custom', 'items']:
        return process_advanced_split_payment(order_id, order)
    else:
        return process_simple_split_payment(order_id, order)

def process_simple_split_payment(order_id, order):
    """Process simple split payment (legacy functionality)"""
    # Get split payment data
    payment_methods = request.form.getlist('payment_method[]')
    payment_amounts = request.form.getlist('payment_amount[]')
    
    if not payment_methods or not payment_amounts or len(payment_methods) != len(payment_amounts):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': 'Invalid split payment details'}), 400
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
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': 'No valid payment amounts provided'}), 400
        flash('No valid payment amounts provided', 'error')
        return redirect(url_for('orders.checkout', order_id=order_id))
    
    db.session.commit()
    
    # Check if order is fully paid
    if order.is_fully_paid():
        old_status = order.status
        order.status = OrderStatus.CONFIRMED
        db.session.commit()
        
        # Emit order status update to kitchen
        from app.socketio_events import emit_order_status_update
        emit_order_status_update(order, old_status)
        
        # Update kitchen stats
        emit_kitchen_stats()
        
        response_data = {
            'success': True,
            'message': f'Order {order.order_number} paid successfully with split payment',
            'redirect': url_for('orders.order_details', order_id=order_id),
            'update_totals': True,
            'order_data': order.to_dict()
        }
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify(response_data)
        
        flash(response_data['message'], 'success')
        return redirect(response_data['redirect'])
    
    response_data = {
        'success': True,
        'message': f'Split payment processed: ₹{total_payment:.2f}',
        'update_totals': True,
        'order_data': order.to_dict()
    }
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify(response_data)
    
    flash(response_data['message'], 'success')
    return redirect(url_for('orders.checkout', order_id=order_id))

def process_advanced_split_payment(order_id, order):
    """Process advanced split payment with split tracking"""
    # Get advanced split payment data
    split_names = request.form.getlist('split_name[]')
    split_amounts = request.form.getlist('split_amount[]')
    split_payment_methods = request.form.getlist('split_payment_method[]')
    split_items = request.form.getlist('split_items[]')
    split_type = request.form.get('split_type')
    
    # Validate input
    if (not split_names or not split_amounts or not split_payment_methods or
        len(split_names) != len(split_amounts) or
        len(split_names) != len(split_payment_methods)):
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': 'Invalid split bill details'}), 400
        flash('Invalid split bill details', 'error')
        return redirect(url_for('orders.checkout', order_id=order_id))
    
    total_payment = 0.0
    payments_created = []
    split_details = []
    
    # Process each split
    for i, name in enumerate(split_names):
        try:
            amount = float(split_amounts[i])
            if amount <= 0:
                continue
            
            # Parse items for this split if provided
            items_data = []
            if i < len(split_items) and split_items[i]:
                try:
                    items_data = json.loads(split_items[i])
                except (json.JSONDecodeError, TypeError):
                    items_data = []
            
            # Create payment record
            payment = Payment(
                order_id=order_id,
                amount=amount,
                method=PaymentMethod(split_payment_methods[i])
            )
            
            db.session.add(payment)
            payments_created.append(payment)
            total_payment += amount
            
            # Store split details for receipt and reporting
            split_details.append({
                'name': name,
                'amount': amount,
                'payment_method': split_payment_methods[i],
                'items': items_data
            })
            
        except (ValueError, TypeError):
            continue
    
    if total_payment <= 0:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': 'No valid payment amounts provided'}), 400
        flash('No valid payment amounts provided', 'error')
        return redirect(url_for('orders.checkout', order_id=order_id))
    
    # Create split bill record for tracking
    split_bill = SplitBill(
        order_id=order_id,
        split_type=split_type,
        total_amount=total_payment,
        split_details=json.dumps(split_details),
        created_by=current_user.id
    )
    
    db.session.add(split_bill)
    db.session.commit()
    
    # Check if order is fully paid
    if order.is_fully_paid():
        old_status = order.status
        order.status = OrderStatus.CONFIRMED
        db.session.commit()
        
        # Emit order status update to kitchen
        from app.socketio_events import emit_order_status_update
        emit_order_status_update(order, old_status)
        
        # Update kitchen stats
        emit_kitchen_stats()
        
        response_data = {
            'success': True,
            'message': f'Order {order.order_number} paid successfully with split bill',
            'redirect': url_for('orders.order_details', order_id=order_id),
            'update_totals': True,
            'order_data': order.to_dict(),
            'split_bill_id': split_bill.id
        }
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify(response_data)
        
        flash(response_data['message'], 'success')
        return redirect(response_data['redirect'])
    
    response_data = {
        'success': True,
        'message': f'Split bill processed: ₹{total_payment:.2f}',
        'update_totals': True,
        'order_data': order.to_dict(),
        'split_bill_id': split_bill.id
    }
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify(response_data)
    
    flash(response_data['message'], 'success')
    return redirect(url_for('orders.checkout', order_id=order_id))

# API endpoints
@bp.route('/api/cart')
@login_required
def api_cart():
    """API endpoint to get cart contents"""
    cart = session.get('cart', {})
    
    # Calculate totals
    subtotal = sum(item['unit_price'] * item['quantity'] for item in cart.values())
    
    # Get discount from session
    discount = session.get('cart_discount', {})
    discount_amount = discount.get('amount', 0.0)
    
    # Get GST settings from database
    try:
        from app.models.gst import GSTSetting
        gst_setting = GSTSetting.query.filter_by(is_active=True).first()
        
        if gst_setting:
            tax_rate = gst_setting.get_total_gst_rate()
            tax_description = f'GST ({tax_rate * 100:.1f}%)'
        else:
            # Fallback to default GST rate
            tax_rate = 0.18  # 18% GST
            tax_description = 'GST (18.0%)'
    except Exception:
        # Fallback to default GST rate if there's an error
        tax_rate = 0.18  # 18% GST
        tax_description = 'GST (18.0%)'
    
    # Calculate tax on discounted subtotal
    discounted_subtotal = subtotal - discount_amount
    tax = discounted_subtotal * tax_rate
    total = discounted_subtotal + tax
    
    return jsonify({
        'items': list(cart.values()),
        'subtotal': subtotal,
        'discount': discount,
        'discount_amount': discount_amount,
        'tax': tax,
        'total': total,
        'item_count': len(cart),
        'tax_rate': tax_rate,
        'tax_description': tax_description
    })


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

@bp.route('/api/item/<int:item_id>/variants')
@login_required
def api_item_variants(item_id):
    """API endpoint to get variants for a specific menu item"""
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

@bp.route('/email/receipt/<int:order_id>', methods=['POST'])
@login_required
def email_receipt(order_id):
    """Email receipt for an order"""
    order = Order.query.get_or_404(order_id)
    
    if not order.is_fully_paid():
        flash('Order must be fully paid before emailing receipt', 'error')
        return redirect(url_for('orders.checkout', order_id=order_id))
    
    customer_email = request.form.get('customer_email')
    if not customer_email:
        flash('Customer email is required', 'error')
        return redirect(url_for('orders.order_details', order_id=order_id))
    
    try:
        notification_service.send_order_receipt(order, email=customer_email)
        flash('Receipt emailed successfully', 'success')
    except Exception as e:
        flash(f'Error emailing receipt: {str(e)}', 'error')
    
    return redirect(url_for('orders.order_details', order_id=order_id))

@bp.route('/sms/receipt/<int:order_id>', methods=['POST'])
@login_required
def sms_receipt(order_id):
    """SMS receipt for an order"""
    order = Order.query.get_or_404(order_id)
    
    if not order.is_fully_paid():
        flash('Order must be fully paid before SMSing receipt', 'error')
        return redirect(url_for('orders.checkout', order_id=order_id))
    
    customer_phone = request.form.get('customer_phone')
    if not customer_phone:
        flash('Customer phone number is required', 'error')
        return redirect(url_for('orders.order_details', order_id=order_id))
    
    try:
        notification_service.send_order_receipt(order, phone=customer_phone)
        flash('Receipt sent via SMS successfully', 'success')
    except Exception as e:
        flash(f'Error sending SMS receipt: {str(e)}', 'error')
    
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

# Split Bill API endpoints
@bp.route('/api/orders/<int:order_id>/split-bill', methods=['GET'])
@login_required
def api_split_bill_calculate(order_id):
    """API endpoint to calculate split bill options"""
    order = Order.query.get_or_404(order_id)
    
    split_type = request.args.get('type', 'equal')
    number_of_splits = int(request.args.get('splits', 2))
    
    if number_of_splits < 2 or number_of_splits > 8:
        return jsonify({'error': 'Number of splits must be between 2 and 8'}), 400
    
    balance_due = order.get_balance_due()
    
    result = {
        'order_id': order_id,
        'balance_due': balance_due,
        'split_type': split_type,
        'number_of_splits': number_of_splits,
        'order_items': [item.to_dict() for item in order.items]
    }
    
    if split_type == 'equal':
        equal_amount = balance_due / number_of_splits
        result['splits'] = [
            {
                'id': i + 1,
                'name': f'Person {i + 1}',
                'amount': equal_amount,
                'payment_method': 'cash'
            }
            for i in range(number_of_splits)
        ]
    
    elif split_type == 'items':
        # Initialize empty splits for item-based splitting
        result['splits'] = [
            {
                'id': i + 1,
                'name': f'Person {i + 1}',
                'amount': 0,
                'payment_method': 'cash',
                'items': []
            }
            for i in range(number_of_splits)
        ]
    
    elif split_type == 'custom':
        # Initialize with zero amounts for custom splitting
        result['splits'] = [
            {
                'id': i + 1,
                'name': f'Person {i + 1}',
                'amount': 0,
                'payment_method': 'cash'
            }
            for i in range(number_of_splits)
        ]
    
    return jsonify(result)

@bp.route('/api/orders/validate-split', methods=['POST'])
@login_required
def api_validate_split():
    """API endpoint to validate split bill data"""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    order_id = data.get('order_id')
    split_type = data.get('split_type')
    splits = data.get('splits', [])
    
    if not order_id or not split_type or not splits:
        return jsonify({'error': 'Missing required fields'}), 400
    
    # Get order
    order = Order.query.get(order_id)
    if not order:
        return jsonify({'error': 'Order not found'}), 404
    
    balance_due = order.get_balance_due()
    
    # Validate splits
    total_allocated = 0
    for split in splits:
        amount = split.get('amount', 0)
        if amount <= 0:
            return jsonify({'error': f'Invalid amount for {split.get("name", "Unknown")}'}), 400
        total_allocated += amount
    
    # Check if total matches balance due
    tolerance = 0.01  # Small tolerance for floating point
    if abs(total_allocated - balance_due) > tolerance:
        return jsonify({
            'error': f'Total allocated (₹{total_allocated:.2f}) must equal balance due (₹{balance_due:.2f})',
            'total_allocated': total_allocated,
            'balance_due': balance_due,
            'difference': total_allocated - balance_due
        }), 400
    
    # Validate item-based splits
    if split_type == 'items':
        all_items = set(item.id for item in order.items)
        assigned_items = set()
        
        for split in splits:
            split_items = split.get('items', [])
            for item in split_items:
                if 'id' in item:
                    assigned_items.add(item['id'])
        
        if assigned_items != all_items:
            return jsonify({'error': 'All items must be assigned to splits'}), 400
    
    return jsonify({
        'valid': True,
        'message': 'Split validation successful',
        'total_allocated': total_allocated,
        'balance_due': balance_due
    })

@bp.route('/api/orders/<int:order_id>/split-history', methods=['GET'])
@login_required
def api_split_history(order_id):
    """API endpoint to get split bill history for an order"""
    order = Order.query.get_or_404(order_id)
    
    split_bills = SplitBill.query.filter_by(order_id=order_id).order_by(SplitBill.created_at.desc()).all()
    
    return jsonify({
        'order_id': order_id,
        'split_bills': [split_bill.to_dict() for split_bill in split_bills]
    })

@bp.route('/print/split-bill-receipt/<int:order_id>', methods=['GET'])
@login_required
def print_split_bill_receipt(order_id):
    """Print split bill receipt for an order"""
    order = Order.query.get_or_404(order_id)
    
    if not order.is_fully_paid():
        flash('Order must be fully paid before printing split bill receipt', 'error')
        return redirect(url_for('orders.checkout', order_id=order_id))
    
    # Get the most recent split bill for this order
    split_bill = SplitBill.query.filter_by(order_id=order_id).order_by(SplitBill.created_at.desc()).first()
    
    if not split_bill:
        flash('No split bill found for this order', 'error')
        return redirect(url_for('orders.order_details', order_id=order_id))
    
    return render_template('orders/split_bill_receipt.html', order=order, split_bill=split_bill)

@bp.route('/reports/split-bills')
@login_required
def split_bills_report():
    """Split bills report page"""
    # Get date range from query parameters
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    # Build query
    query = SplitBill.query.join(Order).join(User)
    
    # Filter by date range if provided
    if start_date:
        try:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            query = query.filter(SplitBill.created_at >= start_dt)
        except ValueError:
            flash('Invalid start date format', 'error')
    
    if end_date:
        try:
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
            # Add one day to include the entire end date
            end_dt = end_dt.replace(hour=23, minute=59, second=59)
            query = query.filter(SplitBill.created_at <= end_dt)
        except ValueError:
            flash('Invalid end date format', 'error')
    
    # Get split bills
    split_bills = query.order_by(SplitBill.created_at.desc()).limit(100).all()
    
    # Calculate statistics
    total_split_bills = len(split_bills)
    total_amount = sum(float(sb.total_amount) for sb in split_bills)
    
    # Group by split type
    split_type_counts = {}
    split_type_amounts = {}
    for sb in split_bills:
        split_type = sb.split_type
        split_type_counts[split_type] = split_type_counts.get(split_type, 0) + 1
        split_type_amounts[split_type] = split_type_amounts.get(split_type, 0) + float(sb.total_amount)
    
    # Group by payment method
    payment_method_counts = {}
    payment_method_amounts = {}
    for sb in split_bills:
        details = sb.get_split_details()
        for detail in details:
            method = detail.get('payment_method', 'unknown')
            payment_method_counts[method] = payment_method_counts.get(method, 0) + 1
            payment_method_amounts[method] = payment_method_amounts.get(method, 0) + float(detail.get('amount', 0))
    
    return render_template('orders/split_bills_report.html',
                        split_bills=split_bills,
                        total_split_bills=total_split_bills,
                        total_amount=total_amount,
                        split_type_counts=split_type_counts,
                        split_type_amounts=split_type_amounts,
                        payment_method_counts=payment_method_counts,
                        payment_method_amounts=payment_method_amounts,
                        start_date=start_date,
                        end_date=end_date)

@bp.route('/api/reports/split-bills')
@login_required
def api_split_bills_report():
    """API endpoint for split bills report data"""
    # Get date range from query parameters
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    # Build query
    query = SplitBill.query.join(Order).join(User)
    
    # Filter by date range if provided
    if start_date:
        try:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            query = query.filter(SplitBill.created_at >= start_dt)
        except ValueError:
            return jsonify({'error': 'Invalid start date format'}), 400
    
    if end_date:
        try:
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
            # Add one day to include the entire end date
            end_dt = end_dt.replace(hour=23, minute=59, second=59)
            query = query.filter(SplitBill.created_at <= end_dt)
        except ValueError:
            return jsonify({'error': 'Invalid end date format'}), 400
    
    # Get split bills
    split_bills = query.order_by(SplitBill.created_at.desc()).limit(200).all()
    
    # Calculate statistics
    total_split_bills = len(split_bills)
    total_amount = sum(float(sb.total_amount) for sb in split_bills)
    
    # Group by split type
    split_type_counts = {}
    split_type_amounts = {}
    for sb in split_bills:
        split_type = sb.split_type
        split_type_counts[split_type] = split_type_counts.get(split_type, 0) + 1
        split_type_amounts[split_type] = split_type_amounts.get(split_type, 0) + float(sb.total_amount)
    
    # Group by payment method
    payment_method_counts = {}
    payment_method_amounts = {}
    for sb in split_bills:
        details = sb.get_split_details()
        for detail in details:
            method = detail.get('payment_method', 'unknown')
            payment_method_counts[method] = payment_method_counts.get(method, 0) + 1
            payment_method_amounts[method] = payment_method_amounts.get(method, 0) + float(detail.get('amount', 0))
    
    return jsonify({
        'split_bills': [sb.to_dict() for sb in split_bills],
        'summary': {
            'total_split_bills': total_split_bills,
            'total_amount': total_amount,
            'split_type_counts': split_type_counts,
            'split_type_amounts': split_type_amounts,
            'payment_method_counts': payment_method_counts,
            'payment_method_amounts': payment_method_amounts
        }
    })

# Customer attachment routes
@bp.route('/<int:order_id>/attach-customer', methods=['POST'])
@login_required
def attach_customer(order_id):
    """Attach a customer to an order"""
    order = Order.query.get_or_404(order_id)
    
    if request.is_json:
        data = request.get_json()
        customer_id = data.get('customer_id')
    else:
        customer_id = request.form.get('customer_id', type=int)
    
    if not customer_id:
        return jsonify({'success': False, 'message': 'Customer ID is required'}), 400
    
    customer = Customer.query.get(customer_id)
    if not customer:
        return jsonify({'success': False, 'message': 'Customer not found'}), 404
    
    # Attach customer to order
    order.customer_id = customer_id
    db.session.commit()
    
    # Update customer statistics if order is paid
    if order.is_fully_paid():
        customer.update_order_statistics(float(order.total))
        db.session.commit()
    
    return jsonify({
        'success': True,
        'message': f'Customer {customer.get_full_name()} attached to order',
        'customer': customer.to_dict()
    })

# Cart customer selection routes
@bp.route('/cart/select-customer', methods=['POST'])
@login_required
def select_cart_customer():
    """Select customer for cart"""
    if request.is_json:
        data = request.get_json()
        customer_id = data.get('customer_id')
    else:
        customer_id = request.form.get('customer_id', type=int)
    
    if not customer_id:
        return jsonify({'success': False, 'message': 'Customer ID is required'}), 400
    
    customer = Customer.query.get(customer_id)
    if not customer:
        return jsonify({'success': False, 'message': 'Customer not found'}), 404
    
    # Store customer ID in session
    session['selected_customer_id'] = customer_id
    
    return jsonify({
        'success': True,
        'message': f'Customer {customer.get_full_name()} selected',
        'customer': customer.to_dict()
    })

@bp.route('/cart/clear-customer', methods=['POST'])
@login_required
def clear_cart_customer():
    """Clear customer selection from cart"""
    session.pop('selected_customer_id', None)
    
    return jsonify({
        'success': True,
        'message': 'Customer selection cleared'
    })

@bp.route('/<int:order_id>/remove-customer', methods=['POST'])
@login_required
def remove_customer(order_id):
    """Remove customer from an order"""
    order = Order.query.get_or_404(order_id)
    
    if not order.customer_id:
        return jsonify({'success': False, 'message': 'No customer attached to this order'}), 400
    
    customer = order.customer
    
    # Remove customer from order
    order.customer_id = None
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': f'Customer {customer.get_full_name()} removed from order'
    })

# TPOS API Routes
@bp.route('/api/categories')
@login_required
def api_categories():
    """API endpoint to get menu categories"""
    categories = Category.query.filter_by(is_active=True).order_by(Category.display_order).all()
    return jsonify({
        'categories': [category.to_dict() for category in categories]
    })

@bp.route('/api/menu-items')
@login_required
def api_menu_items():
    """API endpoint to get all menu items"""
    menu_items = MenuItem.query.filter_by(is_available=True).order_by(MenuItem.display_order).all()
    return jsonify({
        'items': [item.to_dict(include_variants=True, include_add_ons=True) for item in menu_items]
    })

@bp.route('/api/quick-items')
@login_required
def api_quick_items():
    """API endpoint to get frequently ordered items"""
    # This would typically be based on order history, for now return popular items
    quick_items = MenuItem.query.filter_by(is_available=True).order_by(MenuItem.display_order).limit(12).all()
    return jsonify({
        'items': [item.to_dict() for item in quick_items]
    })

@bp.route('/api/tables')
@login_required
def api_tables():
    """API endpoint to get tables with status"""
    tables = Table.query.filter_by(is_active=True).order_by(Table.number).all()
    
    # Add current order information
    for table in tables:
        table.current_order = table.get_current_order()
        if table.current_order:
            table.status_color = table.get_status_color()
            table.status_text = table.get_status_text()
    
    return jsonify({
        'tables': [table.to_dict(include_session=True) for table in tables]
    })

@bp.route('/select-table/<int:table_id>', methods=['POST'])
@login_required
def select_table(table_id):
    """Select a table for the current order"""
    table = Table.query.get_or_404(table_id)
    
    if not table.is_available():
        return jsonify({'success': False, 'message': 'Table is not available'}), 400
    
    # Store selected table in session
    session['selected_table_id'] = table_id
    
    return jsonify({
        'success': True,
        'message': f'Table {table.number} selected',
        'table': table.to_dict()
    })

@bp.route('/api/order-items/<int:order_id>')
@login_required
def api_order_items(order_id):
    """API endpoint to get items for a specific order"""
    order = Order.query.get_or_404(order_id)
    
    if not order:
        return jsonify({'error': 'Order not found'}), 404
    
    items = []
    for item in order.items:
        item_data = {
            'id': item.id,
            'menu_item_id': item.item_id,
            'name': item.menu_item.name if item.menu_item else 'Unknown Item',
            'quantity': item.quantity,
            'unit_price': float(item.unit_price),
            'total_price': float(item.get_total_price()),
            'variant_name': item.variant.name if item.variant else None,
            'notes': item.notes,
            'add_ons': [
                {
                    'id': addon.id,
                    'name': addon.name,
                    'price': float(addon.price)
                } for addon in item.add_ons
            ]
        }
        items.append(item_data)
    
    return jsonify({
        'order_id': order_id,
        'order_number': order.order_number,
        'items': items
    })

@bp.route('/hold-order', methods=['POST'])
@login_required
def hold_order():
    """Hold current order as draft"""
    cart = session.get('cart', {})
    
    if not cart:
        return jsonify({'success': False, 'message': 'Cart is empty'}), 400
    
    # Create held order record (this would need a HeldOrder model)
    # For now, just store in session
    held_order_id = f"held_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    session[held_order_id] = {
        'cart': cart,
        'customer_id': session.get('selected_customer_id'),
        'table_id': session.get('selected_table_id'),
        'order_type': session.get('order_type', 'table'),
        'discount': session.get('cart_discount', {}),
        'created_at': datetime.utcnow().isoformat()
    }
    
    # Clear current cart
    session.pop('cart', None)
    session.pop('selected_customer_id', None)
    session.pop('cart_discount', None)
    
    return jsonify({
        'success': True,
        'message': 'Order held successfully',
        'held_order_id': held_order_id
    })

@bp.route('/resume-order/<held_order_id>', methods=['POST'])
@login_required
def resume_order(held_order_id):
    """Resume a held order"""
    held_orders = {k: v for k, v in session.items() if k.startswith('held_')}
    
    if held_order_id not in held_orders:
        return jsonify({'success': False, 'message': 'Held order not found'}), 404
    
    held_order = held_orders[held_order_id]
    
    # Restore cart and customer
    session['cart'] = held_order['cart']
    if held_order.get('customer_id'):
        session['selected_customer_id'] = held_order['customer_id']
    
    if held_order.get('table_id'):
        session['selected_table_id'] = held_order['table_id']
    
    if held_order.get('order_type'):
        session['order_type'] = held_order['order_type']
    
    if held_order.get('discount'):
        session['cart_discount'] = held_order['discount']
    
    # Remove held order from session
    session.pop(held_order_id, None)
    
    return jsonify({
        'success': True,
        'message': 'Order resumed successfully'
    })

@bp.route('/held-orders')
@login_required
def list_held_orders():
    """List all held orders"""
    held_orders = {k: v for k, v in session.items() if k.startswith('held_')}
    
    return render_template('orders/held_orders.html', held_orders=held_orders)

@bp.route('/delete-held-order/<held_order_id>', methods=['POST'])
@login_required
def delete_held_order(held_order_id):
    """Delete a held order"""
    held_orders = {k: v for k, v in session.items() if k.startswith('held_')}
    
    if held_order_id not in held_orders:
        return jsonify({'success': False, 'message': 'Held order not found'}), 404
    
    # Remove held order from session
    session.pop(held_order_id, None)
    
    return jsonify({
        'success': True,
        'message': 'Held order deleted successfully'
    })

@bp.route('/kot-print/<int:order_id>')
@login_required
def kot_print(order_id):
    """Print KOT (Kitchen Order Ticket)"""
    order = Order.query.get_or_404(order_id)
    
    try:
        print_kitchen_ticket(order)
        return jsonify({
            'success': True,
            'message': 'KOT printed successfully'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error printing KOT: {str(e)}'
        }), 500

@bp.route('/set-order-type', methods=['POST'])
@login_required
def set_order_type():
    """Set the order type (table, takeaway, delivery)"""
    order_type = request.form.get('order_type')
    
    if order_type not in ['table', 'takeaway', 'delivery']:
        return jsonify({'success': False, 'message': 'Invalid order type'}), 400
    
    session['order_type'] = order_type
    
    return jsonify({
        'success': True,
        'message': f'Order type set to {order_type}'
    })

# Missing API routes that TPOS needs
@bp.route('/api/menu/reorder-categories', methods=['POST'])
@login_required
def api_reorder_categories():
    """API endpoint to reorder menu categories"""
    try:
        categories = Category.query.filter_by(is_active=True).order_by(Category.display_order).all()
        return jsonify({
            'categories': [category.to_dict() for category in categories]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/api/menu/reorder-items', methods=['POST'])
@login_required
def api_reorder_items():
    """API endpoint to reorder menu items"""
    try:
        menu_items = MenuItem.query.filter_by(is_available=True).order_by(MenuItem.display_order).all()
        return jsonify({
            'items': [item.to_dict(include_variants=True, include_add_ons=True) for item in menu_items]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/tables/api/list')
@login_required
def api_tables_list():
    """API endpoint to get tables list"""
    try:
        tables = Table.query.filter_by(is_active=True).order_by(Table.number).all()
        
        # Add status information
        table_list = []
        for table in tables:
            table_data = table.to_dict()
            table_data['status_color'] = table.get_status_color()
            table_data['status_text'] = table.get_status_text()
            table_list.append(table_data)
        
        return jsonify({
            'tables': table_list
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/customers/api/selected-customer')
@login_required
def api_selected_customer():
    """API endpoint to get selected customer"""
    try:
        customer_id = session.get('selected_customer_id')
        if customer_id:
            customer = Customer.query.get(customer_id)
            if customer:
                return jsonify({
                    'success': True,
                    'customer': customer.to_dict()
                })
        
        return jsonify({
            'success': False,
            'customer': None
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/process-payment', methods=['POST'])
@login_required
def process_cart_payment():
    """Process payment directly from cart (TPOS functionality)"""
    cart = session.get('cart', {})
    
    if not cart:
        return jsonify({'success': False, 'message': 'Cart is empty'}), 400
    
    try:
        # Get customer ID from session or form
        customer_id = session.get('selected_customer_id')
        
        # Get discount from session
        discount = session.get('cart_discount', {})
        
        # Create order from cart
        order = Order(
            user_id=current_user.id,
            customer_id=customer_id,
            status=OrderStatus.PENDING
        )
        
        # Apply discount if exists
        if discount:
            order.discount_type = discount.get('type')
            order.discount_amount = discount.get('amount', 0.0)
            order.discount_reason = discount.get('reason', '')
        
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
                # Handle both ID-only and detail objects
                if isinstance(add_on_detail, dict):
                    add_on_id = add_on_detail.get('id')
                else:
                    add_on_id = add_on_detail
                
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
        
        # Get payment data from form
        payment_method = request.form.get('payment_method')
        amount = float(request.form.get('amount', order.total))
        
        if not payment_method:
            return jsonify({'success': False, 'message': 'Payment method is required'}), 400
        
        # Create payment
        payment = Payment(
            order_id=order.id,
            amount=amount,
            method=PaymentMethod(payment_method)
        )
        
        db.session.add(payment)
        db.session.commit()
        
        # Check if order is fully paid
        if order.is_fully_paid():
            old_status = order.status
            order.status = OrderStatus.CONFIRMED
            db.session.commit()
            
            # Emit order status update to kitchen
            from app.socketio_events import emit_order_status_update
            emit_order_status_update(order, old_status)
            
            # Update kitchen stats
            emit_kitchen_stats()
            
            # Print kitchen ticket if configured
            try:
                print_kitchen_ticket(order)
            except Exception as e:
                print(f"Error printing kitchen ticket: {e}")
        
        # Clear cart and customer selection
        session.pop('cart', None)
        session.pop('selected_customer_id', None)
        session.pop('cart_discount', None)
        
        return jsonify({
            'success': True,
            'message': f'Payment processed successfully for order {order.order_number}',
            'order_id': order.id,
            'order_number': order.order_number,
            'redirect': url_for('orders.order_details', order_id=order.id)
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@bp.route('/api/payment-methods')
@login_required
def api_payment_methods():
    """API endpoint to get available payment methods"""
    try:
        payment_methods = [
            {'key': 'cash', 'name': 'Cash', 'icon': 'fas fa-money-bill-wave'},
            {'key': 'card', 'name': 'Card', 'icon': 'fas fa-credit-card'},
            {'key': 'mobile', 'name': 'Mobile', 'icon': 'fas fa-mobile-alt'},
            {'key': 'credit', 'name': 'Credit', 'icon': 'fas fa-credit-card'}
        ]
        
        return jsonify({
            'payment_methods': payment_methods
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/customers/api/search')
@login_required
def api_search_customers():
    """API endpoint to search customers"""
    from sqlalchemy import or_
    
    query = request.args.get('q', '')
    try:
        customers = []
        if query and len(query) >= 2:
            customers = Customer.query.filter(
                or_(
                    Customer.first_name.ilike(f'%{query}%'),
                    Customer.last_name.ilike(f'%{query}%'),
                    Customer.email.ilike(f'%{query}%'),
                    Customer.phone.ilike(f'%{query}%'),
                    Customer.customer_code.ilike(f'%{query}%')
                ),
                Customer.is_active == True
            ).limit(10).all()
        
        return jsonify({
            'customers': [customer.to_dict() for customer in customers]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Table Order Management Routes
@bp.route('/tables/<int:table_id>/create-order', methods=['GET', 'POST'])
@login_required
def create_table_order(table_id):
    """Create order directly for table"""
    table = Table.query.get_or_404(table_id)
    
    if not table.is_available() and not table.get_current_order():
        flash('Table is not available for new orders', 'error')
        return redirect(url_for('tables.floor_plan'))
    
    if request.method == 'GET':
        # Show order creation form for table
        return render_template('orders/table_order.html', table=table)
    
    # POST - create order from form data
    cart = session.get('cart', {})
    
    if not cart:
        flash('Cart is empty', 'error')
        return redirect(url_for('orders.view_cart'))
    
    # Get customer ID from form or session
    customer_id = request.form.get('customer_id', type=int) or session.get('selected_customer_id')
    seat_number = request.form.get('seat_number')
    course_number = request.form.get('course_number', type=int, default=1)
    
    # Create order for table
    order = Order(
        table_id=table_id,
        waiter_id=current_user.id,
        seat_number=seat_number,
        course_number=course_number,
        user_id=current_user.id,
        customer_id=customer_id,
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
        for add_on_detail in cart_item['add_ons']:
            if isinstance(add_on_detail, dict):
                add_on_id = add_on_detail.get('id')
            else:
                add_on_id = add_on_detail
                
            add_on = AddOn.query.get(add_on_id)
            if add_on:
                order_item.add_ons.append(add_on)
        
        order.items.append(order_item)
    
    # Calculate totals
    order.calculate_totals()
    
    db.session.add(order)
    db.session.commit()
    
    # Update table status
    table.occupy()
    db.session.commit()
    
    # Refresh order to load relationships
    db.session.refresh(order)
    
    # Emit new order notification to kitchen via WebSocket
    emit_new_order(order)
    
    # Update kitchen stats
    emit_kitchen_stats()
    
    # Print kitchen ticket if configured
    try:
        print_kitchen_ticket(order)
    except Exception as e:
        print(f"Error printing kitchen ticket: {e}")
    
    # Clear cart and customer selection
    session.pop('cart', None)
    session.pop('selected_customer_id', None)
    
    flash(f'Order {order.order_number} created for table {table.number}', 'success')
    
    if request.headers.get('HX-Request'):
        return render_template('orders/partials/order_success.html', order=order)
    
    return redirect(url_for('orders.order_details', order_id=order.id))

@bp.route('/tables/<int:table_id>/orders')
@login_required
def table_orders(table_id):
    """View all orders for table"""
    table = Table.query.get_or_404(table_id)
    
    # Get all orders for this table
    orders = Order.query.filter_by(table_id=table_id).order_by(Order.created_at.desc()).limit(50).all()
    
    return render_template('orders/table_orders.html', table=table, orders=orders)

@bp.route('/orders/table/<int:table_id>/add-item', methods=['POST'])
@login_required
def add_item_to_table_order(table_id):
    """Add item to existing table order"""
    table = Table.query.get_or_404(table_id)
    
    # Get current active order for table
    current_order = table.get_current_order()
    
    if not current_order:
        flash('No active order found for this table', 'error')
        return redirect(url_for('tables.floor_plan'))
    
    if not current_order.can_be_modified():
        flash('Order cannot be modified in current status', 'error')
        return redirect(url_for('orders.order_details', order_id=current_order.id))
    
    # Get item data from form
    item_id = request.form.get('item_id', type=int)
    quantity = request.form.get('quantity', type=int, default=1)
    variant_id = request.form.get('variant_id', type=int)
    add_on_ids = request.form.getlist('add_ons')
    notes = request.form.get('notes', '')
    seat_number = request.form.get('seat_number')
    
    if not item_id:
        flash('Menu item is required', 'error')
        return redirect(url_for('orders.order_details', order_id=current_order.id))
    
    # Get menu item
    menu_item = MenuItem.query.get_or_404(item_id)
    
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
    
    flash(f'{menu_item.name} added to order {current_order.order_number}', 'success')
    
    if request.headers.get('HX-Request'):
        return render_template('orders/partials/order_items.html', order=current_order)
    
    return redirect(url_for('orders.order_details', order_id=current_order.id))

@bp.route('/orders/<int:order_id>/transfer-table', methods=['GET', 'POST'])
@login_required
def transfer_order_table(order_id):
    """Transfer order to different table"""
    order = Order.query.get_or_404(order_id)
    
    if not order.can_be_transferred():
        flash('Order cannot be transferred in current status', 'error')
        return redirect(url_for('orders.order_details', order_id=order_id))
    
    if request.method == 'GET':
        # Show transfer form
        tables = Table.query.filter_by(is_active=True).order_by(Table.number).all()
        available_tables = [t for t in tables if t.id != order.table_id and t.is_available()]
        
        return render_template('orders/transfer_order.html',
                           order=order,
                           available_tables=available_tables)
    
    # POST - process transfer
    new_table_id = request.form.get('new_table_id', type=int)
    
    if not new_table_id:
        flash('Please select a destination table', 'error')
        return redirect(url_for('orders.transfer_order_table', order_id=order_id))
    
    success, message = order.transfer_to_table(new_table_id, current_user.id)
    
    if success:
        flash(message, 'success')
    else:
        flash(message, 'error')
    
    return redirect(url_for('orders.order_details', order_id=order_id))

@bp.route('/orders/<int:order_id>/split-by-seat', methods=['GET', 'POST'])
@login_required
def split_order_by_seat(order_id):
    """Split order by seat"""
    order = Order.query.get_or_404(order_id)
    
    if not order.can_be_split():
        flash('Order cannot be split in current status', 'error')
        return redirect(url_for('orders.order_details', order_id=order_id))
    
    if request.method == 'GET':
        # Show split form
        return render_template('orders/split_order.html', order=order)
    
    # POST - process split
    seat_assignments = {}
    
    # Parse seat assignments from form
    for key, value in request.form.items():
        if key.startswith('seat_'):
            seat_number = key.replace('seat_', '')
            item_ids = request.form.getlist(f'items_{seat_number}')
            if item_ids:
                seat_assignments[seat_number] = [int(item_id) for item_id in item_ids if item_id.isdigit()]
    
    if not seat_assignments:
        flash('Please assign items to seats', 'error')
        return redirect(url_for('orders.split_order_by_seat', order_id=order_id))
    
    success, message = order.split_by_seat(seat_assignments)
    
    if success:
        flash(message, 'success')
        return redirect(url_for('orders.order_details', order_id=order_id))
    else:
        flash(message, 'error')
        return redirect(url_for('orders.split_order_by_seat', order_id=order_id))

@bp.route('/orders/<int:order_id>/merge', methods=['GET', 'POST'])
@login_required
def merge_orders(order_id):
    """Merge multiple orders"""
    primary_order = Order.query.get_or_404(order_id)
    
    if not primary_order.can_be_merged():
        flash('Order cannot be merged in current status', 'error')
        return redirect(url_for('orders.order_details', order_id=order_id))
    
    if request.method == 'GET':
        # Show merge form
        # Get other orders that can be merged
        if primary_order.table_id:
            other_orders = Order.query.filter(
                Order.table_id == primary_order.table_id,
                Order.id != order_id,
                Order.status.in_([OrderStatus.PENDING, OrderStatus.CONFIRMED])
            ).all()
        else:
            other_orders = []
        
        return render_template('orders/merge_orders.html',
                           primary_order=primary_order,
                           other_orders=other_orders)
    
    # POST - process merge
    other_order_id = request.form.get('other_order_id', type=int)
    
    if not other_order_id:
        flash('Please select an order to merge', 'error')
        return redirect(url_for('orders.merge_orders', order_id=order_id))
    
    success, message = primary_order.merge_with_order(other_order_id, current_user.id)
    
    if success:
        flash(message, 'success')
    else:
        flash(message, 'error')
    
    return redirect(url_for('orders.order_details', order_id=order_id))

@bp.route('/api/gst-settings')
@login_required
def api_gst_settings():
    """API endpoint to get GST settings"""
    try:
        # Get GST settings from database
        from app.models.gst import GSTSetting
        
        # For now, use default restaurant (this would be enhanced in a multi-tenant setup)
        gst_setting = GSTSetting.query.filter_by(is_active=True).first()
        
        if gst_setting:
            gst_settings = {
                'enabled': True,
                'cgst_rate': float(gst_setting.cgst_rate),
                'sgst_rate': float(gst_setting.sgst_rate),
                'igst_rate': float(gst_setting.igst_rate),
                'cess_rate': float(gst_setting.cess_rate),
                'total_rate': gst_setting.get_total_gst_rate(),
                'description': f'GST ({gst_setting.get_total_gst_rate() * 100:.1f}%)'
            }
        else:
            # Fallback to default GST rates
            gst_settings = {
                'enabled': True,
                'cgst_rate': 9.0,  # 9% CGST
                'sgst_rate': 9.0,  # 9% SGST
                'igst_rate': 0.0,  # 0% IGST
                'cess_rate': 0.0,  # 0% CESS
                'total_rate': 18.0,  # Total 18% GST
                'description': 'GST (18.0%)'
            }
        
        return jsonify(gst_settings)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/apply-cart-discount', methods=['POST'])
@login_required
def apply_cart_discount():
    """Apply discount to cart"""
    try:
        data = request.get_json()
        discount_type = data.get('discount_type')  # 'percentage' or 'fixed'
        discount_value = data.get('discount_value', type=float)
        discount_reason = data.get('discount_reason', '')
        
        if not discount_type or not discount_value or discount_value <= 0:
            return jsonify({'success': False, 'message': 'Invalid discount details'}), 400
        
        # Store discount in session
        cart = session.get('cart', {})
        
        # Calculate discount amount
        subtotal = sum(item['unit_price'] * item['quantity'] for item in cart.values())
        
        if discount_type == 'percentage':
            if discount_value > 100:
                return jsonify({'success': False, 'message': 'Percentage discount cannot exceed 100%'}), 400
            discount_amount = subtotal * (discount_value / 100)
        else:  # fixed
            if discount_value > subtotal:
                return jsonify({'success': False, 'message': 'Fixed discount cannot exceed subtotal'}), 400
            discount_amount = discount_value
        
        # Store discount in session
        session['cart_discount'] = {
            'type': discount_type,
            'value': discount_value,
            'amount': discount_amount,
            'reason': discount_reason
        }
        
        return jsonify({
            'success': True,
            'message': f'Discount applied: ₹{discount_amount:.2f}',
            'discount_amount': discount_amount
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@bp.route('/remove-cart-discount', methods=['POST'])
@login_required
def remove_cart_discount():
    """Remove discount from cart"""
    try:
        session.pop('cart_discount', None)
        return jsonify({
            'success': True,
            'message': 'Discount removed'
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500