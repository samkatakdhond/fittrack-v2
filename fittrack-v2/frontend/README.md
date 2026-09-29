# FitTrack Pro — Fitness Tracker Website

A full-stack ready fitness tracker frontend, designed for Flask + MySQL backend integration.

## 📁 File Structure
```
fitness-tracker/
├── index.html          ← Landing page (hero, features, how-it-works)
├── login.html          ← Login page with form validation
├── register.html       ← Registration with password strength indicator
├── dashboard.html      ← Main dashboard with charts, stats, ML insights
├── workout.html        ← Workout plans (Beginner/Intermediate/Advanced)
├── diet.html           ← Nutrition tracker + diet plan recommendations
├── profile.html        ← User profile, body metrics, BMI calculator
├── css/
│   └── style.css       ← Global dark athletic design system
├── js/
│   ├── utils.js        ← Shared utilities, auth helpers, localStorage
│   ├── auth.js         ← Login & register logic
│   ├── dashboard.js    ← Charts (Chart.js), ML mock predictions
│   ├── profile.js      ← Profile & body metrics management
│   ├── workout.js      ← Workout logging & plan display
│   └── diet.js         ← Meal tracking & diet plan display
└── data/
    ├── diet.json        ← Static diet plan data (replace with API)
    └── workout.json     ← Static workout plan data (replace with API)
```

## 🚀 How to Run
Open `index.html` in any browser. No server needed for frontend phase.

## 🔐 Demo Login
- **Email:** demo@fittrack.com  
- **Password:** demo1234

## 🛠️ Flask + MySQL Backend Integration

All `TODO (Backend):` comments in JS files mark where to replace localStorage with API calls.

### Suggested Flask Endpoints:
```
POST   /api/auth/register    ← auth.js
POST   /api/auth/login       ← auth.js
POST   /api/auth/logout      ← utils.js
GET    /api/profile          ← profile.js
PUT    /api/profile          ← profile.js
PUT    /api/profile/metrics  ← profile.js
PUT    /api/auth/password    ← profile.js
GET    /api/dashboard/summary← dashboard.js
POST   /api/workouts         ← dashboard.js, workout.js
GET    /api/workouts         ← workout.js
POST   /api/meals            ← diet.js
GET    /api/meals?date=...   ← diet.js
DELETE /api/meals/:id        ← diet.js
GET    /api/diet-plans       ← diet.js
GET    /api/ml/insights      ← dashboard.js
```

### MySQL Schema (suggested):
```sql
CREATE TABLE users (id INT AUTO_INCREMENT PRIMARY KEY, name VARCHAR(100), email VARCHAR(150) UNIQUE, password_hash VARCHAR(255), goal VARCHAR(50), gender VARCHAR(20), created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE user_profiles (user_id INT, height FLOAT, weight FLOAT, target_weight FLOAT, age INT, activity_level VARCHAR(30), FOREIGN KEY(user_id) REFERENCES users(id));
CREATE TABLE workouts (id INT AUTO_INCREMENT PRIMARY KEY, user_id INT, type VARCHAR(50), duration INT, intensity VARCHAR(20), calories INT, logged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(user_id) REFERENCES users(id));
CREATE TABLE meals (id INT AUTO_INCREMENT PRIMARY KEY, user_id INT, meal_type VARCHAR(30), food_name VARCHAR(150), calories INT, category VARCHAR(50), logged_date DATE, FOREIGN KEY(user_id) REFERENCES users(id));
```

## 🎨 Design
- Dark athletic theme inspired by MapMyFitness
- Font: Bebas Neue (display) + Barlow Condensed (UI) + Barlow (body)
- Accent: #f4501e (orange-red)
- Charts: Chart.js
