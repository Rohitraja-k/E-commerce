"""
Database configuration, helpers, schema initialization, and seeding.
Uses Python's built-in sqlite3 with row factory for dictionary-style access.
"""

import os
import sqlite3
from flask import g, current_app
from werkzeug.security import generate_password_hash

DB_NAME = "ecommerce.db"


def get_db_path():
    """Return the absolute path to the SQLite database file."""
    if current_app and "DATABASE" in current_app.config:
        return current_app.config["DATABASE"]
    base_dir = os.path.abspath(os.path.dirname(__file__))
    return os.path.join(base_dir, DB_NAME)


def get_db():
    """
    Open a new database connection if there is none yet for the
    current application context.
    """
    if "db" not in g:
        g.db = sqlite3.connect(get_db_path())
        g.db.row_factory = sqlite3.Row
        # Enable foreign key support
        g.db.execute("PRAGMA foreign_keys = ON;")
    return g.db


def close_db(e=None):
    """Close the database connection if open."""
    db = g.pop("db", None)
    if db is not None:
        db.close()


def query_db(query, args=(), one=False):
    """Convenience helper to execute a query and return rows as dicts."""
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    if rv:
        if one:
            return dict(rv[0])
        return [dict(row) for row in rv]
    return None if one else []


def execute_db(query, args=(), commit=True):
    """Convenience helper to execute an INSERT/UPDATE/DELETE query."""
    db = get_db()
    cur = db.cursor()
    cur.execute(query, args)
    if commit:
        db.commit()
    last_id = cur.lastrowid
    row_count = cur.rowcount
    cur.close()
    return {"lastrowid": last_id, "rowcount": row_count}


def init_db(app=None):
    """Initialize tables from schema.sql and seed sample data."""
    base_dir = os.path.abspath(os.path.dirname(__file__))
    schema_path = os.path.join(base_dir, "schema.sql")
    db_path = get_db_path()

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")

    with open(schema_path, "r", encoding="utf-8") as f:
        conn.executescript(f.read())

    # Check if database is already seeded
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as count FROM users")
    user_count = cursor.fetchone()["count"]

    if user_count == 0:
        seed_data(conn)

    conn.commit()
    conn.close()
    print(f"Database initialized and verified at: {db_path}")


