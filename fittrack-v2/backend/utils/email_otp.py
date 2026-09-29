"""
FitTrack Pro — Email OTP Utility
Handles OTP generation, email sending via Gmail SMTP, and DB persistence.
"""
import os
import random
import string
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timedelta
from models import db, OTPStore

# ── Constants ──────────────────────────────────────────────────────────────
OTP_EXPIRY_MINUTES = 5
MAX_ATTEMPTS       = 3

# ── Helpers ────────────────────────────────────────────────────────────────

def generate_otp(length: int = 6) -> str:
    """Return a cryptographically-safe numeric OTP."""
    return ''.join(random.choices(string.digits, k=length))


def _get_smtp_credentials():
    username = os.environ.get('MAIL_USERNAME', '').strip()
    password = os.environ.get('MAIL_PASSWORD', '').strip()
    if not username or not password:
        raise EnvironmentError(
            "MAIL_USERNAME and MAIL_PASSWORD must be set in your .env file. "
            "Use a Gmail App Password (not your regular password)."
        )
    return username, password


def send_otp_email(recipient_email: str, otp: str, purpose: str) -> None:
    """
    Send a styled OTP email via Gmail SMTP (TLS on port 587).
    purpose: 'register' | 'reset'
    """
    username, password = _get_smtp_credentials()

    subject_map = {
        'register': '🔐 Verify Your FitTrack Account',
        'reset':    '🔑 FitTrack Password Reset OTP',
    }
    action_map = {
        'register': 'complete your registration',
        'reset':    'reset your password',
    }
    subject = subject_map.get(purpose, '🔐 Your FitTrack OTP')
    action  = action_map.get(purpose, 'continue')

    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="UTF-8">
      <style>
        body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #0f0f0f; color: #e0e0e0; margin: 0; padding: 0; }}
        .wrapper {{ max-width: 520px; margin: 40px auto; background: #1a1a1a; border-radius: 16px;
                   border: 1px solid #2a2a2a; overflow: hidden; }}
        .header  {{ background: linear-gradient(135deg, #f4501e, #e03a10); padding: 32px 40px; text-align: center; }}
        .logo    {{ font-size: 28px; font-weight: 900; letter-spacing: 3px; color: #fff; }}
        .logo span {{ color: #ffd0c0; }}
        .body    {{ padding: 36px 40px; }}
        h2       {{ margin: 0 0 8px; font-size: 20px; color: #fff; }}
        p        {{ margin: 0 0 20px; color: #aaa; line-height: 1.6; font-size: 14px; }}
        .otp-box {{ background: #111; border: 2px dashed #f4501e; border-radius: 12px;
                   text-align: center; padding: 24px; margin: 24px 0; }}
        .otp-code{{ font-size: 42px; font-weight: 900; letter-spacing: 12px;
                   color: #f4501e; font-family: monospace; }}
        .expiry  {{ font-size: 13px; color: #666; margin-top: 8px; }}
        .warning {{ background: rgba(244,80,30,0.08); border-left: 3px solid #f4501e;
                   border-radius: 4px; padding: 12px 16px; font-size: 13px; color: #aaa; }}
        .footer  {{ padding: 20px 40px; border-top: 1px solid #222; text-align: center;
                   font-size: 12px; color: #555; }}
      </style>
    </head>
    <body>
      <div class="wrapper">
        <div class="header">
          <div class="logo">FIT<span>TRACK</span></div>
        </div>
        <div class="body">
          <h2>Your One-Time Password</h2>
          <p>Use the code below to {action}. It expires in <strong>{OTP_EXPIRY_MINUTES} minutes</strong>.</p>
          <div class="otp-box">
            <div class="otp-code">{otp}</div>
            <div class="expiry">⏳ Valid for {OTP_EXPIRY_MINUTES} minutes &nbsp;|&nbsp; Max {MAX_ATTEMPTS} attempts</div>
          </div>
          <div class="warning">
            ⚠️  Never share this code. FitTrack will never ask for it over the phone or chat.
            If you did not request this, you can safely ignore this email.
          </div>
        </div>
        <div class="footer">© FitTrack Pro &nbsp;·&nbsp; This is an automated message, do not reply.</div>
      </div>
    </body>
    </html>
    """

    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From']    = f'FitTrack Pro <{username}>'
    msg['To']      = recipient_email
    msg.attach(MIMEText(html_body, 'html'))

    with smtplib.SMTP('smtp.gmail.com', 587) as server:
        server.ehlo()
        server.starttls()
        server.login(username, password)
        server.sendmail(username, recipient_email, msg.as_string())


# ── DB helpers ────────────────────────────────────────────────────────────

def store_otp(email: str, otp: str, purpose: str) -> None:
    """Upsert OTP record for (email, purpose). Replaces any existing one."""
    # Remove any previous OTP for this email+purpose
    OTPStore.query.filter_by(email=email, purpose=purpose).delete()
    record = OTPStore(
        email      = email,
        otp_code   = otp,
        purpose    = purpose,
        attempts   = 0,
        expires_at = datetime.utcnow() + timedelta(minutes=OTP_EXPIRY_MINUTES),
    )
    db.session.add(record)
    db.session.commit()


def verify_otp(email: str, submitted_otp: str, purpose: str) -> dict:
    """
    Verify submitted OTP.
    Returns {'ok': True} on success.
    Returns {'ok': False, 'error': str, 'attempts_left': int} on failure.
    """
    record = OTPStore.query.filter_by(email=email, purpose=purpose).first()

    if not record:
        return {'ok': False, 'error': 'No OTP found. Please request a new one.', 'attempts_left': 0}

    if record.is_expired():
        OTPStore.query.filter_by(email=email, purpose=purpose).delete()
        db.session.commit()
        return {'ok': False, 'error': 'OTP has expired. Please request a new one.', 'attempts_left': 0}

    if record.attempts >= MAX_ATTEMPTS:
        OTPStore.query.filter_by(email=email, purpose=purpose).delete()
        db.session.commit()
        return {'ok': False, 'error': 'Too many failed attempts. Please request a new OTP.', 'attempts_left': 0}

    if record.otp_code != submitted_otp.strip():
        record.increment_attempt()
        db.session.commit()
        attempts_left = MAX_ATTEMPTS - record.attempts
        return {
            'ok': False,
            'error': f'Incorrect OTP. {attempts_left} attempt(s) remaining.',
            'attempts_left': attempts_left,
        }

    # ✅ OTP correct — clean up
    OTPStore.query.filter_by(email=email, purpose=purpose).delete()
    db.session.commit()
    return {'ok': True}


def can_resend_otp(email: str, purpose: str) -> bool:
    """Return True if a new OTP can be requested (old one expired or missing)."""
    record = OTPStore.query.filter_by(email=email, purpose=purpose).first()
    return record is None or record.is_expired()
