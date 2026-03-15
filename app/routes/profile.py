from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user, logout_user
from bson.objectid import ObjectId
from app import db, bcrypt

profile_bp = Blueprint("profile", __name__)


@profile_bp.route("/profile", methods=["GET", "POST"])
@login_required
def index():
    if request.method == "POST":
        update_data = {
            "name": request.form.get("name", "").strip(),
            "country_code": request.form.get("country_code", "+1").strip(),
            "phone_number": request.form.get("phone_number", "").strip(),
            "whatsapp_number": request.form.get("whatsapp_number", "").strip(),
            "timezone": request.form.get("timezone", "UTC"),
        }

        db.users.update_one(
            {"_id": ObjectId(current_user.id)},
            {"$set": update_data},
        )
        flash("Profile updated!", "success")
        return redirect(url_for("profile.index"))

    user_data = db.users.find_one({"_id": ObjectId(current_user.id)})
    user_id = ObjectId(current_user.id)
    total_reminders = db.reminders.count_documents({"user_id": user_id})
    total_notifications = db.notifications.count_documents({"user_id": user_id, "status": "sent"})
    return render_template("profile.html", user=user_data, total_reminders=total_reminders, total_notifications=total_notifications)


@profile_bp.route("/profile/change-password", methods=["POST"])
@login_required
def change_password():
    current_password = request.form.get("current_password", "")
    new_password = request.form.get("new_password", "")

    user_data = db.users.find_one({"_id": ObjectId(current_user.id)})

    if not bcrypt.check_password_hash(user_data["password_hash"], current_password):
        flash("Current password is incorrect.", "error")
        return redirect(url_for("profile.index"))

    if len(new_password) < 6:
        flash("New password must be at least 6 characters.", "error")
        return redirect(url_for("profile.index"))

    new_hash = bcrypt.generate_password_hash(new_password).decode("utf-8")
    db.users.update_one(
        {"_id": ObjectId(current_user.id)},
        {"$set": {"password_hash": new_hash}},
    )
    flash("Password changed!", "success")
    return redirect(url_for("profile.index"))


@profile_bp.route("/profile/delete", methods=["POST"])
@login_required
def delete_account():
    user_id = ObjectId(current_user.id)
    db.reminders.delete_many({"user_id": user_id})
    db.users.delete_one({"_id": user_id})
    logout_user()
    flash("Account deleted.", "success")
    return redirect(url_for("auth.login"))
