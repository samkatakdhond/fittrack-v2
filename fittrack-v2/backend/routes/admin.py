"""
FitTrack Admin Routes — Full-Featured
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, User, Workout, Meal, ActivityLog, WaterLog, Streak, UserProfile
from datetime import datetime, timedelta
from functools import wraps
from sqlalchemy import func

bp = Blueprint('admin', __name__)

def admin_required(fn):
    @wraps(fn)
    @jwt_required()
    def wrapper(*args, **kwargs):
        user_id = int(get_jwt_identity())
        user    = db.session.get(User, user_id)
        if not user or not user.is_admin():
            return jsonify({'error': 'Admin access required'}), 403
        return fn(*args, **kwargs)
    return wrapper

def _log(user_id, action, detail=None):
    log = ActivityLog(user_id=user_id, action=action, detail=detail,
                      ip_address=request.remote_addr)
    db.session.add(log)

@bp.route('/stats', methods=['GET'])
@admin_required
def get_stats():
    try:
        now      = datetime.utcnow()
        today    = now.date()
        week_ago = now - timedelta(days=7)
        total_users    = User.query.count()
        verified_users = User.query.filter_by(is_verified=True).count()
        total_workouts = Workout.query.count()
        total_meals    = Meal.query.count()
        today_regs     = User.query.filter(func.date(User.created_at) == today).count()
        new_users_week = User.query.filter(User.created_at >= week_ago).count()
        active_users   = db.session.query(func.count(func.distinct(Workout.user_id))).filter(
                             Workout.logged_at >= week_ago).scalar() or 0
        return jsonify({
            'total_users': total_users, 'verified_users': verified_users,
            'unverified': total_users - verified_users,
            'total_workouts': total_workouts, 'total_meals': total_meals,
            'today_regs': today_regs, 'new_users_week': new_users_week,
            'active_users_week': int(active_users),
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/analytics', methods=['GET'])
@admin_required
def get_analytics():
    try:
        growth = []
        for i in range(29, -1, -1):
            d = (datetime.utcnow() - timedelta(days=i)).date()
            count = User.query.filter(func.date(User.created_at) == d).count()
            growth.append({'date': d.isoformat(), 'count': count})
        top_workouts = db.session.query(Workout.type, func.count(Workout.id).label('cnt'))\
            .group_by(Workout.type).order_by(func.count(Workout.id).desc()).limit(6).all()
        top_meals = db.session.query(Meal.food_name, func.count(Meal.id).label('cnt'))\
            .group_by(Meal.food_name).order_by(func.count(Meal.id).desc()).limit(6).all()
        top_users = db.session.query(User.name, User.email, func.count(Workout.id).label('workouts'))\
            .join(Workout, Workout.user_id == User.id, isouter=True)\
            .group_by(User.id, User.name, User.email)\
            .order_by(func.count(Workout.id).desc()).limit(5).all()
        goal_dist = db.session.query(User.goal, func.count(User.id).label('cnt'))\
            .group_by(User.goal).all()
        return jsonify({
            'user_growth':  growth,
            'top_workouts': [{'type': r.type, 'count': r.cnt} for r in top_workouts],
            'top_meals':    [{'name': r.food_name, 'count': r.cnt} for r in top_meals],
            'top_users':    [{'name': r.name, 'email': r.email, 'workouts': r.workouts} for r in top_users],
            'goal_dist':    [{'goal': r.goal or 'unknown', 'count': r.cnt} for r in goal_dist],
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/users', methods=['GET'])
@admin_required
def get_users():
    try:
        page     = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))
        search   = request.args.get('search', '').strip()
        query    = User.query
        if search:
            query = query.filter(db.or_(User.name.ilike(f'%{search}%'), User.email.ilike(f'%{search}%')))
        paginated = query.order_by(User.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
        users = []
        for u in paginated.items:
            d = u.to_dict()
            d['workout_count'] = Workout.query.filter_by(user_id=u.id).count()
            d['meal_count']    = Meal.query.filter_by(user_id=u.id).count()
            users.append(d)
        return jsonify({'users': users, 'total': paginated.total, 'page': paginated.page, 'pages': paginated.pages}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/users/<int:uid>/activity', methods=['GET'])
@admin_required
def get_user_activity(uid):
    try:
        user = db.session.get(User, uid)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        workouts = [w.to_dict() for w in Workout.query.filter_by(user_id=uid).order_by(Workout.logged_at.desc()).limit(20).all()]
        meals    = [m.to_dict() for m in Meal.query.filter_by(user_id=uid).order_by(Meal.logged_at.desc()).limit(20).all()]
        streak   = user.streaks.to_dict() if user.streaks else {}
        logs     = [l.to_dict() for l in ActivityLog.query.filter_by(user_id=uid).order_by(ActivityLog.created_at.desc()).limit(30).all()]
        return jsonify({'user': user.to_dict(), 'workouts': workouts, 'meals': meals, 'streak': streak, 'logs': logs}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/users/<int:uid>', methods=['DELETE'])
@admin_required
def delete_user(uid):
    try:
        admin_id = int(get_jwt_identity())
        if uid == admin_id:
            return jsonify({'error': 'Cannot delete your own admin account'}), 400
        user = db.session.get(User, uid)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        _log(admin_id, 'admin_delete_user', f'Deleted {user.email} (id={uid})')
        db.session.delete(user)
        db.session.commit()
        return jsonify({'message': f'User {user.email} deleted'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@bp.route('/users/<int:uid>/role', methods=['PUT'])
@admin_required
def set_role(uid):
    try:
        admin_id = int(get_jwt_identity())
        data     = request.get_json()
        new_role = data.get('role')
        if new_role not in ('user', 'admin'):
            return jsonify({'error': 'Role must be user or admin'}), 400
        user = db.session.get(User, uid)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        user.role = new_role
        _log(admin_id, 'admin_set_role', f'Set {user.email} → {new_role}')
        db.session.commit()
        return jsonify({'message': f'Role updated to {new_role}', 'user': user.to_dict()}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@bp.route('/workouts', methods=['GET'])
@admin_required
def list_workouts():
    try:
        page   = int(request.args.get('page', 1))
        search = request.args.get('search', '').strip()
        q = Workout.query
        if search:
            q = q.filter(Workout.type.ilike(f'%{search}%'))
        pag = q.order_by(Workout.logged_at.desc()).paginate(page=page, per_page=30, error_out=False)
        rows = []
        for w in pag.items:
            d = w.to_dict()
            u = db.session.get(User, w.user_id)
            d['user_name'] = u.name if u else '(deleted)'
            d['user_email'] = u.email if u else ''
            rows.append(d)
        return jsonify({'workouts': rows, 'total': pag.total, 'pages': pag.pages, 'page': pag.page}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/workouts/<int:wid>', methods=['DELETE'])
@admin_required
def delete_workout(wid):
    try:
        admin_id = int(get_jwt_identity())
        w = db.session.get(Workout, wid)
        if not w:
            return jsonify({'error': 'Workout not found'}), 404
        _log(admin_id, 'admin_delete_workout', f'Workout id={wid}')
        db.session.delete(w)
        db.session.commit()
        return jsonify({'message': 'Workout deleted'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@bp.route('/meals', methods=['GET'])
@admin_required
def list_meals():
    try:
        page   = int(request.args.get('page', 1))
        search = request.args.get('search', '').strip()
        q = Meal.query
        if search:
            q = q.filter(Meal.food_name.ilike(f'%{search}%'))
        pag = q.order_by(Meal.logged_at.desc()).paginate(page=page, per_page=30, error_out=False)
        rows = []
        for m in pag.items:
            d = m.to_dict()
            u = db.session.get(User, m.user_id)
            d['user_name']  = u.name  if u else '(deleted)'
            d['user_email'] = u.email if u else ''
            rows.append(d)
        return jsonify({'meals': rows, 'total': pag.total, 'pages': pag.pages, 'page': pag.page}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/meals/<int:mid>', methods=['DELETE'])
@admin_required
def delete_meal(mid):
    try:
        admin_id = int(get_jwt_identity())
        m = db.session.get(Meal, mid)
        if not m:
            return jsonify({'error': 'Meal not found'}), 404
        _log(admin_id, 'admin_delete_meal', f'Meal id={mid}')
        db.session.delete(m)
        db.session.commit()
        return jsonify({'message': 'Meal deleted'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@bp.route('/logs', methods=['GET'])
@admin_required
def get_logs():
    try:
        page       = int(request.args.get('page', 1))
        log_filter = request.args.get('filter', 'all')
        q = ActivityLog.query
        if log_filter == 'failed':
            q = q.filter(ActivityLog.action.ilike('%fail%'))
        elif log_filter == 'otp':
            q = q.filter(ActivityLog.action.ilike('%otp%'))
        elif log_filter == 'admin':
            q = q.filter(ActivityLog.action.ilike('admin_%'))
        logs = q.order_by(ActivityLog.created_at.desc()).paginate(page=page, per_page=50, error_out=False)
        enriched = []
        for l in logs.items:
            d = l.to_dict()
            if l.user_id:
                u = db.session.get(User, l.user_id)
                d['user_name']  = u.name  if u else '(deleted)'
                d['user_email'] = u.email if u else ''
            else:
                d['user_name'] = 'System'; d['user_email'] = ''
            enriched.append(d)
        return jsonify({'logs': enriched, 'total': logs.total, 'page': logs.page, 'pages': logs.pages}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
