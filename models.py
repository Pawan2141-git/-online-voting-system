from datetime import datetime, timezone
from flask import request, current_app
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import URLSafeTimedSerializer
import hashlib

def utc_now_naive():
    return datetime.now(timezone.utc).replace(tzinfo=None)

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    voter_id = db.Column(db.String(50), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='voter')  # 'admin' or 'voter'
    date_of_birth = db.Column(db.Date, nullable=True)
    state = db.Column(db.String(100), nullable=True, default='Delhi (NCT)')
    constituency = db.Column(db.String(100), nullable=True, default='New Delhi')
    is_verified = db.Column(db.Boolean, default=True, nullable=False)

    verification_sent_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=utc_now_naive)

    # Relationships
    vote_records = db.relationship('VoteRecord', backref='user', lazy=True, cascade='all, delete-orphan')
    audit_logs = db.relationship('AuditLog', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        return self.role == 'admin'

    @property
    def age(self):
        if not self.date_of_birth:
            return 18
        today = datetime.utcnow().date()
        return today.year - self.date_of_birth.year - ((today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day))

    @property
    def is_eligible_voter(self):
        return self.age >= 18

    def has_voted_in(self, election_id):
        return VoteRecord.query.filter_by(user_id=self.id, election_id=election_id).first() is not None

    def get_reset_token(self, secret_key="RESET_PASSWORD_SALT_2026"):
        return hashlib.sha256(f"{self.id}:{self.email}:{self.password_hash}:{secret_key}".encode('utf-8')).hexdigest()

    def verify_reset_token(self, token, secret_key="RESET_PASSWORD_SALT_2026"):
        expected = hashlib.sha256(f"{self.id}:{self.email}:{self.password_hash}:{secret_key}".encode('utf-8')).hexdigest()
        return token == expected

    def get_verification_token(self, expires_sec=3600):
        secret_key = current_app.config.get('SECRET_KEY', 'online-voting-system-secret-key-2026-safe-key')
        s = URLSafeTimedSerializer(secret_key)
        return s.dumps({'user_id': self.id, 'email': self.email}, salt='email-verification-salt')

    @staticmethod
    def verify_token(token, expires_sec=3600):
        secret_key = current_app.config.get('SECRET_KEY', 'online-voting-system-secret-key-2026-safe-key')
        s = URLSafeTimedSerializer(secret_key)
        try:
            data = s.loads(token, salt='email-verification-salt', max_age=expires_sec)
            user_id = data.get('user_id')
            return User.query.get(user_id)
        except Exception:
            return None

    def __repr__(self):
        return f'<User {self.email} ({self.role})>'



class Election(db.Model):
    __tablename__ = 'elections'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='upcoming')  # 'upcoming', 'active', 'closed'
    created_at = db.Column(db.DateTime, default=utc_now_naive)

    # Relationships
    candidates = db.relationship('Candidate', backref='election', lazy=True, cascade='all, delete-orphan')
    vote_records = db.relationship('VoteRecord', backref='election', lazy=True, cascade='all, delete-orphan')
    votes = db.relationship('Vote', backref='election', lazy=True, cascade='all, delete-orphan')

    def update_status(self):
        """Dynamically evaluate and update status based on current UTC time."""
        now = utc_now_naive()
        start = self.start_time.replace(tzinfo=None) if self.start_time else now
        end = self.end_time.replace(tzinfo=None) if self.end_time else now

        if now < start:
            computed = 'upcoming'
        elif start <= now <= end:
            computed = 'active'
        else:
            computed = 'closed'

        if self.status != computed:
            self.status = computed
            db.session.commit()

        return computed

    @property
    def current_status(self):
        now = utc_now_naive()
        start = self.start_time.replace(tzinfo=None) if self.start_time else now
        end = self.end_time.replace(tzinfo=None) if self.end_time else now

        if now < start:
            return 'upcoming'
        elif start <= now <= end:
            return 'active'
        else:
            return 'closed'

    @property
    def total_votes(self):
        return Vote.query.filter_by(election_id=self.id).count()

    def seconds_remaining(self):
        now = utc_now_naive()
        end = self.end_time.replace(tzinfo=None) if self.end_time else now
        diff = (end - now).total_seconds()
        return max(0, int(diff))

    def __repr__(self):
        return f'<Election {self.title}>'


