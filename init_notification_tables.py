"""
Initialize notification tables for the Restaurant POS System
"""

from app import create_app, db
from app.models.notification import Notification, NotificationLog, NotificationPreference, EmailTemplate, SmsTemplate

def init_notification_tables():
    """Initialize notification tables"""
    app = create_app()
    
    with app.app_context():
        print("Creating notification tables...")
        
        # Create all notification-related tables
        db.create_all()
        
        # Create default email templates
        create_default_email_templates()
        
        # Create default SMS templates
        create_default_sms_templates()
        
        print("Notification tables created successfully!")

def create_default_email_templates():
    """Create default email templates"""
    from app.models.notification import EmailTemplate
    
    # Check if templates already exist
    existing_templates = EmailTemplate.query.filter_by(restaurant_id=None).count()
    if existing_templates > 0:
        print("Default email templates already exist")
        return
    
    # Order receipt template
    receipt_template = EmailTemplate(
        name='order_receipt',
        subject='Receipt - Order {{ order.order_number }}',
        html_content='''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Order Receipt</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; }
        .header { background-color: #2c3e50; color: white; padding: 20px; text-align: center; }
        .content { padding: 20px; }
        .footer { background-color: #f8f9fa; padding: 20px; text-align: center; font-size: 12px; }
    </style>
</head>
<body>
    <div class="header">
        <h1>Order Receipt</h1>
        <p>Order {{ order.order_number }}</p>
    </div>
    <div class="content">
        <p>Thank you for your order!</p>
        <p>Total: ${{ order.total }}</p>
    </div>
    <div class="footer">
        <p>Thank you for your business!</p>
    </div>
</body>
</html>''',
        is_default=True
    )
    
    # Order confirmation template
    confirmation_template = EmailTemplate(
        name='order_confirmation',
        subject='Order Confirmation - {{ order.order_number }}',
        html_content='''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Order Confirmation</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; }
        .header { background-color: #27ae60; color: white; padding: 20px; text-align: center; }
        .content { padding: 20px; }
        .footer { background-color: #f8f9fa; padding: 20px; text-align: center; font-size: 12px; }
    </style>
</head>
<body>
    <div class="header">
        <h1>Order Confirmed!</h1>
        <p>Order {{ order.order_number }}</p>
    </div>
    <div class="content">
        <p>Your order has been confirmed and is being prepared.</p>
        <p>Estimated time: {{ estimated_time }}</p>
        <p>Total: ${{ order.total }}</p>
    </div>
    <div class="footer">
        <p>We'll notify you when your order is ready!</p>
    </div>
</body>
</html>''',
        is_default=True
    )
    
    # Low stock alert template
    low_stock_template = EmailTemplate(
        name='low_stock_alert',
        subject='Low Stock Alert - {{ ingredient.name }}',
        html_content='''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Low Stock Alert</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; }
        .header { background-color: #e74c3c; color: white; padding: 20px; text-align: center; }
        .content { padding: 20px; }
        .footer { background-color: #f8f9fa; padding: 20px; text-align: center; font-size: 12px; }
    </style>
</head>
<body>
    <div class="header">
        <h1>⚠️ Low Stock Alert</h1>
    </div>
    <div class="content">
        <p>Ingredient: {{ ingredient.name }}</p>
        <p>Current Stock: {{ current_stock }} {{ ingredient.unit }}</p>
        <p>Minimum Stock: {{ threshold }} {{ ingredient.unit }}</p>
        <p>Shortage: {{ shortage }} {{ ingredient.unit }}</p>
        <p>Please restock soon to avoid service disruption.</p>
    </div>
    <div class="footer">
        <p>This is an automated alert from Restaurant POS System</p>
    </div>
</body>
</html>''',
        is_default=True
    )
    
    # License renewal reminder template
    license_template = EmailTemplate(
        name='license_renewal',
        subject='License Renewal Reminder - {{ license.license_type }}',
        html_content='''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>License Renewal Reminder</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; }
        .header { background-color: #f39c12; color: white; padding: 20px; text-align: center; }
        .content { padding: 20px; }
        .footer { background-color: #f8f9fa; padding: 20px; text-align: center; font-size: 12px; }
    </style>
</head>
<body>
    <div class="header">
        <h1>📋 License Renewal Reminder</h1>
    </div>
    <div class="content">
        <p>License Type: {{ license.license_type }}</p>
        <p>License Number: {{ license.license_number }}</p>
        <p>Expiry Date: {{ expiry_date }}</p>
        <p>Days Remaining: {{ days_until_expiry }}</p>
        <p>Please renew your license before it expires to avoid service interruption.</p>
    </div>
    <div class="footer">
        <p>This is an automated reminder from Restaurant POS System</p>
    </div>
</body>
</html>''',
        is_default=True
    )
    
    db.session.add_all([receipt_template, confirmation_template, low_stock_template, license_template])
    db.session.commit()
    print("Default email templates created")

def create_default_sms_templates():
    """Create default SMS templates"""
    from app.models.notification import SmsTemplate
    
    # Check if templates already exist
    existing_templates = SmsTemplate.query.filter_by(restaurant_id=None).count()
    if existing_templates > 0:
        print("Default SMS templates already exist")
        return
    
    # Order confirmation template
    confirmation_template = SmsTemplate(
        name='order_confirmation',
        content='Order {{ order.order_number }} confirmed! {{ estimated_time }}. Total: ${{ "%.2f"|format(order.total) }}. Thank you!',
        is_default=True
    )
    
    # Order receipt template
    receipt_template = SmsTemplate(
        name='order_receipt',
        content='Your order {{ order.order_number }} is complete. Total: ${{ "%.2f"|format(order.total) }}. Thank you for your purchase!',
        is_default=True
    )
    
    db.session.add_all([confirmation_template, receipt_template])
    db.session.commit()
    print("Default SMS templates created")

if __name__ == '__main__':
    init_notification_tables()