"""
Admin Blueprint providing complete store administration:
- Dashboard KPI metrics and alerts
- Full Product CRUD (Add, Edit, Delete, View)
- Order management and status fulfillment updates
- User overview
"""

import re
import uuid
from flask import (
    Blueprint, render_template, request, redirect,
    url_for, flash
)
from auth import admin_required
from database import query_db, execute_db

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("/")
@admin_bp.route("/dashboard")
@admin_required
def dashboard():
    """Admin dashboard with high-level revenue, order volume, and catalog metrics."""
    # 1. Total revenue (excluding cancelled orders)
    revenue_row = query_db(
        "SELECT COALESCE(SUM(total_amount), 0) as total FROM orders WHERE status != 'Cancelled'",
        one=True
    )
    total_revenue = revenue_row["total"] if revenue_row else 0.0

    # 2. Total orders count
    orders_count = query_db("SELECT COUNT(*) as count FROM orders", one=True)["count"]

    # 3. Total products count
    products_count = query_db("SELECT COUNT(*) as count FROM products", one=True)["count"]

    # 4. Total registered customers count
    customers_count = query_db(
        "SELECT COUNT(*) as count FROM users WHERE role = 'user'",
        one=True
    )["count"]

    # 5. Low stock alerts (stock <= 10)
    low_stock_products = query_db(
        """
        SELECT p.id, p.name, p.stock, p.price, c.name as category_name
        FROM products p
        JOIN categories c ON p.category_id = c.id
        WHERE p.stock <= 10
        ORDER BY p.stock ASC
        LIMIT 6
        """
    )

    # 6. Recent 5 orders
    recent_orders = query_db(
        """
        SELECT id, order_number, customer_name, customer_email, total_amount, status, created_at
        FROM orders
        ORDER BY created_at DESC
        LIMIT 6
        """
    )

    return render_template(
        "admin/dashboard.html",
        total_revenue=total_revenue,
        orders_count=orders_count,
        products_count=products_count,
        customers_count=customers_count,
        low_stock_products=low_stock_products,
        recent_orders=recent_orders
    )


# ----------------------------------------------------------------------
# PRODUCT MANAGEMENT (CRUD)
# ----------------------------------------------------------------------

@admin_bp.route("/products")
@admin_required
def products():
    """View and search all catalog products."""
    search = request.args.get("search", "").strip()
    category_id = request.args.get("category_id", type=int)

    query = """
        SELECT p.*, c.name as category_name
        FROM products p
        JOIN categories c ON p.category_id = c.id
        WHERE 1=1
    """
    params = []

    if search:
        query += " AND (p.name LIKE ? OR p.description LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])

    if category_id:
        query += " AND p.category_id = ?"
        params.append(category_id)

    query += " ORDER BY p.id DESC"

    products_list = query_db(query, params)
    categories = query_db("SELECT id, name FROM categories ORDER BY name ASC")

    return render_template(
        "admin/products.html",
        products=products_list,
        categories=categories,
        search=search,
        selected_category=category_id
    )


