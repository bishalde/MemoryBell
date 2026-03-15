from flask import Flask
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from pymongo import MongoClient
from config import Config

bcrypt = Bcrypt()
login_manager = LoginManager()
login_manager.login_view = "auth.login"
mongo_client = None
db = None


def create_app():
    global mongo_client, db

    app = Flask(__name__)
    app.config.from_object(Config)

    bcrypt.init_app(app)
    login_manager.init_app(app)

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

    app.register_blueprint(home_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(reminders_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(cron_bp)

    return app
