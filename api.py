"""
REST API Blueprint providing JSON endpoints for Products, Cart, Orders, Categories, and Authentication.
Adheres to standard HTTP status codes, structured JSON responses, and role authorization.
"""

import re
import uuid
from datetime import datetime
from functools import wraps
from flask import Blueprint, jsonify, request, session
from werkzeug.security import generate_password_hash, check_password_hash
from database import query_db, execute_db, get_db
import cart_service

api_bp = Blueprint("api", __name__, url_prefix="/api")


def api_login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("user_id"):
            return jsonify({"success": False, "error": "Authentication required."}), 401
        return f(*args, **kwargs)
    return decorated_function


def api_admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = session.get("user_id")
        if not user_id:
            return jsonify({"success": False, "error": "Authentication required."}), 401
        user = query_db("SELECT role FROM users WHERE id = ?", (user_id,), one=True)
        if not user or user["role"] != "admin":
            return jsonify({"success": False, "error": "Admin privileges required."}), 403
        return f(*args, **kwargs)
    return decorated_function


# ----------------------------------------------------------------------
# PRODUCTS REST API
# ----------------------------------------------------------------------

@api_bp.route("/products", methods=["GET"])
def get_products():
    """List products with optional search, category filter, sorting, and pagination."""
    category_slug = request.args.get("category")
    search = request.args.get("search", "").strip()
    sort_by = request.args.get("sort", "newest")  # 'price_asc', 'price_desc', 'name', 'newest'
    limit = request.args.get("limit", 50, type=int)
    offset = request.args.get("offset", 0, type=int)

    query = """
        SELECT p.id, p.name, p.slug, p.description, p.price, p.stock,
               p.image_url, p.is_featured, p.created_at,
               c.id as category_id, c.name as category_name, c.slug as category_slug
        FROM products p
        JOIN categories c ON p.category_id = c.id
        WHERE 1=1
    """
    params = []

    if category_slug:
        query += " AND c.slug = ?"
        params.append(category_slug)

    if search:
        query += " AND (p.name LIKE ? OR p.description LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])

    if sort_by == "price_asc":
        query += " ORDER BY p.price ASC"
    elif sort_by == "price_desc":
        query += " ORDER BY p.price DESC"
    elif sort_by == "name":
        query += " ORDER BY p.name ASC"
    else:
        query += " ORDER BY p.id DESC"

    query += " LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    products = query_db(query, params)
    return jsonify({"success": True, "count": len(products), "data": products}), 200


@api_bp.route("/products/<int:product_id>", methods=["GET"])
def get_product(product_id):
    """Retrieve detailed product info by ID."""
    product = query_db(
        """
        SELECT p.*, c.name as category_name, c.slug as category_slug
        FROM products p
        JOIN categories c ON p.category_id = c.id
        WHERE p.id = ?
        """,
        (product_id,),
        one=True
    )
    if not product:
        return jsonify({"success": False, "error": "Product not found."}), 404
    return jsonify({"success": True, "data": product}), 200


