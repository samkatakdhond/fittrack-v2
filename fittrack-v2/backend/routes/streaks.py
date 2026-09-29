"""Streak and badge routes."""
from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, Streak, Workout, Meal, WaterLog, UserProfile
from utils.date_utils import get_user_today
from datetime import timedelta

bp = Blueprint('streaks', __name__)

BADGES = [
    ('streak_3',    '3-Day Warrior',      '🔥', lambda s: s.workout_streak >= 3),
    ('streak_7',    'Week Champion',       '🏆', lambda s: s.workout_streak >= 7),
    ('streak_30',   '30-Day Legend',       '👑', lambda s: s.workout_streak >= 30),
    ('hydrated_7',  'Hydration Hero',      '💧', lambda s: s.water_streak >= 7),
    ('diet_7',      'Clean Eater',         '🥗', lambda s: s.diet_streak >= 7),
    ('best_10',     'Personal Best ×10',   '⭐', lambda s: s.workout_best_streak >= 10),
]

def _update_streaks(user_id):
    today   = get_user_today()
    streak  = Streak.query.filter_by(user_id=user_id).first()
    if not streak:
        streak = Streak(user_id=user_id)
        db.session.add(streak)

    yesterday = today - timedelta(days=1)

    # Workout streak
    had_workout = Workout.query.filter_by(user_id=user_id, workout_date=today).first() is not None
    if had_workout:
        if streak.last_workout_date == yesterday:
            streak.workout_streak += 1
        elif streak.last_workout_date != today:
            streak.workout_streak = 1
        streak.last_workout_date = today
        streak.workout_best_streak = max(streak.workout_streak, streak.workout_best_streak)
    elif streak.last_workout_date and streak.last_workout_date < yesterday:
        streak.workout_streak = 0

    # Diet streak
    had_meal = Meal.query.filter_by(user_id=user_id, logged_date=today).first() is not None
    if had_meal:
        if streak.last_diet_date == yesterday:
            streak.diet_streak += 1
        elif streak.last_diet_date != today:
            streak.diet_streak = 1
        streak.last_diet_date = today
        streak.diet_best_streak = max(streak.diet_streak, streak.diet_best_streak)
    elif streak.last_diet_date and streak.last_diet_date < yesterday:
        streak.diet_streak = 0

    db.session.commit()
    return streak

@bp.route('', methods=['GET'])
@jwt_required()
def get_streaks():
    try:
        user_id = int(get_jwt_identity())
        streak  = _update_streaks(user_id)
        badges  = [{'key':k,'name':n,'emoji':e,'earned': fn(streak)} for k,n,e,fn in BADGES]
        return jsonify({'streaks': streak.to_dict(), 'badges': badges}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
