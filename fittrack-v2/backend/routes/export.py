"""
Data Export Routes
GET /api/export/csv   → download fitness data as CSV
GET /api/export/pdf   → download fitness report as PDF (HTML-based)
"""
import io, csv
from flask import Blueprint, make_response, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, User, UserProfile, Workout, Meal, WeightLog, WaterLog
from datetime import datetime

bp = Blueprint('export', __name__)

@bp.route('/csv', methods=['GET'])
@jwt_required()
def export_csv():
    try:
        user_id = int(get_jwt_identity())
        user    = db.session.get(User, user_id)

        output  = io.StringIO()
        writer  = csv.writer(output)

        # Workouts
        writer.writerow(['=== WORKOUTS ==='])
        writer.writerow(['Date','Type','Duration (min)','Intensity','Calories Burned'])
        for w in Workout.query.filter_by(user_id=user_id).order_by(Workout.workout_date.desc()).all():
            writer.writerow([w.workout_date, w.type, w.duration, w.intensity, w.calories])

        writer.writerow([])

        # Meals
        writer.writerow(['=== MEALS ==='])
        writer.writerow(['Date','Meal Type','Food','Calories','Category'])
        for m in Meal.query.filter_by(user_id=user_id).order_by(Meal.logged_date.desc()).all():
            writer.writerow([m.logged_date, m.meal_type, m.food_name, m.calories, m.category or ''])

        writer.writerow([])

        # Weight
        writer.writerow(['=== WEIGHT LOG ==='])
        writer.writerow(['Date','Weight (kg)'])
        for wl in WeightLog.query.filter_by(user_id=user_id).order_by(WeightLog.logged_date.desc()).all():
            writer.writerow([wl.logged_date, wl.weight])

        writer.writerow([])

        # Water
        writer.writerow(['=== WATER LOG ==='])
        writer.writerow(['Date','Amount (ml)'])
        for w in WaterLog.query.filter_by(user_id=user_id).order_by(WaterLog.logged_date.desc()).all():
            writer.writerow([w.logged_date, w.amount_ml])

        output.seek(0)
        resp = make_response(output.getvalue())
        fname = f"fittrack_{user.name.replace(' ','_')}_{datetime.utcnow().strftime('%Y%m%d')}.csv"
        resp.headers['Content-Type']        = 'text/csv'
        resp.headers['Content-Disposition'] = f'attachment; filename="{fname}"'
        return resp
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/pdf', methods=['GET'])
@jwt_required()
def export_pdf():
    try:
        user_id = int(get_jwt_identity())
        user    = db.session.get(User, user_id)
        profile = UserProfile.query.filter_by(user_id=user_id).first()

        workouts = Workout.query.filter_by(user_id=user_id).order_by(Workout.workout_date.desc()).limit(20).all()
        meals    = Meal.query.filter_by(user_id=user_id).order_by(Meal.logged_date.desc()).limit(20).all()
        weights  = WeightLog.query.filter_by(user_id=user_id).order_by(WeightLog.logged_date.desc()).limit(10).all()

        bmi = None
        if profile and profile.weight and profile.height:
            bmi = round(profile.weight / ((profile.height / 100) ** 2), 1)

        total_cal_burned = sum(w.calories for w in workouts)
        total_cal_in     = sum(m.calories for m in meals)

        workout_rows = ''.join(
            f'<tr><td>{w.workout_date}</td><td>{w.type}</td>'
            f'<td>{w.duration} min</td><td>{w.intensity}</td><td>{w.calories}</td></tr>'
            for w in workouts)

        meal_rows = ''.join(
            f'<tr><td>{m.logged_date}</td><td>{m.meal_type}</td>'
            f'<td>{m.food_name}</td><td>{m.calories}</td></tr>'
            for m in meals)

        weight_rows = ''.join(
            f'<tr><td>{wl.logged_date}</td><td>{wl.weight} kg</td></tr>'
            for wl in weights)

        html = f"""<!DOCTYPE html><html><head><meta charset="UTF-8">
<title>FitTrack Report</title>
<style>
  body{{font-family:Arial,sans-serif;color:#222;padding:30px;max-width:900px;margin:0 auto}}
  h1{{color:#f4501e;font-size:2rem;border-bottom:3px solid #f4501e;padding-bottom:10px}}
  h2{{color:#333;font-size:1.2rem;margin-top:30px;border-left:4px solid #f4501e;padding-left:10px}}
  .stats{{display:flex;gap:20px;flex-wrap:wrap;margin:20px 0}}
  .stat{{background:#f9f9f9;border:1px solid #ddd;border-radius:8px;padding:15px 20px;min-width:150px}}
  .stat-val{{font-size:1.8rem;font-weight:700;color:#f4501e}}
  .stat-lbl{{font-size:0.8rem;color:#666;text-transform:uppercase}}
  table{{width:100%;border-collapse:collapse;margin-top:10px;font-size:0.85rem}}
  th{{background:#f4501e;color:#fff;padding:8px 10px;text-align:left}}
  td{{border-bottom:1px solid #eee;padding:7px 10px}}
  tr:nth-child(even){{background:#f9f9f9}}
  .footer{{margin-top:40px;font-size:0.75rem;color:#aaa;text-align:center;border-top:1px solid #eee;padding-top:15px}}
</style></head><body>
<h1>🏋️ FitTrack Pro — Fitness Report</h1>
<p><strong>Name:</strong> {user.name} &nbsp;|&nbsp;
   <strong>Email:</strong> {user.email} &nbsp;|&nbsp;
   <strong>Generated:</strong> {datetime.utcnow().strftime('%d %b %Y')}</p>
<div class="stats">
  <div class="stat"><div class="stat-val">{len(workouts)}</div><div class="stat-lbl">Workouts</div></div>
  <div class="stat"><div class="stat-val">{total_cal_burned}</div><div class="stat-lbl">Cal Burned</div></div>
  <div class="stat"><div class="stat-val">{total_cal_in}</div><div class="stat-lbl">Cal Consumed</div></div>
  <div class="stat"><div class="stat-val">{bmi or 'N/A'}</div><div class="stat-lbl">BMI</div></div>
  <div class="stat"><div class="stat-val">{profile.weight if profile and profile.weight else 'N/A'}</div><div class="stat-lbl">Weight (kg)</div></div>
</div>
<h2>Recent Workouts</h2>
<table><tr><th>Date</th><th>Type</th><th>Duration</th><th>Intensity</th><th>Calories</th></tr>{workout_rows}</table>
<h2>Recent Meals</h2>
<table><tr><th>Date</th><th>Type</th><th>Food</th><th>Calories</th></tr>{meal_rows}</table>
<h2>Weight History</h2>
<table><tr><th>Date</th><th>Weight</th></tr>{weight_rows}</table>
<div class="footer">FitTrack Pro &nbsp;·&nbsp; Report generated {datetime.utcnow().strftime('%d %b %Y %H:%M')} UTC</div>
</body></html>"""

        resp = make_response(html)
        fname = f"fittrack_report_{user.name.replace(' ','_')}_{datetime.utcnow().strftime('%Y%m%d')}.html"
        resp.headers['Content-Type']        = 'text/html'
        resp.headers['Content-Disposition'] = f'attachment; filename="{fname}"'
        return resp
    except Exception as e:
        return jsonify({'error': str(e)}), 500
