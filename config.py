import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, 'voting_system.db').replace('\\', '/')

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'online-voting-system-secret-key-2026-safe-key'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or f"sqlite:///{DB_PATH}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5MB max upload size
    RATELIMIT_DEFAULT = "200 per day;50 per hour"
    RATELIMIT_STORAGE_URI = "memory://"
    
    # Gemini AI Chatbot Settings
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')
    CHAT_RATE_LIMIT = "5 per minute"
    LOG_CHAT = os.environ.get('LOG_CHAT', 'True').lower() in ('true', '1', 't')

    # Flask-Mail Settings for Email Verification
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'True').lower() in ('true', '1', 't')
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME', '')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', '')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', ('MatDan Electoral Portal', 'noreply@matdan-india.gov.in'))


