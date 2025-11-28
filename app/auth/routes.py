from flask import render_template, request, redirect, url_for, flash, session, current_app, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from sqlalchemy import not_
from app.auth import bp
from app.models.user import User
from app import db
from datetime import datetime, timedelta
from werkzeug.urls import url_parse

@bp.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = bool(request.form.get('remember'))
        
        if request.headers.get('HX-Request'):
            # HTMX request - return partial response
            user = User.query.filter_by(email=email).first()
            
            if user and user.check_password(password) and user.user_active:
                login_user(user, remember=remember)
                user.update_last_login()
                
                # Set session timeout based on remember preference
                session.permanent = True  # Always make session permanent
                if remember:
                    current_app.permanent_session_lifetime = timedelta(days=7)
                else:
                    current_app.permanent_session_lifetime = timedelta(hours=2)
                
                # Check if this is HTMX request
                if request.headers.get('HX-Request'):
                    # HTMX request - return success response with redirect info
                    return jsonify({
                        'success': True,
                        'user': user.to_dict(),
                        'redirect': url_for('main.dashboard'),
                        'remember': remember
                    })
                else:
                    # Regular form submission - redirect normally
                    next_page = request.args.get('next')
                    if not next_page or url_parse(next_page).netloc != '':
                        next_page = url_for('main.dashboard')
                    return redirect(next_page)
            else:
                if request.headers.get('HX-Request'):
                    return jsonify({
                        'success': False,
                        'message': 'Invalid email or password'
                    })
                else:
                    return render_template('auth/login.html',
                                       email=email,
                                       error='Invalid email or password')
        
        # Regular form submission
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password) and user.user_active:
            login_user(user, remember=remember)
            user.update_last_login()
            
            # Set session timeout based on remember preference
            session.permanent = True  # Always make session permanent
            if remember:
                current_app.permanent_session_lifetime = timedelta(days=7)
            else:
                current_app.permanent_session_lifetime = timedelta(hours=2)
            
            next_page = request.args.get('next')
            if not next_page or url_parse(next_page).netloc != '':
                next_page = url_for('main.dashboard')
            
            flash(f'Welcome back, {user.name}!', 'success')
            return redirect(next_page)
        else:
            flash('Invalid email or password', 'error')
    
    return render_template('auth/login.html')

@bp.route('/pin-login', methods=['POST'])
def pin_login():
    """Handle PIN login for quick access"""
    pin = request.form.get('pin')
    
    if request.headers.get('HX-Request'):
        # HTMX request
        users = User.query.filter(User.pin_code != None, User.user_active == True).all()
        
        for user in users:
            if user.check_pin(pin):
                login_user(user, remember=False)
                user.update_last_login()
                
                # Set session timeout for PIN login (shorter but persistent)
                session.permanent = True
                current_app.permanent_session_lifetime = timedelta(hours=1)
                
                if user.role == 'cashier':
                    return render_template('auth/partials/cashier_login_success.html')
                elif user.role == 'kitchen':
                    return render_template('auth/partials/kitchen_login_success.html')
        
        return render_template('auth/partials/pin_form.html', error='Invalid PIN')
    
    # Regular PIN login
    users = User.query.filter(User.pin_code != None, User.user_active == True).all()
    
    for user in users:
        if user.check_pin(pin):
            login_user(user, remember=False)
            user.update_last_login()
            
            # Set session timeout for PIN login (shorter but persistent)
            session.permanent = True
            current_app.permanent_session_lifetime = timedelta(hours=1)
            
            flash(f'Welcome back, {user.name}!', 'success')
            return redirect(url_for('main.dashboard'))
    
    flash('Invalid PIN', 'error')
    return redirect(url_for('auth.login'))

@bp.route('/logout')
@login_required
def logout():
    """Handle user logout"""
    logout_user()
    flash('You have been logged out', 'info')
    return redirect(url_for('auth.login'))

@bp.route('/session-timeout')
def session_timeout():
    """Handle session timeout"""
    logout_user()
    flash('Your session has expired due to inactivity', 'warning')
    return redirect(url_for('auth.login'))

@bp.route('/profile')
@login_required
def profile():
    """User profile page"""
    return render_template('auth/profile.html')

@bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    """Change user password"""
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        if not current_user.check_password(current_password):
            flash('Current password is incorrect', 'error')
        elif new_password != confirm_password:
            flash('New passwords do not match', 'error')
        elif not new_password or len(new_password) < 6:
            flash('Password must be at least 6 characters long', 'error')
        else:
            current_user.set_password(new_password)
            db.session.commit()
            flash('Password changed successfully', 'success')
            return redirect(url_for('auth.profile'))
    
    return render_template('auth/change_password.html')

@bp.route('/set-pin', methods=['GET', 'POST'])
@login_required
def set_pin():
    """Set or change PIN code"""
    if request.method == 'POST':
        pin = request.form.get('pin')
        confirm_pin = request.form.get('confirm_pin')
        
        if pin != confirm_pin:
            flash('PINs do not match', 'error')
        elif not pin or len(pin) != 4 or not pin.isdigit():
            flash('PIN must be exactly 4 digits', 'error')
        else:
            current_user.set_pin(pin)
            db.session.commit()
            flash('PIN set successfully', 'success')
            return redirect(url_for('auth.profile'))
    
    return render_template('auth/set_pin.html')

@bp.context_processor
def inject_auth_helpers():
    """Add authentication helpers to templates"""
    def role_required(role):
        """Check if current user has required role"""
        return current_user.is_authenticated and current_user.has_role(role)
    
    def can_manage_users():
        """Check if current user can manage users"""
        return current_user.is_authenticated and current_user.can_access_admin_features()
    
    def can_manage_menu():
        """Check if current user can manage menu"""
        return current_user.is_authenticated and current_user.can_access_manager_features()
    
    return dict(
        role_required=role_required,
        can_manage_users=can_manage_users,
        can_manage_menu=can_manage_menu
    )

@bp.route('/status')
def auth_status():
    """Check authentication status for API requests"""
    if current_user.is_authenticated:
        return jsonify({
            'authenticated': True,
            'user': current_user.to_dict(),
            'remember': session.permanent
        })
    else:
        return jsonify({
            'authenticated': False,
            'user': None,
            'remember': False
        })

@bp.route('/api/status')
def api_auth_status():
    """API endpoint for authentication status"""
    return auth_status()