from flask import Flask, render_template, redirect, url_for, flash, request, make_response, abort
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from datetime import datetime, timezone
from functools import wraps
import os
import csv
import io
from werkzeug.utils import secure_filename

try:
    from flask_socketio import SocketIO, emit
    HAS_SOCKETIO = True
except ImportError:
    HAS_SOCKETIO = False
    SocketIO = None
    emit = None

from flask import send_from_directory, jsonify
from flask_mail import Mail
from config import Config
from models import db, User, Election, Candidate, VoteRecord, Vote, AuditLog, PushSubscription
from forms import LoginForm, RegisterForm, ElectionForm, CandidateForm, VoteForm, BulkVoterImportForm, ResetPasswordRequestForm, ResetPasswordForm
from chat import chat_bp
from utils.email import send_verification_email

app = Flask(__name__)
app.config.from_object(Config)

@app.route('/sw.js')
def service_worker():
    return send_from_directory(app.static_folder, 'sw.js', mimetype='application/javascript')

@app.route('/api/push-subscribe', methods=['POST'])
def push_subscribe():
    data = request.get_json() or {}
    endpoint = data.get('endpoint')
    if not endpoint:
        return jsonify({'error': 'Endpoint is required.'}), 400
    
    keys = data.get('keys', {})
    p256dh = keys.get('p256dh')
    auth = keys.get('auth')
    uid = current_user.id if current_user and current_user.is_authenticated else None

    try:
        existing = PushSubscription.query.filter_by(endpoint=endpoint).first()
        if not existing:
            sub = PushSubscription(user_id=uid, endpoint=endpoint, p256dh=p256dh, auth=auth)
            db.session.add(sub)
            db.session.commit()
    except Exception:
        db.session.rollback()

    return jsonify({'status': 'success', 'message': 'Subscribed to election reminders.'})


# Initialize Flask-Mail
mail = Mail(app)

# Register Blueprints
app.register_blueprint(chat_bp)


# Initialize Extensions
db.init_app(app)
csrf = CSRFProtect(app)
limiter = Limiter(get_remote_address, app=app, default_limits=["200 per day", "50 per hour"], storage_uri="memory://")
if HAS_SOCKETIO:
    socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')
else:
    socketio = None

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Ensure database tables exist automatically on startup and before requests
def init_db():
    try:
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        db.create_all()

        try:
            with db.engine.connect() as conn:
                from sqlalchemy import inspect, text
                inspector = inspect(db.engine)
                if 'users' in inspector.get_table_names():
                    columns = [c['name'] for c in inspector.get_columns('users')]
                    if 'is_verified' not in columns:
                        conn.execute(text("ALTER TABLE users ADD COLUMN is_verified BOOLEAN NOT NULL DEFAULT 1"))
                    if 'verification_sent_at' not in columns:
                        conn.execute(text("ALTER TABLE users ADD COLUMN verification_sent_at DATETIME"))
                    conn.commit()
        except Exception:
            pass

        try:
            if User.query.filter_by(role='admin').first() is None:
                from seed import seed_database
                seed_database()
        except Exception:
            db.session.rollback()
            db.create_all()
            from seed import seed_database
            seed_database()
    except Exception as e:
        db.session.rollback()
        try:
            db.create_all()
        except Exception:
            pass


with app.app_context():
    init_db()


@app.before_request
def ensure_db_tables():
    if not getattr(app, '_db_tables_created', False):
        init_db()
        app._db_tables_created = True

# Security Headers Middleware
@app.after_request
def apply_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    return response

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'warning'


@login_manager.user_loader
def load_user(user_id):
    try:
        return User.query.get(int(user_id))
    except Exception:
        db.session.rollback()
        return None


