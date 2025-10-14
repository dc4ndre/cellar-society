
# ============================================
# IMPORTS
# ============================================

from flask import Flask, render_template, request, redirect, url_for, flash, session
from functools import wraps
from datetime import datetime
import sqlite3
import hashlib


# ============================================
# APP CONFIGURATION
# ============================================

app = Flask(__name__)
app.secret_key = 'cellar_society_secret_2025'


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
        # Password: admin123 (hashed with SHA-256)
        hashed_pw = hashlib.sha256('admin123'.encode()).hexdigest()
        c.execute("INSERT INTO admins (username, password) VALUES (?, ?)", 
                 ('admin', hashed_pw))
    
    conn.commit()
    conn.close()
    print("Database initialized successfully!")


def get_db_connection():
    """
    Create and return database connection
    Uses row_factory for dictionary-like access
    """
    conn = sqlite3.connect('cellar_society.db')
    conn.row_factory = sqlite3.Row
    return conn


# ============================================
# DATA STRUCTURES - HASH TABLE
# ============================================

class ProductHashTable:
    
    def __init__(self):
        
        self.table = {}
    
    def insert(self, product_id, product_data):

        self.table[product_id] = product_data
    
    def get(self, product_id):

        return self.table.get(product_id, None)
    
    def delete(self, product_id):

        if product_id in self.table:
            del self.table[product_id]
            return True
        return False
    
    def get_all(self):

        return list(self.table.values())


# Initialize global hash table instance
product_cache = ProductHashTable()


def load_products_to_cache():

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
    
    def __init__(self, product):
        self.product = product  # Product dictionary
        self.left = None        # Left child (smaller price)
        self.right = None       # Right child (larger price)


class ProductBST:
    
    def __init__(self):
    
        self.root = None
    
    def insert(self, product):
        
        if not self.root:
            self.root = Node(product)
        else:
            self._insert_recursive(self.root, product)
    
    def _insert_recursive(self, node, product):
        
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
        
        results = []
        self._range_search(self.root, min_price, max_price, results)
        return results
    
    def _range_search(self, node, min_price, max_price, results):
        
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
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_id' not in session:
            flash('Please login first', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


# ============================================
# ROUTES - AUTHENTICATION
# ============================================

@app.route('/')
def index():
    
    if 'admin_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    
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
    
    session.clear()
    flash('Logged out successfully', 'success')
    return redirect(url_for('login'))


# ============================================
# ROUTES - DASHBOARD
# ============================================

@app.route('/dashboard')
@login_required
def dashboard():
    
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
        'pending_orders': pending_orders
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
        image_url = request.form.get('image_url', '')
        
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
        image_url = request.form.get('image_url', '')
        
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
    
    conn = get_db_connection()
    
    # Get product name for flash message
    product = conn.execute(
        'SELECT name FROM products WHERE id = ?', 
        (product_id,)
    ).fetchone()
    
    if product:
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
# ROUTES - ORDER MANAGEMENT (View Only)
# ============================================

@app.route('/orders')
@login_required
def orders():
   
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
    
    conn = get_db_connection()
    
    # Get order with all related dataa
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


# ============================================
# APPLICATION STARTUP
# ============================================

if __name__ == '__main__':
    # Initialize database and create tables
    init_db()
    
    # Load products into hash table cache
    load_products_to_cache()
    
    # Print startup messages
    print("=" * 60)
    print(" Cellar Society Admin Panel Starting...")
    print("=" * 60)
    print(" Access at: http://localhost:5000")
    print(" Default Login:")
    print("   Username: admin")
    print("   Password: admin456")
    print("=" * 60)
    
    # Run Flask application
    app.run(debug=True, port=5000)