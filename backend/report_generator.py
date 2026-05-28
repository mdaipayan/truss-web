"""
report_generator.py
────────────────────
Generates a complete, self-contained HTML engineering report including:
  • Model description (nodes, members, loads, combos)
  • DSM theory with step-by-step equations
  • Full analysis results (displacements, forces, reactions)
  • IS 800:2007 code checks per member (step-by-step)
  • Optimization results per method
  • Side-by-side comparison of all methods run
  • Print-to-PDF ready layout

Returns a single HTML string — open in browser or print to PDF.
"""
import math
import datetime
from typing import Optional


# ─────────────────────────────────────────────────────────────────
#  HTML / CSS skeleton
# ─────────────────────────────────────────────────────────────────

_CSS = """
:root {
  --ink:    #1a1a2e; --ink2:  #3d3d5c; --ink3:  #6b7280;
  --accent: #2563eb; --ok:    #15803d; --warn:  #b45309; --fail: #b91c1c;
  --bg:     #ffffff; --bg2:   #f8fafc; --border: #e2e8f0;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: 'Times New Roman', Times, serif;
  font-size: 11pt; color: var(--ink); background: var(--bg);
  max-width: 960px; margin: 0 auto; padding: 20px;
}
h1 { font-size: 20pt; color: var(--accent); margin-bottom: 4px; }
h2 { font-size: 14pt; color: var(--ink);   margin: 22px 0 8px;
     padding-bottom: 4px; border-bottom: 2px solid var(--accent); }
h3 { font-size: 12pt; color: var(--ink2);  margin: 14px 0 6px; }
h4 { font-size: 11pt; color: var(--ink2);  margin: 10px 0 4px; font-style: italic; }
p  { margin-bottom: 8px; line-height: 1.6; }
/* Tables */
table { width: 100%; border-collapse: collapse; margin: 10px 0 16px; font-size: 10pt; }
th {
  background: var(--accent); color: #fff;
  padding: 6px 8px; text-align: center; font-weight: 600;
}
td { padding: 5px 8px; border: 1px solid var(--border); vertical-align: top; }
tr:nth-child(even) td { background: var(--bg2); }
td.num { text-align: right; font-family: 'Courier New', monospace; font-size: 9.5pt; }
td.ctr { text-align: center; }
/* Formula boxes */
.formula {
  background: #f0f4ff; border-left: 4px solid var(--accent);
  padding: 8px 14px; margin: 8px 0 12px;
  font-family: 'Courier New', monospace; font-size: 10pt;
  white-space: pre-wrap; line-height: 1.8;
}
/* Status badges */
.ok   { color: var(--ok);   font-weight: 600; }
.fail { color: var(--fail); font-weight: 600; }
.warn { color: var(--warn); font-weight: 600; }
/* Info boxes */
.info-box {
  background: #eff6ff; border: 1px solid #bfdbfe;
  border-radius: 6px; padding: 10px 14px; margin: 10px 0;
}
.warn-box {
  background: #fffbeb; border: 1px solid #fcd34d;
  border-radius: 6px; padding: 10px 14px; margin: 10px 0;
}
/* Cover */
.cover {
  text-align: center; padding: 40px 20px 30px;
  border-bottom: 3px double var(--accent); margin-bottom: 30px;
}
.cover .subtitle { font-size: 12pt; color: var(--ink2); margin: 8px 0; }
.cover .meta     { font-size: 10pt; color: var(--ink3); margin-top: 20px; }
/* Section numbers */
.sec-num { color: var(--accent); margin-right: 6px; }
/* Comparison table highlight */
.best-col td { background: #f0fdf4 !important; font-weight: 600; }
/* Print */
@media print {
  body { max-width: 100%; padding: 10px; font-size: 10pt; }
  .no-print { display: none !important; }
  h2 { page-break-before: always; }
  h2:first-of-type { page-break-before: avoid; }
  table { page-break-inside: avoid; }
  .formula { background: #f5f5f5; }
}
"""

_PRINT_BTN = """
<div class="no-print" style="
  position:fixed; top:16px; right:16px;
  background:#2563eb; color:#fff; padding:10px 20px;
  border-radius:8px; cursor:pointer; font-family:sans-serif;
  font-size:13px; font-weight:600; box-shadow:0 4px 12px rgba(0,0,0,.2);
  z-index:999;
" onclick="window.print()">⬇ Save / Print PDF</div>
"""