# Custom Admin Required Decorator
def admin_required(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            flash('Access restricted to administrators only.', 'danger')
            return redirect(url_for('voter_dashboard'))
        return f(*args, **kwargs)
    return decorated_function


# Context Processor to make datetime available in templates
@app.context_processor
def inject_now():
    return {'now': datetime.now(timezone.utc)}


# ==================== PUBLIC ROUTES ====================

@app.route('/')
def index():
    try:
        if current_user.is_authenticated:
            if current_user.is_admin:
                return redirect(url_for('admin_dashboard'))
            return redirect(url_for('voter_dashboard'))

        elections = Election.query.all()
    except Exception:
        db.session.rollback()
        init_db()
        if current_user.is_authenticated:
            if current_user.is_admin:
                return redirect(url_for('admin_dashboard'))
            return redirect(url_for('voter_dashboard'))
        elections = Election.query.all()

    for e in elections:
        e.update_status()

    active_elections = Election.query.filter_by(status='active').all()
    upcoming_elections = Election.query.filter_by(status='upcoming').all()
    recent_closed = Election.query.filter_by(status='closed').order_by(Election.end_time.desc()).limit(3).all()

    return render_template('index.html', 
                           active_elections=active_elections, 
                           upcoming_elections=upcoming_elections,
                           recent_closed=recent_closed)


@app.route('/register', methods=['GET', 'POST'])
def register():
    try:
        if current_user.is_authenticated:
            return redirect(url_for('index'))
    except Exception:
        db.session.rollback()
        init_db()

    form = RegisterForm()
    if form.validate_on_submit():
        user = User(
            full_name=form.full_name.data.strip(),
            email=form.email.data.lower().strip(),
            voter_id=form.voter_id.data.upper().strip(),
            date_of_birth=form.date_of_birth.data,
            state=form.state.data,
            constituency=form.constituency.data.strip(),
            role='voter',
            is_verified=True
        )
        user.set_password(form.password.data)
        try:
            db.session.add(user)
            db.session.commit()
            AuditLog.log('VOTER_REGISTERED', f"New voter registered: {user.full_name} ({user.voter_id}) - State: {user.state}", user_id=user.id)
        except Exception:
            db.session.rollback()
            init_db()
            db.session.add(user)
            db.session.commit()

        flash('Registration successful! You can now log in with your credentials.', 'success')
        return redirect(url_for('login'))

    return render_template('auth/register.html', form=form)



@app.route('/verify/<token>')
def verify_email(token):
    try:
        user = User.verify_token(token)
    except Exception:
        db.session.rollback()
        init_db()
        user = User.verify_token(token)

    if not user:
        flash('The verification link is invalid or has expired.', 'danger')
        return render_template('auth/verify_failed.html')
    
    if not user.is_verified:
        user.is_verified = True
        db.session.commit()
        AuditLog.log('EMAIL_VERIFIED', f"Email verified for user: {user.email}", user_id=user.id)

    return render_template('auth/verify_success.html', user=user)


@app.route('/resend-verification', methods=['GET', 'POST'])
def resend_verification():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        identity = request.form.get('identity', '').strip()
        try:
            user = User.query.filter(
                (User.email == identity.lower()) | (User.voter_id == identity.upper())
            ).first()
        except Exception:
            db.session.rollback()
            init_db()
            user = User.query.filter(
                (User.email == identity.lower()) | (User.voter_id == identity.upper())
            ).first()

        if user:
            if user.is_verified:
                flash('Your account is already verified! You can log in directly.', 'info')
                return redirect(url_for('login'))
            
            send_verification_email(user, mail)
            AuditLog.log('VERIFICATION_RESENT', f"Resent verification email to: {user.email}", user_id=user.id)
            flash(f'A new email verification link has been sent to {user.email}.', 'info')
            return redirect(url_for('login'))
        else:
            flash('No registered account found with provided Email or EPIC Voter ID.', 'danger')

    return render_template('auth/resend_verification.html')



@app.route('/login', methods=['GET', 'POST'])
@limiter.limit("10 per minute", methods=["POST"])
def login():
    try:
        if current_user.is_authenticated:
            return redirect(url_for('index'))
    except Exception:
        db.session.rollback()
        init_db()

    form = LoginForm()
    if form.validate_on_submit():
        identity = form.identity.data.strip()
        try:
            user = User.query.filter(
                (User.email == identity.lower()) | (User.voter_id == identity.upper())
            ).first()
        except Exception:
            db.session.rollback()
            init_db()
            user = User.query.filter(
                (User.email == identity.lower()) | (User.voter_id == identity.upper())
            ).first()

        if user and user.check_password(form.password.data):
            login_user(user)
            AuditLog.log('USER_LOGIN', f"User logged in: {user.email}", user_id=user.id)
            flash(f'Welcome back, {user.full_name}!', 'success')
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            if user.is_admin:
                return redirect(url_for('admin_dashboard'))
            return redirect(url_for('voter_dashboard'))

        else:
            AuditLog.log('LOGIN_FAILED', f"Failed login attempt for identity: {identity}")
            flash('Invalid Email/EPIC Voter ID or password.', 'danger')

    return render_template('auth/login.html', form=form)



@app.route('/logout')
@login_required
def logout():
    uid = current_user.id
    email = current_user.email
    logout_user()
    AuditLog.log('USER_LOGOUT', f"User logged out: {email}", user_id=uid)
    flash('You have been logged out safely.', 'info')
    return redirect(url_for('index'))


@app.route('/reset-password-request', methods=['GET', 'POST'])
def reset_password_request():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    form = ResetPasswordRequestForm()
    if form.validate_on_submit():
        identity = form.identity.data.strip()
        user = User.query.filter(
            (User.email == identity.lower()) | (User.voter_id == identity.upper())
        ).first()

        if user:
            token = user.get_reset_token()
            reset_url = url_for('reset_password', token=token, _external=True)
            AuditLog.log('PASSWORD_RESET_REQUESTED', f"Password reset requested for: {user.email}", user_id=user.id)
            flash(f'Password reset token generated! Demo Reset URL: {reset_url}', 'info')
            return redirect(url_for('reset_password', token=token))
        else:
            flash('No registered voter found with provided details.', 'danger')

    return render_template('auth/reset_password_request.html', form=form)


@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    users = User.query.all()
    user = next((u for u in users if u.verify_reset_token(token)), None)

    if not user:
        flash('Invalid or expired reset token.', 'danger')
        return redirect(url_for('reset_password_request'))

    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        AuditLog.log('PASSWORD_RESET_SUCCESS', f"Password successfully updated for: {user.email}", user_id=user.id)
        flash('Your password has been reset successfully! You can now log in.', 'success')
        return redirect(url_for('login'))

    return render_template('auth/reset_password.html', form=form, user=user)


# ==================== ADMIN ROUTES ====================

@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    elections = Election.query.order_by(Election.created_at.desc()).all()
    for e in elections:
        e.update_status()

    total_voters = User.query.filter_by(role='voter').count()
    total_elections = len(elections)
    total_votes_cast = Vote.query.count()
    active_count = sum(1 for e in elections if e.current_status == 'active')

    # Turnout Percentage Calculation
    voted_users_count = db.session.query(db.func.count(db.func.distinct(VoteRecord.user_id))).scalar() or 0
    voter_participation_pct = round((voted_users_count / total_voters * 100), 1) if total_voters > 0 else 0.0


    recent_logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(5).all()

    return render_template('admin/dashboard.html',
                           elections=elections[:5],
                           total_voters=total_voters,
                           total_elections=total_elections,
                           total_votes_cast=total_votes_cast,
                           active_count=active_count,
                           voter_participation_pct=voter_participation_pct,
                           recent_logs=recent_logs)


@app.route('/admin/elections')
@admin_required
def admin_elections():
    elections = Election.query.order_by(Election.created_at.desc()).all()
    for e in elections:
        e.update_status()
    return render_template('admin/elections.html', elections=elections)


@app.route('/admin/elections/create', methods=['GET', 'POST'])
@admin_required
def admin_election_create():
    form = ElectionForm()
    if form.validate_on_submit():
        election = Election(
            title=form.title.data.strip(),
            description=form.description.data.strip(),
            start_time=form.start_time.data,
            end_time=form.end_time.data,
            status=form.status.data
        )
        db.session.add(election)
        db.session.commit()
        election.update_status()
        AuditLog.log('ELECTION_CREATED', f"Created election: {election.title}", user_id=current_user.id)
        flash(f'Election "{election.title}" created successfully.', 'success')
        return redirect(url_for('admin_elections'))
    return render_template('admin/election_form.html', form=form, title="Create New Election")


@app.route('/admin/elections/<int:election_id>/edit', methods=['GET', 'POST'])
@admin_required
def admin_election_edit(election_id):
    election = Election.query.get_or_404(election_id)
    form = ElectionForm(obj=election)

    if form.validate_on_submit():
        election.title = form.title.data.strip()
        election.description = form.description.data.strip()
        election.start_time = form.start_time.data
        election.end_time = form.end_time.data
        election.status = form.status.data
        db.session.commit()
        election.update_status()
        AuditLog.log('ELECTION_UPDATED', f"Updated election ID {election.id}: {election.title}", user_id=current_user.id)
        flash(f'Election "{election.title}" updated successfully.', 'success')
        return redirect(url_for('admin_elections'))

    return render_template('admin/election_form.html', form=form, election=election, title=f"Edit: {election.title}")


@app.route('/admin/elections/<int:election_id>/delete', methods=['POST'])
@admin_required
def admin_election_delete(election_id):
    election = Election.query.get_or_404(election_id)
    title = election.title
    db.session.delete(election)
    db.session.commit()
    AuditLog.log('ELECTION_DELETED', f"Deleted election: {title}", user_id=current_user.id)
    flash(f'Election "{title}" and all associated candidates/votes were deleted.', 'info')
    return redirect(url_for('admin_elections'))


@app.route('/admin/elections/<int:election_id>/candidates')
@admin_required
def admin_candidates(election_id):
    election = Election.query.get_or_404(election_id)
    candidates = Candidate.query.filter_by(election_id=election_id).all()
    return render_template('admin/candidates.html', election=election, candidates=candidates)


@app.route('/admin/candidates/create/<int:election_id>', methods=['GET', 'POST'])
@admin_required
def admin_candidate_create(election_id):
    election = Election.query.get_or_404(election_id)
    form = CandidateForm()
    if form.validate_on_submit():
        photo_url = form.photo_url.data.strip() if form.photo_url.data else None
        
        if form.photo_file.data:
            try:
                os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
                file = form.photo_file.data
                filename = secure_filename(f"cand_{election_id}_{int(datetime.utcnow().timestamp())}_{file.filename}")
                upload_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(upload_path)
                photo_url = url_for('static', filename=f'uploads/{filename}')
            except Exception as e:
                app.logger.error(f"Error saving uploaded photo: {e}")
                if not photo_url:
                    photo_url = None

        candidate = Candidate(
            election_id=election_id,
            name=form.name.data.strip(),
            party=form.party.data.strip(),
            photo_url=photo_url,
            bio=form.bio.data.strip() if form.bio.data else None
        )
        db.session.add(candidate)
        db.session.commit()
        AuditLog.log('CANDIDATE_ADDED', f"Added candidate {candidate.name} ({candidate.party}) to election ID {election_id}", user_id=current_user.id)
        flash(f'Candidate "{candidate.name}" added to {election.title}.', 'success')
        return redirect(url_for('admin_candidates', election_id=election_id))

    return render_template('admin/candidate_form.html', form=form, election=election, title="Add Candidate")


@app.route('/admin/candidates/<int:candidate_id>/edit', methods=['GET', 'POST'])
@admin_required
def admin_candidate_edit(candidate_id):
    candidate = Candidate.query.get_or_404(candidate_id)
    election = candidate.election
    form = CandidateForm(obj=candidate)

    if form.validate_on_submit():
        candidate.name = form.name.data.strip()
        candidate.party = form.party.data.strip()
        
        if form.photo_file.data:
            try:
                os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
                file = form.photo_file.data
                filename = secure_filename(f"cand_{candidate.election_id}_{int(datetime.utcnow().timestamp())}_{file.filename}")
                upload_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(upload_path)
                candidate.photo_url = url_for('static', filename=f'uploads/{filename}')
            except Exception as e:
                app.logger.error(f"Error saving uploaded photo: {e}")
        elif form.photo_url.data:
            candidate.photo_url = form.photo_url.data.strip()

        candidate.bio = form.bio.data.strip() if form.bio.data else None
        db.session.commit()
        AuditLog.log('CANDIDATE_UPDATED', f"Updated candidate {candidate.name} (ID {candidate.id})", user_id=current_user.id)
        flash(f'Candidate "{candidate.name}" updated.', 'success')
        return redirect(url_for('admin_candidates', election_id=election.id))

    return render_template('admin/candidate_form.html', form=form, election=election, candidate=candidate, title=f"Edit: {candidate.name}")



@app.route('/admin/candidates/<int:candidate_id>/delete', methods=['POST'])
@admin_required
def admin_candidate_delete(candidate_id):
    candidate = Candidate.query.get_or_404(candidate_id)
    election_id = candidate.election_id
    name = candidate.name
    db.session.delete(candidate)
    db.session.commit()
    AuditLog.log('CANDIDATE_DELETED', f"Deleted candidate: {name} (ID {candidate_id})", user_id=current_user.id)
    flash(f'Candidate "{name}" removed.', 'info')
    return redirect(url_for('admin_candidates', election_id=election_id))


@app.route('/admin/voters')
@admin_required
def admin_voters():
    voters = User.query.filter_by(role='voter').order_by(User.created_at.desc()).all()
    return render_template('admin/voters.html', voters=voters)


@app.route('/admin/voters/import', methods=['GET', 'POST'])
@admin_required
def admin_voters_import():
    form = BulkVoterImportForm()
    if form.validate_on_submit():
        csv_file = form.csv_file.data
        stream = io.StringIO(csv_file.stream.read().decode("UTF-8"), newline=None)
        csv_reader = csv.DictReader(stream)

        imported_count = 0
        skipped_count = 0

        for row in csv_reader:
            full_name = row.get('full_name', '').strip()
            email = row.get('email', '').strip().lower()
            voter_id = row.get('voter_id', '').strip().upper()
            password = row.get('password', 'voter123').strip()

            if not full_name or not email or not voter_id:
                continue

            if User.query.filter((User.email == email) | (User.voter_id == voter_id)).first():
                skipped_count += 1
                continue

            user = User(
                full_name=full_name,
                email=email,
                voter_id=voter_id,
                role='voter'
            )
            user.set_password(password)
            db.session.add(user)
            imported_count += 1

        db.session.commit()
        AuditLog.log('BULK_VOTERS_IMPORTED', f"Imported {imported_count} voters from CSV (Skipped {skipped_count} duplicates)", user_id=current_user.id)
        flash(f'Bulk Import Complete: Successfully registered {imported_count} voters ({skipped_count} skipped duplicates).', 'success')
        return redirect(url_for('admin_voters'))

    return render_template('admin/voter_import.html', form=form)


@app.route('/admin/audit-logs')
@admin_required
def admin_audit_logs():
    logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).all()
    return render_template('admin/audit_logs.html', logs=logs)


