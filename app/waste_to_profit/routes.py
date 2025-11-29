"""
Waste-to-Profit Module Routes
Provides REST API endpoints for all waste management and profit optimization features
"""

from flask import render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta
import logging
from sqlalchemy import text as db_text

from app import db
from app.waste_to_profit import bp
from app.waste_to_profit.services.expiry_tracking_service import ExpiryTrackingService
from app.waste_to_profit.services.waste_analytics_service import WasteAnalyticsService
from app.waste_to_profit.services.chef_special_service import ChefSpecialService
from app.waste_to_profit.services.inventory_optimization_service import InventoryOptimizationService
from app.waste_to_profit.services.sustainability_service import SustainabilityService
from app.waste_to_profit.services.staff_training_service import StaffTrainingService

# Initialize services
expiry_service = ExpiryTrackingService()
analytics_service = WasteAnalyticsService()
chef_service = ChefSpecialService()
optimization_service = InventoryOptimizationService()
sustainability_service = SustainabilityService()
training_service = StaffTrainingService()

logger = logging.getLogger(__name__)


# Dashboard Routes
@bp.route('/')
@login_required
def dashboard():
    """Waste-to-Profit dashboard"""
    try:
        # Get overview data
        expiring_count = len(expiry_service.get_expiring_items(days_ahead=7))
        active_specials = len(chef_service.get_active_chef_specials())
        monthly_savings = analytics_service.get_waste_overview(
            start_date=date.today() - timedelta(days=30),
            end_date=date.today()
        ).get('total_waste_cost', 0)
        
        return render_template('waste_to_profit/dashboard.html',
                         expiring_count=expiring_count,
                         active_specials=active_specials,
                         monthly_savings=monthly_savings)
    except Exception as e:
        logger.error(f"Error loading dashboard: {str(e)}")
        flash('Error loading dashboard', 'error')
        return redirect(url_for('waste_to_profit.dashboard'))


# Expiry Tracking Routes
@bp.route('/expiry-tracking')
@login_required
def expiry_tracking():
    """Expiry tracking page"""
    try:
        # Get expiring items
        expiring_items = expiry_service.get_expiring_items(days_ahead=14)
        
        return render_template('waste_to_profit/expiry_tracking.html',
                         expiring_items=expiring_items)
    except Exception as e:
        logger.error(f"Error loading expiry tracking: {str(e)}")
        flash('Error loading expiry tracking', 'error')
        return redirect(url_for('waste_to_profit.dashboard'))


@bp.route('/expiry-tracking/fifo')
@login_required
def fifo_recommendations():
    """FIFO recommendations page"""
    try:
        # Get FIFO recommendations
        recommendations = expiry_service.get_fifo_recommendations()
        
        return render_template('waste_to_profit/fifo_recommendations.html',
                         recommendations=recommendations)
    except Exception as e:
        logger.error(f"Error loading FIFO recommendations: {str(e)}")
        flash('Error loading FIFO recommendations', 'error')
        return redirect(url_for('waste_to_profit.dashboard'))


@bp.route('/expiry-tracking/add', methods=['GET', 'POST'])
@login_required
def add_expiry_tracking():
    """Add expiry tracking record"""
    if request.method == 'GET':
        ingredients = db.session.execute(db_text('SELECT id, name FROM ingredients ORDER BY name')).fetchall()
        return render_template('waste_to_profit/add_expiry_tracking.html', ingredients=ingredients)
    
    try:
        # Get form data
        ingredient_id = request.form.get('ingredient_id', type=int)
        batch_number = request.form.get('batch_number') or ''
        lot_number = request.form.get('lot_number') or ''
        expiry_date_str = request.form.get('expiry_date', '')
        expiry_date = datetime.strptime(expiry_date_str, '%Y-%m-%d').date() if expiry_date_str else date.today()
        quantity = float(request.form.get('quantity', '0') or '0')
        unit_cost = float(request.form.get('unit_cost', '0') or '0')
        supplier_id = request.form.get('supplier_id', type=int) if request.form.get('supplier_id') else None
        storage_location = request.form.get('storage_location') or ''
        
        # Create expiry tracking record
        expiry_service.create_expiry_tracking(
            ingredient_id=ingredient_id or 0,
            batch_number=batch_number,
            lot_number=lot_number,
            expiry_date=expiry_date,
            quantity=quantity,
            unit_cost=unit_cost,
            supplier_id=supplier_id or 0,
            storage_location=storage_location,
            user_id=current_user.id
        )
        
        flash('Expiry tracking record created successfully', 'success')
        return redirect(url_for('waste_to_profit.expiry_tracking'))
        
    except Exception as e:
        logger.error(f"Error adding expiry tracking: {str(e)}")
        flash('Error creating expiry tracking record', 'error')
        return redirect(url_for('waste_to_profit.add_expiry_tracking'))


