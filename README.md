# ShopZone - Modern Flask E-Commerce Web Application

A full-featured, beginner-friendly E-Commerce Web Application built with **Python Flask**, **SQLite**, **HTML5**, **CSS3**, and **JavaScript**.

---

## 🌟 Features Overview

1. **Product Catalog & Details**:
   - Browse catalog by categories: *Electronics*, *Fashion*, *Home & Living*, *Books & Stationery*.
   - Filter by category pills, search by keywords, and sort by Price (Low to High, High to Low) or Newest.
   - Detailed product view with high-res imagery, specifications, live stock indicators, and related products.

2. **Interactive Shopping Cart**:
   - Add products from catalog cards or product detail page.
   - Interactive quantity controls (`+` / `-` buttons) bounded by available inventory stock.
   - Instant cart calculations: Subtotal, 8% Sales Tax, Dynamic Free Shipping progress bar (Free shipping on orders over $50), and Total.
   - Quick Add-to-Cart with dynamic JSON API and toast notifications without page reloads.

3. **Secure Checkout & Order Placement**:
   - Multi-step checkout form collecting shipping address and contact info.
   - Payment method selection: Credit / Debit Card (demo card format with instant validation), PayPal, Cash on Delivery.
   - Real-time stock verification: automatically reduces inventory upon successful checkout.
   - Order confirmation receipt with distinct reference numbers (e.g. `ORD-20261010-ABCD12`).

4. **User Authentication & Role-Based Access Control**:
   - User Registration with validation (email regex, unique username, password strength).
   - Secure password hashing using `werkzeug.security.generate_password_hash`.
   - Role-based authorization: **Admin** and **User** access levels enforced by `@login_required` and `@admin_required` decorators.
   - Autofill demo login shortcuts on the login page for effortless testing.

5. **Comprehensive Admin Dashboard**:
   - Key performance indicators (KPIs): Total Revenue, Total Orders, Active Catalog Items, Total Customers.
   - Low inventory warning system (alerts when stock $\le$ 10).
   - Full Product CRUD: Add, Edit (with live image preview), and Delete products.
   - Order Management: Filter orders by status (*Pending*, *Processing*, *Shipped*, *Delivered*, *Cancelled*) and update fulfillment statuses.
   - User Directory: View registered customers, order counts, and lifetime spending.

6. **Full REST API**:
   - RESTful JSON endpoints for products, shopping cart, orders, and authentication.

7. **Modern, Responsive Design**:
   - Responsive CSS Grid and Flexbox layout tailored for desktop, tablet, and mobile screens.
   - Toast notification system, dismissible alerts, and mobile hamburger navigation.

---

## 📁 Project Structure

```
flask-ecommerce/
├── app.py                  # Application entry point, factory, filters, error handlers
├── database.py             # SQLite connection management, schema initialization & seeding
├── schema.sql              # Database schema (users, categories, products, orders, order_items)
├── auth.py                 # Authentication routes (login, register, logout, RBAC decorators)
├── shop.py                 # Storefront routes (home, catalog, product detail, cart, checkout)
├── admin.py                # Admin dashboard routes, product CRUD, order status updates
├── cart_service.py         # Session cart operations, price & tax logic, stock checks
├── api.py                  # REST API JSON endpoints
├── test_app.py             # Automated unit & integration test suite (15 tests)
├── requirements.txt        # Python package dependencies
├── README.md               # Documentation & setup guide
├── ecommerce.db            # SQLite database file (auto-created on first run)
├── static/
│   ├── css/
│   │   └── style.css       # Responsive CSS design system
│   └── js/
│       └── main.js         # Interactive cart, toast popups, mobile menu
└── templates/
    ├── base.html           # Master layout with navbar, cart badge, alert container, footer
    ├── index.html          # Homepage with hero banner and featured products
    ├── products.html       # Catalog with search, category filtering, and sorting
    ├── product_detail.html # Product detail page with quantity picker
    ├── cart.html           # Full shopping cart page
    ├── checkout.html       # Checkout form with address & payment options
    ├── order_success.html  # Order confirmation receipt page
    ├── order_history.html  # Customer past orders list
    ├── login.html          # Login page with demo autofill buttons
    ├── register.html       # User registration page
    ├── 404.html            # Custom 404 Not Found error page
    ├── 403.html            # Custom 403 Forbidden error page
    ├── 500.html            # Custom 500 Internal Server error page
    └── admin/
        ├── dashboard.html  # Admin KPI metrics and low stock alerts
        ├── products.html   # Admin product inventory table
        ├── product_form.html # Add / Edit product form with live image preview
        ├── orders.html     # Orders management table with status filter tabs
        ├── order_detail.html # Order fulfillment detail and status dropdown
        └── users.html      # Registered users directory
```

