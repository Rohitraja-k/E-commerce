"""
Automated Test Suite for Flask E-Commerce Application.
Tests authentication, role permissions, catalog, shopping cart, checkout,
admin product CRUD, admin orders, and REST API endpoints.
"""

import os
import unittest
import tempfile
import json
from app import create_app
import database


class EcommerceTestCase(unittest.TestCase):
    def setUp(self):
        """Create temporary test database and test Flask client."""
        self.db_fd, self.db_path = tempfile.mkstemp(suffix=".db")
        self.app = create_app({
            "TESTING": True,
            "DATABASE": self.db_path,
            "SECRET_KEY": "test-secret-key"
        })
        self.client = self.app.test_client()

        with self.app.app_context():
            database.init_db()

    def tearDown(self):
        """Clean up temporary test database."""
        os.close(self.db_fd)
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    # ---------------------------------------------------------
    # Helper Methods
    # ---------------------------------------------------------
    def login(self, username, password):
        return self.client.post("/auth/login", data={
            "login_id": username,
            "password": password
        }, follow_redirects=True)

    def logout(self):
        return self.client.get("/auth/logout", follow_redirects=True)

    # ---------------------------------------------------------
    # 1. Storefront & Catalog Tests
    # ---------------------------------------------------------
    def test_homepage_loads(self):
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"ShopZone", res.data)
        self.assertIn(b"Sony WH-1000XM5", res.data)

    def test_products_catalog_and_filter(self):
        res = self.client.get("/products")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"All Products", res.data)

        # Filter by category
        res_cat = self.client.get("/products?category=electronics")
        self.assertEqual(res_cat.status_code, 200)
        self.assertIn(b"Sony WH-1000XM5", res_cat.data)

        # Search by keyword
        res_search = self.client.get("/products?search=Keyboard")
        self.assertEqual(res_search.status_code, 200)
        self.assertIn(b"Keychron", res_search.data)

    def test_product_detail_page(self):
        res = self.client.get("/product/1")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Sony WH-1000XM5", res.data)
        self.assertIn(b"Add to Cart", res.data)

    # ---------------------------------------------------------
    # 2. Authentication & Roles Tests
    # ---------------------------------------------------------
    def test_user_registration(self):
        res = self.client.post("/auth/register", data={
            "full_name": "Alice Smith",
            "username": "alicesmith",
            "email": "alice@example.com",
            "password": "password123",
            "confirm_password": "password123"
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Registration successful", res.data)

        # Test duplicate registration error
        res_dup = self.client.post("/auth/register", data={
            "full_name": "Alice Smith",
            "username": "alicesmith",
            "email": "alice@example.com",
            "password": "password123",
            "confirm_password": "password123"
        }, follow_redirects=True)
        self.assertIn(b"already taken", res_dup.data)

    def test_user_login_and_logout(self):
        # Successful login with user credentials
        res = self.login("john@example.com", "user123")
        self.assertIn(b"Welcome back, John Doe", res.data)

        # Logout
        res_out = self.logout()
        self.assertIn(b"successfully logged out", res_out.data)

    def test_invalid_login(self):
        res = self.login("admin@shopzone.com", "wrongpassword")
        self.assertIn(b"Invalid username/email or password", res.data)

    def test_role_based_access(self):
        # 1. Guest trying to access admin dashboard -> redirected to login
        res_guest = self.client.get("/admin/dashboard", follow_redirects=True)
        self.assertIn(b"Administrator login required", res_guest.data)

        # 2. Regular user trying to access admin dashboard -> access denied
        self.login("john@example.com", "user123")
        res_user = self.client.get("/admin/dashboard", follow_redirects=True)
        self.assertIn(b"Access denied. Administrator privileges are required.", res_user.data)
        self.logout()

        # 3. Admin user -> successfully views admin dashboard
        self.login("admin@shopzone.com", "admin123")
        res_admin = self.client.get("/admin/dashboard")
        self.assertEqual(res_admin.status_code, 200)
        self.assertIn(b"Store Overview", res_admin.data)
        self.logout()

    # ---------------------------------------------------------
    # 3. Shopping Cart Tests
    # ---------------------------------------------------------
    def test_cart_workflow(self):
        # Add item to cart
        res_add = self.client.post("/cart/add/1", data={"quantity": 2}, follow_redirects=True)
        self.assertEqual(res_add.status_code, 200)

        # View cart
        res_cart = self.client.get("/cart")
        self.assertEqual(res_cart.status_code, 200)
        self.assertIn(b"Sony WH-1000XM5", res_cart.data)

        # Update quantity
        res_update = self.client.post("/cart/update/1", data={"quantity": 3}, follow_redirects=True)
        self.assertEqual(res_update.status_code, 200)

        # Remove item
        res_remove = self.client.post("/cart/remove/1", follow_redirects=True)
        self.assertEqual(res_remove.status_code, 200)
        self.assertIn(b"Your cart is empty", res_remove.data)

    # ---------------------------------------------------------
    # 4. Checkout and Stock Deduction Tests
    # ---------------------------------------------------------
    def test_checkout_and_stock_reduction(self):
        # Add product 1 (Sony Headphones, initial stock = 18)
        self.client.post("/cart/add/1", data={"quantity": 2}, follow_redirects=True)

        # Place Order via Checkout form
        res_checkout = self.client.post("/checkout", data={
            "customer_name": "Test Customer",
            "customer_email": "customer@test.com",
            "customer_phone": "1234567890",
            "shipping_address": "123 Main St",
            "city": "Metropolis",
            "postal_code": "10001",
            "country": "United States",
            "payment_method": "Credit Card",
            "notes": "Fragile shipment"
        }, follow_redirects=True)

        self.assertEqual(res_checkout.status_code, 200)
        self.assertIn(b"Thank You for Your Order!", res_checkout.data)
        self.assertIn(b"ORD-", res_checkout.data)

        # Verify stock was reduced from 18 to 16 in database
        with self.app.app_context():
            prod = database.query_db("SELECT stock FROM products WHERE id = 1", one=True)
            self.assertEqual(prod["stock"], 16)

    # ---------------------------------------------------------
    # 5. Admin Product CRUD Tests
    # ---------------------------------------------------------
    def test_admin_product_crud(self):
        self.login("admin@shopzone.com", "admin123")

        # 1. Create Product
        res_create = self.client.post("/admin/products/new", data={
            "name": "Noise Cancelling Earbuds Pro",
            "description": "True wireless earbuds with active ANC and 32hr battery.",
            "price": "149.99",
            "stock": "45",
            "category_id": "1",
            "image_url": "https://images.unsplash.com/photo-1590658268037-6bf12165a8df",
            "is_featured": "1"
        }, follow_redirects=True)
        self.assertIn(b"created successfully", res_create.data)

        # Verify product created
        with self.app.app_context():
            new_p = database.query_db("SELECT * FROM products WHERE name = 'Noise Cancelling Earbuds Pro'", one=True)
            self.assertIsNotNone(new_p)
            new_p_id = new_p["id"]
            self.assertEqual(new_p["stock"], 45)

        # 2. Edit Product
        res_edit = self.client.post(f"/admin/products/{new_p_id}/edit", data={
            "name": "Noise Cancelling Earbuds Pro Max",
            "description": "Updated premium sound edition.",
            "price": "179.99",
            "stock": "50",
            "category_id": "1",
            "image_url": "https://images.unsplash.com/photo-1590658268037-6bf12165a8df",
            "is_featured": "1"
        }, follow_redirects=True)
        self.assertIn(b"updated successfully", res_edit.data)

        with self.app.app_context():
            updated_p = database.query_db("SELECT name, price FROM products WHERE id = ?", (new_p_id,), one=True)
            self.assertEqual(updated_p["name"], "Noise Cancelling Earbuds Pro Max")
            self.assertEqual(updated_p["price"], 179.99)

        # 3. Delete Product
        res_del = self.client.post(f"/admin/products/{new_p_id}/delete", follow_redirects=True)
        self.assertIn(b"was deleted", res_del.data)

        with self.app.app_context():
            deleted_p = database.query_db("SELECT id FROM products WHERE id = ?", (new_p_id,), one=True)
            self.assertIsNone(deleted_p)

        self.logout()

    # ---------------------------------------------------------
    # 6. Admin Order Status Update Tests
    # ---------------------------------------------------------
    def test_admin_update_order_status(self):
        self.login("admin@shopzone.com", "admin123")

        # Update order 1 status to Shipped
        res = self.client.post("/admin/orders/1/status", data={
            "status": "Shipped"
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"status updated to &#39;Shipped&#39;", res.data)

        with self.app.app_context():
            order = database.query_db("SELECT status FROM orders WHERE id = 1", one=True)
            self.assertEqual(order["status"], "Shipped")

        self.logout()

    # ---------------------------------------------------------
    # 7. REST API Tests
    # ---------------------------------------------------------
    def test_api_products(self):
        res = self.client.get("/api/products")
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertTrue(data["success"])
        self.assertGreater(data["count"], 0)

        # Single product
        res_single = self.client.get("/api/products/1")
        self.assertEqual(res_single.status_code, 200)
        single_data = json.loads(res_single.data)
        self.assertEqual(single_data["data"]["name"], "Sony WH-1000XM5 Wireless Headphones")

    def test_api_cart(self):
        # Add to cart via API
        res_add = self.client.post("/api/cart/add", json={
            "product_id": 2,
            "quantity": 1
        })
        self.assertEqual(res_add.status_code, 200)
        data_add = json.loads(res_add.data)
        self.assertTrue(data_add["success"])
        self.assertEqual(data_add["cart_count"], 1)

        # Get cart via API
        res_cart = self.client.get("/api/cart")
        self.assertEqual(res_cart.status_code, 200)
        cart_data = json.loads(res_cart.data)
        self.assertEqual(len(cart_data["data"]["items"]), 1)

        # Clear cart via API
        res_clear = self.client.post("/api/cart/clear")
        self.assertEqual(res_clear.status_code, 200)

    def test_api_categories(self):
        res = self.client.get("/api/categories")
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertTrue(data["success"])
        self.assertEqual(len(data["data"]), 4)

    def test_api_auth_login(self):
        res = self.client.post("/api/auth/login", json={
            "login_id": "admin@shopzone.com",
            "password": "admin123"
        })
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertTrue(data["success"])
        self.assertEqual(data["user"]["role"], "admin")


if __name__ == "__main__":
    unittest.main()
