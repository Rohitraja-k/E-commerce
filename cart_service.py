"""
Shopping Cart service managing cart state in user session.
Handles real-time price lookup, stock availability checks, taxes, and shipping calculations.
"""

from flask import session
from database import query_db

TAX_RATE = 0.08  # 8% sales tax
FREE_SHIPPING_THRESHOLD = 50.00
STANDARD_SHIPPING_FEE = 5.99


def get_cart():
    """Retrieve raw cart dictionary {str(product_id): quantity} from session."""
    if "cart" not in session or not isinstance(session["cart"], dict):
        session["cart"] = {}
    return session["cart"]


def get_cart_count():
    """Return total number of items currently in cart."""
    cart = get_cart()
    return sum(cart.values())


def get_cart_details():
    """
    Fetch up-to-date product data for cart items and compute pricing totals.
    Handles product deletions and out-of-stock changes gracefully.
    """
    cart = get_cart()
    items = []
    subtotal = 0.0

    if not cart:
        return {
            "items": [],
            "cart_items": [],
            "subtotal": 0.0,
            "tax": 0.0,
            "shipping_fee": 0.0,
            "total": 0.0,
            "item_count": 0,
            "free_shipping_eligible": False,
            "amount_for_free_shipping": FREE_SHIPPING_THRESHOLD
        }

    # Fetch all products present in cart
    placeholders = ",".join("?" for _ in cart.keys())
    product_ids = [int(pid) for pid in cart.keys()]
    db_products = query_db(
        f"""
        SELECT p.id, p.name, p.slug, p.price, p.stock, p.image_url, c.name as category_name
        FROM products p
        JOIN categories c ON p.category_id = c.id
        WHERE p.id IN ({placeholders})
        """,
        product_ids
    )

    product_map = {p["id"]: p for p in db_products}

    # Clean up any products that might have been removed from database
    stale_keys = []
    for pid_str, quantity in list(cart.items()):
        pid = int(pid_str)
        if pid not in product_map:
            stale_keys.append(pid_str)
            continue

        prod = product_map[pid]
        # Cap quantity to current available stock
        actual_qty = min(quantity, prod["stock"])
        if actual_qty <= 0:
            stale_keys.append(pid_str)
            continue

        if actual_qty != quantity:
            cart[pid_str] = actual_qty
            session.modified = True

        item_subtotal = round(prod["price"] * actual_qty, 2)
        subtotal += item_subtotal

        items.append({
            "product_id": prod["id"],
            "name": prod["name"],
            "slug": prod["slug"],
            "price": prod["price"],
            "image_url": prod["image_url"],
            "stock": prod["stock"],
            "category": prod["category_name"],
            "quantity": actual_qty,
            "subtotal": item_subtotal
        })

    for stale in stale_keys:
        cart.pop(stale, None)
        session.modified = True

    subtotal = round(subtotal, 2)
    tax = round(subtotal * TAX_RATE, 2) if subtotal > 0 else 0.0
    shipping_fee = 0.0 if (subtotal >= FREE_SHIPPING_THRESHOLD or subtotal == 0) else STANDARD_SHIPPING_FEE
    total = round(subtotal + tax + shipping_fee, 2)
    item_count = sum(item["quantity"] for item in items)
    free_shipping_diff = round(max(0.0, FREE_SHIPPING_THRESHOLD - subtotal), 2)

    return {
        "items": items,
        "cart_items": items,
        "subtotal": subtotal,
        "tax": tax,
        "shipping_fee": shipping_fee,
        "total": total,
        "item_count": item_count,
        "free_shipping_eligible": subtotal >= FREE_SHIPPING_THRESHOLD,
        "amount_for_free_shipping": free_shipping_diff
    }


def add_to_cart(product_id, quantity=1):
    """Add a product to the cart or increment quantity."""
    try:
        product_id = int(product_id)
        quantity = int(quantity)
        if quantity <= 0:
            return False, "Quantity must be at least 1."
    except (ValueError, TypeError):
        return False, "Invalid product or quantity."

    product = query_db("SELECT id, name, stock FROM products WHERE id = ?", (product_id,), one=True)
    if not product:
        return False, "Product not found."

    if product["stock"] <= 0:
        return False, f"Sorry, '{product['name']}' is out of stock."

    cart = get_cart()
    current_qty = cart.get(str(product_id), 0)
    new_qty = current_qty + quantity

    if new_qty > product["stock"]:
        return False, f"Cannot add {quantity} more. Only {product['stock']} in stock ({current_qty} already in cart)."

    cart[str(product_id)] = new_qty
    session.modified = True
    return True, f"Added '{product['name']}' to cart."


def update_cart_quantity(product_id, quantity):
    """Update quantity for a specific product in cart."""
    try:
        product_id = int(product_id)
        quantity = int(quantity)
    except (ValueError, TypeError):
        return False, "Invalid input."

    cart = get_cart()
    pid_str = str(product_id)

    if quantity <= 0:
        cart.pop(pid_str, None)
        session.modified = True
        return True, "Item removed from cart."

    product = query_db("SELECT id, name, stock FROM products WHERE id = ?", (product_id,), one=True)
    if not product:
        cart.pop(pid_str, None)
        session.modified = True
        return False, "Product no longer available."

    if quantity > product["stock"]:
        cart[pid_str] = product["stock"]
        session.modified = True
        return False, f"Adjusted to available stock ({product['stock']} units)."

    cart[pid_str] = quantity
    session.modified = True
    return True, "Cart updated."


def remove_from_cart(product_id):
    """Remove a product from cart."""
    cart = get_cart()
    pid_str = str(product_id)
    if pid_str in cart:
        del cart[pid_str]
        session.modified = True
        return True, "Item removed from cart."
    return False, "Item not found in cart."


def clear_cart():
    """Clear all items from session cart."""
    session["cart"] = {}
    session.modified = True
