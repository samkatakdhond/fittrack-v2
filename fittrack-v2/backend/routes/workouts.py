"""Workout routes — timezone-aware date logging."""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, Workout
from utils.achievements import evaluate_achievements
from utils.date_utils import get_user_today
from datetime import datetime, timedelta

bp = Blueprint('workouts', __name__)


@bp.route('', methods=['POST'])
@jwt_required()
def log_workout():
    try:
        user_id = int(get_jwt_identity())
        data    = request.get_json()

        # Use user's local date (passed as tz_offset in body or query param)
        try:
            tz_offset = int(data.get('tz_offset', request.args.get('tz_offset', 0)))
        except (TypeError, ValueError):
            tz_offset = 0

        from datetime import timedelta
        local_today = (datetime.utcnow() + timedelta(minutes=tz_offset)).date()

        workout = Workout(
            user_id=user_id,
            type=data['type'],
            duration=int(data['duration']),
            intensity=data['intensity'],
            calories=int(data['calories']),
            completed=data.get('completed', True),
            workout_date=local_today,          # ← local date, not UTC
        )
        db.session.add(workout)
        db.session.commit()

        new_achievements = evaluate_achievements(user_id)

        return jsonify({
            'message': 'Workout logged',
            'workout': workout.to_dict(),
            'new_achievements': new_achievements,
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@bp.route('/<int:workout_id>/complete', methods=['PUT'])
@jwt_required()
def mark_complete(workout_id):
    try:
        user_id = int(get_jwt_identity())
        workout = Workout.query.filter_by(id=workout_id, user_id=user_id).first()
        if not workout:
            return jsonify({'error': 'Workout not found'}), 404
        workout.completed = True
        db.session.commit()
        new_achievements = evaluate_achievements(user_id)
        return jsonify({'message': 'Marked as complete', 'workout': workout.to_dict(), 'new_achievements': new_achievements}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@bp.route('', methods=['GET'])
@jwt_required()
def get_workouts():
    try:
        user_id    = int(get_jwt_identity())
        days       = request.args.get('days', type=int, default=30)
        today      = get_user_today()
        start_date = today - timedelta(days=days)
        workouts   = (Workout.query
                      .filter(Workout.user_id == user_id, Workout.workout_date >= start_date)
                      .order_by(Workout.logged_at.desc()).all())
        return jsonify({'workouts': [w.to_dict() for w in workouts]}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/stats', methods=['GET'])
@jwt_required()
def get_stats():
    try:
        user_id    = int(get_jwt_identity())
        days       = request.args.get('days', type=int, default=7)
        today      = get_user_today()
        start_date = today - timedelta(days=days)
        workouts   = Workout.query.filter(
            Workout.user_id == user_id,
            Workout.workout_date >= start_date
        ).all()
        return jsonify({
            'total_sessions': len(workouts),
            'total_duration': sum(w.duration for w in workouts),
            'total_calories': sum(w.calories for w in workouts),
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
