"""
================================================================================
CELLAR SOCIETY - E-Commerce Management System
================================================================================
Admin Side - Flask Application
CPE 6 2nd Year Final Project

Data Structures Used:
1. Hash Table (Dictionary) - O(1) product lookup
2. Binary Search Tree - O(log n) searching/filtering
3. Queue - O(1) order processing (for customer side integration)
4. Stack - O(1) browsing history (for customer side integration)
================================================================================
"""

# ============================================
# IMPORTS
# ============================================

from flask import Flask, render_template, request, redirect, url_for, flash, session
from functools import wraps
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
from PIL import Image
import sqlite3
import hashlib
import os


# ============================================
# APP CONFIGURATION
# ============================================

app = Flask(__name__)
app.secret_key = 'cellar_society_admin_secret_2024'  # Different secret key from customer
app.config['SESSION_COOKIE_NAME'] = 'admin_session'  # Different cookie name


# File upload configuration
UPLOAD_FOLDER = 'static/uploads/wines'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE


# ============================================
# HELPER FUNCTIONS FOR FILE UPLOAD
# ============================================

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def save_wine_image(file):
    """
    Save uploaded wine image to static folder
    Returns: relative path to saved image or None if failed
    """
    if file and allowed_file(file.filename):
        # Create secure filename with timestamp to avoid duplicates
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        name, ext = os.path.splitext(filename)
        unique_filename = f"{name}_{timestamp}{ext}"
        
        # Save file
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(filepath)
        
        # Return relative path for database storage
        return f"/static/uploads/wines/{unique_filename}"
    return None


# ============================================
# DATABASE SETUP
# ============================================

