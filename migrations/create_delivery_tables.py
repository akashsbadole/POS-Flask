"""
Create advanced delivery management tables
Migration script for GPS tracking, driver management, and route optimization
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.models.delivery import (
    Driver, Delivery, DeliveryRoute, DriverLocation, DeliveryTracking,
    DriverRating, DriverPerformance, DriverEarning, DeliveryFeedback, DeliveryZone
)
from datetime import datetime
import uuid
from sqlalchemy import text
from sqlalchemy import text

def create_delivery_tables():
    """Create all delivery-related tables"""
    
    from app import db
    
    print("Creating advanced delivery management tables...")
    
    # Create tables in order to respect foreign key constraints
    tables_to_create = [
        'delivery_zones',        # No foreign keys
        'drivers',               # References users
        'delivery_routes',        # References drivers
        'driver_locations',      # References drivers
        'deliveries',            # References orders, drivers, delivery_routes
        'delivery_tracking',      # References deliveries
        'driver_ratings',        # References drivers, customers, deliveries
        'driver_performance',    # References drivers
        'driver_earnings',       # References drivers, deliveries
        'delivery_feedback'       # References deliveries, customers
    ]
    
    for table_name in tables_to_create:
        print(f"Creating table: {table_name}")
        # SQLAlchemy will create tables based on model definitions
        if table_name == 'delivery_zones':
            DeliveryZone.__table__.create(db.engine, checkfirst=True)
        elif table_name == 'drivers':
            Driver.__table__.create(db.engine, checkfirst=True)
        elif table_name == 'delivery_routes':
            DeliveryRoute.__table__.create(db.engine, checkfirst=True)
        elif table_name == 'driver_locations':
            DriverLocation.__table__.create(db.engine, checkfirst=True)
        elif table_name == 'deliveries':
            Delivery.__table__.create(db.engine, checkfirst=True)
        elif table_name == 'delivery_tracking':
            DeliveryTracking.__table__.create(db.engine, checkfirst=True)
        elif table_name == 'driver_ratings':
            DriverRating.__table__.create(db.engine, checkfirst=True)
        elif table_name == 'driver_performance':
            DriverPerformance.__table__.create(db.engine, checkfirst=True)
        elif table_name == 'driver_earnings':
            DriverEarning.__table__.create(db.engine, checkfirst=True)
        elif table_name == 'delivery_feedback':
            DeliveryFeedback.__table__.create(db.engine, checkfirst=True)
    
    print("All delivery tables created successfully!")

def create_indexes():
    """Create performance indexes for delivery tables"""
    
    from app import db
    
    print("Creating performance indexes...")
    
    # Driver table indexes
    db.session.execute(text('CREATE INDEX IF NOT EXISTS idx_drivers_user_id ON drivers(user_id)'))
    db.session.execute(text('CREATE INDEX IF NOT EXISTS idx_drivers_status ON drivers(status)'))
    db.session.execute(text('CREATE INDEX IF NOT EXISTS idx_drivers_is_active ON drivers(is_active)'))
    db.session.execute(text('CREATE INDEX IF NOT EXISTS idx_drivers_location ON drivers(current_location_lat, current_location_lng)'))
    
    # Delivery table indexes
    db.session.execute(text('CREATE INDEX IF NOT EXISTS idx_deliveries_order_id ON deliveries(order_id)'))
    db.session.execute(text('CREATE INDEX IF NOT EXISTS idx_deliveries_driver_id ON deliveries(driver_id)'))
    db.session.execute(text('CREATE INDEX IF NOT EXISTS idx_deliveries_status ON deliveries(status)'))
    db.session.execute(text('CREATE INDEX IF NOT EXISTS idx_deliveries_created_at ON deliveries(created_at)'))
    db.session.execute(text('CREATE INDEX IF NOT EXISTS idx_deliveries_delivery_number ON deliveries(delivery_number)'))
    
    # Delivery route indexes
    db.session.execute(text('CREATE INDEX IF NOT EXISTS idx_delivery_routes_driver_id ON delivery_routes(driver_id)'))
    db.session.execute(text('CREATE INDEX IF NOT EXISTS idx_delivery_routes_status ON delivery_routes(status)'))
    db.session.execute(text('CREATE INDEX IF NOT EXISTS idx_delivery_routes_created_at ON delivery_routes(created_at)'))
    
    # Driver location indexes
    db.session.execute(text('CREATE INDEX IF NOT EXISTS idx_driver_locations_driver_id ON driver_locations(driver_id)'))
    db.session.execute(text('CREATE INDEX IF NOT EXISTS idx_driver_locations_timestamp ON driver_locations(timestamp)'))
    db.session.execute(text('CREATE INDEX IF NOT EXISTS idx_driver_locations_coordinates ON driver_locations(latitude, longitude)'))
    
    # Delivery tracking indexes
    db.session.execute(text('CREATE INDEX IF NOT EXISTS idx_delivery_tracking_delivery_id ON delivery_tracking(delivery_id)'))
    db.session.execute(text('CREATE INDEX IF NOT EXISTS idx_delivery_tracking_timestamp ON delivery_tracking(timestamp)'))
    
    # Driver rating indexes
    db.session.execute(text('CREATE INDEX IF NOT EXISTS idx_driver_ratings_driver_id ON driver_ratings(driver_id)'))
    db.session.execute(text('CREATE INDEX IF NOT EXISTS idx_driver_ratings_delivery_id ON driver_ratings(delivery_id)'))
    db.session.execute(text('CREATE INDEX IF NOT EXISTS idx_driver_ratings_rating_type ON driver_ratings(rating_type)'))
    
    # Driver performance indexes
    db.session.execute(text('CREATE INDEX IF NOT EXISTS idx_driver_performance_driver_id ON driver_performance(driver_id)'))
    db.session.execute(text('CREATE INDEX IF NOT EXISTS idx_driver_performance_date ON driver_performance(date)'))
    
    # Driver earnings indexes
    db.session.execute(text('CREATE INDEX IF NOT EXISTS idx_driver_earnings_driver_id ON driver_earnings(driver_id)'))
    db.session.execute(text('CREATE INDEX IF NOT EXISTS idx_driver_earnings_delivery_id ON driver_earnings(delivery_id)'))
    db.session.execute(text('CREATE INDEX IF NOT EXISTS idx_driver_earnings_earning_type ON driver_earnings(earning_type)'))
    db.session.execute(text('CREATE INDEX IF NOT EXISTS idx_driver_earnings_created_at ON driver_earnings(created_at)'))
    
    # Delivery feedback indexes
    db.session.execute(text('CREATE INDEX IF NOT EXISTS idx_delivery_feedback_delivery_id ON delivery_feedback(delivery_id)'))
    db.session.execute(text('CREATE INDEX IF NOT EXISTS idx_delivery_feedback_customer_id ON delivery_feedback(customer_id)'))
    db.session.execute(text('CREATE INDEX IF NOT EXISTS idx_delivery_feedback_created_at ON delivery_feedback(created_at)'))
    
    # Delivery zone indexes
    db.session.execute(text('CREATE INDEX IF NOT EXISTS idx_delivery_zones_is_active ON delivery_zones(is_active)'))
    db.session.execute(text('CREATE INDEX IF NOT EXISTS idx_delivery_zones_priority ON delivery_zones(priority)'))
    
    db.session.commit()
    
    print("Performance indexes created successfully!")

def seed_default_delivery_zones():
    """Create default delivery zones"""
    
    print("Seeding default delivery zones...")
    
    # Check if zones already exist
    existing_zones = DeliveryZone.query.count()
    if existing_zones > 0:
        print(f"Found {existing_zones} existing delivery zones, skipping seeding")
        return
    
    # Create default delivery zones (example for a restaurant in a city)
    default_zones = [
        {
            'name': 'City Center',
            'description': 'Central business district area',
            'zone_type': 'polygon',
            'coordinates': [
                {'lat': 40.7580, 'lng': -73.9855},  # Times Square
                {'lat': 40.7614, 'lng': -73.9776},  # Central Park South
                {'lat': 40.7489, 'lng': -73.9680},  # Grand Central
                {'lat': 40.7282, 'lng': -73.9942},  # Washington Square Park
                {'lat': 40.7489, 'lng': -74.0030}   # World Trade Center
            ],
            'base_delivery_fee': 2.99,
            'fee_per_km': 0.50,
            'minimum_order_amount': 15.00,
            'free_delivery_above': 35.00,
            'estimated_delivery_time': 25,
            'priority': 1
        },
        {
            'name': 'Midtown Manhattan',
            'description': 'Midtown area including Times Square and Grand Central',
            'zone_type': 'circle',
            'coordinates': [{'lat': 40.7580, 'lng': -73.9855}],  # Center: Times Square
            'radius': 3.0,  # 3 km radius
            'base_delivery_fee': 1.99,
            'fee_per_km': 0.75,
            'minimum_order_amount': 12.00,
            'free_delivery_above': 30.00,
            'estimated_delivery_time': 20,
            'priority': 2
        },
        {
            'name': 'Downtown Manhattan',
            'description': 'Financial district and surrounding areas',
            'zone_type': 'circle',
            'coordinates': [{'lat': 40.7074, 'lng': -74.0113}],  # Center: Wall Street
            'radius': 2.5,
            'base_delivery_fee': 2.49,
            'fee_per_km': 0.80,
            'minimum_order_amount': 15.00,
            'free_delivery_above': 40.00,
            'estimated_delivery_time': 30,
            'priority': 2
        }
    ]
    
    for zone_data in default_zones:
        zone = DeliveryZone(**zone_data)
        db.session.add(zone)
    
    try:
        db.session.commit()
        print(f"Created {len(default_zones)} default delivery zones")
    except Exception as e:
        print(f"Error creating delivery zones: {e}")
        db.session.rollback()

def add_delivery_columns_to_orders():
    """Add delivery-related columns to existing orders table if they don't exist"""
    
    from app import db
    
    print("Adding delivery columns to orders table...")
    
    # Check if delivery columns already exist
    inspector = db.inspect(db.engine)
    orders_columns = [col['name'] for col in inspector.get_columns('orders')]
    
    columns_to_add = [
        ('delivery_latitude', 'FLOAT'),
        ('delivery_longitude', 'FLOAT'),
        ('delivery_address', 'TEXT'),
        ('delivery_instructions', 'TEXT'),
        ('customer_phone_for_delivery', 'VARCHAR(20)'),
        ('contactless_delivery', 'BOOLEAN DEFAULT FALSE'),
        ('delivery_fee', 'NUMERIC(6,2) DEFAULT 0.00'),
        ('delivery_zone_id', 'INTEGER')
    ]
    
    for column_name, column_type in columns_to_add:
        if column_name not in orders_columns:
            try:
                db.session.execute(text(f'ALTER TABLE orders ADD COLUMN {column_name} {column_type}'))
                print(f"Added column: {column_name}")
            except Exception as e:
                print(f"Error adding column {column_name}: {e}")
        else:
            print(f"Column {column_name} already exists, skipping")

def run_migration():
    """Run the complete migration"""
    
    print("Starting advanced delivery system migration...")
    
    try:
        # Create tables
        create_delivery_tables()
        
        # Create indexes
        create_indexes()
        
        # Add columns to existing orders table
        add_delivery_columns_to_orders()
        
        # Seed default data
        seed_default_delivery_zones()
        
        print("Advanced delivery system migration completed successfully!")
        
    except Exception as e:
        print(f"Migration failed: {e}")
        db.session.rollback()
        raise

if __name__ == "__main__":
    run_migration()