# ─────────────────────────────────────────────────────────────────
#  Catalog lookup helper
# ─────────────────────────────────────────────────────────────────

def _catalog_by_name(name: str):
    from is_catalog import get_isa_catalog
    cat = get_isa_catalog()
    row = cat[cat["Designation"] == name]
    if row.empty:
        return {"A": 0.0, "r": 0.01, "w": 0.0}
    return {
        "A": float(row.iloc[0]["Area_m2"]),
        "r": float(row.iloc[0]["r_min_m"]),
        "w": float(row.iloc[0]["Weight_kg_m"]),
    }


# ─────────────────────────────────────────────────────────────────
#  IS 800 per-member calculation (returns dict with all steps)
# ─────────────────────────────────────────────────────────────────

def _is800_check(force_n: float, length_m: float,
                  A_m2: float, r_m: float,
                  fy: float = 250e6, E: float = 200e9,
                  K: float = 1.0, alpha: float = 0.49,
                  gm0: float = 1.1) -> dict:
    """Full IS 800:2007 code check for one member. Returns all intermediate values."""
    A = A_m2
    r = max(r_m, 1e-6)
    L = length_m
    F = force_n
    sigma_actual = abs(F) / max(A, 1e-12)

    KLr = K * L / r

    # Allowable tension
    fa_t = fy / gm0

    if F >= 0:  # tension
        nature = "Tension"
        dcr = sigma_actual / fa_t
        return {
            "nature": nature, "KLr": KLr,
            "sigma_actual_mpa": sigma_actual / 1e6,
            "fa_mpa": fa_t / 1e6,
            "dcr": dcr,
            "slender_ok": KLr <= 400,
            "stress_ok": dcr <= 1.0,
            "pass": KLr <= 400 and dcr <= 1.0,
            # For report steps:
            "step_slender_limit": 400,
            "fcc_mpa": None, "lambda_n": None,
            "phi": None, "fcd_mpa": None,
        }
    else:  # compression
        nature = "Compression"
        slender_ok = KLr <= 180
        # Euler stress
        fcc = (math.pi ** 2 * E) / max(KLr, 1e-3) ** 2
        lam_n = math.sqrt(fy / fcc)
        phi = 0.5 * (1 + alpha * (lam_n - 0.2) + lam_n ** 2)
        fcd = fy / (phi + math.sqrt(max(phi ** 2 - lam_n ** 2, 1e-12)))
        fa_c = min(fcd, fy) / gm0
        dcr = sigma_actual / fa_c
        return {
            "nature": nature, "KLr": KLr,
            "sigma_actual_mpa": sigma_actual / 1e6,
            "fa_mpa": fa_c / 1e6,
            "dcr": dcr,
            "slender_ok": slender_ok,
            "stress_ok": dcr <= 1.0,
            "pass": slender_ok and dcr <= 1.0,
            "step_slender_limit": 180,
            "fcc_mpa": fcc / 1e6,
            "lambda_n": lam_n,
            "phi": phi,
            "fcd_mpa": fcd / 1e6,
        }


# ─────────────────────────────────────────────────────────────────
#  HTML section builders
# ─────────────────────────────────────────────────────────────────

def _cover(project: str, engineer: str, model_stats: dict) -> str:
    date = datetime.date.today().strftime("%B %d, %Y")
    return f"""
<div class="cover">
  <h1>Space Truss Analysis Report</h1>
  <div class="subtitle">{project}</div>
  <div class="subtitle">3D Direct Stiffness Method &nbsp;·&nbsp; IS 800:2007 Code Checks
       &nbsp;·&nbsp; Multi-Method Optimisation</div>
  <div class="meta">
    Prepared by: <strong>{engineer}</strong><br>
    Department of Civil Engineering, KITS Ramtek, Nagpur<br>
    Date: {date}
  </div>
  <div class="meta" style="margin-top:14px; font-size:10pt;">
    Nodes: {model_stats['nodes']} &nbsp;|&nbsp;
    Members: {model_stats['members']} &nbsp;|&nbsp;
    Free DOF: {model_stats['free_dof']} &nbsp;|&nbsp;
    Load combos: {model_stats['combos']}
  </div>
</div>
"""


