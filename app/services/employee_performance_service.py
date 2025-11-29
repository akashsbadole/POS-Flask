"""
Employee Performance Reports Service
Handles employee analytics and performance tracking reports
"""

from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from sqlalchemy import func, and_, or_, desc, asc, extract
from app import db
from app.models.employee import EmployeeProfile, EmployeeAttendance, PayrollRecord
from app.models.order import Order, OrderItem, OrderStatus
from app.models.enhanced_reports import (
    EmployeePerformance, ReportCache
)
from app.models.user import User
from app.services.enhanced_reports_service import EnhancedReportsService

class EmployeePerformanceService:
    """Service for employee performance analytics and reporting"""
    
    @staticmethod
    def get_sales_performance_by_staff(start_date: datetime, end_date: datetime,
                                     restaurant_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get sales performance by staff"""
        cache_key = EnhancedReportsService.generate_cache_key('staff_sales_performance', {
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'restaurant_id': restaurant_id
        })
        
        cache = EnhancedReportsService.get_or_create_cache(cache_key, 'staff_sales_performance', {}, 30)
        if cache and cache.get_cache_data():
            return cache.get_cache_data()
        
        query = db.session.query(
            User.id,
            User.name,
            EmployeeProfile.designation,
            func.count(Order.id).label('total_orders'),
            func.sum(Order.total_amount).label('total_sales'),
            func.avg(Order.total_amount).label('avg_order_value'),
            func.sum(Order.tip_amount).label('total_tips'),
            func.count(func.distinct(Order.customer_id)).label('unique_customers')
        ).join(
            EmployeeProfile, User.id == EmployeeProfile.user_id
        ).outerjoin(
            Order, User.id == Order.employee_id
        ).filter(
            Order.created_at >= start_date,
            Order.created_at <= end_date,
            Order.status == OrderStatus.SERVED
        )
        
        if restaurant_id:
            query = query.filter(Order.restaurant_id == restaurant_id)
        
        results = query.group_by(
            User.id, User.name, EmployeeProfile.designation
        ).order_by(desc('total_sales')).all()
        
        performance_data = []
        for emp_id, name, designation, orders, sales, avg_order, tips, customers in results:
            total_sales = float(sales or 0)
            total_tips = float(tips or 0)
            performance_data.append({
                'employee_id': emp_id,
                'name': name,
                'position': designation,
                'total_orders': orders or 0,
                'total_sales': total_sales,
                'avg_order_value': float(avg_order or 0),
                'total_tips': total_tips,
                'unique_customers': customers or 0,
                'tip_percentage': (total_tips / total_sales * 100) if total_sales > 0 else 0,
                'sales_per_order': total_sales / (orders or 1)
            })
        
        EnhancedReportsService.save_cache_data(cache, performance_data)
        return performance_data
    
    @staticmethod
    def get_service_quality_metrics(start_date: datetime, end_date: datetime,
                                  restaurant_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get service quality metrics"""
        cache_key = EnhancedReportsService.generate_cache_key('service_quality_metrics', {
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'restaurant_id': restaurant_id
        })
        
        cache = EnhancedReportsService.get_or_create_cache(cache_key, 'service_quality_metrics', {}, 30)
        if cache and cache.get_cache_data():
            return cache.get_cache_data()
        
        # This would require customer feedback/rating tables
        # For now, return placeholder structure based on available data
        query = db.session.query(
            User.id,
            User.name,
            EmployeeProfile.designation,
            func.count(Order.id).label('total_orders'),
            func.avg(Order.total_amount).label('avg_order_value')
        ).join(
            EmployeeProfile, User.id == EmployeeProfile.user_id
        ).outerjoin(
            Order, User.id == Order.employee_id
        ).filter(
            Order.created_at >= start_date,
            Order.created_at <= end_date,
            Order.status == OrderStatus.SERVED
        )
        
        if restaurant_id:
            query = query.filter(Order.restaurant_id == restaurant_id)
        
        results = query.group_by(
            User.id, User.name, EmployeeProfile.designation
        ).order_by(desc('total_orders')).all()
        
        quality_data = []
        for emp_id, name, designation, orders, avg_order in results:
            quality_data.append({
                'employee_id': emp_id,
                'name': name,
                'position': designation,
                'total_orders': orders or 0,
                'avg_order_value': float(avg_order or 0),
                'customer_rating': 4.5,  # Placeholder - would come from feedback table
                'service_speed': 'Good',  # Placeholder - would calculate from order times
                'accuracy_rate': 98.5,  # Placeholder - would calculate from order accuracy
                'complaints_count': 0  # Placeholder - would come from complaints table
            })
        
        EnhancedReportsService.save_cache_data(cache, quality_data)
        return quality_data
    
    @staticmethod
    def get_attendance_punctuality_reports(start_date: datetime, end_date: datetime,
                                        restaurant_id: Optional[int] = None) -> Dict[str, Any]:
        """Get attendance and punctuality reports"""
        cache_key = EnhancedReportsService.generate_cache_key('attendance_punctuality', {
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'restaurant_id': restaurant_id
        })
        
        cache = EnhancedReportsService.get_or_create_cache(cache_key, 'attendance_punctuality', {}, 30)
        if cache and cache.get_cache_data():
            return cache.get_cache_data()
        
        query = db.session.query(
            User.id,
            User.name,
            EmployeeProfile.designation,
            func.count(EmployeeAttendance.id).label('total_days'),
            func.sum(
                func.case(
                    (EmployeeAttendance.attendance_status == 'present', 1),
                    else_=0
                )
            ).label('present_days'),
            func.sum(
                func.case(
                    (EmployeeAttendance.attendance_status == 'absent', 1),
                    else_=0
                )
            ).label('absent_days'),
            func.sum(
                func.case(
                    (EmployeeAttendance.attendance_status == 'late', 1),
                    else_=0
                )
            ).label('late_days'),
            func.avg(
                func.case(
                    (EmployeeAttendance.check_in_time.isnot(None),
                     func.extract('hour', EmployeeAttendance.check_in_time) * 60 +
                     func.extract('minute', EmployeeAttendance.check_in_time)),
                    else_=None
                )
            ).label('avg_check_in_minute')
        ).join(
            EmployeeProfile, User.id == EmployeeProfile.user_id
        ).outerjoin(
            EmployeeAttendance, User.id == EmployeeAttendance.user_id
        ).filter(
            EmployeeAttendance.date >= start_date,
            EmployeeAttendance.date <= end_date
        )
        
        if restaurant_id:
            query = query.filter(EmployeeProfile.restaurant_id == restaurant_id)
        
        results = query.group_by(
            User.id, User.name, EmployeeProfile.designation
        ).order_by(desc('present_days')).all()
        
        attendance_data = []
        total_employees = 0
        avg_attendance_rate = 0
        avg_punctuality_rate = 0
        
        for emp_id, name, designation, total_days, present, absent, late, avg_check_in in results:
            if total_days > 0:
                attendance_rate = (present / total_days) * 100
                punctuality_rate = ((total_days - late) / total_days) * 100
            else:
                attendance_rate = 0
                punctuality_rate = 0
            
            employee_data = {
                'employee_id': emp_id,
                'name': name,
                'position': designation,
                'total_days': total_days or 0,
                'present_days': present or 0,
                'absent_days': absent or 0,
                'late_days': late or 0,
                'attendance_rate': attendance_rate,
                'punctuality_rate': punctuality_rate,
                'avg_check_in_time': str(avg_check_in) if avg_check_in else 'N/A'
            }
            attendance_data.append(employee_data)
            
            total_employees += 1
            avg_attendance_rate += attendance_rate
            avg_punctuality_rate += punctuality_rate
        
        summary = {
            'total_employees': total_employees,
            'avg_attendance_rate': avg_attendance_rate / total_employees if total_employees > 0 else 0,
            'avg_punctuality_rate': avg_punctuality_rate / total_employees if total_employees > 0 else 0
        }
        
        EnhancedReportsService.save_cache_data(cache, {'attendance_data': attendance_data, 'summary': summary})
        return {'attendance_data': attendance_data, 'summary': summary}
    
    @staticmethod
    def get_productivity_analysis(start_date: datetime, end_date: datetime,
                                restaurant_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get productivity analysis"""
        cache_key = EnhancedReportsService.generate_cache_key('productivity_analysis', {
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'restaurant_id': restaurant_id
        })
        
        cache = EnhancedReportsService.get_or_create_cache(cache_key, 'productivity_analysis', {}, 30)
        if cache and cache.get_cache_data():
            return cache.get_cache_data()
        
        query = db.session.query(
            User.id,
            User.name,
            EmployeeProfile.designation,
            func.count(Order.id).label('total_orders'),
            func.sum(Order.total_amount).label('total_sales'),
            func.count(OrderItem.id).label('total_items'),
            func.avg(
                func.case(
                    (Order.completed_at.isnot(None) & Order.created_at.isnot(None),
                     func.extract('epoch', Order.completed_at - Order.created_at) / 60),
                    else_=None
                )
            ).label('avg_order_time_minutes')
        ).join(
            EmployeeProfile, User.id == EmployeeProfile.user_id
        ).outerjoin(
            Order, User.id == Order.employee_id
        ).outerjoin(
            OrderItem, Order.id == OrderItem.order_id
        ).filter(
            Order.created_at >= start_date,
            Order.created_at <= end_date,
            Order.status == OrderStatus.SERVED
        )
        
        if restaurant_id:
            query = query.filter(Order.restaurant_id == restaurant_id)
        
        results = query.group_by(
            User.id, User.name, EmployeeProfile.designation
        ).order_by(desc('total_sales')).all()
        
        productivity_data = []
        for emp_id, name, designation, orders, sales, items, avg_time in results:
            total_sales = float(sales or 0)
            orders_per_hour = orders / 8  # Assuming 8-hour shifts
            items_per_order = items / orders if orders > 0 else 0
            
            productivity_data.append({
                'employee_id': emp_id,
                'name': name,
                'position': designation,
                'total_orders': orders or 0,
                'total_sales': total_sales,
                'total_items': items or 0,
                'orders_per_hour': orders_per_hour,
                'items_per_order': items_per_order,
                'avg_order_time': float(avg_time or 0),
                'sales_per_hour': total_sales / 8,  # Assuming 8-hour shifts
                'efficiency_score': min(100, (orders_per_hour * 10))  # Simple efficiency calculation
            })
        
        EnhancedReportsService.save_cache_data(cache, productivity_data)
        return productivity_data
    
    @staticmethod
    def get_overtime_cost_analysis(start_date: datetime, end_date: datetime,
                                restaurant_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get overtime cost analysis"""
        cache_key = EnhancedReportsService.generate_cache_key('overtime_cost_analysis', {
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'restaurant_id': restaurant_id
        })
        
        cache = EnhancedReportsService.get_or_create_cache(cache_key, 'overtime_cost_analysis', {}, 30)
        if cache and cache.get_cache_data():
            return cache.get_cache_data()
        
        # This would require overtime tracking in attendance or payroll tables
        # For now, return placeholder structure
        query = db.session.query(
            User.id,
            User.name,
            EmployeeProfile.designation,
            EmployeeProfile.basic_salary,
            func.sum(PayrollRecord.overtime_hours).label('total_overtime'),
            func.sum(PayrollRecord.overtime_pay).label('total_overtime_pay')
        ).join(
            EmployeeProfile, User.id == EmployeeProfile.user_id
        ).outerjoin(
            PayrollRecord, User.id == PayrollRecord.user_id
        ).filter(
            PayrollRecord.pay_period_start >= start_date,
            PayrollRecord.pay_period_end <= end_date
        )
        
        if restaurant_id:
            query = query.filter(EmployeeProfile.restaurant_id == restaurant_id)
        
        results = query.group_by(
            User.id, User.name, EmployeeProfile.designation, EmployeeProfile.basic_salary
        ).all()
        
        overtime_data = []
        for emp_id, name, designation, basic_salary, total_overtime, total_overtime_pay in results:
            # Calculate hourly rate from basic salary (assuming 160 hours/month)
            hourly_rate = float(basic_salary or 0) / 160 if basic_salary else 0
            
            overtime_data.append({
                'employee_id': emp_id,
                'name': name,
                'position': designation,
                'hourly_rate': hourly_rate,
                'regular_hours': 160,  # Standard monthly hours
                'overtime_hours': float(total_overtime or 0),
                'overtime_cost': float(total_overtime_pay or 0),
                'total_cost': float(basic_salary or 0) + float(total_overtime_pay or 0)
            })
        
        EnhancedReportsService.save_cache_data(cache, overtime_data)
        return overtime_data
    
    @staticmethod
    def get_staff_scheduling_efficiency(start_date: datetime, end_date: datetime,
                                      restaurant_id: Optional[int] = None) -> Dict[str, Any]:
        """Get staff scheduling efficiency"""
        cache_key = EnhancedReportsService.generate_cache_key('staff_scheduling_efficiency', {
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'restaurant_id': restaurant_id
        })
        
        cache = EnhancedReportsService.get_or_create_cache(cache_key, 'staff_scheduling_efficiency', {}, 30)
        if cache and cache.get_cache_data():
            return cache.get_cache_data()
        
        # This would require schedule tables
        # For now, return placeholder structure
        scheduling_data = {
            'summary': {
                'total_shifts': 120,
                'filled_shifts': 115,
                'unfilled_shifts': 5,
                'fill_rate': 95.8,
                'overtime_shifts': 8,
                'schedule_adherence': 92.3
            },
            'by_position': {
                'Waiter': {'scheduled': 60, 'worked': 58, 'absent': 2},
                'Cook': {'scheduled': 40, 'worked': 39, 'absent': 1},
                'Manager': {'scheduled': 20, 'worked': 18, 'absent': 2}
            },
            'peak_coverage': {
                'breakfast': {'required': 8, 'scheduled': 8, 'actual': 7},
                'lunch': {'required': 12, 'scheduled': 12, 'actual': 11},
                'dinner': {'required': 10, 'scheduled': 10, 'actual': 10}
            }
        }
        
        EnhancedReportsService.save_cache_data(cache, scheduling_data)
        return scheduling_data