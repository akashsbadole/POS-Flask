"""
Notification routes for managing email and SMS notifications
"""

from flask import render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
from app.notifications import bp
from app.notifications.service import notification_service
from app.models.notification import Notification, NotificationLog, NotificationPreference, EmailTemplate, SmsTemplate
from app.models.order import Order
from app import db
from datetime import datetime, timedelta

@bp.route('/')
@login_required
def dashboard():
    """Notification dashboard"""
    if not current_user.can_access_manager_features():
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    # Get recent notifications
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', '')
    type_filter = request.args.get('type', '')
    
    query = Notification.query
    
    # Apply filters
    if status_filter:
        query = query.filter_by(status=status_filter)
    if type_filter:
        query = query.filter_by(type=type_filter)
    
    notifications = query.order_by(Notification.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    # Get statistics
    stats = get_notification_stats()
    
    return render_template('notifications/dashboard.html', 
                         notifications=notifications, 
                         stats=stats,
                         status_filter=status_filter,
                         type_filter=type_filter)

@bp.route('/settings')
@login_required
def settings():
    """Notification settings page"""
    if not current_user.can_access_manager_features():
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    # Get notification preferences
    preferences = NotificationPreference.query.filter_by(
        restaurant_id=current_user.restaurant_id
    ).all() if current_user.restaurant_id else []
    
    # Get email templates
    email_templates = EmailTemplate.query.filter_by(
        restaurant_id=current_user.restaurant_id
    ).all() if current_user.restaurant_id else EmailTemplate.query.filter_by(restaurant_id=None).all()
    
    # Get SMS templates
    sms_templates = SmsTemplate.query.filter_by(
        restaurant_id=current_user.restaurant_id
    ).all() if current_user.restaurant_id else SmsTemplate.query.filter_by(restaurant_id=None).all()
    
    return render_template('notifications/settings.html',
                         preferences=preferences,
                         email_templates=email_templates,
                         sms_templates=sms_templates)

@bp.route('/test', methods=['GET', 'POST'])
@login_required
def test_notification():
    """Test notification sending"""
    if not current_user.can_access_manager_features():
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        notification_type = request.form.get('notification_type')
        recipient = request.form.get('recipient')
        
        if not recipient:
            flash('Recipient is required', 'error')
            return redirect(url_for('notifications.test_notification'))
        
        # Test email notification
        if notification_type in ['email_receipt', 'email_confirmation', 'email_low_stock', 'email_license']:
            if '@' not in recipient:
                flash('Invalid email address', 'error')
                return redirect(url_for('notifications.test_notification'))
            
            if notification_type == 'email_receipt':
                # Create a test order
                test_order = create_test_order()
                result = notification_service.send_order_receipt(test_order, email=recipient)
            elif notification_type == 'email_confirmation':
                test_order = create_test_order()
                result = notification_service.send_order_confirmation(test_order, email=recipient)
            elif notification_type == 'email_low_stock':
                test_ingredient = create_test_ingredient()
                result = notification_service.send_low_stock_alert(test_ingredient, 5.0, 10.0)
            elif notification_type == 'email_license':
                test_license = create_test_license()
                result = notification_service.send_license_renewal_reminder(test_license, 30)
            
            if result:
                flash('Test email sent successfully', 'success')
            else:
                flash('Failed to send test email', 'error')
        
        # Test SMS notification
        elif notification_type in ['sms_receipt', 'sms_confirmation']:
            # Basic phone number validation
            if not recipient.startswith('+'):
                flash('Phone number must include country code (e.g., +1)', 'error')
                return redirect(url_for('notifications.test_notification'))
            
            test_order = create_test_order()
            if notification_type == 'sms_receipt':
                result = notification_service.send_order_receipt(test_order, phone=recipient)
            elif notification_type == 'sms_confirmation':
                result = notification_service.send_order_confirmation(test_order, phone=recipient)
            
            if result and result.get('sms'):
                flash('Test SMS sent successfully', 'success')
            else:
                flash('Failed to send test SMS', 'error')
        
        return redirect(url_for('notifications.test_notification'))
    
    return render_template('notifications/test.html')

@bp.route('/logs')
@login_required
def notification_logs():
    """View notification delivery logs"""
    if not current_user.can_access_manager_features():
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', '')
    channel_filter = request.args.get('channel', '')
    
    query = NotificationLog.query
    
    # Apply filters
    if status_filter:
        query = query.filter_by(status=status_filter)
    if channel_filter:
        query = query.filter_by(channel=channel_filter)
    
    logs = query.order_by(NotificationLog.attempt_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('notifications/logs.html',
                         logs=logs,
                         status_filter=status_filter,
                         channel_filter=channel_filter)

@bp.route('/preferences', methods=['POST'])
@login_required
def update_preferences():
    """Update notification preferences"""
    if not current_user.can_access_manager_features():
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    notification_type = request.form.get('notification_type')
    channel = request.form.get('channel')
    is_enabled = request.form.get('is_enabled') == 'true'
    
    # Find existing preference or create new one
    preference = NotificationPreference.query.filter_by(
        restaurant_id=current_user.restaurant_id,
        notification_type=notification_type,
        channel=channel
    ).first()
    
    if preference:
        preference.is_enabled = is_enabled
        preference.updated_at = datetime.utcnow()
    else:
        preference = NotificationPreference(
            restaurant_id=current_user.restaurant_id,
            notification_type=notification_type,
            channel=channel,
            is_enabled=is_enabled
        )
        db.session.add(preference)
    
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Preference updated'})

@bp.route('/templates/email', methods=['GET', 'POST'])
@login_required
def email_templates():
    """Manage email templates"""
    if not current_user.can_access_manager_features():
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        template_id = request.form.get('template_id')
        name = request.form.get('name')
        subject = request.form.get('subject')
        html_content = request.form.get('html_content')
        text_content = request.form.get('text_content')
        
        if template_id:
            # Update existing template
            template = EmailTemplate.query.get(template_id)
            if template and (template.restaurant_id == current_user.restaurant_id or template.restaurant_id is None):
                template.name = name
                template.subject = subject
                template.html_content = html_content
                template.text_content = text_content
                template.updated_at = datetime.utcnow()
        else:
            # Create new template
            template = EmailTemplate(
                name=name,
                subject=subject,
                html_content=html_content,
                text_content=text_content,
                restaurant_id=current_user.restaurant_id
            )
            db.session.add(template)
        
        db.session.commit()
        flash('Email template saved successfully', 'success')
        return redirect(url_for('notifications.email_templates'))
    
    templates = EmailTemplate.query.filter(
        (EmailTemplate.restaurant_id == current_user.restaurant_id) |
        (EmailTemplate.restaurant_id.is_(None))
    ).all()
    
    return render_template('notifications/email_templates.html', templates=templates)

@bp.route('/templates/sms', methods=['GET', 'POST'])
@login_required
def sms_templates():
    """Manage SMS templates"""
    if not current_user.can_access_manager_features():
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        template_id = request.form.get('template_id')
        name = request.form.get('name')
        content = request.form.get('content')
        
        if template_id:
            # Update existing template
            template = SmsTemplate.query.get(template_id)
            if template and (template.restaurant_id == current_user.restaurant_id or template.restaurant_id is None):
                template.name = name
                template.content = content
                template.updated_at = datetime.utcnow()
        else:
            # Create new template
            template = SmsTemplate(
                name=name,
                content=content,
                restaurant_id=current_user.restaurant_id
            )
            db.session.add(template)
        
        db.session.commit()
        flash('SMS template saved successfully', 'success')
        return redirect(url_for('notifications.sms_templates'))
    
    templates = SmsTemplate.query.filter(
        (SmsTemplate.restaurant_id == current_user.restaurant_id) |
        (SmsTemplate.restaurant_id.is_(None))
    ).all()
    
    return render_template('notifications/sms_templates.html', templates=templates)

@bp.route('/retry/<int:notification_id>')
@login_required
def retry_notification(notification_id):
    """Retry a failed notification"""
    if not current_user.can_access_manager_features():
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    notification = Notification.query.get_or_404(notification_id)
    
    if notification.status != 'failed':
        flash('Only failed notifications can be retried', 'error')
        return redirect(url_for('notifications.dashboard'))
    
    # Reset notification status
    notification.status = 'pending'
    notification.error_message = None
    notification.retry_count += 1
    
    if notification.retry_count >= notification.max_retries:
        flash('Maximum retry attempts reached', 'error')
        return redirect(url_for('notifications.dashboard'))
    
    db.session.commit()
    
    # Resend based on type
    if notification.type == 'email':
        # Resend email
        notification_service._send_email_async(
            notification.id,
            notification.content,
            notification.context or {}
        )
    elif notification.type == 'sms':
        # Resend SMS
        notification_service._send_sms_async(
            notification.id,
            notification.content,
            notification.context or {}
        )
    
    flash('Notification retry initiated', 'success')
    return redirect(url_for('notifications.dashboard'))

# Helper functions
def get_notification_stats():
    """Get notification statistics"""
    total = Notification.query.count()
    sent = Notification.query.filter_by(status='sent').count()
    failed = Notification.query.filter_by(status='failed').count()
    pending = Notification.query.filter_by(status='pending').count()
    
    email_count = Notification.query.filter_by(type='email').count()
    sms_count = Notification.query.filter_by(type='sms').count()
    
    return {
        'total': total,
        'sent': sent,
        'failed': failed,
        'pending': pending,
        'email_count': email_count,
        'sms_count': sms_count,
        'success_rate': (sent / total * 100) if total > 0 else 0
    }

def create_test_order():
    """Create a test order for testing notifications"""
    from app.models.menu import MenuItem
    from app.models.user import User
    
    # Get a sample menu item
    menu_item = MenuItem.query.first()
    if not menu_item:
        menu_item = type('MockMenuItem', (), {
            'name': 'Test Item',
            'price': 10.00
        })()
    
    # Create test order
    test_order = type('MockOrder', (), {
        'order_number': 'TEST001',
        'status': 'completed',
        'subtotal': 10.00,
        'tax_amount': 0.80,
        'total': 10.80,
        'created_at': datetime.utcnow(),
        'items': [],
        'payments': [],
        'restaurant': None,
        'table': None
    })()
    
    return test_order

def create_test_ingredient():
    """Create a test ingredient for testing notifications"""
    from app.models.inventory import Ingredient, IngredientCategory
    
    # Get a sample ingredient category
    category = IngredientCategory.query.first()
    if not category:
        category = type('MockCategory', (), {'name': 'Test Category'})()
    
    # Create test ingredient
    test_ingredient = type('MockIngredient', (), {
        'name': 'Test Ingredient',
        'category': category,
        'unit': 'kg'
    })()
    
    return test_ingredient

def create_test_license():
    """Create a test license for testing notifications"""
    test_license = type('MockLicense', (), {
        'license_type': 'Business License',
        'license_number': 'TEST-12345',
        'issued_to': 'Test Restaurant',
        'issuing_authority': 'Test Authority',
        'issue_date': datetime.utcnow() - timedelta(days=365),
        'expiry_date': (datetime.utcnow() + timedelta(days=30)).strftime('%Y-%m-%d'),
        'description': 'Test license for notification testing'
    })()
    
    return test_license