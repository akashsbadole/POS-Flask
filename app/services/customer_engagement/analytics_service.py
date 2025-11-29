"""
Customer Analytics Service
Handles comprehensive customer analytics including:
- Advanced customer segmentation
- Lifetime value prediction
- Churn prediction and prevention
- Visit pattern analysis
- Spending behavior analysis
- Customer journey mapping
"""

from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from sqlalchemy import func, and_, or_, desc, extract
import json
import math

from app import db
from app.models.customer import Customer
from app.models.customer_engagement import (
    CustomerBehavior, CustomerJourney, CustomerPreference
)
from app.models.order import Order, OrderItem
from app.models.menu import MenuItem, Category


class CustomerAnalyticsService:
    """Advanced customer analytics service"""
    
    @staticmethod
    def get_customer_segments(restaurant_id: int, segmentation_type: str = 'behavioral') -> Dict[str, Any]:
        """Perform advanced customer segmentation"""
        # Get customer data
        customers = Customer.query.filter_by(
            restaurant_id=restaurant_id,
            is_active=True
        ).all()
        
        if segmentation_type == 'behavioral':
            segments = CustomerAnalyticsService._behavioral_segmentation(customers)
        elif segmentation_type == 'value':
            segments = CustomerAnalyticsService._value_segmentation(customers)
        elif segmentation_type == 'rfm':
            segments = CustomerAnalyticsService._rfm_segmentation(customers)
        elif segmentation_type == 'engagement':
            segments = CustomerAnalyticsService._engagement_segmentation(customers)
        elif segmentation_type == 'predictive':
            segments = CustomerAnalyticsService._predictive_segmentation(customers)
        else:
            segments = CustomerAnalyticsService._behavioral_segmentation(customers)
        
        return {
            'segmentation_type': segmentation_type,
            'total_customers': len(customers),
            'segments': segments,
            'segment_analysis': CustomerAnalyticsService._analyze_segments(segments, customers),
            'recommendations': CustomerAnalyticsService._generate_segment_recommendations(segments)
        }
    
    @staticmethod
    def _behavioral_segmentation(customers: List[Customer]) -> List[Dict]:
        """Perform behavioral segmentation"""
        segments = {
            'loyal_customers': [],
            'at_risk_customers': [],
            'new_customers': [],
            'occasional_customers': [],
            'high_value_customers': [],
            'price_sensitive_customers': []
        }
        
        for customer in customers:
            # Calculate behavioral metrics
            days_since_last_order = (datetime.now() - customer.last_order_date).days if customer.last_order_date else 999
            avg_order_value = float(customer.average_order_value or 0)
            order_frequency = CustomerAnalyticsService._calculate_order_frequency(customer)
            
            # Segment based on behavior
            if days_since_last_order <= 30 and order_frequency >= 4:  # Frequent recent visitors
                if avg_order_value >= 50:
                    segments['high_value_customers'].append(customer)
                else:
                    segments['loyal_customers'].append(customer)
            elif days_since_last_order <= 90 and order_frequency >= 2:
                segments['occasional_customers'].append(customer)
            elif days_since_last_order > 90 and order_frequency >= 1:
                segments['at_risk_customers'].append(customer)
            elif days_since_last_order <= 30 and order_frequency == 1:
                segments['new_customers'].append(customer)
            
            # Price sensitivity based on average order value vs. menu prices
            if avg_order_value > 0:
                avg_menu_price = CustomerAnalyticsService._get_average_menu_price(customer.restaurant_id)
                if avg_order_value < avg_menu_price * 0.8:
                    if customer not in segments['price_sensitive_customers']:
                        segments['price_sensitive_customers'].append(customer)
        
        return [
            {
                'name': segment_name.replace('_', ' ').title(),
                'customers': segment_customers,
                'count': len(segment_customers),
                'percentage': (len(segment_customers) / len(customers)) * 100 if customers else 0,
                'characteristics': CustomerAnalyticsService._describe_segment_characteristics(segment_name, segment_customers)
            }
            for segment_name, segment_customers in segments.items()
        ]
    
    @staticmethod
    def _value_segmentation(customers: List[Customer]) -> List[Dict]:
        """Perform value-based segmentation"""
        segments = {
            'vip_champions': [],
            'loyal_customers': [],
            'potential_loyal': [],
            'new_customers': [],
            'low_value': []
        }
        
        # Calculate value thresholds
        total_spent_values = [float(c.total_spent or 0) for c in customers]
        thresholds = {
            'low': 0,
            'medium': 0,
            'high': 0,
            'vip': 0
        }
        
        if total_spent_values:
            percentiles = [
                math.floor(len(total_spent_values) * 0.2),  # 20th percentile
                math.floor(len(total_spent_values) * 0.4),  # 40th percentile
                math.floor(len(total_spent_values) * 0.6),  # 60th percentile
                math.floor(len(total_spent_values) * 0.8)   # 80th percentile
            ]
            sorted_values = sorted(total_spent_values)
            
            if len(sorted_values) > 4:
                thresholds = {
                    'low': sorted_values[percentiles[0]],
                    'medium': sorted_values[percentiles[1]],
                    'high': sorted_values[percentiles[2]],
                    'vip': sorted_values[percentiles[3]]
                }
            else:
                # Fallback for small customer base
                avg_spent = sum(total_spent_values) / len(total_spent_values)
                thresholds = {
                    'low': avg_spent * 0.5,
                    'medium': avg_spent,
                    'high': avg_spent * 1.5,
                    'vip': avg_spent * 2.0
                }
        
        # Segment customers
        for customer in customers:
            total_spent = float(customer.total_spent or 0)
            
            if total_spent >= thresholds['vip']:
                segments['vip_champions'].append(customer)
            elif total_spent >= thresholds['high']:
                segments['loyal_customers'].append(customer)
            elif total_spent >= thresholds['medium']:
                segments['potential_loyal'].append(customer)
            elif total_spent >= thresholds['low']:
                segments['new_customers'].append(customer)
            else:
                segments['low_value'].append(customer)
        
        return [
            {
                'name': segment_name.replace('_', ' ').title(),
                'customers': segment_customers,
                'count': len(segment_customers),
                'percentage': (len(segment_customers) / len(customers)) * 100 if customers else 0,
                'characteristics': CustomerAnalyticsService._describe_value_segment_characteristics(segment_name, segment_customers)
            }
            for segment_name, segment_customers in segments.items()
        ]
    
    @staticmethod
    def _rfm_segmentation(customers: List[Customer]) -> List[Dict]:
        """Perform RFM (Recency, Frequency, Monetary) segmentation"""
        segments = {
            'champions': [],      # High R, High F, High M
            'loyal_customers': [],  # High R, High F, Medium M
            'potential_loyalist': [],  # High R, Medium F, High M
            'new_customers': [],   # High R, Low F, Low M
            'at_risk': [],        # Low R, High F, High M
            'cant_lose_them': [],  # Low R, Medium F, Medium M
            'hibernating': [],    # Low R, Low F, High M
            'lost': []           # Low R, Low F, Low M
        }
        
        for customer in customers:
            rfm_scores = CustomerAnalyticsService._calculate_rfm_scores(customer)
            
            # Segment based on RFM scores
            r, f, m = rfm_scores['recency'], rfm_scores['frequency'], rfm_scores['monetary']
            
            if r >= 4 and f >= 4 and m >= 4:
                segments['champions'].append(customer)
            elif r >= 4 and f >= 4 and m >= 3:
                segments['loyal_customers'].append(customer)
            elif r >= 4 and f >= 2 and m >= 4:
                segments['potential_loyalist'].append(customer)
            elif r >= 4 and f <= 2 and m <= 2:
                segments['new_customers'].append(customer)
            elif r <= 2 and f >= 4 and m >= 4:
                segments['at_risk'].append(customer)
            elif r <= 2 and f >= 3 and m >= 3:
                segments['cant_lose_them'].append(customer)
            elif r <= 2 and f <= 2 and m >= 4:
                segments['hibernating'].append(customer)
            else:
                segments['lost'].append(customer)
        
        return [
            {
                'name': segment_name.replace('_', ' ').title(),
                'customers': segment_customers,
                'count': len(segment_customers),
                'percentage': (len(segment_customers) / len(customers)) * 100 if customers else 0,
                'characteristics': CustomerAnalyticsService._describe_rfm_segment_characteristics(segment_name, segment_customers)
            }
            for segment_name, segment_customers in segments.items()
        ]
    
    @staticmethod
    def _engagement_segmentation(customers: List[Customer]) -> List[Dict]:
        """Perform engagement-based segmentation"""
        segments = {
            'highly_engaged': [],
            'moderately_engaged': [],
            'low_engagement': [],
            'at_risk_churn': [],
            'new_engagers': []
        }
        
        for customer in customers:
            engagement_score = CustomerAnalyticsService._calculate_engagement_score(customer)
            
            if engagement_score >= 8:
                segments['highly_engaged'].append(customer)
            elif engagement_score >= 6:
                segments['moderately_engaged'].append(customer)
            elif engagement_score >= 4:
                segments['low_engagement'].append(customer)
            elif engagement_score >= 2:
                segments['at_risk_churn'].append(customer)
            else:
                segments['new_engagers'].append(customer)
        
        return [
            {
                'name': segment_name.replace('_', ' ').title(),
                'customers': segment_customers,
                'count': len(segment_customers),
                'percentage': (len(segment_customers) / len(customers)) * 100 if customers else 0,
                'characteristics': CustomerAnalyticsService._describe_engagement_segment_characteristics(segment_name, segment_customers)
            }
            for segment_name, segment_customers in segments.items()
        ]
    
    @staticmethod
    def _predictive_segmentation(customers: List[Customer]) -> List[Dict]:
        """Perform predictive segmentation using ML-like scoring"""
        segments = {
            'high_churn_risk': [],
            'medium_churn_risk': [],
            'low_churn_risk': [],
            'high_growth_potential': [],
            'medium_growth_potential': [],
            'low_growth_potential': []
        }
        
        for customer in customers:
            churn_risk = CustomerAnalyticsService._calculate_churn_risk(customer)
            growth_potential = CustomerAnalyticsService._calculate_growth_potential(customer)
            
            # Churn risk segmentation
            if churn_risk >= 0.8:
                segments['high_churn_risk'].append(customer)
            elif churn_risk >= 0.6:
                segments['medium_churn_risk'].append(customer)
            elif churn_risk >= 0.4:
                segments['low_churn_risk'].append(customer)
            
            # Growth potential segmentation
            if growth_potential >= 0.8:
                segments['high_growth_potential'].append(customer)
            elif growth_potential >= 0.6:
                segments['medium_growth_potential'].append(customer)
            elif growth_potential >= 0.4:
                segments['low_growth_potential'].append(customer)
        
        return [
            {
                'name': segment_name.replace('_', ' ').title(),
                'customers': segment_customers,
                'count': len(segment_customers),
                'percentage': (len(segment_customers) / len(customers)) * 100 if customers else 0,
                'characteristics': CustomerAnalyticsService._describe_predictive_segment_characteristics(segment_name, segment_customers)
            }
            for segment_name, segment_customers in segments.items()
        ]
    
    @staticmethod
    def predict_customer_lifetime_value(customer_id: int) -> Dict[str, Any]:
        """Predict customer lifetime value (CLV)"""
        customer = Customer.query.get(customer_id)
        if not customer:
            return {}
        
        # Historical CLV calculation
        historical_clv = float(customer.total_spent or 0)
        
        # Predictive CLV components
        avg_order_value = float(customer.average_order_value or 0)
        order_frequency = CustomerAnalyticsService._calculate_order_frequency(customer)
        customer_lifetime_months = CustomerAnalyticsService._calculate_customer_lifetime(customer)
        
        # Predict future behavior
        predicted_months = CustomerAnalyticsService._predict_customer_lifetime_months(customer)
        predicted_frequency = CustomerAnalyticsService._predict_future_frequency(customer)
        predicted_avg_order = CustomerAnalyticsService._predict_future_order_value(customer)
        
        # Calculate predicted CLV
        if predicted_months > 0 and predicted_frequency > 0:
            predicted_clv = predicted_avg_order * predicted_frequency * predicted_months
        else:
            predicted_clv = 0
        
        # Adjust for loyalty tier
        loyalty_multiplier = CustomerAnalyticsService._get_loyalty_multiplier(customer)
        adjusted_clv = predicted_clv * loyalty_multiplier
        
        # Risk adjustment
        churn_risk = CustomerAnalyticsService._calculate_churn_risk(customer)
        risk_adjustment = 1 - (churn_risk * 0.3)  # Reduce CLV by churn risk
        final_clv = adjusted_clv * risk_adjustment
        
        return {
            'customer_id': customer_id,
            'historical_clv': historical_clv,
            'predicted_clv': predicted_clv,
            'adjusted_clv': final_clv,
            'clv_tier': CustomerAnalyticsService._get_clv_tier(final_clv),
            'components': {
                'avg_order_value': avg_order_value,
                'order_frequency': order_frequency,
                'customer_lifetime_months': customer_lifetime_months,
                'predicted_months': predicted_months,
                'predicted_frequency': predicted_frequency,
                'predicted_avg_order': predicted_avg_order,
                'loyalty_multiplier': loyalty_multiplier,
                'churn_risk': churn_risk,
                'risk_adjustment': risk_adjustment
            },
            'confidence': CustomerAnalyticsService._calculate_clv_confidence(customer),
            'recommendations': CustomerAnalyticsService._generate_clv_recommendations(customer, final_clv)
        }
    
    @staticmethod
    def predict_churn_risk(restaurant_id: int, customer_id: Optional[int] = None) -> Dict[str, Any]:
        """Predict churn risk for customers"""
        if customer_id:
            # Predict for specific customer
            customer = Customer.query.get(customer_id)
            if not customer:
                return {}
            
            churn_risk = CustomerAnalyticsService._calculate_churn_risk(customer)
            risk_factors = CustomerAnalyticsService._analyze_churn_factors(customer)
            
            return {
                'customer_id': customer_id,
                'churn_risk_score': churn_risk,
                'risk_level': CustomerAnalyticsService._get_risk_level(churn_risk),
                'risk_factors': risk_factors,
                'prediction_date': datetime.now().isoformat(),
                'recommendations': CustomerAnalyticsService._generate_retention_recommendations(customer, churn_risk)
            }
        else:
            # Predict for all customers
            customers = Customer.query.filter_by(
                restaurant_id=restaurant_id,
                is_active=True
            ).all()
            
            predictions = []
            risk_distribution = {'low': 0, 'medium': 0, 'high': 0, 'critical': 0}
            
            for customer in customers:
                churn_risk = CustomerAnalyticsService._calculate_churn_risk(customer)
                risk_level = CustomerAnalyticsService._get_risk_level(churn_risk)
                
                predictions.append({
                    'customer_id': customer.id,
                    'customer_name': customer.get_full_name(),
                    'churn_risk_score': churn_risk,
                    'risk_level': risk_level,
                    'last_order_date': customer.last_order_date.isoformat() if customer.last_order_date else None,
                    'days_since_last_order': (datetime.now() - customer.last_order_date).days if customer.last_order_date else 999
                })
                
                risk_distribution[risk_level] += 1
            
            return {
                'total_customers': len(customers),
                'predictions': predictions,
                'risk_distribution': risk_distribution,
                'high_risk_customers': [p for p in predictions if p['risk_level'] in ['high', 'critical']],
                'retention_campaign_targets': len([p for p in predictions if p['risk_level'] in ['medium', 'high', 'critical']]),
                'prediction_date': datetime.now().isoformat()
            }
    
    @staticmethod
    def analyze_visit_patterns(restaurant_id: int, days: int = 30) -> Dict[str, Any]:
        """Analyze customer visit patterns"""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # Get visit data by hour and day
        visit_patterns = db.session.query(
            extract('dow', Order.created_at).label('day_of_week'),
            extract('hour', Order.created_at).label('hour_of_day'),
            func.count(Order.id).label('visit_count'),
            func.count(func.distinct(Order.customer_id)).label('unique_customers'),
            func.sum(Order.total).label('total_revenue')
        ).filter(
            Order.restaurant_id == restaurant_id,
            Order.created_at >= cutoff_date,
            Order.status.in_(['served', 'completed'])
        ).group_by(
            extract('dow', Order.created_at),
            extract('hour', Order.created_at)
        ).order_by('day_of_week', 'hour_of_day').all()
        
        # Process patterns
        day_names = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
        hourly_data = {}
        daily_data = {}
        
        for day, hour, visits, customers, revenue in visit_patterns:
            day_name = day_names[int(day)]
            
            # Hourly breakdown
            if day_name not in hourly_data:
                hourly_data[day_name] = {}
            hourly_data[day_name][f"{hour:02d}"] = {
                'visits': visits,
                'unique_customers': customers,
                'revenue': float(revenue or 0)
            }
            
            # Daily summary
            if day_name not in daily_data:
                daily_data[day_name] = {'total_visits': 0, 'total_revenue': 0}
            daily_data[day_name]['total_visits'] += visits
            daily_data[day_name]['total_revenue'] += float(revenue or 0)
        
        # Find peak hours and days
        peak_hours = CustomerAnalyticsService._find_peak_hours(hourly_data)
        peak_days = CustomerAnalyticsService._find_peak_days(daily_data)
        
        return {
            'period_days': days,
            'hourly_patterns': hourly_data,
            'daily_patterns': daily_data,
            'peak_hours': peak_hours,
            'peak_days': peak_days,
            'insights': CustomerAnalyticsService._generate_visit_insights(hourly_data, daily_data),
            'recommendations': CustomerAnalyticsService._generate_scheduling_recommendations(peak_hours, peak_days)
        }
    
    @staticmethod
    def analyze_spending_behavior(restaurant_id: int, days: int = 30) -> Dict[str, Any]:
        """Analyze customer spending behavior"""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # Get spending data
        spending_data = db.session.query(
            Customer.id,
            Customer.total_spent,
            Customer.average_order_value,
            Customer.total_orders,
            func.count(Order.id).label('recent_orders'),
            func.sum(Order.total).label('recent_spent')
        ).outerjoin(Order).filter(
            Customer.restaurant_id == restaurant_id,
            Order.created_at >= cutoff_date,
            Order.status.in_(['served', 'completed'])
        ).group_by(Customer.id).all()
        
        if not spending_data:
            return {
                'period_days': days,
                'total_customers': 0,
                'spending_segments': {},
                'insights': {},
                'recommendations': []
            }
        
        # Analyze spending patterns
        spending_segments = CustomerAnalyticsService._segment_by_spending(spending_data)
        
        # Calculate spending metrics
        total_customers = len(spending_data)
        avg_total_spent = sum(float(s.total_spent or 0) for s in spending_data) / total_customers
        avg_recent_spent = sum(float(s.recent_spent or 0) for s in spending_data) / total_customers
        avg_order_value = sum(float(s.average_order_value or 0) for s in spending_data) / total_customers
        
        return {
            'period_days': days,
            'total_customers': total_customers,
            'spending_segments': spending_segments,
            'metrics': {
                'average_total_spent': round(avg_total_spent, 2),
                'average_recent_spent': round(avg_recent_spent, 2),
                'average_order_value': round(avg_order_value, 2),
                'spending_distribution': CustomerAnalyticsService._calculate_spending_distribution(spending_data)
            },
            'insights': CustomerAnalyticsService._generate_spending_insights(spending_data),
            'recommendations': CustomerAnalyticsService._generate_spending_recommendations(spending_data)
        }
    
    @staticmethod
    def map_customer_journey(customer_id: int) -> Dict[str, Any]:
        """Map customer journey and touchpoints"""
        customer = Customer.query.get(customer_id)
        if not customer:
            return {}
        
        # Get customer behaviors for journey mapping
        behaviors = CustomerBehavior.query.filter_by(customer_id=customer_id).order_by(
            CustomerBehavior.created_at
        ).all()
        
        # Get customer orders
        orders = Order.query.filter_by(customer_id=customer_id).order_by(
            Order.created_at
        ).all()
        
        # Map journey stages
        journey_stages = CustomerAnalyticsService._map_journey_stages(behaviors, orders)
        
        # Calculate journey metrics
        journey_metrics = CustomerAnalyticsService._calculate_journey_metrics(journey_stages)
        
        return {
            'customer_id': customer_id,
            'customer_name': customer.get_full_name(),
            'journey_stages': journey_stages,
            'metrics': journey_metrics,
            'touchpoint_analysis': CustomerAnalyticsService._analyze_touchpoints(behaviors),
            'journey_visualization': CustomerAnalyticsService._generate_journey_visualization(journey_stages),
            'recommendations': CustomerAnalyticsService._generate_journey_recommendations(journey_stages)
        }
    
    # Helper methods
    @staticmethod
    def _calculate_order_frequency(customer: Customer) -> float:
        """Calculate customer order frequency (orders per month)"""
        if not customer.created_at or customer.total_orders == 0:
            return 0.0
        
        customer_age_months = (datetime.now() - customer.created_at).days / 30.44
        return customer.total_orders / max(1, customer_age_months)
    
    @staticmethod
    def _get_average_menu_price(restaurant_id: int) -> float:
        """Get average menu item price"""
        avg_price = db.session.query(
            func.avg(MenuItem.price)
        ).filter_by(
            restaurant_id=restaurant_id,
            is_available=True
        ).scalar()
        
        return float(avg_price or 0)
    
    @staticmethod
    def _describe_segment_characteristics(segment_name: str, customers: List[Customer]) -> Dict[str, Any]:
        """Describe characteristics of a customer segment"""
        if not customers:
            return {}
        
        total_customers = len(customers)
        avg_total_spent = sum(float(c.total_spent or 0) for c in customers) / total_customers
        avg_order_value = sum(float(c.average_order_value or 0) for c in customers) / total_customers
        avg_orders = sum(c.total_orders for c in customers) / total_customers
        
        return {
            'count': total_customers,
            'average_total_spent': round(avg_total_spent, 2),
            'average_order_value': round(avg_order_value, 2),
            'average_orders': round(avg_orders, 1),
            'loyalty_distribution': CustomerAnalyticsService._get_loyalty_distribution(customers)
        }
    
    @staticmethod
    def _describe_value_segment_characteristics(segment_name: str, customers: List[Customer]) -> Dict[str, Any]:
        """Describe characteristics of value-based segment"""
        base_chars = CustomerAnalyticsService._describe_segment_characteristics(segment_name, customers)
        
        # Add value-specific characteristics
        if customers:
            spending_values = [float(c.total_spent or 0) for c in customers]
            base_chars['spending_range'] = {
                'min': min(spending_values),
                'max': max(spending_values),
                'median': sorted(spending_values)[len(spending_values) // 2]
            }
        
        return base_chars
    
    @staticmethod
    def _describe_rfm_segment_characteristics(segment_name: str, customers: List[Customer]) -> Dict[str, Any]:
        """Describe characteristics of RFM segment"""
        base_chars = CustomerAnalyticsService._describe_segment_characteristics(segment_name, customers)
        
        # Add RFM-specific characteristics
        if customers:
            rfm_scores = [CustomerAnalyticsService._calculate_rfm_scores(c) for c in customers]
            recency_scores = [s['recency'] for s in rfm_scores]
            frequency_scores = [s['frequency'] for s in rfm_scores]
            monetary_scores = [s['monetary'] for s in rfm_scores]
            
            base_chars['rfm_averages'] = {
                'recency': sum(recency_scores) / len(recency_scores),
                'frequency': sum(frequency_scores) / len(frequency_scores),
                'monetary': sum(monetary_scores) / len(monetary_scores)
            }
        
        return base_chars
    
    @staticmethod
    def _describe_engagement_segment_characteristics(segment_name: str, customers: List[Customer]) -> Dict[str, Any]:
        """Describe characteristics of engagement segment"""
        base_chars = CustomerAnalyticsService._describe_segment_characteristics(segment_name, customers)
        
        # Add engagement-specific characteristics
        if customers:
            engagement_scores = [CustomerAnalyticsService._calculate_engagement_score(c) for c in customers]
            base_chars['engagement_averages'] = {
                'score': sum(engagement_scores) / len(engagement_scores),
                'min': min(engagement_scores),
                'max': max(engagement_scores)
            }
        
        return base_chars
    
    @staticmethod
    def _describe_predictive_segment_characteristics(segment_name: str, customers: List[Customer]) -> Dict[str, Any]:
        """Describe characteristics of predictive segment"""
        base_chars = CustomerAnalyticsService._describe_segment_characteristics(segment_name, customers)
        
        # Add predictive-specific characteristics
        if customers:
            churn_risks = [CustomerAnalyticsService._calculate_churn_risk(c) for c in customers]
            growth_potentials = [CustomerAnalyticsService._calculate_growth_potential(c) for c in customers]
            
            base_chars['predictive_averages'] = {
                'churn_risk': sum(churn_risks) / len(churn_risks),
                'growth_potential': sum(growth_potentials) / len(growth_potentials)
            }
        
        return base_chars
    
    @staticmethod
    def _calculate_rfm_scores(customer: Customer) -> Dict[str, int]:
        """Calculate RFM scores for customer"""
        # Recency (days since last order)
        if customer.last_order_date:
            days_since_last = (datetime.now() - customer.last_order_date).days
            recency_score = max(1, 5 - (days_since_last // 30))  # 5-point scale
        else:
            recency_score = 1
        
        # Frequency (orders in last 6 months)
        six_months_ago = datetime.now() - timedelta(days=180)
        recent_orders = Order.query.filter(
            Order.customer_id == customer.id,
            Order.created_at >= six_months_ago,
            Order.status.in_(['served', 'completed'])
        ).count()
        
        if recent_orders >= 20:
            frequency_score = 5
        elif recent_orders >= 10:
            frequency_score = 4
        elif recent_orders >= 5:
            frequency_score = 3
        elif recent_orders >= 2:
            frequency_score = 2
        elif recent_orders >= 1:
            frequency_score = 1
        else:
            frequency_score = 1
        
        # Monetary (total spending)
        total_spent = float(customer.total_spent or 0)
        if total_spent >= 1000:
            monetary_score = 5
        elif total_spent >= 500:
            monetary_score = 4
        elif total_spent >= 250:
            monetary_score = 3
        elif total_spent >= 100:
            monetary_score = 2
        elif total_spent >= 50:
            monetary_score = 1
        else:
            monetary_score = 1
        
        return {
            'recency': recency_score,
            'frequency': frequency_score,
            'monetary': monetary_score
        }
    
    @staticmethod
    def _calculate_engagement_score(customer: Customer) -> float:
        """Calculate customer engagement score"""
        score = 0.0
        
        # Order frequency component
        frequency = CustomerAnalyticsService._calculate_order_frequency(customer)
        score += min(3.0, frequency)  # Max 3 points for frequency
        
        # Recency component
        if customer.last_order_date:
            days_since_last = (datetime.now() - customer.last_order_date).days
            if days_since_last <= 7:
                score += 2.0
            elif days_since_last <= 30:
                score += 1.0
        
        # Loyalty component
        if customer.loyalty_member:
            score += 1.0
            if customer.loyalty_points > 0:
                score += min(1.0, customer.loyalty_points / 500)  # Max 1 point for loyalty
        
        # Feedback component
        # This would require feedback data
        # score += feedback_score
        
        return min(10.0, score)
    
    @staticmethod
    def _calculate_churn_risk(customer: Customer) -> float:
        """Calculate churn risk score (0-1, higher = higher risk)"""
        risk = 0.0
        
        # Recency risk
        if customer.last_order_date:
            days_since_last = (datetime.now() - customer.last_order_date).days
            if days_since_last > 90:
                risk += 0.4
            elif days_since_last > 60:
                risk += 0.3
            elif days_since_last > 30:
                risk += 0.2
            elif days_since_last > 14:
                risk += 0.1
        
        # Frequency risk
        frequency = CustomerAnalyticsService._calculate_order_frequency(customer)
        if frequency < 0.5:  # Less than 1 order per 2 months
            risk += 0.3
        elif frequency < 1:  # Less than 1 order per month
            risk += 0.2
        
        # Loyalty risk
        if not customer.loyalty_member:
            risk += 0.2
        
        # Spending trend risk
        # This would require analyzing spending trend over time
        # For now, use simple heuristic
        avg_order_value = float(customer.average_order_value or 0)
        if avg_order_value < 20:  # Low average order value
            risk += 0.1
        
        return min(1.0, risk)
    
    @staticmethod
    def _calculate_growth_potential(customer: Customer) -> float:
        """Calculate customer growth potential score (0-1, higher = higher potential)"""
        potential = 0.0
        
        # Spending growth component
        total_spent = float(customer.total_spent or 0)
        if total_spent >= 500:
            potential += 0.3
        elif total_spent >= 200:
            potential += 0.2
        elif total_spent >= 100:
            potential += 0.1
        
        # Frequency component
        frequency = CustomerAnalyticsService._calculate_order_frequency(customer)
        if frequency >= 4:  # More than 1 order per week
            potential += 0.3
        elif frequency >= 2:  # More than 1 order per 2 weeks
            potential += 0.2
        elif frequency >= 1:  # More than 1 order per month
            potential += 0.1
        
        # Loyalty component
        if customer.loyalty_member and customer.loyalty_points > 200:
            potential += 0.2
        elif customer.loyalty_member:
            potential += 0.1
        
        # Recent activity component
        if customer.last_order_date:
            days_since_last = (datetime.now() - customer.last_order_date).days
            if days_since_last <= 14:
                potential += 0.2
        
        return min(1.0, potential)
    
    @staticmethod
    def _get_risk_level(risk_score: float) -> str:
        """Get risk level from risk score"""
        if risk_score >= 0.8:
            return 'critical'
        elif risk_score >= 0.6:
            return 'high'
        elif risk_score >= 0.4:
            return 'medium'
        else:
            return 'low'
    
    @staticmethod
    def _get_loyalty_multiplier(customer: Customer) -> float:
        """Get loyalty tier multiplier for CLV calculation"""
        if not customer.loyalty_tier:
            return 1.0
        
        tier_multipliers = {
            'bronze': 1.0,
            'silver': 1.2,
            'gold': 1.5,
            'platinum': 2.0
        }
        
        return tier_multipliers.get(customer.loyalty_tier, 1.0)
    
    @staticmethod
    def _calculate_customer_lifetime(customer: Customer) -> float:
        """Calculate customer lifetime in months"""
        if not customer.created_at:
            return 1.0  # Default to 1 month
        
        return (datetime.now() - customer.created_at).days / 30.44
    
    @staticmethod
    def _predict_customer_lifetime_months(customer: Customer) -> float:
        """Predict remaining customer lifetime in months"""
        current_lifetime = CustomerAnalyticsService._calculate_customer_lifetime(customer)
        churn_risk = CustomerAnalyticsService._calculate_churn_risk(customer)
        
        # Adjust prediction based on churn risk
        if churn_risk >= 0.8:
            return max(3.0, 12 - current_lifetime)  # Predict 3 more months
        elif churn_risk >= 0.6:
            return max(6.0, 24 - current_lifetime)  # Predict 6 more months
        elif churn_risk >= 0.4:
            return max(12.0, 36 - current_lifetime)  # Predict 12 more months
        else:
            return max(24.0, 48 - current_lifetime)  # Predict 24 more months
    
    @staticmethod
    def _predict_future_frequency(customer: Customer) -> float:
        """Predict future order frequency"""
        current_frequency = CustomerAnalyticsService._calculate_order_frequency(customer)
        churn_risk = CustomerAnalyticsService._calculate_churn_risk(customer)
        
        # Adjust frequency based on churn risk
        frequency_adjustment = 1 - (churn_risk * 0.5)
        return max(0.1, current_frequency * frequency_adjustment)
    
    @staticmethod
    def _predict_future_order_value(customer: Customer) -> float:
        """Predict future average order value"""
        current_avg = float(customer.average_order_value or 0)
        growth_potential = CustomerAnalyticsService._calculate_growth_potential(customer)
        
        # Increase order value based on growth potential
        value_increase = 1 + (growth_potential * 0.3)
        return current_avg * value_increase
    
    @staticmethod
    def _get_clv_tier(clv: float) -> str:
        """Get CLV tier from value"""
        if clv >= 2000:
            return 'platinum'
        elif clv >= 1000:
            return 'gold'
        elif clv >= 500:
            return 'silver'
        elif clv >= 100:
            return 'bronze'
        else:
            return 'basic'
    
    @staticmethod
    def _calculate_clv_confidence(customer: Customer) -> float:
        """Calculate confidence level for CLV prediction"""
        data_points = 0
        
        # More data points = higher confidence
        if customer.total_orders > 0:
            data_points += min(3.0, customer.total_orders / 10)
        
        if customer.total_spent > 0:
            data_points += min(3.0, float(customer.total_spent) / 500)
        
        if customer.created_at:
            customer_age_months = CustomerAnalyticsService._calculate_customer_lifetime(customer)
            data_points += min(2.0, customer_age_months / 12)
        
        return min(1.0, data_points / 8.0)
    
    @staticmethod
    def _get_loyalty_distribution(customers: List[Customer]) -> Dict[str, int]:
        """Get loyalty tier distribution"""
        distribution = {'non_member': 0, 'bronze': 0, 'silver': 0, 'gold': 0, 'platinum': 0}
        
        for customer in customers:
            if not customer.loyalty_member:
                distribution['non_member'] += 1
            else:
                tier = customer.loyalty_tier or 'bronze'
                if tier in distribution:
                    distribution[tier] += 1
        
        return distribution
    
    @staticmethod
    def _generate_segment_recommendations(segments: List[Dict]) -> List[str]:
        """Generate recommendations based on segmentation analysis"""
        recommendations = []
        
        for segment in segments:
            segment_name = segment['name'].lower()
            count = segment['count']
            
            if 'high value' in segment_name or 'vip' in segment_name:
                recommendations.append(f"Implement VIP program for {count} high-value customers")
            elif 'at risk' in segment_name or 'churn' in segment_name:
                recommendations.append(f"Launch retention campaign for {count} at-risk customers")
            elif 'new' in segment_name:
                recommendations.append(f"Focus on onboarding for {count} new customers")
            elif 'loyal' in segment_name:
                recommendations.append(f"Create loyalty rewards for {count} loyal customers")
        
        return recommendations
    
    @staticmethod
    def _generate_clv_recommendations(customer: Customer, clv: float) -> List[str]:
        """Generate recommendations based on CLV analysis"""
        recommendations = []
        
        clv_tier = CustomerAnalyticsService._get_clv_tier(clv)
        
        if clv_tier in ['platinum', 'gold']:
            recommendations.append("Offer premium experiences and exclusive access")
        elif clv_tier == 'silver':
            recommendations.append("Provide enhanced loyalty benefits and personalized offers")
        elif clv_tier == 'bronze':
            recommendations.append("Focus on increasing order frequency and value")
        else:
            recommendations.append("Implement welcome program and first-order incentives")
        
        # Growth potential recommendations
        growth_potential = CustomerAnalyticsService._calculate_growth_potential(customer)
        if growth_potential >= 0.7:
            recommendations.append("Target for upselling and cross-selling opportunities")
        
        return recommendations
    
    @staticmethod
    def _generate_retention_recommendations(customer: Customer, churn_risk: float) -> List[str]:
        """Generate retention recommendations based on churn risk"""
        recommendations = []
        
        risk_level = CustomerAnalyticsService._get_risk_level(churn_risk)
        
        if risk_level == 'critical':
            recommendations.extend([
                "Immediate personal outreach required",
                "Offer significant retention incentive",
                "Schedule follow-up within 48 hours"
            ])
        elif risk_level == 'high':
            recommendations.extend([
                "Personalized retention campaign",
                "Special discount offer",
                "Feedback collection to understand issues"
            ])
        elif risk_level == 'medium':
            recommendations.extend([
                "Re-engagement email campaign",
                "Loyalty points bonus",
                "Personalized recommendations"
            ])
        else:
            recommendations.extend([
                "Regular engagement communications",
                "Loyalty program promotion",
                "New product announcements"
            ])
        
        return recommendations
    
    @staticmethod
    def _find_peak_hours(hourly_data: Dict) -> List[Dict]:
        """Find peak business hours"""
        hour_totals = {}
        
        for day_name, day_data in hourly_data.items():
            for hour, hour_data in day_data.items():
                hour_int = int(hour)
                if hour_int not in hour_totals:
                    hour_totals[hour_int] = 0
                hour_totals[hour_int] += hour_data['visits']
        
        # Sort by total visits and get top hours
        sorted_hours = sorted(hour_totals.items(), key=lambda x: x[1], reverse=True)
        
        return [
            {'hour': hour, 'visits': visits, 'revenue': sum(
                hourly_data[day_name][hour]['revenue']
                for day_name, day_data in hourly_data.items()
                if hour in day_data
            )}
            for hour, visits in sorted_hours[:5]
        ]
    
    @staticmethod
    def _find_peak_days(daily_data: Dict) -> List[Dict]:
        """Find peak business days"""
        sorted_days = sorted(
            daily_data.items(),
            key=lambda x: x[1]['total_visits'],
            reverse=True
        )
        
        return [
            {
                'day': day_name,
                'visits': day_data['total_visits'],
                'revenue': day_data['total_revenue']
            }
            for day_name, day_data in sorted_days[:3]
        ]
    
    @staticmethod
    def _generate_visit_insights(hourly_data: Dict, daily_data: Dict) -> List[str]:
        """Generate insights from visit pattern analysis"""
        insights = []
        
        # Calculate busiest times
        total_hourly_visits = sum(
            sum(hour_data['visits'] for hour_data in day_data.values())
            for day_data in hourly_data.values()
        )
        
        if total_hourly_visits > 0:
            peak_hour_visits = max(
                max(hour_data.values(), key=lambda x: x['visits'])['visits']
                for hour_data in hourly_data.values()
                if hour_data
            )
            peak_percentage = (peak_hour_visits / total_hourly_visits) * 100
            
            if peak_percentage >= 15:
                insights.append(f"Peak hours account for {peak_percentage:.1f}% of total visits")
        
        # Day of week patterns
        total_daily_visits = sum(day_data['total_visits'] for day_data in daily_data.values())
        if total_daily_visits > 0:
            busiest_day = max(daily_data.items(), key=lambda x: x[1]['total_visits'])
            slowest_day = min(daily_data.items(), key=lambda x: x[1]['total_visits'])
            
            insights.append(f"{busiest_day[0]} is busiest day with {busiest_day[1]['total_visits']} visits")
            insights.append(f"{slowest_day[0]} is slowest day with {slowest_day[1]['total_visits']} visits")
        
        return insights
    
    @staticmethod
    def _generate_scheduling_recommendations(peak_hours: List[Dict], peak_days: List[Dict]) -> List[str]:
        """Generate staffing and inventory recommendations"""
        recommendations = []
        
        if peak_hours:
            peak_hour_range = f"{peak_hours[0]['hour']}:00 - {peak_hours[-1]['hour']}:00"
            recommendations.append(f"Ensure adequate staffing during peak hours ({peak_hour_range})")
        
        if peak_days:
            peak_day_names = [day['day'] for day in peak_days]
            recommendations.append(f"Schedule promotions for {', '.join(peak_day_names)}")
        
        return recommendations
    
    @staticmethod
    def _segment_by_spending(spending_data: List) -> Dict[str, List[Customer]]:
        """Segment customers by spending patterns"""
        segments = {
            'high_spenders': [],
            'medium_spenders': [],
            'low_spenders': [],
            'occasional_spenders': []
        }
        
        for data in spending_data:
            recent_orders = data.recent_orders or 0
            recent_spent = float(data.recent_spent or 0)
            avg_order = float(data.average_order_value or 0)
            
            if recent_orders >= 4 and avg_order >= 50:
                segments['high_spenders'].append(data)
            elif recent_orders >= 2 and avg_order >= 30:
                segments['medium_spenders'].append(data)
            elif recent_orders >= 1 and avg_order >= 20:
                segments['low_spenders'].append(data)
            else:
                segments['occasional_spenders'].append(data)
        
        return segments
    
    @staticmethod
    def _calculate_spending_distribution(spending_data: List) -> Dict[str, Any]:
        """Calculate spending distribution metrics"""
        if not spending_data:
            return {}
        
        spending_values = [float(s.recent_spent or 0) for s in spending_data]
        
        return {
            'min': min(spending_values),
            'max': max(spending_values),
            'median': sorted(spending_values)[len(spending_values) // 2],
            'mean': sum(spending_values) / len(spending_values),
            'percentiles': {
                '25th': sorted(spending_values)[len(spending_values) // 4],
                '50th': sorted(spending_values)[len(spending_values) // 2],
                '75th': sorted(spending_values)[len(spending_values) * 3 // 4],
                '90th': sorted(spending_values)[len(spending_values) * 9 // 10]
            }
        }
    
    @staticmethod
    def _generate_spending_insights(spending_data: List) -> List[str]:
        """Generate insights from spending behavior analysis"""
        insights = []
        
        if not spending_data:
            return insights
        
        total_customers = len(spending_data)
        high_spenders = len([s for s in spending_data if s.recent_orders >= 4 and float(s.average_order_value or 0) >= 50])
        
        if high_spenders > 0:
            high_spender_percentage = (high_spenders / total_customers) * 100
            insights.append(f"{high_spender_percentage:.1f}% of customers are high spenders")
        
        # Calculate spending concentration
        total_spent = sum(float(s.recent_spent or 0) for s in spending_data)
        if total_spent > 0:
            top_20_percent_spent = sum(sorted([float(s.recent_spent or 0) for s in spending_data], reverse=True)[:int(total_customers * 0.2)])
            concentration = (top_20_percent_spent / total_spent) * 100
            
            if concentration >= 60:
                insights.append(f"Top 20% of customers account for {concentration:.1f}% of revenue")
        
        return insights
    
    @staticmethod
    def _generate_spending_recommendations(spending_data: List) -> List[str]:
        """Generate recommendations based on spending behavior"""
        recommendations = []
        
        # Target low spenders
        low_spenders = [s for s in spending_data if s.recent_orders <= 1 or float(s.average_order_value or 0) < 20]
        if low_spenders:
            recommendations.append(f"Target {len(low_spenders)} low spenders with upselling campaigns")
        
        # Reward high spenders
        high_spenders = [s for s in spending_data if s.recent_orders >= 4 and float(s.average_order_value or 0) >= 50]
        if high_spenders:
            recommendations.append(f"Create VIP program for {len(high_spenders)} high spenders")
        
        # Encourage occasional spenders
        occasional_spenders = [s for s in spending_data if 1 <= s.recent_orders <= 3]
        if occasional_spenders:
            recommendations.append(f"Launch frequency-building campaign for {len(occasional_spenders)} occasional spenders")
        
        return recommendations
    
    @staticmethod
    def _map_journey_stages(behaviors: List[CustomerBehavior], orders: List[Order]) -> List[Dict]:
        """Map customer journey stages"""
        stages = []
        
        # Awareness stage
        awareness_behaviors = [b for b in behaviors if b.behavior_type in ['page_view', 'search']]
        if awareness_behaviors:
            stages.append({
                'stage': 'awareness',
                'touchpoints': awareness_behaviors,
                'duration_days': CustomerAnalyticsService._calculate_stage_duration(awareness_behaviors)
            })
        
        # Consideration stage
        consideration_behaviors = [b for b in behaviors if b.behavior_type in ['item_view', 'add_to_cart']]
        if consideration_behaviors:
            stages.append({
                'stage': 'consideration',
                'touchpoints': consideration_behaviors,
                'duration_days': CustomerAnalyticsService._calculate_stage_duration(consideration_behaviors)
            })
        
        # Conversion stage
        if orders:
            stages.append({
                'stage': 'conversion',
                'touchpoints': orders,
                'duration_days': CustomerAnalyticsService._calculate_conversion_duration(orders)
            })
        
        # Retention stage
        retention_behaviors = [b for b in behaviors if b.behavior_type in ['purchase', 'review']]
        if retention_behaviors:
            stages.append({
                'stage': 'retention',
                'touchpoints': retention_behaviors,
                'duration_days': CustomerAnalyticsService._calculate_stage_duration(retention_behaviors)
            })
        
        # Advocacy stage
        advocacy_behaviors = [b for b in behaviors if b.behavior_type in ['share', 'referral']]
        if advocacy_behaviors:
            stages.append({
                'stage': 'advocacy',
                'touchpoints': advocacy_behaviors,
                'duration_days': CustomerAnalyticsService._calculate_stage_duration(advocacy_behaviors)
            })
        
        return stages
    
    @staticmethod
    def _calculate_stage_duration(behaviors: List[CustomerBehavior]) -> float:
        """Calculate duration of a journey stage in days"""
        if not behaviors:
            return 0.0
        
        dates = [b.created_at for b in behaviors]
        if len(dates) < 2:
            return 0.0
        
        return (max(dates) - min(dates)).days + 1  # +1 to include both start and end day
    
    @staticmethod
    def _calculate_conversion_duration(orders: List[Order]) -> float:
        """Calculate conversion duration in days"""
        if not orders:
            return 0.0
        
        dates = [o.created_at for o in orders]
        if len(dates) < 2:
            return 1.0
        
        return (max(dates) - min(dates)).days + 1
    
    @staticmethod
    def _calculate_journey_metrics(stages: List[Dict]) -> Dict[str, Any]:
        """Calculate journey metrics"""
        total_stages = len(stages)
        total_duration = sum(stage['duration_days'] for stage in stages)
        
        # Calculate conversion rates between stages
        conversion_rates = {}
        for i in range(total_stages - 1):
            from_stage = stages[i]['stage']
            to_stage = stages[i + 1]['stage']
            
            # Simplified conversion calculation
            conversion_rates[f"{from_stage}_to_{to_stage}"] = 0.5  # Placeholder
        
        return {
            'total_stages': total_stages,
            'total_duration_days': total_duration,
            'average_stage_duration': total_duration / total_stages if total_stages > 0 else 0,
            'conversion_rates': conversion_rates
        }
    
    @staticmethod
    def _analyze_touchpoints(behaviors: List[CustomerBehavior]) -> Dict[str, Any]:
        """Analyze customer touchpoints"""
        touchpoint_counts = {}
        device_types = {}
        
        for behavior in behaviors:
            behavior_type = behavior.behavior_type
            if behavior_type not in touchpoint_counts:
                touchpoint_counts[behavior_type] = 0
            touchpoint_counts[behavior_type] += 1
            
            if behavior.device_type:
                if behavior.device_type not in device_types:
                    device_types[behavior.device_type] = 0
                device_types[behavior.device_type] += 1
        
        return {
            'touchpoint_counts': touchpoint_counts,
            'device_distribution': device_types,
            'most_common_touchpoint': max(touchpoint_counts.items(), key=lambda x: x[1])[0] if touchpoint_counts else None
        }
    
    @staticmethod
    def _generate_journey_visualization(stages: List[Dict]) -> Dict[str, Any]:
        """Generate journey visualization data"""
        return {
            'stages': [
                {
                    'name': stage['stage'],
                    'duration_days': stage['duration_days'],
                    'touchpoint_count': len(stage['touchpoints'])
                }
                for stage in stages
            ],
            'flow_chart': CustomerAnalyticsService._generate_flow_chart_data(stages)
        }
    
    @staticmethod
    def _generate_flow_chart_data(stages: List[Dict]) -> List[Dict]:
        """Generate flow chart data for journey visualization"""
        flow_data = []
        
        for i, stage in enumerate(stages):
            flow_data.append({
                'id': i,
                'name': stage['stage'],
                'position': {'x': i * 200, 'y': 100},
                'connections': [i + 1] if i < len(stages) - 1 else []
            })
        
        return flow_data
    
    @staticmethod
    def _generate_journey_recommendations(stages: List[Dict]) -> List[str]:
        """Generate journey optimization recommendations"""
        recommendations = []
        
        # Analyze stage durations
        long_stages = [s for s in stages if s['duration_days'] > 7]
        if long_stages:
            recommendations.append(f"Optimize {len(long_stages)} stages with long durations")
        
        # Analyze touchpoint efficiency
        for stage in stages:
            if stage['stage'] == 'consideration' and stage['duration_days'] > 3:
                recommendations.append("Streamline consideration stage to reduce drop-offs")
        
        return recommendations
    
    @staticmethod
    def _analyze_segments(segments: List[Dict], customers: List[Customer]) -> Dict[str, Any]:
        """Analyze segments and provide insights"""
        total_customers = len(customers)
        analysis = {
            'largest_segment': None,
            'smallest_segment': None,
            'segment_balance': {},
            'overlap_analysis': {}
        }
        
        if not segments:
            return analysis
        
        # Find largest and smallest segments
        segment_sizes = [(s['name'], s['count']) for s in segments]
        largest_segment = max(segment_sizes, key=lambda x: x[1])
        smallest_segment = min(segment_sizes, key=lambda x: x[1])
        
        analysis['largest_segment'] = {
            'name': largest_segment[0],
            'count': largest_segment[1],
            'percentage': (largest_segment[1] / total_customers) * 100 if total_customers > 0 else 0
        }
        
        analysis['smallest_segment'] = {
            'name': smallest_segment[0],
            'count': smallest_segment[1],
            'percentage': (smallest_segment[1] / total_customers) * 100 if total_customers > 0 else 0
        }
        
        # Analyze segment balance
        ideal_size = total_customers / len(segments) if segments else 1
        analysis['segment_balance'] = {
            'ideal_size': ideal_size,
            'variance': [(s['name'], abs(s['count'] - ideal_size)) for s in segments]
        }
        
        return analysis
    
    @staticmethod
    def _analyze_churn_factors(customer: Customer) -> Dict[str, Any]:
        """Analyze factors contributing to customer churn risk"""
        factors = {
            'recency_risk': 0.0,
            'frequency_risk': 0.0,
            'loyalty_risk': 0.0,
            'spending_risk': 0.0,
            'engagement_risk': 0.0
        }
        
        # Recency risk
        if customer.last_order_date:
            days_since_last = (datetime.now() - customer.last_order_date).days
            if days_since_last > 90:
                factors['recency_risk'] = 0.8
            elif days_since_last > 60:
                factors['recency_risk'] = 0.6
            elif days_since_last > 30:
                factors['recency_risk'] = 0.4
            elif days_since_last > 14:
                factors['recency_risk'] = 0.2
        else:
            factors['recency_risk'] = 1.0
        
        # Frequency risk
        frequency = CustomerAnalyticsService._calculate_order_frequency(customer)
        if frequency < 0.5:
            factors['frequency_risk'] = 0.8
        elif frequency < 1:
            factors['frequency_risk'] = 0.6
        elif frequency < 2:
            factors['frequency_risk'] = 0.4
        elif frequency < 4:
            factors['frequency_risk'] = 0.2
        
        # Loyalty risk
        if not customer.loyalty_member:
            factors['loyalty_risk'] = 0.6
        elif not customer.loyalty_tier or customer.loyalty_tier == 'bronze':
            factors['loyalty_risk'] = 0.3
        else:
            factors['loyalty_risk'] = 0.1
        
        # Spending risk
        avg_order_value = float(customer.average_order_value or 0)
        if avg_order_value < 15:
            factors['spending_risk'] = 0.6
        elif avg_order_value < 25:
            factors['spending_risk'] = 0.3
        else:
            factors['spending_risk'] = 0.1
        
        # Engagement risk
        engagement_score = CustomerAnalyticsService._calculate_engagement_score(customer)
        if engagement_score < 3:
            factors['engagement_risk'] = 0.8
        elif engagement_score < 5:
            factors['engagement_risk'] = 0.6
        elif engagement_score < 7:
            factors['engagement_risk'] = 0.4
        else:
            factors['engagement_risk'] = 0.2
        
        # Find highest risk factors
        sorted_factors = sorted(factors.items(), key=lambda x: x[1], reverse=True)
        
        return {
            'individual_factors': factors,
            'highest_risk_factor': sorted_factors[0][0] if sorted_factors else None,
            'risk_breakdown': {
                'high_risk': [factor for factor, score in factors.items() if score >= 0.6],
                'medium_risk': [factor for factor, score in factors.items() if 0.3 <= score < 0.6],
                'low_risk': [factor for factor, score in factors.items() if score < 0.3]
            }
        }