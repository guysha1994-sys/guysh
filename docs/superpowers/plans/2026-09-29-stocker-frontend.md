# Stocker Frontend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** בניית ה-frontend (React + Vite + TypeScript, PWA) לאפליקציית
Stocker: 5 מסכים (login, תיק, המלצות, מדדים, עסקה) בעיצוב "מסוף מסחר
כהה", ותוספת קטנה ל-backend (שדה `quantity` + שתי פעולות חדשות על
פוזיציה — "קנה עוד" עם חישוב ממוצע משוקלל, ו"עדכן סטופלוס") שהחלק
"עסקה" תלוי בה.

**Architecture:** React 18 + Vite + TypeScript, SPA עם `react-router-dom`
(5 routes), בלי ספריית state גלובלי — כל מסך שולף נתונים בעצמו דרך
מודול `api.ts` דק. `vite-plugin-pwa` להתקנה כאפליקציה. הבנייה
(`vite build`) מייצרת `frontend/dist`, וה-backend הקיים (`main.py`,
כבר מוגדר) מגיש אותה תחת `/`.

**Tech Stack:** React 18, TypeScript, Vite, react-router-dom,
vite-plugin-pwa. Backend: FastAPI/Pydantic (תוספת ל-router קיים).

**Spec:** [docs/superpowers/specs/2026-09-29-stock-recommendation-webapp-design.md](../specs/2026-09-29-stock-recommendation-webapp-design.md)

## Global Constraints

- **שפת ממשק: אנגלית, LTR.** כל הטקסטים בקוד (labels, כפתורים, הודעות
  שגיאה) באנגלית.
- **עיצוב — טוקנים מדויקים** (`frontend/src/styles/theme.css`):
  `--bg: #12110F`, `--surface: #1C1A17`, `--surface-hover: #24211D`,
  `--border: #2E2A24`, `--accent: #E8A33D`, `--positive: #3FB950`,
  `--negative: #F85149`, `--text: #E6E2DA`, `--text-dim: #8B877E`.
  גופנים: **IBM Plex Mono** למספרים/טיקרים/כותרות,
  **IBM Plex Sans** לטקסט ממשק — נטענים מ-Google Fonts. `--accent`
  (ענבר) הוא צבע המותג; `--positive`/`--negative` (ירוק/אדום) הם **רק**
  לסימון רווח/הפסד, לא לניווט/מותג. בלי all-caps labels, בלי חצים (→)
  בכפתורים.