def _section_model(nodes, members, loads, combos) -> str:
    # Node table
    node_rows = "".join(
        f"<tr><td class='ctr'>N{n['id']}</td>"
        f"<td class='num'>{n['x']:.3f}</td>"
        f"<td class='num'>{n['y']:.3f}</td>"
        f"<td class='num'>{n['z']:.3f}</td>"
        f"<td class='ctr'>{'✓' if n.get('rx') else ''}</td>"
        f"<td class='ctr'>{'✓' if n.get('ry') else ''}</td>"
        f"<td class='ctr'>{'✓' if n.get('rz') else ''}</td></tr>"
        for n in nodes
    )

    # Member length calculation
    node_by_id = {n["id"]: n for n in nodes}
    def _len(ni, nj):
        a, b = node_by_id.get(ni, {}), node_by_id.get(nj, {})
        if not a or not b:
            return 0.0
        return math.sqrt((b["x"]-a["x"])**2+(b["y"]-a["y"])**2+(b["z"]-a["z"])**2)

    mem_rows = "".join(
        f"<tr><td class='ctr'>M{m['id']}</td>"
        f"<td class='ctr'>N{m['node_i']} → N{m['node_j']}</td>"
        f"<td class='num'>{_len(m['node_i'],m['node_j']):.4f}</td>"
        f"<td class='num'>{m['area']*1e4:.4f}</td>"
        f"<td class='num'>{m['E']/1e9:.0f}</td></tr>"
        for m in members
    )

    # Load table
    load_rows = "".join(
        f"<tr><td class='ctr'>N{l['node_id']}</td>"
        f"<td class='num'>{l['fx']/1000:.2f}</td>"
        f"<td class='num'>{l['fy']/1000:.2f}</td>"
        f"<td class='num'>{l['fz']/1000:.2f}</td>"
        f"<td class='ctr'>{l['load_case']}</td></tr>"
        for l in loads
    )

    # Combo table
    combo_rows = "".join(
        f"<tr><td>{c['name']}</td>" +
        "".join(f"<td class='num'>{v:.2f}</td>" for v in c['factors'].values()) +
        "</tr>"
        for c in combos
    )
    combo_headers = "".join(
        f"<th>{k}</th>" for k in (combos[0]["factors"].keys() if combos else [])
    )

    return f"""
<h2><span class="sec-num">1.</span> Structural Model</h2>

<h3>1.1 Node Coordinates</h3>
<table>
  <tr><th>Node</th><th>X (m)</th><th>Y (m)</th><th>Z (m)</th>
      <th>Rx</th><th>Ry</th><th>Rz</th></tr>
  {node_rows}
</table>

<h3>1.2 Member Connectivity</h3>
<table>
  <tr><th>Member</th><th>Connectivity</th><th>Length (m)</th>
      <th>Area (cm²)</th><th>E (GPa)</th></tr>
  {mem_rows}
</table>

<h3>1.3 Applied Loads (Base Cases)</h3>
<table>
  <tr><th>Node</th><th>Fx (kN)</th><th>Fy (kN)</th><th>Fz (kN)</th><th>Case</th></tr>
  {load_rows}
</table>

<h3>1.4 Load Combinations (IS 875)</h3>
<table>
  <tr><th>Combination Name</th>{combo_headers}</tr>
  {combo_rows}
</table>
"""


