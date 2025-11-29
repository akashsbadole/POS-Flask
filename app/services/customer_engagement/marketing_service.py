"""
Marketing Automation Service
Handles comprehensive marketing automation including:
- Automated email campaigns
- SMS/WhatsApp marketing integration
- Personalized offer generation
- Customer segmentation for targeted marketing
- Campaign performance tracking
- A/B testing for marketing messages
"""

from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from sqlalchemy import func, and_, or_, desc
import json
import uuid

from app import db
from app.models.customer import Customer
from app.models.user import User
from app.models.customer_engagement import (
    MarketingCampaign, CampaignMessage, CustomerCommunication,
    CommunicationTemplate, CustomerPreference
)
from app.models.order import Order


class MarketingService:
    """Advanced marketing automation service"""
    
    @staticmethod
    def create_campaign(restaurant_id: int, campaign_data: dict, created_by: Optional[int] = None) -> MarketingCampaign:
        """Create new marketing campaign"""
        campaign = MarketingCampaign(
            restaurant_id=restaurant_id,
            name=campaign_data.get('name'),
            description=campaign_data.get('description'),
            campaign_type=campaign_data.get('campaign_type'),
            target_audience=json.dumps(campaign_data.get('target_audience', {})),
            message_template=campaign_data.get('message_template'),
            subject_template=campaign_data.get('subject_template'),
            schedule_type=campaign_data.get('schedule_type', 'immediate'),
            scheduled_at=campaign_data.get('scheduled_at'),
            recurring_pattern=json.dumps(campaign_data.get('recurring_pattern', {})),
            trigger_conditions=json.dumps(campaign_data.get('trigger_conditions', {})),
            is_ab_test=campaign_data.get('is_ab_test', False),
            variant_a_template=campaign_data.get('variant_a_template'),
            variant_b_template=campaign_data.get('variant_b_template'),
            test_percentage=campaign_data.get('test_percentage', 50.0),
            created_by=created_by,
            status='draft'
        )
        
        db.session.add(campaign)
        db.session.commit()
        
        return campaign
    
    @staticmethod
    def get_target_customers(campaign: MarketingCampaign) -> List[Customer]:
        """Get customers matching campaign target audience"""
        target_audience = campaign.get_target_audience()
        
        # Start with all active customers
        query = Customer.query.filter_by(
            restaurant_id=campaign.restaurant_id,
            is_active=True,
            marketing_consent=True
        )
        
        # Apply segmentation filters
        if 'loyalty_tiers' in target_audience:
            tiers = target_audience['loyalty_tiers']
            if tiers:
                query = query.filter(Customer.loyalty_tier.in_(tiers))
        
        if 'spending_range' in target_audience:
            spending_range = target_audience['spending_range']
            if 'min' in spending_range:
                query = query.filter(Customer.total_spent >= spending_range['min'])
            if 'max' in spending_range:
                query = query.filter(Customer.total_spent <= spending_range['max'])
        
        if 'order_count_range' in target_audience:
            order_range = target_audience['order_count_range']
            if 'min' in order_range:
                query = query.filter(Customer.total_orders >= order_range['min'])
            if 'max' in order_range:
                query = query.filter(Customer.total_orders <= order_range['max'])
        
        if 'last_order_days' in target_audience:
            days = target_audience['last_order_days']
            cutoff_date = datetime.now() - timedelta(days=days)
            query = query.filter(Customer.last_order_date >= cutoff_date)
        
        if 'customer_since' in target_audience:
            since_data = target_audience['customer_since']
            if 'days' in since_data:
                cutoff_date = datetime.now() - timedelta(days=since_data['days'])
                query = query.filter(Customer.created_at >= cutoff_date)
        
        if 'preferences' in target_audience:
            preferences = target_audience['preferences']
            for pref_type, pref_values in preferences.items():
                # This would need to query CustomerPreference table
                pass
        
        if 'locations' in target_audience:
            locations = target_audience['locations']
            if locations:
                location_conditions = []
                for location in locations:
                    location_conditions.extend([
                        Customer.city.ilike(f'%{location}%'),
                        Customer.state.ilike(f'%{location}%'),
                        Customer.postal_code.ilike(f'%{location}%')
                    ])
                if location_conditions:
                    query = query.filter(or_(*location_conditions))
        
        return query.all()
    
    @staticmethod
    def launch_campaign(campaign_id: int) -> Tuple[bool, str]:
        """Launch marketing campaign"""
        campaign = MarketingCampaign.query.get(campaign_id)
        if not campaign:
            return False, "Campaign not found"
        
        if campaign.status != 'draft':
            return False, "Campaign already launched"
        
        # Get target customers
        customers = MarketingService.get_target_customers(campaign)
        
        if not customers:
            return False, "No customers match target audience"
        
        # Update campaign status
        campaign.status = 'active'
        campaign.sent_count = len(customers)
        db.session.commit()
        
        # Create campaign messages
        for customer in customers:
            MarketingService.create_campaign_message(campaign, customer)
        
        # Schedule immediate sending if needed
        if campaign.schedule_type == 'immediate':
            MarketingService.send_campaign_messages(campaign_id)
        
        return True, f"Campaign launched to {len(customers)} customers"
    
    @staticmethod
    def create_campaign_message(campaign: MarketingCampaign, customer: Customer) -> CampaignMessage:
        """Create individual campaign message for customer"""
        # Determine message variant for A/B testing
        if campaign.is_ab_test:
            import random
            use_variant_a = random.random() < (campaign.test_percentage / 100)
            variant = 'variant_a' if use_variant_a else 'variant_b'
            message_content = campaign.variant_a_template if use_variant_a else campaign.variant_b_template
        else:
            variant = 'control'
            message_content = campaign.message_template
        
        # Personalize message content
        personalized_content = MarketingService.personalize_message(
            message_content, customer, campaign
        )
        
        # Personalize subject if email
        subject = None
        if campaign.campaign_type in ['email', 'whatsapp'] and campaign.subject_template:
            subject = MarketingService.personalize_message(
                campaign.subject_template, customer, campaign
            )
        
        message = CampaignMessage(
            campaign_id=campaign.id,
            customer_id=customer.id,
            recipient=MarketingService.get_recipient_address(customer, campaign.campaign_type),
            subject=subject,
            content=personalized_content,
            variant=variant,
            status='pending'
        )
        
        db.session.add(message)
        return message
    
    @staticmethod
    def personalize_message(template: str, customer: Customer, campaign: Optional[MarketingCampaign] = None) -> str:
        """Personalize message template with customer data"""
        # Get customer preferences for better personalization
        preferences = MarketingService.get_customer_preferences(customer.id)
        
        # Basic personalization variables
        personalization_vars = {
            'customer_name': customer.get_full_name(),
            'first_name': customer.first_name,
            'last_name': customer.last_name,
            'customer_email': customer.email or '',
            'customer_phone': customer.phone or '',
            'customer_code': customer.customer_code,
            'loyalty_points': customer.loyalty_points,
            'loyalty_tier': customer.loyalty_tier or 'None',
            'total_orders': customer.total_orders,
            'total_spent': f"${float(customer.total_spent):.2f}",
            'avg_order_value': f"${float(customer.average_order_value):.2f}",
            'last_order_date': customer.last_order_date.strftime('%Y-%m-%d') if customer.last_order_date else 'Never',
            'customer_since': customer.created_at.strftime('%Y-%m-%d') if customer.created_at else '',
            'restaurant_name': campaign.restaurant.name if campaign and campaign.restaurant else 'Our Restaurant',
            'current_date': datetime.now().strftime('%Y-%m-%d'),
            'current_year': datetime.now().year
        }
        
        # Add preference-based personalization
        if 'dietary' in preferences:
            personalization_vars['dietary_preferences'] = ', '.join(preferences['dietary'])
        
        if 'cuisine' in preferences:
            personalization_vars['cuisine_preferences'] = ', '.join(preferences['cuisine'])
        
        # Add loyalty tier benefits
        if customer.loyalty_tier and campaign:
            from app.services.customer_engagement.loyalty_service import LoyaltyService
            tier = LoyaltyService.get_customer_tier(customer.id)
            if tier:
                benefits = tier.get_additional_benefits()
                personalization_vars['tier_benefits'] = ', '.join(benefits)
                personalization_vars['tier_discount'] = f"{tier.discount_percentage}%"
        
        # Replace variables in template
        personalized = template
        for var, value in personalization_vars.items():
            personalized = personalized.replace(f'{{{var}}}', str(value))
        
        return personalized
    
    @staticmethod
    def get_recipient_address(customer: Customer, campaign_type: str) -> str:
        """Get recipient address based on campaign type"""
        if campaign_type == 'email':
            return customer.email or ''
        elif campaign_type == 'sms':
            return customer.phone or ''
        elif campaign_type == 'whatsapp':
            return customer.phone or ''
        elif campaign_type == 'push':
            # Would need device token from customer integrations
            return ''
        else:
            return ''
    
    @staticmethod
    def get_customer_preferences(customer_id: int) -> Dict[str, List[str]]:
        """Get customer preferences for personalization"""
        preferences = CustomerPreference.query.filter_by(customer_id=customer_id).all()
        
        pref_dict = {}
        for pref in preferences:
            if pref.preference_type not in pref_dict:
                pref_dict[pref.preference_type] = []
            pref_dict[pref.preference_type].append(pref.preference_value)
        
        return pref_dict
    
    @staticmethod
    def send_campaign_messages(campaign_id: int, limit: Optional[int] = None) -> Tuple[int, str]:
        """Send pending campaign messages"""
        campaign = MarketingCampaign.query.get(campaign_id)
        if not campaign:
            return 0, "Campaign not found"
        
        # Get pending messages
        query = CampaignMessage.query.filter_by(
            campaign_id=campaign_id,
            status='pending'
        )
        
        if limit:
            query = query.limit(limit)
        
        messages = query.all()
        
        sent_count = 0
        errors = []
        
        for message in messages:
            try:
                success = MarketingService.send_single_message(message)
                if success:
                    sent_count += 1
                else:
                    errors.append(f"Failed to send to {message.recipient}")
            except Exception as e:
                errors.append(f"Error sending to {message.recipient}: {str(e)}")
        
        # Update campaign statistics
        if sent_count > 0:
            campaign.delivered_count += sent_count
            db.session.commit()
        
        error_message = f"Sent {sent_count} messages"
        if errors:
            error_message += f". Errors: {'; '.join(errors[:5])}"  # Limit error details
        
        return sent_count, error_message
    
    @staticmethod
    def send_single_message(message: CampaignMessage) -> bool:
        """Send single campaign message"""
        # This would integrate with actual email/SMS/WhatsApp services
        # For now, simulate sending
        
        try:
            if message.campaign.campaign_type == 'email':
                # Integrate with email service (SendGrid, AWS SES, etc.)
                success = MarketingService.send_email(message)
            elif message.campaign.campaign_type == 'sms':
                # Integrate with SMS service (Twilio, AWS SNS, etc.)
                success = MarketingService.send_sms(message)
            elif message.campaign.campaign_type == 'whatsapp':
                # Integrate with WhatsApp service (Twilio WhatsApp, etc.)
                success = MarketingService.send_whatsapp(message)
            else:
                success = False
            
            # Update message status
            if success:
                message.status = 'sent'
                message.sent_at = datetime.utcnow()
                # Simulate delivery for demo
                message.status = 'delivered'
                message.delivered_at = datetime.utcnow()
            else:
                message.status = 'failed'
            
            db.session.commit()
            return success
            
        except Exception as e:
            message.status = 'failed'
            db.session.commit()
            return False
    
    @staticmethod
    def send_email(message: CampaignMessage) -> bool:
        """Send email message"""
        # This would integrate with actual email service
        # For now, simulate success
        print(f"Sending email to {message.recipient}: {message.subject}")
        print(f"Content: {message.content[:100]}...")
        return True
    
    @staticmethod
    def send_sms(message: CampaignMessage) -> bool:
        """Send SMS message"""
        # This would integrate with actual SMS service
        # For now, simulate success
        print(f"Sending SMS to {message.recipient}")
        print(f"Content: {message.content[:100]}...")
        return True
    
    @staticmethod
    def send_whatsapp(message: CampaignMessage) -> bool:
        """Send WhatsApp message"""
        # This would integrate with actual WhatsApp service
        # For now, simulate success
        print(f"Sending WhatsApp to {message.recipient}")
        print(f"Content: {message.content[:100]}...")
        return True
    
    @staticmethod
    def track_campaign_performance(campaign_id: int) -> Dict[str, Any]:
        """Track and analyze campaign performance"""
        campaign = MarketingCampaign.query.get(campaign_id)
        if not campaign:
            return {}
        
        # Get message statistics
        messages = CampaignMessage.query.filter_by(campaign_id=campaign_id).all()
        
        total_sent = len([m for m in messages if m.status == 'sent'])
        total_delivered = len([m for m in messages if m.status == 'delivered'])
        total_opened = len([m for m in messages if m.status == 'opened'])
        total_clicked = len([m for m in messages if m.status == 'clicked'])
        total_converted = len([m for m in messages if m.status == 'clicked'])  # Simplified
        
        # Calculate rates
        delivery_rate = (total_delivered / total_sent * 100) if total_sent > 0 else 0
        open_rate = (total_opened / total_delivered * 100) if total_delivered > 0 else 0
        click_rate = (total_clicked / total_opened * 100) if total_opened > 0 else 0
        conversion_rate = (total_converted / total_clicked * 100) if total_clicked > 0 else 0
        
        # A/B test performance
        ab_performance = {}
        if campaign.is_ab_test:
            variant_a_messages = [m for m in messages if m.variant == 'variant_a']
            variant_b_messages = [m for m in messages if m.variant == 'variant_b']
            
            ab_performance = {
                'variant_a': {
                    'sent': len(variant_a_messages),
                    'opened': len([m for m in variant_a_messages if m.status == 'opened']),
                    'clicked': len([m for m in variant_a_messages if m.status == 'clicked'])
                },
                'variant_b': {
                    'sent': len(variant_b_messages),
                    'opened': len([m for m in variant_b_messages if m.status == 'opened']),
                    'clicked': len([m for m in variant_b_messages if m.status == 'clicked'])
                }
            }
        
        return {
            'campaign': {
                'id': campaign.id,
                'name': campaign.name,
                'type': campaign.campaign_type,
                'status': campaign.status
            },
            'performance': {
                'total_sent': total_sent,
                'total_delivered': total_delivered,
                'total_opened': total_opened,
                'total_clicked': total_clicked,
                'total_converted': total_converted,
                'delivery_rate': round(delivery_rate, 2),
                'open_rate': round(open_rate, 2),
                'click_rate': round(click_rate, 2),
                'conversion_rate': round(conversion_rate, 2)
            },
            'ab_test_performance': ab_performance
        }
    
    @staticmethod
    def create_automated_campaigns(restaurant_id: int) -> List[MarketingCampaign]:
        """Create automated trigger-based campaigns"""
        automated_campaigns = []
        
        # Birthday campaign
        birthday_campaign = MarketingService.create_birthday_campaign(restaurant_id)
        if birthday_campaign:
            automated_campaigns.append(birthday_campaign)
        
        # Welcome campaign for new customers
        welcome_campaign = MarketingService.create_welcome_campaign(restaurant_id)
        if welcome_campaign:
            automated_campaigns.append(welcome_campaign)
        
        # Re-engagement campaign for inactive customers
        reengagement_campaign = MarketingService.create_reengagement_campaign(restaurant_id)
        if reengagement_campaign:
            automated_campaigns.append(reengagement_campaign)
        
        # VIP campaign for high-value customers
        vip_campaign = MarketingService.create_vip_campaign(restaurant_id)
        if vip_campaign:
            automated_campaigns.append(vip_campaign)
        
        return automated_campaigns
    
    @staticmethod
    def create_birthday_campaign(restaurant_id: int) -> Optional[MarketingCampaign]:
        """Create automated birthday campaign"""
        campaign_data = {
            'name': 'Birthday Special',
            'description': 'Automated birthday wishes and special offers',
            'campaign_type': 'email',
            'schedule_type': 'triggered',
            'target_audience': {
                'preferences': {
                    'occasion': ['birthday']
                }
            },
            'trigger_conditions': {
                'event': 'birthday',
                'days_before': 0,
                'days_after': 0
            },
            'message_template': '''Happy Birthday, {first_name}! 🎂

To celebrate your special day, we'd like to offer you a special 15% discount on your next order with us.

Plus, we've added 200 bonus points to your loyalty account!

Use code: BDAY{current_year}
Valid for 30 days.

Have a wonderful birthday and we hope to see you soon!

Best regards,
The {restaurant_name} Team''',
            'subject_template': 'Happy Birthday from {restaurant_name}! 🎂'
        }
        
        # Check if campaign already exists
        existing = MarketingCampaign.query.filter_by(
            restaurant_id=restaurant_id,
            name='Birthday Special'
        ).first()
        
        if existing:
            return None
        
        return MarketingService.create_campaign(restaurant_id, campaign_data)
    
    @staticmethod
    def create_welcome_campaign(restaurant_id: int) -> Optional[MarketingCampaign]:
        """Create automated welcome campaign for new customers"""
        campaign_data = {
            'name': 'Welcome New Customer',
            'description': 'Automated welcome message for new customers',
            'campaign_type': 'email',
            'schedule_type': 'triggered',
            'target_audience': {
                'customer_since': {
                    'days': 1
                }
            },
            'trigger_conditions': {
                'event': 'customer_created',
                'delay_hours': 1
            },
            'message_template': '''Dear {customer_name},

Welcome to {restaurant_name}! We're excited to have you join our community.

As a special welcome gift, you've received 100 loyalty points to get you started on your culinary journey with us.

Explore our menu and place your first order to start earning more points!

Your current loyalty tier: {loyalty_tier}
Points needed for next tier: [Calculate and display]

Best regards,
The {restaurant_name} Team''',
            'subject_template': 'Welcome to {restaurant_name}!'
        }
        
        # Check if campaign already exists
        existing = MarketingCampaign.query.filter_by(
            restaurant_id=restaurant_id,
            name='Welcome New Customer'
        ).first()
        
        if existing:
            return None
        
        return MarketingService.create_campaign(restaurant_id, campaign_data)
    
    @staticmethod
    def create_reengagement_campaign(restaurant_id: int) -> Optional[MarketingCampaign]:
        """Create automated re-engagement campaign for inactive customers"""
        campaign_data = {
            'name': 'We Miss You - Re-engagement',
            'description': 'Automated campaign to re-engage inactive customers',
            'campaign_type': 'email',
            'schedule_type': 'triggered',
            'target_audience': {
                'last_order_days': 30
            },
            'trigger_conditions': {
                'event': 'customer_inactive',
                'inactive_days': 30
            },
            'message_template': '''Hi {first_name},

We haven't seen you at {restaurant_name} for a while, and we miss you!

As a special invitation to come back, we'd like to offer you:
- 20% discount on your next order
- Double loyalty points on your next 3 orders

Use code: COMEBACK{current_year}
Valid for 45 days.

We'd love to welcome you back soon!

Best regards,
The {restaurant_name} Team''',
            'subject_template': 'We miss you at {restaurant_name}!'
        }
        
        # Check if campaign already exists
        existing = MarketingCampaign.query.filter_by(
            restaurant_id=restaurant_id,
            name='We Miss You - Re-engagement'
        ).first()
        
        if existing:
            return None
        
        return MarketingService.create_campaign(restaurant_id, campaign_data)
    
    @staticmethod
    def create_vip_campaign(restaurant_id: int) -> Optional[MarketingCampaign]:
        """Create automated VIP campaign for high-value customers"""
        campaign_data = {
            'name': 'VIP Exclusive Offers',
            'description': 'Automated exclusive offers for VIP customers',
            'campaign_type': 'email',
            'schedule_type': 'recurring',
            'target_audience': {
                'loyalty_tiers': ['gold', 'platinum'],
                'spending_range': {
                    'min': 1000
                }
            },
            'recurring_pattern': {
                'frequency': 'monthly',
                'day_of_month': 1
            },
            'message_template': '''Dear {customer_name},

As one of our valued VIP customers, we'd like to extend an exclusive offer just for you.

This month's VIP exclusive:
- 25% discount on all orders
- Priority service
- Early access to new menu items
- Free delivery on all orders

Use code: VIP{current_month}{current_year}
Valid for this month only.

Thank you for your loyalty and continued support!

Best regards,
The {restaurant_name} Team''',
            'subject_template': 'VIP Exclusive Offer from {restaurant_name}'
        }
        
        # Check if campaign already exists
        existing = MarketingCampaign.query.filter_by(
            restaurant_id=restaurant_id,
            name='VIP Exclusive Offers'
        ).first()
        
        if existing:
            return None
        
        return MarketingService.create_campaign(restaurant_id, campaign_data)
    
    @staticmethod
    def get_campaign_analytics(restaurant_id: int, days: int = 30) -> Dict[str, Any]:
        """Get comprehensive campaign analytics"""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        campaigns = MarketingCampaign.query.filter(
            MarketingCampaign.restaurant_id == restaurant_id,
            MarketingCampaign.created_at >= cutoff_date
        ).all()
        
        total_campaigns = len(campaigns)
        total_sent = sum(c.sent_count or 0 for c in campaigns)
        total_delivered = sum(c.delivered_count or 0 for c in campaigns)
        total_opened = sum(c.opened_count or 0 for c in campaigns)
        total_clicked = sum(c.clicked_count or 0 for c in campaigns)
        total_converted = sum(c.converted_count or 0 for c in campaigns)
        
        # Campaign type breakdown
        type_breakdown = {}
        for campaign in campaigns:
            campaign_type = campaign.campaign_type
            if campaign_type not in type_breakdown:
                type_breakdown[campaign_type] = {
                    'count': 0,
                    'sent': 0,
                    'delivered': 0,
                    'opened': 0,
                    'clicked': 0,
                    'converted': 0
                }
            
            type_breakdown[campaign_type]['count'] += 1
            type_breakdown[campaign_type]['sent'] += campaign.sent_count or 0
            type_breakdown[campaign_type]['delivered'] += campaign.delivered_count or 0
            type_breakdown[campaign_type]['opened'] += campaign.opened_count or 0
            type_breakdown[campaign_type]['clicked'] += campaign.clicked_count or 0
            type_breakdown[campaign_type]['converted'] += campaign.converted_count or 0
        
        # Calculate rates
        delivery_rate = (total_delivered / total_sent * 100) if total_sent > 0 else 0
        open_rate = (total_opened / total_delivered * 100) if total_delivered > 0 else 0
        click_rate = (total_clicked / total_opened * 100) if total_opened > 0 else 0
        conversion_rate = (total_converted / total_clicked * 100) if total_clicked > 0 else 0
        
        return {
            'summary': {
                'total_campaigns': total_campaigns,
                'total_sent': total_sent,
                'total_delivered': total_delivered,
                'total_opened': total_opened,
                'total_clicked': total_clicked,
                'total_converted': total_converted,
                'delivery_rate': round(delivery_rate, 2),
                'open_rate': round(open_rate, 2),
                'click_rate': round(click_rate, 2),
                'conversion_rate': round(conversion_rate, 2)
            },
            'type_breakdown': type_breakdown,
            'top_performing_campaigns': MarketingService.get_top_campaigns(campaigns, 'converted_count'),
            'period_days': days
        }
    
    @staticmethod
    def get_top_campaigns(campaigns: List[MarketingCampaign], metric: str = 'converted_count') -> List[Dict]:
        """Get top performing campaigns by metric"""
        sorted_campaigns = sorted(
            campaigns,
            key=lambda c: getattr(c, metric) or 0,
            reverse=True
        )
        
        return [
            {
                'id': campaign.id,
                'name': campaign.name,
                'type': campaign.campaign_type,
                'sent': campaign.sent_count or 0,
                'delivered': campaign.delivered_count or 0,
                'opened': campaign.opened_count or 0,
                'clicked': campaign.clicked_count or 0,
                'converted': campaign.converted_count or 0
            } for campaign in sorted_campaigns[:5]
        ]