"""
Personalization Engine Service
Handles AI-powered personalization including:
- AI-powered menu recommendations
- Personalized dining experiences
- Customer preference tracking
- Behavioral analysis for personalization
- Dynamic menu customization
- Special occasion recognition
"""

from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from sqlalchemy import func, and_, or_, desc
import json
import math

from app import db
from app.models.customer import Customer
from app.models.customer_engagement import (
    CustomerPreference, PersonalizedRecommendation, CustomerBehavior
)
from app.models.order import Order, OrderItem
from app.models.menu import MenuItem, Category


class PersonalizationService:
    """AI-powered personalization engine service"""
    
    @staticmethod
    def track_customer_behavior(customer_id: int, behavior_type: str, behavior_data: dict, 
                          session_id: Optional[str] = None, device_type: Optional[str] = None) -> CustomerBehavior:
        """Track customer behavior for AI learning"""
        behavior = CustomerBehavior(
            customer_id=customer_id,
            behavior_type=behavior_type,
            behavior_data=json.dumps(behavior_data),
            session_id=session_id,
            device_type=device_type,
            location=behavior_data.get('location')
        )
        
        db.session.add(behavior)
        db.session.commit()
        
        # Trigger preference updates based on behavior
        PersonalizationService.update_preferences_from_behavior(customer_id, behavior_type, behavior_data)
        
        return behavior
    
    @staticmethod
    def update_preferences_from_behavior(customer_id: int, behavior_type: str, behavior_data: dict):
        """Update customer preferences based on behavior"""
        customer = Customer.query.get(customer_id)
        if not customer:
            return
        
        # Extract preferences from different behavior types
        if behavior_type == 'item_view':
            # Track viewed items for preference learning
            item_id = behavior_data.get('item_id')
            if item_id:
                PersonalizationService.update_item_preference(customer_id, item_id, 'viewed')
        
        elif behavior_type == 'purchase':
            # Track purchased items for preference learning
            items = behavior_data.get('items', [])
            for item_id in items:
                PersonalizationService.update_item_preference(customer_id, item_id, 'purchased')
        
        elif behavior_type == 'search':
            # Track search terms for preference learning
            search_term = behavior_data.get('search_term')
            category_id = behavior_data.get('category_id')
            if search_term:
                PersonalizationService.update_search_preference(customer_id, search_term, category_id)
        
        elif behavior_type == 'add_to_cart':
            # Track cart additions for preference learning
            item_id = behavior_data.get('item_id')
            if item_id:
                PersonalizationService.update_item_preference(customer_id, item_id, 'carted')
    
    @staticmethod
    def update_item_preference(customer_id: int, item_id: int, action: str):
        """Update item preference based on customer action"""
        menu_item = MenuItem.query.get(item_id)
        if not menu_item:
            return
        
        # Update category preference
        existing_pref = CustomerPreference.query.filter_by(
            customer_id=customer_id,
            preference_type='cuisine',
            preference_value=menu_item.category.name
        ).first()
        
        if existing_pref:
            # Increase strength based on action
            if action == 'purchased':
                existing_pref.strength = min(1.0, existing_pref.strength + 0.2)
                existing_pref.confidence = min(1.0, existing_pref.confidence + 0.1)
            elif action == 'viewed':
                existing_pref.strength = min(1.0, existing_pref.strength + 0.05)
                existing_pref.confidence = min(1.0, existing_pref.confidence + 0.05)
            
            existing_pref.last_updated = datetime.utcnow()
        else:
            # Create new preference
            strength = 0.2 if action == 'purchased' else 0.05
            preference = CustomerPreference(
                customer_id=customer_id,
                preference_type='cuisine',
                preference_value=menu_item.category.name,
                strength=strength,
                confidence=0.1 if action == 'purchased' else 0.05,
                source='behavioral'
            )
            db.session.add(preference)
        
        db.session.commit()
    
    @staticmethod
    def update_search_preference(customer_id: int, search_term: str, category_id: Optional[int]):
        """Update search preference"""
        # Extract cuisine type from search term
        cuisine_types = ['italian', 'chinese', 'indian', 'mexican', 'thai', 'american', 'japanese', 'mediterranean']
        search_lower = search_term.lower()
        
        detected_cuisine = None
        for cuisine in cuisine_types:
            if cuisine in search_lower:
                detected_cuisine = cuisine
                break
        
        if detected_cuisine:
            existing_pref = CustomerPreference.query.filter_by(
                customer_id=customer_id,
                preference_type='cuisine',
                preference_value=detected_cuisine
            ).first()
            
            if existing_pref:
                existing_pref.strength = min(1.0, existing_pref.strength + 0.1)
                existing_pref.confidence = min(1.0, existing_pref.confidence + 0.05)
                existing_pref.last_updated = datetime.utcnow()
            else:
                preference = CustomerPreference(
                    customer_id=customer_id,
                    preference_type='cuisine',
                    preference_value=detected_cuisine,
                    strength=0.1,
                    confidence=0.05,
                    source='behavioral'
                )
                db.session.add(preference)
            
            db.session.commit()
    
    @staticmethod
    def get_customer_preferences(customer_id: int) -> Dict[str, Any]:
        """Get comprehensive customer preferences"""
        preferences = CustomerPreference.query.filter_by(customer_id=customer_id).all()
        
        pref_dict = {
            'dietary': [],
            'cuisine': [],
            'price_range': [],
            'spice_level': [],
            'portion_size': [],
            'occasion': [],
            'allergies': []
        }
        
        for pref in preferences:
            if pref.preference_type in pref_dict:
                pref_dict[pref.preference_type].append({
                    'value': pref.preference_value,
                    'strength': float(pref.strength),
                    'confidence': float(pref.confidence),
                    'source': pref.source,
                    'last_updated': pref.last_updated.isoformat() if pref.last_updated else None
                })
        
        # Sort preferences by strength
        for pref_type in pref_dict:
            pref_dict[pref_type].sort(key=lambda x: x['strength'], reverse=True)
        
        return pref_dict
    
    @staticmethod
    def generate_recommendations(customer_id: int, recommendation_type: str = 'menu_item', 
                           limit: int = 10) -> List[PersonalizedRecommendation]:
        """Generate AI-powered personalized recommendations"""
        customer = Customer.query.get(customer_id)
        if not customer:
            return []
        
        # Get customer preferences and behavior
        preferences = PersonalizationService.get_customer_preferences(customer_id)
        recent_behaviors = CustomerBehavior.query.filter_by(
            customer_id=customer_id
        ).order_by(desc(CustomerBehavior.created_at)).limit(50).all()
        
        # Generate recommendations based on type
        if recommendation_type == 'menu_item':
            recommendations = PersonalizationService.generate_item_recommendations(
                customer, preferences, recent_behaviors, limit
            )
        elif recommendation_type == 'category':
            recommendations = PersonalizationService.generate_category_recommendations(
                customer, preferences, recent_behaviors, limit
            )
        elif recommendation_type == 'combo':
            recommendations = PersonalizationService.generate_combo_recommendations(
                customer, preferences, recent_behaviors, limit
            )
        elif recommendation_type == 'promotion':
            recommendations = PersonalizationService.generate_promotion_recommendations(
                customer, preferences, recent_behaviors, limit
            )
        else:
            recommendations = PersonalizationService.generate_experience_recommendations(
                customer, preferences, recent_behaviors, limit
            )
        
        # Save recommendations to database
        saved_recommendations = []
        for rec_data in recommendations:
            # Check if similar recommendation already exists
            existing = PersonalizedRecommendation.query.filter_by(
                customer_id=customer_id,
                item_id=rec_data.get('item_id'),
                recommendation_type=rec_data.get('recommendation_type')
            ).filter(
                PersonalizedRecommendation.valid_until > datetime.now()
            ).first()
            
            if not existing:
                recommendation = PersonalizedRecommendation(
                    customer_id=customer_id,
                    recommendation_type=rec_data.get('recommendation_type'),
                    item_id=rec_data.get('item_id'),
                    category_id=rec_data.get('category_id'),
                    score=rec_data.get('score'),
                    reason=rec_data.get('reason'),
                    context=json.dumps(rec_data.get('context', {})),
                    valid_until=datetime.now() + timedelta(days=7)
                )
                
                db.session.add(recommendation)
                saved_recommendations.append(recommendation)
        
        db.session.commit()
        return saved_recommendations
    
    @staticmethod
    def generate_item_recommendations(customer: Customer, preferences: Dict, 
                                recent_behaviors: List[CustomerBehavior], limit: int) -> List[Dict]:
        """Generate personalized item recommendations"""
        recommendations = []
        
        # Get customer's favorite categories
        favorite_categories = [pref['value'] for pref in preferences.get('cuisine', [])[:3]]
        
        # Get recently viewed items
        viewed_items = []
        for behavior in recent_behaviors:
            if behavior.behavior_type == 'item_view':
                data = behavior.get_behavior_data()
                if data.get('item_id'):
                    viewed_items.append(data['item_id'])
        
        # Get purchased items
        purchased_items = []
        for behavior in recent_behaviors:
            if behavior.behavior_type == 'purchase':
                data = behavior.get_behavior_data()
                if 'items' in data:
                    purchased_items.extend(data['items'])
        
        # Collaborative filtering - find similar customers
        similar_customers = PersonalizationService.find_similar_customers(customer.id, purchased_items)
        
        # Get items purchased by similar customers but not by this customer
        collaborative_items = PersonalizationService.get_collaborative_recommendations(
            customer.id, similar_customers, purchased_items
        )
        
        # Content-based filtering - recommend similar items to what customer liked
        content_based_items = PersonalizationService.get_content_based_recommendations(
            customer.id, viewed_items, purchased_items, favorite_categories
        )
        
        # Trending items
        trending_items = PersonalizationService.get_trending_items(customer.restaurant_id)
        
        # Combine and score recommendations
        all_items = list(set(collaborative_items + content_based_items + trending_items))
        
        for item_id in all_items[:limit * 2]:  # Get more items than needed for scoring
            menu_item = MenuItem.query.get(item_id)
            if not menu_item or not menu_item.is_available:
                continue
            
            score = PersonalizationService.calculate_recommendation_score(
                customer, menu_item, preferences, viewed_items, purchased_items, similar_customers
            )
            
            reason = PersonalizationService.generate_recommendation_reason(
                score, preferences, viewed_items, purchased_items
            )
            
            recommendations.append({
                'item_id': item_id,
                'recommendation_type': 'menu_item',
                'score': score,
                'reason': reason,
                'context': {
                    'customer_tier': customer.loyalty_tier,
                    'favorite_categories': favorite_categories,
                    'recommendation_sources': ['collaborative', 'content_based', 'trending']
                }
            })
        
        # Sort by score and return top recommendations
        recommendations.sort(key=lambda x: x['score'], reverse=True)
        return recommendations[:limit]
    
    @staticmethod
    def generate_category_recommendations(customer: Customer, preferences: Dict,
                                   recent_behaviors: List[CustomerBehavior], limit: int) -> List[Dict]:
        """Generate personalized category recommendations"""
        recommendations = []
        
        # Get customer's preferred categories
        preferred_categories = [pref['value'] for pref in preferences.get('cuisine', [])]
        
        # Get all available categories
        categories = Category.query.filter_by(is_active=True).all()
        
        for category in categories:
            score = 0.0
            
            # Boost score for preferred categories
            if category.name in preferred_categories:
                pref_strength = next(
                    (pref['strength'] for pref in preferences.get('cuisine', []) 
                    if pref['value'] == category.name
                ), 0)
                score += pref_strength * 0.5
            
            # Boost score for categories with items customer has viewed
            viewed_items_in_category = db.session.query(OrderItem.item_id).join(Order).join(MenuItem).filter(
                Order.customer_id == customer.id,
                MenuItem.category_id == category.id
            ).distinct().count()
            
            if viewed_items_in_category > 0:
                score += min(0.3, viewed_items_in_category * 0.05)
            
            # Boost score for categories with purchased items
            purchased_items_in_category = db.session.query(OrderItem.item_id).join(Order).join(MenuItem).filter(
                Order.customer_id == customer.id,
                MenuItem.category_id == category.id,
                Order.status.in_(['served', 'completed'])
            ).distinct().count()
            
            if purchased_items_in_category > 0:
                score += min(0.4, purchased_items_in_category * 0.03)
            
            # Add some randomness for discovery
            score += hash(category.name) % 10 / 100
            
            recommendations.append({
                'category_id': category.id,
                'recommendation_type': 'category',
                'score': score,
                'reason': f"Based on your interest in {category.name} cuisine",
                'context': {
                    'viewed_items_count': viewed_items_in_category,
                    'purchased_items_count': purchased_items_in_category
                }
            })
        
        # Sort by score and return top recommendations
        recommendations.sort(key=lambda x: x['score'], reverse=True)
        return recommendations[:limit]
    
    @staticmethod
    def generate_combo_recommendations(customer: Customer, preferences: Dict,
                                recent_behaviors: List[CustomerBehavior], limit: int) -> List[Dict]:
        """Generate personalized combo recommendations"""
        recommendations = []
        
        # Get customer's favorite items
        favorite_items = PersonalizationService.get_favorite_items(customer.id)
        
        # Generate combos based on complementary items
        for item_id in favorite_items[:limit]:
            complementary_items = PersonalizationService.get_complementary_items(item_id)
            
            if complementary_items:
                combo_score = PersonalizationService.calculate_combo_score(
                    customer, item_id, complementary_items, preferences
                )
                
                recommendations.append({
                    'item_id': item_id,
                    'recommendation_type': 'combo',
                    'score': combo_score,
                    'reason': f"Customers who bought {MenuItem.query.get(item_id).name} also enjoyed these items",
                    'context': {
                        'primary_item': item_id,
                        'complementary_items': complementary_items[:3]  # Top 3 complementary items
                    }
                })
        
        # Sort by score and return top recommendations
        recommendations.sort(key=lambda x: x['score'], reverse=True)
        return recommendations[:limit]
    
    @staticmethod
    def generate_promotion_recommendations(customer: Customer, preferences: Dict,
                                    recent_behaviors: List[CustomerBehavior], limit: int) -> List[Dict]:
        """Generate personalized promotion recommendations"""
        recommendations = []
        
        # Generate promotions based on customer tier and preferences
        if customer.loyalty_tier:
            # Tier-based promotions
            if customer.loyalty_tier == 'platinum':
                recommendations.append({
                    'recommendation_type': 'promotion',
                    'score': 0.9,
                    'reason': 'Exclusive Platinum member promotion',
                    'context': {
                        'promotion_type': 'tier_exclusive',
                        'tier': customer.loyalty_tier,
                        'discount': 25
                    }
                })
            elif customer.loyalty_tier == 'gold':
                recommendations.append({
                    'recommendation_type': 'promotion',
                    'score': 0.8,
                    'reason': 'Gold member special offer',
                    'context': {
                        'promotion_type': 'tier_exclusive',
                        'tier': customer.loyalty_tier,
                        'discount': 15
                    }
                })
        
        # Generate promotions based on preferences
        preferred_categories = [pref['value'] for pref in preferences.get('cuisine', [])[:2]]
        
        for category_name in preferred_categories:
            category = Category.query.filter_by(name=category_name).first()
            if category:
                recommendations.append({
                    'category_id': category.id,
                    'recommendation_type': 'promotion',
                    'score': 0.7,
                    'reason': f'Special offer for your favorite {category_name} dishes',
                    'context': {
                        'promotion_type': 'category_based',
                        'category': category_name,
                        'discount': 10
                    }
                })
        
        # Generate time-based promotions
        current_hour = datetime.now().hour
        
        if 11 <= current_hour <= 14:  # Lunch time
            recommendations.append({
                'recommendation_type': 'promotion',
                'score': 0.6,
                'reason': 'Lunch time special',
                'context': {
                    'promotion_type': 'time_based',
                    'time_period': 'lunch',
                    'discount': 15
                }
            })
        elif 17 <= current_hour <= 21:  # Dinner time
            recommendations.append({
                'recommendation_type': 'promotion',
                'score': 0.6,
                'reason': 'Dinner time special',
                'context': {
                    'promotion_type': 'time_based',
                    'time_period': 'dinner',
                    'discount': 20
                }
            })
        
        # Sort by score and return top recommendations
        recommendations.sort(key=lambda x: x['score'], reverse=True)
        return recommendations[:limit]
    
    @staticmethod
    def generate_experience_recommendations(customer: Customer, preferences: Dict,
                                     recent_behaviors: List[CustomerBehavior], limit: int) -> List[Dict]:
        """Generate personalized dining experience recommendations"""
        recommendations = []
        
        # Special occasion recognition
        current_date = datetime.now()
        special_occasions = PersonalizationService.detect_special_occasions(customer.id, current_date)
        
        for occasion in special_occasions:
            recommendations.append({
                'recommendation_type': 'experience',
                'score': 0.9,
                'reason': f"Special {occasion['type']} celebration offer",
                'context': {
                    'occasion_type': occasion['type'],
                    'occasion_date': occasion['date'].isoformat(),
                    'recommendation': occasion['recommendation']
                }
            })
        
        # Preference-based experience recommendations
        dietary_prefs = preferences.get('dietary', [])
        spice_prefs = preferences.get('spice_level', [])
        
        if dietary_prefs:
            for diet_pref in dietary_prefs:
                if diet_pref['value'] == 'vegetarian':
                    recommendations.append({
                        'recommendation_type': 'experience',
                        'score': 0.7,
                        'reason': 'Recommended vegetarian dishes and chef specials',
                        'context': {
                            'experience_type': 'dietary_preference',
                            'preference': 'vegetarian',
                            'recommendations': ['Vegetarian chef specials', 'Plant-based options']
                        }
                    })
                elif diet_pref['value'] == 'gluten_free':
                    recommendations.append({
                        'recommendation_type': 'experience',
                        'score': 0.7,
                        'reason': 'Gluten-free menu options available',
                        'context': {
                            'experience_type': 'dietary_preference',
                            'preference': 'gluten_free',
                            'recommendations': ['Gluten-free pasta', 'GF desserts']
                        }
                    })
        
        if spice_prefs:
            preferred_spice = spice_prefs[0]['value'] if spice_prefs else 'medium'
            if preferred_spice == 'mild':
                recommendations.append({
                    'recommendation_type': 'experience',
                    'score': 0.6,
                    'reason': 'Mild spice level options recommended',
                    'context': {
                        'experience_type': 'spice_preference',
                        'preference': 'mild',
                        'recommendations': ['Mild curries', 'Non-spicy options']
                    }
                })
        
        # Sort by score and return top recommendations
        recommendations.sort(key=lambda x: x['score'], reverse=True)
        return recommendations[:limit]
    
    @staticmethod
    def find_similar_customers(customer_id: int, purchased_items: List[int], limit: int = 10) -> List[int]:
        """Find customers with similar purchase patterns"""
        if not purchased_items:
            return []
        
        # Get other customers who purchased the same items
        similar_customers = db.session.query(
            Order.customer_id,
            func.count(Order.id).label('common_items')
        ).join(OrderItem).filter(
            OrderItem.item_id.in_(purchased_items),
            Order.customer_id != customer_id,
            Order.status.in_(['served', 'completed'])
        ).group_by(Order.customer_id).order_by(
            desc('common_items')
        ).limit(limit).all()
        
        return [customer.customer_id for customer in similar_customers]
    
    @staticmethod
    def get_collaborative_recommendations(customer_id: int, similar_customers: List[int], 
                                     purchased_items: List[int], limit: int = 20) -> List[int]:
        """Get items purchased by similar customers but not by this customer"""
        if not similar_customers or not purchased_items:
            return []
        
        # Get items purchased by similar customers
        collaborative_items = db.session.query(
            OrderItem.item_id,
            func.count(OrderItem.id).label('purchase_count')
        ).join(Order).filter(
            Order.customer_id.in_(similar_customers),
            OrderItem.item_id.notin_(purchased_items),
            Order.status.in_(['served', 'completed'])
        ).group_by(OrderItem.item_id).order_by(
            desc('purchase_count')
        ).limit(limit).all()
        
        return [item.item_id for item in collaborative_items]
    
    @staticmethod
    def get_content_based_recommendations(customer_id: int, viewed_items: List[int], 
                                    purchased_items: List[int], favorite_categories: List[str], 
                                    limit: int = 20) -> List[int]:
        """Get items similar to what customer liked"""
        if not viewed_items and not purchased_items:
            return []
        
        # Get items from favorite categories
        liked_items = viewed_items + purchased_items
        if not liked_items:
            return []
        
        # Get items in the same categories as liked items
        content_based_items = db.session.query(
            OrderItem.item_id,
            func.count(OrderItem.id).label('popularity')
        ).join(Order).join(MenuItem).join(Category).filter(
            Category.name.in_(favorite_categories),
            OrderItem.item_id.notin_(liked_items),
            MenuItem.is_available == True
        ).group_by(OrderItem.item_id).order_by(
            desc('popularity')
        ).limit(limit).all()
        
        return [item.item_id for item in content_based_items]
    
    @staticmethod
    def get_trending_items(restaurant_id: int, limit: int = 20) -> List[int]:
        """Get currently trending items"""
        # Get items ordered most frequently in the last 30 days
        thirty_days_ago = datetime.now() - timedelta(days=30)
        
        trending_items = db.session.query(
            OrderItem.item_id,
            func.count(OrderItem.id).label('order_count'),
            func.sum(OrderItem.quantity).label('total_quantity')
        ).join(Order).join(MenuItem).filter(
            MenuItem.restaurant_id == restaurant_id,
            Order.created_at >= thirty_days_ago,
            Order.status.in_(['served', 'completed']),
            MenuItem.is_available == True
        ).group_by(OrderItem.item_id).order_by(
            desc('order_count'),
            desc('total_quantity')
        ).limit(limit).all()
        
        return [item.item_id for item in trending_items]
    
    @staticmethod
    def get_favorite_items(customer_id: int, limit: int = 10) -> List[int]:
        """Get customer's most frequently purchased items"""
        favorite_items = db.session.query(
            OrderItem.item_id,
            func.count(OrderItem.id).label('purchase_count'),
            func.sum(OrderItem.quantity).label('total_quantity')
        ).join(Order).filter(
            Order.customer_id == customer_id,
            Order.status.in_(['served', 'completed'])
        ).group_by(OrderItem.item_id).order_by(
            desc('purchase_count'),
            desc('total_quantity')
        ).limit(limit).all()
        
        return [item.item_id for item in favorite_items]
    
    @staticmethod
    def get_complementary_items(item_id: int, limit: int = 5) -> List[int]:
        """Get items frequently purchased together with the given item"""
        # Find orders that contain this item
        orders_with_item = db.session.query(Order.id).join(OrderItem).filter(
            OrderItem.item_id == item_id,
            Order.status.in_(['served', 'completed'])
        ).subquery()
        
        # Get other items from those orders
        complementary_items = db.session.query(
            OrderItem.item_id,
            func.count(OrderItem.id).label('co_occurrence')
        ).join(Order).filter(
            Order.id.in_(orders_with_item),
            OrderItem.item_id != item_id
        ).group_by(OrderItem.item_id).order_by(
            desc('co_occurrence')
        ).limit(limit).all()
        
        return [item.item_id for item in complementary_items]
    
    @staticmethod
    def calculate_recommendation_score(customer: Customer, item: MenuItem, preferences: Dict,
                                  viewed_items: List[int], purchased_items: List[int], 
                                  similar_customers: List[int]) -> float:
        """Calculate recommendation score for an item"""
        score = 0.0
        
        # Category preference score
        if item.category:
            category_prefs = [pref for pref in preferences.get('cuisine', []) if pref['value'] == item.category.name]
            if category_prefs:
                score += max(pref['strength'] for pref in category_prefs) * 0.3
        
        # Collaborative filtering score
        collaborative_score = len([c for c in similar_customers[:5]]) * 0.1
        score += collaborative_score
        
        # Content-based score
        if item.category and item.category.name in [pref['value'] for pref in preferences.get('cuisine', [])]:
            score += 0.2
        
        # Trending score
        if item.id in viewed_items:
            score += 0.1
        
        if item.id in purchased_items:
            score += 0.15
        
        # Item popularity score
        item_popularity = db.session.query(func.count(OrderItem.id)).join(Order).filter(
            OrderItem.item_id == item.id,
            Order.status.in_(['served', 'completed'])
        ).scalar() or 0
        
        if item_popularity > 0:
            score += min(0.2, math.log(item_popularity + 1) / 10)
        
        # Price preference score
        customer_avg_order = float(customer.average_order_value or 0)
        if customer_avg_order > 0:
            price_diff = abs(float(item.price) - customer_avg_order)
            price_score = max(0, 1 - (price_diff / customer_avg_order))
            score += price_score * 0.1
        
        return min(1.0, score)
    
    @staticmethod
    def calculate_combo_score(customer: Customer, primary_item_id: int, 
                         complementary_items: List[int], preferences: Dict) -> float:
        """Calculate combo recommendation score"""
        score = 0.0
        
        # Base score for having complementary items
        score += min(0.5, len(complementary_items) * 0.1)
        
        # Preference alignment score
        primary_item = MenuItem.query.get(primary_item_id)
        if primary_item and primary_item.category:
            category_prefs = [pref for pref in preferences.get('cuisine', []) if pref['value'] == primary_item.category.name]
            if category_prefs:
                score += max(pref['strength'] for pref in category_prefs) * 0.3
        
        # Price diversity score (encouraging higher total order value)
        total_price = float(primary_item.price if primary_item else 0)
        for comp_item_id in complementary_items[:3]:
            comp_item = MenuItem.query.get(comp_item_id)
            if comp_item:
                total_price += float(comp_item.price)
        
        customer_avg_order = float(customer.average_order_value or 0)
        if customer_avg_order > 0:
            price_diversity_score = min(0.3, (total_price - customer_avg_order) / customer_avg_order)
            score += max(0, price_diversity_score)
        
        return min(1.0, score)
    
    @staticmethod
    def generate_recommendation_reason(score: float, preferences: Dict, 
                                viewed_items: List[int], purchased_items: List[int]) -> str:
        """Generate human-readable recommendation reason"""
        if score > 0.8:
            return "Highly recommended based on your preferences"
        elif score > 0.6:
            return "Recommended based on similar customers' choices"
        elif score > 0.4:
            return "Popular item you might like"
        else:
            return "You might also like this"
    
    @staticmethod
    def detect_special_occasions(customer_id: int, current_date: datetime) -> List[Dict]:
        """Detect special occasions for personalized experiences"""
        occasions = []
        customer = Customer.query.get(customer_id)
        if not customer:
            return occasions
        
        # Check for upcoming birthday (within 7 days)
        if customer.created_at:  # We have customer's birth date in created_at (simplified)
            # This is a simplified approach - in reality, we'd have a separate birth_date field
            customer_birthday = customer.created_at  # Placeholder - would use actual birth date
            current_year_birthday = customer_birthday.replace(year=current_date.year)
            days_until_birthday = (current_year_birthday - current_date).days
            
            if 0 <= days_until_birthday <= 7:
                occasions.append({
                    'type': 'birthday',
                    'date': current_year_birthday,
                    'recommendation': 'Birthday special with complimentary dessert'
                })
        
        # Check for anniversary (customer since date)
        anniversary_date = customer.created_at
        if anniversary_date:
            current_year_anniversary = anniversary_date.replace(year=current_date.year)
            days_until_anniversary = (current_year_anniversary - current_date).days
            
            if 0 <= days_until_anniversary <= 7:
                years_as_customer = current_date.year - anniversary_date.year
                occasions.append({
                    'type': 'anniversary',
                    'date': current_year_anniversary,
                    'recommendation': f'{years_as_customer} year anniversary special'
                })
        
        return occasions
    
    @staticmethod
    def update_recommendation_performance(recommendation_id: int, action: str, 
                                     conversion_value: Optional[float] = None):
        """Update recommendation performance metrics"""
        recommendation = PersonalizedRecommendation.query.get(recommendation_id)
        if not recommendation:
            return
        
        if action == 'shown':
            recommendation.shown_count += 1
        elif action == 'clicked':
            recommendation.clicked_count += 1
        elif action == 'converted' and conversion_value:
            recommendation.converted_count += 1
        
        db.session.commit()
    
    @staticmethod
    def get_personalization_analytics(restaurant_id: int, days: int = 30) -> Dict[str, Any]:
        """Get personalization engine analytics"""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # Recommendation performance
        recommendations = PersonalizedRecommendation.query.filter(
            PersonalizedRecommendation.valid_until >= cutoff_date
        ).all()
        
        total_recommendations = len(recommendations)
        total_shown = sum(rec.shown_count for rec in recommendations)
        total_clicked = sum(rec.clicked_count for rec in recommendations)
        total_converted = sum(rec.converted_count for rec in recommendations)
        
        # Calculate rates
        click_rate = (total_clicked / total_shown * 100) if total_shown > 0 else 0
        conversion_rate = (total_converted / total_clicked * 100) if total_clicked > 0 else 0
        
        # Recommendation type breakdown
        type_breakdown = {}
        for rec in recommendations:
            rec_type = rec.recommendation_type
            if rec_type not in type_breakdown:
                type_breakdown[rec_type] = {
                    'count': 0,
                    'shown': 0,
                    'clicked': 0,
                    'converted': 0
                }
            
            type_breakdown[rec_type]['count'] += 1
            type_breakdown[rec_type]['shown'] += rec.shown_count
            type_breakdown[rec_type]['clicked'] += rec.clicked_count
            type_breakdown[rec_type]['converted'] += rec.converted_count
        
        return {
            'summary': {
                'total_recommendations': total_recommendations,
                'total_shown': total_shown,
                'total_clicked': total_clicked,
                'total_converted': total_converted,
                'click_rate': round(click_rate, 2),
                'conversion_rate': round(conversion_rate, 2)
            },
            'type_breakdown': type_breakdown,
            'top_performing_recommendations': PersonalizationService.get_top_recommendations(recommendations),
            'period_days': days
        }
    
    @staticmethod
    def get_top_recommendations(recommendations: List[PersonalizedRecommendation], limit: int = 10) -> List[Dict]:
        """Get top performing recommendations"""
        # Sort by conversion rate, then click rate
        sorted_recs = sorted(
            recommendations,
            key=lambda rec: (
                (rec.converted_count / max(rec.shown_count, 1)) if rec.shown_count > 0 else 0,
                (rec.clicked_count / max(rec.shown_count, 1)) if rec.shown_count > 0 else 0
            ),
            reverse=True
        )
        
        return [
            {
                'id': rec.id,
                'type': rec.recommendation_type,
                'item_id': rec.item_id,
                'score': float(rec.score),
                'shown': rec.shown_count,
                'clicked': rec.clicked_count,
                'converted': rec.converted_count,
                'conversion_rate': (rec.converted_count / max(rec.shown_count, 1)) * 100 if rec.shown_count > 0 else 0,
                'reason': rec.reason
            } for rec in sorted_recs[:limit]
        ]