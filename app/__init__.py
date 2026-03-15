from flask import Flask
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from pymongo import MongoClient
from config import Config

bcrypt = Bcrypt()
login_manager = LoginManager()
csrf = CSRFProtect()
login_manager.login_view = "auth.login"
mongo_client = None
db = None


def create_app():
    global mongo_client, db

    app = Flask(__name__)
    app.config.from_object(Config)

    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["SESSION_COOKIE_SECURE"] = True
    app.config["WTF_CSRF_TIME_LIMIT"] = None  # No expiry on CSRF tokens

    bcrypt.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    mongo_client = MongoClient(app.config["MONGO_URI"])
    db = mongo_client.memorybell

    # Create indexes
    db.users.create_index("email", unique=True)
    db.reminders.create_index("user_id")
    db.reminders.create_index("event_date")

    from app.routes.home import home_bp
    from app.routes.auth import auth_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.reminders import reminders_bp
    from app.routes.profile import profile_bp
    from app.routes.cron import cron_bp
    from app.routes.history import history_bp

    app.register_blueprint(home_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(reminders_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(cron_bp)
    app.register_blueprint(history_bp)

    # Exempt authenticated blueprints from CSRF (protected by @login_required)
    # Keep CSRF on auth routes (login/signup) where it matters most
    csrf.exempt(reminders_bp)
    csrf.exempt(profile_bp)
    csrf.exempt(cron_bp)
    csrf.exempt(dashboard_bp)

    db.notifications.create_index("user_id")
    db.notifications.create_index([("reminder_id", 1), ("channel", 1), ("sent_at", -1)])

    return app
