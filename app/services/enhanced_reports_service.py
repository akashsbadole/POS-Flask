"""
Enhanced Reports Service
Handles complex analytics and reporting calculations
"""

from datetime import datetime, timedelta, date
from typing import Dict, List, Any, Optional, Tuple
from sqlalchemy import func, and_, or_, desc, asc, extract
from flask import current_app
import json

from app import db
from app.models.order import Order, OrderStatus, OrderType, PaymentMethod
from app.models.menu import MenuItem, Category
from app.models.inventory import Ingredient
from app.models.customer import Customer
from app.models.user import User
from app.models.enhanced_reports import (
    DailySalesSummary, InventoryMovement, WasteTracking,
    EmployeePerformance, CustomerAnalytics, OperationalMetrics, ReportCache
)

class EnhancedReportsService:
    """Service for enhanced reporting and analytics"""
    
    @staticmethod
    def get_or_create_cache(cache_key: str, report_type: str, parameters: Dict[str, Any], 
                          expires_minutes: int = 60) -> Optional[ReportCache]:
        """Get or create cache entry"""
        # Check existing cache
        cache = ReportCache.query.filter_by(cache_key=cache_key).first()
        
        if cache and not cache.is_expired():
            cache.increment_hit()
            db.session.commit()
            return cache
        
        # Create new cache
        expires_at = datetime.utcnow() + timedelta(minutes=expires_minutes)
        cache = ReportCache(
            cache_key=cache_key,
            report_type=report_type,
            expires_at=expires_at
        )
        cache.set_parameters(parameters)
        
        return cache
    
    @staticmethod
    def save_cache_data(cache: ReportCache, data: Any) -> None:
        """Save data to cache"""
        cache.set_cache_data(data)
        db.session.add(cache)
        db.session.commit()
    
    @staticmethod
    def generate_cache_key(report_type: str, parameters: Dict[str, Any]) -> str:
        """Generate unique cache key"""
        import hashlib
        param_str = json.dumps(parameters, sort_keys=True)
        hash_obj = hashlib.md5(f"{report_type}_{param_str}".encode())
        return f"{report_type}_{hash_obj.hexdigest()}"
    
    # SALES ANALYTICS REPORTS
    
    @staticmethod
    def get_hourly_sales_analysis(start_date: datetime, end_date: datetime, 
                              restaurant_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get hourly sales analysis with peak identification"""
        cache_key = EnhancedReportsService.generate_cache_key('hourly_sales', {
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'restaurant_id': restaurant_id
        })
        
        cache = EnhancedReportsService.get_or_create_cache(cache_key, 'hourly_sales', {}, 30)
        if cache.get_cache_data():
            return cache.get_cache_data()
        
        query = db.session.query(
            extract('hour', Order.created_at).label('hour'),
            func.count(Order.id).label('order_count'),
            func.sum(Order.total).label('total_revenue'),
            func.avg(Order.total).label('avg_order_value')
        ).filter(
            Order.created_at >= start_date,
            Order.created_at <= end_date,
            Order.status == OrderStatus.SERVED
        )
        
        if restaurant_id:
            query = query.filter(Order.restaurant_id == restaurant_id)
        
        results = query.group_by(extract('hour', Order.created_at)).order_by('hour').all()
        
        # Process results
        hourly_data = []
        peak_hour = None
        max_revenue = 0
        
        for hour, order_count, total_revenue, avg_order_value in results:
            revenue = float(total_revenue or 0)
            hour_data = {
                'hour': int(hour),
                'order_count': order_count,
                'total_revenue': revenue,
                'avg_order_value': float(avg_order_value or 0),
                'time_period': f"{hour}:00 - {hour}:59"
            }
            hourly_data.append(hour_data)
            
            if revenue > max_revenue:
                max_revenue = revenue
                peak_hour = int(hour)
        
        # Add peak hour information
        for hour_data in hourly_data:
            hour_data['is_peak'] = hour_data['hour'] == peak_hour
        
        EnhancedReportsService.save_cache_data(cache, hourly_data)
        return hourly_data
    
    @staticmethod
    def get_day_part_performance(start_date: datetime, end_date: datetime,
                             restaurant_id: Optional[int] = None) -> Dict[str, Any]:
        """Get day-part performance analysis (breakfast, lunch, dinner)"""
        cache_key = EnhancedReportsService.generate_cache_key('day_part_performance', {
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'restaurant_id': restaurant_id
        })
        
        cache = EnhancedReportsService.get_or_create_cache(cache_key, 'day_part_performance', {}, 30)
        if cache.get_cache_data():
            return cache.get_cache_data()
        
        # Define day parts
        day_parts = {
            'breakfast': {'start': 6, 'end': 11},   # 6 AM - 11 AM
            'lunch': {'start': 11, 'end': 16},     # 11 AM - 4 PM
            'dinner': {'start': 16, 'end': 23},     # 4 PM - 11 PM
            'late_night': {'start': 23, 'end': 29}  # 11 PM - 5 AM
        }
        
        results = {}
        
        for part_name, time_range in day_parts.items():
            query = db.session.query(
                func.count(Order.id).label('order_count'),
                func.sum(Order.total).label('total_revenue'),
                func.avg(Order.total).label('avg_order_value'),
                func.count(func.distinct(Order.customer_id)).label('unique_customers')
            ).filter(
                Order.created_at >= start_date,
                Order.created_at <= end_date,
                Order.status == OrderStatus.SERVED,
                extract('hour', Order.created_at) >= time_range['start'],
                extract('hour', Order.created_at) < time_range['end']
            )
            
            if restaurant_id:
                query = query.filter(Order.restaurant_id == restaurant_id)
            
            part_data = query.first()
            
            results[part_name] = {
                'order_count': part_data.order_count or 0,
                'total_revenue': float(part_data.total_revenue or 0),
                'avg_order_value': float(part_data.avg_order_value or 0),
                'unique_customers': part_data.unique_customers or 0,
                'time_range': f"{time_range['start']}:00 - {time_range['end']}:00"
            }
        
        # Calculate percentages
        total_revenue = sum(part['total_revenue'] for part in results.values())
        for part_name, part_data in results.items():
            part_data['revenue_percentage'] = (
                (part_data['total_revenue'] / total_revenue * 100) if total_revenue > 0 else 0
            )
        
        EnhancedReportsService.save_cache_data(cache, results)
        return results
    
    @staticmethod
    def get_menu_item_performance_ranking(start_date: datetime, end_date: datetime,
                                     restaurant_id: Optional[int] = None,
                                     category_id: Optional[int] = None,
                                     limit: int = 50) -> List[Dict[str, Any]]:
        """Get menu items ranked by performance"""
        cache_key = EnhancedReportsService.generate_cache_key('menu_item_ranking', {
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'restaurant_id': restaurant_id,
            'category_id': category_id,
            'limit': limit
        })
        
        cache = EnhancedReportsService.get_or_create_cache(cache_key, 'menu_item_ranking', {}, 60)
        if cache.get_cache_data():
            return cache.get_cache_data()
        
        from app.models.order import OrderItem
        
        query = db.session.query(
            MenuItem.id,
            MenuItem.name,
            Category.name.label('category_name'),
            func.sum(OrderItem.quantity).label('total_quantity'),
            func.sum(OrderItem.quantity * OrderItem.unit_price).label('total_revenue'),
            func.count(OrderItem.id).label('order_frequency'),
            func.avg(OrderItem.quantity * OrderItem.unit_price).label('avg_price')
        ).join(
            OrderItem, MenuItem.id == OrderItem.item_id
        ).join(
            Order, OrderItem.order_id == Order.id
        ).join(
            Category, MenuItem.category_id == Category.id
        ).filter(
            Order.created_at >= start_date,
            Order.created_at <= end_date,
            Order.status == OrderStatus.SERVED
        )
        
        if restaurant_id:
            query = query.filter(Order.restaurant_id == restaurant_id)
        
        if category_id:
            query = query.filter(MenuItem.category_id == category_id)
        
        results = query.group_by(
            MenuItem.id, MenuItem.name, Category.name
        ).order_by(desc('total_revenue')).limit(limit).all()
        
        # Process results
        item_rankings = []
        for rank, (item_id, name, category_name, total_quantity, total_revenue, 
                   order_frequency, avg_price) in enumerate(results, 1):
            item_rankings.append({
                'rank': rank,
                'item_id': item_id,
                'name': name,
                'category_name': category_name,
                'total_quantity': total_quantity or 0,
                'total_revenue': float(total_revenue or 0),
                'order_frequency': order_frequency or 0,
                'avg_price': float(avg_price or 0),
                'revenue_per_item': float(total_revenue or 0) / (total_quantity or 1)
            })
        
        EnhancedReportsService.save_cache_data(cache, item_rankings)
        return item_rankings
    
    @staticmethod
    def get_category_wise_sales_analysis(start_date: datetime, end_date: datetime,
                                    restaurant_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get category-wise sales analysis"""
        cache_key = EnhancedReportsService.generate_cache_key('category_sales', {
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'restaurant_id': restaurant_id
        })
        
        cache = EnhancedReportsService.get_or_create_cache(cache_key, 'category_sales', {}, 30)
        if cache.get_cache_data():
            return cache.get_cache_data()
        
        from app.models.order import OrderItem
        
        query = db.session.query(
            Category.id,
            Category.name,
            func.count(func.distinct(OrderItem.order_id)).label('order_count'),
            func.sum(OrderItem.quantity).label('total_quantity'),
            func.sum(OrderItem.quantity * OrderItem.unit_price).label('total_revenue'),
            func.count(func.distinct(Order.id)).label('unique_orders')
        ).join(
            MenuItem, Category.id == MenuItem.category_id
        ).join(
            OrderItem, MenuItem.id == OrderItem.item_id
        ).join(
            Order, OrderItem.order_id == Order.id
        ).filter(
            Order.created_at >= start_date,
            Order.created_at <= end_date,
            Order.status == OrderStatus.SERVED
        )
        
        if restaurant_id:
            query = query.filter(Order.restaurant_id == restaurant_id)
        
        results = query.group_by(Category.id, Category.name).order_by(desc('total_revenue')).all()
        
        # Calculate total for percentages
        total_revenue = sum(float(result.total_revenue or 0) for result in results)
        
        category_data = []
        for cat_id, name, order_count, total_quantity, cat_revenue, unique_orders in results:
            revenue = float(cat_revenue or 0)
            category_data.append({
                'category_id': cat_id,
                'name': name,
                'order_count': order_count or 0,
                'total_quantity': total_quantity or 0,
                'total_revenue': revenue,
                'unique_orders': unique_orders or 0,
                'revenue_percentage': (revenue / total_revenue * 100) if total_revenue > 0 else 0,
                'avg_order_value': revenue / (order_count or 1)
            })
        
        EnhancedReportsService.save_cache_data(cache, category_data)
        return category_data
    
    @staticmethod
    def get_payment_method_breakdown(start_date: datetime, end_date: datetime,
                                 restaurant_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get detailed payment method breakdown"""
        cache_key = EnhancedReportsService.generate_cache_key('payment_breakdown', {
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'restaurant_id': restaurant_id
        })
        
        cache = EnhancedReportsService.get_or_create_cache(cache_key, 'payment_breakdown', {}, 30)
        if cache.get_cache_data():
            return cache.get_cache_data()
        
        from app.models.order import Payment
        
        query = db.session.query(
            Payment.method,
            func.count(Payment.id).label('transaction_count'),
            func.sum(Payment.amount).label('total_amount'),
            func.sum(Payment.tip_amount).label('total_tips'),
            func.avg(Payment.amount).label('avg_amount')
        ).join(
            Order, Payment.order_id == Order.id
        ).filter(
            Order.created_at >= start_date,
            Order.created_at <= end_date,
            Order.status == OrderStatus.SERVED,
            Payment.status == 'completed'
        )
        
        if restaurant_id:
            query = query.filter(Order.restaurant_id == restaurant_id)
        
        results = query.group_by(Payment.method).order_by(desc('total_amount')).all()
        
        # Calculate total for percentages
        total_amount = sum(float(result.total_amount or 0) for result in results)
        
        payment_data = []
        for method, count, amount, tips, avg_amount in results:
            total = float(amount or 0)
            payment_data.append({
                'method': method.value if method else 'Unknown',
                'transaction_count': count or 0,
                'total_amount': total,
                'total_tips': float(tips or 0),
                'avg_amount': float(avg_amount or 0),
                'amount_percentage': (total / total_amount * 100) if total_amount > 0 else 0,
                'tip_percentage': (float(tips or 0) / total * 100) if total > 0 else 0
            })
        
        EnhancedReportsService.save_cache_data(cache, payment_data)
        return payment_data
    
    @staticmethod
    def get_discount_promotion_analysis(start_date: datetime, end_date: datetime,
                                  restaurant_id: Optional[int] = None) -> Dict[str, Any]:
        """Analyze discount and promotion effectiveness"""
        cache_key = EnhancedReportsService.generate_cache_key('discount_analysis', {
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'restaurant_id': restaurant_id
        })
        
        cache = EnhancedReportsService.get_or_create_cache(cache_key, 'discount_analysis', {}, 30)
        if cache.get_cache_data():
            return cache.get_cache_data()
        
        # Orders with discounts
        discounted_query = db.session.query(
            func.count(Order.id).label('discounted_orders'),
            func.sum(Order.discount_amount).label('total_discount'),
            func.sum(Order.total).label('discounted_revenue'),
            func.avg(Order.discount_amount).label('avg_discount')
        ).filter(
            Order.created_at >= start_date,
            Order.created_at <= end_date,
            Order.status == OrderStatus.SERVED,
            Order.discount_amount > 0
        )
        
        # Orders without discounts
        regular_query = db.session.query(
            func.count(Order.id).label('regular_orders'),
            func.sum(Order.total).label('regular_revenue')
        ).filter(
            Order.created_at >= start_date,
            Order.created_at <= end_date,
            Order.status == OrderStatus.SERVED,
            Order.discount_amount.is_(None) | (Order.discount_amount == 0)
        )
        
        if restaurant_id:
            discounted_query = discounted_query.filter(Order.restaurant_id == restaurant_id)
            regular_query = regular_query.filter(Order.restaurant_id == restaurant_id)
        
        discounted_data = discounted_query.first()
        regular_data = regular_query.first()
        
        # Discount reason analysis
        discount_reasons_query = db.session.query(
            Order.discount_reason,
            func.count(Order.id).label('usage_count'),
            func.sum(Order.discount_amount).label('total_discount')
        ).filter(
            Order.created_at >= start_date,
            Order.created_at <= end_date,
            Order.status == OrderStatus.SERVED,
            Order.discount_reason.isnot(None)
        )
        
        if restaurant_id:
            discount_reasons_query = discount_reasons_query.filter(Order.restaurant_id == restaurant_id)
        
        reason_results = discount_reasons_query.group_by(Order.discount_reason).order_by(desc('usage_count')).all()
        
        # Process results
        total_orders = (discounted_data.discounted_orders or 0) + (regular_data.regular_orders or 0)
        total_revenue = float(discounted_data.discounted_revenue or 0) + float(regular_data.regular_revenue or 0)
        
        analysis = {
            'summary': {
                'total_orders': total_orders,
                'discounted_orders': discounted_data.discounted_orders or 0,
                'regular_orders': regular_data.regular_orders or 0,
                'discount_usage_rate': ((discounted_data.discounted_orders or 0) / total_orders * 100) if total_orders > 0 else 0,
                'total_revenue': total_revenue,
                'total_discount': float(discounted_data.total_discount or 0),
                'discount_percentage': (float(discounted_data.total_discount or 0) / total_revenue * 100) if total_revenue > 0 else 0,
                'avg_discount_amount': float(discounted_data.avg_discount or 0)
            },
            'reasons': []
        }
        
        for reason, count, total_discount in reason_results:
            analysis['reasons'].append({
                'reason': reason,
                'usage_count': count,
                'total_discount': float(total_discount or 0),
                'avg_discount': float(total_discount or 0) / count
            })
        
        EnhancedReportsService.save_cache_data(cache, analysis)
        return analysis
    
    # FINANCIAL REPORTS
    
    @staticmethod
    def get_profit_loss_statement(start_date: datetime, end_date: datetime,
                              restaurant_id: Optional[int] = None) -> Dict[str, Any]:
        """Generate profit and loss statement"""
        cache_key = EnhancedReportsService.generate_cache_key('profit_loss', {
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'restaurant_id': restaurant_id
        })
        
        cache = EnhancedReportsService.get_or_create_cache(cache_key, 'profit_loss', {}, 60)
        if cache.get_cache_data():
            return cache.get_cache_data()
        
        # Revenue
        revenue_query = db.session.query(
            func.sum(Order.total).label('total_revenue'),
            func.sum(Order.subtotal).label('net_revenue'),
            func.sum(Order.tax_amount).label('tax_collected'),
            func.count(Order.id).label('order_count')
        ).filter(
            Order.created_at >= start_date,
            Order.created_at <= end_date,
            Order.status == OrderStatus.SERVED
        )
        
        if restaurant_id:
            revenue_query = revenue_query.filter(Order.restaurant_id == restaurant_id)
        
        revenue_data = revenue_query.first()
        
        # Cost of Goods Sold (COGS)
        from app.models.order import OrderItem
        from app.models.inventory import MenuItemIngredient
        
        cogs_query = db.session.query(
            func.sum(MenuItemIngredient.quantity_required * Ingredient.unit_cost).label('total_cogs')
        ).join(
            OrderItem, MenuItemIngredient.menu_item_id == OrderItem.item_id
        ).join(
            Order, OrderItem.order_id == Order.id
        ).join(
            Ingredient, MenuItemIngredient.ingredient_id == Ingredient.id
        ).filter(
            Order.created_at >= start_date,
            Order.created_at <= end_date,
            Order.status == OrderStatus.SERVED
        )
        
        if restaurant_id:
            cogs_query = cogs_query.filter(Order.restaurant_id == restaurant_id)
        
        cogs_data = cogs_query.first()
        
        # Expenses
        from app.models.accounting import Expense
        
        expenses_query = db.session.query(
            Expense.category,
            func.sum(Expense.amount).label('total_expense')
        ).filter(
            Expense.created_at >= start_date,
            Expense.created_at <= end_date
        )
        
        if restaurant_id:
            expenses_query = expenses_query.filter(Expense.restaurant_id == restaurant_id)
        
        expense_results = expenses_query.group_by(Expense.category).all()
        
        # Calculate metrics
        total_revenue = float(revenue_data.total_revenue or 0)
        net_revenue = float(revenue_data.net_revenue or 0)
        total_cogs = float(cogs_data.total_cogs or 0)
        gross_profit = net_revenue - total_cogs
        gross_margin = (gross_profit / net_revenue * 100) if net_revenue > 0 else 0
        
        total_expenses = sum(float(exp.total_expense or 0) for exp in expense_results)
        net_profit = gross_profit - total_expenses
        net_margin = (net_profit / net_revenue * 100) if net_revenue > 0 else 0
        
        # Process expenses by category
        expenses_by_category = []
        for category, amount in expense_results:
            expenses_by_category.append({
                'category': category,
                'amount': float(amount or 0),
                'percentage': (float(amount or 0) / total_expenses * 100) if total_expenses > 0 else 0
            })
        
        profit_loss = {
            'period': {
                'start_date': start_date.strftime('%Y-%m-%d'),
                'end_date': end_date.strftime('%Y-%m-%d')
            },
            'revenue': {
                'total_revenue': total_revenue,
                'net_revenue': net_revenue,
                'tax_collected': float(revenue_data.tax_collected or 0),
                'order_count': revenue_data.order_count or 0,
                'avg_order_value': total_revenue / (revenue_data.order_count or 1)
            },
            'cost_of_goods_sold': {
                'total_cogs': total_cogs,
                'cogs_percentage': (total_cogs / net_revenue * 100) if net_revenue > 0 else 0
            },
            'gross_profit': {
                'amount': gross_profit,
                'margin_percentage': gross_margin
            },
            'expenses': {
                'total_expenses': total_expenses,
                'expenses_by_category': expenses_by_category,
                'expense_percentage': (total_expenses / net_revenue * 100) if net_revenue > 0 else 0
            },
            'net_profit': {
                'amount': net_profit,
                'margin_percentage': net_margin
            }
        }
        
        EnhancedReportsService.save_cache_data(cache, profit_loss)
        return profit_loss
    
    @staticmethod
    def get_cash_flow_analysis(start_date: datetime, end_date: datetime,
                           restaurant_id: Optional[int] = None) -> Dict[str, Any]:
        """Analyze cash flow for the period"""
        cache_key = EnhancedReportsService.generate_cache_key('cash_flow', {
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'restaurant_id': restaurant_id
        })
        
        cache = EnhancedReportsService.get_or_create_cache(cache_key, 'cash_flow', {}, 60)
        if cache.get_cache_data():
            return cache.get_cache_data()
        
        # Cash inflows (sales revenue)
        inflow_query = db.session.query(
            func.sum(Order.total).label('total_inflow'),
            func.count(Order.id).label('transaction_count')
        ).filter(
            Order.created_at >= start_date,
            Order.created_at <= end_date,
            Order.status == OrderStatus.SERVED
        )
        
        if restaurant_id:
            inflow_query = inflow_query.filter(Order.restaurant_id == restaurant_id)
        
        inflow_data = inflow_query.first()
        
        # Cash outflows (expenses)
        from app.models.accounting import Expense
        
        outflow_query = db.session.query(
            func.sum(Expense.amount).label('total_outflow'),
            func.count(Expense.id).label('expense_count')
        ).filter(
            Expense.created_at >= start_date,
            Expense.created_at <= end_date
        )
        
        if restaurant_id:
            outflow_query = outflow_query.filter(Expense.restaurant_id == restaurant_id)
        
        outflow_data = outflow_query.first()
        
        # Net cash flow
        total_inflow = float(inflow_data.total_inflow or 0)
        total_outflow = float(outflow_data.total_outflow or 0)
        net_cash_flow = total_inflow - total_outflow
        
        # Daily breakdown
        daily_cash_flow = EnhancedReportsService._get_daily_cash_flow(start_date, end_date, restaurant_id)
        
        cash_flow = {
            'period': {
                'start_date': start_date.strftime('%Y-%m-%d'),
                'end_date': end_date.strftime('%Y-%m-%d')
            },
            'summary': {
                'total_inflow': total_inflow,
                'total_outflow': total_outflow,
                'net_cash_flow': net_cash_flow,
                'inflow_transactions': inflow_data.transaction_count or 0,
                'outflow_transactions': outflow_data.expense_count or 0
            },
            'daily_breakdown': daily_cash_flow,
            'cash_flow_trend': EnhancedReportsService._calculate_cash_flow_trend(daily_cash_flow)
        }
        
        EnhancedReportsService.save_cache_data(cache, cash_flow)
        return cash_flow
    
    @staticmethod
    def _get_daily_cash_flow(start_date: datetime, end_date: datetime,
                          restaurant_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get daily cash flow breakdown"""
        from app.models.accounting import Expense
        
        # Generate date range
        date_range = []
        current_date = start_date.date()
        while current_date <= end_date.date():
            date_range.append(current_date)
            current_date += timedelta(days=1)
        
        daily_data = []
        
        for single_date in date_range:
            date_start = datetime.combine(single_date, datetime.min.time())
            date_end = datetime.combine(single_date, datetime.max.time())
            
            # Daily inflow
            daily_inflow = db.session.query(func.sum(Order.total)).filter(
                Order.created_at >= date_start,
                Order.created_at <= date_end,
                Order.status == OrderStatus.SERVED
            )
            
            if restaurant_id:
                daily_inflow = daily_inflow.filter(Order.restaurant_id == restaurant_id)
            
            inflow_amount = float(daily_inflow.scalar() or 0)
            
            # Daily outflow
            daily_outflow = db.session.query(func.sum(Expense.amount)).filter(
                Expense.created_at >= date_start,
                Expense.created_at <= date_end
            )
            
            if restaurant_id:
                daily_outflow = daily_outflow.filter(Expense.restaurant_id == restaurant_id)
            
            outflow_amount = float(daily_outflow.scalar() or 0)
            
            daily_data.append({
                'date': single_date.strftime('%Y-%m-%d'),
                'inflow': inflow_amount,
                'outflow': outflow_amount,
                'net_flow': inflow_amount - outflow_amount
            })
        
        return daily_data
    
    @staticmethod
    def _calculate_cash_flow_trend(daily_cash_flow: List[Dict[str, Any]]) -> str:
        """Calculate cash flow trend"""
        if len(daily_cash_flow) < 7:
            return 'insufficient_data'
        
        # Compare last 7 days with previous 7 days
        recent_avg = sum(day['net_flow'] for day in daily_cash_flow[-7:]) / 7
        previous_avg = sum(day['net_flow'] for day in daily_cash_flow[-14:-7]) / 7 if len(daily_cash_flow) >= 14 else recent_avg
        
        if recent_avg > previous_avg * 1.1:
            return 'improving'
        elif recent_avg < previous_avg * 0.9:
            return 'declining'
        else:
            return 'stable'