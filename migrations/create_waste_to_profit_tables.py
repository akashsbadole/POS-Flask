"""
Create Waste-to-Profit Tables
Database migration script for waste management and profit optimization tables
"""

import sys
import os
from datetime import datetime, timedelta

# Add the parent directory to the path so we can import app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from sqlalchemy import text as db_text
from app.models.waste_to_profit import (
    ExpiryTracking, WasteRecord, ChefSpecial, SustainabilityMetric,
    StaffTraining, StaffTrainingCompletion, WasteReductionChallenge, ChallengeParticipant
)


def create_waste_to_profit_tables():
    """Create all waste-to-profit related tables"""
    
    print("Creating waste-to-profit tables...")
    
    # Create tables in order to handle foreign key dependencies
    tables_to_create = [
        # Core tracking tables
        ExpiryTracking.__table__,
        WasteRecord.__table__,
        
        # Chef's Special tables
        ChefSpecial.__table__,
        
        # Sustainability tables
        SustainabilityMetric.__table__,
        
        # Staff training tables
        StaffTraining.__table__,
        StaffTrainingCompletion.__table__,
        
        # Challenge/Gamification tables
        WasteReductionChallenge.__table__,
        ChallengeParticipant.__table__
    ]
    
    # Create tables
    for table in tables_to_create:
        try:
            table.create(db.engine, checkfirst=True)
            print(f"✓ Created table: {table.name}")
        except Exception as e:
            print(f"✗ Error creating table {table.name}: {str(e)}")
    
    # Create indexes for better performance
    create_indexes()
    
    print("Waste-to-profit tables creation completed!")


def create_indexes():
    """Create indexes for performance optimization"""
    
    indexes = [
        # ExpiryTracking indexes
        "CREATE INDEX IF NOT EXISTS idx_expiry_ingredient_expiry ON expiry_tracking (ingredient_id, expiry_date);",
        "CREATE INDEX IF NOT EXISTS idx_expiry_risk_expiry ON expiry_tracking (risk_level, expiry_date);",
        "CREATE INDEX IF NOT EXISTS idx_expiry_alert_sent ON expiry_tracking (alert_sent, expiry_date);",
        
        # WasteRecord indexes
        "CREATE INDEX IF NOT EXISTS idx_waste_ingredient_date ON waste_records (ingredient_id, waste_date);",
        "CREATE INDEX IF NOT EXISTS idx_waste_reason_date ON waste_records (waste_reason, waste_date);",
        "CREATE INDEX IF NOT EXISTS idx_waste_department_date ON waste_records (department, waste_date);",
        
        # ChefSpecial indexes
        "CREATE INDEX IF NOT EXISTS idx_chef_special_status ON chef_specials (status, start_date);",
        "CREATE INDEX IF NOT EXISTS idx_chef_special_priority ON chef_specials (priority, created_at);",
        "CREATE INDEX IF NOT EXISTS idx_chef_special_creator ON chef_specials (created_by, created_at);",
        
        # SustainabilityMetric indexes
        "CREATE INDEX IF NOT EXISTS idx_sustainability_metric_type ON sustainability_metrics (metric_type, period_start);",
        "CREATE INDEX IF NOT EXISTS idx_sustainability_period ON sustainability_metrics (period_start, period_end);",
        
        # StaffTraining indexes
        "CREATE INDEX IF NOT EXISTS idx_staff_training_type ON staff_training (training_type, is_active);",
        "CREATE INDEX IF NOT EXISTS idx_staff_training_creator ON staff_training (created_by, created_at);",
        
        # StaffTrainingCompletion indexes
        "CREATE INDEX IF NOT EXISTS idx_training_completion_user ON staff_training_completions (user_id, completed_at);",
        "CREATE INDEX IF NOT EXISTS idx_training_completion_training ON staff_training_completions (training_id, completed_at);",
        
        # Challenge indexes
        "CREATE INDEX IF NOT EXISTS idx_challenge_type_status ON waste_reduction_challenges (challenge_type, is_active);",
        "CREATE INDEX IF NOT EXISTS idx_challenge_dates ON waste_reduction_challenges (start_date, end_date);",
        "CREATE INDEX IF NOT EXISTS idx_challenge_participation ON challenge_participants (challenge_id, user_id);",
        "CREATE INDEX IF NOT EXISTS idx_challenge_progress ON challenge_participants (progress_percentage, completed_at);"
    ]
    
    for index_sql in indexes:
        try:
            with db.engine.connect() as conn:
                conn.execute(db_text(index_sql))
            print(f"✓ Created index: {index_sql[:50]}...")
        except Exception as e:
            print(f"✗ Error creating index: {str(e)}")


