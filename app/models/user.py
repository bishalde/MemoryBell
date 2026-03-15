from flask_login import UserMixin
from app import login_manager, db


class User(UserMixin):
    def __init__(self, user_data):
        self.id = str(user_data["_id"])
        self.name = user_data.get("name", "")
        self.email = user_data.get("email", "")
        self.phone_number = user_data.get("phone_number", "")
        self.whatsapp_number = user_data.get("whatsapp_number", "")
        self.timezone = user_data.get("timezone", "UTC")


@login_manager.user_loader
def load_user(user_id):
    from bson.objectid import ObjectId
    user_data = db.users.find_one({"_id": ObjectId(user_id)})
    if user_data:
        return User(user_data)
    return None
