"""
Shopfront Blueprint handling user-facing catalog, product views, shopping cart, checkout,
and order tracking.
"""

import uuid
from datetime import datetime
from flask import (
    Blueprint, render_template, request, redirect,
    url_for, flash, session
)
from database import query_db, execute_db, get_db
from auth import login_required, get_current_user
import cart_service

shop_bp = Blueprint("shop", __name__)


# ----------------------------------------------------------------------
# CATALOG & PRODUCT PAGES
# ----------------------------------------------------------------------

@shop_bp.route("/")
def index():
    """Homepage showcasing hero banner, categories, and featured products."""
    categories = query_db(
        """
        SELECT c.*, COUNT(p.id) as product_count
        FROM categories c
        LEFT JOIN products p ON c.id = p.category_id
        GROUP BY c.id
        ORDER BY c.name ASC
        """
    )
    featured_products = query_db(
        """
        SELECT p.*, c.name as category_name
        FROM products p
        JOIN categories c ON p.category_id = c.id
        WHERE p.is_featured = 1
        ORDER BY p.id DESC
        LIMIT 8
        """
    )
    new_arrivals = query_db(
        """
        SELECT p.*, c.name as category_name
        FROM products p
        JOIN categories c ON p.category_id = c.id
        ORDER BY p.created_at DESC
        LIMIT 4
        """
    )
    return render_template(
        "index.html",
        categories=categories,
        featured_products=featured_products,
        new_arrivals=new_arrivals
    )


