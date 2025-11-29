"""
Expiry Tracking Service
Manages expiry date monitoring, alerts, and FIFO inventory rotation
"""

from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Tuple
from sqlalchemy import and_, or_, func
import logging

from app import db
from app.models.inventory import Ingredient, StockAdjustment
from app.models.waste_to_profit import ExpiryTracking, WasteRecord
from app.notifications.service import notification_service


class ExpiryTrackingService:
    """Service for managing expiry tracking and alerts"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def create_expiry_tracking(self, ingredient_id: int, batch_number: str = None, 
                            lot_number: str = None, expiry_date: date = None,
                            quantity: float = 0, unit_cost: float = 0,
                            supplier_id: int = None, storage_location: str = None,
                            storage_conditions: dict = None, user_id: int = None) -> ExpiryTracking:
        """
        Create a new expiry tracking record
        
        Args:
            ingredient_id: ID of the ingredient
            batch_number: Batch number for tracking
            lot_number: Lot number for tracking
            expiry_date: Expiry date of the batch
            quantity: Quantity received
            unit_cost: Cost per unit
            supplier_id: Supplier ID
            storage_location: Storage location
            storage_conditions: Storage conditions (temperature, humidity, etc.)
            user_id: User creating the record
            
        Returns:
            Created ExpiryTracking record
        """
        try:
            expiry_tracking = ExpiryTracking(
                ingredient_id=ingredient_id,
                batch_number=batch_number,
                lot_number=lot_number,
                expiry_date=expiry_date,
                quantity=quantity,
                remaining_quantity=quantity,
                unit_cost=unit_cost,
                supplier_id=supplier_id,
                storage_location=storage_location,
                storage_conditions=storage_conditions or {},
                created_by=user_id
            )
            
            expiry_tracking.update_risk_level()
            
            db.session.add(expiry_tracking)
            db.session.commit()
            
            # Check if immediate alert is needed
            if expiry_tracking.risk_level in ['high', 'critical']:
                self._send_expiry_alert(expiry_tracking)
            
            self.logger.info(f"Created expiry tracking for ingredient {ingredient_id}, batch {batch_number}")
            return expiry_tracking
            
        except Exception as e:
            self.logger.error(f"Error creating expiry tracking: {str(e)}")
            db.session.rollback()
            raise
    
    def update_expiry_quantity(self, expiry_id: int, quantity_used: float, reason: str, user_id: int) -> bool:
        """
        Update remaining quantity for an expiry tracking record
        
        Args:
            expiry_id: ID of the expiry tracking record
            quantity_used: Quantity used (positive number)
            reason: Reason for usage
            user_id: User making the update
            
        Returns:
            True if successful, False otherwise
        """
        try:
            expiry = ExpiryTracking.query.get(expiry_id)
            if not expiry:
                self.logger.error(f"Expiry tracking record {expiry_id} not found")
                return False
            
            if quantity_used > float(expiry.remaining_quantity):
                self.logger.error(f"Cannot use more than remaining quantity for expiry {expiry_id}")
                return False
            
            # Update remaining quantity
            old_quantity = expiry.remaining_quantity
            expiry.remaining_quantity = float(expiry.remaining_quantity) - quantity_used
            expiry.updated_at = datetime.utcnow()
            expiry.update_risk_level()
            
            # Create stock adjustment record
            adjustment = StockAdjustment(
                ingredient_id=expiry.ingredient_id,
                quantity=-quantity_used,
                previous_quantity=old_quantity,
                new_quantity=expiry.remaining_quantity,
                reason=f"FIFO usage - {reason}",
                user_id=user_id
            )
            
            db.session.add(adjustment)
            db.session.commit()
            
            self.logger.info(f"Updated expiry {expiry_id}: used {quantity_used}, remaining {expiry.remaining_quantity}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error updating expiry quantity: {str(e)}")
            db.session.rollback()
            return False
    
    def get_expiring_items(self, days_ahead: int = 7, risk_level: str = None) -> List[ExpiryTracking]:
        """
        Get items expiring within the specified number of days
        
        Args:
            days_ahead: Number of days to look ahead
            risk_level: Filter by risk level (optional)
            
        Returns:
            List of ExpiryTracking records
        """
        try:
            target_date = date.today() + timedelta(days=days_ahead)
            
            query = ExpiryTracking.query.filter(
                and_(
                    ExpiryTracking.expiry_date <= target_date,
                    ExpiryTracking.remaining_quantity > 0
                )
            )
            
            if risk_level:
                query = query.filter(ExpiryTracking.risk_level == risk_level)
            
            return query.order_by(ExpiryTracking.expiry_date).all()
            
        except Exception as e:
            self.logger.error(f"Error getting expiring items: {str(e)}")
            return []
    
    def get_fifo_recommendations(self, ingredient_id: int = None) -> List[Dict]:
        """
        Get FIFO (First In, First Out) recommendations for inventory rotation
        
        Args:
            ingredient_id: Optional ingredient ID to filter by
            
        Returns:
            List of FIFO recommendations
        """
        try:
            query = ExpiryTracking.query.filter(
                and_(
                    ExpiryTracking.remaining_quantity > 0,
                    ExpiryTracking.expiry_date >= date.today()
                )
            )
            
            if ingredient_id:
                query = query.filter(ExpiryTracking.ingredient_id == ingredient_id)
            
            # Order by expiry date (FIFO)
            expiry_records = query.order_by(ExpiryTracking.expiry_date).all()
            
            recommendations = []
            for record in expiry_records:
                days_until_expiry = record.get_days_until_expiry()
                
                recommendation = {
                    'expiry_id': record.id,
                    'ingredient_id': record.ingredient_id,
                    'ingredient_name': record.ingredient.name if record.ingredient else 'Unknown',
                    'batch_number': record.batch_number,
                    'lot_number': record.lot_number,
                    'expiry_date': record.expiry_date.isoformat() if record.expiry_date else None,
                    'days_until_expiry': days_until_expiry,
                    'remaining_quantity': float(record.remaining_quantity),
                    'unit': record.ingredient.unit if record.ingredient else 'units',
                    'risk_level': record.risk_level,
                    'priority': self._calculate_fifo_priority(days_until_expiry, record.risk_level),
                    'recommendation': self._generate_fifo_recommendation(days_until_expiry, record.risk_level)
                }
                
                recommendations.append(recommendation)
            
            return recommendations
            
        except Exception as e:
            self.logger.error(f"Error getting FIFO recommendations: {str(e)}")
            return []
    
    def check_and_send_alerts(self) -> Dict[str, int]:
        """
        Check all expiry tracking records and send alerts for items approaching expiry
        
        Returns:
            Dictionary with alert counts by risk level
        """
        try:
            alert_counts = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0}
            
            # Get all active expiry records
            expiry_records = ExpiryTracking.query.filter(
                ExpiryTracking.remaining_quantity > 0
            ).all()
            
            for record in expiry_records:
                record.update_risk_level()
                
                # Send alert if needed and not already sent
                if record.risk_level in ['high', 'critical'] and not record.alert_sent:
                    self._send_expiry_alert(record)
                    record.alert_sent = True
                    alert_counts[record.risk_level] += 1
            
            db.session.commit()
            
            self.logger.info(f"Expiry alerts sent: {alert_counts}")
            return alert_counts
            
        except Exception as e:
            self.logger.error(f"Error checking expiry alerts: {str(e)}")
            return {'critical': 0, 'high': 0, 'medium': 0, 'low': 0}
    
    def auto_create_waste_records(self) -> int:
        """
        Automatically create waste records for expired items
        
        Returns:
            Number of waste records created
        """
        try:
            waste_count = 0
            
            # Find expired items
            expired_items = ExpiryTracking.query.filter(
                and_(
                    ExpiryTracking.expiry_date < date.today(),
                    ExpiryTracking.remaining_quantity > 0
                )
            ).all()
            
            for item in expired_items:
                # Create waste record
                waste_record = WasteRecord(
                    ingredient_id=item.ingredient_id,
                    expiry_tracking_id=item.id,
                    quantity_wasted=item.remaining_quantity,
                    unit_cost=item.unit_cost,
                    total_cost=float(item.remaining_quantity) * float(item.unit_cost),
                    waste_reason='expiry',
                    waste_category='perishable',
                    department='storage',
                    reported_by=1,  # System user
                    waste_date=date.today()
                )
                
                db.session.add(waste_record)
                
                # Update expiry tracking
                item.remaining_quantity = 0
                item.updated_at = datetime.utcnow()
                
                waste_count += 1
            
            db.session.commit()
            
            self.logger.info(f"Auto-created {waste_count} waste records for expired items")
            return waste_count
            
        except Exception as e:
            self.logger.error(f"Error auto-creating waste records: {str(e)}")
            db.session.rollback()
            return 0
    
    def get_expiry_analytics(self, days_back: int = 30) -> Dict:
        """
        Get expiry analytics and insights
        
        Args:
            days_back: Number of days to analyze
            
        Returns:
            Dictionary with expiry analytics
        """
        try:
            start_date = date.today() - timedelta(days=days_back)
            
            # Get expiry records within period
            expiry_records = ExpiryTracking.query.filter(
                ExpiryTracking.created_at >= start_date
            ).all()
            
            # Get waste records within period
            waste_records = WasteRecord.query.filter(
                and_(
                    WasteRecord.waste_date >= start_date,
                    WasteRecord.waste_reason == 'expiry'
                )
            ).all()
            
            # Calculate analytics
            total_items = len(expiry_records)
            expired_items = len([r for r in expiry_records if r.expiry_date < date.today()])
            expiring_soon = len([r for r in expiry_records if 0 <= r.get_days_until_expiry() <= 7])
            
            total_waste_cost = sum(float(w.total_cost) for w in waste_records)
            total_waste_quantity = sum(float(w.quantity_wasted) for w in waste_records)
            
            # Group by category
            category_analysis = {}
            for record in expiry_records:
                if record.ingredient and record.ingredient.category:
                    category = record.ingredient.category
                    if category not in category_analysis:
                        category_analysis[category] = {
                            'total_items': 0,
                            'expired_items': 0,
                            'waste_cost': 0
                        }
                    
                    category_analysis[category]['total_items'] += 1
                    if record.expiry_date < date.today():
                        category_analysis[category]['expired_items'] += 1
            
            for waste in waste_records:
                if waste.ingredient and waste.ingredient.category:
                    category = waste.ingredient.category
                    if category in category_analysis:
                        category_analysis[category]['waste_cost'] += float(waste.total_cost)
            
            return {
                'period_start': start_date.isoformat(),
                'period_end': date.today().isoformat(),
                'total_items': total_items,
                'expired_items': expired_items,
                'expiring_soon': expiring_soon,
                'expiry_rate': (expired_items / total_items * 100) if total_items > 0 else 0,
                'total_waste_cost': total_waste_cost,
                'total_waste_quantity': total_waste_quantity,
                'category_analysis': category_analysis,
                'risk_distribution': self._get_risk_distribution(expiry_records)
            }
            
        except Exception as e:
            self.logger.error(f"Error getting expiry analytics: {str(e)}")
            return {}
    
    def _send_expiry_alert(self, expiry_record: ExpiryTracking) -> bool:
        """
        Send expiry alert notification
        
        Args:
            expiry_record: ExpiryTracking record to alert for
            
        Returns:
            True if alert sent successfully
        """
        try:
            days_until = expiry_record.get_days_until_expiry()
            
            if days_until is None:
                return False
            
            # Prepare alert message
            if days_until < 0:
                urgency = "URGENT - EXPIRED"
                message = f"Ingredient '{expiry_record.ingredient.name}' has EXPIRED {abs(days_until)} days ago!"
            elif days_until == 0:
                urgency = "URGENT - EXPIRES TODAY"
                message = f"Ingredient '{expiry_record.ingredient.name}' expires TODAY!"
            else:
                urgency = "WARNING - EXPIRING SOON"
                message = f"Ingredient '{expiry_record.ingredient.name}' expires in {days_until} days!"
            
            message += f"\n\nBatch: {expiry_record.batch_number or 'N/A'}"
            message += f"\nQuantity: {expiry_record.remaining_quantity} {expiry_record.ingredient.unit if expiry_record.ingredient else 'units'}"
            message += f"\nLocation: {expiry_record.storage_location or 'N/A'}"
            
            # Send notification through notification service
            try:
                notification_service.send_notification(
                    title=f"Expiry Alert: {urgency}",
                    message=message,
                    notification_type="expiry_alert",
                    priority="high" if expiry_record.risk_level == 'critical' else "medium",
                    data={
                        'expiry_id': expiry_record.id,
                        'ingredient_id': expiry_record.ingredient_id,
                        'risk_level': expiry_record.risk_level
                    }
                )
                return True
            except Exception as e:
                self.logger.error(f"Error sending expiry notification: {str(e)}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error sending expiry alert: {str(e)}")
            return False
    
    def _calculate_fifo_priority(self, days_until_expiry: int, risk_level: str) -> str:
        """Calculate FIFO priority based on days until expiry and risk level"""
        if days_until_expiry is None:
            return 'low'
        
        if days_until_expiry < 0:
            return 'critical'
        elif days_until_expiry <= 3:
            return 'high'
        elif days_until_expiry <= 7:
            return 'medium'
        else:
            return 'low'
    
    def _generate_fifo_recommendation(self, days_until_expiry: int, risk_level: str) -> str:
        """Generate FIFO recommendation based on expiry status"""
        if days_until_expiry is None:
            return "Check expiry date"
        
        if days_until_expiry < 0:
            return "IMMEDIATE ACTION REQUIRED - Item has expired"
        elif days_until_expiry == 0:
            return "USE TODAY - Item expires today"
        elif days_until_expiry <= 3:
            return "USE IMMEDIATELY - Item expires very soon"
        elif days_until_expiry <= 7:
            return "USE THIS WEEK - Item expires soon"
        else:
            return "Use before expiry date"
    
    def _get_risk_distribution(self, expiry_records: List[ExpiryTracking]) -> Dict[str, int]:
        """Get distribution of risk levels"""
        distribution = {'low': 0, 'medium': 0, 'high': 0, 'critical': 0}
        
        for record in expiry_records:
            if record.risk_level in distribution:
                distribution[record.risk_level] += 1
        
        return distribution