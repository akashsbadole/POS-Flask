"""
Migration script for creating enhanced customer engagement tables
This script creates all the tables needed for the advanced customer engagement features
including loyalty programs, marketing automation, feedback, personalization, and analytics.
"""

from app import create_app, db
from app.models.customer_engagement import (
    LoyaltyProgram, LoyaltyTier, LoyaltyBadge, CustomerBadge, 
    LoyaltyReward, RewardRedemption, MarketingCampaign, CampaignMessage,
    CustomerFeedback, FeedbackResponse, CustomerPreference,
    PersonalizedRecommendation, CustomerCommunication, CommunicationTemplate,
    CustomerBehavior, CustomerJourney, CustomerIntegration
)

def create_customer_engagement_tables():
    """Create all customer engagement related tables"""
    app = create_app()
    
    with app.app_context():
        print("Creating customer engagement tables...")
        
        # Create all tables in order
        tables_to_create = [
            # Loyalty Program Tables
            LoyaltyProgram.__table__,
            LoyaltyTier.__table__,
            LoyaltyBadge.__table__,
            CustomerBadge.__table__,
            LoyaltyReward.__table__,
            RewardRedemption.__table__,
            
            # Marketing Automation Tables
            MarketingCampaign.__table__,
            CampaignMessage.__table__,
            
            # Customer Feedback Tables
            CustomerFeedback.__table__,
            FeedbackResponse.__table__,
            
            # Personalization Tables
            CustomerPreference.__table__,
            PersonalizedRecommendation.__table__,
            
            # Communication Hub Tables
            CustomerCommunication.__table__,
            CommunicationTemplate.__table__,
            
            # Customer Analytics Tables
            CustomerBehavior.__table__,
            CustomerJourney.__table__,
            
            # Integration Tables
            CustomerIntegration.__table__
        ]
        
        # Create tables
        for table in tables_to_create:
            try:
                table.create(db.engine, checkfirst=True)
                print(f"✓ Created table: {table.name}")
            except Exception as e:
                print(f"✗ Error creating table {table.name}: {str(e)}")
        
        print("Customer engagement tables creation completed!")
        
        # Create default loyalty program if none exists
        create_default_loyalty_program()
        
        # Create default communication templates
        create_default_templates()

def create_default_loyalty_program():
    """Create a default loyalty program for each restaurant"""
    from app.models.restaurant import Restaurant
    
    restaurants = Restaurant.query.filter_by(is_active=True).all()
    
    for restaurant in restaurants:
        # Check if loyalty program already exists
        existing_program = LoyaltyProgram.query.filter_by(
            restaurant_id=restaurant.id
        ).first()
        
        if not existing_program:
            # Create default loyalty program
            program = LoyaltyProgram(
                name="Default Loyalty Program",
                description="Standard loyalty program with points earning and rewards",
                points_per_currency=1.0,
                currency_per_point=0.01,
                welcome_bonus_points=100,
                referral_bonus_points=50,
                birthday_bonus_points=200,
                restaurant_id=restaurant.id
            )
            
            # Set default tier thresholds
            program.set_tier_thresholds({
                'bronze': 0,
                'silver': 500,
                'gold': 1500,
                'platinum': 3000
            })
            
            # Set default tier benefits
            program.set_tier_benefits({
                'bronze': ['Point earning', 'Birthday discount'],
                'silver': ['Point earning (1.2x)', 'Birthday discount', 'Free item after 10 orders'],
                'gold': ['Point earning (1.5x)', 'Birthday discount', 'Free item after 5 orders', 'Exclusive offers'],
                'platinum': ['Point earning (2x)', 'Birthday discount', 'Free item after 3 orders', 'Exclusive offers', 'Priority service']
            })
            
            db.session.add(program)
            
            # Create default tiers
            tiers_data = [
                {
                    'name': 'Bronze',
                    'level': 1,
                    'min_points': 0,
                    'points_multiplier': 1.0,
                    'discount_percentage': 0.0,
                    'color': '#CD7F32'
                },
                {
                    'name': 'Silver',
                    'level': 2,
                    'min_points': 500,
                    'points_multiplier': 1.2,
                    'discount_percentage': 5.0,
                    'color': '#C0C0C0'
                },
                {
                    'name': 'Gold',
                    'level': 3,
                    'min_points': 1500,
                    'points_multiplier': 1.5,
                    'discount_percentage': 10.0,
                    'exclusive_offers': True,
                    'color': '#FFD700'
                },
                {
                    'name': 'Platinum',
                    'level': 4,
                    'min_points': 3000,
                    'points_multiplier': 2.0,
                    'discount_percentage': 15.0,
                    'exclusive_offers': True,
                    'priority_service': True,
                    'color': '#E5E4E2'
                }
            ]
            
            for tier_data in tiers_data:
                tier = LoyaltyTier(
                    program_id=program.id,  # Will be set after program is committed
                    restaurant_id=restaurant.id,
                    **tier_data
                )
                db.session.add(tier)
            
            # Create default badges
            badges_data = [
                {
                    'name': 'First Order',
                    'description': 'Placed your first order',
                    'criteria_type': 'orders',
                    'criteria_value': 1,
                    'points_reward': 50,
                    'icon': '🎯',
                    'color': '#FF6B6B'
                },
                {
                    'name': 'Regular Customer',
                    'description': 'Placed 10 orders',
                    'criteria_type': 'orders',
                    'criteria_value': 10,
                    'points_reward': 100,
                    'icon': '⭐',
                    'color': '#4ECDC4'
                },
                {
                    'name': 'VIP Customer',
                    'description': 'Placed 50 orders',
                    'criteria_type': 'orders',
                    'criteria_value': 50,
                    'points_reward': 500,
                    'icon': '👑',
                    'color': '#FFD93D'
                },
                {
                    'name': 'Food Explorer',
                    'description': 'Tried 20 different items',
                    'criteria_type': 'special',
                    'criteria_value': 20,
                    'points_reward': 200,
                    'icon': '🍽️',
                    'color': '#6BCF7F'
                }
            ]
            
            for badge_data in badges_data:
                badge = LoyaltyBadge(
                    program_id=program.id,  # Will be set after program is committed
                    restaurant_id=restaurant.id,
                    **badge_data
                )
                db.session.add(badge)
            
            print(f"✓ Created default loyalty program for {restaurant.name}")

