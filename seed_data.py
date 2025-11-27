#!/usr/bin/env python3
"""
Comprehensive database seeding script for Restaurant POS System
Creates realistic sample data for testing and demonstration
"""

from app import create_app, db
from app.models.user import User
from app.models.restaurant import Restaurant
from app.models.menu import Category, MenuItem, ItemVariant, AddOn
from app.models.table import Table, TableStatus
from app.models.order import Order, OrderStatus, OrderItem, Payment, PaymentMethod
from app.models.inventory import Ingredient, StockAdjustment, MenuItemIngredient
from app.models.gst import GSTSetting, HSNCode
from app.models.billing import BillingSetting, Invoice, InvoiceItem, InvoicePayment
from datetime import datetime, timedelta
import random

def seed_database():
    """Seed database with comprehensive realistic data"""
    app = create_app()
    
    with app.app_context():
        print("Clearing existing data...")
        # Clear all tables in correct order to avoid foreign key constraints
        db.session.execute(db.text("DELETE FROM invoice_payments"))
        db.session.execute(db.text("DELETE FROM invoice_items"))
        db.session.execute(db.text("DELETE FROM invoices"))
        db.session.execute(db.text("DELETE FROM billing_settings"))
        db.session.execute(db.text("DELETE FROM recurring_invoices"))
        db.session.execute(db.text("DELETE FROM stock_adjustments"))
        db.session.execute(db.text("DELETE FROM menu_item_ingredients"))
        db.session.execute(db.text("DELETE FROM ingredients"))
        db.session.execute(db.text("DELETE FROM payments"))
        db.session.execute(db.text("DELETE FROM order_items"))
        db.session.execute(db.text("DELETE FROM orders"))
        db.session.execute(db.text("DELETE FROM order_item_add_ons"))
        db.session.execute(db.text("DELETE FROM item_add_ons"))
        db.session.execute(db.text("DELETE FROM item_variants"))
        db.session.execute(db.text("DELETE FROM add_ons"))
        db.session.execute(db.text("DELETE FROM menu_items"))
        db.session.execute(db.text("DELETE FROM categories"))
        db.session.execute(db.text("DELETE FROM tables"))
        db.session.execute(db.text("DELETE FROM gst_settings"))
        db.session.execute(db.text("DELETE FROM hsn_codes"))
        db.session.execute(db.text("DELETE FROM users"))
        db.session.execute(db.text("DELETE FROM restaurants"))
        db.session.commit()
        
        print("Creating restaurant...")
        # Create main restaurant
        restaurant = Restaurant(
            name="The Golden Fork",
            address="123 Main Street, Downtown, Mumbai 400001",
            phone="+91-22-23456789",
            email="info@goldenfork.com",
            gst_number="27AAAPL1234C1ZV",
            license_number="FSSAI/12345678901234",
            description="A fine dining restaurant serving authentic Indian and continental cuisine since 2010.",
            currency="INR",
            timezone="Asia/Kolkata"
        )
        db.session.add(restaurant)
        db.session.commit()
        
        print("Creating GST settings...")
        # Create GST settings
        gst_setting = GSTSetting(
            restaurant_id=restaurant.id,
            cgst_rate=0.09,  # 9% CGST
            sgst_rate=0.09,  # 9% SGST
            igst_rate=0.00,  # 0% IGST (same state)
            cess_rate=0.00,  # 0% CESS
            is_active=True
        )
        db.session.add(gst_setting)
        
        # Create HSN codes
        hsn_codes = [
            HSNCode(code="996311", description="Restaurant services", tax_rate=0.18, category="Services"),
            HSNCode(code="996339", description="Catering services", tax_rate=0.18, category="Services"),
            HSNCode(code="210690", description="Food preparations", tax_rate=0.05, category="Goods"),
            HSNCode(code="0902", description="Tea", tax_rate=0.05, category="Goods"),
            HSNCode(code="0901", description="Coffee", tax_rate=0.05, category="Goods"),
            HSNCode(code="2203", description="Beer", tax_rate=0.18, category="Goods"),
            HSNCode(code="2204", description="Wine", tax_rate=0.18, category="Goods"),
            HSNCode(code="2208", description="Spirits", tax_rate=0.18, category="Goods")
        ]
        for hsn in hsn_codes:
            db.session.add(hsn)
        db.session.commit()
        
        print("Creating users...")
        # Create users with different roles
        users = [
            {
                'email': 'admin@goldenfork.com',
                'name': 'Rajesh Kumar',
                'role': 'super_admin',
                'password': 'admin123',
                'pin': '1234',
                'phone': '+91-9876543210'
            },
            {
                'email': 'manager@goldenfork.com',
                'name': 'Priya Sharma',
                'role': 'manager',
                'password': 'manager123',
                'pin': '5678',
                'phone': '+91-9876543211',
                'restaurant_id': restaurant.id
            },
            {
                'email': 'cashier1@goldenfork.com',
                'name': 'Amit Patel',
                'role': 'cashier',
                'password': 'cashier123',
                'pin': '1111',
                'phone': '+91-9876543212',
                'restaurant_id': restaurant.id
            },
            {
                'email': 'cashier2@goldenfork.com',
                'name': 'Sneha Reddy',
                'role': 'cashier',
                'password': 'cashier123',
                'pin': '2222',
                'phone': '+91-9876543213',
                'restaurant_id': restaurant.id
            },
            {
                'email': 'kitchen@goldenfork.com',
                'name': 'Chef Vijay',
                'role': 'kitchen',
                'password': 'kitchen123',
                'pin': '3333',
                'phone': '+91-9876543214',
                'restaurant_id': restaurant.id
            },
            {
                'email': 'staff@goldenfork.com',
                'name': 'Rohit Verma',
                'role': 'staff',
                'password': 'staff123',
                'pin': '4444',
                'phone': '+91-9876543215',
                'restaurant_id': restaurant.id
            }
        ]
        
        created_users = []
        for user_data in users:
            user = User()
            user.email = user_data['email']
            user.name = user_data['name']
            user.role = user_data['role']
            user.restaurant_id = user_data.get('restaurant_id')
            user.phone = user_data.get('phone')
            user.set_password(user_data['password'])
            user.set_pin(user_data['pin'])
            db.session.add(user)
            created_users.append(user)
        db.session.commit()
        
        print("Creating billing settings...")
        # Create billing settings
        billing_setting = BillingSetting(
            restaurant_id=restaurant.id,
            invoice_prefix='GF',
            auto_generate_numbers=True,
            next_invoice_number=1001,
            default_payment_terms=30,
            allow_partial_payments=True,
            auto_send_reminders=True,
            reminder_days='7,14,30',
            default_tax_rate=0.18,
            tax_inclusive=True,
            currency_code='INR',
            currency_symbol='₹',
            email_from_address='billing@goldenfork.com',
            email_from_name='The Golden Fork'
        )
        db.session.add(billing_setting)
        db.session.commit()
        
        print("Creating ingredients...")
        # Create ingredients for inventory
        ingredients = [
            {'name': 'Basmati Rice', 'unit': 'kg', 'current_stock': 50.0, 'minimum_stock': 10.0, 'unit_cost': 120.00, 'supplier': 'Royal Foods'},
            {'name': 'Chicken Breast', 'unit': 'kg', 'current_stock': 25.0, 'minimum_stock': 5.0, 'unit_cost': 280.00, 'supplier': 'Fresh Meat Co.'},
            {'name': 'Tomatoes', 'unit': 'kg', 'current_stock': 15.0, 'minimum_stock': 3.0, 'unit_cost': 40.00, 'supplier': 'Local Farms'},
            {'name': 'Onions', 'unit': 'kg', 'current_stock': 20.0, 'minimum_stock': 5.0, 'unit_cost': 35.00, 'supplier': 'Local Farms'},
            {'name': 'Garlic', 'unit': 'kg', 'current_stock': 5.0, 'minimum_stock': 1.0, 'unit_cost': 150.00, 'supplier': 'Spice World'},
            {'name': 'Ginger', 'unit': 'kg', 'current_stock': 3.0, 'minimum_stock': 0.5, 'unit_cost': 120.00, 'supplier': 'Spice World'},
            {'name': 'Green Chillies', 'unit': 'kg', 'current_stock': 2.0, 'minimum_stock': 0.5, 'unit_cost': 80.00, 'supplier': 'Local Farms'},
            {'name': 'Coriander Leaves', 'unit': 'kg', 'current_stock': 1.5, 'minimum_stock': 0.3, 'unit_cost': 60.00, 'supplier': 'Local Farms'},
            {'name': 'Lemons', 'unit': 'pcs', 'current_stock': 50.0, 'minimum_stock': 10.0, 'unit_cost': 3.00, 'supplier': 'Citrus Grove'},
            {'name': 'Potatoes', 'unit': 'kg', 'current_stock': 30.0, 'minimum_stock': 8.0, 'unit_cost': 25.00, 'supplier': 'Local Farms'},
            {'name': 'Paneer', 'unit': 'kg', 'current_stock': 10.0, 'minimum_stock': 2.0, 'unit_cost': 200.00, 'supplier': 'Dairy Fresh'},
            {'name': 'Milk', 'unit': 'l', 'current_stock': 20.0, 'minimum_stock': 5.0, 'unit_cost': 45.00, 'supplier': 'Dairy Fresh'},
            {'name': 'Butter', 'unit': 'kg', 'current_stock': 5.0, 'minimum_stock': 1.0, 'unit_cost': 320.00, 'supplier': 'Dairy Fresh'},
            {'name': 'Wheat Flour', 'unit': 'kg', 'current_stock': 40.0, 'minimum_stock': 10.0, 'unit_cost': 40.00, 'supplier': 'Royal Foods'},
            {'name': 'Cooking Oil', 'unit': 'l', 'current_stock': 15.0, 'minimum_stock': 3.0, 'unit_cost': 110.00, 'supplier': 'Oil Mills'},
            {'name': 'Sugar', 'unit': 'kg', 'current_stock': 25.0, 'minimum_stock': 5.0, 'unit_cost': 45.00, 'supplier': 'Royal Foods'},
            {'name': 'Salt', 'unit': 'kg', 'current_stock': 10.0, 'minimum_stock': 2.0, 'unit_cost': 20.00, 'supplier': 'Royal Foods'},
            {'name': 'Turmeric Powder', 'unit': 'kg', 'current_stock': 2.0, 'minimum_stock': 0.5, 'unit_cost': 200.00, 'supplier': 'Spice World'},
            {'name': 'Red Chili Powder', 'unit': 'kg', 'current_stock': 2.0, 'minimum_stock': 0.5, 'unit_cost': 180.00, 'supplier': 'Spice World'},
            {'name': 'Garam Masala', 'unit': 'kg', 'current_stock': 1.5, 'minimum_stock': 0.3, 'unit_cost': 250.00, 'supplier': 'Spice World'},
            {'name': 'Tea Leaves', 'unit': 'kg', 'current_stock': 5.0, 'minimum_stock': 1.0, 'unit_cost': 300.00, 'supplier': 'Tea Gardens'},
            {'name': 'Coffee Powder', 'unit': 'kg', 'current_stock': 3.0, 'minimum_stock': 0.5, 'unit_cost': 450.00, 'supplier': 'Coffee Estates'},
            {'name': 'Eggs', 'unit': 'pcs', 'current_stock': 100.0, 'minimum_stock': 20.0, 'unit_cost': 6.00, 'supplier': 'Happy Farms'},
            {'name': 'Bread', 'unit': 'pcs', 'current_stock': 30.0, 'minimum_stock': 10.0, 'unit_cost': 25.00, 'supplier': 'Local Bakery'},
            {'name': 'Cheese', 'unit': 'kg', 'current_stock': 8.0, 'minimum_stock': 2.0, 'unit_cost': 400.00, 'supplier': 'Dairy Fresh'}
        ]
        
        created_ingredients = []
        for ing_data in ingredients:
            ingredient = Ingredient(**ing_data)
            db.session.add(ingredient)
            created_ingredients.append(ingredient)
        db.session.commit()
        
        print("Creating menu categories...")
        # Create menu categories
        categories = [
            {'name': 'Appetizers', 'description': 'Starters and small bites', 'display_order': 1},
            {'name': 'Soups & Salads', 'description': 'Fresh and healthy options', 'display_order': 2},
            {'name': 'Main Course - Vegetarian', 'description': 'Traditional vegetarian dishes', 'display_order': 3},
            {'name': 'Main Course - Non-Vegetarian', 'description': 'Meat and poultry specialties', 'display_order': 4},
            {'name': 'Breads & Rice', 'description': 'Indian breads and rice dishes', 'display_order': 5},
            {'name': 'Desserts', 'description': 'Sweet endings', 'display_order': 6},
            {'name': 'Beverages', 'description': 'Hot and cold drinks', 'display_order': 7}
        ]
        
        created_categories = []
        for cat_data in categories:
            category = Category(**cat_data)
            db.session.add(category)
            created_categories.append(category)
        db.session.commit()
        
        print("Creating add-ons...")
        # Create add-ons
        add_ons = [
            {'name': 'Extra Cheese', 'description': 'Additional cheese topping', 'price': 30.00, 'display_order': 1},
            {'name': 'Extra Spice', 'description': 'Make it extra spicy', 'price': 10.00, 'display_order': 2},
            {'name': 'Jalapenos', 'description': 'Fresh jalapeno slices', 'price': 25.00, 'display_order': 3},
            {'name': 'Olives', 'description': 'Mediterranean olives', 'price': 35.00, 'display_order': 4},
            {'name': 'Mushrooms', 'description': 'Fresh mushroom topping', 'price': 40.00, 'display_order': 5},
            {'name': 'Extra Sauce', 'description': 'Additional sauce on the side', 'price': 20.00, 'display_order': 6},
            {'name': 'Garlic Bread', 'description': '2 pieces of garlic bread', 'price': 60.00, 'display_order': 7},
            {'name': 'French Fries', 'description': 'Crispy french fries', 'price': 80.00, 'display_order': 8}
        ]
        
        created_add_ons = []
        for addon_data in add_ons:
            add_on = AddOn(**addon_data)
            db.session.add(add_on)
            created_add_ons.append(add_on)
        db.session.commit()
        
        print("Creating menu items...")
        # Create menu items with realistic Indian restaurant data
        menu_items = [
            # Appetizers
            {'name': 'Paneer Tikka', 'description': 'Cubes of cottage cheese marinated in spices and grilled in tandoor', 'price': 220.00, 'category_id': created_categories[0].id, 'preparation_time': 20},
            {'name': 'Chicken Tikka', 'description': 'Tender chicken pieces marinated in yogurt and spices, grilled in tandoor', 'price': 280.00, 'category_id': created_categories[0].id, 'preparation_time': 25},
            {'name': 'Vegetable Spring Rolls', 'description': 'Crispy rolls filled with mixed vegetables', 'price': 180.00, 'category_id': created_categories[0].id, 'preparation_time': 15},
            {'name': 'Samosa', 'description': 'Crispy pastry filled with spiced potatoes and peas', 'price': 60.00, 'category_id': created_categories[0].id, 'preparation_time': 10},
            
            # Soups & Salads
            {'name': 'Tomato Soup', 'description': 'Fresh tomato soup with herbs and cream', 'price': 120.00, 'category_id': created_categories[1].id, 'preparation_time': 15},
            {'name': 'Chicken Manchow Soup', 'description': 'Spicy Chinese-style soup with chicken and vegetables', 'price': 160.00, 'category_id': created_categories[1].id, 'preparation_time': 20},
            {'name': 'Greek Salad', 'description': 'Fresh vegetables with feta cheese and olive oil dressing', 'price': 180.00, 'category_id': created_categories[1].id, 'preparation_time': 10},
            {'name': 'Caesar Salad', 'description': 'Romaine lettuce with parmesan and croutons', 'price': 200.00, 'category_id': created_categories[1].id, 'preparation_time': 10},
            
            # Main Course - Vegetarian
            {'name': 'Palak Paneer', 'description': 'Cottage cheese cubes in creamy spinach gravy', 'price': 260.00, 'category_id': created_categories[2].id, 'preparation_time': 25},
            {'name': 'Paneer Butter Masala', 'description': 'Cottage cheese in rich tomato and butter gravy', 'price': 280.00, 'category_id': created_categories[2].id, 'preparation_time': 25},
            {'name': 'Dal Makhani', 'description': 'Creamy black lentils cooked with butter and cream', 'price': 220.00, 'category_id': created_categories[2].id, 'preparation_time': 30},
            {'name': 'Malai Kofta', 'description': 'Vegetable dumplings in rich creamy gravy', 'price': 240.00, 'category_id': created_categories[2].id, 'preparation_time': 25},
            {'name': 'Mixed Vegetable Curry', 'description': 'Seasonal vegetables in aromatic gravy', 'price': 200.00, 'category_id': created_categories[2].id, 'preparation_time': 20},
            
            # Main Course - Non-Vegetarian
            {'name': 'Butter Chicken', 'description': 'Tender chicken in rich tomato and butter gravy', 'price': 320.00, 'category_id': created_categories[3].id, 'preparation_time': 30},
            {'name': 'Chicken Biryani', 'description': 'Fragrant basmati rice with spiced chicken', 'price': 280.00, 'category_id': created_categories[3].id, 'preparation_time': 35},
            {'name': 'Lamb Rogan Josh', 'description': 'Tender lamb pieces in Kashmiri-style gravy', 'price': 380.00, 'category_id': created_categories[3].id, 'preparation_time': 40},
            {'name': 'Fish Curry', 'description': 'Fresh fish fillets in spicy coconut gravy', 'price': 340.00, 'category_id': created_categories[3].id, 'preparation_time': 30},
            {'name': 'Egg Curry', 'description': 'Hard-boiled eggs in spicy onion-tomato gravy', 'price': 180.00, 'category_id': created_categories[3].id, 'preparation_time': 20},
            
            # Breads & Rice
            {'name': 'Butter Naan', 'description': 'Soft leavened bread with butter', 'price': 40.00, 'category_id': created_categories[4].id, 'preparation_time': 10},
            {'name': 'Garlic Naan', 'description': 'Naan bread stuffed with garlic', 'price': 50.00, 'category_id': created_categories[4].id, 'preparation_time': 10},
            {'name': 'Tandoori Roti', 'description': 'Whole wheat bread cooked in tandoor', 'price': 25.00, 'category_id': created_categories[4].id, 'preparation_time': 8},
            {'name': 'Plain Rice', 'description': 'Steamed basmati rice', 'price': 80.00, 'category_id': created_categories[4].id, 'preparation_time': 15},
            {'name': 'Jeera Rice', 'description': 'Basmati rice tempered with cumin', 'price': 100.00, 'category_id': created_categories[4].id, 'preparation_time': 15},
            
            # Desserts
            {'name': 'Gulab Jamun', 'description': 'Soft milk dumplings in sugar syrup', 'price': 80.00, 'category_id': created_categories[5].id, 'preparation_time': 5},
            {'name': 'Rasmalai', 'description': 'Soft cottage cheese dumplings in creamy milk', 'price': 100.00, 'category_id': created_categories[5].id, 'preparation_time': 5},
            {'name': 'Ice Cream', 'description': 'Vanilla/Chocolate/Strawberry ice cream', 'price': 120.00, 'category_id': created_categories[5].id, 'preparation_time': 5},
            {'name': 'Brownie with Ice Cream', 'description': 'Warm chocolate brownie with vanilla ice cream', 'price': 150.00, 'category_id': created_categories[5].id, 'preparation_time': 10},
            
            # Beverages
            {'name': 'Masala Tea', 'description': 'Indian spiced tea', 'price': 40.00, 'category_id': created_categories[6].id, 'preparation_time': 5},
            {'name': 'Filter Coffee', 'description': 'South Indian filter coffee', 'price': 50.00, 'category_id': created_categories[6].id, 'preparation_time': 5},
            {'name': 'Fresh Lime Soda', 'description': 'Refreshing lime soda with salt/sugar', 'price': 60.00, 'category_id': created_categories[6].id, 'preparation_time': 5},
            {'name': 'Mango Lassi', 'description': 'Sweet yogurt drink with mango flavor', 'price': 80.00, 'category_id': created_categories[6].id, 'preparation_time': 5},
            {'name': 'Mineral Water', 'description': 'Bottled mineral water', 'price': 40.00, 'category_id': created_categories[6].id, 'preparation_time': 2},
            {'name': 'Coca Cola', 'description': '300ml Coca Cola', 'price': 50.00, 'category_id': created_categories[6].id, 'preparation_time': 2}
        ]
        
        created_menu_items = []
        for item_data in menu_items:
            menu_item = MenuItem(**item_data)
            db.session.add(menu_item)
            created_menu_items.append(menu_item)
        db.session.commit()
        
        print("Creating menu item variants...")
        # Create variants for some menu items
        variants = [
            {'item_id': created_menu_items[22].id, 'name': 'Regular', 'price_modifier': 0.00},  # Butter Naan
            {'item_id': created_menu_items[22].id, 'name': 'Extra Butter', 'price_modifier': 20.00},
            {'item_id': created_menu_items[23].id, 'name': 'Regular', 'price_modifier': 0.00},  # Garlic Naan
            {'item_id': created_menu_items[23].id, 'name': 'Extra Garlic', 'price_modifier': 15.00},
            {'item_id': created_menu_items[25].id, 'name': 'Regular', 'price_modifier': 0.00},  # Plain Rice
            {'item_id': created_menu_items[25].id, 'name': 'Large Portion', 'price_modifier': 40.00},
            {'item_id': created_menu_items[30].id, 'name': 'Vanilla', 'price_modifier': 0.00},  # Ice Cream
            {'item_id': created_menu_items[30].id, 'name': 'Chocolate', 'price_modifier': 0.00},
            {'item_id': created_menu_items[30].id, 'name': 'Strawberry', 'price_modifier': 0.00},
            {'item_id': created_menu_items[30].id, 'name': 'Salt', 'price_modifier': 0.00},  # Fresh Lime Soda
            {'item_id': created_menu_items[30].id, 'name': 'Sugar', 'price_modifier': 0.00},
            {'item_id': created_menu_items[30].id, 'name': 'Salt & Sugar', 'price_modifier': 0.00}
        ]
        
        for variant_data in variants:
            variant = ItemVariant(**variant_data)
            db.session.add(variant)
        db.session.commit()
        
        print("Creating menu item ingredients...")
        # Create ingredient mappings for menu items
        menu_item_ingredients = [
            # Paneer Tikka
            {'menu_item_id': created_menu_items[0].id, 'ingredient_id': created_ingredients[10].id, 'quantity_required': 0.200},  # Paneer
            {'menu_item_id': created_menu_items[0].id, 'ingredient_id': created_ingredients[15].id, 'quantity_required': 0.050},  # Cooking Oil
            {'menu_item_id': created_menu_items[0].id, 'ingredient_id': created_ingredients[5].id, 'quantity_required': 0.020},  # Ginger
            {'menu_item_id': created_menu_items[0].id, 'ingredient_id': created_ingredients[4].id, 'quantity_required': 0.020},  # Garlic
            {'menu_item_id': created_menu_items[0].id, 'ingredient_id': created_ingredients[17].id, 'quantity_required': 0.010},  # Red Chili Powder
            {'menu_item_id': created_menu_items[0].id, 'ingredient_id': created_ingredients[18].id, 'quantity_required': 0.010},  # Garam Masala
            
            # Chicken Tikka
            {'menu_item_id': created_menu_items[1].id, 'ingredient_id': created_ingredients[1].id, 'quantity_required': 0.250},  # Chicken Breast
            {'menu_item_id': created_menu_items[1].id, 'ingredient_id': created_ingredients[11].id, 'quantity_required': 0.100},  # Milk
            {'menu_item_id': created_menu_items[1].id, 'ingredient_id': created_ingredients[15].id, 'quantity_required': 0.050},  # Cooking Oil
            {'menu_item_id': created_menu_items[1].id, 'ingredient_id': created_ingredients[4].id, 'quantity_required': 0.020},  # Garlic
            {'menu_item_id': created_menu_items[1].id, 'ingredient_id': created_ingredients[5].id, 'quantity_required': 0.020},  # Ginger
            
            # Butter Chicken
            {'menu_item_id': created_menu_items[14].id, 'ingredient_id': created_ingredients[1].id, 'quantity_required': 0.300},  # Chicken Breast
            {'menu_item_id': created_menu_items[14].id, 'ingredient_id': created_ingredients[12].id, 'quantity_required': 0.080},  # Butter
            {'menu_item_id': created_menu_items[14].id, 'ingredient_id': created_ingredients[11].id, 'quantity_required': 0.150},  # Milk
            {'menu_item_id': created_menu_items[14].id, 'ingredient_id': created_ingredients[2].id, 'quantity_required': 0.150},  # Tomatoes
            {'menu_item_id': created_menu_items[14].id, 'ingredient_id': created_ingredients[3].id, 'quantity_required': 0.100},  # Onions
            
            # Palak Paneer
            {'menu_item_id': created_menu_items[9].id, 'ingredient_id': created_ingredients[10].id, 'quantity_required': 0.200},  # Paneer
            {'menu_item_id': created_menu_items[9].id, 'ingredient_id': created_ingredients[7].id, 'quantity_required': 0.300},  # Coriander Leaves
            {'menu_item_id': created_menu_items[9].id, 'ingredient_id': created_ingredients[11].id, 'quantity_required': 0.100},  # Milk
            {'menu_item_id': created_menu_items[9].id, 'ingredient_id': created_ingredients[12].id, 'quantity_required': 0.050},  # Butter
            {'menu_item_id': created_menu_items[9].id, 'ingredient_id': created_ingredients[4].id, 'quantity_required': 0.020},  # Garlic
            
            # Dal Makhani
            {'menu_item_id': created_menu_items[11].id, 'ingredient_id': created_ingredients[0].id, 'quantity_required': 0.100},  # Basmati Rice (for serving)
            {'menu_item_id': created_menu_items[11].id, 'ingredient_id': created_ingredients[11].id, 'quantity_required': 0.200},  # Milk
            {'menu_item_id': created_menu_items[11].id, 'ingredient_id': created_ingredients[12].id, 'quantity_required': 0.060},  # Butter
            {'menu_item_id': created_menu_items[11].id, 'ingredient_id': created_ingredients[3].id, 'quantity_required': 0.080},  # Onions
            {'menu_item_id': created_menu_items[11].id, 'ingredient_id': created_ingredients[18].id, 'quantity_required': 0.015},  # Garam Masala
        ]
        
        for mii_data in menu_item_ingredients:
            mii = MenuItemIngredient(**mii_data)
            db.session.add(mii)
        db.session.commit()
        
        print("Creating tables...")
        # Create restaurant tables
        tables = [
            {'number': 'T1', 'name': 'Window Seat 1', 'capacity': 4, 'floor_position_x': 50, 'floor_position_y': 50, 'floor_section': 'Main Dining'},
            {'number': 'T2', 'name': 'Window Seat 2', 'capacity': 4, 'floor_position_x': 150, 'floor_position_y': 50, 'floor_section': 'Main Dining'},
            {'number': 'T3', 'name': 'Corner Booth 1', 'capacity': 2, 'floor_position_x': 50, 'floor_position_y': 150, 'floor_section': 'Main Dining'},
            {'number': 'T4', 'name': 'Corner Booth 2', 'capacity': 2, 'floor_position_x': 150, 'floor_position_y': 150, 'floor_section': 'Main Dining'},
            {'number': 'T5', 'name': 'Family Table 1', 'capacity': 6, 'floor_position_x': 250, 'floor_position_y': 100, 'floor_section': 'Family Section'},
            {'number': 'T6', 'name': 'Family Table 2', 'capacity': 6, 'floor_position_x': 350, 'floor_position_y': 100, 'floor_section': 'Family Section'},
            {'number': 'T7', 'name': 'Private Dining 1', 'capacity': 8, 'floor_position_x': 50, 'floor_position_y': 250, 'floor_section': 'Private Dining'},
            {'number': 'T8', 'name': 'Private Dining 2', 'capacity': 8, 'floor_position_x': 150, 'floor_position_y': 250, 'floor_section': 'Private Dining'},
            {'number': 'T9', 'name': 'Bar Table 1', 'capacity': 2, 'floor_position_x': 250, 'floor_position_y': 200, 'floor_section': 'Bar Area'},
            {'number': 'T10', 'name': 'Bar Table 2', 'capacity': 2, 'floor_position_x': 350, 'floor_position_y': 200, 'floor_section': 'Bar Area'},
            {'number': 'T11', 'name': 'Outdoor Table 1', 'capacity': 4, 'floor_position_x': 450, 'floor_position_y': 50, 'floor_section': 'Patio'},
            {'number': 'T12', 'name': 'Outdoor Table 2', 'capacity': 4, 'floor_position_x': 450, 'floor_position_y': 150, 'floor_section': 'Patio'}
        ]
        
        created_tables = []
        for table_data in tables:
            table = Table(**table_data)
            db.session.add(table)
            created_tables.append(table)
        db.session.commit()
        
        print("Creating sample orders...")
        # Create sample orders with realistic data
        order_statuses = [OrderStatus.PENDING, OrderStatus.CONFIRMED, OrderStatus.PREPARING, OrderStatus.READY, OrderStatus.SERVED]
        payment_methods = [PaymentMethod.CASH, PaymentMethod.CARD, PaymentMethod.UPI, PaymentMethod.WALLET]
        
        # Create orders for the last few days
        for days_ago in range(7, 0, -1):
            for hour in range(11, 23):  # Restaurant hours 11 AM to 11 PM
                if random.random() < 0.3:  # 30% chance of order in each hour
                    order_date = datetime.now() - timedelta(days=days_ago, hours=(23 - hour))
                    
                    # Random table
                    table = random.choice(created_tables)
                    
                    # Random user (cashier)
                    user = random.choice([u for u in created_users if u.role in ['cashier', 'manager']])
                    
                    # Create order
                    order = Order(
                        table_id=table.id,
                        user_id=user.id,
                        status=random.choice(order_statuses),
                        created_at=order_date,
                        updated_at=order_date
                    )
                    
                    # Add random items to order
                    num_items = random.randint(2, 6)
                    selected_items = random.sample(created_menu_items, min(num_items, len(created_menu_items)))
                    
                    order_items = []
                    for menu_item in selected_items:
                        quantity = random.randint(1, 3)
                        order_item = OrderItem(
                            item_id=menu_item.id,
                            quantity=quantity,
                            unit_price=menu_item.price
                        )
                        order_items.append(order_item)
                        order.items.append(order_item)
                    
                    # Calculate totals
                    order.calculate_totals()
                    
                    # Add payment if order is completed
                    if order.status in [OrderStatus.SERVED]:
                        payment = Payment(
                            order_id=order.id,
                            amount=order.total,
                            method=random.choice(payment_methods),
                            status='completed',
                            created_at=order_date + timedelta(minutes=random.randint(5, 30))
                        )
                        order.payments.append(payment)
                    
                    db.session.add(order)
        
        db.session.commit()
        
        print("Creating sample invoices...")
        # Create sample invoices for bulk customers
        customers = [
            {'name': 'ABC Corporation', 'email': 'accounts@abccorp.com', 'phone': '+91-22-23456781'},
            {'name': 'XYZ Technologies', 'email': 'finance@xyztech.com', 'phone': '+91-22-23456782'},
            {'name': 'Global Services Ltd', 'email': 'billing@globalservices.com', 'phone': '+91-22-23456783'}
        ]
        
        for i, customer in enumerate(customers):
            invoice = Invoice(
                invoice_number=f'GF{2024}{1001 + i:04d}',
                restaurant_id=restaurant.id,
                customer_name=customer['name'],
                customer_email=customer['email'],
                customer_phone=customer['phone'],
                issue_date=datetime.now() - timedelta(days=random.randint(1, 30)),
                due_date=datetime.now() + timedelta(days=30),
                status=random.choice(['sent', 'paid', 'draft']),
                subtotal=random.uniform(5000, 25000),
                tax_amount=0,
                total_amount=0,
                paid_amount=0,
                balance_amount=0
            )
            
            # Calculate tax and total
            tax_amount = float(invoice.subtotal) * 0.18
            invoice.tax_amount = tax_amount
            invoice.total_amount = float(invoice.subtotal) + tax_amount
            invoice.balance_amount = invoice.total_amount
            
            if invoice.status == 'paid':
                invoice.paid_amount = invoice.total_amount
                invoice.balance_amount = 0
                invoice.paid_at = datetime.now() - timedelta(days=random.randint(1, 15))
            
            # Add invoice items
            num_items = random.randint(3, 8)
            for j in range(num_items):
                item_description = random.choice([
                    'Catering Service - Corporate Event',
                    'Bulk Food Delivery - Monthly Supply',
                    'Event Management - Annual Party',
                    'Special Menu Development',
                    'Staff Training Services',
                    'Equipment Rental'
                ])
                
                quantity = random.randint(1, 10)
                unit_price = random.uniform(500, 3000)
                total_price = quantity * unit_price
                
                invoice_item = InvoiceItem(
                    description=item_description,
                    quantity=quantity,
                    unit_price=unit_price,
                    total_price=total_price
                )
                invoice.items.append(invoice_item)
            
            # Add payment if paid
            if invoice.status == 'paid':
                payment = InvoicePayment(
                    invoice_id=invoice.id,
                    amount=invoice.total_amount,
                    payment_method=random.choice(['bank_transfer', 'card']),
                    payment_date=invoice.paid_at
                )
                invoice.payments.append(payment)
            
            db.session.add(invoice)
        
        db.session.commit()
        
        print("Creating stock adjustments...")
        # Create some stock adjustments
        for ingredient in created_ingredients[:10]:  # Adjust stock for first 10 ingredients
            # Random adjustment
            adjustment_type = random.choice(['Stock In', 'Stock Out'])
            if adjustment_type == 'Stock In':
                quantity = random.uniform(1, 20)
                reason = random.choice(['Purchase', 'Return', 'Correction'])
            else:
                quantity = -random.uniform(0.5, 10)
                reason = random.choice(['Usage', 'Waste', 'Spoilage'])
            
            adjustment = StockAdjustment(
                ingredient_id=ingredient.id,
                quantity=float(quantity),
                previous_quantity=float(ingredient.current_stock) - float(quantity),
                new_quantity=float(ingredient.current_stock),
                reason=reason,
                user_id=created_users[2].id  # Manager
            )
            db.session.add(adjustment)
        
        db.session.commit()
        
        print("\n" + "="*50)
        print("DATABASE SEEDING COMPLETED SUCCESSFULLY!")
        print("="*50)
        print(f"\nRestaurant: {restaurant.name}")
        print(f"Address: {restaurant.address}")
        print(f"Phone: {restaurant.phone}")
        print(f"Email: {restaurant.email}")
        
        print("\nUSER CREDENTIALS:")
        print("-" * 30)
        for user in created_users:
            print(f"{user.get_role_display_name()}: {user.email}")
            print(f"  Password: {'admin123' if user.role == 'super_admin' else user.role + '123'}")
            print(f"  PIN: {user.pin_code if user.pin_code else 'N/A'}")
            print()
        
        print("MENU SUMMARY:")
        print("-" * 30)
        for category in created_categories:
            items_count = len([item for item in created_menu_items if item.category_id == category.id])
            print(f"{category.name}: {items_count} items")
        
        print(f"\nTotal Tables: {len(created_tables)}")
        print(f"Total Ingredients: {len(created_ingredients)}")
        print(f"Total Menu Items: {len(created_menu_items)}")
        print(f"Total Users: {len(created_users)}")
        
        print("\nSample Data Created:")
        print("-" * 30)
        print(f"Orders: {Order.query.count()}")
        print(f"Payments: {Payment.query.count()}")
        print(f"Invoices: {Invoice.query.count()}")
        print(f"Stock Adjustments: {StockAdjustment.query.count()}")
        
        print("\n" + "="*50)
        print("You can now start the application and login with any of the above credentials!")
        print("="*50)

if __name__ == '__main__':
    seed_database()