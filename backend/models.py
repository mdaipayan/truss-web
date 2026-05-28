"""
models.py — Pydantic schemas for the Space Truss API.
All request/response types used by the FastAPI routers.
"""
from pydantic import BaseModel, Field
from typing import Optional


# ─────────────────────────────────────────────────────────────────
#  INPUT MODELS
# ─────────────────────────────────────────────────────────────────

class NodeIn(BaseModel):
    id: int
    x: float
    y: float
    z: float
    rx: bool = False
    ry: bool = False
    rz: bool = False


class MemberIn(BaseModel):
    id: int
    node_i: int
    node_j: int
    area: float = Field(default=0.005, gt=0, description="Cross-section area (m²)")
    E: float    = Field(default=2e11,  gt=0, description="Young's modulus (Pa)")


class LoadIn(BaseModel):
    node_id:   int
    fx:        float = 0.0
    fy:        float = 0.0
    fz:        float = 0.0
    load_case: str   = "DL"


class ComboIn(BaseModel):
    name:    str
    factors: dict[str, float]   # e.g. {"DL": 1.5, "WL": 1.0}


class ShapeBound(BaseModel):
    dx_min: float = 0.0
    dx_max: float = 0.0
    dy_min: float = 0.0
    dy_max: float = 0.0
    dz_min: float = 0.0
    dz_max: float = 0.0


class SolveRequest(BaseModel):
    nodes:         list[NodeIn]
    members:       list[MemberIn]
    loads:         list[LoadIn]
    combos:        list[ComboIn]
    analysis_type: str = "linear"   # "linear" | "nonlinear"
    load_steps:    int = 10


# ─────────────────────────────────────────────────────────────────
#  RESULT MODELS
# ─────────────────────────────────────────────────────────────────

class NodeResult(BaseModel):
    id:     int
    ux:     float
    uy:     float
    uz:     float
    rx_val: float
    ry_val: float
    rz_val: float


class MemberResult(BaseModel):
    id:         int
    node_i:     int
    node_j:     int
    force_n:    float       # Newtons
    force_kn:   float       # kN (convenience)
    nature:     str         # "Tension" | "Compression" | "Zero"
    stress_mpa: float


class ComboResult(BaseModel):
    combo_name:         str
    nodes:              list[NodeResult]
    members:            list[MemberResult]
    max_displacement_m: float


class SolveResponse(BaseModel):
    combos: list[ComboResult]


# ─────────────────────────────────────────────────────────────────
#  CATALOG
# ─────────────────────────────────────────────────────────────────

class CatalogEntry(BaseModel):
    index:        int
    designation:  str
    area_cm2:     float
    r_min_cm:     float
    weight_kg_m:  float


# ─────────────────────────────────────────────────────────────────
#  OPTIMIZER REQUESTS
# ─────────────────────────────────────────────────────────────────

class DEOptRequest(BaseModel):
    solve_request:  SolveRequest
    member_groups:  list[list[int]]
    shape_bounds:   dict[int, ShapeBound] = {}
    yield_stress:   float = 250e6
    max_deflection: float = 0.05
    pop_size:       int   = 20
    max_gen:        int   = 100


class GAMINLPRequest(BaseModel):
    solve_request:  SolveRequest
    member_groups:  list[list[int]]
    shape_bounds:   dict[int, ShapeBound] = {}
    yield_stress:   float = 250e6
    max_deflection: float = 0.05
    ga_pop:         int   = 50
    ga_gen:         int   = 80
    minlp_pop:      int   = 15
    minlp_gen:      int   = 80
    n_elite:        int   = 5


# ─────────────────────────────────────────────────────────────────
#  OPTIMIZER RESULTS
# ─────────────────────────────────────────────────────────────────

class SectionAssignment(BaseModel):
    member_id: int
    section:   str
    active:    bool = True


class NodeShift(BaseModel):
    node_id: int
    dx:      float
    dy:      float
    dz:      float


class OptResult(BaseModel):
    sections:        list[SectionAssignment]
    node_shifts:     list[NodeShift]
    topology:        dict[int, bool]
    weight_kg:       float
    orig_weight_kg:  float
    is_valid:        bool
    hist_p1:         list[float]
    hist_p2:         list[float]


# ─────────────────────────────────────────────────────────────────
#  WEBSOCKET MESSAGES  (server → client)
# ─────────────────────────────────────────────────────────────────

class WSProgress(BaseModel):
    type:       str     # "phase" | "progress" | "result" | "error"
    phase:      Optional[int]   = None
    message:    Optional[str]   = None
    generation: Optional[int]   = None
    iteration:  Optional[int]   = None
    best:       Optional[float] = None
    result:     Optional[OptResult] = None
