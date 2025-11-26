# Restaurant POS System - Technical Implementation Guide

## 1. Project Setup & Dependencies

### Requirements.txt
```
Flask==2.3.3
Flask-SQLAlchemy==3.0.5
Flask-Login==0.6.3
Flask-Migrate==4.0.5
Flask-SocketIO==5.3.6
Flask-WTF==1.1.1
WTForms==3.0.1
Werkzeug==2.3.7
python-escpos==3.0
python-dotenv==1.0.0
Pillow==10.0.1
```

### Frontend Dependencies (CDN)
```html
<!-- Tailwind CSS -->
<script src="https://cdn.tailwindcss.com"></script>
<!-- HTMX -->
<script src="https://unpkg.com/htmx.org@1.9.6"></script>
<!-- Alpine.js -->
<script defer src="https://unpkg.com/alpinejs@3.x.x/dist/cdn.min.js"></script>
<!-- Font Awesome -->
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
```

## 2. Database Models Implementation

### User Management Models
```python
# app/models/user.py
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.Enum('cashier', 'kitchen', 'manager', 'admin'), nullable=False)
    pin_code = db.Column(db.String(4), nullable=True)  # For quick login
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def set_pin(self, pin):
        self.pin_code = generate_password_hash(pin)
    
    def check_pin(self, pin):
        return self.pin_code and check_password_hash(self.pin_code, pin)
```

### Menu Management Models
```python
# app/models/menu.py
from datetime import datetime

class Category(db.Model):
    __tablename__ = 'categories'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    display_order = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    items = db.relationship('MenuItem', backref='category', lazy=True, order_by='MenuItem.display_order')

class MenuItem(db.Model):
    __tablename__ = 'menu_items'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
    image_url = db.Column(db.String(255))
    is_available = db.Column(db.Boolean, default=True)
    display_order = db.Column(db.Integer, default=0)
    preparation_time = db.Column(db.Integer)  # minutes
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    variants = db.relationship('ItemVariant', backref='menu_item', lazy=True)
    add_ons = db.relationship('AddOn', secondary='item_add_ons', backref='menu_items')

class ItemVariant(db.Model):
    __tablename__ = 'item_variants'
    
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('menu_items.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)  # e.g., "Small", "Large", "Extra Spicy"
    price_modifier = db.Column(db.Numeric(10, 2), default=0.00)

class AddOn(db.Model):
    __tablename__ = 'add_ons'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Numeric(10, 2), default=0.00)
    is_active = db.Column(db.Boolean, default=True)

# Association table for many-to-many relationship
item_add_ons = db.Table('item_add_ons',
    db.Column('item_id', db.Integer, db.ForeignKey('menu_items.id'), primary_key=True),
    db.Column('addon_id', db.Integer, db.ForeignKey('add_ons.id'), primary_key=True)
)
```

### Order Management Models
```python
# app/models/order.py
from datetime import datetime
from enum import Enum

class OrderStatus(Enum):
    PENDING = 'pending'
    CONFIRMED = 'confirmed'
    PREPARING = 'preparing'
    READY = 'ready'
    SERVED = 'served'
    CANCELLED = 'cancelled'

class Order(db.Model):
    __tablename__ = 'orders'
    
    id = db.Column(db.Integer, primary_key=True)
    table_id = db.Column(db.Integer, db.ForeignKey('tables.id'), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    status = db.Column(db.Enum(OrderStatus), default=OrderStatus.PENDING)
    subtotal = db.Column(db.Numeric(10, 2), nullable=False)
    tax_rate = db.Column(db.Numeric(5, 4), default=0.0000)  # e.g., 0.0875 for 8.75%
    tax_amount = db.Column(db.Numeric(10, 2), default=0.00)
    discount_amount = db.Column(db.Numeric(10, 2), default=0.00)
    discount_type = db.Column(db.Enum('percentage', 'fixed'), nullable=True)
    total = db.Column(db.Numeric(10, 2), nullable=False)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    items = db.relationship('OrderItem', backref='order', lazy=True, cascade='all, delete-orphan')
    payments = db.relationship('Payment', backref='order', lazy=True)

class OrderItem(db.Model):
    __tablename__ = 'order_items'
    
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('menu_items.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Numeric(10, 2), nullable=False)
    variant_id = db.Column(db.Integer, db.ForeignKey('item_variants.id'), nullable=True)
    notes = db.Column(db.Text)
    
    # Relationships
    menu_item = db.relationship('MenuItem', backref='order_items')
    variant = db.relationship('ItemVariant', backref='order_items')
    add_ons = db.relationship('AddOn', secondary='order_item_add_ons', backref='order_items')

class Payment(db.Model):
    __tablename__ = 'payments'
    
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    method = db.Column(db.Enum('cash', 'card', 'upi', 'wallet'), nullable=False)
    transaction_id = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
```

