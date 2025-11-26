from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app.inventory import bp
from app.models.inventory import Ingredient, StockAdjustment, MenuItemIngredient
from app.models.menu import MenuItem
from app import db
from datetime import datetime

@bp.route('/')
@login_required
def dashboard():
    """Inventory dashboard with low stock alerts"""
    # Get low stock ingredients
    low_stock_ingredients = Ingredient.query.filter(
        Ingredient.current_stock <= Ingredient.minimum_stock
    ).all()
    
    # Get recent stock adjustments
    recent_adjustments = StockAdjustment.query.order_by(
        StockAdjustment.created_at.desc()
    ).limit(10).all()
    
    # Get inventory statistics
    total_ingredients = Ingredient.query.count()
    out_of_stock = Ingredient.query.filter(Ingredient.current_stock == 0).count()
    low_stock_count = len(low_stock_ingredients)
    
    return render_template('inventory/dashboard.html', 
                         low_stock_ingredients=low_stock_ingredients,
                         recent_adjustments=recent_adjustments,
                         total_ingredients=total_ingredients,
                         out_of_stock=out_of_stock,
                         low_stock_count=low_stock_count)

@bp.route('/ingredients')
@login_required
def ingredients():
    """List all ingredients"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    stock_filter = request.args.get('stock_filter', '')
    
    query = Ingredient.query
    
    if search:
        query = query.filter(Ingredient.name.contains(search))
    
    if stock_filter == 'low':
        query = query.filter(Ingredient.current_stock <= Ingredient.minimum_stock)
    elif stock_filter == 'out':
        query = query.filter(Ingredient.current_stock == 0)
    
    ingredients = query.order_by(Ingredient.name).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('inventory/ingredients.html', 
                         ingredients=ingredients,
                         search=search,
                         stock_filter=stock_filter)

@bp.route('/ingredients/add', methods=['GET', 'POST'])
@login_required
def add_ingredient():
    """Add new ingredient"""
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        unit = request.form.get('unit')
        current_stock = request.form.get('current_stock', type=float)
        minimum_stock = request.form.get('minimum_stock', type=float)
        unit_cost = request.form.get('unit_cost', type=float)
        supplier = request.form.get('supplier')
        
        if not name or not unit:
            flash('Name and unit are required', 'error')
            return render_template('inventory/ingredient_form.html')
        
        ingredient = Ingredient(
            name=name,
            description=description,
            unit=unit,
            current_stock=current_stock,
            minimum_stock=minimum_stock,
            unit_cost=unit_cost,
            supplier=supplier
        )
        
        db.session.add(ingredient)
        db.session.commit()
        
        # Create initial stock adjustment if stock is provided
        if current_stock and current_stock > 0:
            adjustment = StockAdjustment(
                ingredient_id=ingredient.id,
                quantity=current_stock,
                previous_quantity=0,
                new_quantity=current_stock,
                reason="Initial stock",
                user_id=current_user.id
            )
            db.session.add(adjustment)
            db.session.commit()
        
        flash(f'Ingredient "{name}" added successfully', 'success')
        return redirect(url_for('inventory.ingredients'))
    
    return render_template('inventory/ingredient_form.html')

@bp.route('/ingredients/<int:ingredient_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_ingredient(ingredient_id):
    """Edit ingredient"""
    ingredient = Ingredient.query.get_or_404(ingredient_id)
    
    if request.method == 'POST':
        old_stock = float(ingredient.current_stock)
        
        ingredient.name = request.form.get('name')
        ingredient.description = request.form.get('description')
        ingredient.unit = request.form.get('unit')
        ingredient.minimum_stock = request.form.get('minimum_stock', type=float)
        ingredient.unit_cost = request.form.get('unit_cost', type=float)
        ingredient.supplier = request.form.get('supplier')
        
        db.session.commit()
        
        flash(f'Ingredient "{ingredient.name}" updated successfully', 'success')
        return redirect(url_for('inventory.ingredients'))
    
    return render_template('inventory/ingredient_form.html', ingredient=ingredient)

@bp.route('/ingredients/<int:ingredient_id>/adjust', methods=['GET', 'POST'])
@login_required
def adjust_stock(ingredient_id):
    """Adjust ingredient stock"""
    ingredient = Ingredient.query.get_or_404(ingredient_id)
    
    if request.method == 'POST':
        quantity = request.form.get('quantity', type=float)
        reason = request.form.get('reason', 'Stock adjustment')
        
        if not quantity:
            flash('Quantity is required', 'error')
            return render_template('inventory/adjust_stock.html', ingredient=ingredient)
        
        adjustment = ingredient.adjust_stock(quantity, reason, current_user.id)
        db.session.commit()
        
        flash(f'Stock adjusted for "{ingredient.name}": {quantity:+.3f} {ingredient.unit}', 'success')
        return redirect(url_for('inventory.ingredients'))
    
    return render_template('inventory/adjust_stock.html', ingredient=ingredient)

@bp.route('/ingredients/<int:ingredient_id>/delete', methods=['POST'])
@login_required
def delete_ingredient(ingredient_id):
    """Delete ingredient"""
    ingredient = Ingredient.query.get_or_404(ingredient_id)
    
    # Check if ingredient is used in menu items
    if ingredient.menu_item_ingredients:
        flash(f'Cannot delete "{ingredient.name}" - it is used in menu items', 'error')
        return redirect(url_for('inventory.ingredients'))
    
    name = ingredient.name
    db.session.delete(ingredient)
    db.session.commit()
    
    flash(f'Ingredient "{name}" deleted successfully', 'success')
    return redirect(url_for('inventory.ingredients'))

@bp.route('/menu-ingredients')
@login_required
def menu_ingredients():
    """Show ingredients used in menu items"""
    menu_items = MenuItem.query.all()
    
    return render_template('inventory/menu_ingredients.html', menu_items=menu_items)

@bp.route('/menu-items/<int:menu_item_id>/ingredients', methods=['GET', 'POST'])
@login_required
def manage_menu_item_ingredients(menu_item_id):
    """Manage ingredients for a menu item"""
    menu_item = MenuItem.query.get_or_404(menu_item_id)
    
    if request.method == 'POST':
        # Clear existing ingredients
        MenuItemIngredient.query.filter_by(menu_item_id=menu_item_id).delete()
        
        # Add new ingredients
        ingredient_ids = request.form.getlist('ingredient_id')
        quantities = request.form.getlist('quantity_required')
        
        for i, ingredient_id in enumerate(ingredient_ids):
            if ingredient_id and i < len(quantities):
                quantity = quantities[i]
                if quantity and float(quantity) > 0:
                    menu_item_ingredient = MenuItemIngredient(
                        menu_item_id=menu_item_id,
                        ingredient_id=int(ingredient_id),
                        quantity_required=float(quantity)
                    )
                    db.session.add(menu_item_ingredient)
        
        db.session.commit()
        flash(f'Ingredients updated for "{menu_item.name}"', 'success')
        return redirect(url_for('inventory.menu_ingredients'))
    
    ingredients = Ingredient.query.order_by(Ingredient.name).all()
    return render_template('inventory/menu_item_ingredients.html', 
                         menu_item=menu_item, 
                         ingredients=ingredients)

@bp.route('/adjustments')
@login_required
def stock_adjustments():
    """View stock adjustment history"""
    page = request.args.get('page', 1, type=int)
    ingredient_id = request.args.get('ingredient_id', type=int)
    
    query = StockAdjustment.query
    
    if ingredient_id:
        query = query.filter_by(ingredient_id=ingredient_id)
    
    adjustments = query.order_by(StockAdjustment.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    ingredients = Ingredient.query.order_by(Ingredient.name).all()
    
    return render_template('inventory/adjustments.html', 
                         adjustments=adjustments,
                         ingredients=ingredients,
                         selected_ingredient=ingredient_id)

@bp.route('/reports')
@login_required
def inventory_reports():
    """Inventory reports"""
    # Get ingredients by stock status
    all_ingredients = Ingredient.query.all()
    low_stock = [i for i in all_ingredients if i.is_low_stock()]
    out_of_stock = [i for i in all_ingredients if float(i.current_stock) == 0]
    
    # Calculate total inventory value
    total_value = sum(float(i.current_stock) * float(i.unit_cost) for i in all_ingredients)
    
    return render_template('inventory/reports.html',
                         all_ingredients=all_ingredients,
                         low_stock=low_stock,
                         out_of_stock=out_of_stock,
                         total_value=total_value)

# API endpoints
@bp.route('/api/ingredients')
@login_required
def api_ingredients():
    """API endpoint to get ingredients"""
    ingredients = Ingredient.query.order_by(Ingredient.name).all()
    return jsonify([ingredient.to_dict() for ingredient in ingredients])

@bp.route('/api/ingredients/<int:ingredient_id>')
@login_required
def api_ingredient(ingredient_id):
    """API endpoint to get specific ingredient"""
    ingredient = Ingredient.query.get_or_404(ingredient_id)
    return jsonify(ingredient.to_dict())

@bp.route('/api/menu-items/<int:menu_item_id>/check-availability')
@login_required
def check_menu_item_availability(menu_item_id):
    """Check if menu item can be made with current stock"""
    menu_item = MenuItem.query.get_or_404(menu_item_id)
    
    if not menu_item.menu_item_ingredients:
        return jsonify({'available': True, 'can_make': 999, 'limiting_ingredients': []})
    
    can_make = 999  # Start with high number
    limiting_ingredients = []
    
    for item_ingredient in menu_item.menu_item_ingredients:
        if not item_ingredient.check_availability():
            available_quantity = int(float(item_ingredient.ingredient.current_stock) / float(item_ingredient.quantity_required))
            if available_quantity < can_make:
                can_make = available_quantity
                limiting_ingredients.append({
                    'name': item_ingredient.ingredient.name,
                    'available': float(item_ingredient.ingredient.current_stock),
                    'required': float(item_ingredient.quantity_required),
                    'can_make': available_quantity
                })
    
    return jsonify({
        'available': can_make > 0,
        'can_make': can_make if can_make < 999 else 999,
        'limiting_ingredients': limiting_ingredients
    })