- **בלי ספריית state גלובלי** (Redux וכו') — כל מסך שולף נתונים בעצמו
  דרך `api.ts`.
- **רענון**: כל מסך שמציג נתוני שוק (תיק/המלצות/מדדים) עושה polling
  אוטומטי כל 60 שניות (`usePolling` hook) + כפתור "Refresh" ידני.
- **אין מכירה חלקית** — מכירה תמיד סוגרת את כל הפוזיציה.
- **בדיקות frontend: ידניות**, לפי מה שכבר סוכם ב-spec — **אין**
  Jest/Vitest/React Testing Library בפרויקט הזה. כל משימת frontend
  מאומתת דרך `npm run build` (TypeScript מתקמפל בלי שגיאות) ותיאור
  מדויק של מה שהמיישם בדק ידנית מול `npm run dev`. לאחר שכל המשימות
  הושלמו, יתבצע מעבר ויזואלי סופי בדפדפן על ידי ה-controller (לא חלק
  ממשימה בודדת).
- **ולידציית קלט**: `quantity`/`price`/`stop_loss` בכל טופס חייבים
  להיות מספרים חיוביים — גם בצד ה-API (`Field(gt=0)`) וגם בטופס
  (`min`, `required`).
- **תאימות לאחור**: התוספת ל-backend (Task 1) חייבת להיות בטוחה מול
  קובץ `stocker.db` מקומי שכבר קיים בלי עמודת `quantity` — migration
  תוספתית (`ALTER TABLE ... ADD COLUMN`), לא הרסנית.
- כל הרצות `npm` מתוך `frontend/`. כל הרצות `pytest` מתוך `backend/`.

---

### Task 1: Backend — שדה quantity + פעולות "קנה עוד"/"עדכן סטופלוס"

**Files:**
- Modify: `backend/app/db.py`
- Modify: `backend/app/portfolio.py`
- Modify: `backend/app/routers/portfolio.py`
- Modify: `backend/tests/test_portfolio_api.py`
- Test: `backend/tests/test_db.py`

**Interfaces:**
- Consumes: `get_connection` (קיים ב-`db.py`).
- Produces: `Position` dataclass עם שדה `quantity: float` נוסף;
  `open_position(db_path, ticker, entry_price, quantity, stop_loss) -> int`
  (סיגנטורה משתנה — מוסיף `quantity`); `add_to_position(db_path,
  position_id, quantity, price) -> bool`; `update_stop_loss(db_path,
  position_id, stop_loss) -> bool`. אלו ישמשו את ה-frontend
  (`api.ts`, Task 4) דרך `POST /api/portfolio/{id}/add` ו-
  `PATCH /api/portfolio/{id}`.

- [ ] **Step 1: הוספת migration תוספתית ב-`db.py`**

עדכן את ה-`SCHEMA` הקיים (הוסף `quantity` לטבלת `portfolio_positions`):

```python
CREATE TABLE IF NOT EXISTS portfolio_positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    entry_price REAL NOT NULL,
    quantity REAL NOT NULL DEFAULT 0,
    stop_loss REAL NOT NULL,
    entry_date TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open',
    close_date TEXT
);
```

והוסף פונקציית migration ל-DB-ים ישנים שכבר קיימים בלי העמודה
(כמו ה-`stocker.db` שכבר רץ מקומית):

```python
def _ensure_quantity_column(conn: sqlite3.Connection) -> None:
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(portfolio_positions)")}
    if "quantity" not in columns:
        conn.execute(
            "ALTER TABLE portfolio_positions ADD COLUMN quantity REAL NOT NULL DEFAULT 0"
        )
```

עדכן את `init_db` לקרוא לה:

```python
def init_db(db_path: str) -> None:
    conn = get_connection(db_path)
    try:
        conn.executescript(SCHEMA)
        _ensure_quantity_column(conn)
        conn.commit()
    finally:
        conn.close()
```

- [ ] **Step 2: כתיבת טסט ל-migration**

```python
# backend/tests/test_db.py — הוסף בסוף הקובץ
import sqlite3 as _sqlite3


def test_init_db_adds_quantity_column_to_existing_table(tmp_path):
    db_path = str(tmp_path / "test.db")
    # מדמה DB ישן בלי עמודת quantity
    conn = _sqlite3.connect(db_path)
    conn.execute(
        "CREATE TABLE portfolio_positions ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, ticker TEXT NOT NULL, "
        "entry_price REAL NOT NULL, stop_loss REAL NOT NULL, "
        "entry_date TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'open', "
        "close_date TEXT)"
    )
    conn.commit()
    conn.close()

    init_db(db_path)

    conn = get_connection(db_path)
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(portfolio_positions)")}
    conn.close()
    assert "quantity" in columns
```

- [ ] **Step 3: הרצת הטסט ווידוא שעובר**

Run: `cd backend && .venv/bin/pytest tests/test_db.py -v`
Expected: PASS

- [ ] **Step 4: עדכון `portfolio.py`**

```python
# backend/app/portfolio.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from app.db import get_connection


@dataclass
class Position:
    id: int
    ticker: str
    entry_price: float
    quantity: float
    stop_loss: float
    entry_date: str
    status: str
    close_date: str | None


def list_open_positions(db_path: str) -> list[Position]:
    conn = get_connection(db_path)
    try:
        rows = conn.execute(
            "SELECT * FROM portfolio_positions WHERE status = 'open' ORDER BY entry_date DESC"
        ).fetchall()
        return [Position(**dict(row)) for row in rows]
    finally:
        conn.close()


def open_position(
    db_path: str, ticker: str, entry_price: float, quantity: float, stop_loss: float
) -> int:
    conn = get_connection(db_path)
    try:
        cursor = conn.execute(
            "INSERT INTO portfolio_positions "
            "(ticker, entry_price, quantity, stop_loss, entry_date, status) "
            "VALUES (?, ?, ?, ?, ?, 'open')",
            (ticker.upper(), entry_price, quantity, stop_loss, date.today().isoformat()),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def add_to_position(db_path: str, position_id: int, quantity: float, price: float) -> bool:
    conn = get_connection(db_path)
    try:
        row = conn.execute(
            "SELECT entry_price, quantity FROM portfolio_positions "
            "WHERE id = ? AND status = 'open'",
            (position_id,),
        ).fetchone()
        if row is None:
            return False

        old_quantity = row["quantity"]
        old_entry_price = row["entry_price"]
        new_quantity = old_quantity + quantity
        new_entry_price = (
            old_quantity * old_entry_price + quantity * price
        ) / new_quantity

        conn.execute(
            "UPDATE portfolio_positions SET entry_price = ?, quantity = ? WHERE id = ?",
            (new_entry_price, new_quantity, position_id),
        )
        conn.commit()
        return True
    finally:
        conn.close()


def update_stop_loss(db_path: str, position_id: int, stop_loss: float) -> bool:
    conn = get_connection(db_path)
    try:
        cursor = conn.execute(
            "UPDATE portfolio_positions SET stop_loss = ? WHERE id = ? AND status = 'open'",
            (stop_loss, position_id),
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def close_position(db_path: str, position_id: int) -> bool:
    conn = get_connection(db_path)
    try:
        cursor = conn.execute(
            "UPDATE portfolio_positions SET status = 'closed', close_date = ? "
            "WHERE id = ? AND status = 'open'",
            (date.today().isoformat(), position_id),
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()
```

- [ ] **Step 5: עדכון `routers/portfolio.py`**

```python
# backend/app/routers/portfolio.py
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app import portfolio
from app.data_fetcher import fetch_current_price_and_change

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])


class BuyRequest(BaseModel):
    ticker: str
    entry_price: float = Field(gt=0)
    quantity: float = Field(gt=0)
    stop_loss: float = Field(gt=0)


class AddToPositionRequest(BaseModel):
    quantity: float = Field(gt=0)
    price: float = Field(gt=0)


class UpdateStopLossRequest(BaseModel):
    stop_loss: float = Field(gt=0)


@router.get("")
def list_positions(request: Request):
    db_path = request.app.state.settings.db_path
    positions = portfolio.list_open_positions(db_path)

    result = []
    for p in positions:
        current_price, pct_change = fetch_current_price_and_change(p.ticker)
        pnl_pct = None
        if current_price is not None and p.entry_price:
            pnl_pct = (current_price - p.entry_price) / p.entry_price * 100
        result.append(
            {
                "id": p.id,
                "ticker": p.ticker,
                "entry_price": p.entry_price,
                "quantity": p.quantity,
                "stop_loss": p.stop_loss,
                "entry_date": p.entry_date,
                "current_price": current_price,
                "pct_change": pct_change,
                "pnl_pct": pnl_pct,
            }
        )
    return result


@router.post("")
def buy(body: BuyRequest, request: Request):
    db_path = request.app.state.settings.db_path
    position_id = portfolio.open_position(
        db_path, body.ticker, body.entry_price, body.quantity, body.stop_loss
    )
    return {"id": position_id}


@router.post("/{position_id}/add")
def add_to_position(position_id: int, body: AddToPositionRequest, request: Request):
    db_path = request.app.state.settings.db_path
    updated = portfolio.add_to_position(db_path, position_id, body.quantity, body.price)
    if not updated:
        raise HTTPException(status_code=404, detail="Position not found or not open")
    return {"ok": True}


@router.patch("/{position_id}")
def update_stop_loss(position_id: int, body: UpdateStopLossRequest, request: Request):
    db_path = request.app.state.settings.db_path
    updated = portfolio.update_stop_loss(db_path, position_id, body.stop_loss)
    if not updated:
        raise HTTPException(status_code=404, detail="Position not found or not open")
    return {"ok": True}


@router.post("/{position_id}/sell")
def sell(position_id: int, request: Request):
    db_path = request.app.state.settings.db_path
    closed = portfolio.close_position(db_path, position_id)
    if not closed:
        raise HTTPException(status_code=404, detail="Position not found or already closed")
    return {"ok": True}
```

- [ ] **Step 6: עדכון הטסטים הקיימים + הוספת טסטים חדשים**

`test_buy_then_list_shows_position` הקיים ב-`test_portfolio_api.py`
שולח `{"ticker": ..., "entry_price": ..., "stop_loss": ...}` בלי
`quantity` — כיוון ש-`BuyRequest` דורש `quantity` עכשיו (חובה, `gt=0`),
הטסט הזה ייכשל עם 422 אם לא יעודכן. עדכן אותו:

```python
# backend/tests/test_portfolio_api.py — עדכון הטסטים הקיימים
def test_buy_then_list_shows_position(client, monkeypatch):
    monkeypatch.setattr(
        portfolio_router, "fetch_current_price_and_change", lambda t: (120.0, 2.5)
    )
    _login(client)

    buy_resp = client.post(
        "/api/portfolio",
        json={"ticker": "aapl", "entry_price": 100.0, "quantity": 10, "stop_loss": 90.0},
    )
    assert buy_resp.status_code == 200
    position_id = buy_resp.json()["id"]

    list_resp = client.get("/api/portfolio")
    assert list_resp.status_code == 200
    positions = list_resp.json()
    assert len(positions) == 1
    assert positions[0]["ticker"] == "AAPL"
    assert positions[0]["quantity"] == 10.0
    assert positions[0]["current_price"] == 120.0
    assert positions[0]["pct_change"] == 2.5
    assert round(positions[0]["pnl_pct"], 2) == 20.0
    assert positions[0]["id"] == position_id


def test_sell_removes_position_from_open_list(client, monkeypatch):
    monkeypatch.setattr(
        portfolio_router, "fetch_current_price_and_change", lambda t: (120.0, 2.5)
    )
    _login(client)

    buy_resp = client.post(
        "/api/portfolio",
        json={"ticker": "AAPL", "entry_price": 100.0, "quantity": 10, "stop_loss": 90.0},
    )
    position_id = buy_resp.json()["id"]

    sell_resp = client.post(f"/api/portfolio/{position_id}/sell")
    assert sell_resp.status_code == 200

    list_resp = client.get("/api/portfolio")
    assert list_resp.json() == []


def test_sell_unknown_position_returns_404(client):
    _login(client)
    resp = client.post("/api/portfolio/999/sell")
    assert resp.status_code == 404


def test_buy_rejects_non_positive_quantity(client):
    _login(client)
    resp = client.post(
        "/api/portfolio",
        json={"ticker": "AAPL", "entry_price": 100.0, "quantity": 0, "stop_loss": 90.0},
    )
    assert resp.status_code == 422


def test_add_to_position_computes_weighted_average(client, monkeypatch):
    monkeypatch.setattr(
        portfolio_router, "fetch_current_price_and_change", lambda t: (150.0, 1.0)
    )
    _login(client)

    buy_resp = client.post(
        "/api/portfolio",
        json={"ticker": "AAPL", "entry_price": 100.0, "quantity": 10, "stop_loss": 90.0},
    )
    position_id = buy_resp.json()["id"]

    add_resp = client.post(
        f"/api/portfolio/{position_id}/add", json={"quantity": 10, "price": 120.0}
    )
    assert add_resp.status_code == 200

    positions = client.get("/api/portfolio").json()
    # (10*100 + 10*120) / 20 = 110
    assert positions[0]["entry_price"] == 110.0
    assert positions[0]["quantity"] == 20.0
    assert positions[0]["stop_loss"] == 90.0  # unchanged


def test_add_to_unknown_position_returns_404(client):
    _login(client)
    resp = client.post("/api/portfolio/999/add", json={"quantity": 1, "price": 100.0})
    assert resp.status_code == 404


def test_add_to_position_rejects_non_positive_price(client):
    _login(client)
    buy_resp = client.post(
        "/api/portfolio",
        json={"ticker": "AAPL", "entry_price": 100.0, "quantity": 10, "stop_loss": 90.0},
    )
    position_id = buy_resp.json()["id"]
    resp = client.post(
        f"/api/portfolio/{position_id}/add", json={"quantity": 1, "price": 0}
    )
    assert resp.status_code == 422


def test_update_stop_loss(client, monkeypatch):
    monkeypatch.setattr(
        portfolio_router, "fetch_current_price_and_change", lambda t: (150.0, 1.0)
    )
    _login(client)

    buy_resp = client.post(
        "/api/portfolio",
        json={"ticker": "AAPL", "entry_price": 100.0, "quantity": 10, "stop_loss": 90.0},
    )
    position_id = buy_resp.json()["id"]

    patch_resp = client.patch(f"/api/portfolio/{position_id}", json={"stop_loss": 95.0})
    assert patch_resp.status_code == 200

    positions = client.get("/api/portfolio").json()
    assert positions[0]["stop_loss"] == 95.0
    assert positions[0]["entry_price"] == 100.0  # unchanged


def test_update_stop_loss_unknown_position_returns_404(client):
    _login(client)
    resp = client.patch("/api/portfolio/999", json={"stop_loss": 95.0})
    assert resp.status_code == 404
```

(השאר `import app.routers.portfolio as portfolio_router` בראש הקובץ
כבר קיים משימוש קודם.)

- [ ] **Step 7: הרצת כל חבילת הטסטים**

Run: `cd backend && .venv/bin/pytest tests/ -v`
Expected: PASS (כל הטסטים הקיימים + החדשים)

- [ ] **Step 8: קומיט**

```bash
git add backend/app/db.py backend/app/portfolio.py backend/app/routers/portfolio.py backend/tests/test_db.py backend/tests/test_portfolio_api.py
git commit -m "feat(backend): add position quantity, buy-more averaging, stop-loss update"
```

---

### Task 2: Frontend scaffold (Vite + React + TypeScript + PWA config)

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/tsconfig.json`
- Create: `frontend/tsconfig.node.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/index.html`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/App.tsx`
- Modify: `.gitignore` (repo root)

**Interfaces:**
- Produces: פרויקט Vite שרץ (`npm run dev`) ונבנה (`npm run build`)
  בלי שגיאות. `App.tsx` כרגע placeholder בלבד — Task 6 יחליף אותו
  בניתוב האמיתי.

- [ ] **Step 1: יצירת מבנה התיקייה**

```bash
mkdir -p frontend/src/pages frontend/src/components frontend/src/hooks frontend/src/styles frontend/public
```

- [ ] **Step 2: `package.json`**

```json
{
  "name": "stocker-frontend",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "preview": "vite preview",
    "generate-icons": "node scripts/generate-icons.mjs"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-router-dom": "^6.26.0"
  },
  "devDependencies": {
    "@types/react": "^18.3.3",
    "@types/react-dom": "^18.3.0",
    "@vitejs/plugin-react": "^4.3.1",
    "typescript": "^5.5.3",
    "vite": "^5.4.0",
    "vite-plugin-pwa": "^0.20.0"
  }
}
```

- [ ] **Step 3: `tsconfig.json` ו-`tsconfig.node.json`**

```json
// frontend/tsconfig.json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true
  },
  "include": ["src"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

```json
// frontend/tsconfig.node.json
{
  "compilerOptions": {
    "composite": true,
    "skipLibCheck": true,
    "module": "ESNext",
    "moduleResolution": "bundler",
    "allowSyntheticDefaultImports": true
  },
  "include": ["vite.config.ts"]
}
```

- [ ] **Step 4: `vite.config.ts`**

```ts
// frontend/vite.config.ts
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { VitePWA } from "vite-plugin-pwa";

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: "autoUpdate",
      manifest: {
        name: "Stocker",
        short_name: "Stocker",
        description: "Personal stock screener and portfolio tracker",
        theme_color: "#12110F",
        background_color: "#12110F",
        display: "standalone",
        icons: [
          { src: "icon-192.png", sizes: "192x192", type: "image/png" },
          { src: "icon-512.png", sizes: "512x512", type: "image/png" },
        ],
      },
    }),
  ],
  server: {
    proxy: {
      "/api": "http://localhost:8000",
    },
  },
});
```

- [ ] **Step 5: `index.html`**

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <meta name="theme-color" content="#12110F" />
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link
      href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@400;500;600&display=swap"
      rel="stylesheet"
    />
    <title>Stocker</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 6: `src/main.tsx` ו-placeholder `src/App.tsx`**

```tsx
// frontend/src/main.tsx
import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
```

```tsx
// frontend/src/App.tsx — placeholder, Task 6 מחליף את זה בניתוב האמיתי
export default function App() {
  return <div>Stocker — coming soon</div>;
}
```

- [ ] **Step 7: עדכון `.gitignore` בשורש הריפו**

הוסף לקובץ הקיים (יש בו כבר `node_modules/`, `dist/` — ודא שהם שם;
אם לא, הוסף):

```
node_modules/
dist/
```

- [ ] **Step 8: התקנה ואימות**

```bash
cd frontend
npm install
npm run build
```

Expected: `npm run build` מסתיים בהצלחה, יוצר `frontend/dist/` עם
`index.html` ו-assets. אין שגיאות TypeScript.

```bash
npm run dev
```

Expected: שרת dev עולה (בד"כ על `http://localhost:5173`), פתיחה
בדפדפן מציגה "Stocker — coming soon". עצור את השרת (Ctrl+C) אחרי
האימות.