---

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.9+ (Python 3.10, 3.11, 3.12, 3.13 supported)
- Built-in SQLite3 (requires no external database server)

### 2. Installation

1. Open your terminal / PowerShell in the project directory:
   ```powershell
   cd C:\Users\LENOVO\.gemini\antigravity\scratch\flask-ecommerce
   ```

2. (Optional but recommended) Create and activate a virtual environment:
   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```

3. Install the required dependencies:
   ```powershell
   pip install -r requirements.txt
   ```

### 3. Running the Application

Start the Flask development server:
```powershell
python app.py
```

Open your browser and navigate to:
```
http://127.0.0.1:5000
```

---

## 🔑 Default Accounts (Pre-configured)

The database initializes and seeds itself automatically on the first launch with sample products and the following accounts:

| Role | Username / Email | Password | Access Privileges |
| :--- | :--- | :--- | :--- |
| **Administrator** | `admin@shopzone.com` (or `admin`) | `admin123` | Full access to Admin Dashboard, Product CRUD, Order Statuses, and API |
| **Customer** | `john@example.com` (or `johndoe`) | `user123` | Browse catalog, shopping cart, checkout, view personal order history |

> **Tip:** You can also click the **"Quick Demo Logins"** buttons on the Sign In page to automatically fill in credentials!

---

## 📡 REST API Documentation

All API responses return JSON with standard HTTP status codes:

### Products API
- `GET /api/products` — List products (supports query parameters: `category=<slug>`, `search=<term>`, `sort=price_asc|price_desc|name|newest`, `limit=50`, `offset=0`)
- `GET /api/products/<id>` — Get single product details
- `POST /api/products` — Create product (*Admin only*)
- `PUT /api/products/<id>` — Update product (*Admin only*)
- `DELETE /api/products/<id>` — Delete product (*Admin only*)

### Cart API
- `GET /api/cart` — Get current cart contents, item details, subtotal, tax, shipping, and total
- `POST /api/cart/add` — Add item: `{"product_id": 1, "quantity": 2}`
- `POST /api/cart/update` — Update item quantity: `{"product_id": 1, "quantity": 3}`
- `POST /api/cart/remove` — Remove item: `{"product_id": 1}`
- `POST /api/cart/clear` — Clear entire cart

### Orders API
- `GET /api/orders` — List orders (returns user's own orders, or all orders if Admin)
- `GET /api/orders/<id>` — Get order details with line items
- `POST /api/orders` — Place order directly via JSON:
  ```json
  {
    "customer_name": "Jane Doe",
    "customer_email": "jane@example.com",
    "shipping_address": "456 Elm Street",
    "city": "Seattle",
    "postal_code": "98101",
    "payment_method": "Credit Card"
  }
  ```
- `PATCH /api/orders/<id>/status` — Update order status: `{"status": "Shipped"}` (*Admin only*)

### Categories & Auth API
- `GET /api/categories` — List all categories with product counts
- `GET /api/users/me` — Current user profile (*Authenticated*)
- `POST /api/auth/login` — REST login: `{"login_id": "admin@shopzone.com", "password": "admin123"}`
- `POST /api/auth/logout` — REST logout

---

## 🧪 Running the Automated Tests

Run the test suite using Python's built-in `unittest`:
```powershell
python -m unittest test_app.py -v
```

All 15 tests run against an isolated temporary database, validating:
- Catalog display, category filters, and keyword search
- User registration, password hashing, and authentication
- Role-based permissions (guest, customer, admin)
- Cart additions, updates, deletions, and total calculations
- Checkout order creation and automated stock deduction
- Admin product CRUD and order status fulfillment updates
- REST API endpoints
