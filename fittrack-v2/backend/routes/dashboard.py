"""Dashboard routes v2 — includes BMI, BMR, water, streaks, progress."""
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, User, UserProfile, Workout, Meal, WeightLog, Achievement, WaterLog, Streak
from utils.date_utils import get_user_today, get_user_week_start
from datetime import timedelta

bp = Blueprint('dashboard', __name__)

def calc_bmr(weight, height, age, gender):
    """Mifflin-St Jeor formula"""
    if not all([weight, height, age]): return None
    bmr = 10*weight + 6.25*height - 5*age
    return round(bmr + 5 if gender == 'male' else bmr - 161, 0)

def calc_tdee(bmr, activity_level):
    multipliers = {'sedentary':1.2,'light':1.375,'moderate':1.55,'active':1.725,'very_active':1.9}
    return round(bmr * multipliers.get(activity_level, 1.55)) if bmr else None

@bp.route('/summary', methods=['GET'])
@jwt_required()
def get_summary():
    try:
        user_id    = int(get_jwt_identity())
        user       = db.session.get(User, user_id)
        profile    = UserProfile.query.filter_by(user_id=user_id).first()
        today      = get_user_today()
        week_start = get_user_week_start(today)

        today_meals    = Meal.query.filter(Meal.user_id==user_id, Meal.logged_date==today).all()
        calories_in    = sum(m.calories for m in today_meals)
        today_workouts = Workout.query.filter(Workout.user_id==user_id, Workout.workout_date==today).all()
        calories_burned= sum(w.calories for w in today_workouts)

        # BMI + BMR
        bmi = bmr = tdee = None
        if profile and profile.weight and profile.height:
            bmi = round(profile.weight / ((profile.height/100)**2), 1)
        if profile and profile.weight and profile.height and profile.age:
            bmr  = calc_bmr(profile.weight, profile.height, profile.age, user.gender or 'male')
            tdee = calc_tdee(bmr, profile.activity_level or 'moderate')

        # Weekly
        week_workouts = Workout.query.filter(Workout.user_id==user_id,
            Workout.workout_date>=week_start, Workout.workout_date<=today).all()
        week_meals = Meal.query.filter(Meal.user_id==user_id,
            Meal.logged_date>=week_start, Meal.logged_date<=today).all()

        daily_cal_goal      = (profile.daily_calorie_goal  if profile else None) or 2000
        weekly_workout_goal = (profile.weekly_workout_goal if profile else None) or 5

        # Water
        water_logs  = WaterLog.query.filter_by(user_id=user_id, logged_date=today).all()
        water_today = sum(l.amount_ml for l in water_logs)
        water_goal  = (profile.daily_water_goal_ml if profile else None) or 2500

        # Streaks
        streak = Streak.query.filter_by(user_id=user_id).first()

        today_workout_list = [
            {**w.to_dict(), 'status': 'Done' if w.completed else 'Upcoming'}
            for w in sorted(today_workouts, key=lambda x: x.logged_at, reverse=True)
        ]

        return jsonify({
            'user':    user.to_dict(),
            'profile': profile.to_dict() if profile else {},
            'calories_in':          calories_in,
            'calories_burned':      calories_burned,
            'net_calories':         calories_in - calories_burned,
            'calorie_goal':         daily_cal_goal,
            'bmi':                  bmi,
            'bmr':                  bmr,
            'tdee':                 tdee,
            'weekly_workouts':      len(week_workouts),
            'weekly_workout_goal':  weekly_workout_goal,
            'weekly_calories_in':   sum(m.calories for m in week_meals),
            'weekly_calories_burned':sum(w.calories for w in week_workouts),
            'weekly_cal_target':    daily_cal_goal * 7,
            'water_today_ml':       water_today,
            'water_goal_ml':        water_goal,
            'water_percent':        round(min(water_today/water_goal*100,100),1),
            'streaks':              streak.to_dict() if streak else {},
            'today_workouts':       today_workout_list,
            'resolved_today':       today.isoformat(),
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/bmi-bmr', methods=['GET'])
@jwt_required()
def get_bmi_bmr():
    try:
        user_id = int(get_jwt_identity())
        user    = db.session.get(User, user_id)
        profile = UserProfile.query.filter_by(user_id=user_id).first()
        if not profile:
            return jsonify({'error':'No profile found. Please complete your profile first.'}), 404

        bmi = bmi_category = bmr = tdee = suggested_calories = None

        if profile.weight and profile.height:
            bmi = round(profile.weight / ((profile.height/100)**2), 1)
            if bmi < 18.5:    bmi_category = 'Underweight'
            elif bmi < 25:    bmi_category = 'Normal weight'
            elif bmi < 30:    bmi_category = 'Overweight'
            else:             bmi_category = 'Obese'

        if profile.weight and profile.height and profile.age:
            bmr  = calc_bmr(profile.weight, profile.height, profile.age, user.gender or 'male')
            tdee = calc_tdee(bmr, profile.activity_level or 'moderate')
            goal = user.goal or 'weight_loss'
            if tdee:
                if goal == 'weight_loss':     suggested_calories = tdee - 500
                elif goal == 'muscle_gain':   suggested_calories = tdee + 300
                else:                         suggested_calories = tdee

        return jsonify({
            'bmi': bmi, 'bmi_category': bmi_category,
            'bmr': bmr, 'tdee': tdee,
            'suggested_calories': suggested_calories,
            'goal': user.goal,
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/weight-history', methods=['GET'])
@jwt_required()
def get_weight_history():
    try:
        user_id = int(get_jwt_identity())
        today   = get_user_today()
        cutoff  = today - timedelta(days=30)
        logs    = WeightLog.query.filter(WeightLog.user_id==user_id,
                    WeightLog.logged_date>=cutoff).order_by(WeightLog.logged_date.asc()).all()
        result = []
        for l in logs:
            d = l.to_dict()
            # Ensure date is an ISO string for the frontend
            if 'date' not in d or not d['date']:
                d['date'] = l.logged_date.isoformat() if l.logged_date else None
            result.append(d)
        return jsonify({'weight_logs': result}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/achievements', methods=['GET'])
@jwt_required()
def get_achievements():
    try:
        user_id = int(get_jwt_identity())
        from utils.achievements import ALL_ACHIEVEMENTS, evaluate_achievements
        evaluate_achievements(user_id)
        earned  = {a.key: a for a in Achievement.query.filter_by(user_id=user_id).all()}
        result  = []
        for key, name, emoji in ALL_ACHIEVEMENTS:
            if key in earned:
                result.append({**earned[key].to_dict(), 'earned': True})
            else:
                result.append({'key':key,'name':name,'emoji':emoji,'earned':False,'earned_at':None})
        return jsonify({'achievements': result}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/weekly-chart', methods=['GET'])
@jwt_required()
def get_weekly_chart():
    try:
        user_id    = int(get_jwt_identity())
        today      = get_user_today()
        week_start = get_user_week_start(today)
        workouts = Workout.query.filter(Workout.user_id==user_id,
                    Workout.workout_date>=week_start, Workout.workout_date<=today).all()
        meals    = Meal.query.filter(Meal.user_id==user_id,
                    Meal.logged_date>=week_start, Meal.logged_date<=today).all()
        burned_by_day = [0]*7
        intake_by_day = [0]*7
        water_by_day  = [0]*7
        for w in workouts:
            idx = (w.workout_date - week_start).days
            if 0 <= idx < 7: burned_by_day[idx] += w.calories
        for m in meals:
            idx = (m.logged_date - week_start).days
            if 0 <= idx < 7: intake_by_day[idx] += m.calories
        water_logs = WaterLog.query.filter(WaterLog.user_id==user_id,
                    WaterLog.logged_date>=week_start, WaterLog.logged_date<=today).all()
        for wl in water_logs:
            idx = (wl.logged_date - week_start).days
            if 0 <= idx < 7: water_by_day[idx] += wl.amount_ml
        return jsonify({
            'labels': ['Mon','Tue','Wed','Thu','Fri','Sat','Sun'],
            'burned': burned_by_day,
            'intake': intake_by_day,
            'water':  water_by_day,
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