- [ ] **Step 9: קומיט**

```bash
git add frontend/package.json frontend/package-lock.json frontend/tsconfig.json frontend/tsconfig.node.json frontend/vite.config.ts frontend/index.html frontend/src/main.tsx frontend/src/App.tsx .gitignore
git commit -m "feat(frontend): scaffold Vite + React + TypeScript + PWA config"
```

---

### Task 3: עיצוב — טוקנים ויזואליים (theme.css)

**Files:**
- Create: `frontend/src/styles/theme.css`
- Modify: `frontend/src/main.tsx`

**Interfaces:**
- Produces: CSS custom properties (`--bg`, `--surface`, `--accent`,
  `--positive`, `--negative`, `--text`, `--text-dim`, `--font-mono`,
  `--font-sans`) וסגנונות בסיס (טבלאות, כפתורים, inputs) בשימוש בכל
  מסכי ה-frontend הבאים.

- [ ] **Step 1: כתיבת `theme.css`**

```css
/* frontend/src/styles/theme.css */
:root {
  --bg: #12110f;
  --surface: #1c1a17;
  --surface-hover: #24211d;
  --border: #2e2a24;
  --accent: #e8a33d;
  --positive: #3fb950;
  --negative: #f85149;
  --text: #e6e2da;
  --text-dim: #8b877e;
  --font-mono: "IBM Plex Mono", ui-monospace, "SF Mono", monospace;
  --font-sans: "IBM Plex Sans", -apple-system, sans-serif;
}

* {
  box-sizing: border-box;
}

html,
body,
#root {
  height: 100%;
  margin: 0;
}

body {
  background: var(--bg);
  color: var(--text);
  font-family: var(--font-sans);
  font-size: 15px;
  line-height: 1.5;
}

h1,
h2 {
  font-weight: 600;
}

table {
  width: 100%;
  border-collapse: collapse;
  font-family: var(--font-mono);
}

th,
td {
  padding: 10px 12px;
  text-align: left;
  border-bottom: 1px solid var(--border);
}

th {
  color: var(--text-dim);
  font-family: var(--font-sans);
  font-size: 12px;
  font-weight: 500;
}

td.numeric,
th.numeric {
  text-align: right;
  font-variant-numeric: tabular-nums;
}

tr:hover td {
  background: var(--surface-hover);
}

.positive {
  color: var(--positive);
}

.negative {
  color: var(--negative);
}

button {
  font-family: var(--font-sans);
  background: var(--accent);
  color: var(--bg);
  border: none;
  border-radius: 4px;
  padding: 8px 16px;
  font-weight: 600;
  cursor: pointer;
}

button:hover {
  opacity: 0.9;
}

button.secondary {
  background: transparent;
  color: var(--text);
  border: 1px solid var(--border);
}

input {
  font-family: var(--font-mono);
  background: var(--surface);
  color: var(--text);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 8px 10px;
}

input:focus,
button:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 1px;
}

a {
  color: var(--accent);
  text-decoration: none;
}

.error-text {
  color: var(--negative);
  font-size: 13px;
}

.dim {
  color: var(--text-dim);
  font-size: 13px;
}

@keyframes price-flash {
  0% {
    background-color: rgba(232, 163, 61, 0.25);
  }
  100% {
    background-color: transparent;
  }
}

.price-flash {
  animation: price-flash 0.6s ease-out;
}

@media (prefers-reduced-motion: reduce) {
  .price-flash {
    animation: none;
  }
}

@media (max-width: 640px) {
  th,
  td {
    padding: 8px 6px;
    font-size: 13px;
  }
}
```