@app.route('/admin/results/<int:election_id>')
@admin_required
def admin_results(election_id):
    election = Election.query.get_or_404(election_id)
    election.update_status()

    candidates = Candidate.query.filter_by(election_id=election_id).all()
    total_votes = election.total_votes

    results_data = []
    for c in candidates:
        count = c.vote_count
        percentage = round((count / total_votes * 100), 2) if total_votes > 0 else 0
        results_data.append({
            'candidate': c,
            'votes': count,
            'percentage': percentage
        })

    results_data.sort(key=lambda x: x['votes'], reverse=True)

    return render_template('admin/results.html', election=election, results_data=results_data, total_votes=total_votes)


@app.route('/admin/export/<int:election_id>/csv')
@admin_required
def admin_export_csv(election_id):
    election = Election.query.get_or_404(election_id)
    candidates = Candidate.query.filter_by(election_id=election_id).all()
    total_votes = election.total_votes

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(['Election Title', election.title])
    writer.writerow(['Status', election.current_status])
    writer.writerow(['Start Time', election.start_time.strftime('%Y-%m-%d %H:%M:%S UTC')])
    writer.writerow(['End Time', election.end_time.strftime('%Y-%m-%d %H:%M:%S UTC')])
    writer.writerow(['Total Votes Cast', total_votes])
    writer.writerow([])
    writer.writerow(['Candidate ID', 'Candidate Name', 'Party / Affiliation', 'Votes Received', 'Percentage'])

    for c in candidates:
        count = c.vote_count
        pct = round((count / total_votes * 100), 2) if total_votes > 0 else 0.0
        writer.writerow([c.id, c.name, c.party, count, f"{pct}%"])

    AuditLog.log('EXPORT_CSV', f"Exported CSV for election ID {election_id}", user_id=current_user.id)
    response = make_response(output.getvalue())
    response.headers["Content-Disposition"] = f"attachment; filename=election_{election_id}_results.csv"
    response.headers["Content-type"] = "text/csv"
    return response


