"""routers/solver.py — POST /api/solve"""
from fastapi import APIRouter, HTTPException
from models import SolveRequest, SolveResponse
from services.truss_service import build_and_solve

router = APIRouter()


@router.post("/solve", response_model=SolveResponse)
async def solve(req: SolveRequest):
    """
    Solve the truss for all defined load combinations.
    Returns nodal displacements, reactions, and member forces per combo.
    """
    try:
        combos = build_and_solve(req)
        return SolveResponse(combos=combos)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Solver error: {e}")