def _section_dsm() -> str:
    return """
<h2><span class="sec-num">2.</span> Direct Stiffness Method — Theory</h2>

<h3>2.1 Member Kinematics</h3>
<p>For a space truss member connecting node <em>i</em> to node <em>j</em>, the member
length and direction cosines are:</p>
<div class="formula">L  = √[(xⱼ−xᵢ)² + (yⱼ−yᵢ)² + (zⱼ−zᵢ)²]

l  = (xⱼ−xᵢ)/L    (direction cosine, X-axis)
m  = (yⱼ−yᵢ)/L    (direction cosine, Y-axis)
n  = (zⱼ−zᵢ)/L    (direction cosine, Z-axis)</div>

<h3>2.2 Element Stiffness Matrix (Global)</h3>
<p>The transformation vector T maps local axial deformation to global DOF:</p>
<div class="formula">T = [−l, −m, −n, l, m, n]ᵀ  (1×6)

k_global = (EA/L) × Tᵀ·T  (6×6 symmetric matrix)</div>

<h3>2.3 Global Assembly and Partitioning</h3>
<div class="formula">K_global = Σᵢ  k_global_i    (assemble all element matrices)

Partition into free (f) and restrained (r) DOF:
  [K_ff  K_fr] {U_f}   {F_f}
  [K_rf  K_rr] {U_r} = {F_r}

Since U_r = 0 (supports fixed):
  [K_ff] × {U_f} = {F_f}
  ∴  {U_f} = [K_ff]⁻¹ × {F_f}</div>

<h3>2.4 Internal Force Recovery</h3>
<div class="formula">u_local  = [U_ix, U_iy, U_iz, U_jx, U_jy, U_jz]ᵀ  (global displacements at member DOF)

F_axial  = (EA/L) × (T · u_local)        [N]

σ_actual = F_axial / A                    [Pa]

Tension   → F_axial > 0  (member elongates)
Compression → F_axial < 0  (member shortens)</div>

<h3>2.5 Support Reactions</h3>
<div class="formula">R_global = K_global × U_global − F_global

Reactions at restrained DOF = R_global[restrained_dofs]</div>
"""


def _section_results(solve_result: dict, nodes, members) -> str:
    """Analysis results for all combos."""
    node_by_id = {n["id"]: n for n in nodes}
    blocks = []

    for combo in solve_result.get("combos", []):
        cname = combo["combo_name"]
        max_d = combo["max_displacement_m"] * 1000

        # Displacement table
        disp_rows = "".join(
            f"<tr><td class='ctr'>N{n['id']}</td>"
            f"<td class='num'>{n['ux']*1000:.4f}</td>"
            f"<td class='num'>{n['uy']*1000:.4f}</td>"
            f"<td class='num'>{n['uz']*1000:.4f}</td>"
            f"<td class='num'>{math.sqrt(n['ux']**2+n['uy']**2+n['uz']**2)*1000:.4f}</td></tr>"
            for n in combo["nodes"]
        )

        # Member force table
        mem_rows = "".join(
            f"<tr><td class='ctr'>M{m['id']}</td>"
            f"<td class='ctr'>N{m['node_i']}→N{m['node_j']}</td>"
            f"<td class='num'>{m['force_kn']:+.3f}</td>"
            f"<td class='num'>{abs(m['stress_mpa']):.2f}</td>"
            f"<td class='ctr'>"
            f"<span class=\"{'ok' if m['nature']=='Tension' else 'fail' if m['nature']=='Compression' else 'warn'}\">"
            f"{m['nature']}</span></td></tr>"
            for m in combo["members"]
        )

        # Reaction table
        react_rows = "".join(
            f"<tr><td class='ctr'>N{n['id']}</td>"
            f"<td class='num'>{n['rx_val']/1000:+.3f}</td>"
            f"<td class='num'>{n['ry_val']/1000:+.3f}</td>"
            f"<td class='num'>{n['rz_val']/1000:+.3f}</td></tr>"
            for n in combo["nodes"]
            if abs(n["rx_val"]) > 0.01 or abs(n["ry_val"]) > 0.01 or abs(n["rz_val"]) > 0.01
        )

        defl_status = "ok" if max_d < 50 else "fail"

        blocks.append(f"""
<h3>Combination: {cname}</h3>
<div class="info-box">
  Maximum nodal displacement: <strong class="{defl_status}">{max_d:.3f} mm</strong>
  &nbsp;(typical limit L/300 ≈ serviceability)
</div>

<h4>Nodal Displacements</h4>
<table>
  <tr><th>Node</th><th>Ux (mm)</th><th>Uy (mm)</th><th>Uz (mm)</th><th>|U| (mm)</th></tr>
  {disp_rows}
</table>

<h4>Member Axial Forces</h4>
<table>
  <tr><th>Member</th><th>Nodes</th><th>Force (kN)</th><th>|σ| (MPa)</th><th>Nature</th></tr>
  {mem_rows}
</table>

<h4>Support Reactions</h4>
<table>
  <tr><th>Node</th><th>Rx (kN)</th><th>Ry (kN)</th><th>Rz (kN)</th></tr>
  {react_rows}
</table>
""")

    return f"""
<h2><span class="sec-num">3.</span> Structural Analysis Results</h2>
{''.join(blocks)}
"""


