"""
Waste Analytics Service
Provides comprehensive waste analysis, pattern identification, and reduction recommendations
"""

from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Tuple
from sqlalchemy import and_, or_, func, extract
import numpy as np
import logging

from app import db
from app.models.inventory import Ingredient
from app.models.waste_to_profit import WasteRecord, ExpiryTracking
from app.ai.services.inventory_intelligence_service import InventoryIntelligenceService


class WasteAnalyticsService:
    """Service for waste analytics and reduction insights"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.inventory_service = InventoryIntelligenceService()
    
    def get_waste_overview(self, start_date: date = None, end_date: date = None) -> Dict:
        """
        Get comprehensive waste overview for the specified period
        
        Args:
            start_date: Start date for analysis (default: 30 days ago)
            end_date: End date for analysis (default: today)
            
        Returns:
            Dictionary with waste overview metrics
        """
        try:
            if not start_date:
                start_date = date.today() - timedelta(days=30)
            if not end_date:
                end_date = date.today()
            
            # Get waste records for the period
            waste_records = WasteRecord.query.filter(
                and_(
                    WasteRecord.waste_date >= start_date,
                    WasteRecord.waste_date <= end_date
                )
            ).all()
            
            # Calculate basic metrics
            total_waste_cost = sum(float(w.total_cost) for w in waste_records)
            total_waste_quantity = sum(float(w.quantity_wasted) for w in waste_records)
            total_records = len(waste_records)
            
            # Group by waste reason
            waste_by_reason = {}
            waste_by_category = {}
            waste_by_department = {}
            
            for record in waste_records:
                # By reason
                reason = record.waste_reason or 'unknown'
                if reason not in waste_by_reason:
                    waste_by_reason[reason] = {'count': 0, 'cost': 0, 'quantity': 0}
                waste_by_reason[reason]['count'] += 1
                waste_by_reason[reason]['cost'] += float(record.total_cost)
                waste_by_reason[reason]['quantity'] += float(record.quantity_wasted)
                
                # By category
                category = record.waste_category or 'unknown'
                if category not in waste_by_category:
                    waste_by_category[category] = {'count': 0, 'cost': 0, 'quantity': 0}
                waste_by_category[category]['count'] += 1
                waste_by_category[category]['cost'] += float(record.total_cost)
                waste_by_category[category]['quantity'] += float(record.quantity_wasted)
                
                # By department
                dept = record.department or 'unknown'
                if dept not in waste_by_department:
                    waste_by_department[dept] = {'count': 0, 'cost': 0, 'quantity': 0}
                waste_by_department[dept]['count'] += 1
                waste_by_department[dept]['cost'] += float(record.total_cost)
                waste_by_department[dept]['quantity'] += float(record.quantity_wasted)
            
            # Calculate trends
            previous_period_start = start_date - timedelta(days=30)
            previous_waste_records = WasteRecord.query.filter(
                and_(
                    WasteRecord.waste_date >= previous_period_start,
                    WasteRecord.waste_date < start_date
                )
            ).all()
            
            previous_cost = sum(float(w.total_cost) for w in previous_waste_records)
            cost_change = ((total_waste_cost - previous_cost) / previous_cost * 100) if previous_cost > 0 else 0
            
            return {
                'period_start': start_date.isoformat(),
                'period_end': end_date.isoformat(),
                'total_waste_cost': total_waste_cost,
                'total_waste_quantity': total_waste_quantity,
                'total_records': total_records,
                'average_cost_per_record': total_waste_cost / total_records if total_records > 0 else 0,
                'cost_change_percentage': cost_change,
                'waste_by_reason': waste_by_reason,
                'waste_by_category': waste_by_category,
                'waste_by_department': waste_by_department,
                'top_waste_items': self._get_top_waste_items(waste_records),
                'daily_waste_trend': self._get_daily_waste_trend(start_date, end_date)
            }
            
        except Exception as e:
            self.logger.error(f"Error getting waste overview: {str(e)}")
            return {}
    
    def analyze_waste_patterns(self, days_back: int = 90) -> Dict:
        """
        Analyze waste patterns to identify trends and causes
        
        Args:
            days_back: Number of days to analyze
            
        Returns:
            Dictionary with waste pattern analysis
        """
        try:
            start_date = date.today() - timedelta(days=days_back)
            
            # Get waste records for analysis
            waste_records = WasteRecord.query.filter(
                WasteRecord.waste_date >= start_date
            ).all()
            
            if not waste_records:
                return {'error': 'No waste data available for analysis'}
            
            # Analyze temporal patterns
            temporal_patterns = self._analyze_temporal_patterns(waste_records)
            
            # Analyze ingredient patterns
            ingredient_patterns = self._analyze_ingredient_patterns(waste_records)
            
            # Analyze seasonal patterns
            seasonal_patterns = self._analyze_seasonal_patterns(waste_records)
            
            # Identify problem areas
            problem_areas = self._identify_problem_areas(waste_records)
            
            # Generate insights
            insights = self._generate_waste_insights(
                temporal_patterns, ingredient_patterns, 
                seasonal_patterns, problem_areas
            )
            
            return {
                'analysis_period': {
                    'start_date': start_date.isoformat(),
                    'end_date': date.today().isoformat(),
                    'days_analyzed': days_back
                },
                'temporal_patterns': temporal_patterns,
                'ingredient_patterns': ingredient_patterns,
                'seasonal_patterns': seasonal_patterns,
                'problem_areas': problem_areas,
                'insights': insights,
                'recommendations': self._generate_pattern_recommendations(insights)
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing waste patterns: {str(e)}")
            return {}
    
    def calculate_cost_of_waste(self, start_date: date = None, end_date: date = None) -> Dict:
        """
        Calculate detailed cost analysis of waste
        
        Args:
            start_date: Start date for analysis
            end_date: End date for analysis
            
        Returns:
            Dictionary with cost analysis
        """
        try:
            if not start_date:
                start_date = date.today() - timedelta(days=30)
            if not end_date:
                end_date = date.today()
            
            # Get waste records
            waste_records = WasteRecord.query.filter(
                and_(
                    WasteRecord.waste_date >= start_date,
                    WasteRecord.waste_date <= end_date
                )
            ).all()
            
            # Calculate cost breakdowns
            total_cost = sum(float(w.total_cost) for w in waste_records)
            
            # By waste reason
            cost_by_reason = {}
            for record in waste_records:
                reason = record.waste_reason or 'unknown'
                if reason not in cost_by_reason:
                    cost_by_reason[reason] = 0
                cost_by_reason[reason] += float(record.total_cost)
            
            # By ingredient category
            cost_by_category = {}
            for record in waste_records:
                if record.ingredient and record.ingredient.category:
                    category = record.ingredient.category
                    if category not in cost_by_category:
                        cost_by_category[category] = 0
                    cost_by_category[category] += float(record.total_cost)
            
            # By department
            cost_by_department = {}
            for record in waste_records:
                dept = record.department or 'unknown'
                if dept not in cost_by_department:
                    cost_by_department[dept] = 0
                cost_by_department[dept] += float(record.total_cost)
            
            # Calculate potential savings
            potential_savings = self._calculate_potential_savings(waste_records)
            
            return {
                'period_start': start_date.isoformat(),
                'period_end': end_date.isoformat(),
                'total_cost': total_cost,
                'average_daily_cost': total_cost / ((end_date - start_date).days + 1),
                'cost_by_reason': cost_by_reason,
                'cost_by_category': cost_by_category,
                'cost_by_department': cost_by_department,
                'potential_savings': potential_savings,
                'cost_trends': self._calculate_cost_trends(waste_records)
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating cost of waste: {str(e)}")
            return {}
    
    def get_waste_reduction_recommendations(self, days_back: int = 30) -> List[Dict]:
        """
        Generate AI-powered waste reduction recommendations
        
        Args:
            days_back: Number of days to analyze for recommendations
            
        Returns:
            List of waste reduction recommendations
        """
        try:
            start_date = date.today() - timedelta(days=days_back)
            
            # Get waste data
            waste_records = WasteRecord.query.filter(
                WasteRecord.waste_date >= start_date
            ).all()
            
            recommendations = []
            
            # Analyze expiry waste
            expiry_waste = [w for w in waste_records if w.waste_reason == 'expiry']
            if expiry_waste:
                recommendations.extend(self._generate_expiry_recommendations(expiry_waste))
            
            # Analyze spoilage waste
            spoilage_waste = [w for w in waste_records if w.waste_reason == 'spoilage']
            if spoilage_waste:
                recommendations.extend(self._generate_spoilage_recommendations(spoilage_waste))
            
            # Analyze preparation waste
            prep_waste = [w for w in waste_records if w.waste_reason == 'preparation']
            if prep_waste:
                recommendations.extend(self._generate_preparation_recommendations(prep_waste))
            
            # Analyze overstocking
            overstock_recommendations = self._generate_overstocking_recommendations(waste_records)
            if overstock_recommendations:
                recommendations.extend(overstock_recommendations)
            
            # Sort by priority and impact
            recommendations.sort(key=lambda x: (x.get('priority', 'medium'), x.get('impact', 0)), reverse=True)
            
            return recommendations
            
        except Exception as e:
            self.logger.error(f"Error generating waste reduction recommendations: {str(e)}")
            return []
    
    def track_waste_reduction_goals(self, goals: List[Dict]) -> Dict:
        """
        Track progress towards waste reduction goals
        
        Args:
            goals: List of waste reduction goals
            
        Returns:
            Dictionary with goal tracking information
        """
        try:
            goal_tracking = []
            
            for goal in goals:
                goal_id = goal.get('id')
                target_reduction = goal.get('target_reduction', 0)  # Percentage
                baseline_period = goal.get('baseline_period', 30)  # Days
                current_period = goal.get('current_period', 30)  # Days
                
                # Calculate baseline waste
                baseline_end = date.today() - timedelta(days=current_period)
                baseline_start = baseline_end - timedelta(days=baseline_period)
                
                baseline_records = WasteRecord.query.filter(
                    and_(
                        WasteRecord.waste_date >= baseline_start,
                        WasteRecord.waste_date < baseline_end
                    )
                ).all()
                
                baseline_cost = sum(float(w.total_cost) for w in baseline_records)
                
                # Calculate current waste
                current_start = date.today() - timedelta(days=current_period)
                current_records = WasteRecord.query.filter(
                    WasteRecord.waste_date >= current_start
                ).all()
                
                current_cost = sum(float(w.total_cost) for w in current_records)
                
                # Calculate progress
                if baseline_cost > 0:
                    actual_reduction = ((baseline_cost - current_cost) / baseline_cost) * 100
                    progress = (actual_reduction / target_reduction) * 100 if target_reduction > 0 else 0
                else:
                    actual_reduction = 0
                    progress = 0
                
                goal_tracking.append({
                    'goal_id': goal_id,
                    'goal_name': goal.get('name', 'Unnamed Goal'),
                    'target_reduction': target_reduction,
                    'baseline_cost': baseline_cost,
                    'current_cost': current_cost,
                    'actual_reduction': actual_reduction,
                    'progress_percentage': min(100, max(0, progress)),
                    'on_track': actual_reduction >= (target_reduction * 0.8),  # 80% threshold
                    'baseline_period': f"{baseline_start} to {baseline_end}",
                    'current_period': f"{current_start} to {date.today()}"
                })
            
            return {
                'goals_tracked': len(goal_tracking),
                'overall_progress': sum(g['progress_percentage'] for g in goal_tracking) / len(goal_tracking) if goal_tracking else 0,
                'goals_on_track': sum(1 for g in goal_tracking if g['on_track']),
                'goal_details': goal_tracking
            }
            
        except Exception as e:
            self.logger.error(f"Error tracking waste reduction goals: {str(e)}")
            return {}
    
    def get_department_wise_analysis(self, department: str = None, days_back: int = 30) -> Dict:
        """
        Get department-wise waste analysis
        
        Args:
            department: Specific department to analyze (optional)
            days_back: Number of days to analyze
            
        Returns:
            Dictionary with department-wise analysis
        """
        try:
            start_date = date.today() - timedelta(days=days_back)
            
            query = WasteRecord.query.filter(
                WasteRecord.waste_date >= start_date
            )
            
            if department:
                query = query.filter(WasteRecord.department == department)
            
            waste_records = query.all()
            
            if not waste_records:
                return {'error': 'No waste data found for the specified criteria'}
            
            # Group by department
            department_analysis = {}
            for record in waste_records:
                dept = record.department or 'unknown'
                if dept not in department_analysis:
                    department_analysis[dept] = {
                        'records': [],
                        'total_cost': 0,
                        'total_quantity': 0,
                        'waste_reasons': {},
                        'top_ingredients': {}
                    }
                
                dept_data = department_analysis[dept]
                dept_data['records'].append(record)
                dept_data['total_cost'] += float(record.total_cost)
                dept_data['total_quantity'] += float(record.quantity_wasted)
                
                # Track waste reasons
                reason = record.waste_reason or 'unknown'
                if reason not in dept_data['waste_reasons']:
                    dept_data['waste_reasons'][reason] = {'count': 0, 'cost': 0}
                dept_data['waste_reasons'][reason]['count'] += 1
                dept_data['waste_reasons'][reason]['cost'] += float(record.total_cost)
                
                # Track top ingredients
                if record.ingredient:
                    ing_name = record.ingredient.name
                    if ing_name not in dept_data['top_ingredients']:
                        dept_data['top_ingredients'][ing_name] = {'count': 0, 'cost': 0, 'quantity': 0}
                    dept_data['top_ingredients'][ing_name]['count'] += 1
                    dept_data['top_ingredients'][ing_name]['cost'] += float(record.total_cost)
                    dept_data['top_ingredients'][ing_name]['quantity'] += float(record.quantity_wasted)
            
            # Calculate department rankings
            dept_rankings = sorted(
                [(dept, data['total_cost']) for dept, data in department_analysis.items()],
                key=lambda x: x[1],
                reverse=True
            )
            
            return {
                'analysis_period': {
                    'start_date': start_date.isoformat(),
                    'end_date': date.today().isoformat(),
                    'days_analyzed': days_back
                },
                'department_analysis': department_analysis,
                'department_rankings': dept_rankings,
                'total_departments': len(department_analysis),
                'department_recommendations': self._generate_department_recommendations(department_analysis)
            }
            
        except Exception as e:
            self.logger.error(f"Error getting department-wise analysis: {str(e)}")
            return {}
    
    def _get_top_waste_items(self, waste_records: List[WasteRecord], limit: int = 10) -> List[Dict]:
        """Get top waste items by cost"""
        ingredient_costs = {}
        
        for record in waste_records:
            if record.ingredient:
                ing_name = record.ingredient.name
                if ing_name not in ingredient_costs:
                    ingredient_costs[ing_name] = {
                        'ingredient_id': record.ingredient_id,
                        'name': ing_name,
                        'category': record.ingredient.category,
                        'total_cost': 0,
                        'total_quantity': 0,
                        'record_count': 0
                    }
                
                ingredient_costs[ing_name]['total_cost'] += float(record.total_cost)
                ingredient_costs[ing_name]['total_quantity'] += float(record.quantity_wasted)
                ingredient_costs[ing_name]['record_count'] += 1
        
        # Sort by cost and return top items
        sorted_items = sorted(ingredient_costs.values(), key=lambda x: x['total_cost'], reverse=True)
        return sorted_items[:limit]
    
    def _get_daily_waste_trend(self, start_date: date, end_date: date) -> List[Dict]:
        """Get daily waste trend for the period"""
        daily_waste = {}
        
        # Initialize all dates in range with zero values
        current_date = start_date
        while current_date <= end_date:
            daily_waste[current_date.isoformat()] = {'cost': 0, 'quantity': 0, 'count': 0}
            current_date += timedelta(days=1)
        
        # Aggregate waste by date
        waste_records = WasteRecord.query.filter(
            and_(
                WasteRecord.waste_date >= start_date,
                WasteRecord.waste_date <= end_date
            )
            ).all()
        
        for record in waste_records:
            date_str = record.waste_date.isoformat()
            if date_str in daily_waste:
                daily_waste[date_str]['cost'] += float(record.total_cost)
                daily_waste[date_str]['quantity'] += float(record.quantity_wasted)
                daily_waste[date_str]['count'] += 1
        
        # Convert to list format
        return [
            {
                'date': date,
                'cost': data['cost'],
                'quantity': data['quantity'],
                'count': data['count']
            }
            for date, data in sorted(daily_waste.items())
        ]
    
    def _analyze_temporal_patterns(self, waste_records: List[WasteRecord]) -> Dict:
        """Analyze temporal waste patterns"""
        # By day of week
        day_patterns = {}
        for record in waste_records:
            day_of_week = record.waste_date.weekday()
            if day_of_week not in day_patterns:
                day_patterns[day_of_week] = {'count': 0, 'cost': 0}
            day_patterns[day_of_week]['count'] += 1
            day_patterns[day_of_week]['cost'] += float(record.total_cost)
        
        # By hour (if time data available)
        hour_patterns = {}
        for record in waste_records:
            if record.created_at:
                hour = record.created_at.hour
                if hour not in hour_patterns:
                    hour_patterns[hour] = {'count': 0, 'cost': 0}
                hour_patterns[hour]['count'] += 1
                hour_patterns[hour]['cost'] += float(record.total_cost)
        
        return {
            'day_of_week': day_patterns,
            'hour_of_day': hour_patterns,
            'peak_waste_day': max(day_patterns.items(), key=lambda x: x[1]['cost'])[0] if day_patterns else None,
            'peak_waste_hour': max(hour_patterns.items(), key=lambda x: x[1]['cost'])[0] if hour_patterns else None
        }
    
    def _analyze_ingredient_patterns(self, waste_records: List[WasteRecord]) -> Dict:
        """Analyze ingredient-specific waste patterns"""
        ingredient_analysis = {}
        
        for record in waste_records:
            if record.ingredient:
                ing_id = record.ingredient_id
                if ing_id not in ingredient_analysis:
                    ingredient_analysis[ing_id] = {
                        'name': record.ingredient.name,
                        'category': record.ingredient.category,
                        'waste_events': [],
                        'total_waste': 0,
                        'waste_reasons': {},
                        'avg_waste_per_event': 0
                    }
                
                ingredient_analysis[ing_id]['waste_events'].append({
                    'date': record.waste_date.isoformat(),
                    'quantity': float(record.quantity_wasted),
                    'cost': float(record.total_cost),
                    'reason': record.waste_reason
                })
                
                ingredient_analysis[ing_id]['total_waste'] += float(record.total_cost)
                
                reason = record.waste_reason or 'unknown'
                if reason not in ingredient_analysis[ing_id]['waste_reasons']:
                    ingredient_analysis[ing_id]['waste_reasons'][reason] = 0
                ingredient_analysis[ing_id]['waste_reasons'][reason] += 1
        
        # Calculate averages
        for ing_id, data in ingredient_analysis.items():
            if data['waste_events']:
                data['avg_waste_per_event'] = data['total_waste'] / len(data['waste_events'])
        
        return ingredient_analysis
    
    def _analyze_seasonal_patterns(self, waste_records: List[WasteRecord]) -> Dict:
        """Analyze seasonal waste patterns"""
        seasonal_data = {}
        
        for record in waste_records:
            month = record.waste_date.month
            season = self._get_season(month)
            
            if season not in seasonal_data:
                seasonal_data[season] = {'count': 0, 'cost': 0, 'categories': {}}
            
            seasonal_data[season]['count'] += 1
            seasonal_data[season]['cost'] += float(record.total_cost)
            
            if record.ingredient and record.ingredient.category:
                category = record.ingredient.category
                if category not in seasonal_data[season]['categories']:
                    seasonal_data[season]['categories'][category] = 0
                seasonal_data[season]['categories'][category] += 1
        
        return seasonal_data
    
    def _identify_problem_areas(self, waste_records: List[WasteRecord]) -> List[Dict]:
        """Identify problem areas in waste management"""
        problems = []
        
        # High waste ingredients
        ingredient_costs = {}
        for record in waste_records:
            if record.ingredient:
                ing_name = record.ingredient.name
                if ing_name not in ingredient_costs:
                    ingredient_costs[ing_name] = 0
                ingredient_costs[ing_name] += float(record.total_cost)
        
        if ingredient_costs:
            avg_cost = np.mean(list(ingredient_costs.values()))
            std_cost = np.std(list(ingredient_costs.values()))
            threshold = avg_cost + (2 * std_cost)  # 2 standard deviations
            
            for ing_name, cost in ingredient_costs.items():
                if cost > threshold:
                    problems.append({
                        'type': 'high_waste_ingredient',
                        'ingredient': ing_name,
                        'cost': cost,
                        'severity': 'high' if cost > avg_cost + (3 * std_cost) else 'medium'
                    })
        
        # Frequent waste reasons
        reason_counts = {}
        for record in waste_records:
            reason = record.waste_reason or 'unknown'
            if reason not in reason_counts:
                reason_counts[reason] = 0
            reason_counts[reason] += 1
        
        total_records = len(waste_records)
        for reason, count in reason_counts.items():
            percentage = (count / total_records) * 100
            if percentage > 30:  # More than 30% of waste
                problems.append({
                    'type': 'frequent_waste_reason',
                    'reason': reason,
                    'percentage': percentage,
                    'count': count,
                    'severity': 'high' if percentage > 50 else 'medium'
                })
        
        return problems
    
    def _generate_waste_insights(self, temporal_patterns: Dict, 
                              ingredient_patterns: Dict, 
                              seasonal_patterns: Dict, 
                              problem_areas: List[Dict]) -> List[Dict]:
        """Generate insights from waste analysis"""
        insights = []
        
        # Temporal insights
        if temporal_patterns.get('peak_waste_day') is not None:
            peak_day = temporal_patterns['peak_waste_day']
            day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            insights.append({
                'type': 'temporal',
                'insight': f"Highest waste occurs on {day_names[peak_day]}",
                'recommendation': "Consider adjusting prep schedules and inventory levels for this day",
                'priority': 'medium'
            })
        
        # Ingredient insights
        high_waste_ingredients = [ing for ing in ingredient_patterns.values() 
                               if ing['total_waste'] > 100]  # $100 threshold
        if high_waste_ingredients:
            insights.append({
                'type': 'ingredient',
                'insight': f"{len(high_waste_ingredients)} ingredients have high waste costs",
                'recommendation': "Focus on inventory management for high-waste ingredients",
                'priority': 'high'
            })
        
        # Seasonal insights
        if seasonal_patterns:
            peak_season = max(seasonal_patterns.items(), key=lambda x: x[1]['cost'])[0]
            insights.append({
                'type': 'seasonal',
                'insight': f"Highest waste occurs in {peak_season}",
                'recommendation': "Adjust ordering patterns and menu for seasonal variations",
                'priority': 'medium'
            })
        
        # Problem area insights
        for problem in problem_areas:
            if problem['type'] == 'high_waste_ingredient':
                insights.append({
                    'type': 'problem_area',
                    'insight': f"Ingredient '{problem['ingredient']}' has exceptionally high waste",
                    'recommendation': "Review ordering quantities and storage conditions",
                    'priority': problem['severity']
                })
        
        return insights
    
    def _generate_pattern_recommendations(self, insights: List[Dict]) -> List[Dict]:
        """Generate recommendations based on insights"""
        recommendations = []
        
        for insight in insights:
            if insight['type'] == 'temporal':
                recommendations.append({
                    'category': 'scheduling',
                    'title': 'Optimize Preparation Schedule',
                    'description': insight['recommendation'],
                    'priority': insight['priority'],
                    'estimated_impact': '15-25% waste reduction',
                    'implementation_effort': 'medium'
                })
            
            elif insight['type'] == 'ingredient':
                recommendations.append({
                    'category': 'inventory_management',
                    'title': 'Improve Inventory Control',
                    'description': insight['recommendation'],
                    'priority': insight['priority'],
                    'estimated_impact': '20-30% waste reduction',
                    'implementation_effort': 'high'
                })
            
            elif insight['type'] == 'seasonal':
                recommendations.append({
                    'category': 'menu_planning',
                    'title': 'Seasonal Menu Adjustments',
                    'description': insight['recommendation'],
                    'priority': insight['priority'],
                    'estimated_impact': '10-20% waste reduction',
                    'implementation_effort': 'medium'
                })
        
        return recommendations
    
    def _generate_expiry_recommendations(self, expiry_waste: List[WasteRecord]) -> List[Dict]:
        """Generate recommendations for expiry-related waste"""
        recommendations = []
        
        # Analyze expiry patterns
        total_expiry_cost = sum(float(w.total_cost) for w in expiry_waste)
        
        if total_expiry_cost > 50:  # $50 threshold
            recommendations.append({
                'category': 'expiry_management',
                'title': 'Implement FIFO System',
                'description': 'First In, First Out inventory rotation to reduce expiry waste',
                'priority': 'high',
                'estimated_impact': f"${total_expiry_cost * 0.7:.2f} potential savings",
                'implementation_effort': 'medium',
                'affected_ingredients': len(set(w.ingredient_id for w in expiry_waste))
            })
        
        # Check for consistent expiry issues
        ingredient_expiry_counts = {}
        for record in expiry_waste:
            if record.ingredient_id:
                if record.ingredient_id not in ingredient_expiry_counts:
                    ingredient_expiry_counts[record.ingredient_id] = 0
                ingredient_expiry_counts[record.ingredient_id] += 1
        
        frequent_expiry_ingredients = [ing_id for ing_id, count in ingredient_expiry_counts.items() if count > 3]
        
        if frequent_expiry_ingredients:
            recommendations.append({
                'category': 'ordering',
                'title': 'Reduce Order Quantities',
                'description': f'{len(frequent_expiry_ingredients)} ingredients frequently expire. Reduce order quantities.',
                'priority': 'medium',
                'estimated_impact': '25-35% reduction in expiry waste',
                'implementation_effort': 'low'
            })
        
        return recommendations
    
    def _generate_spoilage_recommendations(self, spoilage_waste: List[WasteRecord]) -> List[Dict]:
        """Generate recommendations for spoilage-related waste"""
        recommendations = []
        
        total_spoilage_cost = sum(float(w.total_cost) for w in spoilage_waste)
        
        if total_spoilage_cost > 30:  # $30 threshold
            recommendations.append({
                'category': 'storage',
                'title': 'Improve Storage Conditions',
                'description': 'Review and optimize temperature, humidity, and storage conditions',
                'priority': 'high',
                'estimated_impact': f"${total_spoilage_cost * 0.6:.2f} potential savings",
                'implementation_effort': 'medium'
            })
        
        return recommendations
    
    def _generate_preparation_recommendations(self, prep_waste: List[WasteRecord]) -> List[Dict]:
        """Generate recommendations for preparation-related waste"""
        recommendations = []
        
        total_prep_cost = sum(float(w.total_cost) for w in prep_waste)
        
        if total_prep_cost > 25:  # $25 threshold
            recommendations.append({
                'category': 'training',
                'title': 'Staff Training on Preparation',
                'description': 'Train staff on proper preparation techniques to reduce waste',
                'priority': 'medium',
                'estimated_impact': f"${total_prep_cost * 0.5:.2f} potential savings",
                'implementation_effort': 'medium'
            })
        
        return recommendations
    
    def _generate_overstocking_recommendations(self, waste_records: List[WasteRecord]) -> List[Dict]:
        """Generate recommendations for overstocking issues"""
        recommendations = []
        
        # Use AI service to get overstocking analysis
        try:
            overstock_analysis = self.inventory_service.optimize_costs()
            
            if overstock_analysis.get('potential_savings', 0) > 50:
                recommendations.append({
                    'category': 'inventory_optimization',
                    'title': 'AI-Powered Inventory Optimization',
                    'description': 'Implement AI-driven ordering recommendations to prevent overstocking',
                    'priority': 'high',
                    'estimated_impact': f"${overstock_analysis['potential_savings']:.2f} potential savings",
                    'implementation_effort': 'high'
                })
        except Exception as e:
            self.logger.error(f"Error getting overstocking analysis: {str(e)}")
        
        return recommendations
    
    def _calculate_potential_savings(self, waste_records: List[WasteRecord]) -> Dict:
        """Calculate potential savings from waste reduction"""
        total_cost = sum(float(w.total_cost) for w in waste_records)
        
        # Estimate potential savings by waste type
        savings_by_reason = {}
        for record in waste_records:
            reason = record.waste_reason or 'unknown'
            if reason not in savings_by_reason:
                savings_by_reason[reason] = 0
            
            # Estimate savings percentage by reason type
            if reason == 'expiry':
                savings_pct = 0.7  # 70% of expiry waste can be prevented
            elif reason == 'spoilage':
                savings_pct = 0.6  # 60% of spoilage can be prevented
            elif reason == 'preparation':
                savings_pct = 0.5  # 50% of preparation waste can be prevented
            else:
                savings_pct = 0.4  # 40% of other waste can be prevented
            
            savings_by_reason[reason] += float(record.total_cost) * savings_pct
        
        total_potential_savings = sum(savings_by_reason.values())
        
        return {
            'total_potential_savings': total_potential_savings,
            'savings_by_reason': savings_by_reason,
            'savings_percentage': (total_potential_savings / total_cost * 100) if total_cost > 0 else 0
        }
    
    def _calculate_cost_trends(self, waste_records: List[WasteRecord]) -> Dict:
        """Calculate cost trends over time"""
        if not waste_records:
            return {}
        
        # Group by week
        weekly_costs = {}
        for record in waste_records:
            # Get week number
            week_start = record.waste_date - timedelta(days=record.waste_date.weekday())
            week_key = week_start.isoformat()
            
            if week_key not in weekly_costs:
                weekly_costs[week_key] = 0
            weekly_costs[week_key] += float(record.total_cost)
        
        # Calculate trend
        weeks = sorted(weekly_costs.keys())
        if len(weeks) < 2:
            return {'trend': 'insufficient_data'}
        
        costs = [weekly_costs[week] for week in weeks]
        
        # Simple linear trend calculation
        x = list(range(len(costs)))
        trend_slope = np.polyfit(x, costs, 1)[0]
        
        if trend_slope > 5:
            trend = 'increasing_rapidly'
        elif trend_slope > 0:
            trend = 'increasing'
        elif trend_slope < -5:
            trend = 'decreasing_rapidly'
        elif trend_slope < 0:
            trend = 'decreasing'
        else:
            trend = 'stable'
        
        return {
            'trend': trend,
            'trend_slope': trend_slope,
            'weekly_costs': weekly_costs,
            'average_weekly_cost': np.mean(costs),
            'recent_week_cost': costs[-1] if costs else 0
        }
    
    def _generate_department_recommendations(self, department_analysis: Dict) -> List[Dict]:
        """Generate recommendations for each department"""
        recommendations = []
        
        for dept, data in department_analysis.items():
            # Identify top waste reason for department
            if data['waste_reasons']:
                top_reason = max(data['waste_reasons'].items(), key=lambda x: x[1]['cost'])[0]
                
                if top_reason == 'expiry':
                    recommendations.append({
                        'department': dept,
                        'category': 'expiry_management',
                        'title': f'Improve FIFO in {dept}',
                        'description': f'{dept} department has high expiry waste. Implement better rotation.',
                        'priority': 'high' if data['total_cost'] > 100 else 'medium'
                    })
                elif top_reason == 'spoilage':
                    recommendations.append({
                        'department': dept,
                        'category': 'storage',
                        'title': f'Review Storage in {dept}',
                        'description': f'{dept} department has high spoilage. Check storage conditions.',
                        'priority': 'high' if data['total_cost'] > 100 else 'medium'
                    })
                elif top_reason == 'preparation':
                    recommendations.append({
                        'department': dept,
                        'category': 'training',
                        'title': f'Training for {dept}',
                        'description': f'{dept} department has high preparation waste. Additional training needed.',
                        'priority': 'medium'
                    })
        
        return recommendations
    
    def _get_season(self, month: int) -> str:
        """Get season from month number"""
        if month in [12, 1, 2]:
            return 'Winter'
        elif month in [3, 4, 5]:
            return 'Spring'
        elif month in [6, 7, 8]:
            return 'Summer'
        else:
            return 'Fall'