## 3. Authentication System Implementation

### Login Route with HTMX
```python
# app/auth/routes.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_user, logout_user, login_required, current_user
from app.models.user import User
from app import db
from datetime import timedelta

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.headers.get('HX-Request'):
            # HTMX request - return partial
            email = request.form.get('email')
            password = request.form.get('password')
            
            user = User.query.filter_by(email=email).first()
            
            if user and user.check_password(password) and user.is_active:
                login_user(user, remember=True)
                user.last_login = datetime.utcnow()
                db.session.commit()
                
                # Redirect based on role
                if user.role == 'cashier':
                    return render_template('partials/cashier_dashboard.html')
                elif user.role == 'kitchen':
                    return render_template('partials/kitchen_display.html')
                elif user.role in ['manager', 'admin']:
                    return render_template('partials/manager_dashboard.html')
            else:
                return render_template('auth/login_form.html', error='Invalid credentials')
        
        # Regular form submission
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password) and user.is_active:
            login_user(user, remember=True)
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            return redirect(url_for(f'{user.role}.dashboard'))
        else:
            flash('Invalid credentials', 'error')
    
    return render_template('auth/login.html')

@auth_bp.route('/pin-login', methods=['POST'])
def pin_login():
    pin = request.form.get('pin')
    
    # Find user by PIN
    user = User.query.filter(User.pin_code.isnot(None)).all()
    for u in user:
        if u.check_pin(pin) and u.is_active:
            login_user(u, remember=True)
            u.last_login = datetime.utcnow()
            db.session.commit()
            
            if request.headers.get('HX-Request'):
                return render_template('partials/cashier_dashboard.html')
            return redirect(url_for('cashier.dashboard'))
    
    if request.headers.get('HX-Request'):
        return render_template('auth/pin_form.html', error='Invalid PIN')
    flash('Invalid PIN', 'error')
    return redirect(url_for('auth.login'))

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))
```

## 4. HTMX Implementation Patterns

### Cart Management with HTMX
```python
# app/orders/routes.py
from flask import Blueprint, render_template, request, jsonify, session
from flask_login import login_required, current_user
from app.models.menu import MenuItem, ItemVariant, AddOn
from app.models.order import Order, OrderItem
from app import db

orders_bp = Blueprint('orders', __name__)

@orders_bp.route('/cart/add', methods=['POST'])
@login_required
def add_to_cart():
    item_id = request.form.get('item_id')
    quantity = int(request.form.get('quantity', 1))
    variant_id = request.form.get('variant_id')
    add_on_ids = request.form.getlist('add_ons')
    notes = request.form.get('notes', '')
    
    # Get cart from session
    cart = session.get('cart', {})
    
    # Create cart item key
    cart_key = f"{item_id}_{variant_id or '0'}_{'_'.join(add_on_ids)}"
    
    if cart_key in cart:
        cart[cart_key]['quantity'] += quantity
    else:
        menu_item = MenuItem.query.get(item_id)
        variant = ItemVariant.query.get(variant_id) if variant_id else None
        
        cart[cart_key] = {
            'item_id': item_id,
            'item_name': menu_item.name,
            'quantity': quantity,
            'unit_price': float(menu_item.price),
            'variant_id': variant_id,
            'variant_name': variant.name if variant else None,
            'variant_price': float(variant.price_modifier) if variant else 0,
            'add_ons': add_on_ids,
            'notes': notes
        }
    
    session['cart'] = cart
    
    # Return updated cart partial
    return render_template('partials/cart.html', cart=cart)

@orders_bp.route('/cart/update', methods=['POST'])
@login_required
def update_cart():
    cart_key = request.form.get('cart_key')
    quantity = int(request.form.get('quantity', 0))
    
    cart = session.get('cart', {})
    
    if quantity == 0:
        del cart[cart_key]
    else:
        cart[cart_key]['quantity'] = quantity
    
    session['cart'] = cart
    
    return render_template('partials/cart.html', cart=cart)

@orders_bp.route('/cart/clear', methods=['POST'])
@login_required
def clear_cart():
    session.pop('cart', None)
    return render_template('partials/cart.html', cart={})
```

