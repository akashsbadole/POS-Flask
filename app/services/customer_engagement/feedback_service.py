"""
Customer Feedback System Service
Handles comprehensive customer feedback management including:
- Real-time feedback collection
- Rating and review management
- Sentiment analysis of feedback
- Feedback-driven improvement suggestions
- Customer complaint resolution workflow
- Net Promoter Score (NPS) tracking
"""

from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from sqlalchemy import func, and_, or_, desc
import json
import re

from app import db
from app.models.customer import Customer
from app.models.user import User
from app.models.customer_engagement import (
    CustomerFeedback, FeedbackResponse
)
from app.models.order import Order


class FeedbackService:
    """Advanced customer feedback management service"""
    
    @staticmethod
    def create_feedback(feedback_data: dict, customer_id: Optional[int] = None) -> CustomerFeedback:
        """Create new customer feedback"""
        feedback = CustomerFeedback(
            customer_id=customer_id,
            order_id=feedback_data.get('order_id'),
            feedback_type=feedback_data.get('feedback_type', 'rating'),
            overall_rating=feedback_data.get('overall_rating'),
            food_rating=feedback_data.get('food_rating'),
            service_rating=feedback_data.get('service_rating'),
            ambiance_rating=feedback_data.get('ambiance_rating'),
            value_rating=feedback_data.get('value_rating'),
            title=feedback_data.get('title'),
            comments=feedback_data.get('comments'),
            restaurant_id=feedback_data.get('restaurant_id'),
            priority=feedback_data.get('priority', 'medium')
        )
        
        # Perform AI sentiment analysis
        sentiment = FeedbackService.analyze_sentiment(feedback_data.get('comments', ''))
        feedback.sentiment_score = sentiment['score']
        feedback.sentiment_label = sentiment['label']
        feedback.set_topics(sentiment['topics'])
        feedback.set_emotions(sentiment['emotions'])
        
        db.session.add(feedback)
        db.session.commit()
        
        # Auto-assign feedback based on priority and type
        FeedbackService.auto_assign_feedback(feedback)
        
        # Trigger automated responses for certain feedback types
        FeedbackService.trigger_automated_responses(feedback)
        
        return feedback
    
    @staticmethod
    def analyze_sentiment(text: str) -> Dict[str, Any]:
        """Analyze sentiment of feedback text"""
        if not text or len(text.strip()) == 0:
            return {
                'score': 0.5,
                'label': 'neutral',
                'topics': [],
                'emotions': []
            }
        
        text = text.lower()
        
        # Positive words
        positive_words = [
            'good', 'great', 'excellent', 'amazing', 'love', 'perfect', 'wonderful', 
            'fantastic', 'satisfied', 'happy', 'pleased', 'delicious', 'awesome',
            'outstanding', 'superb', 'brilliant', 'tasty', 'flavorful', 'fresh'
        ]
        
        # Negative words
        negative_words = [
            'bad', 'terrible', 'awful', 'hate', 'worst', 'disappointed', 
            'unsatisfied', 'angry', 'frustrated', 'poor', 'disgusting',
            'cold', 'slow', 'rude', 'dirty', 'overpriced', 'bland'
        ]
        
        # Count positive and negative words
        positive_count = sum(1 for word in positive_words if word in text)
        negative_count = sum(1 for word in negative_words if word in text)
        
        # Calculate sentiment score
        total_words = len(text.split())
        if total_words == 0:
            sentiment_score = 0.5
        else:
            sentiment_score = 0.5 + (positive_count - negative_count) / (total_words * 0.5)
            sentiment_score = max(0.0, min(1.0, sentiment_score))
        
        # Determine sentiment label
        if sentiment_score > 0.65:
            sentiment_label = 'positive'
        elif sentiment_score < 0.35:
            sentiment_label = 'negative'
        else:
            sentiment_label = 'neutral'
        
        # Extract topics
        topics = FeedbackService.extract_topics(text)
        
        # Extract emotions
        emotions = FeedbackService.extract_emotions(text)
        
        return {
            'score': round(sentiment_score, 3),
            'label': sentiment_label,
            'topics': topics,
            'emotions': emotions,
            'positive_words': positive_count,
            'negative_words': negative_count
        }
    
    @staticmethod
    def extract_topics(text: str) -> List[str]:
        """Extract topics from feedback text"""
        topics = []
        text = text.lower()
        
        # Topic keywords
        topic_keywords = {
            'food_quality': ['food', 'taste', 'flavor', 'fresh', 'delicious', 'bland', 'overcooked', 'undercooked', 'portion', 'quality'],
            'service': ['service', 'staff', 'waiter', 'waitress', 'rude', 'friendly', 'helpful', 'slow', 'fast', 'attentive'],
            'ambiance': ['ambiance', 'atmosphere', 'decor', 'clean', 'dirty', 'music', 'noise', 'lighting', 'comfortable'],
            'pricing': ['price', 'cost', 'expensive', 'cheap', 'value', 'worth', 'overpriced', 'reasonable', 'affordable'],
            'delivery': ['delivery', 'pickup', 'time', 'late', 'fast', 'slow', 'packaging', 'driver'],
            'menu': ['menu', 'variety', 'selection', 'options', 'choices', 'limited', 'extensive']
        }
        
        for topic, keywords in topic_keywords.items():
            if any(keyword in text for keyword in keywords):
                topics.append(topic)
        
        return topics
    
    @staticmethod
    def extract_emotions(text: str) -> List[str]:
        """Extract emotions from feedback text"""
        emotions = []
        text = text.lower()
        
        # Emotion keywords
        emotion_keywords = {
            'excitement': ['excited', 'thrilled', 'amazed', 'wow', 'incredible', 'fantastic'],
            'disappointment': ['disappointed', 'let down', 'expected more', 'hoped for', 'wished'],
            'anger': ['angry', 'furious', 'upset', 'frustrated', 'annoyed', 'irritated'],
            'satisfaction': ['satisfied', 'pleased', 'content', 'happy', 'delighted'],
            'concern': ['concerned', 'worried', 'unsure', 'hesitant', 'cautious']
        }
        
        for emotion, keywords in emotion_keywords.items():
            if any(keyword in text for keyword in keywords):
                emotions.append(emotion)
        
        return emotions if emotions else ['neutral']
    
    @staticmethod
    def auto_assign_feedback(feedback: CustomerFeedback) -> Optional[User]:
        """Automatically assign feedback to appropriate staff"""
        # Assignment rules based on feedback type and priority
        if feedback.priority in ['high', 'urgent']:
            # High priority feedback goes to managers
            assignee = User.query.filter_by(
                restaurant_id=feedback.restaurant_id,
                role='manager'
            ).first()
        elif feedback.feedback_type == 'complaint':
            # Complaints go to managers
            assignee = User.query.filter_by(
                restaurant_id=feedback.restaurant_id,
                role='manager'
            ).first()
        elif 'food' in feedback.get_topics():
            # Food-related feedback goes to kitchen manager
            assignee = User.query.filter_by(
                restaurant_id=feedback.restaurant_id,
                role='kitchen'
            ).first()
        elif 'service' in feedback.get_topics():
            # Service-related feedback goes to floor manager
            assignee = User.query.filter_by(
                restaurant_id=feedback.restaurant_id,
                role='manager'
            ).first()
        else:
            # General feedback goes to any available staff
            assignee = User.query.filter_by(
                restaurant_id=feedback.restaurant_id
            ).first()
        
        if assignee:
            feedback.assigned_to = assignee.id
            db.session.commit()
            return assignee
        
        return None
    
    @staticmethod
    def trigger_automated_responses(feedback: CustomerFeedback):
        """Trigger automated responses for certain feedback types"""
        if feedback.feedback_type == 'complaint' or feedback.sentiment_label == 'negative':
            # Send immediate acknowledgment for complaints
            FeedbackService.create_automated_response(
                feedback,
                'acknowledgment',
                'Thank you for your feedback. We take your concerns seriously and will investigate this matter promptly. Our team will get back to you within 24 hours.'
            )
        
        elif feedback.overall_rating and feedback.overall_rating <= 2:
            # Send response for very low ratings
            FeedbackService.create_automated_response(
                feedback,
                'acknowledgment',
                'We\'re sorry to hear about your experience. Your feedback is important to us and we\'d like to make things right. Please contact us directly at [restaurant phone] or [restaurant email].'
            )
        
        elif feedback.overall_rating and feedback.overall_rating >= 5:
            # Send thank you for excellent ratings
            FeedbackService.create_automated_response(
                feedback,
                'acknowledgment',
                'Thank you for the wonderful rating! We\'re delighted you had a great experience and look forward to serving you again soon.'
            )
    
    @staticmethod
    def create_automated_response(feedback: CustomerFeedback, response_type: str, message: str) -> FeedbackResponse:
        """Create automated response to feedback"""
        response = FeedbackResponse(
            feedback_id=feedback.id,
            responder_id=None,  # Automated response has no specific responder
            response_type=response_type,
            message=message,
            communication_channel='email',
            communicated_at=datetime.utcnow()
        )
        
        db.session.add(response)
        db.session.commit()
        
        return response
    
    @staticmethod
    def create_response(feedback_id: int, responder_id: int, response_data: dict) -> FeedbackResponse:
        """Create manual response to feedback"""
        feedback = CustomerFeedback.query.get(feedback_id)
        if not feedback:
            raise ValueError("Feedback not found")
        
        response = FeedbackResponse(
            feedback_id=feedback_id,
            responder_id=responder_id,
            response_type=response_data.get('response_type', 'investigation'),
            message=response_data.get('message'),
            communication_channel=response_data.get('communication_channel', 'email')
        )
        
        db.session.add(response)
        
        # Update feedback status
        if response_data.get('response_type') == 'resolution':
            feedback.status = 'resolved'
            feedback.resolved_at = datetime.utcnow()
            feedback.resolution_notes = response_data.get('message')
        elif response_data.get('response_type') == 'investigation':
            feedback.status = 'investigating'
        else:
            feedback.status = 'acknowledged'
        
        db.session.commit()
        
        return response
    
    @staticmethod
    def get_feedback_analytics(restaurant_id: int, days: int = 30) -> Dict[str, Any]:
        """Get comprehensive feedback analytics"""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # Get feedback in period
        feedback_query = CustomerFeedback.query.filter(
            CustomerFeedback.restaurant_id == restaurant_id,
            CustomerFeedback.created_at >= cutoff_date
        )
        
        total_feedback = feedback_query.count()
        
        if total_feedback == 0:
            return {
                'summary': {
                    'total_feedback': 0,
                    'average_rating': 0,
                    'sentiment_distribution': {'positive': 0, 'negative': 0, 'neutral': 0},
                    'feedback_types': {},
                    'priority_breakdown': {'low': 0, 'medium': 0, 'high': 0, 'urgent': 0}
                },
                'period_days': days
            }
        
        # Rating statistics
        rating_stats = db.session.query(
            func.avg(CustomerFeedback.overall_rating).label('avg_overall'),
            func.avg(CustomerFeedback.food_rating).label('avg_food'),
            func.avg(CustomerFeedback.service_rating).label('avg_service'),
            func.avg(CustomerFeedback.ambiance_rating).label('avg_ambiance'),
            func.avg(CustomerFeedback.value_rating).label('avg_value')
        ).filter(
            CustomerFeedback.restaurant_id == restaurant_id,
            CustomerFeedback.created_at >= cutoff_date,
            CustomerFeedback.overall_rating.isnot(None)
        ).first()
        
        # Sentiment distribution
        sentiment_stats = db.session.query(
            CustomerFeedback.sentiment_label,
            func.count(CustomerFeedback.id).label('count')
        ).filter(
            CustomerFeedback.restaurant_id == restaurant_id,
            CustomerFeedback.created_at >= cutoff_date
        ).group_by(CustomerFeedback.sentiment_label).all()
        
        sentiment_distribution = {'positive': 0, 'negative': 0, 'neutral': 0}
        for sentiment, count in sentiment_stats:
            sentiment_distribution[sentiment] = count
        
        # Feedback type breakdown
        type_stats = db.session.query(
            CustomerFeedback.feedback_type,
            func.count(CustomerFeedback.id).label('count')
        ).filter(
            CustomerFeedback.restaurant_id == restaurant_id,
            CustomerFeedback.created_at >= cutoff_date
        ).group_by(CustomerFeedback.feedback_type).all()
        
        feedback_types = {feedback_type: count for feedback_type, count in type_stats}
        
        # Priority breakdown
        priority_stats = db.session.query(
            CustomerFeedback.priority,
            func.count(CustomerFeedback.id).label('count')
        ).filter(
            CustomerFeedback.restaurant_id == restaurant_id,
            CustomerFeedback.created_at >= cutoff_date
        ).group_by(CustomerFeedback.priority).all()
        
        priority_breakdown = {'low': 0, 'medium': 0, 'high': 0, 'urgent': 0}
        for priority, count in priority_stats:
            priority_breakdown[priority] = count
        
        # Topic analysis
        topic_stats = FeedbackService.get_topic_analytics(restaurant_id, cutoff_date)
        
        # Resolution metrics
        resolution_stats = FeedbackService.get_resolution_analytics(restaurant_id, cutoff_date)
        
        return {
            'summary': {
                'total_feedback': total_feedback,
                'average_rating': round(float(getattr(rating_stats, 'avg_overall', 0) or 0), 2),
                'rating_breakdown': {
                    'overall': round(float(getattr(rating_stats, 'avg_overall', 0) or 0), 2),
                    'food': round(float(getattr(rating_stats, 'avg_food', 0) or 0), 2),
                    'service': round(float(getattr(rating_stats, 'avg_service', 0) or 0), 2),
                    'ambiance': round(float(getattr(rating_stats, 'avg_ambiance', 0) or 0), 2),
                    'value': round(float(getattr(rating_stats, 'avg_value', 0) or 0), 2)
                },
                'sentiment_distribution': sentiment_distribution,
                'feedback_types': feedback_types,
                'priority_breakdown': priority_breakdown,
                'resolution_metrics': resolution_stats
            },
            'topic_analysis': topic_stats,
            'trend_analysis': FeedbackService.get_feedback_trends(restaurant_id, days),
            'improvement_suggestions': FeedbackService.generate_improvement_suggestions(
                sentiment_distribution, topic_stats, rating_stats
            ),
            'period_days': days
        }
    
    @staticmethod
    def get_topic_analytics(restaurant_id: int, cutoff_date: datetime) -> Dict[str, Any]:
        """Get topic-based analytics"""
        feedback = CustomerFeedback.query.filter(
            CustomerFeedback.restaurant_id == restaurant_id,
            CustomerFeedback.created_at >= cutoff_date
        ).all()
        
        topic_counts = {}
        topic_ratings = {}
        
        for fb in feedback:
            topics = fb.get_topics()
            for topic in topics:
                if topic not in topic_counts:
                    topic_counts[topic] = 0
                    topic_ratings[topic] = []
                
                topic_counts[topic] += 1
                if fb.overall_rating:
                    topic_ratings[topic].append(fb.overall_rating)
        
        # Calculate average ratings per topic
        topic_avg_ratings = {}
        for topic, ratings in topic_ratings.items():
            if ratings:
                topic_avg_ratings[topic] = sum(ratings) / len(ratings)
            else:
                topic_avg_ratings[topic] = 0
        
        return {
            'topic_counts': topic_counts,
            'topic_ratings': topic_avg_ratings,
            'most_mentioned': sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        }
    
    @staticmethod
    def get_resolution_analytics(restaurant_id: int, cutoff_date: datetime) -> Dict[str, Any]:
        """Get resolution metrics analytics"""
        feedback = CustomerFeedback.query.filter(
            CustomerFeedback.restaurant_id == restaurant_id,
            CustomerFeedback.created_at >= cutoff_date
        ).all()
        
        total_feedback = len(feedback)
        resolved_count = len([fb for fb in feedback if fb.status == 'resolved'])
        pending_count = len([fb for fb in feedback if fb.status in ['pending', 'acknowledged', 'investigating']])
        
        # Calculate average resolution time
        resolved_feedback = [fb for fb in feedback if fb.status == 'resolved' and fb.resolved_at]
        resolution_times = []
        
        for fb in resolved_feedback:
            resolution_time = fb.resolved_at - fb.created_at
            resolution_times.append(resolution_time.total_seconds() / 3600)  # Convert to hours
        
        avg_resolution_time = sum(resolution_times) / len(resolution_times) if resolution_times else 0
        
        return {
            'total_feedback': total_feedback,
            'resolved_count': resolved_count,
            'pending_count': pending_count,
            'resolution_rate': (resolved_count / total_feedback * 100) if total_feedback > 0 else 0,
            'average_resolution_hours': round(avg_resolution_time, 2),
            'resolution_distribution': {
                'within_24h': len([t for t in resolution_times if t <= 24]),
                'within_48h': len([t for t in resolution_times if t <= 48]),
                'over_48h': len([t for t in resolution_times if t > 48])
            }
        }
    
    @staticmethod
    def get_feedback_trends(restaurant_id: int, days: int) -> Dict[str, Any]:
        """Get feedback trends over time"""
        # Get daily feedback counts for the period
        daily_feedback = db.session.query(
            func.date(CustomerFeedback.created_at).label('date'),
            func.count(CustomerFeedback.id).label('count'),
            func.avg(CustomerFeedback.overall_rating).label('avg_rating')
        ).filter(
            CustomerFeedback.restaurant_id == restaurant_id,
            CustomerFeedback.created_at >= datetime.now() - timedelta(days=days)
        ).group_by(
            func.date(CustomerFeedback.created_at)
        ).order_by('date').all()
        
        # Calculate trend
        if len(daily_feedback) >= 2:
            recent_data = daily_feedback[-1] if len(daily_feedback) > 0 else {}
            previous_data = daily_feedback[-2] if len(daily_feedback) > 1 else {}
            recent_avg = recent_data.get('avg_rating') or 0
            previous_avg = previous_data.get('avg_rating') or 0
            trend = 'improving' if recent_avg > previous_avg else 'declining' if recent_avg < previous_avg else 'stable'
        else:
            trend = 'insufficient_data'
        
        return {
            'daily_feedback': [
                {
                    'date': str(item.date),
                    'count': item.count,
                    'average_rating': round(float(item.avg_rating or 0), 2)
                } for item in daily_feedback
            ],
            'trend': trend,
            'period_days': days
        }
    
    @staticmethod
    def generate_improvement_suggestions(sentiment_dist: Dict, topic_stats: Dict, rating_stats: Any) -> List[str]:
        """Generate improvement suggestions based on feedback analysis"""
        suggestions = []
        
        # Sentiment-based suggestions
        negative_percentage = (sentiment_dist.get('negative', 0) / sum(sentiment_dist.values()) * 100) if sum(sentiment_dist.values()) > 0 else 0
        
        if negative_percentage > 30:
            suggestions.append("High negative sentiment indicates need for immediate service improvement")
        
        # Topic-based suggestions
        topic_counts = topic_stats.get('topic_counts', {})
        
        if topic_counts.get('service', 0) > topic_counts.get('food_quality', 0):
            suggestions.append("Service quality issues are more frequent than food quality - focus on staff training")
        
        if topic_counts.get('food_quality', 0) > topic_counts.get('service', 0):
            suggestions.append("Food quality issues are more frequent than service - review kitchen processes")
        
        if topic_counts.get('pricing', 0) > 0:
            suggestions.append("Pricing concerns detected - review value proposition and portion sizes")
        
        if topic_counts.get('ambiance', 0) > 0:
            suggestions.append("Ambiance issues reported - evaluate restaurant environment and cleanliness")
        
        # Rating-based suggestions
        if rating_stats:
            if float(rating_stats.avg_service or 0) < 3.5:
                suggestions.append("Service ratings are below average - implement service quality monitoring")
            
            if float(rating_stats.avg_food or 0) < 3.5:
                suggestions.append("Food ratings are below average - review food preparation and quality control")
            
            if float(rating_stats.avg_ambiance or 0) < 3.5:
                suggestions.append("Ambiance ratings are below average - improve restaurant atmosphere")
            
            if float(rating_stats.avg_value or 0) < 3.5:
                suggestions.append("Value ratings are below average - review pricing and portion sizes")
        
        return suggestions
    
    @staticmethod
    def calculate_nps(restaurant_id: int, days: int = 30) -> Dict[str, Any]:
        """Calculate Net Promoter Score (NPS)"""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # For NPS, we need feedback with likelihood to recommend question
        # This would require a specific NPS survey or feedback field
        # For now, simulate NPS based on overall ratings
        
        feedback = CustomerFeedback.query.filter(
            CustomerFeedback.restaurant_id == restaurant_id,
            CustomerFeedback.created_at >= cutoff_date,
            CustomerFeedback.overall_rating.isnot(None)
        ).all()
        
        if not feedback:
            return {
                'nps_score': 0,
                'promoters_percentage': 0,
                'detractors_percentage': 0,
                'passives_percentage': 0,
                'total_respondents': 0,
                'period_days': days
            }
        
        # Convert ratings to NPS categories (simplified approach)
        promoters = len([f for f in feedback if f.overall_rating >= 5])  # 5-star ratings
        passives = len([f for f in feedback if f.overall_rating in [3, 4]])  # 3-4 star ratings
        detractors = len([f for f in feedback if f.overall_rating <= 2])  # 1-2 star ratings
        
        total_respondents = len(feedback)
        
        # Calculate NPS
        promoters_percentage = (promoters / total_respondents) * 100
        detractors_percentage = (detractors / total_respondents) * 100
        nps_score = promoters_percentage - detractors_percentage
        
        return {
            'nps_score': round(nps_score, 1),
            'promoters_percentage': round(promoters_percentage, 1),
            'detractors_percentage': round(detractors_percentage, 1),
            'passives_percentage': round(100 - promoters_percentage - detractors_percentage, 1),
            'total_respondents': total_respondents,
            'respondents_breakdown': {
                'promoters': promoters,
                'passives': passives,
                'detractors': detractors
            },
            'nps_category': FeedbackService.get_nps_category(nps_score),
            'period_days': days
        }
    
    @staticmethod
    def get_nps_category(nps_score: float) -> str:
        """Get NPS category based on score"""
        if nps_score >= 70:
            return 'Excellent'
        elif nps_score >= 50:
            return 'Good'
        elif nps_score >= 20:
            return 'Average'
        elif nps_score >= 0:
            return 'Poor'
        else:
            return 'Very Poor'
    
    @staticmethod
    def get_pending_feedback(restaurant_id: int, assigned_to: Optional[int] = None) -> List[CustomerFeedback]:
        """Get pending feedback for staff to respond to"""
        query = CustomerFeedback.query.filter(
            CustomerFeedback.restaurant_id == restaurant_id,
            CustomerFeedback.status.in_(['pending', 'acknowledged', 'investigating'])
        ).order_by(
            desc(CustomerFeedback.priority),
            desc(CustomerFeedback.created_at)
        )
        
        if assigned_to:
            query = query.filter_by(assigned_to=assigned_to)
        
        return query.all()
    
    @staticmethod
    def get_feedback_dashboard_data(restaurant_id: int) -> Dict[str, Any]:
        """Get dashboard data for feedback management"""
        # Recent feedback
        recent_feedback = CustomerFeedback.query.filter_by(
            restaurant_id=restaurant_id
        ).order_by(desc(CustomerFeedback.created_at)).limit(10).all()
        
        # Pending high-priority feedback
        urgent_feedback = CustomerFeedback.query.filter_by(
            restaurant_id=restaurant_id,
            priority='urgent',
            status='pending'
        ).count()
        
        high_priority_feedback = CustomerFeedback.query.filter_by(
            restaurant_id=restaurant_id,
            priority='high',
            status='pending'
        ).count()
        
        # Today's feedback
        today = datetime.now().date()
        today_feedback = CustomerFeedback.query.filter(
            CustomerFeedback.restaurant_id == restaurant_id,
            func.date(CustomerFeedback.created_at) == today
        ).count()
        
        # Recent analytics
        recent_analytics = FeedbackService.get_feedback_analytics(restaurant_id, 7)
        recent_nps = FeedbackService.calculate_nps(restaurant_id, 7)
        
        return {
            'recent_feedback': [
                {
                    'id': fb.id,
                    'customer_name': fb.customer.get_full_name() if fb.customer else 'Anonymous',
                    'feedback_type': fb.feedback_type,
                    'overall_rating': fb.overall_rating,
                    'sentiment_label': fb.sentiment_label,
                    'priority': fb.priority,
                    'status': fb.status,
                    'created_at': fb.created_at.isoformat() if fb.created_at else None,
                    'topics': fb.get_topics()
                } for fb in recent_feedback
            ],
            'alerts': {
                'urgent_pending': urgent_feedback,
                'high_priority_pending': high_priority_feedback,
                'today_feedback': today_feedback
            },
            'analytics': {
                'last_7_days': recent_analytics['summary'],
                'nps_last_7_days': recent_nps
            }
        }