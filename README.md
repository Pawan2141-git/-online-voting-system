Online Voting Platform
A secure, AI‑enhanced web application for creating and running digital elections. It supports email verification, optional two‑factor authentication, real‑time fraud detection, admin dashboards, result exports (CSV / PDF), interactive charts, and a Google Gemini chatbot for instant help.

Table of Contents
Features
Tech Stack
Getting Started
Prerequisites
Installation
Configuration
Database Setup
Create Admin User
Run the App
Usage
Testing
Docker
Contributing
License
Features
Email verification – voters must confirm their email before logging in.
Optional 2FA – admins (or any user) can enable OTP via email or authenticator app.
Rate limiting – protects login and chatbot endpoints (default 5 requests / minute per IP).
Fraud detection – Isolation Forest flags abnormal IPs, rapid submissions, or duplicate voter hashes.
Admin dashboard – create elections, manage candidates, import/export voters (CSV), view audit logs.
Result export – download CSV, styled PDF (WeasyPrint), and view Chart.js visualizations.
AI chatbot – floating widget powered by Google Gemini answers FAQs in real time.
Responsive UI – Bootstrap 5, mobile‑first, WCAG‑AA accessible.
Internationalisation – ready for Flask‑Babel (multi‑language support).
Docker ready – one‑click container deployment.
Tech Stack
Layer	Technology
Backend	Python 3.12, Flask, SQLAlchemy, Flask‑Login, Flask‑WTF, Flask‑Migrate, Flask‑Limiter, Flask‑Mail
Database	SQLite (dev) – easily switch to PostgreSQL/MySQL via DATABASE_URL
AI	Google Gemini (gemini-pro) via HTTP client
Frontend	HTML5, Bootstrap 5, Chart.js, vanilla JS (chat widget)
PDFs	WeasyPrint
Containerisation	Docker
Getting Started
Prerequisites
Python 3.12+
Git
(Optional) Docker
Installation
bash


git clone https://github.com/your‑username/online‑voting‑platform.git
cd online-voting-platform
python -m venv venv
venv\Scripts\activate   # Windows
# source venv/bin/activate   # macOS/Linux
pip install -r requirements.txt
Configuration
Create a .env file in the project root (or export variables in your shell). Example:

dotenv


# Flask
SECRET_KEY= # leave empty to auto‑generate a secure key
DATABASE_URL=sqlite:///online_voting.db
# Rate limiting (Flask‑Limiter)
RATELIMIT_DEFAULT='200 per day; 5 per minute'
# Email (Flask‑Mail)
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=your.email@example.com
MAIL_PASSWORD=your_email_app_password
MAIL_DEFAULT_SENDER=your.email@example.com
# Gemini chatbot
CHAT_PROVIDER=gemini
GEMINI_API_KEY=YOUR_GEMINI_API_KEY
GEMINI_MODEL=gemini-pro
# Chat logging (optional)
LOG_CHAT=true
CHAT_RATE_LIMIT='5 per minute'
Secret key – if omitted, the app generates a random 32‑byte URL‑safe key at runtime.
Mail credentials – required for email verification and optional OTP.
Database Setup
bash


flask db init
flask db migrate -m "Initial schema with email verification"
flask db upgrade
Create Admin User
Edit seed.py (or run the script directly) to set your preferred admin credentials, then:

bash


python seed.py
The script creates an admin with the role admin and a hashed password.

Run the App
bash


flask run
Open http://127.0.0.1:5000 in your browser.

Usage
Route	Description
/auth/register	Register a new voter – receives verification email.
/auth/verify/<token>	Activate account via verification link.
/auth/login	Log in (unverified accounts are blocked).
/admin/dashboard	Admin home – create elections, manage candidates, view logs.
/voter/election/<id>/vote	Cast a vote (one vote per election).
/admin/election/<id>/results/csv	Download CSV of votes.
/admin/election/<id>/results/pdf	Download styled PDF report.
/api/chat	POST JSON { "message": "..." } – Gemini chatbot response (rate‑limited).
Floating chat button	Available on every page, opens a modal for interactive help.
Testing
bash


pytest
The tests/ folder contains unit tests for models, routes, and the fraud detector.

Docker
A ready‑to‑use Dockerfile is provided.

bash


docker build -t online-voting .
docker run -d -p 8000:5000 --env-file .env online-voting
The app will be reachable at http://localhost:8000.

Contributing
Fork the repository.
Create a feature branch (git checkout -b feature/awesome-feature).
Write tests for new code.
Ensure pytest passes.
Submit a Pull Request with a clear description.
Please follow the existing code style (PEP 8) and add documentation where appropriate.

License
This project is licensed under the MIT License – see the LICENSE file for details.

Enjoy secure, transparent, and AI‑enhanced online voting!
