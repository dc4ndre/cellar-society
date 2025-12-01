# Cellar Society - E-Commerce Wine Management System
## Project Summary

### Overview
**Cellar Society** is a full-stack e-commerce platform for premium wine sales, developed as a CPE 6 2nd Year Final Project. The system features separate admin and customer portals built with Flask (Python), SQLite database, and implements various data structures for efficient operations.

---

## System Architecture

### Two-Portal Design
1. **Admin Portal** (`app.py`) - Port 5000
   - Product/inventory management
   - Customer account viewing
   - Order processing & status updates
   - Customer messaging system

2. **Customer Portal** (`customer_app.py`) - Port 5001
   - Product browsing & search
   - Shopping cart & checkout
   - Order tracking with delivery estimates
   - Profile management & browsing history
   - Messaging with admin

---

## Core Features

### Admin Side
- **Product Management (CRUD)**
  - Add/edit/delete wine products
  - Image upload support
  - Stock management
  - Real-time search & filtering

- **Order Management**
  - View all orders with filtering
  - Update order status (Pending → Processing → Delivered → Received)
  - Automatic delivery date calculation (4 days)
  - Track order lifecycle

- **Customer Management**
  - View customer accounts (read-only)
  - Access customer details & order history
  - Message individual customers

- **Dashboard Analytics**
  - Total products, customers, orders
  - Pending orders count
  - Recent order activity
  - Unread message notifications

### Customer Side
- **Shopping Experience**
  - Browse wine collection by category
  - Advanced search with history (Stack - LIFO)
  - Product recommendations
  - Detailed product pages

- **Shopping Cart**
  - Add/remove/update quantities
  - "Buy Now" quick checkout option
  - Session-based cart storage

- **Order Tracking**
  - Shopee-style tabs (To Pay, To Ship, To Receive, Completed, Cancelled)
  - Real-time status updates
  - Delivery date estimates
  - Order confirmation system

- **User Profile**
  - Edit personal information
  - Manage delivery address
  - Change password
  - View browsing history (Stack - LIFO, last 10 items)
  - Account deletion option

---

## Data Structures Implementation

### 1. **Hash Table** (O(1) lookup)
```python
class ProductHashTable
```
- Product ID → Product data mapping
- Fast product retrieval in admin panel

### 2. **Binary Search Tree** (O(log n) search)
```python
class ProductBST
```
- Price-based product organization
- Efficient price range filtering

### 3. **Queue** (FIFO - O(1) operations)
```python
class OrderQueue
```
- Order processing pipeline
- First-in, first-out order handling

### 4. **Stack** (LIFO - O(1) operations)
```python
class BrowsingHistory
class SearchHistory
```
- Browsing history (last 50 products)
- Search history (last 10 queries)
- Recent activity tracking

### 5. **Shopping Cart** (Hash Table)
```python
class ShoppingCart
```
- Product ID → {product_info, quantity}
- O(1) add/remove/update operations

---

## Database Schema

### Tables
1. **admins** - Admin credentials
2. **products** - Wine inventory (name, type, region, vintage, price, alcohol, stock, image)
3. **customers** - Customer accounts (name, email, password, phone, address)
4. **orders** - Purchase records (customer_id, product_id, quantity, price, status, dates)
5. **messages** - Admin-customer communication

### Key Relationships
- Orders → Customers (Foreign Key)
- Orders → Products (Foreign Key)
- Messages → Customers (Foreign Key)

---

## Technology Stack

### Backend
- **Framework**: Flask (Python)
- **Database**: SQLite with row_factory
- **Authentication**: SHA-256 password hashing
- **Session Management**: Flask sessions

### Frontend
- **Template Engine**: Jinja2
- **Styling**: Custom CSS (no frameworks)
- **Design**: Responsive, wine-themed UI
- **Colors**: Primary (#5a2a27), Accent (#c6a664)

### File Handling
- **Image Upload**: Werkzeug secure_filename
- **Image Processing**: Pillow (PIL)
- **Allowed Formats**: PNG, JPG, JPEG, GIF, WEBP
- **Max Size**: 16MB

---

## Key Workflows

### Order Lifecycle
1. **Customer** places order → Status: Pending
2. **Admin** processes order → Status: Processing (sets delivery date)
3. **Admin** ships order → Status: Delivered
4. **Customer** confirms receipt → Status: Received

### Messaging System
- Customers can message admin for inquiries
- Admin can reply directly to individual customers
- Real-time unread message notifications
- Private conversation threads

### Browsing History
- Automatically tracks last 50 viewed products
- Uses Stack (LIFO) - most recent first
- Clear history option
- Displayed in profile page

---

## Security Features
- Password hashing (SHA-256)
- Login required decorators
- Session-based authentication
- Separate admin/customer sessions
- SQL injection prevention (parameterized queries)

---

## File Structure
```
/static/uploads/wines/    # Product images
/templates/
  /admin/                 # Admin portal templates
  /customer/              # Customer portal templates
app.py                    # Admin application
customer_app.py           # Customer application
cellar_society.db         # SQLite database
```

---

## Notable Features

### Smart Search
- Live search with dropdown suggestions
- Search history tracking
- Recent searches display
- Clear history option

### Delivery Tracking
- Estimated delivery: 4 days from processing
- Shipped date tracking
- Status-based filtering
- Automatic date calculation

### Responsive Design
- Mobile-friendly layouts
- Grid-based product display
- Adaptive navigation
- Touch-friendly controls

---

## Default Credentials
**Admin Portal** (localhost:5000)
- Username: `admin`
- Password: `admin456`

**Customer Portal** (localhost:5001)
- Register new account required

---