def seed_data(conn):
    """Seed initial users, categories, products, and sample orders."""
    cursor = conn.cursor()

    # 1. Seed Users (1 Admin, 1 Regular Customer)
    users = [
        (
            "admin",
            "admin@shopzone.com",
            generate_password_hash("admin123"),
            "System Administrator",
            "admin"
        ),
        (
            "johndoe",
            "john@example.com",
            generate_password_hash("user123"),
            "John Doe",
            "user"
        )
    ]
    cursor.executemany(
        """
        INSERT INTO users (username, email, password_hash, full_name, role)
        VALUES (?, ?, ?, ?, ?)
        """,
        users
    )

    # 2. Seed Categories
    categories = [
        (1, "Electronics", "electronics", "Gadgets, audio, computing and mobile accessories", "bi-laptop"),
        (2, "Fashion", "fashion", "Apparel, travel gear, eyewear, and everyday essentials", "bi-bag"),
        (3, "Home & Living", "home-living", "Minimalist home decor, lighting, and kitchenware", "bi-house-heart"),
        (4, "Books & Stationery", "books-stationery", "Curated developer books and quality notebooks", "bi-book")
    ]
    cursor.executemany(
        """
        INSERT INTO categories (id, name, slug, description, icon)
        VALUES (?, ?, ?, ?, ?)
        """,
        categories
    )

    # 3. Seed Products
    products = [
        (
            "Sony WH-1000XM5 Wireless Headphones",
            "sony-wh-1000xm5-wireless-headphones",
            "Industry-leading noise canceling headphones with dual processors and 8 microphones for exceptional call quality and immersion.",
            348.00,
            1,
            "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=800&auto=format&fit=crop&q=80",
            18,
            1
        ),
        (
            "Apple Watch SE (GPS, 40mm)",
            "apple-watch-se-gps-40mm",
            "Essential features to help you stay connected, active, healthy, and safe. High-luminance Retina display.",
            249.00,
            1,
            "https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=800&auto=format&fit=crop&q=80",
            25,
            1
        ),
        (
            "Keychron K2 Mechanical Keyboard",
            "keychron-k2-mechanical-keyboard",
            "Compact 75% layout wireless mechanical keyboard with Mac & Windows compatibility, hot-swappable Gateron G Pro switches.",
            89.99,
            1,
            "https://images.unsplash.com/photo-1587829741301-dc798b83add3?w=800&auto=format&fit=crop&q=80",
            30,
            1
        ),
        (
            "Anker 737 Power Bank 24,000mAh",
            "anker-737-power-bank-24000mah",
            "Ultra-powerful two-way charging with Power Delivery 3.1 and smart digital display. 140W fast output.",
            129.99,
            1,
            "https://images.unsplash.com/photo-1609592426802-53b754924ef9?w=800&auto=format&fit=crop&q=80",
            40,
            0
        ),
        (
            "Minimalist Leather Travel Backpack",
            "minimalist-leather-travel-backpack",
            "Full-grain water-resistant leather backpack featuring padded 16-inch laptop compartment and anti-theft hidden pocket.",
            119.50,
            2,
            "https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=800&auto=format&fit=crop&q=80",
            15,
            1
        ),
        (
            "Organic Heavyweight Cotton Hoodie",
            "organic-heavyweight-cotton-hoodie",
            "Crafted from 100% combed organic French terry cotton with reinforced double stitching and tailored relaxed fit.",
            58.00,
            2,
            "https://images.unsplash.com/photo-1556905055-8f358a7a47b2?w=800&auto=format&fit=crop&q=80",
            50,
            0
        ),
        (
            "Ray-Ban Classic Polarized Sunglasses",
            "ray-ban-classic-polarized-sunglasses",
            "Iconic lightweight metal frames with crystal green polarized lenses offering 100% UV protection and glare elimination.",
            145.00,
            2,
            "https://images.unsplash.com/photo-1511499767150-a48a237f0083?w=800&auto=format&fit=crop&q=80",
            20,
            1
        ),
        (
            "Premium Canvas Low-Top Sneakers",
            "premium-canvas-low-top-sneakers",
            "Timeless low-top silhouette with cushioned vulcanized rubber sole and breathable canvas upper for all-day comfort.",
            65.00,
            2,
            "https://images.unsplash.com/photo-1525966222134-fcfa99b8ae77?w=800&auto=format&fit=crop&q=80",
            35,
            0
        ),
        (
            "Barista Pour-Over Coffee Maker Set",
            "barista-pour-over-coffee-maker-set",
            "Heat-resistant borosilicate glass carafe with laser-cut reusable stainless steel mesh filter and silicone grip collar.",
            38.50,
            3,
            "https://images.unsplash.com/photo-1514432324607-a09d9b4aefdd?w=800&auto=format&fit=crop&q=80",
            22,
            1
        ),
        (
            "Minimalist Dimmable LED Desk Lamp",
            "minimalist-dimmable-led-desk-lamp",
            "Sleek aluminum architecture with 5 color temperatures, touch brightness slider, and built-in USB wireless charging base.",
            48.00,
            3,
            "https://images.unsplash.com/photo-1507473885765-e6ed057f782c?w=800&auto=format&fit=crop&q=80",
            12,
            0
        ),
        (
            "Ceramic Geometric Indoor Planter Set",
            "ceramic-geometric-indoor-planter-set",
            "Set of 3 matte white ceramic pots with drainage holes and natural bamboo saucers. Ideal for succulents and desk greenery.",
            29.99,
            3,
            "https://images.unsplash.com/photo-1485955900006-10f4d324d411?w=800&auto=format&fit=crop&q=80",
            30,
            0
        ),
        (
            "The Pragmatic Programmer (20th Anniversary)",
            "the-pragmatic-programmer-20th-anniversary",
            "One of the most significant books in software engineering, offering timeless insights on code craftsmanship and career growth.",
            49.95,
            4,
            "https://images.unsplash.com/photo-1544716278-ca5e3f4abd8c?w=800&auto=format&fit=crop&q=80",
            45,
            1
        ),
        (
            "Hardcover Dotted Grid Journal",
            "hardcover-dotted-grid-journal",
            "160gsm bleed-proof bamboo paper, lay-flat thread-bound binding, inner accordion pocket, and dual ribbon bookmarks.",
            19.50,
            4,
            "https://images.unsplash.com/photo-1531346878377-a5be20888e57?w=800&auto=format&fit=crop&q=80",
            60,
            0
        )
    ]

    cursor.executemany(
        """
        INSERT INTO products (name, slug, description, price, category_id, image_url, stock, is_featured)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        products
    )

    # 4. Seed a Sample Order for John Doe
    cursor.execute(
        """
        INSERT INTO orders (
            order_number, user_id, customer_name, customer_email, customer_phone,
            shipping_address, city, postal_code, country, payment_method,
            subtotal, tax, shipping_fee, total_amount, status, notes
        ) VALUES (
            'ORD-202610-1001', 2, 'John Doe', 'john@example.com', '+1 (555) 234-5678',
            '742 Evergreen Terrace', 'Springfield', '97477', 'United States', 'Credit Card',
            348.00, 27.84, 0.00, 375.84, 'Processing', 'Please leave at front door'
        )
        """
    )
    sample_order_id = cursor.lastrowid

    cursor.execute(
        """
        INSERT INTO order_items (order_id, product_id, product_name, price, quantity, subtotal)
        VALUES (?, 1, 'Sony WH-1000XM5 Wireless Headphones', 348.00, 1, 348.00)
        """,
        (sample_order_id,)
    )


def init_app(app):
    """Register database functions with the Flask app."""
    app.teardown_appcontext(close_db)
    with app.app_context():
        init_db(app)
