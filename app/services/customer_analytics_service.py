"""
Customer Analytics Reports Service
Handles customer behavior and analytics reports
"""

from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from sqlalchemy import func, and_, or_, desc, asc, extract
from app import db
from app.models.customer import Customer
from app.models.order import Order, OrderItem
from app.models.enhanced_reports import (
    CustomerAnalytics, ReportCache
)
from app.services.enhanced_reports_service import EnhancedReportsService

class CustomerAnalyticsService:
    """Service for customer analytics and reporting"""
    
    @staticmethod
    def get_customer_lifetime_value(restaurant_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get customer lifetime value analysis"""
        cache_key = EnhancedReportsService.generate_cache_key('customer_lifetime_value', {
            'restaurant_id': restaurant_id
        })
        
        cache = EnhancedReportsService.get_or_create_cache(cache_key, 'customer_lifetime_value', {}, 60)
        if cache and cache.get_cache_data():
            return cache.get_cache_data()
        
        query = db.session.query(
            Customer.id,
            Customer.name,
            Customer.email,
            Customer.phone,
            Customer.created_at.label('customer_since'),
            func.count(Order.id).label('total_orders'),
            func.sum(Order.total_amount).label('total_spent'),
            func.avg(Order.total_amount).label('avg_order_value'),
            func.min(Order.created_at).label('first_order'),
            func.max(Order.created_at).label('last_order'),
            func.sum(Order.tip_amount).label('total_tips'),
            func.count(func.distinct(extract('year', Order.created_at) * 100 + extract('month', Order.created_at))).label('active_months')
        ).outerjoin(
            Order, Customer.id == Order.customer_id
        ).filter(
            Order.status == 'served'
        )
        
        if restaurant_id:
            query = query.filter(Order.restaurant_id == restaurant_id)
        
        results = query.group_by(
            Customer.id, Customer.name, Customer.email, Customer.phone, Customer.created_at
        ).order_by(desc('total_spent')).all()
        
        clv_data = []
        for customer_id, name, email, phone, customer_since, orders, spent, avg_order, first_order, last_order, tips, active_months in results:
            total_spent = float(spent or 0)
            total_tips = float(tips or 0)
            customer_lifetime = (datetime.now() - customer_since).days if customer_since else 0
            
            # Calculate customer lifetime value
            if customer_lifetime > 0 and orders > 0:
                clv = total_spent
                avg_monthly_value = total_spent / active_months if active_months > 0 else 0
                purchase_frequency = orders / active_months if active_months > 0 else 0
            else:
                clv = 0
                avg_monthly_value = 0
                purchase_frequency = 0
            
            clv_data.append({
                'customer_id': customer_id,
                'name': name,
                'email': email,
                'phone': phone,
                'customer_since': customer_since.strftime('%Y-%m-%d') if customer_since else None,
                'total_orders': orders or 0,
                'total_spent': total_spent,
                'avg_order_value': float(avg_order or 0),
                'total_tips': total_tips,
                'first_order': first_order.strftime('%Y-%m-%d') if first_order else None,
                'last_order': last_order.strftime('%Y-%m-%d') if last_order else None,
                'active_months': active_months or 0,
                'customer_lifetime_days': customer_lifetime,
                'customer_lifetime_value': clv,
                'avg_monthly_value': avg_monthly_value,
                'purchase_frequency': purchase_frequency,
                'tip_percentage': (total_tips / total_spent * 100) if total_spent > 0 else 0
            })
        
        EnhancedReportsService.save_cache_data(cache, clv_data)
        return clv_data
    
    @staticmethod
    def get_repeat_customer_analysis(start_date: datetime, end_date: datetime,
                                restaurant_id: Optional[int] = None) -> Dict[str, Any]:
        """Get repeat customer analysis"""
        cache_key = EnhancedReportsService.generate_cache_key('repeat_customer_analysis', {
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'restaurant_id': restaurant_id
        })
        
        cache = EnhancedReportsService.get_or_create_cache(cache_key, 'repeat_customer_analysis', {}, 30)
        if cache and cache.get_cache_data():
            return cache.get_cache_data()
        
        # Get customer order counts
        customer_orders = db.session.query(
            Customer.id,
            Customer.name,
            func.count(Order.id).label('order_count'),
            func.sum(Order.total_amount).label('total_spent'),
            func.min(Order.created_at).label('first_order'),
            func.max(Order.created_at).label('last_order')
        ).join(
            Order, Customer.id == Order.customer_id
        ).filter(
            Order.created_at >= start_date,
            Order.created_at <= end_date,
            Order.status == 'served'
        )
        
        if restaurant_id:
            customer_orders = customer_orders.filter(Order.restaurant_id == restaurant_id)
        
        customer_orders = customer_orders.group_by(
            Customer.id, Customer.name
        ).all()
        
        # Categorize customers
        new_customers = []
        repeat_customers = []
        loyal_customers = []
        at_risk_customers = []
        
        total_customers = len(customer_orders)
        total_revenue = 0
        
        for customer_id, name, order_count, total_spent, first_order, last_order in customer_orders:
            spent = float(total_spent or 0)
            total_revenue += spent
            
            days_since_last_order = (datetime.now() - last_order).days if last_order else 999
            
            customer_data = {
                'customer_id': customer_id,
                'name': name,
                'order_count': order_count,
                'total_spent': spent,
                'avg_order_value': spent / order_count if order_count > 0 else 0,
                'first_order': first_order.strftime('%Y-%m-%d') if first_order else None,
                'last_order': last_order.strftime('%Y-%m-%d') if last_order else None,
                'days_since_last_order': days_since_last_order
            }
            
            # Categorize based on order frequency and recency
            if order_count == 1:
                new_customers.append(customer_data)
            elif order_count >= 10 and days_since_last_order <= 30:
                loyal_customers.append(customer_data)
            elif order_count >= 2 and days_since_last_order <= 60:
                repeat_customers.append(customer_data)
            elif order_count >= 2 and days_since_last_order > 60:
                at_risk_customers.append(customer_data)
        
        analysis = {
            'summary': {
                'total_customers': total_customers,
                'total_revenue': total_revenue,
                'new_customers': len(new_customers),
                'repeat_customers': len(repeat_customers),
                'loyal_customers': len(loyal_customers),
                'at_risk_customers': len(at_risk_customers),
                'new_customer_percentage': (len(new_customers) / total_customers * 100) if total_customers > 0 else 0,
                'repeat_customer_percentage': (len(repeat_customers) / total_customers * 100) if total_customers > 0 else 0,
                'loyal_customer_percentage': (len(loyal_customers) / total_customers * 100) if total_customers > 0 else 0
            },
            'new_customers': new_customers[:20],  # Top 20
            'repeat_customers': repeat_customers[:20],  # Top 20
            'loyal_customers': loyal_customers[:20],  # Top 20
            'at_risk_customers': at_risk_customers[:20]  # Top 20
        }
        
        EnhancedReportsService.save_cache_data(cache, analysis)
        return analysis
    
    @staticmethod
    def get_customer_segmentation_reports(restaurant_id: Optional[int] = None) -> Dict[str, Any]:
        """Get customer segmentation reports"""
        cache_key = EnhancedReportsService.generate_cache_key('customer_segmentation', {
            'restaurant_id': restaurant_id
        })
        
        cache = EnhancedReportsService.get_or_create_cache(cache_key, 'customer_segmentation', {}, 60)
        if cache and cache.get_cache_data():
            return cache.get_cache_data()
        
        # Get customer spending patterns
        customer_data = db.session.query(
            Customer.id,
            Customer.name,
            func.count(Order.id).label('total_orders'),
            func.sum(Order.total_amount).label('total_spent'),
            func.avg(Order.total_amount).label('avg_order_value'),
            func.max(Order.created_at).label('last_order_date')
        ).outerjoin(
            Order, Customer.id == Order.customer_id
        ).filter(
            Order.status == 'served'
        )
        
        if restaurant_id:
            customer_data = customer_data.filter(Order.restaurant_id == restaurant_id)
        
        customer_data = customer_data.group_by(
            Customer.id, Customer.name
        ).all()
        
        # Segment customers
        segments = {
            'high_value': [],      # High spenders
            'frequent': [],        # Frequent visitors
            'new': [],             # New customers
            'at_risk': [],         # At risk of churning
            'inactive': [],        # Inactive customers
            'occasional': []       # Occasional visitors
        }
        
        total_customers = len(customer_data)
        
        for customer_id, name, orders, spent, avg_order, last_order in customer_data:
            total_spent = float(spent or 0)
            days_since_last_order = (datetime.now() - last_order).days if last_order else 999
            
            customer_info = {
                'customer_id': customer_id,
                'name': name,
                'total_orders': orders or 0,
                'total_spent': total_spent,
                'avg_order_value': float(avg_order or 0),
                'days_since_last_order': days_since_last_order
            }
            
            # Apply segmentation rules
            if total_spent >= 1000:
                segments['high_value'].append(customer_info)
            elif orders >= 20:
                segments['frequent'].append(customer_info)
            elif orders == 1 and days_since_last_order <= 30:
                segments['new'].append(customer_info)
            elif orders >= 5 and days_since_last_order > 60:
                segments['at_risk'].append(customer_info)
            elif days_since_last_order > 90:
                segments['inactive'].append(customer_info)
            else:
                segments['occasional'].append(customer_info)
        
        # Calculate segment percentages
        segmentation_report = {
            'summary': {
                'total_customers': total_customers,
                'high_value_count': len(segments['high_value']),
                'frequent_count': len(segments['frequent']),
                'new_count': len(segments['new']),
                'at_risk_count': len(segments['at_risk']),
                'inactive_count': len(segments['inactive']),
                'occasional_count': len(segments['occasional']),
                'high_value_percentage': (len(segments['high_value']) / total_customers * 100) if total_customers > 0 else 0,
                'frequent_percentage': (len(segments['frequent']) / total_customers * 100) if total_customers > 0 else 0,
                'new_percentage': (len(segments['new']) / total_customers * 100) if total_customers > 0 else 0,
                'at_risk_percentage': (len(segments['at_risk']) / total_customers * 100) if total_customers > 0 else 0,
                'inactive_percentage': (len(segments['inactive']) / total_customers * 100) if total_customers > 0 else 0,
                'occasional_percentage': (len(segments['occasional']) / total_customers * 100) if total_customers > 0 else 0
            },
            'segments': {
                'high_value': segments['high_value'][:20],
                'frequent': segments['frequent'][:20],
                'new': segments['new'][:20],
                'at_risk': segments['at_risk'][:20],
                'inactive': segments['inactive'][:20],
                'occasional': segments['occasional'][:20]
            }
        }
        
        EnhancedReportsService.save_cache_data(cache, segmentation_report)
        return segmentation_report
    
    @staticmethod
    def get_loyalty_program_effectiveness(start_date: datetime, end_date: datetime,
                                      restaurant_id: Optional[int] = None) -> Dict[str, Any]:
        """Get loyalty program effectiveness analysis"""
        cache_key = EnhancedReportsService.generate_cache_key('loyalty_effectiveness', {
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'restaurant_id': restaurant_id
        })
        
        cache = EnhancedReportsService.get_or_create_cache(cache_key, 'loyalty_effectiveness', {}, 30)
        if cache and cache.get_cache_data():
            return cache.get_cache_data()
        
        # This would require loyalty program tables
        # For now, return placeholder structure
        loyalty_data = {
            'summary': {
                'total_members': 150,
                'active_members': 120,
                'new_members_this_period': 25,
                'redemption_rate': 68.5,
                'points_issued': 15000,
                'points_redeemed': 10275,
                'loyalty_revenue': 5000,
                'program_cost': 2000,
                'roi': 150.0
            },
            'member_tiers': {
                'Bronze': {'count': 80, 'avg_spent': 250, 'retention_rate': 75},
                'Silver': {'count': 45, 'avg_spent': 450, 'retention_rate': 85},
                'Gold': {'count': 20, 'avg_spent': 750, 'retention_rate': 92},
                'Platinum': {'count': 5, 'avg_spent': 1200, 'retention_rate': 98}
            },
            'top_performers': [
                {'customer_id': 1, 'name': 'John Doe', 'points_earned': 1200, 'points_redeemed': 800, 'net_spent': 1500},
                {'customer_id': 2, 'name': 'Jane Smith', 'points_earned': 1000, 'points_redeemed': 600, 'net_spent': 1200}
            ]
        }
        
        EnhancedReportsService.save_cache_data(cache, loyalty_data)
        return loyalty_data
    
    @staticmethod
    def get_feedback_rating_analysis(start_date: datetime, end_date: datetime,
                                restaurant_id: Optional[int] = None) -> Dict[str, Any]:
        """Get feedback and rating analysis"""
        cache_key = EnhancedReportsService.generate_cache_key('feedback_analysis', {
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'restaurant_id': restaurant_id
        })
        
        cache = EnhancedReportsService.get_or_create_cache(cache_key, 'feedback_analysis', {}, 30)
        if cache and cache.get_cache_data():
            return cache.get_cache_data()
        
        # This would require feedback/rating tables
        # For now, return placeholder structure
        feedback_data = {
            'summary': {
                'total_reviews': 245,
                'average_rating': 4.2,
                '5_star_reviews': 120,
                '4_star_reviews': 65,
                '3_star_reviews': 35,
                '2_star_reviews': 15,
                '1_star_reviews': 10,
                'response_rate': 78.5,
                'resolved_complaints': 45,
                'pending_complaints': 8
            },
            'rating_distribution': {
                'food_quality': 4.3,
                'service': 4.1,
                'ambiance': 4.0,
                'value_for_money': 4.2,
                'cleanliness': 4.4
            },
            'trend_analysis': {
                'current_month_avg': 4.2,
                'previous_month_avg': 4.1,
                'rating_change': 0.1,
                'review_volume_change': 15.5
            },
            'recent_feedback': [
                {'date': '2024-01-15', 'rating': 5, 'comment': 'Excellent food and service!', 'customer_id': 1},
                {'date': '2024-01-14', 'rating': 3, 'comment': 'Good food but slow service', 'customer_id': 2}
            ]
        }
        
        EnhancedReportsService.save_cache_data(cache, feedback_data)
        return feedback_data
    
    @staticmethod
    def get_customer_visit_frequency(start_date: datetime, end_date: datetime,
                                restaurant_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get customer visit frequency analysis"""
        cache_key = EnhancedReportsService.generate_cache_key('visit_frequency', {
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'restaurant_id': restaurant_id
        })
        
        cache = EnhancedReportsService.get_or_create_cache(cache_key, 'visit_frequency', {}, 30)
        if cache and cache.get_cache_data():
            return cache.get_cache_data()
        
        # Get visit patterns by day of week and hour
        visit_patterns = db.session.query(
            extract('dow', Order.created_at).label('day_of_week'),
            extract('hour', Order.created_at).label('hour_of_day'),
            func.count(Order.id).label('visit_count'),
            func.count(func.distinct(Order.customer_id)).label('unique_customers'),
            func.sum(Order.total_amount).label('total_revenue')
        ).filter(
            Order.created_at >= start_date,
            Order.created_at <= end_date,
            Order.status == 'served'
        )
        
        if restaurant_id:
            visit_patterns = visit_patterns.filter(Order.restaurant_id == restaurant_id)
        
        visit_patterns = visit_patterns.group_by(
            extract('dow', Order.created_at),
            extract('hour', Order.created_at)
        ).order_by('day_of_week', 'hour_of_day').all()
        
        # Process the data
        frequency_data = []
        day_names = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
        
        for day_of_week, hour_of_day, visit_count, unique_customers, revenue in visit_patterns:
            frequency_data.append({
                'day_of_week': int(day_of_week),
                'day_name': day_names[int(day_of_week)],
                'hour_of_day': int(hour_of_day),
                'visit_count': visit_count,
                'unique_customers': unique_customers,
                'total_revenue': float(revenue or 0),
                'avg_revenue_per_visit': float(revenue or 0) / visit_count if visit_count > 0 else 0,
                'repeat_visit_rate': (visit_count - unique_customers) / visit_count * 100 if visit_count > 0 else 0
            })
        
        EnhancedReportsService.save_cache_data(cache, frequency_data)
        return frequency_data