### Cart HTML Template with HTMX
```html
<!-- templates/partials/cart.html -->
<div id="cart-container" hx-trigger="cartUpdated from:body" hx-get="/cart/current" hx-swap="innerHTML">
  <div class="bg-white rounded-lg shadow-lg p-4">
    <h3 class="text-lg font-semibold mb-4">Order Cart</h3>
    
    {% if cart %}
      <div class="space-y-2 mb-4">
        {% for key, item in cart.items() %}
          <div class="flex justify-between items-center p-2 bg-gray-50 rounded">
            <div class="flex-1">
              <div class="font-medium">{{ item.item_name }}</div>
              {% if item.variant_name %}
                <div class="text-sm text-gray-600">{{ item.variant_name }}</div>
              {% endif %}
              <div class="text-sm text-gray-600">
                ${{ "%.2f"|format(item.unit_price + item.variant_price) }} x {{ item.quantity }}
              </div>
            </div>
            <div class="flex items-center space-x-2">
              <button 
                hx-post="/cart/update"
                hx-vals='{"cart_key": "{{ key }}", "quantity": {{ item.quantity - 1 }}}'
                hx-target="#cart-container"
                class="w-8 h-8 bg-red-500 text-white rounded hover:bg-red-600">
                -
              </button>
              <span class="w-8 text-center">{{ item.quantity }}</span>
              <button 
                hx-post="/cart/update"
                hx-vals='{"cart_key": "{{ key }}", "quantity": {{ item.quantity + 1 }}}'
                hx-target="#cart-container"
                class="w-8 h-8 bg-green-500 text-white rounded hover:bg-green-600">
                +
              </button>
            </div>
          </div>
        {% endfor %}
      </div>
      
      <div class="border-t pt-4">
        <div class="flex justify-between mb-2">
          <span>Subtotal:</span>
          <span>${{ "%.2f"|format(cart_subtotal) }}</span>
        </div>
        <div class="flex justify-between mb-2">
          <span>Tax (8.75%):</span>
          <span>${{ "%.2f"|format(cart_tax) }}</span>
        </div>
        <div class="flex justify-between font-bold text-lg">
          <span>Total:</span>
          <span>${{ "%.2f"|format(cart_total) }}</span>
        </div>
      </div>
      
      <div class="mt-4 space-y-2">
        <button 
          hx-post="/orders/create"
          hx-target="#main-content"
          class="w-full bg-blue-600 text-white py-2 px-4 rounded hover:bg-blue-700">
          Create Order
        </button>
        <button 
          hx-post="/cart/clear"
          hx-target="#cart-container"
          class="w-full bg-gray-300 text-gray-700 py-2 px-4 rounded hover:bg-gray-400">
          Clear Cart
        </button>
      </div>
    {% else %}
      <p class="text-gray-500 text-center py-8">Cart is empty</p>
    {% endif %}
  </div>
</div>
```

## 5. Real-time Kitchen Display System