- [ ] **Step 2: ייבוא ה-CSS ב-`main.tsx`**

```tsx
// frontend/src/main.tsx
import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./styles/theme.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
```

- [ ] **Step 3: אימות ויזואלי**

```bash
cd frontend && npm run dev
```

Expected: רקע כהה (`#12110F`), טקסט בהיר. פתח את הדפדפן ואמת ידנית.
עצור את השרת אחרי האימות.

- [ ] **Step 4: קומיט**

```bash
git add frontend/src/styles/theme.css frontend/src/main.tsx
git commit -m "feat(frontend): add dark trading-terminal design tokens"
```

---

### Task 4: לקוח API (`api.ts`)

**Files:**
- Create: `frontend/src/api.ts`

**Interfaces:**
- Consumes: ה-endpoints הקיימים ב-backend (`/api/auth/*`,
  `/api/portfolio*`, `/api/recommendations`, `/api/indices*`), כולל
  התוספות מ-Task 1 (`/add`, `PATCH`).
- Produces: `ApiError` class (`status: number`), types
  (`Position`, `RecommendationResult`, `RecommendationsResponse`,
  `WatchedIndex`), ופונקציות: `login`, `logout`, `getPortfolio`,
  `buyPosition`, `addToPosition`, `updateStopLoss`, `sellPosition`,
  `getRecommendations`, `getIndices`, `addIndex`, `removeIndex` —
  בשימוש בכל מסכי ה-frontend (Tasks 7-11).

- [ ] **Step 1: כתיבת `api.ts`**

```ts
// frontend/src/api.ts

export interface Position {
  id: number;
  ticker: string;
  entry_price: number;
  quantity: number;
  stop_loss: number;
  entry_date: string;
  current_price: number | null;
  pct_change: number | null;
  pnl_pct: number | null;
}

export interface RecommendationResult {
  ticker: string;
  score: number;
  current_price: number | null;
  pct_change: number | null;
  pct_from_52w_high: number;
  relative_strength: number;
  avg_dollar_volume: number;
}

export interface RecommendationsResponse {
  run_date: string | null;
  results: RecommendationResult[];
}

export interface WatchedIndex {
  symbol: string;
  display_name: string;
  current_price: number | null;
  pct_change: number | null;
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(path, {
    credentials: "same-origin",
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new ApiError(response.status, body.detail || response.statusText);
  }
  return response.json() as Promise<T>;
}

export function login(password: string): Promise<{ ok: boolean }> {
  return apiFetch("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ password }),
  });
}

export function logout(): Promise<{ ok: boolean }> {
  return apiFetch("/api/auth/logout", { method: "POST" });
}

export function getPortfolio(): Promise<Position[]> {
  return apiFetch("/api/portfolio");
}

export function buyPosition(
  ticker: string,
  entryPrice: number,
  quantity: number,
  stopLoss: number
): Promise<{ id: number }> {
  return apiFetch("/api/portfolio", {
    method: "POST",
    body: JSON.stringify({
      ticker,
      entry_price: entryPrice,
      quantity,
      stop_loss: stopLoss,
    }),
  });
}

export function addToPosition(
  id: number,
  quantity: number,
  price: number
): Promise<{ ok: boolean }> {
  return apiFetch(`/api/portfolio/${id}/add`, {
    method: "POST",
    body: JSON.stringify({ quantity, price }),
  });
}

export function updateStopLoss(id: number, stopLoss: number): Promise<{ ok: boolean }> {
  return apiFetch(`/api/portfolio/${id}`, {
    method: "PATCH",
    body: JSON.stringify({ stop_loss: stopLoss }),
  });
}

export function sellPosition(id: number): Promise<{ ok: boolean }> {
  return apiFetch(`/api/portfolio/${id}/sell`, { method: "POST" });
}

export function getRecommendations(): Promise<RecommendationsResponse> {
  return apiFetch("/api/recommendations");
}

export function getIndices(): Promise<WatchedIndex[]> {
  return apiFetch("/api/indices");
}

export function addIndex(symbol: string, displayName: string): Promise<{ ok: boolean }> {
  return apiFetch("/api/indices", {
    method: "POST",
    body: JSON.stringify({ symbol, display_name: displayName }),
  });
}

export function removeIndex(symbol: string): Promise<{ ok: boolean }> {
  return apiFetch(`/api/indices/${symbol}`, { method: "DELETE" });
}
```

- [ ] **Step 2: אימות קומפילציה**

```bash
cd frontend && npm run build
```

Expected: PASS, בלי שגיאות TypeScript (הקובץ עדיין לא בשימוש בשום
מקום, אבל הוא חייב לקמפל בפני עצמו).

- [ ] **Step 3: קומיט**

```bash
git add frontend/src/api.ts
git commit -m "feat(frontend): add typed API client"
```

---

### Task 5: קומפוננטות משותפות (PriceCell, RefreshBar, usePolling)

**Files:**
- Create: `frontend/src/hooks/usePolling.ts`
- Create: `frontend/src/components/PriceCell.tsx`
- Create: `frontend/src/components/RefreshBar.tsx`

**Interfaces:**
- Consumes: כלום (מודולים עצמאיים).
- Produces: `usePolling(fetcher: () => Promise<void>, intervalMs?: number)
  -> { lastUpdated: Date | null, refresh: () => Promise<void> }`;
  `<PriceCell price={number|null} pctChange={number|null} />`;
  `<RefreshBar lastUpdated={Date|null} onRefresh={() => void} />` —
  בשימוש בכל מסכי תיק/המלצות/מדדים (Tasks 8-10).

- [ ] **Step 1: `usePolling.ts`**

```tsx
// frontend/src/hooks/usePolling.ts
import { useCallback, useEffect, useRef, useState } from "react";

export function usePolling(fetcher: () => Promise<void>, intervalMs = 60000) {
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;

  const refresh = useCallback(async () => {
    await fetcherRef.current();
    setLastUpdated(new Date());
  }, []);

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, intervalMs);
    return () => clearInterval(id);
  }, [refresh, intervalMs]);

  return { lastUpdated, refresh };
}
```

- [ ] **Step 2: `PriceCell.tsx`**

```tsx
// frontend/src/components/PriceCell.tsx
import { useEffect, useRef, useState } from "react";

export function PriceCell({
  price,
  pctChange,
}: {
  price: number | null;
  pctChange: number | null;
}) {
  const [flash, setFlash] = useState(false);
  const previous = useRef<number | null>(price);

  useEffect(() => {
    if (previous.current !== null && price !== null && previous.current !== price) {
      setFlash(true);
      const timeout = setTimeout(() => setFlash(false), 600);
      previous.current = price;
      return () => clearTimeout(timeout);
    }
    previous.current = price;
  }, [price]);

  if (price === null) {
    return <span className="dim">—</span>;
  }

  const colorClass = pctChange === null ? "" : pctChange >= 0 ? "positive" : "negative";

  return (
    <span className={flash ? "price-flash" : ""}>
      {price.toFixed(2)}
      {pctChange !== null && (
        <span className={colorClass} style={{ marginLeft: "8px", fontSize: "13px" }}>
          {pctChange >= 0 ? "+" : ""}
          {pctChange.toFixed(2)}%
        </span>
      )}
    </span>
  );
}
```

- [ ] **Step 3: `RefreshBar.tsx`**

