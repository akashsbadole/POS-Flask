"""
A/B Testing Framework for AI Features
Provides comprehensive A/B testing capabilities including:
- Test creation and management
- Participant assignment and tracking
- Statistical significance testing
- Result analysis and reporting
- Automated winner selection
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
import json
import logging
import uuid
import hashlib
from enum import Enum

from app import db
from app.models.ai_models import (
    AIModel, AIABTest, AIABTestParticipant, AIPredictionLog
)
from app.models.customer import Customer
from app.models.order import Order


class TestStatus(Enum):
    """A/B Test Status Enum"""
    DRAFT = 'draft'
    RUNNING = 'running'
    PAUSED = 'paused'
    COMPLETED = 'completed'
    CANCELLED = 'cancelled'


class TestType(Enum):
    """A/B Test Type Enum"""
    MODEL_COMPARISON = 'model_comparison'
    FEATURE_TOGGLE = 'feature_toggle'
    PARAMETER_TUNING = 'parameter_tuning'
    UI_VARIATION = 'ui_variation'
    PRICING_STRATEGY = 'pricing_strategy'


class AssignmentStrategy(Enum):
    """Participant Assignment Strategy"""
    RANDOM = 'random'
    HASH_BASED = 'hash_based'
    WEIGHTED = 'weighted'
    SEQUENTIAL = 'sequential'


class AIABTestingFramework:
    """AI A/B Testing Framework"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.significance_threshold = 0.05  # 5% significance level
        self.min_sample_size = 100  # Minimum sample size for significance testing
    
    def create_test(self, test_config: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new A/B test"""
        try:
            # Validate required fields
            required_fields = ['name', 'description', 'variants', 'traffic_allocation']
            for field in required_fields:
                if field not in test_config:
                    return {'error': f'Missing required field: {field}'}
            
            # Validate variants
            variants = test_config['variants']
            if not isinstance(variants, dict) or len(variants) < 2:
                return {'error': 'Test must have at least 2 variants'}
            
            # Validate traffic allocation
            allocation = test_config['traffic_allocation']
            if not isinstance(allocation, dict) or set(allocation.keys()) != set(variants.keys()):
                return {'error': 'Traffic allocation must match variants'}
            
            # Validate allocation sums to 1.0
            total_allocation = sum(allocation.values())
            if abs(total_allocation - 1.0) > 0.01:
                return {'error': 'Traffic allocation must sum to 1.0'}
            
            # Create test record
            test = AIABTest(
                name=test_config['name'],
                description=test_config['description'],
                test_type=test_config.get('test_type', TestType.MODEL_COMPARISON.value),
                variants=variants,
                traffic_allocation=allocation,
                target_metrics=test_config.get('target_metrics', ['conversion_rate']),
                success_criteria=test_config.get('success_criteria', {}),
                assignment_strategy=test_config.get('assignment_strategy', AssignmentStrategy.RANDOM.value),
                start_date=test_config.get('start_date'),
                end_date=test_config.get('end_date'),
                min_sample_size=test_config.get('min_sample_size', self.min_sample_size),
                significance_threshold=test_config.get('significance_threshold', self.significance_threshold),
                status=TestStatus.DRAFT.value,
                is_active=False,
                created_at=datetime.now()
            )
            
            db.session.add(test)
            db.session.commit()
            
            self.logger.info(f"Created A/B test: {test.name}")
            
            return {
                'success': True,
                'test_id': test.id,
                'test_name': test.name,
                'status': test.status
            }
            
        except Exception as e:
            self.logger.error(f"Error creating A/B test: {str(e)}")
            db.session.rollback()
            return {'error': str(e)}
    
    def start_test(self, test_id: int) -> Dict[str, Any]:
        """Start an A/B test"""
        try:
            test = AIABTest.query.get(test_id)
            if not test:
                return {'error': 'A/B test not found'}
            
            if test.status != TestStatus.DRAFT.value:
                return {'error': f'Cannot start test in {test.status} status'}
            
            # Update test status
            test.status = TestStatus.RUNNING.value
            test.is_active = True
            test.start_date = datetime.now()
            
            db.session.commit()
            
            self.logger.info(f"Started A/B test: {test.name}")
            
            return {
                'success': True,
                'test_id': test.id,
                'test_name': test.name,
                'status': test.status,
                'start_date': test.start_date.isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error starting A/B test: {str(e)}")
            db.session.rollback()
            return {'error': str(e)}
    
    def assign_participant(self, test_id: int, participant_id: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Assign a participant to a test variant"""
        try:
            test = AIABTest.query.get(test_id)
            if not test:
                return {'error': 'A/B test not found'}
            
            if test.status != TestStatus.RUNNING.value:
                return {'error': f'Cannot assign participants to test in {test.status} status'}
            
            # Check if participant is already assigned
            existing = AIABTestParticipant.query.filter_by(
                test_id=test_id,
                participant_id=participant_id
            ).first()
            
            if existing:
                return {
                    'success': True,
                    'variant': existing.variant,
                    'participant_id': participant_id,
                    'already_assigned': True
                }
            
            # Assign variant based on strategy
            variant = self._assign_variant(test, participant_id, context)
            
            # Create participant record
            participant = AIABTestParticipant(
                test_id=test_id,
                participant_id=participant_id,
                variant=variant,
                context=context or {},
                assigned_at=datetime.now()
            )
            
            db.session.add(participant)
            db.session.commit()
            
            return {
                'success': True,
                'variant': variant,
                'participant_id': participant_id,
                'assigned_at': participant.assigned_at.isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error assigning participant: {str(e)}")
            db.session.rollback()
            return {'error': str(e)}
    
    def record_conversion(self, test_id: int, participant_id: str, conversion_data: Dict[str, Any]) -> Dict[str, Any]:
        """Record a conversion event for a test participant"""
        try:
            participant = AIABTestParticipant.query.filter_by(
                test_id=test_id,
                participant_id=participant_id
            ).first()
            
            if not participant:
                return {'error': 'Participant not found in test'}
            
            # Update participant metrics
            current_metrics = participant.metrics or {}
            
            # Merge conversion data
            for key, value in conversion_data.items():
                if key in current_metrics:
                    if isinstance(current_metrics[key], list):
                        current_metrics[key].append(value)
                    elif isinstance(current_metrics[key], (int, float)):
                        current_metrics[key] += value
                    else:
                        current_metrics[key] = value
                else:
                    current_metrics[key] = value
            
            # Set conversion flag
            current_metrics['converted'] = True
            current_metrics['conversion_date'] = datetime.now().isoformat()
            
            participant.metrics = current_metrics
            participant.converted_at = datetime.now()
            
            db.session.commit()
            
            return {
                'success': True,
                'participant_id': participant_id,
                'variant': participant.variant,
                'conversion_data': conversion_data
            }
            
        except Exception as e:
            self.logger.error(f"Error recording conversion: {str(e)}")
            db.session.rollback()
            return {'error': str(e)}
    
    def get_test_results(self, test_id: int, include_raw_data: bool = False) -> Dict[str, Any]:
        """Get comprehensive results for an A/B test"""
        try:
            test = AIABTest.query.get(test_id)
            if not test:
                return {'error': 'A/B test not found'}
            
            # Get participants
            participants = AIABTestParticipant.query.filter_by(test_id=test_id).all()
            
            if not participants:
                return {
                    'success': True,
                    'test_id': test_id,
                    'test_name': test.name,
                    'message': 'No participants yet',
                    'participants': []
                }
            
            # Group participants by variant
            variant_data = {}
            for participant in participants:
                variant = participant.variant
                if variant not in variant_data:
                    variant_data[variant] = []
                variant_data[variant].append(participant)
            
            # Calculate metrics for each variant
            variant_results = {}
            for variant, participant_list in variant_data.items():
                result = self._calculate_variant_metrics(participant_list, test.target_metrics)
                variant_results[variant] = result
            
            # Perform statistical significance tests
            significance_results = self._perform_significance_tests(variant_results, test.target_metrics)
            
            # Determine winner
            winner = self._determine_winner(variant_results, significance_results, test.target_metrics)
            
            # Calculate test duration and sample size
            test_duration = None
            if test.start_date:
                end_date = test.end_date or datetime.now()
                test_duration = (end_date - test.start_date).days
            
            total_participants = len(participants)
            
            results = {
                'success': True,
                'test_id': test_id,
                'test_name': test.name,
                'test_type': test.test_type,
                'status': test.status,
                'start_date': test.start_date.isoformat() if test.start_date else None,
                'end_date': test.end_date.isoformat() if test.end_date else None,
                'test_duration_days': test_duration,
                'total_participants': total_participants,
                'variants': test.variants,
                'target_metrics': test.target_metrics,
                'variant_results': variant_results,
                'significance_results': significance_results,
                'winner': winner,
                'min_sample_size_reached': total_participants >= test.min_sample_size,
                'generated_at': datetime.now().isoformat()
            }
            
            # Include raw data if requested
            if include_raw_data:
                results['raw_participant_data'] = [
                    {
                        'participant_id': p.participant_id,
                        'variant': p.variant,
                        'metrics': p.metrics,
                        'converted_at': p.converted_at.isoformat() if p.converted_at else None,
                        'assigned_at': p.assigned_at.isoformat()
                    }
                    for p in participants
                ]
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error getting test results: {str(e)}")
            return {'error': str(e)}
    
    def stop_test(self, test_id: int, reason: str = None) -> Dict[str, Any]:
        """Stop an A/B test"""
        try:
            test = AIABTest.query.get(test_id)
            if not test:
                return {'error': 'A/B test not found'}
            
            if test.status not in [TestStatus.RUNNING.value, TestStatus.PAUSED.value]:
                return {'error': f'Cannot stop test in {test.status} status'}
            
            # Update test status
            test.status = TestStatus.COMPLETED.value
            test.is_active = False
            test.end_date = datetime.now()
            
            if reason:
                test.success_criteria = test.success_criteria or {}
                test.success_criteria['stop_reason'] = reason
            
            db.session.commit()
            
            self.logger.info(f"Stopped A/B test: {test.name}")
            
            return {
                'success': True,
                'test_id': test.id,
                'test_name': test.name,
                'status': test.status,
                'end_date': test.end_date.isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error stopping A/B test: {str(e)}")
            db.session.rollback()
            return {'error': str(e)}
    
    def get_active_tests(self) -> List[Dict[str, Any]]:
        """Get all active A/B tests"""
        try:
            tests = AIABTest.query.filter_by(is_active=True).all()
            
            active_tests = []
            for test in tests:
                # Get participant count
                participant_count = AIABTestParticipant.query.filter_by(test_id=test.id).count()
                
                active_tests.append({
                    'id': test.id,
                    'name': test.name,
                    'description': test.description,
                    'test_type': test.test_type,
                    'status': test.status,
                    'start_date': test.start_date.isoformat() if test.start_date else None,
                    'end_date': test.end_date.isoformat() if test.end_date else None,
                    'participant_count': participant_count,
                    'variants': list(test.variants.keys())
                })
            
            return active_tests
            
        except Exception as e:
            self.logger.error(f"Error getting active tests: {str(e)}")
            return []
    
    def _assign_variant(self, test: AIABTest, participant_id: str, context: Dict[str, Any] = None) -> str:
        """Assign a variant to a participant based on strategy"""
        try:
            strategy = test.assignment_strategy
            variants = list(test.variants.keys())
            allocation = test.traffic_allocation
            
            if strategy == AssignmentStrategy.RANDOM.value:
                # Random assignment based on traffic allocation
                rand_val = np.random.random()
                cumulative = 0.0
                
                for variant in variants:
                    cumulative += allocation[variant]
                    if rand_val <= cumulative:
                        return variant
                
                # Fallback to last variant
                return variants[-1]
            
            elif strategy == AssignmentStrategy.HASH_BASED.value:
                # Consistent hash-based assignment
                hash_input = f"{test.id}_{participant_id}"
                hash_val = int(hashlib.md5(hash_input.encode()).hexdigest(), 16)
                hash_float = hash_val / (16 ** 32)  # Normalize to 0-1
                
                cumulative = 0.0
                for variant in variants:
                    cumulative += allocation[variant]
                    if hash_float <= cumulative:
                        return variant
                
                return variants[-1]
            
            elif strategy == AssignmentStrategy.WEIGHTED.value:
                # Weighted assignment based on context
                # In a real implementation, this would use context to bias assignment
                return self._weighted_assignment(variants, allocation, context)
            
            elif strategy == AssignmentStrategy.SEQUENTIAL.value:
                # Sequential round-robin assignment
                current_count = AIABTestParticipant.query.filter_by(test_id=test.id).count()
                variant_index = current_count % len(variants)
                return variants[variant_index]
            
            else:
                # Default to random
                return np.random.choice(variants)
                
        except Exception as e:
            self.logger.error(f"Error assigning variant: {str(e)}")
            return list(test.variants.keys())[0]  # Fallback to first variant
    
    def _weighted_assignment(self, variants: List[str], allocation: Dict[str, float], context: Dict[str, Any] = None) -> str:
        """Weighted assignment based on context"""
        try:
            # Simple weighted assignment - in a real implementation, this would be more sophisticated
            if not context:
                # Fall back to random assignment
                rand_val = np.random.random()
                cumulative = 0.0
                
                for variant in variants:
                    cumulative += allocation[variant]
                    if rand_val <= cumulative:
                        return variant
                
                return variants[-1]
            
            # Example: bias assignment based on customer segment
            customer_segment = context.get('customer_segment')
            if customer_segment == 'vip':
                # Bias towards treatment variant for VIP customers
                treatment_variants = [v for v in variants if 'treatment' in v.lower() or 'b' in v.lower()]
                if treatment_variants:
                    return np.random.choice(treatment_variants)
            
            # Default to weighted random
            rand_val = np.random.random()
            cumulative = 0.0
            
            for variant in variants:
                cumulative += allocation[variant]
                if rand_val <= cumulative:
                    return variant
            
            return variants[-1]
            
        except Exception as e:
            self.logger.error(f"Error in weighted assignment: {str(e)}")
            return variants[0]  # Fallback to first variant
    
    def _calculate_variant_metrics(self, participants: List, target_metrics: List[str]) -> Dict[str, Any]:
        """Calculate metrics for a variant"""
        try:
            if not participants:
                return {
                    'participant_count': 0,
                    'conversion_rate': 0.0,
                    'metrics': {}
                }
            
            participant_count = len(participants)
            converted_participants = [p for p in participants if p.converted_at]
            conversion_count = len(converted_participants)
            conversion_rate = conversion_count / participant_count if participant_count > 0 else 0
            
            # Calculate additional metrics
            metrics = {
                'conversion_rate': conversion_rate,
                'conversion_count': conversion_count,
                'participant_count': participant_count
            }
            
            # Calculate target-specific metrics
            all_metrics = {}
            for participant in participants:
                if participant.metrics:
                    for key, value in participant.metrics.items():
                        if key not in all_metrics:
                            all_metrics[key] = []
                        
                        if isinstance(value, (int, float)):
                            all_metrics[key].append(value)
                        elif isinstance(value, list):
                            all_metrics[key].extend(value)
            
            # Calculate aggregate metrics
            for metric_name, values in all_metrics.items():
                if values and isinstance(values[0], (int, float)):
                    metrics[metric_name] = {
                        'mean': float(np.mean(values)),
                        'std': float(np.std(values)),
                        'min': float(np.min(values)),
                        'max': float(np.max(values)),
                        'sum': float(np.sum(values))
                    }
            
            return {
                'participant_count': participant_count,
                'conversion_rate': conversion_rate,
                'metrics': metrics
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating variant metrics: {str(e)}")
            return {
                'participant_count': 0,
                'conversion_rate': 0.0,
                'metrics': {}
            }
    
    def _perform_significance_tests(self, variant_results: Dict[str, Any], target_metrics: List[str]) -> Dict[str, Any]:
        """Perform statistical significance tests between variants"""
        try:
            if len(variant_results) < 2:
                return {'significant': False, 'message': 'Need at least 2 variants for significance testing'}
            
            significance_results = {}
            
            # Test each target metric
            for metric in target_metrics:
                if metric == 'conversion_rate':
                    # Perform chi-square test for conversion rates
                    significance_results[metric] = self._test_conversion_rates(variant_results)
                else:
                    # Perform t-test for continuous metrics
                    significance_results[metric] = self._test_continuous_metrics(variant_results, metric)
            
            return significance_results
            
        except Exception as e:
            self.logger.error(f"Error performing significance tests: {str(e)}")
            return {'significant': False, 'error': str(e)}
    
    def _test_conversion_rates(self, variant_results: Dict[str, Any]) -> Dict[str, Any]:
        """Test statistical significance of conversion rates"""
        try:
            variants = list(variant_results.keys())
            
            if len(variants) == 2:
                # Two-sample test for proportions
                v1, v2 = variants[0], variants[1]
                
                r1 = variant_results[v1]['conversion_rate']
                r2 = variant_results[v2]['conversion_rate']
                n1 = variant_results[v1]['participant_count']
                n2 = variant_results[v2]['participant_count']
                
                if n1 == 0 or n2 == 0:
                    return {'significant': False, 'message': 'Insufficient sample size'}
                
                # Calculate pooled proportion
                p_pooled = (r1 * n1 + r2 * n2) / (n1 + n2)
                
                # Calculate standard error
                se = np.sqrt(p_pooled * (1 - p_pooled) * (1/n1 + 1/n2))
                
                if se == 0:
                    return {'significant': False, 'message': 'Cannot calculate significance'}
                
                # Calculate z-score
                z_score = abs(r1 - r2) / se
                
                # Calculate p-value (two-tailed)
                p_value = 2 * (1 - self._normal_cdf(z_score))
                
                return {
                    'significant': p_value < 0.05,
                    'p_value': float(p_value),
                    'z_score': float(z_score),
                    'test_type': 'two_proportion_z_test',
                    'variant_rates': {v1: r1, v2: r2}
                }
            else:
                # Multiple variants - would need chi-square test
                return {
                    'significant': False,
                    'message': 'Multiple variant significance testing not implemented',
                    'variant_rates': {v: variant_results[v]['conversion_rate'] for v in variants}
                }
                
        except Exception as e:
            self.logger.error(f"Error testing conversion rates: {str(e)}")
            return {'significant': False, 'error': str(e)}
    
    def _test_continuous_metrics(self, variant_results: Dict[str, Any], metric: str) -> Dict[str, Any]:
        """Test statistical significance of continuous metrics"""
        try:
            variants = list(variant_results.keys())
            
            if len(variants) == 2:
                # Two-sample t-test
                v1, v2 = variants[0], variants[1]
                
                v1_metrics = variant_results[v1]['metrics'].get(metric, {})
                v2_metrics = variant_results[v2]['metrics'].get(metric, {})
                
                if 'mean' not in v1_metrics or 'mean' not in v2_metrics:
                    return {'significant': False, 'message': 'Metric data not available'}
                
                mean1, std1 = v1_metrics['mean'], v1_metrics.get('std', 0)
                mean2, std2 = v2_metrics['mean'], v2_metrics.get('std', 0)
                n1, n2 = variant_results[v1]['participant_count'], variant_results[v2]['participant_count']
                
                # Calculate t-statistic
                if n1 == 0 or n2 == 0:
                    return {'significant': False, 'message': 'Insufficient sample size'}
                
                # Pooled standard error
                se = np.sqrt(std1**2/n1 + std2**2/n2)
                
                if se == 0:
                    return {'significant': False, 'message': 'Cannot calculate significance'}
                
                t_stat = abs(mean1 - mean2) / se
                
                # Approximate p-value (simplified)
                df = n1 + n2 - 2
                p_value = 2 * (1 - self._t_cdf(t_stat, df))
                
                return {
                    'significant': p_value < 0.05,
                    'p_value': float(p_value),
                    't_statistic': float(t_stat),
                    'test_type': 'two_sample_t_test',
                    'variant_means': {v1: mean1, v2: mean2}
                }
            else:
                return {
                    'significant': False,
                    'message': 'Multiple variant testing not implemented for continuous metrics'
                }
                
        except Exception as e:
            self.logger.error(f"Error testing continuous metrics: {str(e)}")
            return {'significant': False, 'error': str(e)}
    
    def _normal_cdf(self, x: float) -> float:
        """Approximate normal CDF"""
        return 0.5 * (1 + np.tanh(np.sqrt(2/np.pi) * (x + 0.044715 * np.power(x, 3))))
    
    def _t_cdf(self, t: float, df: int) -> float:
        """Approximate t-distribution CDF"""
        # Simplified approximation - in practice, use scipy.stats.t.cdf
        if df > 30:
            # Approximate with normal distribution for large df
            return self._normal_cdf(t)
        else:
            # Simplified approximation for smaller df
            return self._normal_cdf(t * np.sqrt((df - 2) / df))
    
    def _determine_winner(self, variant_results: Dict[str, Any], significance_results: Dict[str, Any], target_metrics: List[str]) -> Optional[str]:
        """Determine the winning variant"""
        try:
            # Check if any metric is statistically significant
            significant_metrics = [m for m in target_metrics if significance_results.get(m, {}).get('significant', False)]
            
            if not significant_metrics:
                return None
            
            # For now, use the first significant metric to determine winner
            primary_metric = significant_metrics[0]
            
            if primary_metric == 'conversion_rate':
                # Find variant with highest conversion rate
                best_variant = None
                best_rate = -1
                
                for variant, results in variant_results.items():
                    rate = results['conversion_rate']
                    if rate > best_rate:
                        best_rate = rate
                        best_variant = variant
                
                return best_variant
            else:
                # Find variant with highest value for the metric
                best_variant = None
                best_value = float('-inf')
                
                for variant, results in variant_results.items():
                    metric_data = results['metrics'].get(primary_metric, {})
                    mean_value = metric_data.get('mean', 0)
                    
                    if mean_value > best_value:
                        best_value = mean_value
                        best_variant = variant
                
                return best_variant
                
        except Exception as e:
            self.logger.error(f"Error determining winner: {str(e)}")
            return None


# Global A/B testing framework instance
ab_testing_framework = AIABTestingFramework()


def get_ab_testing_framework() -> AIABTestingFramework:
    """Get the global A/B testing framework instance"""
    return ab_testing_framework