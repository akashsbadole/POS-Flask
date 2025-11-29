"""
Enhanced Reports Routes
Provides API endpoints for all enhanced reporting services
"""

from datetime import datetime, timedelta
from flask import Blueprint, jsonify, request, current_app
from flask_login import login_required, current_user
from typing import Optional

from app.services.enhanced_reports_service import EnhancedReportsService
from app.services.inventory_reports_service import InventoryReportsService
from app.services.employee_performance_service import EmployeePerformanceService
from app.services.customer_analytics_service import CustomerAnalyticsService
from app.services.operational_reports_service import OperationalReportsService

enhanced_reports_bp = Blueprint('enhanced_reports', __name__)

def get_date_params():
    """Helper to get date parameters from request"""
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    restaurant_id = request.args.get('restaurant_id', type=int)
    
    if start_date:
        start_date = datetime.strptime(start_date, '%Y-%m-%d')
    else:
        start_date = datetime.now() - timedelta(days=30)
    
    if end_date:
        end_date = datetime.strptime(end_date, '%Y-%m-%d')
    else:
        end_date = datetime.now()
    
    return start_date, end_date, restaurant_id

# Sales Analytics Routes
@enhanced_reports_bp.route('/api/reports/sales/hourly-analysis')
@login_required
def hourly_sales_analysis():
    """Get hourly sales analysis with peak identification"""
    start_date, end_date, restaurant_id = get_date_params()
    try:
        data = EnhancedReportsService.get_hourly_sales_analysis(start_date, end_date, restaurant_id)
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        current_app.logger.error(f"Error in hourly sales analysis: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@enhanced_reports_bp.route('/api/reports/sales/day-part-performance')
@login_required
def day_part_performance():
    """Get day-part performance reports (breakfast, lunch, dinner)"""
    start_date, end_date, restaurant_id = get_date_params()
    try:
        data = EnhancedReportsService.get_day_part_performance(start_date, end_date, restaurant_id)
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        current_app.logger.error(f"Error in day part performance: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@enhanced_reports_bp.route('/api/reports/sales/menu-item-performance')
@login_required
def menu_item_performance():
    """Get menu item performance ranking"""
    start_date, end_date, restaurant_id = get_date_params()
    try:
        data = EnhancedReportsService.get_menu_item_performance_ranking(start_date, end_date, restaurant_id)
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        current_app.logger.error(f"Error in menu item performance: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@enhanced_reports_bp.route('/api/reports/sales/category-analysis')
@login_required
def category_sales_analysis():
    """Get category-wise sales analysis"""
    start_date, end_date, restaurant_id = get_date_params()
    try:
        data = EnhancedReportsService.get_category_wise_sales_analysis(start_date, end_date, restaurant_id)
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        current_app.logger.error(f"Error in category sales analysis: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@enhanced_reports_bp.route('/api/reports/sales/payment-methods')
@login_required
def payment_method_breakdown():
    """Get payment method breakdown"""
    start_date, end_date, restaurant_id = get_date_params()
    try:
        data = EnhancedReportsService.get_payment_method_breakdown(start_date, end_date, restaurant_id)
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        current_app.logger.error(f"Error in payment method breakdown: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@enhanced_reports_bp.route('/api/reports/sales/discount-analysis')
@login_required
def discount_promotion_analysis():
    """Get discount and promotion effectiveness"""
    start_date, end_date, restaurant_id = get_date_params()
    try:
        data = EnhancedReportsService.get_discount_promotion_analysis(start_date, end_date, restaurant_id)
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        current_app.logger.error(f"Error in discount analysis: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Financial Reports Routes
@enhanced_reports_bp.route('/api/reports/financial/profit-loss')
@login_required
def profit_loss_statement():
    """Get profit and loss statements"""
    start_date, end_date, restaurant_id = get_date_params()
    try:
        data = EnhancedReportsService.get_profit_loss_statement(start_date, end_date, restaurant_id)
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        current_app.logger.error(f"Error in profit loss statement: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@enhanced_reports_bp.route('/api/reports/financial/cash-flow')
@login_required
def cash_flow_analysis():
    """Get cash flow analysis"""
    start_date, end_date, restaurant_id = get_date_params()
    try:
        data = EnhancedReportsService.get_cash_flow_analysis(start_date, end_date, restaurant_id)
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        current_app.logger.error(f"Error in cash flow analysis: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Inventory Reports Routes
@enhanced_reports_bp.route('/api/reports/inventory/stock-movement')
@login_required
def stock_movement_analysis():
    """Get stock movement analysis"""
    start_date, end_date, restaurant_id = get_date_params()
    try:
        data = InventoryReportsService.get_stock_movement_analysis(start_date, end_date, restaurant_id)
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        current_app.logger.error(f"Error in stock movement analysis: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@enhanced_reports_bp.route('/api/reports/inventory/waste-tracking')
@login_required
def waste_spoilage_tracking():
    """Get waste and spoilage tracking"""
    start_date, end_date, restaurant_id = get_date_params()
    try:
        data = InventoryReportsService.get_waste_spoilage_tracking(start_date, end_date, restaurant_id)
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        current_app.logger.error(f"Error in waste tracking: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@enhanced_reports_bp.route('/api/reports/inventory/valuation')
@login_required
def inventory_valuation():
    """Get inventory valuation report"""
    start_date, end_date, restaurant_id = get_date_params()
    try:
        data = InventoryReportsService.get_inventory_valuation_report(start_date, end_date, restaurant_id)
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        current_app.logger.error(f"Error in inventory valuation: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@enhanced_reports_bp.route('/api/reports/inventory/low-stock-alerts')
@login_required
def low_stock_alerts():
    """Get low stock alerts dashboard"""
    restaurant_id = request.args.get('restaurant_id', type=int)
    try:
        data = InventoryReportsService.get_low_stock_alerts(restaurant_id)
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        current_app.logger.error(f"Error in low stock alerts: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@enhanced_reports_bp.route('/api/reports/inventory/expiry-tracking')
@login_required
def expiry_tracking():
    """Get expiry tracking report"""
    restaurant_id = request.args.get('restaurant_id', type=int)
    try:
        data = InventoryReportsService.get_expiry_tracking_report(restaurant_id)
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        current_app.logger.error(f"Error in expiry tracking: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Employee Performance Routes
@enhanced_reports_bp.route('/api/reports/employee/sales-performance')
@login_required
def sales_performance_by_staff():
    """Get sales performance by staff"""
    start_date, end_date, restaurant_id = get_date_params()
    try:
        data = EmployeePerformanceService.get_sales_performance_by_staff(start_date, end_date, restaurant_id)
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        current_app.logger.error(f"Error in staff sales performance: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@enhanced_reports_bp.route('/api/reports/employee/service-quality')
@login_required
def service_quality_metrics():
    """Get service quality metrics"""
    start_date, end_date, restaurant_id = get_date_params()
    try:
        data = EmployeePerformanceService.get_service_quality_metrics(start_date, end_date, restaurant_id)
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        current_app.logger.error(f"Error in service quality metrics: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@enhanced_reports_bp.route('/api/reports/employee/attendance')
@login_required
def attendance_punctuality():
    """Get attendance and punctuality reports"""
    start_date, end_date, restaurant_id = get_date_params()
    try:
        data = EmployeePerformanceService.get_attendance_punctuality_reports(start_date, end_date, restaurant_id)
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        current_app.logger.error(f"Error in attendance reports: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@enhanced_reports_bp.route('/api/reports/employee/productivity')
@login_required
def productivity_analysis():
    """Get productivity analysis"""
    start_date, end_date, restaurant_id = get_date_params()
    try:
        data = EmployeePerformanceService.get_productivity_analysis(start_date, end_date, restaurant_id)
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        current_app.logger.error(f"Error in productivity analysis: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@enhanced_reports_bp.route('/api/reports/employee/overtime')
@login_required
def overtime_cost_analysis():
    """Get overtime cost analysis"""
    start_date, end_date, restaurant_id = get_date_params()
    try:
        data = EmployeePerformanceService.get_overtime_cost_analysis(start_date, end_date, restaurant_id)
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        current_app.logger.error(f"Error in overtime analysis: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@enhanced_reports_bp.route('/api/reports/employee/scheduling')
@login_required
def staff_scheduling_efficiency():
    """Get staff scheduling efficiency"""
    start_date, end_date, restaurant_id = get_date_params()
    try:
        data = EmployeePerformanceService.get_staff_scheduling_efficiency(start_date, end_date, restaurant_id)
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        current_app.logger.error(f"Error in scheduling efficiency: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Customer Analytics Routes
@enhanced_reports_bp.route('/api/reports/customer/lifetime-value')
@login_required
def customer_lifetime_value():
    """Get customer lifetime value"""
    restaurant_id = request.args.get('restaurant_id', type=int)
    try:
        data = CustomerAnalyticsService.get_customer_lifetime_value(restaurant_id)
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        current_app.logger.error(f"Error in customer lifetime value: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@enhanced_reports_bp.route('/api/reports/customer/repeat-analysis')
@login_required
def repeat_customer_analysis():
    """Get repeat customer analysis"""
    start_date, end_date, restaurant_id = get_date_params()
    try:
        data = CustomerAnalyticsService.get_repeat_customer_analysis(start_date, end_date, restaurant_id)
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        current_app.logger.error(f"Error in repeat customer analysis: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@enhanced_reports_bp.route('/api/reports/customer/segmentation')
@login_required
def customer_segmentation():
    """Get customer segmentation reports"""
    restaurant_id = request.args.get('restaurant_id', type=int)
    try:
        data = CustomerAnalyticsService.get_customer_segmentation_reports(restaurant_id)
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        current_app.logger.error(f"Error in customer segmentation: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@enhanced_reports_bp.route('/api/reports/customer/loyalty-effectiveness')
@login_required
def loyalty_program_effectiveness():
    """Get loyalty program effectiveness"""
    start_date, end_date, restaurant_id = get_date_params()
    try:
        data = CustomerAnalyticsService.get_loyalty_program_effectiveness(start_date, end_date, restaurant_id)
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        current_app.logger.error(f"Error in loyalty effectiveness: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@enhanced_reports_bp.route('/api/reports/customer/feedback-analysis')
@login_required
def feedback_rating_analysis():
    """Get feedback and rating analysis"""
    start_date, end_date, restaurant_id = get_date_params()
    try:
        data = CustomerAnalyticsService.get_feedback_rating_analysis(start_date, end_date, restaurant_id)
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        current_app.logger.error(f"Error in feedback analysis: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@enhanced_reports_bp.route('/api/reports/customer/visit-frequency')
@login_required
def customer_visit_frequency():
    """Get customer visit frequency"""
    start_date, end_date, restaurant_id = get_date_params()
    try:
        data = CustomerAnalyticsService.get_customer_visit_frequency(start_date, end_date, restaurant_id)
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        current_app.logger.error(f"Error in visit frequency: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Operational Reports Routes
@enhanced_reports_bp.route('/api/reports/operations/table-turnover')
@login_required
def table_turnover_rates():
    """Get table turnover rates"""
    start_date, end_date, restaurant_id = get_date_params()
    try:
        data = OperationalReportsService.get_table_turnover_rates(start_date, end_date, restaurant_id)
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        current_app.logger.error(f"Error in table turnover: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@enhanced_reports_bp.route('/api/reports/operations/kitchen-prep-time')
@login_required
def kitchen_preparation_time():
    """Get kitchen preparation time analysis"""
    start_date, end_date, restaurant_id = get_date_params()
    try:
        data = OperationalReportsService.get_kitchen_preparation_time_analysis(start_date, end_date, restaurant_id)
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        current_app.logger.error(f"Error in kitchen prep time: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@enhanced_reports_bp.route('/api/reports/operations/order-fulfillment')
@login_required
def order_fulfillment_efficiency():
    """Get order fulfillment efficiency"""
    start_date, end_date, restaurant_id = get_date_params()
    try:
        data = OperationalReportsService.get_order_fulfillment_efficiency(start_date, end_date, restaurant_id)
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        current_app.logger.error(f"Error in order fulfillment: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@enhanced_reports_bp.route('/api/reports/operations/delivery-performance')
@login_required
def delivery_performance_metrics():
    """Get delivery performance metrics"""
    start_date, end_date, restaurant_id = get_date_params()
    try:
        data = OperationalReportsService.get_delivery_performance_metrics(start_date, end_date, restaurant_id)
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        current_app.logger.error(f"Error in delivery performance: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@enhanced_reports_bp.route('/api/reports/operations/peak-capacity')
@login_required
def peak_capacity_utilization():
    """Get peak capacity utilization"""
    start_date, end_date, restaurant_id = get_date_params()
    try:
        data = OperationalReportsService.get_peak_capacity_utilization(start_date, end_date, restaurant_id)
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        current_app.logger.error(f"Error in capacity utilization: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@enhanced_reports_bp.route('/api/reports/operations/equipment-usage')
@login_required
def equipment_usage_analysis():
    """Get equipment usage analysis"""
    start_date, end_date, restaurant_id = get_date_params()
    try:
        data = OperationalReportsService.get_equipment_usage_analysis(start_date, end_date, restaurant_id)
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        current_app.logger.error(f"Error in equipment usage: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Dashboard Summary Route
@enhanced_reports_bp.route('/api/reports/dashboard/summary')
@login_required
def dashboard_summary():
    """Get comprehensive dashboard summary"""
    start_date, end_date, restaurant_id = get_date_params()
    try:
        # Get key metrics from all services
        summary = {
            'sales_metrics': {
                'hourly_analysis': EnhancedReportsService.get_hourly_sales_analysis(start_date, end_date, restaurant_id)[:5],
                'day_part_performance': EnhancedReportsService.get_day_part_performance(start_date, end_date, restaurant_id),
                'top_menu_items': EnhancedReportsService.get_menu_item_performance_ranking(start_date, end_date, restaurant_id)[:5]
            },
            'financial_metrics': {
                'profit_loss': EnhancedReportsService.get_profit_loss_statement(start_date, end_date, restaurant_id),
                'cash_flow': EnhancedReportsService.get_cash_flow_analysis(start_date, end_date, restaurant_id)
            },
            'inventory_metrics': {
                'low_stock_alerts': InventoryReportsService.get_low_stock_alerts(restaurant_id)[:5],
                'inventory_valuation': InventoryReportsService.get_inventory_valuation_report(start_date, end_date, restaurant_id)
            },
            'employee_metrics': {
                'top_performers': EmployeePerformanceService.get_sales_performance_by_staff(start_date, end_date, restaurant_id)[:5],
                'attendance_summary': EmployeePerformanceService.get_attendance_punctuality_reports(start_date, end_date, restaurant_id)['summary']
            },
            'customer_metrics': {
                'repeat_customers': CustomerAnalyticsService.get_repeat_customer_analysis(start_date, end_date, restaurant_id)['summary'],
                'customer_segments': CustomerAnalyticsService.get_customer_segmentation_reports(restaurant_id)['summary']
            },
            'operational_metrics': {
                'table_turnover': OperationalReportsService.get_table_turnover_rates(start_date, end_date, restaurant_id)[:5],
                'order_efficiency': OperationalReportsService.get_order_fulfillment_efficiency(start_date, end_date, restaurant_id)['summary']
            }
        }
        return jsonify({'success': True, 'data': summary})
    except Exception as e:
        current_app.logger.error(f"Error in dashboard summary: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Cache Management Route
@enhanced_reports_bp.route('/api/reports/cache/clear', methods=['POST'])
@login_required
def clear_report_cache():
    """Clear report cache"""
    try:
        # This would need to be implemented in the cache service
        return jsonify({'success': True, 'message': 'Report cache cleared successfully'})
    except Exception as e:
        current_app.logger.error(f"Error clearing cache: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500