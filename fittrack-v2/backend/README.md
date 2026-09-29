# FitTrack Pro — Backend Setup Guide

## Prerequisites
- Python 3.9+
- MySQL running locally (installed directly, NOT XAMPP)

---

## Step 1 — Create the Database

Open your MySQL shell and run:

```bash
mysql -u root -p < setup_mysql.sql
```

Or manually:
```sql
CREATE DATABASE fittrack_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

---

## Step 2 — Configure Environment

Copy `.env.example` to `.env` and fill in your MySQL password:

```bash
cp .env.example .env
```

Edit `.env`:
```
MYSQL_USER=root
MYSQL_PASSWORD=your_actual_password
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_DB=fittrack_db
```

---

## Step 3 — Install Dependencies

```bash
pip install -r requirements.txt
```

---

## Step 4 — Run the Server

```bash
python app.py
```

Tables are **auto-created** on first run. You'll see:
```
✅ Database tables ready!
🔥  FitTrack Pro — Backend Server
📡  Running on  : http://127.0.0.1:5000
```

---

## API Endpoints

| Method | URL | Auth | Description |
|--------|-----|------|-------------|
| POST | /api/auth/register | ❌ | Create account |
| POST | /api/auth/login | ❌ | Login → get JWT token |
| POST | /api/auth/logout | ✅ | Logout |
| GET | /api/auth/me | ✅ | Current user info |
| GET | /api/profile | ✅ | Get profile |
| PUT | /api/profile | ✅ | Update name/gender/goal |
| PUT | /api/profile/metrics | ✅ | Update height/weight/target |
| PUT | /api/profile/password | ✅ | Change password |
| GET | /api/workouts | ✅ | Get workouts (?days=30) |
| POST | /api/workouts | ✅ | Log a workout |
| GET | /api/workouts/stats | ✅ | Weekly stats |
| GET | /api/meals | ✅ | Get meals (?date=YYYY-MM-DD) |
| POST | /api/meals | ✅ | Log a meal |
| DELETE | /api/meals/<id> | ✅ | Delete a meal |
| GET | /api/dashboard/summary | ✅ | Today's dashboard data |
| GET | /api/ml/insights | ✅ | AI insights |
| GET | /api/ml/calorie-recommendation | ✅ | Calorie targets |

✅ = Requires `Authorization: Bearer <token>` header

---

## Frontend

No changes needed in your frontend. Just make sure it points to:
```
http://127.0.0.1:5000
```
