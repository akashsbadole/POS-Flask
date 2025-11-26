from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app.tables import bp
from app.models.table import Table, TableStatus, TableSession
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