from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app.tables import bp
from app.models.table import Table, TableStatus, TableSession, TableMerge
from app.models.table_assignment import TableAssignment
from app.models.order import Order, OrderStatus
from app.models.user import User
from app import db
from datetime import datetime

@bp.route('/floor-plan')
@login_required
def floor_plan():
    """Display restaurant floor plan"""
    if not current_user.can_access_manager_features():
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    tables = Table.query.filter_by(is_active=True).all()
    
    if request.headers.get('HX-Request'):
        return render_template('tables/partials/floor_plan.html', tables=tables)
    
    return render_template('tables/floor_plan.html', tables=tables)

@bp.route('/manage')
@login_required
def manage_tables():
    """Manage tables"""
    if not current_user.can_access_manager_features():
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    tables = Table.query.order_by(Table.number).all()
    
    return render_template('tables/manage.html', tables=tables)

@bp.route('/new', methods=['GET', 'POST'])
@login_required
def create_table():
    """Create a new table"""
    if not current_user.can_access_manager_features():
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        number = request.form.get('number')
        capacity = request.form.get('capacity', type=int)
        floor_section = request.form.get('floor_section')
        floor_position_x = request.form.get('floor_position_x', type=int, default=0)
        floor_position_y = request.form.get('floor_position_y', type=int, default=0)
        
        if number and capacity:
            table = Table(
                number=number,
                capacity=capacity,
                floor_section=floor_section,
                floor_position_x=floor_position_x,
                floor_position_y=floor_position_y
            )
            db.session.add(table)
            db.session.commit()
            
            flash(f'Table {number} created successfully', 'success')
            
            if request.headers.get('HX-Request'):
                return render_template('tables/partials/table_card.html', table=table)
            
            return redirect(url_for('tables.manage_tables'))
    
    return render_template('tables/table_form.html')