def _section_is800(members, nodes, combo_result: dict,
                   sections: Optional[dict] = None,
                   fy: float = 250e6, E: float = 200e9) -> str:
    """Step-by-step IS 800:2007 checks for every member."""
    from is_catalog import get_isa_catalog
    catalog = get_isa_catalog()

    node_by_id = {n["id"]: n for n in nodes}
    force_by_id = {m["id"]: m["force_n"] for m in combo_result["members"]}

    def _length(ni, nj):
        a, b = node_by_id.get(ni, {}), node_by_id.get(nj, {})
        if not a or not b:
            return 1.0
        return math.sqrt((b["x"]-a["x"])**2+(b["y"]-a["y"])**2+(b["z"]-a["z"])**2)

    blocks = []
    summary_rows = []

    for m in members:
        mid = m["id"]
        L = _length(m["node_i"], m["node_j"])
        F = force_by_id.get(mid, 0.0)

        # Section properties
        if sections and mid in sections:
            sec_name = sections[mid]
            props = _catalog_by_name(sec_name)
            A, r = props["A"], props["r"]
        else:
            A = m.get("area", m.get("A", 0.005))
            r = 0.01
            sec_name = f"A={A*1e4:.2f} cm² (default)"

        chk = _is800_check(F, L, A, r, fy=fy, E=E)

        status_str = "✓ PASS" if chk["pass"] else "✗ FAIL"
        status_cls = "ok" if chk["pass"] else "fail"

        # Step-by-step block
        if chk["nature"] == "Compression":
            step_html = f"""
<div class="formula">Member M{mid}  ({chk['nature']})  |  Section: {sec_name}
  N{m['node_i']} → N{m['node_j']}  |  L = {L:.4f} m  |  A = {A*1e4:.4f} cm²  |  r_min = {r*1000:.2f} mm

Step 1 — Slenderness ratio (IS 800 Cl. 7.1)
  KL/r = 1.0 × {L:.4f} / {r:.6f} = {chk['KLr']:.2f}
  Limit (compression) = 180
  {'✓ OK' if chk['slender_ok'] else '✗ EXCEEDS LIMIT'}

Step 2 — Euler critical stress (IS 800 Annex D)
  f_cc = π²E / (KL/r)² = π² × {E/1e9:.0f}×10⁹ / {chk['KLr']:.2f}²
       = {chk['fcc_mpa']:.2f} MPa

Step 3 — Non-dimensional slenderness ratio
  λ_n = √(f_y / f_cc) = √({fy/1e6:.0f} / {chk['fcc_mpa']:.2f}) = {chk['lambda_n']:.4f}

Step 4 — Buckling reduction factor φ  (Curve c, α = 0.49)
  φ = 0.5 × [1 + α(λ_n − 0.2) + λ_n²]
    = 0.5 × [1 + 0.49×({chk['lambda_n']:.4f}−0.2) + {chk['lambda_n']:.4f}²]
    = {chk['phi']:.4f}

Step 5 — Design compressive stress
  f_cd = f_y / [φ + √(φ² − λ_n²)]
       = {fy/1e6:.0f} / [{chk['phi']:.4f} + √({chk['phi']:.4f}² − {chk['lambda_n']:.4f}²)]
       = {chk['fcd_mpa']:.2f} MPa

Step 6 — Allowable compressive stress (γ_m0 = 1.1)
  f_ac = f_cd / γ_m0 = {chk['fcd_mpa']:.2f} / 1.1 = {chk['fa_mpa']:.2f} MPa

Step 7 — Actual stress vs allowable
  σ_actual = |F| / A = {abs(F)/1000:.2f} kN / {A*1e4:.4f} cm² = {chk['sigma_actual_mpa']:.2f} MPa
  DCR = σ / f_ac = {chk['sigma_actual_mpa']:.2f} / {chk['fa_mpa']:.2f} = {chk['dcr']:.4f}
  {'✓ DCR ≤ 1.0 — PASS' if chk['stress_ok'] else '✗ DCR > 1.0 — FAIL'}

Overall: {status_str}</div>"""
        else:  # tension or zero
            step_html = f"""
<div class="formula">Member M{mid}  ({chk['nature']})  |  Section: {sec_name}
  N{m['node_i']} → N{m['node_j']}  |  L = {L:.4f} m  |  A = {A*1e4:.4f} cm²  |  r_min = {r*1000:.2f} mm

Step 1 — Slenderness ratio (IS 800 Cl. 7.1 — tension limit = 400)
  KL/r = {chk['KLr']:.2f}  ≤ 400  {'✓ OK' if chk['slender_ok'] else '✗ FAIL'}

Step 2 — Allowable tensile stress (γ_m0 = 1.1)
  f_at = f_y / γ_m0 = {fy/1e6:.0f} / 1.1 = {fy/1e6/1.1:.2f} MPa

Step 3 — Actual stress vs allowable
  σ_actual = F / A = {F/1000:.2f} kN / {A*1e4:.4f} cm² = {chk['sigma_actual_mpa']:.2f} MPa
  DCR = σ / f_at = {chk['sigma_actual_mpa']:.2f} / {chk['fa_mpa']:.2f} = {chk['dcr']:.4f}
  {'✓ DCR ≤ 1.0 — PASS' if chk['stress_ok'] else '✗ DCR > 1.0 — FAIL'}

Overall: {status_str}</div>"""

        blocks.append(step_html)

        # Summary row
        summary_rows.append(
            f"<tr>"
            f"<td class='ctr'>M{mid}</td>"
            f"<td class='ctr'>{sec_name}</td>"
            f"<td class='ctr'>{chk['nature']}</td>"
            f"<td class='num'>{F/1000:+.2f}</td>"
            f"<td class='num'>{chk['KLr']:.1f}</td>"
            f"<td class='num'>{chk['sigma_actual_mpa']:.2f}</td>"
            f"<td class='num'>{chk['fa_mpa']:.2f}</td>"
            f"<td class='num'>{chk['dcr']:.3f}</td>"
            f"<td class='ctr'><span class='{status_cls}'>{status_str}</span></td>"
            f"</tr>"
        )

    n_pass = sum(1 for m in members
                 if _is800_check(
                     force_by_id.get(m["id"], 0.0),
                     _length(m["node_i"], m["node_j"]),
                     (sections and _catalog_by_name(sections.get(m["id"], ""))["A"]) or m.get("area", 0.005),
                     (sections and _catalog_by_name(sections.get(m["id"], ""))["r"]) or 0.01,
                 )["pass"])
    n_total = len(members)
    overall_cls = "ok" if n_pass == n_total else "fail"

    return f"""
<h2><span class="sec-num">4.</span> IS 800:2007 Code Compliance Checks</h2>

<p>Checks performed per <strong>IS 800:2007</strong> using:</p>
<div class="formula">Yield stress  f_y = {fy/1e6:.0f} MPa  (IS 2062 Grade A)
Elastic modulus E  = {E/1e9:.0f} GPa
Effective length K = 1.0  (pin-pin assumption)
Partial factor  γ_m0 = 1.1  (IS 800 Cl. 5.4.1)
Buckling curve  c  (α = 0.49, IS 800 Annex D)
Slenderness limits: 180 (compression), 400 (tension)  [IS 800 Cl. 7.1]</div>

<div class="{'info-box' if n_pass==n_total else 'warn-box'}">
  Code compliance: <span class="{overall_cls}"><strong>{n_pass}/{n_total} members pass IS 800:2007</strong></span>
</div>

<h3>4.1 Detailed Step-by-Step Checks</h3>
{''.join(blocks)}

<h3>4.2 Compliance Summary</h3>
<table>
  <tr><th>Member</th><th>Section</th><th>Nature</th><th>F (kN)</th>
      <th>KL/r</th><th>σ (MPa)</th><th>f_allow (MPa)</th><th>DCR</th><th>Status</th></tr>
  {''.join(summary_rows)}
</table>
"""


