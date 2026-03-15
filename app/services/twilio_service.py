from xml.sax.saxutils import escape
from twilio.rest import Client
from config import Config


def get_twilio_client():
    return Client(Config.TWILIO_ACCOUNT_SID, Config.TWILIO_AUTH_TOKEN)


def send_otp(to_number):
    """Send OTP via Twilio Verify."""
    client = get_twilio_client()
    verification = client.verify.v2.services(
        Config.TWILIO_VERIFY_SID
    ).verifications.create(to=to_number, channel="sms")
    return verification.status


def check_otp(to_number, code):
    """Verify OTP code via Twilio Verify."""
    client = get_twilio_client()
    try:
        check = client.verify.v2.services(
            Config.TWILIO_VERIFY_SID
        ).verification_checks.create(to=to_number, code=code)
        return check.status == "approved"
    except Exception:
        return False


def send_whatsapp_reminder(to_number, message):
    client = get_twilio_client()
    msg = client.messages.create(
        from_=f"whatsapp:{Config.TWILIO_WHATSAPP_NUMBER}",
        body=message,
        to=f"whatsapp:{to_number}",
    )
    return msg.sid


def send_sms_reminder(to_number, message):
    client = get_twilio_client()
    msg = client.messages.create(
        from_=Config.TWILIO_PHONE_NUMBER,
        body=message,
        to=to_number,
    )
    return msg.sid


def send_call_reminder(to_number, ssml_body):
    """Send a phone call with SSML content using Polly neural voice."""
    client = get_twilio_client()
    twiml = (
        '<Response>'
        '<Say voice="Polly.Joanna-Neural">'
        f'{ssml_body}'
        '</Say>'
        '<Pause length="1"/>'
        '<Say voice="Polly.Joanna-Neural">'
        'If you would like to hear this again, stay on the line.'
        '</Say>'
        '<Pause length="2"/>'
        '<Say voice="Polly.Joanna-Neural">'
        f'{ssml_body}'
        '</Say>'
        '<Pause length="1"/>'
        '<Say voice="Polly.Joanna-Neural">'
        'Thank you for using Memory Bell. Have a wonderful day! Goodbye.'
        '</Say>'
        '</Response>'
    )
    call = client.calls.create(
        twiml=twiml,
        to=to_number,
        from_=Config.TWILIO_PHONE_NUMBER,
    )
    return call.sid
