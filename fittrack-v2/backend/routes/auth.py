"""
FitTrack Pro — Authentication Routes with Email OTP MFA
Routes:
  POST /api/auth/register              → Step 1: send OTP, cache registration data
  POST /api/auth/verify-register       → Step 2: verify OTP, create user
  POST /api/auth/resend-otp            → Resend OTP (register or reset)
  POST /api/auth/login                 → Login (requires is_verified=True)
  POST /api/auth/logout                → Logout
  GET  /api/auth/me                    → Current user
  POST /api/auth/forgot-password       → Step 1: send reset OTP
  POST /api/auth/verify-reset-otp      → Step 2: verify OTP
  POST /api/auth/reset-password        → Step 3: set new password
"""
from flask import Blueprint, request, jsonify, session
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from models import db, User, UserProfile, WeightLog
from datetime import datetime
from utils.email_otp import generate_otp, send_otp_email, store_otp, verify_otp

bp = Blueprint('auth', __name__)

# ──────────────────────────────────────────────────────────────────────────
# REGISTRATION — Step 1: Validate form, send OTP, cache pending data
# ──────────────────────────────────────────────────────────────────────────
@bp.route('/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        for field in ['name', 'email', 'password', 'goal']:
            if not data.get(field):
                return jsonify({'error': f'{field} is required'}), 400

        email = data['email'].lower().strip()

        if User.query.filter_by(email=email).first():
            return jsonify({'error': 'Email already registered'}), 400

        # Generate & send OTP
        otp = generate_otp()
        send_otp_email(email, otp, purpose='register')
        store_otp(email, otp, purpose='register')

        # Cache registration data in server-side session (never saved to DB yet)
        session['pending_registration'] = {
            'name':           data['name'],
            'email':          email,
            'password':       data['password'],      # plain — hashed only after OTP verify
            'goal':           data['goal'],
            'gender':         data.get('gender'),
            'height':         data.get('height'),
            'weight':         data.get('weight'),
            'target_weight':  data.get('target_weight'),
            'age':            data.get('age'),
            'activity_level': data.get('activity_level', 'moderate'),
        }

        return jsonify({
            'message': 'OTP sent to your email. Please verify to complete registration.',
            'email':   email,
            'step':    'verify_otp',
        }), 200

    except EnvironmentError as e:
        return jsonify({'error': str(e)}), 500
    except Exception as e:
        return jsonify({'error': f'Failed to send OTP: {str(e)}'}), 500


# ──────────────────────────────────────────────────────────────────────────
# REGISTRATION — Step 2: Verify OTP, create user
# ──────────────────────────────────────────────────────────────────────────
@bp.route('/verify-register', methods=['POST'])
def verify_register():
    try:
        data  = request.get_json()
        email = data.get('email', '').lower().strip()
        otp   = data.get('otp', '').strip()

        if not email or not otp:
            return jsonify({'error': 'Email and OTP are required'}), 400

        result = verify_otp(email, otp, purpose='register')
        if not result['ok']:
            return jsonify({
                'error':         result['error'],
                'attempts_left': result.get('attempts_left', 0),
            }), 400

        # Pull cached registration data
        pending = session.get('pending_registration')
        if not pending or pending.get('email') != email:
            return jsonify({'error': 'Session expired. Please register again.'}), 400

        # Re-check email uniqueness (edge case: parallel registration)
        if User.query.filter_by(email=email).first():
            return jsonify({'error': 'Email already registered'}), 400

        # ── Create verified user ───────────────────────────────────────
        user = User(
            name        = pending['name'],
            email       = email,
            goal        = pending['goal'],
            gender      = pending.get('gender'),
            is_verified = True,
        )
        user.set_password(pending['password'])
        db.session.add(user)
        db.session.flush()

        height        = pending.get('height')
        weight        = pending.get('weight')
        target_weight = pending.get('target_weight')
        age           = pending.get('age')

        profile = UserProfile(
            user_id       = user.id,
            height        = float(height)        if height        else None,
            weight        = float(weight)        if weight        else None,
            target_weight = float(target_weight) if target_weight else None,
            age           = int(age)             if age           else None,
            activity_level= pending.get('activity_level', 'moderate'),
        )
        db.session.add(profile)

        if weight:
            log = WeightLog(
                user_id     = user.id,
                weight      = float(weight),
                logged_date = datetime.utcnow().date(),
            )
            db.session.add(log)

        db.session.commit()
        session.pop('pending_registration', None)

        bmi = None
        if profile.weight and profile.height:
            bmi = round(profile.weight / ((profile.height / 100) ** 2), 1)

        return jsonify({
            'message': 'Account verified and created successfully! You can now log in.',
            'user':    user.to_dict(),
            'bmi':     bmi,
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# ──────────────────────────────────────────────────────────────────────────
# RESEND OTP (shared for register + reset)
# ──────────────────────────────────────────────────────────────────────────
@bp.route('/resend-otp', methods=['POST'])
def resend_otp():
    try:
        data    = request.get_json()
        email   = data.get('email', '').lower().strip()
        purpose = data.get('purpose', 'register')   # 'register' | 'reset'

        if not email:
            return jsonify({'error': 'Email is required'}), 400
        if purpose not in ('register', 'reset'):
            return jsonify({'error': 'Invalid purpose'}), 400

        # For register resend, confirm pending data still exists
        if purpose == 'register':
            pending = session.get('pending_registration')
            if not pending or pending.get('email') != email:
                return jsonify({'error': 'Session expired. Please fill the form again.'}), 400

        # For reset resend, email must exist
        if purpose == 'reset':
            if not User.query.filter_by(email=email).first():
                return jsonify({'error': 'No account found for this email.'}), 404

        otp = generate_otp()
        send_otp_email(email, otp, purpose=purpose)
        store_otp(email, otp, purpose=purpose)

        return jsonify({'message': 'A new OTP has been sent to your email.'}), 200

    except Exception as e:
        return jsonify({'error': f'Failed to resend OTP: {str(e)}'}), 500


# ──────────────────────────────────────────────────────────────────────────
# LOGIN — only allows verified accounts
# ──────────────────────────────────────────────────────────────────────────
@bp.route('/login', methods=['POST'])
def login():
    try:
        data     = request.get_json()
        email    = data.get('email', '').lower().strip()
        password = data.get('password', '')

        if not email or not password:
            return jsonify({'error': 'Email and password required'}), 400

        user = User.query.filter_by(email=email).first()

        if not user or not user.check_password(password):
            return jsonify({'error': 'Invalid email or password'}), 401

        if not user.is_verified:
            return jsonify({
                'error':        'Your account is not verified. Please check your email for the OTP.',
                'unverified':   True,
                'email':        email,
            }), 403

        token = create_access_token(identity=str(user.id))
        return jsonify({
            'message':      'Login successful',
            'access_token': token,
            'user':         user.to_dict(),
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ──────────────────────────────────────────────────────────────────────────
# LOGOUT
# ──────────────────────────────────────────────────────────────────────────
@bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    return jsonify({'message': 'Logout successful'}), 200


# ──────────────────────────────────────────────────────────────────────────
# CURRENT USER
# ──────────────────────────────────────────────────────────────────────────
@bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    try:
        user_id = int(get_jwt_identity())
        user    = db.session.get(User, user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        return jsonify({'user': user.to_dict()}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ──────────────────────────────────────────────────────────────────────────
# FORGOT PASSWORD — Step 1: Send OTP
# ──────────────────────────────────────────────────────────────────────────
@bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    try:
        data  = request.get_json()
        email = data.get('email', '').lower().strip()

        if not email:
            return jsonify({'error': 'Email is required'}), 400

        user = User.query.filter_by(email=email).first()
        # Always return success-like message to prevent email enumeration
        if not user:
            return jsonify({
                'message': 'If this email exists in our system, an OTP will be sent shortly.',
                'email':   email,
                'step':    'verify_otp',
            }), 200

        otp = generate_otp()
        send_otp_email(email, otp, purpose='reset')
        store_otp(email, otp, purpose='reset')

        return jsonify({
            'message': 'OTP sent to your email. Enter it below to reset your password.',
            'email':   email,
            'step':    'verify_otp',
        }), 200

    except Exception as e:
        return jsonify({'error': f'Failed to send OTP: {str(e)}'}), 500


# ──────────────────────────────────────────────────────────────────────────
# FORGOT PASSWORD — Step 2: Verify OTP
# ──────────────────────────────────────────────────────────────────────────
@bp.route('/verify-reset-otp', methods=['POST'])
def verify_reset_otp():
    try:
        data  = request.get_json()
        email = data.get('email', '').lower().strip()
        otp   = data.get('otp', '').strip()

        if not email or not otp:
            return jsonify({'error': 'Email and OTP are required'}), 400

        result = verify_otp(email, otp, purpose='reset')
        if not result['ok']:
            return jsonify({
                'error':         result['error'],
                'attempts_left': result.get('attempts_left', 0),
            }), 400

        # Mark session as reset-authorised
        session['reset_verified_email'] = email
        return jsonify({
            'message': 'OTP verified. You may now set a new password.',
            'step':    'new_password',
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ──────────────────────────────────────────────────────────────────────────
# FORGOT PASSWORD — Step 3: Set new password
# ──────────────────────────────────────────────────────────────────────────
@bp.route('/reset-password', methods=['POST'])
def reset_password():
    try:
        data         = request.get_json()
        email        = data.get('email', '').lower().strip()
        new_password = data.get('new_password', '')

        verified_email = session.get('reset_verified_email')
        if not verified_email or verified_email != email:
            return jsonify({'error': 'Password reset session expired or invalid. Please start again.'}), 403

        if not new_password or len(new_password) < 8:
            return jsonify({'error': 'Password must be at least 8 characters'}), 400

        user = User.query.filter_by(email=email).first()
        if not user:
            return jsonify({'error': 'User not found'}), 404

        user.set_password(new_password)
        db.session.commit()
        session.pop('reset_verified_email', None)

        return jsonify({'message': 'Password reset successfully. You can now log in.'}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
