"""
Credit account management routes
"""
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from sqlalchemy import desc, or_
from datetime import datetime
from app import db
from app.models.customer import Customer
from app.models.credit import CreditAccount, CreditTransaction
from app.models.order import Order

credit_bp = Blueprint('credit', __name__, url_prefix='/billing/credit')

@credit_bp.route('/accounts')
@login_required
def credit_accounts():
    """List all customer credit accounts"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '', type=str)
    status_filter = request.args.get('status', '', type=str)
    
    # Build query
    query = CreditAccount.query.join(Customer)
    
    # Apply search filter
    if search:
        query = query.filter(
            or_(
                Customer.first_name.ilike(f'%{search}%'),
                Customer.last_name.ilike(f'%{search}%'),
                Customer.email.ilike(f'%{search}%'),
                Customer.phone.ilike(f'%{search}%'),
                Customer.company_name.ilike(f'%{search}%')
            )
        )
    
    # Apply status filter
    if status_filter == 'active':
        query = query.filter(CreditAccount.is_active == True)
    elif status_filter == 'inactive':
        query = query.filter(CreditAccount.is_active == False)
    elif status_filter == 'overdue':
        # Filter accounts with overdue balances
        query = query.filter(CreditAccount.current_balance > 0)
    
    # Order by created_at as fallback
    credit_accounts = query.order_by(desc(CreditAccount.created_at)).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('billing/credit_accounts.html', 
                         credit_accounts=credit_accounts,
                         search=search,
                         status_filter=status_filter)

@credit_bp.route('/accounts/<int:account_id>')
@login_required
def credit_account_view(account_id):
    """View credit account details"""
    account = CreditAccount.query.get_or_404(account_id)
    
    # Get recent transactions
    transactions = CreditTransaction.query.filter_by(
        credit_account_id=account_id
    ).order_by(desc(CreditTransaction.created_at)).limit(20).all()
    
    # Get recent orders for this customer
    orders = Order.query.filter_by(customer_id=account.customer_id).order_by(
        desc(Order.created_at)
    ).limit(10).all()
    
    return render_template('billing/credit_account_view.html',
                         account=account,
                         transactions=transactions,
                         orders=orders)

@credit_bp.route('/accounts/<int:account_id>/activate', methods=['GET', 'POST'])
@login_required
def credit_account_activate(account_id):
    """Activate a credit account"""
    account = CreditAccount.query.get_or_404(account_id)
    
    if request.method == 'POST':
        credit_limit = float(request.form.get('credit_limit', 0))
        credit_terms = int(request.form.get('credit_terms', 30))
        approval_limit = float(request.form.get('approval_limit', 0))
        
        if credit_limit <= 0:
            flash('Credit limit must be greater than 0', 'error')
            return render_template('billing/credit_account_activate.html', account=account)
        
        account.credit_limit = credit_limit
        account.credit_terms = credit_terms
        account.approval_limit = approval_limit
        account.is_active = True
        account.update_available_credit()
        
        # Update customer fields for backward compatibility
        customer = account.customer
        customer.credit_limit = credit_limit
        customer.credit_terms = credit_terms
        customer.credit_account_active = True
        customer.available_credit = account.available_credit
        
        db.session.commit()
        
        flash(f'Credit account activated for {customer.get_full_name()}', 'success')
        return redirect(url_for('credit.credit_account_view', account_id=account_id))
    
    return render_template('billing/credit_account_activate.html', account=account)

@credit_bp.route('/accounts/<int:account_id>/deactivate', methods=['POST'])
@login_required
def credit_account_deactivate(account_id):
    """Deactivate a credit account"""
    account = CreditAccount.query.get_or_404(account_id)
    
    account.is_active = False
    
    # Update customer fields for backward compatibility
    customer = account.customer
    customer.credit_account_active = False
    
    db.session.commit()
    
    flash(f'Credit account deactivated for {customer.get_full_name()}', 'success')
    return redirect(url_for('credit.credit_account_view', account_id=account_id))

@credit_bp.route('/accounts/<int:account_id>/payment', methods=['GET', 'POST'])
@login_required
def credit_payment(account_id):
    """Make payment towards credit account"""
    account = CreditAccount.query.get_or_404(account_id)
    
    if request.method == 'POST':
        amount = float(request.form.get('amount', 0))
        payment_method = request.form.get('payment_method', 'CASH')
        notes = request.form.get('notes', '')
        
        if amount <= 0:
            flash('Payment amount must be greater than 0', 'error')
            return render_template('billing/credit_payment.html', account=account)
        
        if amount > account.current_balance:
            flash(f'Payment exceeds current balance of ${account.current_balance:.2f}', 'error')
            return render_template('billing/credit_payment.html', account=account)
        
        try:
            transaction = account.make_payment(
                amount=amount,
                payment_method=payment_method,
                notes=notes,
                created_by=current_user.id
            )
            
            # Update customer fields for backward compatibility
            customer = account.customer
            customer.current_balance = account.current_balance
            customer.available_credit = account.available_credit
            customer.last_credit_activity = account.last_activity
            
            db.session.commit()
            
            flash(f'Payment of ${amount:.2f} processed successfully', 'success')
            return redirect(url_for('credit.credit_account_view', account_id=account_id))
            
        except ValueError as e:
            flash(str(e), 'error')
    
    return render_template('billing/credit_payment.html', account=account)

@credit_bp.route('/accounts/<int:account_id>/adjust', methods=['GET', 'POST'])
@login_required
def credit_adjust(account_id):
    """Adjust credit account balance"""
    account = CreditAccount.query.get_or_404(account_id)
    
    if request.method == 'POST':
        amount = float(request.form.get('amount', 0))
        adjustment_type = request.form.get('adjustment_type', 'MANUAL')
        notes = request.form.get('notes', '')
        
        if amount == 0:
            flash('Adjustment amount cannot be 0', 'error')
            return render_template('billing/credit_adjust.html', account=account)
        
        try:
            transaction = account.adjust_balance(
                amount=amount,
                adjustment_type=adjustment_type,
                notes=notes,
                created_by=current_user.id
            )
            
            # Update customer fields for backward compatibility
            customer = account.customer
            customer.current_balance = account.current_balance
            customer.available_credit = account.available_credit
            customer.last_credit_activity = account.last_activity
            
            db.session.commit()
            
            action = 'increased' if amount > 0 else 'decreased'
            flash(f'Balance {action} by ${abs(amount):.2f}', 'success')
            return redirect(url_for('credit.credit_account_view', account_id=account_id))
            
        except ValueError as e:
            flash(str(e), 'error')
    
    return render_template('billing/credit_adjust.html', account=account)

# API Routes
@credit_bp.route('/api/check-credit/<int:customer_id>')
@login_required
def api_check_credit(customer_id):
    """API endpoint to check customer credit availability"""
    customer = Customer.query.get_or_404(customer_id)
    amount = float(request.args.get('amount', 0))
    
    if amount <= 0:
        return jsonify({'error': 'Invalid amount'}), 400
    
    credit_summary = customer.get_credit_summary()
    
    if not credit_summary['has_credit_account'] or not credit_summary['is_active']:
        return jsonify({
            'can_use_credit': False,
            'message': 'No active credit account'
        })
    
    can_use = customer.can_use_credit(amount)
    
    return jsonify({
        'can_use_credit': can_use,
        'credit_summary': credit_summary,
        'message': 'Credit available' if can_use else 'Insufficient credit'
    })

@credit_bp.route('/api/overdue-accounts')
@login_required
def api_overdue_accounts():
    """API endpoint to get overdue credit accounts"""
    overdue_accounts = []
    
    accounts = CreditAccount.query.filter(
        CreditAccount.current_balance > 0
    ).all()
    
    for account in accounts:
        overdue_amount = account.get_overdue_amount()
        if overdue_amount > 0:
            overdue_accounts.append({
                'id': account.id,
                'customer_name': account.customer.get_full_name(),
                'customer_email': account.customer.email,
                'current_balance': float(account.current_balance),
                'overdue_amount': float(overdue_amount),
                'credit_terms': account.credit_terms,
                'last_activity': account.last_activity.isoformat() if account.last_activity else None
            })
    
    return jsonify({'overdue_accounts': overdue_accounts})