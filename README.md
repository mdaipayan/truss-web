# Space Truss Suite — Web Application

3D Space Truss Analysis (DSM) + IS 800:2007 GA-MINLP Optimisation.  
Developed by **D Mandal**, Assistant Professor, KITS Ramtek, Nagpur.

---

## Stack

| Layer    | Technology                                |
|----------|-------------------------------------------|
| Backend  | FastAPI · uvicorn · scipy · DEAP · NumPy  |
| Frontend | React 18 · Vite · Plotly.js · Zustand     |
| Protocol | REST (solver / DE) + WebSocket (GA-MINLP) |

---

## Quick Start

### 1. Copy existing solver files into the backend

```
cp core_solver.py        truss-web/backend/
cp ai_optimizer.py       truss-web/backend/
cp ga_minlp_optimizer.py truss-web/backend/
cp is_catalog.py         truss-web/backend/
cp report_gen.py         truss-web/backend/
```

### 2. Backend

```bash
cd truss-web/backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

API docs: http://localhost:8000/docs

### 3. Frontend (development)

```bash
cd truss-web/frontend
npm install
npm run dev
```

Open http://localhost:5173

The Vite dev server proxies `/api/*` → `http://localhost:8000`
(including WebSocket upgrades) so no CORS issues.

### 4. Production build

```bash
cd truss-web/frontend && npm run build
# Built SPA is placed at frontend/dist/
# FastAPI serves it automatically from /
cd ../backend && uvicorn main:app --port 8000
```

---

## API Endpoints

| Method    | Path                        | Description                         |
|-----------|-----------------------------|-------------------------------------|
| `POST`    | `/api/solve`                | Linear / non-linear DSM solve       |
| `POST`    | `/api/optimize/de`          | DE sizing + shape optimiser         |
| `WS`      | `/api/optimize/ga-minlp`    | GA-MINLP with live progress stream  |
| `GET`     | `/api/catalog`              | Full ISA section catalog (SP 6(1))  |
| `GET`     | `/api/benchmarks`           | List built-in benchmark models      |
| `GET`     | `/api/benchmarks/{name}`    | Get a benchmark as a SolveRequest   |
| `GET`     | `/api/health`               | Health check                        |

---

## Project Layout

```
truss-web/
├── backend/
│   ├── main.py                 ← FastAPI entry point
│   ├── models.py               ← Pydantic request/response schemas
│   ├── benchmarks.py           ← Tetrahedron, 25-bar, 72-bar presets
│   ├── routers/
│   │   ├── solver.py           ← POST /api/solve
│   │   ├── optimizer.py        ← DE + GA-MINLP WebSocket
│   │   └── catalog.py          ← catalog + benchmarks endpoints
│   ├── services/
│   │   └── truss_service.py    ← bridge: Pydantic ↔ TrussSystem
│   ├── core_solver.py          ← (copy from original)
│   ├── ai_optimizer.py         ← (copy from original)
│   ├── ga_minlp_optimizer.py   ← (new GA-MINLP file)
│   ├── is_catalog.py           ← (copy from original)
│   └── requirements.txt
└── frontend/
    ├── src/
    │   ├── App.jsx             ← root layout
    │   ├── store/index.js      ← Zustand global state
    │   ├── api/client.js       ← fetch + WebSocket wrappers
    │   └── components/
    │       ├── InputPanel.jsx  ← editable node/member/load tables
    │       ├── Viewer3D.jsx    ← Plotly.js 3D canvas
    │       ├── ResultsPanel.jsx← forces, displacements, sections
    │       └── OptimiserPanel.jsx ← DE/GA-MINLP controls + live charts
    ├── index.html
    ├── vite.config.js
    ├── tailwind.config.js
    └── package.json
```
