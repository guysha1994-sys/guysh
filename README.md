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

## פריסה בענן (Oracle Cloud Always Free)

האפליקציה רצה על VM חינמי לתמיד (Oracle Cloud, Ampere A1) עם
Docker Compose: קונטיינר אחד לאפליקציה + קונטיינר Caddy שמנפיק
ומחדש אוטומטית תעודת TLS מ-Let's Encrypt (דרך שם מארח `<IP>.sslip.io`,
בלי צורך בדומיין בבעלות). התצורה ב-`deploy/`.

**עדכון קוד לאחר push:**

```bash
ssh -i <ssh-key> ubuntu@<server-ip>
cd ~/stocker
git pull
cd deploy
sudo docker compose up -d --build
```

**הגדרה ראשונית בשרת חדש:**

1. פתיחת פורטים 80/443 גם ב-Security List (Oracle Console) וגם
   ב-firewall המקומי (`iptables`) — Oracle חוסם את שניהם כברירת מחדל
2. התקנת Docker: `curl -fsSL https://get.docker.com | sudo sh`
3. `git clone` את הריפו, ליצור `deploy/.env` (ר' `deploy/.env.example`)
   עם `STOCKER_SESSION_SECRET` אקראי, `STOCKER_LOGIN_PASSWORD`,
   ו-`DOMAIN=<public-ip>.sslip.io`
4. `cd deploy && sudo docker compose up -d --build`

`docker compose` עם `restart: unless-stopped` ו-`systemctl enable docker`
מבטיחים שהאפליקציה עולה אוטומטית גם אחרי ריסטארט לשרת. הנתונים
(SQLite) נשמרים ב-named volume, לא נמחקים בין דיפלויים.

## מצב הפרויקט

- ✅ Backend API מלא (auth, portfolio, recommendations, indices, screener יומי)
- ✅ Frontend (React + Vite, PWA)
- ✅ פריסה לענן (Oracle Cloud Always Free, HTTPS אמיתי)