class Candidate(db.Model):
    __tablename__ = 'candidates'

    id = db.Column(db.Integer, primary_key=True)
    election_id = db.Column(db.Integer, db.ForeignKey('elections.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    party = db.Column(db.String(100), nullable=False)
    photo_url = db.Column(db.String(255), nullable=True)
    bio = db.Column(db.Text, nullable=True)

    # Relationships
    votes = db.relationship('Vote', backref='candidate', lazy=True, cascade='all, delete-orphan')

    @property
    def vote_count(self):
        return Vote.query.filter_by(candidate_id=self.id).count()

    def __repr__(self):
        return f'<Candidate {self.name} - {self.party}>'


class VoteRecord(db.Model):
    """Tracks that a user has voted in an election to prevent double voting."""
    __tablename__ = 'vote_records'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    election_id = db.Column(db.Integer, db.ForeignKey('elections.id'), nullable=False)
    voted_at = db.Column(db.DateTime, default=utc_now_naive)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'election_id', name='unique_user_election_vote'),
    )

    def __repr__(self):
        return f'<VoteRecord User:{self.user_id} Election:{self.election_id}>'


class Vote(db.Model):
    """Anonymized ballot vote entry for auditing and count aggregation."""
    __tablename__ = 'votes'

    id = db.Column(db.Integer, primary_key=True)
    election_id = db.Column(db.Integer, db.ForeignKey('elections.id'), nullable=False)
    candidate_id = db.Column(db.Integer, db.ForeignKey('candidates.id'), nullable=False)
    voter_hash = db.Column(db.String(64), nullable=False)
    timestamp = db.Column(db.DateTime, default=utc_now_naive)

    @staticmethod
    def generate_hash(user_id, election_id, secret_salt="VOTING_ANONYMOUS_SALT_2026"):
        return hashlib.sha256(f"{user_id}:{election_id}:{secret_salt}".encode('utf-8')).hexdigest()

    def __repr__(self):
        return f'<Vote Election:{self.election_id} Candidate:{self.candidate_id}>'


class AuditLog(db.Model):
    """Stores administrative activity logs for compliance and audit trail."""
    __tablename__ = 'audit_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    action = db.Column(db.String(100), nullable=False)
    details = db.Column(db.Text, nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    timestamp = db.Column(db.DateTime, default=utc_now_naive)

    @staticmethod
    def log(action, details=None, user_id=None, ip_address=None):
        try:
            log_entry = AuditLog(
                user_id=user_id,
                action=action,
                details=details,
                ip_address=ip_address or (request.remote_addr if request else '127.0.0.1')
            )
            db.session.add(log_entry)
            db.session.commit()
        except Exception:
            db.session.rollback()

    def __repr__(self):
        return f'<AuditLog {self.action} at {self.timestamp}>'


class ChatLog(db.Model):
    """Stores interactions with the Gemini AI Chatbot Assistant for audit and administrative oversight."""
    __tablename__ = 'chat_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    user_message = db.Column(db.Text, nullable=False)
    bot_response = db.Column(db.Text, nullable=False)
    ip_address = db.Column(db.String(45), nullable=True)
    timestamp = db.Column(db.DateTime, default=utc_now_naive)

    def __repr__(self):
        return f'<ChatLog User:{self.user_id} at {self.timestamp}>'


class PushSubscription(db.Model):
    """Stores browser Web Push Subscriptions for election reminders."""
    __tablename__ = 'push_subscriptions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    endpoint = db.Column(db.Text, nullable=False, unique=True)
    p256dh = db.Column(db.Text, nullable=True)
    auth = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=utc_now_naive)

    def __repr__(self):
        return f'<PushSubscription User:{self.user_id}>'