```tsx
// frontend/src/components/RefreshBar.tsx
export function RefreshBar({
  lastUpdated,
  onRefresh,
}: {
  lastUpdated: Date | null;
  onRefresh: () => void;
}) {
  return (
    <div
      style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        marginBottom: "16px",
      }}
    >
      <span className="dim">
        {lastUpdated ? `Updated ${lastUpdated.toLocaleTimeString()}` : "Loading…"}
      </span>
      <button className="secondary" onClick={onRefresh}>
        Refresh
      </button>
    </div>
  );
}
```

- [ ] **Step 4: אימות קומפילציה**

```bash
cd frontend && npm run build
```

Expected: PASS

- [ ] **Step 5: קומיט**

```bash
git add frontend/src/hooks/usePolling.ts frontend/src/components/PriceCell.tsx frontend/src/components/RefreshBar.tsx
git commit -m "feat(frontend): add polling hook and price/refresh components"
```

---

### Task 6: ניתוב מלא (NavBar + App.tsx)

**Files:**
- Create: `frontend/src/components/NavBar.tsx`
- Modify: `frontend/src/App.tsx`

**Interfaces:**
- Consumes: כלום עדיין. משימה זו רצה **לפני** Tasks 7-11 (העמודים
  האמיתיים עדיין לא קיימים), ולכן `App.tsx` צריך משהו לייבא —
  Step 1 יוצר stub מינימלי לכל אחד מחמשת העמודים. כל Task מ-7 עד 11
  **מחליף** את ה-stub שלו בעמוד האמיתי (לא מוסיף קובץ חדש).
- Produces: ניתוב מלא בין 5 המסכים; `<Layout>` wrapper עם `<NavBar>`.

- [ ] **Step 1: יצירת stub לכל אחד מ-5 העמודים**

```tsx
// frontend/src/pages/Login.tsx
export default function Login() {
  return <div>Login — coming soon</div>;
}
```

```tsx
// frontend/src/pages/Portfolio.tsx
export default function Portfolio() {
  return <div>Portfolio — coming soon</div>;
}
```

```tsx
// frontend/src/pages/Recommendations.tsx
export default function Recommendations() {
  return <div>Recommendations — coming soon</div>;
}
```

```tsx
// frontend/src/pages/Indices.tsx
export default function Indices() {
  return <div>Indices — coming soon</div>;
}
```

```tsx
// frontend/src/pages/Trade.tsx
export default function Trade() {
  return <div>Trade — coming soon</div>;
}
```

- [ ] **Step 2: `NavBar.tsx`**

```tsx
// frontend/src/components/NavBar.tsx
import { NavLink } from "react-router-dom";
import type { CSSProperties } from "react";

export default function NavBar() {
  return (
    <nav
      style={{
        display: "flex",
        alignItems: "center",
        gap: "24px",
        padding: "14px 20px",
        borderBottom: "1px solid var(--border)",
        fontFamily: "var(--font-mono)",
      }}
    >
      <span style={{ color: "var(--accent)", fontWeight: 600 }}>STOCKER</span>
      <NavLink to="/portfolio" style={navLinkStyle}>
        Portfolio
      </NavLink>
      <NavLink to="/recommendations" style={navLinkStyle}>
        Recommendations
      </NavLink>
      <NavLink to="/indices" style={navLinkStyle}>
        Indices
      </NavLink>
    </nav>
  );
}

function navLinkStyle({ isActive }: { isActive: boolean }): CSSProperties {
  return {
    color: isActive ? "var(--accent)" : "var(--text-dim)",
    fontSize: "14px",
  };
}
```

- [ ] **Step 3: `App.tsx` — ניתוב מלא**

```tsx
// frontend/src/App.tsx
import type { ReactNode } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import NavBar from "./components/NavBar";
import Login from "./pages/Login";
import Portfolio from "./pages/Portfolio";
import Recommendations from "./pages/Recommendations";
import Indices from "./pages/Indices";
import Trade from "./pages/Trade";

function Layout({ children }: { children: ReactNode }) {
  return (
    <>
      <NavBar />
      <main style={{ padding: "20px", maxWidth: "960px", margin: "0 auto" }}>
        {children}
      </main>
    </>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route
          path="/portfolio"
          element={
            <Layout>
              <Portfolio />
            </Layout>
          }
        />
        <Route
          path="/recommendations"
          element={
            <Layout>
              <Recommendations />
            </Layout>
          }
        />
        <Route
          path="/indices"
          element={
            <Layout>
              <Indices />
            </Layout>
          }
        />
        <Route
          path="/trade/:ticker"
          element={
            <Layout>
              <Trade />
            </Layout>
          }
        />
        <Route path="*" element={<Navigate to="/portfolio" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
```

- [ ] **Step 4: אימות**

```bash
cd frontend && npm run build
```

Expected: PASS (גם אם חלק מהעמודים הם עדיין stub-ים).

```bash
npm run dev
```

Expected: `/portfolio` מציג NavBar + "Portfolio — coming soon" (או את
העמוד האמיתי אם Task 8 כבר רץ). ניווט בין הטאבים עובד. עצור את השרת
אחרי האימות.

- [ ] **Step 5: קומיט**

```bash
git add frontend/src/App.tsx frontend/src/components/NavBar.tsx frontend/src/pages/
git commit -m "feat(frontend): wire full routing with nav bar"
```

---

### Task 7: מסך Login

**Files:**
- Create: `frontend/src/pages/Login.tsx` (מחליף stub אם קיים)

**Interfaces:**
- Consumes: `login` מ-`api.ts` (Task 4).
- Produces: מסך התחברות שמפנה ל-`/portfolio` בהצלחה.

- [ ] **Step 1: כתיבת `Login.tsx`**

```tsx
// frontend/src/pages/Login.tsx
import { useState } from "react";
import type { FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { login } from "../api";

export default function Login() {
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const navigate = useNavigate();

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await login(password);
      navigate("/portfolio");
    } catch {
      setError("Wrong password.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div
      style={{
        display: "flex",
        height: "100vh",
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      <form onSubmit={handleSubmit} style={{ width: "280px" }}>
        <h1
          style={{
            fontFamily: "var(--font-mono)",
            color: "var(--accent)",
            marginBottom: "24px",
          }}
        >
          STOCKER
        </h1>
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="Password"
          autoFocus
          required
          style={{ display: "block", width: "100%", marginBottom: "12px" }}
        />
        <button type="submit" disabled={busy} style={{ width: "100%" }}>
          {busy ? "Signing in…" : "Sign in"}
        </button>
        {error && <p className="error-text">{error}</p>}
      </form>
    </div>
  );
}
```

- [ ] **Step 2: אימות ידני**

```bash
cd backend && source .venv/bin/activate && export STOCKER_SESSION_SECRET=dev STOCKER_LOGIN_PASSWORD=dev123 STOCKER_DB_PATH=./stocker.db && uvicorn app.main:create_app --factory --reload &
cd frontend && npm run dev
```

Expected: `http://localhost:5173/login` מציג טופס סיסמה; סיסמה שגויה
מציגה "Wrong password."; סיסמה נכונה (`dev123`) מפנה ל-`/portfolio`.
עצור את שני השרתים אחרי האימות (`kill %1` להורדת ה-backend, Ctrl+C
לעצירת ה-frontend).

- [ ] **Step 3: קומיט**

```bash
git add frontend/src/pages/Login.tsx
git commit -m "feat(frontend): add login page"
```

---

### Task 8: מסך Portfolio

**Files:**
- Create: `frontend/src/pages/Portfolio.tsx` (מחליף stub אם קיים)

**Interfaces:**
- Consumes: `getPortfolio`, `ApiError`, `Position` מ-`api.ts`;
  `usePolling` מ-`hooks/usePolling.ts`; `PriceCell`, `RefreshBar`
  מ-`components/`.
- Produces: מסך תיק שמנווט ל-`/trade/:ticker` עם
  `state: { position }` בלחיצה על שורה.

- [ ] **Step 1: כתיבת `Portfolio.tsx`**

