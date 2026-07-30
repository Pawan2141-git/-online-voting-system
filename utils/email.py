from flask import url_for, current_app, flash
from flask_mail import Message
from markupsafe import Markup
from datetime import datetime

def send_verification_email(user, mail_instance=None):
    """Generates an email verification token and sends verification email."""
    token = user.get_verification_token()
    verify_url = url_for('verify_email', token=token, _external=True)
    
    user.verification_sent_at = datetime.utcnow()
    
    subject = "Verify Your Account - MatDan Electoral Portal India"
    sender = current_app.config.get('MAIL_DEFAULT_SENDER', ('MatDan Electoral Portal', 'noreply@matdan-india.gov.in'))
    
    html_body = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: auto; padding: 20px; border: 1px solid #E2E8F0; border-radius: 10px;">
        <h2 style="color: #002B66; text-align: center;">MatDan India - Digital Electoral Portal</h2>
        <hr style="border: none; border-top: 3px solid #FF9933; margin-bottom: 20px;">
        <p>Namaste <strong>{user.full_name}</strong>,</p>
        <p>Thank you for registering on the official <strong>MatDan India Digital Voting Portal</strong> (EPIC No: <strong>{user.voter_id}</strong>).</p>
        <p>To activate your voter account and participate in upcoming elections, please verify your email address by clicking the button below:</p>
        <div style="text-align: center; margin: 30px 0;">
            <a href="{verify_url}" style="background-color: #FF9933; color: white; padding: 12px 28px; text-decoration: none; border-radius: 50px; font-weight: bold; display: inline-block;">Verify My Voter Account</a>
        </div>
        <p style="font-size: 0.85em; color: #64748B;">This verification link will expire in 1 hour. If you did not create an account on MatDan Portal, please ignore this email.</p>
        <hr style="border: none; border-top: 1px solid #E2E8F0; margin-top: 30px;">
        <p style="font-size: 0.75em; color: #94A3B8; text-align: center;">Election Commission Information Infrastructure &copy; 2026</p>
    </div>
    """

    msg = Message(
        subject=subject,
        recipients=[user.email],
        html=html_body,
        sender=sender
    )

    try:
        if mail_instance:
            mail_instance.send(msg)
        else:
            from app import mail
            mail.send(msg)
        current_app.logger.info(f"Verification email successfully sent to {user.email}")
    except Exception as e:
        current_app.logger.warning(f"Could not send email via SMTP ({e}). Providing direct link for verification: {verify_url}")
        flash(Markup(f'Local Demo Notice: Email server not connected. Click here to verify account: <a href="{verify_url}" class="alert-link">{verify_url}</a>'), 'info')
    
    return verify_url


