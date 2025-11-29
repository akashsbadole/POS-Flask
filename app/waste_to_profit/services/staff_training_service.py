"""
Staff Training Service
Manages staff training modules, completion tracking, and gamification for waste reduction
"""

from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Tuple
from sqlalchemy import and_, or_, func
import logging

from app import db
from app.models.user import User
from app.models.waste_to_profit import StaffTraining, StaffTrainingCompletion, WasteReductionChallenge, ChallengeParticipant


class StaffTrainingService:
    """Service for staff training and engagement"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def create_training_module(self, title: str, description: str, training_type: str,
                          content: str = None, video_url: str = None,
                          quiz_questions: List[Dict] = None, duration_minutes: int = None,
                          difficulty_level: str = 'beginner', target_roles: List[str] = None,
                          is_mandatory: bool = False, user_id: int = None) -> StaffTraining:
        """
        Create a new staff training module
        
        Args:
            title: Training title
            description: Training description
            training_type: Type of training
            content: Training content
            video_url: Video URL
            quiz_questions: Quiz questions and answers
            duration_minutes: Duration in minutes
            difficulty_level: Difficulty level
            target_roles: Target roles for training
            is_mandatory: Whether training is mandatory
            user_id: User creating training
            
        Returns:
            Created StaffTraining record
        """
        try:
            training = StaffTraining(
                title=title,
                description=description,
                training_type=training_type,
                content=content,
                video_url=video_url,
                quiz_questions=quiz_questions or [],
                duration_minutes=duration_minutes,
                difficulty_level=difficulty_level,
                target_roles=target_roles or [],
                is_mandatory=is_mandatory,
                created_by=user_id
            )
            
            db.session.add(training)
            db.session.commit()
            
            self.logger.info(f"Created training module: {title}")
            return training
            
        except Exception as e:
            self.logger.error(f"Error creating training module: {str(e)}")
            db.session.rollback()
            raise
    
    def get_training_modules(self, training_type: str = None, is_active: bool = True) -> List[StaffTraining]:
        """
        Get training modules with optional filtering
        
        Args:
            training_type: Optional training type filter
            is_active: Filter by active status
            
        Returns:
            List of StaffTraining records
        """
        try:
            query = StaffTraining.query.filter_by(is_active=is_active)
            
            if training_type:
                query = query.filter_by(training_type=training_type)
            
            return query.order_by(StaffTraining.created_at.desc()).all()
            
        except Exception as e:
            self.logger.error(f"Error getting training modules: {str(e)}")
            return []
    
    def enroll_user_in_training(self, user_id: int, training_id: int) -> bool:
        """
        Enroll a user in a training module
        
        Args:
            user_id: User ID
            training_id: Training ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Check if already enrolled
            existing = StaffTrainingCompletion.query.filter_by(
                user_id=user_id, training_id=training_id
            ).first()
            
            if existing:
                self.logger.warning(f"User {user_id} already enrolled in training {training_id}")
                return False
            
            # Create enrollment record
            enrollment = StaffTrainingCompletion(
                training_id=training_id,
                user_id=user_id,
                started_at=datetime.utcnow()
            )
            
            db.session.add(enrollment)
            db.session.commit()
            
            self.logger.info(f"Enrolled user {user_id} in training {training_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error enrolling user in training: {str(e)}")
            db.session.rollback()
            return False
    
    def complete_training(self, user_id: int, training_id: int, quiz_score: int = None,
                       feedback: str = None, rating: int = None) -> bool:
        """
        Mark a training as completed for a user
        
        Args:
            user_id: User ID
            training_id: Training ID
            quiz_score: Quiz score
            feedback: User feedback
            rating: User rating (1-5)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            completion = StaffTrainingCompletion.query.filter_by(
                user_id=user_id, training_id=training_id
            ).first()
            
            if not completion:
                self.logger.error(f"User {user_id} not enrolled in training {training_id}")
                return False
            
            # Update completion record
            completion.completed_at = datetime.utcnow()
            completion.quiz_score = quiz_score
            completion.feedback = feedback
            completion.rating = rating
            
            # Calculate time spent
            if completion.started_at:
                time_spent = completion.completed_at - completion.started_at
                completion.time_spent_minutes = int(time_spent.total_seconds() / 60)
            
            # Check if passed
            training = StaffTraining.query.get(training_id)
            if training and quiz_score is not None:
                completion.passed = quiz_score >= training.completion_threshold
                completion.certificate_issued = completion.passed
            
            db.session.commit()
            
            self.logger.info(f"Completed training {training_id} for user {user_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error completing training: {str(e)}")
            db.session.rollback()
            return False
    
    def get_user_training_progress(self, user_id: int) -> Dict:
        """
        Get training progress for a specific user
        
        Args:
            user_id: User ID
            
        Returns:
            Dictionary with training progress information
        """
        try:
            # Get all training completions for user
            completions = StaffTrainingCompletion.query.filter_by(user_id=user_id).all()
            
            # Get all available trainings
            all_trainings = StaffTraining.query.filter_by(is_active=True).all()
            
            # Calculate progress metrics
            total_trainings = len(all_trainings)
            completed_trainings = len([c for c in completions if c.completed_at])
            passed_trainings = len([c for c in completions if c.passed])
            mandatory_trainings = [t for t in all_trainings if t.is_mandatory]
            mandatory_completed = len([c for c in completions 
                                   if c.training and c.training.is_mandatory and c.passed])
            
            # Calculate by training type
            type_progress = {}
            for completion in completions:
                if completion.training:
                    training_type = completion.training.training_type
                    if training_type not in type_progress:
                        type_progress[training_type] = {
                            'total': 0, 'completed': 0, 'passed': 0
                        }
                    
                    type_progress[training_type]['total'] += 1
                    if completion.completed_at:
                        type_progress[training_type]['completed'] += 1
                    if completion.passed:
                        type_progress[training_type]['passed'] += 1
            
            return {
                'user_id': user_id,
                'total_trainings': total_trainings,
                'completed_trainings': completed_trainings,
                'passed_trainings': passed_trainings,
                'mandatory_trainings': len(mandatory_trainings),
                'mandatory_completed': mandatory_completed,
                'completion_rate': (completed_trainings / total_trainings * 100) if total_trainings > 0 else 0,
                'pass_rate': (passed_trainings / completed_trainings * 100) if completed_trainings > 0 else 0,
                'mandatory_completion_rate': (mandatory_completed / len(mandatory_trainings) * 100) if mandatory_trainings else 100,
                'training_type_progress': type_progress,
                'recent_completions': sorted(
                    [c for c in completions if c.completed_at],
                    key=lambda x: x.completed_at,
                    reverse=True
                )[:5],
                'certificates_earned': len([c for c in completions if c.certificate_issued])
            }
            
        except Exception as e:
            self.logger.error(f"Error getting user training progress: {str(e)}")
            return {}
    
    def get_team_training_analytics(self, department: str = None, days_back: int = 30) -> Dict:
        """
        Get team training analytics
        
        Args:
            department: Optional department filter
            days_back: Number of days to analyze
            
        Returns:
            Dictionary with team training analytics
        """
        try:
            start_date = datetime.utcnow() - timedelta(days=days_back)
            
            # Get recent completions
            query = StaffTrainingCompletion.query.filter(
                StaffTrainingCompletion.completed_at >= start_date
            )
            
            if department:
                # Filter by user department (would need user department info)
                # For now, return all completions
                pass
            
            completions = query.all()
            
            # Calculate analytics
            total_completions = len(completions)
            passed_completions = len([c for c in completions if c.passed])
            avg_score = sum(c.quiz_score or 0 for c in completions) / total_completions if total_completions > 0 else 0
            avg_time = sum(c.time_spent_minutes or 0 for c in completions) / total_completions if total_completions > 0 else 0
            avg_rating = sum(c.rating or 0 for c in completions) / len([c for c in completions if c.rating]) if completions else 0
            
            # Group by training type
            type_analytics = {}
            for completion in completions:
                if completion.training:
                    training_type = completion.training.training_type
                    if training_type not in type_analytics:
                        type_analytics[training_type] = {
                            'completions': 0, 'passed': 0, 'avg_score': 0, 'avg_time': 0
                        }
                    
                    type_analytics[training_type]['completions'] += 1
                    if completion.passed:
                        type_analytics[training_type]['passed'] += 1
                    
                    scores = [c.quiz_score for c in completions 
                              if c.training and c.training.training_type == training_type and c.quiz_score is not None]
                    if scores:
                        type_analytics[training_type]['avg_score'] = sum(scores) / len(scores)
                    
                    times = [c.time_spent_minutes for c in completions 
                             if c.training and c.training.training_type == training_type and c.time_spent_minutes]
                    if times:
                        type_analytics[training_type]['avg_time'] = sum(times) / len(times)
            
            return {
                'period_start': start_date.isoformat(),
                'period_end': datetime.utcnow().isoformat(),
                'total_completions': total_completions,
                'passed_completions': passed_completions,
                'pass_rate': (passed_completions / total_completions * 100) if total_completions > 0 else 0,
                'average_score': avg_score,
                'average_time_minutes': avg_time,
                'average_rating': avg_rating,
                'training_type_analytics': type_analytics,
                'top_performers': self._get_top_performers(completions),
                'training_effectiveness': self._calculate_training_effectiveness(completions)
            }
            
        except Exception as e:
            self.logger.error(f"Error getting team training analytics: {str(e)}")
            return {}
    
    def create_waste_reduction_challenge(self, title: str, description: str, challenge_type: str,
                                     target_metric: str, target_value: float,
                                     start_date: date, end_date: date,
                                     reward_type: str, reward_value: str,
                                     participation_rules: str = None,
                                     user_id: int = None) -> WasteReductionChallenge:
        """
        Create a waste reduction challenge
        
        Args:
            title: Challenge title
            description: Challenge description
            challenge_type: Type of challenge
            target_metric: Target metric
            target_value: Target value
            start_date: Start date
            end_date: End date
            reward_type: Type of reward
            reward_value: Reward value
            participation_rules: Participation rules
            user_id: User creating challenge
            
        Returns:
            Created WasteReductionChallenge record
        """
        try:
            challenge = WasteReductionChallenge(
                title=title,
                description=description,
                challenge_type=challenge_type,
                target_metric=target_metric,
                target_value=target_value,
                start_date=start_date,
                end_date=end_date,
                reward_type=reward_type,
                reward_value=reward_value,
                participation_rules=participation_rules,
                created_by=user_id
            )
            
            db.session.add(challenge)
            db.session.commit()
            
            self.logger.info(f"Created waste reduction challenge: {title}")
            return challenge
            
        except Exception as e:
            self.logger.error(f"Error creating waste reduction challenge: {str(e)}")
            db.session.rollback()
            raise
    
    def enroll_user_in_challenge(self, user_id: int, challenge_id: int) -> bool:
        """
        Enroll a user in a waste reduction challenge
        
        Args:
            user_id: User ID
            challenge_id: Challenge ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Check if already enrolled
            existing = ChallengeParticipant.query.filter_by(
                user_id=user_id, challenge_id=challenge_id
            ).first()
            
            if existing:
                self.logger.warning(f"User {user_id} already enrolled in challenge {challenge_id}")
                return False
            
            # Create enrollment
            participation = ChallengeParticipant(
                challenge_id=challenge_id,
                user_id=user_id,
                current_value=0,
                progress_percentage=0
            )
            
            db.session.add(participation)
            db.session.commit()
            
            self.logger.info(f"Enrolled user {user_id} in challenge {challenge_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error enrolling user in challenge: {str(e)}")
            db.session.rollback()
            return False
    
    def update_challenge_progress(self, user_id: int, challenge_id: int, 
                              value_addition: float, notes: str = None) -> bool:
        """
        Update challenge progress for a user
        
        Args:
            user_id: User ID
            challenge_id: Challenge ID
            value_addition: Value to add to progress
            notes: Optional notes
            
        Returns:
            True if successful, False otherwise
        """
        try:
            participation = ChallengeParticipant.query.filter_by(
                user_id=user_id, challenge_id=challenge_id
            ).first()
            
            if not participation:
                self.logger.error(f"User {user_id} not enrolled in challenge {challenge_id}")
                return False
            
            # Update progress
            participation.current_value += value_addition
            participation.update_progress()
            participation.notes = notes
            
            # Check if completed
            if participation.progress_percentage >= 100 and not participation.completed_at:
                participation.completed_at = datetime.utcnow()
                participation.reward_claimed = False
            
            db.session.commit()
            
            self.logger.info(f"Updated challenge progress for user {user_id}, challenge {challenge_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error updating challenge progress: {str(e)}")
            db.session.rollback()
            return False
    
    def get_challenge_leaderboard(self, challenge_id: int = None) -> List[Dict]:
        """
        Get challenge leaderboard
        
        Args:
            challenge_id: Optional specific challenge
            
        Returns:
            List of leaderboard entries
        """
        try:
            query = ChallengeParticipant.query.join(WasteReductionChallenge)
            
            if challenge_id:
                query = query.filter(ChallengeParticipant.challenge_id == challenge_id)
            
            # Only include active challenges
            query = query.filter(
                and_(
                    WasteReductionChallenge.is_active == True,
                    WasteReductionChallenge.end_date >= date.today()
                )
            )
            
            participations = query.all()
            
            # Group by challenge
            challenge_leaderboards = {}
            for participation in participations:
                challenge_id = participation.challenge_id
                if challenge_id not in challenge_leaderboards:
                    challenge_leaderboards[challenge_id] = []
                
                challenge_leaderboards[challenge_id].append(participation.to_dict())
            
            # Sort each leaderboard
            for challenge_id, entries in challenge_leaderboards.items():
                entries.sort(key=lambda x: (x['progress_percentage'], x['current_value']), reverse=True)
                challenge_leaderboards[challenge_id] = entries[:10]  # Top 10
            
            return challenge_leaderboards if challenge_id else list(challenge_leaderboards.values())[0]
            
        except Exception as e:
            self.logger.error(f"Error getting challenge leaderboard: {str(e)}")
            return []
    
    def get_training_recommendations(self, user_id: int = None) -> List[Dict]:
        """
        Get personalized training recommendations
        
        Args:
            user_id: Optional user ID for personalization
            
        Returns:
            List of training recommendations
        """
        try:
            recommendations = []
            
            # Get user's training history
            user_progress = self.get_user_training_progress(user_id) if user_id else {}
            
            # Get all available trainings
            all_trainings = StaffTraining.query.filter_by(is_active=True).all()
            
            # Analyze training gaps
            completed_types = set()
            if user_progress.get('training_type_progress'):
                completed_types = set(
                    t_type for t_type, data in user_progress['training_type_progress'].items()
                    if data['passed'] > 0
                )
            
            for training in all_trainings:
                # Skip if already passed
                if training.training_type in completed_types:
                    continue
                
                # Calculate recommendation priority
                priority = self._calculate_training_priority(training, user_progress)
                
                recommendations.append({
                    'training_id': training.id,
                    'title': training.title,
                    'description': training.description,
                    'training_type': training.training_type,
                    'difficulty_level': training.difficulty_level,
                    'duration_minutes': training.duration_minutes,
                    'is_mandatory': training.is_mandatory,
                    'priority_score': priority,
                    'reason': self._get_training_recommendation_reason(training, user_progress),
                    'estimated_benefit': self._estimate_training_benefit(training, user_progress)
                })
            
            # Sort by priority
            recommendations.sort(key=lambda x: x['priority_score'], reverse=True)
            
            return recommendations[:10]  # Top 10 recommendations
            
        except Exception as e:
            self.logger.error(f"Error getting training recommendations: {str(e)}")
            return []
    
    def _get_top_performers(self, completions: List[StaffTrainingCompletion]) -> List[Dict]:
        """Get top performers based on training completions"""
        try:
            # Group by user and calculate metrics
            user_metrics = {}
            
            for completion in completions:
                user_id = completion.user_id
                if user_id not in user_metrics:
                    user_metrics[user_id] = {
                        'completions': 0, 'passed': 0, 'total_score': 0,
                        'total_time': 0, 'ratings': [], 'user_name': None
                    }
                
                user_metrics[user_id]['completions'] += 1
                if completion.passed:
                    user_metrics[user_id]['passed'] += 1
                if completion.quiz_score:
                    user_metrics[user_id]['total_score'] += completion.quiz_score
                if completion.time_spent_minutes:
                    user_metrics[user_id]['total_time'] += completion.time_spent_minutes
                if completion.rating:
                    user_metrics[user_id]['ratings'].append(completion.rating)
                if completion.user and not user_metrics[user_id]['user_name']:
                    user_metrics[user_id]['user_name'] = completion.user.name
            
            # Calculate final metrics
            performers = []
            for user_id, metrics in user_metrics.items():
                avg_score = metrics['total_score'] / metrics['completions'] if metrics['completions'] > 0 else 0
                avg_time = metrics['total_time'] / metrics['completions'] if metrics['completions'] > 0 else 0
                avg_rating = sum(metrics['ratings']) / len(metrics['ratings']) if metrics['ratings'] else 0
                pass_rate = (metrics['passed'] / metrics['completions'] * 100) if metrics['completions'] > 0 else 0
                
                performers.append({
                    'user_id': user_id,
                    'user_name': metrics['user_name'],
                    'completions': metrics['completions'],
                    'passed': metrics['passed'],
                    'pass_rate': pass_rate,
                    'average_score': avg_score,
                    'average_time_minutes': avg_time,
                    'average_rating': avg_rating,
                    'performance_score': self._calculate_performance_score(
                        pass_rate, avg_score, avg_rating
                    )
                })
            
            # Sort by performance score
            performers.sort(key=lambda x: x['performance_score'], reverse=True)
            
            return performers[:10]  # Top 10
            
        except Exception as e:
            self.logger.error(f"Error getting top performers: {str(e)}")
            return []
    
    def _calculate_training_effectiveness(self, completions: List[StaffTrainingCompletion]) -> Dict:
        """Calculate training effectiveness metrics"""
        try:
            if not completions:
                return {}
            
            total_completions = len(completions)
            passed_completions = len([c for c in completions if c.passed])
            
            # Calculate effectiveness by training type
            type_effectiveness = {}
            for completion in completions:
                if completion.training:
                    training_type = completion.training.training_type
                    if training_type not in type_effectiveness:
                        type_effectiveness[training_type] = {
                            'completions': 0, 'passed': 0, 'avg_score': 0, 'avg_rating': 0
                        }
                    
                    type_effectiveness[training_type]['completions'] += 1
                    if completion.passed:
                        type_effectiveness[training_type]['passed'] += 1
                    
                    scores = [c.quiz_score for c in completions 
                              if c.training and c.training.training_type == training_type and c.quiz_score is not None]
                    if scores:
                        type_effectiveness[training_type]['avg_score'] = sum(scores) / len(scores)
                    
                    ratings = [c.rating for c in completions 
                               if c.training and c.training.training_type == training_type and c.rating]
                    if ratings:
                        type_effectiveness[training_type]['avg_rating'] = sum(ratings) / len(ratings)
            
            # Calculate overall effectiveness
            overall_pass_rate = (passed_completions / total_completions * 100) if total_completions > 0 else 0
            overall_avg_score = sum(c.quiz_score or 0 for c in completions) / total_completions if total_completions > 0 else 0
            overall_avg_rating = sum(c.rating for c in completions if c.rating) / len([c for c in completions if c.rating]) if completions else 0
            
            return {
                'overall_pass_rate': overall_pass_rate,
                'overall_average_score': overall_avg_score,
                'overall_average_rating': overall_avg_rating,
                'type_effectiveness': type_effectiveness,
                'most_effective_type': max(type_effectiveness.items(), 
                                           key=lambda x: x[1]['pass_rate'])[0] if type_effectiveness else None,
                'least_effective_type': min(type_effectiveness.items(), 
                                            key=lambda x: x[1]['pass_rate'])[0] if type_effectiveness else None
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating training effectiveness: {str(e)}")
            return {}
    
    def _calculate_training_priority(self, training: StaffTraining, user_progress: Dict) -> float:
        """Calculate priority score for training recommendation"""
        try:
            priority = 0
            
            # Base priority for mandatory trainings
            if training.is_mandatory:
                priority += 50
            
            # Priority based on training type relevance
            type_relevance = {
                'waste_reduction': 30,
                'inventory_management': 25,
                'food_safety': 20,
                'sustainability': 15
            }
            
            priority += type_relevance.get(training.training_type, 10)
            
            # Priority based on user's completion history
            if user_progress.get('training_type_progress'):
                type_progress = user_progress['training_type_progress'].get(training.training_type, {})
                completed_count = type_progress.get('completed', 0)
                
                # Lower priority for already completed types
                if completed_count > 0:
                    priority -= 15
            
            # Priority based on difficulty (easier trainings get higher priority)
            difficulty_priority = {
                'beginner': 20,
                'intermediate': 10,
                'advanced': 5
            }
            
            priority += difficulty_priority.get(training.difficulty_level, 10)
            
            return max(0, priority)
            
        except Exception as e:
            self.logger.error(f"Error calculating training priority: {str(e)}")
            return 0
    
    def _get_training_recommendation_reason(self, training: StaffTraining, user_progress: Dict) -> str:
        """Get reason for training recommendation"""
        if training.is_mandatory:
            return "Mandatory training for all staff"
        
        if user_progress.get('training_type_progress'):
            type_progress = user_progress['training_type_progress'].get(training.training_type, {})
            if type_progress.get('completed', 0) == 0:
                return f"Recommended to improve {training.training_type.replace('_', ' ')} skills"
            elif type_progress.get('passed', 0) == 0:
                return f"Retake recommended for {training.training_type.replace('_', ' ')} training"
        
        return f"Recommended for professional development in {training.training_type.replace('_', ' ')}"
    
    def _estimate_training_benefit(self, training: StaffTraining, user_progress: Dict) -> str:
        """Estimate benefit of training"""
        benefits = {
            'waste_reduction': 'Reduce food waste by 15-25%',
            'inventory_management': 'Improve inventory accuracy by 20%',
            'food_safety': 'Ensure compliance and safety standards',
            'sustainability': 'Contribute to environmental goals'
        }
        
        return benefits.get(training.training_type, 'Professional development opportunity')
    
    def _calculate_performance_score(self, pass_rate: float, avg_score: float, avg_rating: float) -> float:
        """Calculate overall performance score"""
        # Weighted score: pass rate (40%), average score (35%), average rating (25%)
        return (pass_rate * 0.4) + ((avg_score / 100) * 35) + (avg_rating / 5 * 25)