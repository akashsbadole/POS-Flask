from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
from app import db
from app.models.payment_gateway import (
    PaymentGateway, PaymentTransaction, PaymentMethodConfig, 
    PaymentGatewayType, PaymentMethod, TransactionStatus
)
from app.models.subscription import Subscription, SubscriptionPlan
from app.services.payment_service import get_payment_service, PaymentGatewayError
from datetime import datetime
import json

bp = Blueprint('payment', __name__, url_prefix='/payment')

@bp.route('/process/<int:subscription_id>', methods=['GET', 'POST'])
@login_required
def process_payment(subscription_id):
    """Process payment for subscription"""
    if current_user.is_super_admin():
        flash('Super admin cannot process payments', 'error')
        return redirect(url_for('main.dashboard'))
    
    subscription = Subscription.query.get_or_404(subscription_id)
    
    # Check permissions
    if subscription.restaurant_id != current_user.restaurant_id:
        flash('Access denied', 'error')
        return redirect(url_for('subscription.dashboard'))
    
    # Check if payment is already processed
    if subscription.status == 'active':
        flash('Subscription is already active', 'info')
        return redirect(url_for('subscription.my_subscription'))
    
    # Get available payment gateways
    gateways = PaymentGateway.query.filter_by(is_active=True).all()
    
    if request.method == 'POST':
        gateway_type = request.form.get('gateway_type')
        payment_method = request.form.get('payment_method')
        
        if not gateway_type or not payment_method:
            flash('Please select payment gateway and method', 'error')
            return render_template('payment/process.html', 
                               subscription=subscription, 
                               gateways=gateways)
        
        try:
            # Process payment
            payment_details = {
                'user_id': current_user.id,
                'email': current_user.email,
                'name': current_user.name
            }
            
            payment_svc = get_payment_service()
            transaction = payment_svc.process_subscription_payment(
                subscription_id=subscription_id,
                amount=subscription.amount,
                payment_method=payment_method,
                gateway_type=gateway_type,
                payment_details=payment_details
            )
            
            flash('Payment processed successfully!', 'success')
            return redirect(url_for('payment.payment_success', transaction_id=transaction.id))
            
        except PaymentGatewayError as e:
            flash(f'Payment failed: {str(e)}', 'error')
            return render_template('payment/process.html', 
                               subscription=subscription, 
                               gateways=gateways)
        except Exception as e:
            current_app.logger.error(f"Payment processing error: {str(e)}")
            flash('An error occurred while processing payment', 'error')
            return render_template('payment/process.html', 
                               subscription=subscription, 
                               gateways=gateways)
    
    return render_template('payment/process.html', 
                       subscription=subscription, 
                       gateways=gateways)

@bp.route('/success/<int:transaction_id>')
@login_required
def payment_success(transaction_id):
    """Payment success page"""
    transaction = PaymentTransaction.query.get_or_404(transaction_id)
    
    # Check permissions
    if transaction.user_id != current_user.id and not current_user.is_super_admin():
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    subscription = None
    if transaction.subscription_id:
        subscription = Subscription.query.get(transaction.subscription_id)
    
    return render_template('payment/success.html', 
                       transaction=transaction, 
                       subscription=subscription)

@bp.route('/failed/<int:transaction_id>')
@login_required
def payment_failed(transaction_id):
    """Payment failed page"""
    transaction = PaymentTransaction.query.get_or_404(transaction_id)
    
    # Check permissions
    if transaction.user_id != current_user.id and not current_user.is_super_admin():
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    subscription = None
    if transaction.subscription_id:
        subscription = Subscription.query.get(transaction.subscription_id)
    
    return render_template('payment/failed.html', 
                       transaction=transaction, 
                       subscription=subscription)

