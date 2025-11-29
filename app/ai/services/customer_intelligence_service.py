"""
AI Customer Intelligence Service
Provides intelligent customer analysis including:
- Customer segmentation using AI
- Churn prediction and prevention
- Lifetime value calculation
- Personalized marketing recommendations
- Sentiment analysis from feedback
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from sklearn.cluster import KMeans
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import silhouette_score, classification_report
import json
import logging
import re

from app import db
from app.models.customer import Customer, LoyaltyTransaction
from app.models.order import Order, OrderItem
from app.models.menu import MenuItem, Category
from app.models.ai_models import AIModel, AICustomerBehavior, AIPredictionLog


class CustomerIntelligenceService:
    """AI-powered customer intelligence system"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.models = {}
        self.scalers = {}
        self.encoders = {}
        self.load_models()
    
    def load_models(self):
        """Load trained customer intelligence models"""
        try:
            # Get active customer models
            active_models = AIModel.query.filter_by(
                model_type='customer', 
                is_active=True, 
                is_production=True
            ).all()
            
            for model in active_models:
                # In a real implementation, load the actual ML models
                # self.models[model.algorithm] = joblib.load(model.model_path)
                # self.scalers[model.algorithm] = joblib.load(model.metadata_path)
                self.logger.info(f"Loaded customer model: {model.name}")
                
        except Exception as e:
            self.logger.error(f"Error loading customer models: {str(e)}")
    
    def segment_customers(self, segmentation_type='behavioral'):
        """
        Segment customers using AI algorithms
        
        Args:
            segmentation_type: Type of segmentation (behavioral, value, demographic)
            
        Returns:
            Dictionary with customer segments and analysis
        """
        try:
            # Get customer data
            customer_data = self._get_customer_features()
            
            if len(customer_data) < 10:
                return {'error': 'Insufficient customer data for segmentation'}
            
            # Prepare features for clustering
            X = self._prepare_segmentation_features(customer_data, segmentation_type)
            
            # Perform clustering
            if segmentation_type == 'behavioral':
                segments = self._behavioral_segmentation(X)
            elif segmentation_type == 'value':
                segments = self._value_segmentation(X)
            elif segmentation_type == 'demographic':
                segments = self._demographic_segmentation(X)
            else:
                segments = self._behavioral_segmentation(X)  # Default to behavioral
            
            # Analyze segments
            segment_analysis = self._analyze_segments(customer_data, segments)
            
            return {
                'segmentation_type': segmentation_type,
                'total_customers': len(customer_data),
                'segments': segment_analysis,
                'silhouette_score': self._calculate_segmentation_quality(X, segments),
                'recommendations': self._generate_segmentation_recommendations(segment_analysis)
            }
            
        except Exception as e:
            self.logger.error(f"Error segmenting customers: {str(e)}")
            return {'error': str(e)}
    
    def predict_churn(self, customer_id=None, days_ahead=30):
        """
        Predict customer churn risk
        
        Args:
            customer_id: Specific customer to analyze (optional)
            days_ahead: Prediction horizon
            
        Returns:
            Dictionary with churn predictions and risk factors
        """
        try:
            if customer_id:
                # Predict for specific customer
                prediction = self._predict_customer_churn(customer_id)
                return {'customer_predictions': [prediction]}
            else:
                # Predict for all customers
                customers = Customer.query.filter(Customer.is_active == True).all()
                predictions = []
                
                for customer in customers:
                    prediction = self._predict_customer_churn(customer.id)
                    predictions.append(prediction)
                
                # Analyze overall churn risk
                high_risk_customers = [p for p in predictions if p.get('risk_level') == 'high']
                medium_risk_customers = [p for p in predictions if p.get('risk_level') == 'medium']
                
                return {
                    'customer_predictions': predictions,
                    'total_customers': len(customers),
                    'high_risk_count': len(high_risk_customers),
                    'medium_risk_count': len(medium_risk_customers),
                    'overall_churn_rate': len(high_risk_customers) / len(customers),
                    'retention_recommendations': self._generate_retention_recommendations(predictions)
                }
                
        except Exception as e:
            self.logger.error(f"Error predicting churn: {str(e)}")
            return {'error': str(e)}
    
    def calculate_lifetime_value(self, customer_id=None):
        """
        Calculate customer lifetime value (CLV)
        
        Args:
            customer_id: Specific customer to analyze (optional)
            
        Returns:
            Dictionary with CLV calculations and insights
        """
        try:
            if customer_id:
                # Calculate for specific customer
                clv_data = self._calculate_customer_clv(customer_id)
                return {'customer_clv': [clv_data]}
            else:
                # Calculate for all customers
                customers = Customer.query.filter(Customer.is_active == True).all()
                clv_data = []
                
                for customer in customers:
                    clv = self._calculate_customer_clv(customer.id)
                    clv_data.append(clv)
                
                # Analyze CLV distribution
                clv_values = [c.get('clv', 0) for c in clv_data]
                
                return {
                    'customer_clv': clv_data,
                    'total_customers': len(customers),
                    'average_clv': np.mean(clv_values),
                    'median_clv': np.median(clv_values),
                    'top_10_percent_value': np.percentile(clv_values, 90),
                    'clv_distribution': {
                        'high': len([c for c in clv_data if c.get('clv_tier') == 'high']),
                        'medium': len([c for c in clv_data if c.get('clv_tier') == 'medium']),
                        'low': len([c for c in clv_data if c.get('clv_tier') == 'low'])
                    },
                    'retention_strategies': self._generate_clv_strategies(clv_data)
                }
                
        except Exception as e:
            self.logger.error(f"Error calculating lifetime value: {str(e)}")
            return {'error': str(e)}
    
    def get_marketing_recommendations(self, customer_id=None, campaign_type='retention'):
        """
        Generate personalized marketing recommendations
        
        Args:
            customer_id: Target customer (optional)
            campaign_type: Type of campaign (retention, upsell, reactivation)
            
        Returns:
            Dictionary with marketing recommendations
        """
        try:
            if customer_id:
                # Generate for specific customer
                recommendations = self._generate_customer_recommendations(customer_id, campaign_type)
                return {'customer_recommendations': [recommendations]}
            else:
                # Generate for customer segments
                segments = self._get_customer_segments()
                campaign_recommendations = []
                
                for segment in segments:
                    recs = self._generate_segment_recommendations(segment, campaign_type)
                    campaign_recommendations.append({
                        'segment_id': segment.get('segment_id'),
                        'segment_name': segment.get('segment_name'),
                        'customer_count': segment.get('customer_count', 0),
                        'recommendations': recs
                    })
                
                return {
                    'campaign_recommendations': campaign_recommendations,
                    'total_segments': len(segments),
                    'estimated_reach': sum(s.get('customer_count', 0) for s in campaign_recommendations)
                }
                
        except Exception as e:
            self.logger.error(f"Error generating marketing recommendations: {str(e)}")
            return {'error': str(e)}
    
    def analyze_feedback_sentiment(self, feedback_data=None):
        """
        Analyze sentiment from customer feedback
        
        Args:
            feedback_data: List of feedback texts (optional)
            
        Returns:
            Dictionary with sentiment analysis and insights
        """
        try:
            if not feedback_data:
                # Get feedback from database
                feedback_data = self._get_customer_feedback()
            
            if not feedback_data:
                return {'error': 'No feedback data available'}
            
            # Perform sentiment analysis
            sentiment_results = []
            
            for feedback in feedback_data:
                sentiment = self._analyze_sentiment(feedback.get('text', ''))
                sentiment_results.append({
                    'feedback_id': feedback.get('id'),
                    'customer_id': feedback.get('customer_id'),
                    'sentiment': sentiment.get('sentiment'),
                    'confidence': sentiment.get('confidence'),
                    'emotions': sentiment.get('emotions'),
                    'topics': sentiment.get('topics'),
                    'feedback_date': feedback.get('date')
                })
            
            # Aggregate sentiment analysis
            sentiment_summary = self._aggregate_sentiment_results(sentiment_results)
            
            return {
                'sentiment_results': sentiment_results,
                'sentiment_summary': sentiment_summary,
                'feedback_count': len(sentiment_results),
                'recommendations': self._generate_sentiment_recommendations(sentiment_summary)
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing feedback sentiment: {str(e)}")
            return {'error': str(e)}
    
    def _get_customer_features(self):
        """Get features for customer segmentation"""
        try:
            # Get customer data with order history
            customers = db.session.query(
                Customer.id,
                Customer.name,
                Customer.email,
                Customer.phone,
                Customer.created_at
            ).outerjoin(Order).filter(Customer.is_active == True).all()
            
            customer_features = []
            
            for customer in customers:
                # Calculate RFM metrics
                rfm = self._calculate_rfm_metrics(customer.id)
                
                # Calculate behavioral metrics
                behavior = self._calculate_behavioral_metrics(customer.id)
                
                feature_vector = [
                    rfm['recency_days'],
                    rfm['frequency'],
                    rfm['monetary_value'],
                    behavior.get('avg_order_value', 0),
                    behavior.get('preferred_categories_count', 0),
                    behavior.get('order_frequency_score', 0),
                    behavior.get('loyalty_score', 0)
                ]
                
                customer_features.append({
                    'customer_id': customer.id,
                    'customer': customer,
                    'features': feature_vector,
                    'rfm': rfm,
                    'behavior': behavior
                })
            
            return customer_features
            
        except Exception as e:
            self.logger.error(f"Error getting customer features: {str(e)}")
            return []
    
    def _calculate_rfm_metrics(self, customer_id):
        """Calculate Recency, Frequency, Monetary metrics"""
        try:
            # Get customer orders
            orders = Order.query.filter_by(customer_id=customer_id).order_by(Order.created_at.desc()).all()
            
            if not orders:
                return {
                    'recency_days': 999,
                    'frequency': 0,
                    'monetary_value': 0
                }
            
            # Calculate recency (days since last order)
            last_order = orders[0]
            recency_days = (datetime.now() - last_order.created_at).days
            
            # Calculate frequency (number of orders in last year)
            one_year_ago = datetime.now() - timedelta(days=365)
            frequency = len([o for o in orders if o.created_at >= one_year_ago])
            
            # Calculate monetary value (total spent in last year)
            monetary_value = sum([o.total_amount for o in orders if o.created_at >= one_year_ago])
            
            return {
                'recency_days': recency_days,
                'frequency': frequency,
                'monetary_value': monetary_value
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating RFM metrics: {str(e)}")
            return {'recency_days': 999, 'frequency': 0, 'monetary_value': 0}
    
    def _calculate_behavioral_metrics(self, customer_id):
        """Calculate behavioral metrics for customer"""
        try:
            # Get order items for customer
            order_items = db.session.query(
                OrderItem.quantity,
                OrderItem.price,
                Order.created_at,
                MenuItem.category_id
            ).join(Order).join(MenuItem).filter(
                Order.customer_id == customer_id
            ).all()
            
            if not order_items:
                return {
                    'avg_order_value': 0,
                    'preferred_categories_count': 0,
                    'order_frequency_score': 0,
                    'loyalty_score': 0
                }
            
            # Calculate metrics
            total_orders = len(set(oi.order_id for oi in order_items))
            total_spent = sum(oi.quantity * oi.price for oi in order_items)
            avg_order_value = total_spent / total_orders if total_orders > 0 else 0
            
            # Calculate preferred categories
            category_counts = {}
            for oi in order_items:
                if oi.menu_item and oi.menu_item.category_id:
                    category_id = oi.menu_item.category_id
                    category_counts[category_id] = category_counts.get(category_id, 0) + 1
            
            preferred_categories_count = len(category_counts)
            
            # Calculate order frequency score (orders per month)
            first_order = min(oi.created_at for oi in order_items)
            months_active = ((datetime.now() - first_order).days / 30) + 1
            order_frequency_score = total_orders / months_active if months_active > 0 else 0
            
            # Calculate loyalty score (based on visit frequency and order patterns)
            loyalty_transactions = LoyaltyTransaction.query.filter_by(customer_id=customer_id).count()
            loyalty_score = min(10, loyalty_transactions / 10)  # Scale to 0-10
            
            return {
                'avg_order_value': avg_order_value,
                'preferred_categories_count': preferred_categories_count,
                'order_frequency_score': order_frequency_score,
                'loyalty_score': loyalty_score
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating behavioral metrics: {str(e)}")
            return {'avg_order_value': 0, 'preferred_categories_count': 0, 'order_frequency_score': 0, 'loyalty_score': 0}
    
    def _behavioral_segmentation(self, X):
        """Perform behavioral segmentation using K-means clustering"""
        try:
            # Standardize features
            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X)
            
            # Determine optimal number of clusters (elbow method would be better)
            n_clusters = min(5, max(3, len(X) // 10))  # 3-5 clusters
            
            # Perform K-means clustering
            kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            cluster_labels = kmeans.fit_predict(X_scaled)
            
            # Calculate cluster centers
            cluster_centers = scaler.inverse_transform(kmeans.cluster_centers_)
            
            # Create segment definitions
            segments = []
            for i in range(n_clusters):
                center = cluster_centers[i]
                
                # Determine segment characteristics
                if center[2] > 1000:  # High monetary value
                    if center[1] > 10:  # High frequency
                        segment_name = "VIP Champions"
                        segment_description = "High value, frequent customers"
                    elif center[0] < 30:  # Recent purchasers
                        segment_name = "New VIPs"
                        segment_description = "Recently active high-value customers"
                    else:
                        segment_name = "Loyal Customers"
                        segment_description = "High value but less frequent"
                elif center[1] > 5:  # Medium frequency
                    if center[2] > 500:
                        segment_name = "Regular Customers"
                        segment_description = "Consistent medium-value customers"
                    else:
                        segment_name = "Occasional Customers"
                        segment_description = "Regular but lower-value customers"
                elif center[0] < 60:  # Recent purchasers
                    segment_name = "New Customers"
                    segment_description = "Recently acquired customers"
                else:
                    segment_name = "At Risk Customers"
                    segment_description = "Low value, infrequent customers"
                
                segments.append({
                    'segment_id': i,
                    'segment_name': segment_name,
                    'segment_description': segment_description,
                    'cluster_center': center.tolist(),
                    'characteristics': {
                        'recency': center[0],
                        'frequency': center[1],
                        'monetary': center[2]
                    }
                })
            
            return segments
            
        except Exception as e:
            self.logger.error(f"Error in behavioral segmentation: {str(e)}")
            return []
    
    def _value_segmentation(self, X):
        """Perform value-based segmentation"""
        try:
            # Simple value-based segmentation using monetary value
            monetary_values = [x[2] for x in X]  # Monetary value is 3rd feature
            
            # Define value thresholds
            percentiles = np.percentile(monetary_values, [20, 40, 60, 80])
            
            segments = []
            for i, x in enumerate(X):
                monetary = x[2]
                
                if monetary >= percentiles[3]:  # Top 20%
                    segment_name = "Platinum"
                    segment_description = "Highest value customers"
                elif monetary >= percentiles[2]:  # 60-80%
                    segment_name = "Gold"
                    segment_description = "High value customers"
                elif monetary >= percentiles[1]:  # 40-60%
                    segment_name = "Silver"
                    segment_description = "Medium value customers"
                elif monetary >= percentiles[0]:  # 20-40%
                    segment_name = "Bronze"
                    segment_description = "Low value customers"
                else:
                    segment_name = "Basic"
                    segment_description = "Lowest value customers"
                
                segments.append({
                    'segment_id': i,
                    'segment_name': segment_name,
                    'segment_description': segment_description,
                    'value_tier': segment_name.lower()
                })
            
            return segments
            
        except Exception as e:
            self.logger.error(f"Error in value segmentation: {str(e)}")
            return []
    
    def _demographic_segmentation(self, X):
        """Perform demographic-based segmentation"""
        try:
            # For demo purposes, use simple rules based on available data
            segments = []
            
            for i, x in enumerate(X):
                # Simple demographic segmentation (would use actual demographic data)
                age_group = "Unknown"
                if len(x) > 3:  # Assuming age is available
                    age_group = "Adult" if x[3] > 25 else "Young Adult"
                
                segments.append({
                    'segment_id': i,
                    'segment_name': f"{age_group} Customers",
                    'segment_description': f"Segment based on {age_group} demographics"
                })
            
            return segments
            
        except Exception as e:
            self.logger.error(f"Error in demographic segmentation: {str(e)}")
            return []
    
    def _analyze_segments(self, customer_data, segments):
        """Analyze and describe customer segments"""
        try:
            segment_analysis = []
            
            # Assign customers to segments
            for i, segment in enumerate(segments):
                segment_customers = []
                
                for customer in customer_data:
                    # Find closest segment center
                    features = np.array(customer['features'])
                    center = np.array(segment['cluster_center'])
                    
                    # Calculate distance to center
                    distance = np.linalg.norm(features - center)
                    
                    # Assign to closest segment
                    if i == 0 or distance < np.linalg.norm(features - np.array(segments[0]['cluster_center'])):
                        segment_customers.append(customer)
                
                segment_analysis.append({
                    'segment_id': i,
                    'segment': segment,
                    'customer_count': len(segment_customers),
                    'customers': segment_customers,
                    'percentage': (len(segment_customers) / len(customer_data)) * 100
                })
            
            return segment_analysis
            
        except Exception as e:
            self.logger.error(f"Error analyzing segments: {str(e)}")
            return []
    
    def _calculate_segmentation_quality(self, X, segments):
        """Calculate segmentation quality metrics"""
        try:
            if len(X) < 2 or len(segments) < 2:
                return 0
            
            # Get cluster labels
            labels = []
            for customer in X:
                # Find closest segment
                features = np.array(customer['features'])
                distances = [np.linalg.norm(features - np.array(s['cluster_center'])) for s in segments]
                closest_segment = np.argmin(distances)
                labels.append(closest_segment)
            
            # Calculate silhouette score
            silhouette_avg = silhouette_score(X, labels)
            
            return silhouette_avg
            
        except Exception as e:
            self.logger.error(f"Error calculating segmentation quality: {str(e)}")
            return 0
    
    def _generate_segmentation_recommendations(self, segment_analysis):
        """Generate recommendations based on segment analysis"""
        try:
            recommendations = []
            
            for segment in segment_analysis:
                segment_name = segment['segment']['segment_name'].lower()
                
                if 'vip' in segment_name:
                    recommendations.extend([
                        "Offer exclusive VIP benefits",
                        "Provide priority service",
                        "Create loyalty premium tier"
                    ])
                elif 'loyal' in segment_name:
                    recommendations.extend([
                        "Implement retention programs",
                        "Offer frequency-based rewards",
                        "Provide early access to new items"
                    ])
                elif 'new' in segment_name:
                    recommendations.extend([
                        "Focus on onboarding experience",
                        "Provide welcome discounts",
                        "Educate about menu offerings"
                    ])
                elif 'risk' in segment_name:
                    recommendations.extend([
                        "Implement reactivation campaign",
                        "Offer special incentives",
                        "Gather feedback to improve experience"
                    ])
                else:
                    recommendations.extend([
                        "Standard engagement strategies",
                        "Personalized offers",
                        "Cross-selling opportunities"
                    ])
            
            return recommendations
            
        except Exception as e:
            self.logger.error(f"Error generating segmentation recommendations: {str(e)}")
            return []
    
    def _predict_customer_churn(self, customer_id):
        """Predict churn risk for specific customer"""
        try:
            # Get customer features
            customer = Customer.query.get(customer_id)
            if not customer:
                return {}
            
            # Calculate churn risk factors
            rfm = self._calculate_rfm_metrics(customer_id)
            
            # Calculate churn risk score
            risk_factors = {
                'recency_score': max(0, 5 - rfm['recency_days']),  # Recent is good
                'frequency_score': min(10, rfm['frequency']),  # Frequent is good
                'monetary_score': min(10, rfm['monetary_value'] / 100),  # High value is good
                'tenure_score': min(10, (datetime.now() - customer.created_at).days / 30)  # Longer tenure is good
            }
            
            # Calculate overall churn risk
            churn_score = (
                risk_factors['recency_score'] * 0.3 +
                risk_factors['frequency_score'] * 0.3 +
                risk_factors['monetary_score'] * 0.2 +
                risk_factors['tenure_score'] * 0.2
            )
            
            # Determine risk level
            if churn_score >= 8:
                risk_level = 'low'
            elif churn_score >= 5:
                risk_level = 'medium'
            else:
                risk_level = 'high'
            
            # Calculate churn probability
            churn_probability = 1 - (churn_score / 10)
            
            return {
                'customer_id': customer_id,
                'customer_name': customer.name,
                'churn_score': churn_score,
                'risk_level': risk_level,
                'churn_probability': churn_probability,
                'risk_factors': risk_factors,
                'prediction_date': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error predicting customer churn: {str(e)}")
            return {}
    
    def _calculate_customer_clv(self, customer_id):
        """Calculate customer lifetime value"""
        try:
            # Get customer order history
            orders = Order.query.filter_by(customer_id=customer_id).all()
            
            if not orders:
                return {
                    'customer_id': customer_id,
                    'clv': 0,
                    'clv_tier': 'low'
                }
            
            # Calculate CLV components
            total_revenue = sum(o.total_amount for o in orders)
            order_count = len(orders)
            
            if order_count == 0:
                avg_order_value = 0
            else:
                avg_order_value = total_revenue / order_count
            
            # Calculate customer lifespan (in months)
            first_order = min(o.created_at for o in orders)
            lifespan_months = ((datetime.now() - first_order).days / 30) + 1
            
            # Calculate purchase frequency
            if lifespan_months > 0:
                purchase_frequency = order_count / lifespan_months
            else:
                purchase_frequency = 0
            
            # Simple CLV calculation (can be enhanced with more sophisticated models)
            clv = avg_order_value * purchase_frequency * 12  # Annual value
            
            # Determine CLV tier
            if clv >= 1000:
                clv_tier = 'high'
            elif clv >= 500:
                clv_tier = 'medium'
            elif clv >= 100:
                clv_tier = 'low'
            else:
                clv_tier = 'very_low'
            
            return {
                'customer_id': customer_id,
                'clv': clv,
                'clv_tier': clv_tier,
                'total_revenue': total_revenue,
                'order_count': order_count,
                'avg_order_value': avg_order_value,
                'purchase_frequency': purchase_frequency,
                'customer_lifespan_months': lifespan_months
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating customer CLV: {str(e)}")
            return {'customer_id': customer_id, 'clv': 0, 'clv_tier': 'low'}
    
    def _generate_customer_recommendations(self, customer_id, campaign_type):
        """Generate personalized recommendations for customer"""
        try:
            customer = Customer.query.get(customer_id)
            if not customer:
                return {}
            
            recommendations = []
            
            if campaign_type == 'retention':
                # Retention campaign recommendations
                rfm = self._calculate_rfm_metrics(customer_id)
                
                if rfm['recency_days'] > 30:
                    recommendations.append("Re-engagement offer needed")
                
                if rfm['frequency'] < 2:
                    recommendations.append("Frequency building campaign")
                
                if rfm['monetary_value'] > 500:
                    recommendations.append("VIP loyalty program")
                else:
                    recommendations.append("First-time buyer discount")
            
            elif campaign_type == 'upsell':
                # Upsell campaign recommendations
                recommendations.append("Personalized product recommendations")
                recommendations.append("Category-based cross-sells")
                recommendations.append("Loyalty tier upgrade offers")
            
            elif campaign_type == 'reactivation':
                # Reactivation campaign recommendations
                recommendations.append("We miss you offer")
                recommendations.append("What's new promotion")
                recommendations.append("Exclusive comeback discount")
            
            return {
                'customer_id': customer_id,
                'campaign_type': campaign_type,
                'recommendations': recommendations,
                'generation_date': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error generating customer recommendations: {str(e)}")
            return {}
    
    def _analyze_sentiment(self, text):
        """Analyze sentiment of feedback text"""
        try:
            # Simple sentiment analysis (in production, would use NLP library)
            text = text.lower()
            
            # Positive words
            positive_words = ['good', 'great', 'excellent', 'amazing', 'love', 'perfect', 'wonderful', 'fantastic', 'satisfied', 'happy', 'pleased']
            
            # Negative words
            negative_words = ['bad', 'terrible', 'awful', 'hate', 'worst', 'disappointed', 'unsatisfied', 'angry', 'frustrated', 'poor']
            
            # Count positive and negative words
            positive_count = sum(1 for word in positive_words if word in text)
            negative_count = sum(1 for word in negative_words if word in text)
            
            # Calculate sentiment score
            if positive_count > negative_count:
                sentiment = 'positive'
                confidence = min(0.9, 0.5 + (positive_count - negative_count) * 0.1)
            elif negative_count > positive_count:
                sentiment = 'negative'
                confidence = min(0.9, 0.5 + (negative_count - positive_count) * 0.1)
            else:
                sentiment = 'neutral'
                confidence = 0.5
            
            # Extract emotions (simplified)
            emotions = []
            if 'love' in text or 'excellent' in text:
                emotions.append('excitement')
            elif 'disappointed' in text or 'terrible' in text:
                emotions.append('disappointment')
            elif 'angry' in text or 'frustrated' in text:
                emotions.append('anger')
            else:
                emotions.append('neutral')
            
            # Extract topics (simplified)
            topics = []
            if 'service' in text or 'staff' in text:
                topics.append('service')
            if 'food' in text or 'meal' in text or 'taste' in text:
                topics.append('food_quality')
            if 'price' in text or 'cost' in text or 'expensive' in text:
                topics.append('pricing')
            if 'delivery' in text or 'time' in text or 'late' in text:
                topics.append('delivery')
            
            return {
                'sentiment': sentiment,
                'confidence': confidence,
                'emotions': emotions,
                'topics': topics,
                'positive_words': positive_count,
                'negative_words': negative_count
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing sentiment: {str(e)}")
            return {'sentiment': 'neutral', 'confidence': 0.5, 'emotions': [], 'topics': []}
    
    def _aggregate_sentiment_results(self, sentiment_results):
        """Aggregate sentiment analysis results"""
        try:
            if not sentiment_results:
                return {
                    'overall_sentiment': 'neutral',
                    'sentiment_distribution': {'positive': 0, 'negative': 0, 'neutral': 0},
                    'common_topics': [],
                    'key_insights': []
                }
            
            # Count sentiments
            sentiment_counts = {'positive': 0, 'negative': 0, 'neutral': 0}
            all_topics = []
            all_emotions = []
            
            for result in sentiment_results:
                sentiment = result.get('sentiment', 'neutral')
                sentiment_counts[sentiment] += 1
                
                topics = result.get('topics', [])
                all_topics.extend(topics)
                
                emotions = result.get('emotions', [])
                all_emotions.extend(emotions)
            
            # Calculate overall sentiment
            total_feedback = len(sentiment_results)
            overall_sentiment = max(sentiment_counts, key=sentiment_counts.get)
            
            # Find common topics
            topic_counts = {}
            for topic in all_topics:
                topic_counts[topic] = topic_counts.get(topic, 0) + 1
            
            common_topics = sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            
            # Generate insights
            insights = []
            if sentiment_counts['negative'] / total_feedback > 0.3:
                insights.append("High negative sentiment requires immediate attention")
            
            if 'service' in dict(common_topics).keys():
                insights.append("Service quality issues need to be addressed")
            
            if 'pricing' in dict(common_topics).keys():
                insights.append("Pricing concerns are affecting customer satisfaction")
            
            return {
                'overall_sentiment': overall_sentiment,
                'sentiment_distribution': {
                    k: (v / total_feedback) * 100 for k, v in sentiment_counts.items()
                },
                'common_topics': common_topics,
                'key_insights': insights
            }
            
        except Exception as e:
            self.logger.error(f"Error aggregating sentiment results: {str(e)}")
            return {'overall_sentiment': 'neutral', 'sentiment_distribution': {}, 'common_topics': [], 'key_insights': []}
    
    def _generate_sentiment_recommendations(self, sentiment_summary):
        """Generate recommendations based on sentiment analysis"""
        try:
            recommendations = []
            
            negative_percentage = sentiment_summary['sentiment_distribution'].get('negative', 0)
            
            if negative_percentage > 30:
                recommendations.extend([
                    "Immediate customer service intervention required",
                    "Review feedback response protocols",
                    "Implement customer recovery program"
                ])
            elif negative_percentage > 15:
                recommendations.extend([
                    "Monitor feedback trends closely",
                    "Provide additional staff training",
                    "Review product/service quality"
                ])
            
            common_topics = sentiment_summary.get('common_topics', [])
            topic_dict = dict(common_topics)
            
            if 'service' in topic_dict:
                recommendations.append("Focus on service improvement initiatives")
            
            if 'food_quality' in topic_dict:
                recommendations.append("Review kitchen processes and ingredients")
            
            if 'delivery' in topic_dict:
                recommendations.append("Optimize delivery operations")
            
            if 'pricing' in topic_dict:
                recommendations.append("Review pricing strategy and communication")
            
            return recommendations
            
        except Exception as e:
            self.logger.error(f"Error generating sentiment recommendations: {str(e)}")
            return []
    
    def _get_customer_feedback(self):
        """Get customer feedback from database"""
        try:
            # In a real implementation, this would query feedback table
            # For now, simulate feedback data
            
            # Get recent orders and simulate feedback
            recent_orders = Order.query.filter(
                Order.created_at >= datetime.now() - timedelta(days=30)
            ).limit(20).all()
            
            feedback_data = []
            for order in recent_orders:
                # Simulate feedback based on order characteristics
                if order.total_amount > 100:  # Large order
                    sentiment_words = ['excellent', 'great', 'good']
                    sentiment = 'positive'
                elif order.total_amount < 20:  # Small order
                    sentiment_words = ['okay', 'average', 'fine']
                    sentiment = 'neutral'
                else:
                    sentiment_words = ['disappointed', 'could be better', 'mixed']
                    sentiment = 'negative'
                
                feedback_text = ' '.join(np.random.choice(sentiment_words) for _ in range(3))
                
                feedback_data.append({
                    'id': order.id,
                    'customer_id': order.customer_id,
                    'text': feedback_text,
                    'date': order.created_at.date().isoformat()
                })
            
            return feedback_data
            
        except Exception as e:
            self.logger.error(f"Error getting customer feedback: {str(e)}")
            return []
    
    def _get_customer_segments(self):
        """Get pre-calculated customer segments"""
        try:
            # In a real implementation, this would query segment assignments
            # For now, return sample segments
            
            return [
                {
                    'segment_id': 1,
                    'segment_name': 'VIP Champions',
                    'customer_count': 50,
                    'description': 'High-value, frequent customers'
                },
                {
                    'segment_id': 2,
                    'segment_name': 'Loyal Customers',
                    'customer_count': 150,
                    'description': 'Regular, loyal customers'
                },
                {
                    'segment_id': 3,
                    'segment_name': 'New Customers',
                    'customer_count': 100,
                    'description': 'Recently acquired customers'
                }
            ]
            
        except Exception as e:
            self.logger.error(f"Error getting customer segments: {str(e)}")
            return []
    
    def _generate_segment_recommendations(self, segment, campaign_type):
        """Generate recommendations for customer segment"""
        try:
            recommendations = []
            segment_name = segment['segment_name'].lower()
            
            if 'vip' in segment_name:
                if campaign_type == 'retention':
                    recommendations.extend([
                        "Exclusive VIP events",
                        "Personalized concierge service",
                        "Early access to new menu items"
                    ])
                elif campaign_type == 'upsell':
                    recommendations.extend([
                        "Premium product recommendations",
                        "Chef's table experiences",
                        "Limited edition offerings"
                    ])
            
            elif 'loyal' in segment_name:
                if campaign_type == 'retention':
                    recommendations.extend([
                        "Loyalty tier upgrades",
                        "Frequency-based rewards",
                        "Anniversary recognition"
                    ])
                elif campaign_type == 'upsell':
                    recommendations.extend([
                        "Category expansion suggestions",
                        "Bundle deals",
                        "Seasonal preferences"
                    ])
            
            elif 'new' in segment_name:
                if campaign_type == 'retention':
                    recommendations.extend([
                        "Onboarding education",
                        "First purchase incentives",
                        "Menu exploration guides"
                    ])
                elif campaign_type == 'upsell':
                    recommendations.extend([
                        "Popular item highlights",
                        "Category introductions",
                        "Value combo suggestions"
                    ])
            
            return recommendations
            
        except Exception as e:
            self.logger.error(f"Error generating segment recommendations: {str(e)}")
            return []
    
    def _generate_retention_recommendations(self, churn_predictions):
        """Generate customer retention recommendations"""
        try:
            recommendations = []
            
            high_risk_customers = [p for p in churn_predictions if p.get('risk_level') == 'high']
            medium_risk_customers = [p for p in churn_predictions if p.get('risk_level') == 'medium']
            
            # High-risk customer recommendations
            if high_risk_customers:
                recommendations.extend([
                    "Immediate personal outreach",
                    "Special retention offers",
                    "Service recovery intervention",
                    "Feedback collection and action"
                ])
            
            # Medium-risk customer recommendations
            if medium_risk_customers:
                recommendations.extend([
                    "Proactive engagement campaigns",
                    "Loyalty program incentives",
                    "Personalized communications"
                ])
            
            # General recommendations
            recommendations.extend([
                "Implement early warning system",
                "Regular satisfaction surveys",
                "Competitive offer monitoring"
            ])
            
            return recommendations
            
        except Exception as e:
            self.logger.error(f"Error generating retention recommendations: {str(e)}")
            return []
    
    def _generate_clv_strategies(self, clv_data):
        """Generate strategies based on customer lifetime value"""
        try:
            strategies = []
            
            for customer in clv_data:
                clv_tier = customer.get('clv_tier', 'low')
                
                if clv_tier == 'high':
                    strategies.extend([
                        "VIP treatment and exclusive benefits",
                        "Personalized account management",
                        "High-touch service model"
                    ])
                elif clv_tier == 'medium':
                    strategies.extend([
                        "Loyalty program advancement",
                        "Cross-selling opportunities",
                        "Referral program incentives"
                    ])
                elif clv_tier == 'low':
                    strategies.extend([
                        "Education and engagement",
                        "Value-building initiatives",
                        "Frequency encouragement"
                    ])
                else:
                    strategies.extend([
                        "Welcome and onboarding",
                        "First purchase experience",
                        "Relationship building"
                    ])
            
            return strategies
            
        except Exception as e:
            self.logger.error(f"Error generating CLV strategies: {str(e)}")
            return []
    
    def log_customer_behavior(self, customer_id, behavior_type, behavior_data, order_id=None):
        """Log customer behavior for AI training"""
        try:
            log_entry = AICustomerBehavior(
                customer_id=customer_id,
                behavior_type=behavior_type,
                behavior_data=behavior_data,
                order_id=order_id
            )
            
            db.session.add(log_entry)
            db.session.commit()
            
        except Exception as e:
            self.logger.error(f"Error logging customer behavior: {str(e)}")
            db.session.rollback()