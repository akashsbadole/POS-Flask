from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Union
from flask import current_app
import json
import hashlib
import hmac
import requests
from app import db
from app.models.payment_gateway import (
    PaymentGateway, PaymentTransaction, PaymentMethodConfig,
    WebhookEvent, PaymentGatewayType, PaymentMethod, TransactionStatus
)
from app.models.subscription import Subscription, SubscriptionPayment

class PaymentGatewayError(Exception):
    """Custom exception for payment gateway errors"""
    pass

class PaymentService:
    """Service for handling payment gateway operations"""
    
    def __init__(self):
        self.active_gateways = {}
        self._load_active_gateways()
    
    def _load_active_gateways(self):
        """Load active payment gateways"""
        gateways = PaymentGateway.query.filter_by(is_active=True).all()
        for gateway in gateways:
            # Handle both enum and string values for gateway_type
            gateway_type = gateway.gateway_type.value if hasattr(gateway.gateway_type, 'value') else str(gateway.gateway_type)
            self.active_gateways[gateway_type] = gateway
    
    def get_gateway(self, gateway_type: str) -> Optional[PaymentGateway]:
        """Get payment gateway by type"""
        return self.active_gateways.get(gateway_type)
    
    def process_subscription_payment(self, subscription_id: int, amount: float,
                                   payment_method: str, gateway_type: str = "razorpay",
                                   payment_details: Optional[Dict[str, Any]] = None) -> PaymentTransaction:
        """Process payment for subscription"""
        gateway = self.get_gateway(gateway_type)
        if not gateway:
            raise PaymentGatewayError(f"Payment gateway {gateway_type} not found or inactive")
        
        # Create transaction record
        transaction = PaymentTransaction(
            subscription_id=subscription_id,
            user_id=payment_details.get('user_id') if payment_details else None,
            gateway_id=gateway.id,
            amount=amount,
            currency='INR',
            payment_method=payment_method,
            status='pending'
        )
        
        db.session.add(transaction)
        db.session.flush()
        
        try:
            # Process payment based on gateway type
            if gateway_type == "razorpay":
                result = self._process_razorpay_payment(transaction, payment_details or {})
            elif gateway_type == "stripe":
                result = self._process_stripe_payment(transaction, payment_details or {})
            else:
                raise PaymentGatewayError(f"Unsupported gateway: {gateway_type}")
            
            # Update transaction with result
            if result.get('success'):
                transaction.mark_completed(result.get('response'))
                # Update subscription payment record
                self._update_subscription_payment(subscription_id, transaction)
            else:
                transaction.mark_failed(
                    result.get('error_code'),
                    result.get('error_message'),
                    result.get('response')
                )
                raise PaymentGatewayError(result.get('error_message', 'Payment failed'))
            
            return transaction
            
        except Exception as e:
            transaction.mark_failed(None, str(e))
            db.session.commit()
            raise PaymentGatewayError(f"Payment processing failed: {str(e)}")
    
    def _process_razorpay_payment(self, transaction: PaymentTransaction,
                                 payment_details: Dict[str, Any]) -> Dict[str, Any]:
        """Process payment via Razorpay"""
        gateway = self.get_gateway("razorpay")
        if not gateway:
            return {
                'success': False,
                'error_code': 'gateway_not_found',
                'error_message': 'Razorpay gateway not found'
            }
        
        config = gateway.get_config_dict()
        
        # For demo purposes, simulate payment processing
        # In production, integrate with actual Razorpay API
        if bool(gateway.test_mode):
            # Simulate successful payment in test mode
            return {
                'success': True,
                'transaction_id': f"test_rzp_{transaction.id}_{int(datetime.utcnow().timestamp())}",
                'response': {'status': 'captured', 'id': f"test_rzp_{transaction.id}"}
            }
        
        # Production Razorpay integration
        try:
            # Create order
            order_data = {
                'amount': int(float(getattr(transaction, 'amount', 0)) * 100),  # Razorpay expects amount in paise
                'currency': transaction.currency,
                'receipt': f"subscr_{transaction.subscription_id}",
                'payment_capture': 1
            }
            
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f"Basic {config.get('api_key')}"
            }
            
            response = requests.post(
                'https://api.razorpay.com/v1/orders',
                json=order_data,
                headers=headers
            )
            
            if response.status_code == 200:
                order_result = response.json()
                
                # If payment_id is provided, capture the payment
                if 'payment_id' in payment_details:
                    capture_response = requests.post(
                        f"https://api.razorpay.com/v1/payments/{payment_details['payment_id']}/capture",
                        json={'amount': int(float(getattr(transaction, 'amount', 0)) * 100)},
                        headers=headers
                    )
                    
                    if capture_response.status_code == 200:
                        return {
                            'success': True,
                            'transaction_id': payment_details['payment_id'],
                            'response': capture_response.json()
                        }
                    else:
                        return {
                            'success': False,
                            'error_code': 'capture_failed',
                            'error_message': 'Failed to capture payment',
                            'response': capture_response.text
                        }
                else:
                    return {
                        'success': True,
                        'transaction_id': order_result['id'],
                        'response': order_result
                    }
            else:
                return {
                    'success': False,
                    'error_code': 'order_creation_failed',
                    'error_message': 'Failed to create payment order',
                    'response': response.text
                }
                
        except Exception as e:
            return {
                'success': False,
                'error_code': 'api_error',
                'error_message': str(e)
            }
    
    def _process_stripe_payment(self, transaction: PaymentTransaction,
                              payment_details: Dict[str, Any]) -> Dict[str, Any]:
        """Process payment via Stripe"""
        gateway = self.get_gateway("stripe")
        if not gateway:
            return {
                'success': False,
                'error_code': 'gateway_not_found',
                'error_message': 'Stripe gateway not found'
            }
        
        config = gateway.get_config_dict()
        
        # For demo purposes, simulate payment processing
        # In production, integrate with actual Stripe API
        if bool(gateway.test_mode):
            # Simulate successful payment in test mode
            return {
                'success': True,
                'transaction_id': f"test_stripe_{transaction.id}_{int(datetime.utcnow().timestamp())}",
                'response': {'status': 'succeeded', 'id': f"test_stripe_{transaction.id}"}
            }
        
        # Production Stripe integration would go here
        # For now, return simulated success
        return {
            'success': True,
            'transaction_id': f"stripe_{transaction.id}_{int(datetime.utcnow().timestamp())}",
            'response': {'status': 'succeeded'}
        }
    
    def _update_subscription_payment(self, subscription_id: int, transaction: PaymentTransaction):
        """Update subscription payment record"""
        subscription = Subscription.query.get(subscription_id)
        if subscription:
            # Create or update subscription payment record
            payment = SubscriptionPayment.query.filter_by(
                subscription_id=subscription_id
            ).order_by(SubscriptionPayment.created_at.desc()).first()
            
            if payment:
                payment.transaction_id = transaction.transaction_id
                payment.status = 'completed'
                payment.payment_date = datetime.utcnow()
                payment.invoice_url = f"/invoices/{transaction.id}"
            else:
                payment = SubscriptionPayment(
                    subscription_id=subscription_id,
                    amount=transaction.amount,
                    currency=transaction.currency,
                    payment_method=transaction.payment_method,
                    transaction_id=transaction.transaction_id,
                    status='completed',
                    payment_date=datetime.utcnow(),
                    billing_period_start=subscription.start_date,
                    billing_period_end=subscription.end_date,
                    invoice_url=f"/invoices/{transaction.id}"
                )
                db.session.add(payment)
            
            # Update subscription status if needed
            if subscription.status in ['trial', 'pending']:
                subscription.status = 'active'
            
            db.session.commit()
    
    def process_refund(self, transaction_id: int, amount: Optional[float] = None, reason: Optional[str] = None) -> bool:
        """Process refund for a transaction"""
        transaction = PaymentTransaction.query.get(transaction_id)
        if not transaction:
            raise PaymentGatewayError("Transaction not found")
        
        if transaction.status != 'completed':
            raise PaymentGatewayError("Cannot refund non-completed transaction")
        
        gateway = transaction.gateway
        refund_amount = amount or transaction.get_amount()
        
        try:
            # Process refund based on gateway type
            if gateway.gateway_type == 'razorpay':
                result = self._process_razorpay_refund(transaction, refund_amount)
            elif gateway.gateway_type == 'stripe':
                result = self._process_stripe_refund(transaction, refund_amount)
            else:
                raise PaymentGatewayError(f"Refund not supported for gateway: {gateway.gateway_type}")
            
            if result.get('success'):
                transaction.refund(refund_amount, reason)
                return True
            else:
                raise PaymentGatewayError(result.get('error_message', 'Refund failed'))
                
        except Exception as e:
            raise PaymentGatewayError(f"Refund processing failed: {str(e)}")
    
    def _process_razorpay_refund(self, transaction: PaymentTransaction, amount: float) -> Dict[str, Any]:
        """Process refund via Razorpay"""
        gateway = transaction.gateway
        if not gateway:
            return {
                'success': False,
                'error_code': 'gateway_not_found',
                'error_message': 'Gateway not found for transaction'
            }
        
        config = gateway.get_config_dict()
        
        if gateway.test_mode:
            # Simulate successful refund in test mode
            return {
                'success': True,
                'refund_id': f"test_rzp_refund_{transaction.id}_{int(datetime.utcnow().timestamp())}",
                'response': {'status': 'processed'}
            }
        
        # Production Razorpay refund integration
        try:
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f"Basic {config.get('api_key')}"
            }
            
            refund_data = {
                'amount': int(amount * 100),  # Razorpay expects amount in paise
                'payment_id': transaction.transaction_id
            }
            
            response = requests.post(
                'https://api.razorpay.com/v1/refunds',
                json=refund_data,
                headers=headers
            )
            
            if response.status_code == 200:
                return {
                    'success': True,
                    'refund_id': response.json().get('id'),
                    'response': response.json()
                }
            else:
                return {
                    'success': False,
                    'error_code': 'refund_failed',
                    'error_message': 'Failed to process refund',
                    'response': response.text
                }
                
        except Exception as e:
            return {
                'success': False,
                'error_code': 'api_error',
                'error_message': str(e)
            }
    
    def _process_stripe_refund(self, transaction: PaymentTransaction, amount: float) -> Dict[str, Any]:
        """Process refund via Stripe"""
        gateway = transaction.gateway
        if not gateway:
            return {
                'success': False,
                'error_code': 'gateway_not_found',
                'error_message': 'Gateway not found for transaction'
            }
        
        if gateway.test_mode:
            # Simulate successful refund in test mode
            return {
                'success': True,
                'refund_id': f"test_stripe_refund_{transaction.id}_{int(datetime.utcnow().timestamp())}",
                'response': {'status': 'succeeded'}
            }
        
        # Production Stripe refund integration would go here
        # For now, return simulated success
        return {
            'success': True,
            'refund_id': f"stripe_refund_{transaction.id}_{int(datetime.utcnow().timestamp())}",
            'response': {'status': 'succeeded'}
        }
    
    def verify_webhook(self, gateway_type: str, payload: str, signature: str, secret: Optional[str] = None) -> bool:
        """Verify webhook signature"""
        if gateway_type == "razorpay":
            return self._verify_razorpay_webhook(payload, signature, secret or "")
        elif gateway_type == "stripe":
            return self._verify_stripe_webhook(payload, signature, secret or "")
        return False
    
    def _verify_razorpay_webhook(self, payload: str, signature: str, secret: str) -> bool:
        """Verify Razorpay webhook signature"""
        try:
            expected_signature = hmac.new(
                secret.encode('utf-8'),
                payload.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            return hmac.compare_digest(expected_signature, signature)
        except Exception:
            return False
    
    def _verify_stripe_webhook(self, payload: str, signature: str, secret: str) -> bool:
        """Verify Stripe webhook signature"""
        try:
            # Stripe webhook verification logic
            # This is a simplified version
            return True  # Implement actual Stripe verification
        except Exception:
            return False
    
    def process_webhook_event(self, gateway_type: str, event_type: str, event_data: Dict[str, Any]) -> bool:
        """Process webhook event from payment gateway"""
        gateway = self.get_gateway(gateway_type)
        if not gateway:
            return False
        
        # Log webhook event
        webhook_event = WebhookEvent(
            gateway_id=gateway.id,
            event_type=event_type,
            event_data=json.dumps(event_data)
        )
        db.session.add(webhook_event)
        db.session.flush()
        
        try:
            # Process event based on type
            if event_type in ['payment.captured', 'payment.succeeded']:
                self._handle_payment_success(event_data)
            elif event_type in ['payment.failed', 'charge.failed']:
                self._handle_payment_failure(event_data)
            elif event_type in ['payment.refunded', 'charge.refunded']:
                self._handle_payment_refund(event_data)
            
            webhook_event.mark_processed()
            return True
            
        except Exception as e:
            webhook_event.error_message = str(e)  # type: ignore
            webhook_event.processing_attempts += 1  # type: ignore
            db.session.commit()
            return False
    
    def _handle_payment_success(self, event_data: Dict[str, Any]):
        """Handle successful payment webhook"""
        transaction_id = event_data.get('payment_id') or event_data.get('id')
        if transaction_id:
            transaction = PaymentTransaction.query.filter_by(
                transaction_id=transaction_id
            ).first()
            if transaction and transaction.status == 'pending':
                transaction.mark_completed(event_data)
                self._update_subscription_payment(transaction.subscription_id, transaction)
    
    def _handle_payment_failure(self, event_data: Dict[str, Any]):
        """Handle payment failure webhook"""
        transaction_id = event_data.get('payment_id') or event_data.get('id')
        if transaction_id:
            transaction = PaymentTransaction.query.filter_by(
                transaction_id=transaction_id
            ).first()
            if transaction and transaction.status == 'pending':
                transaction.mark_failed(
                    event_data.get('error_code'),
                    event_data.get('error_description'),
                    event_data
                )
    
    def _handle_payment_refund(self, event_data: Dict[str, Any]):
        """Handle payment refund webhook"""
        transaction_id = event_data.get('payment_id') or event_data.get('charge')
        if transaction_id:
            transaction = PaymentTransaction.query.filter_by(
                transaction_id=transaction_id
            ).first()
            if transaction and transaction.status == 'completed':
                refund_amount = event_data.get('amount', 0) / 100  # Convert from paise/cents
                transaction.refund(refund_amount, "Webhook refund")

# Global payment service instance
payment_service = None

def get_payment_service():
    """Get or create payment service instance"""
    global payment_service
    if payment_service is None:
        payment_service = PaymentService()
    return payment_service