@bp.route('/history')
@login_required
def payment_history():
    """View payment history"""
    if current_user.is_super_admin():
        # Super admin sees all transactions
        transactions = PaymentTransaction.query.order_by(
            PaymentTransaction.created_at.desc()
        ).all()
    else:
        # Regular user sees their transactions
        transactions = PaymentTransaction.query.filter_by(
            user_id=current_user.id
        ).order_by(PaymentTransaction.created_at.desc()).all()
    
    return render_template('payment/history.html', transactions=transactions)

@bp.route('/refund/<int:transaction_id>', methods=['GET', 'POST'])
@login_required
def refund_payment(transaction_id):
    """Process refund for transaction"""
    transaction = PaymentTransaction.query.get_or_404(transaction_id)
    
    # Check permissions - only super admin can process refunds
    if not current_user.is_super_admin():
        flash('Access denied', 'error')
        return redirect(url_for('payment.payment_history'))
    
    if transaction.status != TransactionStatus.COMPLETED:
        flash('Cannot refund non-completed transaction', 'error')
        return redirect(url_for('payment.payment_history'))
    
    if transaction.refunded_amount > 0:
        flash('Transaction already has refunds', 'warning')
        return redirect(url_for('payment.payment_history'))
    
    if request.method == 'POST':
        refund_amount = float(request.form.get('refund_amount', 0))
        reason = request.form.get('reason', '')
        
        if refund_amount <= 0 or refund_amount > transaction.get_amount():
            flash('Invalid refund amount', 'error')
            return render_template('payment/refund.html', transaction=transaction)
        
        try:
            payment_svc = get_payment_service()
            success = payment_svc.process_refund(
                transaction_id=transaction_id,
                amount=refund_amount,
                reason=reason
            )
            
            if success:
                flash(f'Refund of ₹{refund_amount:.2f} processed successfully', 'success')
                return redirect(url_for('payment.payment_history'))
            else:
                flash('Refund failed', 'error')
                
        except PaymentGatewayError as e:
            flash(f'Refund failed: {str(e)}', 'error')
        except Exception as e:
            current_app.logger.error(f"Refund processing error: {str(e)}")
            flash('An error occurred while processing refund', 'error')
    
    return render_template('payment/refund.html', transaction=transaction)

@bp.route('/webhook/<string:gateway_type>', methods=['POST'])
def webhook(gateway_type):
    """Handle webhook events from payment gateways"""
    try:
        # Get gateway
        payment_svc = get_payment_service()
        gateway = payment_svc.get_gateway(gateway_type)
        if not gateway:
            return jsonify({'error': 'Gateway not found'}), 404
        
        # Get webhook data
        payload = request.data.decode('utf-8')
        signature = request.headers.get('X-Webhook-Signature', '')
        
        # Verify webhook signature
        payment_svc = get_payment_service()
        if not payment_svc.verify_webhook(
            gateway_type, payload, signature, gateway.webhook_secret
        ):
            return jsonify({'error': 'Invalid signature'}), 401
        
        # Parse event data
        try:
            event_data = json.loads(payload)
        except json.JSONDecodeError:
            return jsonify({'error': 'Invalid JSON'}), 400
        
        # Process webhook event
        payment_svc = get_payment_service()
        success = payment_svc.process_webhook_event(
            gateway_type, 
            event_data.get('event', ''), 
            event_data
        )
        
        if success:
            return jsonify({'status': 'processed'}), 200
        else:
            return jsonify({'status': 'processing_failed'}), 500
            
    except Exception as e:
        current_app.logger.error(f"Webhook processing error: {str(e)}")
        return jsonify({'error': 'Processing failed'}), 500

