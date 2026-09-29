"""
FitTrack Pro — SQLAlchemy Models (v2 Production)
Tables: users, user_profiles, workouts, meals, weight_logs,
        achievements, chat_messages, otp_store,
        water_logs, streaks, activity_logs, refresh_tokens
"""
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    id              = db.Column(db.Integer, primary_key=True)
    name            = db.Column(db.String(100), nullable=False)
    email           = db.Column(db.String(150), unique=True, nullable=False, index=True)
    password_hash   = db.Column(db.String(255), nullable=False)
    goal            = db.Column(db.String(50), default='weight_loss')
    gender          = db.Column(db.String(20))
    avatar_filename = db.Column(db.String(200))
    is_verified     = db.Column(db.Boolean, default=False, nullable=False)
    role            = db.Column(db.String(20), default='user', nullable=False)
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)
    last_login      = db.Column(db.DateTime)
    profile         = db.relationship('UserProfile',  backref='user', uselist=False, cascade='all, delete-orphan')
    workouts        = db.relationship('Workout',       backref='user', cascade='all, delete-orphan')
    meals           = db.relationship('Meal',          backref='user', cascade='all, delete-orphan')
    weight_logs     = db.relationship('WeightLog',     backref='user', cascade='all, delete-orphan')
    achievements    = db.relationship('Achievement',   backref='user', cascade='all, delete-orphan')
    chat_messages   = db.relationship('ChatMessage',   backref='user', cascade='all, delete-orphan')
    water_logs      = db.relationship('WaterLog',      backref='user', cascade='all, delete-orphan')
    streaks         = db.relationship('Streak',        backref='user', uselist=False, cascade='all, delete-orphan')
    activity_logs   = db.relationship('ActivityLog',   backref='user', cascade='all, delete-orphan')
    refresh_tokens  = db.relationship('RefreshToken',  backref='user', cascade='all, delete-orphan')
    def set_password(self, p): self.password_hash = generate_password_hash(p)
    def check_password(self, p): return check_password_hash(self.password_hash, p)
    def is_admin(self): return self.role == 'admin'
    def to_dict(self):
        return {'id':self.id,'name':self.name,'email':self.email,'goal':self.goal,
                'gender':self.gender,'avatar_filename':self.avatar_filename,
                'is_verified':self.is_verified,'role':self.role,
                'created_at':self.created_at.isoformat() if self.created_at else None,
                'last_login':self.last_login.isoformat() if self.last_login else None}

class OTPStore(db.Model):
    __tablename__ = 'otp_store'
    id         = db.Column(db.Integer, primary_key=True)
    email      = db.Column(db.String(150), nullable=False, index=True)
    otp_code   = db.Column(db.String(6),   nullable=False)
    purpose    = db.Column(db.String(20),  nullable=False)
    attempts   = db.Column(db.Integer, default=0, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    def is_expired(self): return datetime.utcnow() > self.expires_at
    def increment_attempt(self): self.attempts += 1

class RefreshToken(db.Model):
    __tablename__ = 'refresh_tokens'
    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    token_hash = db.Column(db.String(255), nullable=False, unique=True)
    expires_at = db.Column(db.DateTime, nullable=False)
    revoked    = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    def is_valid(self): return not self.revoked and datetime.utcnow() < self.expires_at

class UserProfile(db.Model):
    __tablename__ = 'user_profiles'
    id                  = db.Column(db.Integer, primary_key=True)
    user_id             = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True)
    height              = db.Column(db.Float)
    weight              = db.Column(db.Float)
    target_weight       = db.Column(db.Float)
    age                 = db.Column(db.Integer)
    activity_level      = db.Column(db.String(30), default='moderate')
    weekly_workout_goal = db.Column(db.Integer, default=5)
    daily_calorie_goal  = db.Column(db.Integer, default=2000)
    daily_water_goal_ml = db.Column(db.Integer, default=2500)
    updated_at          = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    def to_dict(self):
        return {'user_id':self.user_id,'height':self.height,'weight':self.weight,
                'target_weight':self.target_weight,'age':self.age,
                'activity_level':self.activity_level,
                'weekly_workout_goal':self.weekly_workout_goal,
                'daily_calorie_goal':self.daily_calorie_goal,
                'daily_water_goal_ml':self.daily_water_goal_ml}

class Workout(db.Model):
    __tablename__ = 'workouts'
    id           = db.Column(db.Integer, primary_key=True)
    user_id      = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    type         = db.Column(db.String(50),  nullable=False)
    duration     = db.Column(db.Integer,     nullable=False)
    intensity    = db.Column(db.String(20),  nullable=False)
    calories     = db.Column(db.Integer,     nullable=False)
    completed    = db.Column(db.Boolean,     default=True)
    logged_at    = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    workout_date = db.Column(db.Date,     default=datetime.utcnow,  index=True)
    def to_dict(self):
        return {'id':self.id,'type':self.type,'duration':self.duration,
                'intensity':self.intensity,'calories':self.calories,'completed':self.completed,
                'logged_at':self.logged_at.isoformat() if self.logged_at else None,
                'date':self.workout_date.isoformat() if self.workout_date else None}

