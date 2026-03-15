import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "fallback-secret-key")
    MONGO_URI = os.getenv("MONGO_URI")
    TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
    TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
    TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER")
    TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")
    CRON_SECRET = os.getenv("CRON_SECRET", "")
    TWILIO_VERIFY_SID = os.getenv("TWILIO_VERIFY_SID", "")
    MAX_REMINDERS_PER_USER = 5