def init_db():
    """
    Initialize SQLite database with tables
    Creates: admins, products, customers, orders tables
    """
    conn = sqlite3.connect('cellar_society.db')
    c = conn.cursor()
    
    # Admin table - stores admin credentials
    c.execute('''CREATE TABLE IF NOT EXISTS admins (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Products table - stores wine inventory
    c.execute('''CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        type TEXT NOT NULL,
        region TEXT NOT NULL,
        vintage INTEGER NOT NULL,
        price REAL NOT NULL,
        alcohol REAL NOT NULL,
        stock INTEGER NOT NULL,
        description TEXT,
        image_url TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Customers table - for viewing only (customer side will manage)
    c.execute('''CREATE TABLE IF NOT EXISTS customers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        phone TEXT,
        address TEXT,
        joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Orders table - for viewing (customer side will create)
    c.execute('''CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        quantity INTEGER NOT NULL,
        total_price REAL NOT NULL,
        status TEXT DEFAULT 'Pending',
        order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (customer_id) REFERENCES customers(id),
        FOREIGN KEY (product_id) REFERENCES products(id)
    )''')
    
    # Create default admin if not exists
    c.execute("SELECT * FROM admins WHERE username='admin'")
    if not c.fetchone():
        # Password: admin456 (hashed with SHA-256)
        hashed_pw = hashlib.sha256('admin456'.encode()).hexdigest()
        c.execute("INSERT INTO admins (username, password) VALUES (?, ?)", 
                 ('admin', hashed_pw))
    
    conn.commit()
    conn.close()
    print("✅ Database initialized successfully!")


def get_db_connection():
    """
    Create and return database connection
    Uses row_factory for dictionary-like access
    """
    conn = sqlite3.connect('cellar_society.db')
    conn.row_factory = sqlite3.Row
    return conn

def migrate_database():
    """Add missing columns to orders table"""
    conn = sqlite3.connect('cellar_society.db')
    try:
        conn.execute('''
            ALTER TABLE orders 
            ADD COLUMN estimated_delivery_date TEXT
        ''')
        print("✅ Added estimated_delivery_date column")
    except sqlite3.OperationalError:
        pass
    
    try:
        conn.execute('''
            ALTER TABLE orders 
            ADD COLUMN shipped_date TEXT
        ''')
        print("✅ Added shipped_date column")
    except sqlite3.OperationalError:
        pass
    
    conn.commit()
    conn.close()

# ============================================
# DATA STRUCTURES - HASH TABLE
# ============================================

class ProductHashTable:
    """
    Hash Table implementation for O(1) product lookup by ID
    
    Purpose: Quick product retrieval in admin panel
    Time Complexity: O(1) for insert, get, delete
    Space Complexity: O(n) where n is number of products
    
    Implementation: Uses Python dictionary (built-in hash table)
    Key: product_id (integer)
    Value: product_data (dictionary with all product info)
    """
    
    def __init__(self):
        """Initialize empty hash table"""
        self.table = {}
    
    def insert(self, product_id, product_data):
        """
        Insert product into hash table
        Time Complexity: O(1) average case
        """
        self.table[product_id] = product_data
    
    def get(self, product_id):
        """
        Get product by ID
        Time Complexity: O(1) average case
        Returns: product_data or None if not found
        """
        return self.table.get(product_id, None)
    
    def delete(self, product_id):
        """
        Delete product from hash table
        Time Complexity: O(1) average case
        Returns: True if deleted, False if not found
        """
        if product_id in self.table:
            del self.table[product_id]
            return True
        return False
    
    def get_all(self):
        """
        Get all products as list
        Time Complexity: O(n)
        """
        return list(self.table.values())


# Initialize global hash table instance
product_cache = ProductHashTable()


def load_products_to_cache():
    """
    Load all products from database into hash table
    Called after any product modification for cache consistency
    """
    conn = sqlite3.connect('cellar_society.db')
    c = conn.cursor()
    c.execute("SELECT * FROM products")
    products = c.fetchall()
    conn.close()
    
    # Clear and rebuild cache
    product_cache.table.clear()
    
    for p in products:
        product_data = {
            'id': p[0],
            'name': p[1],
            'type': p[2],
            'region': p[3],
            'vintage': p[4],
            'price': p[5],
            'alcohol': p[6],
            'stock': p[7],
            'description': p[8],
            'image_url': p[9]
        }
        product_cache.insert(p[0], product_data)


# ============================================
# DATA STRUCTURES - BINARY SEARCH TREE
# ============================================

class Node:
    """
    Node class for Binary Search Tree
    Each node contains product data and pointers to left/right children
    """
    
    def __init__(self, product):
        self.product = product  # Product dictionary
        self.left = None        # Left child (smaller price)
        self.right = None       # Right child (larger price)


class ProductBST:
    """
    Binary Search Tree implementation for O(log n) searching by price
    
    Purpose: Efficient product filtering and price-based searching
    Time Complexity: 
        - Insert: O(log n) average, O(n) worst case
        - Search: O(log n) average, O(n) worst case
    Space Complexity: O(n)
    
    Organization: Left subtree < parent < right subtree (by price)
    """
    
    def __init__(self):
        """Initialize empty BST"""
        self.root = None
    
    def insert(self, product):
        """
        Insert product into BST organized by price
        Time Complexity: O(log n) average case
        """
        if not self.root:
            self.root = Node(product)
        else:
            self._insert_recursive(self.root, product)
    
    def _insert_recursive(self, node, product):
        """Helper method for recursive insertion"""
        if product['price'] < node.product['price']:
            # Go left (smaller price)
            if node.left is None:
                node.left = Node(product)
            else:
                self._insert_recursive(node.left, product)
        else:
            # Go right (larger or equal price)
            if node.right is None:
                node.right = Node(product)
            else:
                self._insert_recursive(node.right, product)
    
    def search_by_price_range(self, min_price, max_price):
        """
        Search for products within price range
        Time Complexity: O(log n + k) where k is number of results
        Returns: List of products in price range
        """
        results = []
        self._range_search(self.root, min_price, max_price, results)
        return results
    
    def _range_search(self, node, min_price, max_price, results):
        """Helper method for recursive range search"""
        if node is None:
            return
        
        # Check if current node is in range
        if min_price <= node.product['price'] <= max_price:
            results.append(node.product)
        
        # Search left subtree if min_price is smaller than current
        if min_price < node.product['price']:
            self._range_search(node.left, min_price, max_price, results)
        
        # Search right subtree if max_price is larger than current
        if max_price > node.product['price']:
            self._range_search(node.right, min_price, max_price, results)


# ============================================
# HELPER FUNCTIONS & DECORATORS
# ============================================

def login_required(f):
    """
    Decorator to protect admin routes
    Redirects to login if no active session
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_id' not in session:
            flash('Please login first', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def get_admin_notification_counts():
    """Get all notification counts for admin"""
    conn = get_db_connection()
    
    # Pending orders (need to be processed)
    pending_orders = conn.execute('''
        SELECT COUNT(*) as count FROM orders 
        WHERE status = 'Pending'
    ''').fetchone()['count']
    
    # Processing orders (need to be shipped)
    processing_orders = conn.execute('''
        SELECT COUNT(*) as count FROM orders 
        WHERE status = 'Processing'
    ''').fetchone()['count']
    
    # Unread messages from customers
    unread_messages = conn.execute('''
        SELECT COUNT(*) as count FROM messages 
        WHERE sender_type = 'customer' AND is_read = 0
    ''').fetchone()['count']
    
    conn.close()
    
    total = pending_orders + processing_orders + unread_messages
    
    return {
        'pending_orders': pending_orders,
        'processing_orders': processing_orders,
        'unread_messages': unread_messages,
        'total': total
    }

# ============================================
# ROUTES - AUTHENTICATION
# ============================================

# ============================================
# CONTEXT PROCESSOR
# ============================================

@app.context_processor
def inject_admin_notifications():
    """Make notification counts available to all admin templates"""
    return {
        'notifications': get_admin_notification_counts()
    }

# ============================================
# ROUTES - AUTHENTICATION
# ============================================

@app.route('/')
def index():
    """
    Landing page - redirects to appropriate page
    If logged in: go to dashboard
    If not logged in: go to login
    """
    if 'admin_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    Admin login handler
    GET: Display login form
    POST: Validate credentials and create session
    """
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Hash password for comparison
        hashed_pw = hashlib.sha256(password.encode()).hexdigest()
        
        # Check credentials in database
        conn = get_db_connection()
        admin = conn.execute(
            'SELECT * FROM admins WHERE username = ? AND password = ?',
            (username, hashed_pw)
        ).fetchone()
        conn.close()
        
        if admin:
            # Create session
            session['admin_id'] = admin['id']
            session['admin_username'] = admin['username']
            flash(f'Welcome back, {username}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials', 'error')
    
    return render_template('admin/login.html')


@app.route('/logout')
def logout():
    """
    Admin logout handler
    Clears session and redirects to login
    """
    session.clear()
    flash('Logged out successfully', 'success')
    return redirect(url_for('login'))


# ============================================
# ROUTES - DASHBOARD
# ============================================

@app.route('/dashboard')
@login_required
def dashboard():
    """
    Admin dashboard with statistics and recent orders
    Displays: Total products, customers, orders, pending orders
    Shows: 5 most recent orders
    """
    conn = get_db_connection()
    
    # Get statistics
    total_products = conn.execute(
        'SELECT COUNT(*) as count FROM products'
    ).fetchone()['count']
    
    total_customers = conn.execute(
        'SELECT COUNT(*) as count FROM customers'
    ).fetchone()['count']
    
    total_orders = conn.execute(
        'SELECT COUNT(*) as count FROM orders'
    ).fetchone()['count']
    
    pending_orders = conn.execute(
        'SELECT COUNT(*) as count FROM orders WHERE status = "Pending"'
    ).fetchone()['count']
    
    processing_orders = conn.execute(
        'SELECT COUNT(*) as count FROM orders WHERE status = "Processing"'
    ).fetchone()['count']
    
    unread_messages = conn.execute('''
        SELECT COUNT(*) as count FROM messages 
        WHERE sender_type = 'customer' AND is_read = 0
    ''').fetchone()['count']

    # Get recent orders with joins
    recent_orders = conn.execute('''
        SELECT o.id, c.name as customer_name, p.name as product_name, 
               o.quantity, o.total_price, o.status, o.order_date
        FROM orders o
        JOIN customers c ON o.customer_id = c.id
        JOIN products p ON o.product_id = p.id
        ORDER BY o.order_date DESC
        LIMIT 5
    ''').fetchall()
    
    conn.close()
    
    # Prepare statistics dictionary
    stats = {
        'total_products': total_products,
        'total_customers': total_customers,
        'total_orders': total_orders,
        'pending_orders': pending_orders,
        'processing_orders': processing_orders,
        'unread_messages': unread_messages
    }
    
    return render_template('admin/dashboard.html', 
                         stats=stats, 
                         recent_orders=recent_orders)

# ============================================
# ROUTES - PRODUCT MANAGEMENT (CRUD)
# ============================================

@app.route('/products')
@login_required
def products():
    """
    View all products (wine inventory)
    Note: Filtering happens client-side with JavaScript for better UX
    Loads all products and updates hash table cache
    """
    conn = get_db_connection()
    
    # Load ALL products (no server-side filtering)
    products = conn.execute(
        'SELECT * FROM products ORDER BY created_at DESC'
    ).fetchall()
    
    conn.close()
    
    # Load into hash table for quick access
    load_products_to_cache()
    
    return render_template('admin/products.html', products=products)


@app.route('/products/add', methods=['GET', 'POST'])
@login_required
def add_product():
    """
    Add new wine product
    GET: Display add product form
    POST: Insert product into database and hash table
    """
    if request.method == 'POST':
        # Get form data
        name = request.form['name']
        wine_type = request.form['type']
        region = request.form['region']
        vintage = int(request.form['vintage'])
        price = float(request.form['price'])
        alcohol = float(request.form['alcohol'])
        stock = int(request.form['stock'])
        description = request.form.get('description', '')
        
        # Handle image upload
        image_url = ''
        if 'wine_image' in request.files:
            file = request.files['wine_image']
            if file and file.filename:
                saved_path = save_wine_image(file)
                if saved_path:
                    image_url = saved_path
                else:
                    flash('Invalid image file format', 'error')
                    return redirect(url_for('add_product'))
        
        # Insert into database
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('''
            INSERT INTO products 
            (name, type, region, vintage, price, alcohol, stock, description, image_url)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (name, wine_type, region, vintage, price, alcohol, stock, 
              description, image_url))
        
        conn.commit()
        product_id = c.lastrowid
        conn.close()
        
        # Add to hash table cache
        product_data = {
            'id': product_id,
            'name': name,
            'type': wine_type,
            'region': region,
            'vintage': vintage,
            'price': price,
            'alcohol': alcohol,
            'stock': stock,
            'description': description,
            'image_url': image_url
        }
        product_cache.insert(product_id, product_data)
        
        flash(f'Wine "{name}" added successfully!', 'success')
        return redirect(url_for('products'))
    
    return render_template('admin/add_product.html')


