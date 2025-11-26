#!/usr/bin/env python3
"""
Database initialization script for Restaurant POS System
Creates initial database tables and sets up default admin user
"""

from app import create_app, db
from app.models.user import User
from app.models.menu import Category, MenuItem
from app.models.table import Table, TableStatus
import os

def init_database():
    """Initialize database with tables and default data"""
    app = create_app()
    
    with app.app_context():
        print("Creating database tables...")
        db.create_all()
        
        # Create default admin user if not exists
        admin_email = os.environ.get('ADMIN_EMAIL', 'admin@restaurant.com')
        admin_password = os.environ.get('ADMIN_PASSWORD', 'admin123')
        
        admin_user = User.query.filter_by(email=admin_email).first()
        if not admin_user:
            print(f"Creating admin user: {admin_email}")
            admin_user = User(
                email=admin_email,
                name='System Administrator',
                role='admin'
            )
            admin_user.set_password(admin_password)
            admin_user.set_pin('1234')  # Default PIN for admin
            db.session.add(admin_user)
            db.session.commit()
            print("Admin user created successfully!")
        else:
            print("Admin user already exists")
        
        # Create default categories
        categories = [
            {'name': 'Appetizers', 'display_order': 1},
            {'name': 'Main Courses', 'display_order': 2},
            {'name': 'Desserts', 'display_order': 3},
            {'name': 'Beverages', 'display_order': 4}
        ]
        
        for cat_data in categories:
            category = Category.query.filter_by(name=cat_data['name']).first()
            if not category:
                print(f"Creating category: {cat_data['name']}")
                category = Category(**cat_data)
                db.session.add(category)
        
        db.session.commit()
        print("Categories created successfully!")
        
        # Create sample menu items
        appetizers = Category.query.filter_by(name='Appetizers').first()
        main_courses = Category.query.filter_by(name='Main Courses').first()
        
        if appetizers:
            sample_items = [
                {
                    'name': 'Spring Rolls',
                    'description': 'Crispy vegetable spring rolls with sweet chili sauce',
                    'price': 6.99,
                    'category_id': appetizers.id,
                    'preparation_time': 15
                },
                {
                    'name': 'Calamari',
                    'description': 'Golden fried calamari with marinara sauce',
                    'price': 9.99,
                    'category_id': appetizers.id,
                    'preparation_time': 20
                }
            ]
            
            for item_data in sample_items:
                item = MenuItem.query.filter_by(name=item_data['name']).first()
                if not item:
                    print(f"Creating menu item: {item_data['name']}")
                    item = MenuItem(**item_data)
                    db.session.add(item)
        
        if main_courses:
            main_items = [
                {
                    'name': 'Grilled Salmon',
                    'description': 'Fresh Atlantic salmon with lemon butter sauce',
                    'price': 18.99,
                    'category_id': main_courses.id,
                    'preparation_time': 25
                },
                {
                    'name': 'Ribeye Steak',
                    'description': '12oz ribeye steak with mashed potatoes',
                    'price': 24.99,
                    'category_id': main_courses.id,
                    'preparation_time': 30
                }
            ]
            
            for item_data in main_items:
                item = MenuItem.query.filter_by(name=item_data['name']).first()
                if not item:
                    print(f"Creating menu item: {item_data['name']}")
                    item = MenuItem(**item_data)
                    db.session.add(item)
        
        db.session.commit()
        print("Sample menu items created successfully!")
        
        # Create default tables
        tables = [
            {'number': 'T1', 'capacity': 4, 'floor_position_x': 50, 'floor_position_y': 50},
            {'number': 'T2', 'capacity': 4, 'floor_position_x': 150, 'floor_position_y': 50},
            {'number': 'T3', 'capacity': 2, 'floor_position_x': 50, 'floor_position_y': 150},
            {'number': 'T4', 'capacity': 6, 'floor_position_x': 150, 'floor_position_y': 150},
            {'number': 'T5', 'capacity': 8, 'floor_position_x': 250, 'floor_position_y': 100}
        ]
        
        for table_data in tables:
            table = Table.query.filter_by(number=table_data['number']).first()
            if not table:
                print(f"Creating table: {table_data['number']}")
                table = Table(**table_data)
                db.session.add(table)
        
        db.session.commit()
        print("Default tables created successfully!")
        
        print("\nDatabase initialization completed!")
        print(f"Admin login: {admin_email}")
        print(f"Admin password: {admin_password}")
        print(f"Admin PIN: 1234")
        print("\nPlease change these credentials after first login!")

def create_sample_users():
    """Create sample users for different roles"""
    app = create_app()
    
    with app.app_context():
        # Create sample cashier
        cashier = User.query.filter_by(email='cashier@restaurant.com').first()
        if not cashier:
            print("Creating sample cashier user...")
            cashier = User(
                email='cashier@restaurant.com',
                name='John Cashier',
                role='cashier'
            )
            cashier.set_password('cashier123')
            cashier.set_pin('1111')
            db.session.add(cashier)
        
        # Create sample kitchen staff
        kitchen = User.query.filter_by(email='kitchen@restaurant.com').first()
        if not kitchen:
            print("Creating sample kitchen user...")
            kitchen = User(
                email='kitchen@restaurant.com',
                name='Jane Kitchen',
                role='kitchen'
            )
            kitchen.set_password('kitchen123')
            kitchen.set_pin('2222')
            db.session.add(kitchen)
        
        # Create sample manager
        manager = User.query.filter_by(email='manager@restaurant.com').first()
        if not manager:
            print("Creating sample manager user...")
            manager = User(
                email='manager@restaurant.com',
                name='Bob Manager',
                role='manager'
            )
            manager.set_password('manager123')
            manager.set_pin('3333')
            db.session.add(manager)
        
        db.session.commit()
        print("Sample users created successfully!")
        print("\nSample User Credentials:")
        print("Cashier: cashier@restaurant.com / cashier123 (PIN: 1111)")
        print("Kitchen: kitchen@restaurant.com / kitchen123 (PIN: 2222)")
        print("Manager: manager@restaurant.com / manager123 (PIN: 3333)")

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'sample-users':
        create_sample_users()
    else:
        init_database()