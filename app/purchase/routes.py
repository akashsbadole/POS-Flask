from flask import Blueprint, jsonify, request, render_template, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from app.purchase import bp
from app.models.purchase import Purchase, PurchasePayment, PurchaseInvoice, PurchaseEmail, PurchaseStatus
from app.models.subscription import SubscriptionPlan
from app.models.license import LicenseTemplate
from app.models.user import User
from app import db
from datetime import datetime, timedelta
import json
import uuid
# import stripe  # Uncomment when stripe is installed

@bp.route('/')
def purchase_home():
    """Purchase home page with available plans and licenses"""
    subscription_plans = SubscriptionPlan.query.filter_by(is_active=True).all()
    license_templates = LicenseTemplate.query.filter_by(is_active=True).all()
    
    return render_template('purchase/home.html', 
                         subscription_plans=subscription_plans,
                         license_templates=license_templates)

@bp.route('/plans')
def subscription_plans():
    """View available subscription plans"""
    plans = SubscriptionPlan.query.filter_by(is_active=True).order_by(SubscriptionPlan.price).all()
    return render_template('purchase/plans.html', plans=plans)

@bp.route('/licenses')
def licenses():
    """View available license templates"""
    templates = LicenseTemplate.query.filter_by(is_active=True).all()
    return render_template('purchase/licenses.html', templates=templates)

@bp.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    """Checkout process for purchases"""
    if request.method == 'GET':
        # Get items from session or request params
        items = request.args.get('items', '[]')
        try:
            items = json.loads(items)
        except:
            items = []
        
        if not items:
            flash('No items in cart', 'error')
            return redirect(url_for('purchase.purchase_home'))
        
        return render_template('purchase/checkout.html', items=items)
    
    # Process checkout
    data = request.get_json()
    
    try:
        # Create purchase record
        purchase = Purchase(
            customer_id=current_user.id,
            restaurant_id=current_user.restaurant_id if current_user.restaurant_id else None,
            items=data.get('items', []),
            payment_method=data.get('payment_method', 'stripe'),
            customer_name=data.get('customer_name', current_user.name),
            customer_email=data.get('customer_email', current_user.email),
            customer_phone=data.get('customer_phone', ''),
            billing_address=data.get('billing_address'),
            is_trial=data.get('is_trial', False),
            trial_days=data.get('trial_days', 0)
        )
        
        # Calculate totals
        purchase.calculate_total()
        
        db.session.add(purchase)
        db.session.flush()  # Get purchase ID
        
        # Process payment based on method
        if data.get('payment_method') == 'stripe':
            payment_result = process_stripe_payment(purchase, data)
        elif data.get('payment_method') == 'paypal':
            payment_result = process_paypal_payment(purchase, data)
        else:
            raise ValueError('Unsupported payment method')
        
        if payment_result['success']:
            setattr(purchase, 'status', PurchaseStatus.COMPLETED)
            setattr(purchase, 'completed_at', datetime.utcnow())
            setattr(purchase, 'payment_status', 'completed')
            setattr(purchase, 'transaction_id', payment_result['transaction_id'])
            
            # Create invoice
            invoice = PurchaseInvoice(
                purchase_id=purchase.id,
                subtotal=purchase.subtotal,
                tax_amount=purchase.tax_amount,
                discount_amount=purchase.discount_amount,
                total_amount=purchase.total_amount,
                customer_name=purchase.customer_name,
                customer_email=purchase.customer_email,
                billing_address=purchase.billing_address
            )
            db.session.add(invoice)
            
            # Send confirmation emails
            send_purchase_confirmation_emails(purchase, invoice)
            
            db.session.commit()
            
            return jsonify({
                'success': True,
                'purchase_id': purchase.id,
                'purchase_number': purchase.purchase_number,
                'redirect_url': url_for('purchase.confirmation', purchase_number=purchase.purchase_number)
            })
        else:
            setattr(purchase, 'status', PurchaseStatus.FAILED)
            setattr(purchase, 'payment_status', 'failed')
            db.session.commit()
            
            return jsonify({
                'success': False,
                'error': payment_result['error']
            }), 400
            
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Checkout error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'An error occurred during checkout. Please try again.'
        }), 500

