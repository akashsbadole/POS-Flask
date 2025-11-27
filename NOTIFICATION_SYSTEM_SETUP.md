# Email/SMS Notification System Setup Guide

This guide explains how to configure and use the Email/SMS Notification System for the Restaurant POS application.

## Overview

The notification system provides:
- Email notifications for orders, receipts, low stock alerts, and license renewals
- SMS notifications for order confirmations and receipts
- Notification preferences management
- Template customization
- Delivery tracking and retry logic

## 1. Configuration

### Environment Variables

Add the following environment variables to your `.env` file or system environment:

#### Email Configuration (SMTP)
```bash
# Email provider (gmail, outlook, custom)
EMAIL_PROVIDER=gmail

# SMTP server settings
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USE_SSL=false
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
MAIL_DEFAULT_SENDER=noreply@yourrestaurant.com
MAIL_MAX_EMAILS=10
```

#### SMS Configuration (Twilio)
```bash
# SMS provider (twilio, aws_sns, custom)
SMS_PROVIDER=twilio

# Twilio settings
SMS_ACCOUNT_SID=your-twilio-account-sid
SMS_AUTH_TOKEN=your-twilio-auth-token
SMS_FROM_NUMBER=+1234567890
```

#### SMS Configuration (AWS SNS)
```bash
# AWS SNS settings
SMS_PROVIDER=aws_sns
SMS_AWS_ACCESS_KEY=your-aws-access-key
SMS_AWS_SECRET_KEY=your-aws-secret-key
SMS_AWS_REGION=us-east-1
```

#### Notification Settings
```bash
# Enable/disable notifications
ENABLE_EMAIL_NOTIFICATIONS=true
ENABLE_SMS_NOTIFICATIONS=false

# Queue and retry settings
NOTIFICATION_QUEUE_ENABLED=true
NOTIFICATION_RETRY_ATTEMPTS=3
NOTIFICATION_RETRY_DELAY=60
```

### Gmail Setup

1. Enable 2-Factor authentication on your Gmail account
2. Generate an App Password:
   - Go to Google Account settings
   - Security → 2-Step Verification → App passwords
   - Generate a new app password
   - Use this app password in `MAIL_PASSWORD`

### Outlook Setup

1. Use these settings for Outlook:
```bash
EMAIL_PROVIDER=outlook
MAIL_SERVER=smtp-mail.outlook.com
MAIL_PORT=587
MAIL_USE_TLS=true
```

### Twilio Setup

1. Create a Twilio account at https://www.twilio.com
2. Get your Account SID and Auth Token from the Console
3. Purchase a phone number or use your existing one
4. Add the credentials to your environment variables

## 2. Database Setup

Run the database migration script to create notification tables:

```bash
python init_notification_tables.py
```

This will create:
- `notifications` - Main notification records
- `notification_logs` - Delivery attempt logs
- `notification_preferences` - User preferences
- `email_templates` - Custom email templates
- `sms_templates` - Custom SMS templates

## 3. Install Dependencies

Install the required packages:

```bash
pip install -r requirements.txt
```

Key packages for notifications:
- `Flask-Mail==0.9.1` - Email sending
- `twilio==8.8.0` - SMS sending via Twilio
- `boto3==1.28.57` - SMS sending via AWS SNS
- `celery==5.3.2` - Background task processing
- `redis==5.0.0` - Message queue (optional)

## 4. Integration Points

### Order Process Integration

The notification system is automatically integrated into:

1. **Order Confirmation** - Sent when order is created
   - Email: Full order details with estimated time
   - SMS: Brief confirmation with order number

2. **Order Receipt** - Sent when order is paid
   - Email: Detailed receipt with items and payments
   - SMS: Short receipt with total amount

3. **Low Stock Alerts** - Sent when ingredients fall below threshold
   - Email: Detailed alert with current stock and shortage
   - Automatic: Sent during stock adjustments

### Adding Notifications to Custom Workflows

```python
from app.notifications.service import notification_service

# Send order confirmation
notification_service.send_order_confirmation(order, email="customer@example.com", phone="+1234567890")

# Send order receipt
notification_service.send_order_receipt(order, email="customer@example.com", phone="+1234567890")

# Send low stock alert
notification_service.send_low_stock_alert(ingredient, current_stock, threshold)

# Send license renewal reminder
notification_service.send_license_renewal_reminder(license_obj, days_until_expiry)
```

## 5. Template Customization

### Email Templates

