from functools import wraps
from flask import abort, flash, redirect, url_for
from flask_login import current_user

def role_required(*roles):
    """
    Decorator to require specific user roles to access a route
    Usage: @role_required('admin', 'manager')
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login'))
            
            if not current_user.user_active:
                flash('Your account is inactive', 'error')
                return redirect(url_for('auth.login'))
            
            if current_user.role not in roles:
                flash('You do not have permission to access this page', 'error')
                abort(403)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def restaurant_required(f):
    """
    Decorator to require user to be associated with a restaurant
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        
        if not current_user.user_active:
            flash('Your account is inactive', 'error')
            return redirect(url_for('auth.login'))
        
        if current_user.role == 'super_admin':
            return f(*args, **kwargs)
        
        if not current_user.restaurant_id:
            flash('You must be associated with a restaurant to access this page', 'error')
            return redirect(url_for('auth.login'))
        
        return f(*args, **kwargs)
    return decorated_function

def super_admin_required(f):
    """
    Decorator to require super admin access
    """
    return role_required('super_admin')(f)

def restaurant_owner_required(f):
    """
    Decorator to require restaurant owner access
    """
    return role_required('restaurant_owner', 'super_admin')(f)

def manager_required(f):
    """
    Decorator to require manager access
    """
    return role_required('manager', 'restaurant_owner', 'super_admin')(f)

def cashier_required(f):
    """
    Decorator to require cashier access
    """
    return role_required('cashier', 'manager', 'restaurant_owner', 'super_admin')(f)

def kitchen_required(f):
    """
    Decorator to require kitchen staff access
    """
    return role_required('kitchen', 'manager', 'restaurant_owner', 'super_admin')(f)

def staff_required(f):
    """
    Decorator to require staff access
    """
    return role_required('staff', 'manager', 'restaurant_owner', 'super_admin')(f)

def permission_required(permission):
    """
    Decorator to require specific permission
    Usage: @permission_required('manage_restaurant')
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login'))
            
            if not current_user.user_active:
                flash('Your account is inactive', 'error')
                return redirect(url_for('auth.login'))
            
            user_permissions = current_user.get_permissions()
            if permission not in user_permissions:
                flash('You do not have permission to perform this action', 'error')
                abort(403)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def restaurant_management_required(f):
    """
    Decorator to require restaurant management permissions
    """
    return permission_required('manage_restaurant')(f)

def subscription_management_required(f):
    """
    Decorator to require subscription management permissions
    """
    return permission_required('manage_subscriptions')(f)

def license_management_required(f):
    """
    Decorator to require license management permissions
    """
    return permission_required('manage_licenses')(f)

def user_management_required(f):
    """
    Decorator to require user management permissions
    """
    return permission_required('manage_users')(f)

def reporting_required(f):
    """
    Decorator to require reporting permissions
    """
    return permission_required('view_reports')(f)

def inventory_management_required(f):
    """
    Decorator to require inventory management permissions
    """
    return permission_required('manage_inventory')(f)