@bp.route('/confirmation/<purchase_number>')
@login_required
def confirmation(purchase_number):
    """Purchase confirmation page"""
    purchase = Purchase.query.filter_by(purchase_number=purchase_number).first_or_404()
    
    # Verify ownership
    if purchase.customer_id != current_user.id:
        return render_template('errors/403.html'), 403
    
    return render_template('purchase/confirmation.html', purchase=purchase)

@bp.route('/history')
@login_required
def purchase_history():
    """Purchase history for current user"""
    purchases = Purchase.query.filter_by(customer_id=current_user.id).order_by(Purchase.purchased_at.desc()).all()
    return render_template('purchase/history.html', purchases=purchases)

@bp.route('/invoice/<invoice_number>')
@login_required
def view_invoice(invoice_number):
    """View purchase invoice"""
    invoice = PurchaseInvoice.query.filter_by(invoice_number=invoice_number).first_or_404()
    
    # Verify ownership
    if invoice.purchase.customer_id != current_user.id:
        return render_template('errors/403.html'), 403
    
    return render_template('purchase/invoice.html', invoice=invoice)

@bp.route('/api/stripe/create-payment-intent', methods=['POST'])
@login_required
def create_stripe_payment_intent():
    """Create Stripe payment intent"""
    try:
        data = request.get_json()
        amount = int(float(data.get('amount', 0)) * 100)  # Convert to cents
        
        # Configure Stripe (should be in config)
        # stripe.api_key = current_app.config.get('STRIPE_SECRET_KEY')
        
        # Placeholder for Stripe integration
        # intent = stripe.PaymentIntent.create(
        #     amount=amount,
        #     currency='usd',
        #     metadata={
        #         'user_id': current_user.id,
        #         'purchase_number': data.get('purchase_number', '')
        #     }
        # )
        
        return jsonify({
            'client_secret': 'pi_test_placeholder'  # intent.client_secret
        })
        
    except Exception as e:
        current_app.logger.error(f"Stripe payment intent error: {str(e)}")
        return jsonify({
            'error': 'Failed to create payment intent'
        }), 500

@bp.route('/api/trial/start', methods=['POST'])
@login_required
def start_trial():
    """Start a free trial"""
    try:
        data = request.get_json()
        plan_id = data.get('plan_id')
        trial_days = data.get('trial_days', 14)
        
        # Get subscription plan
        plan = SubscriptionPlan.query.get_or_404(plan_id)
        
        # Create trial purchase
        purchase = Purchase(
            customer_id=current_user.id,
            restaurant_id=current_user.restaurant_id if current_user.restaurant_id else None,
            subscription_plan_id=plan_id,
            items=[{
                'type': 'subscription',
                'plan_id': plan_id,
                'name': plan.name,
                'price': 0,
                'quantity': 1
            }],
            subtotal=0,
            tax_amount=0,
            discount_amount=0,
            total_amount=0,
            payment_method='trial',
            customer_name=current_user.name,
            customer_email=current_user.email,
            is_trial=True,
            trial_days=trial_days,
            trial_ends_at=datetime.utcnow() + timedelta(days=trial_days),
            status='completed',
            completed_at=datetime.utcnow()
        )
        
        db.session.add(purchase)
        db.session.flush()
        
        # Create invoice for trial
        invoice = PurchaseInvoice(
            purchase_id=purchase.id,
            subtotal=0,
            tax_amount=0,
            discount_amount=0,
            total_amount=0,
            customer_name=current_user.name,
            customer_email=current_user.email,
            status='paid',
            paid_date=datetime.utcnow()
        )
        db.session.add(invoice)
        
        # Send trial confirmation email
        send_trial_confirmation_email(purchase)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'purchase_number': purchase.purchase_number,
            'trial_ends_at': purchase.trial_ends_at.isoformat()
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Trial start error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to start trial'
        }), 500

