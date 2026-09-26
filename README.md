# MemoryBell

Never forget what matters. Store birthdays, anniversaries & special dates in one place and get reminded via **SMS** and **Phone Calls**.

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![Flask](https://img.shields.io/badge/Flask-3.0-green)
![MongoDB](https://img.shields.io/badge/MongoDB-Atlas-brightgreen)
![Twilio](https://img.shields.io/badge/Twilio-SMS%20%26%20Calls-red)

## Features

### Reminders
- **Texts to your own phone**: every reminder goes to the number on your account, so you're the one who remembers.
- **Text them on the day (optional)**: add the other person's number and a message, and MemoryBell texts it to them on the day, signed with your name.
- **Two-part live preview**: while you fill in the form, see exactly what you'll get and what they'll get, and send yourself a test text of either (3 per hour).
- **Smart timing**: on the day, or 1, 3 or 7 days before, including dates that cross the new year.
- **Years and milestones**: add the year to see "turns 60" or "25th anniversary" in the text and on the dashboard.
- **Notes and gift ideas**: a private note that only appears in your reminder.
- **Quick-start presets**: Mom's birthday, anniversary, best friend and more.
- **Pause, skip or duplicate**: skip this year, pause until you turn it back on, or copy a reminder as a starting point.
- **Phone calls and WhatsApp**: a voice call (Polly Neural) or WhatsApp instead of SMS.

### Dashboard and history
- **Your year at a glance**: a 12-month strip of every date, which opens on the current month.
- **Delivery tracking**: History shows Twilio's real result for each text (Delivered, Pending or Failed), grouped by month, with search and filters.
- **Plain-English failures**: each failure explains why it happened (for example "Blocked by the mobile network") and how to fix it.
- **Resend and refresh**: resend a failed text (3 per hour), or ask Twilio for the latest statuses.
- **Export your data**: download your reminders as CSV, or everything as JSON.

### Account and security
- **OTP signup**: phone verification with Twilio Verify.
- **Secure sessions**: Bcrypt passwords, Flask-Login and CSRF protection.
- **Signed webhooks**: Twilio status callbacks are checked against `X-Twilio-Signature`.
- **Fair usage**: up to 5 reminders per account, with no duplicate sends in a day.
- **Light and dark themes**.

## Tech Stack

- **Backend**: Flask (Python)
- **Database**: MongoDB Atlas (PyMongo)
- **SMS/Calls**: Twilio (REST API, Verify, TwiML)
- **Auth**: Flask-Login + Flask-Bcrypt
- **Security**: Flask-WTF CSRFProtect
- **Frontend**: TailwindCSS (CDN, no build step), vanilla JS
- **Deployment**: Vercel / Docker + Gunicorn
- **Cron**: cron-job.org (8 AM IST daily)

## Project Structure

```
MemoryBell/
├── app/
│   ├── __init__.py            # App factory, extensions, indexes
│   ├── models/
│   │   └── user.py            # User model for Flask-Login
│   ├── routes/
│   │   ├── auth.py            # Signup (OTP), login, logout
│   │   ├── dashboard.py       # Dashboard and year view
│   │   ├── reminders.py       # Create/edit/duplicate/pause, test texts (5 limit)
│   │   ├── history.py         # Delivery history, refresh, resend
│   │   ├── profile.py         # Profile, password, data export
│   │   ├── twilio_hooks.py    # Twilio delivery-status webhook
│   │   ├── cron.py            # Cron trigger endpoint
│   │   └── home.py            # Homepage
│   ├── services/
│   │   ├── scheduler.py       # Reminder matching, message text, sending
│   │   ├── twilio_service.py  # Twilio SMS, call, WhatsApp, OTP
│   │   ├── delivery.py        # Delivery statuses and error explanations
│   │   └── dates.py           # Date, milestone and pause helpers
│   ├── static/
│   │   ├── css/app.css        # Design tokens and components
│   │   └── js/sms-preview.js  # Live SMS preview (mirrors scheduler.py)
│   └── templates/             # Jinja2 templates
├── config.py                  # App configuration
├── requirements.txt           # Python dependencies
├── Dockerfile                 # Container build
├── vercel.json                # Vercel config
└── run.py                     # Dev server entry
```

## Setup

### 1. Clone & Install

```bash
git clone https://github.com/bishalde/memorybell.git
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
# Optional: your deployed URL. Turns on live delivery reports from Twilio.
PUBLIC_BASE_URL=https://your-domain.com
```

Without `PUBLIC_BASE_URL`, texts still send. Delivery statuses then stay "Pending" until you press **Refresh statuses** on the History page.

### 3. Run

```bash
python run.py
```

Then open [http://localhost:8080](http://localhost:8080).

Or with Docker:

```bash
docker build -t memorybell .
docker run -p 8080:8080 --env-file .env memorybell
```

### 4. Setup Cron

Use [cron-job.org](https://cron-job.org) to hit:

```
GET https://your-domain.com/api/cron/check-reminders?secret=your-cron-secret
```

Schedule: `30 2 * * *` (8:00 AM IST daily)

### 5. Delivery reports (optional)

With `PUBLIC_BASE_URL` set, every text asks Twilio to report its status to:

```
POST https://your-domain.com/api/twilio/status
```

You don't need to set anything in the Twilio console. The URL is sent with each message, and requests are verified with your auth token.

> **Texting Indian numbers:** Indian networks filter texts from unregistered international senders (DLT). If History shows "Blocked by the mobile network" (error 30007), use a DLT-registered sender or keep your Twilio balance positive.

## Live Demo

[https://memorybell.vercel.app](https://memorybell.vercel.app)

## Author

Made with love by [Bishal](https://bishalde.vercel.app/)

- [Source code](https://github.com/bishalde/memorybell)
- [GitHub](https://github.com/bishalde)
- [LinkedIn](https://www.linkedin.com/in/bishalde/)
- [Website](https://bishalde.vercel.app/)
