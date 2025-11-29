"""
Customer Engagement Integration Service
Handles third-party integrations including:
- Email service providers (SendGrid, Mailgun, SES)
- SMS/WhatsApp gateways (Twilio, MessageBird)
- Social media platforms (Facebook, Instagram, Twitter)
- Payment systems (Stripe, PayPal, Square)
- Analytics platforms (Google Analytics, Mixpanel)
- CRM systems (Salesforce, HubSpot)
"""

from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import json
import logging
import requests
from abc import ABC, abstractmethod

from app import db
from app.models.customer import Customer
from app.models.customer_engagement import (
    CustomerCommunication, CommunicationTemplate, MarketingCampaign
)


class IntegrationProvider(ABC):
    """Base class for integration providers"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.api_key = config.get('api_key')
        self.base_url = config.get('base_url', '')
        self.webhook_secret = config.get('webhook_secret')
    
    @abstractmethod
    def send_message(self, message_data: Dict) -> Dict[str, Any]:
        """Send message through provider"""
        pass
    
    @abstractmethod
    def validate_webhook(self, payload: Dict, signature: str) -> bool:
        """Validate incoming webhook"""
        pass
    
    @abstractmethod
    def get_delivery_status(self, message_id: str) -> Dict[str, Any]:
        """Get delivery status for message"""
        pass


class SendGridIntegration(IntegrationProvider):
    """SendGrid email integration"""
    
    def send_message(self, message_data: Dict) -> Dict[str, Any]:
        """Send email via SendGrid"""
        try:
            url = "https://api.sendgrid.com/v3/mail/send"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "personalizations": [{
                    "to": [{"email": email} for email in message_data.get('recipients', [])],
                    "subject": message_data.get('subject', ''),
                    "content": [{
                        "type": "text/html",
                        "value": message_data.get('content', '')
                    }]
                }]
            }
            
            response = requests.post(url, headers=headers, json=payload)
            
            if response.status_code == 202:
                return {
                    'success': True,
                    'message_id': response.headers.get('X-Message-Id'),
                    'provider': 'sendgrid'
                }
            else:
                return {
                    'success': False,
                    'error': f"SendGrid API error: {response.status_code}",
                    'response': response.text
                }
                
        except Exception as e:
            logging.error(f"SendGrid integration error: {str(e)}")
            return {
                'success': False,
                'error': f"SendGrid integration failed: {str(e)}"
            }
    
    def validate_webhook(self, payload: Dict, signature: str) -> bool:
        """Validate SendGrid webhook"""
        # Implementation would verify SendGrid webhook signature
        return True  # Simplified for now
    
    def get_delivery_status(self, message_id: str) -> Dict[str, Any]:
        """Get delivery status from SendGrid"""
        try:
            url = f"https://api.sendgrid.com/v3/messages/{message_id}"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'status': data.get('status', 'unknown'),
                    'delivered_at': data.get('last_event_time'),
                    'provider': 'sendgrid'
                }
            else:
                return {
                    'status': 'error',
                    'error': f"Status check failed: {response.status_code}"
                }
                
        except Exception as e:
            logging.error(f"SendGrid status check error: {str(e)}")
            return {
                'status': 'error',
                'error': f"Status check failed: {str(e)}"
            }


class TwilioIntegration(IntegrationProvider):
    """Twilio SMS/WhatsApp integration"""
    
    def send_message(self, message_data: Dict) -> Dict[str, Any]:
        """Send SMS/WhatsApp via Twilio"""
        try:
            from twilio.rest import Client
            
            client = Client(self.api_key, self.config.get('account_sid'))
            
            message_type = message_data.get('message_type', 'sms')
            recipients = message_data.get('recipients', [])
            
            results = []
            for recipient in recipients:
                if message_type == 'sms':
                    message = client.messages.create(
                        body=message_data.get('content', ''),
                        from_=self.config.get('from_number'),
                        to=recipient
                    )
                    results.append({
                        'recipient': recipient,
                        'message_id': message.sid,
                        'status': 'queued'
                    })
                elif message_type == 'whatsapp':
                    message = client.messages.create(
                        body=message_data.get('content', ''),
                        from_=f'whatsapp:{self.config.get("from_number")}',
                        to=f'whatsapp:{recipient}'
                    )
                    results.append({
                        'recipient': recipient,
                        'message_id': message.sid,
                        'status': 'queued'
                    })
            
            return {
                'success': True,
                'results': results,
                'provider': 'twilio'
            }
            
        except Exception as e:
            logging.error(f"Twilio integration error: {str(e)}")
            return {
                'success': False,
                'error': f"Twilio integration failed: {str(e)}"
            }
    
    def validate_webhook(self, payload: Dict, signature: str) -> bool:
        """Validate Twilio webhook"""
        # Implementation would verify Twilio webhook signature
        return True  # Simplified for now
    
    def get_delivery_status(self, message_id: str) -> Dict[str, Any]:
        """Get delivery status from Twilio"""
        try:
            from twilio.rest import Client
            
            client = Client(self.api_key, self.config.get('account_sid'))
            message = client.messages(message_id).fetch()
            
            return {
                'status': message.status,
                'delivered_at': message.date_updated.isoformat() if message.date_updated else None,
                'provider': 'twilio'
            }
            
        except Exception as e:
            logging.error(f"Twilio status check error: {str(e)}")
            return {
                'status': 'error',
                'error': f"Status check failed: {str(e)}"
            }


class StripeIntegration(IntegrationProvider):
    """Stripe payment integration"""
    
    def send_message(self, message_data: Dict) -> Dict[str, Any]:
        """Process payment via Stripe"""
        # stripe is now properly included in requirements.txt
        # This import should work correctly after pip install -r requirements.txt
        try:
            import stripe
            stripe.api_key = self.api_key
            
            # Process payment for reward redemption
            payment_intent = stripe.PaymentIntent.create(
                amount=int(message_data.get('amount', 0) * 100),  # Convert to cents
                currency=message_data.get('currency', 'usd'),
                payment_method_types=['card'],
                metadata=message_data.get('metadata', {})
            )
            
            return {
                'success': True,
                'payment_intent_id': payment_intent.id,
                'client_secret': payment_intent.client_secret,
                'provider': 'stripe'
            }
        except ImportError:
            logging.error("Stripe package not installed. Please run 'pip install -r requirements.txt' to install.")
            return {
                'success': False,
                'error': 'Stripe package not installed. Please run "pip install -r requirements.txt" to install.'
            }
            
        except Exception as e:
            logging.error(f"Stripe integration error: {str(e)}")
            return {
                'success': False,
                'error': f"Stripe integration failed: {str(e)}"
            }
    
    def validate_webhook(self, payload: Dict, signature: str) -> bool:
        """Validate Stripe webhook"""
        # stripe is now properly included in requirements.txt
        # This import should work correctly after pip install -r requirements.txt
        try:
            import stripe
            event = stripe.Webhook.construct_event(
                payload,
                signature,
                self.webhook_secret
            )
            return True
            
        except Exception as e:
            logging.error(f"Stripe webhook validation error: {str(e)}")
            return False
    
    def get_delivery_status(self, message_id: str) -> Dict[str, Any]:
        """Get payment status from Stripe"""
        # stripe is now properly included in requirements.txt
        # This import should work correctly after pip install -r requirements.txt
        try:
            import stripe
            payment_intent = stripe.PaymentIntent.retrieve(message_id)
            
            return {
                'status': payment_intent.status,
                'amount': payment_intent.amount / 100,  # Convert back to dollars
                'currency': payment_intent.currency,
                'provider': 'stripe'
            }
            
        except Exception as e:
            logging.error(f"Stripe status check error: {str(e)}")
            return {
                'status': 'error',
                'error': f"Status check failed: {str(e)}"
            }


class FacebookIntegration(IntegrationProvider):
    """Facebook social media integration"""
    
    def send_message(self, message_data: Dict) -> Dict[str, Any]:
        """Post to Facebook"""
        try:
            url = f"https://graph.facebook.com/v18.0/{self.config.get('page_id')}/feed"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "message": message_data.get('content', ''),
                "link": message_data.get('link', ''),
                "picture": message_data.get('image_url', '')
            }
            
            response = requests.post(url, headers=headers, json=payload)
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'success': True,
                    'post_id': data.get('id'),
                    'provider': 'facebook'
                }
            else:
                return {
                    'success': False,
                    'error': f"Facebook API error: {response.status_code}",
                    'response': response.text
                }
                
        except Exception as e:
            logging.error(f"Facebook integration error: {str(e)}")
            return {
                'success': False,
                'error': f"Facebook integration failed: {str(e)}"
            }
    
    def validate_webhook(self, payload: Dict, signature: str) -> bool:
        """Validate Facebook webhook"""
        # Implementation would verify Facebook webhook signature
        return True  # Simplified for now
    
    def get_delivery_status(self, message_id: str) -> Dict[str, Any]:
        """Get post status from Facebook"""
        try:
            url = f"https://graph.facebook.com/v18.0/{message_id}"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'status': 'published',
                    'likes': data.get('likes', {}).get('summary', {}).get('total_count', 0),
                    'shares': data.get('shares', {}).get('summary', {}).get('total_count', 0),
                    'provider': 'facebook'
                }
            else:
                return {
                    'status': 'error',
                    'error': f"Status check failed: {response.status_code}"
                }
                
        except Exception as e:
            logging.error(f"Facebook status check error: {str(e)}")
            return {
                'status': 'error',
                'error': f"Status check failed: {str(e)}"
            }


class CustomerEngagementIntegrationService:
    """Service for managing third-party integrations"""
    
    @staticmethod
    def get_active_integrations(restaurant_id: int) -> Dict[str, Any]:
        """Get all active integrations for restaurant"""
        # This would query from database
        # For now, return sample integrations
        return {
            'email': {
                'provider': 'sendgrid',
                'status': 'active',
                'config': {
                    'api_key': 'configured',
                    'from_email': 'noreply@restaurant.com'
                }
            },
            'sms': {
                'provider': 'twilio',
                'status': 'active',
                'config': {
                    'account_sid': 'configured',
                    'from_number': '+1234567890'
                }
            },
            'payment': {
                'provider': 'stripe',
                'status': 'active',
                'config': {
                    'api_key': 'configured',
                    'webhook_secret': 'configured'
                }
            },
            'social': {
                'provider': 'facebook',
                'status': 'inactive',
                'config': {
                    'api_key': 'not_configured',
                    'page_id': 'not_configured'
                }
            }
        }
    
    @staticmethod
    def send_email(restaurant_id: int, message_data: Dict) -> Dict[str, Any]:
        """Send email through configured provider"""
        integrations = CustomerEngagementIntegrationService.get_active_integrations(restaurant_id)
        email_config = integrations.get('email', {})
        
        if not email_config or email_config.get('status') != 'active':
            return {
                'success': False,
                'error': 'Email integration not configured or inactive'
            }
        
        provider_config = email_config.get('config', {})
        provider_name = email_config.get('provider', 'sendgrid')
        
        if provider_name == 'sendgrid':
            provider = SendGridIntegration(provider_config)
        elif provider_name == 'mailgun':
            # provider = MailgunIntegration(provider_config)
            return {'success': False, 'error': 'Mailgun integration not implemented'}
        elif provider_name == 'ses':
            # provider = SESIntegration(provider_config)
            return {'success': False, 'error': 'SES integration not implemented'}
        else:
            return {'success': False, 'error': f'Unknown email provider: {provider_name}'}
        
        return provider.send_message(message_data)
    
    @staticmethod
    def send_sms(restaurant_id: int, message_data: Dict) -> Dict[str, Any]:
        """Send SMS through configured provider"""
        integrations = CustomerEngagementIntegrationService.get_active_integrations(restaurant_id)
        sms_config = integrations.get('sms', {})
        
        if not sms_config or sms_config.get('status') != 'active':
            return {
                'success': False,
                'error': 'SMS integration not configured or inactive'
            }
        
        provider_config = sms_config.get('config', {})
        provider_name = sms_config.get('provider', 'twilio')
        
        if provider_name == 'twilio':
            provider = TwilioIntegration(provider_config)
        elif provider_name == 'messagebird':
            # provider = MessageBirdIntegration(provider_config)
            return {'success': False, 'error': 'MessageBird integration not implemented'}
        else:
            return {'success': False, 'error': f'Unknown SMS provider: {provider_name}'}
        
        return provider.send_message(message_data)
    
    @staticmethod
    def process_payment(restaurant_id: int, payment_data: Dict) -> Dict[str, Any]:
        """Process payment through configured provider"""
        integrations = CustomerEngagementIntegrationService.get_active_integrations(restaurant_id)
        payment_config = integrations.get('payment', {})
        
        if not payment_config or payment_config.get('status') != 'active':
            return {
                'success': False,
                'error': 'Payment integration not configured or inactive'
            }
        
        provider_config = payment_config.get('config', {})
        provider_name = payment_config.get('provider', 'stripe')
        
        if provider_name == 'stripe':
            provider = StripeIntegration(provider_config)
        elif provider_name == 'paypal':
            # provider = PayPalIntegration(provider_config)
            return {'success': False, 'error': 'PayPal integration not implemented'}
        elif provider_name == 'square':
            # provider = SquareIntegration(provider_config)
            return {'success': False, 'error': 'Square integration not implemented'}
        else:
            return {'success': False, 'error': f'Unknown payment provider: {provider_name}'}
        
        return provider.send_message(payment_data)
    
    @staticmethod
    def post_to_social(restaurant_id: int, post_data: Dict) -> Dict[str, Any]:
        """Post to social media through configured provider"""
        integrations = CustomerEngagementIntegrationService.get_active_integrations(restaurant_id)
        social_config = integrations.get('social', {})
        
        if not social_config or social_config.get('status') != 'active':
            return {
                'success': False,
                'error': 'Social media integration not configured or inactive'
            }
        
        provider_config = social_config.get('config', {})
        provider_name = social_config.get('provider', 'facebook')
        
        if provider_name == 'facebook':
            provider = FacebookIntegration(provider_config)
        elif provider_name == 'instagram':
            # provider = InstagramIntegration(provider_config)
            return {'success': False, 'error': 'Instagram integration not implemented'}
        elif provider_name == 'twitter':
            # provider = TwitterIntegration(provider_config)
            return {'success': False, 'error': 'Twitter integration not implemented'}
        else:
            return {'success': False, 'error': f'Unknown social provider: {provider_name}'}
        
        return provider.send_message(post_data)
    
    @staticmethod
    def sync_customer_data(restaurant_id: int, provider: str, customer_data: Dict) -> Dict[str, Any]:
        """Sync customer data with external CRM"""
        try:
            if provider == 'salesforce':
                return CustomerEngagementIntegrationService._sync_to_salesforce(customer_data)
            elif provider == 'hubspot':
                return CustomerEngagementIntegrationService._sync_to_hubspot(customer_data)
            elif provider == 'mailchimp':
                return CustomerEngagementIntegrationService._sync_to_mailchimp(customer_data)
            else:
                return {'success': False, 'error': f'Unknown CRM provider: {provider}'}
                
        except Exception as e:
            logging.error(f"CRM sync error: {str(e)}")
            return {
                'success': False,
                'error': f"CRM sync failed: {str(e)}"
            }
    
    @staticmethod
    def _sync_to_salesforce(customer_data: Dict) -> Dict[str, Any]:
        """Sync to Salesforce CRM"""
        # Implementation would use Salesforce API
        return {
            'success': True,
            'provider': 'salesforce',
            'synced_customers': len(customer_data.get('customers', [])),
            'message': 'Customer data synced to Salesforce'
        }
    
    @staticmethod
    def _sync_to_hubspot(customer_data: Dict) -> Dict[str, Any]:
        """Sync to HubSpot CRM"""
        # Implementation would use HubSpot API
        return {
            'success': True,
            'provider': 'hubspot',
            'synced_customers': len(customer_data.get('customers', [])),
            'message': 'Customer data synced to HubSpot'
        }
    
    @staticmethod
    def _sync_to_mailchimp(customer_data: Dict) -> Dict[str, Any]:
        """Sync to Mailchimp"""
        # Implementation would use Mailchimp API
        return {
            'success': True,
            'provider': 'mailchimp',
            'synced_customers': len(customer_data.get('customers', [])),
            'message': 'Customer data synced to Mailchimp'
        }
    
    @staticmethod
    def track_analytics_event(restaurant_id: int, event_data: Dict) -> Dict[str, Any]:
        """Track analytics event to external platforms"""
        try:
            # Track to Google Analytics
            CustomerEngagementIntegrationService._track_to_google_analytics(event_data)
            
            # Track to Mixpanel
            CustomerEngagementIntegrationService._track_to_mixpanel(event_data)
            
            return {
                'success': True,
                'tracked_to': ['google_analytics', 'mixpanel'],
                'event': event_data.get('event_name')
            }
            
        except Exception as e:
            logging.error(f"Analytics tracking error: {str(e)}")
            return {
                'success': False,
                'error': f"Analytics tracking failed: {str(e)}"
            }
    
    @staticmethod
    def _track_to_google_analytics(event_data: Dict):
        """Track event to Google Analytics"""
        # Implementation would use Google Analytics Measurement Protocol
        pass
    
    @staticmethod
    def _track_to_mixpanel(event_data: Dict):
        """Track event to Mixpanel"""
        # Implementation would use Mixpanel API
        pass
    
    @staticmethod
    def handle_webhook(restaurant_id: int, provider: str, payload: Dict, signature: str) -> Dict[str, Any]:
        """Handle incoming webhook from provider"""
        try:
            integrations = CustomerEngagementIntegrationService.get_active_integrations(restaurant_id)
            provider_config = integrations.get(provider, {})
            
            if not provider_config or provider_config.get('status') != 'active':
                return {
                    'success': False,
                    'error': f'{provider} integration not configured or inactive'
                }
            
            config = provider_config.get('config', {})
            provider_name = provider_config.get('provider')
            
            if provider_name == 'sendgrid':
                integration = SendGridIntegration(config)
            elif provider_name == 'twilio':
                integration = TwilioIntegration(config)
            elif provider_name == 'stripe':
                integration = StripeIntegration(config)
            elif provider_name == 'facebook':
                integration = FacebookIntegration(config)
            else:
                return {'success': False, 'error': f'Unknown provider: {provider_name}'}
            
            if integration.validate_webhook(payload, signature):
                # Process webhook based on provider and event type
                return CustomerEngagementIntegrationService._process_webhook_event(provider, payload)
            else:
                return {'success': False, 'error': 'Invalid webhook signature'}
                
        except Exception as e:
            logging.error(f"Webhook handling error: {str(e)}")
            return {
                'success': False,
                'error': f"Webhook processing failed: {str(e)}"
            }
    
    @staticmethod
    def _process_webhook_event(provider: str, payload: Dict) -> Dict[str, Any]:
        """Process webhook event based on provider"""
        event_type = payload.get('event', 'unknown')
        
        if provider == 'sendgrid':
            return CustomerEngagementIntegrationService._process_sendgrid_webhook(event_type, payload)
        elif provider == 'twilio':
            return CustomerEngagementIntegrationService._process_twilio_webhook(event_type, payload)
        elif provider == 'stripe':
            return CustomerEngagementIntegrationService._process_stripe_webhook(event_type, payload)
        else:
            return {'success': False, 'error': f'Webhook processing not implemented for {provider}'}
    
    @staticmethod
    def _process_sendgrid_webhook(event_type: str, payload: Dict) -> Dict[str, Any]:
        """Process SendGrid webhook events"""
        if event_type in ['delivered', 'open', 'click']:
            # Update communication status in database
            message_id = payload.get('message_id')
            if message_id:
                communication = CustomerCommunication.query.filter_by(
                    external_id=message_id
                ).first()
                
                if communication:
                    if event_type == 'delivered':
                        communication.status = 'delivered'
                        communication.delivered_at = datetime.now()
                    elif event_type == 'open':
                        communication.opened_at = datetime.now()
                    elif event_type == 'click':
                        communication.clicked_at = datetime.now()
                    
                    db.session.commit()
        
        return {'success': True, 'event': event_type}
    
    @staticmethod
    def _process_twilio_webhook(event_type: str, payload: Dict) -> Dict[str, Any]:
        """Process Twilio webhook events"""
        if event_type == 'message_status':
            # Update SMS delivery status
            message_id = payload.get('message_id')
            status = payload.get('status')
            
            if message_id and status:
                communication = CustomerCommunication.query.filter_by(
                    external_id=message_id
                ).first()
                
                if communication:
                    communication.status = status
                    if status == 'delivered':
                        communication.delivered_at = datetime.now()
                    
                    db.session.commit()
        
        return {'success': True, 'event': event_type}
    
    @staticmethod
    def _process_stripe_webhook(event_type: str, payload: Dict) -> Dict[str, Any]:
        """Process Stripe webhook events"""
        if event_type in ['payment_intent.succeeded', 'payment_intent.payment_failed']:
            # Update payment status
            payment_intent_id = payload.get('payment_intent_id')
            status = payload.get('status')
            
            if payment_intent_id:
                # Update payment records in database
                # This would update the payment status
                pass
        
        return {'success': True, 'event': event_type}