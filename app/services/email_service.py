"""
Email Service for POS Application

This service handles email communications including:
- Invoice emails
- Order notifications
- Password reset emails
- System notifications
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime
import logging
from flask import current_app, render_template, url_for
import os

logger = logging.getLogger(__name__)

class EmailService:
    """Service for sending emails"""
    
    def __init__(self):
        """Initialize email service with configuration"""
        self.smtp_server = current_app.config.get('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = current_app.config.get('SMTP_PORT', 587)
        self.smtp_username = current_app.config.get('SMTP_USERNAME')
        self.smtp_password = current_app.config.get('SMTP_PASSWORD')
        self.from_email = current_app.config.get('FROM_EMAIL', self.smtp_username)
        self.from_name = current_app.config.get('FROM_NAME', 'POS System')
        self.use_tls = current_app.config.get('SMTP_USE_TLS', True)
    
    def send_invoice_email(self, recipient_email, invoice_number, amount, due_date, invoice_url, customer_name):
        """Send invoice email to customer"""
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"Invoice #{invoice_number} from {self.from_name}"
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = recipient_email
            
            # Render email template
            html_content = render_template('emails/invoice.html', 
                                        invoice_number=invoice_number,
                                        amount=amount,
                                        due_date=due_date,
                                        invoice_url=invoice_url,
                                        customer_name=customer_name,
                                        company_name=self.from_name)
            
            text_content = render_template('emails/invoice.txt', 
                                       invoice_number=invoice_number,
                                       amount=amount,
                                       due_date=due_date,
                                       invoice_url=invoice_url,
                                       customer_name=customer_name,
                                       company_name=self.from_name)
            
            # Attach parts
            msg.attach(MIMEText(text_content, 'plain'))
            msg.attach(MIMEText(html_content, 'html'))
            
            # Send email
            result = self._send_email(msg, recipient_email)
            
            return result
            
        except Exception as e:
            logger.error(f"Error creating invoice email: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def send_order_confirmation(self, recipient_email, order_number, order_details, customer_name):
        """Send order confirmation email"""
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"Order Confirmation #{order_number}"
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = recipient_email
            
            html_content = render_template('emails/order_confirmation.html',
                                        order_number=order_number,
                                        order_details=order_details,
                                        customer_name=customer_name)
            
            text_content = render_template('emails/order_confirmation.txt',
                                       order_number=order_number,
                                       order_details=order_details,
                                       customer_name=customer_name)
            
            msg.attach(MIMEText(text_content, 'plain'))
            msg.attach(MIMEText(html_content, 'html'))
            
            return self._send_email(msg, recipient_email)
            
        except Exception as e:
            logger.error(f"Error creating order confirmation email: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def send_password_reset(self, recipient_email, reset_token, user_name):
        """Send password reset email"""
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = "Password Reset Request"
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = recipient_email
            
            reset_url = url_for('auth.reset_password', token=reset_token, _external=True)
            
            html_content = render_template('emails/password_reset.html',
                                        reset_url=reset_url,
                                        user_name=user_name,
                                        company_name=self.from_name)
            
            text_content = render_template('emails/password_reset.txt',
                                       reset_url=reset_url,
                                       user_name=user_name,
                                       company_name=self.from_name)
            
            msg.attach(MIMEText(text_content, 'plain'))
            msg.attach(MIMEText(html_content, 'html'))
            
            return self._send_email(msg, recipient_email)
            
        except Exception as e:
            logger.error(f"Error creating password reset email: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def send_low_stock_alert(self, recipient_email, low_stock_items):
        """Send low stock alert to manager"""
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = "Low Stock Alert"
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = recipient_email
            
            html_content = render_template('emails/low_stock_alert.html',
                                        low_stock_items=low_stock_items,
                                        company_name=self.from_name)
            
            text_content = render_template('emails/low_stock_alert.txt',
                                       low_stock_items=low_stock_items,
                                       company_name=self.from_name)
            
            msg.attach(MIMEText(text_content, 'plain'))
            msg.attach(MIMEText(html_content, 'html'))
            
            return self._send_email(msg, recipient_email)
            
        except Exception as e:
            logger.error(f"Error creating low stock alert email: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def send_daily_report(self, recipient_email, report_data):
        """Send daily report email"""
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"Daily Report - {datetime.now().strftime('%Y-%m-%d')}"
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = recipient_email
            
            html_content = render_template('emails/daily_report.html',
                                        report_data=report_data,
                                        company_name=self.from_name)
            
            text_content = render_template('emails/daily_report.txt',
                                       report_data=report_data,
                                       company_name=self.from_name)
            
            msg.attach(MIMEText(text_content, 'plain'))
            msg.attach(MIMEText(html_content, 'html'))
            
            return self._send_email(msg, recipient_email)
            
        except Exception as e:
            logger.error(f"Error creating daily report email: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _send_email(self, message, recipient_email):
        """Send email using SMTP"""
        try:
            # Check if SMTP configuration is available
            if not all([self.smtp_server, self.smtp_username, self.smtp_password]):
                return {'success': False, 'error': 'SMTP configuration missing'}
            
            # Ensure from_email is not None
            from_email = self.from_email or self.smtp_username
            if not from_email:
                return {'success': False, 'error': 'From email address not configured'}
            
            # Create SMTP session
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            
            if self.use_tls:
                server.starttls()
            
            # Login and send with proper type checking
            if not self.smtp_username or not self.smtp_password:
                return {'success': False, 'error': 'SMTP credentials not configured'}
            
            server.login(self.smtp_username, self.smtp_password)
            text = message.as_string()
            server.sendmail(from_email, recipient_email, text)
            server.quit()
            
            logger.info(f"Email sent successfully to {recipient_email}")
            return {'success': True}
            
        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"SMTP authentication failed: {str(e)}")
            return {'success': False, 'error': 'SMTP authentication failed'}
        except smtplib.SMTPException as e:
            logger.error(f"SMTP error: {str(e)}")
            return {'success': False, 'error': f'SMTP error: {str(e)}'}
        except Exception as e:
            logger.error(f"Error sending email: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def test_email_configuration(self):
        """Test email configuration"""
        try:
            # Ensure we have a valid from email for testing
            test_email = self.from_email or self.smtp_username
            if not test_email:
                return {'success': False, 'error': 'No email address configured for testing'}
            
            test_msg = MIMEMultipart()
            test_msg['Subject'] = "Email Configuration Test"
            test_msg['From'] = f"{self.from_name} <{test_email}>"
            test_msg['To'] = test_email
            test_msg.attach(MIMEText("This is a test email to verify the email configuration.", 'plain'))
            
            return self._send_email(test_msg, test_email)
            
        except Exception as e:
            logger.error(f"Email configuration test failed: {str(e)}")
            return {'success': False, 'error': str(e)}

# Email template functions
def create_invoice_template():
    """Create invoice email template"""
    template_dir = os.path.join(current_app.root_path, 'templates', 'emails')
    os.makedirs(template_dir, exist_ok=True)
    
    html_template = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Invoice #{{ invoice_number }}</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { border-bottom: 2px solid #007bff; padding-bottom: 20px; margin-bottom: 20px; }
        .invoice-details { background: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0; }
        .btn { display: inline-block; padding: 12px 24px; background: #007bff; color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }
        .footer { border-top: 1px solid #eee; padding-top: 20px; margin-top: 30px; font-size: 12px; color: #666; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Invoice #{{ invoice_number }}</h1>
            <p>Hello {{ customer_name }},</p>
            <p>Thank you for your business. Please find your invoice details below.</p>
        </div>
        
        <div class="invoice-details">
            <h3>Invoice Details</h3>
            <p><strong>Invoice Number:</strong> #{{ invoice_number }}</p>
            <p><strong>Amount Due:</strong> ₹{{ "%.2f"|format(amount) }}</p>
            <p><strong>Due Date:</strong> {{ due_date.strftime('%d %B %Y') if due_date else 'Due on receipt' }}</p>
        </div>
        
        <p>To view your complete invoice and make payment, please click the button below:</p>
        
        <a href="{{ invoice_url }}" class="btn">View Invoice</a>
        
        <p>If you have any questions, please don't hesitate to contact us.</p>
        
        <div class="footer">
            <p>Best regards,<br>{{ company_name }} Team</p>
            <p>This is an automated message. Please do not reply to this email.</p>
        </div>
    </div>
</body>
</html>
    """
    
    text_template = """
Invoice #{{ invoice_number }}

Hello {{ customer_name }},

Thank you for your business. Please find your invoice details below.

Invoice Details:
Invoice Number: #{{ invoice_number }}
Amount Due: ₹{{ "%.2f"|format(amount) }}
Due Date: {{ due_date.strftime('%d %B %Y') if due_date else 'Due on receipt' }}

To view your complete invoice and make payment, please visit:
{{ invoice_url }}

If you have any questions, please don't hesitate to contact us.

Best regards,
{{ company_name }} Team

This is an automated message. Please do not reply to this email.
    """
    
    with open(os.path.join(template_dir, 'invoice.html'), 'w') as f:
        f.write(html_template)
    
    with open(os.path.join(template_dir, 'invoice.txt'), 'w') as f:
        f.write(text_template)

# Initialize email templates
def init_email_templates():
    """Initialize email templates if they don't exist"""
    try:
        create_invoice_template()
        logger.info("Email templates initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize email templates: {str(e)}")