@admin_bp.route("/products/new", methods=["GET", "POST"])
@admin_required
def product_new():
    """Add a new product with comprehensive validation."""
    categories = query_db("SELECT id, name FROM categories ORDER BY name ASC")

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        price_raw = request.form.get("price", "").strip()
        stock_raw = request.form.get("stock", "").strip()
        category_id = request.form.get("category_id", type=int)
        image_url = request.form.get("image_url", "").strip()
        is_featured = 1 if request.form.get("is_featured") == "1" else 0

        errors = []
        if not name:
            errors.append("Product name is required.")
        if not description:
            errors.append("Product description is required.")

        try:
            price = float(price_raw)
            if price < 0:
                errors.append("Price must be a positive number.")
        except (ValueError, TypeError):
            errors.append("Please enter a valid price.")

        try:
            stock = int(stock_raw)
            if stock < 0:
                errors.append("Stock cannot be negative.")
        except (ValueError, TypeError):
            errors.append("Please enter a valid stock quantity.")

        if not category_id:
            errors.append("Please select a valid category.")

        if not image_url:
            image_url = "https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=800&auto=format&fit=crop&q=80"

        if errors:
            for error in errors:
                flash(error, "danger")
            return render_template(
                "admin/product_form.html",
                is_edit=False,
                categories=categories,
                form_data=request.form
            )

        slug = re.sub(r"[^a-zA-Z0-9]+", "-", name.lower()).strip("-")
        slug = f"{slug}-{uuid.uuid4().hex[:6]}"

        try:
            execute_db(
                """
                INSERT INTO products (name, slug, description, price, category_id, image_url, stock, is_featured)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (name, slug, description, price, category_id, image_url, stock, is_featured)
            )
            flash(f"Product '{name}' created successfully!", "success")
            return redirect(url_for("admin.products"))
        except Exception as e:
            flash(f"Error saving product: {str(e)}", "danger")

    return render_template(
        "admin/product_form.html",
        is_edit=False,
        categories=categories,
        form_data={}
    )


@admin_bp.route("/products/<int:product_id>/edit", methods=["GET", "POST"])
@admin_required
def product_edit(product_id):
    """Edit an existing product."""
    product = query_db("SELECT * FROM products WHERE id = ?", (product_id,), one=True)
    if not product:
        flash("Product not found.", "danger")
        return redirect(url_for("admin.products"))

    categories = query_db("SELECT id, name FROM categories ORDER BY name ASC")

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        price_raw = request.form.get("price", "").strip()
        stock_raw = request.form.get("stock", "").strip()
        category_id = request.form.get("category_id", type=int)
        image_url = request.form.get("image_url", "").strip()
        is_featured = 1 if request.form.get("is_featured") == "1" else 0

        errors = []
        if not name:
            errors.append("Product name is required.")
        if not description:
            errors.append("Product description is required.")

        try:
            price = float(price_raw)
            if price < 0:
                errors.append("Price must be a positive number.")
        except (ValueError, TypeError):
            errors.append("Please enter a valid price.")

        try:
            stock = int(stock_raw)
            if stock < 0:
                errors.append("Stock cannot be negative.")
        except (ValueError, TypeError):
            errors.append("Please enter a valid stock quantity.")

        if not category_id:
            errors.append("Please select a valid category.")

        if not image_url:
            image_url = product["image_url"]

        if errors:
            for error in errors:
                flash(error, "danger")
            return render_template(
                "admin/product_form.html",
                is_edit=True,
                product=product,
                categories=categories,
                form_data=request.form
            )

        try:
            execute_db(
                """
                UPDATE products
                SET name = ?, description = ?, price = ?, category_id = ?, image_url = ?, stock = ?, is_featured = ?
                WHERE id = ?
                """,
                (name, description, price, category_id, image_url, stock, is_featured, product_id)
            )
            flash(f"Product '{name}' updated successfully!", "success")
            return redirect(url_for("admin.products"))
        except Exception as e:
            flash(f"Error updating product: {str(e)}", "danger")

    return render_template(
        "admin/product_form.html",
        is_edit=True,
        product=product,
        categories=categories,
        form_data=product
    )


@admin_bp.route("/products/<int:product_id>/delete", methods=["POST"])
@admin_required
def product_delete(product_id):
    """Delete a product from the database."""
    product = query_db("SELECT id, name FROM products WHERE id = ?", (product_id,), one=True)
    if not product:
        flash("Product not found.", "danger")
        return redirect(url_for("admin.products"))

    try:
        execute_db("DELETE FROM products WHERE id = ?", (product_id,))
        flash(f"Product '{product['name']}' was deleted.", "info")
    except Exception as e:
        flash(f"Unable to delete product: {str(e)}", "danger")

    return redirect(url_for("admin.products"))


# ----------------------------------------------------------------------
# ORDER MANAGEMENT
# ----------------------------------------------------------------------

@admin_bp.route("/orders")
@admin_required
def orders():
    """Manage customer orders with filtering by status."""
    status_filter = request.args.get("status", "").strip()

    query = """
        SELECT o.*, u.username as account_username
        FROM orders o
        LEFT JOIN users u ON o.user_id = u.id
        WHERE 1=1
    """
    params = []

    if status_filter:
        query += " AND o.status = ?"
        params.append(status_filter)

    query += " ORDER BY o.created_at DESC"
    orders_list = query_db(query, params)

    # Counts by status
    counts_raw = query_db("SELECT status, COUNT(*) as count FROM orders GROUP BY status")
    counts = {row["status"]: row["count"] for row in counts_raw}
    total_count = sum(counts.values())

    return render_template(
        "admin/orders.html",
        orders=orders_list,
        selected_status=status_filter,
        status_counts=counts,
        total_orders=total_count
    )


@admin_bp.route("/orders/<int:order_id>")
@admin_required
def order_detail(order_id):
    """View detailed customer order, items, and shipping info."""
    order = query_db(
        """
        SELECT o.*, u.username as account_username
        FROM orders o
        LEFT JOIN users u ON o.user_id = u.id
        WHERE o.id = ?
        """,
        (order_id,),
        one=True
    )
    if not order:
        flash("Order not found.", "danger")
        return redirect(url_for("admin.orders"))

    items = query_db("SELECT * FROM order_items WHERE order_id = ?", (order_id,))

    return render_template("admin/order_detail.html", order=order, items=items)


@admin_bp.route("/orders/<int:order_id>/status", methods=["POST"])
@admin_required
def update_order_status(order_id):
    """Update fulfillment status of an order."""
    new_status = request.form.get("status", "").strip()
    valid_statuses = ["Pending", "Processing", "Shipped", "Delivered", "Cancelled"]

    if new_status not in valid_statuses:
        flash("Invalid order status requested.", "danger")
        return redirect(url_for("admin.order_detail", order_id=order_id))

    execute_db("UPDATE orders SET status = ? WHERE id = ?", (new_status, order_id))
    flash(f"Order #{order_id} status updated to '{new_status}'.", "success")
    return redirect(url_for("admin.order_detail", order_id=order_id))


# ----------------------------------------------------------------------
# USER DIRECTORY
# ----------------------------------------------------------------------

@admin_bp.route("/users")
@admin_required
def users():
    """View registered users in the system."""
    users_list = query_db(
        """
        SELECT u.id, u.username, u.email, u.full_name, u.role, u.created_at,
               COUNT(o.id) as order_count,
               COALESCE(SUM(o.total_amount), 0) as total_spent
        FROM users u
        LEFT JOIN orders o ON u.id = o.user_id
        GROUP BY u.id
        ORDER BY u.id ASC
        """
    )
    return render_template("admin/users.html", users=users_list)
