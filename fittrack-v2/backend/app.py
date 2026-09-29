"""FitTrack Pro Backend v2 — Flask + MySQL"""
import os, sys
from flask import Flask, send_from_directory, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_session import Session
from config import Config, setup_logging
from models import db
from routes import auth, profile, workouts, meals, dashboard, ml, chat, water, streaks, admin, export

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    setup_logging(app)

    CORS(app, supports_credentials=True, origins="*",
         allow_headers=["Content-Type","Authorization"],
         methods=["GET","POST","PUT","DELETE","OPTIONS"])

    Session(app)
    db.init_app(app)
    JWTManager(app)

    # Blueprints
    app.register_blueprint(auth.bp,      url_prefix='/api/auth')
    app.register_blueprint(profile.bp,   url_prefix='/api/profile')
    app.register_blueprint(workouts.bp,  url_prefix='/api/workouts')
    app.register_blueprint(meals.bp,     url_prefix='/api/meals')
    app.register_blueprint(dashboard.bp, url_prefix='/api/dashboard')
    app.register_blueprint(ml.bp,        url_prefix='/api/ml')
    app.register_blueprint(chat.bp,      url_prefix='/api/chat')
    app.register_blueprint(water.bp,     url_prefix='/api/water')
    app.register_blueprint(streaks.bp,   url_prefix='/api/streaks')
    app.register_blueprint(admin.bp,     url_prefix='/api/admin')
    app.register_blueprint(export.bp,    url_prefix='/api/export')

    with app.app_context():
        try:
            db.create_all()
            with db.engine.connect() as conn:
                from sqlalchemy import text
                conn.execute(text("SELECT 1"))
            app.logger.info("✅ Database connected & tables ready!")
        except Exception as e:
            print(f"\n❌ DATABASE ERROR: {e}")
            print("   Check MYSQL_PASSWORD in .env and ensure MySQL is running.\n")
            sys.exit(1)

    # Serve frontend
    frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'frontend'))
    if os.path.exists(frontend_dir):
        @app.route('/', defaults={'path': 'login.html'})
        @app.route('/<path:path>')
        def serve_frontend(path):
            if path.startswith('api/'): return jsonify({'error':'Not found'}), 404
            full = os.path.join(frontend_dir, path)
            if os.path.isfile(full): return send_from_directory(frontend_dir, path)
            return send_from_directory(frontend_dir, 'login.html')
    return app

if __name__ == '__main__':
    app = create_app()
    print("\n" + "="*55)
    print("🔥  FitTrack Pro v2 — Backend Server")
    print("="*55)
    print("🌐  App  : http://127.0.0.1:5000")
    print("👑  Admin: http://127.0.0.1:5000/admin.html")
    print("="*55 + "\n")
    app.run(debug=True, host='0.0.0.0', port=5000)
