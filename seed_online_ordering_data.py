"""
Seed data for Online Ordering Interface testing
Creates sample menu items, categories, and test data
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models.menu import MenuItem, Category, ItemVariant, AddOn
from app.models.user import User
from datetime import datetime

def seed_online_ordering_data():
    """Seed data for online ordering testing"""
    app = create_app()
    
    with app.app_context():
        print("Seeding Online Ordering Data...")
        
        # Check if any user exists for testing
        print("\n1. Checking for existing user...")
        test_user = User.query.first()
        if test_user:
            print(f"SUCCESS: Found existing user: {test_user.name}")
        else:
            print("WARNING: No users found in database. Please create a user first.")
            return
        
        # Create categories
        print("\n2. Creating categories...")
        categories_data = [
            {'name': 'Appetizers', 'description': 'Start your meal with our delicious appetizers'},
            {'name': 'Main Courses', 'description': 'Hearty main dishes to satisfy your hunger'},
            {'name': 'Beverages', 'description': 'Refreshing drinks and beverages'},
            {'name': 'Desserts', 'description': 'Sweet endings to your perfect meal'}
        ]
        
        created_categories = {}
        for cat_data in categories_data:
            category = Category.query.filter_by(name=cat_data['name']).first()
            if not category:
                category = Category(
                    name=cat_data['name'],
                    description=cat_data['description'],
                    is_active=True,
                    display_order=len(created_categories) + 1
                )
                db.session.add(category)
                db.session.commit()
                print(f"SUCCESS: Created category: {category.name}")
            else:
                print(f"SUCCESS: Category already exists: {category.name}")
            
            created_categories[category.name] = category
        
        # Create menu items
        print("\n3. Creating menu items...")
        menu_items_data = [
            {
                'name': 'Spring Rolls',
                'description': 'Crispy vegetable spring rolls served with sweet chili sauce',
                'price': 6.99,
                'category': 'Appetizers'
            },
            {
                'name': 'Chicken Wings',
                'description': 'Buffalo style chicken wings with celery and blue cheese dip',
                'price': 8.99,
                'category': 'Appetizers'
            },
            {
                'name': 'Grilled Salmon',
                'description': 'Fresh Atlantic salmon grilled to perfection with lemon butter sauce',
                'price': 18.99,
                'category': 'Main Courses'
            },
            {
                'name': 'Beef Burger',
                'description': 'Juicy beef patty with lettuce, tomato, onion, and special sauce',
                'price': 12.99,
                'category': 'Main Courses'
            },
            {
                'name': 'Vegetable Stir Fry',
                'description': 'Mixed vegetables stir-fried with ginger and soy sauce',
                'price': 10.99,
                'category': 'Main Courses'
            },
            {
                'name': 'Fresh Lemonade',
                'description': 'Freshly squeezed lemonade with mint',
                'price': 3.99,
                'category': 'Beverages'
            },
            {
                'name': 'Iced Coffee',
                'description': 'Cold brew coffee with ice and your choice of milk',
                'price': 4.99,
                'category': 'Beverages'
            },
            {
                'name': 'Chocolate Cake',
                'description': 'Rich chocolate cake with chocolate ganache',
                'price': 6.99,
                'category': 'Desserts'
            },
            {
                'name': 'Ice Cream Sundae',
                'description': 'Vanilla ice cream with chocolate sauce and whipped cream',
                'price': 5.99,
                'category': 'Desserts'
            }
        ]
        
        created_items = []
        for item_data in menu_items_data:
            item = MenuItem.query.filter_by(name=item_data['name']).first()
            if not item:
                item = MenuItem(
                    name=item_data['name'],
                    description=item_data['description'],
                    price=item_data['price'],
                    category_id=created_categories[item_data['category']].id,
                    is_available=True,
                    display_order=len(created_items) + 1,
                    preparation_time=15  # 15 minutes default
                )
                db.session.add(item)
                db.session.commit()
                print(f"SUCCESS: Created menu item: {item.name}")
            else:
                print(f"SUCCESS: Menu item already exists: {item.name}")
            
            created_items.append(item)
        
        # Create variants for some items
        print("\n4. Creating item variants...")
        variants_data = [
            {'item_name': 'Beef Burger', 'name': 'Small', 'price_modifier': -2.00},
            {'item_name': 'Beef Burger', 'name': 'Large', 'price_modifier': 3.00},
            {'item_name': 'Grilled Salmon', 'name': 'Half Portion', 'price_modifier': -5.00},
            {'item_name': 'Fresh Lemonade', 'name': 'Large', 'price_modifier': 1.50},
        ]
        
        for variant_data in variants_data:
            item = MenuItem.query.filter_by(name=variant_data['item_name']).first()
            if item:
                existing_variant = ItemVariant.query.filter_by(
                    item_id=item.id, 
                    name=variant_data['name']
                ).first()
                
                if not existing_variant:
                    variant = ItemVariant(
                        item_id=item.id,
                        name=variant_data['name'],
                        price_modifier=variant_data['price_modifier'],
                        is_available=True,
                        display_order=1
                    )
                    db.session.add(variant)
                    db.session.commit()
                    print(f"SUCCESS: Created variant: {variant_data['item_name']} - {variant_data['name']}")
                else:
                    print(f"SUCCESS: Variant already exists: {variant_data['item_name']} - {variant_data['name']}")
        
        # Create add-ons
        print("\n5. Creating add-ons...")
        add_ons_data = [
            {'name': 'Extra Cheese', 'price': 1.50},
            {'name': 'Bacon', 'price': 2.00},
            {'name': 'Avocado', 'price': 2.50},
            {'name': 'Extra Sauce', 'price': 0.75},
            {'name': 'Side Salad', 'price': 3.99},
            {'name': 'French Fries', 'price': 3.49},
        ]
        
        for add_on_data in add_ons_data:
            add_on = AddOn.query.filter_by(name=add_on_data['name']).first()
            if not add_on:
                add_on = AddOn(
                    name=add_on_data['name'],
                    price=add_on_data['price'],
                    is_active=True,
                    display_order=len(add_ons_data) + 1
                )
                db.session.add(add_on)
                db.session.commit()
                print(f"SUCCESS: Created add-on: {add_on.name}")
            else:
                print(f"SUCCESS: Add-on already exists: {add_on.name}")
        
        print("\nSUCCESS: Online ordering data seeding completed!")
        print(f"Created {len(created_categories)} categories")
        print(f"Created {len(created_items)} menu items")
        print("Created variants and add-ons")

if __name__ == "__main__":
    seed_online_ordering_data()