@app.route('/products/edit/<int:product_id>', methods=['GET', 'POST'])
@login_required
def edit_product(product_id):
    """
    Edit existing wine product
    GET: Display edit form with current product data
    POST: Update product in database and hash table
    """
    conn = get_db_connection()
    
    if request.method == 'POST':
        # Get form data
        name = request.form['name']
        wine_type = request.form['type']
        region = request.form['region']
        vintage = int(request.form['vintage'])
        price = float(request.form['price'])
        alcohol = float(request.form['alcohol'])
        stock = int(request.form['stock'])
        description = request.form.get('description', '')
        
        # Get current product to preserve old image if no new one uploaded
        current_product = conn.execute(
            'SELECT image_url FROM products WHERE id = ?', 
            (product_id,)
        ).fetchone()
        
        image_url = current_product['image_url'] if current_product else ''
        
        # Handle image upload (only if new file is provided)
        if 'wine_image' in request.files:
            file = request.files['wine_image']
            if file and file.filename:
                saved_path = save_wine_image(file)
                if saved_path:
                    # Delete old image file if it exists
                    if image_url and os.path.exists('.' + image_url):
                        try:
                            os.remove('.' + image_url)
                        except:
                            pass
                    image_url = saved_path
        
        # Update database
        conn.execute('''
            UPDATE products 
            SET name=?, type=?, region=?, vintage=?, price=?, 
                alcohol=?, stock=?, description=?, image_url=?
            WHERE id=?
        ''', (name, wine_type, region, vintage, price, alcohol, stock, 
              description, image_url, product_id))
        
        conn.commit()
        conn.close()
        
        # Update hash table cache
        load_products_to_cache()
        
        flash(f'Wine "{name}" updated successfully!', 'success')
        return redirect(url_for('products'))
    
    # Get product for editing
    product = conn.execute(
        'SELECT * FROM products WHERE id = ?', 
        (product_id,)
    ).fetchone()
    
    conn.close()
    
    if not product:
        flash('Product not found', 'error')
        return redirect(url_for('products'))
    
    return render_template('admin/edit_product.html', product=product)