@bp.route('/api/trial/extend', methods=['POST'])
@login_required
def extend_trial():
    """Extend trial period"""
    try:
        data = request.get_json()
        purchase_id = data.get('purchase_id')
        extension_days = data.get('extension_days', 7)
        
        # Get trial purchase
        purchase = Purchase.query.get_or_404(purchase_id)
        
        if not purchase.is_trial:
            return jsonify({
                'success': False,
                'error': 'This is not a trial purchase'
            }), 400
        
        if purchase.trial_ends_at and purchase.trial_ends_at > datetime.utcnow():
            # Extend trial period
            purchase.trial_ends_at = purchase.trial_ends_at + timedelta(days=extension_days)
            purchase.trial_days = (purchase.trial_days or 0) + extension_days
            
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': f'Trial extended by {extension_days} days',
                'new_end_date': purchase.trial_ends_at.isoformat(),
                'total_trial_days': purchase.trial_days
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Trial has already ended'
            }), 400
            
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Trial extension error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to extend trial'
        }), 500

@bp.route('/api/trial/convert', methods=['POST'])
@login_required
def convert_trial():
    """Convert trial to paid subscription"""
    try:
        data = request.get_json()
        purchase_id = data.get('purchase_id')
        payment_method = data.get('payment_method')
        
        # Get trial purchase
        purchase = Purchase.query.get_or_404(purchase_id)
        
        if not purchase.is_trial:
            return jsonify({
                'success': False,
                'error': 'This is not a trial purchase'
            }), 400
        
        if purchase.trial_ends_at and purchase.trial_ends_at <= datetime.utcnow():
            return jsonify({
                'success': False,
                'error': 'Trial has already ended'
            }), 400
        
        # Create new paid purchase
        paid_purchase = Purchase(
            customer_id=purchase.customer_id,
            restaurant_id=purchase.restaurant_id,
            subscription_plan_id=purchase.subscription_plan_id,
            items=purchase.items,
            subtotal=purchase.subtotal,
            tax_amount=purchase.tax_amount,
            discount_amount=purchase.discount_amount,
            total_amount=purchase.total_amount,
            payment_method=payment_method,
            customer_name=purchase.customer_name,
            customer_email=purchase.customer_email,
            customer_phone=purchase.customer_phone,
            billing_address=purchase.billing_address,
            is_trial=False,
            trial_days=0,
            status='completed',
            completed_at=datetime.utcnow()
        )
        
        db.session.add(paid_purchase)
        db.session.flush()
        
        # Mark trial as converted
        purchase.status = 'converted'
        purchase.converted_to_purchase_id = paid_purchase.id
        
        # Create invoice for paid purchase
        invoice = PurchaseInvoice(
            purchase_id=paid_purchase.id,
            subtotal=paid_purchase.subtotal,
            tax_amount=paid_purchase.tax_amount,
            discount_amount=paid_purchase.discount_amount,
            total_amount=paid_purchase.total_amount,
            customer_name=paid_purchase.customer_name,
            customer_email=paid_purchase.customer_email,
            billing_address=paid_purchase.billing_address,
            status='paid',
            paid_date=datetime.utcnow()
        )
        db.session.add(invoice)
        
        db.session.commit()
        
        # Send conversion confirmation
        send_trial_conversion_email(purchase, paid_purchase)
        
        return jsonify({
            'success': True,
            'message': 'Trial converted to paid subscription successfully',
            'new_purchase_id': paid_purchase.id,
            'invoice_id': invoice.id
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Trial conversion error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to convert trial'
        }), 500

