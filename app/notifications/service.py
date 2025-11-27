"""
Notification service for handling email and SMS notifications
"""

import os
import logging
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from flask import current_app, render_template
from flask_mail import Mail, Message
import twilio
from twilio.rest import Client
import boto3
from botocore.exceptions import ClientError
from sqlalchemy.exc import SQLAlchemyError

from app import db
from app.models.notification import Notification, NotificationLog, NotificationPreference

# Configure logging
logger = logging.getLogger(__name__)

class NotificationService:
    """Main notification service class"""
    
    def __init__(self, app=None):
        self.app = app
        self.mail = None
        self.twilio_client = None
        self.sns_client = None
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize notification service with Flask app"""
        self.app = app
        
        # Initialize Flask-Mail
        self.mail = Mail(app)
        
        # Initialize Twilio client if configured
        if app.config.get('SMS_PROVIDER') == 'twilio' and app.config.get('SMS_ACCOUNT_SID'):
            try:
                self.twilio_client = Client(
                    app.config.get('SMS_ACCOUNT_SID'),
                    app.config.get('SMS_AUTH_TOKEN')
                )
                logger.info("Twilio client initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Twilio client: {e}")
        
        # Initialize AWS SNS client if configured
        if app.config.get('SMS_PROVIDER') == 'aws_sns':
            try:
                self.sns_client = boto3.client(
                    'sns',
                    aws_access_key_id=app.config.get('SMS_AWS_ACCESS_KEY'),
                    aws_secret_access_key=app.config.get('SMS_AWS_SECRET_KEY'),
                    region_name=app.config.get('SMS_AWS_REGION', 'us-east-1')
                )
                logger.info("AWS SNS client initialized")
            except Exception as e:
                logger.error(f"Failed to initialize AWS SNS client: {e}")
    
    def send_email(self, 
                   to: str, 
                   subject: str, 
                   template: str, 
                   context: Dict[str, Any] = None,
                   cc: List[str] = None,
                   bcc: List[str] = None,
                   attachments: List[str] = None,
                   priority: str = 'normal',
                   send_async: bool = True) -> Optional[Notification]:
        """
        Send email notification
        
        Args:
            to: Recipient email address
            subject: Email subject
            template: Email template name
            context: Template context variables
            cc: CC recipients
            bcc: BCC recipients
            attachments: List of attachment file paths
            priority: Email priority (low, normal, high)
            send_async: Whether to send asynchronously
            
        Returns:
            Notification object if successful, None otherwise
        """
        if not self._is_email_enabled():
            logger.warning("Email notifications are disabled")
            return None
        
        if context is None:
            context = {}
        
        # Create notification record
        notification = Notification(
            type='email',
            recipient=to,
            subject=subject,
            content=template,
            context=context,
            priority=priority,
            status='pending'
        )
        
        try:
            db.session.add(notification)
            db.session.commit()
            
            if send_async:
                # Send email in background thread
                thread = threading.Thread(
                    target=self._send_email_async,
                    args=(notification.id, template, context, cc, bcc, attachments)
                )
                thread.daemon = True
                thread.start()
            else:
                # Send email synchronously
                self._send_email_sync(notification, template, context, cc, bcc, attachments)
            
            return notification
            
        except SQLAlchemyError as e:
            logger.error(f"Database error creating email notification: {e}")
            db.session.rollback()
            return None
    
    def send_sms(self, 
                 to: str, 
                 message: str,
                 context: Dict[str, Any] = None,
                 priority: str = 'normal',
                 send_async: bool = True) -> Optional[Notification]:
        """
        Send SMS notification
        
        Args:
            to: Recipient phone number (E.164 format)
            message: SMS message or template name
            context: Template context variables
            priority: SMS priority (low, normal, high)
            send_async: Whether to send asynchronously
            
        Returns:
            Notification object if successful, None otherwise
        """
        if not self._is_sms_enabled():
            logger.warning("SMS notifications are disabled")
            return None
        
        if context is None:
            context = {}
        
        # Create notification record
        notification = Notification(
            type='sms',
            recipient=to,
            content=message,
            context=context,
            priority=priority,
            status='pending'
        )
        
        try:
            db.session.add(notification)
            db.session.commit()
            
            if send_async:
                # Send SMS in background thread
                thread = threading.Thread(
                    target=self._send_sms_async,
                    args=(notification.id, message, context)
                )
                thread.daemon = True
                thread.start()
            else:
                # Send SMS synchronously
                self._send_sms_sync(notification, message, context)
            
            return notification
            
        except SQLAlchemyError as e:
            logger.error(f"Database error creating SMS notification: {e}")
            db.session.rollback()
            return None
    
    def send_order_receipt(self, order, email: str = None, phone: str = None) -> Dict[str, Optional[Notification]]:
        """
        Send order receipt via email and/or SMS
        
        Args:
            order: Order object
            email: Customer email address
            phone: Customer phone number
            
        Returns:
            Dictionary with email and SMS notification results
        """
        results = {'email': None, 'sms': None}
        
        # Prepare context for templates
        context = {
            'order': order,
            'order_items': order.items,
            'payments': order.payments,
            'restaurant': order.restaurant,
            'current_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # Send email receipt
        if email and self._should_send_email_notification(order, 'order_receipt'):
            results['email'] = self.send_email(
                to=email,
                subject=f"Receipt - Order {order.order_number}",
                template='notifications/email/order_receipt.html',
                context=context,
                priority='high'
            )
        
        # Send SMS receipt
        if phone and self._should_send_sms_notification(order, 'order_receipt'):
            sms_message = f"Your order {order.order_number} is complete. Total: ${order.total:.2f}. Thank you for your purchase!"
            results['sms'] = self.send_sms(
                to=phone,
                message=sms_message,
                context=context,
                priority='high'
            )
        
        return results
    
    def send_order_confirmation(self, order, email: str = None, phone: str = None) -> Dict[str, Optional[Notification]]:
        """
        Send order confirmation via email and/or SMS
        
        Args:
            order: Order object
            email: Customer email address
            phone: Customer phone number
            
        Returns:
            Dictionary with email and SMS notification results
        """
        results = {'email': None, 'sms': None}
        
        # Prepare context for templates
        context = {
            'order': order,
            'order_items': order.items,
            'restaurant': order.restaurant,
            'estimated_time': '15-20 minutes',  # Could be configurable
            'current_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # Send email confirmation
        if email and self._should_send_email_notification(order, 'order_confirmation'):
            results['email'] = self.send_email(
                to=email,
                subject=f"Order Confirmation - {order.order_number}",
                template='notifications/email/order_confirmation.html',
                context=context,
                priority='high'
            )
        
        # Send SMS confirmation
        if phone and self._should_send_sms_notification(order, 'order_confirmation'):
            sms_message = f"Order {order.order_number} confirmed! Estimated time: 15-20 minutes. We'll notify you when ready."
            results['sms'] = self.send_sms(
                to=phone,
                message=sms_message,
                context=context,
                priority='high'
            )
        
        return results
    
    def send_low_stock_alert(self, ingredient, current_stock: float, threshold: float) -> Optional[Notification]:
        """
        Send low stock alert to administrators
        
        Args:
            ingredient: Ingredient object
            current_stock: Current stock quantity
            threshold: Low stock threshold
            
        Returns:
            Notification object if successful, None otherwise
        """
        context = {
            'ingredient': ingredient,
            'current_stock': current_stock,
            'threshold': threshold,
            'shortage': threshold - current_stock,
            'alert_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # Get admin emails
        admin_emails = self._get_admin_emails()
        if not admin_emails:
            logger.warning("No admin emails configured for low stock alerts")
            return None
        
        return self.send_email(
            to=admin_emails,
            subject=f"Low Stock Alert: {ingredient.name}",
            template='notifications/email/low_stock_alert.html',
            context=context,
            priority='high'
        )
    
    def send_license_renewal_reminder(self, license_obj, days_until_expiry: int) -> Optional[Notification]:
        """
        Send license renewal reminder
        
        Args:
            license_obj: License object
            days_until_expiry: Days until license expires
            
        Returns:
            Notification object if successful, None otherwise
        """
        context = {
            'license': license_obj,
            'days_until_expiry': days_until_expiry,
            'expiry_date': license_obj.expiry_date.strftime('%Y-%m-%d'),
            'renewal_url': 'https://your-domain.com/license/renew',  # Update with actual URL
            'reminder_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # Get admin emails
        admin_emails = self._get_admin_emails()
        if not admin_emails:
            logger.warning("No admin emails configured for license renewal reminders")
            return None
        
        priority = 'high' if days_until_expiry <= 7 else 'normal'
        
        return self.send_email(
            to=admin_emails,
            subject=f"License Renewal Reminder: {license_obj.license_type}",
            template='notifications/email/license_renewal_reminder.html',
            context=context,
            priority=priority
        )
    
    def _send_email_async(self, notification_id: int, template: str, context: Dict[str, Any], 
                         cc: List[str] = None, bcc: List[str] = None, 
                         attachments: List[str] = None):
        """Send email asynchronously"""
        with self.app.app_context():
            try:
                notification = Notification.query.get(notification_id)
                if not notification:
                    logger.error(f"Notification {notification_id} not found")
                    return
                
                self._send_email_sync(notification, template, context, cc, bcc, attachments)
                
            except Exception as e:
                logger.error(f"Error sending email asynchronously: {e}")
                if 'notification' in locals():
                    self._mark_notification_failed(notification, str(e))
    
    def _send_email_sync(self, notification: Notification, template: str, context: Dict[str, Any],
                        cc: List[str] = None, bcc: List[str] = None, 
                        attachments: List[str] = None):
        """Send email synchronously"""
        try:
            # Render email template
            html_content = render_template(template, **context)
            
            # Create email message
            msg = Message(
                subject=notification.subject,
                sender=current_app.config.get('MAIL_DEFAULT_SENDER'),
                recipients=[notification.recipient],
                cc=cc or [],
                bcc=bcc or []
            )
            
            msg.html = html_content
            
            # Add attachments if provided
            if attachments:
                for attachment_path in attachments:
                    if os.path.exists(attachment_path):
                        with current_app.open_resource(attachment_path) as fp:
                            msg.attach(
                                os.path.basename(attachment_path),
                                'application/octet-stream',
                                fp.read()
                            )
            
            # Send email
            self.mail.send(msg)
            
            # Update notification status
            notification.status = 'sent'
            notification.sent_at = datetime.utcnow()
            db.session.commit()
            
            # Log successful delivery
            self._log_notification_delivery(notification, 'email', 'success')
            
            logger.info(f"Email sent successfully to {notification.recipient}")
            
        except Exception as e:
            logger.error(f"Error sending email to {notification.recipient}: {e}")
            self._mark_notification_failed(notification, str(e))
            self._log_notification_delivery(notification, 'email', 'failed', str(e))
    
    def _send_sms_async(self, notification_id: int, message: str, context: Dict[str, Any]):
        """Send SMS asynchronously"""
        with self.app.app_context():
            try:
                notification = Notification.query.get(notification_id)
                if not notification:
                    logger.error(f"Notification {notification_id} not found")
                    return
                
                self._send_sms_sync(notification, message, context)
                
            except Exception as e:
                logger.error(f"Error sending SMS asynchronously: {e}")
                if 'notification' in locals():
                    self._mark_notification_failed(notification, str(e))
    
    def _send_sms_sync(self, notification: Notification, message: str, context: Dict[str, Any]):
        """Send SMS synchronously"""
        try:
            # Render message template if it's a template name
            if message.endswith('.html') or message.endswith('.txt'):
                rendered_message = render_template(f'notifications/sms/{message}', **context)
            else:
                rendered_message = message
            
            success = False
            error_message = None
            
            # Send via Twilio
            if self.app.config.get('SMS_PROVIDER') == 'twilio' and self.twilio_client:
                try:
                    twilio_message = self.twilio_client.messages.create(
                        body=rendered_message,
                        from_=self.app.config.get('SMS_FROM_NUMBER'),
                        to=notification.recipient
                    )
                    success = True
                    logger.info(f"SMS sent via Twilio to {notification.recipient}")
                    
                except twilio.base.exceptions.TwilioRestException as e:
                    error_message = f"Twilio error: {e}"
                    logger.error(error_message)
            
            # Send via AWS SNS
            elif self.app.config.get('SMS_PROVIDER') == 'aws_sns' and self.sns_client:
                try:
                    self.sns_client.publish(
                        PhoneNumber=notification.recipient,
                        Message=rendered_message
                    )
                    success = True
                    logger.info(f"SMS sent via AWS SNS to {notification.recipient}")
                    
                except ClientError as e:
                    error_message = f"AWS SNS error: {e}"
                    logger.error(error_message)
            
            else:
                error_message = "No SMS provider configured"
                logger.error(error_message)
            
            # Update notification status
            if success:
                notification.status = 'sent'
                notification.sent_at = datetime.utcnow()
                self._log_notification_delivery(notification, 'sms', 'success')
            else:
                self._mark_notification_failed(notification, error_message or 'Unknown error')
                self._log_notification_delivery(notification, 'sms', 'failed', error_message)
            
            db.session.commit()
            
        except Exception as e:
            logger.error(f"Error sending SMS to {notification.recipient}: {e}")
            self._mark_notification_failed(notification, str(e))
            self._log_notification_delivery(notification, 'sms', 'failed', str(e))
    
    def _mark_notification_failed(self, notification: Notification, error_message: str):
        """Mark notification as failed"""
        notification.status = 'failed'
        notification.error_message = error_message
        notification.failed_at = datetime.utcnow()
        db.session.commit()
    
    def _log_notification_delivery(self, notification: Notification, channel: str, status: str, error_message: str = None):
        """Log notification delivery attempt"""
        log_entry = NotificationLog(
            notification_id=notification.id,
            channel=channel,
            status=status,
            error_message=error_message,
            attempt_at=datetime.utcnow()
        )
        db.session.add(log_entry)
        db.session.commit()
    
    def _is_email_enabled(self) -> bool:
        """Check if email notifications are enabled"""
        return (current_app.config.get('ENABLE_EMAIL_NOTIFICATIONS', True) and 
                current_app.config.get('MAIL_SERVER') and 
                current_app.config.get('MAIL_USERNAME') and 
                current_app.config.get('MAIL_PASSWORD'))
    
    def _is_sms_enabled(self) -> bool:
        """Check if SMS notifications are enabled"""
        return (current_app.config.get('ENABLE_SMS_NOTIFICATIONS', False) and
                ((current_app.config.get('SMS_PROVIDER') == 'twilio' and 
                  current_app.config.get('SMS_ACCOUNT_SID') and 
                  current_app.config.get('SMS_AUTH_TOKEN')) or
                 (current_app.config.get('SMS_PROVIDER') == 'aws_sns' and 
                  current_app.config.get('SMS_AWS_ACCESS_KEY') and 
                  current_app.config.get('SMS_AWS_SECRET_KEY'))))
    
    def _should_send_email_notification(self, order, notification_type: str) -> bool:
        """Check if email notification should be sent based on preferences"""
        # Check if customer has email preferences
        preference = NotificationPreference.query.filter_by(
            order_id=order.id,
            notification_type=notification_type,
            channel='email'
        ).first()
        
        # If preference exists and is disabled, don't send
        if preference and not preference.is_enabled:
            return False
        
        # Default to enabled if no preference exists
        return True
    
    def _should_send_sms_notification(self, order, notification_type: str) -> bool:
        """Check if SMS notification should be sent based on preferences"""
        # Check if customer has SMS preferences
        preference = NotificationPreference.query.filter_by(
            order_id=order.id,
            notification_type=notification_type,
            channel='sms'
        ).first()
        
        # If preference exists and is disabled, don't send
        if preference and not preference.is_enabled:
            return False
        
        # Default to enabled if no preference exists
        return True
    
    def _get_admin_emails(self) -> List[str]:
        """Get list of admin email addresses"""
        from app.models.user import User
        admins = User.query.filter_by(is_admin=True).all()
        return [admin.email for admin in admins if admin.email]

# Create global notification service instance
notification_service = NotificationService()