```tsx
// frontend/src/pages/Portfolio.tsx
import { useCallback, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ApiError, getPortfolio } from "../api";
import type { Position } from "../api";
import { usePolling } from "../hooks/usePolling";
import { PriceCell } from "../components/PriceCell";
import { RefreshBar } from "../components/RefreshBar";

export default function Portfolio() {
  const [positions, setPositions] = useState<Position[]>([]);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  const fetchPositions = useCallback(async () => {
    try {
      const data = await getPortfolio();
      setPositions(data);
      setError(null);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        navigate("/login");
        return;
      }
      setError("Could not load your portfolio.");
    }
  }, [navigate]);

  const { lastUpdated, refresh } = usePolling(fetchPositions);

  return (
    <div>
      <h1 style={{ fontFamily: "var(--font-mono)" }}>Portfolio</h1>
      <RefreshBar lastUpdated={lastUpdated} onRefresh={refresh} />
      {error && <p className="error-text">{error}</p>}
      {positions.length === 0 && !error ? (
        <p className="dim">No open positions yet. Buy something from Recommendations.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Ticker</th>
              <th className="numeric">Qty</th>
              <th className="numeric">Entry</th>
              <th className="numeric">Stop</th>
              <th className="numeric">Price</th>
              <th className="numeric">P/L</th>
            </tr>
          </thead>
          <tbody>
            {positions.map((p) => (
              <tr
                key={p.id}
                onClick={() => navigate(`/trade/${p.ticker}`, { state: { position: p } })}
                style={{ cursor: "pointer" }}
              >
                <td>{p.ticker}</td>
                <td className="numeric">{p.quantity}</td>
                <td className="numeric">{p.entry_price.toFixed(2)}</td>
                <td className="numeric">{p.stop_loss.toFixed(2)}</td>
                <td className="numeric">
                  <PriceCell price={p.current_price} pctChange={p.pct_change} />
                </td>
                <td
                  className={`numeric ${
                    p.pnl_pct !== null && p.pnl_pct >= 0 ? "positive" : "negative"
                  }`}
                >
                  {p.pnl_pct !== null
                    ? `${p.pnl_pct >= 0 ? "+" : ""}${p.pnl_pct.toFixed(2)}%`
                    : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
```

- [ ] **Step 2: אימות ידני**

הרץ backend + frontend (כמו ב-Task 7), התחבר, ונווט ל-`/portfolio`.

Expected: אם אין פוזיציות — הודעת "No open positions yet". אם יש
(אפשר ליצור אחת דרך `curl` ל-`POST /api/portfolio` עם `quantity`) —
טבלה עם הנתונים, רענון אוטומטי אחרי 60 שניות (או מיידי דרך כפתור
Refresh).

- [ ] **Step 3: קומיט**

```bash
git add frontend/src/pages/Portfolio.tsx
git commit -m "feat(frontend): add portfolio page"
```

---

### Task 9: מסך Recommendations

**Files:**
- Create: `frontend/src/pages/Recommendations.tsx` (מחליף stub אם קיים)

**Interfaces:**
- Consumes: `getRecommendations`, `ApiError`, `RecommendationResult`
  מ-`api.ts`; `usePolling`; `PriceCell`, `RefreshBar`.
