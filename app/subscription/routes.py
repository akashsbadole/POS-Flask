from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app.subscription import bp
from app.models.subscription import SubscriptionPlan, Subscription, SubscriptionPayment, SubscriptionUsage, SubscriptionFeature, SubscriptionAddon
from app.models.restaurant import Restaurant
from app import db
from datetime import datetime, timedelta
import json

@bp.route('/')
@login_required
def dashboard():
    """Subscription dashboard"""
    if not current_user.is_super_admin() and not current_user.can_access_manager_features():
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    if current_user.is_super_admin():
        # Super admin sees all subscriptions
        subscriptions = Subscription.query.all()
        plans = SubscriptionPlan.query.all()
    else:
        # Restaurant owner sees their subscription
        subscriptions = Subscription.query.filter_by(restaurant_id=current_user.restaurant_id).all()
        plans = SubscriptionPlan.query.filter_by(is_active=True).all()
    
    return render_template('subscription/dashboard.html', subscriptions=subscriptions, plans=plans)

@bp.route('/plans')
@login_required
def plans():
    """View available subscription plans"""
    if current_user.is_super_admin():
        plans = SubscriptionPlan.query.all()
    else:
        plans = SubscriptionPlan.query.filter_by(is_active=True).all()
    
    current_subscription = None
    if not current_user.is_super_admin() and current_user.restaurant_id:
        current_subscription = Subscription.query.filter_by(
            restaurant_id=current_user.restaurant_id,
            status='active'
        ).first()
    
    return render_template('subscription/plans.html', plans=plans, current_subscription=current_subscription)

@bp.route('/subscribe/<int:plan_id>', methods=['GET', 'POST'])
@login_required
def subscribe(plan_id):
    """Subscribe to a plan"""
    if current_user.is_super_admin():
        flash('Super admin cannot subscribe to plans', 'error')
        return redirect(url_for('subscription.plans'))
    
    if not current_user.can_access_manager_features():
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    plan = SubscriptionPlan.query.get_or_404(plan_id)
    
    # Check if already has active subscription
    existing_subscription = Subscription.query.filter_by(
        restaurant_id=current_user.restaurant_id,
        status='active'
    ).first()
    
    if existing_subscription:
        flash('You already have an active subscription', 'warning')
        return redirect(url_for('subscription.dashboard'))
    
    if request.method == 'POST':
        billing_cycle = request.form.get('billing_cycle', 'monthly')
        payment_method = request.form.get('payment_method')
        
        # Calculate amount based on billing cycle
        if billing_cycle == 'yearly':
            amount = plan.price_yearly
        else:
            amount = plan.price_monthly
        
        # Create subscription
        subscription = Subscription(
            restaurant_id=current_user.restaurant_id,
            plan_id=plan.id,
            billing_cycle=billing_cycle,
            amount=amount,
            currency=plan.currency,
            payment_method=payment_method,
            start_date=datetime.utcnow(),
            end_date=datetime.utcnow() + timedelta(days=30 if billing_cycle == 'monthly' else 365),
            next_billing_date=datetime.utcnow() + timedelta(days=30 if billing_cycle == 'monthly' else 365),
            status='trial' if plan.plan_type.value == 'basic' else 'active',
            trial_end_date=datetime.utcnow() + timedelta(days=14) if plan.plan_type.value == 'basic' else None
        )
        
        db.session.add(subscription)
        db.session.flush()
        
        # Create payment record
        payment = SubscriptionPayment(
            subscription_id=subscription.id,
            amount=amount,
            currency=plan.currency,
            payment_method=payment_method,
            status='pending',
            billing_period_start=subscription.start_date,
            billing_period_end=subscription.end_date
        )
        
        db.session.add(payment)
        db.session.commit()
        
        flash('Subscription created successfully!', 'success')
        return redirect(url_for('subscription.dashboard'))
    
    return render_template('subscription/subscribe.html', plan=plan)

@bp.route('/my-subscription')
@login_required
def my_subscription():
    """View current subscription details"""
    if current_user.is_super_admin():
        flash('Super admin does not have a subscription', 'info')
        return redirect(url_for('subscription.plans'))
    
    subscription = Subscription.query.filter_by(
        restaurant_id=current_user.restaurant_id
    ).order_by(Subscription.created_at.desc()).first()
    
    if not subscription:
        flash('No subscription found', 'info')
        return redirect(url_for('subscription.plans'))
    
    # Get usage statistics
    usage_stats = subscription.get_usage_stats()
    
    # Get payment history
    payments = SubscriptionPayment.query.filter_by(
        subscription_id=subscription.id
    ).order_by(SubscriptionPayment.created_at.desc()).all()
    
    return render_template('subscription/my_subscription.html', 
                         subscription=subscription, 
                         usage_stats=usage_stats,
                         payments=payments)

@bp.route('/cancel/<int:subscription_id>', methods=['GET', 'POST'])
@login_required
def cancel_subscription(subscription_id):
    """Cancel subscription"""
    subscription = Subscription.query.get_or_404(subscription_id)
    
    # Check permissions
    if not current_user.is_super_admin() and subscription.restaurant_id != current_user.restaurant_id:
        flash('Access denied', 'error')
        return redirect(url_for('subscription.dashboard'))
    
    if request.method == 'POST':
        reason = request.form.get('reason')
        subscription.cancel_subscription(reason)
        db.session.commit()
        
        flash('Subscription cancelled successfully', 'success')
        return redirect(url_for('subscription.dashboard'))
    
    return render_template('subscription/cancel.html', subscription=subscription)