@app.route('/products/delete/<int:product_id>', methods=['POST'])
@login_required
def delete_product(product_id):
    """
    Delete wine product
    Removes from both database and hash table
    """
    conn = get_db_connection()
    
    # Get product details including image
    product = conn.execute(
        'SELECT name, image_url FROM products WHERE id = ?', 
        (product_id,)
    ).fetchone()
    
    if product:
        # Delete image file if it exists
        if product['image_url'] and os.path.exists('.' + product['image_url']):
            try:
                os.remove('.' + product['image_url'])
            except:
                pass
        
        # Delete from database
        conn.execute('DELETE FROM products WHERE id = ?', (product_id,))
        conn.commit()
        
        # Delete from hash table
        product_cache.delete(product_id)
        
        flash(f'Wine "{product["name"]}" deleted successfully!', 'success')
    else:
        flash('Product not found', 'error')
    
    conn.close()
    return redirect(url_for('products'))


# ============================================
# ROUTES - CUSTOMER MANAGEMENT (View Only)
# ============================================

@app.route('/customers')
@login_required
def customers():
    """
    View all customer accounts
    Admin can only VIEW customers (not create/edit)
    Customers register through customer portal
    """
    search = request.args.get('search', '')
    
    conn = get_db_connection()
    query = 'SELECT * FROM customers WHERE 1=1'
    params = []
    
    # Add search filter if provided
    if search:
        query += ' AND (name LIKE ? OR email LIKE ?)'
        params.extend([f'%{search}%', f'%{search}%'])
    
    query += ' ORDER BY joined_at DESC'
    customers = conn.execute(query, params).fetchall()
    conn.close()
    
    return render_template('admin/customers.html', 
                         customers=customers, 
                         search=search)


