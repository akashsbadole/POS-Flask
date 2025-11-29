"""
AI Performance Monitoring System
Monitors AI model performance, prediction accuracy, and system health including:
- Model performance tracking
- Prediction accuracy monitoring
- System health checks
- Performance alerts and notifications
- Model drift detection
- A/B testing results analysis
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
import json
import logging
from collections import defaultdict
import statistics

from app import db
from app.models.ai_models import (
    AIModel, AIPredictionLog, AIConfiguration, AITrainingJob,
    AIABTest, AIABTestParticipant, AIRecommendation
)
from app.models.notification import Notification


class AIPerformanceMonitor:
    """AI Performance Monitoring System"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.alert_thresholds = {
            'accuracy_min': 0.7,
            'prediction_confidence_min': 0.6,
            'response_time_max': 2.0,  # seconds
            'error_rate_max': 0.05,  # 5%
            'drift_threshold': 0.1  # 10% performance drop
        }
    
    def get_model_performance_metrics(self, model_type: str = None, days: int = 30) -> Dict[str, Any]:
        """Get performance metrics for AI models"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            # Get models
            if model_type:
                models = AIModel.query.filter_by(model_type=model_type).all()
            else:
                models = AIModel.query.all()
            
            performance_data = {}
            
            for model in models:
                # Get prediction logs for this model
                predictions = AIPredictionLog.query.filter(
                    AIPredictionLog.model_type == model.model_type,
                    AIPredictionLog.created_at >= start_date,
                    AIPredictionLog.created_at <= end_date
                ).all()
                
                if not predictions:
                    continue
                
                # Calculate metrics
                total_predictions = len(predictions)
                avg_confidence = np.mean([p.confidence_score for p in predictions])
                confidence_std = np.std([p.confidence_score for p in predictions])
                
                # Get predictions with high confidence
                high_confidence_predictions = [p for p in predictions if p.confidence_score >= 0.8]
                high_confidence_rate = len(high_confidence_predictions) / total_predictions
                
                # Calculate error rate (simplified - would need actual feedback)
                error_rate = self._calculate_error_rate(predictions)
                
                # Response time (if available)
                response_times = []
                for pred in predictions:
                    if pred.metadata and 'response_time' in pred.metadata:
                        response_times.append(pred.metadata['response_time'])
                
                avg_response_time = np.mean(response_times) if response_times else None
                
                # Model performance from database
                db_metrics = model.performance_metrics or {}
                
                performance_data[model.model_type] = {
                    'model_id': model.id,
                    'model_name': model.name,
                    'algorithm': model.algorithm,
                    'version': model.version,
                    'is_active': model.is_active,
                    'is_production': model.is_production,
                    'total_predictions': total_predictions,
                    'avg_confidence': float(avg_confidence),
                    'confidence_std': float(confidence_std),
                    'high_confidence_rate': float(high_confidence_rate),
                    'error_rate': float(error_rate),
                    'avg_response_time': float(avg_response_time) if avg_response_time else None,
                    'db_metrics': db_metrics,
                    'last_trained': model.last_trained_at.isoformat() if model.last_trained_at else None,
                    'last_evaluated': model.last_evaluated_at.isoformat() if model.last_evaluated_at else None
                }
            
            return {
                'success': True,
                'performance_data': performance_data,
                'period_days': days,
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting model performance metrics: {str(e)}")
            return {'error': str(e)}
    
    def detect_model_drift(self, model_type: str = None, days: int = 7) -> Dict[str, Any]:
        """Detect model drift and performance degradation"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            baseline_start = end_date - timedelta(days=days*2)
            baseline_end = start_date
            
            # Get models
            if model_type:
                models = AIModel.query.filter_by(model_type=model_type).all()
            else:
                models = AIModel.query.all()
            
            drift_results = {}
            
            for model in models:
                # Get recent predictions
                recent_predictions = AIPredictionLog.query.filter(
                    AIPredictionLog.model_type == model.model_type,
                    AIPredictionLog.created_at >= start_date,
                    AIPredictionLog.created_at <= end_date
                ).all()
                
                # Get baseline predictions
                baseline_predictions = AIPredictionLog.query.filter(
                    AIPredictionLog.model_type == model.model_type,
                    AIPredictionLog.created_at >= baseline_start,
                    AIPredictionLog.created_at <= baseline_end
                ).all()
                
                if not recent_predictions or not baseline_predictions:
                    continue
                
                # Calculate metrics
                recent_confidence = np.mean([p.confidence_score for p in recent_predictions])
                baseline_confidence = np.mean([p.confidence_score for p in baseline_predictions])
                
                recent_error_rate = self._calculate_error_rate(recent_predictions)
                baseline_error_rate = self._calculate_error_rate(baseline_predictions)
                
                # Calculate drift
                confidence_drift = abs(recent_confidence - baseline_confidence)
                error_drift = abs(recent_error_rate - baseline_error_rate)
                
                # Determine if drift is significant
                significant_drift = (
                    confidence_drift > self.alert_thresholds['drift_threshold'] or
                    error_drift > self.alert_thresholds['drift_threshold']
                )
                
                drift_results[model.model_type] = {
                    'model_id': model.id,
                    'model_name': model.name,
                    'recent_confidence': float(recent_confidence),
                    'baseline_confidence': float(baseline_confidence),
                    'confidence_drift': float(confidence_drift),
                    'recent_error_rate': float(recent_error_rate),
                    'baseline_error_rate': float(baseline_error_rate),
                    'error_drift': float(error_drift),
                    'significant_drift': significant_drift,
                    'drift_detected': significant_drift,
                    'recommendation': self._get_drift_recommendation(significant_drift, confidence_drift, error_drift)
                }
                
                # Create alert if significant drift detected
                if significant_drift:
                    self._create_drift_alert(model, drift_results[model.model_type])
            
            return {
                'success': True,
                'drift_results': drift_results,
                'period_days': days,
                'drift_threshold': self.alert_thresholds['drift_threshold'],
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error detecting model drift: {str(e)}")
            return {'error': str(e)}
    
    def analyze_ab_test_results(self, test_id: int = None) -> Dict[str, Any]:
        """Analyze A/B test results and statistical significance"""
        try:
            if test_id:
                # Analyze specific test
                test = AIABTest.query.get(test_id)
                if not test:
                    return {'error': 'A/B test not found'}
                
                tests = [test]
            else:
                # Analyze all active tests
                tests = AIABTest.query.filter_by(is_active=True).all()
            
            results = {}
            
            for test in tests:
                # Get participants
                participants = AIABTestParticipant.query.filter_by(test_id=test.id).all()
                
                if not participants:
                    continue
                
                # Group by variant
                variant_data = defaultdict(list)
                
                for participant in participants:
                    variant_data[participant.variant].append({
                        'participant_id': participant.participant_id,
                        'metrics': participant.metrics or {},
                        'created_at': participant.created_at
                    })
                
                # Analyze each variant
                variant_analysis = {}
                
                for variant, participant_list in variant_data.items():
                    # Calculate metrics
                    conversion_rate = self._calculate_conversion_rate(participant_list)
                    avg_value = self._calculate_average_value(participant_list)
                    engagement_rate = self._calculate_engagement_rate(participant_list)
                    
                    variant_analysis[variant] = {
                        'participant_count': len(participant_list),
                        'conversion_rate': float(conversion_rate),
                        'avg_value': float(avg_value),
                        'engagement_rate': float(engagement_rate),
                        'metrics_summary': self._summarize_metrics(participant_list)
                    }
                
                # Statistical significance test
                significance_test = self._perform_significance_test(variant_data)
                
                # Determine winner
                winner = self._determine_test_winner(variant_analysis, significance_test)
                
                results[test.id] = {
                    'test_name': test.name,
                    'test_description': test.description,
                    'start_date': test.start_date.isoformat() if test.start_date else None,
                    'end_date': test.end_date.isoformat() if test.end_date else None,
                    'status': test.status,
                    'variant_analysis': variant_analysis,
                    'significance_test': significance_test,
                    'winner': winner,
                    'recommendation': self._get_ab_test_recommendation(test, variant_analysis, significance_test)
                }
            
            return {
                'success': True,
                'ab_test_results': results,
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing A/B test results: {str(e)}")
            return {'error': str(e)}
    
    def get_prediction_accuracy_analysis(self, model_type: str = None, days: int = 30) -> Dict[str, Any]:
        """Analyze prediction accuracy and confidence distribution"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            # Get prediction logs
            if model_type:
                predictions = AIPredictionLog.query.filter(
                    AIPredictionLog.model_type == model_type,
                    AIPredictionLog.created_at >= start_date,
                    AIPredictionLog.created_at <= end_date
                ).all()
            else:
                predictions = AIPredictionLog.query.filter(
                    AIPredictionLog.created_at >= start_date,
                    AIPredictionLog.created_at <= end_date
                ).all()
            
            if not predictions:
                return {'error': 'No prediction data found for the specified period'}
            
            # Group by model type
            model_predictions = defaultdict(list)
            for pred in predictions:
                model_predictions[pred.model_type].append(pred)
            
            accuracy_analysis = {}
            
            for m_type, pred_list in model_predictions.items():
                # Confidence distribution
                confidence_scores = [p.confidence_score for p in pred_list]
                
                # Confidence bins
                confidence_bins = {
                    'very_low': len([c for c in confidence_scores if c < 0.2]),
                    'low': len([c for c in confidence_scores if 0.2 <= c < 0.4]),
                    'medium': len([c for c in confidence_scores if 0.4 <= c < 0.6]),
                    'high': len([c for c in confidence_scores if 0.6 <= c < 0.8]),
                    'very_high': len([c for c in confidence_scores if c >= 0.8])
                }
                
                # Calculate statistics
                avg_confidence = np.mean(confidence_scores)
                confidence_std = np.std(confidence_scores)
                min_confidence = np.min(confidence_scores)
                max_confidence = np.max(confidence_scores)
                
                # Error rate by confidence level
                error_by_confidence = self._calculate_error_by_confidence(pred_list)
                
                # Prediction volume over time
                prediction_timeline = self._create_prediction_timeline(pred_list)
                
                accuracy_analysis[m_type] = {
                    'total_predictions': len(pred_list),
                    'avg_confidence': float(avg_confidence),
                    'confidence_std': float(confidence_std),
                    'min_confidence': float(min_confidence),
                    'max_confidence': float(max_confidence),
                    'confidence_distribution': confidence_bins,
                    'error_by_confidence': error_by_confidence,
                    'prediction_timeline': prediction_timeline,
                    'performance_trend': self._calculate_performance_trend(pred_list)
                }
            
            return {
                'success': True,
                'accuracy_analysis': accuracy_analysis,
                'period_days': days,
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing prediction accuracy: {str(e)}")
            return {'error': str(e)}
    
    def get_system_health_status(self) -> Dict[str, Any]:
        """Get overall AI system health status"""
        try:
            health_status = {
                'overall_status': 'healthy',
                'timestamp': datetime.now().isoformat(),
                'components': {}
            }
            
            # Check model health
            models = AIModel.query.filter_by(is_production=True).all()
            model_health = {}
            
            for model in models:
                # Get recent predictions
                recent_predictions = AIPredictionLog.query.filter(
                    AIPredictionLog.model_type == model.model_type,
                    AIPredictionLog.created_at >= datetime.now() - timedelta(hours=24)
                ).all()
                
                if not recent_predictions:
                    model_health[model.model_type] = {
                        'status': 'warning',
                        'message': 'No recent predictions'
                    }
                    continue
                
                # Calculate metrics
                avg_confidence = np.mean([p.confidence_score for p in recent_predictions])
                error_rate = self._calculate_error_rate(recent_predictions)
                
                # Determine status
                if (avg_confidence < self.alert_thresholds['prediction_confidence_min'] or
                    error_rate > self.alert_thresholds['error_rate_max']):
                    status = 'critical'
                elif (avg_confidence < self.alert_thresholds['prediction_confidence_min'] * 1.2 or
                      error_rate > self.alert_thresholds['error_rate_max'] * 0.8):
                    status = 'warning'
                else:
                    status = 'healthy'
                
                model_health[model.model_type] = {
                    'status': status,
                    'avg_confidence': float(avg_confidence),
                    'error_rate': float(error_rate),
                    'predictions_24h': len(recent_predictions)
                }
            
            health_status['components']['models'] = model_health
            
            # Check training jobs
            recent_training_jobs = AITrainingJob.query.filter(
                AITrainingJob.started_at >= datetime.now() - timedelta(hours=24)
            ).all()
            
            failed_jobs = [job for job in recent_training_jobs if job.status == 'failed']
            running_jobs = [job for job in recent_training_jobs if job.status == 'running']
            
            training_health = {
                'status': 'critical' if failed_jobs else 'warning' if running_jobs else 'healthy',
                'total_jobs_24h': len(recent_training_jobs),
                'failed_jobs': len(failed_jobs),
                'running_jobs': len(running_jobs),
                'success_rate': (len(recent_training_jobs) - len(failed_jobs)) / len(recent_training_jobs) if recent_training_jobs else 1.0
            }
            
            health_status['components']['training'] = training_health
            
            # Check A/B tests
            active_tests = AIABTest.query.filter_by(is_active=True).all()
            
            ab_test_health = {
                'status': 'healthy',
                'active_tests': len(active_tests),
                'message': f'{len(active_tests)} active A/B tests'
            }
            
            health_status['components']['ab_tests'] = ab_test_health
            
            # Determine overall status
            component_statuses = [comp['status'] for comp in health_status['components'].values()]
            
            if 'critical' in component_statuses:
                health_status['overall_status'] = 'critical'
            elif 'warning' in component_statuses:
                health_status['overall_status'] = 'warning'
            else:
                health_status['overall_status'] = 'healthy'
            
            return health_status
            
        except Exception as e:
            self.logger.error(f"Error getting system health status: {str(e)}")
            return {
                'overall_status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def _calculate_error_rate(self, predictions: List) -> float:
        """Calculate error rate for predictions (simplified)"""
        try:
            # In a real implementation, this would compare predictions with actual outcomes
            # For now, use confidence score as a proxy
            if not predictions:
                return 0.0
            
            # Assume predictions with confidence < 0.5 are more likely to be wrong
            low_confidence_predictions = [p for p in predictions if p.confidence_score < 0.5]
            error_rate = len(low_confidence_predictions) / len(predictions)
            
            return error_rate
            
        except Exception as e:
            self.logger.error(f"Error calculating error rate: {str(e)}")
            return 0.0
    
    def _calculate_error_by_confidence(self, predictions: List) -> Dict[str, float]:
        """Calculate error rate by confidence level"""
        try:
            confidence_ranges = [
                (0.0, 0.2, 'very_low'),
                (0.2, 0.4, 'low'),
                (0.4, 0.6, 'medium'),
                (0.6, 0.8, 'high'),
                (0.8, 1.0, 'very_high')
            ]
            
            error_by_confidence = {}
            
            for min_conf, max_conf, label in confidence_ranges:
                range_predictions = [p for p in predictions if min_conf <= p.confidence_score < max_conf]
                
                if range_predictions:
                    error_rate = self._calculate_error_rate(range_predictions)
                    error_by_confidence[label] = float(error_rate)
                else:
                    error_by_confidence[label] = 0.0
            
            return error_by_confidence
            
        except Exception as e:
            self.logger.error(f"Error calculating error by confidence: {str(e)}")
            return {}
    
    def _create_prediction_timeline(self, predictions: List) -> List[Dict]:
        """Create prediction timeline for trend analysis"""
        try:
            # Group predictions by hour
            hourly_counts = defaultdict(int)
            hourly_confidence = defaultdict(list)
            
            for pred in predictions:
                hour_key = pred.created_at.strftime('%Y-%m-%d %H:00:00')
                hourly_counts[hour_key] += 1
                hourly_confidence[hour_key].append(pred.confidence_score)
            
            # Create timeline
            timeline = []
            for hour in sorted(hourly_counts.keys()):
                avg_confidence = np.mean(hourly_confidence[hour]) if hourly_confidence[hour] else 0
                
                timeline.append({
                    'hour': hour,
                    'predictions': hourly_counts[hour],
                    'avg_confidence': float(avg_confidence)
                })
            
            return timeline[-24:]  # Return last 24 hours
            
        except Exception as e:
            self.logger.error(f"Error creating prediction timeline: {str(e)}")
            return []
    
    def _calculate_performance_trend(self, predictions: List) -> Dict[str, float]:
        """Calculate performance trend over time"""
        try:
            if len(predictions) < 10:
                return {'trend': 0.0, 'direction': 'stable'}
            
            # Split predictions into two halves
            mid_point = len(predictions) // 2
            first_half = predictions[:mid_point]
            second_half = predictions[mid_point:]
            
            # Calculate average confidence for each half
            first_confidence = np.mean([p.confidence_score for p in first_half])
            second_confidence = np.mean([p.confidence_score for p in second_half])
            
            # Calculate trend
            trend = second_confidence - first_confidence
            
            if trend > 0.05:
                direction = 'improving'
            elif trend < -0.05:
                direction = 'degrading'
            else:
                direction = 'stable'
            
            return {
                'trend': float(trend),
                'direction': direction,
                'first_half_confidence': float(first_confidence),
                'second_half_confidence': float(second_confidence)
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating performance trend: {str(e)}")
            return {'trend': 0.0, 'direction': 'unknown'}
    
    def _calculate_conversion_rate(self, participants: List) -> float:
        """Calculate conversion rate for A/B test participants"""
        try:
            if not participants:
                return 0.0
            
            conversions = 0
            for participant in participants:
                metrics = participant.metrics or {}
                if metrics.get('converted', False):
                    conversions += 1
            
            return conversions / len(participants)
            
        except Exception as e:
            self.logger.error(f"Error calculating conversion rate: {str(e)}")
            return 0.0
    
    def _calculate_average_value(self, participants: List) -> float:
        """Calculate average value for A/B test participants"""
        try:
            if not participants:
                return 0.0
            
            total_value = 0
            for participant in participants:
                metrics = participant.metrics or {}
                total_value += metrics.get('value', 0)
            
            return total_value / len(participants)
            
        except Exception as e:
            self.logger.error(f"Error calculating average value: {str(e)}")
            return 0.0
    
    def _calculate_engagement_rate(self, participants: List) -> float:
        """Calculate engagement rate for A/B test participants"""
        try:
            if not participants:
                return 0.0
            
            engaged_count = 0
            for participant in participants:
                metrics = participant.metrics or {}
                if metrics.get('engaged', False):
                    engaged_count += 1
            
            return engaged_count / len(participants)
            
        except Exception as e:
            self.logger.error(f"Error calculating engagement rate: {str(e)}")
            return 0.0
    
    def _summarize_metrics(self, participants: List) -> Dict[str, Any]:
        """Summarize metrics for A/B test participants"""
        try:
            if not participants:
                return {}
            
            all_metrics = defaultdict(list)
            
            for participant in participants:
                metrics = participant.metrics or {}
                for key, value in metrics.items():
                    if isinstance(value, (int, float)):
                        all_metrics[key].append(value)
            
            summary = {}
            for key, values in all_metrics.items():
                if values:
                    summary[key] = {
                        'mean': float(np.mean(values)),
                        'std': float(np.std(values)),
                        'min': float(np.min(values)),
                        'max': float(np.max(values))
                    }
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Error summarizing metrics: {str(e)}")
            return {}
    
    def _perform_significance_test(self, variant_data: Dict) -> Dict[str, Any]:
        """Perform statistical significance test for A/B test"""
        try:
            if len(variant_data) < 2:
                return {'significant': False, 'message': 'Need at least 2 variants for significance test'}
            
            # Get conversion rates for each variant
            conversion_rates = {}
            sample_sizes = {}
            
            for variant, participants in variant_data.items():
                conversion_rates[variant] = self._calculate_conversion_rate(participants)
                sample_sizes[variant] = len(participants)
            
            # Simple chi-square test for conversion rates
            # In a real implementation, use proper statistical tests
            variants = list(variant_data.keys())
            if len(variants) == 2:
                # Two-sample test
                rate1, rate2 = conversion_rates[variants[0]], conversion_rates[variants[1]]
                size1, size2 = sample_sizes[variants[0]], sample_sizes[variants[1]]
                
                # Calculate pooled standard error
                pooled_rate = (rate1 * size1 + rate2 * size2) / (size1 + size2)
                se = np.sqrt(pooled_rate * (1 - pooled_rate) * (1/size1 + 1/size2))
                
                # Calculate z-score
                if se > 0:
                    z_score = abs(rate1 - rate2) / se
                    # Approximate p-value (two-tailed)
                    p_value = 2 * (1 - self._normal_cdf(abs(z_score)))
                    significant = p_value < 0.05
                else:
                    z_score = 0
                    p_value = 1.0
                    significant = False
                
                return {
                    'significant': significant,
                    'p_value': float(p_value),
                    'z_score': float(z_score),
                    'test_type': 'two_sample_z_test',
                    'conversion_rates': conversion_rates,
                    'sample_sizes': sample_sizes
                }
            else:
                # Multiple variants - would need ANOVA or similar
                return {
                    'significant': False,
                    'message': 'Multiple variant significance testing not implemented',
                    'conversion_rates': conversion_rates,
                    'sample_sizes': sample_sizes
                }
                
        except Exception as e:
            self.logger.error(f"Error performing significance test: {str(e)}")
            return {'significant': False, 'error': str(e)}
    
    def _normal_cdf(self, x: float) -> float:
        """Approximate normal CDF"""
        return 0.5 * (1 + np.tanh(np.sqrt(2/np.pi) * (x + 0.044715 * np.power(x, 3))))
    
    def _determine_test_winner(self, variant_analysis: Dict, significance_test: Dict) -> Optional[str]:
        """Determine winner of A/B test"""
        try:
            if not significance_test.get('significant', False):
                return None
            
            # Find variant with highest conversion rate
            best_variant = None
            best_rate = -1
            
            for variant, analysis in variant_analysis.items():
                if analysis['conversion_rate'] > best_rate:
                    best_rate = analysis['conversion_rate']
                    best_variant = variant
            
            return best_variant
            
        except Exception as e:
            self.logger.error(f"Error determining test winner: {str(e)}")
            return None
    
    def _get_ab_test_recommendation(self, test, variant_analysis: Dict, significance_test: Dict) -> str:
        """Get recommendation for A/B test"""
        try:
            if not significance_test.get('significant', False):
                return "Continue test or conclude no significant difference"
            
            winner = self._determine_test_winner(variant_analysis, significance_test)
            
            if winner:
                winner_analysis = variant_analysis[winner]
                return f"Implement variant '{winner}' with {winner_analysis['conversion_rate']:.2%} conversion rate"
            else:
                return "No clear winner - consider running test longer or testing different variants"
                
        except Exception as e:
            self.logger.error(f"Error getting A/B test recommendation: {str(e)}")
            return "Unable to determine recommendation"
    
    def _get_drift_recommendation(self, significant_drift: bool, confidence_drift: float, error_drift: float) -> str:
        """Get recommendation for model drift"""
        try:
            if not significant_drift:
                return "No significant drift detected - continue monitoring"
            
            if confidence_drift > 0.1:
                return "Significant confidence drift detected - consider retraining model"
            
            if error_drift > 0.1:
                return "Significant error rate increase detected - immediate retraining recommended"
            
            return "Model drift detected - investigate data quality and consider retraining"
            
        except Exception as e:
            self.logger.error(f"Error getting drift recommendation: {str(e)}")
            return "Unable to determine recommendation"
    
    def _create_drift_alert(self, model, drift_data: Dict):
        """Create alert for model drift"""
        try:
            alert_message = f"Model drift detected for {model.name} ({model.model_type})"
            
            notification = Notification(
                title='AI Model Drift Alert',
                message=alert_message,
                type='warning',
                metadata={
                    'model_id': model.id,
                    'model_type': model.model_type,
                    'drift_data': drift_data
                }
            )
            
            db.session.add(notification)
            db.session.commit()
            
            self.logger.warning(f"Created drift alert for model {model.name}")
            
        except Exception as e:
            self.logger.error(f"Error creating drift alert: {str(e)}")


# Global performance monitor instance
performance_monitor = AIPerformanceMonitor()


def get_performance_monitor() -> AIPerformanceMonitor:
    """Get the global performance monitor instance"""
    return performance_monitor