def insert_default_data():
    """Insert default data for waste-to-profit module"""
    
    print("Inserting default waste-to-profit data...")
    
    try:
        # Insert default sustainability metrics
        default_metrics = [
            {
                'metric_type': 'waste_reduction',
                'metric_name': 'Weekly Waste Reduction Rate',
                'metric_value': 0,
                'metric_unit': '%',
                'target_value': 20,
                'period_start': datetime.now().date(),
                'period_end': datetime.now().date(),
                'description': 'Target: 20% weekly waste reduction'
            },
            {
                'metric_type': 'cost_savings',
                'metric_name': 'Monthly Cost Savings',
                'metric_value': 0,
                'metric_unit': '$',
                'target_value': 500,
                'period_start': datetime.now().date(),
                'period_end': datetime.now().date(),
                'description': 'Target: $500 monthly cost savings'
            },
            {
                'metric_type': 'carbon_footprint',
                'metric_name': 'Monthly Carbon Footprint',
                'metric_value': 0,
                'metric_unit': 'kg CO2',
                'target_value': 100,
                'period_start': datetime.now().date(),
                'period_end': datetime.now().date(),
                'description': 'Target: Keep carbon footprint below 100kg CO2 monthly'
            }
        ]
        
        for metric_data in default_metrics:
            # Check if metric already exists
            existing = SustainabilityMetric.query.filter_by(
                metric_type=metric_data['metric_type'],
                metric_name=metric_data['metric_name']
            ).first()
            
            if not existing:
                metric = SustainabilityMetric(
                    metric_type=metric_data['metric_type'],
                    metric_name=metric_data['metric_name'],
                    metric_value=metric_data['metric_value'],
                    metric_unit=metric_data['metric_unit'],
                    target_value=metric_data['target_value'],
                    period_start=metric_data['period_start'],
                    period_end=metric_data['period_end'],
                    calculation_method='System calculated',
                    notes=metric_data['description']
                )
                db.session.add(metric)
        
        # Insert default staff training modules
        default_trainings = [
            {
                'title': 'Introduction to Waste Reduction',
                'description': 'Learn the basics of food waste reduction and its importance',
                'training_type': 'waste_reduction',
                'content': '# Introduction to Waste Reduction\n\nFood waste is a significant issue in the restaurant industry...',
                'duration_minutes': 30,
                'difficulty_level': 'beginner',
                'target_roles': ['kitchen_staff', 'manager', 'chef'],
                'is_mandatory': True,
                'completion_threshold': 70,
                'quiz_questions': [
                    {
                        'question': 'What is the primary goal of waste reduction?',
                        'options': ['Save money', 'Reduce environmental impact', 'Improve efficiency', 'All of the above'],
                        'correct_answer': 3
                    },
                    {
                        'question': 'What percentage of food waste is considered acceptable?',
                        'options': ['0-5%', '5-10%', '10-15%', '15-20%'],
                        'correct_answer': 0
                    }
                ]
            },
            {
                'title': 'FIFO Inventory Management',
                'description': 'Learn First In, First Out inventory management principles',
                'training_type': 'inventory_management',
                'content': '# FIFO Inventory Management\n\nFIFO (First In, First Out) is a crucial inventory management principle...',
                'duration_minutes': 25,
                'difficulty_level': 'beginner',
                'target_roles': ['kitchen_staff', 'manager'],
                'is_mandatory': True,
                'completion_threshold': 75,
                'quiz_questions': [
                    {
                        'question': 'What does FIFO stand for?',
                        'options': ['First In, First Out', 'First Out, First In', 'Fast In, Fast Out', 'Food In, Food Out'],
                        'correct_answer': 0
                    },
                    {
                        'question': 'Why is FIFO important?',
                        'options': ['Reduces waste', 'Ensures freshness', 'Improves rotation', 'All of the above'],
                        'correct_answer': 3
                    }
                ]
            },
            {
                'title': 'Sustainable Practices',
                'description': 'Learn about sustainable restaurant practices and environmental impact',
                'training_type': 'sustainability',
                'content': '# Sustainable Practices\n\nSustainability in restaurants involves multiple aspects...',
                'duration_minutes': 35,
                'difficulty_level': 'intermediate',
                'target_roles': ['manager', 'chef', 'owner'],
                'is_mandatory': False,
                'completion_threshold': 80,
                'quiz_questions': [
                    {
                        'question': 'What is carbon footprint?',
                        'options': ['Environmental impact measure', 'Financial metric', 'Customer satisfaction score', 'Food quality indicator'],
                        'correct_answer': 0
                    },
                    {
                        'question': 'How can restaurants reduce their environmental impact?',
                        'options': ['Reduce waste', 'Save energy', 'Source locally', 'All of the above'],
                        'correct_answer': 3
                    }
                ]
            }
        ]
        
        for training_data in default_trainings:
            # Check if training already exists
            existing = StaffTraining.query.filter_by(
                title=training_data['title'],
                training_type=training_data['training_type']
            ).first()
            
            if not existing:
                training = StaffTraining(
                    title=training_data['title'],
                    description=training_data['description'],
                    training_type=training_data['training_type'],
                    content=training_data['content'],
                    duration_minutes=training_data['duration_minutes'],
                    difficulty_level=training_data['difficulty_level'],
                    target_roles=training_data['target_roles'],
                    is_mandatory=training_data['is_mandatory'],
                    completion_threshold=training_data['completion_threshold'],
                    quiz_questions=training_data['quiz_questions'],
                    created_by=1  # Admin user
                )
                db.session.add(training)
        
        # Insert default challenge
        default_challenge = {
            'title': 'Monthly Waste Reduction Challenge',
            'description': 'Reduce food waste by 20% this month and win prizes!',
            'challenge_type': 'individual',
            'target_metric': 'waste_reduction',
            'target_value': 20,
            'metric_unit': '%',
            'start_date': datetime.now().date(),
            'end_date': datetime.now().date() + timedelta(days=30),
            'reward_type': 'points',
            'reward_value': '100 points + $50 bonus',
            'participation_rules': 'Track waste reduction through the system. Highest percentage reduction wins.',
            'is_active': True,
            'created_by': 1  # Admin user
        }
        
        existing_challenge = WasteReductionChallenge.query.filter_by(
            title=default_challenge['title']
        ).first()
        
        if not existing_challenge:
            challenge = WasteReductionChallenge(
                title=default_challenge['title'],
                description=default_challenge['description'],
                challenge_type=default_challenge['challenge_type'],
                target_metric=default_challenge['target_metric'],
                target_value=default_challenge['target_value'],
                metric_unit=default_challenge['metric_unit'],
                start_date=default_challenge['start_date'],
                end_date=default_challenge['end_date'],
                reward_type=default_challenge['reward_type'],
                reward_value=default_challenge['reward_value'],
                participation_rules=default_challenge['participation_rules'],
                is_active=default_challenge['is_active'],
                created_by=default_challenge['created_by']
            )
            db.session.add(challenge)
        
        db.session.commit()
        print("✓ Default waste-to-profit data inserted successfully!")
        
    except Exception as e:
        print(f"✗ Error inserting default data: {str(e)}")
        db.session.rollback()


def main():
    """Main function to run the migration"""
    
    app = create_app()
    
    with app.app_context():
        try:
            create_waste_to_profit_tables()
            insert_default_data()
            print("\n✅ Waste-to-profit tables migration completed successfully!")
            
        except Exception as e:
            print(f"\n❌ Migration failed: {str(e)}")
            sys.exit(1)


if __name__ == '__main__':
    main()