@app.route('/customers/<int:customer_id>')
@login_required
def customer_detail(customer_id):
    """
    View customer details and order history
    Shows: Customer info + all orders placed by this customer
    """
    conn = get_db_connection()
    
    # Get customer information
    customer = conn.execute(
        'SELECT * FROM customers WHERE id = ?', 
        (customer_id,)
    ).fetchone()
    
    if not customer:
        flash('Customer not found', 'error')
        conn.close()
        return redirect(url_for('customers'))
    
    # Get customer's order history
    orders = conn.execute('''
        SELECT o.*, p.name as product_name, p.type as product_type
        FROM orders o
        JOIN products p ON o.product_id = p.id
        WHERE o.customer_id = ?
        ORDER BY o.order_date DESC
    ''', (customer_id,)).fetchall()
    
    conn.close()
    
    return render_template('admin/customer_detail.html', 
                         customer=customer, 
                         orders=orders)


# ============================================
# ROUTES - ORDER MANAGEMENT
# ============================================

@app.route('/orders')
@login_required
def orders():
    """
    View all orders with optional status filtering
    Admin can VIEW and UPDATE order status
    Filter options: All, Pending, Processing, Delivered, Received
    """
    status_filter = request.args.get('status', '')
    
    conn = get_db_connection()
    
    # Build query with joins
    query = '''
        SELECT o.*, c.name as customer_name, c.email as customer_email,
               p.name as product_name, p.type as product_type
        FROM orders o
        JOIN customers c ON o.customer_id = c.id
        JOIN products p ON o.product_id = p.id
        WHERE 1=1
    '''
    params = []
    
    # Add status filter if provided
    if status_filter:
        query += ' AND o.status = ?'
        params.append(status_filter)
    
    query += ' ORDER BY o.order_date DESC'
    orders = conn.execute(query, params).fetchall()
    conn.close()
    
    return render_template('admin/orders.html', 
                         orders=orders, 
                         status_filter=status_filter)


