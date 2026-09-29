# backend/Dockerfile

# ---- Frontend build stage ----
FROM node:20-slim AS frontend-build

WORKDIR /frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

# ---- Backend runtime stage ----
FROM python:3.11-slim

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/app ./app

# main.py resolves frontend_dist as <repo-root>/frontend/dist — in this
# image that's /frontend/dist (three parents up from /app/app/main.py).
COPY --from=frontend-build /frontend/dist /frontend/dist

ENV STOCKER_DB_PATH=/data/stocker.db
EXPOSE 8000

CMD ["uvicorn", "app.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
