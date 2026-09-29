"""FitTrack Pro — Configuration v2"""
import os, logging
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

class Config:
    # ── Security ─────────────────────────────────────────
    SECRET_KEY               = os.environ.get('SECRET_KEY', 'CHANGE-THIS-IN-PRODUCTION')
    JWT_SECRET_KEY           = os.environ.get('JWT_SECRET_KEY', 'CHANGE-JWT-IN-PRODUCTION')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=2)
    JWT_REFRESH_TOKEN_EXPIRES= timedelta(days=30)
    JWT_TOKEN_LOCATION       = ['headers']

    # ── MySQL ─────────────────────────────────────────────
    MYSQL_USER     = os.environ.get('MYSQL_USER',     'root')
    MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD', '')
    MYSQL_HOST     = os.environ.get('MYSQL_HOST',     'localhost')
    MYSQL_PORT     = os.environ.get('MYSQL_PORT',     '3306')
    MYSQL_DB       = os.environ.get('MYSQL_DB',       'fittrack_db')

    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}"
        f"@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False

    # ── Flask Session ─────────────────────────────────────
    SESSION_TYPE              = 'filesystem'
    SESSION_COOKIE_SECURE     = False
    SESSION_COOKIE_HTTPONLY   = True
    SESSION_COOKIE_SAMESITE   = 'Lax'
    PERMANENT_SESSION_LIFETIME= timedelta(minutes=15)

    # ── Gmail SMTP ────────────────────────────────────────
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME', '')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', '')

    # ── CORS ──────────────────────────────────────────────
    CORS_HEADERS  = 'Content-Type'

    # ── Logging ───────────────────────────────────────────
    LOG_LEVEL     = os.environ.get('LOG_LEVEL', 'INFO')

def setup_logging(app):
    level = getattr(logging, app.config.get('LOG_LEVEL', 'INFO').upper(), logging.INFO)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(
        '[%(asctime)s] %(levelname)s %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    ))
    app.logger.handlers = [handler]
    app.logger.setLevel(level)
    app.logger.info('FitTrack Pro v2 — logging active')