@app.route('/orders/<int:order_id>')
@login_required
def order_detail(order_id):
    """
    View complete order details
    Shows: Order info, customer info, product info
    """
    conn = get_db_connection()
    
    # Get order with all related data
    order = conn.execute('''
        SELECT o.*, 
               c.name as customer_name, c.email as customer_email,
               c.phone as customer_phone, c.address as customer_address,
               p.name as product_name, p.type as product_type, 
               p.region as product_region, p.vintage as product_vintage
        FROM orders o
        JOIN customers c ON o.customer_id = c.id
        JOIN products p ON o.product_id = p.id
        WHERE o.id = ?
    ''', (order_id,)).fetchone()
    
    conn.close()
    
    if not order:
        flash('Order not found', 'error')
        return redirect(url_for('orders'))
    
    return render_template('admin/order_detail.html', order=order)


@app.route('/orders/update-status/<int:order_id>', methods=['POST'])
@login_required
def update_order_status(order_id):
    """
    Update order status
    Admin can change: Pending → Processing → Delivered
    """
    new_status = request.form.get('status')
    
    # Valid statuses
    valid_statuses = ['Pending', 'Processing', 'Delivered', 'Received', 'Cancelled']
    
    if new_status not in valid_statuses:
        flash('Invalid status', 'error')
        return redirect(url_for('orders'))
    
    conn = get_db_connection()
    
    # Get order details
    order = conn.execute(
        'SELECT * FROM orders WHERE id = ?',
        (order_id,)
    ).fetchone()
    
    if not order:
        flash('Order not found', 'error')
        conn.close()
        return redirect(url_for('orders'))
    
    # Calculate estimated delivery date if status is changing to Processing
    estimated_delivery = None
    shipped_date = None
    
    if new_status == 'Processing':
        # Set shipped date to today
        shipped_date = datetime.now().strftime('%Y-%m-%d')
        # Set estimated delivery to 3-5 days from now (using 4 days as middle ground)
        estimated_delivery = (datetime.now() + timedelta(days=4)).strftime('%B %d, %Y')
    
    # Update status and dates
    if estimated_delivery:
        conn.execute('''
            UPDATE orders 
            SET status = ?, estimated_delivery_date = ?, shipped_date = ?
            WHERE id = ?
        ''', (new_status, estimated_delivery, shipped_date, order_id))
    else:
        conn.execute('''
            UPDATE orders 
            SET status = ?
            WHERE id = ?
        ''', (new_status, order_id))
    
    conn.commit()
    conn.close()
    
    flash(f'Order #{order_id} status updated to {new_status}', 'success')
    return redirect(url_for('orders'))
