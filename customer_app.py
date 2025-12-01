from flask import Flask, render_template, request, redirect, url_for, flash, session
from functools import wraps
from datetime import datetime, timedelta
from collections import deque
import sqlite3
import hashlib
import os

app = Flask(__name__)
app.secret_key = 'cellar_society_customer_secret_2024'
app.config['SESSION_COOKIE_NAME'] = 'customer_session'

def get_db_connection():
    conn = sqlite3.connect('cellar_society.db')
    conn.row_factory = sqlite3.Row
    return conn

def migrate_database():
    conn = get_db_connection()
    try:
        conn.execute('ALTER TABLE orders ADD COLUMN estimated_delivery_date TEXT')
        print("✅ Added estimated_delivery_date column")
    except sqlite3.OperationalError:
        pass
    
    try:
        conn.execute('ALTER TABLE orders ADD COLUMN shipped_date TEXT')
        print("✅ Added shipped_date column")
    except sqlite3.OperationalError:
        pass
    
    conn.commit()
    conn.close()

class OrderQueue:
    def __init__(self):
        self.queue = deque()
    
    def enqueue(self, order_data):
        self.queue.append(order_data)
    
    def dequeue(self):
        if not self.is_empty():
            return self.queue.popleft()
        return None
    
    def is_empty(self):
        return len(self.queue) == 0
    
    def size(self):
        return len(self.queue)

class BrowsingHistory:
    def __init__(self):
        self.stack = []
    
    def push(self, page_url):
        if not self.stack or self.stack[-1] != page_url:
            self.stack.append(page_url)
    
    def pop(self):
        if not self.is_empty():
            return self.stack.pop()
        return None
    
    def peek(self):
        if not self.is_empty():
            return self.stack[-1]
        return None
    
    def is_empty(self):
        return len(self.stack) == 0
    
    def clear(self):
        self.stack.clear()

class SearchHistory:
    def __init__(self, max_size=10):
        self.stack = []
        self.max_size = max_size
    
    def push(self, search_query):
        search_query = search_query.strip().lower()
        if search_query in self.stack:
            self.stack.remove(search_query)
        self.stack.append(search_query)
        if len(self.stack) > self.max_size:
            self.stack.pop(0)
    
    def get_recent(self, limit=5):
        return list(reversed(self.stack[-limit:]))
    
    def clear(self):
        self.stack.clear()
    
    def get_all(self):
        return list(reversed(self.stack))

class ShoppingCart:
    def __init__(self):
        self.cart = {}
    
    def add_item(self, product_id, product_data, quantity=1):
        if product_id in self.cart:
            self.cart[product_id]['quantity'] += quantity
        else:
            self.cart[product_id] = {'product': product_data, 'quantity': quantity}
    
    def remove_item(self, product_id):
        if product_id in self.cart:
            del self.cart[product_id]
    
    def update_quantity(self, product_id, quantity):
        if product_id in self.cart:
            if quantity <= 0:
                self.remove_item(product_id)
            else:
                self.cart[product_id]['quantity'] = quantity
    
    def get_items(self):
        return self.cart
    
    def get_total(self):
        total = 0
        for item_data in self.cart.values():
            total += item_data['product']['price'] * item_data['quantity']
        return total
    
    def get_item_count(self):
        return sum(item['quantity'] for item in self.cart.values())
    
    def clear(self):
        self.cart.clear()