@app.route('/admin/export/<int:election_id>/pdf')
@admin_required
def admin_export_pdf(election_id):
    election = Election.query.get_or_404(election_id)
    candidates = Candidate.query.filter_by(election_id=election_id).all()
    total_votes = election.total_votes

    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib import colors

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
        elements = []
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            'TitleStyle',
            parent=styles['Heading1'],
            fontSize=20,
            textColor=colors.HexColor('#1E293B'),
            spaceAfter=12
        )
        meta_style = ParagraphStyle(
            'MetaStyle',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#475569'),
            spaceAfter=4
        )

        elements.append(Paragraph(f"Official Election Results: {election.title}", title_style))
        elements.append(Paragraph(f"Status: <b>{election.current_status.upper()}</b>", meta_style))
        elements.append(Paragraph(f"Period: {election.start_time.strftime('%b %d, %Y %H:%M')} to {election.end_time.strftime('%b %d, %Y %H:%M')} UTC", meta_style))
        elements.append(Paragraph(f"Total Votes Cast: <b>{total_votes}</b>", meta_style))
        elements.append(Spacer(1, 16))

        # Table data
        data = [['Candidate', 'Party', 'Votes', 'Percentage']]
        for c in candidates:
            count = c.vote_count
            pct = f"{round((count / total_votes * 100), 2)}%" if total_votes > 0 else "0%"
            data.append([c.name, c.party, str(count), pct])

        t = Table(data, colWidths=[180, 180, 80, 80])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0F172A')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F8FAFC')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F1F5F9')]),
        ]))

        elements.append(t)
        doc.build(elements)
        buffer.seek(0)

        AuditLog.log('EXPORT_PDF', f"Exported PDF for election ID {election_id}", user_id=current_user.id)
        response = make_response(buffer.getvalue())
        response.headers["Content-Disposition"] = f"attachment; filename=election_{election_id}_report.pdf"
        response.headers["Content-type"] = "application/pdf"
        return response

    except Exception as e:
        flash(f'Error generating PDF report: {str(e)}', 'danger')
        return redirect(url_for('admin_results', election_id=election_id))