Templates are located in `app/templates/notifications/email/`:
- `order_receipt.html` - Order receipt email
- `order_confirmation.html` - Order confirmation email
- `low_stock_alert.html` - Low stock alert email
- `license_renewal_reminder.html` - License renewal reminder email

### SMS Templates

Templates are located in `app/templates/notifications/sms/`:
- `order_receipt.txt` - Order receipt SMS
- `order_confirmation.txt` - Order confirmation SMS

### Custom Templates

Create custom templates via the admin interface:
1. Go to Notifications → Settings
2. Click "Manage Templates" under Email or SMS sections
3. Create or edit templates with Jinja2 variables

#### Available Template Variables

**Order Templates:**
- `{{ order.order_number }}` - Order number
- `{{ order.total }}` - Order total
- `{{ order.created_at }}` - Order date/time
- `{{ order.items }}` - Order items list
- `{{ order.payments }}` - Payment information
- `{{ restaurant.name }}` - Restaurant name
- `{{ estimated_time }}` - Estimated preparation time

**Low Stock Templates:**
- `{{ ingredient.name }}` - Ingredient name
- `{{ current_stock }}` - Current stock level
- `{{ threshold }}` - Minimum stock threshold
- `{{ shortage }}` - Amount below threshold

**License Templates:**
- `{{ license.license_type }}` - Type of license
- `{{ license.license_number }}` - License number
- `{{ days_until_expiry }}` - Days until expiration
- `{{ expiry_date }}` - Expiration date

## 6. Management Interface

Access the notification management at `/notifications`:

### Dashboard (`/notifications/`)
- View all notifications with filtering
- See statistics (sent, failed, pending)
- Retry failed notifications
- Monitor success rates

### Settings (`/notifications/settings`)
- Configure notification preferences
- Manage email and SMS templates
- Enable/disable notification types
- Set per-order or global preferences

### Test Notifications (`/notifications/test`)
- Test email notifications with various templates
- Test SMS notifications
- Verify configuration status
- Debug delivery issues

### Logs (`/notifications/logs`)
- View detailed delivery logs
- Filter by status and channel
- Troubleshoot failed deliveries
- Monitor retry attempts

## 7. Monitoring and Troubleshooting

### Checking Notification Status

1. Check the dashboard for real-time status
2. Review logs for detailed delivery information
3. Monitor success rates and identify issues

### Common Issues

**Email Not Sending:**
- Check SMTP credentials and server settings
- Verify firewall allows SMTP traffic
- Check if email/password is correct
- Ensure TLS/SSL settings match provider requirements

**SMS Not Sending:**
- Verify Twilio credentials and phone number
- Check account balance and permissions
- Ensure phone number is in E.164 format (+countrycode<number>)
- Check if recipient phone number is valid

**High Failure Rates:**
- Check recipient email/phone validity
- Review templates for syntax errors
- Monitor rate limits with providers
- Check for network connectivity issues

### Debug Mode

Enable debug logging by setting:
```python
app.config['DEBUG'] = True
app.config['MAIL_SUPPRESS_SEND'] = False  # Set to True for testing
```

## 8. Security Considerations

### Email Security
- Use app-specific passwords for Gmail
- Enable TLS/SSL as required by provider
- Store credentials securely (environment variables, not in code)
- Consider using OAuth2 for production deployments

### SMS Security
- Protect Twilio credentials
- Validate phone numbers before sending
- Implement rate limiting to prevent abuse
- Consider opt-in requirements for marketing messages

### Data Privacy
- Log all notifications for audit trail
- Provide opt-out mechanisms
- Secure personal information in templates
- Comply with relevant regulations (GDPR, TCPA)

## 9. Production Deployment

### Scaling Considerations
- Use Redis/Celery for high-volume notifications
- Implement proper error handling and retry logic
- Monitor provider rate limits
- Consider multiple SMTP providers for redundancy

### Performance Optimization
- Enable notification queue for async processing
- Cache templates to reduce database load
- Batch notifications where possible
- Monitor and optimize slow queries

## 10. API Integration

The notification system can also be used via API:

```python
# Send notification via API
POST /api/notifications/send
{
    "type": "email",
    "recipient": "customer@example.com",
    "subject": "Test",
    "template": "order_confirmation",
    "context": {"order_id": 123}
}
```

## Support

For issues or questions:
1. Check the application logs
2. Review the notification dashboard
3. Test with the notification test interface
4. Consult the troubleshooting guide above

## Next Steps

1. Configure your environment variables
2. Run the database migration
3. Test notifications with the test interface
4. Customize templates for your brand
5. Monitor the dashboard for delivery status