"""
Customer Communication Hub Service
Handles comprehensive customer communication including:
- Omni-channel communication management
- Automated notifications and alerts
- Customer service chat integration
- Appointment and reservation management
- Loyalty program notifications
- Personalized messaging
"""

from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from sqlalchemy import func, and_, or_, desc
import json
import logging

from app import db
from app.models.customer import Customer
from app.models.customer_engagement import (
    CustomerCommunication, CommunicationTemplate,
    LoyaltyProgram, RewardRedemption
)
from app.models.order import Order
from app.models.user import User


class CustomerCommunicationService:
    """Comprehensive customer communication service"""
    
    @staticmethod
    def send_communication(
        restaurant_id: int,
        customer_id: Optional[int] = None,
        segment_criteria: Optional[Dict] = None,
        message_data: Optional[Dict] = None,
        channel: str = 'email',
        scheduled_for: Optional[datetime] = None,
        created_by: Optional[int] = None
    ) -> Dict[str, Any]:
        """Send communication to customer or customer segment"""
        if not message_data:
            return {'success': False, 'error': 'Message data is required'}
        
        # Determine recipients
        if customer_id:
            recipients = [Customer.query.get(customer_id)]
        elif segment_criteria:
            recipients = CustomerCommunicationService._get_segment_customers(
                restaurant_id, segment_criteria
            )
        else:
            return {'success': False, 'error': 'Either customer_id or segment_criteria is required'}
        
        if not recipients or None in recipients:
            return {'success': False, 'error': 'No valid recipients found'}
        
        # Create communication records
        communications = []
        for recipient in recipients:
            if not recipient:
                continue
                
            # Personalize message
            personalized_message = CustomerCommunicationService._personalize_message(
                message_data, recipient
            )
            
            communication = CustomerCommunication(
                customer_id=recipient.id,
                restaurant_id=restaurant_id,
                channel=channel,
                message_type=message_data.get('type', 'general'),
                subject=message_data.get('subject', ''),
                content=personalized_message.get('content', ''),
                metadata=json.dumps({
                    'template_id': message_data.get('template_id'),
                    'personalization_data': personalized_message.get('personalization_data', {}),
                    'original_message': message_data
                }),
                status='scheduled' if scheduled_for else 'pending',
                scheduled_for=scheduled_for,
                created_by=created_by
            )
            
            db.session.add(communication)
            communications.append(communication)
        
        db.session.commit()
        
        # Process communications immediately if not scheduled
        if not scheduled_for:
            CustomerCommunicationService._process_communications(communications)
        
        return {
            'success': True,
            'communications_sent': len(communications),
            'communication_ids': [c.id for c in communications],
            'recipients': len([r for r in recipients if r])
        }
    
    @staticmethod
    def create_automated_campaign(
        restaurant_id: int,
        campaign_config: Dict,
        created_by: Optional[int] = None
    ) -> Dict[str, Any]:
        """Create automated communication campaign"""
        required_fields = ['name', 'trigger_event', 'message_template']
        for field in required_fields:
            if field not in campaign_config:
                return {'success': False, 'error': f'Missing required field: {field}'}
        
        # Create campaign configuration
        campaign = {
            'name': campaign_config['name'],
            'description': campaign_config.get('description', ''),
            'trigger_event': campaign_config['trigger_event'],
            'message_template': campaign_config['message_template'],
            'channel': campaign_config.get('channel', 'email'),
            'segment_criteria': campaign_config.get('segment_criteria', {}),
            'schedule_config': campaign_config.get('schedule_config', {}),
            'conditions': campaign_config.get('conditions', {}),
            'is_active': campaign_config.get('is_active', True),
            'created_by': created_by,
            'created_at': datetime.now().isoformat()
        }
        
        # Store campaign configuration (could be moved to a dedicated table)
        # For now, store as a communication template
        template = CommunicationTemplate(
            restaurant_id=restaurant_id,
            name=campaign['name'],
            template_type='automated_campaign',
            channel=campaign['channel'],
            subject_template=campaign['message_template'].get('subject', ''),
            content_template=campaign['message_template'].get('content', ''),
            metadata=json.dumps(campaign),
            is_active=campaign['is_active'],
            created_by=created_by
        )
        
        db.session.add(template)
        db.session.commit()
        
        return {
            'success': True,
            'campaign_id': template.id,
            'campaign': campaign
        }
    
    @staticmethod
    def process_loyalty_notifications(restaurant_id: int) -> Dict[str, Any]:
        """Process loyalty program notifications"""
        notifications_sent = 0
        
        # Get active loyalty program
        loyalty_program = LoyaltyProgram.query.filter_by(
            restaurant_id=restaurant_id,
            is_active=True
        ).first()
        
        if not loyalty_program:
            return {'success': False, 'error': 'No active loyalty program found'}
        
        # Process different types of loyalty notifications
        
        # 1. Points earned notifications
        recent_orders = Order.query.filter(
            Order.restaurant_id == restaurant_id,
            Order.status.in_(['served', 'completed']),
            Order.created_at >= datetime.now() - timedelta(hours=24)
        ).all()
        
        for order in recent_orders:
            if order.customer_id:
                # Check if points already notified for this order
                existing_notification = CustomerCommunication.query.filter_by(
                    customer_id=order.customer_id,
                    message_type='loyalty_points_earned',
                    metadata=json.dumps({'order_id': order.id}).replace('"', "'")
                ).first()
                
                if not existing_notification:
                    # Calculate points earned
                    points_earned = int(order.total * loyalty_program.points_per_currency)
                    
                    if points_earned > 0:
                        message_data = {
                            'type': 'loyalty_points_earned',
                            'subject': f'You earned {points_earned} points!',
                            'content': f'Great news! You earned {points_earned} loyalty points from your recent order. Your current balance is {order.customer.loyalty_points or 0} points.',
                            'template_id': 'loyalty_points_earned'
                        }
                        
                        result = CustomerCommunicationService.send_communication(
                            restaurant_id=restaurant_id,
                            customer_id=order.customer_id,
                            message_data=message_data,
                            channel='email'
                        )
                        
                        if result['success']:
                            notifications_sent += 1
        
        # 2. Tier upgrade notifications
        customers = Customer.query.filter_by(
            restaurant_id=restaurant_id,
            loyalty_member=True
        ).all()
        
        for customer in customers:
            # Check if customer qualifies for tier upgrade
            current_tier = customer.loyalty_tier or 'bronze'
            new_tier = CustomerCommunicationService._check_tier_upgrade(customer, loyalty_program)
            
            if new_tier and new_tier != current_tier:
                # Check if upgrade already notified
                existing_notification = CustomerCommunication.query.filter_by(
                    customer_id=customer.id,
                    message_type='loyalty_tier_upgrade',
                    metadata=json.dumps({'new_tier': new_tier}).replace('"', "'")
                ).first()
                
                if not existing_notification:
                    message_data = {
                        'type': 'loyalty_tier_upgrade',
                        'subject': f'Congratulations! You are now {new_tier.title()}!',
                        'content': f'Amazing! You have been upgraded to {new_tier.title()} tier. Enjoy exclusive benefits and rewards!',
                        'template_id': 'loyalty_tier_upgrade'
                    }
                    
                    result = CustomerCommunicationService.send_communication(
                        restaurant_id=restaurant_id,
                        customer_id=customer.id,
                        message_data=message_data,
                        channel='email'
                    )
                    
                    if result['success']:
                        notifications_sent += 1
        
        # 3. Points expiry reminders
        expiry_threshold_days = 30  # Notify 30 days before expiry
        expiry_date = datetime.now() + timedelta(days=expiry_threshold_days)
        
        customers_with_expiring_points = Customer.query.filter(
            Customer.restaurant_id == restaurant_id,
            Customer.loyalty_member == True,
            Customer.loyalty_points_expiry <= expiry_date,
            Customer.loyalty_points_expiry > datetime.now()
        ).all()
        
        for customer in customers_with_expiring_points:
            # Check if reminder already sent
            existing_notification = CustomerCommunication.query.filter_by(
                customer_id=customer.id,
                message_type='loyalty_points_expiry',
                metadata=json.dumps({'expiry_date': customer.loyalty_points_expiry.isoformat()}).replace('"', "'")
            ).first()
            
            if not existing_notification:
                days_until_expiry = (customer.loyalty_points_expiry - datetime.now()).days
                message_data = {
                    'type': 'loyalty_points_expiry',
                    'subject': f'Your points expire in {days_until_expiry} days!',
                    'content': f'You have {customer.loyalty_points} points that will expire in {days_until_expiry} days. Use them before they expire!',
                    'template_id': 'loyalty_points_expiry'
                }
                
                result = CustomerCommunicationService.send_communication(
                    restaurant_id=restaurant_id,
                    customer_id=customer.id,
                    message_data=message_data,
                    channel='email'
                )
                
                if result['success']:
                    notifications_sent += 1
        
        return {
            'success': True,
            'notifications_sent': notifications_sent,
            'processed_orders': len(recent_orders),
            'processed_customers': len(customers)
        }
    
    @staticmethod
    def get_communication_history(
        restaurant_id: int,
        customer_id: Optional[int] = None,
        limit: int = 50
    ) -> Dict[str, Any]:
        """Get communication history"""
        query = CustomerCommunication.query.filter_by(restaurant_id=restaurant_id)
        
        if customer_id:
            query = query.filter_by(customer_id=customer_id)
        
        communications = query.order_by(
            CustomerCommunication.created_at.desc()
        ).limit(limit).all()
        
        return {
            'communications': [
                {
                    'id': comm.id,
                    'customer_id': comm.customer_id,
                    'customer_name': comm.customer.get_full_name() if comm.customer else 'Unknown',
                    'channel': comm.channel,
                    'message_type': comm.message_type,
                    'subject': comm.subject,
                    'content_preview': comm.content[:100] + '...' if len(comm.content) > 100 else comm.content,
                    'status': comm.status,
                    'sent_at': comm.sent_at.isoformat() if comm.sent_at else None,
                    'created_at': comm.created_at.isoformat(),
                    'metadata': json.loads(comm.metadata) if comm.metadata else {}
                }
                for comm in communications
            ],
            'total_count': len(communications)
        }
    
    @staticmethod
    def get_communication_templates(restaurant_id: int) -> List[Dict]:
        """Get available communication templates"""
        templates = CommunicationTemplate.query.filter_by(
            restaurant_id=restaurant_id,
            is_active=True
        ).all()
        
        return [
            {
                'id': template.id,
                'name': template.name,
                'template_type': template.template_type,
                'channel': template.channel,
                'subject_template': template.subject_template,
                'content_template': template.content_template,
                'metadata': json.loads(template.metadata) if template.metadata else {},
                'created_at': template.created_at.isoformat()
            }
            for template in templates
        ]
    
    @staticmethod
    def create_communication_template(
        restaurant_id: int,
        template_data: Dict,
        created_by: Optional[int] = None
    ) -> Dict[str, Any]:
        """Create new communication template"""
        required_fields = ['name', 'template_type', 'channel', 'content_template']
        for field in required_fields:
            if field not in template_data:
                return {'success': False, 'error': f'Missing required field: {field}'}
        
        template = CommunicationTemplate(
            restaurant_id=restaurant_id,
            name=template_data['name'],
            template_type=template_data['template_type'],
            channel=template_data['channel'],
            subject_template=template_data.get('subject_template', ''),
            content_template=template_data['content_template'],
            metadata=json.dumps(template_data.get('metadata', {})),
            is_active=template_data.get('is_active', True),
            created_by=created_by
        )
        
        db.session.add(template)
        db.session.commit()
        
        return {
            'success': True,
            'template_id': template.id,
            'template': {
                'id': template.id,
                'name': template.name,
                'template_type': template.template_type,
                'channel': template.channel
            }
        }
    
    @staticmethod
    def get_communication_analytics(restaurant_id: int, days: int = 30) -> Dict[str, Any]:
        """Get communication analytics and performance metrics"""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # Get communication statistics
        communications = CustomerCommunication.query.filter(
            CustomerCommunication.restaurant_id == restaurant_id,
            CustomerCommunication.created_at >= cutoff_date
        ).all()
        
        # Calculate metrics
        total_sent = len(communications)
        total_delivered = len([c for c in communications if c.status == 'delivered'])
        total_failed = len([c for c in communications if c.status == 'failed'])
        total_opened = len([c for c in communications if c.metadata and 'opened_at' in json.loads(c.metadata)])
        total_clicked = len([c for c in communications if c.metadata and 'clicked_at' in json.loads(c.metadata)])
        
        # Channel breakdown
        channel_stats = {}
        for comm in communications:
            channel = comm.channel
            if channel not in channel_stats:
                channel_stats[channel] = {'sent': 0, 'delivered': 0, 'opened': 0, 'clicked': 0}
            
            channel_stats[channel]['sent'] += 1
            if comm.status == 'delivered':
                channel_stats[channel]['delivered'] += 1
            if comm.metadata and 'opened_at' in json.loads(comm.metadata):
                channel_stats[channel]['opened'] += 1
            if comm.metadata and 'clicked_at' in json.loads(comm.metadata):
                channel_stats[channel]['clicked'] += 1
        
        # Message type breakdown
        message_type_stats = {}
        for comm in communications:
            msg_type = comm.message_type
            if msg_type not in message_type_stats:
                message_type_stats[msg_type] = 0
            message_type_stats[msg_type] += 1
        
        # Calculate rates
        delivery_rate = (total_delivered / total_sent * 100) if total_sent > 0 else 0
        open_rate = (total_opened / total_delivered * 100) if total_delivered > 0 else 0
        click_rate = (total_clicked / total_delivered * 100) if total_delivered > 0 else 0
        
        return {
            'period_days': days,
            'total_sent': total_sent,
            'total_delivered': total_delivered,
            'total_failed': total_failed,
            'total_opened': total_opened,
            'total_clicked': total_clicked,
            'rates': {
                'delivery_rate': round(delivery_rate, 2),
                'open_rate': round(open_rate, 2),
                'click_rate': round(click_rate, 2),
                'failure_rate': round((total_failed / total_sent * 100) if total_sent > 0 else 0, 2)
            },
            'channel_breakdown': channel_stats,
            'message_type_breakdown': message_type_stats,
            'daily_stats': CustomerCommunicationService._get_daily_communication_stats(restaurant_id, days)
        }
    
    # Helper methods
    @staticmethod
    def _get_segment_customers(restaurant_id: int, criteria: Dict) -> List[Customer]:
        """Get customers matching segment criteria"""
        query = Customer.query.filter_by(restaurant_id=restaurant_id, is_active=True)
        
        # Apply various criteria
        if 'loyalty_tier' in criteria:
            query = query.filter(Customer.loyalty_tier.in_(criteria['loyalty_tier']))
        
        if 'min_orders' in criteria:
            query = query.filter(Customer.total_orders >= criteria['min_orders'])
        
        if 'max_orders' in criteria:
            query = query.filter(Customer.total_orders <= criteria['max_orders'])
        
        if 'min_spent' in criteria:
            query = query.filter(Customer.total_spent >= criteria['min_spent'])
        
        if 'max_spent' in criteria:
            query = query.filter(Customer.total_spent <= criteria['max_spent'])
        
        if 'days_since_last_order' in criteria:
            cutoff_date = datetime.now() - timedelta(days=criteria['days_since_last_order'])
            query = query.filter(Customer.last_order_date <= cutoff_date)
        
        if 'created_after' in criteria:
            query = query.filter(Customer.created_at >= criteria['created_after'])
        
        if 'created_before' in criteria:
            query = query.filter(Customer.created_at <= criteria['created_before'])
        
        return query.all()
    
    @staticmethod
    def _personalize_message(message_data: Dict, customer: Customer) -> Dict[str, Any]:
        """Personalize message for customer"""
        content = message_data.get('content', '')
        subject = message_data.get('subject', '')
        
        # Personalization variables
        personalization_vars = {
            'customer_name': customer.get_full_name(),
            'first_name': customer.first_name,
            'last_name': customer.last_name,
            'email': customer.email,
            'phone': customer.phone,
            'loyalty_points': customer.loyalty_points or 0,
            'loyalty_tier': (customer.loyalty_tier or 'bronze').title(),
            'total_orders': customer.total_orders,
            'total_spent': f"${customer.total_spent:.2f}" if customer.total_spent else "$0.00",
            'last_order_date': customer.last_order_date.strftime('%B %d, %Y') if customer.last_order_date else 'Never'
        }
        
        # Replace placeholders
        personalized_content = content
        personalized_subject = subject
        
        for var, value in personalization_vars.items():
            placeholder = f"{{{var}}}"
            personalized_content = personalized_content.replace(placeholder, str(value))
            personalized_subject = personalized_subject.replace(placeholder, str(value))
        
        return {
            'content': personalized_content,
            'subject': personalized_subject,
            'personalization_data': personalization_vars
        }
    
    @staticmethod
    def _process_communications(communications: List[CustomerCommunication]) -> None:
        """Process communications (send them)"""
        for comm in communications:
            try:
                # This would integrate with actual email/SMS services
                # For now, simulate sending
                comm.status = 'sent'
                comm.sent_at = datetime.now()
                
                # Update metadata with tracking info
                metadata = json.loads(comm.metadata) if comm.metadata else {}
                metadata['sent_at'] = comm.sent_at.isoformat()
                metadata['delivery_method'] = comm.channel
                comm.metadata = json.dumps(metadata)
                
            except Exception as e:
                logging.error(f"Failed to send communication {comm.id}: {str(e)}")
                comm.status = 'failed'
                metadata = json.loads(comm.metadata) if comm.metadata else {}
                metadata['error'] = str(e)
                comm.metadata = json.dumps(metadata)
        
        db.session.commit()
    
    @staticmethod
    def _check_tier_upgrade(customer: Customer, loyalty_program: LoyaltyProgram) -> Optional[str]:
        """Check if customer qualifies for tier upgrade"""
        if not loyalty_program or not customer.loyalty_member:
            return None
        
        tiers_config = json.loads(loyalty_program.tiers_config) if loyalty_program.tiers_config else {}
        current_tier = customer.loyalty_tier or 'bronze'
        
        # Check each tier from highest to lowest
        tier_hierarchy = ['platinum', 'gold', 'silver', 'bronze']
        current_tier_index = tier_hierarchy.index(current_tier) if current_tier in tier_hierarchy else 3
        
        # Check higher tiers
        for i in range(current_tier_index - 1, -1, -1):
            tier_name = tier_hierarchy[i]
            tier_config = tiers_config.get(tier_name, {})
            
            # Check qualification criteria
            min_orders = tier_config.get('min_orders', 0)
            min_spent = tier_config.get('min_spent', 0)
            min_points = tier_config.get('min_points', 0)
            
            if (customer.total_orders >= min_orders and 
                (customer.total_spent or 0) >= min_spent and 
                (customer.loyalty_points or 0) >= min_points):
                return tier_name
        
        return None
    
    @staticmethod
    def _get_daily_communication_stats(restaurant_id: int, days: int) -> List[Dict]:
        """Get daily communication statistics"""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # Query daily stats
        daily_stats = db.session.query(
            func.date(CustomerCommunication.created_at).label('date'),
            func.count(CustomerCommunication.id).label('total_sent'),
            func.sum(func.case([(CustomerCommunication.status == 'delivered', 1)], else_=0)).label('total_delivered'),
            func.sum(func.case([(CustomerCommunication.status == 'failed', 1)], else_=0)).label('total_failed')
        ).filter(
            CustomerCommunication.restaurant_id == restaurant_id,
            CustomerCommunication.created_at >= cutoff_date
        ).group_by(
            func.date(CustomerCommunication.created_at)
        ).order_by('date').all()
        
        return [
            {
                'date': stat.date.isoformat(),
                'total_sent': stat.total_sent,
                'total_delivered': stat.total_delivered or 0,
                'total_failed': stat.total_failed or 0,
                'delivery_rate': round((stat.total_delivered / stat.total_sent * 100) if stat.total_sent > 0 else 0, 2)
            }
            for stat in daily_stats
        ]
    
    @staticmethod
    def handle_customer_response(
        communication_id: int,
        response_data: Dict
    ) -> Dict[str, Any]:
        """Handle customer response to communication"""
        communication = CustomerCommunication.query.get(communication_id)
        if not communication:
            return {'success': False, 'error': 'Communication not found'}
        
        # Update communication metadata with response
        metadata = json.loads(communication.metadata) if communication.metadata else {}
        metadata.update({
            'customer_response': response_data,
            'responded_at': datetime.now().isoformat()
        })
        communication.metadata = json.dumps(metadata)
        
        # Process response based on type
        response_type = response_data.get('type', 'general')
        
        if response_type == 'unsubscribe':
            # Handle unsubscribe request
            CustomerCommunicationService._handle_unsubscribe(communication.customer_id, response_data)
        elif response_type == 'opt_in':
            # Handle opt-in request
            CustomerCommunicationService._handle_opt_in(communication.customer_id, response_data)
        elif response_type == 'feedback':
            # Handle feedback response
            CustomerCommunicationService._handle_feedback_response(communication.customer_id, response_data)
        
        db.session.commit()
        
        return {
            'success': True,
            'response_type': response_type,
            'processed': True
        }
    
    @staticmethod
    def _handle_unsubscribe(customer_id: int, response_data: Dict) -> None:
        """Handle unsubscribe request"""
        # Update customer preferences
        customer = Customer.query.get(customer_id)
        if customer:
            # This would update customer communication preferences
            # For now, just log the unsubscribe
            pass
    
    @staticmethod
    def _handle_opt_in(customer_id: int, response_data: Dict) -> None:
        """Handle opt-in request"""
        # Update customer preferences
        customer = Customer.query.get(customer_id)
        if customer:
            # This would update customer communication preferences
            # For now, just log the opt-in
            pass
    
    @staticmethod
    def _handle_feedback_response(customer_id: int, response_data: Dict) -> None:
        """Handle feedback response"""
        # Process customer feedback
        # This could integrate with the feedback system
        pass