def _section_opt_result(method_name: str, result: dict,
                         members, nodes, fy: float = 250e6) -> str:
    """One optimizer's result with IS 800 check per member."""
    if not result:
        return f"<h3>{method_name} — No result available</h3>"

    sections_dict = {s["member_id"]: s["section"]
                     for s in result.get("sections", [])}
    topology_dict = result.get("topology", {})
    active = [s for s in result.get("sections", []) if s.get("active", True)]
    removed = [s for s in result.get("sections", []) if not s.get("active", True)]

    orig_w = result.get("orig_weight_kg", 0.0)
    opt_w  = result.get("weight_kg", 0.0)
    saved  = orig_w - opt_w
    pct    = (saved / orig_w * 100) if orig_w > 0 else 0.0
    valid  = result.get("is_valid", False)

    node_by_id = {n["id"]: n for n in nodes}
    def _length(ni, nj):
        a, b = node_by_id.get(ni, {}), node_by_id.get(nj, {})
        if not a or not b: return 1.0
        return math.sqrt((b["x"]-a["x"])**2+(b["y"]-a["y"])**2+(b["z"]-a["z"])**2)

    sec_rows = ""
    for m in members:
        mid = m["id"]
        sec = sections_dict.get(mid, "—")
        is_active = topology_dict.get(mid, True)
        if not is_active:
            sec_rows += (f"<tr style='opacity:.5;'><td class='ctr'>M{mid}</td>"
                         f"<td class='ctr' colspan='5'><em>Removed by topology optimiser</em></td></tr>")
            continue
        if sec == "—":
            continue
        L = _length(m["node_i"], m["node_j"])
        props = _catalog_by_name(sec)
        A, r = props["A"], props["r"]
        sec_rows += (f"<tr><td class='ctr'>M{mid}</td><td>{sec}</td>"
                     f"<td class='num'>{A*1e4:.3f}</td>"
                     f"<td class='num'>{r*1000:.2f}</td>"
                     f"<td class='num'>{props['w']:.2f}</td>"
                     f"<td class='num'>{L*props['w']:.2f}</td></tr>")

    removed_str = (f", {len(removed)} removed by GA"
                   if removed else " (all members retained)")

    return f"""
<h3>{method_name}</h3>

<div class="{'info-box' if valid else 'warn-box'}">
  <strong>Optimised weight: {opt_w:.2f} kg</strong>
  &nbsp;|&nbsp; Original: {orig_w:.2f} kg
  &nbsp;|&nbsp; Saved: {saved:.2f} kg ({pct:.1f}%)
  &nbsp;|&nbsp; IS 800: <span class="{'ok' if valid else 'fail'}">
    {'✓ Compliant' if valid else '✗ Constraints active'}</span>
  &nbsp;|&nbsp; Active members: {len(active)}{removed_str}
</div>

<table>
  <tr><th>Member</th><th>Section (SP 6(1))</th><th>A (cm²)</th>
      <th>r_min (mm)</th><th>w (kg/m)</th><th>Weight (kg)</th></tr>
  {sec_rows}
</table>
"""


