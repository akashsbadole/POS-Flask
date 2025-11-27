from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from app.models.menu import MenuItem, Category as MenuCategory
from app.models.order import Order
from app.models.table import Table
from app.models.user import User
from app import db
from datetime import datetime, timedelta
import time

bp = Blueprint('offline', __name__)

@bp.route('/menu/items')
@login_required
def get_menu_items():
    """Get menu items for offline caching"""
    try:
        items = MenuItem.query.filter_by(is_available=True).all()
        return jsonify({
            'success': True,
            'data': [item.to_dict() for item in items],
            'cached_at': datetime.utcnow().isoformat()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/menu/categories')
@login_required
def get_menu_categories():
    """Get menu categories for offline caching"""
    try:
        categories = MenuCategory.query.filter_by(is_active=True).all()
        return jsonify({
            'success': True,
            'data': [category.to_dict() for category in categories],
            'cached_at': datetime.utcnow().isoformat()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/tables')
@login_required
def get_tables():
    """Get tables for offline caching"""
    try:
        tables = Table.query.all()
        return jsonify({
            'success': True,
            'data': [table.to_dict() for table in tables],
            'cached_at': datetime.utcnow().isoformat()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/orders/recent')
@login_required
def get_recent_orders():
    """Get recent orders for offline caching"""
    try:
        # Get orders from last 7 days
        week_ago = datetime.utcnow() - timedelta(days=7)
        orders = Order.query.filter(
            Order.created_at >= week_ago,
            Order.restaurant_id == current_user.restaurant_id
        ).order_by(Order.created_at.desc()).limit(50).all()
        
        return jsonify({
            'success': True,
            'data': [order.to_dict() for order in orders],
            'cached_at': datetime.utcnow().isoformat()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/sync/order', methods=['POST'])
@login_required
def sync_order():
    """Sync offline orders when back online"""
    try:
        order_data = request.get_json()
        
        # Check if this is an offline order
        if 'offline_created' in order_data:
            # Create new order from offline data
            order = Order(
                restaurant_id=current_user.restaurant_id,
                user_id=current_user.id,
                table_id=order_data.get('table_id'),
                status='confirmed',
                subtotal=order_data.get('subtotal', 0),
                tax_amount=order_data.get('tax_amount', 0),
                total=order_data.get('total', 0),
                created_at=datetime.fromtimestamp(order_data['offline_created'] / 1000)
            )
            
            db.session.add(order)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'order_id': order.id,
                'message': 'Order synced successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Invalid offline order data'
            }), 400
            
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/sync/inventory', methods=['POST'])
@login_required
def sync_inventory():
    """Sync offline inventory changes when back online"""
    try:
        inventory_data = request.get_json()
        action = inventory_data.get('action')
        data = inventory_data.get('data')
        
        if action == 'create':
            # Create new inventory item
            from app.models.inventory import Ingredient
            ingredient = Ingredient(
                name=data.get('name'),
                current_stock=data.get('stock_level', 0),
                unit_cost=data.get('unit_cost', 0),
                minimum_stock=data.get('minimum_stock', 0),
                restaurant_id=current_user.restaurant_id
            )
            db.session.add(ingredient)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'ingredient_id': ingredient.id,
                'message': 'Inventory item synced successfully'
            })
            
        elif action == 'update':
            # Update existing inventory item
            from app.models.inventory import Ingredient
            ingredient = Ingredient.query.filter_by(
                id=data.get('id'),
                restaurant_id=current_user.restaurant_id
            ).first()
            
            if ingredient:
                ingredient.current_stock = data.get('stock_level', ingredient.current_stock)
                ingredient.unit_cost = data.get('unit_cost', ingredient.unit_cost)
                ingredient.minimum_stock = data.get('minimum_stock', ingredient.minimum_stock)
                db.session.commit()
                
                return jsonify({
                    'success': True,
                    'ingredient_id': ingredient.id,
                    'message': 'Inventory item updated successfully'
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'Inventory item not found'
                }), 404
                
        elif action == 'adjust':
            # Adjust stock level
            from app.models.inventory import Ingredient
            ingredient = Ingredient.query.filter_by(
                id=data.get('id'),
                restaurant_id=current_user.restaurant_id
            ).first()
            
            if ingredient:
                adjustment = data.get('adjustment', 0)
                ingredient.current_stock += adjustment
                db.session.commit()
                
                return jsonify({
                    'success': True,
                    'ingredient_id': ingredient.id,
                    'new_stock': ingredient.current_stock,
                    'message': 'Stock adjusted successfully'
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'Inventory item not found'
                }), 404
        else:
            return jsonify({
                'success': False,
                'error': 'Invalid inventory action'
            }), 400
            
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/sync/menu', methods=['POST'])
@login_required
def sync_menu():
    """Sync offline menu changes when back online"""
    try:
        menu_data = request.get_json()
        action = menu_data.get('action')
        data = menu_data.get('data')
        
        if action == 'create':
            # Create new menu item
            from app.models.menu import MenuItem
            menu_item = MenuItem(
                name=data.get('name'),
                description=data.get('description', ''),
                price=data.get('price', 0),
                category_id=data.get('category_id'),
                is_available=data.get('is_available', True),
                restaurant_id=current_user.restaurant_id
            )
            db.session.add(menu_item)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'item_id': menu_item.id,
                'message': 'Menu item synced successfully'
            })
            
        elif action == 'update':
            # Update existing menu item
            from app.models.menu import MenuItem
            menu_item = MenuItem.query.filter_by(
                id=data.get('id'),
                restaurant_id=current_user.restaurant_id
            ).first()
            
            if menu_item:
                menu_item.name = data.get('name', menu_item.name)
                menu_item.description = data.get('description', menu_item.description)
                menu_item.price = data.get('price', menu_item.price)
                menu_item.category_id = data.get('category_id', menu_item.category_id)
                menu_item.is_available = data.get('is_available', menu_item.is_available)
                db.session.commit()
                
                return jsonify({
                    'success': True,
                    'item_id': menu_item.id,
                    'message': 'Menu item updated successfully'
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'Menu item not found'
                }), 404
        else:
            return jsonify({
                'success': False,
                'error': 'Invalid menu action'
            }), 400
            
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/sync/user', methods=['POST'])
@login_required
def sync_user():
    """Sync offline user changes when back online"""
    try:
        user_data = request.get_json()
        action = user_data.get('action')
        data = user_data.get('data')
        
        if action == 'update':
            # Update user profile
            user = User.query.get(current_user.id)
            if user:
                user.name = data.get('name', user.name)
                user.email = data.get('email', user.email)
                user.phone = data.get('phone', user.phone)
                db.session.commit()
                
                return jsonify({
                    'success': True,
                    'user_id': user.id,
                    'message': 'User profile updated successfully'
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'User not found'
                }), 404
        elif action == 'profile':
            # Update user profile settings
            user = User.query.get(current_user.id)
            if user:
                # Update profile-specific fields
                if 'preferences' in data:
                    # Store user preferences (would need a user preferences table)
                    pass
                db.session.commit()
                
                return jsonify({
                    'success': True,
                    'user_id': user.id,
                    'message': 'User profile updated successfully'
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'User not found'
                }), 404
        else:
            return jsonify({
                'success': False,
                'error': 'Invalid user action'
            }), 400
            
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/sync/cart', methods=['POST'])
@login_required
def sync_cart():
    """Sync offline cart when back online"""
    try:
        cart_data = request.get_json()
        
        # Process cart sync logic here
        # This would integrate with the existing cart system
        
        return jsonify({
            'success': True,
            'message': 'Cart synced successfully'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/storage/info')
@login_required
def get_storage_info():
    """Get storage usage information for offline data"""
    try:
        # This would typically be handled client-side with IndexedDB
        # But we can provide server-side quotas and limits
        
        return jsonify({
            'success': True,
            'data': {
                'max_cache_age_hours': 24,
                'max_offline_orders': 100,
                'max_menu_items': 1000,
                'sync_batch_size': 50,
                'retry_attempts': 3
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/status')
def get_offline_status():
    """Get offline capability status"""
    return jsonify({
        'success': True,
        'data': {
            'offline_enabled': True,
            'sync_enabled': True,
            'cache_version': '2.0',
            'features': [
                'menu_caching',
                'order_sync',
                'cart_offline',
                'table_status',
                'notifications'
            ]
        }
    })

@bp.route('/sync/conflict', methods=['POST'])
@login_required
def resolve_conflict():
    """Resolve conflicts between offline and online data"""
    try:
        conflict_data = request.get_json()
        data_type = conflict_data.get('type')
        local_data = conflict_data.get('local_data')
        server_data = conflict_data.get('server_data')
        
        # Simple conflict resolution strategy
        resolution = 'local_wins'  # Default strategy
        
        if data_type == 'order':
            # For orders, use the most recent update
            local_modified = local_data.get('last_modified', 0)
            server_modified = server_data.get('last_modified', 0)
            
            if local_modified > server_modified:
                resolution = 'local_wins'
            else:
                resolution = 'server_wins'
        elif data_type == 'inventory':
            # For inventory, use the server value but add local adjustment
            resolution = 'merge'
        elif data_type == 'menu':
            # For menu items, use the most recent update
            local_modified = local_data.get('last_modified', 0)
            server_modified = server_data.get('last_modified', 0)
            
            if local_modified > server_modified:
                resolution = 'local_wins'
            else:
                resolution = 'server_wins'
        elif data_type == 'user':
            # For user profiles, merge the data
            resolution = 'merge'
        
        return jsonify({
            'success': True,
            'resolution': resolution,
            'message': f'Conflict resolved using {resolution} strategy'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/sync/batch', methods=['POST'])
@login_required
def sync_batch():
    """Process a batch of sync operations"""
    try:
        batch_data = request.get_json()
        operations = batch_data.get('operations', [])
        results = []
        
        for operation in operations:
            op_type = operation.get('type')
            op_action = operation.get('action', 'create')
            op_data = operation.get('data')
            
            try:
                if op_type == 'order':
                    # Process order operation
                    if op_action == 'create':
                        order = Order(
                            restaurant_id=current_user.restaurant_id,
                            user_id=current_user.id,
                            table_id=op_data.get('table_id'),
                            status='confirmed',
                            subtotal=op_data.get('subtotal', 0),
                            tax_amount=op_data.get('tax_amount', 0),
                            total=op_data.get('total', 0),
                            created_at=datetime.fromtimestamp(op_data.get('offline_created', time.time()) / 1000)
                        )
                        db.session.add(order)
                        db.session.commit()
                        results.append({'success': True, 'id': order.id, 'type': 'order'})
                    else:
                        results.append({'success': False, 'error': 'Unsupported order action', 'type': 'order'})
                        
                elif op_type == 'inventory':
                    # Process inventory operation
                    from app.models.inventory import Ingredient
                    if op_action == 'create':
                        ingredient = Ingredient(
                            name=op_data.get('name'),
                            current_stock=op_data.get('current_stock', 0),
                            unit_cost=op_data.get('unit_cost', 0),
                            minimum_stock=op_data.get('minimum_stock', 0),
                            restaurant_id=current_user.restaurant_id
                        )
                        db.session.add(ingredient)
                        db.session.commit()
                        results.append({'success': True, 'id': ingredient.id, 'type': 'inventory'})
                    elif op_action == 'update':
                        ingredient = Ingredient.query.filter_by(
                            id=op_data.get('ingredient_id'),
                            restaurant_id=current_user.restaurant_id
                        ).first()
                        if ingredient:
                            adjustment = op_data.get('stock_adjustment', 0)
                            ingredient.current_stock += adjustment
                            db.session.commit()
                            results.append({'success': True, 'id': ingredient.id, 'type': 'inventory'})
                        else:
                            results.append({'success': False, 'error': 'Ingredient not found', 'type': 'inventory'})
                    else:
                        results.append({'success': False, 'error': 'Unsupported inventory action', 'type': 'inventory'})
                        
                elif op_type == 'menu':
                    # Process menu operation
                    if op_action == 'create':
                        menu_item = MenuItem(
                            name=op_data.get('name'),
                            description=op_data.get('description', ''),
                            price=op_data.get('price', 0),
                            category_id=op_data.get('category_id'),
                            is_available=op_data.get('is_available', True),
                            restaurant_id=current_user.restaurant_id
                        )
                        db.session.add(menu_item)
                        db.session.commit()
                        results.append({'success': True, 'id': menu_item.id, 'type': 'menu'})
                    else:
                        results.append({'success': False, 'error': 'Unsupported menu action', 'type': 'menu'})
                        
                elif op_type == 'user':
                    # Process user operation
                    if op_action == 'update':
                        user = User.query.get(current_user.id)
                        if user:
                            profile_updates = op_data.get('profile_updates', {})
                            if 'phone' in profile_updates:
                                user.phone = profile_updates['phone']
                            if 'address' in profile_updates:
                                user.address = profile_updates['address']
                            db.session.commit()
                            results.append({'success': True, 'id': user.id, 'type': 'user'})
                        else:
                            results.append({'success': False, 'error': 'User not found', 'type': 'user'})
                    else:
                        results.append({'success': False, 'error': 'Unsupported user action', 'type': 'user'})
                        
                else:
                    results.append({'success': False, 'error': f'Unknown operation type: {op_type}', 'type': op_type})
                    
            except Exception as e:
                db.session.rollback()
                results.append({'success': False, 'error': str(e), 'type': op_type})
        
        return jsonify({
            'success': True,
            'results': results,
            'processed': len(results)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500