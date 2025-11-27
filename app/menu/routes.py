from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app.menu import bp
from app.models.menu import Category, MenuItem, ItemVariant, AddOn
from app.models.user import User
from app import db
from datetime import datetime

@bp.route('/categories')
@login_required
def list_categories():
    """List all menu categories"""
    if not current_user.can_access_manager_features():
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    categories = Category.query.order_by(Category.display_order).all()
    
    if request.headers.get('HX-Request'):
        return render_template('menu/partials/category_list.html', categories=categories)
    
    return render_template('menu/categories.html', categories=categories)

@bp.route('/categories/new', methods=['GET', 'POST'])
@login_required
def create_category():
    """Create a new menu category"""
    if not current_user.can_access_manager_features():
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        display_order = request.form.get('display_order', 0, type=int)
        
        if name:
            category = Category(
                name=name,
                description=description,
                display_order=display_order
            )
            db.session.add(category)
            db.session.commit()
            
            flash(f'Category "{name}" created successfully', 'success')
            
            if request.headers.get('HX-Request'):
                return render_template('menu/partials/category_item.html', category=category)
            
            return redirect(url_for('menu.list_categories'))
    
    return render_template('menu/category_form.html')

@bp.route('/categories/<int:category_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_category(category_id):
    """Edit an existing menu category"""
    if not current_user.can_access_manager_features():
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    category = Category.query.get_or_404(category_id)
    
    if request.method == 'POST':
        category.name = request.form.get('name')
        category.description = request.form.get('description')
        category.display_order = request.form.get('display_order', 0, type=int)
        
        db.session.commit()
        
        flash(f'Category "{category.name}" updated successfully', 'success')
        
        if request.headers.get('HX-Request'):
            return render_template('menu/partials/category_item.html', category=category)
        
        return redirect(url_for('menu.list_categories'))
    
    return render_template('menu/category_form.html', category=category, edit_mode=True)

@bp.route('/items')
@login_required
def list_items():
    """List all menu items"""
    if not current_user.can_access_manager_features():
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    category_id = request.args.get('category_id', type=int)
    
    query = MenuItem.query
    if category_id:
        query = query.filter_by(category_id=category_id)
    
    items = query.order_by(MenuItem.display_order).all()
    categories = Category.query.order_by(Category.display_order).all()
    
    if request.headers.get('HX-Request'):
        return render_template('menu/partials/item_list.html', items=items, categories=categories, selected_category=category_id)
    
    return render_template('menu/items.html', items=items, categories=categories, selected_category=category_id)

@bp.route('/items/new', methods=['GET', 'POST'])
@login_required
def create_item():
    """Create a new menu item"""
    if not current_user.can_access_manager_features():
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        price = request.form.get('price', type=float)
        category_id = request.form.get('category_id', type=int)
        preparation_time = request.form.get('preparation_time', type=int)
        
        if name and price and category_id:
            item = MenuItem(
                name=name,
                description=description,
                price=price,
                category_id=category_id,
                preparation_time=preparation_time
            )
            db.session.add(item)
            db.session.commit()
            
            flash(f'Menu item "{name}" created successfully', 'success')
            
            if request.headers.get('HX-Request'):
                return render_template('menu/partials/item_card.html', item=item)
            
            return redirect(url_for('menu.list_items'))
    
    categories = Category.query.order_by(Category.display_order).all()
    return render_template('menu/item_form.html', categories=categories)

@bp.route('/items/<int:item_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_item(item_id):
    """Edit an existing menu item"""
    if not current_user.can_access_manager_features():
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    item = MenuItem.query.get_or_404(item_id)
    
    if request.method == 'POST':
        item.name = request.form.get('name')
        item.description = request.form.get('description')
        item.price = request.form.get('price', type=float)
        item.category_id = request.form.get('category_id', type=int)
        item.preparation_time = request.form.get('preparation_time', type=int)
        item.is_available = 'is_available' in request.form
        
        db.session.commit()
        
        flash(f'Menu item "{item.name}" updated successfully', 'success')
        
        if request.headers.get('HX-Request'):
            return render_template('menu/partials/item_card.html', item=item)
        
        return redirect(url_for('menu.list_items'))
    
    categories = Category.query.order_by(Category.display_order).all()
    return render_template('menu/item_form.html', item=item, categories=categories, edit_mode=True)

@bp.route('/items/<int:item_id>/toggle-availability', methods=['POST'])
@login_required
def toggle_availability(item_id):
    """Toggle item availability"""
    if not current_user.can_access_manager_features():
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    item = MenuItem.query.get_or_404(item_id)
    item.is_available = not item.is_available
    db.session.commit()
    
    status = "available" if item.is_available else "unavailable"
    flash(f'Item "{item.name}" is now {status}', 'success')
    
    if request.headers.get('HX-Request'):
        return render_template('menu/partials/item_card.html', item=item)
    
    return redirect(url_for('menu.list_items'))

# API endpoints for frontend
@bp.route('/api/categories')
@login_required
def api_categories():
    """API endpoint to get categories"""
    categories = Category.query.filter_by(is_active=True).order_by(Category.display_order).all()
    return jsonify([cat.to_dict() for cat in categories])

@bp.route('/api/items')
@login_required
def api_items():
    """API endpoint to get menu items"""
    items = MenuItem.query.filter_by(is_available=True).order_by(MenuItem.display_order).all()
    return jsonify([item.to_dict() for item in items])

@bp.route('/api/item/<int:item_id>')
@login_required
def api_item(item_id):
    """API endpoint to get specific menu item"""
    item = MenuItem.query.get_or_404(item_id)
    return jsonify(item.to_dict())