@bp.route('/expiry-tracking/alerts')
@login_required
def check_expiry_alerts():
    """Check and send expiry alerts"""
    try:
        # Check and send alerts
        alert_counts = expiry_service.check_and_send_alerts()
        
        return jsonify({
            'success': True,
            'alert_counts': alert_counts,
            'message': f"Alerts sent: {sum(alert_counts.values())} total"
        })
        
    except Exception as e:
        logger.error(f"Error checking expiry alerts: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


# Waste Analytics Routes
@bp.route('/analytics')
@login_required
def waste_analytics():
    """Waste analytics dashboard"""
    try:
        # Get waste overview
        overview = analytics_service.get_waste_overview(
            start_date=date.today() - timedelta(days=30),
            end_date=date.today()
        )
        
        return render_template('waste_to_profit/analytics.html',
                         overview=overview)
    except Exception as e:
        logger.error(f"Error loading waste analytics: {str(e)}")
        flash('Error loading waste analytics', 'error')
        return redirect(url_for('waste_to_profit.dashboard'))


@bp.route('/analytics/patterns')
@login_required
def waste_patterns():
    """Waste pattern analysis"""
    try:
        # Get pattern analysis
        patterns = analytics_service.analyze_waste_patterns(days_back=90)
        
        return render_template('waste_to_profit/waste_patterns.html',
                         patterns=patterns)
    except Exception as e:
        logger.error(f"Error analyzing waste patterns: {str(e)}")
        flash('Error analyzing waste patterns', 'error')
        return redirect(url_for('waste_to_profit.dashboard'))


@bp.route('/analytics/cost')
@login_required
def cost_analysis():
    """Cost of waste analysis"""
    try:
        # Get cost analysis
        cost_analysis = analytics_service.calculate_cost_of_waste(
            start_date=date.today() - timedelta(days=30),
            end_date=date.today()
        )
        
        return render_template('waste_to_profit/cost_analysis.html',
                         cost_analysis=cost_analysis)
    except Exception as e:
        logger.error(f"Error analyzing cost of waste: {str(e)}")
        flash('Error analyzing cost of waste', 'error')
        return redirect(url_for('waste_to_profit.dashboard'))


@bp.route('/analytics/recommendations')
@login_required
def waste_recommendations():
    """Waste reduction recommendations"""
    try:
        # Get recommendations
        recommendations = analytics_service.get_waste_reduction_recommendations(days_back=30)
        
        return render_template('waste_to_profit/waste_recommendations.html',
                         recommendations=recommendations)
    except Exception as e:
        logger.error(f"Error getting waste recommendations: {str(e)}")
        flash('Error getting waste recommendations', 'error')
        return redirect(url_for('waste_to_profit.dashboard'))


@bp.route('/analytics/department/<department>')
@login_required
def department_analysis(department):
    """Department-wise waste analysis"""
    try:
        # Get department analysis
        analysis = analytics_service.get_department_wise_analysis(department=department, days_back=30)
        
        return render_template('waste_to_profit/department_analysis.html',
                         department=department,
                         analysis=analysis)
    except Exception as e:
        logger.error(f"Error analyzing department: {str(e)}")
        flash('Error analyzing department', 'error')
        return redirect(url_for('waste_to_profit.dashboard'))


# Chef's Special Routes
@bp.route('/chef-specials')
@login_required
def chef_specials():
    """Chef's Specials listing"""
    try:
        # Get active specials
        specials = chef_service.get_active_chef_specials()
        
        return render_template('waste_to_profit/chef_specials.html',
                         specials=specials)
    except Exception as e:
        logger.error(f"Error loading Chef's Specials: {str(e)}")
        flash('Error loading Chef\'s Specials', 'error')
        return redirect(url_for('waste_to_profit.dashboard'))


@bp.route('/chef-specials/suggestions')
@login_required
def chef_special_suggestions():
    """Chef's Special suggestions"""
    try:
        # Get suggestions
        suggestions = chef_service.suggest_chef_specials(limit=10)
        
        return render_template('waste_to_profit/chef_special_suggestions.html',
                         suggestions=suggestions)
    except Exception as e:
        logger.error(f"Error getting Chef's Special suggestions: {str(e)}")
        flash('Error getting Chef\'s Special suggestions', 'error')
        return redirect(url_for('waste_to_profit.dashboard'))


@bp.route('/chef-specials/create', methods=['GET', 'POST'])
@login_required
def create_chef_special():
    """Create Chef's Special"""
    if request.method == 'GET':
        return render_template('waste_to_profit/create_chef_special.html')
    
    try:
        # Get form data
        name = request.form.get('name') or ''
        description = request.form.get('description') or ''
        special_price = float(request.form.get('special_price', '0') or '0')
        preparation_instructions = request.form.get('preparation_instructions') or ''
        spice_level = request.form.get('spice_level') or 'medium'
        
        # Get ingredients used
        ingredients_used = []
        ingredient_ids = request.form.getlist('ingredient_id')
        quantities = request.form.getlist('quantity')
        
        for i, ing_id in enumerate(ingredient_ids):
            if i < len(quantities) and ing_id and quantities[i]:
                ingredients_used.append({
                    'ingredient_id': int(ing_id),
                    'quantity': float(quantities[i])
                })
        
        # Create Chef's Special
        chef_service.create_chef_special(
            name=name,
            description=description,
            ingredients_used=ingredients_used,
            special_price=special_price,
            preparation_instructions=preparation_instructions,
            spice_level=spice_level,
            user_id=current_user.id
        )
        
        flash('Chef\'s Special created successfully', 'success')
        return redirect(url_for('waste_to_profit.chef_specials'))
        
    except Exception as e:
        logger.error(f"Error creating Chef's Special: {str(e)}")
        flash('Error creating Chef\'s Special', 'error')
        return redirect(url_for('waste_to_profit.create_chef_special'))


@bp.route('/chef-specials/<int:special_id>/activate', methods=['POST'])
@login_required
def activate_chef_special(special_id):
    """Activate Chef's Special"""
    try:
        # Get form data
        max_quantity_per_day = request.form.get('max_quantity_per_day', type=int)
        end_date_str = request.form.get('end_date', '')
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date() if end_date_str else None
        
        # Activate special
        success = chef_service.activate_chef_special(
            special_id=special_id,
            max_quantity_per_day=max_quantity_per_day or 0,
            end_date=end_date or date.today(),
            user_id=current_user.id
        )
        
        if success:
            flash('Chef\'s Special activated successfully', 'success')
        else:
            flash('Error activating Chef\'s Special', 'error')
        
        return redirect(url_for('waste_to_profit.chef_specials'))
        
    except Exception as e:
        logger.error(f"Error activating Chef's Special: {str(e)}")
        flash('Error activating Chef\'s Special', 'error')
        return redirect(url_for('waste_to_profit.chef_specials'))


@bp.route('/chef-specials/<int:special_id>/pricing')
@login_required
def chef_special_pricing(special_id):
    """Chef's Special pricing recommendations"""
    try:
        # Get pricing recommendations
        pricing = chef_service.get_dynamic_pricing_recommendations(special_id)
        
        return render_template('waste_to_profit/chef_special_pricing.html',
                         special_id=special_id,
                         pricing=pricing)
    except Exception as e:
        logger.error(f"Error getting pricing recommendations: {str(e)}")
        flash('Error getting pricing recommendations', 'error')
        return redirect(url_for('waste_to_profit.chef_specials'))


@bp.route('/chef-specials/analytics')
@login_required
def chef_special_analytics():
    """Chef's Special analytics"""
    try:
        # Get analytics
        analytics = chef_service.get_chef_special_analytics(days_back=30)
        
        return render_template('waste_to_profit/chef_special_analytics.html',
                         analytics=analytics)
    except Exception as e:
        logger.error(f"Error getting Chef's Special analytics: {str(e)}")
        flash('Error getting Chef\'s Special analytics', 'error')
        return redirect(url_for('waste_to_profit.dashboard'))


# Inventory Optimization Routes
@bp.route('/inventory/optimization')
@login_required
def inventory_optimization():
    """Inventory optimization recommendations"""
    try:
        # Get recommendations
        recommendations = optimization_service.get_optimization_recommendations(days_back=30)
        
        return render_template('waste_to_profit/inventory_optimization.html',
                         recommendations=recommendations)
    except Exception as e:
        logger.error(f"Error getting inventory optimization: {str(e)}")
        flash('Error getting inventory optimization', 'error')
        return redirect(url_for('waste_to_profit.dashboard'))


@bp.route('/inventory/demand-forecasting')
@login_required
def demand_forecasting():
    """Demand forecasting"""
    try:
        # Get forecasting data
        forecasting = optimization_service.get_demand_forecasting(days_ahead=30)
        
        return render_template('waste_to_profit/demand_forecasting.html',
                         forecasting=forecasting)
    except Exception as e:
        logger.error(f"Error getting demand forecasting: {str(e)}")
        flash('Error getting demand forecasting', 'error')
        return redirect(url_for('waste_to_profit.dashboard'))


@bp.route('/inventory/purchasing')
@login_required
def purchasing_recommendations():
    """Purchasing recommendations"""
    try:
        # Get recommendations
        recommendations = optimization_service.get_purchasing_recommendations(days_ahead=30)
        
        return render_template('waste_to_profit/purchasing_recommendations.html',
                         recommendations=recommendations)
    except Exception as e:
        logger.error(f"Error getting purchasing recommendations: {str(e)}")
        flash('Error getting purchasing recommendations', 'error')
        return redirect(url_for('waste_to_profit.dashboard'))


@bp.route('/inventory/supplier-performance')
@login_required
def supplier_performance():
    """Supplier performance analysis"""
    try:
        # Get performance analysis
        analysis = optimization_service.get_supplier_performance_analysis(days_back=90)
        
        return render_template('waste_to_profit/supplier_performance.html',
                         analysis=analysis)
    except Exception as e:
        logger.error(f"Error analyzing supplier performance: {str(e)}")
        flash('Error analyzing supplier performance', 'error')
        return redirect(url_for('waste_to_profit.dashboard'))


@bp.route('/inventory/storage-optimization')
@login_required
def storage_optimization():
    """Storage optimization recommendations"""
    try:
        # Get storage recommendations
        recommendations = optimization_service.get_storage_optimization()
        
        return render_template('waste_to_profit/storage_optimization.html',
                         recommendations=recommendations)
    except Exception as e:
        logger.error(f"Error getting storage optimization: {str(e)}")
        flash('Error getting storage optimization', 'error')
        return redirect(url_for('waste_to_profit.dashboard'))


@bp.route('/inventory/turnover-analysis')
@login_required
def turnover_analysis():
    """Inventory turnover analysis"""
    try:
        # Get turnover analysis
        analysis = optimization_service.get_inventory_turnover_analysis(days_back=90)
        
        return render_template('waste_to_profit/turnover_analysis.html',
                         analysis=analysis)
    except Exception as e:
        logger.error(f"Error analyzing inventory turnover: {str(e)}")
        flash('Error analyzing inventory turnover', 'error')
        return redirect(url_for('waste_to_profit.dashboard'))


@bp.route('/inventory/cost-opportunities')
@login_required
def cost_opportunities():
    """Cost-saving opportunities"""
    try:
        # Get opportunities
        opportunities = optimization_service.get_cost_saving_opportunities(days_back=30)
        
        return render_template('waste_to_profit/cost_opportunities.html',
                         opportunities=opportunities)
    except Exception as e:
        logger.error(f"Error getting cost opportunities: {str(e)}")
        flash('Error getting cost opportunities', 'error')
        return redirect(url_for('waste_to_profit.dashboard'))


# Sustainability Routes
@bp.route('/sustainability')
@login_required
def sustainability():
    """Sustainability dashboard"""
    try:
        # Get environmental impact
        impact = sustainability_service.calculate_environmental_impact(
            start_date=date.today() - timedelta(days=30),
            end_date=date.today()
        )
        
        return render_template('waste_to_profit/sustainability.html',
                         impact=impact)
    except Exception as e:
        logger.error(f"Error loading sustainability: {str(e)}")
        flash('Error loading sustainability', 'error')
        return redirect(url_for('waste_to_profit.dashboard'))


@bp.route('/sustainability/metrics')
@login_required
def sustainability_metrics():
    """Sustainability metrics"""
    try:
        # Get metrics
        metrics = sustainability_service.get_sustainability_metrics()
        
        return render_template('waste_to_profit/sustainability_metrics.html',
                         metrics=metrics)
    except Exception as e:
        logger.error(f"Error getting sustainability metrics: {str(e)}")
        flash('Error getting sustainability metrics', 'error')
        return redirect(url_for('waste_to_profit.dashboard'))


@bp.route('/sustainability/kpis')
@login_required
def sustainability_kpis():
    """Sustainability KPIs"""
    try:
        # Get KPIs
        kpis = sustainability_service.calculate_sustainability_kpis(days_back=30)
        
        return render_template('waste_to_profit/sustainability_kpis.html',
                         kpis=kpis)
    except Exception as e:
        logger.error(f"Error calculating sustainability KPIs: {str(e)}")
        flash('Error calculating sustainability KPIs', 'error')
        return redirect(url_for('waste_to_profit.dashboard'))


@bp.route('/sustainability/report')
@login_required
def sustainability_report():
    """Generate sustainability report"""
    try:
        # Get report type
        report_type = request.args.get('type', 'comprehensive')
        
        # Generate report
        report = sustainability_service.generate_sustainability_report(
            report_type=report_type,
            period_start=date.today() - timedelta(days=30),
            period_end=date.today()
        )
        
        return render_template('waste_to_profit/sustainability_report.html',
                         report_type=report_type,
                         report=report)
    except Exception as e:
        logger.error(f"Error generating sustainability report: {str(e)}")
        flash('Error generating sustainability report', 'error')
        return redirect(url_for('waste_to_profit.dashboard'))


@bp.route('/sustainability/certification')
@login_required
def green_certification():
    """Green certification status"""
    try:
        # Get certification status
        certification = sustainability_service.get_green_certification_status()
        
        return render_template('waste_to_profit/green_certification.html',
                         certification=certification)
    except Exception as e:
        logger.error(f"Error getting green certification status: {str(e)}")
        flash('Error getting green certification status', 'error')
        return redirect(url_for('waste_to_profit.dashboard'))


# Staff Training Routes
@bp.route('/training')
@login_required
def training_modules():
    """Training modules listing"""
    try:
        # Get training modules
        modules = training_service.get_training_modules()
        
        return render_template('waste_to_profit/training_modules.html',
                         modules=modules)
    except Exception as e:
        logger.error(f"Error loading training modules: {str(e)}")
        flash('Error loading training modules', 'error')
        return redirect(url_for('waste_to_profit.dashboard'))


@bp.route('/training/create', methods=['GET', 'POST'])
@login_required
def create_training_module():
    """Create training module"""
    if request.method == 'GET':
        return render_template('waste_to_profit/create_training.html')
    
    try:
        # Get form data
        title = request.form.get('title') or ''
        description = request.form.get('description') or ''
        training_type = request.form.get('training_type') or ''
        content = request.form.get('content') or ''
        duration_minutes = request.form.get('duration_minutes', type=int)
        difficulty_level = request.form.get('difficulty_level') or 'beginner'
        target_roles = request.form.getlist('target_roles')
        is_mandatory = request.form.get('is_mandatory') == 'on'
        
        # Get quiz questions
        quiz_questions = []
        questions = request.form.getlist('question')
        options_lists = request.form.getlist('options')
        correct_answers = request.form.getlist('correct_answer')
        
        for i, question in enumerate(questions):
            if i < len(options_lists) and i < len(correct_answers):
                options = options_lists[i].split(',')
                quiz_questions.append({
                    'question': question,
                    'options': [opt.strip() for opt in options],
                    'correct_answer': int(correct_answers[i])
                })
        
        # Create training module
        training_service.create_training_module(
            title=title,
            description=description,
            training_type=training_type,
            content=content,
            quiz_questions=quiz_questions,
            duration_minutes=duration_minutes or 30,
            difficulty_level=difficulty_level,
            target_roles=target_roles,
            is_mandatory=is_mandatory,
            user_id=current_user.id
        )
        
        flash('Training module created successfully', 'success')
        return redirect(url_for('waste_to_profit.training_modules'))
        
    except Exception as e:
        logger.error(f"Error creating training module: {str(e)}")
        flash('Error creating training module', 'error')
        return redirect(url_for('waste_to_profit.create_training_module'))


@bp.route('/training/<int:training_id>/enroll', methods=['POST'])
@login_required
def enroll_training(training_id):
    """Enroll in training"""
    try:
        # Enroll user
        success = training_service.enroll_user_in_training(
            user_id=current_user.id,
            training_id=training_id
        )
        
        if success:
            flash('Enrolled in training successfully', 'success')
        else:
            flash('Error enrolling in training', 'error')
        
        return redirect(url_for('waste_to_profit.training_modules'))
        
    except Exception as e:
        logger.error(f"Error enrolling in training: {str(e)}")
        flash('Error enrolling in training', 'error')
        return redirect(url_for('waste_to_profit.training_modules'))


@bp.route('/training/<int:training_id>/complete', methods=['POST'])
@login_required
def complete_training(training_id):
    """Complete training"""
    try:
        # Get form data
        quiz_score = request.form.get('quiz_score', type=int)
        feedback = request.form.get('feedback') or ''
        rating = request.form.get('rating', type=int)
        
        # Complete training
        success = training_service.complete_training(
            user_id=current_user.id,
            training_id=training_id,
            quiz_score=quiz_score or 0,
            feedback=feedback,
            rating=rating or 0
        )
        
        if success:
            flash('Training completed successfully', 'success')
        else:
            flash('Error completing training', 'error')
        
        return redirect(url_for('waste_to_profit.training_modules'))
        
    except Exception as e:
        logger.error(f"Error completing training: {str(e)}")
        flash('Error completing training', 'error')
        return redirect(url_for('waste_to_profit.training_modules'))


@bp.route('/training/analytics')
@login_required
def training_analytics():
    """Training analytics"""
    try:
        # Get analytics
        analytics = training_service.get_team_training_analytics(days_back=30)
        
        return render_template('waste_to_profit/training_analytics.html',
                         analytics=analytics)
    except Exception as e:
        logger.error(f"Error getting training analytics: {str(e)}")
        flash('Error getting training analytics', 'error')
        return redirect(url_for('waste_to_profit.dashboard'))


@bp.route('/training/recommendations')
@login_required
def training_recommendations():
    """Training recommendations"""
    try:
        # Get recommendations
        recommendations = training_service.get_training_recommendations(
            user_id=current_user.id
        )
        
        return render_template('waste_to_profit/training_recommendations.html',
                         recommendations=recommendations)
    except Exception as e:
        logger.error(f"Error getting training recommendations: {str(e)}")
        flash('Error getting training recommendations', 'error')
        return redirect(url_for('waste_to_profit.dashboard'))


# Challenges/Gamification Routes
@bp.route('/challenges')
@login_required
def challenges():
    """Waste reduction challenges"""
    try:
        # Get challenges
        challenges = db.session.execute(
            db_text('SELECT * FROM waste_reduction_challenges WHERE is_active = TRUE ORDER BY created_at DESC')
        ).fetchall()
        
        return render_template('waste_to_profit/challenges.html',
                         challenges=challenges)
    except Exception as e:
        logger.error(f"Error loading challenges: {str(e)}")
        flash('Error loading challenges', 'error')
        return redirect(url_for('waste_to_profit.dashboard'))


@bp.route('/challenges/create', methods=['GET', 'POST'])
@login_required
def create_challenge():
    """Create waste reduction challenge"""
    if request.method == 'GET':
        return render_template('waste_to_profit/create_challenge.html')
    
    try:
        # Get form data
        title = request.form.get('title') or ''
        description = request.form.get('description') or ''
        challenge_type = request.form.get('challenge_type') or ''
        target_metric = request.form.get('target_metric') or ''
        target_value = float(request.form.get('target_value', '0') or '0')
        start_date_str = request.form.get('start_date', '')
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date() if start_date_str else date.today()
        end_date_str = request.form.get('end_date', '')
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date() if end_date_str else date.today()
        reward_type = request.form.get('reward_type') or ''
        reward_value = request.form.get('reward_value') or ''
        participation_rules = request.form.get('participation_rules') or ''
        
        # Create challenge
        training_service.create_waste_reduction_challenge(
            title=title,
            description=description,
            challenge_type=challenge_type,
            target_metric=target_metric,
            target_value=target_value,
            start_date=start_date,
            end_date=end_date,
            reward_type=reward_type,
            reward_value=reward_value,
            participation_rules=participation_rules,
            user_id=current_user.id
        )
        
        flash('Challenge created successfully', 'success')
        return redirect(url_for('waste_to_profit.challenges'))
        
    except Exception as e:
        logger.error(f"Error creating challenge: {str(e)}")
        flash('Error creating challenge', 'error')
        return redirect(url_for('waste_to_profit.create_challenge'))


@bp.route('/challenges/<int:challenge_id>/join', methods=['POST'])
@login_required
def join_challenge(challenge_id):
    """Join waste reduction challenge"""
    try:
        # Join challenge
        success = training_service.enroll_user_in_challenge(
            user_id=current_user.id,
            challenge_id=challenge_id
        )
        
        if success:
            flash('Joined challenge successfully', 'success')
        else:
            flash('Error joining challenge', 'error')
        
        return redirect(url_for('waste_to_profit.challenges'))
        
    except Exception as e:
        logger.error(f"Error joining challenge: {str(e)}")
        flash('Error joining challenge', 'error')
        return redirect(url_for('waste_to_profit.challenges'))


@bp.route('/challenges/leaderboard')
@login_required
def challenge_leaderboard():
    """Challenge leaderboard"""
    try:
        # Get leaderboard
        challenge_id = request.args.get('challenge_id', type=int)
        
        if challenge_id:
            leaderboard = training_service.get_challenge_leaderboard(challenge_id=challenge_id)
        else:
            leaderboard = training_service.get_challenge_leaderboard()
        
        return render_template('waste_to_profit/challenge_leaderboard.html',
                         challenge_id=challenge_id,
                         leaderboard=leaderboard)
    except Exception as e:
        logger.error(f"Error getting challenge leaderboard: {str(e)}")
        flash('Error getting challenge leaderboard', 'error')
        return redirect(url_for('waste_to_profit.challenges'))


# API Routes
@bp.route('/api/expiring-items')
@login_required
def api_expiring_items():
    """API endpoint for expiring items"""
    try:
        days_ahead = request.args.get('days_ahead', 7, type=int)
        expiring_items = expiry_service.get_expiring_items(days_ahead=days_ahead)
        
        return jsonify({
            'success': True,
            'expiring_items': [item.to_dict() for item in expiring_items],
            'count': len(expiring_items)
        })
        
    except Exception as e:
        logger.error(f"Error getting expiring items API: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/api/waste-analytics')
@login_required
def api_waste_analytics():
    """API endpoint for waste analytics"""
    try:
        days_back = request.args.get('days_back', 30, type=int)
        analytics = analytics_service.get_waste_overview(
            start_date=date.today() - timedelta(days=days_back),
            end_date=date.today()
        )
        
        return jsonify({
            'success': True,
            'analytics': analytics
        })
        
    except Exception as e:
        logger.error(f"Error getting waste analytics API: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/api/chef-special-suggestions')
@login_required
def api_chef_special_suggestions():
    """API endpoint for Chef's Special suggestions"""
    try:
        limit = request.args.get('limit', 10, type=int)
        suggestions = chef_service.suggest_chef_specials(limit=limit)
        
        return jsonify({
            'success': True,
            'suggestions': suggestions
        })
        
    except Exception as e:
        logger.error(f"Error getting Chef's Special suggestions API: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/api/sustainability-impact')
@login_required
def api_sustainability_impact():
    """API endpoint for sustainability impact"""
    try:
        days_back = request.args.get('days_back', 30, type=int)
        impact = sustainability_service.calculate_environmental_impact(
            start_date=date.today() - timedelta(days=days_back),
            end_date=date.today()
        )
        
        return jsonify({
            'success': True,
            'impact': impact
        })
        
    except Exception as e:
        logger.error(f"Error getting sustainability impact API: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500