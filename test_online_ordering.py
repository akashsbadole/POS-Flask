"""
Test script for Online Ordering Interface
Tests the complete flow from menu browsing to order creation
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models.menu import MenuItem, Category, ItemVariant, AddOn
from app.models.order import Order, OrderItem, OrderStatus, OrderType
from app.models.customer import Customer
from app.models.user import User
from datetime import datetime

def test_online_ordering():
    """Test online ordering functionality"""
    app = create_app()
    
    with app.app_context():
        print("Testing Online Ordering Interface...")
        
        # Test 1: Check if menu items exist
        print("\n1. Checking menu items...")
        menu_items = MenuItem.query.filter_by(is_available=True).limit(5).all()
        if menu_items:
            print(f"SUCCESS: Found {len(menu_items)} available menu items")
            for item in menu_items:
                print(f"  - {item.name}: ${item.price}")
        else:
            print("ERROR: No available menu items found")
            return False
        
        # Test 2: Check categories
        print("\n2. Checking categories...")
        categories = Category.query.filter_by(is_active=True).all()
        if categories:
            print(f"SUCCESS: Found {len(categories)} active categories")
            for cat in categories:
                print(f"  - {cat.name}")
        else:
            print("ERROR: No active categories found")
            return False
        
        # Test 3: Check if OrderType enum works
        print("\n3. Testing OrderType enum...")
        try:
            order_types = [OrderType.DINE_IN, OrderType.TAKEAWAY, OrderType.DELIVERY]
            print(f"SUCCESS: OrderType enum values: {[ot.value for ot in order_types]}")
        except Exception as e:
            print(f"ERROR: OrderType enum error: {e}")
            return False
        
        # Test 4: Create test customer
        print("\n4. Creating test customer...")
        try:
            # Generate unique customer code using timestamp
            import time
            unique_code = f"TEST{int(time.time()) % 10000:04d}"
            
            test_customer = Customer(
                customer_code=unique_code,
                first_name='Test',
                last_name='Customer',
                email=f"test{unique_code}@example.com",
                phone=f"123456789{unique_code[-3:]}",
                loyalty_member=False,
                restaurant_id=1  # Assuming restaurant with ID 1 exists
            )
            db.session.add(test_customer)
            db.session.commit()
            print(f"SUCCESS: Created test customer: {test_customer.first_name} {test_customer.last_name}")
        except Exception as e:
            print(f"ERROR: Error creating customer: {e}")
            return False
        
        # Test 5: Create test online order
        print("\n5. Creating test online order...")
        try:
            # Get first menu item for testing
            test_item = menu_items[0]
            
            # Create order with TAKEAWAY type
            test_order = Order(
                customer_id=test_customer.id,
                user_id=1,  # Assuming user with ID 1 exists
                order_type=OrderType.TAKEAWAY,
                status=OrderStatus.PENDING,
                notes="Test online order"
            )
            
            # Add order item
            from app.models.order import OrderItem
            order_item = OrderItem(
                item_id=test_item.id,
                quantity=2,
                unit_price=test_item.price,
                notes="Test order item"
            )
            test_order.items.append(order_item)
            
            # Calculate totals
            test_order.calculate_totals()
            
            db.session.add(test_order)
            db.session.commit()
            
            print(f"SUCCESS: Created test order: {test_order.order_number}")
            print(f"  - Order Type: {test_order.order_type.value}")
            print(f"  - Status: {test_order.status.value}")
            print(f"  - Total: ${test_order.total}")
            # Count items using a query
            from app.models.order import OrderItem
            items_count = OrderItem.query.filter_by(order_id=test_order.id).count()
            print(f"  - Items: {items_count}")
            
        except Exception as e:
            print(f"ERROR: Error creating order: {e}")
            db.session.rollback()
            return False
        
        # Test 6: Test order to_dict method
        print("\n6. Testing order serialization...")
        try:
            order_dict = test_order.to_dict(include_items=True)
            print(f"SUCCESS: Order serialized successfully")
            print(f"  - Order Number: {order_dict['order_number']}")
            print(f"  - Order Type: {order_dict['order_type']}")
            print(f"  - Status: {order_dict['status']}")
            print(f"  - Customer: {order_dict['customer_name']}")
        except Exception as e:
            print(f"ERROR: Error serializing order: {e}")
            return False
        
        # Test 7: Test delivery order
        print("\n7. Testing delivery order...")
        try:
            delivery_order = Order(
                customer_id=test_customer.id,
                user_id=1,
                order_type=OrderType.DELIVERY,
                status=OrderStatus.PENDING,
                notes="Test delivery order"
            )
            
            delivery_order.calculate_totals()
            db.session.add(delivery_order)
            db.session.commit()
            
            print(f"SUCCESS: Created delivery order: {delivery_order.order_number}")
            print(f"  - Order Type: {delivery_order.order_type.value}")
            
        except Exception as e:
            print(f"ERROR: Error creating delivery order: {e}")
            return False
        
        print("\nSUCCESS: All online ordering tests passed!")
        return True

if __name__ == "__main__":
    success = test_online_ordering()
    if success:
        print("\nSUCCESS: Online Ordering Interface is working correctly!")
    else:
        print("\nERROR: Online Ordering Interface has issues that need to be fixed.")
        sys.exit(1)