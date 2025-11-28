"""
License renewal reminder service for Restaurant POS System
Handles automated renewal notifications for expiring licenses
"""

import os
import json
from datetime import datetime, timedelta
from flask import current_app
from app import db
from app.models.license import License, LicenseStatus
from app.models.user import User
from app.models.restaurant import Restaurant


class LicenseRenewalService:
    """Service for managing license renewal reminders"""
    
    def __init__(self):
        self.reminder_intervals = [90, 60, 30, 14, 7, 3, 1]  # Days before expiry
        self.default_email_template = """
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                .header { background: #f97316; color: white; padding: 20px; text-align: center; }
                .content { background: #f9f9f9; padding: 20px; border-radius: 5px; margin: 20px 0; }
                .license-info { background: #e9ecef; padding: 15px; border-radius: 5px; margin: 10px 0; }
                .footer { background: #f8f9fa; padding: 15px; text-align: center; font-size: 12px; color: #666; }
                .btn { display: inline-block; padding: 10px 20px; background: #28a745; color: white; text-decoration: none; border-radius: 5px; margin: 10px 5px; }
                .urgent { color: #dc3545; font-weight: bold; }
                .warning { color: #ffc107; font-weight: bold; }
                .info { color: #17a2b8; font-weight: bold; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>License Renewal Reminder</h1>
                </div>
                <div class="content">
                    <h2>License Expiring Soon</h2>
                    <div class="license-info">
                        <p><strong>License Key:</strong> {license_key}</p>
                        <p><strong>Product:</strong> {product_name}</p>
                        <p><strong>Type:</strong> {license_type}</p>
                        <p><strong>Expires:</strong> {expiry_date}</p>
                        <p><strong>Days Until Expiry:</strong> <span class="{urgency_class}">{days_until_expiry}</span></p>
                        <p><strong>Restaurant:</strong> {restaurant_name}</p>
                        <p><strong>User:</strong> {user_name}</p>
                        {activation_info}
                    </div>
                    <p>Please renew your license before it expires to avoid service interruption.</p>
                    <a href="{renewal_url}" class="btn">Renew License</a>
                </div>
                <div class="footer">
                    <p>This is an automated reminder from Restaurant POS System.</p>
                    <p>If you have questions, please contact your system administrator.</p>
                </div>
            </div>
        </body>
        </html>
        """
    
    def check_expiring_licenses(self):
        """Check for licenses expiring within configured intervals"""
        expiring_licenses = {}
        
        for days in self.reminder_intervals:
            threshold_date = datetime.utcnow() + timedelta(days=days)
            
            # Find licenses expiring in this interval
            licenses = License.query.filter(
                License.expiry_date <= threshold_date,
                License.expiry_date > datetime.utcnow(),
                License.status == LicenseStatus.ACTIVE
            ).all()
            
            if licenses:
                expiring_licenses[days] = licenses
        
        return expiring_licenses
    
    def send_renewal_reminders(self, test_mode=False):
        """Send renewal reminders for expiring licenses"""
        try:
            expiring_licenses = self.check_expiring_licenses()
            
            if not expiring_licenses:
                current_app.logger.info("No licenses expiring soon")
                return {
                    'success': True,
                    'message': 'No licenses expiring soon',
                    'reminders_sent': 0
                }
            
            total_reminders = 0
            
            for days, licenses in expiring_licenses.items():
                for license in licenses:
                    # Check if we already sent a reminder for this interval
                    if not self._should_send_reminder(license, days):
                        continue
                    
                    # Determine urgency based on days until expiry
                    urgency = self._get_urgency(days)
                    
                    # Prepare email content
                    email_content = self._prepare_email_content(license, days, urgency)
                    
                    # Send email
                    if not test_mode:
                        success = self._send_email(license, email_content)
                        if success:
                            total_reminders += 1
                            # Log the reminder
                            self._log_reminder_sent(license, days, urgency)
                        else:
                            current_app.logger.error(f"Failed to send renewal reminder for license {license.license_key}")
                    else:
                        # Test mode - just log what would be sent
                        total_reminders += 1
                        current_app.logger.info(f"TEST MODE: Would send {urgency} reminder for license {license.license_key} expiring in {days} days")
            
            return {
                'success': True,
                'message': f'Sent {total_reminders} renewal reminders',
                'reminders_sent': total_reminders,
                'expiring_counts': {days: len(licenses) for days, licenses in expiring_licenses.items()}
            }
            
        except Exception as e:
            current_app.logger.error(f"Error sending renewal reminders: {str(e)}")
            return {
                'success': False,
                'message': f'Error: {str(e)}',
                'reminders_sent': 0
            }
    
    def _should_send_reminder(self, license, days):
        """Check if we should send a reminder for this license/interval"""
        # Check if we sent a reminder for this interval recently
        from app.models.notification import Notification
        
        recent_notification = Notification.query.filter(
            Notification.type == 'license_renewal',
            Notification.reference_id == str(license.id),
            Notification.reference_type == f'days_{days}',
            Notification.created_at >= datetime.utcnow() - timedelta(days=7)  # Don't send more than once per week
        ).first()
        
        return recent_notification is None
    
    def _get_urgency(self, days):
        """Determine urgency level based on days until expiry"""
        if days <= 7:
            return 'urgent'
        elif days <= 30:
            return 'warning'
        else:
            return 'info'
    
    def _prepare_email_content(self, license, days, urgency):
        """Prepare email content for renewal reminder"""
        # Get license details
        license_type = license.license_type.value if license.license_type else 'Unknown'
        
        # Get user and restaurant info
        user = User.query.get(license.user_id) if license.user_id else None
        restaurant = Restaurant.query.get(license.restaurant_id) if license.restaurant_id else None
        
        # Prepare activation info if available
        activation_info = ""
        if license.current_activations > 0:
            activation_info = f"<p><strong>Current Activations:</strong> {license.current_activations}/{license.max_activations}</p>"
        
        # Determine urgency class for styling
        urgency_class = {
            'urgent': 'urgent',
            'warning': 'warning',
            'info': 'info'
        }.get(urgency, 'info')
        
        # Format dates
        expiry_date = license.expiry_date.strftime('%B %d, %Y') if license.expiry_date else 'Unknown'
        
        # Create renewal URL
        renewal_url = f"{current_app.config.get('BASE_URL', 'http://localhost:5000')}/license/licenses/{license.id}"
        
        # Prepare email content
        email_content = self.default_email_template.format(
            license_key=license.license_key,
            product_name=license.product_name or 'Unknown Product',
            license_type=license_type.title(),
            expiry_date=expiry_date,
            days_until_expiry=days,
            urgency_class=urgency_class,
            restaurant_name=restaurant.name if restaurant else 'Unknown Restaurant',
            user_name=user.name if user else 'Unknown User',
            activation_info=activation_info,
            renewal_url=renewal_url
        )
        
        return {
            'subject': f'License Renewal Reminder: {license.product_name} expires in {days} days',
            'html': email_content,
            'text': self._extract_text_from_html(email_content),
            'urgency': urgency,
            'days': days
        }
    
    def _extract_text_from_html(self, html_content):
        """Extract plain text from HTML content"""
        # Simple text extraction - remove HTML tags
        import re
        text = re.sub('<[^<]+?>', '', html_content)
        return ' '.join(text.split())
    
    def _send_email(self, license, email_content):
        """Send renewal reminder email"""
        try:
            from flask_mail import Message
            
            # Get recipient email
            recipient = self._get_recipient_email(license)
            
            if not recipient:
                current_app.logger.warning(f"No recipient email found for license {license.license_key}")
                return False
            
            # Create message
            msg = Message(
                subject=email_content['subject'],
                recipients=[recipient],
                html=email_content['html'],
                sender=current_app.config.get('MAIL_DEFAULT_SENDER', 'noreply@restaurantpos.com')
            )
            
            # Send email
            from app import mail
            mail.send(msg)
            
            return True
            
        except Exception as e:
            current_app.logger.error(f"Error sending email for license {license.license_key}: {str(e)}")
            return False
    
    def _get_recipient_email(self, license):
        """Get the appropriate recipient email for the license"""
        # Try to get user email first
        if license.user_id:
            user = User.query.get(license.user_id)
            if user and user.email:
                return user.email
        
        # Fall back to restaurant email
        if license.restaurant_id:
            restaurant = Restaurant.query.get(license.restaurant_id)
            if restaurant and restaurant.email:
                return restaurant.email
        
        # Fall back to system admin
        admin_email = current_app.config.get('ADMIN_EMAIL')
        if admin_email:
            return admin_email
        
        return None
    
    def _log_reminder_sent(self, license, days, urgency):
        """Log that a renewal reminder was sent"""
        try:
            from app.models.notification import Notification
            
            notification = Notification(
                type='license_renewal',
                title=f'License Renewal Reminder',
                message=f'Renewal reminder sent for {license.product_name} expiring in {days} days',
                reference_id=str(license.id),
                reference_type=f'days_{days}',
                urgency=urgency,
                user_id=license.user_id,
                restaurant_id=license.restaurant_id,
                is_read=False
            )
            
            db.session.add(notification)
            db.session.commit()
            
        except Exception as e:
            current_app.logger.error(f"Error logging renewal reminder: {str(e)}")
    
    def get_renewal_statistics(self):
        """Get statistics about renewal reminders"""
        try:
            from app.models.notification import Notification
            
            # Get renewal notifications in last 30 days
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            
            renewal_notifications = Notification.query.filter(
                Notification.type == 'license_renewal',
                Notification.created_at >= thirty_days_ago
            ).all()
            
            # Group by urgency
            stats = {
                'total_sent': len(renewal_notifications),
                'by_urgency': {'urgent': 0, 'warning': 0, 'info': 0},
                'by_days': {},
                'recent_licenses': []
            }
            
            for notification in renewal_notifications:
                # Count by urgency
                if notification.urgency in stats['by_urgency']:
                    stats['by_urgency'][notification.urgency] += 1
                
                # Count by days
                if notification.reference_type and notification.reference_type.startswith('days_'):
                    days = notification.reference_type.replace('days_', '')
                    if days not in stats['by_days']:
                        stats['by_days'][days] = 0
                    stats['by_days'][days] += 1
                
                # Track recent licenses
                if notification.reference_id and notification.reference_id not in stats['recent_licenses']:
                    license = License.query.get(int(notification.reference_id))
                    if license:
                        stats['recent_licenses'].append({
                            'id': license.id,
                            'license_key': license.license_key,
                            'product_name': license.product_name,
                            'expiry_date': license.expiry_date.isoformat() if license.expiry_date else None,
                            'days_until_expiry': license.days_until_expiry()
                        })
            
            return stats
            
        except Exception as e:
            current_app.logger.error(f"Error getting renewal statistics: {str(e)}")
            return {
                'total_sent': 0,
                'by_urgency': {'urgent': 0, 'warning': 0, 'info': 0},
                'by_days': {},
                'recent_licenses': []
            }
    
    def schedule_automatic_reminders(self):
        """Schedule automatic renewal reminders using system scheduler"""
        try:
            # This would typically be called by a scheduler like cron or Celery
            return self.send_renewal_reminders()
        except Exception as e:
            current_app.logger.error(f"Error in scheduled renewal reminders: {str(e)}")
            return {
                'success': False,
                'message': f'Error: {str(e)}'
            }
    
    def create_renewal_task(self, license_id, days_before_expiry):
        """Create a scheduled task for specific license renewal"""
        try:
            from app.models.task import ScheduledTask
            
            # Calculate when to send the reminder
            license_obj = License.query.get(license_id)
            if not license_obj or not license_obj.expiry_date:
                return {
                    'success': False,
                    'message': 'License not found or no expiry date'
                }
            
            reminder_date = license_obj.expiry_date - timedelta(days=days_before_expiry)
            
            # Create scheduled task
            task = ScheduledTask(
                task_type='license_renewal_reminder',
                title=f'License Renewal Reminder - {license_obj.product_name}',
                description=f'Send renewal reminder for license {license_obj.license_key}',
                scheduled_at=reminder_date,
                parameters=json.dumps({
                    'license_id': license_id,
                    'days_before_expiry': days_before_expiry
                }),
                is_active=True
            )
            
            db.session.add(task)
            db.session.commit()
            
            return {
                'success': True,
                'message': f'Renewal reminder scheduled for {license_obj.product_name}',
                'reminder_date': reminder_date.isoformat()
            }
            
        except Exception as e:
            current_app.logger.error(f"Error creating renewal task: {str(e)}")
            return {
                'success': False,
                'message': f'Error: {str(e)}'
            }


# Global instance for the service
license_renewal_service = LicenseRenewalService()