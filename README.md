# MemoryBell

Never forget what matters. Store birthdays, anniversaries & special dates in one place and get reminded via **SMS** and **Phone Calls**.

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![Flask](https://img.shields.io/badge/Flask-3.0-green)
![MongoDB](https://img.shields.io/badge/MongoDB-Atlas-brightgreen)
![Twilio](https://img.shields.io/badge/Twilio-SMS%20%26%20Calls-red)

## Features

- **SMS Reminders** - Get clear, well-formatted SMS reminders for your important dates
- **Phone Call Reminders** - Automated voice call reminders with natural-sounding speech (Polly Neural)
- **Smart Timing** - Choose to be reminded same day, 1 day, 3 days, or 7 days before
- **OTP Verification** - Phone number verification via Twilio Verify during signup
- **CSRF Protection** - All forms protected against cross-site request forgery
- **Secure Authentication** - Bcrypt password hashing with Flask-Login sessions
- **Beautiful Dashboard** - Clean, modern UI to manage all your reminders
- **Notification History** - Track all sent reminders with delivery status
- **Profile Management** - Update your info, change password, manage timezone
- **Deduplication** - Smart dedup prevents duplicate notifications
- **5 Reminder Limit** - Fair usage with up to 5 reminders per user

## Tech Stack

- **Backend**: Flask (Python)
- **Database**: MongoDB Atlas (PyMongo)
- **SMS/Calls**: Twilio (REST API, Verify, TwiML)
- **Auth**: Flask-Login + Flask-Bcrypt
- **Security**: Flask-WTF CSRFProtect
- **Frontend**: TailwindCSS (CDN)
- **Deployment**: Vercel / Docker + Gunicorn
- **Cron**: cron-job.org (8 AM IST daily)

## Project Structure

```
MemoryBell/
├── app/
│   ├── __init__.py          # App factory, extensions
│   ├── models/
│   │   └── user.py          # User model for Flask-Login
│   ├── routes/
│   │   ├── auth.py          # Signup (OTP), login, logout
│   │   ├── dashboard.py     # Main dashboard
│   │   ├── reminders.py     # CRUD reminders (5 limit)
│   │   ├── profile.py       # Profile & password
│   │   ├── cron.py          # Cron trigger endpoint
│   │   ├── history.py       # Notification history
│   │   └── home.py          # Homepage
│   ├── services/
│   │   ├── twilio_service.py # Twilio SMS, Call, OTP
│   │   └── scheduler.py     # Reminder matching & sending
│   └── templates/           # Jinja2 templates
├── config.py                # App configuration
├── requirements.txt         # Python dependencies
├── Dockerfile               # Container build
├── vercel.json              # Vercel config
└── run.py                   # Dev server entry
```

## Setup

### 1. Clone & Install

```bash
git clone https://github.com/bishalde/MemoryBell.git
cd MemoryBell
pip install -r requirements.txt
```

### 2. Environment Variables

Create a `.env` file:

```env
SECRET_KEY=your-secret-key
MONGO_URI=mongodb+srv://...
TWILIO_ACCOUNT_SID=ACxxxxxxxx
TWILIO_AUTH_TOKEN=xxxxxxxx
TWILIO_PHONE_NUMBER=+1xxxxxxxxxx
TWILIO_WHATSAPP_NUMBER=+1xxxxxxxxxx
TWILIO_VERIFY_SID=VAxxxxxxxx
CRON_SECRET=your-cron-secret
```

### 3. Run

```bash
python run.py
```

Or with Docker:

```bash
docker build -t memorybell .
docker run -p 5000:5000 --env-file .env memorybell
```

### 4. Setup Cron

Use [cron-job.org](https://cron-job.org) to hit:

```
GET https://your-domain.com/api/cron/check-reminders?secret=your-cron-secret
```

Schedule: `30 2 * * *` (8:00 AM IST daily)

## Live Demo

[https://memorybell.vercel.app](https://memorybell.vercel.app)

## Author

Made with love by [Bishal](https://bishalde.vercel.app/)

- [GitHub](https://github.com/bishalde)
- [LinkedIn](https://www.linkedin.com/in/bishalde/)
- [Website](https://bishalde.vercel.app/)