class Meal(db.Model):
    __tablename__ = 'meals'
    id          = db.Column(db.Integer, primary_key=True)
    user_id     = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    meal_type   = db.Column(db.String(30),  nullable=False)
    food_name   = db.Column(db.String(150), nullable=False)
    calories    = db.Column(db.Integer,     nullable=False)
    category    = db.Column(db.String(50))
    logged_date = db.Column(db.Date,     default=datetime.utcnow, index=True)
    logged_at   = db.Column(db.DateTime, default=datetime.utcnow)
    def to_dict(self):
        return {'id':self.id,'type':self.meal_type,'name':self.food_name,
                'calories':self.calories,'category':self.category,
                'date':self.logged_date.isoformat() if self.logged_date else None,
                'logged_at':self.logged_at.isoformat() if self.logged_at else None}

class WeightLog(db.Model):
    __tablename__ = 'weight_logs'
    id          = db.Column(db.Integer, primary_key=True)
    user_id     = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    weight      = db.Column(db.Float,   nullable=False)
    logged_date = db.Column(db.Date,    default=datetime.utcnow, index=True)
    logged_at   = db.Column(db.DateTime, default=datetime.utcnow)
    def to_dict(self):
        return {'id':self.id,'weight':self.weight,
                'date':self.logged_date.isoformat() if self.logged_date else None}

class WaterLog(db.Model):
    __tablename__ = 'water_logs'
    id          = db.Column(db.Integer, primary_key=True)
    user_id     = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    amount_ml   = db.Column(db.Integer, nullable=False, default=250)
    logged_date = db.Column(db.Date,    default=datetime.utcnow, index=True)
    logged_at   = db.Column(db.DateTime, default=datetime.utcnow)
    def to_dict(self):
        return {'id':self.id,'amount_ml':self.amount_ml,
                'date':self.logged_date.isoformat() if self.logged_date else None,
                'logged_at':self.logged_at.isoformat() if self.logged_at else None}

class Streak(db.Model):
    __tablename__ = 'streaks'
    id                  = db.Column(db.Integer, primary_key=True)
    user_id             = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True)
    workout_streak      = db.Column(db.Integer, default=0)
    workout_best_streak = db.Column(db.Integer, default=0)
    diet_streak         = db.Column(db.Integer, default=0)
    diet_best_streak    = db.Column(db.Integer, default=0)
    water_streak        = db.Column(db.Integer, default=0)
    water_best_streak   = db.Column(db.Integer, default=0)
    last_workout_date   = db.Column(db.Date)
    last_diet_date      = db.Column(db.Date)
    last_water_date     = db.Column(db.Date)
    updated_at          = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    def to_dict(self):
        return {'workout_streak':self.workout_streak,'workout_best_streak':self.workout_best_streak,
                'diet_streak':self.diet_streak,'diet_best_streak':self.diet_best_streak,
                'water_streak':self.water_streak,'water_best_streak':self.water_best_streak}

class Achievement(db.Model):
    __tablename__ = 'achievements'
    id        = db.Column(db.Integer, primary_key=True)
    user_id   = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    key       = db.Column(db.String(60),  nullable=False)
    name      = db.Column(db.String(100), nullable=False)
    emoji     = db.Column(db.String(10),  nullable=False)
    earned_at = db.Column(db.DateTime, default=datetime.utcnow)
    __table_args__ = (db.UniqueConstraint('user_id', 'key', name='uq_user_achievement'),)
    def to_dict(self):
        return {'key':self.key,'name':self.name,'emoji':self.emoji,
                'earned_at':self.earned_at.isoformat() if self.earned_at else None}

class ChatMessage(db.Model):
    __tablename__ = 'chat_messages'
    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    role       = db.Column(db.String(20),  nullable=False)
    content    = db.Column(db.Text,        nullable=False)
    created_at = db.Column(db.DateTime,    default=datetime.utcnow, index=True)
    def to_dict(self):
        return {'id':self.id,'role':self.role,'content':self.content,
                'created_at':self.created_at.isoformat() if self.created_at else None}

class ActivityLog(db.Model):
    __tablename__ = 'activity_logs'
    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)
    action     = db.Column(db.String(100), nullable=False)
    detail     = db.Column(db.Text)
    ip_address = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    def to_dict(self):
        return {'id':self.id,'user_id':self.user_id,'action':self.action,
                'detail':self.detail,'ip_address':self.ip_address,
                'created_at':self.created_at.isoformat() if self.created_at else None}