### WebSocket Events
```python
# app/kitchen/socketio_events.py
from flask_socketio import emit, join_room, leave_room
from flask_login import current_user
from app import socketio
from app.models.order import Order, OrderStatus
from app.models.user import User
from app import db

@socketio.on('join_kitchen')
def on_join_kitchen():
    if current_user.is_authenticated and current_user.role == 'kitchen':
        join_room('kitchen')
        emit('joined_kitchen', {'status': 'success'})

@socketio.on('update_order_status')
def on_update_order_status(data):
    if current_user.is_authenticated and current_user.role == 'kitchen':
        order_id = data.get('order_id')
        new_status = data.get('status')
        
        order = Order.query.get(order_id)
        if order:
            order.status = OrderStatus(new_status)
            db.session.commit()
            
            # Broadcast to all kitchen displays
            emit('order_status_updated', {
                'order_id': order_id,
                'status': new_status,
                'updated_by': current_user.name
            }, room='kitchen')
            
            # Also notify cashier if order is ready
            if new_status == OrderStatus.READY:
                emit('order_ready', {
                    'order_id': order_id,
                    'table_number': order.table.number if order.table else 'Takeaway'
                }, room='cashier')

def broadcast_new_order(order):
    """Broadcast new order to kitchen displays"""
    socketio.emit('new_order', {
        'order_id': order.id,
        'items': [{
            'name': item.menu_item.name,
            'quantity': item.quantity,
            'notes': item.notes
        } for item in order.items],
        'table_number': order.table.number if order.table else 'Takeaway',
        'created_at': order.created_at.isoformat()
    }, room='kitchen')
```

### Kitchen Display Template
```html
<!-- templates/kitchen/display.html -->
<div x-data="kitchenDisplay()" x-init="initSocket()">
  <div class="bg-gray-100 min-h-screen p-4">
    <h1 class="text-2xl font-bold mb-6">Kitchen Display System</h1>
    
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      <template x-for="order in orders" :key="order.id">
        <div class="bg-white rounded-lg shadow-lg p-4" 
             :class="{
               'border-yellow-400': order.status === 'new',
               'border-blue-400': order.status === 'preparing',
               'border-green-400': order.status === 'ready'
             }">
          <div class="flex justify-between items-start mb-3">
            <div>
              <h3 class="font-bold text-lg">Order #<span x-text="order.id"></span></h3>
              <p class="text-sm text-gray-600">
                Table: <span x-text="order.table_number || 'Takeaway'"></span>
              </p>
              <p class="text-sm text-gray-600">
                Time: <span x-text="formatTime(order.created_at)"></span>
              </p>
            </div>
            <div class="flex space-x-2">
              <button @click="updateStatus(order.id, 'preparing')" 
                      :disabled="order.status === 'preparing' || order.status === 'ready'"
                      class="px-3 py-1 bg-blue-500 text-white rounded text-sm hover:bg-blue-600 disabled:bg-gray-300">
                Preparing
              </button>
              <button @click="updateStatus(order.id, 'ready')" 
                      :disabled="order.status === 'ready'"
                      class="px-3 py-1 bg-green-500 text-white rounded text-sm hover:bg-green-600 disabled:bg-gray-300">
                Ready
              </button>
            </div>
          </div>
          
          <div class="space-y-2">
            <template x-for="item in order.items" :key="item.name">
              <div class="flex justify-between items-center">
                <div>
                  <span x-text="item.quantity"></span>x 
                  <span x-text="item.name"></span>
                  <span x-show="item.notes" class="text-sm text-gray-600" x-text="'(' + item.notes + ')'"></span>
                </div>
              </div>
            </template>
          </div>
          
          <div x-show="order.status === 'preparing'" class="mt-3">
            <div class="bg-blue-100 p-2 rounded">
              <div class="flex justify-between text-sm">
                <span>Timer:</span>
                <span x-text="getElapsedTime(order.created_at)"></span>
              </div>
            </div>
          </div>
        </div>
      </template>
    </div>
  </div>
</div>

<script>
function kitchenDisplay() {
  return {
    orders: [],
    socket: null,
    
    initSocket() {
      // Connect to WebSocket
      this.socket = io();
      
      this.socket.on('new_order', (data) => {
        this.orders.unshift({
          ...data,
          status: 'new'
        });
      });
      
      this.socket.on('order_status_updated', (data) => {
        const order = this.orders.find(o => o.id === data.order_id);
        if (order) {
          order.status = data.status;
        }
      });
      
      // Join kitchen room
      this.socket.emit('join_kitchen');
      
      // Load initial orders
      this.loadOrders();
    },
    
    async loadOrders() {
      try {
        const response = await fetch('/kitchen/orders');
        this.orders = await response.json();
      } catch (error) {
        console.error('Error loading orders:', error);
      }
    },
    
    updateStatus(orderId, status) {
      this.socket.emit('update_order_status', {
        order_id: orderId,
        status: status
      });
    },
    
    formatTime(timestamp) {
      return new Date(timestamp).toLocaleTimeString();
    },
    
    getElapsedTime(startTime) {
      const start = new Date(startTime);
      const now = new Date();
      const diff = Math.floor((now - start) / 1000 / 60); // minutes
      return `${diff} min`;
    }
  }
}
</script>
```

