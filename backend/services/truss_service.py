"""
services/truss_service.py
─────────────────────────
Bridge between the FastAPI Pydantic models and the existing
core_solver.py objects (TrussSystem, Node, Member).

All solver calls go through build_and_solve() which returns
a list of ComboResult objects (one per load combination).
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import numpy as np
from core_solver import TrussSystem, Node, Member
from models import (
    SolveRequest, ComboResult, NodeResult, MemberResult,
    DEOptRequest, GAMINLPRequest, OptResult,
    SectionAssignment, NodeShift,
)
from ai_optimizer    import TrussOptimizer
from is_catalog      import get_isa_catalog


# ─────────────────────────────────────────────────────────────────
#  CORE BUILD HELPER
# ─────────────────────────────────────────────────────────────────

def _build_ts(req: SolveRequest, factors: dict[str, float]) -> TrussSystem:
    """
    Construct a TrussSystem from the API request + one combo's factors.
    factors maps load_case name → scalar (e.g. {"DL": 1.5, "WL": 1.0}).
    """
    ts       = TrussSystem()
    node_map = {}

    for nd in req.nodes:
        n = Node(nd.id, nd.x, nd.y, nd.z, nd.rx, nd.ry, nd.rz)
        ts.nodes.append(n)
        node_map[nd.id] = n

    for mb in req.members:
        if mb.node_i not in node_map or mb.node_j not in node_map:
            raise ValueError(
                f"Member {mb.id} references unknown node {mb.node_i} or {mb.node_j}"
            )
        ts.members.append(
            Member(mb.id, node_map[mb.node_i], node_map[mb.node_j], mb.E, mb.area)
        )

    for ld in req.loads:
        if ld.node_id not in node_map:
            raise ValueError(f"Load references unknown node {ld.node_id}")
        factor = factors.get(ld.load_case, 1.0)
        target = node_map[ld.node_id]
        ts.loads[target.dofs[0]] = ts.loads.get(target.dofs[0], 0.0) + ld.fx * factor
        ts.loads[target.dofs[1]] = ts.loads.get(target.dofs[1], 0.0) + ld.fy * factor
        ts.loads[target.dofs[2]] = ts.loads.get(target.dofs[2], 0.0) + ld.fz * factor

    return ts


def _extract_results(ts: TrussSystem, combo_name: str) -> ComboResult:
    """Convert a solved TrussSystem into the API result model."""
    node_results = []
    for n in ts.nodes:
        ux = float(ts.U_global[n.dofs[0]]) if ts.U_global is not None else 0.0
        uy = float(ts.U_global[n.dofs[1]]) if ts.U_global is not None else 0.0
        uz = float(ts.U_global[n.dofs[2]]) if ts.U_global is not None else 0.0
        node_results.append(NodeResult(
            id=n.id, ux=ux, uy=uy, uz=uz,
            rx_val=float(n.rx_val),
            ry_val=float(n.ry_val),
            rz_val=float(n.rz_val),
        ))

    member_results = []
    max_disp = float(np.max(np.abs(ts.U_global))) if ts.U_global is not None else 0.0

    for m in ts.members:
        f    = float(m.calculate_force())
        a    = max(float(m.A), 1e-12)
        sig  = f / a / 1e6  # MPa
        nature = (
            "Tension"     if f >  1.0 else
            "Compression" if f < -1.0 else
            "Zero"
        )
        member_results.append(MemberResult(
            id=m.id, node_i=m.node_i.id, node_j=m.node_j.id,
            force_n=f, force_kn=round(f / 1000, 4),
            nature=nature, stress_mpa=round(sig, 4),
        ))

    return ComboResult(
        combo_name=combo_name,
        nodes=node_results,
        members=member_results,
        max_displacement_m=round(max_disp, 8),
    )


# ─────────────────────────────────────────────────────────────────
#  PUBLIC API
# ─────────────────────────────────────────────────────────────────

def build_and_solve(req: SolveRequest) -> list[ComboResult]:
    """Solve all load combinations and return one ComboResult each."""
    results = []
    for combo in req.combos:
        ts = _build_ts(req, combo.factors)
        if not ts.nodes or not ts.members:
            raise ValueError("Model must have at least one node and one member.")
        if req.analysis_type == "nonlinear":
            ts.solve_nonlinear(load_steps=req.load_steps)
        else:
            ts.solve()
        results.append(_extract_results(ts, combo.name))
    return results


def run_de_optimizer(req: DEOptRequest) -> OptResult:
    """
    Run the existing DE optimizer (TrussOptimizer) and return OptResult.
    Blocking call — run in a thread pool from the router.
    """
    # Build one TrussSystem per combo
    combos_ts = []
    for combo in req.solve_request.combos:
        ts = _build_ts(req.solve_request, combo.factors)
        if req.solve_request.analysis_type == "nonlinear":
            ts.solve_nonlinear(load_steps=req.solve_request.load_steps)
        else:
            ts.solve()
        combos_ts.append(ts)

    orig_weight = sum(m.A * m.L * 7850 for m in combos_ts[0].members)

    # Shape bounds → list format expected by TrussOptimizer
    shape_bounds_dict = {}
    for nid, sb in req.shape_bounds.items():
        shape_bounds_dict[int(nid)] = [
            sb.dx_min, sb.dx_max,
            sb.dy_min, sb.dy_max,
            sb.dz_min, sb.dz_max,
        ]

    optimizer = TrussOptimizer(
        base_combos    = combos_ts,
        member_groups  = req.member_groups,
        shape_bounds   = shape_bounds_dict,
        yield_stress   = req.yield_stress,
        max_deflection = req.max_deflection,
    )
    final_sections, final_shifts, final_weight, is_valid, history = optimizer.optimize(
        pop_size=req.pop_size, max_gen=req.max_gen
    )

    # Build catalog
    cat = get_isa_catalog()

    sections = [
        SectionAssignment(member_id=m_id, section=sec, active=True)
        for m_id, sec in final_sections.items()
    ]
    node_shifts = [
        NodeShift(node_id=nid, dx=s["dx"], dy=s["dy"], dz=s["dz"])
        for nid, s in final_shifts.items()
    ]

    return OptResult(
        sections=sections,
        node_shifts=node_shifts,
        topology={m.id: True for m in combos_ts[0].members},
        weight_kg=round(final_weight, 3),
        orig_weight_kg=round(orig_weight, 3),
        is_valid=is_valid,
        hist_p1=[],
        hist_p2=[w for w in history if w < 1e6],
    )


def run_ga_minlp_optimizer(
    req: GAMINLPRequest,
    progress_cb=None,
) -> OptResult:
    """
    Run the GA-MINLP optimizer with optional progress callback.
    progress_cb(msg: dict) is called from the optimizer thread.
    """
    try:
        from ga_minlp_optimizer import GAMINLPOptimizer
    except ImportError:
        raise RuntimeError(
            "ga_minlp_optimizer.py not found in the backend directory."
        )

    combos_ts = []
    for combo in req.solve_request.combos:
        ts = _build_ts(req.solve_request, combo.factors)
        if req.solve_request.analysis_type == "nonlinear":
            ts.solve_nonlinear(load_steps=req.solve_request.load_steps)
        else:
            ts.solve()
        combos_ts.append(ts)

    orig_weight = sum(m.A * m.L * 7850 for m in combos_ts[0].members)

    shape_bounds_dict = {}
    for nid, sb in req.shape_bounds.items():
        shape_bounds_dict[int(nid)] = [
            sb.dx_min, sb.dx_max,
            sb.dy_min, sb.dy_max,
            sb.dz_min, sb.dz_max,
        ]

    optimizer = GAMINLPOptimizer(
        base_combos    = combos_ts,
        member_groups  = req.member_groups,
        shape_bounds   = shape_bounds_dict,
        yield_stress   = req.yield_stress,
        max_deflection = req.max_deflection,
        n_elite        = req.n_elite,
    )

    # Monkey-patch the GA toolbox to emit progress
    if progress_cb:
        _orig_p1 = optimizer.run_phase1
        def _p1_with_cb(pop_size, n_gen):
            if progress_cb:
                progress_cb({"type": "phase", "phase": 1,
                             "message": f"GA running ({n_gen} generations)…"})
            result = _orig_p1(pop_size=pop_size, n_gen=n_gen)
            for i, v in enumerate(optimizer.hist_p1):
                progress_cb({"type": "progress", "phase": 1,
                             "generation": i + 1, "best": v})
            return result
        optimizer.run_phase1 = _p1_with_cb

        _orig_p2 = optimizer.run_phase2
        _p2_rank = [0]
        def _p2_with_cb(topo, shape, pop_size, max_gen):
            _p2_rank[0] += 1
            if progress_cb:
                progress_cb({"type": "phase", "phase": 2,
                             "message": f"MINLP sizing candidate {_p2_rank[0]}/{req.n_elite}…"})
            result = _orig_p2(topo, shape, pop_size=pop_size, max_gen=max_gen)
            for i, v in enumerate(optimizer.hist_p2[-max_gen:]):
                progress_cb({"type": "progress", "phase": 2,
                             "iteration": i + 1, "best": v})
            return result
        optimizer.run_phase2 = _p2_with_cb

    (
        final_sections,
        topology_dict,
        final_shifts,
        final_weight,
        is_valid,
        hist_p1,
        hist_p2,
    ) = optimizer.optimize(
        ga_pop=req.ga_pop, ga_gen=req.ga_gen,
        minlp_pop=req.minlp_pop, minlp_gen=req.minlp_gen,
    )

    sections = [
        SectionAssignment(member_id=m_id, section=sec, active=topology_dict.get(m_id, True))
        for m_id, sec in final_sections.items()
    ]
    node_shifts = [
        NodeShift(node_id=nid, dx=s["dx"], dy=s["dy"], dz=s["dz"])
        for nid, s in final_shifts.items()
    ]

    return OptResult(
        sections=sections,
        node_shifts=node_shifts,
        topology={int(k): bool(v) for k, v in topology_dict.items()},
        weight_kg=round(final_weight, 3),
        orig_weight_kg=round(orig_weight, 3),
        is_valid=is_valid,
        hist_p1=[w for w in hist_p1 if w < 1e11],
        hist_p2=[w for w in hist_p2 if w < 1e6],
    )
