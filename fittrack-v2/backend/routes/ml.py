"""ML / Smart Insights routes — real user data, no static predictions."""
from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, User, UserProfile, Workout, Meal, WeightLog
from datetime import datetime, timedelta

bp = Blueprint('ml', __name__)


@bp.route('/insights', methods=['GET'])
@jwt_required()
def get_insights():
    try:
        user_id = int(get_jwt_identity())
        user    = db.session.get(User, user_id)
        profile = UserProfile.query.filter_by(user_id=user_id).first()

        today    = datetime.utcnow().date()
        week_ago = today - timedelta(days=7)

        meals    = Meal.query.filter(Meal.user_id == user_id,    Meal.logged_date    >= week_ago).all()
        workouts = Workout.query.filter(Workout.user_id == user_id, Workout.workout_date >= week_ago).all()

        insights = []

        if not meals and not workouts:
            insights.append({'type': 'tip', 'message': 'Start logging workouts and meals to receive personalised insights! 📋'})
            return jsonify({'insights': insights}), 200

        total_cal_in     = sum(m.calories for m in meals)
        total_cal_burned = sum(w.calories for w in workouts)

        # ── BUG FIX 1 & 3: Normalize totals to a full 7-day week ──────────────
        # BUG 3: days_with_data / days_with_workouts were computed but NEVER USED.
        # The raw totals only cover days the user actually logged. If they logged
        # 3 days out of 7, total_cal_in is ~3/7 of a real weekly total, making
        # the balance look like a huge deficit even when eating normally. We
        # extrapolate to 7 days so predictions reflect the user's actual habits.
        days_with_meals    = max(len(set(m.logged_date for m in meals)),    1)
        days_with_workouts = max(len(set(w.workout_date for w in workouts)), 1)

        # Projected weekly totals (extrapolated from logged days)
        weekly_cal_in     = total_cal_in     / days_with_meals    * 7
        weekly_cal_burned = total_cal_burned / days_with_workouts * 7

        # ── BUG FIX 1: Removed double-counting of exercise calories ───────────
        # The previous formula was:
        #   weekly_cal_balance = total_cal_in - weekly_maintenance - total_cal_burned
        # where weekly_maintenance = TDEE * 7.
        # TDEE already incorporates exercise via the activity multiplier (1.2–1.725),
        # so subtracting total_cal_burned a second time counted exercise twice —
        # inflating the apparent deficit by hundreds of kcal per day.
        #
        # Fix: use BMR (no activity multiplier) as the metabolic baseline, then
        # add logged exercise explicitly. This ties predictions directly to real
        # logged workout data instead of a blanket activity estimate.
        if profile and profile.weight and profile.height and profile.age:
            if user.gender == 'male':
                bmr = (10 * profile.weight) + (6.25 * profile.height) - (5 * profile.age) + 5
            else:
                bmr = (10 * profile.weight) + (6.25 * profile.height) - (5 * profile.age) - 161
            weekly_bmr = bmr * 7
        else:
            # Fallback: ~1700 kcal/day BMR for an average adult
            weekly_bmr = 1700 * 7

        # positive = surplus (eating more than you burn), negative = deficit
        weekly_cal_balance = weekly_cal_in - weekly_bmr - weekly_cal_burned

        # ── Insight 1: calorie balance ─────────────────────────────────────────
        if weekly_cal_balance < -300:
            deficit = abs(int(weekly_cal_balance))
            insights.append({'type': 'success',
                              'message': f"You're averaging a weekly deficit of ~{deficit} kcal — great for weight loss! 🔥"})
        elif weekly_cal_balance > 300:
            surplus = int(weekly_cal_balance)
            insights.append({'type': 'info',
                              'message': f"You're in a ~{surplus} kcal weekly surplus — good for muscle gain 💪"})
        else:
            insights.append({'type': 'info',
                              'message': "Calories are well balanced this week — perfect for maintenance ⚖️"})

        # ── Insight 2: weight change prediction ───────────────────────────────
        # BUG FIX 2: Weight change sign was inverted.
        # Old code: projected_change = round(-weekly_cal_balance / 7700, 2)
        # When in a deficit weekly_cal_balance < 0, so -weekly_cal_balance > 0,
        # making projected_change POSITIVE → direction labelled "gain". Wrong.
        # A calorie deficit means the body burns stored fat → weight DECREASES.
        # Fix: remove the negation so the sign matches the balance sign:
        #   surplus  (positive balance) → positive change → weight gain  ✓
        #   deficit  (negative balance) → negative change → weight loss  ✓
        projected_change = round(weekly_cal_balance / 7700, 2)   # 7700 kcal ≈ 1 kg fat
        if abs(projected_change) >= 0.1:
            sign      = '+' if projected_change > 0 else ''
            direction = 'gain' if projected_change > 0 else 'loss'
            insights.append({'type': 'prediction',
                              'message': f"Projected weight {direction} this week: {sign}{projected_change} kg 📊"})

        # ── Insight 3: workout frequency ──────────────────────────────────────
        workout_sessions = len(workouts)
        if workout_sessions >= 5:
            insights.append({'type': 'success',
                              'message': f"Excellent workout frequency — {workout_sessions} sessions this week! 🏆"})
        elif workout_sessions >= 3:
            insights.append({'type': 'success',
                              'message': f"Good consistency — {workout_sessions} workouts this week 💪"})
        else:
            needed = 3 - workout_sessions
            insights.append({'type': 'tip',
                              'message': f"Try to fit in {needed} more workout{'s' if needed > 1 else ''} this week for best results 🎯"})

        # ── Insight 4: protein target ─────────────────────────────────────────
        if profile and profile.weight:
            protein_g = int(profile.weight * 1.6)
            insights.append({'type': 'tip',
                              'message': f"Aim for ~{protein_g}g of protein daily to support your goal 🥩"})

        # ── Insight 5: goal context ───────────────────────────────────────────
        goal_map = {
            'weight_loss': 'Your goal is weight loss — maintain a consistent calorie deficit 🎯',
            'muscle_gain': "Your goal is muscle gain — ensure you're eating enough protein and in a slight surplus 💪",
            'maintenance': 'Your goal is maintenance — keep calories balanced with activity ⚖️',
        }
        if user.goal in goal_map:
            insights.append({'type': 'info', 'message': goal_map[user.goal]})

        return jsonify({'insights': insights, 'weekly_cal_balance': round(weekly_cal_balance)}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/calorie-recommendation', methods=['GET'])
@jwt_required()
def get_calorie_recommendation():
    try:
        user_id = int(get_jwt_identity())
        user    = db.session.get(User, user_id)
        profile = UserProfile.query.filter_by(user_id=user_id).first()

        if not profile or not all([profile.weight, profile.height, profile.age]):
            return jsonify({'error': 'Complete your profile (weight, height, age) first'}), 400

        if user.gender == 'male':
            bmr = (10 * profile.weight) + (6.25 * profile.height) - (5 * profile.age) + 5
        else:
            bmr = (10 * profile.weight) + (6.25 * profile.height) - (5 * profile.age) - 161

        multipliers = {'sedentary': 1.2, 'light': 1.375, 'moderate': 1.55, 'active': 1.725}
        tdee   = int(bmr * multipliers.get(profile.activity_level or 'moderate', 1.55))
        target = tdee - 500 if user.goal == 'weight_loss' else (tdee + 300 if user.goal == 'muscle_gain' else tdee)

        return jsonify({'bmr': int(bmr), 'tdee': tdee, 'target_calories': target, 'goal': user.goal}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