## 6. Alpine.js Reactive Components

### Menu Item Selection
```html
<!-- templates/partials/menu_item_modal.html -->
<div x-data="menuItemModal()" x-show="show" 
     x-transition:enter="transition ease-out duration-300"
     x-transition:enter-start="opacity-0"
     x-transition:enter-end="opacity-100"
     x-transition:leave="transition ease-in duration-200"
     x-transition:leave-start="opacity-100"
     x-transition:leave-end="opacity-0"
     class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
     style="display: none;">
  
  <div @click.away="close()" class="bg-white rounded-lg p-6 max-w-md w-full mx-4">
    <h3 class="text-xl font-bold mb-4" x-text="item.name"></h3>
    
    <div x-show="item.description" class="text-gray-600 mb-4" x-text="item.description"></div>
    
    <!-- Variants Selection -->
    <div x-show="variants.length > 0" class="mb-4">
      <h4 class="font-semibold mb-2">Choose Option:</h4>
      <div class="space-y-2">
        <template x-for="variant in variants" :key="variant.id">
          <label class="flex items-center space-x-2 cursor-pointer">
            <input type="radio" :value="variant.id" x-model="selectedVariant" 
                   class="form-radio text-blue-600">
            <span x-text="variant.name"></span>
            <span class="text-gray-600" x-text="'+$' + variant.price_modifier.toFixed(2)"></span>
          </label>
        </template>
      </div>
    </div>
    
    <!-- Add-ons Selection -->
    <div x-show="addOns.length > 0" class="mb-4">
      <h4 class="font-semibold mb-2">Add-ons:</h4>
      <div class="space-y-2">
        <template x-for="addOn in addOns" :key="addOn.id">
          <label class="flex items-center space-x-2 cursor-pointer">
            <input type="checkbox" :value="addOn.id" x-model="selectedAddOns" 
                   class="form-checkbox text-blue-600">
            <span x-text="addOn.name"></span>
            <span class="text-gray-600" x-text="'+$' + addOn.price.toFixed(2)"></span>
          </label>
        </template>
      </div>
    </div>
    
    <!-- Quantity Selection -->
    <div class="mb-4">
      <h4 class="font-semibold mb-2">Quantity:</h4>
      <div class="flex items-center space-x-2">
        <button @click="quantity > 1 ? quantity-- : null" 
                class="w-8 h-8 bg-gray-200 rounded hover:bg-gray-300">-</button>
        <span class="w-12 text-center" x-text="quantity"></span>
        <button @click="quantity++" 
                class="w-8 h-8 bg-gray-200 rounded hover:bg-gray-300">+</button>
      </div>
    </div>
    
    <!-- Special Instructions -->
    <div class="mb-4">
      <h4 class="font-semibold mb-2">Special Instructions:</h4>
      <textarea x-model="notes" rows="3" 
                class="w-full border rounded px-3 py-2"
                placeholder="Any special requests..."></textarea>
    </div>
    
    <!-- Price Display -->
    <div class="border-t pt-4 mb-4">
      <div class="flex justify-between items-center">
        <span class="font-semibold">Total:</span>
        <span class="text-xl font-bold" x-text="'$' + calculateTotal().toFixed(2)"></span>
      </div>
    </div>
    
    <!-- Action Buttons -->
    <div class="flex space-x-2">
      <button @click="addToCart()" 
              class="flex-1 bg-blue-600 text-white py-2 px-4 rounded hover:bg-blue-700">
        Add to Cart
      </button>
      <button @click="close()" 
              class="flex-1 bg-gray-300 text-gray-700 py-2 px-4 rounded hover:bg-gray-400">
        Cancel
      </button>
    </div>
  </div>
</div>

<script>
function menuItemModal() {
  return {
    show: false,
    item: {},
    variants: [],
    addOns: [],
    selectedVariant: null,
    selectedAddOns: [],
    quantity: 1,
    notes: '',
    
    open(itemId) {
      fetch(`/menu/item/${itemId}`)
        .then(response => response.json())
        .then(data => {
          this.item = data.item;
          this.variants = data.variants;
          this.addOns = data.add_ons;
          this.selectedVariant = this.variants.length > 0 ? this.variants[0].id : null;
          this.selectedAddOns = [];
          this.quantity = 1;
          this.notes = '';
          this.show = true;
        });
    },
    
    close() {
      this.show = false;
    },
    
    calculateTotal() {
      let total = this.item.price;
      
      if (this.selectedVariant) {
        const variant = this.variants.find(v => v.id == this.selectedVariant);
        if (variant) {
          total += variant.price_modifier;
        }
      }
      
      this.selectedAddOns.forEach(addOnId => {
        const addOn = this.addOns.find(a => a.id == addOnId);
        if (addOn) {
          total += addOn.price;
        }
      });
      
      return total * this.quantity;
    },
    
    addToCart() {
      const formData = new FormData();
      formData.append('item_id', this.item.id);
      formData.append('quantity', this.quantity);
      formData.append('variant_id', this.selectedVariant || '');
      formData.append('notes', this.notes);
      
      this.selectedAddOns.forEach(addOnId => {
        formData.append('add_ons', addOnId);
      });
      
      fetch('/cart/add', {
        method: 'POST',
        body: formData,
        headers: {
          'HX-Request': 'true'
        }
      })
      .then(response => response.text())
      .then(html => {
        // Update cart
        document.getElementById('cart-container').innerHTML = html;
        // Close modal
        this.close();
        // Show success message
        this.showNotification('Item added to cart!');
      });
    },
    
    showNotification(message) {
      // Simple notification implementation
      const notification = document.createElement('div');
      notification.className = 'fixed top-4 right-4 bg-green-500 text-white px-4 py-2 rounded shadow-lg z-50';
      notification.textContent = message;
      document.body.appendChild(notification);
      
      setTimeout(() => {
        notification.remove();
      }, 3000);
    }
  }
}
</script>
```

## 7. Tailwind CSS Configuration

### Custom Tailwind Config
```javascript
// tailwind.config.js
module.exports = {
  content: [
    './app/templates/**/*.html',
    './app/static/js/**/*.js'
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#eff6ff',
          500: '#3b82f6',
          600: '#2563eb',
          700: '#1d4ed8',
        },
        success: {
          50: '#f0fdf4',
          500: '#22c55e',
          600: '#16a34a',
        },
        danger: {
          50: '#fef2f2',
          500: '#ef4444',
          600: '#dc2626',
        }
      },
      animation: {
        'fade-in': 'fadeIn 0.3s ease-in-out',
        'slide-up': 'slideUp 0.3s ease-out',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { transform: 'translateY(10px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        }
      }
    },
  },
  plugins: [
    require('@tailwindcss/forms'),
    require('@tailwindcss/typography'),
  ],
}
```

This implementation guide provides the core technical patterns and code structures needed to build the Restaurant POS system with Flask, HTMX, Alpine.js, and Tailwind CSS. The next step would be to implement these components in the actual codebase following the todo list we created.