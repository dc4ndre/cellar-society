"""
================================================================================
CELLAR SOCIETY - E-Commerce Customer Portal
================================================================================
Customer Side - Flask Application
CPE 6 2nd Year Final Project

Data Structures Used:
1. Queue - O(1) order processing and checkout
2. Stack - O(1) browsing history navigation
3. Hash Table - O(1) cart management
================================================================================
"""

# ============================================
# IMPORTS
# ============================================

from flask import Flask, render_template, request, redirect, url_for, flash, session
from functools import wraps
from datetime import datetime
from collections import deque
import sqlite3
import hashlib
import os


# ============================================
# APP CONFIGURATION
# ============================================

app = Flask(__name__)
app.secret_key = 'cellar_society_customer_secret_2024'
app.config['SESSION_COOKIE_NAME'] = 'customer_session'


# ============================================
# DATABASE CONNECTION
# ============================================

def get_db_connection():
    """Connect to the same database as admin side"""
    conn = sqlite3.connect('cellar_society.db')
    conn.row_factory = sqlite3.Row
    return conn


# ============================================
# DATA STRUCTURES - QUEUE (Order Processing)
# ============================================

class OrderQueue:
    """
    Queue implementation for order processing
    FIFO - First In, First Out
    Time Complexity: O(1) for enqueue and dequeue
    """
    
    def __init__(self):
        self.queue = deque()
    
    def enqueue(self, order_data):
        """Add order to queue - O(1)"""
        self.queue.append(order_data)
    
    def dequeue(self):
        """Remove and return first order - O(1)"""
        if not self.is_empty():
            return self.queue.popleft()
        return None
    
    def is_empty(self):
        """Check if queue is empty"""
        return len(self.queue) == 0
    
    def size(self):
        """Get queue size"""
        return len(self.queue)


# ============================================
# DATA STRUCTURES - STACK (Browsing History)
# ============================================

class BrowsingHistory:
    """
    Stack implementation for browsing history
    LIFO - Last In, First Out
    Time Complexity: O(1) for push and pop
    """
    
    def __init__(self):
        self.stack = []
    
    def push(self, page_url):
        """Add page to history - O(1)"""
        # Avoid duplicate consecutive entries
        if not self.stack or self.stack[-1] != page_url:
            self.stack.append(page_url)
    
    def pop(self):
        """Remove and return last visited page - O(1)"""
        if not self.is_empty():
            return self.stack.pop()
        return None
    
    def peek(self):
        """View last page without removing"""
        if not self.is_empty():
            return self.stack[-1]
        return None
    
    def is_empty(self):
        """Check if history is empty"""
        return len(self.stack) == 0
    
    def clear(self):
        """Clear all history"""
        self.stack.clear()


# ============================================
# DATA STRUCTURES - HASH TABLE (Shopping Cart)
# ============================================

class ShoppingCart:
    """
    Hash Table for shopping cart management
    Key: product_id, Value: {product_info, quantity}
    Time Complexity: O(1) for add, remove, update
    """
    
    def __init__(self):
        self.cart = {}
    
    def add_item(self, product_id, product_data, quantity=1):
        """Add item to cart - O(1)"""
        if product_id in self.cart:
            self.cart[product_id]['quantity'] += quantity
        else:
            self.cart[product_id] = {
                'product': product_data,
                'quantity': quantity
            }
    
    def remove_item(self, product_id):
        """Remove item from cart - O(1)"""
        if product_id in self.cart:
            del self.cart[product_id]
    
    def update_quantity(self, product_id, quantity):
        """Update item quantity - O(1)"""
        if product_id in self.cart:
            if quantity <= 0:
                self.remove_item(product_id)
            else:
                self.cart[product_id]['quantity'] = quantity
    
    def get_items(self):
        """Get all cart items"""
        return self.cart
    
    def get_total(self):
        """Calculate cart total"""
        total = 0
        for item_data in self.cart.values():
            total += item_data['product']['price'] * item_data['quantity']
        return total
    
    def get_item_count(self):
        """Get total number of items"""
        return sum(item['quantity'] for item in self.cart.values())
    
    def clear(self):
        """Empty the cart"""
        self.cart.clear()


# Global instances
order_queue = OrderQueue()
browsing_history = BrowsingHistory()


