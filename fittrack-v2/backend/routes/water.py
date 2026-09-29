"""Water intake tracking routes."""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, WaterLog, UserProfile, Streak
from utils.date_utils import get_user_today
from datetime import datetime

bp = Blueprint('water', __name__)

@bp.route('', methods=['GET'])
@jwt_required()
def get_today():
    try:
        user_id = int(get_jwt_identity())
        today   = get_user_today()
        logs    = WaterLog.query.filter_by(user_id=user_id, logged_date=today).all()
        total   = sum(l.amount_ml for l in logs)
        profile = UserProfile.query.filter_by(user_id=user_id).first()
        goal    = (profile.daily_water_goal_ml if profile else None) or 2500
        return jsonify({'total_ml':total,'goal_ml':goal,'logs':[l.to_dict() for l in logs],
                        'percent':round(min(total/goal*100,100),1)}), 200
    except Exception as e:
        return jsonify({'error':str(e)}), 500

@bp.route('', methods=['POST'])
@jwt_required()
def log_water():
    try:
        user_id   = int(get_jwt_identity())
        data      = request.get_json()
        amount_ml = int(data.get('amount_ml', 250))
        today     = get_user_today()
        log = WaterLog(user_id=user_id, amount_ml=amount_ml, logged_date=today)
        db.session.add(log)
        # update water streak
        streak = Streak.query.filter_by(user_id=user_id).first()
        if not streak:
            streak = Streak(user_id=user_id)
            db.session.add(streak)
        from datetime import timedelta
        yesterday = today - timedelta(days=1)
        if streak.last_water_date == yesterday:
            streak.water_streak += 1
        elif streak.last_water_date != today:
            streak.water_streak = 1
        streak.last_water_date = today
        if streak.water_streak > streak.water_best_streak:
            streak.water_best_streak = streak.water_streak
        db.session.commit()
        return jsonify({'message':'Water logged','log':log.to_dict()}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error':str(e)}), 500

@bp.route('/goal', methods=['PUT'])
@jwt_required()
def update_goal():
    try:
        user_id = int(get_jwt_identity())
        data    = request.get_json()
        goal    = int(data.get('daily_water_goal_ml', 2500))
        profile = UserProfile.query.filter_by(user_id=user_id).first()
        if not profile:
            profile = UserProfile(user_id=user_id)
            db.session.add(profile)
        profile.daily_water_goal_ml = goal
        db.session.commit()
        return jsonify({'message':'Water goal updated','goal_ml':goal}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error':str(e)}), 500
