"""
main.py — FastAPI entry point for the Space Truss Analysis API.

Run:
    uvicorn main:app --reload --port 8000

The React frontend (after `npm run build`) is served as a static SPA
from the /frontend/dist directory when available.
"""
import os
import sys

# Make backend/ the module root so `from models import …` works everywhere
sys.path.insert(0, os.path.dirname(__file__))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from routers import solver, optimizer, catalog, report

app = FastAPI(
    title="Space Truss Analysis API",
    description=(
        "3D Space Truss Analysis (Direct Stiffness Method) + IS 800:2007 "
        "GA-MINLP Optimisation. Developed by D Mandal, KITS Ramtek."
    ),
    version="2.0.0",
)

# Allow the React dev server (localhost:5173) during development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(solver.router,    prefix="/api", tags=["Solver"])
app.include_router(optimizer.router, prefix="/api", tags=["Optimizer"])
app.include_router(catalog.router,   prefix="/api", tags=["Catalog"])
app.include_router(report.router,    prefix="/api", tags=["Report"])


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "2.0.0"}


# Serve the built React SPA in production
_dist = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
if os.path.isdir(_dist):
    app.mount("/", StaticFiles(directory=_dist, html=True), name="spa")
