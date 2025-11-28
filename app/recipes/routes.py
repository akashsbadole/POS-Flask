from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app.recipes import bp
from app.models.recipe import Recipe, RecipeIngredient, RecipeCategory, RecipeTag
from app.models.menu import MenuItem
from app.models.inventory import Ingredient
from app import db
from datetime import datetime

@bp.route('/')
@login_required
def index():
    """Recipe management dashboard"""
    if not current_user.can_access_manager_features():
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    category_id = request.args.get('category_id', type=int)
    
    # Build query
    query = Recipe.query
    
    if search:
        query = query.filter(Recipe.name.contains(search))
    
    if category_id:
        # Filter by menu item category
        query = query.join(MenuItem).filter(MenuItem.category_id == category_id)
    
    recipes = query.order_by(Recipe.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    categories = RecipeCategory.query.filter_by(is_active=True).order_by(RecipeCategory.display_order).all()
    
    return render_template('recipes/index.html', recipes=recipes, categories=categories, search=search, selected_category=category_id)

@bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    """Create new recipe"""
    if not current_user.can_access_manager_features():
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        recipe = Recipe(
            menu_item_id=request.form.get('menu_item_id', type=int),
            name=request.form.get('name'),
            description=request.form.get('description'),
            instructions=request.form.get('instructions'),
            prep_time=request.form.get('prep_time', type=int),
            cook_time=request.form.get('cook_time', type=int),
            serving_size=request.form.get('serving_size', type=int),
            difficulty_level=request.form.get('difficulty_level'),
            is_active='is_active' in request.form
        )
        
        db.session.add(recipe)
        db.session.flush()  # Get the recipe ID
        
        # Add ingredients
        ingredient_ids = request.form.getlist('ingredient_id[]')
        quantities = request.form.getlist('quantity[]')
        notes_list = request.form.getlist('notes[]')
        
        for i, ingredient_id in enumerate(ingredient_ids):
            if ingredient_id and i < len(quantities):
                recipe_ingredient = RecipeIngredient(
                    recipe_id=recipe.id,
                    ingredient_id=int(ingredient_id),
                    quantity=float(quantities[i]) if quantities[i] else 0,
                    notes=notes_list[i] if i < len(notes_list) else None
                )
                db.session.add(recipe_ingredient)
        
        # Add tags
        tag_ids = request.form.getlist('tag_ids[]')
        for tag_id in tag_ids:
            tag = RecipeTag.query.get(tag_id)
            if tag and tag not in recipe.tags:
                recipe.tags.append(tag)
        
        # Update recipe cost
        recipe.update_cost()
        
        db.session.commit()
        flash('Recipe created successfully', 'success')
        return redirect(url_for('recipes.index'))
    
    menu_items = MenuItem.query.filter_by(is_available=True).all()
    ingredients = Ingredient.query.filter_by(is_active=True).all()
    categories = RecipeCategory.query.filter_by(is_active=True).all()
    tags = RecipeTag.query.all()
    
    return render_template('recipes/form.html', 
                         recipe=None,
                         menu_items=menu_items,
                         ingredients=ingredients,
                         categories=categories,
                         tags=tags)

@bp.route('/<int:recipe_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(recipe_id):
    """Edit existing recipe"""
    if not current_user.can_access_manager_features():
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    recipe = Recipe.query.get_or_404(recipe_id)
    
    if request.method == 'POST':
        recipe.menu_item_id = request.form.get('menu_item_id', type=int)
        recipe.name = request.form.get('name')
        recipe.description = request.form.get('description')
        recipe.instructions = request.form.get('instructions')
        recipe.prep_time = request.form.get('prep_time', type=int)
        recipe.cook_time = request.form.get('cook_time', type=int)
        recipe.serving_size = request.form.get('serving_size', type=int)
        recipe.difficulty_level = request.form.get('difficulty_level')
        recipe.is_active = 'is_active' in request.form
        
        # Clear existing ingredients
        RecipeIngredient.query.filter_by(recipe_id=recipe.id).delete()
        
        # Add updated ingredients
        ingredient_ids = request.form.getlist('ingredient_id[]')
        quantities = request.form.getlist('quantity[]')
        notes_list = request.form.getlist('notes[]')
        
        for i, ingredient_id in enumerate(ingredient_ids):
            if ingredient_id and i < len(quantities):
                recipe_ingredient = RecipeIngredient(
                    recipe_id=recipe.id,
                    ingredient_id=int(ingredient_id),
                    quantity=float(quantities[i]) if quantities[i] else 0,
                    notes=notes_list[i] if i < len(notes_list) else None
                )
                db.session.add(recipe_ingredient)
        
        # Clear existing tags
        recipe.tags.clear()
        
        # Add updated tags
        tag_ids = request.form.getlist('tag_ids[]')
        for tag_id in tag_ids:
            tag = RecipeTag.query.get(tag_id)
            if tag:
                recipe.tags.append(tag)
        
        # Update recipe cost
        recipe.update_cost()
        
        db.session.commit()
        flash('Recipe updated successfully', 'success')
        return redirect(url_for('recipes.view', recipe_id=recipe.id))
    
    menu_items = MenuItem.query.filter_by(is_available=True).all()
    ingredients = Ingredient.query.filter_by(is_active=True).all()
    categories = RecipeCategory.query.filter_by(is_active=True).all()
    tags = RecipeTag.query.all()
    
    return render_template('recipes/form.html', 
                         recipe=recipe,
                         menu_items=menu_items,
                         ingredients=ingredients,
                         categories=categories,
                         tags=tags)

@bp.route('/<int:recipe_id>')
@login_required
def view(recipe_id):
    """View recipe details"""
    recipe = Recipe.query.get_or_404(recipe_id)
    
    return render_template('recipes/view.html', recipe=recipe)

@bp.route('/<int:recipe_id>/delete', methods=['POST'])
@login_required
def delete(recipe_id):
    """Delete recipe"""
    if not current_user.can_access_manager_features():
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    recipe = Recipe.query.get_or_404(recipe_id)
    
    db.session.delete(recipe)
    db.session.commit()
    
    flash('Recipe deleted successfully', 'success')
    return redirect(url_for('recipes.index'))

@bp.route('/categories')
@login_required
def categories():
    """Manage recipe categories"""
    if not current_user.can_access_manager_features():
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    categories = RecipeCategory.query.order_by(RecipeCategory.display_order).all()
    
    return render_template('recipes/categories.html', categories=categories)

@bp.route('/categories/create', methods=['GET', 'POST'])
@login_required
def create_category():
    """Create recipe category"""
    if not current_user.can_access_manager_features():
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        category = RecipeCategory(
            name=request.form.get('name'),
            description=request.form.get('description'),
            color=request.form.get('color', '#6B7280'),
            display_order=request.form.get('display_order', type=int, default=0),
            is_active='is_active' in request.form
        )
        
        db.session.add(category)
        db.session.commit()
        
        flash('Category created successfully', 'success')
        return redirect(url_for('recipes.categories'))
    
    return render_template('recipes/category_form.html', category=None)

@bp.route('/categories/<int:category_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_category(category_id):
    """Edit recipe category"""
    if not current_user.can_access_manager_features():
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    category = RecipeCategory.query.get_or_404(category_id)
    
    if request.method == 'POST':
        category.name = request.form.get('name')
        category.description = request.form.get('description')
        category.color = request.form.get('color', '#6B7280')
        category.display_order = request.form.get('display_order', type=int, default=0)
        category.is_active = 'is_active' in request.form
        
        db.session.commit()
        
        flash('Category updated successfully', 'success')
        return redirect(url_for('recipes.categories'))
    
    return render_template('recipes/category_form.html', category=category)

@bp.route('/categories/<int:category_id>/delete', methods=['POST'])
@login_required
def delete_category(category_id):
    """Delete recipe category"""
    if not current_user.can_access_manager_features():
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    category = RecipeCategory.query.get_or_404(category_id)
    
    db.session.delete(category)
    db.session.commit()
    
    flash('Category deleted successfully', 'success')
    return redirect(url_for('recipes.categories'))

@bp.route('/cost-calculator')
@login_required
def cost_calculator():
    """Recipe cost calculator"""
    if not current_user.can_access_manager_features():
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    return render_template('recipes/cost_calculator.html')

@bp.route('/api/calculate-cost', methods=['POST'])
@login_required
def api_calculate_cost():
    """API endpoint to calculate recipe cost"""
    if not current_user.can_access_manager_features():
        return jsonify({'error': 'Access denied'}), 403
    
    if not request.is_json:
        return jsonify({'error': 'Invalid JSON'}), 400
    
    data = request.get_json()
    ingredient_ids = data.get('ingredient_ids', [])
    quantities = data.get('quantities', [])
    
    total_cost = 0.0
    ingredients_data = []
    
    for i, ingredient_id in enumerate(ingredient_ids):
        if i < len(quantities):
            ingredient = Ingredient.query.get(ingredient_id)
            if ingredient:
                cost = float(quantities[i]) * float(ingredient.unit_cost)
                total_cost += cost
                
                ingredients_data.append({
                    'name': ingredient.name,
                    'quantity': quantities[i],
                    'unit': ingredient.unit,
                    'unit_cost': float(ingredient.unit_cost),
                    'total_cost': cost
                })
    
    return jsonify({
        'total_cost': total_cost,
        'ingredients': ingredients_data
    })

@bp.route('/api/search')
@login_required
def api_search():
    """API endpoint to search recipes"""
    if not current_user.can_access_manager_features():
        return jsonify({'error': 'Access denied'}), 403
    
    query = request.args.get('q', '')
    menu_item_id = request.args.get('menu_item_id', type=int)
    
    recipes_query = Recipe.query
    
    if query:
        recipes_query = recipes_query.filter(Recipe.name.contains(query))
    
    if menu_item_id:
        recipes_query = recipes_query.filter_by(menu_item_id=menu_item_id)
    
    recipes = recipes_query.limit(20).all()
    
    return jsonify({
        'recipes': [recipe.to_dict() for recipe in recipes]
    })

@bp.route('/<int:recipe_id>/scale', methods=['POST'])
@login_required
def scale_recipe(recipe_id):
    """Scale recipe to different serving size"""
    if not current_user.can_access_manager_features():
        return jsonify({'error': 'Access denied'}), 403
    
    recipe = Recipe.query.get_or_404(recipe_id)
    
    if not request.is_json:
        return jsonify({'error': 'Invalid JSON'}), 400
    
    data = request.get_json()
    target_servings = data.get('target_servings', type=int)
    
    if not target_servings or target_servings <= 0:
        return jsonify({'error': 'Invalid target servings'}), 400
    
    # Scale the recipe
    scaling_factor = recipe.scale_to(target_servings)
    
    if scaling_factor is None:
        return jsonify({'error': 'Recipe cannot be scaled'}), 400
    
    # Get scaled ingredients
    scaled_ingredients = []
    for recipe_ingredient in recipe.ingredients:
        scaled_quantity = float(recipe_ingredient.quantity) * scaling_factor
        scaled_ingredients.append({
            'id': recipe_ingredient.id,
            'name': recipe_ingredient.ingredient.name,
            'original_quantity': float(recipe_ingredient.quantity),
            'scaled_quantity': round(scaled_quantity, 2),
            'unit': recipe_ingredient.ingredient.unit,
            'unit_cost': float(recipe_ingredient.ingredient.unit_cost),
            'total_cost': round(scaled_quantity * float(recipe_ingredient.ingredient.unit_cost), 2)
        })
    
    return jsonify({
        'success': True,
        'original_servings': recipe.serving_size,
        'target_servings': target_servings,
        'scaling_factor': scaling_factor,
        'scaled_nutrition': recipe.get_scaled_nutrition(target_servings),
        'ingredients': scaled_ingredients,
        'scaled_cost_per_serving': float(recipe.cost_per_serving) * scaling_factor if recipe.cost_per_serving else 0.0,
        'scaled_total_cost': recipe.calculate_total_cost() * scaling_factor
    })

@bp.route('/<int:recipe_id>/nutrition')
@login_required
def recipe_nutrition(recipe_id):
    """Get nutritional information for recipe"""
    if not current_user.can_access_manager_features():
        return jsonify({'error': 'Access denied'}), 403
    
    recipe = Recipe.query.get_or_404(recipe_id)
    
    return jsonify({
        'recipe': recipe.to_dict(),
        'nutrition': recipe.get_nutrition_summary(),
        'daily_value_percentages': {
            'protein': recipe.get_daily_value_percentage(recipe.protein, 50),  # 50g daily value
            'carbohydrates': recipe.get_daily_value_percentage(recipe.carbohydrates, 300),  # 300g daily value
            'fat': recipe.get_daily_value_percentage(recipe.fat, 65),  # 65g daily value
            'sodium': recipe.get_daily_value_percentage(recipe.sodium, 2300),  # 2300mg daily value
            'fiber': recipe.get_daily_value_percentage(recipe.fiber, 25),  # 25g daily value
        }
    })

@bp.route('/api/scale-batch', methods=['POST'])
@login_required
def api_scale_batch():
    """Scale multiple recipes at once"""
    if not current_user.can_access_manager_features():
        return jsonify({'error': 'Access denied'}), 403
    
    if not request.is_json:
        return jsonify({'error': 'Invalid JSON'}), 400
    
    data = request.get_json()
    recipe_ids = data.get('recipe_ids', [])
    target_servings = data.get('target_servings', 1)
    
    if not recipe_ids or not isinstance(recipe_ids, list):
        return jsonify({'error': 'Invalid recipe IDs'}), 400
    
    results = []
    for recipe_id in recipe_ids:
        recipe = Recipe.query.get(recipe_id)
        if recipe:
            scaling_factor = recipe.scale_to(target_servings)
            if scaling_factor:
                results.append({
                    'recipe_id': recipe.id,
                    'recipe_name': recipe.name,
                    'original_servings': recipe.serving_size,
                    'target_servings': target_servings,
                    'scaling_factor': scaling_factor,
                    'scaled_nutrition': recipe.get_scaled_nutrition(target_servings),
                    'success': True
                })
            else:
                results.append({
                    'recipe_id': recipe.id,
                    'recipe_name': recipe.name,
                    'error': 'Recipe cannot be scaled',
                    'success': False
                })
        else:
            results.append({
                'recipe_id': recipe_id,
                'error': 'Recipe not found',
                'success': False
            })
    
    return jsonify({
        'success': True,
        'results': results,
        'target_servings': target_servings
    })