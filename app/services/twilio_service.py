from twilio.rest import Client
from config import Config


def get_twilio_client():
    return Client(Config.TWILIO_ACCOUNT_SID, Config.TWILIO_AUTH_TOKEN)


def send_whatsapp_reminder(to_number, message):
    client = get_twilio_client()
    msg = client.messages.create(
        from_=f"whatsapp:{Config.TWILIO_WHATSAPP_NUMBER}",
        body=message,
        to=f"whatsapp:{to_number}",
    )
    return msg.sid


def send_call_reminder(to_number, message):
    client = get_twilio_client()
    call = client.calls.create(
        twiml=f"<Response><Say voice='alice'>{message}</Say></Response>",
        to=to_number,
        from_=Config.TWILIO_PHONE_NUMBER,
    )
    return call.sid