@bp.route('/<int:table_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_table(table_id):
    """Edit an existing table"""
    if not current_user.can_access_manager_features():
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    table = Table.query.get_or_404(table_id)
    
    if request.method == 'POST':
        table.number = request.form.get('number')
        table.capacity = request.form.get('capacity', type=int)
        table.floor_section = request.form.get('floor_section')
        table.floor_position_x = request.form.get('floor_position_x', type=int)
        table.floor_position_y = request.form.get('floor_position_y', type=int)
        table.is_active = 'is_active' in request.form
        
        db.session.commit()
        
        flash(f'Table {table.number} updated successfully', 'success')
        
        if request.headers.get('HX-Request'):
            return render_template('tables/partials/table_card.html', table=table)
        
        return redirect(url_for('tables.manage_tables'))
    
    return render_template('tables/table_form.html', table=table, edit_mode=True)

@bp.route('/<int:table_id>/delete', methods=['POST'])
@login_required
def delete_table(table_id):
    """Delete a table"""
    if not current_user.can_access_manager_features():
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    table = Table.query.get_or_404(table_id)
    
    # Check if table has active orders
    active_order = table.get_current_order()
    if active_order:
        flash('Cannot delete table with active order', 'error')
        return redirect(url_for('tables.manage_tables'))
    
    db.session.delete(table)
    db.session.commit()
    
    flash(f'Table {table.number} deleted successfully', 'success')
    
    if request.headers.get('HX-Request'):
        return ''
    
    return redirect(url_for('tables.manage_tables'))


@bp.route('/<int:table_id>/position', methods=['POST'])
@login_required
def update_table_position(table_id):
    """Update table position on floor plan"""
    if not current_user.can_access_manager_features():
        return jsonify({'error': 'Access denied'}), 403
    
    table = Table.query.get_or_404(table_id)
    data = request.get_json()
    
    if data:
        table.floor_position_x = int(data.get('x', 0))
        table.floor_position_y = int(data.get('y', 0))
        table.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Position updated'})
    
    return jsonify({'error': 'Invalid data'}), 400

@bp.route('/<int:table_id>/assign-order', methods=['POST'])
@login_required
def assign_order(table_id):
    """Assign order to table"""
    if not current_user.can_access_manager_features():
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    table = Table.query.get_or_404(table_id)
    order_id = request.form.get('order_id', type=int)
    
    if order_id:
        order = Order.query.get_or_404(order_id)
        
        # Check if order is already assigned to another table
        if order.table_id and order.table_id != table_id:
            flash('Order is already assigned to another table', 'error')
            return redirect(url_for('tables.floor_plan'))
        
        # Assign order to table
        order.table_id = table_id
        order.status = OrderStatus.CONFIRMED
        db.session.commit()
        
        # Update table status
        table.occupy()
        db.session.commit()
        
        flash(f'Order {order.order_number} assigned to table {table.number}', 'success')
    
    if request.headers.get('HX-Request'):
        return render_template('tables/partials/table_card.html', table=table)
    
    return redirect(url_for('tables.floor_plan'))

@bp.route('/<int:table_id>/free', methods=['POST'])
@login_required
def free_table(table_id):
    """Free a table"""
    if not current_user.can_access_manager_features():
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    table = Table.query.get_or_404(table_id)
    
    # Complete any active session
    current_session = table.get_current_session()
    if current_session:
        current_session.end_session()
        db.session.commit()
    
    table.free()
    db.session.commit()
    
    flash(f'Table {table.number} freed', 'success')
    
    if request.headers.get('HX-Request'):
        return render_template('tables/partials/table_card.html', table=table)
    
    return redirect(url_for('tables.floor_plan'))

@bp.route('/<int:table_id>/status', methods=['POST'])
@login_required
def update_table_status(table_id):
    """Update table status"""
    if not current_user.can_access_manager_features():
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    table = Table.query.get_or_404(table_id)
    new_status = request.form.get('status')
    
    if new_status:
        try:
            status = TableStatus(new_status)
            
            if status == TableStatus.FREE:
                table.free()
            elif status == TableStatus.OCCUPIED:
                table.occupy()
            elif status == TableStatus.CLEANING:
                table.set_cleaning()
            elif status == TableStatus.RESERVED:
                table.reserve()
            elif status == TableStatus.MAINTENANCE:
                table.status = TableStatus.MAINTENANCE
                table.updated_at = datetime.utcnow()
            
            db.session.commit()
            
            flash(f'Table {table.number} status updated to {status}', 'success')
            
        except ValueError:
            flash('Invalid status', 'error')
    
    if request.headers.get('HX-Request'):
        return render_template('tables/partials/table_card.html', table=table)
    
    return redirect(url_for('tables.floor_plan'))

# API endpoints
@bp.route('/api/tables')
@login_required
def get_tables():
    """API endpoint to get all tables"""
    tables = Table.query.filter_by(is_active=True).all()
    return jsonify([table.to_dict(include_session=True) for table in tables])

@bp.route('/api/table/<int:table_id>')
@login_required
def get_table(table_id):
    """API endpoint to get specific table"""
    table = Table.query.get_or_404(table_id)
    return jsonify(table.to_dict(include_session=True))

@bp.route('/api/sections')
@login_required
def get_sections():
    """API endpoint to get floor sections"""
    sections = db.session.query(Table.floor_section).distinct().all()
    return jsonify([section[0] for section in sections if section[0]])

@bp.route('/partials/table-list')
@login_required
def partials_table_list():
    """Return table list partial for HTMX requests"""
    if not current_user.can_access_manager_features():
        return '', 403  # Forbidden
    
    # Get query parameters
    search = request.args.get('search', '')
    status = request.args.get('status', '')
    
    # Build query
    query = Table.query
    
    if search:
        query = query.filter(
            Table.number.ilike(f'%{search}%') |
            Table.name.ilike(f'%{search}%')
        )
    
    if status:
        try:
            query = query.filter(Table.status == TableStatus(status))
        except ValueError:
            pass  # Invalid status, ignore
    
    tables = query.order_by(Table.number).all()
    
    return render_template('tables/partials/table_list.html', tables=tables)

@bp.route('/merge', methods=['GET', 'POST'])
@login_required
def merge_tables():
    """Merge two or more tables"""
    if not current_user.can_access_manager_features():
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        parent_table_id = request.form.get('parent_table_id', type=int)
        child_table_ids = request.form.getlist('child_table_ids', type=int)
        notes = request.form.get('notes', '')
        
        if not parent_table_id or not child_table_ids:
            flash('Please select a parent table and at least one table to merge', 'error')
            return redirect(url_for('tables.merge_tables'))
        
        parent_table = Table.query.get_or_404(parent_table_id)
        
        # Check if parent table can be used for merging
        if not parent_table.can_be_merged():
            flash(f'Table {parent_table.number} cannot be used for merging', 'error')
            return redirect(url_for('tables.merge_tables'))
        
        # Merge each child table
        merge_results = []
        for child_id in child_table_ids:
            child_table = Table.query.get_or_404(child_id)
            
            if not child_table.can_be_merged():
                merge_results.append(f"Table {child_table.number} cannot be merged (not available)")
                continue
            
            success, message = parent_table.merge_with(child_table, current_user, notes)
            if success:
                merge_results.append(message)
            else:
                merge_results.append(f"Failed to merge table {child_table.number}: {message}")
        
        if all("merged with" in result for result in merge_results):
            flash('Tables merged successfully', 'success')
        else:
            flash('Some merges failed: ' + '; '.join(merge_results), 'warning')
        
        return redirect(url_for('tables.floor_plan'))
    
    # GET request - show merge form
    tables = Table.query.filter_by(is_active=True).order_by(Table.number).all()
    available_tables = [t for t in tables if t.can_be_merged()]
    
    return render_template('tables/merge_tables.html',
                         tables=available_tables,
                         sections=db.session.query(Table.floor_section).distinct().all())

@bp.route('/split/<int:table_id>', methods=['GET', 'POST'])
@login_required
def split_table(table_id):
    """Split a merged table"""
    if not current_user.can_access_manager_features():
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    table = Table.query.get_or_404(table_id)
    
    if request.method == 'POST':
        notes = request.form.get('notes', '')
        
        if not table.can_be_split():
            flash(f'Table {table.number} cannot be split', 'error')
            return redirect(url_for('tables.split_table', table_id=table_id))
        
        success, message = table.split_from(current_user, notes)
        
        if success:
            flash(message, 'success')
        else:
            flash(f'Failed to split table: {message}', 'error')
        
        return redirect(url_for('tables.floor_plan'))
    
    # GET request - show split confirmation
    merge_info = table.get_merge_info()
    
    return render_template('tables/split_table.html',
                         table=table,
                         merge_info=merge_info)

@bp.route('/api/merge-history')
@login_required
def merge_history():
    """API endpoint to get table merge/split history"""
    if not current_user.can_access_manager_features():
        return jsonify({'error': 'Access denied'}), 403
    
    history = TableMerge.query.order_by(TableMerge.merged_at.desc()).limit(50).all()
    return jsonify([merge.to_dict() for merge in history])

@bp.route('/api/available-for-merge')
@login_required
def available_for_merge():
    """API endpoint to get tables available for merging"""
    if not current_user.can_access_manager_features():
        return jsonify({'error': 'Access denied'}), 403
    
    tables = Table.query.filter_by(is_active=True).all()
    available = [t.to_dict() for t in tables if t.can_be_merged()]
    
    return jsonify({
        'tables': available,
        'sections': list(set([t.floor_section for t in available if t.floor_section]))
    })

# Table Assignment Routes
@bp.route('/<int:table_id>/assign-waiter', methods=['GET', 'POST'])
@login_required
def assign_waiter(table_id):
    """Assign a waiter to a table"""
    if not current_user.can_access_manager_features():
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    table = Table.query.get_or_404(table_id)
    
    if request.method == 'POST':
        waiter_id = request.form.get('waiter_id', type=int)
        notes = request.form.get('notes', '')
        
        if not waiter_id:
            flash('Please select a waiter', 'error')
            return render_template('tables/assign_waiter.html', table=table)
        
        # Verify waiter exists and has appropriate role
        waiter = User.query.get(waiter_id)
        if not waiter or waiter.role not in ['staff', 'employee', 'cashier', 'manager']:
            flash('Invalid waiter selected', 'error')
            return render_template('tables/assign_waiter.html', table=table)
        
        # Assign waiter to table
        assignment = table.assign_waiter(waiter_id, current_user.id, notes)
        
        flash(f'{waiter.name} assigned to table {table.number}', 'success')
        
        if request.headers.get('HX-Request'):
            return render_template('tables/partials/table_assignment_info.html', table=table)
        
        return redirect(url_for('tables.manage_tables'))
    
    # GET request - show assignment form
    # Get available waiters (staff, employee, cashier, manager roles)
    available_waiters = User.query.filter(
        User.role.in_(['staff', 'employee', 'cashier', 'manager']),
        User.user_active == True
    ).all()
    
    return render_template('tables/assign_waiter.html',
                         table=table,
                         available_waiters=available_waiters)

@bp.route('/<int:table_id>/relieve-waiter', methods=['POST'])
@login_required
def relieve_waiter(table_id):
    """Relieve waiter from table"""
    if not current_user.can_access_manager_features():
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    table = Table.query.get_or_404(table_id)
    notes = request.form.get('notes', '')
    
    success = table.relieve_waiter(current_user.id, notes)
    
    if success:
        current_assignment = table.get_current_assignment()
        if current_assignment and current_assignment.waiter:
            flash(f'{current_assignment.waiter.name} relieved from table {table.number}', 'success')
        else:
            flash(f'Waiter relieved from table {table.number}', 'success')
    else:
        flash('No active assignment found for this table', 'error')
    
    if request.headers.get('HX-Request'):
        return render_template('tables/partials/table_assignment_info.html', table=table)
    
    return redirect(url_for('tables.manage_tables'))

@bp.route('/waiter-assignments')
@login_required
def waiter_assignments():
    """View all waiter assignments"""
    if not current_user.can_access_manager_features():
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    # Get all active assignments
    active_assignments = TableAssignment.query.filter_by(is_active=True).all()
    
    # Get recent assignment history
    recent_assignments = TableAssignment.query.order_by(
        TableAssignment.assigned_at.desc()
    ).limit(50).all()
    
    return render_template('tables/waiter_assignments.html',
                         active_assignments=active_assignments,
                         recent_assignments=recent_assignments)

@bp.route('/my-assignments')
@login_required
def my_assignments():
    """View current user's table assignments"""
    # Only waiters can view their assignments
    if current_user.role not in ['staff', 'employee', 'cashier', 'manager']:
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    # Get active assignments for current user
    active_assignments = TableAssignment.get_active_assignments_for_waiter(current_user.id)
    
    # Get assignment history for current user
    assignment_history = TableAssignment.get_assignment_history_for_waiter(current_user.id, limit=50)
    
    return render_template('tables/my_tables.html',
                         active_assignments=active_assignments,
                         assignment_history=assignment_history)

# API endpoints for table assignments
@bp.route('/api/table-assignments')
@login_required
def api_table_assignments():
    """API endpoint to get all table assignments"""
    if not current_user.can_access_manager_features():
        return jsonify({'error': 'Access denied'}), 403
    
    assignments = TableAssignment.query.order_by(
        TableAssignment.assigned_at.desc()
    ).limit(100).all()
    
    return jsonify([assignment.to_dict(include_performance=True) for assignment in assignments])

@bp.route('/api/table/<int:table_id>/current-assignment')
@login_required
def api_current_assignment(table_id):
    """API endpoint to get current assignment for a table"""
    table = Table.query.get_or_404(table_id)
    assignment = table.get_current_assignment()
    
    if assignment:
        return jsonify(assignment.to_dict(include_performance=True))
    else:
        return jsonify({'message': 'No active assignment found'}), 404

@bp.route('/api/waiter/<int:waiter_id>/assignments')
@login_required
def api_waiter_assignments(waiter_id):
    """API endpoint to get assignments for a specific waiter"""
    # Users can only view their own assignments unless they're managers
    if current_user.id != waiter_id and not current_user.can_access_manager_features():
        return jsonify({'error': 'Access denied'}), 403
    
    active_assignments = TableAssignment.get_active_assignments_for_waiter(waiter_id)
    assignment_history = TableAssignment.get_assignment_history_for_waiter(waiter_id, limit=50)
    
    return jsonify({
        'active_assignments': [assignment.to_dict(include_performance=True) for assignment in active_assignments],
        'assignment_history': [assignment.to_dict(include_performance=True) for assignment in assignment_history]
    })

# Table Order Management Routes
@bp.route('/<int:table_id>/quick-order', methods=['GET', 'POST'])
@login_required
def quick_table_order(table_id):
    """Quick order creation for table"""
    table = Table.query.get_or_404(table_id)
    
    if not table.is_available() and not table.get_current_order():
        flash('Table is not available for new orders', 'error')
        return redirect(url_for('tables.floor_plan'))
    
    if request.method == 'GET':
        # Get menu items for quick order
        categories = Category.query.filter_by(is_active=True).order_by(Category.display_order).all()
        return render_template('tables/quick_order.html', table=table, categories=categories)
    
    # POST - create quick order
    item_id = request.form.get('item_id', type=int)
    quantity = request.form.get('quantity', type=int, default=1)
    notes = request.form.get('notes', '')
    
    if not item_id:
        flash('Please select a menu item', 'error')
        return redirect(url_for('tables.quick_table_order', table_id=table_id))
    
    # Get or create current order for table
    current_order = table.get_current_order()
    if not current_order:
        # Create new order
        current_order = Order(
            table_id=table_id,
            waiter_id=current_user.id,
            user_id=current_user.id,
            status=OrderStatus.PENDING
        )
        db.session.add(current_order)
        db.session.commit()
        
        # Update table status
        table.occupy()
        db.session.commit()
    
    if not current_order.can_be_modified():
        flash('Order cannot be modified in current status', 'error')
        return redirect(url_for('tables.quick_table_order', table_id=table_id))
    
    # Add item to order
    menu_item = MenuItem.query.get_or_404(item_id)
    order_item = OrderItem(
        order_id=current_order.id,
        item_id=item_id,
        quantity=quantity,
        unit_price=float(menu_item.price),
        notes=notes
    )
    
    db.session.add(order_item)
    current_order.calculate_totals()
    db.session.commit()
    
    # Emit order update to kitchen
    from app.socketio_events import emit_order_status_update
    emit_order_status_update(current_order, current_order.status)
    
    flash(f'{menu_item.name} added to table {table.number}', 'success')
    
    return redirect(url_for('tables.quick_table_order', table_id=table_id))

@bp.route('/<int:table_id>/current-order')
@login_required
def current_table_order(table_id):
    """View current order for table"""
    table = Table.query.get_or_404(table_id)
    current_order = table.get_current_order()
    
    if not current_order:
        flash('No active order for this table', 'info')
        return redirect(url_for('tables.floor_plan'))
    
    return render_template('tables/current_order.html', table=table, order=current_order)

@bp.route('/<int:table_id>/order-history')
@login_required
def table_order_history(table_id):
    """View order history for table"""
    table = Table.query.get_or_404(table_id)
    
    # Get order history
    orders = Order.query.filter_by(table_id=table_id).order_by(Order.created_at.desc()).limit(100).all()
    
    return render_template('tables/order_history.html', table=table, orders=orders)

@bp.route('/<int:table_id>/settle-order', methods=['GET', 'POST'])
@login_required
def settle_table_order(table_id):
    """Settle current order for table"""
    table = Table.query.get_or_404(table_id)
    current_order = table.get_current_order()
    
    if not current_order:
        flash('No active order for this table', 'error')
        return redirect(url_for('tables.floor_plan'))
    
    if request.method == 'GET':
        return render_template('tables/settle_order.html', table=table, order=current_order)
    
    # POST - process settlement
    action = request.form.get('action')
    
    if action == 'mark_paid':
        # Mark order as paid (for cash payments)
        payment_method = request.form.get('payment_method', 'cash')
        amount = float(request.form.get('amount', current_order.get_balance_due()))
        
        payment = Payment(
            order_id=current_order.id,
            amount=amount,
            method=PaymentMethod(payment_method)
        )
        
        db.session.add(payment)
        
        if current_order.is_fully_paid():
            old_status = current_order.status
            current_order.status = OrderStatus.CONFIRMED
            current_order.completed_at = datetime.utcnow()
            
            # Free the table
            table.free()
            
            # Emit order status update
            from app.socketio_events import emit_order_status_update, emit_kitchen_stats
            emit_order_status_update(current_order, old_status)
            emit_kitchen_stats()
        
        db.session.commit()
        flash(f'Order {current_order.order_number} marked as paid', 'success')
        
    elif action == 'transfer':
        # Transfer to another table
        new_table_id = request.form.get('new_table_id', type=int)
        if new_table_id:
            success, message = current_order.transfer_to_table(new_table_id, current_user.id)
            if success:
                flash(message, 'success')
            else:
                flash(message, 'error')
        else:
            flash('Please select a destination table', 'error')
    
    return redirect(url_for('tables.current_table_order', table_id=table_id))