# ============================================
# ROUTES - MESSAGING SYSTEM
# ============================================

@app.route('/messages')
@login_required
def messages():
    """View all customer conversations"""
    conn = get_db_connection()
    
    # Get list of customers who have sent messages with unread count
    customers_with_messages = conn.execute('''
        SELECT 
            c.id,
            c.name,
            c.email,
            COUNT(CASE WHEN m.is_read = 0 AND m.sender_type = 'customer' THEN 1 END) as unread_count,
            MAX(m.created_at) as last_message_time
        FROM customers c
        INNER JOIN messages m ON c.id = m.customer_id
        GROUP BY c.id, c.name, c.email
        ORDER BY last_message_time DESC
    ''').fetchall()
    
    conn.close()
    
    return render_template('admin/messages.html', 
                         customers=customers_with_messages)


@app.route('/messages/<int:customer_id>')
@login_required
def message_thread(customer_id):
    """View conversation with specific customer"""
    conn = get_db_connection()
    
    # Get customer info
    customer = conn.execute(
        'SELECT * FROM customers WHERE id = ?',
        (customer_id,)
    ).fetchone()
    
    if not customer:
        flash('Customer not found', 'error')
        conn.close()
        return redirect(url_for('messages'))
    
    # Get all messages in this conversation
    messages = conn.execute('''
        SELECT * FROM messages 
        WHERE customer_id = ?
        ORDER BY created_at ASC
    ''', (customer_id,)).fetchall()
    
    # Mark admin's unread messages as read (messages from customer)
    conn.execute('''
        UPDATE messages 
        SET is_read = 1
        WHERE customer_id = ? AND sender_type = 'customer' AND is_read = 0
    ''', (customer_id,))
    
    conn.commit()
    conn.close()
    
    return render_template('admin/message_thread.html',
                         customer=customer,
                         messages=messages)


@app.route('/messages/<int:customer_id>/send', methods=['POST'])
@login_required
def send_message_to_customer(customer_id):
    """Send message to customer"""
    message_text = request.form.get('message', '').strip()
    
    if not message_text:
        flash('Message cannot be empty', 'error')
        return redirect(url_for('message_thread', customer_id=customer_id))
    
    if len(message_text) > 1000:
        flash('Message is too long (max 1000 characters)', 'error')
        return redirect(url_for('message_thread', customer_id=customer_id))
    
    conn = get_db_connection()
    
    # Verify customer exists
    customer = conn.execute(
        'SELECT * FROM customers WHERE id = ?',
        (customer_id,)
    ).fetchone()
    
    if not customer:
        flash('Customer not found', 'error')
        conn.close()
        return redirect(url_for('messages'))
    
    conn.execute('''
        INSERT INTO messages (customer_id, sender_type, message)
        VALUES (?, 'admin', ?)
    ''', (customer_id, message_text))
    
    conn.commit()
    conn.close()
    
    flash('Message sent successfully!', 'success')
    return redirect(url_for('message_thread', customer_id=customer_id))


def get_total_unread_messages():
    """Get total count of unread messages from customers"""
    conn = get_db_connection()
    count = conn.execute('''
        SELECT COUNT(*) as count FROM messages 
        WHERE sender_type = 'customer' AND is_read = 0
    ''').fetchone()['count']
    conn.close()
    return count

# ============================================
# APPLICATION STARTUP
# ============================================

if __name__ == '__main__':
    # Initialize database and create tables
    init_db()
    migrate_database()  # ADD THIS LINE
    
    # Load products into hash table cache
    load_products_to_cache()
    
    # Print startup messages
    print("=" * 60)
    print("🍷 Cellar Society Admin Panel Starting...")
    print("=" * 60)
    print("🔗 Access at: http://localhost:5000")
    print("👤 Default Login:")
    print("   Username: admin")
    print("   Password: admin456")
    print("=" * 60)
    
    # Run Flask application
    app.run(debug=True, port=5000)