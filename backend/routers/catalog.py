"""
routers/catalog.py
──────────────────
GET  /api/catalog            — full ISA section catalog
GET  /api/benchmarks         — list of named benchmark models
GET  /api/benchmarks/{name}  — return a specific benchmark as a SolveRequest
"""
from fastapi import APIRouter, HTTPException
from models import CatalogEntry, SolveRequest
from is_catalog import get_isa_catalog
from benchmarks import BENCHMARKS

router = APIRouter()


@router.get("/catalog", response_model=list[CatalogEntry])
async def get_catalog():
    """Return the full SP 6(1) ISA section catalog."""
    df = get_isa_catalog()
    return [
        CatalogEntry(
            index=int(i),
            designation=str(row["Designation"]),
            area_cm2=float(row["Area_cm2"]),
            r_min_cm=float(row["r_min_cm"]),
            weight_kg_m=float(row["Weight_kg_m"]),
        )
        for i, row in df.iterrows()
    ]


@router.get("/benchmarks")
async def list_benchmarks():
    """Return names and short descriptions of all built-in benchmarks."""
    return [
        {"name": k, "description": v["description"]}
        for k, v in BENCHMARKS.items()
    ]


@router.get("/benchmarks/{name}")
async def get_benchmark(name: str):
    """Return a complete SolveRequest payload for a named benchmark."""
    if name not in BENCHMARKS:
        raise HTTPException(status_code=404, detail=f"Benchmark '{name}' not found.")
    return BENCHMARKS[name]["payload"]
