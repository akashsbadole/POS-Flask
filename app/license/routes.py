from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app.license import bp
from app.models.license import License, LicenseActivation, LicenseTemplate, LicenseUsage, LicenseViolation
from app.models.restaurant import Restaurant
from app.models.user import User
from app import db
from datetime import datetime, timedelta
import json

@bp.route('/')
@login_required
def dashboard():
    """License management dashboard"""
    if not current_user.is_super_admin():
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    # Get statistics
    stats = get_license_stats()
    
    return render_template('license/dashboard.html', stats=stats)

@bp.route('/licenses')
@login_required
def licenses():
    """List all licenses"""
    if not current_user.is_super_admin():
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', '')
    license_type_filter = request.args.get('type', '')
    
    query = License.query
    
    # Filter by status
    if status_filter:
        query = query.filter_by(status=status_filter)
    
    # Filter by type
    if license_type_filter:
        query = query.filter_by(license_type=license_type_filter)
    
    licenses = query.order_by(License.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('license/licenses.html', licenses=licenses, status_filter=status_filter, license_type_filter=license_type_filter)

@bp.route('/templates')
@login_required
def templates():
    """Manage license templates"""
    if not current_user.is_super_admin():
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    templates = LicenseTemplate.query.filter_by(is_active=True).order_by(LicenseTemplate.created_at.desc()).all()
    
    return render_template('license/templates.html', templates=templates)

@bp.route('/templates/create', methods=['GET', 'POST'])
@login_required
def create_template():
    """Create new license template"""
    if not current_user.is_super_admin():
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        template = LicenseTemplate(
            name=request.form.get('name'),
            description=request.form.get('description'),
            license_type=request.form.get('license_type'),
            product_name=request.form.get('product_name'),
            default_duration_days=int(request.form.get('default_duration_days', 365)),
            max_activations=int(request.form.get('max_activations', 1)),
            created_by=current_user.id
        )
        
        # Set features
        features = request.form.getlist('features')
        template.set_features_list(features)
        
        # Set restrictions
        restrictions = request.form.getlist('restrictions')
        template.set_restrictions_list(restrictions)
        
        db.session.add(template)
        db.session.commit()
        
        flash('License template created successfully', 'success')
        return redirect(url_for('license.templates'))
    
    return render_template('license/template_form.html', template=None)

@bp.route('/templates/<int:template_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_template(template_id):
    """Edit license template"""
    if not current_user.is_super_admin():
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    template = LicenseTemplate.query.get_or_404(template_id)
    
    if request.method == 'POST':
        template.name = request.form.get('name')
        template.description = request.form.get('description')
        template.license_type = request.form.get('license_type')
        template.product_name = request.form.get('product_name')
        template.default_duration_days = int(request.form.get('default_duration_days', 365))
        template.max_activations = int(request.form.get('max_activations', 1))
        
        # Set features
        features = request.form.getlist('features')
        template.set_features_list(features)
        
        # Set restrictions
        restrictions = request.form.getlist('restrictions')
        template.set_restrictions_list(restrictions)
        
        db.session.commit()
        
        flash('License template updated successfully', 'success')
        return redirect(url_for('license.templates'))
    
    return render_template('license/template_form.html', template=template)

@bp.route('/licenses/<int:license_id>')
@login_required
def view_license(license_id):
    """View license details"""
    if not current_user.is_super_admin():
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    license = License.query.get_or_404(license_id)
    
    # Get activations
    activations = LicenseActivation.query.filter_by(license_id=license_id).order_by(LicenseActivation.activated_at.desc()).all()
    
    # Get usage statistics
    usage_stats = LicenseUsage.query.filter_by(license_id=license_id).order_by(LicenseUsage.usage_date.desc()).limit(30).all()
    
    return render_template('license/view.html', license=license, activations=activations, usage_stats=usage_stats)

@bp.route('/licenses/<int:license_id>/activate', methods=['POST'])
@login_required
def activate_license(license_id):
    """Activate license"""
    if not current_user.is_super_admin():
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    license = License.query.get_or_404(license_id)
    
    if request.method == 'POST':
        device_id = request.form.get('device_id')
        user_id = request.form.get('user_id', type=int)
        
        success, message = license.activate(device_id=device_id, user_id=user_id)
        
        if success:
            flash(message, 'success')
        else:
            flash(message, 'error')
    
    return redirect(url_for('license.view_license', license_id=license_id))

@bp.route('/licenses/<int:license_id>/deactivate', methods=['POST'])
@login_required
def deactivate_license(license_id):
    """Deactivate license"""
    if not current_user.is_super_admin():
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    license = License.query.get_or_404(license_id)
    
    if request.method == 'POST':
        device_id = request.form.get('device_id')
        user_id = request.form.get('user_id', type=int)
        
        success, message = license.deactivate(device_id=device_id, user_id=user_id)
        
        if success:
            flash(message, 'success')
        else:
            flash(message, 'error')
    
    return redirect(url_for('license.view_license', license_id=license_id))

@bp.route('/licenses/<int:license_id>/verify', methods=['POST'])
@login_required
def verify_license(license_id):
    """Verify license"""
    if not current_user.is_super_admin():
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    license = License.query.get_or_404(license_id)
    
    if request.method == 'POST':
        success, message = license.verify_license()
        
        if success:
            flash(message, 'success')
        else:
            flash(message, 'error')
    
    return redirect(url_for('license.view_license', license_id=license_id))

@bp.route('/licenses/generate', methods=['GET', 'POST'])
@login_required
def generate_license():
    """Generate new license from template"""
    if not current_user.is_super_admin():
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        template_id = request.form.get('template_id', type=int)
        restaurant_id = request.form.get('restaurant_id', type=int)
        user_id = request.form.get('user_id', type=int)
        device_id = request.form.get('device_id')
        duration_days = int(request.form.get('duration_days', 365))
        
        template = LicenseTemplate.query.get_or_404(template_id)
        
        # Generate unique license key
        import uuid
        license_key = str(uuid.uuid4()).upper()
        
        # Create license
        license = License(
            license_key=license_key,
            license_type=template.license_type,
            product_name=template.product_name,
            product_version=template.product_version,
            restaurant_id=restaurant_id,
            user_id=user_id,
            device_id=device_id,
            status='active',
            issued_date=datetime.utcnow(),
            expiry_date=datetime.utcnow() + timedelta(days=duration_days),
            max_activations=template.max_activations
        )
        
        # Copy features and restrictions from template
        license.set_features_list(template.get_features_list())
        license.set_restrictions_list(template.get_restrictions_list())
        
        db.session.add(license)
        db.session.commit()
        
        flash('License generated successfully', 'success')
        return redirect(url_for('license.view_license', license_id=license.id))
    
    # GET request - show generate form
    templates = LicenseTemplate.query.filter_by(is_active=True).all()
    restaurants = Restaurant.query.all()
    users = User.query.all()
    
    return render_template('license/generate.html', templates=templates, restaurants=restaurants, users=users)

@bp.route('/violations')
@login_required
def violations():
    """View license violations"""
    if not current_user.is_super_admin():
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    page = request.args.get('page', 1, type=int)
    severity_filter = request.args.get('severity', '')
    
    query = LicenseViolation.query
    
    if severity_filter:
        query = query.filter_by(severity=severity_filter)
    
    violations = query.order_by(LicenseViolation.detected_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('license/violations.html', violations=violations, severity_filter=severity_filter)

@bp.route('/usage')
@login_required
def usage():
    """License usage statistics"""
    if not current_user.is_super_admin():
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    page = request.args.get('page', 1, type=int)
    license_id_filter = request.args.get('license_id', type=int)
    
    query = LicenseUsage.query
    
    if license_id_filter:
        query = query.filter_by(license_id=license_id_filter)
    
    usage = query.order_by(LicenseUsage.usage_date.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('license/usage.html', usage=usage, license_id_filter=license_id_filter)

@bp.route('/api/license/<int:license_id>/check')
@login_required
def api_check_license(license_id):
    """API endpoint to check license validity"""
    license = License.query.get_or_404(license_id)
    
    return jsonify({
        'valid': license.is_valid(),
        'expired': license.is_expired(),
        'days_until_expiry': license.days_until_expiry(),
        'current_activations': license.current_activations,
        'max_activations': license.max_activations,
        'license_key': license.license_key,
        'product_name': license.product_name,
        'license_type': license.license_type.value if license.license_type else None,
        'features': license.get_features_list(),
        'restrictions': license.get_restrictions_list()
    })

@bp.route('/api/licenses/bulk-activate', methods=['POST'])
@login_required
def api_bulk_activate_licenses():
    """Bulk activate licenses"""
    if not current_user.is_super_admin():
        return jsonify({'error': 'Access denied'}), 403
    
    data = request.get_json()
    license_keys = data.get('license_keys', [])
    device_id = data.get('device_id')
    user_id = data.get('user_id')
    
    results = []
    errors = []
    
    for license_key in license_keys:
        license = License.query.filter_by(license_key=license_key).first()
        if license:
            success, message = license.activate(device_id=device_id, user_id=user_id)
            if success:
                results.append({
                    'license_key': license_key,
                    'success': True,
                    'message': message
                })
            else:
                errors.append({
                    'license_key': license_key,
                    'error': message
                })
        else:
            errors.append({
                'license_key': license_key,
                'error': 'License not found'
            })
    
    return jsonify({
        'results': results,
        'errors': errors,
        'total_processed': len(license_keys),
        'success_count': len(results),
        'error_count': len(errors)
    })

@bp.route('/api/licenses/<int:license_id>/usage-track', methods=['POST'])
@login_required
def api_track_usage(license_id):
    """Track license usage"""
    if not current_user.is_super_admin():
        return jsonify({'error': 'Access denied'}), 403
    
    license = License.query.get_or_404(license_id)
    data = request.get_json()
    
    usage = LicenseUsage(
        license_id=license_id,
        usage_count=data.get('usage_count', 1),
        feature_usage=data.get('feature_usage', '{}'),
        user_id=data.get('user_id'),
        device_id=data.get('device_id'),
        api_calls=data.get('api_calls', 0),
        data_transferred_mb=data.get('data_transferred_mb', 0.0),
        active_sessions=data.get('active_sessions', 0),
        peak_concurrent_users=data.get('peak_concurrent_users', 0)
    )
    
    db.session.add(usage)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Usage tracked successfully',
        'usage_id': usage.id
    })

@bp.route('/api/licenses/validate', methods=['POST'])
@login_required
def api_validate_license():
    """Validate license key"""
    data = request.get_json()
    license_key = data.get('license_key')
    
    if not license_key:
        return jsonify({
            'valid': False,
            'error': 'License key is required'
        }), 400
    
    license = License.query.filter_by(license_key=license_key).first()
    
    if not license:
        return jsonify({
            'valid': False,
            'error': 'Invalid license key'
        }), 404
    
    # Check if license is valid and not expired
    is_valid = license.is_valid() and not license.is_expired()
    
    return jsonify({
        'valid': is_valid,
        'license': {
            'id': license.id,
            'license_key': license.license_key,
            'product_name': license.product_name,
            'license_type': license.license_type.value if license.license_type else None,
            'status': license.status.value if license.status else None,
            'expiry_date': license.expiry_date.isoformat() if license.expiry_date else None,
            'days_until_expiry': license.days_until_expiry(),
            'features': license.get_features_list(),
            'restrictions': license.get_restrictions_list(),
            'current_activations': license.current_activations,
            'max_activations': license.max_activations
        }
    })

@bp.route('/api/licenses/expiring', methods=['GET'])
@login_required
def api_expiring_licenses():
    """Get licenses expiring soon"""
    if not current_user.is_super_admin():
        return jsonify({'error': 'Access denied'}), 403
    
    days = request.args.get('days', 30, type=int)
    threshold_date = datetime.utcnow() + timedelta(days=days)
    
    expiring_licenses = License.query.filter(
        License.expiry_date <= threshold_date,
        License.expiry_date > datetime.utcnow(),
        License.status == 'active'
    ).order_by(License.expiry_date.asc()).all()
    
    return jsonify({
        'expiring_licenses': [license.to_dict() for license in expiring_licenses],
        'days_threshold': days,
        'count': len(expiring_licenses)
    })

@bp.route('/api/licenses/violations/check', methods=['POST'])
@login_required
def api_check_violations():
    """Check for license violations"""
    if not current_user.is_super_admin():
        return jsonify({'error': 'Access denied'}), 403
    
    data = request.get_json()
    license_id = data.get('license_id')
    user_id = data.get('user_id')
    device_id = data.get('device_id')
    
    license = License.query.get_or_404(license_id)
    
    violations = []
    
    # Check for overuse violations
    usage_count = LicenseUsage.query.filter_by(license_id=license_id).count()
    if usage_count > 1000:  # Example threshold
        violations.append({
            'type': 'overuse',
            'description': f'Usage count ({usage_count}) exceeds allowed limit',
            'severity': 'high'
        })
    
    # Check for concurrent activation violations
    if license.current_activations > license.max_activations:
        violations.append({
            'type': 'concurrent_activation',
            'description': f'Current activations ({license.current_activations}) exceeds maximum ({license.max_activations})',
            'severity': 'medium'
        })
    
    # Record violations if any found
    if violations:
        for violation_data in violations:
            violation = LicenseViolation(
                license_id=license_id,
                violation_type=violation_data['type'],
                description=violation_data['description'],
                severity=violation_data['severity'],
                user_id=user_id,
                device_id=device_id
            )
            db.session.add(violation)
        
        db.session.commit()
    
    return jsonify({
        'violations': violations,
        'has_violations': len(violations) > 0,
        'license_id': license_id
    })

# Helper functions
def get_license_stats():
    """Get license statistics"""
    total_licenses = License.query.count()
    active_licenses = License.query.filter_by(status='active').count()
    expired_licenses = License.query.filter(License.expiry_date < datetime.utcnow()).count()
    suspended_licenses = License.query.filter_by(status='suspended').count()
    total_activations = LicenseActivation.query.count()
    recent_activations = LicenseActivation.query.filter(
        LicenseActivation.activated_at >= datetime.utcnow() - timedelta(days=7)
    ).count()
    total_violations = LicenseViolation.query.count()
    
    return {
        'total_licenses': total_licenses,
        'active_licenses': active_licenses,
        'expired_licenses': expired_licenses,
        'suspended_licenses': suspended_licenses,
        'total_activations': total_activations,
        'recent_activations': recent_activations,
        'total_violations': total_violations
    }