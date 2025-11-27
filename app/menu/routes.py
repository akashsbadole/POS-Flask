from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app.menu import bp
from app.models.menu import Category, MenuItem, ItemVariant, AddOn, AddOnCategory
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
    return jsonify([item.to_dict(include_add_ons=True) for item in items])

@bp.route('/api/item/<int:item_id>')
@login_required
def api_item(item_id):
    """API endpoint to get specific menu item"""
    item = MenuItem.query.get_or_404(item_id)
    return jsonify(item.to_dict())

# Variant management routes
@bp.route('/items/<int:item_id>/variants')
@login_required
def list_variants(item_id):
    """List all variants for a menu item"""
    if not current_user.can_access_manager_features():
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    item = MenuItem.query.get_or_404(item_id)
    variants = ItemVariant.query.filter_by(item_id=item_id).order_by(ItemVariant.display_order).all()
    
    if request.headers.get('HX-Request'):
        return render_template('menu/partials/variant_list.html', variants=variants, item=item)
    
    return render_template('menu/variants.html', variants=variants, item=item)

@bp.route('/items/<int:item_id>/variants/new', methods=['GET', 'POST'])
@login_required
def create_variant(item_id):
    """Create a new variant for a menu item"""
    if not current_user.can_access_manager_features():
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    item = MenuItem.query.get_or_404(item_id)
    
    if request.method == 'POST':
        name = request.form.get('name')
        price_modifier = request.form.get('price_modifier', type=float, default=0.00)
        display_order = request.form.get('display_order', type=int, default=0)
        
        if name:
            variant = ItemVariant(
                item_id=item_id,
                name=name,
                price_modifier=price_modifier,
                display_order=display_order
            )
            db.session.add(variant)
            db.session.commit()
            
            flash(f'Variant "{name}" created successfully', 'success')
            
            if request.headers.get('HX-Request'):
                return render_template('menu/partials/variant_card.html', variant=variant, item=item)
            
            return redirect(url_for('menu.list_variants', item_id=item_id))
    
    return render_template('menu/variant_form.html', item=item)

