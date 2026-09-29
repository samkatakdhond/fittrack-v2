"""
Achievement engine — rule-based, no randomness.
Call `evaluate_achievements(user_id)` after any state-changing action.
"""
from datetime import datetime, timedelta
from models import db, Achievement, Workout, WeightLog

# All possible achievements: (key, name, emoji)
ALL_ACHIEVEMENTS = [
    ('first_workout',       'First Workout',        '🏋️'),
    ('workouts_10',         '10 Workouts Done',     '💪'),
    ('streak_7',            '7-Day Streak',         '🔥'),
    ('weekly_goal_done',    'Weekly Goal Crushed',  '🏆'),
    ('first_1kg_loss',      'First 1kg Lost',       '⚖️'),
]


def _unlock(user_id: int, key: str, name: str, emoji: str) -> bool:
    """Unlock an achievement if not already earned. Returns True if newly unlocked."""
    exists = Achievement.query.filter_by(user_id=user_id, key=key).first()
    if exists:
        return False
    a = Achievement(user_id=user_id, key=key, name=name, emoji=emoji)
    db.session.add(a)
    return True


def evaluate_achievements(user_id: int) -> list:
    """
    Checks all rule conditions and persists newly unlocked achievements.
    Returns list of newly-unlocked achievement dicts.
    """
    newly_unlocked = []

    all_workouts = Workout.query.filter_by(user_id=user_id).order_by(Workout.workout_date).all()
    total_workouts = len(all_workouts)

    # 1. First Workout Completed
    if total_workouts >= 1:
        if _unlock(user_id, 'first_workout', 'First Workout', '🏋️'):
            newly_unlocked.append('first_workout')

    # 2. 10 Workouts Completed
    if total_workouts >= 10:
        if _unlock(user_id, 'workouts_10', '10 Workouts Done', '💪'):
            newly_unlocked.append('workouts_10')

    # 3. 7-Day Streak (7 consecutive calendar days with at least 1 workout)
    if total_workouts >= 7:
        workout_dates = sorted(set(w.workout_date for w in all_workouts), reverse=True)
        streak = 1
        for i in range(1, len(workout_dates)):
            if (workout_dates[i - 1] - workout_dates[i]).days == 1:
                streak += 1
                if streak >= 7:
                    break
            else:
                streak = 1
        if streak >= 7:
            if _unlock(user_id, 'streak_7', '7-Day Streak', '🔥'):
                newly_unlocked.append('streak_7')

    # 4. Weekly Goal Completed (>= 5 workouts in any rolling 7-day window)
    if total_workouts >= 5:
        workout_dates = sorted(set(w.workout_date for w in all_workouts))
        for d in workout_dates:
            week_end = d + timedelta(days=6)
            count = sum(1 for wd in workout_dates if d <= wd <= week_end)
            if count >= 5:
                if _unlock(user_id, 'weekly_goal_done', 'Weekly Goal Crushed', '🏆'):
                    newly_unlocked.append('weekly_goal_done')
                break

    # 5. First 1kg Weight Loss
    logs = WeightLog.query.filter_by(user_id=user_id).order_by(WeightLog.logged_date).all()
    if len(logs) >= 2:
        first_weight = logs[0].weight
        min_weight   = min(l.weight for l in logs)
        if (first_weight - min_weight) >= 1.0:
            if _unlock(user_id, 'first_1kg_loss', 'First 1kg Lost', '⚖️'):
                newly_unlocked.append('first_1kg_loss')

    db.session.commit()
    return newly_unlocked