def create_default_templates():
    """Create default communication templates"""
    from app.models.restaurant import Restaurant
    
    restaurants = Restaurant.query.filter_by(is_active=True).all()
    
    for restaurant in restaurants:
        # Check if templates already exist
        existing_templates = CommunicationTemplate.query.filter_by(
            restaurant_id=restaurant.id
        ).count()
        
        if existing_templates == 0:
            # Create default email templates
            email_templates = [
                {
                    'name': 'Welcome Email',
                    'description': 'Welcome email for new customers',
                    'channel': 'email',
                    'communication_type': 'marketing',
                    'subject_template': 'Welcome to {restaurant_name}!',
                    'content_template': 'Dear {customer_name},\n\nWelcome to {restaurant_name}! We\'re excited to have you join our community.\n\nAs a special welcome gift, you\'ve received {welcome_bonus_points} loyalty points to get you started on your culinary journey with us.\n\nExplore our menu and place your first order to start earning more points!\n\nBest regards,\nThe {restaurant_name} Team',
                    'variables': ['customer_name', 'restaurant_name', 'welcome_bonus_points']
                },
                {
                    'name': 'Birthday Offer',
                    'description': 'Birthday special offer email',
                    'channel': 'email',
                    'communication_type': 'promotional',
                    'subject_template': 'Happy Birthday from {restaurant_name}! 🎂',
                    'content_template': 'Happy Birthday, {customer_name}!\n\nTo celebrate your special day, we\'d like to offer you a special {birthday_discount}% discount on your next order with us.\n\nPlus, we\'ve added {birthday_bonus_points} bonus points to your loyalty account!\n\nUse code: BDAY{year}\nValid for {validity_days} days.\n\nHave a wonderful birthday!\nThe {restaurant_name} Team',
                    'variables': ['customer_name', 'restaurant_name', 'birthday_discount', 'birthday_bonus_points', 'year', 'validity_days']
                },
                {
                    'name': 'Order Confirmation',
                    'description': 'Order confirmation email',
                    'channel': 'email',
                    'communication_type': 'transactional',
                    'subject_template': 'Your {restaurant_name} Order #{order_number} is Confirmed',
                    'content_template': 'Dear {customer_name},\n\nThank you for your order #{order_number} at {restaurant_name}!\n\nOrder Details:\n{order_details}\n\nTotal: {order_total}\nEstimated delivery/pickup time: {estimated_time}\n\nWe\'ll notify you when your order is ready.\n\nThank you for choosing {restaurant_name}!\n\nTrack your order: {tracking_url}',
                    'variables': ['customer_name', 'restaurant_name', 'order_number', 'order_details', 'order_total', 'estimated_time', 'tracking_url']
                }
            ]
            
            # Create default SMS templates
            sms_templates = [
                {
                    'name': 'Order Ready SMS',
                    'description': 'SMS notification when order is ready',
                    'channel': 'sms',
                    'communication_type': 'transactional',
                    'content_template': 'Hi {customer_name}! Your order #{order_number} from {restaurant_name} is ready for {order_type}. Order total: {order_total}',
                    'variables': ['customer_name', 'restaurant_name', 'order_number', 'order_type', 'order_total']
                },
                {
                    'name': 'Promotional Offer',
                    'description': 'General promotional SMS',
                    'channel': 'sms',
                    'communication_type': 'promotional',
                    'content_template': 'Special offer from {restaurant_name}! Get {discount}% off on your next order. Use code: {promo_code}. Valid until {expiry_date}. Order now: {order_url}',
                    'variables': ['restaurant_name', 'discount', 'promo_code', 'expiry_date', 'order_url']
                }
            ]
            
            all_templates = email_templates + sms_templates
            
            for template_data in all_templates:
                template = CommunicationTemplate(
                    restaurant_id=restaurant.id,
                    **template_data
                )
                db.session.add(template)
            
            print(f"✓ Created default communication templates for {restaurant.name}")

if __name__ == '__main__':
    create_customer_engagement_tables()
    print("Customer engagement migration completed successfully!")