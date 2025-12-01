Here is the **entire document rewritten cleanly, formally, and consistently**, with the **Category Hash Table** fully integrated.
I kept all content accurate, organized, and professional for a project paper.

---

# **Cellar Society — E-Commerce Wine Management System**

## **Project Summary**

---

## **Overview**

**Cellar Society** is a full-stack e-commerce platform designed for premium wine retail, developed as the Final Project for CPE 6 (2nd Year). The system provides two separate portals—Admin and Customer—built using Flask (Python) and SQLite. It integrates multiple data structures to optimize product management, customer interactions, order processing, and overall system performance.

---

# **System Architecture**

## **Two-Portal Design**

### **1. Admin Portal** (`app.py`) — Port 5000

* Product and inventory management
* Customer account viewing
* Order processing & status control
* Messaging system for customer communication

### **2. Customer Portal** (`customer_app.py`) — Port 5001

* Product browsing and category-based filtering
* Advanced search with browsing history
* Shopping cart and checkout
* Order tracking with delivery estimates
* Profile management and messaging features

---

# **Core Features**

## **Admin Features**

### **Product Management (CRUD)**

* Add, edit, and delete wine products
* Upload product images
* Manage stock and availability
* Real-time search and filtering

### **Order Management**

* View and filter all customer orders
* Update order status (Pending → Processing → Delivered → Received)
* Auto-calculate delivery date (4 days from processing)
* Track full order lifecycle

### **Customer Management**

* View customer accounts (read-only)
* Access personal details and order history
* Send direct messages to customers

### **Dashboard Analytics**

* Total counts for products, customers, and orders
* Pending order notifications
* Recent order activity feed
* Unread message alerts

---

## **Customer Features**

### **Shopping Experience**

* Browse wines by category
* Advanced search with LIFO history
* Smart product recommendations
* Detailed product pages

### **Shopping Cart**

* Add, remove, and modify quantities
* “Buy Now” instant checkout
* Session-based cart storage

### **Order Tracking**

* Shopee-style status tabs (To Pay, To Ship, To Receive, Completed, Cancelled)
* Real-time status updates
* Delivery date estimates
* Order receipt confirmation

### **User Profile**

* Edit personal information
* Manage delivery address
* Change password
* View browsing history (Stack – last 10 items)
* Account deletion option

---

# **Data Structures Implementation**

## **1. Hash Table — Product Storage (O(1) Lookup)**

```python
class ProductHashTable
```

* Maps product ID → product data
* Enables instant product retrieval in admin operations

---

## **2. Hash Table — Category Organization (O(1) Lookup)**

```python
class CategoryHashTable
```

* Stores products by category (Red, White, Rosé, Sparkling, Dessert, Fortified)
* Category → list of products
* Fast category filtering without scanning the entire product list
* O(1) insertion, lookup, and category counting

---

## **3. Binary Search Tree — Price Filtering (O(log n) Search)**

```python
class ProductBST
```

* Organizes products by price
* Efficient retrieval for price ranges and sorted displays

---

## **4. Queue — Order Processing (FIFO, O(1))**

```python
class OrderQueue
```

* Ensures orders are processed in the order they were placed
* Supports predictable workflow for admins

---

## **5. Stack — Browsing & Search History (LIFO, O(1))**

```python
class BrowsingHistory
class SearchHistory
```

* Tracks recent browsing (last 50 items)
* Stores recent search queries (last 10)
* Provides quick revisit functionality for users

---

## **6. Shopping Cart — Hash Table Structure**

```python
class ShoppingCart
```

* Product ID → product information + quantity
* O(1) add, update, and remove operations
* Reliable structure for customer checkout workflow

---

# **Database Schema**

## **Tables**

1. **admins** — Admin credentials
2. **products** — Wine inventory (name, type, region, vintage, price, alcohol, stock, image)
3. **customers** — Customer accounts (name, email, password, phone, address)
4. **orders** — Order data (customer_id, product_id, quantity, price, status, timestamps)
5. **messages** — Admin–customer communication threads

## **Relationships**

* Orders → Customers (Foreign Key)
* Orders → Products (Foreign Key)
* Messages → Customers (Foreign Key)

---

# **Technology Stack**

## **Backend**

* **Framework:** Flask (Python)
* **Database:** SQLite
* **Password Security:** SHA-256 hashing
* **Session Handling:** Flask sessions

## **Frontend**

* **Template Engine:** Jinja2
* **Styling:** Custom CSS (no third-party frameworks)
* **UI Theme:** Wine-themed layout with colors

  * Primary: `#5a2a27`
  * Accent: `#c6a664`

## **File Handling**

* **Image Upload:** Werkzeug secure_filename
* **Image Processing:** Pillow (PIL)
* **Supported Formats:** PNG, JPG, JPEG, GIF, WEBP
* **Max File Size:** 16MB

---

# **Key Workflows**

## **Order Lifecycle**

1. Customer places order → **Pending**
2. Admin processes order → **Processing** (delivery date assigned)
3. Admin ships order → **Delivered**
4. Customer confirms receipt → **Received**

---

## **Messaging System**

* Customers can message the admin
* Admin replies to individual users
* Real-time unread message alerts
* Private conversation threads

---

## **Browsing History**

* Tracks last 50 viewed products
* Uses Stack (LIFO) — most recent at the top
* Option to clear history
* Displayed in the profile section

---

# **Security Features**

* SHA-256 password hashing
* Login-required decorators
* Session-based authentication
* Separate admin/customer session states
* SQL injection prevention (parameterized queries)

---

# **File Structure**

```
/static/uploads/wines/      # Wine images
/templates/
    /admin/                # Admin portal templates
    /customer/             # Customer portal templates
app.py                     # Admin application
customer_app.py            # Customer application
cellar_society.db          # SQLite database
```

---

# **Additional Features**

## **Smart Search**

* Live search suggestions
* Search history tracking
* "Recent searches" dropdown
* Clear history option

## **Delivery Tracking**

* Estimated delivery: 4 days
* Tracks ship date and status
* Organized status filtering
* Auto date computation

## **Responsive UI**

* Mobile-friendly layouts
* Grid-based product displays
* Adaptive navigation
* Touch-optimized controls

---

