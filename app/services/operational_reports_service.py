"""
Operational Reports Service
Handles operational efficiency and performance reports
"""

from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from sqlalchemy import func, and_, or_, desc, asc, extract
from app import db
from app.models.table import Table
from app.models.order import Order, OrderItem
from app.models.menu import MenuItem
from app.models.enhanced_reports import (
    OperationalMetrics, ReportCache
)
from app.services.enhanced_reports_service import EnhancedReportsService

class OperationalReportsService:
    """Service for operational analytics and reporting"""
    
    @staticmethod
    def get_table_turnover_rates(start_date: datetime, end_date: datetime,
                              restaurant_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get table turnover rates analysis"""
        cache_key = EnhancedReportsService.generate_cache_key('table_turnover_rates', {
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'restaurant_id': restaurant_id
        })
        
        cache = EnhancedReportsService.get_or_create_cache(cache_key, 'table_turnover_rates', {}, 30)
        if cache and cache.get_cache_data():
            return cache.get_cache_data()
        
        query = db.session.query(
            Table.id,
            Table.number,
            Table.capacity,
            Table.section,
            func.count(Order.id).label('total_orders'),
            func.sum(Order.total_amount).label('total_revenue'),
            func.avg(
                func.case(
                    (Order.completed_at.isnot(None) & Order.created_at.isnot(None),
                     func.extract('epoch', Order.completed_at - Order.created_at) / 60),
                    else_=None
                )
            ).label('avg_duration_minutes'),
            func.sum(
                func.case(
                    (Order.completed_at.isnot(None) & Order.created_at.isnot(None),
                     func.extract('epoch', Order.completed_at - Order.created_at) / 3600),
                    else_=0
                )
            ).label('total_occupied_hours')
        ).outerjoin(
            Order, Table.id == Order.table_id
        ).filter(
            Order.created_at >= start_date,
            Order.created_at <= end_date,
            Order.status == 'served'
        )
        
        if restaurant_id:
            query = query.filter(Table.restaurant_id == restaurant_id)
        
        results = query.group_by(
            Table.id, Table.number, Table.capacity, Table.section
        ).order_by(desc('total_revenue')).all()
        
        turnover_data = []
        for table_id, number, capacity, section, orders, revenue, avg_duration, occupied_hours in results:
            total_revenue = float(revenue or 0)
            total_hours = (end_date - start_date).total_seconds() / 3600  # Operating hours
            turnover_rate = orders / (total_hours / 8) if total_hours > 0 else 0  # Assuming 8-hour shifts
            
            turnover_data.append({
                'table_id': table_id,
                'table_number': number,
                'capacity': capacity,
                'section': section,
                'total_orders': orders or 0,
                'total_revenue': total_revenue,
                'avg_duration_minutes': float(avg_duration or 0),
                'total_occupied_hours': float(occupied_hours or 0),
                'turnover_rate': turnover_rate,
                'revenue_per_hour': total_revenue / (occupied_hours or 1),
                'revenue_per_seat': total_revenue / (orders * capacity) if orders > 0 and capacity > 0 else 0,
                'occupancy_rate': (occupied_hours / total_hours * 100) if total_hours > 0 else 0
            })
        
        EnhancedReportsService.save_cache_data(cache, turnover_data)
        return turnover_data
    
    @staticmethod
    def get_kitchen_preparation_time_analysis(start_date: datetime, end_date: datetime,
                                          restaurant_id: Optional[int] = None) -> Dict[str, Any]:
        """Get kitchen preparation time analysis"""
        cache_key = EnhancedReportsService.generate_cache_key('kitchen_prep_time', {
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'restaurant_id': restaurant_id
        })
        
        cache = EnhancedReportsService.get_or_create_cache(cache_key, 'kitchen_prep_time', {}, 30)
        if cache and cache.get_cache_data():
            return cache.get_cache_data()
        
        # Get item preparation times
        item_prep_times = db.session.query(
            MenuItem.id,
            MenuItem.name,
            MenuItem.category,
            func.count(OrderItem.id).label('order_count'),
            func.avg(
                func.case(
                    (Order.completed_at.isnot(None) & Order.created_at.isnot(None),
                     func.extract('epoch', Order.completed_at - Order.created_at) / 60),
                    else_=None
                )
            ).label('avg_prep_time_minutes'),
            func.min(
                func.case(
                    (Order.completed_at.isnot(None) & Order.created_at.isnot(None),
                     func.extract('epoch', Order.completed_at - Order.created_at) / 60),
                    else_=None
                )
            ).label('min_prep_time'),
            func.max(
                func.case(
                    (Order.completed_at.isnot(None) & Order.created_at.isnot(None),
                     func.extract('epoch', Order.completed_at - Order.created_at) / 60),
                    else_=None
                )
            ).label('max_prep_time')
        ).join(
            OrderItem, MenuItem.id == OrderItem.menu_item_id
        ).join(
            Order, OrderItem.order_id == Order.id
        ).filter(
            Order.created_at >= start_date,
            Order.created_at <= end_date,
            Order.status == 'served'
        )
        
        if restaurant_id:
            item_prep_times = item_prep_times.filter(Order.restaurant_id == restaurant_id)
        
        item_results = item_prep_times.group_by(
            MenuItem.id, MenuItem.name, MenuItem.category
        ).order_by(desc('order_count')).all()
        
        # Process item data
        item_analysis = []
        for item_id, name, category, order_count, avg_prep, min_prep, max_prep in item_results:
            item_analysis.append({
                'item_id': item_id,
                'name': name,
                'category': category,
                'order_count': order_count,
                'avg_prep_time_minutes': float(avg_prep or 0),
                'min_prep_time_minutes': float(min_prep or 0),
                'max_prep_time_minutes': float(max_prep or 0)
            })
        
        # Get category summary
        category_summary = db.session.query(
            MenuItem.category,
            func.count(OrderItem.id).label('total_orders'),
            func.avg(
                func.case(
                    (Order.completed_at.isnot(None) & Order.created_at.isnot(None),
                     func.extract('epoch', Order.completed_at - Order.created_at) / 60),
                    else_=None
                )
            ).label('avg_prep_time')
        ).join(
            OrderItem, MenuItem.id == OrderItem.menu_item_id
        ).join(
            Order, OrderItem.order_id == Order.id
        ).filter(
            Order.created_at >= start_date,
            Order.created_at <= end_date,
            Order.status == 'served'
        )
        
        if restaurant_id:
            category_summary = category_summary.filter(Order.restaurant_id == restaurant_id)
        
        category_results = category_summary.group_by(MenuItem.category).all()
        
        categories = {}
        for category, total_orders, avg_prep in category_results:
            categories[category] = {
                'total_orders': total_orders,
                'avg_prep_time_minutes': float(avg_prep or 0)
            }
        
        # Get hourly preparation time trends
        hourly_trends = db.session.query(
            extract('hour', Order.created_at).label('hour'),
            func.count(Order.id).label('order_count'),
            func.avg(
                func.case(
                    (Order.completed_at.isnot(None) & Order.created_at.isnot(None),
                     func.extract('epoch', Order.completed_at - Order.created_at) / 60),
                    else_=None
                )
            ).label('avg_prep_time')
        ).filter(
            Order.created_at >= start_date,
            Order.created_at <= end_date,
            Order.status == 'served'
        )
        
        if restaurant_id:
            hourly_trends = hourly_trends.filter(Order.restaurant_id == restaurant_id)
        
        hourly_results = hourly_trends.group_by('hour').order_by('hour').all()
        
        hourly_analysis = []
        for hour, order_count, avg_prep in hourly_results:
            hourly_analysis.append({
                'hour': int(hour),
                'order_count': order_count,
                'avg_prep_time_minutes': float(avg_prep or 0)
            })
        
        kitchen_analysis = {
            'item_analysis': item_analysis[:50],  # Top 50 items
            'category_summary': categories,
            'hourly_trends': hourly_analysis,
            'summary': {
                'total_orders_analyzed': sum(item['order_count'] for item in item_analysis),
                'overall_avg_prep_time': sum(item['avg_prep_time_minutes'] for item in item_analysis) / len(item_analysis) if item_analysis else 0,
                'fastest_prep_time': min(item['avg_prep_time_minutes'] for item in item_analysis) if item_analysis else 0,
                'slowest_prep_time': max(item['avg_prep_time_minutes'] for item in item_analysis) if item_analysis else 0
            }
        }
        
        EnhancedReportsService.save_cache_data(cache, kitchen_analysis)
        return kitchen_analysis
    
    @staticmethod
    def get_order_fulfillment_efficiency(start_date: datetime, end_date: datetime,
                                     restaurant_id: Optional[int] = None) -> Dict[str, Any]:
        """Get order fulfillment efficiency metrics"""
        cache_key = EnhancedReportsService.generate_cache_key('order_fulfillment_efficiency', {
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'restaurant_id': restaurant_id
        })
        
        cache = EnhancedReportsService.get_or_create_cache(cache_key, 'order_fulfillment_efficiency', {}, 30)
        if cache and cache.get_cache_data():
            return cache.get_cache_data()
        
        # Get order fulfillment metrics
        query = db.session.query(
            func.count(Order.id).label('total_orders'),
            func.sum(
                func.case(
                    (Order.status == 'served', 1),
                    else_=0
                )
            ).label('completed_orders'),
            func.sum(
                func.case(
                    (Order.status == 'cancelled', 1),
                    else_=0
                )
            ).label('cancelled_orders'),
            func.avg(
                func.case(
                    (Order.completed_at.isnot(None) & Order.created_at.isnot(None),
                     func.extract('epoch', Order.completed_at - Order.created_at) / 60),
                    else_=None
                )
            ).label('avg_fulfillment_time'),
            func.sum(
                func.case(
                    (Order.completed_at.isnot(None) & Order.created_at.isnot(None),
                     func.extract('epoch', Order.completed_at - Order.created_at) / 60),
                    else_=0
                )
            ).label('total_fulfillment_time'),
            func.count(func.distinct(Order.employee_id)).label('staff_involved')
        ).filter(
            Order.created_at >= start_date,
            Order.created_at <= end_date
        )
        
        if restaurant_id:
            query = query.filter(Order.restaurant_id == restaurant_id)
        
        result = query.first()
        
        if result:
            total_orders = result.total_orders or 0
            completed_orders = result.completed_orders or 0
            cancelled_orders = result.cancelled_orders or 0
            avg_fulfillment_time = float(result.avg_fulfillment_time or 0)
            total_fulfillment_time = float(result.total_fulfillment_time or 0)
            staff_involved = result.staff_involved or 0
        else:
            total_orders = 0
            completed_orders = 0
            cancelled_orders = 0
            avg_fulfillment_time = 0
            total_fulfillment_time = 0
            staff_involved = 0
        
        # Calculate efficiency metrics
        completion_rate = (completed_orders / total_orders * 100) if total_orders > 0 else 0
        cancellation_rate = (cancelled_orders / total_orders * 100) if total_orders > 0 else 0
        orders_per_staff = total_orders / staff_involved if staff_involved > 0 else 0
        
        # Get hourly efficiency breakdown
        hourly_efficiency = db.session.query(
            extract('hour', Order.created_at).label('hour'),
            func.count(Order.id).label('order_count'),
            func.sum(
                func.case(
                    (Order.status == 'served', 1),
                    else_=0
                )
            ).label('completed_count'),
            func.avg(
                func.case(
                    (Order.completed_at.isnot(None) & Order.created_at.isnot(None),
                     func.extract('epoch', Order.completed_at - Order.created_at) / 60),
                    else_=None
                )
            ).label('avg_fulfillment_time')
        ).filter(
            Order.created_at >= start_date,
            Order.created_at <= end_date
        )
        
        if restaurant_id:
            hourly_efficiency = hourly_efficiency.filter(Order.restaurant_id == restaurant_id)
        
        hourly_results = hourly_efficiency.group_by('hour').order_by('hour').all()
        
        hourly_breakdown = []
        for hour, order_count, completed_count, avg_time in hourly_results:
            hourly_breakdown.append({
                'hour': int(hour),
                'order_count': order_count,
                'completed_count': completed_count,
                'completion_rate': (completed_count / order_count * 100) if order_count > 0 else 0,
                'avg_fulfillment_time': float(avg_time or 0)
            })
        
        efficiency_data = {
            'summary': {
                'total_orders': total_orders,
                'completed_orders': completed_orders,
                'cancelled_orders': cancelled_orders,
                'completion_rate': completion_rate,
                'cancellation_rate': cancellation_rate,
                'avg_fulfillment_time_minutes': avg_fulfillment_time,
                'total_fulfillment_time_minutes': total_fulfillment_time,
                'staff_involved': staff_involved,
                'orders_per_staff': orders_per_staff
            },
            'hourly_breakdown': hourly_breakdown,
            'efficiency_score': min(100, completion_rate * 0.7 + (100 - cancellation_rate) * 0.3)  # Weighted efficiency score
        }
        
        EnhancedReportsService.save_cache_data(cache, efficiency_data)
        return efficiency_data
    
    @staticmethod
    def get_delivery_performance_metrics(start_date: datetime, end_date: datetime,
                                    restaurant_id: Optional[int] = None) -> Dict[str, Any]:
        """Get delivery performance metrics"""
        cache_key = EnhancedReportsService.generate_cache_key('delivery_performance', {
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'restaurant_id': restaurant_id
        })
        
        cache = EnhancedReportsService.get_or_create_cache(cache_key, 'delivery_performance', {}, 30)
        if cache and cache.get_cache_data():
            return cache.get_cache_data()
        
        # This would require delivery tracking tables
        # For now, return placeholder structure
        delivery_data = {
            'summary': {
                'total_deliveries': 150,
                'on_time_deliveries': 135,
                'late_deliveries': 15,
                'on_time_rate': 90.0,
                'avg_delivery_time_minutes': 28.5,
                'avg_distance_km': 3.2,
                'delivery_revenue': 3750,
                'delivery_costs': 450,
                'delivery_profit': 3300
            },
            'performance_by_time': {
                'morning': {'deliveries': 30, 'on_time_rate': 95.0, 'avg_time': 25},
                'afternoon': {'deliveries': 60, 'on_time_rate': 88.0, 'avg_time': 30},
                'evening': {'deliveries': 45, 'on_time_rate': 92.0, 'avg_time': 28},
                'night': {'deliveries': 15, 'on_time_rate': 85.0, 'avg_time': 35}
            },
            'driver_performance': [
                {'driver_id': 1, 'name': 'John Driver', 'deliveries': 45, 'on_time_rate': 96.0, 'avg_time': 24},
                {'driver_id': 2, 'name': 'Jane Rider', 'deliveries': 38, 'on_time_rate': 92.0, 'avg_time': 27}
            ],
            'delivery_issues': [
                {'date': '2024-01-15', 'issue': 'Traffic delay', 'count': 3},
                {'date': '2024-01-14', 'issue': 'Customer not available', 'count': 2}
            ]
        }
        
        EnhancedReportsService.save_cache_data(cache, delivery_data)
        return delivery_data
    
    @staticmethod
    def get_peak_capacity_utilization(start_date: datetime, end_date: datetime,
                                  restaurant_id: Optional[int] = None) -> Dict[str, Any]:
        """Get peak capacity utilization analysis"""
        cache_key = EnhancedReportsService.generate_cache_key('peak_capacity_utilization', {
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'restaurant_id': restaurant_id
        })
        
        cache = EnhancedReportsService.get_or_create_cache(cache_key, 'peak_capacity_utilization', {}, 30)
        if cache and cache.get_cache_data():
            return cache.get_cache_data()
        
        # Get capacity utilization by hour and day
        capacity_data = db.session.query(
            extract('dow', Order.created_at).label('day_of_week'),
            extract('hour', Order.created_at).label('hour_of_day'),
            func.count(Order.id).label('order_count'),
            func.count(func.distinct(Order.table_id)).label('tables_used'),
            func.sum(Order.total_amount).label('total_revenue')
        ).filter(
            Order.created_at >= start_date,
            Order.created_at <= end_date,
            Order.status == 'served'
        )
        
        if restaurant_id:
            capacity_data = capacity_data.filter(Order.restaurant_id == restaurant_id)
        
        capacity_results = capacity_data.group_by(
            extract('dow', Order.created_at),
            extract('hour', Order.created_at)
        ).order_by('day_of_week', 'hour_of_day').all()
        
        # Get total table capacity
        total_tables = Table.query.filter_by(restaurant_id=restaurant_id).count() if restaurant_id else Table.query.count()
        
        utilization_data = []
        day_names = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
        
        for day_of_week, hour_of_day, order_count, tables_used, revenue in capacity_results:
            utilization_rate = (tables_used / total_tables * 100) if total_tables > 0 else 0
            
            utilization_data.append({
                'day_of_week': int(day_of_week),
                'day_name': day_names[int(day_of_week)],
                'hour_of_day': int(hour_of_day),
                'order_count': order_count,
                'tables_used': tables_used,
                'total_tables': total_tables,
                'utilization_rate': utilization_rate,
                'total_revenue': float(revenue or 0),
                'revenue_per_table': float(revenue or 0) / tables_used if tables_used > 0 else 0
            })
        
        # Find peak hours
        peak_hours = sorted(utilization_data, key=lambda x: x['utilization_rate'], reverse=True)[:10]
        
        capacity_analysis = {
            'peak_hours': peak_hours,
            'utilization_by_day': {},
            'hourly_average': {},
            'summary': {
                'total_analyzed_periods': len(utilization_data),
                'avg_utilization_rate': sum(item['utilization_rate'] for item in utilization_data) / len(utilization_data) if utilization_data else 0,
                'peak_utilization_rate': max(item['utilization_rate'] for item in utilization_data) if utilization_data else 0,
                'lowest_utilization_rate': min(item['utilization_rate'] for item in utilization_data) if utilization_data else 0,
                'total_tables': total_tables
            }
        }
        
        # Calculate daily averages
        for day in range(7):
            day_data = [item for item in utilization_data if item['day_of_week'] == day]
            if day_data:
                capacity_analysis['utilization_by_day'][day_names[day]] = {
                    'avg_utilization': sum(item['utilization_rate'] for item in day_data) / len(day_data),
                    'peak_utilization': max(item['utilization_rate'] for item in day_data),
                    'total_orders': sum(item['order_count'] for item in day_data)
                }
        
        # Calculate hourly averages
        for hour in range(24):
            hour_data = [item for item in utilization_data if item['hour_of_day'] == hour]
            if hour_data:
                capacity_analysis['hourly_average'][hour] = {
                    'avg_utilization': sum(item['utilization_rate'] for item in hour_data) / len(hour_data),
                    'peak_utilization': max(item['utilization_rate'] for item in hour_data),
                    'total_orders': sum(item['order_count'] for item in hour_data)
                }
        
        EnhancedReportsService.save_cache_data(cache, capacity_analysis)
        return capacity_analysis
    
    @staticmethod
    def get_equipment_usage_analysis(start_date: datetime, end_date: datetime,
                                 restaurant_id: Optional[int] = None) -> Dict[str, Any]:
        """Get equipment usage analysis"""
        cache_key = EnhancedReportsService.generate_cache_key('equipment_usage', {
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'restaurant_id': restaurant_id
        })
        
        cache = EnhancedReportsService.get_or_create_cache(cache_key, 'equipment_usage', {}, 30)
        if cache and cache.get_cache_data():
            return cache.get_cache_data()
        
        # This would require equipment tracking tables
        # For now, return placeholder structure
        equipment_data = {
            'summary': {
                'total_equipment': 25,
                'active_equipment': 23,
                'maintenance_scheduled': 3,
                'equipment_downtime_hours': 12,
                'avg_utilization_rate': 78.5
            },
            'equipment_categories': {
                'Kitchen Equipment': {
                    'count': 12,
                    'utilization_rate': 85.2,
                    'maintenance_cost': 2500,
                    'energy_consumption': 4500
                },
                'HVAC Systems': {
                    'count': 4,
                    'utilization_rate': 92.1,
                    'maintenance_cost': 1800,
                    'energy_consumption': 3200
                },
                'Point of Sale': {
                    'count': 6,
                    'utilization_rate': 76.8,
                    'maintenance_cost': 800,
                    'energy_consumption': 600
                },
                'Display Equipment': {
                    'count': 3,
                    'utilization_rate': 65.4,
                    'maintenance_cost': 400,
                    'energy_consumption': 800
                }
            },
            'maintenance_schedule': [
                {'equipment_id': 1, 'name': 'Oven #1', 'scheduled_date': '2024-02-01', 'type': 'Preventive'},
                {'equipment_id': 2, 'name': 'Fridge #2', 'scheduled_date': '2024-02-05', 'type': 'Routine'}
            ],
            'usage_efficiency': {
                'peak_usage_hours': ['11:00-14:00', '18:00-21:00'],
                'low_usage_hours': ['02:00-06:00', '22:00-01:00'],
                'energy_cost_savings': 1200
            }
        }
        
        EnhancedReportsService.save_cache_data(cache, equipment_data)
        return equipment_data