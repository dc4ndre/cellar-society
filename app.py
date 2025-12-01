from flask import Flask, render_template, request, redirect, url_for, flash, session
from functools import wraps
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
from PIL import Image
import sqlite3
import hashlib
import os

app = Flask(__name__)
app.secret_key = 'cellar_society_admin_secret_2024'
app.config['SESSION_COOKIE_NAME'] = 'admin_session'

UPLOAD_FOLDER = 'static/uploads/wines'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_FILE_SIZE = 16 * 1024 * 1024

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_wine_image(file):
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        name, ext = os.path.splitext(filename)
        unique_filename = f"{name}_{timestamp}{ext}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(filepath)
        return f"/static/uploads/wines/{unique_filename}"
    return None

def init_db():
    conn = sqlite3.connect('cellar_society.db')
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS admins (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
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
    
    c.execute('''CREATE TABLE IF NOT EXISTS customers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        phone TEXT,
        address TEXT,
        joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
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
    
    c.execute("SELECT * FROM admins WHERE username='admin'")
    if not c.fetchone():
        hashed_pw = hashlib.sha256('admin456'.encode()).hexdigest()
        c.execute("INSERT INTO admins (username, password) VALUES (?, ?)", ('admin', hashed_pw))
    
    conn.commit()
    conn.close()

def get_db_connection():
    conn = sqlite3.connect('cellar_society.db')
    conn.row_factory = sqlite3.Row
    return conn

def migrate_database():
    conn = sqlite3.connect('cellar_society.db')
    try:
        conn.execute('ALTER TABLE orders ADD COLUMN estimated_delivery_date TEXT')
    except sqlite3.OperationalError:
        pass
    
    try:
        conn.execute('ALTER TABLE orders ADD COLUMN shipped_date TEXT')
    except sqlite3.OperationalError:
        pass
    
    conn.commit()
    conn.close()

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

product_cache = ProductHashTable()

def load_products_to_cache():
    conn = sqlite3.connect('cellar_society.db')
    c = conn.cursor()
    c.execute("SELECT * FROM products")
    products = c.fetchall()
    conn.close()
    
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

class Node:
    def __init__(self, product):
        self.product = product
        self.left = None
        self.right = None

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
            if node.left is None:
                node.left = Node(product)
            else:
                self._insert_recursive(node.left, product)
        else:
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
        
        if min_price <= node.product['price'] <= max_price:
            results.append(node.product)
        
        if min_price < node.product['price']:
            self._range_search(node.left, min_price, max_price, results)
        
        if max_price > node.product['price']:
            self._range_search(node.right, min_price, max_price, results)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_id' not in session:
            flash('Please login first', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def get_admin_notification_counts():
    conn = get_db_connection()
    
    pending_orders = conn.execute('''
        SELECT COUNT(*) as count FROM orders 
        WHERE status = 'Pending'
    ''').fetchone()['count']
    
    processing_orders = conn.execute('''
        SELECT COUNT(*) as count FROM orders 
        WHERE status = 'Processing'
    ''').fetchone()['count']
    
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

@app.context_processor
def inject_admin_notifications():
    return {
        'notifications': get_admin_notification_counts()
    }

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
        hashed_pw = hashlib.sha256(password.encode()).hexdigest()
        
        conn = get_db_connection()
        admin = conn.execute(
            'SELECT * FROM admins WHERE username = ? AND password = ?',
            (username, hashed_pw)
        ).fetchone()
        conn.close()
        
        if admin:
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

@app.route('/dashboard')
@login_required
def dashboard():
    conn = get_db_connection()
    
    total_products = conn.execute('SELECT COUNT(*) as count FROM products').fetchone()['count']
    total_customers = conn.execute('SELECT COUNT(*) as count FROM customers').fetchone()['count']
    total_orders = conn.execute('SELECT COUNT(*) as count FROM orders').fetchone()['count']
    pending_orders = conn.execute('SELECT COUNT(*) as count FROM orders WHERE status = "Pending"').fetchone()['count']
    processing_orders = conn.execute('SELECT COUNT(*) as count FROM orders WHERE status = "Processing"').fetchone()['count']
    unread_messages = conn.execute('''
        SELECT COUNT(*) as count FROM messages 
        WHERE sender_type = 'customer' AND is_read = 0
    ''').fetchone()['count']

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
    
    stats = {
        'total_products': total_products,
        'total_customers': total_customers,
        'total_orders': total_orders,
        'pending_orders': pending_orders,
        'processing_orders': processing_orders,
        'unread_messages': unread_messages
    }
    
    return render_template('admin/dashboard.html', stats=stats, recent_orders=recent_orders)

@app.route('/products')
@login_required
def products():
    conn = get_db_connection()
    products = conn.execute('SELECT * FROM products ORDER BY created_at DESC').fetchall()
    conn.close()
    load_products_to_cache()
    return render_template('admin/products.html', products=products)

@app.route('/products/add', methods=['GET', 'POST'])
@login_required
def add_product():
    if request.method == 'POST':
        name = request.form['name']
        wine_type = request.form['type']
        region = request.form['region']
        vintage = int(request.form['vintage'])
        price = float(request.form['price'])
        alcohol = float(request.form['alcohol'])
        stock = int(request.form['stock'])
        description = request.form.get('description', '')
        
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
        
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('''
            INSERT INTO products 
            (name, type, region, vintage, price, alcohol, stock, description, image_url)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (name, wine_type, region, vintage, price, alcohol, stock, description, image_url))
        
        conn.commit()
        product_id = c.lastrowid
        conn.close()
        
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
        name = request.form['name']
        wine_type = request.form['type']
        region = request.form['region']
        vintage = int(request.form['vintage'])
        price = float(request.form['price'])
        alcohol = float(request.form['alcohol'])
        stock = int(request.form['stock'])
        description = request.form.get('description', '')
        
        current_product = conn.execute('SELECT image_url FROM products WHERE id = ?', (product_id,)).fetchone()
        image_url = current_product['image_url'] if current_product else ''
        
        if 'wine_image' in request.files:
            file = request.files['wine_image']
            if file and file.filename:
                saved_path = save_wine_image(file)
                if saved_path:
                    if image_url and os.path.exists('.' + image_url):
                        try:
                            os.remove('.' + image_url)
                        except:
                            pass
                    image_url = saved_path
        
        conn.execute('''
            UPDATE products 
            SET name=?, type=?, region=?, vintage=?, price=?, 
                alcohol=?, stock=?, description=?, image_url=?
            WHERE id=?
        ''', (name, wine_type, region, vintage, price, alcohol, stock, description, image_url, product_id))
        
        conn.commit()
        conn.close()
        load_products_to_cache()
        
        flash(f'Wine "{name}" updated successfully!', 'success')
        return redirect(url_for('products'))
    
    product = conn.execute('SELECT * FROM products WHERE id = ?', (product_id,)).fetchone()
    conn.close()
    
    if not product:
        flash('Product not found', 'error')
        return redirect(url_for('products'))
    
    return render_template('admin/edit_product.html', product=product)

@app.route('/products/delete/<int:product_id>', methods=['POST'])
@login_required
def delete_product(product_id):
    conn = get_db_connection()
    
    product = conn.execute('SELECT name, image_url FROM products WHERE id = ?', (product_id,)).fetchone()
    
    if product:
        if product['image_url'] and os.path.exists('.' + product['image_url']):
            try:
                os.remove('.' + product['image_url'])
            except:
                pass
        
        conn.execute('DELETE FROM products WHERE id = ?', (product_id,))
        conn.commit()
        product_cache.delete(product_id)
        flash(f'Wine "{product["name"]}" deleted successfully!', 'success')
    else:
        flash('Product not found', 'error')
    
    conn.close()
    return redirect(url_for('products'))

@app.route('/customers')
@login_required
def customers():
    search = request.args.get('search', '')
    conn = get_db_connection()
    query = 'SELECT * FROM customers WHERE 1=1'
    params = []
    
    if search:
        query += ' AND (name LIKE ? OR email LIKE ?)'
        params.extend([f'%{search}%', f'%{search}%'])
    
    query += ' ORDER BY joined_at DESC'
    customers = conn.execute(query, params).fetchall()
    conn.close()
    
    return render_template('admin/customers.html', customers=customers, search=search)

@app.route('/customers/<int:customer_id>')
@login_required
def customer_detail(customer_id):
    conn = get_db_connection()
    
    customer = conn.execute('SELECT * FROM customers WHERE id = ?', (customer_id,)).fetchone()
    
    if not customer:
        flash('Customer not found', 'error')
        conn.close()
        return redirect(url_for('customers'))
    
    orders = conn.execute('''
        SELECT o.*, p.name as product_name, p.type as product_type
        FROM orders o
        JOIN products p ON o.product_id = p.id
        WHERE o.customer_id = ?
        ORDER BY o.order_date DESC
    ''', (customer_id,)).fetchall()
    
    conn.close()
    
    return render_template('admin/customer_detail.html', customer=customer, orders=orders)

@app.route('/orders')
@login_required
def orders():
    status_filter = request.args.get('status', '')
    conn = get_db_connection()
    
    query = '''
        SELECT o.*, c.name as customer_name, c.email as customer_email,
               p.name as product_name, p.type as product_type
        FROM orders o
        JOIN customers c ON o.customer_id = c.id
        JOIN products p ON o.product_id = p.id
        WHERE 1=1
    '''
    params = []
    
    if status_filter:
        query += ' AND o.status = ?'
        params.append(status_filter)
    
    query += ' ORDER BY o.order_date DESC'
    orders = conn.execute(query, params).fetchall()
    conn.close()
    
    return render_template('admin/orders.html', orders=orders, status_filter=status_filter)

@app.route('/orders/<int:order_id>')
@login_required
def order_detail(order_id):
    conn = get_db_connection()
    
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
    new_status = request.form.get('status')
    valid_statuses = ['Pending', 'Processing', 'Delivered', 'Received', 'Cancelled']
    
    if new_status not in valid_statuses:
        flash('Invalid status', 'error')
        return redirect(url_for('orders'))
    
    conn = get_db_connection()
    order = conn.execute('SELECT * FROM orders WHERE id = ?', (order_id,)).fetchone()
    
    if not order:
        flash('Order not found', 'error')
        conn.close()
        return redirect(url_for('orders'))
    
    estimated_delivery = None
    shipped_date = None
    
    if new_status == 'Processing':
        shipped_date = datetime.now().strftime('%Y-%m-%d')
        estimated_delivery = (datetime.now() + timedelta(days=4)).strftime('%B %d, %Y')
    
    if estimated_delivery:
        conn.execute('''
            UPDATE orders 
            SET status = ?, estimated_delivery_date = ?, shipped_date = ?
            WHERE id = ?
        ''', (new_status, estimated_delivery, shipped_date, order_id))
    else:
        conn.execute('UPDATE orders SET status = ? WHERE id = ?', (new_status, order_id))
    
    conn.commit()
    conn.close()
    
    flash(f'Order #{order_id} status updated to {new_status}', 'success')
    return redirect(url_for('orders'))

@app.route('/messages')
@login_required
def messages():
    conn = get_db_connection()
    
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
    
    return render_template('admin/messages.html', customers=customers_with_messages)

@app.route('/messages/<int:customer_id>')
@login_required
def message_thread(customer_id):
    conn = get_db_connection()
    
    customer = conn.execute('SELECT * FROM customers WHERE id = ?', (customer_id,)).fetchone()
    
    if not customer:
        flash('Customer not found', 'error')
        conn.close()
        return redirect(url_for('messages'))
    
    messages = conn.execute('''
        SELECT * FROM messages 
        WHERE customer_id = ?
        ORDER BY created_at ASC
    ''', (customer_id,)).fetchall()
    
    conn.execute('''
        UPDATE messages 
        SET is_read = 1
        WHERE customer_id = ? AND sender_type = 'customer' AND is_read = 0
    ''', (customer_id,))
    
    conn.commit()
    conn.close()
    
    return render_template('admin/message_thread.html', customer=customer, messages=messages)

@app.route('/messages/<int:customer_id>/send', methods=['POST'])
@login_required
def send_message_to_customer(customer_id):
    message_text = request.form.get('message', '').strip()
    
    if not message_text:
        flash('Message cannot be empty', 'error')
        return redirect(url_for('message_thread', customer_id=customer_id))
    
    if len(message_text) > 1000:
        flash('Message is too long (max 1000 characters)', 'error')
        return redirect(url_for('message_thread', customer_id=customer_id))
    
    conn = get_db_connection()
    customer = conn.execute('SELECT * FROM customers WHERE id = ?', (customer_id,)).fetchone()
    
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
    conn = get_db_connection()
    count = conn.execute('''
        SELECT COUNT(*) as count FROM messages 
        WHERE sender_type = 'customer' AND is_read = 0
    ''').fetchone()['count']
    conn.close()
    return count

if __name__ == '__main__':
    init_db()
    migrate_database()
    load_products_to_cache()
    
    print("=" * 60)
    print("🍷 Cellar Society Admin Panel Starting...")
    print("=" * 60)
    print("🔗 Access at: http://localhost:5000")
    print("👤 Default Login:")
    print("   Username: admin")
    print("   Password: admin456")
    print("=" * 60)
    
    app.run(debug=True, port=5000)