# ============================================
# SESSION CART MANAGEMENT
# ============================================

def get_cart():
    """Get shopping cart from session"""
    if 'cart' not in session:
        session['cart'] = {}
    return session['cart']


def save_cart(cart_dict):
    """Save shopping cart to session"""
    session['cart'] = cart_dict
    session.modified = True


def get_cart_total():
    """Calculate total price of items in cart"""
    cart = get_cart()
    total = 0
    for item in cart.values():
        total += item['price'] * item['quantity']
    return total


def get_cart_count():
    """Get total number of items in cart"""
    cart = get_cart()
    return sum(item['quantity'] for item in cart.values())


# ============================================
# DECORATORS
# ============================================

def login_required(f):
    """Decorator to protect customer routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'customer_id' not in session:
            flash('Please login first to access this page', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


# ============================================
# ROUTES - HOME & SHOP
# ============================================

@app.route('/')
def index():
    """Landing page - redirect to shop"""
    return redirect(url_for('shop'))


@app.route('/shop')
def shop():
    """Main shop page - browse all wines"""
    # Get filters from query params
    wine_type = request.args.get('type', '')
    search = request.args.get('search', '')
    sort = request.args.get('sort', 'newest')
    
    conn = get_db_connection()
    
    # Build query
    query = 'SELECT * FROM products WHERE stock > 0'
    params = []
    
    if wine_type:
        query += ' AND type = ?'
        params.append(wine_type)
    
    if search:
        query += ' AND (name LIKE ? OR region LIKE ?)'
        params.extend([f'%{search}%', f'%{search}%'])
    
    # Sorting
    if sort == 'price_low':
        query += ' ORDER BY price ASC'
    elif sort == 'price_high':
        query += ' ORDER BY price DESC'
    elif sort == 'name':
        query += ' ORDER BY name ASC'
    else:  # newest
        query += ' ORDER BY created_at DESC'
    
    products = conn.execute(query, params).fetchall()
    conn.close()
    
    return render_template('customer/shop.html', 
                         products=products,
                         wine_type=wine_type,
                         search=search,
                         sort=sort,
                         cart_count=get_cart_count())


@app.route('/product/<int:product_id>')
def product_detail(product_id):
    """Individual product detail page"""
    conn = get_db_connection()
    product = conn.execute(
        'SELECT * FROM products WHERE id = ?', 
        (product_id,)
    ).fetchone()
    conn.close()
    
    if not product:
        flash('Product not found', 'error')
        return redirect(url_for('shop'))
    
    # Add to browsing history (Stack - LIFO)
    if 'browsing_history' not in session:
        session['browsing_history'] = []
    
    history = list(session['browsing_history'])
    
    if product_id in history:
        history.remove(product_id)
    
    history.append(product_id)
    
    if len(history) > 50:
        history = history[-50:]
    
    session['browsing_history'] = history
    session.modified = True
    
    return render_template('customer/product_detail.html', 
                         product=product,
                         cart_count=get_cart_count())


# ============================================
# ROUTES - AUTHENTICATION
# ============================================

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Customer registration"""
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        phone = request.form.get('phone', '')
        address = request.form.get('address', '')
        
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return redirect(url_for('register'))
        
        hashed_pw = hashlib.sha256(password.encode()).hexdigest()
        
        conn = get_db_connection()
        
        existing = conn.execute(
            'SELECT * FROM customers WHERE email = ?', 
            (email,)
        ).fetchone()
        
        if existing:
            flash('Email already registered', 'error')
            conn.close()
            return redirect(url_for('register'))
        
        conn.execute('''
            INSERT INTO customers (name, email, password, phone, address)
            VALUES (?, ?, ?, ?, ?)
        ''', (name, email, hashed_pw, phone, address))
        
        conn.commit()
        conn.close()
        
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    
    return render_template('customer/register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Customer login"""
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        hashed_pw = hashlib.sha256(password.encode()).hexdigest()
        
        conn = get_db_connection()
        customer = conn.execute(
            'SELECT * FROM customers WHERE email = ? AND password = ?',
            (email, hashed_pw)
        ).fetchone()
        conn.close()
        
        if customer:
            session['customer_id'] = customer['id']
            session['customer_name'] = customer['name']
            session['customer_email'] = customer['email']
            
            flash(f'Welcome back, {customer["name"]}!', 'success')
            return redirect(url_for('shop'))
        else:
            flash('Invalid email or password', 'error')
    
    return render_template('customer/login.html')


@app.route('/logout')
def logout():
    """Customer logout"""
    browsing_history.clear()
    session.clear()
    flash('Logged out successfully', 'success')
    return redirect(url_for('login'))


# ============================================
# ROUTES - SHOPPING CART
# ============================================

@app.route('/cart/add/<int:product_id>', methods=['POST'])
def add_to_cart(product_id):
    """Add product to cart"""
    quantity = int(request.form.get('quantity', 1))
    
    conn = get_db_connection()
    product = conn.execute(
        'SELECT * FROM products WHERE id = ?', 
        (product_id,)
    ).fetchone()
    conn.close()
    
    if not product:
        flash('Product not found', 'error')
        return redirect(url_for('shop'))
    
    if product['stock'] < quantity:
        flash('Insufficient stock', 'error')
        return redirect(url_for('product_detail', product_id=product_id))
    
    cart = get_cart()
    
    if str(product_id) in cart:
        cart[str(product_id)]['quantity'] += quantity
    else:
        cart[str(product_id)] = {
            'id': product['id'],
            'name': product['name'],
            'price': product['price'],
            'image_url': product['image_url'],
            'quantity': quantity,
            'stock': product['stock']
        }
    
    save_cart(cart)
    flash(f'Added {product["name"]} to cart', 'success')
    
    return redirect(url_for('view_cart'))


@app.route('/cart')
def view_cart():
    """View shopping cart"""
    cart = get_cart()
    total = get_cart_total()
    
    return render_template('customer/cart.html', 
                         cart=cart, 
                         total=total,
                         cart_count=get_cart_count())


@app.route('/cart/update/<int:product_id>', methods=['POST'])
def update_cart(product_id):
    """Update cart item quantity"""
    quantity = int(request.form.get('quantity', 0))
    
    cart = get_cart()
    
    if str(product_id) in cart:
        if quantity <= 0:
            del cart[str(product_id)]
            flash('Item removed from cart', 'success')
        else:
            cart[str(product_id)]['quantity'] = quantity
            flash('Cart updated', 'success')
    
    save_cart(cart)
    return redirect(url_for('view_cart'))


@app.route('/cart/remove/<int:product_id>')
def remove_from_cart(product_id):
    """Remove item from cart"""
    cart = get_cart()
    
    if str(product_id) in cart:
        del cart[str(product_id)]
        flash('Item removed from cart', 'success')
    
    save_cart(cart)
    return redirect(url_for('view_cart'))


# ============================================
# ROUTES - CHECKOUT & ORDERS
# ============================================

@app.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    """Checkout process"""
    cart = get_cart()
    
    if not cart:
        flash('Your cart is empty', 'error')
        return redirect(url_for('shop'))
    
    if request.method == 'POST':
        conn = get_db_connection()
        
        for item in cart.values():
            order_data = {
                'customer_id': session['customer_id'],
                'product_id': item['id'],
                'quantity': item['quantity'],
                'total_price': item['price'] * item['quantity'],
                'status': 'Pending'
            }
            
            order_queue.enqueue(order_data)
            
            conn.execute('''
                INSERT INTO orders 
                (customer_id, product_id, quantity, total_price, status)
                VALUES (?, ?, ?, ?, ?)
            ''', (order_data['customer_id'], order_data['product_id'],
                  order_data['quantity'], order_data['total_price'],
                  order_data['status']))
            
            conn.execute('''
                UPDATE products 
                SET stock = stock - ? 
                WHERE id = ?
            ''', (item['quantity'], item['id']))
        
        conn.commit()
        conn.close()
        
        session['cart'] = {}
        session.modified = True
        
        flash('Order placed successfully!', 'success')
        return redirect(url_for('my_orders'))
    
    total = get_cart_total()
    
    return render_template('customer/checkout.html', 
                         cart=cart, 
                         total=total,
                         cart_count=get_cart_count())


@app.route('/my-orders')
@login_required
def my_orders():
    """View customer's order history with Shopee-style tabs"""
    # Get status filter from query params
    status_filter = request.args.get('status', '')
    
    conn = get_db_connection()
    
    # Get order counts for each status (for badges)
    pending_count = conn.execute('''
        SELECT COUNT(*) as count FROM orders 
        WHERE customer_id = ? AND status = 'Pending'
    ''', (session['customer_id'],)).fetchone()['count']
    
    processing_count = conn.execute('''
        SELECT COUNT(*) as count FROM orders 
        WHERE customer_id = ? AND status = 'Processing'
    ''', (session['customer_id'],)).fetchone()['count']
    
    delivered_count = conn.execute('''
        SELECT COUNT(*) as count FROM orders 
        WHERE customer_id = ? AND status = 'Delivered'
    ''', (session['customer_id'],)).fetchone()['count']
    
    # Build query based on status filter
    query = '''
        SELECT o.*, p.name as product_name, p.type as product_type, 
               p.image_url as product_image
        FROM orders o
        JOIN products p ON o.product_id = p.id
        WHERE o.customer_id = ?
    '''
    params = [session['customer_id']]
    
    if status_filter:
        query += ' AND o.status = ?'
        params.append(status_filter)
    
    query += ' ORDER BY o.order_date DESC'
    
    orders = conn.execute(query, params).fetchall()
    conn.close()
    
    return render_template('customer/my_orders.html', 
                         orders=orders,
                         status_filter=status_filter,
                         pending_count=pending_count,
                         processing_count=processing_count,
                         delivered_count=delivered_count,
                         cart_count=get_cart_count())


@app.route('/order/cancel/<int:order_id>', methods=['POST'])
@login_required
def cancel_order(order_id):
    """Cancel an order (only if status is Pending)"""
    conn = get_db_connection()
    
    order = conn.execute('''
        SELECT o.*, p.name as product_name 
        FROM orders o
        JOIN products p ON o.product_id = p.id
        WHERE o.id = ? AND o.customer_id = ?
    ''', (order_id, session['customer_id'])).fetchone()
    
    if not order:
        flash('Order not found', 'error')
        conn.close()
        return redirect(url_for('my_orders'))
    
    if order['status'] != 'Pending':
        flash('Only pending orders can be cancelled', 'error')
        conn.close()
        return redirect(url_for('my_orders'))
    
    conn.execute('''
        UPDATE orders 
        SET status = 'Cancelled'
        WHERE id = ?
    ''', (order_id,))
    
    conn.execute('''
        UPDATE products 
        SET stock = stock + ?
        WHERE id = ?
    ''', (order['quantity'], order['product_id']))
    
    conn.commit()
    conn.close()
    
    flash(f'Order #{order_id} for {order["product_name"]} has been cancelled', 'success')
    return redirect(url_for('my_orders'))


@app.route('/order/received/<int:order_id>', methods=['POST'])
@login_required
def mark_received(order_id):
    """Mark order as received (only if status is Delivered)"""
    conn = get_db_connection()
    
    order = conn.execute('''
        SELECT o.*, p.name as product_name 
        FROM orders o
        JOIN products p ON o.product_id = p.id
        WHERE o.id = ? AND o.customer_id = ?
    ''', (order_id, session['customer_id'])).fetchone()
    
    if not order:
        flash('Order not found', 'error')
        conn.close()
        return redirect(url_for('my_orders'))
    
    if order['status'] != 'Delivered':
        flash('Only delivered orders can be marked as received', 'error')
        conn.close()
        return redirect(url_for('my_orders'))
    
    conn.execute('''
        UPDATE orders 
        SET status = 'Received'
        WHERE id = ?
    ''', (order_id,))
    
    conn.commit()
    conn.close()
    
    flash(f'Order #{order_id} marked as received. Thank you!', 'success')
    return redirect(url_for('my_orders'))


# ============================================
# ROUTES - PROFILE
# ============================================

@app.route('/profile')
@login_required
def profile():
    """Customer profile page with browsing history"""
    conn = get_db_connection()
    
    customer = conn.execute(
        'SELECT * FROM customers WHERE id = ?', 
        (session['customer_id'],)
    ).fetchone()
    
    if 'browsing_history' not in session:
        session['browsing_history'] = []
    
    history_products = []
    if session['browsing_history']:
        recent_views = list(session['browsing_history'])[-10:]
        recent_views.reverse()
        
        for product_id in recent_views:
            product = conn.execute(
                'SELECT * FROM products WHERE id = ?',
                (product_id,)
            ).fetchone()
            if product:
                history_products.append(product)
    
    conn.close()
    
    return render_template('customer/profile.html', 
                         customer=customer,
                         cart_count=get_cart_count(),
                         browsing_history=history_products)


@app.route('/history/clear', methods=['POST'])
@login_required
def clear_history():
    """Clear browsing history"""
    session['browsing_history'] = []
    session.modified = True
    flash('Browsing history cleared', 'success')
    return redirect(url_for('profile'))


@app.route('/profile/edit', methods=['POST'])
@login_required
def edit_profile():
    """Update customer profile"""
    name = request.form['name']
    phone = request.form.get('phone', '')
    address = request.form.get('address', '')
    
    conn = get_db_connection()
    conn.execute('''
        UPDATE customers 
        SET name = ?, phone = ?, address = ?
        WHERE id = ?
    ''', (name, phone, address, session['customer_id']))
    
    conn.commit()
    conn.close()
    
    session['customer_name'] = name
    flash('Profile updated successfully', 'success')
    
    return redirect(url_for('profile'))


@app.route('/profile/change-password', methods=['POST'])
@login_required
def change_password():
    """Change customer password"""
    current_password = request.form['current_password']
    new_password = request.form['new_password']
    confirm_password = request.form['confirm_password']
    
    if new_password != confirm_password:
        flash('New passwords do not match', 'error')
        return redirect(url_for('profile'))
    
    if len(new_password) < 6:
        flash('Password must be at least 6 characters', 'error')
        return redirect(url_for('profile'))
    
    current_hashed = hashlib.sha256(current_password.encode()).hexdigest()
    new_hashed = hashlib.sha256(new_password.encode()).hexdigest()
    
    conn = get_db_connection()
    
    customer = conn.execute(
        'SELECT * FROM customers WHERE id = ? AND password = ?',
        (session['customer_id'], current_hashed)
    ).fetchone()
    
    if not customer:
        flash('Current password is incorrect', 'error')
        conn.close()
        return redirect(url_for('profile'))
    
    conn.execute('''
        UPDATE customers 
        SET password = ?
        WHERE id = ?
    ''', (new_hashed, session['customer_id']))
    
    conn.commit()
    conn.close()
    
    flash('Password changed successfully!', 'success')
    return redirect(url_for('profile'))


@app.route('/profile/delete-account', methods=['POST'])
@login_required
def delete_account():
    """Delete customer account"""
    password = request.form['password']
    confirm_text = request.form['confirm_text']
    
    if confirm_text != 'DELETE':
        flash('Please type DELETE to confirm account deletion', 'error')
        return redirect(url_for('profile'))
    
    hashed_pw = hashlib.sha256(password.encode()).hexdigest()
    
    conn = get_db_connection()
    
    customer = conn.execute(
        'SELECT * FROM customers WHERE id = ? AND password = ?',
        (session['customer_id'], hashed_pw)
    ).fetchone()
    
    if not customer:
        flash('Incorrect password', 'error')
        conn.close()
        return redirect(url_for('profile'))
    
    pending_orders = conn.execute(
        'SELECT COUNT(*) as count FROM orders WHERE customer_id = ? AND status IN ("Pending", "Processing")',
        (session['customer_id'],)
    ).fetchone()['count']
    
    if pending_orders > 0:
        flash('Cannot delete account with pending or processing orders', 'error')
        conn.close()
        return redirect(url_for('profile'))
    
    conn.execute('DELETE FROM orders WHERE customer_id = ?', (session['customer_id'],))
    conn.execute('DELETE FROM customers WHERE id = ?', (session['customer_id'],))
    
    conn.commit()
    conn.close()
    
    session.clear()
    
    flash('Your account has been permanently deleted', 'success')
    return redirect(url_for('shop'))


# ============================================
# APPLICATION STARTUP
# ============================================

if __name__ == '__main__':
    print("=" * 60)
    print("🍷 Cellar Society Customer Portal Starting...")
    print("=" * 60)
    print("🔗 Access at: http://localhost:5001")
    print("=" * 60)
    
    app.run(debug=True, port=5001)