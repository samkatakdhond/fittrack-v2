"""
FitTrack Pro — Database Migration Script
Run ONCE with: python migrate.py
Safely adds new columns and tables without losing existing data.
"""
from app import create_app
from models import db
from sqlalchemy import text

app = create_app()

MIGRATIONS = [
    # user_profiles — new goal columns
    ("user_profiles", "weekly_workout_goal",
     "ALTER TABLE user_profiles ADD COLUMN weekly_workout_goal INT DEFAULT 5"),
    ("user_profiles", "daily_calorie_goal",
     "ALTER TABLE user_profiles ADD COLUMN daily_calorie_goal INT DEFAULT 2000"),
    # workouts — completed flag
    ("workouts", "completed",
     "ALTER TABLE workouts ADD COLUMN completed TINYINT(1) DEFAULT 1"),
    # users — profile picture filename (v9)
    ("users", "avatar_filename",
     "ALTER TABLE users ADD COLUMN avatar_filename VARCHAR(200) DEFAULT NULL"),
]

def column_exists(conn, table, column):
    result = conn.execute(text(
        "SELECT COUNT(*) FROM information_schema.columns "
        "WHERE table_schema = DATABASE() AND table_name = :t AND column_name = :c"
    ), {"t": table, "c": column})
    return result.scalar() > 0

def table_exists(conn, table):
    result = conn.execute(text(
        "SELECT COUNT(*) FROM information_schema.tables "
        "WHERE table_schema = DATABASE() AND table_name = :t"
    ), {"t": table})
    return result.scalar() > 0

with app.app_context():
    with db.engine.connect() as conn:
        print("\n🔧 Running FitTrack Pro migrations...\n")

        # 1. Column migrations
        for table, column, sql in MIGRATIONS:
            if not column_exists(conn, table, column):
                conn.execute(text(sql))
                conn.commit()
                print(f"  ✅ Added column  : {table}.{column}")
            else:
                print(f"  ⏭️  Already exists: {table}.{column}")

        # 2. New tables via SQLAlchemy create_all
        print()
        db.create_all()
        for tbl in ("weight_logs", "achievements"):
            if table_exists(conn, tbl):
                print(f"  ✅ Table ready   : {tbl}")
            else:
                print(f"  ⚠️  Missing table : {tbl}")

        print("\n✅ Migration complete — restart app.py\n")
