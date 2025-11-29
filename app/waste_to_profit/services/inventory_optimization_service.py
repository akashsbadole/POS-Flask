"""
Inventory Optimization Service
Provides AI-powered inventory optimization recommendations to reduce waste and improve efficiency
"""

from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Tuple
from sqlalchemy import and_, or_, func
import numpy as np
import logging

from app import db
from app.models.inventory import Ingredient, StockAdjustment
from app.models.waste_to_profit import ExpiryTracking, WasteRecord
from app.ai.services.inventory_intelligence_service import InventoryIntelligenceService


class InventoryOptimizationService:
    """Service for inventory optimization recommendations"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.inventory_service = InventoryIntelligenceService()
    
    def get_optimization_recommendations(self, category: Optional[str] = None, days_back: int = 30) -> List[Dict]:
        """
        Get comprehensive inventory optimization recommendations
        
        Args:
            category: Optional category to filter by
            days_back: Number of days to analyze
            
        Returns:
            List of optimization recommendations
        """
        try:
            recommendations = []
            
            # Get waste analysis
            waste_analysis = self._analyze_waste_patterns(category, days_back)
            
            # Get usage patterns
            usage_patterns = self._analyze_usage_patterns(category, days_back)
            
            # Get current inventory status
            inventory_status = self._analyze_inventory_status(category)
            
            # Generate different types of recommendations
            recommendations.extend(self._generate_purchasing_recommendations(waste_analysis, usage_patterns))
            recommendations.extend(self._generate_storage_recommendations(inventory_status))
            recommendations.extend(self._generate_rotation_recommendations(inventory_status))
            recommendations.extend(self._generate_pricing_recommendations(waste_analysis))
            recommendations.extend(self._generate_supplier_recommendations(waste_analysis))
            
            # Sort by priority and impact
            recommendations.sort(key=lambda x: (
                x.get('priority_score', 0), 
                x.get('potential_savings', 0)
            ), reverse=True)
            
            return recommendations
            
        except Exception as e:
            self.logger.error(f"Error getting optimization recommendations: {str(e)}")
            return []
    
    def get_demand_forecasting(self, ingredient_id: Optional[int] = None, days_ahead: int = 30) -> Dict:
        """
        Get demand forecasting for ingredients
        
        Args:
            ingredient_id: Optional specific ingredient
            days_ahead: Number of days to forecast
            
        Returns:
            Dictionary with demand forecasting data
        """
        try:
            if ingredient_id:
                # Forecast for specific ingredient
                forecast = self._forecast_ingredient_demand(ingredient_id, days_ahead)
                return {'ingredient_forecasts': [forecast]}
            else:
                # Forecast for all ingredients
                ingredients = Ingredient.query.filter(Ingredient.is_active == True).all()
                forecasts = []
                
                for ingredient in ingredients:
                    forecast = self._forecast_ingredient_demand(ingredient.id, days_ahead)
                    forecasts.append(forecast)
                
                return {'ingredient_forecasts': forecasts}
                
        except Exception as e:
            self.logger.error(f"Error getting demand forecasting: {str(e)}")
            return {}
    
    def get_purchasing_recommendations(self, supplier_id: Optional[int] = None, days_ahead: int = 30) -> Dict:
        """
        Get smart purchasing recommendations to reduce overstocking
        
        Args:
            supplier_id: Optional supplier filter
            days_ahead: Planning horizon
            
        Returns:
            Dictionary with purchasing recommendations
        """
        try:
            # Get AI-powered purchase orders
            ai_recommendations = self.inventory_service.generate_purchase_orders(supplier_id, days_ahead)
            
            # Enhance with waste-to-profit specific analysis
            enhanced_recommendations = self._enhance_purchase_recommendations(
                ai_recommendations, days_ahead
            )
            
            # Group by urgency and supplier
            urgency_groups = {'urgent': [], 'high': [], 'medium': [], 'low': []}
            supplier_groups = {}
            
            for rec in enhanced_recommendations:
                urgency = rec.get('urgency', 'low')
                urgency_groups[urgency].append(rec)
                
                supplier = rec.get('best_supplier', {}).get('name', 'Unknown')
                if supplier not in supplier_groups:
                    supplier_groups[supplier] = {'items': [], 'total_cost': 0}
                
                supplier_groups[supplier]['items'].append(rec)
                supplier_groups[supplier]['total_cost'] += rec.get('estimated_cost', 0)
            
            return {
                'recommendations': enhanced_recommendations,
                'urgency_groups': urgency_groups,
                'supplier_groups': supplier_groups,
                'total_estimated_cost': sum(rec.get('estimated_cost', 0) for rec in enhanced_recommendations),
                'total_urgent_items': len(urgency_groups['urgent']),
                'implementation_timeline': self._generate_implementation_timeline(urgency_groups)
            }
            
        except Exception as e:
            self.logger.error(f"Error getting purchasing recommendations: {str(e)}")
            return {}
    
    def get_supplier_performance_analysis(self, days_back: int = 90) -> Dict:
        """
        Analyze supplier performance for freshness and quality
        
        Args:
            days_back: Number of days to analyze
            
        Returns:
            Dictionary with supplier performance analysis
        """
        try:
            # Get base supplier analysis from AI service
            base_analysis = self.inventory_service.analyze_supplier_performance(days_back)
            
            # Enhance with waste-to-profit specific metrics
            enhanced_analysis = self._enhance_supplier_analysis(base_analysis, days_back)
            
            # Generate recommendations
            recommendations = self._generate_supplier_recommendations(enhanced_analysis)
            
            return {
                'supplier_analysis': enhanced_analysis,
                'top_performers': enhanced_analysis.get('top_performers', []),
                'needs_improvement': enhanced_analysis.get('needs_improvement', []),
                'freshness_scores': self._calculate_freshness_scores(days_back),
                'recommendations': recommendations,
                'cost_optimization_opportunities': self._find_cost_optimization_opportunities(enhanced_analysis)
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing supplier performance: {str(e)}")
            return {}
    
    def get_storage_optimization(self) -> Dict:
        """
        Get storage optimization recommendations
        
        Returns:
            dict: Storage optimization recommendations
        """
        try:
            from app.models.waste_to_profit import ExpiryTracking
            from app.models.inventory import Ingredient
            
            # Get expiry tracking data
            expiry_items = ExpiryTracking.query.filter(
                ExpiryTracking.status.in_(['fresh', 'expiring_soon'])
            ).all()
            
            # Analyze storage patterns
            storage_analysis = {}
            
            for item in expiry_items:
                storage_location = item.storage_location or 'unknown'
                
                if storage_location not in storage_analysis:
                    storage_analysis[storage_location] = {
                        'total_items': 0,
                        'expiring_items': 0,
                        'total_value': 0,
                        'ingredients': []
                    }
                
                storage_analysis[storage_location]['total_items'] += 1
                storage_analysis[storage_location]['total_value'] += item.quantity * item.unit_cost
                
                if item.status == 'expiring_soon':
                    storage_analysis[storage_location]['expiring_items'] += 1
                
                # Add ingredient info
                ingredient = Ingredient.query.get(item.ingredient_id)
                if ingredient:
                    storage_analysis[storage_location]['ingredients'].append({
                        'ingredient_name': ingredient.name,
                        'quantity': item.quantity,
                        'expiry_date': item.expiry_date,
                        'status': item.status
                    })
            
            # Generate recommendations
            recommendations = []
            
            for location, data in storage_analysis.items():
                # Calculate risk percentage
                risk_percentage = (data['expiring_items'] / data['total_items']) * 100 if data['total_items'] > 0 else 0
                
                if risk_percentage > 30:  # High risk
                    priority = 'high'
                    recommendation = f"High risk location: {location}. Consider FIFO implementation and regular monitoring"
                elif risk_percentage > 15:  # Medium risk
                    priority = 'medium'
                    recommendation = f"Medium risk location: {location}. Improve organization and monitoring"
                else:  # Low risk
                    priority = 'low'
                    recommendation = f"Good storage practices in {location}. Maintain current procedures"
                
                recommendations.append({
                    'storage_location': location,
                    'total_items': data['total_items'],
                    'expiring_items': data['expiring_items'],
                    'risk_percentage': risk_percentage,
                    'total_value': data['total_value'],
                    'priority': priority,
                    'recommendation': recommendation
                })
            
            # Sort by risk percentage
            recommendations.sort(key=lambda x: x['risk_percentage'], reverse=True)
            
            return {
                'recommendations': recommendations,
                'total_locations': len(recommendations),
                'high_risk_locations': len([r for r in recommendations if r['priority'] == 'high']),
                'medium_risk_locations': len([r for r in recommendations if r['priority'] == 'medium']),
                'low_risk_locations': len([r for r in recommendations if r['priority'] == 'low'])
            }
            
        except Exception as e:
            self.logger.error(f"Error getting storage optimization: {str(e)}")
            return {
                'recommendations': [],
                'total_locations': 0,
                'high_risk_locations': 0,
                'medium_risk_locations': 0,
                'low_risk_locations': 0
            }
    
    def get_inventory_turnover_analysis(self, days_back: int = 90) -> Dict:
        """
        Get inventory turnover analysis
        
        Args:
            days_back (int): Number of days to analyze
            
        Returns:
            dict: Inventory turnover analysis
        """
        try:
            from app.models.inventory import Ingredient
            
            # Get inventory turnover data
            ingredients = Ingredient.query.all()
            turnover_data = []
            
            for ingredient in ingredients:
                # Get consumption data
                consumption_data = self._get_ingredient_consumption(ingredient.id, days_back)
                
                # Calculate turnover rate
                avg_inventory = self._get_average_inventory(ingredient.id, days_back)
                turnover_rate = consumption_data['total_quantity'] / avg_inventory if avg_inventory > 0 else 0
                
                # Calculate days of inventory
                daily_consumption = consumption_data['total_quantity'] / days_back
                days_of_inventory = avg_inventory / daily_consumption if daily_consumption > 0 else 0
                
                turnover_data.append({
                    'ingredient_id': ingredient.id,
                    'ingredient_name': ingredient.name,
                    'avg_inventory': avg_inventory,
                    'turnover_rate': turnover_rate,
                    'days_of_inventory': days_of_inventory,
                    'total_consumed': consumption_data['total_quantity'],
                    'category': ingredient.category
                })
            
            # Sort by turnover rate
            turnover_data.sort(key=lambda x: x['turnover_rate'])
            
            # Get summary statistics
            summary = {
                'avg_turnover_rate': sum(item['turnover_rate'] for item in turnover_data) / len(turnover_data) if turnover_data else 0,
                'avg_days_of_inventory': sum(item['days_of_inventory'] for item in turnover_data) / len(turnover_data) if turnover_data else 0,
                'slow_moving_count': len([item for item in turnover_data if item['turnover_rate'] < 0.5]),
                'fast_moving_count': len([item for item in turnover_data if item['turnover_rate'] > 2.0])
            }
            
            return {
                'turnover_data': turnover_data,
                'summary': summary,
                'analysis_period': days_back
            }
            
        except Exception as e:
            self.logger.error(f"Error getting inventory turnover analysis: {str(e)}")
            return {
                'turnover_data': [],
                'summary': {
                    'avg_turnover_rate': 0,
                    'avg_days_of_inventory': 0,
                    'slow_moving_count': 0,
                    'fast_moving_count': 0
                },
                'analysis_period': days_back
            }
    
    def get_cost_saving_opportunities(self, days_back: int = 30) -> Dict:
        """
        Get cost-saving opportunities
        
        Args:
            days_back (int): Number of days to analyze
            
        Returns:
            dict: Cost-saving opportunities
        """
        try:
            from app.models.waste_to_profit import WasteRecord
            from app.models.inventory import Ingredient
            
            # Get waste records
            waste_records = WasteRecord.query.filter(
                WasteRecord.waste_date >= datetime.now() - timedelta(days=days_back)
            ).all()
            
            # Analyze waste patterns
            waste_by_ingredient = {}
            total_waste_cost = 0
            
            for record in waste_records:
                ingredient_id = record.ingredient_id
                cost = record.cost_value or 0
                
                if ingredient_id not in waste_by_ingredient:
                    waste_by_ingredient[ingredient_id] = {
                        'total_quantity': 0,
                        'total_cost': 0,
                        'waste_count': 0
                    }
                
                waste_by_ingredient[ingredient_id]['total_quantity'] += record.quantity
                waste_by_ingredient[ingredient_id]['total_cost'] += cost
                waste_by_ingredient[ingredient_id]['waste_count'] += 1
                total_waste_cost += cost
            
            # Identify opportunities
            opportunities = []
            
            for ingredient_id, waste_data in waste_by_ingredient.items():
                ingredient = Ingredient.query.get(ingredient_id)
                if not ingredient:
                    continue
                
                # Calculate potential savings
                waste_cost = waste_data['total_cost']
                waste_percentage = waste_data['total_quantity'] / 100  # Assuming 100 units as baseline
                
                # Determine opportunity type
                if waste_percentage > 0.2:  # More than 20% waste
                    opportunity_type = 'high_waste'
                    priority = 'high'
                    potential_savings = waste_cost * 0.7  # 70% of waste cost could be saved
                elif waste_percentage > 0.1:  # More than 10% waste
                    opportunity_type = 'medium_waste'
                    priority = 'medium'
                    potential_savings = waste_cost * 0.5  # 50% of waste cost could be saved
                else:
                    opportunity_type = 'low_waste'
                    priority = 'low'
                    potential_savings = waste_cost * 0.3  # 30% of waste cost could be saved
                
                # Generate recommendation
                if opportunity_type == 'high_waste':
                    recommendation = f"Consider reducing order quantity for {ingredient.name} or implementing better storage practices"
                elif opportunity_type == 'medium_waste':
                    recommendation = f"Monitor {ingredient.name} usage patterns and adjust ordering accordingly"
                else:
                    recommendation = f"Regular monitoring of {ingredient.name} waste patterns recommended"
                
                opportunities.append({
                    'ingredient_id': ingredient_id,
                    'ingredient_name': ingredient.name,
                    'opportunity_type': opportunity_type,
                    'priority': priority,
                    'waste_cost': waste_cost,
                    'potential_savings': potential_savings,
                    'waste_percentage': waste_percentage * 100,
                    'recommendation': recommendation,
                    'waste_count': waste_data['waste_count']
                })
            
            # Sort by potential savings
            opportunities.sort(key=lambda x: x['potential_savings'], reverse=True)
            
            # Get summary
            summary = {
                'total_opportunities': len(opportunities),
                'high_priority_count': len([o for o in opportunities if o['priority'] == 'high']),
                'medium_priority_count': len([o for o in opportunities if o['priority'] == 'medium']),
                'low_priority_count': len([o for o in opportunities if o['priority'] == 'low']),
                'total_potential_savings': sum(o['potential_savings'] for o in opportunities),
                'total_waste_cost': total_waste_cost
            }
            
            return {
                'opportunities': opportunities,
                'summary': summary,
                'analysis_period': days_back
            }
            
        except Exception as e:
            self.logger.error(f"Error getting cost-saving opportunities: {str(e)}")
            return {
                'opportunities': [],
                'summary': {
                    'total_opportunities': 0,
                    'high_priority_count': 0,
                    'medium_priority_count': 0,
                    'low_priority_count': 0,
                    'total_potential_savings': 0,
                    'total_waste_cost': 0
                },
                'analysis_period': days_back
            }
    
    def _get_ingredient_consumption(self, ingredient_id: int, days_back: int) -> Dict:
        """Helper method to get ingredient consumption data"""
        # This is a placeholder implementation
        # In a real system, you would query order items, recipe usage, etc.
        return {
            'total_quantity': 50.0,  # Placeholder
            'daily_average': 50.0 / days_back
        }
    
    def _get_average_inventory(self, ingredient_id: int, days_back: int) -> float:
        """Helper method to get average inventory levels"""
        # This is a placeholder implementation
        # In a real system, you would query stock levels over time
        return 100.0  # Placeholder
    
    def _analyze_waste_patterns(self, category: Optional[str], days_back: int) -> Dict:
        """Analyze waste patterns for ingredients"""
        try:
            query = WasteRecord.query.filter(
                WasteRecord.waste_date >= datetime.now() - timedelta(days=days_back)
            )
            
            if category:
                query = query.join(Ingredient).filter(Ingredient.category == category)
            
            waste_records = query.all()
            
            waste_by_ingredient = {}
            total_waste_cost = 0
            
            for record in waste_records:
                ingredient_id = record.ingredient_id
                cost = record.cost_value or 0
                
                if ingredient_id not in waste_by_ingredient:
                    waste_by_ingredient[ingredient_id] = {
                        'total_quantity': 0,
                        'total_cost': 0,
                        'waste_count': 0,
                        'reasons': {}
                    }
                
                waste_by_ingredient[ingredient_id]['total_quantity'] += record.quantity
                waste_by_ingredient[ingredient_id]['total_cost'] += cost
                waste_by_ingredient[ingredient_id]['waste_count'] += 1
                total_waste_cost += cost
                
                # Track reasons
                reason = record.waste_reason or 'unknown'
                if reason not in waste_by_ingredient[ingredient_id]['reasons']:
                    waste_by_ingredient[ingredient_id]['reasons'][reason] = 0
                waste_by_ingredient[ingredient_id]['reasons'][reason] += 1
            
            return {
                'waste_by_ingredient': waste_by_ingredient,
                'total_waste_cost': total_waste_cost,
                'total_waste_records': len(waste_records)
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing waste patterns: {str(e)}")
            return {'waste_by_ingredient': {}, 'total_waste_cost': 0, 'total_waste_records': 0}
    
    def _analyze_usage_patterns(self, category: Optional[str], days_back: int) -> Dict:
        """Analyze usage patterns for ingredients"""
        try:
            # This is a placeholder implementation
            # In a real system, you would query order items, recipe usage, etc.
            
            ingredients = Ingredient.query
            if category:
                ingredients = ingredients.filter(Ingredient.category == category)
            
            ingredients = ingredients.all()
            
            usage_by_ingredient = {}
            
            for ingredient in ingredients:
                # Simulate usage data
                usage_by_ingredient[ingredient.id] = {
                    'ingredient_name': ingredient.name,
                    'total_usage': np.random.uniform(50, 500),  # Random usage for demo
                    'daily_average': np.random.uniform(1.5, 15),
                    'peak_days': ['Monday', 'Friday'],  # Simulated peak days
                    'usage_trend': np.random.choice(['increasing', 'decreasing', 'stable'])
                }
            
            return {
                'usage_by_ingredient': usage_by_ingredient,
                'analysis_period': days_back
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing usage patterns: {str(e)}")
            return {'usage_by_ingredient': {}, 'analysis_period': days_back}
    
    def _analyze_inventory_status(self, category: Optional[str]) -> Dict:
        """Analyze current inventory status"""
        try:
            query = ExpiryTracking.query.filter(
                ExpiryTracking.status.in_(['fresh', 'expiring_soon'])
            )
            
            if category:
                query = query.join(Ingredient).filter(Ingredient.category == category)
            
            expiry_items = query.all()
            
            inventory_by_ingredient = {}
            total_inventory_value = 0
            
            for item in expiry_items:
                ingredient_id = item.ingredient_id
                
                if ingredient_id not in inventory_by_ingredient:
                    inventory_by_ingredient[ingredient_id] = {
                        'total_quantity': 0,
                        'total_value': 0,
                        'fresh_items': 0,
                        'expiring_items': 0,
                        'storage_locations': set()
                    }
                
                inventory_by_ingredient[ingredient_id]['total_quantity'] += item.quantity
                inventory_by_ingredient[ingredient_id]['total_value'] += item.quantity * item.unit_cost
                total_inventory_value += item.quantity * item.unit_cost
                
                if item.status == 'fresh':
                    inventory_by_ingredient[ingredient_id]['fresh_items'] += 1
                else:
                    inventory_by_ingredient[ingredient_id]['expiring_items'] += 1
                
                if item.storage_location:
                    inventory_by_ingredient[ingredient_id]['storage_locations'].add(item.storage_location)
            
            # Convert sets to lists for JSON serialization
            for ingredient_id in inventory_by_ingredient:
                inventory_by_ingredient[ingredient_id]['storage_locations'] = list(
                    inventory_by_ingredient[ingredient_id]['storage_locations']
                )
            
            return {
                'inventory_by_ingredient': inventory_by_ingredient,
                'total_inventory_value': total_inventory_value,
                'total_items_tracked': len(expiry_items)
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing inventory status: {str(e)}")
            return {'inventory_by_ingredient': {}, 'total_inventory_value': 0, 'total_items_tracked': 0}
    
    def _generate_purchasing_recommendations(self, waste_analysis: Dict, usage_patterns: Dict) -> List[Dict]:
        """Generate purchasing recommendations based on waste and usage analysis"""
        recommendations = []
        
        try:
            waste_by_ingredient = waste_analysis.get('waste_by_ingredient', {})
            usage_by_ingredient = usage_patterns.get('usage_by_ingredient', {})
            
            # Find ingredients with high waste but low usage
            for ingredient_id, waste_data in waste_by_ingredient.items():
                if ingredient_id in usage_by_ingredient:
                    usage_data = usage_by_ingredient[ingredient_id]
                    
                    waste_cost = waste_data['total_cost']
                    usage_avg = usage_data['daily_average']
                    
                    # Calculate waste percentage
                    waste_percentage = waste_data['total_quantity'] / 100  # Assuming 100 units as baseline
                    
                    if waste_percentage > 0.15 and usage_avg < 5:  # High waste, low usage
                        priority = 'high'
                        potential_savings = waste_cost * 0.8
                        recommendation = (
                            f"Reduce purchasing quantity for {usage_data['ingredient_name']} "
                            f"due to high waste rate ({waste_percentage:.1%}) and low usage"
                        )
                    elif waste_percentage > 0.1:  # Moderate waste
                        priority = 'medium'
                        potential_savings = waste_cost * 0.5
                        recommendation = (
                            f"Consider reducing order quantity for {usage_data['ingredient_name']} "
                            f"due to moderate waste rate ({waste_percentage:.1%})"
                        )
                    else:
                        continue
                    
                    recommendations.append({
                        'type': 'purchasing',
                        'ingredient_id': ingredient_id,
                        'ingredient_name': usage_data['ingredient_name'],
                        'priority': priority,
                        'potential_savings': potential_savings,
                        'recommendation': recommendation,
                        'waste_percentage': waste_percentage * 100,
                        'daily_usage': usage_avg,
                        'priority_score': 80 if priority == 'high' else 60
                    })
            
            return recommendations
            
        except Exception as e:
            self.logger.error(f"Error generating purchasing recommendations: {str(e)}")
            return []
    
    def _generate_storage_recommendations(self, inventory_status: Dict) -> List[Dict]:
        """Generate storage optimization recommendations"""
        recommendations = []
        
        try:
            inventory_by_ingredient = inventory_status.get('inventory_by_ingredient', {})
            
            # Analyze storage patterns
            storage_analysis = {}
            
            for ingredient_id, data in inventory_by_ingredient.items():
                expiring_ratio = data['expiring_items'] / (data['fresh_items'] + data['expiring_items']) if (data['fresh_items'] + data['expiring_items']) > 0 else 0
                
                if expiring_ratio > 0.3:  # High ratio of expiring items
                    for location in data['storage_locations']:
                        if location not in storage_analysis:
                            storage_analysis[location] = {
                                'total_items': 0,
                                'expiring_items': 0,
                                'total_value': 0,
                                'ingredients': []
                            }
                        
                        storage_analysis[location]['total_items'] += 1
                        storage_analysis[location]['expiring_items'] += 1
                        storage_analysis[location]['total_value'] += data['total_value']
                        storage_analysis[location]['ingredients'].append(ingredient_id)
            
            # Generate recommendations based on storage analysis
            for location, data in storage_analysis.items():
                risk_percentage = (data['expiring_items'] / data['total_items']) * 100 if data['total_items'] > 0 else 0
                
                if risk_percentage > 40:  # High risk
                    priority = 'high'
                    recommendation = f"Implement FIFO system in {location} - {risk_percentage:.1f}% of items expiring"
                    potential_savings = data['total_value'] * 0.3
                elif risk_percentage > 20:  # Medium risk
                    priority = 'medium'
                    recommendation = f"Improve rotation in {location} - {risk_percentage:.1f}% of items expiring"
                    potential_savings = data['total_value'] * 0.2
                else:
                    continue
                
                recommendations.append({
                    'type': 'storage',
                    'storage_location': location,
                    'priority': priority,
                    'potential_savings': potential_savings,
                    'recommendation': recommendation,
                    'risk_percentage': risk_percentage,
                    'affected_items': data['total_items'],
                    'priority_score': 75 if priority == 'high' else 55
                })
            
            return recommendations
            
        except Exception as e:
            self.logger.error(f"Error generating storage recommendations: {str(e)}")
            return []
    
    def _generate_rotation_recommendations(self, inventory_status: Dict) -> List[Dict]:
        """Generate inventory rotation recommendations"""
        recommendations = []
        
        try:
            inventory_by_ingredient = inventory_status.get('inventory_by_ingredient', {})
            
            for ingredient_id, data in inventory_by_ingredient.items():
                expiring_items = data['expiring_items']
                total_items = data['fresh_items'] + expiring_items
                
                if total_items > 0:
                    expiring_ratio = expiring_items / total_items
                    
                    if expiring_ratio > 0.25:  # More than 25% expiring
                        priority = 'high'
                        recommendation = f"Urgent rotation needed for ingredient {ingredient_id} - {expiring_ratio:.1%} of stock expiring"
                        potential_savings = data['total_value'] * 0.4
                    elif expiring_ratio > 0.15:  # More than 15% expiring
                        priority = 'medium'
                        recommendation = f"Regular rotation needed for ingredient {ingredient_id} - {expiring_ratio:.1%} of stock expiring"
                        potential_savings = data['total_value'] * 0.2
                    else:
                        continue
                    
                    recommendations.append({
                        'type': 'rotation',
                        'ingredient_id': ingredient_id,
                        'priority': priority,
                        'potential_savings': potential_savings,
                        'recommendation': recommendation,
                        'expiring_ratio': expiring_ratio * 100,
                        'expiring_items': expiring_items,
                        'total_items': total_items,
                        'priority_score': 70 if priority == 'high' else 50
                    })
            
            return recommendations
            
        except Exception as e:
            self.logger.error(f"Error generating rotation recommendations: {str(e)}")
            return []
    
    def _generate_pricing_recommendations(self, waste_analysis: Dict) -> List[Dict]:
        """Generate pricing recommendations to reduce waste"""
        recommendations = []
        
        try:
            waste_by_ingredient = waste_analysis.get('waste_by_ingredient', {})
            
            for ingredient_id, waste_data in waste_by_ingredient.items():
                waste_cost = waste_data['total_cost']
                
                if waste_cost > 50:  # Significant waste cost
                    # Check if waste is due to overpricing
                    reasons = waste_data.get('reasons', {})
                    expired_reason = reasons.get('expired', 0)
                    
                    if expired_reason > waste_data['waste_count'] * 0.5:  # More than half due to expiration
                        priority = 'medium'
                        potential_savings = waste_cost * 0.3
                        recommendation = f"Consider promotional pricing for ingredient {ingredient_id} to move inventory before expiration"
                        
                        recommendations.append({
                            'type': 'pricing',
                            'ingredient_id': ingredient_id,
                            'priority': priority,
                            'potential_savings': potential_savings,
                            'recommendation': recommendation,
                            'waste_cost': waste_cost,
                            'expired_count': expired_reason,
                            'priority_score': 45
                        })
            
            return recommendations
            
        except Exception as e:
            self.logger.error(f"Error generating pricing recommendations: {str(e)}")
            return []
    
    def _generate_supplier_recommendations(self, waste_analysis: Dict) -> List[Dict]:
        """Generate supplier-related recommendations"""
        recommendations = []
        
        try:
            # This is a placeholder implementation
            # In a real system, you would analyze supplier performance data
            
            total_waste_cost = waste_analysis.get('total_waste_cost', 0)
            
            if total_waste_cost > 100:  # Significant waste
                recommendations.append({
                    'type': 'supplier',
                    'priority': 'medium',
                    'potential_savings': total_waste_cost * 0.15,
                    'recommendation': 'Review supplier delivery schedules and quality to reduce waste',
                    'total_waste_cost': total_waste_cost,
                    'priority_score': 40
                })
            
            return recommendations
            
        except Exception as e:
            self.logger.error(f"Error generating supplier recommendations: {str(e)}")
            return []
    
    def _forecast_ingredient_demand(self, ingredient_id: int, days_ahead: int) -> Dict:
        """Forecast demand for a specific ingredient"""
        try:
            # Get ingredient details
            ingredient = Ingredient.query.get(ingredient_id)
            if not ingredient:
                return {}
            
            # This is a placeholder implementation
            # In a real system, you would use time series analysis
            
            base_demand = np.random.uniform(10, 50)  # Base daily demand
            seasonal_factor = 1.0 + 0.2 * np.sin(2 * np.pi * datetime.now().day / 365)  # Seasonal variation
            
            daily_forecast = []
            for day in range(days_ahead):
                # Add some randomness
                daily_demand = base_demand * seasonal_factor * (1 + np.random.uniform(-0.1, 0.1))
                daily_forecast.append({
                    'date': (datetime.now() + timedelta(days=day)).date().isoformat(),
                    'forecasted_demand': max(0, daily_demand)
                })
            
            total_forecasted_demand = sum(item['forecasted_demand'] for item in daily_forecast)
            
            return {
                'ingredient_id': ingredient_id,
                'ingredient_name': ingredient.name,
                'forecast_period_days': days_ahead,
                'daily_forecast': daily_forecast,
                'total_forecasted_demand': total_forecasted_demand,
                'average_daily_demand': total_forecasted_demand / days_ahead,
                'confidence_level': 0.8  # Placeholder confidence
            }
            
        except Exception as e:
            self.logger.error(f"Error forecasting ingredient demand: {str(e)}")
            return {}
    
    def _enhance_purchase_recommendations(self, ai_recommendations: Dict, days_ahead: int) -> List[Dict]:
        """Enhance AI purchase recommendations with waste-to-profit analysis"""
        enhanced_recommendations = []
        
        try:
            # Get base recommendations from AI service
            base_recs = ai_recommendations.get('recommendations', [])
            
            for rec in base_recs:
                # Add waste-to-profit specific enhancements
                enhanced_rec = rec.copy()
                
                # Add waste risk assessment
                ingredient_id = rec.get('ingredient_id')
                if ingredient_id:
                    # Check for waste history
                    waste_records = WasteRecord.query.filter_by(ingredient_id=ingredient_id).limit(10).all()
                    waste_count = len(waste_records)
                    total_waste = sum(r.quantity for r in waste_records)
                    
                    enhanced_rec['waste_risk'] = 'high' if waste_count > 5 else 'medium' if waste_count > 2 else 'low'
                    enhanced_rec['historical_waste_quantity'] = total_waste
                    enhanced_rec['waste_incidents'] = waste_count
                    
                    # Adjust recommended quantity based on waste history
                    if waste_count > 5:
                        enhanced_rec['recommended_quantity'] *= 0.8  # Reduce by 20%
                        enhanced_rec['adjustment_reason'] = 'Reduced due to high waste history'
                
                enhanced_recommendations.append(enhanced_rec)
            
            return enhanced_recommendations
            
        except Exception as e:
            self.logger.error(f"Error enhancing purchase recommendations: {str(e)}")
            return ai_recommendations.get('recommendations', [])
    
    def _generate_implementation_timeline(self, urgency_groups: Dict) -> Dict:
        """Generate implementation timeline for recommendations"""
        try:
            timeline = {
                'immediate': [],  # Today-1 day
                'short_term': [],  # 2-7 days
                'medium_term': [],  # 1-4 weeks
                'long_term': []   # 1+ months
            }
            
            # Categorize recommendations by urgency
            for urgency, recommendations in urgency_groups.items():
                if urgency == 'urgent':
                    timeline['immediate'].extend(recommendations)
                elif urgency == 'high':
                    timeline['short_term'].extend(recommendations)
                elif urgency == 'medium':
                    timeline['medium_term'].extend(recommendations)
                else:  # low
                    timeline['long_term'].extend(recommendations)
            
            # Add timeframes
            timeline['immediate_days'] = ['0-1 days']
            timeline['short_term_days'] = ['2-7 days']
            timeline['medium_term_days'] = ['1-4 weeks']
            timeline['long_term_days'] = ['1+ months']
            
            return timeline
            
        except Exception as e:
            self.logger.error(f"Error generating implementation timeline: {str(e)}")
            return {}
    
    def _enhance_supplier_analysis(self, base_analysis: Dict, days_back: int) -> Dict:
        """Enhance supplier analysis with waste-to-profit specific metrics"""
        try:
            enhanced_analysis = base_analysis.copy()
            
            # Add waste-to-profit specific metrics
            enhanced_analysis['waste_impact_scores'] = {}
            enhanced_analysis['freshness_performance'] = {}
            
            # This is a placeholder implementation
            # In a real system, you would analyze actual supplier data
            
            suppliers = enhanced_analysis.get('suppliers', [])
            for supplier in suppliers:
                supplier_id = supplier.get('id')
                if supplier_id:
                    # Calculate waste impact score
                    waste_score = np.random.uniform(0.6, 0.95)  # Placeholder score
                    enhanced_analysis['waste_impact_scores'][supplier_id] = waste_score
                    
                    # Calculate freshness performance
                    freshness_score = np.random.uniform(0.7, 0.98)  # Placeholder score
                    enhanced_analysis['freshness_performance'][supplier_id] = freshness_score
            
            return enhanced_analysis
            
        except Exception as e:
            self.logger.error(f"Error enhancing supplier analysis: {str(e)}")
            return base_analysis
    
    def _calculate_freshness_scores(self, days_back: int) -> Dict:
        """Calculate freshness scores for ingredients"""
        try:
            freshness_scores = {}
            
            # Get expiry tracking data
            expiry_items = ExpiryTracking.query.filter(
                ExpiryTracking.created_at >= datetime.now() - timedelta(days=days_back)
            ).all()
            
            # Group by ingredient
            ingredient_freshness = {}
            for item in expiry_items:
                ingredient_id = item.ingredient_id
                
                if ingredient_id not in ingredient_freshness:
                    ingredient_freshness[ingredient_id] = {
                        'total_items': 0,
                        'fresh_items': 0,
                        'expiring_items': 0,
                        'expired_items': 0
                    }
                
                ingredient_freshness[ingredient_id]['total_items'] += 1
                
                if item.status == 'fresh':
                    ingredient_freshness[ingredient_id]['fresh_items'] += 1
                elif item.status == 'expiring_soon':
                    ingredient_freshness[ingredient_id]['expiring_items'] += 1
                else:  # expired
                    ingredient_freshness[ingredient_id]['expired_items'] += 1
            
            # Calculate freshness scores
            for ingredient_id, data in ingredient_freshness.items():
                total = data['total_items']
                if total > 0:
                    # Freshness score: weighted average of status
                    freshness_score = (
                        (data['fresh_items'] * 1.0 +
                         data['expiring_items'] * 0.5 +
                         data['expired_items'] * 0.0) / total
                    )
                    
                    freshness_scores[ingredient_id] = {
                        'freshness_score': freshness_score,
                        'freshness_percentage': freshness_score * 100,
                        'total_items': total,
                        'fresh_items': data['fresh_items'],
                        'expiring_items': data['expiring_items'],
                        'expired_items': data['expired_items']
                    }
            
            return freshness_scores
            
        except Exception as e:
            self.logger.error(f"Error calculating freshness scores: {str(e)}")
            return {}
    
    def _find_cost_optimization_opportunities(self, enhanced_analysis: Dict) -> List[Dict]:
        """Find cost optimization opportunities based on supplier analysis"""
        opportunities = []
        
        try:
            suppliers = enhanced_analysis.get('suppliers', [])
            waste_impact_scores = enhanced_analysis.get('waste_impact_scores', {})
            
            for supplier in suppliers:
                supplier_id = supplier.get('id')
                if supplier_id and supplier_id in waste_impact_scores:
                    waste_score = waste_impact_scores[supplier_id]
                    
                    if waste_score < 0.8:  # Poor waste performance
                        priority = 'high'
                        potential_savings = supplier.get('total_spend', 0) * 0.15
                        recommendation = f"Consider alternative suppliers for {supplier.get('name')} due to high waste impact"
                    elif waste_score < 0.9:  # Moderate waste performance
                        priority = 'medium'
                        potential_savings = supplier.get('total_spend', 0) * 0.08
                        recommendation = f"Work with {supplier.get('name')} to improve quality and reduce waste"
                    else:
                        continue
                    
                    opportunities.append({
                        'type': 'supplier_optimization',
                        'supplier_id': supplier_id,
                        'supplier_name': supplier.get('name'),
                        'priority': priority,
                        'potential_savings': potential_savings,
                        'recommendation': recommendation,
                        'waste_impact_score': waste_score,
                        'current_spend': supplier.get('total_spend', 0)
                    })
            
            return opportunities
            
        except Exception as e:
            self.logger.error(f"Error finding cost optimization opportunities: {str(e)}")
            return []