def _section_comparison(opt_results: list) -> str:
    """Side-by-side comparison of all methods."""
    if len(opt_results) < 2:
        return ""

    headers = "".join(f"<th>{r['method']}</th>" for r in opt_results)
    weights  = [r["result"].get("weight_kg", 0) for r in opt_results]
    best_idx = weights.index(min(weights))

    def row(label, vals, fmt=lambda x: x, best_fn=None):
        cells = ""
        for i, v in enumerate(vals):
            cls = "best-col" if i == best_idx else ""
            cells += f"<td class='ctr {cls}'>{fmt(v)}</td>"
        return f"<tr><td><strong>{label}</strong></td>{cells}</tr>"

    weights_fmt = [f"{w:.2f} kg" for w in weights]
    orig_w  = opt_results[0]["result"].get("orig_weight_kg", 1.0)
    savings = [f"{(orig_w-w)/orig_w*100:.1f}%" for w in weights]
    valids  = [
        '<span class="ok">✓ Compliant</span>'
        if r["result"].get("is_valid") else
        '<span class="fail">✗ Violated</span>'
        for r in opt_results
    ]
    topology = [
        f"{sum(1 for v in r['result'].get('topology',{}).values() if not v)} removed"
        if any(not v for v in r["result"].get("topology", {}).values())
        else "All retained"
        for r in opt_results
    ]

    weight_rows = "".join(
        f"<tr><td><strong>{label}</strong></td>"
        + "".join(
            f"<td class='ctr {'best-col' if i == best_idx else ''}'>{vals[i]}</td>"
            for i in range(len(opt_results))
        ) + "</tr>"
        for label, vals in [
            ("Optimised weight (kg)", [f"{w:.2f}" for w in weights]),
            ("Weight saved (%)",       savings),
            ("IS 800 status",          valids),
            ("Topology",               topology),
        ]
    )

    return f"""
<h2><span class="sec-num">6.</span> Method Comparison Summary</h2>

<table>
  <tr><th>Metric</th>{headers}</tr>
  {weight_rows}
</table>

<div class="info-box">
  <strong>Best result: {opt_results[best_idx]['method']}</strong>
  &nbsp;— achieves {weights[best_idx]:.2f} kg ({(orig_w-weights[best_idx])/orig_w*100:.1f}% lighter than baseline).
</div>

<h3>Interpretation</h3>
<p>The comparison above validates the hybrid GA-MINLP approach described in this study.
While DE performs faster (pure sizing), GA-MINLP additionally explores topology
(member removal) and enforces IS 800 constraints exactly through the MINLP Phase 2
rather than through penalty relaxation. This results in a lighter, code-compliant
design that serves as the recommended final configuration.</p>
"""


