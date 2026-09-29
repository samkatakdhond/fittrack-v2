"""Meal routes — timezone-aware date logging."""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, Meal
from utils.date_utils import get_user_today
from datetime import datetime, timedelta

bp = Blueprint('meals', __name__)


@bp.route('', methods=['POST'])
@jwt_required()
def log_meal():
    try:
        user_id = int(get_jwt_identity())
        data    = request.get_json()

        # FIX 2: Use user's local date (tz_offset from body or query param), not UTC
        try:
            tz_offset = int(data.get('tz_offset', request.args.get('tz_offset', 0)))
        except (TypeError, ValueError):
            tz_offset = 0
        local_today = (datetime.utcnow() + timedelta(minutes=tz_offset)).date()

        meal = Meal(
            user_id=user_id,
            meal_type=data['type'],
            food_name=data['name'],
            calories=int(data['calories']),
            category=data.get('category'),
            logged_date=local_today          # ← local date, not UTC
        )
        db.session.add(meal)
        db.session.commit()
        return jsonify({'message': 'Meal logged', 'meal': meal.to_dict()}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@bp.route('', methods=['GET'])
@jwt_required()
def get_meals():
    try:
        user_id  = int(get_jwt_identity())
        date_str = request.args.get('date')
        # FIX 2: fall back to user's local today, not UTC
        if date_str:
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
        else:
            date = get_user_today()
        meals = (Meal.query
                 .filter(Meal.user_id == user_id, Meal.logged_date == date)
                 .order_by(Meal.logged_at).all())
        return jsonify({'meals': [m.to_dict() for m in meals], 'date': date.isoformat()}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/<int:meal_id>', methods=['DELETE'])
@jwt_required()
def delete_meal(meal_id):
    try:
        user_id = int(get_jwt_identity())
        meal    = Meal.query.filter_by(id=meal_id, user_id=user_id).first()
        if not meal:
            return jsonify({'error': 'Meal not found'}), 404
        db.session.delete(meal)
        db.session.commit()
        return jsonify({'message': 'Meal deleted'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
