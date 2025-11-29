"""
Inventory Reports Service
Handles inventory analytics and waste tracking reports
"""

from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from sqlalchemy import func, and_, or_, desc, asc, extract
from app import db
from app.models.inventory import Ingredient
from app.models.enhanced_reports import (
    InventoryMovement, WasteTracking, ReportCache
)
from app.services.enhanced_reports_service import EnhancedReportsService

class InventoryReportsService:
    """Service for inventory analytics and reporting"""
    
    @staticmethod
    def get_stock_movement_analysis(start_date: datetime, end_date: datetime,
                                restaurant_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get stock movement analysis"""
        cache_key = EnhancedReportsService.generate_cache_key('stock_movement', {
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'restaurant_id': restaurant_id
        })
        
        cache = EnhancedReportsService.get_or_create_cache(cache_key, 'stock_movement', {}, 30)
        if cache and cache.get_cache_data():
            return cache.get_cache_data()
        
        query = db.session.query(
            Ingredient.id,
            Ingredient.name,
            Ingredient.category,
            func.sum(InventoryMovement.quantity).label('total_movement'),
            func.sum(
                func.case(
                    (InventoryMovement.movement_type == 'purchase', InventoryMovement.quantity),
                    else_=0
                )
            ).label('total_in'),
            func.sum(
                func.case(
                    (InventoryMovement.movement_type == 'sale', InventoryMovement.quantity),
                    else_=0
                )
            ).label('total_out'),
            func.sum(InventoryMovement.total_cost).label('total_cost'),
            func.count(InventoryMovement.id).label('transaction_count')
        ).join(
            InventoryMovement, Ingredient.id == InventoryMovement.ingredient_id
        ).filter(
            InventoryMovement.created_at >= start_date,
            InventoryMovement.created_at <= end_date
        )
        
        if restaurant_id:
            query = query.filter(InventoryMovement.restaurant_id == restaurant_id)
        
        results = query.group_by(
            Ingredient.id, Ingredient.name, Ingredient.category
        ).order_by(desc('total_cost')).all()
        
        movement_data = []
        for ingredient_id, name, category, total_movement, total_in, total_out, total_cost, transaction_count in results:
            movement_data.append({
                'ingredient_id': ingredient_id,
                'name': name,
                'category': category,
                'total_movement': float(total_movement or 0),
                'total_in': float(total_in or 0),
                'total_out': float(total_out or 0),
                'total_cost': float(total_cost or 0),
                'transaction_count': transaction_count or 0,
                'net_change': float(total_in or 0) - float(total_out or 0),
                'avg_cost_per_unit': float(total_cost or 0) / (abs(total_movement or 1))
            })
        
        EnhancedReportsService.save_cache_data(cache, movement_data)
        return movement_data
    
    @staticmethod
    def get_waste_spoilage_tracking(start_date: datetime, end_date: datetime,
                                   restaurant_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get waste and spoilage tracking report"""
        cache_key = EnhancedReportsService.generate_cache_key('waste_tracking', {
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'restaurant_id': restaurant_id
        })
        
        cache = EnhancedReportsService.get_or_create_cache(cache_key, 'waste_tracking', {}, 30)
        if cache and cache.get_cache_data():
            return cache.get_cache_data()
        
        query = db.session.query(
            WasteTracking.id,
            WasteTracking.ingredient_id,
            Ingredient.name.label('ingredient_name'),
            Ingredient.category.label('ingredient_category'),
            WasteTracking.waste_type,
            WasteTracking.quantity,
            WasteTracking.unit_cost,
            WasteTracking.total_cost,
            WasteTracking.reason,
            WasteTracking.waste_date,
            WasteTracking.reported_by,
            WasteTracking.approved_by
        ).join(
            Ingredient, WasteTracking.ingredient_id == Ingredient.id
        ).filter(
            WasteTracking.waste_date >= start_date,
            WasteTracking.waste_date <= end_date
        )
        
        if restaurant_id:
            query = query.filter(WasteTracking.restaurant_id == restaurant_id)
        
        results = query.order_by(desc(WasteTracking.waste_date)).all()
        
        waste_data = []
        total_waste_cost = 0
        
        for waste in results:
            waste_info = {
                'id': waste.id,
                'ingredient_id': waste.ingredient_id,
                'ingredient_name': waste.ingredient_name,
                'ingredient_category': waste.ingredient_category,
                'waste_type': waste.waste_type,
                'quantity': float(waste.quantity),
                'unit_cost': float(waste.unit_cost),
                'total_cost': float(waste.total_cost),
                'reason': waste.reason,
                'waste_date': waste.waste_date.strftime('%Y-%m-%d'),
                'reported_by': waste.reported_by,
                'approved_by': waste.approved_by
            }
            waste_data.append(waste_info)
            total_waste_cost += float(waste.total_cost)
        
        # Add summary statistics
        waste_by_type = {}
        waste_by_category = {}
        
        for waste in waste_data:
            # By type
            waste_type = waste['waste_type']
            if waste_type not in waste_by_type:
                waste_by_type[waste_type] = {'count': 0, 'cost': 0}
            waste_by_type[waste_type]['count'] += 1
            waste_by_type[waste_type]['cost'] += waste['total_cost']
            
            # By category
            category = waste['ingredient_category']
            if category not in waste_by_category:
                waste_by_category[category] = {'count': 0, 'cost': 0}
            waste_by_category[category]['count'] += 1
            waste_by_category[category]['cost'] += waste['total_cost']
        
        summary = {
            'total_waste_cost': total_waste_cost,
            'total_waste_items': len(waste_data),
            'waste_by_type': waste_by_type,
            'waste_by_category': waste_by_category
        }
        
        EnhancedReportsService.save_cache_data(cache, {'waste_data': waste_data, 'summary': summary})
        return {'waste_data': waste_data, 'summary': summary}
    
    @staticmethod
    def get_inventory_valuation_report(start_date: datetime, end_date: datetime,
                                   restaurant_id: Optional[int] = None) -> Dict[str, Any]:
        """Get inventory valuation report"""
        cache_key = EnhancedReportsService.generate_cache_key('inventory_valuation', {
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'restaurant_id': restaurant_id
        })
        
        cache = EnhancedReportsService.get_or_create_cache(cache_key, 'inventory_valuation', {}, 60)
        if cache and cache.get_cache_data():
            return cache.get_cache_data()
        
        query = db.session.query(
            Ingredient.id,
            Ingredient.name,
            Ingredient.category,
            Ingredient.current_stock,
            Ingredient.unit_cost,
            Ingredient.minimum_stock,
            (Ingredient.current_stock * Ingredient.unit_cost).label('total_value')
        ).filter(Ingredient.current_stock > 0)
        
        if restaurant_id:
            query = query.filter(Ingredient.restaurant_id == restaurant_id)
        
        results = query.order_by(desc('total_value')).all()
        
        inventory_data = []
        total_value = 0
        total_items = 0
        low_stock_items = 0
        out_of_stock_items = 0
        
        category_summary = {}
        
        for ingredient_id, name, category, current_stock, unit_cost, minimum_stock, total_value in results:
            stock_value = float(total_value)
            stock_level = 'normal'
            
            if current_stock == 0:
                stock_level = 'out_of_stock'
                out_of_stock_items += 1
            elif current_stock <= minimum_stock:
                stock_level = 'low_stock'
                low_stock_items += 1
            
            item_data = {
                'ingredient_id': ingredient_id,
                'name': name,
                'category': category,
                'current_stock': float(current_stock),
                'unit_cost': float(unit_cost),
                'minimum_stock': float(minimum_stock),
                'total_value': stock_value,
                'stock_level': stock_level
            }
            inventory_data.append(item_data)
            
            total_value += stock_value
            total_items += 1
            
            # Category summary
            if category not in category_summary:
                category_summary[category] = {'count': 0, 'value': 0}
            category_summary[category]['count'] += 1
            category_summary[category]['value'] += stock_value
        
        valuation_report = {
            'summary': {
                'total_items': total_items,
                'total_value': total_value,
                'low_stock_items': low_stock_items,
                'out_of_stock_items': out_of_stock_items,
                'avg_value_per_item': total_value / total_items if total_items > 0 else 0
            },
            'category_breakdown': category_summary,
            'inventory_items': inventory_data
        }
        
        EnhancedReportsService.save_cache_data(cache, valuation_report)
        return valuation_report
    
    @staticmethod
    def get_low_stock_alerts(restaurant_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get low stock alerts dashboard"""
        cache_key = EnhancedReportsService.generate_cache_key('low_stock_alerts', {
            'restaurant_id': restaurant_id
        })
        
        cache = EnhancedReportsService.get_or_create_cache(cache_key, 'low_stock_alerts', {}, 15)
        if cache and cache.get_cache_data():
            return cache.get_cache_data()
        
        query = db.session.query(
            Ingredient.id,
            Ingredient.name,
            Ingredient.category,
            Ingredient.current_stock,
            Ingredient.minimum_stock,
            Ingredient.unit,
            (Ingredient.minimum_stock - Ingredient.current_stock).label('shortage'),
            ((Ingredient.minimum_stock - Ingredient.current_stock) * Ingredient.unit_cost).label('shortage_value')
        ).filter(
            Ingredient.current_stock <= Ingredient.minimum_stock,
            Ingredient.current_stock > 0
        )
        
        if restaurant_id:
            query = query.filter(Ingredient.restaurant_id == restaurant_id)
        
        results = query.order_by(desc('shortage_value')).all()
        
        low_stock_data = []
        for ingredient_id, name, category, current_stock, minimum_stock, unit, shortage, shortage_value in results:
            urgency = 'critical' if current_stock == 0 else 'warning'
            
            low_stock_data.append({
                'ingredient_id': ingredient_id,
                'name': name,
                'category': category,
                'current_stock': float(current_stock),
                'minimum_stock': float(minimum_stock),
                'unit': unit,
                'shortage': float(shortage),
                'shortage_value': float(shortage_value),
                'urgency': urgency
            })
        
        EnhancedReportsService.save_cache_data(cache, low_stock_data)
        return low_stock_data
    
    @staticmethod
    def get_expiry_tracking_report(restaurant_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get expiry tracking report"""
        cache_key = EnhancedReportsService.generate_cache_key('expiry_tracking', {
            'restaurant_id': restaurant_id
        })
        
        cache = EnhancedReportsService.get_or_create_cache(cache_key, 'expiry_tracking', {}, 60)
        if cache.get_cache_data():
            return cache.get_cache_data()
        
        # This would need expiry date field in ingredients model
        # For now, return a placeholder structure
        expiry_data = []
        
        EnhancedReportsService.save_cache_data(cache, expiry_data)
        return expiry_data