@bp.route('/methods/<string:gateway_type>')
@login_required
def get_payment_methods(gateway_type):
    """Get available payment methods for a gateway"""
    payment_svc = get_payment_service()
    gateway = payment_svc.get_gateway(gateway_type)
    if not gateway:
        return jsonify({'error': 'Gateway not found'}), 404
    
    # Get payment method configs
    method_configs = PaymentMethodConfig.query.filter_by(
        gateway_id=gateway.id,
        is_enabled=True
    ).all()
    
    methods = []
    for config in method_configs:
        methods.append({
            'type': config.method_type.value if config.method_type else None,
            'min_amount': config.get_min_amount(),
            'max_amount': config.get_max_amount(),
            'fee_percentage': config.get_fee_percentage(),
            'fee_fixed': config.get_fee_fixed()
        })
    
    return jsonify({'methods': methods})

@bp.route('/calculate-fee', methods=['POST'])
@login_required
def calculate_fee():
    """Calculate processing fee for payment"""
    gateway_type = request.json.get('gateway_type')
    payment_method = request.json.get('payment_method')
    amount = float(request.json.get('amount', 0))
    
    if not gateway_type or not payment_method or amount <= 0:
        return jsonify({'error': 'Invalid parameters'}), 400
    
    payment_svc = get_payment_service()
    gateway = payment_svc.get_gateway(gateway_type)
    if not gateway:
        return jsonify({'error': 'Gateway not found'}), 404
    
    # Get payment method config
    method_config = PaymentMethodConfig.query.filter_by(
        gateway_id=gateway.id,
        method_type=PaymentMethod(payment_method),
        is_enabled=True
    ).first()
    
    if not method_config:
        return jsonify({'error': 'Payment method not available'}), 404
    
    # Check amount limits
    if amount < method_config.get_min_amount() or amount > method_config.get_max_amount():
        return jsonify({'error': 'Amount outside allowed range'}), 400
    
    # Calculate fee
    fee = method_config.calculate_fee(amount)
    total_amount = amount + fee
    
    return jsonify({
        'fee': fee,
        'total_amount': total_amount,
        'fee_breakdown': {
            'percentage': method_config.get_fee_percentage(),
            'fixed': method_config.get_fee_fixed()
        }
    })

# Admin routes for payment gateway management
@bp.route('/admin/gateways')
@login_required
def admin_gateways():
    """Manage payment gateways (super admin only)"""
    if not current_user.is_super_admin():
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    gateways = PaymentGateway.query.all()
    return render_template('payment/admin_gateways.html', gateways=gateways)

@bp.route('/admin/gateways/<int:gateway_id>/toggle', methods=['POST'])
@login_required
def toggle_gateway(gateway_id):
    """Toggle payment gateway active status"""
    if not current_user.is_super_admin():
        return jsonify({'error': 'Access denied'}), 403
    
    gateway = PaymentGateway.query.get_or_404(gateway_id)
    gateway.is_active = not gateway.is_active
    db.session.commit()
    
    return jsonify({
        'status': 'success',
        'is_active': gateway.is_active
    })

@bp.route('/admin/gateways/<int:gateway_id>/config', methods=['GET', 'POST'])
@login_required
def configure_gateway(gateway_id):
    """Configure payment gateway"""
    if not current_user.is_super_admin():
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    gateway = PaymentGateway.query.get_or_404(gateway_id)
    
    if request.method == 'POST':
        # Update gateway configuration
        gateway.name = request.form.get('name')
        gateway.test_mode = 'test_mode' in request.form
        gateway.webhook_secret = request.form.get('webhook_secret')
        
        # Update gateway-specific config
        config = gateway.get_config_dict()
        if gateway.gateway_type == PaymentGatewayType.RAZORPAY:
            config['api_key'] = request.form.get('api_key')
            config['api_secret'] = request.form.get('api_secret')
        elif gateway.gateway_type == PaymentGatewayType.STRIPE:
            config['publishable_key'] = request.form.get('publishable_key')
            config['secret_key'] = request.form.get('secret_key')
        
        gateway.set_config(config)
        db.session.commit()
        
        flash('Gateway configuration updated successfully', 'success')
        return redirect(url_for('payment.admin_gateways'))
    
    return render_template('payment/gateway_config.html', gateway=gateway)