# ==================== VOTER ROUTES ====================

@app.route('/voter/dashboard')
@login_required
def voter_dashboard():
    if current_user.is_admin:
        return redirect(url_for('admin_dashboard'))

    elections = Election.query.order_by(Election.start_time.asc()).all()
    for e in elections:
        e.update_status()

    voted_election_ids = {vr.election_id for vr in current_user.vote_records}

    return render_template('voter/dashboard.html',
                           elections=elections,
                           voted_election_ids=voted_election_ids)


@app.route('/voter/vote/<int:election_id>', methods=['GET', 'POST'])
@login_required
def voter_vote(election_id):
    if current_user.is_admin:
        flash('Administrators cannot cast votes.', 'warning')
        return redirect(url_for('admin_dashboard'))

    election = Election.query.get_or_404(election_id)
    status = election.update_status()

    if status != 'active':
        flash('This election is not currently open for voting.', 'danger')
        return redirect(url_for('voter_dashboard'))

    if current_user.has_voted_in(election_id):
        flash('You have already cast your vote in this election.', 'info')
        return redirect(url_for('voter_results', election_id=election_id))

    candidates = Candidate.query.filter_by(election_id=election_id).all()
    if not candidates:
        flash('No candidates listed for this election yet.', 'warning')
        return redirect(url_for('voter_dashboard'))

    form = VoteForm()
    form.candidate_id.choices = [(c.id, c.name) for c in candidates]

    if form.validate_on_submit():
        selected_candidate_id = form.candidate_id.data
        candidate = Candidate.query.get(selected_candidate_id)
        if not candidate or candidate.election_id != election_id:
            flash('Invalid candidate selected.', 'danger')
            return redirect(url_for('voter_vote', election_id=election_id))

        existing_record = VoteRecord.query.filter_by(user_id=current_user.id, election_id=election_id).first()
        if existing_record:
            flash('You have already cast your vote in this election.', 'warning')
            return redirect(url_for('voter_dashboard'))

        vote_record = VoteRecord(user_id=current_user.id, election_id=election_id)
        voter_hash = Vote.generate_hash(current_user.id, election_id)
        anonymized_vote = Vote(
            election_id=election_id,
            candidate_id=selected_candidate_id,
            voter_hash=voter_hash
        )

        db.session.add(vote_record)
        db.session.add(anonymized_vote)
        db.session.commit()

        AuditLog.log('VOTE_CAST', f"Anonymized vote cast in election ID {election_id}", user_id=current_user.id)

        # Broadcast WebSocket live vote update event across all connected clients
        if HAS_SOCKETIO and socketio:
            try:
                candidates_list = Candidate.query.filter_by(election_id=election_id).all()
                tot_v = election.total_votes
                c_data = []
                for c in candidates_list:
                    cnt = c.vote_count
                    pct = round((cnt / tot_v * 100), 2) if tot_v > 0 else 0
                    c_data.append({'id': c.id, 'name': c.name, 'party': c.party, 'votes': cnt, 'percentage': pct})
                c_data.sort(key=lambda x: x['votes'], reverse=True)
                socketio.emit('vote_update', {'election_id': election_id, 'total_votes': tot_v, 'candidates': c_data})
            except Exception:
                pass

        flash(f'Your vote for "{candidate.name}" has been recorded successfully!', 'success')
        return redirect(url_for('voter_results', election_id=election_id))

    return render_template('voter/vote.html', election=election, candidates=candidates, form=form)