- Produces: מסך המלצות שמנווט ל-`/trade/:ticker` **בלי** `state`
  (מציין קנייה ראשונה, ר' Task 11).

- [ ] **Step 1: כתיבת `Recommendations.tsx`**

```tsx
// frontend/src/pages/Recommendations.tsx
import { useCallback, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ApiError, getRecommendations } from "../api";
import type { RecommendationResult } from "../api";
import { usePolling } from "../hooks/usePolling";
import { PriceCell } from "../components/PriceCell";
import { RefreshBar } from "../components/RefreshBar";

export default function Recommendations() {
  const [runDate, setRunDate] = useState<string | null>(null);
  const [results, setResults] = useState<RecommendationResult[]>([]);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  const fetchRecommendations = useCallback(async () => {
    try {
      const data = await getRecommendations();
      setRunDate(data.run_date);
      setResults(data.results);
      setError(null);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        navigate("/login");
        return;
      }
      setError("Could not load recommendations.");
    }
  }, [navigate]);

  const { lastUpdated, refresh } = usePolling(fetchRecommendations);

  return (
    <div>
      <h1 style={{ fontFamily: "var(--font-mono)" }}>Recommendations</h1>
      <p className="dim">{runDate ? `Screener run: ${runDate}` : "No screener run yet."}</p>
      <RefreshBar lastUpdated={lastUpdated} onRefresh={refresh} />
      {error && <p className="error-text">{error}</p>}
      {results.length === 0 && !error ? (
        <p className="dim">Nothing qualifies yet — check back after the next screener run.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Ticker</th>
              <th className="numeric">Price</th>
              <th className="numeric">Score</th>
            </tr>
          </thead>
          <tbody>
            {results.map((r) => (
              <tr
                key={r.ticker}
                onClick={() => navigate(`/trade/${r.ticker}`)}
                style={{ cursor: "pointer" }}
              >
                <td>{r.ticker}</td>
                <td className="numeric">
                  <PriceCell price={r.current_price} pctChange={r.pct_change} />
                </td>
                <td className="numeric">{r.score.toFixed(1)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
```

- [ ] **Step 2: אימות ידני**

הרץ backend + frontend, התחבר, נווט ל-`/recommendations`.

Expected: אם `screener_results` ריק — "Nothing qualifies yet…". אחרת
טבלה עם דירוג. לחיצה על שורה מנווטת ל-`/trade/<ticker>` (יציג
placeholder עד Task 11).

- [ ] **Step 3: קומיט**

```bash
git add frontend/src/pages/Recommendations.tsx
git commit -m "feat(frontend): add recommendations page"
```

---

### Task 10: מסך Indices

**Files:**
- Create: `frontend/src/pages/Indices.tsx` (מחליף stub אם קיים)

**Interfaces:**
- Consumes: `getIndices`, `addIndex`, `removeIndex`, `ApiError`,
  `WatchedIndex` מ-`api.ts`; `usePolling`; `PriceCell`, `RefreshBar`.
- Produces: מסך מדדים עם הוספה/הסרה.

- [ ] **Step 1: כתיבת `Indices.tsx`**

```tsx
// frontend/src/pages/Indices.tsx
import { useCallback, useState } from "react";
import type { FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { addIndex, ApiError, getIndices, removeIndex } from "../api";
import type { WatchedIndex } from "../api";
import { usePolling } from "../hooks/usePolling";
import { PriceCell } from "../components/PriceCell";
import { RefreshBar } from "../components/RefreshBar";

export default function Indices() {
  const [indices, setIndices] = useState<WatchedIndex[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [symbol, setSymbol] = useState("");
  const [displayName, setDisplayName] = useState("");
  const navigate = useNavigate();

  const fetchIndices = useCallback(async () => {
    try {
      const data = await getIndices();
      setIndices(data);
      setError(null);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        navigate("/login");
        return;
      }
      setError("Could not load indices.");
    }
  }, [navigate]);

  const { lastUpdated, refresh } = usePolling(fetchIndices);

  async function handleAdd(e: FormEvent) {
    e.preventDefault();
    if (!symbol.trim() || !displayName.trim()) return;
    try {
      await addIndex(symbol.trim(), displayName.trim());
      setSymbol("");
      setDisplayName("");
      await refresh();
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        navigate("/login");
        return;
      }
      setError("Could not add index.");
    }
  }

  async function handleRemove(sym: string) {
    try {
      await removeIndex(sym);
      await refresh();
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        navigate("/login");
        return;
      }
      setError("Could not remove index.");
    }
  }

  return (
    <div>
      <h1 style={{ fontFamily: "var(--font-mono)" }}>Indices</h1>
      <RefreshBar lastUpdated={lastUpdated} onRefresh={refresh} />
      {error && <p className="error-text">{error}</p>}
      <table>
        <thead>
          <tr>
            <th>Symbol</th>
            <th>Name</th>
            <th className="numeric">Price</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {indices.map((i) => (
            <tr key={i.symbol}>
              <td>{i.symbol}</td>
              <td>{i.display_name}</td>
              <td className="numeric">
                <PriceCell price={i.current_price} pctChange={i.pct_change} />
              </td>
              <td>
                <button className="secondary" onClick={() => handleRemove(i.symbol)}>
                  Remove
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <form onSubmit={handleAdd} style={{ marginTop: "24px" }}>
        <input
          value={symbol}
          onChange={(e) => setSymbol(e.target.value)}
          placeholder="Symbol (e.g. SOXX)"
          required
          style={{ marginRight: "8px" }}
        />
        <input
          value={displayName}
          onChange={(e) => setDisplayName(e.target.value)}
          placeholder="Display name"
          required
          style={{ marginRight: "8px" }}
        />
        <button type="submit">Add index</button>
      </form>
    </div>
  );
}
```

- [ ] **Step 2: אימות ידני**

הרץ backend + frontend, התחבר, נווט ל-`/indices`. הוסף מדד (לדוגמה
`SOXX` / "Semiconductors"), ודא שהוא מופיע בטבלה עם מחיר, הסר אותו.

- [ ] **Step 3: קומיט**

```bash
git add frontend/src/pages/Indices.tsx
git commit -m "feat(frontend): add indices page"
```

---

### Task 11: מסך Trade (קנייה / קנה עוד / עדכן סטופלוס / מכירה)

**Files:**
- Create: `frontend/src/pages/Trade.tsx` (מחליף stub אם קיים)

**Interfaces:**
- Consumes: `buyPosition`, `addToPosition`, `updateStopLoss`,
  `sellPosition`, `ApiError`, `Position` מ-`api.ts`.
- Produces: מסך עסקה — קנייה ראשונה (בלי `location.state.position`)
  לעומת ניהול פוזיציה קיימת (עם `location.state.position`, כפי
  שנשלח מ-`Portfolio.tsx`).

- [ ] **Step 1: כתיבת `Trade.tsx`**

```tsx
// frontend/src/pages/Trade.tsx
import { useState } from "react";
import type { FormEvent } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import { addToPosition, ApiError, buyPosition, sellPosition, updateStopLoss } from "../api";
import type { Position } from "../api";

type TradeState = { position?: Position };

export default function Trade() {
  const { ticker } = useParams<{ ticker: string }>();
  const location = useLocation();
  const navigate = useNavigate();
  const position = (location.state as TradeState | null)?.position;
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function handleAuthError(err: unknown): Promise<boolean> {
    if (err instanceof ApiError && err.status === 401) {
      navigate("/login");
      return true;
    }
    return false;
  }

  async function handleBuy(entryPrice: number, quantity: number, stopLoss: number) {
    setBusy(true);
    setError(null);
    try {
      await buyPosition(ticker!, entryPrice, quantity, stopLoss);
      navigate("/portfolio");
    } catch (err) {
      if (!(await handleAuthError(err))) {
        setError("Could not open position. Check your inputs and try again.");
      }
    } finally {
      setBusy(false);
    }
  }

  async function handleAddToPosition(quantity: number, price: number) {
    if (!position) return;
    setBusy(true);
    setError(null);
    try {
      await addToPosition(position.id, quantity, price);
      navigate("/portfolio");
    } catch (err) {
      if (!(await handleAuthError(err))) {
        setError("Could not add to position. Check your inputs and try again.");
      }
    } finally {
      setBusy(false);
    }
  }

  async function handleUpdateStopLoss(stopLoss: number) {
    if (!position) return;
    setBusy(true);
    setError(null);
    try {
      await updateStopLoss(position.id, stopLoss);
      navigate("/portfolio");
    } catch (err) {
      if (!(await handleAuthError(err))) {
        setError("Could not update stop-loss. Check your input and try again.");
      }
    } finally {
      setBusy(false);
    }
  }

  async function handleSell() {
    if (!position) return;
    setBusy(true);
    setError(null);
    try {
      await sellPosition(position.id);
      navigate("/portfolio");
    } catch (err) {
      if (!(await handleAuthError(err))) {
        setError("Could not sell position. Try again.");
      }
    } finally {
      setBusy(false);
    }
  }

  if (position) {
    return (
      <div style={{ maxWidth: "420px" }}>
        <h1 style={{ fontFamily: "var(--font-mono)" }}>{position.ticker}</h1>
        <p className="dim">
          {position.quantity} shares @ avg {position.entry_price.toFixed(2)} · stop{" "}
          {position.stop_loss.toFixed(2)}
        </p>

        <section style={{ marginTop: "24px" }}>
          <h2 style={{ fontSize: "15px" }}>Buy more</h2>
          <AddForm onSubmit={handleAddToPosition} busy={busy} />
        </section>

        <section style={{ marginTop: "24px" }}>
          <h2 style={{ fontSize: "15px" }}>Update stop-loss</h2>
          <StopLossForm
            onSubmit={handleUpdateStopLoss}
            initialValue={position.stop_loss}
            busy={busy}
          />
        </section>

        <section style={{ marginTop: "24px" }}>
          <button className="secondary" onClick={handleSell} disabled={busy}>
            Sell entire position
          </button>
        </section>

        {error && <p className="error-text">{error}</p>}
      </div>
    );
  }

  return (
    <div style={{ maxWidth: "420px" }}>
      <h1 style={{ fontFamily: "var(--font-mono)" }}>Buy {ticker}</h1>
      <BuyForm onSubmit={handleBuy} busy={busy} />
      {error && <p className="error-text">{error}</p>}
    </div>
  );
}

function BuyForm({
  onSubmit,
  busy,
}: {
  onSubmit: (entryPrice: number, quantity: number, stopLoss: number) => void;
  busy: boolean;
}) {
  const [entryPrice, setEntryPrice] = useState("");
  const [quantity, setQuantity] = useState("");
  const [stopLoss, setStopLoss] = useState("");

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        onSubmit(Number(entryPrice), Number(quantity), Number(stopLoss));
      }}
    >
      <label className="dim">Entry price</label>
      <input
        value={entryPrice}
        onChange={(e) => setEntryPrice(e.target.value)}
        type="number"
        step="0.01"
        min="0.01"
        required
        style={{ display: "block", width: "100%", marginBottom: "12px" }}
      />
      <label className="dim">Quantity</label>
      <input
        value={quantity}
        onChange={(e) => setQuantity(e.target.value)}
        type="number"
        step="0.0001"
        min="0.0001"
        required
        style={{ display: "block", width: "100%", marginBottom: "12px" }}
      />
      <label className="dim">Stop-loss</label>
      <input
        value={stopLoss}
        onChange={(e) => setStopLoss(e.target.value)}
        type="number"
        step="0.01"
        min="0.01"
        required
        style={{ display: "block", width: "100%", marginBottom: "16px" }}
      />
      <button type="submit" disabled={busy}>
        Buy
      </button>
    </form>
  );
}

function AddForm({
  onSubmit,
  busy,
}: {
  onSubmit: (quantity: number, price: number) => void;
  busy: boolean;
}) {
  const [quantity, setQuantity] = useState("");
  const [price, setPrice] = useState("");

  return (
    <form
      onSubmit={(e: FormEvent) => {
        e.preventDefault();
        onSubmit(Number(quantity), Number(price));
      }}
    >
      <input
        value={quantity}
        onChange={(e) => setQuantity(e.target.value)}
        type="number"
        step="0.0001"
        min="0.0001"
        placeholder="Quantity"
        required
        style={{ marginRight: "8px" }}
      />
      <input
        value={price}
        onChange={(e) => setPrice(e.target.value)}
        type="number"
        step="0.01"
        min="0.01"
        placeholder="Price"
        required
        style={{ marginRight: "8px" }}
      />
      <button type="submit" disabled={busy}>
        Add
      </button>
    </form>
  );
}

function StopLossForm({
  onSubmit,
  initialValue,
  busy,
}: {
  onSubmit: (stopLoss: number) => void;
  initialValue: number;
  busy: boolean;
}) {
  const [stopLoss, setStopLoss] = useState(String(initialValue));

  return (
    <form
      onSubmit={(e: FormEvent) => {
        e.preventDefault();
        onSubmit(Number(stopLoss));
      }}
    >
      <input
        value={stopLoss}
        onChange={(e) => setStopLoss(e.target.value)}
        type="number"
        step="0.01"
        min="0.01"
        required
        style={{ marginRight: "8px" }}
      />
      <button type="submit" disabled={busy}>
        Update
      </button>
    </form>
  );
}
```

- [ ] **Step 2: אימות ידני**

הרץ backend + frontend, התחבר:
1. מ-`/recommendations`, לחץ על טיקר → טופס קנייה ראשונה → קנה → נווט
   חזרה ל-`/portfolio` והפוזיציה מופיעה.
2. מ-`/portfolio`, לחץ על השורה שנוצרה → מסך ניהול עם 3 פעולות. נסה
   "Buy more" (ודא שהכמות/מחיר הממוצע התעדכנו נכון ב-`/portfolio`),
   "Update stop-loss", ולבסוף "Sell entire position" (הפוזיציה נעלמת
   מהתיק).

- [ ] **Step 3: קומיט**

```bash
git add frontend/src/pages/Trade.tsx
git commit -m "feat(frontend): add trade page (buy, add-to-position, stop-loss, sell)"
```

---

### Task 12: אייקוני PWA + אימות manifest

**Files:**
- Create: `frontend/scripts/generate-icons.mjs`
- Create: `frontend/public/icon-192.png` (נוצר בהרצה, לא נכתב ידנית)
- Create: `frontend/public/icon-512.png` (נוצר בהרצה, לא נכתב ידנית)

**Interfaces:**
- Produces: קבצי PNG תקינים בגדלים 192×192 ו-512×512, המאוזכרים
  ב-`vite.config.ts` (Task 2) — נדרשים כדי ש-`vite-plugin-pwa` יבנה
  manifest תקין.

- [ ] **Step 1: כתיבת סקריפט יצירת האייקונים**

```js
// frontend/scripts/generate-icons.mjs
import { writeFileSync } from "node:fs";
import { deflateSync } from "node:zlib";

const CRC_TABLE = (() => {
  const table = new Uint32Array(256);
  for (let n = 0; n < 256; n++) {
    let c = n;
    for (let k = 0; k < 8; k++) {
      c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
    }
    table[n] = c >>> 0;
  }
  return table;
})();

function crc32(buf) {
  let crc = 0xffffffff;
  for (const byte of buf) {
    crc = CRC_TABLE[(crc ^ byte) & 0xff] ^ (crc >>> 8);
  }
  return (crc ^ 0xffffffff) >>> 0;
}

function chunk(type, data) {
  const typeBuf = Buffer.from(type, "ascii");
  const lengthBuf = Buffer.alloc(4);
  lengthBuf.writeUInt32BE(data.length, 0);
  const crcBuf = Buffer.alloc(4);
  crcBuf.writeUInt32BE(crc32(Buffer.concat([typeBuf, data])), 0);
  return Buffer.concat([lengthBuf, typeBuf, data, crcBuf]);
}

function solidColorPng(size, [r, g, b]) {
  const ihdr = Buffer.alloc(13);
  ihdr.writeUInt32BE(size, 0);
  ihdr.writeUInt32BE(size, 4);
  ihdr[8] = 8; // bit depth
  ihdr[9] = 2; // color type: RGB
  ihdr[10] = 0;
  ihdr[11] = 0;
  ihdr[12] = 0;

  const rowLength = size * 3;
  const raw = Buffer.alloc((rowLength + 1) * size);
  for (let y = 0; y < size; y++) {
    const rowStart = y * (rowLength + 1);
    raw[rowStart] = 0; // filter: none
    for (let x = 0; x < size; x++) {
      const px = rowStart + 1 + x * 3;
      raw[px] = r;
      raw[px + 1] = g;
      raw[px + 2] = b;
    }
  }

  const idat = deflateSync(raw);
  const signature = Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]);

  return Buffer.concat([
    signature,
    chunk("IHDR", ihdr),
    chunk("IDAT", idat),
    chunk("IEND", Buffer.alloc(0)),
  ]);
}

const AMBER = [0xe8, 0xa3, 0x3d];

writeFileSync(new URL("../public/icon-192.png", import.meta.url), solidColorPng(192, AMBER));
writeFileSync(new URL("../public/icon-512.png", import.meta.url), solidColorPng(512, AMBER));

console.log("Generated public/icon-192.png and public/icon-512.png");
```

- [ ] **Step 2: הרצת הסקריפט**

```bash
cd frontend && npm run generate-icons
```

Expected: מדפיס "Generated public/icon-192.png and public/icon-512.png",
שני הקבצים נוצרים ב-`frontend/public/`.

- [ ] **Step 3: אימות שהקבצים תקינים ושה-build כולל אותם**

```bash
file public/icon-192.png public/icon-512.png
npm run build
ls dist/ | grep -i manifest
```

Expected: `file` מזהה את שני הקבצים כ-`PNG image data, 192 x 192`
ו-`512 x 512` בהתאמה. ה-build מייצר קובץ manifest
(`manifest.webmanifest` או דומה) בתוך `dist/`.

- [ ] **Step 4: קומיט**

```bash
git add frontend/scripts/generate-icons.mjs frontend/public/icon-192.png frontend/public/icon-512.png
git commit -m "feat(frontend): add PWA icon generator and generated icons"
```

---

### Task 13: אינטגרציה סופית — הגשה דרך ה-backend

**Files:**
- (אין קבצים חדשים — משימת אימות בלבד, אין צורך ב-commit חדש אלא אם
  נמצאת בעיה שדורשת תיקון)

**Interfaces:**
- Consumes: `frontend/dist` (מ-`npm run build`), ואת ה-static mount
  שכבר קיים ב-`backend/app/main.py` (מ-Task 12 בתוכנית ה-backend):
  `if frontend_dist.exists(): app.mount("/", StaticFiles(...))`.

- [ ] **Step 1: build מלא ואימות שהנתיב שה-backend מצפה לו תואם**

```bash
cd frontend && npm run build
ls ../backend/../frontend/dist  # ודא שהתיקייה נוצרה
```

בדוק ב-`backend/app/main.py` את השורה המדויקת שמחשבת את הנתיב
ל-`frontend_dist` (נכתבה ב-Task 12 של תוכנית ה-backend):

```python
frontend_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
```

`__file__` הוא `backend/app/main.py`, אז `.parent.parent.parent` הוא
שורש הריפו, ולכן הנתיב הוא `<repo-root>/frontend/dist` — בדיוק איפה
ש-`npm run build` כותב. אם הנתיבים לא תואמים, תקן את אחד הצדדים
ותעד את השינוי.

- [ ] **Step 2: הרצת ה-backend עם ה-frontend הבנוי ואימות הגשה**

```bash
cd backend
source .venv/bin/activate
export STOCKER_SESSION_SECRET=dev STOCKER_LOGIN_PASSWORD=dev123 STOCKER_DB_PATH=./stocker.db
uvicorn app.main:create_app --factory --reload &
sleep 1
curl -s http://localhost:8000/ | head -5
curl -s http://localhost:8000/api/health
kill %1
```

Expected: הבקשה הראשונה (`/`) מחזירה HTML (תוכן `index.html` של
ה-frontend הבנוי, לא 404) — סימן שה-backend מגיש את ה-frontend כמו
שצריך. הבקשה השנייה מחזירה `{"status":"ok"}`.

- [ ] **Step 3: הרצת כל טסטי ה-backend כאימות רגרסיה סופי**

```bash
cd backend && .venv/bin/pytest tests/ -v
```

Expected: PASS (אין regressions מהתוספות ל-`main.py`/`portfolio.py`
מ-Task 1 — ה-static mount עצמו נכתב כבר בתוכנית ה-backend, כאן רק
מוודאים שהוא באמת מגיש קבצים אמיתיים עכשיו כשהם קיימים).

- [ ] **Step 4: דיווח**

אין קומיט נוסף אם הכול עבד כמצופה (זו משימת אימות). אם נדרש תיקון
נתיב, בצע אותו וקומיט עם הודעה מתארת את התיקון.

**הערה לבקר (controller):** לאחר משימה זו, בצע בעצמך מעבר ויזואלי מלא
בדפדפן (עם כלי הדפדפן המובנה של הסשן) על 5 המסכים — login, portfolio
(כולל buy/add/update-stop/sell), recommendations, indices — לפני
שמדווחים למשתמש שהעבודה מוכנה. זו לא משימה בתוכנית עצמה כי אין דרך
לתת לה קוד קונקרטי מראש, אבל היא חלק בלתי נפרד מסיום התוכנית (לפי
ההנחיה "For UI or frontend changes, start the dev server and use the
feature in a browser before reporting the task as complete").
