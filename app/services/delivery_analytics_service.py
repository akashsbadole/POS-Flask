"""
Delivery Analytics Service for Advanced Delivery Management
Handles delivery performance metrics, driver analytics, and business intelligence
"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from flask import current_app
from sqlalchemy import func, text, and_, or_

from app import db
from app.models.delivery import (
    Driver, Delivery, DeliveryRoute, DriverLocation, DeliveryTracking,
    DriverRating, DriverPerformance, DriverEarning, DeliveryFeedback, DeliveryZone,
    DeliveryStatus, DriverStatus
)
from app.models.order import Order

class DeliveryAnalyticsService:
    """Service for comprehensive delivery analytics and reporting"""
    
    def get_dashboard_metrics(self, date_range: str = 'today') -> Dict:
        """
        Get comprehensive dashboard metrics for delivery operations
        
        Args:
            date_range: 'today', 'week', 'month', 'year'
        
        Returns:
            Dictionary with all dashboard metrics
        """
        try:
            start_date, end_date = self._get_date_range(date_range)
            
            # Get basic counts
            total_deliveries = Delivery.query.filter(
                Delivery.created_at >= start_date,
                Delivery.created_at < end_date
            ).count()
            
            successful_deliveries = Delivery.query.filter(
                Delivery.created_at >= start_date,
                Delivery.created_at < end_date,
                Delivery.status == DeliveryStatus.DELIVERED.value
            ).count()
            
            failed_deliveries = Delivery.query.filter(
                Delivery.created_at >= start_date,
                Delivery.created_at < end_date,
                Delivery.status == DeliveryStatus.FAILED.value
            ).count()
            
            cancelled_deliveries = Delivery.query.filter(
                Delivery.created_at >= start_date,
                Delivery.created_at < end_date,
                Delivery.status == DeliveryStatus.CANCELLED.value
            ).count()
            
            # Get active drivers
            active_drivers = Driver.query.filter_by(status=DriverStatus.AVAILABLE.value).count()
            total_drivers = Driver.query.filter_by(is_active=True).count()
            
            # Get revenue metrics
            delivery_orders = db.session.query(Order).join(Delivery).filter(
                Delivery.created_at >= start_date,
                Delivery.created_at < end_date,
                Delivery.status == DeliveryStatus.DELIVERED.value
            ).all()
            
            total_revenue = sum(float(order.total) for order in delivery_orders)
            delivery_fees = sum(float(order.delivery_fee or 0) for order in delivery_orders)
            
            # Get performance metrics
            avg_delivery_time = self._get_average_delivery_time(start_date, end_date)
            on_time_percentage = self._get_on_time_percentage(start_date, end_date)
            
            # Get driver performance
            top_performers = self._get_top_performing_drivers(start_date, end_date, limit=5)
            
            # Get zone performance
            zone_performance = self._get_delivery_zone_performance(start_date, end_date)
            
            return {
                'date_range': date_range,
                'period_start': start_date.isoformat(),
                'period_end': end_date.isoformat(),
                
                # Delivery metrics
                'total_deliveries': total_deliveries,
                'successful_deliveries': successful_deliveries,
                'failed_deliveries': failed_deliveries,
                'cancelled_deliveries': cancelled_deliveries,
                'success_rate': (successful_deliveries / max(total_deliveries, 1)) * 100,
                'failure_rate': (failed_deliveries / max(total_deliveries, 1)) * 100,
                
                # Driver metrics
                'active_drivers': active_drivers,
                'total_drivers': total_drivers,
                'driver_utilization': (active_drivers / max(total_drivers, 1)) * 100,
                
                # Revenue metrics
                'total_revenue': total_revenue,
                'delivery_fees': delivery_fees,
                'average_order_value': total_revenue / max(successful_deliveries, 1),
                
                # Performance metrics
                'average_delivery_time_minutes': avg_delivery_time,
                'on_time_delivery_percentage': on_time_percentage,
                
                # Top performers
                'top_performers': top_performers,
                
                # Zone performance
                'zone_performance': zone_performance
            }
            
        except Exception as e:
            current_app.logger.error(f"Error getting dashboard metrics: {str(e)}")
            return {}
    
    def get_driver_analytics(self, driver_id: int, date_range: str = 'month') -> Dict:
        """
        Get comprehensive analytics for a specific driver
        
        Args:
            driver_id: Driver ID
            date_range: 'week', 'month', 'quarter', 'year'
        
        Returns:
            Driver analytics dictionary
        """
        try:
            start_date, end_date = self._get_date_range(date_range)
            driver = Driver.query.get(driver_id)
            
            if not driver:
                return {'error': 'Driver not found'}
            
            # Get delivery metrics
            deliveries = Delivery.query.filter(
                Delivery.driver_id == driver_id,
                Delivery.created_at >= start_date,
                Delivery.created_at < end_date
            ).all()
            
            total_deliveries = len(deliveries)
            successful_deliveries = len([d for d in deliveries if d.status == DeliveryStatus.DELIVERED.value])
            failed_deliveries = len([d for d in deliveries if d.status == DeliveryStatus.FAILED.value])
            
            # Get earnings
            earnings = DriverEarning.query.filter(
                DriverEarning.driver_id == driver_id,
                DriverEarning.created_at >= start_date,
                DriverEarning.created_at < end_date
            ).all()
            
            total_earnings = sum(float(e.amount) for e in earnings)
            base_earnings = sum(float(e.amount) for e in earnings if e.earning_type == 'base')
            commission_earnings = sum(float(e.amount) for e in earnings if e.earning_type == 'commission')
            tip_earnings = sum(float(e.amount) for e in earnings if e.earning_type == 'tip')
            
            # Get ratings
            ratings = DriverRating.query.filter(
                DriverRating.driver_id == driver_id,
                DriverRating.created_at >= start_date,
                DriverRating.created_at < end_date
            ).all()
            
            avg_rating = sum(r.rating for r in ratings) / max(len(ratings), 1)
            
            # Get performance metrics
            avg_delivery_time = self._get_driver_average_delivery_time(driver_id, start_date, end_date)
            total_distance = sum(float(d.actual_distance or 0) for d in deliveries)
            
            # Get location analytics
            location_analytics = self._get_driver_location_analytics(driver_id, start_date, end_date)
            
            # Get daily breakdown
            daily_breakdown = self._get_driver_daily_breakdown(driver_id, start_date, end_date)
            
            return {
                'driver_id': driver_id,
                'driver_name': driver.user.name if driver.user else 'Unknown',
                'date_range': date_range,
                'period_start': start_date.isoformat(),
                'period_end': end_date.isoformat(),
                
                # Delivery metrics
                'total_deliveries': total_deliveries,
                'successful_deliveries': successful_deliveries,
                'failed_deliveries': failed_deliveries,
                'success_rate': (successful_deliveries / max(total_deliveries, 1)) * 100,
                
                # Earnings
                'total_earnings': total_earnings,
                'base_earnings': base_earnings,
                'commission_earnings': commission_earnings,
                'tip_earnings': tip_earnings,
                'average_earnings_per_delivery': total_earnings / max(successful_deliveries, 1),
                
                # Performance
                'average_rating': avg_rating,
                'average_delivery_time_minutes': avg_delivery_time,
                'total_distance_km': total_distance,
                'average_distance_per_delivery': total_distance / max(total_deliveries, 1),
                
                # Location analytics
                'location_analytics': location_analytics,
                
                # Daily breakdown
                'daily_breakdown': daily_breakdown
            }
            
        except Exception as e:
            current_app.logger.error(f"Error getting driver analytics: {str(e)}")
            return {'error': str(e)}
    
    def get_delivery_trends(self, date_range: str = 'month') -> Dict:
        """
        Get delivery trends and patterns
        
        Args:
            date_range: 'week', 'month', 'quarter', 'year'
        
        Returns:
            Trends analytics dictionary
        """
        try:
            start_date, end_date = self._get_date_range(date_range)
            
            # Get hourly delivery patterns
            hourly_pattern = self._get_hourly_delivery_pattern(start_date, end_date)
            
            # Get daily delivery patterns
            daily_pattern = self._get_daily_delivery_pattern(start_date, end_date)
            
            # Get weekly delivery patterns
            weekly_pattern = self._get_weekly_delivery_pattern(start_date, end_date)
            
            # Get delivery time trends
            delivery_time_trends = self._get_delivery_time_trends(start_date, end_date)
            
            # Get zone trends
            zone_trends = self._get_zone_delivery_trends(start_date, end_date)
            
            return {
                'date_range': date_range,
                'period_start': start_date.isoformat(),
                'period_end': end_date.isoformat(),
                
                # Patterns
                'hourly_pattern': hourly_pattern,
                'daily_pattern': daily_pattern,
                'weekly_pattern': weekly_pattern,
                
                # Trends
                'delivery_time_trends': delivery_time_trends,
                'zone_trends': zone_trends
            }
            
        except Exception as e:
            current_app.logger.error(f"Error getting delivery trends: {str(e)}")
            return {'error': str(e)}
    
    def get_customer_satisfaction_analytics(self, date_range: str = 'month') -> Dict:
        """
        Get customer satisfaction analytics for deliveries
        
        Args:
            date_range: 'week', 'month', 'quarter', 'year'
        
        Returns:
            Customer satisfaction analytics
        """
        try:
            start_date, end_date = self._get_date_range(date_range)
            
            # Get feedback metrics
            feedback = DeliveryFeedback.query.filter(
                DeliveryFeedback.created_at >= start_date,
                DeliveryFeedback.created_at < end_date
            ).all()
            
            total_feedback = len(feedback)
            
            if total_feedback == 0:
                return {
                    'date_range': date_range,
                    'total_feedback': 0,
                    'average_ratings': {},
                    'rating_distribution': {},
                    'common_issues': [],
                    'satisfaction_trends': []
                }
            
            # Calculate average ratings
            avg_overall = sum(f.overall_rating for f in feedback) / total_feedback
            avg_delivery_speed = sum(f.delivery_speed_rating or 0 for f in feedback) / max(len([f for f in feedback if f.delivery_speed_rating]), 1)
            avg_food_quality = sum(f.food_quality_rating or 0 for f in feedback) / max(len([f for f in feedback if f.food_quality_rating]), 1)
            avg_driver_professionalism = sum(f.driver_professionalism_rating or 0 for f in feedback) / max(len([f for f in feedback if f.driver_professionalism_rating]), 1)
            avg_packaging_quality = sum(f.packaging_quality_rating or 0 for f in feedback) / max(len([f for f in feedback if f.packaging_quality_rating]), 1)
            
            # Rating distribution
            rating_distribution = {}
            for rating in range(1, 6):
                count = len([f for f in feedback if f.overall_rating == rating])
                rating_distribution[str(rating)] = {
                    'count': count,
                    'percentage': (count / total_feedback) * 100
                }
            
            # Common issues
            all_issues = []
            for f in feedback:
                if f.issues:
                    all_issues.extend(f.issues)
            
            from collections import Counter
            issue_counter = Counter(all_issues)
            common_issues = [{'issue': issue, 'count': count} for issue, count in issue_counter.most_common(10)]
            
            # Would order again percentage
            would_order_again = len([f for f in feedback if f.would_order_again is True])
            would_order_again_percentage = (would_order_again / total_feedback) * 100
            
            return {
                'date_range': date_range,
                'period_start': start_date.isoformat(),
                'period_end': end_date.isoformat(),
                
                # Basic metrics
                'total_feedback': total_feedback,
                'would_order_again_percentage': would_order_again_percentage,
                
                # Average ratings
                'average_ratings': {
                    'overall': avg_overall,
                    'delivery_speed': avg_delivery_speed,
                    'food_quality': avg_food_quality,
                    'driver_professionalism': avg_driver_professionalism,
                    'packaging_quality': avg_packaging_quality
                },
                
                # Rating distribution
                'rating_distribution': rating_distribution,
                
                # Common issues
                'common_issues': common_issues
            }
            
        except Exception as e:
            current_app.logger.error(f"Error getting customer satisfaction analytics: {str(e)}")
            return {'error': str(e)}
    
    def get_cost_analysis(self, date_range: str = 'month') -> Dict:
        """
        Get cost analysis for delivery operations
        
        Args:
            date_range: 'week', 'month', 'quarter', 'year'
        
        Returns:
            Cost analysis dictionary
        """
        try:
            start_date, end_date = self._get_date_range(date_range)
            
            # Get delivery costs
            deliveries = Delivery.query.filter(
                Delivery.created_at >= start_date,
                Delivery.created_at < end_date,
                Delivery.status == DeliveryStatus.DELIVERED.value
            ).all()
            
            # Calculate total distance and fuel costs
            total_distance = sum(float(d.actual_distance or 0) for d in deliveries)
            fuel_cost_per_km = 0.15  # Configurable
            total_fuel_cost = total_distance * fuel_cost_per_km
            
            # Get driver earnings (cost to business)
            driver_earnings = DriverEarning.query.filter(
                DriverEarning.created_at >= start_date,
                DriverEarning.created_at < end_date,
                DriverEarning.earning_type.in_(['base', 'commission'])
            ).all()
            
            total_driver_earnings = sum(float(e.amount) for e in driver_earnings)
            
            # Get delivery revenue
            delivery_orders = db.session.query(Order).join(Delivery).filter(
                Delivery.created_at >= start_date,
                Delivery.created_at < end_date,
                Delivery.status == DeliveryStatus.DELIVERED.value
            ).all()
            
            total_delivery_revenue = sum(float(order.delivery_fee or 0) for order in delivery_orders)
            
            # Calculate cost per delivery
            total_deliveries = len(deliveries)
            cost_per_delivery = (total_fuel_cost + total_driver_earnings) / max(total_deliveries, 1)
            
            # Cost breakdown by category
            cost_breakdown = {
                'fuel_costs': total_fuel_cost,
                'driver_earnings': total_driver_earnings,
                'total_costs': total_fuel_cost + total_driver_earnings
            }
            
            # Efficiency metrics
            cost_efficiency = total_delivery_revenue / max(total_fuel_cost + total_driver_earnings, 1)
            revenue_per_delivery = total_delivery_revenue / max(total_deliveries, 1)
            
            return {
                'date_range': date_range,
                'period_start': start_date.isoformat(),
                'period_end': end_date.isoformat(),
                
                # Volume metrics
                'total_deliveries': total_deliveries,
                'total_distance_km': total_distance,
                'average_distance_per_delivery': total_distance / max(total_deliveries, 1),
                
                # Cost metrics
                'cost_breakdown': cost_breakdown,
                'cost_per_delivery': cost_per_delivery,
                
                # Revenue metrics
                'total_delivery_revenue': total_delivery_revenue,
                'revenue_per_delivery': revenue_per_delivery,
                
                # Efficiency
                'cost_efficiency_ratio': cost_efficiency,
                'profit_per_delivery': revenue_per_delivery - cost_per_delivery
            }
            
        except Exception as e:
            current_app.logger.error(f"Error getting cost analysis: {str(e)}")
            return {'error': str(e)}
    
    def _get_date_range(self, date_range: str) -> Tuple[datetime, datetime]:
        """Get start and end date for a given range"""
        end_date = datetime.utcnow()
        
        if date_range == 'today':
            start_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
        elif date_range == 'week':
            start_date = end_date - timedelta(days=7)
        elif date_range == 'month':
            start_date = end_date - timedelta(days=30)
        elif date_range == 'quarter':
            start_date = end_date - timedelta(days=90)
        elif date_range == 'year':
            start_date = end_date - timedelta(days=365)
        else:
            start_date = end_date - timedelta(days=30)  # Default to month
        
        return start_date, end_date
    
    def _get_average_delivery_time(self, start_date: datetime, end_date: datetime) -> float:
        """Get average delivery time for a period"""
        try:
            deliveries = Delivery.query.filter(
                Delivery.pickup_time.isnot(None),
                Delivery.delivery_time.isnot(None),
                Delivery.created_at >= start_date,
                Delivery.created_at < end_date
            ).all()
            
            if not deliveries:
                return 0.0
            
            total_time = sum(
                (d.delivery_time - d.pickup_time).total_seconds() / 60
                for d in deliveries
            )
            
            return total_time / len(deliveries)
            
        except Exception as e:
            current_app.logger.error(f"Error calculating average delivery time: {str(e)}")
            return 0.0
    
    def _get_on_time_percentage(self, start_date: datetime, end_date: datetime) -> float:
        """Get percentage of on-time deliveries"""
        try:
            deliveries = Delivery.query.filter(
                Delivery.created_at >= start_date,
                Delivery.created_at < end_date,
                Delivery.status == DeliveryStatus.DELIVERED.value
            ).all()
            
            if not deliveries:
                return 0.0
            
            on_time_count = 0
            for delivery in deliveries:
                if delivery.estimated_duration and delivery.pickup_time and delivery.delivery_time:
                    actual_time = (delivery.delivery_time - delivery.pickup_time).total_seconds() / 60
                    if actual_time <= delivery.estimated_duration * 1.2:  # 20% tolerance
                        on_time_count += 1
            
            return (on_time_count / len(deliveries)) * 100
            
        except Exception as e:
            current_app.logger.error(f"Error calculating on-time percentage: {str(e)}")
            return 0.0
    
    def _get_top_performing_drivers(self, start_date: datetime, end_date: datetime, limit: int = 5) -> List[Dict]:
        """Get top performing drivers for a period"""
        try:
            # Get driver performance metrics
            drivers = db.session.query(
                Driver.id,
                Driver.user_id,
                func.count(Delivery.id).label('total_deliveries'),
                func.sum(func.case([(Delivery.status == DeliveryStatus.DELIVERED.value, 1)], else_=0)).label('successful_deliveries')
            ).join(Delivery).filter(
                Delivery.created_at >= start_date,
                Delivery.created_at < end_date
            ).group_by(Driver.id).order_by(
                func.count(Delivery.id).desc()
            ).limit(limit).all()
            
            result = []
            for driver_data in drivers:
                driver = Driver.query.get(driver_data.id)
                avg_rating = driver.get_average_rating()
                
                result.append({
                    'driver_id': driver_data.id,
                    'driver_name': driver.user.name if driver.user else 'Unknown',
                    'total_deliveries': driver_data.total_deliveries,
                    'successful_deliveries': driver_data.successful_deliveries,
                    'success_rate': (driver_data.successful_deliveries / max(driver_data.total_deliveries, 1)) * 100,
                    'average_rating': avg_rating
                })
            
            return result
            
        except Exception as e:
            current_app.logger.error(f"Error getting top performing drivers: {str(e)}")
            return []
    
    def _get_delivery_zone_performance(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        """Get performance by delivery zones"""
        try:
            # This would require zone assignment in deliveries
            # For now, return empty list
            return []
            
        except Exception as e:
            current_app.logger.error(f"Error getting zone performance: {str(e)}")
            return []
    
    def _get_driver_average_delivery_time(self, driver_id: int, start_date: datetime, end_date: datetime) -> float:
        """Get average delivery time for a specific driver"""
        try:
            deliveries = Delivery.query.filter(
                Delivery.driver_id == driver_id,
                Delivery.pickup_time.isnot(None),
                Delivery.delivery_time.isnot(None),
                Delivery.created_at >= start_date,
                Delivery.created_at < end_date
            ).all()
            
            if not deliveries:
                return 0.0
            
            total_time = sum(
                (d.delivery_time - d.pickup_time).total_seconds() / 60
                for d in deliveries
            )
            
            return total_time / len(deliveries)
            
        except Exception as e:
            current_app.logger.error(f"Error calculating driver average delivery time: {str(e)}")
            return 0.0
    
    def _get_driver_location_analytics(self, driver_id: int, start_date: datetime, end_date: datetime) -> Dict:
        """Get location-based analytics for a driver"""
        try:
            locations = DriverLocation.query.filter(
                DriverLocation.driver_id == driver_id,
                DriverLocation.timestamp >= start_date,
                DriverLocation.timestamp < end_date
            ).all()
            
            if not locations:
                return {
                    'total_locations': 0,
                    'average_speed': 0,
                    'max_speed': 0,
                    'total_distance': 0
                }
            
            speeds = [loc.speed for loc in locations if loc.speed]
            avg_speed = sum(speeds) / len(speeds) if speeds else 0
            max_speed = max(speeds) if speeds else 0
            
            # Calculate total distance (simplified)
            total_distance = 0
            for i in range(1, len(locations)):
                dist = ((locations[i].latitude - locations[i-1].latitude)**2 + 
                        (locations[i].longitude - locations[i-1].longitude)**2)**0.5 * 111  # Approximate km
                total_distance += dist
            
            return {
                'total_locations': len(locations),
                'average_speed': avg_speed,
                'max_speed': max_speed,
                'total_distance_km': total_distance
            }
            
        except Exception as e:
            current_app.logger.error(f"Error getting driver location analytics: {str(e)}")
            return {}
    
    def _get_driver_daily_breakdown(self, driver_id: int, start_date: datetime, end_date: datetime) -> List[Dict]:
        """Get daily breakdown of driver performance"""
        try:
            # Group deliveries by day
            daily_data = db.session.query(
                func.date(Delivery.created_at).label('date'),
                func.count(Delivery.id).label('total_deliveries'),
                func.sum(func.case([(Delivery.status == DeliveryStatus.DELIVERED.value, 1)], else_=0)).label('successful_deliveries')
            ).filter(
                Delivery.driver_id == driver_id,
                Delivery.created_at >= start_date,
                Delivery.created_at < end_date
            ).group_by(func.date(Delivery.created_at)).all()
            
            result = []
            for data in daily_data:
                result.append({
                    'date': data.date.isoformat(),
                    'total_deliveries': data.total_deliveries,
                    'successful_deliveries': data.successful_deliveries,
                    'success_rate': (data.successful_deliveries / max(data.total_deliveries, 1)) * 100
                })
            
            return result
            
        except Exception as e:
            current_app.logger.error(f"Error getting driver daily breakdown: {str(e)}")
            return []
    
    def _get_hourly_delivery_pattern(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        """Get hourly delivery pattern"""
        try:
            hourly_data = db.session.query(
                func.extract('hour', Delivery.created_at).label('hour'),
                func.count(Delivery.id).label('deliveries')
            ).filter(
                Delivery.created_at >= start_date,
                Delivery.created_at < end_date
            ).group_by(func.extract('hour', Delivery.created_at)).all()
            
            # Fill in missing hours with 0
            result = []
            for hour in range(24):
                count = next((d.deliveries for d in hourly_data if d.hour == hour), 0)
                result.append({
                    'hour': hour,
                    'deliveries': count,
                    'hour_label': f"{hour:02d}:00"
                })
            
            return result
            
        except Exception as e:
            current_app.logger.error(f"Error getting hourly delivery pattern: {str(e)}")
            return []
    
    def _get_daily_delivery_pattern(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        """Get daily delivery pattern (day of week)"""
        try:
            daily_data = db.session.query(
                func.extract('dow', Delivery.created_at).label('day_of_week'),
                func.count(Delivery.id).label('deliveries')
            ).filter(
                Delivery.created_at >= start_date,
                Delivery.created_at < end_date
            ).group_by(func.extract('dow', Delivery.created_at)).all()
            
            day_names = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
            result = []
            
            for day in range(7):
                count = next((d.deliveries for d in daily_data if d.day_of_week == day), 0)
                result.append({
                    'day_of_week': day,
                    'day_name': day_names[day],
                    'deliveries': count
                })
            
            return result
            
        except Exception as e:
            current_app.logger.error(f"Error getting daily delivery pattern: {str(e)}")
            return []
    
    def _get_weekly_delivery_pattern(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        """Get weekly delivery pattern"""
        try:
            # Group by week
            weekly_data = db.session.query(
                func.date_trunc('week', Delivery.created_at).label('week'),
                func.count(Delivery.id).label('deliveries')
            ).filter(
                Delivery.created_at >= start_date,
                Delivery.created_at < end_date
            ).group_by(func.date_trunc('week', Delivery.created_at)).all()
            
            result = []
            for data in weekly_data:
                result.append({
                    'week_start': data.week.isoformat(),
                    'deliveries': data.deliveries
                })
            
            return result
            
        except Exception as e:
            current_app.logger.error(f"Error getting weekly delivery pattern: {str(e)}")
            return []
    
    def _get_delivery_time_trends(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        """Get delivery time trends over the period"""
        try:
            # Group by day
            daily_data = db.session.query(
                func.date(Delivery.created_at).label('date'),
                func.avg(func.extract('epoch', Delivery.delivery_time - Delivery.pickup_time) / 60).label('avg_delivery_time')
            ).filter(
                Delivery.pickup_time.isnot(None),
                Delivery.delivery_time.isnot(None),
                Delivery.created_at >= start_date,
                Delivery.created_at < end_date
            ).group_by(func.date(Delivery.created_at)).all()
            
            result = []
            for data in daily_data:
                result.append({
                    'date': data.date.isoformat(),
                    'average_delivery_time': float(data.avg_delivery_time) if data.avg_delivery_time else 0
                })
            
            return result
            
        except Exception as e:
            current_app.logger.error(f"Error getting delivery time trends: {str(e)}")
            return []
    
    def _get_zone_delivery_trends(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        """Get delivery trends by zone"""
        try:
            # This would require zone assignment in deliveries
            # For now, return empty list
            return []
            
        except Exception as e:
            current_app.logger.error(f"Error getting zone delivery trends: {str(e)}")
            return []