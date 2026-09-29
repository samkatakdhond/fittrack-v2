"""
FitTrack — Create / Promote Admin Account
Run once: python create_admin.py

Edit ADMIN_EMAIL and ADMIN_PASSWORD below with YOUR credentials.
This script creates the account (if it doesn't exist) and sets role='admin' + is_verified=True.
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))

# ── ✏️  SET YOUR ADMIN CREDENTIALS HERE ──────────────────────────────────────
ADMIN_EMAIL    = "fittrack1214@gmail.com"   # ← your email
ADMIN_PASSWORD = "fittrack@121406"             # ← your password (min 8 chars)
ADMIN_NAME     = "FitTrack (Admin)"
# ─────────────────────────────────────────────────────────────────────────────

from dotenv import load_dotenv
load_dotenv()

from app import create_app
from models import db, User

app = create_app()

with app.app_context():
    existing = User.query.filter_by(email=ADMIN_EMAIL.lower().strip()).first()
    if existing:
        existing.role        = 'admin'
        existing.is_verified = True
        existing.set_password(ADMIN_PASSWORD)
        db.session.commit()
        print(f"✅  Existing account promoted to admin: {ADMIN_EMAIL}")
    else:
        admin = User(
            name        = ADMIN_NAME,
            email       = ADMIN_EMAIL.lower().strip(),
            goal        = 'maintenance',
            is_verified = True,
            role        = 'admin',
        )
        admin.set_password(ADMIN_PASSWORD)
        db.session.add(admin)
        db.session.commit()
        print(f"✅  Admin account created: {ADMIN_EMAIL}")

    print(f"\n🔑  Login at: http://127.0.0.1:5000/admin.html")
    print(f"   Email   : {ADMIN_EMAIL}")
    print(f"   Password: {ADMIN_PASSWORD}")
    print(f"   Role    : admin\n")
