# 🌾 Smart Irrigation & Farm Advisory — Monorepo

Turns NASA POWER weather history into:
- **Daily predictions** (Temp, Humidity, Wind, Precip) via **Random Forest**
- **Irrigation needs** using **ET₀ (Hargreaves)** → **ETc (Kc)** + effective rainfall
- Plain‑English **farm advisories** (irrigation, field work, pest risk, frost, spray window)

**Stack:** FastAPI (Python) + Next.js/React (TypeScript), Tailwind CSS, React Query.

---

## 📦 Repository structure

```
.
├─ backend/                     # FastAPI API server (Python)
│  ├─ main.py
│  ├─ requirements.txt
│  ├─ start.sh / start.bat
│  ├─ models/                   # (gitignored) saved joblib models (optional)
│  ├─ data/                     # (gitignored) optional raw/processed files
│  └─ services/
│     ├─ __init__.py
│     ├─ io.py                  # NASA POWER fetch
│     ├─ features.py            # DOY sin/cos, lags, rolling stats
│     ├─ model.py               # RF training + recursive daily forecast
│     ├─ irrigation.py          # ET0 (Hargreaves), ETc, effective rainfall
│     └─ advisory.py            # human-readable recommendations
└─ frontend/                    # Next.js (React + TS)
   ├─ app/
   │  ├─ page.tsx               # UI: form + results
   │  ├─ layout.tsx             # wraps React Query Provider
   │  ├─ react-query-provider.tsx
   │  └─ api.ts                 # tiny fetch helper
   ├─ .env.local                # NEXT_PUBLIC_API_BASE=http://localhost:8000
   ├─ package.json
   └─ tailwind/postcss configs
```

> Legacy Streamlit files (`app.py`, `rain_visualize.py`, etc.) are not used in this monorepo.

---

## ✅ Prerequisites

- **Python** 3.10+ (3.11 recommended)  
- **Node.js** 18+ (LTS)  
- Internet access (backend calls NASA POWER)

---

## 🚀 Quick start (two terminals)

### Terminal A — Backend (FastAPI)

```bash
cd backend
python -m venv .venv

# Windows
.\.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Health check:  
- Open `http://localhost:8000/health` → `{"ok": true}`  
- API docs: `http://localhost:8000/docs`

Minimal POST (in Swagger “Try it out” or curl):

```json
{
  "lat": 45.65,
  "lon": -73.38,
  "target_date": "2025-07-10",
  "kc": 1.15,
  "soil_buffer_mm": 2,
  "eff_rain_factor": 0.8,
  "start": "20180101",
  "end": "20201231"
}
```

### Terminal B — Frontend (Next.js)

```bash
cd frontend
npm install

# Create .env.local if missing:
# NEXT_PUBLIC_API_BASE=http://localhost:8000

npm run dev
```

Open **http://localhost:3000** and submit the form to see predictions, irrigation, and advisories.

---

## 🔌 API overview

### `GET /health`
Returns `{ "ok": true }`.

### `POST /api/forecast-advice`
**Request**
```json
{
  "lat": 45.65,
  "lon": -73.38,
  "target_date": "YYYY-MM-DD",
  "kc": 1.15,
  "soil_buffer_mm": 2,
  "eff_rain_factor": 0.8,
  "start": "YYYYMMDD",
  "end": "YYYYMMDD"
}
```

**Response (example)**
```json
{
  "target": "2025-07-10",
  "prediction": { "Temp": 19.8, "Humidity": 72.0, "Wind": 3.2, "Precip": 0.6 },
  "irrigation_mm": 3.4,
  "et0": 4.1,
  "etc": 4.7,
  "peff": 0.5,
  "recommendations": {
    "irrigation": "...",
    "pest": "...",
    "field": "...",
    "spray": "...",
    "frost": "..."
  }
}
```

**What happens under the hood**
1. Fetch NASA POWER daily data for lat/lon & date range  
2. Feature engineering (DOY sin/cos, lags 1/7/14, rolling means)  
3. Train 4 Random Forests (Temp, Humidity, Wind, Precip)  
4. Recursive day‑by‑day forecast to `target_date`  
5. Compute ET₀ → ETc → net irrigation; generate advisory text

> First call to a new location can be slower due to training. You can add joblib caching in `services/model.py`.

---

## ⚙️ Environment variables

`frontend/.env.local`
```
NEXT_PUBLIC_API_BASE=http://localhost:8000
```
Change this for deployments (e.g., your hosted FastAPI URL).

---

## 🧪 Testing tips

- Backend alone:
  - `curl http://localhost:8000/health`
  - `http://localhost:8000/docs` and run the POST with a near `target_date` and short `start/end` for faster responses.
- Frontend error “No QueryClient set”: ensure `react-query-provider.tsx` is used in `app/layout.tsx`.

---

## 🛠 Troubleshooting

- **422 Unprocessable Entity** → wrong JSON shape or date format; use `"YYYY-MM-DD"`.
- **Slow responses** → reduce history window (`start`, `end`) during dev; add model caching later.
- **CORS** → already allowed for `localhost:3000`. If you change ports/hosts, update the CORS origins in `backend/main.py`.
- **Port in use** → change backend port (`--port 8010`) and update `NEXT_PUBLIC_API_BASE`.

---

## 🧰 One‑command dev (optional)

Add this at repo root as `package.json`:

```json
{
  "name": "farm-monorepo",
  "private": true,
  "scripts": {
    "dev": "concurrently -n BACKEND,FRONTEND -c blue,green \"cd backend && uvicorn main:app --reload --port 8000\" \"cd frontend && npm run dev\""
  },
  "devDependencies": { "concurrently": "^8.2.0" }
}
```

Then:

```bash
npm run dev
```

> If you use a Python venv, activate it in the BACKEND command or start the backend separately.