@app.route('/voter/results/<int:election_id>')
@login_required
def voter_results(election_id):
    election = Election.query.get_or_404(election_id)
    status = election.update_status()

    has_voted = current_user.has_voted_in(election_id)

    if status != 'closed' and not has_voted:
        flash('Election results are hidden until you have cast your vote or the election has ended.', 'warning')
        return redirect(url_for('voter_dashboard'))

    candidates = Candidate.query.filter_by(election_id=election_id).all()
    total_votes = election.total_votes

    results_data = []
    for c in candidates:
        count = c.vote_count
        percentage = round((count / total_votes * 100), 2) if total_votes > 0 else 0
        results_data.append({
            'candidate': c,
            'votes': count,
            'percentage': percentage
        })

    results_data.sort(key=lambda x: x['votes'], reverse=True)

    return render_template('voter/results.html',
                           election=election,
                           results_data=results_data,
                           total_votes=total_votes,
                           has_voted=has_voted)


# ==================== ERROR HANDLERS ====================

@app.errorhandler(404)
def page_not_found(e):
    return render_template('base.html', error_title="404 - Page Not Found", error_msg="The page you requested could not be found."), 404

@app.errorhandler(403)
def forbidden(e):
    return render_template('base.html', error_title="403 - Forbidden", error_msg="You do not have permission to access this resource."), 403

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('base.html', error_title="500 - Server Error", error_msg="An unexpected error occurred. Please try again later."), 500


if __name__ == '__main__':
    with app.app_context():
        init_db()
    print("=" * 65)
    print("  MatDan India - Digital Voting Portal")
    print("  Running locally on: http://localhost:5000 / http://127.0.0.1:5000")
    print("=" * 65)
    if HAS_SOCKETIO and socketio:
        socketio.run(app, host='127.0.0.1', port=5000, debug=True, allow_unsafe_werkzeug=True)
    else:
        app.run(host='127.0.0.1', port=5000, debug=True)