@api_bp.route("/products", methods=["POST"])
@api_admin_required
def create_product():
    """Create a new product (Admin only)."""
    data = request.get_json() or {}
    name = (data.get("name") or "").strip()
    description = (data.get("description") or "").strip()
    price = data.get("price")
    category_id = data.get("category_id")
    image_url = (data.get("image_url") or "").strip()
    stock = data.get("stock", 0)
    is_featured = 1 if data.get("is_featured") else 0

    errors = []
    if not name:
        errors.append("Product name is required.")
    if not description:
        errors.append("Product description is required.")
    try:
        price = float(price)
        if price < 0:
            errors.append("Price must be a positive number.")
    except (ValueError, TypeError):
        errors.append("Valid price number is required.")

    try:
        stock = int(stock)
        if stock < 0:
            errors.append("Stock must be zero or positive.")
    except (ValueError, TypeError):
        errors.append("Stock must be an integer.")

    if not category_id:
        errors.append("Valid category is required.")
    else:
        cat = query_db("SELECT id FROM categories WHERE id = ?", (category_id,), one=True)
        if not cat:
            errors.append("Specified category does not exist.")

    if not image_url:
        image_url = "https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=800&auto=format&fit=crop&q=80"

    if errors:
        return jsonify({"success": False, "errors": errors}), 400

    slug = re.sub(r"[^a-zA-Z0-9]+", "-", name.lower()).strip("-")
    slug = f"{slug}-{uuid.uuid4().hex[:6]}"

    res = execute_db(
        """
        INSERT INTO products (name, slug, description, price, category_id, image_url, stock, is_featured)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (name, slug, description, price, category_id, image_url, stock, is_featured)
    )

    created = query_db("SELECT * FROM products WHERE id = ?", (res["lastrowid"],), one=True)
    return jsonify({"success": True, "message": "Product created successfully.", "data": created}), 201


@api_bp.route("/products/<int:product_id>", methods=["PUT"])
@api_admin_required
def update_product(product_id):
    """Update an existing product (Admin only)."""
    product = query_db("SELECT * FROM products WHERE id = ?", (product_id,), one=True)
    if not product:
        return jsonify({"success": False, "error": "Product not found."}), 404

    data = request.get_json() or {}
    name = (data.get("name") or product["name"]).strip()
    description = (data.get("description") or product["description"]).strip()
    image_url = (data.get("image_url") or product["image_url"]).strip()

    try:
        price = float(data.get("price", product["price"]))
        stock = int(data.get("stock", product["stock"]))
        category_id = int(data.get("category_id", product["category_id"]))
        is_featured = 1 if data.get("is_featured", product["is_featured"]) else 0
    except (ValueError, TypeError):
        return jsonify({"success": False, "error": "Invalid numerical values provided."}), 400

    execute_db(
        """
        UPDATE products
        SET name = ?, description = ?, price = ?, category_id = ?, image_url = ?, stock = ?, is_featured = ?
        WHERE id = ?
        """,
        (name, description, price, category_id, image_url, stock, is_featured, product_id)
    )

    updated = query_db("SELECT * FROM products WHERE id = ?", (product_id,), one=True)
    return jsonify({"success": True, "message": "Product updated successfully.", "data": updated}), 200


@api_bp.route("/products/<int:product_id>", methods=["DELETE"])
@api_admin_required
def delete_product(product_id):
    """Delete a product (Admin only)."""
    product = query_db("SELECT * FROM products WHERE id = ?", (product_id,), one=True)
    if not product:
        return jsonify({"success": False, "error": "Product not found."}), 404

    execute_db("DELETE FROM products WHERE id = ?", (product_id,))
    # Remove from session cart if present
    cart_service.remove_from_cart(product_id)
    return jsonify({"success": True, "message": "Product deleted successfully."}), 200


# ----------------------------------------------------------------------
# CART REST API
# ----------------------------------------------------------------------

@api_bp.route("/cart", methods=["GET"])
def get_cart_state():
    """Retrieve full breakdown of user's shopping cart."""
    details = cart_service.get_cart_details()
    return jsonify({"success": True, "data": details}), 200


@api_bp.route("/cart/add", methods=["POST"])
def add_cart_item():
    """Add product and quantity to cart."""
    data = request.get_json() or {}
    product_id = data.get("product_id")
    quantity = data.get("quantity", 1)

    success, message = cart_service.add_to_cart(product_id, quantity)
    if not success:
        return jsonify({"success": False, "error": message}), 400

    details = cart_service.get_cart_details()
    return jsonify({
        "success": True,
        "message": message,
        "cart_count": details["item_count"],
        "data": details
    }), 200


@api_bp.route("/cart/update", methods=["POST"])
def update_cart_item():
    """Update item quantity in cart."""
    data = request.get_json() or {}
    product_id = data.get("product_id")
    quantity = data.get("quantity")

    success, message = cart_service.update_cart_quantity(product_id, quantity)
    details = cart_service.get_cart_details()
    return jsonify({
        "success": success,
        "message": message,
        "cart_count": details["item_count"],
        "data": details
    }), (200 if success else 400)


@api_bp.route("/cart/remove", methods=["POST"])
def remove_cart_item():
    """Remove a product entirely from cart."""
    data = request.get_json() or {}
    product_id = data.get("product_id")

    success, message = cart_service.remove_from_cart(product_id)
    details = cart_service.get_cart_details()
    return jsonify({
        "success": success,
        "message": message,
        "cart_count": details["item_count"],
        "data": details
    }), 200


@api_bp.route("/cart/clear", methods=["POST"])
def clear_cart_items():
    """Clear entire shopping cart."""
    cart_service.clear_cart()
    return jsonify({"success": True, "message": "Cart cleared.", "cart_count": 0}), 200


# ----------------------------------------------------------------------
# ORDERS REST API
# ----------------------------------------------------------------------

@api_bp.route("/orders", methods=["GET"])
@api_login_required
def get_orders():
    """
    List orders. Regular users receive only their own orders.
    Administrators receive all orders across the system.
    """
    user_id = session.get("user_id")
    user = query_db("SELECT role FROM users WHERE id = ?", (user_id,), one=True)

    if user and user["role"] == "admin":
        orders = query_db(
            """
            SELECT o.*, u.username as account_username
            FROM orders o
            LEFT JOIN users u ON o.user_id = u.id
            ORDER BY o.created_at DESC
            """
        )
    else:
        orders = query_db(
            """
            SELECT * FROM orders
            WHERE user_id = ?
            ORDER BY created_at DESC
            """,
            (user_id,)
        )

    return jsonify({"success": True, "count": len(orders), "data": orders}), 200


@api_bp.route("/orders/<int:order_id>", methods=["GET"])
@api_login_required
def get_order(order_id):
    """Retrieve detailed order information with items."""
    user_id = session.get("user_id")
    user = query_db("SELECT role FROM users WHERE id = ?", (user_id,), one=True)

    order = query_db("SELECT * FROM orders WHERE id = ?", (order_id,), one=True)
    if not order:
        return jsonify({"success": False, "error": "Order not found."}), 404

    # Security check: users can only see their own orders unless admin
    if user["role"] != "admin" and order["user_id"] != user_id:
        return jsonify({"success": False, "error": "Unauthorized access to order."}), 403

    items = query_db("SELECT * FROM order_items WHERE order_id = ?", (order_id,))
    order_data = dict(order)
    order_data["items"] = items

    return jsonify({"success": True, "data": order_data}), 200


@api_bp.route("/orders", methods=["POST"])
def place_order():
    """
    Place a new order directly via REST API.
    Reduces inventory stock, creates order and line items, clears cart.
    """
    data = request.get_json() or {}
    customer_name = (data.get("customer_name") or "").strip()
    customer_email = (data.get("customer_email") or "").strip()
    customer_phone = (data.get("customer_phone") or "").strip()
    shipping_address = (data.get("shipping_address") or "").strip()
    city = (data.get("city") or "").strip()
    postal_code = (data.get("postal_code") or "").strip()
    country = (data.get("country") or "United States").strip()
    payment_method = (data.get("payment_method") or "Credit Card").strip()
    notes = (data.get("notes") or "").strip()

    errors = []
    if not customer_name:
        errors.append("Customer full name is required.")
    if not customer_email or "@" not in customer_email:
        errors.append("Valid customer email is required.")
    if not shipping_address:
        errors.append("Shipping address is required.")
    if not city:
        errors.append("City is required.")
    if not postal_code:
        errors.append("Postal code is required.")

    cart_details = cart_service.get_cart_details()
    if not cart_details["items"]:
        errors.append("Shopping cart is empty.")

    if errors:
        return jsonify({"success": False, "errors": errors}), 400

    # Verify inventory availability
    for item in cart_details["items"]:
        prod = query_db("SELECT stock, name FROM products WHERE id = ?", (item["product_id"],), one=True)
        if not prod or prod["stock"] < item["quantity"]:
            return jsonify({
                "success": False,
                "error": f"Insufficient stock for '{item['name']}'. Only {prod['stock'] if prod else 0} remaining."
            }), 400

    user_id = session.get("user_id")
    order_number = f"ORD-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"

    db = get_db()
    cursor = db.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO orders (
                order_number, user_id, customer_name, customer_email, customer_phone,
                shipping_address, city, postal_code, country, payment_method,
                subtotal, tax, shipping_fee, total_amount, status, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Pending', ?)
            """,
            (
                order_number, user_id, customer_name, customer_email, customer_phone,
                shipping_address, city, postal_code, country, payment_method,
                cart_details["subtotal"], cart_details["tax"], cart_details["shipping_fee"],
                cart_details["total"], notes
            )
        )
        order_id = cursor.lastrowid

        # Insert order line items and reduce stock
        for item in cart_details["items"]:
            cursor.execute(
                """
                INSERT INTO order_items (order_id, product_id, product_name, price, quantity, subtotal)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (order_id, item["product_id"], item["name"], item["price"], item["quantity"], item["subtotal"])
            )
            cursor.execute(
                """
                UPDATE products
                SET stock = stock - ?
                WHERE id = ?
                """,
                (item["quantity"], item["product_id"])
            )

        db.commit()
        # Empty user cart after successful purchase
        cart_service.clear_cart()

        return jsonify({
            "success": True,
            "message": "Order placed successfully!",
            "order_number": order_number,
            "order_id": order_id
        }), 201

    except Exception as e:
        db.rollback()
        return jsonify({"success": False, "error": f"Database error: {str(e)}"}), 500


@api_bp.route("/orders/<int:order_id>/status", methods=["PATCH"])
@api_admin_required
def update_order_status(order_id):
    """Update order fulfillment status (Admin only)."""
    valid_statuses = ["Pending", "Processing", "Shipped", "Delivered", "Cancelled"]
    data = request.get_json() or {}
    new_status = data.get("status")

    if new_status not in valid_statuses:
        return jsonify({
            "success": False,
            "error": f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
        }), 400

    order = query_db("SELECT id FROM orders WHERE id = ?", (order_id,), one=True)
    if not order:
        return jsonify({"success": False, "error": "Order not found."}), 404

    execute_db("UPDATE orders SET status = ? WHERE id = ?", (new_status, order_id))
    return jsonify({"success": True, "message": f"Order status updated to '{new_status}'."}), 200


# ----------------------------------------------------------------------
# CATEGORIES & USER PROFILE REST API
# ----------------------------------------------------------------------

@api_bp.route("/categories", methods=["GET"])
def get_categories():
    """Retrieve all product categories with product counts."""
    categories = query_db(
        """
        SELECT c.*, COUNT(p.id) as product_count
        FROM categories c
        LEFT JOIN products p ON c.id = p.category_id
        GROUP BY c.id
        ORDER BY c.name ASC
        """
    )
    return jsonify({"success": True, "data": categories}), 200


@api_bp.route("/users/me", methods=["GET"])
@api_login_required
def get_current_user_profile():
    """Retrieve current logged-in user profile."""
    user_id = session.get("user_id")
    user = query_db(
        "SELECT id, username, email, full_name, role, created_at FROM users WHERE id = ?",
        (user_id,),
        one=True
    )
    return jsonify({"success": True, "data": user}), 200


@api_bp.route("/auth/login", methods=["POST"])
def api_login():
    """REST API user login."""
    data = request.get_json() or {}
    login_id = (data.get("login_id") or "").strip()
    password = data.get("password", "")

    if not login_id or not password:
        return jsonify({"success": False, "error": "Login ID and password are required."}), 400

    user = query_db(
        """
        SELECT id, username, email, password_hash, full_name, role
        FROM users
        WHERE LOWER(username) = LOWER(?) OR LOWER(email) = LOWER(?)
        """,
        (login_id, login_id),
        one=True
    )

    if not user or not check_password_hash(user["password_hash"], password):
        return jsonify({"success": False, "error": "Invalid credentials."}), 401

    session["user_id"] = user["id"]
    session["username"] = user["username"]
    session["full_name"] = user["full_name"]
    session["role"] = user["role"]
    session.permanent = True

    return jsonify({
        "success": True,
        "message": "Login successful.",
        "user": {
            "id": user["id"],
            "username": user["username"],
            "email": user["email"],
            "full_name": user["full_name"],
            "role": user["role"]
        }
    }), 200


@api_bp.route("/auth/logout", methods=["POST"])
def api_logout():
    """REST API user logout."""
    cart_backup = session.get("cart")
    session.clear()
    if cart_backup:
        session["cart"] = cart_backup
    return jsonify({"success": True, "message": "Successfully logged out."}), 200
