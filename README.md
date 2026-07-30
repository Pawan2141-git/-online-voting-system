# 🗳️ MatDan India - Digital Electoral Portal & Online Voting System

[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.0.2-green.svg)](https://flask.palletsprojects.org/)
[![Bootstrap](https://img.shields.io/badge/Bootstrap-5.3.2-purple.svg)](https://getbootstrap.com/)
[![License](https://img.shields.io/badge/License-MIT-orange.svg)](LICENSE)

A **secure, modern, and mobile-first Indian Online Voting System** web application built with **Flask, SQLite (SQLAlchemy ORM), Flask-Login, Flask-WTF, Flask-Limiter, Bootstrap 5, Web Push Notifications, and Google Gemini AI Assistant**.

---

## 📌 Project Overview

**MatDan India** is a digital electoral portal designed to simulate democratic national, state, and constituency-level elections with enterprise-grade security, mathematical ballot anonymization, real-time analytics, and mobile responsiveness.

---

## ✨ Key Features

### 1. 🛡️ Role-Based Access Control
- **Admin / CEO Dashboard**:
  - Create, edit, activate, and close elections.
  - Candidate management with photo uploads and party symbols.
  - Electoral Roll management & Bulk Voter CSV import.
  - Comprehensive Audit Logs for security monitoring.
  - Live election analytics with Chart.js visualizations.
  - Export turnout & results in **CSV** and **styled PDF** formats.
- **Voter Portal**:
  - Quick Voter ID (EPIC Number) registration and instant login.
  - Interactive voting booth with NOTA (None of the Above) option.
  - Double-vote prevention (1 account = 1 ballot constraint).
  - Real-time election schedule tracking and result viewing.

### 2. 🔐 Security & Ballot Anonymization
- **Cryptographic Anonymization**: Votes are stored separately from voter identity (`Vote` vs `VoteRecord`) using SHA-256 ballot hashes.
- **CSRF & Rate Limiting**: Anti-CSRF token verification and brute-force IP rate limiting (`Flask-Limiter`).
- **Audit Logging**: Every administrative action, vote cast, and login attempt is recorded with IP telemetry.

### 3. 🤖 Gemini AI Electoral Assistant
- Integrated floating **AI Chatbot** (`/api/chat`) powered by Google's Gemini 1.5 Flash API.
- Answers electoral rules, voting eligibility, EPIC card queries, and election statuses in real time.

### 4. 🔔 Web Push Notifications & Reminders
- Browser Service Worker (`sw.js`) sending desktop/mobile notifications when elections start or close.

### 5. 📱 Mobile-First Responsive Design
- Touch-friendly 44px targets, fluid Bootstrap 5 grid layout, and responsive candidate cards for mobile viewports.

---

## 🛠️ Technology Stack

- **Backend**: Python 3.12, Flask, Flask-SQLAlchemy, Flask-Login, Flask-WTF, Flask-Limiter, Flask-Mail
- **Frontend**: HTML5, Vanilla CSS3, JavaScript (ES6+), Bootstrap 5.3, Bootstrap Icons, Chart.js
- **AI & Real-Time**: Google Gemini Flash API, Web Push Notifications API (pywebpush, Service Worker)
- **PDF Generation**: ReportLab
- **Testing**: Pytest

---

## 🔑 Pre-Seeded Test Credentials

Running `python seed.py` populates the database with demo accounts:

| Role | Email / Identity | Password | EPIC Voter ID Card |
| :--- | :--- | :--- | :--- |
| **Admin / CEO** | `admin@eci.gov.in` | `admin123` | `ECI0001001` |
| **Sample Voter 1** | `rajesh.sharma@example.in` | `voter123` | `DLX1234567` |
| **Sample Voter 2** | `priya.patel@example.in` | `voter123` | `GUJ9876543` |
| **Sample Voter 3** | `amit.banerjee@example.in` | `voter123` | `WBK5544332` |

---

## ⚡ Quick Start Guide (Local Setup)

```bash
# 1. Clone the repository
git clone https://github.com/Pawan2141-git/-online-voting-system.git
cd -online-voting-system

# 2. Create and activate virtual environment
python -m venv .venv
# On Windows:
.\.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

# 3. Install required dependencies
pip install -r requirements.txt

# 4. Seed database with initial tables and demo accounts
python seed.py

# 5. Run the Flask application
python app.py
```

Open your browser and visit: `http://127.0.0.1:5000`

---

## 🧪 Running Automated Tests

```bash
python -m pytest
```

---

## 📄 License

This project is open-source under the MIT License.
