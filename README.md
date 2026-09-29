# Stocker

אפליקציית web אישית למעקב מניות: סקרינר יומי על S&P500+Nasdaq-100,
תיק השקעות וירטואלי, ומסך מדדים.

## הרצה מקומית

### Backend

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

export STOCKER_SESSION_SECRET="change-me"
export STOCKER_LOGIN_PASSWORD="change-me"
export STOCKER_DB_PATH="./stocker.db"

uvicorn app.main:create_app --factory --reload
```

בדיקת תקינות: `curl http://localhost:8000/api/health`

### Frontend (בפיתוח, שרת נפרד עם hot-reload)

```bash
cd frontend
npm install
npm run dev
```

עולה על `http://localhost:5173`, מנתב קריאות `/api/*` ל-backend שרץ על
פורט 8000 (מוגדר ב-`vite.config.ts`).

## בדיקות

```bash
cd backend
pytest tests/ -v
```

## Docker

ה-Dockerfile בונה בשני שלבים: קודם בונה את ה-frontend (Node), ואז
מעתיק את התוצאה לתוך תמונת ה-Python שמריצה את ה-backend ומגישה גם את
קבצי ה-frontend הבנויים. ה-build context הוא **שורש הריפו**, לא
`backend/`:

```bash
docker build -f backend/Dockerfile -t stocker .
docker run --rm -p 8000:8000 \
  -e STOCKER_SESSION_SECRET=change-me \
  -e STOCKER_LOGIN_PASSWORD=change-me \
  -v stocker_data:/data \
  stocker
```

(ה-`-v stocker_data:/data` שומר את קובץ ה-SQLite בין הרצות — בלעדיו
הנתונים נמחקים בכל `docker run` חדש.)

## מצב הפרויקט

- ✅ Backend API מלא (auth, portfolio, recommendations, indices, screener יומי)
- ✅ Frontend (React + Vite, PWA)
- ⏳ פריסה לענן