@shop_bp.route("/products")
def products():
    """Catalog page supporting search, category filter, and sorting."""
    search = request.args.get("search", "").strip()
    category_slug = request.args.get("category", "").strip()
    sort_by = request.args.get("sort", "newest")

    query = """
        SELECT p.*, c.name as category_name, c.slug as category_slug
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

    products_list = query_db(query, params)
    categories = query_db("SELECT * FROM categories ORDER BY name ASC")

    active_category = None
    if category_slug:
        active_category = query_db("SELECT * FROM categories WHERE slug = ?", (category_slug,), one=True)

    return render_template(
        "products.html",
        products=products_list,
        categories=categories,
        search=search,
        selected_category=category_slug,
        active_category=active_category,
        sort_by=sort_by
    )


@shop_bp.route("/product/<int:product_id>")
def product_detail(product_id):
    """Detailed view for a single product with stock indicator and related items."""
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
        flash("Product not found.", "danger")
        return redirect(url_for("shop.products"))

    related_products = query_db(
        """
        SELECT p.*, c.name as category_name
        FROM products p
        JOIN categories c ON p.category_id = c.id
        WHERE p.category_id = ? AND p.id != ?
        LIMIT 4
        """,
        (product["category_id"], product["id"])
    )

    return render_template(
        "product_detail.html",
        product=product,
        related_products=related_products
    )


# ----------------------------------------------------------------------
# SHOPPING CART
# ----------------------------------------------------------------------

@shop_bp.route("/cart")
def cart():
    """Shopping cart review page."""
    cart_data = cart_service.get_cart_details()
    return render_template("cart.html", cart=cart_data)


@shop_bp.route("/cart/add/<int:product_id>", methods=["POST"])
def cart_add(product_id):
    """Add item to shopping cart from standard form submission."""
    quantity = request.form.get("quantity", 1, type=int)
    success, msg = cart_service.add_to_cart(product_id, quantity)
    if success:
        flash(msg, "success")
    else:
        flash(msg, "danger")

    next_url = request.form.get("next") or request.referrer or url_for("shop.cart")
    return redirect(next_url)


@shop_bp.route("/cart/update/<int:product_id>", methods=["POST"])
def cart_update(product_id):
    """Update item quantity in cart."""
    quantity = request.form.get("quantity", 1, type=int)
    success, msg = cart_service.update_cart_quantity(product_id, quantity)
    if success:
        flash(msg, "info")
    else:
        flash(msg, "warning")
    return redirect(url_for("shop.cart"))


@shop_bp.route("/cart/remove/<int:product_id>", methods=["POST"])
def cart_remove(product_id):
    """Remove item from cart."""
    success, msg = cart_service.remove_from_cart(product_id)
    if success:
        flash(msg, "info")
    return redirect(url_for("shop.cart"))


# ----------------------------------------------------------------------
# CHECKOUT & ORDERS
# ----------------------------------------------------------------------

@shop_bp.route("/checkout", methods=["GET", "POST"])
def checkout():
    """Checkout page to collect shipping, payment, and submit orders."""
    cart_data = cart_service.get_cart_details()

    if not cart_data["items"]:
        flash("Your cart is empty. Add items before checking out.", "warning")
        return redirect(url_for("shop.products"))

    current_user = get_current_user()

    if request.method == "POST":
        customer_name = request.form.get("customer_name", "").strip()
        customer_email = request.form.get("customer_email", "").strip()
        customer_phone = request.form.get("customer_phone", "").strip()
        shipping_address = request.form.get("shipping_address", "").strip()
        city = request.form.get("city", "").strip()
        postal_code = request.form.get("postal_code", "").strip()
        country = request.form.get("country", "United States").strip()
        payment_method = request.form.get("payment_method", "Credit Card").strip()
        notes = request.form.get("notes", "").strip()

        errors = []
        if not customer_name:
            errors.append("Please enter your full name.")
        if not customer_email or "@" not in customer_email:
            errors.append("Please enter a valid email address.")
        if not shipping_address:
            errors.append("Please enter your shipping address.")
        if not city:
            errors.append("Please enter your city.")
        if not postal_code:
            errors.append("Please enter your postal/ZIP code.")

        # Re-check stock in case of race conditions
        for item in cart_data["items"]:
            prod = query_db("SELECT stock, name FROM products WHERE id = ?", (item["product_id"],), one=True)
            if not prod or prod["stock"] < item["quantity"]:
                errors.append(f"Sorry, '{item['name']}' only has {prod['stock'] if prod else 0} remaining in stock.")

        if errors:
            for err in errors:
                flash(err, "danger")
            return render_template(
                "checkout.html",
                cart=cart_data,
                user=current_user,
                form_data=request.form
            )

        # Place the order
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
                    cart_data["subtotal"], cart_data["tax"], cart_data["shipping_fee"],
                    cart_data["total"], notes
                )
            )
            order_id = cursor.lastrowid

            for item in cart_data["items"]:
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
            cart_service.clear_cart()

            flash("Your order has been placed successfully!", "success")
            return redirect(url_for("shop.order_success", order_number=order_number))

        except Exception as e:
            db.rollback()
            flash(f"An error occurred while processing your order: {str(e)}", "danger")

    return render_template(
        "checkout.html",
        cart=cart_data,
        user=current_user,
        form_data={}
    )


@shop_bp.route("/order/success/<order_number>")
def order_success(order_number):
    """Order confirmation receipt."""
    order = query_db("SELECT * FROM orders WHERE order_number = ?", (order_number,), one=True)
    if not order:
        flash("Order not found.", "warning")
        return redirect(url_for("shop.index"))

    items = query_db("SELECT * FROM order_items WHERE order_id = ?", (order["id"],))
    return render_template("order_success.html", order=order, items=items)


@shop_bp.route("/orders")
@login_required
def orders():
    """User's historical orders list."""
    user_id = session.get("user_id")
    user_orders = query_db(
        """
        SELECT * FROM orders
        WHERE user_id = ?
        ORDER BY created_at DESC
        """,
        (user_id,)
    )
    return render_template("order_history.html", orders=user_orders)


@shop_bp.route("/orders/<int:order_id>")
@login_required
def order_view(order_id):
    """View single past order by customer."""
    user_id = session.get("user_id")
    order = query_db("SELECT * FROM orders WHERE id = ? AND user_id = ?", (order_id, user_id), one=True)
    if not order:
        flash("Order not found or unauthorized.", "danger")
        return redirect(url_for("shop.orders"))

    items = query_db("SELECT * FROM order_items WHERE order_id = ?", (order["id"],))
    return render_template("order_success.html", order=order, items=items, is_history=True)