@bp.route('/reactivate/<int:subscription_id>', methods=['POST'])
@login_required
def reactivate_subscription(subscription_id):
    """Reactivate cancelled subscription"""
    subscription = Subscription.query.get_or_404(subscription_id)
    
    # Check permissions
    if not current_user.is_super_admin() and subscription.restaurant_id != current_user.restaurant_id:
        flash('Access denied', 'error')
        return redirect(url_for('subscription.dashboard'))
    
    if subscription.status != 'cancelled':
        flash('Only cancelled subscriptions can be reactivated', 'error')
        return redirect(url_for('subscription.dashboard'))
    
    # Reactivate subscription
    subscription.status = 'active'
    subscription.cancelled_at = None
    subscription.cancellation_reason = None
    subscription.end_date = datetime.utcnow() + timedelta(days=30)
    subscription.next_billing_date = subscription.end_date
    
    db.session.commit()
    
    flash('Subscription reactivated successfully', 'success')
    return redirect(url_for('subscription.dashboard'))

# Super Admin only routes
@bp.route('/admin/plans')
@login_required
def admin_plans():
    """Manage subscription plans (super admin only)"""
    if not current_user.is_super_admin():
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    plans = SubscriptionPlan.query.all()
    return render_template('subscription/admin_plans.html', plans=plans)

@bp.route('/admin/plans/create', methods=['GET', 'POST'])
@login_required
def create_plan():
    """Create new subscription plan (super admin only)"""
    if not current_user.is_super_admin():
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        plan = SubscriptionPlan(
            name=request.form.get('name'),
            plan_type=request.form.get('plan_type'),
            description=request.form.get('description'),
            price_monthly=float(request.form.get('price_monthly') or 0),
            price_yearly=float(request.form.get('price_yearly') or 0),
            currency=request.form.get('currency', 'INR'),
            max_users=int(request.form.get('max_users') or 1),
            max_restaurants=int(request.form.get('max_restaurants') or 1),
            max_orders_per_month=int(request.form.get('max_orders_per_month') or 1000),
            api_access='api_access' in request.form,
            advanced_reporting='advanced_reporting' in request.form,
            priority_support='priority_support' in request.form,
            custom_branding='custom_branding' in request.form,
            is_active='is_active' in request.form
        )
        
        # Set features
        features = request.form.getlist('features')
        plan.set_features_list(features)
        
        db.session.add(plan)
        db.session.commit()
        
        flash('Subscription plan created successfully', 'success')
        return redirect(url_for('subscription.admin_plans'))
    
    return render_template('subscription/plan_form.html', plan=None)

@bp.route('/admin/plans/<int:plan_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_plan(plan_id):
    """Edit subscription plan (super admin only)"""
    if not current_user.is_super_admin():
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    plan = SubscriptionPlan.query.get_or_404(plan_id)
    
    if request.method == 'POST':
        plan.name = request.form.get('name')
        plan.plan_type = request.form.get('plan_type')
        plan.description = request.form.get('description')
        plan.price_monthly = float(request.form.get('price_monthly') or 0)
        plan.price_yearly = float(request.form.get('price_yearly') or 0)
        plan.currency = request.form.get('currency', 'INR')
        plan.max_users = int(request.form.get('max_users') or 1)
        plan.max_restaurants = int(request.form.get('max_restaurants') or 1)
        plan.max_orders_per_month = int(request.form.get('max_orders_per_month') or 1000)
        plan.api_access = 'api_access' in request.form
        plan.advanced_reporting = 'advanced_reporting' in request.form
        plan.priority_support = 'priority_support' in request.form
        plan.custom_branding = 'custom_branding' in request.form
        plan.is_active = 'is_active' in request.form
        
        # Set features
        features = request.form.getlist('features')
        plan.set_features_list(features)
        
        db.session.commit()
        
        flash('Subscription plan updated successfully', 'success')
        return redirect(url_for('subscription.admin_plans'))
    
    return render_template('subscription/plan_form.html', plan=plan)

@bp.route('/admin/subscriptions')
@login_required
def admin_subscriptions():
    """Manage all subscriptions (super admin only)"""
    if not current_user.is_super_admin():
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', '')
    
    query = Subscription.query
    
    if status_filter:
        query = query.filter_by(status=status_filter)
    
    subscriptions = query.order_by(Subscription.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('subscription/admin_subscriptions.html', 
                         subscriptions=subscriptions, 
                         status_filter=status_filter)

# Helper functions
def get_subscription_stats():
    """Get subscription statistics"""
    if current_user.is_super_admin():
        total_subscriptions = Subscription.query.count()
        active_subscriptions = Subscription.query.filter_by(status='active').count()
        trial_subscriptions = Subscription.query.filter_by(status='trial').count()
        cancelled_subscriptions = Subscription.query.filter_by(status='cancelled').count()
        
        monthly_revenue = db.session.query(
            db.func.sum(SubscriptionPayment.amount)
        ).filter(
            SubscriptionPayment.status == 'completed',
            SubscriptionPayment.payment_date >= datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        ).scalar() or 0
    else:
        # Restaurant-specific stats
        restaurant_subscriptions = Subscription.query.filter_by(restaurant_id=current_user.restaurant_id)
        total_subscriptions = restaurant_subscriptions.count()
        active_subscriptions = restaurant_subscriptions.filter_by(status='active').count()
        trial_subscriptions = restaurant_subscriptions.filter_by(status='trial').count()
        cancelled_subscriptions = restaurant_subscriptions.filter_by(status='cancelled').count()
        
        monthly_revenue = 0  # Not relevant for restaurant owners
    
    return {
        'total_subscriptions': total_subscriptions,
        'active_subscriptions': active_subscriptions,
        'trial_subscriptions': trial_subscriptions,
        'cancelled_subscriptions': cancelled_subscriptions,
        'monthly_revenue': monthly_revenue
    }