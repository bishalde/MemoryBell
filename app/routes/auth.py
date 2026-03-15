from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required
from app import db, bcrypt
from app.models.user import User

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        phone_number = request.form.get("phone_number", "").strip()
        whatsapp_number = request.form.get("whatsapp_number", "").strip()

        if not name or not email or not password:
            flash("Name, email and password are required.", "error")
            return redirect(url_for("auth.signup"))

        if db.users.find_one({"email": email}):
            flash("Email already registered.", "error")
            return redirect(url_for("auth.signup"))

        password_hash = bcrypt.generate_password_hash(password).decode("utf-8")

        user_data = {
            "name": name,
            "email": email,
            "password_hash": password_hash,
            "phone_number": phone_number,
            "whatsapp_number": whatsapp_number or phone_number,
            "timezone": "UTC",
            "created_at": datetime.utcnow(),
        }

        result = db.users.insert_one(user_data)
        user_data["_id"] = result.inserted_id
        login_user(User(user_data))
        flash("Account created successfully!", "success")
        return redirect(url_for("dashboard.index"))

    return render_template("signup.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        user_data = db.users.find_one({"email": email})
        if user_data and bcrypt.check_password_hash(user_data["password_hash"], password):
            login_user(User(user_data))
            flash("Logged in successfully!", "success")
            return redirect(url_for("dashboard.index"))

        flash("Invalid email or password.", "error")
        return redirect(url_for("auth.login"))

    return render_template("login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out.", "success")
    return redirect(url_for("auth.login"))
