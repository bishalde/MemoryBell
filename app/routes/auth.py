from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_user, logout_user, login_required
from app import db, bcrypt
from app.models.user import User
from app.services.twilio_service import send_otp, check_otp

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        country_code = request.form.get("country_code", "+91")
        phone_number = request.form.get("phone_number", "").strip()
        whatsapp_number = request.form.get("whatsapp_number", "").strip()

        if not name or not email or not password or not phone_number:
            flash("Name, email, password and phone number are required.", "error")
            return redirect(url_for("auth.signup"))

        if len(password) < 6:
            flash("Password must be at least 6 characters.", "error")
            return redirect(url_for("auth.signup"))

        if db.users.find_one({"email": email}):
            flash("Email already registered.", "error")
            return redirect(url_for("auth.signup"))

        full_phone = country_code + phone_number if not phone_number.startswith("+") else phone_number

        try:
            send_otp(full_phone)
        except Exception as e:
            flash(f"Could not send OTP. Please check your phone number. ({e})", "error")
            return redirect(url_for("auth.signup"))

        session["signup_data"] = {
            "name": name,
            "email": email,
            "password": password,
            "country_code": country_code,
            "phone_number": phone_number,
            "whatsapp_number": whatsapp_number,
            "full_phone": full_phone,
        }

        flash("OTP sent to your phone number. Please verify.", "success")
        return redirect(url_for("auth.verify_otp"))

    return render_template("signup.html")


@auth_bp.route("/verify-otp", methods=["GET", "POST"])
def verify_otp():
    signup_data = session.get("signup_data")
    if not signup_data:
        flash("Please sign up first.", "error")
        return redirect(url_for("auth.signup"))

    if request.method == "POST":
        code = request.form.get("otp_code", "").strip()
        full_phone = signup_data["full_phone"]

        if not code or len(code) != 6:
            flash("Please enter the 6-digit OTP code.", "error")
            return redirect(url_for("auth.verify_otp"))

        if not check_otp(full_phone, code):
            flash("Invalid or expired OTP. Please try again.", "error")
            return redirect(url_for("auth.verify_otp"))

        password_hash = bcrypt.generate_password_hash(signup_data["password"]).decode("utf-8")

        user_data = {
            "name": signup_data["name"],
            "email": signup_data["email"],
            "password_hash": password_hash,
            "country_code": signup_data["country_code"],
            "phone_number": signup_data["phone_number"],
            "whatsapp_number": signup_data["whatsapp_number"] or signup_data["phone_number"],
            "phone_verified": True,
            "timezone": "UTC",
            "created_at": datetime.utcnow(),
        }

        result = db.users.insert_one(user_data)
        user_data["_id"] = result.inserted_id
        session.pop("signup_data", None)
        login_user(User(user_data))
        flash("Account created successfully! Phone verified.", "success")
        return redirect(url_for("dashboard.index"))

    return render_template("verify_otp.html", phone=signup_data["full_phone"])


@auth_bp.route("/resend-otp", methods=["POST"])
def resend_otp():
    signup_data = session.get("signup_data")
    if not signup_data:
        flash("Please sign up first.", "error")
        return redirect(url_for("auth.signup"))

    try:
        send_otp(signup_data["full_phone"])
        flash("OTP resent successfully.", "success")
    except Exception:
        flash("Could not resend OTP. Please try again.", "error")

    return redirect(url_for("auth.verify_otp"))


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
