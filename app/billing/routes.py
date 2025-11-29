from flask import render_template, request, redirect, url_for, flash, jsonify, make_response
from flask_login import login_required, current_user
from app.billing import bp
from app.models.billing import Invoice, InvoiceItem, InvoicePayment, BillingSetting, RecurringInvoice
from app.models.order import Order
from app.models.restaurant import Restaurant
from app import db
from datetime import datetime, timedelta
import csv
from io import StringIO
from flask import make_response

@bp.route('/')
@login_required
def dashboard():
    """Billing dashboard"""
    if not current_user.can_access_manager_features():
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    # Get statistics
    stats = get_billing_stats()
    
    return render_template('billing/dashboard.html', stats=stats)

@bp.route('/invoices')
@login_required
def invoices():
    """List invoices"""
    if not current_user.can_access_manager_features():
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', '')
    
    query = Invoice.query
    
    # Filter by restaurant if not super admin
    if not current_user.is_super_admin():
        query = query.filter_by(restaurant_id=current_user.restaurant_id)
    
    # Filter by status
    if status_filter:
        query = query.filter_by(status=status_filter)
    
    invoices = query.order_by(Invoice.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('billing/invoices.html', invoices=invoices, status_filter=status_filter)

@bp.route('/invoice/new', methods=['GET', 'POST'])
@bp.route('/invoices/create', methods=['GET', 'POST'])
@login_required
def create_invoice():
    """Create new invoice"""
    if not current_user.can_access_manager_features():
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        # Get billing settings
        billing_settings = BillingSetting.query.filter_by(
            restaurant_id=current_user.restaurant_id
        ).first()
        
        if not billing_settings:
            flash('Billing settings not configured', 'error')
            return redirect(url_for('billing.invoices'))
        
        # Create invoice
        invoice = Invoice(
            invoice_number=billing_settings.generate_invoice_number(),
            restaurant_id=current_user.restaurant_id,
            customer_name=request.form.get('customer_name'),
            customer_email=request.form.get('customer_email'),
            customer_phone=request.form.get('customer_phone'),
            customer_address=request.form.get('customer_address'),
            issue_date=datetime.strptime(request.form.get('issue_date', ''), '%Y-%m-%d') if request.form.get('issue_date') else datetime.utcnow(),
            due_date=datetime.strptime(request.form.get('due_date', ''), '%Y-%m-%d') if request.form.get('due_date') else None,
            terms=request.form.get('terms'),
            notes=request.form.get('notes'),
            subtotal=0.00,  # Initialize with 0, will be calculated after items are added
            tax_amount=0.00,
            total_amount=0.00,
            balance_amount=0.00
        )
        
        db.session.add(invoice)
        db.session.flush()  # Get invoice ID
        
        # Add invoice items
        item_descriptions = request.form.getlist('item_description[]')
        item_quantities = request.form.getlist('item_quantity[]')
        item_prices = request.form.getlist('item_price[]')
        item_tax_rates = request.form.getlist('item_tax_rate[]')
        
        for i, description in enumerate(item_descriptions):
            if description and i < len(item_quantities) and i < len(item_prices):
                quantity = float(item_quantities[i]) if item_quantities[i] else 0
                unit_price = float(item_prices[i]) if item_prices[i] else 0
                tax_rate = float(item_tax_rates[i]) if item_tax_rates[i] else 0
                
                # Calculate tax amount
                subtotal = quantity * unit_price
                tax_amount = subtotal * (tax_rate / 100)
                
                invoice_item = InvoiceItem(
                    invoice_id=invoice.id,
                    description=description,
                    quantity=quantity,
                    unit_price=unit_price,
                    discount_amount=0.00,  # Initialize with 0
                    tax_rate=tax_rate,
                    tax_amount=tax_amount
                )
                invoice_item.calculate_totals()
                db.session.add(invoice_item)
        
        # Calculate invoice totals
        invoice.calculate_totals()
        
        db.session.commit()
        
        flash('Invoice created successfully', 'success')
        return redirect(url_for('billing.view_invoice', invoice_id=invoice.id))
    
    # Get billing settings
    billing_settings = BillingSetting.query.filter_by(
        restaurant_id=current_user.restaurant_id
    ).first()
    
    return render_template('billing/invoice_form.html', invoice=None, billing_settings=billing_settings)

@bp.route('/invoices/<int:invoice_id>')
@login_required
def view_invoice(invoice_id):
    """View invoice details"""
    invoice = Invoice.query.get_or_404(invoice_id)
    
    # Check permissions
    if not current_user.is_super_admin() and invoice.restaurant_id != current_user.restaurant_id:
        flash('Access denied', 'error')
        return redirect(url_for('billing.invoices'))
    
    return render_template('billing/invoice_view.html', invoice=invoice)

@bp.route('/invoices/<int:invoice_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_invoice(invoice_id):
    """Edit existing invoice"""
    if not current_user.can_access_manager_features():
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    invoice = Invoice.query.get_or_404(invoice_id)
    
    # Check permissions
    if not current_user.is_super_admin() and invoice.restaurant_id != current_user.restaurant_id:
        flash('Access denied', 'error')
        return redirect(url_for('billing.invoices'))
    
    if request.method == 'POST':
        invoice.customer_name = request.form.get('customer_name')
        invoice.customer_email = request.form.get('customer_email')
        invoice.customer_phone = request.form.get('customer_phone')
        invoice.customer_address = request.form.get('customer_address')
        issue_date_str = request.form.get('issue_date')
        invoice.issue_date = datetime.strptime(issue_date_str, '%Y-%m-%d') if issue_date_str else invoice.issue_date
        due_date_str = request.form.get('due_date')
        invoice.due_date = datetime.strptime(due_date_str, '%Y-%m-%d') if due_date_str else invoice.due_date
        invoice.terms = request.form.get('terms')
        invoice.notes = request.form.get('notes')
        
        # Update existing items
        InvoiceItem.query.filter_by(invoice_id=invoice.id).delete()
        
        # Add updated items
        item_descriptions = request.form.getlist('item_description[]')
        item_quantities = request.form.getlist('item_quantity[]')
        item_prices = request.form.getlist('item_price[]')
        item_tax_rates = request.form.getlist('item_tax_rate[]')
        
        for i, description in enumerate(item_descriptions):
            if description and i < len(item_quantities) and i < len(item_prices):
                invoice_item = InvoiceItem(
                    invoice_id=invoice.id,
                    description=description,
                    quantity=float(item_quantities[i]) if item_quantities[i] else 0,
                    unit_price=float(item_prices[i]) if item_prices[i] else 0,
                    tax_rate=float(item_tax_rates[i]) if item_tax_rates[i] else 0,
                    tax_amount=float(item_quantities[i]) * float(item_prices[i]) * (float(item_tax_rates[i]) if item_tax_rates[i] else 0)
                )
                invoice_item.calculate_totals()
                db.session.add(invoice_item)
        
        # Recalculate totals
        invoice.calculate_totals()
        
        db.session.commit()
        
        flash('Invoice updated successfully', 'success')
        return redirect(url_for('billing.view_invoice', invoice_id=invoice.id))
    
    billing_settings = BillingSetting.query.filter_by(
        restaurant_id=current_user.restaurant_id
    ).first()
    
    return render_template('billing/invoice_form.html', invoice=invoice, billing_settings=billing_settings)

@bp.route('/invoices/<int:invoice_id>/delete', methods=['POST'])
@login_required
def delete_invoice(invoice_id):
    """Delete invoice"""
    if not current_user.can_access_manager_features():
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    invoice = Invoice.query.get_or_404(invoice_id)
    
    # Check permissions
    if not current_user.is_super_admin() and invoice.restaurant_id != current_user.restaurant_id:
        flash('Access denied', 'error')
        return redirect(url_for('billing.invoices'))
    
    db.session.delete(invoice)
    db.session.commit()
    
    flash('Invoice deleted successfully', 'success')
    return redirect(url_for('billing.invoices'))

@bp.route('/invoices/<int:invoice_id>/send', methods=['POST'])
@login_required
def send_invoice(invoice_id):
    """Send invoice to customer"""
    if not current_user.can_access_manager_features():
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    invoice = Invoice.query.get_or_404(invoice_id)
    
    # Check permissions
    if not current_user.is_super_admin() and invoice.restaurant_id != current_user.restaurant_id:
        flash('Access denied', 'error')
        return redirect(url_for('billing.invoices'))
    
    # Mark as sent
    invoice.mark_as_sent()
    db.session.commit()
    
    # TODO: Implement email sending
    flash('Invoice marked as sent', 'success')
    return redirect(url_for('billing.view_invoice', invoice_id=invoice_id))

@bp.route('/invoices/<int:invoice_id>/print')
@login_required
def print_invoice(invoice_id):
    """Generate printable invoice"""
    if not current_user.can_access_manager_features():
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    invoice = Invoice.query.get_or_404(invoice_id)
    
    # Check permissions
    if not current_user.is_super_admin() and invoice.restaurant_id != current_user.restaurant_id:
        flash('Access denied', 'error')
        return redirect(url_for('billing.invoices'))
    
    # Generate HTML for printing
    html_content = render_template('billing/invoice_print.html', invoice=invoice)
    
    # For now, just return HTML content for browser printing
    # PDF generation can be added later with a proper PDF library
    return html_content
    
    return redirect(url_for('billing.view_invoice', invoice_id=invoice_id))

@bp.route('/invoices/<int:invoice_id>/payment', methods=['POST'])
@login_required
def add_payment(invoice_id):
    """Add payment to invoice"""
    if not current_user.can_access_manager_features():
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    invoice = Invoice.query.get_or_404(invoice_id)
    
    # Check permissions
    if not current_user.is_super_admin() and invoice.restaurant_id != current_user.restaurant_id:
        flash('Access denied', 'error')
        return redirect(url_for('billing.invoices'))
    
    payment_date_str = request.form.get('payment_date')
    payment = InvoicePayment(
        invoice_id=invoice_id,
        amount=request.form.get('amount', type=float),
        payment_method=request.form.get('payment_method'),
        transaction_id=request.form.get('transaction_id'),
        reference_number=request.form.get('reference_number'),
        notes=request.form.get('notes'),
        payment_date=datetime.strptime(payment_date_str, '%Y-%m-%d') if payment_date_str else datetime.utcnow()
    )
    
    db.session.add(payment)
    
    # Update invoice paid amount
    invoice.mark_as_paid(payment.amount)
    
    db.session.commit()
    
    flash('Payment added successfully', 'success')
    return redirect(url_for('billing.view_invoice', invoice_id=invoice_id))

@bp.route('/recurring')
@login_required
def recurring_invoices():
    """Manage recurring invoices"""
    if not current_user.can_access_manager_features():
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    page = request.args.get('page', 1, type=int)
    
    query = RecurringInvoice.query
    
    # Filter by restaurant if not super admin
    if not current_user.is_super_admin():
        query = query.filter_by(restaurant_id=current_user.restaurant_id)
    
    recurring_invoices = query.filter_by(is_active=True).order_by(RecurringInvoice.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('billing/recurring.html', recurring_invoices=recurring_invoices)

@bp.route('/recurring/create', methods=['GET', 'POST'])
@login_required
def create_recurring():
    """Create recurring invoice"""
    if not current_user.can_access_manager_features():
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        start_date_str = request.form.get('start_date')
        end_date_str = request.form.get('end_date')
        recurring_invoice = RecurringInvoice(
            restaurant_id=current_user.restaurant_id,
            customer_name=request.form.get('customer_name'),
            customer_email=request.form.get('customer_email'),
            description=request.form.get('description'),
            amount=request.form.get('amount', type=float),
            frequency=request.form.get('frequency'),
            interval_count=request.form.get('interval_count', type=int, default=1),
            start_date=datetime.strptime(start_date_str, '%Y-%m-%d') if start_date_str else datetime.utcnow(),
            end_date=datetime.strptime(end_date_str, '%Y-%m-%d') if end_date_str else None
        )
        
        db.session.add(recurring_invoice)
        db.session.commit()
        
        flash('Recurring invoice created successfully', 'success')
        return redirect(url_for('billing.recurring'))
    
    return render_template('billing/recurring_form.html', recurring_invoice=None)

@bp.route('/recurring/<int:recurring_id>/toggle', methods=['POST'])
@login_required
def toggle_recurring(recurring_id):
    """Toggle recurring invoice active status"""
    if not current_user.can_access_manager_features():
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    recurring_invoice = RecurringInvoice.query.get_or_404(recurring_id)
    
    # Check permissions
    if not current_user.is_super_admin() and recurring_invoice.restaurant_id != current_user.restaurant_id:
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    recurring_invoice.is_active = not recurring_invoice.is_active
    db.session.commit()
    
    return jsonify({'success': True, 'active': recurring_invoice.is_active})

@bp.route('/settings')
@login_required
def settings():
    """Billing settings"""
    if not current_user.can_access_manager_features():
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    billing_settings = BillingSetting.query.filter_by(
        restaurant_id=current_user.restaurant_id
    ).first()
    
    if request.method == 'POST':
        if not billing_settings:
            billing_settings = BillingSetting(restaurant_id=current_user.restaurant_id)
            db.session.add(billing_settings)
        
        billing_settings.invoice_prefix = request.form.get('invoice_prefix', 'INV')
        billing_settings.auto_generate_numbers = 'auto_generate_numbers' in request.form
        billing_settings.default_payment_terms = request.form.get('default_payment_terms', type=int, default=30)
        billing_settings.allow_partial_payments = 'allow_partial_payments' in request.form
        billing_settings.auto_send_reminders = 'auto_send_reminders' in request.form
        billing_settings.reminder_days = request.form.get('reminder_days', '7,14,30')
        billing_settings.default_tax_rate = request.form.get('default_tax_rate', type=float, default=0.18)
        billing_settings.tax_inclusive = 'tax_inclusive' in request.form
        billing_settings.currency_code = request.form.get('currency_code', 'INR')
        billing_settings.currency_symbol = request.form.get('currency_symbol', '₹')
        billing_settings.email_from_address = request.form.get('email_from_address')
        billing_settings.email_from_name = request.form.get('email_from_name')
        billing_settings.email_cc_addresses = request.form.get('email_cc_addresses')
        
        db.session.commit()
        
        flash('Billing settings updated successfully', 'success')
        return redirect(url_for('billing.settings'))
    
    return render_template('billing/settings.html', billing_settings=billing_settings)

@bp.route('/export/invoices')
@login_required
def export_invoices():
    """Export invoices as CSV"""
    if not current_user.can_access_manager_features():
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    status_filter = request.args.get('status', '')
    
    query = Invoice.query
    
    # Filter by restaurant if not super admin
    if not current_user.is_super_admin():
        query = query.filter_by(restaurant_id=current_user.restaurant_id)
    
    # Filter by status
    if status_filter:
        query = query.filter_by(status=status_filter)
    
    invoices = query.order_by(Invoice.created_at.desc()).all()
    
    # Create CSV
    output = StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow([
        'Invoice Number', 'Customer Name', 'Email', 'Issue Date', 'Due Date', 
        'Status', 'Subtotal', 'Tax Amount', 'Total Amount', 'Paid Amount', 'Balance'
    ])
    
    # Write data
    for invoice in invoices:
        writer.writerow([
            invoice.invoice_number,
            invoice.customer_name,
            invoice.customer_email,
            invoice.issue_date.strftime('%Y-%m-%d') if invoice.issue_date else '',
            invoice.due_date.strftime('%Y-%m-%d') if invoice.due_date else '',
            invoice.status,
            invoice.subtotal,
            invoice.tax_amount,
            invoice.total_amount,
            invoice.paid_amount,
            invoice.balance_amount
        ])
    
    # Create response
    output.seek(0)
    response = make_response(output.getvalue())
    response.headers['Content-Disposition'] = 'attachment; filename=invoices.csv'
    response.headers['Content-type'] = 'text/csv'
    
    return response

# Helper functions
def get_billing_stats():
    """Get billing statistics"""
    query = Invoice.query
    
    # Filter by restaurant if not super admin
    if not current_user.is_super_admin():
        query = query.filter_by(restaurant_id=current_user.restaurant_id)
    
    # Get counts
    total_invoices = query.count()
    draft_invoices = query.filter_by(status='draft').count()
    sent_invoices = query.filter_by(status='sent').count()
    paid_invoices = query.filter_by(status='paid').count()
    overdue_invoices = sum(1 for invoice in query.all() if invoice.check_overdue())
    
    # Calculate totals
    total_amount = sum(float(invoice.total_amount) for invoice in query.all())
    paid_amount = sum(float(invoice.paid_amount) for invoice in query.all())
    outstanding_amount = total_amount - paid_amount
    
    return {
        'total_invoices': total_invoices,
        'draft_invoices': draft_invoices,
        'sent_invoices': sent_invoices,
        'paid_invoices': paid_invoices,
        'overdue_invoices': overdue_invoices,
        'total_amount': total_amount,
        'paid_amount': paid_amount,
        'outstanding_amount': outstanding_amount
    }