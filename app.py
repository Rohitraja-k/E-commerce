"""
Flask E-Commerce Application Entry Point.
Initializes the Flask app, registers blueprints, context processors, filters, and error handlers.
"""

import os
from flask import Flask, render_template, request, jsonify
from database import init_app, query_db
from auth import auth_bp, get_current_user
from shop import shop_bp
from admin import admin_bp
from api import api_bp
import cart_service


def create_app(test_config=None):
    """Application factory for the E-Commerce Flask application."""
    app = Flask(__name__, instance_relative_config=True)

    # Configuration
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", "super-secret-ecommerce-key-2026-xyz"),
        DATABASE=os.path.join(app.root_path, "ecommerce.db"),
    )

    if test_config:
        app.config.update(test_config)

    # Initialize Database
    init_app(app)

    # Register Blueprints
    app.register_blueprint(shop_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp)

    # Global Context Processors for Jinja Templates
    @app.context_processor
    def inject_globals():
        user = get_current_user()
        cart_count = cart_service.get_cart_count()
        nav_categories = query_db("SELECT id, name, slug FROM categories ORDER BY name ASC")
        return dict(
            current_user=user,
            cart_count=cart_count,
            nav_categories=nav_categories
        )

    # Custom Jinja Template Filters
    @app.template_filter("currency")
    def currency_filter(value):
        """Format number as US currency: $1,234.56"""
        try:
            return f"${float(value):,.2f}"
        except (ValueError, TypeError):
            return "$0.00"

    @app.template_filter("datetime_format")
    def datetime_format_filter(value, fmt="%b %d, %Y %I:%M %p"):
        """Format timestamp string into readable date."""
        if not value:
            return ""
        try:
            # Handle standard SQLite timestamp format
            from datetime import datetime
            if isinstance(value, str):
                dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            else:
                dt = value
            return dt.strftime(fmt)
        except Exception:
            return str(value)

    # Error Handlers
    @app.errorhandler(404)
    def page_not_found(e):
        if request.path.startswith("/api/"):
            return jsonify({"success": False, "error": "API route not found"}), 404
        return render_template("404.html"), 404

    @app.errorhandler(403)
    def forbidden(e):
        if request.path.startswith("/api/"):
            return jsonify({"success": False, "error": "Forbidden"}), 403
        return render_template("403.html"), 403

    @app.errorhandler(500)
    def internal_server_error(e):
        if request.path.startswith("/api/"):
            return jsonify({"success": False, "error": "Internal server error"}), 500
        return render_template("500.html"), 500

    return app


app = create_app()

if __name__ == "__main__":
    print("=" * 60)
    print("  ShopZone E-Commerce Store is starting...")
    print("  URL: http://127.0.0.1:5000")
    print("  Default Admin Account : admin@shopzone.com / admin123")
    print("  Default User Account  : john@example.com / user123")
    print("=" * 60)
    app.run(host="127.0.0.1", port=5000, debug=True)