@bp.route('/variants/<int:variant_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_variant(variant_id):
    """Edit an existing variant"""
    if not current_user.can_access_manager_features():
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    variant = ItemVariant.query.get_or_404(variant_id)
    
    if request.method == 'POST':
        variant.name = request.form.get('name')
        variant.price_modifier = request.form.get('price_modifier', type=float, default=0.00)
        variant.display_order = request.form.get('display_order', type=int, default=0)
        variant.is_available = 'is_available' in request.form
        
        db.session.commit()
        
        flash(f'Variant "{variant.name}" updated successfully', 'success')
        
        if request.headers.get('HX-Request'):
            return render_template('menu/partials/variant_card.html', variant=variant, item=variant.menu_item)
        
        return redirect(url_for('menu.list_variants', item_id=variant.item_id))
    
    return render_template('menu/variant_form.html', variant=variant, item=variant.menu_item, edit_mode=True)

@bp.route('/variants/<int:variant_id>/toggle-availability', methods=['POST'])
@login_required
def toggle_variant_availability(variant_id):
    """Toggle variant availability"""
    if not current_user.can_access_manager_features():
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    variant = ItemVariant.query.get_or_404(variant_id)
    variant.is_available = not variant.is_available
    db.session.commit()
    
    status = "available" if variant.is_available else "unavailable"
    flash(f'Variant "{variant.name}" is now {status}', 'success')
    
    if request.headers.get('HX-Request'):
        return render_template('menu/partials/variant_card.html', variant=variant, item=variant.menu_item)
    
    return redirect(url_for('menu.list_variants', item_id=variant.item_id))

@bp.route('/variants/<int:variant_id>/delete', methods=['POST'])
@login_required
def delete_variant(variant_id):
    """Delete a variant"""
    if not current_user.can_access_manager_features():
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    variant = ItemVariant.query.get_or_404(variant_id)
    item_id = variant.item_id
    variant_name = variant.name
    
    db.session.delete(variant)
    db.session.commit()
    
    flash(f'Variant "{variant_name}" deleted successfully', 'success')
    
    return redirect(url_for('menu.list_variants', item_id=item_id))

# API endpoints for variants
@bp.route('/api/items/<int:item_id>/variants')
@login_required
def api_item_variants(item_id):
    """API endpoint to get variants for a specific item"""
    variants = ItemVariant.query.filter_by(item_id=item_id, is_available=True).order_by(ItemVariant.display_order).all()
    return jsonify([variant.to_dict() for variant in variants])

# Add-on management routes
@bp.route('/addons')
@login_required
def list_addons():
    """List all add-ons"""
    if not current_user.can_access_manager_features():
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    addons = AddOn.query.order_by(AddOn.display_order).all()
    
    if request.headers.get('HX-Request'):
        return render_template('menu/partials/addon_list.html', addons=addons)
    
    return render_template('menu/addons.html', addons=addons)

@bp.route('/addons/new', methods=['GET', 'POST'])
@login_required
def create_addon():
    """Create a new add-on"""
    if not current_user.can_access_manager_features():
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        price = request.form.get('price', type=float, default=0.00)
        display_order = request.form.get('display_order', type=int, default=0)
        category_id = request.form.get('category_id', type=int)
        
        if name:
            addon = AddOn(
                name=name,
                description=description,
                price=price,
                display_order=display_order,
                category_id=category_id
            )
            db.session.add(addon)
            db.session.commit()
            
            flash(f'Add-on "{name}" created successfully', 'success')
            
            if request.headers.get('HX-Request'):
                return render_template('menu/partials/addon_card.html', addon=addon)
            
            return redirect(url_for('menu.list_addons'))
    
    addon_categories = AddOnCategory.query.filter_by(is_active=True).order_by(AddOnCategory.display_order).all()
    return render_template('menu/addon_form.html', addon_categories=addon_categories)

@bp.route('/addons/<int:addon_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_addon(addon_id):
    """Edit an existing add-on"""
    if not current_user.can_access_manager_features():
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    addon = AddOn.query.get_or_404(addon_id)
    
    if request.method == 'POST':
        addon.name = request.form.get('name')
        addon.description = request.form.get('description')
        addon.price = request.form.get('price', type=float, default=0.00)
        addon.display_order = request.form.get('display_order', type=int, default=0)
        addon.category_id = request.form.get('category_id', type=int)
        addon.is_active = 'is_active' in request.form
        
        db.session.commit()
        
        flash(f'Add-on "{addon.name}" updated successfully', 'success')
        
        if request.headers.get('HX-Request'):
            return render_template('menu/partials/addon_card.html', addon=addon)
        
        return redirect(url_for('menu.list_addons'))
    
    addon_categories = AddOnCategory.query.filter_by(is_active=True).order_by(AddOnCategory.display_order).all()
    return render_template('menu/addon_form.html', addon=addon, edit_mode=True, addon_categories=addon_categories)

@bp.route('/addons/<int:addon_id>/toggle-availability', methods=['POST'])
@login_required
def toggle_addon_availability(addon_id):
    """Toggle add-on availability"""
    if not current_user.can_access_manager_features():
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    addon = AddOn.query.get_or_404(addon_id)
    addon.is_active = not addon.is_active
    db.session.commit()
    
    status = "available" if addon.is_active else "unavailable"
    flash(f'Add-on "{addon.name}" is now {status}', 'success')
    
    if request.headers.get('HX-Request'):
        return render_template('menu/partials/addon_card.html', addon=addon)
    
    return redirect(url_for('menu.list_addons'))

@bp.route('/addons/<int:addon_id>/delete', methods=['POST'])
@login_required
def delete_addon(addon_id):
    """Delete an add-on"""
    if not current_user.can_access_manager_features():
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    addon = AddOn.query.get_or_404(addon_id)
    addon_name = addon.name
    
    db.session.delete(addon)
    db.session.commit()
    
    flash(f'Add-on "{addon_name}" deleted successfully', 'success')
    
    return redirect(url_for('menu.list_addons'))

@bp.route('/items/<int:item_id>/addons')
@login_required
def manage_item_addons(item_id):
    """Manage add-ons for a specific menu item"""
    if not current_user.can_access_manager_features():
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    item = MenuItem.query.get_or_404(item_id)
    all_addons = AddOn.query.order_by(AddOn.display_order).all()
    item_addons = item.add_ons.all()
    
    if request.headers.get('HX-Request'):
        return render_template('menu/partials/item_addons.html',
                              item=item, all_addons=all_addons, item_addons=item_addons)
    
    return render_template('menu/item_addons.html',
                          item=item, all_addons=all_addons, item_addons=item_addons)

@bp.route('/items/<int:item_id>/addons/update', methods=['POST'])
@login_required
def update_item_addons(item_id):
    """Update add-ons for a menu item"""
    if not current_user.can_access_manager_features():
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    item = MenuItem.query.get_or_404(item_id)
    addon_ids = request.form.getlist('addon_ids')
    
    # Clear existing add-ons
    item.add_ons.clear()
    
    # Add selected add-ons
    for addon_id in addon_ids:
        addon = AddOn.query.get(addon_id)
        if addon:
            item.add_ons.append(addon)
    
    db.session.commit()
    
    flash(f'Add-ons for "{item.name}" updated successfully', 'success')
    
    if request.headers.get('HX-Request'):
        all_addons = AddOn.query.order_by(AddOn.display_order).all()
        item_addons = item.add_ons.all()
        return render_template('menu/partials/item_addons.html',
                              item=item, all_addons=all_addons, item_addons=item_addons)
    
    return redirect(url_for('menu.manage_item_addons', item_id=item_id))

# Add-on category management routes
@bp.route('/addon-categories')
@login_required
def list_addon_categories():
    """List all add-on categories"""
    if not current_user.can_access_manager_features():
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    categories = AddOnCategory.query.order_by(AddOnCategory.display_order).all()
    
    if request.headers.get('HX-Request'):
        return render_template('menu/partials/addon_category_list.html', categories=categories)
    
    return render_template('menu/addon_categories.html', categories=categories)

@bp.route('/addon-categories/new', methods=['GET', 'POST'])
@login_required
def create_addon_category():
    """Create a new add-on category"""
    if not current_user.can_access_manager_features():
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        display_order = request.form.get('display_order', type=int, default=0)
        
        if name:
            category = AddOnCategory(
                name=name,
                description=description,
                display_order=display_order
            )
            db.session.add(category)
            db.session.commit()
            
            flash(f'Add-on category "{name}" created successfully', 'success')
            
            if request.headers.get('HX-Request'):
                return render_template('menu/partials/addon_category_item.html', category=category)
            
            return redirect(url_for('menu.list_addon_categories'))
    
    return render_template('menu/addon_category_form.html')

@bp.route('/addon-categories/<int:category_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_addon_category(category_id):
    """Edit an existing add-on category"""
    if not current_user.can_access_manager_features():
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    category = AddOnCategory.query.get_or_404(category_id)
    
    if request.method == 'POST':
        category.name = request.form.get('name')
        category.description = request.form.get('description')
        category.display_order = request.form.get('display_order', type=int, default=0)
        category.is_active = 'is_active' in request.form
        
        db.session.commit()
        
        flash(f'Add-on category "{category.name}" updated successfully', 'success')
        
        if request.headers.get('HX-Request'):
            return render_template('menu/partials/addon_category_item.html', category=category)
        
        return redirect(url_for('menu.list_addon_categories'))
    
    return render_template('menu/addon_category_form.html', category=category, edit_mode=True)

@bp.route('/addon-categories/<int:category_id>/delete', methods=['POST'])
@login_required
def delete_addon_category(category_id):
    """Delete an add-on category"""
    if not current_user.can_access_manager_features():
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    category = AddOnCategory.query.get_or_404(category_id)
    category_name = category.name
    
    # Check if category has add-ons
    if category.add_ons.count() > 0:
        flash(f'Cannot delete category "{category_name}" because it has add-ons. Move or delete the add-ons first.', 'error')
        return redirect(url_for('menu.list_addon_categories'))
    
    db.session.delete(category)
    db.session.commit()
    
    flash(f'Add-on category "{category_name}" deleted successfully', 'success')
    
    return redirect(url_for('menu.list_addon_categories'))

# API endpoints for add-ons
@bp.route('/api/addons')
@login_required
def api_addons():
    """API endpoint to get all add-ons"""
    addons = AddOn.query.filter_by(is_active=True).order_by(AddOn.display_order).all()
    return jsonify([addon.to_dict() for addon in addons])

@bp.route('/api/addon-categories')
@login_required
def api_addon_categories():
    """API endpoint to get all add-on categories"""
    categories = AddOnCategory.query.filter_by(is_active=True).order_by(AddOnCategory.display_order).all()
    return jsonify([category.to_dict() for category in categories])

@bp.route('/api/items/<int:item_id>/addons')
@login_required
def api_item_addons(item_id):
    """API endpoint to get add-ons for a specific item"""
    item = MenuItem.query.get_or_404(item_id)
    return jsonify([addon.to_dict() for addon in item.get_available_add_ons()])

# Reordering API endpoints
@bp.route('/api/menu/reorder-items', methods=['POST'])
@login_required
def api_reorder_items():
    """API endpoint to reorder menu items within a category"""
    if not current_user.can_access_manager_features():
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        data = request.get_json()
        items_data = data.get('items', [])
        category_id = data.get('category_id')
        
        if not items_data:
            return jsonify({'error': 'No items data provided'}), 400
        
        # Update display orders for each item
        for item_data in items_data:
            item_id = item_data.get('id')
            display_order = item_data.get('display_order', 0)
            
            if item_id:
                item = MenuItem.query.get(item_id)
                if item:
                    item.display_order = display_order
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'{len(items_data)} items reordered successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@bp.route('/api/menu/reorder-categories', methods=['POST'])
@login_required
def api_reorder_categories():
    """API endpoint to reorder menu categories"""
    if not current_user.can_access_manager_features():
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        data = request.get_json()
        categories_data = data.get('categories', [])
        
        if not categories_data:
            return jsonify({'error': 'No categories data provided'}), 400
        
        # Update display orders for each category
        for category_data in categories_data:
            category_id = category_data.get('id')
            display_order = category_data.get('display_order', 0)
            
            if category_id:
                category = Category.query.get(category_id)
                if category:
                    category.display_order = display_order
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'{len(categories_data)} categories reordered successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@bp.route('/api/menu/move-item', methods=['POST'])
@login_required
def api_move_item():
    """API endpoint to move an item to a different category"""
    if not current_user.can_access_manager_features():
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        data = request.get_json()
        item_id = data.get('item_id')
        new_category_id = data.get('new_category_id')
        new_display_order = data.get('new_display_order', 0)
        
        if not item_id or not new_category_id:
            return jsonify({'error': 'Item ID and new category ID are required'}), 400
        
        item = MenuItem.query.get_or_404(item_id)
        old_category_id = item.category_id
        
        # Update item category and display order
        item.category_id = new_category_id
        item.display_order = new_display_order
        
        # Reorder items in old category
        old_category_items = MenuItem.query.filter_by(category_id=old_category_id).order_by(MenuItem.display_order).all()
        for index, category_item in enumerate(old_category_items):
            if category_item.id != item_id:
                category_item.display_order = index
        
        # Reorder items in new category
        new_category_items = MenuItem.query.filter_by(category_id=new_category_id).order_by(MenuItem.display_order).all()
        for index, category_item in enumerate(new_category_items):
            if category_item.id == item_id:
                category_item.display_order = new_display_order
            elif category_item.display_order >= new_display_order:
                category_item.display_order = index + 1
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Item "{item.name}" moved to new category successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@bp.route('/api/menu/bulk-reorder', methods=['POST'])
@login_required
def api_bulk_reorder():
    """API endpoint for bulk reordering operations"""
    if not current_user.can_access_manager_features():
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        data = request.get_json()
        operation = data.get('operation')
        
        if operation == 'reset_alphabetical':
            # Reset items to alphabetical order within categories
            category_id = data.get('category_id')
            query = MenuItem.query
            
            if category_id:
                query = query.filter_by(category_id=category_id)
            
            items = query.order_by(MenuItem.name).all()
            for index, item in enumerate(items):
                item.display_order = index
                
            message = f'Items reset to alphabetical order'
            
        elif operation == 'sort_by_price':
            # Sort items by price within categories
            category_id = data.get('category_id')
            ascending = data.get('ascending', True)
            query = MenuItem.query
            
            if category_id:
                query = query.filter_by(category_id=category_id)
            
            if ascending:
                items = query.order_by(MenuItem.price).all()
            else:
                items = query.order_by(MenuItem.price.desc()).all()
                
            for index, item in enumerate(items):
                item.display_order = index
                
            message = f'Items sorted by price {"(ascending)" if ascending else "(descending)"}'
            
        elif operation == 'sort_categories_alphabetical':
            # Sort categories alphabetically
            categories = Category.query.order_by(Category.name).all()
            for index, category in enumerate(categories):
                category.display_order = index
                
            message = 'Categories sorted alphabetically'
            
        else:
            return jsonify({'error': 'Invalid operation'}), 400
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': message
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500