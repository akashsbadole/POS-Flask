"""
Advanced Loyalty Program Service
Handles comprehensive loyalty program management including:
- Multi-tier loyalty system
- Points earning and redemption
- Badge and achievement system
- Reward management
- Gamification elements
- Referral program
- Special occasion offers
"""

from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from sqlalchemy import func, and_, or_, desc
import json
import random
import string

from app import db
from app.models.customer import Customer
from app.models.customer_engagement import (
    LoyaltyProgram, LoyaltyTier, LoyaltyBadge, CustomerBadge,
    LoyaltyReward, RewardRedemption
)
from app.models.order import Order, OrderItem


class LoyaltyService:
    """Advanced loyalty program management service"""
    
    @staticmethod
    def get_active_program(restaurant_id: int) -> Optional[LoyaltyProgram]:
        """Get active loyalty program for restaurant"""
        return LoyaltyProgram.query.filter_by(
            restaurant_id=restaurant_id,
            is_active=True
        ).first()
    
    @staticmethod
    def create_program(restaurant_id: int, program_data: dict) -> LoyaltyProgram:
        """Create new loyalty program"""
        program = LoyaltyProgram(
            restaurant_id=restaurant_id,
            name=program_data.get('name'),
            description=program_data.get('description'),
            points_per_currency=program_data.get('points_per_currency', 1.0),
            currency_per_point=program_data.get('currency_per_point', 0.01),
            welcome_bonus_points=program_data.get('welcome_bonus_points', 0),
            referral_bonus_points=program_data.get('referral_bonus_points', 0),
            birthday_bonus_points=program_data.get('birthday_bonus_points', 0),
            badges_enabled=program_data.get('badges_enabled', True),
            achievements_enabled=program_data.get('achievements_enabled', True),
            leaderboard_enabled=program_data.get('leaderboard_enabled', False)
        )
        
        # Set tier thresholds and benefits
        if 'tier_thresholds' in program_data:
            program.set_tier_thresholds(program_data['tier_thresholds'])
        
        if 'tier_benefits' in program_data:
            program.set_tier_benefits(program_data['tier_benefits'])
        
        db.session.add(program)
        db.session.commit()
        
        # Create tiers if provided
        if 'tiers' in program_data:
            LoyaltyService.create_tiers(program.id, program_data['tiers'])
        
        return program
    
    @staticmethod
    def create_tiers(program_id: int, tiers_data: List[dict]) -> List[LoyaltyTier]:
        """Create loyalty tiers for program"""
        tiers = []
        for tier_data in tiers_data:
            tier = LoyaltyTier(
                program_id=program_id,
                name=tier_data.get('name'),
                level=tier_data.get('level'),
                min_points=tier_data.get('min_points', 0),
                points_multiplier=tier_data.get('points_multiplier', 1.0),
                discount_percentage=tier_data.get('discount_percentage', 0.0),
                free_delivery=tier_data.get('free_delivery', False),
                exclusive_offers=tier_data.get('exclusive_offers', False),
                priority_service=tier_data.get('priority_service', False),
                color=tier_data.get('color', '#808080'),
                icon=tier_data.get('icon')
            )
            
            if 'additional_benefits' in tier_data:
                tier.set_additional_benefits(tier_data['additional_benefits'])
            
            db.session.add(tier)
            tiers.append(tier)
        
        db.session.commit()
        return tiers
    
    @staticmethod
    def earn_points(customer_id: int, order: Order, points_multiplier: float = 1.0) -> int:
        """Earn points from order with multipliers"""
        customer = Customer.query.get(customer_id)
        if not customer or not customer.loyalty_member:
            return 0
        
        # Get active loyalty program
        program = LoyaltyService.get_active_program(customer.restaurant_id)
        if not program:
            return 0
        
        # Calculate base points
        base_points = int(float(order.total) * float(program.points_per_currency))
        
        # Apply customer tier multiplier
        customer_tier = LoyaltyService.get_customer_tier(customer_id)
        tier_multiplier = float(customer_tier.points_multiplier) if customer_tier else 1.0
        
        # Apply all multipliers
        final_points = int(base_points * tier_multiplier * points_multiplier)
        
        # Add points to customer
        if customer.add_loyalty_points(final_points, f"Points earned from order #{order.order_number}", order.id):
            db.session.commit()
            
            # Check for badge achievements
            LoyaltyService.check_badge_achievements(customer_id)
            
            # Update customer tier if needed
            LoyaltyService.update_customer_tier(customer_id)
            
            return final_points
        
        return 0
    
    @staticmethod
    def redeem_points(customer_id: int, reward_id: int, order_id: Optional[int] = None) -> Tuple[bool, str]:
        """Redeem points for reward"""
        customer = Customer.query.get(customer_id)
        if not customer:
            return False, "Customer not found"
        
        reward = LoyaltyReward.query.get(reward_id)
        if not reward or not reward.is_active:
            return False, "Reward not found or inactive"
        
        # Check if customer has enough points
        if customer.loyalty_points < reward.points_cost:
            return False, "Insufficient points"
        
        # Check reward availability
        if reward.quantity_available and reward.quantity_claimed >= reward.quantity_available:
            return False, "Reward out of stock"
        
        # Check reward validity
        if reward.valid_from and datetime.now() < reward.valid_from:
            return False, "Reward not yet available"
        
        if reward.valid_until and datetime.now() > reward.valid_until:
            return False, "Reward expired"
        
        # Create redemption
        redemption_code = LoyaltyService.generate_redemption_code()
        redemption = RewardRedemption(
            customer_id=customer_id,
            reward_id=reward_id,
            points_used=reward.points_cost,
            redemption_code=redemption_code,
            order_id=order_id,
            expires_at=datetime.now() + timedelta(days=30)  # 30 days validity
        )
        
        # Deduct points from customer
        if customer.redeem_loyalty_points(reward.points_cost, f"Redeemed reward: {reward.name}", order_id):
            db.session.add(redemption)
            
            # Update reward claimed count
            reward.quantity_claimed += 1
            
            db.session.commit()
            return True, redemption_code
        
        return False, "Failed to redeem points"
    
    @staticmethod
    def get_customer_tier(customer_id: int) -> Optional[LoyaltyTier]:
        """Get customer's current loyalty tier"""
        customer = Customer.query.get(customer_id)
        if not customer:
            return None
        
        program = LoyaltyService.get_active_program(customer.restaurant_id)
        if not program:
            return None
        
        # Find highest tier customer qualifies for
        tier = LoyaltyTier.query.filter_by(
            program_id=program.id,
            is_active=True
        ).filter(
            LoyaltyTier.min_points <= customer.loyalty_points
        ).order_by(desc(LoyaltyTier.level)).first()
        
        return tier
    
    @staticmethod
    def update_customer_tier(customer_id: int) -> bool:
        """Update customer's loyalty tier based on points"""
        customer = Customer.query.get(customer_id)
        if not customer:
            return False
        
        new_tier = LoyaltyService.get_customer_tier(customer_id)
        old_tier_name = customer.loyalty_tier
        
        if new_tier and new_tier.name != old_tier_name:
            customer.loyalty_tier = new_tier.name
            db.session.commit()
            
            # Send tier upgrade notification
            LoyaltyService.send_tier_upgrade_notification(customer, new_tier)
            return True
        
        return False
    
    @staticmethod
    def check_badge_achievements(customer_id: int) -> List[CustomerBadge]:
        """Check and award new badges for customer"""
        customer = Customer.query.get(customer_id)
        if not customer:
            return []
        
        program = LoyaltyService.get_active_program(customer.restaurant_id)
        if not program or not program.badges_enabled:
            return []
        
        new_badges = []
        
        # Get all available badges
        badges = LoyaltyBadge.query.filter_by(
            program_id=program.id,
            is_active=True
        ).all()
        
        for badge in badges:
            # Check if customer already has this badge
            existing_badge = CustomerBadge.query.filter_by(
                customer_id=customer_id,
                badge_id=badge.id
            ).first()
            
            if existing_badge:
                continue
            
            # Check if customer meets badge criteria
            if LoyaltyService.check_badge_criteria(customer, badge):
                customer_badge = CustomerBadge(
                    customer_id=customer_id,
                    badge_id=badge.id,
                    progress_current=badge.criteria_value,
                    progress_target=badge.criteria_value
                )
                
                db.session.add(customer_badge)
                new_badges.append(customer_badge)
                
                # Award badge points if any
                if badge.points_reward > 0:
                    customer.add_loyalty_points(
                        badge.points_reward,
                        f"Achieved badge: {badge.name}"
                    )
        
        if new_badges:
            db.session.commit()
            # Send badge notification
            LoyaltyService.send_badge_achievement_notification(customer, new_badges)
        
        return new_badges
    
    @staticmethod
    def check_badge_criteria(customer: Customer, badge: LoyaltyBadge) -> bool:
        """Check if customer meets badge criteria"""
        if badge.criteria_type == 'orders':
            # Check order count
            if badge.time_period == 'all_time':
                order_count = customer.total_orders
            elif badge.time_period == 'yearly':
                one_year_ago = datetime.now() - timedelta(days=365)
                order_count = Order.query.filter(
                    Order.customer_id == customer.id,
                    Order.created_at >= one_year_ago,
                    Order.status.in_(['served', 'completed'])
                ).count()
            elif badge.time_period == 'monthly':
                one_month_ago = datetime.now() - timedelta(days=30)
                order_count = Order.query.filter(
                    Order.customer_id == customer.id,
                    Order.created_at >= one_month_ago,
                    Order.status.in_(['served', 'completed'])
                ).count()
            else:  # weekly
                one_week_ago = datetime.now() - timedelta(days=7)
                order_count = Order.query.filter(
                    Order.customer_id == customer.id,
                    Order.created_at >= one_week_ago,
                    Order.status.in_(['served', 'completed'])
                ).count()
            
            return order_count >= badge.criteria_value
        
        elif badge.criteria_type == 'spending':
            # Check total spending
            if badge.time_period == 'all_time':
                total_spent = float(customer.total_spent)
            elif badge.time_period == 'yearly':
                one_year_ago = datetime.now() - timedelta(days=365)
                orders = Order.query.filter(
                    Order.customer_id == customer.id,
                    Order.created_at >= one_year_ago,
                    Order.status.in_(['served', 'completed'])
                ).all()
                total_spent = sum(float(order.total) for order in orders)
            elif badge.time_period == 'monthly':
                one_month_ago = datetime.now() - timedelta(days=30)
                orders = Order.query.filter(
                    Order.customer_id == customer.id,
                    Order.created_at >= one_month_ago,
                    Order.status.in_(['served', 'completed'])
                ).all()
                total_spent = sum(float(order.total) for order in orders)
            else:  # weekly
                one_week_ago = datetime.now() - timedelta(days=7)
                orders = Order.query.filter(
                    Order.customer_id == customer.id,
                    Order.created_at >= one_week_ago,
                    Order.status.in_(['served', 'completed'])
                ).all()
                total_spent = sum(float(order.total) for order in orders)
            
            return total_spent >= badge.criteria_value
        
        elif badge.criteria_type == 'visits':
            # Check visit frequency (simplified as order count)
            return customer.total_orders >= badge.criteria_value
        
        elif badge.criteria_type == 'referrals':
            # Check referral count (would need referral tracking)
            # For now, return False
            return False
        
        elif badge.criteria_type == 'streak':
            # Check visit streak (simplified)
            # For now, return False
            return False
        
        elif badge.criteria_type == 'special':
            # Special badges with custom criteria
            if badge.name == 'Food Explorer':
                # Check unique items tried
                order_items = db.session.query(
                    func.count(func.distinct(OrderItem.item_id))
                ).join(Order).filter(
                    Order.customer_id == customer.id,
                    Order.status.in_(['served', 'completed'])
                ).scalar()
                return order_items >= badge.criteria_value
        
        return False
    
    @staticmethod
    def create_reward(program_id: int, reward_data: dict) -> LoyaltyReward:
        """Create new reward for loyalty program"""
        reward = LoyaltyReward(
            program_id=program_id,
            name=reward_data.get('name'),
            description=reward_data.get('description'),
            reward_type=reward_data.get('reward_type'),
            points_cost=reward_data.get('points_cost'),
            discount_value=reward_data.get('discount_value'),
            discount_type=reward_data.get('discount_type'),
            min_order_value=reward_data.get('min_order_value'),
            quantity_available=reward_data.get('quantity_available'),
            valid_from=reward_data.get('valid_from'),
            valid_until=reward_data.get('valid_until')
        )
        
        if 'applicable_items' in reward_data:
            reward.set_applicable_items(reward_data['applicable_items'])
        
        if 'applicable_categories' in reward_data:
            reward.set_applicable_categories(reward_data['applicable_categories'])
        
        db.session.add(reward)
        db.session.commit()
        
        return reward
    
    @staticmethod
    def get_available_rewards(customer_id: int) -> List[LoyaltyReward]:
        """Get rewards available to customer"""
        customer = Customer.query.get(customer_id)
        if not customer:
            return []
        
        program = LoyaltyService.get_active_program(customer.restaurant_id)
        if not program:
            return []
        
        # Get active rewards that customer can afford
        rewards = LoyaltyReward.query.filter_by(
            program_id=program.id,
            is_active=True
        ).filter(
            or_(
                LoyaltyReward.valid_until.is_(None),
                LoyaltyReward.valid_until > datetime.now()
            )
        ).filter(
            or_(
                LoyaltyReward.valid_from.is_(None),
                LoyaltyReward.valid_from <= datetime.now()
            )
        ).filter(
            LoyaltyReward.points_cost <= customer.loyalty_points
        ).all()
        
        # Filter out out-of-stock rewards
        available_rewards = []
        for reward in rewards:
            if not reward.quantity_available or reward.quantity_claimed < reward.quantity_available:
                available_rewards.append(reward)
        
        return available_rewards
    
    @staticmethod
    def process_referral(referrer_id: int, referred_customer_id: int) -> bool:
        """Process customer referral and award bonus points"""
        referrer = Customer.query.get(referrer_id)
        referred = Customer.query.get(referred_customer_id)
        
        if not referrer or not referred:
            return False
        
        program = LoyaltyService.get_active_program(referrer.restaurant_id)
        if not program or program.referral_bonus_points <= 0:
            return False
        
        # Award bonus points to referrer
        if referrer.add_loyalty_points(
            program.referral_bonus_points,
            f"Referral bonus for {referred.get_full_name()}",
            None
        ):
            db.session.commit()
            
            # Send referral notification
            LoyaltyService.send_referral_notification(referrer, referred)
            return True
        
        return False
    
    @staticmethod
    def process_birthday_bonus(customer_id: int) -> bool:
        """Process birthday bonus points"""
        customer = Customer.query.get(customer_id)
        if not customer:
            return False
        
        program = LoyaltyService.get_active_program(customer.restaurant_id)
        if not program or program.birthday_bonus_points <= 0:
            return False
        
        # Check if birthday bonus already given this year
        current_year = datetime.now().year
        # This would need a separate tracking table for birthday bonuses
        # For now, assume it hasn't been given
        
        if customer.add_loyalty_points(
            program.birthday_bonus_points,
            f"Birthday bonus points",
            None
        ):
            db.session.commit()
            
            # Send birthday notification
            LoyaltyService.send_birthday_notification(customer)
            return True
        
        return False
    
    @staticmethod
    def generate_redemption_code() -> str:
        """Generate unique redemption code"""
        while True:
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
            existing = RewardRedemption.query.filter_by(redemption_code=code).first()
            if not existing:
                return code
    
    @staticmethod
    def get_loyalty_leaderboard(restaurant_id: int, limit: int = 10) -> List[Dict]:
        """Get loyalty points leaderboard"""
        customers = Customer.query.filter_by(
            restaurant_id=restaurant_id,
            loyalty_member=True
        ).order_by(desc(Customer.loyalty_points)).limit(limit).all()
        
        leaderboard = []
        for rank, customer in enumerate(customers, 1):
            tier = LoyaltyService.get_customer_tier(customer.id)
            leaderboard.append({
                'rank': rank,
                'customer_id': customer.id,
                'customer_name': customer.get_full_name(),
                'loyalty_points': customer.loyalty_points,
                'tier': tier.name if tier else None,
                'tier_color': tier.color if tier else '#808080'
            })
        
        return leaderboard
    
    @staticmethod
    def get_customer_loyalty_summary(customer_id: int) -> Dict[str, Any]:
        """Get comprehensive loyalty summary for customer"""
        customer = Customer.query.get(customer_id)
        if not customer:
            return {}
        
        program = LoyaltyService.get_active_program(customer.restaurant_id)
        if not program:
            return {}
        
        tier = LoyaltyService.get_customer_tier(customer_id)
        
        # Get customer badges
        badges = db.session.query(
            LoyaltyBadge.name,
            LoyaltyBadge.description,
            LoyaltyBadge.icon,
            LoyaltyBadge.color,
            CustomerBadge.earned_at
        ).join(CustomerBadge).filter(
            CustomerBadge.customer_id == customer_id
        ).all()
        
        # Get recent redemptions
        recent_redemptions = RewardRedemption.query.filter_by(
            customer_id=customer_id
        ).order_by(desc(RewardRedemption.created_at)).limit(5).all()
        
        # Get available rewards
        available_rewards = LoyaltyService.get_available_rewards(customer_id)
        
        return {
            'program': {
                'name': program.name,
                'points_per_currency': float(program.points_per_currency),
                'currency_per_point': float(program.currency_per_point)
            },
            'customer': {
                'loyalty_points': customer.loyalty_points,
                'tier': tier.name if tier else None,
                'tier_level': tier.level if tier else 0,
                'tier_benefits': tier.get_additional_benefits() if tier else [],
                'member_since': customer.loyalty_member_since
            },
            'badges': [
                {
                    'name': badge.name,
                    'description': badge.description,
                    'icon': badge.icon,
                    'color': badge.color,
                    'earned_at': badge.earned_at.isoformat() if badge.earned_at else None
                } for badge in badges
            ],
            'recent_redemptions': [
                {
                    'reward_name': redemption.reward.name,
                    'points_used': redemption.points_used,
                    'redemption_code': redemption.redemption_code,
                    'status': redemption.status,
                    'created_at': redemption.created_at.isoformat() if redemption.created_at else None
                } for redemption in recent_redemptions
            ],
            'available_rewards': len(available_rewards),
            'next_tier': LoyaltyService.get_next_tier_info(customer_id)
        }
    
    @staticmethod
    def get_next_tier_info(customer_id: int) -> Optional[Dict[str, Any]]:
        """Get information about customer's next loyalty tier"""
        customer = Customer.query.get(customer_id)
        if not customer:
            return None
        
        current_tier = LoyaltyService.get_customer_tier(customer_id)
        if not current_tier:
            return None
        
        # Get next tier
        next_tier = LoyaltyTier.query.filter_by(
            program_id=current_tier.program_id,
            is_active=True
        ).filter(
            LoyaltyTier.level == current_tier.level + 1
        ).first()
        
        if not next_tier:
            return None  # Already at highest tier
        
        points_needed = next_tier.min_points - customer.loyalty_points
        
        return {
            'name': next_tier.name,
            'level': next_tier.level,
            'min_points': next_tier.min_points,
            'points_multiplier': float(next_tier.points_multiplier),
            'discount_percentage': float(next_tier.discount_percentage),
            'points_needed': max(0, points_needed),
            'benefits': next_tier.get_additional_benefits(),
            'color': next_tier.color,
            'icon': next_tier.icon
        }
    
    @staticmethod
    def send_tier_upgrade_notification(customer: Customer, new_tier: LoyaltyTier):
        """Send tier upgrade notification to customer"""
        # This would integrate with the communication hub
        # For now, just log the notification
        print(f"Tier upgrade notification sent to {customer.get_full_name()}: {new_tier.name}")
    
    @staticmethod
    def send_badge_achievement_notification(customer: Customer, new_badges: List[CustomerBadge]):
        """Send badge achievement notification to customer"""
        # This would integrate with the communication hub
        # For now, just log the notification
        badge_names = [badge.badge.name for badge in new_badges]
        print(f"Badge achievement notification sent to {customer.get_full_name()}: {', '.join(badge_names)}")
    
    @staticmethod
    def send_referral_notification(referrer: Customer, referred: Customer):
        """Send referral notification to referrer"""
        # This would integrate with the communication hub
        # For now, just log the notification
        print(f"Referral notification sent to {referrer.get_full_name()} for referring {referred.get_full_name()}")
    
    @staticmethod
    def send_birthday_notification(customer: Customer):
        """Send birthday notification to customer"""
        # This would integrate with the communication hub
        # For now, just log the notification
        print(f"Birthday notification sent to {customer.get_full_name()}")