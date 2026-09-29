"""
FitTrack — Clear All User Data
Run from: fittrack-pro/backend/
Command : python clear_database.py
"""

import sys
from app import create_app
from models import db, User, UserProfile, Workout, Meal, WeightLog, Achievement

app = create_app()

with app.app_context():
    print("\n" + "="*45)
    print("  FitTrack — Delete ALL User Data")
    print("="*45)

    # Show current counts before deleting
    print("\n📊 Current records in database:")
    print(f"   Users        : {User.query.count()}")
    print(f"   Profiles     : {UserProfile.query.count()}")
    print(f"   Workouts     : {Workout.query.count()}")
    print(f"   Meals        : {Meal.query.count()}")
    print(f"   Weight Logs  : {WeightLog.query.count()}")
    print(f"   Achievements : {Achievement.query.count()}")

    # Safety confirmation
    print("\n⚠️  This will permanently delete ALL data.")
    confirm = input("   Type YES to confirm: ").strip()

    if confirm != "YES":
        print("\n❌ Cancelled. No data was deleted.\n")
        sys.exit(0)

    # Delete in correct order (child tables first to avoid FK constraint errors)
    try:
        Achievement.query.delete()
        WeightLog.query.delete()
        Meal.query.delete()
        Workout.query.delete()
        UserProfile.query.delete()
        User.query.delete()
        db.session.commit()

        print("\n✅ All user data deleted successfully!")
        print("\n📊 Records after deletion:")
        print(f"   Users        : {User.query.count()}")
        print(f"   Profiles     : {UserProfile.query.count()}")
        print(f"   Workouts     : {Workout.query.count()}")
        print(f"   Meals        : {Meal.query.count()}")
        print(f"   Weight Logs  : {WeightLog.query.count()}")
        print(f"   Achievements : {Achievement.query.count()}")
        print()

    except Exception as e:
        db.session.rollback()
        print(f"\n❌ Error: {e}")
        print("   No data was deleted (transaction rolled back).\n")
        sys.exit(1)