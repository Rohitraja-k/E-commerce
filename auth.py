"""
Authentication module: Registration, Login, Logout, and Role-Based Access Control.
Includes secure password hashing, input validation, and route decorators.
"""

import re
from functools import wraps
from flask import (
    Blueprint, render_template, request, redirect,
    url_for, flash, session, g
)
from werkzeug.security import generate_password_hash, check_password_hash
from database import query_db, execute_db

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

EMAIL_REGEX = re.compile(r"^[\w\.-]+@[\w\.-]+\.\w+$")
USERNAME_REGEX = re.compile(r"^[a-zA-Z0-9_]{3,30}$")


def get_current_user():
    """Fetch current logged-in user details from database or None."""
    user_id = session.get("user_id")
    if not user_id:
        return None
    user = query_db(
        "SELECT id, username, email, full_name, role, created_at FROM users WHERE id = ?",
        (user_id,),
        one=True
    )
    return user


def login_required(f):
    """Decorator to require authenticated user."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please sign in to access this page.", "warning")
            return redirect(url_for("auth.login", next=request.url))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """Decorator to require admin role."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = session.get("user_id")
        if not user_id:
            flash("Administrator login required.", "warning")
            return redirect(url_for("auth.login", next=request.url))
        
        user = query_db("SELECT role FROM users WHERE id = ?", (user_id,), one=True)
        if not user or user["role"] != "admin":
            flash("Access denied. Administrator privileges are required.", "danger")
            return redirect(url_for("shop.index"))
        return f(*args, **kwargs)
    return decorated_function


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    """User registration with rigorous validation and password hashing."""
    if session.get("user_id"):
        return redirect(url_for("shop.index"))

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        errors = []

        # Validation
        if not full_name:
            errors.append("Full name is required.")
        if not username or not USERNAME_REGEX.match(username):
            errors.append("Username must be 3-30 characters long and contain only letters, numbers, and underscores.")
        if not email or not EMAIL_REGEX.match(email):
            errors.append("A valid email address is required.")
        if len(password) < 6:
            errors.append("Password must be at least 6 characters long.")
        if password != confirm_password:
            errors.append("Passwords do not match.")

        # Check existing user
        if not errors:
            existing_user = query_db(
                "SELECT id, username, email FROM users WHERE username = ? OR email = ?",
                (username, email),
                one=True
            )
            if existing_user:
                if existing_user["username"].lower() == username.lower():
                    errors.append("Username is already taken.")
                if existing_user["email"].lower() == email.lower():
                    errors.append("Email is already registered.")

        if errors:
            for error in errors:
                flash(error, "danger")
            return render_template(
                "register.html",
                full_name=full_name,
                username=username,
                email=email
            )

        # Hash password and insert user
        password_hash = generate_password_hash(password)
        try:
            res = execute_db(
                """
                INSERT INTO users (username, email, password_hash, full_name, role)
                VALUES (?, ?, ?, ?, 'user')
                """,
                (username, email, password_hash, full_name)
            )
            flash("Registration successful! You can now log in.", "success")
            return redirect(url_for("auth.login"))
        except Exception as e:
            flash(f"Error registering user: {str(e)}", "danger")

    return render_template("register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """User login supporting email or username."""
    if session.get("user_id"):
        return redirect(url_for("shop.index"))

    next_url = request.args.get("next")

    if request.method == "POST":
        login_id = request.form.get("login_id", "").strip()
        password = request.form.get("password", "")

        if not login_id or not password:
            flash("Please enter both username/email and password.", "danger")
            return render_template("login.html", login_id=login_id, next=next_url)

        # Look up user by username OR email
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
            flash("Invalid username/email or password.", "danger")
            return render_template("login.html", login_id=login_id, next=next_url)

        # Save session
        session["user_id"] = user["id"]
        session["username"] = user["username"]
        session["full_name"] = user["full_name"]
        session["role"] = user["role"]
        session.permanent = True

        flash(f"Welcome back, {user['full_name']}!", "success")

        target = next_url if next_url and next_url.startswith("/") else url_for("shop.index")
        return redirect(target)

    return render_template("login.html", next=next_url)


@auth_bp.route("/logout")
def logout():
    """Sign the user out while preserving guest cart if desired."""
    cart_backup = session.get("cart")
    session.clear()
    if cart_backup:
        session["cart"] = cart_backup
    flash("You have been successfully logged out.", "info")
    return redirect(url_for("shop.index"))
