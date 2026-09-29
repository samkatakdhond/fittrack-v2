"""Profile routes"""
import os
import uuid
from flask import Blueprint, request, jsonify, send_from_directory, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, User, UserProfile
from datetime import datetime

ALLOWED_EXT = {'jpg', 'jpeg', 'png', 'gif', 'webp'}
MAX_SIZE_MB  = 3

bp = Blueprint('profile', __name__)


def _get_user(user_id):
    return db.session.get(User, user_id)


@bp.route('', methods=['GET'])
@jwt_required()
def get_profile():
    try:
        user_id = int(get_jwt_identity())
        user    = _get_user(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        profile = UserProfile.query.filter_by(user_id=user_id).first()
        return jsonify({'user': user.to_dict(), 'profile': profile.to_dict() if profile else {}}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('', methods=['PUT'])
@jwt_required()
def update_profile():
    try:
        user_id = int(get_jwt_identity())
        user    = _get_user(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        data = request.get_json()
        if 'name'   in data: user.name   = data['name']
        if 'gender' in data: user.gender = data['gender']
        if 'goal'   in data: user.goal   = data['goal']

        profile = UserProfile.query.filter_by(user_id=user_id).first()
        if not profile:
            profile = UserProfile(user_id=user_id)
            db.session.add(profile)

        if 'age'            in data: profile.age            = data['age']
        if 'activity_level' in data: profile.activity_level = data['activity_level']

        db.session.commit()
        return jsonify({'message': 'Profile updated', 'user': user.to_dict(), 'profile': profile.to_dict()}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@bp.route('/metrics', methods=['PUT'])
@jwt_required()
def update_metrics():
    try:
        user_id = int(get_jwt_identity())
        data    = request.get_json()

        profile = UserProfile.query.filter_by(user_id=user_id).first()
        if not profile:
            profile = UserProfile(user_id=user_id)
            db.session.add(profile)

        if 'height'        in data: profile.height        = float(data['height'])
        if 'weight'        in data:
            new_weight = float(data['weight'])
            profile.weight = new_weight
            # Record historical weight entry so the weight-history chart has real data
            from models import WeightLog
            today = datetime.utcnow().date()
            existing = WeightLog.query.filter_by(user_id=user_id, logged_date=today).first()
            if existing:
                existing.weight = new_weight   # update today's entry if already logged
            else:
                db.session.add(WeightLog(user_id=user_id, weight=new_weight, logged_date=today))
        if 'target_weight' in data: profile.target_weight = float(data['target_weight'])
        if 'goal'          in data:
            user = _get_user(user_id)
            user.goal = data['goal']

        db.session.commit()

        bmi = None
        if profile.weight and profile.height:
            bmi = round(profile.weight / ((profile.height / 100) ** 2), 1)

        return jsonify({'message': 'Metrics updated', 'profile': profile.to_dict(), 'bmi': bmi}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@bp.route('/weight-history', methods=['GET'])
@jwt_required()
def get_weight_history():
    """Return the last 30 days of weight entries logged via /metrics updates.
    Each time a user saves their weight in the profile page it is recorded here.
    """
    try:
        user_id = int(get_jwt_identity())
        from models import WeightLog
        from datetime import datetime, timedelta
        thirty_ago = datetime.utcnow().date() - timedelta(days=30)
        entries = WeightLog.query.filter(
            WeightLog.user_id == user_id,
            WeightLog.logged_date >= thirty_ago
        ).order_by(WeightLog.logged_date.asc()).all()
        return jsonify({'entries': [{'date': str(e.logged_date), 'weight': e.weight} for e in entries]}), 200
    except Exception as e:
        # If WeightLog model doesn't exist yet, return empty list gracefully
        return jsonify({'entries': []}), 200





@bp.route('/stats', methods=['GET'])
@jwt_required()
def get_profile_stats():
    """Return real streak, total workouts, and weight progress for the profile hero section."""
    try:
        from models import Workout, WeightLog
        from datetime import timedelta

        user_id = int(get_jwt_identity())

        # ── Total workouts (all time) ──────────────────────────────────────
        all_workouts = Workout.query.filter_by(user_id=user_id).all()
        total_workouts = len(all_workouts)

        # ── Current streak (consecutive days ending today or yesterday) ───
        workout_dates = sorted(set(w.workout_date for w in all_workouts), reverse=True)
        streak = 0
        if workout_dates:
            # FIX: use user's local timezone date, not UTC server date
            from utils.date_utils import get_user_today as _get_today
            today = _get_today()
            # streak is valid only if user worked out today or yesterday
            if workout_dates[0] >= today - timedelta(days=1):
                streak = 1
                for i in range(1, len(workout_dates)):
                    gap = (workout_dates[i - 1] - workout_dates[i]).days
                    if gap == 1:
                        streak += 1
                    else:
                        break   # streak broken

        # ── Weight progress (first log vs latest log) ──────────────────
        logs = WeightLog.query.filter_by(user_id=user_id)                 .order_by(WeightLog.logged_date.asc()).all()
        progress = None
        if len(logs) >= 2:
            change  = round(logs[-1].weight - logs[0].weight, 1)
            sign    = '+' if change > 0 else ''
            progress = f"{sign}{change}kg"
        elif len(logs) == 1:
            progress = f"{logs[0].weight}kg"

        return jsonify({
            'total_workouts': total_workouts,
            'streak':         streak,
            'progress':       progress,
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/avatar', methods=['POST'])
@jwt_required()
def upload_avatar():
    """
    Upload a profile picture.
    Accepts multipart/form-data with field name 'avatar'.
    Saves file to /uploads/avatars/<uuid>.<ext>
    Stores ONLY the filename in DB — never base64 in MySQL.
    """
    user_id = int(get_jwt_identity())
    user    = _get_user(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    if 'avatar' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    f    = request.files['avatar']
    ext  = f.filename.rsplit('.', 1)[-1].lower() if '.' in f.filename else ''
    if ext not in ALLOWED_EXT:
        return jsonify({'error': f'File type .{ext} not allowed. Use jpg/png/gif/webp'}), 400

    # Read bytes to check size
    data = f.read()
    if len(data) > MAX_SIZE_MB * 1024 * 1024:
        return jsonify({'error': f'File too large (max {MAX_SIZE_MB}MB)'}), 400

    # Build save path — uploads/avatars/ inside backend folder
    uploads_dir = os.path.join(current_app.root_path, 'uploads', 'avatars')
    os.makedirs(uploads_dir, exist_ok=True)

    # Delete old avatar file if it exists
    if user.avatar_filename:
        old_path = os.path.join(uploads_dir, user.avatar_filename)
        if os.path.isfile(old_path):
            os.remove(old_path)

    # Save new file as UUID to prevent collisions & path traversal
    filename = f"{uuid.uuid4().hex}.{ext}"
    save_path = os.path.join(uploads_dir, filename)
    with open(save_path, 'wb') as fp:
        fp.write(data)

    # Store ONLY filename in DB
    user.avatar_filename = filename
    db.session.commit()

    return jsonify({
        'message':  'Avatar uploaded',
        'filename': filename,
        'url':      f'/api/profile/avatar/{filename}',
    }), 200


@bp.route('/avatar/<filename>', methods=['GET'])
def serve_avatar(filename):
    """Serve a stored avatar image. No auth required (URL is already a UUID)."""
    # Basic safety: no path traversal
    if '/' in filename or '\\' in filename or '..' in filename:
        return jsonify({'error': 'Invalid filename'}), 400
    uploads_dir = os.path.join(current_app.root_path, 'uploads', 'avatars')
    return send_from_directory(uploads_dir, filename)


@bp.route('/avatar', methods=['DELETE'])
@jwt_required()
def delete_avatar():
    """Remove the user's profile picture and revert to initials."""
    user_id = int(get_jwt_identity())
    user    = _get_user(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    if user.avatar_filename:
        uploads_dir = os.path.join(current_app.root_path, 'uploads', 'avatars')
        old_path    = os.path.join(uploads_dir, user.avatar_filename)
        if os.path.isfile(old_path):
            os.remove(old_path)
        user.avatar_filename = None
        db.session.commit()

    return jsonify({'message': 'Avatar removed'}), 200

@bp.route('/password', methods=['PUT'])
@jwt_required()
def change_password():
    try:
        user_id = int(get_jwt_identity())
        user    = _get_user(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        data = request.get_json()
        if not user.check_password(data.get('currentPassword', '')):
            return jsonify({'error': 'Current password is incorrect'}), 401
        if len(data.get('newPassword', '')) < 8:
            return jsonify({'error': 'Password must be at least 8 characters'}), 400

        user.set_password(data['newPassword'])
        db.session.commit()
        return jsonify({'message': 'Password updated successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
