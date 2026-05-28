"""
routers/report.py
──────────────────
POST /api/report  →  returns complete HTML report (text/html)
"""
from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Optional
from models import SolveRequest

router = APIRouter()


class OptResultPayload(BaseModel):
    method: str
    result: dict


class ReportRequest(BaseModel):
    project_name:  str = "Space Truss Analysis"
    engineer:      str = "D Mandal"
    solve_request: SolveRequest
    solve_result:  dict                     # SolveResponse as dict
    opt_results:   list[OptResultPayload] = []
    yield_stress:  float = 250e6


@router.post("/report", response_class=HTMLResponse)
async def generate_report(req: ReportRequest):
    """
    Generate and return a full engineering report as a self-contained HTML page.
    The page includes a Print-to-PDF button so the user can save it as a PDF.
    """
    from report_generator import generate_report as _gen

    html = _gen(
        project_name = req.project_name,
        engineer     = req.engineer,
        nodes        = [n.model_dump() for n in req.solve_request.nodes],
        members      = [m.model_dump() for m in req.solve_request.members],
        loads        = [l.model_dump() for l in req.solve_request.loads],
        combos       = [c.model_dump() for c in req.solve_request.combos],
        solve_result = req.solve_result,
        opt_results  = [o.model_dump() for o in req.opt_results],
        fy           = req.yield_stress,
    )
    return HTMLResponse(content=html, status_code=200)