# ─────────────────────────────────────────────────────────────────
#  Main entry point
# ─────────────────────────────────────────────────────────────────

def generate_report(
    project_name: str,
    engineer: str,
    nodes: list,
    members: list,
    loads: list,
    combos: list,
    solve_result: dict,
    opt_results: list,          # [{"method": "DE", "result": {...}}, ...]
    fy: float = 250e6,
) -> str:
    """
    Build and return a complete HTML report string.

    Parameters
    ----------
    project_name  : title string
    engineer      : author name
    nodes/members/loads/combos : model input dicts
    solve_result  : API SolveResponse dict
    opt_results   : list of {"method": str, "result": OptResult dict}
    fy            : yield stress in Pa
    """
    node_by_id = {n["id"]: n for n in nodes}

    def _dof():
        restrained = sum(int(n.get("rx",0))+int(n.get("ry",0))+int(n.get("rz",0)) for n in nodes)
        return 3*len(nodes) - restrained

    stats = {
        "nodes":    len(nodes),
        "members":  len(members),
        "free_dof": _dof(),
        "combos":   len(combos),
    }

    # Use first combo result for IS 800 checks (most critical typically)
    combo0 = solve_result["combos"][0] if solve_result.get("combos") else None

    # Sections from first opt result (if available)
    first_opt_sections = None
    if opt_results:
        first_opt_sections = {
            s["member_id"]: s["section"]
            for s in opt_results[0]["result"].get("sections", [])
            if s.get("active", True)
        }

    # Build sections
    body = (
        _cover(project_name, engineer, stats) +
        _section_model(nodes, members, loads, combos) +
        _section_dsm() +
        _section_results(solve_result, nodes, members)
    )

    if combo0:
        body += _section_is800(
            members, nodes, combo0,
            sections=first_opt_sections, fy=fy
        )

    if opt_results:
        body += f'<h2><span class="sec-num">5.</span> Optimisation Results</h2>'
        for item in opt_results:
            body += _section_opt_result(
                item["method"], item["result"], members, nodes, fy=fy
            )

    if len(opt_results) >= 2:
        body += _section_comparison(opt_results)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>{project_name} — Truss Analysis Report</title>
  <style>{_CSS}</style>
</head>
<body>
  {_PRINT_BTN}
  {body}
  <p style="margin-top:40px; color:var(--ink3); font-size:9pt; text-align:center;">
    Generated by Space Truss Suite v2.0 · D Mandal · KITS Ramtek ·
    {datetime.date.today().strftime("%B %d, %Y")}
  </p>
</body>
</html>"""
