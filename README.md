# Stocker

אפליקציית web אישית למעקב מניות: סקרינר יומי על S&P500+Nasdaq-100,
תיק השקעות וירטואלי, ומסך מדדים.

## הרצה מקומית (backend בלבד, ללא frontend עדיין)

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

## בדיקות

```bash
cd backend
pytest tests/ -v
```

## Docker

```bash
docker build -f backend/Dockerfile -t stocker-backend .
docker run --rm -p 8000:8000 \
  -e STOCKER_SESSION_SECRET=change-me \
  -e STOCKER_LOGIN_PASSWORD=change-me \
  stocker-backend
```

## מצב הפרויקט

- ✅ Backend API מלא (auth, portfolio, recommendations, indices, screener יומי)
- ⏳ Frontend (React) — פלאן נפרד
- ⏳ פריסה לענן — פלאן נפרד