@bp.route('/api/trial/status/<int:purchase_id>')
@login_required
def trial_status(purchase_id):
    """Get trial status"""
    try:
        purchase = Purchase.query.get_or_404(purchase_id)
        
        if not purchase.is_trial:
            return jsonify({
                'success': False,
                'error': 'This is not a trial purchase'
            }), 404
        
        days_remaining = 0
        if purchase.trial_ends_at:
            delta = purchase.trial_ends_at - datetime.utcnow()
            days_remaining = max(0, delta.days)
        
        return jsonify({
            'success': True,
            'trial': {
                'purchase_id': purchase.id,
                'purchase_number': purchase.purchase_number,
                'trial_days': purchase.trial_days,
                'trial_ends_at': purchase.trial_ends_at.isoformat() if purchase.trial_ends_at else None,
                'days_remaining': days_remaining,
                'is_expired': days_remaining <= 0,
                'status': purchase.status,
                'subscription_plan_id': purchase.subscription_plan_id,
                'can_extend': days_remaining > 0,
                'can_convert': days_remaining > 0
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Trial status error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to get trial status'
        }), 500

@bp.route('/api/trial/usage/<int:purchase_id>')
@login_required
def trial_usage(purchase_id):
    """Get trial usage statistics"""
    try:
        purchase = Purchase.query.get_or_404(purchase_id)
        
        if not purchase.is_trial:
            return jsonify({
                'success': False,
                'error': 'This is not a trial purchase'
            }), 404
        
        # Calculate usage statistics
        days_used = 0
        if purchase.trial_ends_at and purchase.purchased_at:
            days_used = (datetime.utcnow() - purchase.purchased_at).days
        
        days_remaining = 0
        if purchase.trial_ends_at:
            delta = purchase.trial_ends_at - datetime.utcnow()
            days_remaining = max(0, delta.days)
        
        usage_percentage = 0
        if purchase.trial_days > 0:
            usage_percentage = (days_used / purchase.trial_days) * 100
        
        return jsonify({
            'success': True,
            'usage': {
                'purchase_id': purchase.id,
                'trial_days_total': purchase.trial_days,
                'days_used': days_used,
                'days_remaining': days_remaining,
                'usage_percentage': round(usage_percentage, 2),
                'is_expired': days_remaining <= 0,
                'usage_level': 'high' if usage_percentage > 80 else 'medium' if usage_percentage > 50 else 'low'
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Trial usage error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to get trial usage'
        }), 500

# Helper functions for payment processing
def process_stripe_payment(purchase, data):
    """Process Stripe payment"""
    try:
        # Placeholder for Stripe integration
        # stripe.api_key = current_app.config.get('STRIPE_SECRET_KEY')
        
        # intent = stripe.PaymentIntent.create(
        #     amount=int(float(purchase.total_amount) * 100),
        #     currency='usd',
        #     payment_method=data.get('payment_method_id'),
        #     confirmation_method='manual',
        #     confirm=True
        # )
        
        # if intent.status == 'succeeded':
        #     return {
        #         'success': True,
        #         'transaction_id': intent.id
        #     }
        # else:
        #     return {
        #         'success': False,
        #         'error': f'Payment failed: {intent.status}'
        #     }
        
        # For testing, return success
        return {
            'success': True,
            'transaction_id': f'stripe_test_{uuid.uuid4().hex[:8]}'
        }
            
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

def process_paypal_payment(purchase, data):
    """Process PayPal payment"""
    # PayPal integration would go here
    # For now, return success for testing
    return {
        'success': True,
        'transaction_id': f'paypal_{uuid.uuid4().hex[:8]}'
    }

# Email functions
def send_purchase_confirmation_emails(purchase, invoice):
    """Send purchase confirmation emails"""
    try:
        # Send to customer
        customer_email = PurchaseEmail(
            purchase_id=purchase.id,
            email_type='order_confirmation',
            recipient_email=purchase.customer_email,
            recipient_name=purchase.customer_name,
            subject=f'Order Confirmation - {purchase.purchase_number}',
            content=render_template('emails/purchase_confirmation.html', purchase=purchase, invoice=invoice),
            status='sent',
            sent_at=datetime.utcnow()
        )
        db.session.add(customer_email)
        
        # Send invoice
        invoice_email = PurchaseEmail(
            purchase_id=purchase.id,
            email_type='invoice',
            recipient_email=purchase.customer_email,
            recipient_name=purchase.customer_name,
            subject=f'Invoice - {invoice.invoice_number}',
            content=render_template('emails/invoice.html', invoice=invoice),
            status='sent',
            sent_at=datetime.utcnow()
        )
        db.session.add(invoice_email)
        
    except Exception as e:
        current_app.logger.error(f"Failed to send purchase confirmation emails: {str(e)}")

def send_trial_confirmation_email(purchase):
    """Send trial confirmation email"""
    try:
        trial_email = PurchaseEmail(
            purchase_id=purchase.id,
            email_type='trial_confirmation',
            recipient_email=purchase.customer_email,
            recipient_name=purchase.customer_name,
            subject=f'Trial Started - {purchase.purchase_number}',
            content=render_template('emails/trial_confirmation.html', purchase=purchase),
            status='sent',
            sent_at=datetime.utcnow()
        )
        db.session.add(trial_email)
        
    except Exception as e:
        current_app.logger.error(f"Failed to send trial confirmation email: {str(e)}")

def send_trial_conversion_email(trial_purchase, paid_purchase):
    """Send trial conversion confirmation email"""
    try:
        conversion_email = PurchaseEmail(
            purchase_id=trial_purchase.id,
            email_type='trial_conversion',
            recipient_email=trial_purchase.customer_email,
            recipient_name=trial_purchase.customer_name,
            subject=f'Trial Converted - {trial_purchase.purchase_number}',
            content=render_template('emails/trial_conversion.html', trial_purchase=trial_purchase, paid_purchase=paid_purchase),
            status='sent',
            sent_at=datetime.utcnow()
        )
        db.session.add(conversion_email)
        
    except Exception as e:
        current_app.logger.error(f"Failed to send trial conversion email: {str(e)}")

def send_trial_extension_email(purchase, extension_days):
    """Send trial extension confirmation email"""
    try:
        extension_email = PurchaseEmail(
            purchase_id=purchase.id,
            email_type='trial_extension',
            recipient_email=purchase.customer_email,
            recipient_name=purchase.customer_name,
            subject=f'Trial Extended - {purchase.purchase_number}',
            content=render_template('emails/trial_extension.html', purchase=purchase, extension_days=extension_days),
            status='sent',
            sent_at=datetime.utcnow()
        )
        db.session.add(extension_email)
        
    except Exception as e:
        current_app.logger.error(f"Failed to send trial extension email: {str(e)}")

def get_trial_statistics():
    """Get overall trial statistics"""
    try:
        total_trials = Purchase.query.filter_by(is_trial=True).count()
        active_trials = Purchase.query.filter(
            Purchase.is_trial == True,
            Purchase.trial_ends_at > datetime.utcnow(),
            Purchase.status == 'completed'
        ).count()
        expired_trials = Purchase.query.filter(
            Purchase.is_trial == True,
            Purchase.trial_ends_at <= datetime.utcnow()
        ).count()
        converted_trials = Purchase.query.filter_by(status='converted').count()
        
        return {
            'total_trials': total_trials,
            'active_trials': active_trials,
            'expired_trials': expired_trials,
            'converted_trials': converted_trials,
            'conversion_rate': (converted_trials / total_trials * 100) if total_trials > 0 else 0
        }
        
    except Exception as e:
        current_app.logger.error(f"Failed to get trial statistics: {str(e)}")
        return {
            'total_trials': 0,
            'active_trials': 0,
            'expired_trials': 0,
            'converted_trials': 0,
            'conversion_rate': 0
        }