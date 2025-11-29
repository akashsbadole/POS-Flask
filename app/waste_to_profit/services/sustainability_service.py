"""
Sustainability Service
Manages sustainability metrics, reporting, and environmental impact tracking
"""

from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Tuple
from sqlalchemy import and_, or_, func
import numpy as np
import logging

from app import db
from app.models.inventory import Ingredient
from app.models.waste_to_profit import WasteRecord, SustainabilityMetric, ChefSpecial
from app.ai.services.inventory_intelligence_service import InventoryIntelligenceService


class SustainabilityService:
    """Service for sustainability metrics and reporting"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.inventory_service = InventoryIntelligenceService()
        
        # Carbon footprint factors (kg CO2e per kg of food)
        self.carbon_factors = {
            'meat': 27.0,
            'poultry': 6.9,
            'fish': 5.4,
            'dairy': 3.2,
            'vegetable': 2.0,
            'fruit': 1.1,
            'grain': 1.5,
            'liquid': 0.8,
            'other': 2.5
        }
        
        # Water usage factors (liters per kg of food)
        self.water_factors = {
            'meat': 15400,
            'poultry': 4325,
            'fish': 3691,
            'dairy': 1020,
            'vegetable': 322,
            'fruit': 962,
            'grain': 1644,
            'liquid': 200,
            'other': 1500
        }
    
    def calculate_environmental_impact(self, start_date: date = None, end_date: date = None) -> Dict:
        """
        Calculate environmental impact of waste and operations
        
        Args:
            start_date: Start date for analysis
            end_date: End date for analysis
            
        Returns:
            Dictionary with environmental impact metrics
        """
        try:
            if not start_date:
                start_date = date.today() - timedelta(days=30)
            if not end_date:
                end_date = date.today()
            
            # Get waste records for period
            waste_records = WasteRecord.query.filter(
                and_(
                    WasteRecord.waste_date >= start_date,
                    WasteRecord.waste_date <= end_date
                )
            ).all()
            
            # Calculate environmental metrics
            total_waste_kg = 0
            carbon_footprint = 0
            water_usage = 0
            
            category_impacts = {}
            
            for record in waste_records:
                if record.ingredient:
                    category = record.ingredient.category or 'other'
                    quantity_kg = self._convert_to_kg(
                        float(record.quantity_wasted),
                        record.ingredient.unit
                    )
                    
                    total_waste_kg += quantity_kg
                    
                    # Calculate carbon footprint
                    carbon_factor = self.carbon_factors.get(category, self.carbon_factors['other'])
                    carbon_impact = quantity_kg * carbon_factor
                    carbon_footprint += carbon_impact
                    
                    # Calculate water usage
                    water_factor = self.water_factors.get(category, self.water_factors['other'])
                    water_impact = quantity_kg * water_factor
                    water_usage += water_impact
                    
                    # Track by category
                    if category not in category_impacts:
                        category_impacts[category] = {
                            'quantity_kg': 0,
                            'carbon_footprint': 0,
                            'water_usage': 0
                        }
                    
                    category_impacts[category]['quantity_kg'] += quantity_kg
                    category_impacts[category]['carbon_footprint'] += carbon_impact
                    category_impacts[category]['water_usage'] += water_impact
            
            # Calculate positive impacts from Chef's Specials
            chef_specials = ChefSpecial.query.filter(
                and_(
                    ChefSpecial.created_at >= start_date,
                    ChefSpecial.created_at <= end_date
                )
            ).all()
            
            waste_reduction = sum(float(s.cost_savings or 0) for s in chef_specials)
            carbon_saved = self._estimate_carbon_savings(waste_reduction)
            
            return {
                'period_start': start_date.isoformat(),
                'period_end': end_date.isoformat(),
                'total_waste_kg': total_waste_kg,
                'carbon_footprint_kg': carbon_footprint,
                'water_usage_liters': water_usage,
                'category_breakdown': category_impacts,
                'waste_reduction_kg': waste_reduction / 10,  # Estimate kg saved
                'carbon_saved_kg': carbon_saved,
                'net_carbon_impact': carbon_footprint - carbon_saved,
                'equivalencies': self._calculate_environmental_equivalencies(
                    carbon_footprint, water_usage, carbon_saved
                ),
                'impact_trends': self._calculate_impact_trends(start_date, end_date)
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating environmental impact: {str(e)}")
            return {}
    
    def get_sustainability_metrics(self, period_start: date = None, period_end: date = None) -> List[Dict]:
        """
        Get all sustainability metrics for the specified period
        
        Args:
            period_start: Start date for metrics
            period_end: End date for metrics
            
        Returns:
            List of sustainability metrics
        """
        try:
            if not period_start:
                period_start = date.today() - timedelta(days=30)
            if not period_end:
                period_end = date.today()
            
            # Get metrics for period
            metrics = SustainabilityMetric.query.filter(
                and_(
                    SustainabilityMetric.period_start >= period_start,
                    SustainabilityMetric.period_end <= period_end
                )
            ).all()
            
            return [metric.to_dict() for metric in metrics]
            
        except Exception as e:
            self.logger.error(f"Error getting sustainability metrics: {str(e)}")
            return []
    
    def calculate_sustainability_kpis(self, days_back: int = 30) -> Dict:
        """
        Calculate key performance indicators for sustainability
        
        Args:
            days_back: Number of days to analyze
            
        Returns:
            Dictionary with KPIs
        """
        try:
            start_date = date.today() - timedelta(days=days_back)
            
            # Get current period data
            current_metrics = self.get_sustainability_metrics(start_date, date.today())
            
            # Get previous period for comparison
            previous_start = start_date - timedelta(days=days_back)
            previous_metrics = self.get_sustainability_metrics(previous_start, start_date)
            
            # Calculate KPIs
            kpis = {
                'waste_reduction_rate': self._calculate_waste_reduction_rate(current_metrics),
                'cost_savings_rate': self._calculate_cost_savings_rate(current_metrics),
                'carbon_footprint_reduction': self._calculate_carbon_reduction_rate(
                    current_metrics, previous_metrics
                ),
                'sustainability_score': self._calculate_overall_sustainability_score(current_metrics),
                'target_achievement': self._calculate_target_achievement(current_metrics),
                'trend_analysis': self._analyze_sustainability_trends(
                    current_metrics, previous_metrics
                )
            }
            
            return kpis
            
        except Exception as e:
            self.logger.error(f"Error calculating sustainability KPIs: {str(e)}")
            return {}
    
    def generate_sustainability_report(self, report_type: str = 'comprehensive', 
                                 period_start: date = None, period_end: date = None) -> Dict:
        """
        Generate comprehensive sustainability report
        
        Args:
            report_type: Type of report ('comprehensive', 'environmental', 'cost', 'compliance')
            period_start: Start date for report
            period_end: End date for report
            
        Returns:
            Dictionary with sustainability report
        """
        try:
            if not period_start:
                period_start = date.today() - timedelta(days=30)
            if not period_end:
                period_end = date.today()
            
            # Get base data
            environmental_impact = self.calculate_environmental_impact(period_start, period_end)
            metrics = self.get_sustainability_metrics(period_start, period_end)
            kpis = self.calculate_sustainability_kpis(
                (period_end - period_start).days
            )
            
            # Generate report based on type
            if report_type == 'comprehensive':
                report = self._generate_comprehensive_report(
                    environmental_impact, metrics, kpis, period_start, period_end
                )
            elif report_type == 'environmental':
                report = self._generate_environmental_report(
                    environmental_impact, period_start, period_end
                )
            elif report_type == 'cost':
                report = self._generate_cost_report(metrics, kpis, period_start, period_end)
            elif report_type == 'compliance':
                report = self._generate_compliance_report(metrics, kpis, period_start, period_end)
            else:
                report = {'error': 'Invalid report type'}
            
            return report
            
        except Exception as e:
            self.logger.error(f"Error generating sustainability report: {str(e)}")
            return {}
    
    def track_sustainability_goals(self, goals: List[Dict]) -> Dict:
        """
        Track progress towards sustainability goals
        
        Args:
            goals: List of sustainability goals
            
        Returns:
            Dictionary with goal tracking information
        """
        try:
            goal_tracking = []
            
            for goal in goals:
                goal_id = goal.get('id')
                target_value = goal.get('target_value', 0)
                metric_type = goal.get('metric_type')
                period_days = goal.get('period_days', 30)
                
                # Get current metrics
                end_date = date.today()
                start_date = end_date - timedelta(days=period_days)
                
                current_metrics = [m for m in self.get_sustainability_metrics(start_date, end_date)
                               if m.get('metric_type') == metric_type]
                
                if current_metrics:
                    current_value = sum(m.get('metric_value', 0) for m in current_metrics)
                    progress = (current_value / target_value) * 100 if target_value > 0 else 0
                    on_track = progress >= 80  # 80% threshold
                else:
                    current_value = 0
                    progress = 0
                    on_track = False
                
                goal_tracking.append({
                    'goal_id': goal_id,
                    'goal_name': goal.get('name', 'Unnamed Goal'),
                    'metric_type': metric_type,
                    'target_value': target_value,
                    'current_value': current_value,
                    'progress_percentage': min(100, max(0, progress)),
                    'on_track': on_track,
                    'period_days': period_days,
                    'period_start': start_date.isoformat(),
                    'period_end': end_date.isoformat()
                })
            
            return {
                'goals_tracked': len(goal_tracking),
                'overall_progress': sum(g['progress_percentage'] for g in goal_tracking) / len(goal_tracking) if goal_tracking else 0,
                'goals_on_track': sum(1 for g in goal_tracking if g['on_track']),
                'goal_details': goal_tracking
            }
            
        except Exception as e:
            self.logger.error(f"Error tracking sustainability goals: {str(e)}")
            return {}
    
    def get_green_certification_status(self) -> Dict:
        """
        Get status for green restaurant certification requirements
        
        Returns:
            Dictionary with certification status and requirements
        """
        try:
            # Get current metrics
            current_metrics = self.get_sustainability_metrics(
                date.today() - timedelta(days=90), date.today()
            )
            
            # Define certification requirements
            certification_requirements = {
                'waste_reduction': {
                    'required': 30,  # 30% waste reduction
                    'current': 0,
                    'met': False
                },
                'energy_efficiency': {
                    'required': 20,  # 20% energy reduction
                    'current': 0,
                    'met': False
                },
                'water_conservation': {
                    'required': 15,  # 15% water reduction
                    'current': 0,
                    'met': False
                },
                'sustainable_sourcing': {
                    'required': 50,  # 50% sustainable sourcing
                    'current': 0,
                    'met': False
                }
            }
            
            # Update with current metrics
            for metric in current_metrics:
                metric_type = metric.get('metric_type')
                if metric_type in certification_requirements:
                    current_value = metric.get('metric_value', 0)
                    target_value = metric.get('target_value', 0)
                    
                    if target_value > 0:
                        percentage = (current_value / target_value) * 100
                        certification_requirements[metric_type]['current'] = percentage
                        certification_requirements[metric_type]['met'] = percentage >= certification_requirements[metric_type]['required']
            
            # Calculate overall certification status
            met_requirements = sum(1 for req in certification_requirements.values() if req['met'])
            total_requirements = len(certification_requirements)
            overall_percentage = (met_requirements / total_requirements) * 100
            
            return {
                'certification_ready': overall_percentage >= 80,
                'overall_percentage': overall_percentage,
                'requirements_met': met_requirements,
                'total_requirements': total_requirements,
                'detailed_requirements': certification_requirements,
                'recommendations': self._generate_certification_recommendations(certification_requirements),
                'next_review_date': (date.today() + timedelta(days=30)).isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting green certification status: {str(e)}")
            return {}
    
    def _convert_to_kg(self, quantity: float, unit: str) -> float:
        """Convert quantity to kilograms"""
        conversion_factors = {
            'kg': 1.0,
            'g': 0.001,
            'l': 1.0,  # Assume 1L = 1kg for liquids
            'ml': 0.001,
            'pcs': 0.1,  # Assume 1 piece = 100g
            'units': 0.1
        }
        
        return quantity * conversion_factors.get(unit.lower(), 0.1)
    
    def _estimate_carbon_savings(self, cost_savings: float) -> float:
        """Estimate carbon savings from cost savings"""
        # Rough estimate: $1 of food waste = 0.5kg CO2e saved
        return cost_savings * 0.5
    
    def _calculate_environmental_equivalencies(self, carbon_footprint: float, 
                                         water_usage: float, carbon_saved: float) -> Dict:
        """Calculate environmental equivalencies for better understanding"""
        net_carbon = carbon_footprint - carbon_saved
        
        return {
            'car_equivalent': net_carbon / 0.00012,  # kg CO2 per km driven
            'tree_equivalent': net_carbon / 21,  # kg CO2 absorbed per tree per year
            'smartphone_charges': water_usage / 0.005,  # Liters per charge
            'shower_minutes': water_usage / 9.5,  # Liters per shower minute
            'energy_savings': carbon_saved * 4.5  # kWh per kg CO2 saved
        }
    
    def _calculate_impact_trends(self, start_date: date, end_date: date) -> Dict:
        """Calculate trend data for environmental impacts"""
        try:
            # Get data for multiple periods
            periods = []
            current_end = end_date
            
            for i in range(4):  # 4 periods
                period_start = current_end - timedelta(days=7)
                period_end = current_end
                
                period_impact = self.calculate_environmental_impact(period_start, period_end)
                
                periods.append({
                    'period_start': period_start.isoformat(),
                    'period_end': period_end.isoformat(),
                    'carbon_footprint': period_impact.get('carbon_footprint_kg', 0),
                    'water_usage': period_impact.get('water_usage_liters', 0),
                    'waste_kg': period_impact.get('total_waste_kg', 0)
                })
                
                current_end = period_start
            
            return {
                'periods': periods,
                'trend_direction': self._determine_trend_direction(periods),
                'average_weekly_impact': {
                    'carbon': np.mean([p['carbon_footprint'] for p in periods]),
                    'water': np.mean([p['water_usage'] for p in periods]),
                    'waste': np.mean([p['waste_kg'] for p in periods])
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating impact trends: {str(e)}")
            return {}
    
    def _determine_trend_direction(self, periods: List[Dict]) -> str:
        """Determine trend direction from period data"""
        if len(periods) < 2:
            return 'insufficient_data'
        
        # Compare first and last periods
        first = periods[-1]
        last = periods[0]
        
        carbon_change = last['carbon_footprint'] - first['carbon_footprint']
        water_change = last['water_usage'] - first['water_usage']
        waste_change = last['waste_kg'] - first['waste_kg']
        
        # Determine overall trend
        if carbon_change < -5 and water_change < -100 and waste_change < -1:
            return 'improving_rapidly'
        elif carbon_change < -2 and water_change < -50 and waste_change < -0.5:
            return 'improving'
        elif carbon_change > 5 and water_change > 100 and waste_change > 1:
            return 'deteriorating'
        elif carbon_change > 2 and water_change > 50 and waste_change > 0.5:
            return 'deteriorating_slowly'
        else:
            return 'stable'
    
    def _calculate_waste_reduction_rate(self, metrics: List[Dict]) -> float:
        """Calculate waste reduction rate from metrics"""
        waste_metrics = [m for m in metrics if m.get('metric_type') == 'waste_reduction']
        
        if not waste_metrics:
            return 0
        
        total_reduction = sum(m.get('metric_value', 0) for m in waste_metrics)
        return total_reduction / len(waste_metrics) if waste_metrics else 0
    
    def _calculate_cost_savings_rate(self, metrics: List[Dict]) -> float:
        """Calculate cost savings rate from metrics"""
        cost_metrics = [m for m in metrics if m.get('metric_type') == 'cost_savings']
        
        if not cost_metrics:
            return 0
        
        total_savings = sum(m.get('metric_value', 0) for m in cost_metrics)
        return total_savings / len(cost_metrics) if cost_metrics else 0
    
    def _calculate_carbon_reduction_rate(self, current_metrics: List[Dict], 
                                    previous_metrics: List[Dict]) -> float:
        """Calculate carbon footprint reduction rate"""
        current_carbon = sum(m.get('metric_value', 0) for m in current_metrics 
                            if m.get('metric_type') == 'carbon_footprint')
        previous_carbon = sum(m.get('metric_value', 0) for m in previous_metrics 
                             if m.get('metric_type') == 'carbon_footprint')
        
        if previous_carbon == 0:
            return 0
        
        return ((previous_carbon - current_carbon) / previous_carbon) * 100
    
    def _calculate_overall_sustainability_score(self, metrics: List[Dict]) -> float:
        """Calculate overall sustainability score"""
        if not metrics:
            return 0
        
        # Weight different metric types
        weights = {
            'waste_reduction': 0.3,
            'cost_savings': 0.2,
            'carbon_footprint': 0.25,
            'water_usage': 0.15,
            'energy_efficiency': 0.1
        }
        
        total_score = 0
        total_weight = 0
        
        for metric in metrics:
            metric_type = metric.get('metric_type')
            if metric_type in weights:
                value = metric.get('metric_value', 0)
                target = metric.get('target_value', 100)
                
                # Normalize to 0-100 scale
                normalized_value = min(100, (value / target) * 100) if target > 0 else 0
                
                total_score += normalized_value * weights[metric_type]
                total_weight += weights[metric_type]
        
        return total_score / total_weight if total_weight > 0 else 0
    
    def _calculate_target_achievement(self, metrics: List[Dict]) -> Dict:
        """Calculate achievement of targets"""
        achievements = {}
        
        for metric in metrics:
            metric_type = metric.get('metric_type')
            current_value = metric.get('metric_value', 0)
            target_value = metric.get('target_value', 100)
            
            if target_value > 0:
                achievement = (current_value / target_value) * 100
                achievements[metric_type] = {
                    'current': current_value,
                    'target': target_value,
                    'achievement_percentage': min(100, achievement),
                    'met': achievement >= 100
                }
        
        return achievements
    
    def _analyze_sustainability_trends(self, current_metrics: List[Dict], 
                                     previous_metrics: List[Dict]) -> Dict:
        """Analyze trends in sustainability metrics"""
        trends = {}
        
        for metric_type in ['waste_reduction', 'cost_savings', 'carbon_footprint']:
            current_values = [m.get('metric_value', 0) for m in current_metrics 
                           if m.get('metric_type') == metric_type]
            previous_values = [m.get('metric_value', 0) for m in previous_metrics 
                            if m.get('metric_type') == metric_type]
            
            if current_values and previous_values:
                current_avg = np.mean(current_values)
                previous_avg = np.mean(previous_values)
                
                if previous_avg != 0:
                    change = ((current_avg - previous_avg) / previous_avg) * 100
                    trends[metric_type] = {
                        'current_value': current_avg,
                        'previous_value': previous_avg,
                        'percentage_change': change,
                        'trend': 'improving' if change > 0 else 'declining' if change < 0 else 'stable'
                    }
        
        return trends
    
    def _generate_comprehensive_report(self, environmental_impact: Dict, metrics: List[Dict],
                                   kpis: Dict, period_start: date, period_end: date) -> Dict:
        """Generate comprehensive sustainability report"""
        return {
            'report_type': 'comprehensive',
            'period_start': period_start.isoformat(),
            'period_end': period_end.isoformat(),
            'executive_summary': {
                'total_waste_reduction': kpis.get('waste_reduction_rate', 0),
                'total_cost_savings': kpis.get('cost_savings_rate', 0),
                'carbon_footprint_reduction': kpis.get('carbon_footprint_reduction', 0),
                'overall_sustainability_score': kpis.get('sustainability_score', 0)
            },
            'environmental_impact': environmental_impact,
            'detailed_metrics': metrics,
            'key_performance_indicators': kpis,
            'recommendations': self._generate_comprehensive_recommendations(kpis),
            'appendix': {
                'methodology': 'Data collected from inventory, waste tracking, and Chef\'s Special systems',
                'assumptions': 'Carbon and water factors based on industry standards',
                'limitations': 'Data accuracy dependent on proper recording practices'
            }
        }
    
    def _generate_environmental_report(self, environmental_impact: Dict, 
                                    period_start: date, period_end: date) -> Dict:
        """Generate environmental impact report"""
        return {
            'report_type': 'environmental',
            'period_start': period_start.isoformat(),
            'period_end': period_end.isoformat(),
            'carbon_footprint': {
                'total_kg': environmental_impact.get('carbon_footprint_kg', 0),
                'by_category': environmental_impact.get('category_breakdown', {}),
                'equivalencies': environmental_impact.get('equivalencies', {})
            },
            'water_usage': {
                'total_liters': environmental_impact.get('water_usage_liters', 0),
                'by_category': environmental_impact.get('category_breakdown', {})
            },
            'waste_analysis': {
                'total_waste_kg': environmental_impact.get('total_waste_kg', 0),
                'reduction_achieved': environmental_impact.get('waste_reduction_kg', 0)
            },
            'recommendations': self._generate_environmental_recommendations(environmental_impact)
        }
    
    def _generate_cost_report(self, metrics: List[Dict], kpis: Dict,
                            period_start: date, period_end: date) -> Dict:
        """Generate cost-focused sustainability report"""
        return {
            'report_type': 'cost',
            'period_start': period_start.isoformat(),
            'period_end': period_end.isoformat(),
            'financial_summary': {
                'total_cost_savings': kpis.get('cost_savings_rate', 0),
                'waste_cost_avoided': sum(m.get('metric_value', 0) for m in metrics 
                                        if m.get('metric_type') == 'waste_cost_avoided'),
                'operational_efficiency': sum(m.get('metric_value', 0) for m in metrics 
                                         if m.get('metric_type') == 'operational_efficiency')
            },
            'roi_analysis': {
                'implementation_costs': 10000,  # Estimated
                'annual_savings': kpis.get('cost_savings_rate', 0) * 12,
                'payback_period_months': 10000 / (kpis.get('cost_savings_rate', 0) * 12) if kpis.get('cost_savings_rate', 0) > 0 else 0
            },
            'detailed_metrics': metrics,
            'recommendations': self._generate_cost_recommendations(kpis)
        }
    
    def _generate_compliance_report(self, metrics: List[Dict], kpis: Dict,
                                period_start: date, period_end: date) -> Dict:
        """Generate regulatory compliance report"""
        return {
            'report_type': 'compliance',
            'period_start': period_start.isoformat(),
            'period_end': period_end.isoformat(),
            'regulatory_status': {
                'waste_tracking_compliance': self._check_waste_tracking_compliance(metrics),
                'environmental_reporting': self._check_environmental_reporting_compliance(metrics),
                'food_safety_standards': self._check_food_safety_compliance(metrics)
            },
            'certification_status': self.get_green_certification_status(),
            'audit_readiness': {
                'documentation_complete': self._check_documentation_completeness(metrics),
                'training_records': self._check_training_completeness(metrics),
                'monitoring_systems': self._check_monitoring_systems(metrics)
            },
            'recommendations': self._generate_compliance_recommendations(kpis)
        }
    
    def _generate_certification_recommendations(self, requirements: Dict) -> List[str]:
        """Generate recommendations for green certification"""
        recommendations = []
        
        for req_type, req_data in requirements.items():
            if not req_data['met']:
                gap = req_data['required'] - req_data['current']
                recommendations.append(
                    f"Improve {req_type.replace('_', ' ')} by {gap:.1f}% to meet certification requirements"
                )
        
        if not recommendations:
            recommendations.append("All certification requirements met - maintain current performance")
        
        return recommendations
    
    def _generate_comprehensive_recommendations(self, kpis: Dict) -> List[Dict]:
        """Generate recommendations from comprehensive analysis"""
        recommendations = []
        
        score = kpis.get('sustainability_score', 0)
        
        if score < 50:
            recommendations.append({
                'priority': 'high',
                'category': 'overall_performance',
                'description': 'Sustainability performance below target - comprehensive improvement needed',
                'actions': ['Implement waste reduction program', 'Enhance tracking systems', 'Staff training']
            })
        elif score < 75:
            recommendations.append({
                'priority': 'medium',
                'category': 'performance_improvement',
                'description': 'Good progress with room for improvement',
                'actions': ['Optimize existing programs', 'Expand successful initiatives']
            })
        else:
            recommendations.append({
                'priority': 'low',
                'category': 'maintenance',
                'description': 'Excellent sustainability performance - maintain current practices',
                'actions': ['Regular monitoring', 'Continuous improvement', 'Share best practices']
            })
        
        return recommendations
    
    def _generate_environmental_recommendations(self, impact: Dict) -> List[Dict]:
        """Generate environmental impact recommendations"""
        recommendations = []
        
        carbon = impact.get('carbon_footprint_kg', 0)
        water = impact.get('water_usage_liters', 0)
        
        if carbon > 100:
            recommendations.append({
                'priority': 'high',
                'category': 'carbon_reduction',
                'description': 'High carbon footprint - implement reduction strategies',
                'actions': ['Reduce food waste', 'Optimize energy usage', 'Consider renewable energy']
            })
        
        if water > 10000:
            recommendations.append({
                'priority': 'medium',
                'category': 'water_conservation',
                'description': 'High water usage - implement conservation measures',
                'actions': ['Fix leaks', 'Install efficient fixtures', 'Water recycling']
            })
        
        return recommendations
    
    def _generate_cost_recommendations(self, kpis: Dict) -> List[Dict]:
        """Generate cost-focused recommendations"""
        recommendations = []
        
        savings = kpis.get('cost_savings_rate', 0)
        
        if savings < 100:
            recommendations.append({
                'priority': 'high',
                'category': 'cost_optimization',
                'description': 'Low cost savings - implement efficiency measures',
                'actions': ['Waste reduction programs', 'Process optimization', 'Technology investment']
            })
        
        return recommendations
    
    def _generate_compliance_recommendations(self, kpis: Dict) -> List[Dict]:
        """Generate compliance-focused recommendations"""
        recommendations = []
        
        recommendations.append({
            'priority': 'medium',
            'category': 'documentation',
            'description': 'Maintain comprehensive documentation for compliance',
            'actions': ['Regular updates', 'Centralized storage', 'Audit preparation']
        })
        
        return recommendations
    
    def _check_waste_tracking_compliance(self, metrics: List[Dict]) -> bool:
        """Check waste tracking compliance"""
        waste_metrics = [m for m in metrics if m.get('metric_type') == 'waste_tracking']
        return len(waste_metrics) > 0
    
    def _check_environmental_reporting_compliance(self, metrics: List[Dict]) -> bool:
        """Check environmental reporting compliance"""
        env_metrics = [m for m in metrics if m.get('metric_type') in ['carbon_footprint', 'water_usage']]
        return len(env_metrics) > 0
    
    def _check_food_safety_compliance(self, metrics: List[Dict]) -> bool:
        """Check food safety compliance"""
        safety_metrics = [m for m in metrics if m.get('metric_type') == 'food_safety']
        return len(safety_metrics) > 0
    
    def _check_documentation_completeness(self, metrics: List[Dict]) -> bool:
        """Check documentation completeness"""
        doc_metrics = [m for m in metrics if 'documentation' in m.get('metric_type', '')]
        return len(doc_metrics) > 0
    
    def _check_training_completeness(self, metrics: List[Dict]) -> bool:
        """Check training completeness"""
        training_metrics = [m for m in metrics if 'training' in m.get('metric_type', '')]
        return len(training_metrics) > 0
    
    def _check_monitoring_systems(self, metrics: List[Dict]) -> bool:
        """Check monitoring systems"""
        monitoring_metrics = [m for m in metrics if 'monitoring' in m.get('metric_type', '')]
        return len(monitoring_metrics) > 0