order_queue = OrderQueue()
browsing_history = BrowsingHistory()
search_history = SearchHistory()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'customer_id' not in session:
            flash('Please login first to access this page', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def get_cart():
    if 'cart' not in session:
        session['cart'] = {}
    return session['cart']

def save_cart(cart_dict):
    session['cart'] = cart_dict
    session.modified = True

def get_cart_total():
    cart = get_cart()
    total = 0
    for item in cart.values():
        total += item['price'] * item['quantity']
    return total

def get_cart_count():
    cart = get_cart()
    return sum(item['quantity'] for item in cart.values())

def get_notification_counts():
    if 'customer_id' not in session:
        return {'orders_to_pay': 0, 'orders_to_receive': 0, 'unread_messages': 0, 'total': 0}
    
    conn = get_db_connection()
    orders_to_pay = conn.execute('SELECT COUNT(*) as count FROM orders WHERE customer_id = ? AND status = "Pending"', (session['customer_id'],)).fetchone()['count']
    orders_to_receive = conn.execute('SELECT COUNT(*) as count FROM orders WHERE customer_id = ? AND status = "Delivered"', (session['customer_id'],)).fetchone()['count']
    unread_messages = conn.execute('SELECT COUNT(*) as count FROM messages WHERE customer_id = ? AND sender_type = "admin" AND is_read = 0', (session['customer_id'],)).fetchone()['count']
    conn.close()
    
    total = orders_to_pay + orders_to_receive + unread_messages
    return {'orders_to_pay': orders_to_pay, 'orders_to_receive': orders_to_receive, 'unread_messages': unread_messages, 'total': total}

@app.context_processor
def inject_notifications():
    return {'notifications': get_notification_counts(), 'cart_count': get_cart_count()}

@app.route('/')
def index():
    return render_template('customer/landing.html', cart_count=get_cart_count())

@app.route('/shop')
def shop():
    wine_type = request.args.get('type', '')
    search = request.args.get('search', '')
    sort = request.args.get('sort', 'newest')
    
    if search and 'customer_id' in session:
        if 'search_history' not in session:
            session['search_history'] = []
        history = session['search_history']
        search_lower = search.strip().lower()
        if search_lower in history:
            history.remove(search_lower)
        history.append(search_lower)
        if len(history) > 10:
            history = history[-10:]
        session['search_history'] = history
        session.modified = True
    
    conn = get_db_connection()
    query = 'SELECT * FROM products WHERE stock > 0'
    params = []
    
    if wine_type:
        query += ' AND type = ?'
        params.append(wine_type)
    
    if search:
        query += ' AND (name LIKE ? OR region LIKE ? OR type LIKE ?)'
        params.extend([f'%{search}%', f'%{search}%', f'%{search}%'])
    
    if sort == 'price_low':
        query += ' ORDER BY price ASC'
    elif sort == 'price_high':
        query += ' ORDER BY price DESC'
    elif sort == 'name':
        query += ' ORDER BY name ASC'
    else:
        query += ' ORDER BY created_at DESC'
    
    products = conn.execute(query, params).fetchall()
    recommendations = conn.execute('SELECT * FROM products WHERE stock > 0 ORDER BY RANDOM() LIMIT 6').fetchall()
    conn.close()
    
    recent_searches = []
    if 'customer_id' in session and 'search_history' in session:
        recent_searches = list(reversed(session['search_history'][-5:]))
    
    return render_template('customer/shop.html', products=products, wine_type=wine_type, search=search, sort=sort, cart_count=get_cart_count(), recent_searches=recent_searches, recommendations=recommendations)

@app.route('/product/<int:product_id>')
def product_detail(product_id):
    conn = get_db_connection()
    product = conn.execute('SELECT * FROM products WHERE id = ?', (product_id,)).fetchone()
    conn.close()
    
    if not product:
        flash('Product not found', 'error')
        return redirect(url_for('shop'))
    
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
    
    return render_template('customer/product_detail.html', product=product, cart_count=get_cart_count())

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        phone = request.form.get('phone', '').strip()
        address = request.form.get('address', '').strip()
        
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return redirect(url_for('register'))
        
        if not phone:
            flash('Phone number is required for order delivery', 'error')
            return redirect(url_for('register'))
        
        if not address:
            flash('Delivery address is required for order delivery', 'error')
            return redirect(url_for('register'))
        
        if len(phone) < 10:
            flash('Please enter a valid phone number (at least 10 digits)', 'error')
            return redirect(url_for('register'))
        
        if len(address) < 20:
            flash('Please enter a complete delivery address (minimum 20 characters)', 'error')
            return redirect(url_for('register'))
        
        hashed_pw = hashlib.sha256(password.encode()).hexdigest()
        conn = get_db_connection()
        existing = conn.execute('SELECT * FROM customers WHERE email = ?', (email,)).fetchone()
        
        if existing:
            flash('Email already registered', 'error')
            conn.close()
            return redirect(url_for('register'))
        
        conn.execute('INSERT INTO customers (name, email, password, phone, address) VALUES (?, ?, ?, ?, ?)', (name, email, hashed_pw, phone, address))
        conn.commit()
        conn.close()
        
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    
    return render_template('customer/register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        hashed_pw = hashlib.sha256(password.encode()).hexdigest()
        
        conn = get_db_connection()
        customer = conn.execute('SELECT * FROM customers WHERE email = ? AND password = ?', (email, hashed_pw)).fetchone()
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
    browsing_history.clear()
    session.clear()
    flash('Logged out successfully', 'success')
    return redirect(url_for('login'))

@app.route('/cart/add/<int:product_id>', methods=['POST'])
def add_to_cart(product_id):
    quantity = int(request.form.get('quantity', 1))
    conn = get_db_connection()
    product = conn.execute('SELECT * FROM products WHERE id = ?', (product_id,)).fetchone()
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
        cart[str(product_id)] = {'id': product['id'], 'name': product['name'], 'price': product['price'], 'image_url': product['image_url'], 'quantity': quantity, 'stock': product['stock']}
    
    save_cart(cart)
    flash(f'Added {product["name"]} to cart', 'success')
    return redirect(url_for('view_cart'))

@app.route('/cart')
def view_cart():
    cart = get_cart()
    total = get_cart_total()
    return render_template('customer/cart.html', cart=cart, total=total, cart_count=get_cart_count())

@app.route('/cart/update/<int:product_id>', methods=['POST'])
def update_cart(product_id):
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
    cart = get_cart()
    if str(product_id) in cart:
        del cart[str(product_id)]
        flash('Item removed from cart', 'success')
    save_cart(cart)
    return redirect(url_for('view_cart'))

@app.route('/buy-now/<int:product_id>', methods=['POST'])
def buy_now(product_id):
    quantity = int(request.form.get('quantity', 1))
    conn = get_db_connection()
    product = conn.execute('SELECT * FROM products WHERE id = ?', (product_id,)).fetchone()
    conn.close()
    
    if not product:
        flash('Product not found', 'error')
        return redirect(url_for('shop'))
    
    if product['stock'] < quantity:
        flash('Insufficient stock', 'error')
        return redirect(url_for('product_detail', product_id=product_id))
    
    if 'customer_id' not in session:
        flash('Please login first to purchase', 'error')
        return redirect(url_for('login'))
    
    buy_now_cart = {str(product_id): {'id': product['id'], 'name': product['name'], 'price': product['price'], 'image_url': product['image_url'], 'quantity': quantity, 'stock': product['stock']}}
    session['buy_now_cart'] = buy_now_cart
    session['is_buy_now'] = True
    session.modified = True
    return redirect(url_for('buy_now_checkout'))

@app.route('/buy-now-checkout', methods=['GET', 'POST'])
@login_required
def buy_now_checkout():
    buy_now_cart = session.get('buy_now_cart', {})
    
    if not buy_now_cart:
        flash('No product selected for quick purchase', 'error')
        return redirect(url_for('shop'))
    
    conn = get_db_connection()
    customer = conn.execute('SELECT * FROM customers WHERE id = ?', (session['customer_id'],)).fetchone()
    
    if not customer['phone'] or not customer['address']:
        flash('Please update your phone number and delivery address in your profile before checking out', 'error')
        conn.close()
        return redirect(url_for('profile'))
    
    if len(customer['phone'].strip()) < 11 or len(customer['address'].strip()) < 11:
        flash('Please provide a valid phone number and complete delivery address in your profile', 'error')
        conn.close()
        return redirect(url_for('profile'))
    
    if request.method == 'POST':
        for item in buy_now_cart.values():
            order_data = {'customer_id': session['customer_id'], 'product_id': item['id'], 'quantity': item['quantity'], 'total_price': item['price'] * item['quantity'], 'status': 'Pending'}
            order_queue.enqueue(order_data)
            conn.execute('INSERT INTO orders (customer_id, product_id, quantity, total_price, status) VALUES (?, ?, ?, ?, ?)', (order_data['customer_id'], order_data['product_id'], order_data['quantity'], order_data['total_price'], order_data['status']))
            conn.execute('UPDATE products SET stock = stock - ? WHERE id = ?', (item['quantity'], item['id']))
        
        conn.commit()
        conn.close()
        session['buy_now_cart'] = {}
        session['is_buy_now'] = False
        session.modified = True
        flash('Order placed successfully!', 'success')
        return redirect(url_for('my_orders'))
    
    total = sum(item['price'] * item['quantity'] for item in buy_now_cart.values())
    conn.close()
    return render_template('customer/buy_now_checkout.html', cart=buy_now_cart, total=total, cart_count=get_cart_count())

@app.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    cart = get_cart()
    
    if not cart:
        flash('Your cart is empty', 'error')
        return redirect(url_for('shop'))
    
    conn = get_db_connection()
    customer = conn.execute('SELECT * FROM customers WHERE id = ?', (session['customer_id'],)).fetchone()
    
    if not customer['phone'] or not customer['address']:
        flash('Please update your phone number and delivery address in your profile before checking out', 'error')
        conn.close()
        return redirect(url_for('profile'))
    
    if len(customer['phone'].strip()) < 10 or len(customer['address'].strip()) < 20:
        flash('Please provide a valid phone number and complete delivery address in your profile', 'error')
        conn.close()
        return redirect(url_for('profile'))
    
    if request.method == 'POST':
        for item in cart.values():
            order_data = {'customer_id': session['customer_id'], 'product_id': item['id'], 'quantity': item['quantity'], 'total_price': item['price'] * item['quantity'], 'status': 'Pending'}
            order_queue.enqueue(order_data)
            conn.execute('INSERT INTO orders (customer_id, product_id, quantity, total_price, status) VALUES (?, ?, ?, ?, ?)', (order_data['customer_id'], order_data['product_id'], order_data['quantity'], order_data['total_price'], order_data['status']))
            conn.execute('UPDATE products SET stock = stock - ? WHERE id = ?', (item['quantity'], item['id']))
        
        conn.commit()
        conn.close()
        session['cart'] = {}
        session.modified = True
        flash('Order placed successfully!', 'success')
        return redirect(url_for('my_orders'))
    
    total = get_cart_total()
    conn.close()
    return render_template('customer/checkout.html', cart=cart, total=total, cart_count=get_cart_count())

@app.route('/my-orders')
@login_required
def my_orders():
    status_filter = request.args.get('status', '')
    conn = get_db_connection()
    
    pending_count = conn.execute('SELECT COUNT(*) as count FROM orders WHERE customer_id = ? AND status = "Pending"', (session['customer_id'],)).fetchone()['count']
    processing_count = conn.execute('SELECT COUNT(*) as count FROM orders WHERE customer_id = ? AND status = "Processing"', (session['customer_id'],)).fetchone()['count']
    delivered_count = conn.execute('SELECT COUNT(*) as count FROM orders WHERE customer_id = ? AND status = "Delivered"', (session['customer_id'],)).fetchone()['count']
    
    query = 'SELECT o.*, p.name as product_name, p.type as product_type, p.image_url as product_image, o.estimated_delivery_date, o.shipped_date FROM orders o JOIN products p ON o.product_id = p.id WHERE o.customer_id = ?'
    params = [session['customer_id']]
    
    if status_filter:
        query += ' AND o.status = ?'
        params.append(status_filter)
    
    query += ' ORDER BY o.order_date DESC'
    orders = conn.execute(query, params).fetchall()
    conn.close()
    
    return render_template('customer/my_orders.html', orders=orders, status_filter=status_filter, pending_count=pending_count, processing_count=processing_count, delivered_count=delivered_count, cart_count=get_cart_count())

@app.route('/order/cancel/<int:order_id>', methods=['POST'])
@login_required
def cancel_order(order_id):
    conn = get_db_connection()
    order = conn.execute('SELECT o.*, p.name as product_name FROM orders o JOIN products p ON o.product_id = p.id WHERE o.id = ? AND o.customer_id = ?', (order_id, session['customer_id'])).fetchone()
    
    if not order:
        flash('Order not found', 'error')
        conn.close()
        return redirect(url_for('my_orders'))
    
    if order['status'] != 'Pending':
        flash('Only pending orders can be cancelled', 'error')
        conn.close()
        return redirect(url_for('my_orders'))
    
    conn.execute('UPDATE orders SET status = "Cancelled" WHERE id = ?', (order_id,))
    conn.execute('UPDATE products SET stock = stock + ? WHERE id = ?', (order['quantity'], order['product_id']))
    conn.commit()
    conn.close()
    
    flash(f'Order #{order_id} for {order["product_name"]} has been cancelled', 'success')
    return redirect(url_for('my_orders'))

@app.route('/order/received/<int:order_id>', methods=['POST'])
@login_required
def mark_received(order_id):
    conn = get_db_connection()
    order = conn.execute('SELECT o.*, p.name as product_name FROM orders o JOIN products p ON o.product_id = p.id WHERE o.id = ? AND o.customer_id = ?', (order_id, session['customer_id'])).fetchone()
    
    if not order:
        flash('Order not found', 'error')
        conn.close()
        return redirect(url_for('my_orders'))
    
    if order['status'] != 'Delivered':
        flash('Only delivered orders can be marked as received', 'error')
        conn.close()
        return redirect(url_for('my_orders'))
    
    conn.execute('UPDATE orders SET status = "Received" WHERE id = ?', (order_id,))
    conn.commit()
    conn.close()
    
    flash(f'Order #{order_id} marked as received. Thank you!', 'success')
    return redirect(url_for('my_orders'))

@app.route('/profile')
@login_required
def profile():
    conn = get_db_connection()
    customer = conn.execute('SELECT * FROM customers WHERE id = ?', (session['customer_id'],)).fetchone()
    
    if 'browsing_history' not in session:
        session['browsing_history'] = []
    
    history_products = []
    if session['browsing_history']:
        recent_views = list(session['browsing_history'])[-10:]
        recent_views.reverse()
        for product_id in recent_views:
            product = conn.execute('SELECT * FROM products WHERE id = ?', (product_id,)).fetchone()
            if product:
                history_products.append(product)
    
    conn.close()
    return render_template('customer/profile.html', customer=customer, cart_count=get_cart_count(), browsing_history=history_products)

@app.route('/history/clear', methods=['POST'])
@login_required
def clear_history():
    session['browsing_history'] = []
    session.modified = True
    flash('Browsing history cleared', 'success')
    return redirect(url_for('profile'))

@app.route('/clear-search-history', methods=['POST'])
@login_required
def clear_search_history():
    session['search_history'] = []
    session.modified = True
    flash('Search history cleared', 'success')
    return redirect(url_for('shop'))

@app.route('/profile/edit', methods=['POST'])
@login_required
def edit_profile():
    name = request.form['name']
    phone = request.form.get('phone', '').strip()
    address = request.form.get('address', '').strip()
    
    if not phone:
        flash('Phone number is required', 'error')
        return redirect(url_for('profile'))
    
    if not address:
        flash('Delivery address is required', 'error')
        return redirect(url_for('profile'))
    
    if len(phone) < 11:
        flash('Please enter a valid phone number (at least 11 digits)', 'error')
        return redirect(url_for('profile'))
    
    if len(address) < 10:
        flash('Please enter a complete delivery address (minimum 10 characters)', 'error')
        return redirect(url_for('profile'))
    
    conn = get_db_connection()
    conn.execute('UPDATE customers SET name = ?, phone = ?, address = ? WHERE id = ?', (name, phone, address, session['customer_id']))
    conn.commit()
    conn.close()
    
    session['customer_name'] = name
    flash('Profile updated successfully', 'success')
    return redirect(url_for('profile'))

@app.route('/profile/change-password', methods=['POST'])
@login_required
def change_password():
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
    customer = conn.execute('SELECT * FROM customers WHERE id = ? AND password = ?', (session['customer_id'], current_hashed)).fetchone()
    
    if not customer:
        flash('Current password is incorrect', 'error')
        conn.close()
        return redirect(url_for('profile'))
    
    conn.execute('UPDATE customers SET password = ? WHERE id = ?', (new_hashed, session['customer_id']))
    conn.commit()
    conn.close()
    
    flash('Password changed successfully!', 'success')
    return redirect(url_for('profile'))

@app.route('/profile/delete-account', methods=['POST'])
@login_required
def delete_account():
    password = request.form['password']
    confirm_text = request.form['confirm_text']
    
    if confirm_text != 'DELETE':
        flash('Please type DELETE to confirm account deletion', 'error')
        return redirect(url_for('profile'))
    
    hashed_pw = hashlib.sha256(password.encode()).hexdigest()
    conn = get_db_connection()
    customer = conn.execute('SELECT * FROM customers WHERE id = ? AND password = ?', (session['customer_id'], hashed_pw)).fetchone()
    
    if not customer:
        flash('Incorrect password', 'error')
        conn.close()
        return redirect(url_for('profile'))
    
    pending_orders = conn.execute('SELECT COUNT(*) as count FROM orders WHERE customer_id = ? AND status IN ("Pending", "Processing")', (session['customer_id'],)).fetchone()['count']
    
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

@app.route('/messages')
@login_required
def messages():
    conn = get_db_connection()
    messages = conn.execute('SELECT * FROM messages WHERE customer_id = ? ORDER BY created_at ASC', (session['customer_id'],)).fetchall()
    conn.execute('UPDATE messages SET is_read = 1 WHERE customer_id = ? AND sender_type = "admin" AND is_read = 0', (session['customer_id'],))
    conn.commit()
    conn.close()
    return render_template('customer/messages.html', messages=messages, cart_count=get_cart_count())

@app.route('/messages/send', methods=['POST'])
@login_required
def send_message():
    message_text = request.form.get('message', '').strip()
    
    if not message_text:
        flash('Message cannot be empty', 'error')
        return redirect(url_for('messages'))
    
    if len(message_text) > 1000:
        flash('Message is too long (max 1000 characters)', 'error')
        return redirect(url_for('messages'))
    
    conn = get_db_connection()
    conn.execute('INSERT INTO messages (customer_id, sender_type, message) VALUES (?, "customer", ?)', (session['customer_id'], message_text))
    conn.commit()
    conn.close()
    
    flash('Message sent to admin successfully!', 'success')
    return redirect(url_for('messages'))

def get_unread_message_count():
    if 'customer_id' not in session:
        return 0
    conn = get_db_connection()
    count = conn.execute('SELECT COUNT(*) as count FROM messages WHERE customer_id = ? AND sender_type = "admin" AND is_read = 0''', (session['customer_id'],)).fetchone()['count']
    conn.close()
    
    return count

if __name__ == '__main__':
    migrate_database()  
    print("=" * 60)
    print("🍷 Cellar Society Customer Portal Starting...")
    print("=" * 60)
    print("🔗 Access at: http://localhost:5001")
    print("=" * 60)
    
    app.run(debug=True, port=5001)