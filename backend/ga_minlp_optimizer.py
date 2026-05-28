"""
ga_minlp_optimizer.py
─────────────────────
Hybrid GA-MINLP optimizer for simultaneous topology, geometry, and sizing
optimisation of 3D space trusses under IS 800:2007 / SP 6(1):1964.

Phase 1  GA   (DEAP)     — global search over topology (binary) + geometry (continuous)
Phase 2  MINLP (scipy DE) — exact IS 800 compliant section sizing for each GA elite

Chromosome layout
─────────────────
  Index  0 … m-1          topology genes  y_i ∈ {0, 1}
  Index  m … m+3k-1        geometry genes  (dx,dy,dz) per free node,  continuous

Coupling to the rest of the app
────────────────────────────────
  • Accepts the same `base_combos` list[TrussSystem] as TrussOptimizer.
  • Returns a 7-tuple compatible with the Streamlit UI block.
  • Inactive members get A = 1e-12 m² (not deleted) so the global K stays
    well-defined; the near-zero stiffness contribution is numerically negligible.
"""

import copy
import random
import numpy as np
from deap import base, creator, tools, algorithms
from scipy.optimize import differential_evolution
from is_catalog import get_isa_catalog


# ── DEAP global type registration (guarded against duplicate calls) ──────────
if not hasattr(creator, "FitnessMinTruss"):
    creator.create("FitnessMinTruss", base.Fitness, weights=(-1.0,))
if not hasattr(creator, "TrussIndividual"):
    creator.create("TrussIndividual", list, fitness=creator.FitnessMinTruss)


class GAMINLPOptimizer:
    """
    Hybrid GA + MINLP two-phase optimizer.

    Parameters
    ----------
    base_combos    : list[TrussSystem]
        One solved TrussSystem per load combination.
    member_groups  : list[list[int]]
        Member ID groups for sizing symmetry / constructability.
        All members in a group get the same catalog section.
    shape_bounds   : dict[int, list[float]]
        {node_id: [dx_lo, dx_hi, dy_lo, dy_hi, dz_lo, dz_hi]}
        Leave empty for pure topology + sizing optimisation.
    yield_stress   : float  (Pa,  default 250 MPa — IS 2062 Grade A)
    max_deflection : float  (m,   default 50 mm)
    is_nonlinear   : bool   (use incremental P-Δ solver in Phase 1/2)
    load_steps     : int    (Newton-Raphson increments for nonlinear)
    n_elite        : int    (how many GA elite solutions carry into Phase 2)
    """

    # Catalog index used for weight estimation in Phase 1 fitness
    # ISA 75×75×6  (index 27) — mid-range section, representative proxy
    _P1_DEFAULT_CAT_IDX = 27

    def __init__(
        self,
        base_combos,
        member_groups=None,
        shape_bounds=None,
        yield_stress=250e6,
        max_deflection=0.05,
        is_nonlinear=False,
        load_steps=10,
        n_elite=5,
    ):
        self.base_combos   = [copy.deepcopy(ts) for ts in base_combos]
        self.yield_stress  = yield_stress
        self.max_deflection = max_deflection
        self.is_nonlinear  = is_nonlinear
        self.load_steps    = load_steps
        self.n_elite       = n_elite
        self.catalog       = get_isa_catalog()

        ref = self.base_combos[0]

        # Ordered member ID list (matches TrussSystem.members order)
        self.member_ids = [m.id for m in ref.members]
        self.n_members  = len(self.member_ids)

        # Sizing groups
        self.member_groups = member_groups or [[m.id] for m in ref.members]
        self.n_groups      = len(self.member_groups)

        # Shape variables
        self.shape_bounds  = shape_bounds or {}
        self._shape_nids   = list(self.shape_bounds.keys())   # ordered node IDs
        self._shape_lohi   = []                               # [(lo,hi), ...]
        for n_id, b in self.shape_bounds.items():
            self._shape_lohi += [(b[0], b[1]), (b[2], b[3]), (b[4], b[5])]
        self.n_shape = len(self._shape_lohi)

        # Total chromosome length: topology genes + shape genes
        self.chrom_len = self.n_members + self.n_shape

        # Immutable base coordinates for geometry resets
        self.base_coords = {n.id: (n.x, n.y, n.z) for n in ref.nodes}

        # Convergence histories (populated during optimise())
        self.hist_p1: list[float] = []
        self.hist_p2: list[float] = []

    # =========================================================== #
    #  Internal helpers                                            #
    # =========================================================== #

    def _decode(self, chrom):
        """Split chromosome into (topo: list[int], shape: list[float])."""
        topo  = [int(round(chrom[i])) for i in range(self.n_members)]
        shape = list(chrom[self.n_members:])
        return topo, shape

    def _apply_to_ts(self, ts, topo, shape, section_indices=None):
        """
        Mutate *ts* in-place:
          1. Shift free nodes by the shape vector.
          2. Set A = 1e-12 for inactive members (topo[i] == 0).
          3. Assign catalog sections to active members if section_indices given.

        Returns False when any member geometry degenerates (zero length).
        """
        # 1. Node shifts
        for j, n_id in enumerate(self._shape_nids):
            node = next((n for n in ts.nodes if n.id == n_id), None)
            if node:
                bx, by, bz = self.base_coords[n_id]
                node.x = bx + shape[3*j]
                node.y = by + shape[3*j + 1]
                node.z = bz + shape[3*j + 2]

        # 2. Topology + sizing
        for i, m_id in enumerate(self.member_ids):
            mbr = next((m for m in ts.members if m.id == m_id), None)
            if mbr is None:
                continue
            try:
                mbr.update_geometry()   # recompute L, l, m, n after node shifts
            except ValueError:
                return False            # degenerate length → penalty

            if topo[i] == 0:
                mbr.A     = 1e-12       # effectively remove the member
                mbr.r_min = 1e-3        # avoid divide-by-zero in buckling calc
            elif section_indices is not None:
                g = next(
                    (gi for gi, grp in enumerate(self.member_groups) if m_id in grp),
                    None,
                )
                if g is not None:
                    cat = int(round(section_indices[g]))
                    mbr.A     = self.catalog.loc[cat, "Area_m2"]
                    mbr.r_min = self.catalog.loc[cat, "r_min_m"]
                    try:
                        mbr.update_geometry()
                    except ValueError:
                        return False
        return True

    def _solve_combos(self, topo, shape, section_indices=None):
        """
        Deep-copy every combo, apply (topo, shape, sections), solve.

        Returns
        -------
        (weight, max_disp, stress_env)  on success
        None                             on any failure (mechanism, singularity…)
        """
        idx_for_weight = (
            section_indices
            if section_indices is not None
            else [self._P1_DEFAULT_CAT_IDX] * self.n_groups
        )
        working  = [copy.deepcopy(ts) for ts in self.base_combos]
        max_disp = 0.0
        stress   = {
            m_id: {"tension": 0.0, "compression": 0.0}
            for m_id in self.member_ids
        }

        for ts in working:
            if not self._apply_to_ts(ts, topo, shape, section_indices):
                return None
            try:
                if self.is_nonlinear:
                    ts.solve_nonlinear(load_steps=self.load_steps)
                else:
                    ts.solve()
            except Exception:
                return None

            if ts.U_global is not None:
                max_disp = max(max_disp, float(np.max(np.abs(ts.U_global))))

            for mbr in ts.members:
                i = self.member_ids.index(mbr.id)
                if topo[i] == 0:
                    continue
                a   = max(mbr.A, 1e-12)
                sig = mbr.internal_force / a
                if sig >= 0:
                    stress[mbr.id]["tension"]     = max(stress[mbr.id]["tension"],     sig)
                else:
                    stress[mbr.id]["compression"] = min(stress[mbr.id]["compression"], sig)

        # Catalog weight (active members only, using the chosen catalog indices)
        ref    = working[0]
        weight = 0.0
        for i, m_id in enumerate(self.member_ids):
            if topo[i] == 0:
                continue
            g = next(
                (gi for gi, grp in enumerate(self.member_groups) if m_id in grp), None
            )
            if g is None:
                continue
            cat     = int(round(idx_for_weight[g]))
            w_per_m = self.catalog.loc[cat, "Weight_kg_m"]
            mbr     = next((m for m in ref.members if m.id == m_id), None)
            if mbr:
                weight += mbr.L * w_per_m

        return weight, max_disp, stress

    # =========================================================== #
    #  Phase 1 — GA (DEAP)                                        #
    # =========================================================== #

    def _fitness_p1(self, individual):
        """
        DEAP fitness function.
        Uses the default mid-catalog section (ISA 75×75×6) for weight proxy.
        IS 800 constraint checks are relaxed here (exact checks in Phase 2).
        """
        topo, shape = self._decode(individual)

        # ── Quick stability gate ──────────────────────────────────────
        n_active  = sum(topo)
        n_nodes   = len(self.base_combos[0].nodes)
        n_react   = sum(
            int(n.rx) + int(n.ry) + int(n.rz)
            for n in self.base_combos[0].nodes
        )
        min_m = max(1, 3 * n_nodes - n_react)
        if n_active < min_m:
            return (1e12,)

        result = self._solve_combos(topo, shape)
        if result is None:
            return (1e12,)

        weight, max_disp, stress = result
        penalty = 0.0

        if max_disp > self.max_deflection:
            penalty += 1e8 * (max_disp / self.max_deflection) ** 2

        # Relaxed stress check (0.6 fy — simplified Phase 1 bound)
        sig_allow = 0.6 * self.yield_stress
        for m_id in self.member_ids:
            if stress[m_id]["tension"] > sig_allow:
                penalty += 1e7 * (stress[m_id]["tension"] / sig_allow) ** 2
            if abs(stress[m_id]["compression"]) > sig_allow:
                penalty += 1e7 * (abs(stress[m_id]["compression"]) / sig_allow) ** 2

        return (weight + penalty,)

    def _make_toolbox(self):
        toolbox = base.Toolbox()

        def _new_individual():
            topo_genes  = [random.randint(0, 1) for _ in range(self.n_members)]
            shape_genes = [random.uniform(lo, hi) for lo, hi in self._shape_lohi]
            return creator.TrussIndividual(topo_genes + shape_genes)

        toolbox.register("individual", _new_individual)
        toolbox.register("population", tools.initRepeat, list, toolbox.individual)
        toolbox.register("evaluate",   self._fitness_p1)
        toolbox.register("mate",       tools.cxTwoPoint)      # natural for mixed chromosome
        toolbox.register("select",     tools.selTournament, tournsize=3)

        def _mutate(ind, bit_prob=0.12, shape_prob=0.15, sigma_frac=0.08):
            # Bit-flip for topology genes
            for i in range(self.n_members):
                if random.random() < bit_prob:
                    ind[i] = 1 - ind[i]
            # Gaussian perturbation for shape genes (clamped to bounds)
            for j, (lo, hi) in enumerate(self._shape_lohi):
                if random.random() < shape_prob:
                    span = max(hi - lo, 1e-6)
                    ind[self.n_members + j] += random.gauss(0, sigma_frac * span)
                    ind[self.n_members + j]  = float(
                        np.clip(ind[self.n_members + j], lo, hi)
                    )
            return (ind,)

        toolbox.register("mutate", _mutate)
        return toolbox

    def run_phase1(self, pop_size: int = 50, n_gen: int = 80):
        """
        Run the GA and return top *n_elite* candidates.

        Returns
        -------
        list of (topo: list[int], shape: list[float], fitness: float)
        """
        toolbox = self._make_toolbox()
        pop     = toolbox.population(n=pop_size)
        hof     = tools.HallOfFame(self.n_elite)

        stats = tools.Statistics(key=lambda ind: ind.fitness.values[0])
        stats.register("min", np.min)
        stats.register("avg", np.mean)

        _, log = algorithms.eaSimple(
            pop, toolbox,
            cxpb=0.70, mutpb=0.25, ngen=n_gen,
            stats=stats, halloffame=hof, verbose=False,
        )

        # Store only feasible generation minima for the convergence plot
        self.hist_p1 = [r["min"] for r in log if r["min"] < 1e11]

        return [
            (
                [int(round(ind[i])) for i in range(self.n_members)],
                list(ind[self.n_members:]),
                ind.fitness.values[0],
            )
            for ind in hof
        ]

    # =========================================================== #
    #  Phase 2 — MINLP (scipy DE with integrality)                #
    # =========================================================== #

    def _fitness_p2(self, x, topo, shape):
        """
        Exact IS 800 sizing objective for fixed topology + geometry.
        All constraint checks are hard (no relaxation).
        """
        result = self._solve_combos(topo, shape, section_indices=x)
        if result is None:
            return 1e12

        weight, max_disp, stress = result
        penalty = 0.0

        # ── IS 800 Cl 5.6.1 deflection ────────────────────────────────
        if max_disp > self.max_deflection:
            penalty += 1e9 * (max_disp / self.max_deflection) ** 2

        # ── IS 800 Cl 7.1 + Annex D — per member group ────────────────
        for g, m_ids in enumerate(self.member_groups):
            cat  = int(round(x[g]))
            r    = self.catalog.loc[cat, "r_min_m"]
            E    = 2e11  # Pa  (IS 800, steel modulus)

            for m_id in m_ids:
                i = self.member_ids.index(m_id)
                if topo[i] == 0:
                    continue

                ref_mbr = next(
                    (m for m in self.base_combos[0].members if m.id == m_id), None
                )
                L = ref_mbr.L if ref_mbr else 1.0

                # Slenderness  (IS 800 Cl 7.1)
                KLr = L / max(r, 1e-6)
                if KLr > 180:
                    penalty += 1e9 * (KLr / 180) ** 2

                # Buckling stress  (IS 800 Annex D, curve c, α = 0.49)
                fcc    = (np.pi ** 2 * E) / max(KLr, 1e-3) ** 2
                lam    = np.sqrt(self.yield_stress / fcc)
                alpha  = 0.49
                phi    = 0.5 * (1 + alpha * (lam - 0.2) + lam ** 2)
                fcd    = self.yield_stress / (phi + np.sqrt(max(phi**2 - lam**2, 0.0)))
                fa_c   = min(fcd, self.yield_stress) / 1.1   # allowable compression
                fa_t   = self.yield_stress / 1.1              # allowable tension

                sig_t = stress[m_id]["tension"]
                sig_c = abs(stress[m_id]["compression"])
                if sig_t > fa_t:
                    penalty += 1e9 * (sig_t / fa_t) ** 2
                if sig_c > fa_c:
                    penalty += 1e9 * (sig_c / fa_c) ** 2

        fitness = weight + penalty
        if fitness < self._p2_best:
            self._p2_best = fitness
        return fitness

    def run_phase2(self, topo, shape, pop_size: int = 15, max_gen: int = 80):
        """
        Run the MINLP sizing phase for a fixed topology + geometry.

        Returns
        -------
        sections   : dict[member_id → section_designation]
        weight     : float (kg, penalty-contaminated when is_valid=False)
        is_valid   : bool  (True iff no IS 800 constraint is violated)
        """
        self._p2_best  = float("inf")
        self.hist_p2   = []
        max_idx        = len(self.catalog) - 1

        def _cb(xk, convergence=None):
            self.hist_p2.append(self._p2_best)

        res = differential_evolution(
            self._fitness_p2,
            bounds     = [(0, max_idx)] * self.n_groups,
            args       = (topo, shape),
            integrality= np.ones(self.n_groups, dtype=int),
            strategy   = "best1bin",
            popsize    = pop_size,
            maxiter    = max_gen,
            tol        = 0.005,
            mutation   = (0.5, 1.0),
            recombination = 0.7,
            callback   = _cb,
            disp       = False,
        )

        opt_idx  = [int(round(v)) for v in res.x]
        sections = {}
        for g, m_ids in enumerate(self.member_groups):
            name = self.catalog.loc[opt_idx[g], "Designation"]
            for m_id in m_ids:
                sections[m_id] = name

        return sections, res.fun, (res.fun < 1e8)

    # =========================================================== #
    #  Public entry point                                          #
    # =========================================================== #

    def optimize(
        self,
        ga_pop:    int = 50,
        ga_gen:    int = 80,
        minlp_pop: int = 15,
        minlp_gen: int = 80,
    ):
        """
        Full two-phase GA-MINLP optimisation.

        Returns
        -------
        sections     : dict[member_id → section_name]
        topology     : dict[member_id → bool]   True = active, False = removed
        node_shifts  : dict[node_id  → {dx,dy,dz}]
        final_weight : float  (kg)
        is_valid     : bool
        hist_p1      : list[float]  — GA best-per-generation (for plot)
        hist_p2      : list[float]  — MINLP best-per-iteration (for plot)
        """
        # ── Phase 1 ──────────────────────────────────────────────
        elite = self.run_phase1(pop_size=ga_pop, n_gen=ga_gen)

        # ── Phase 2 ──────────────────────────────────────────────
        best_weight = float("inf")
        best_pack   = None
        combined_p2 = []

        for rank, (topo, shape, _) in enumerate(elite):
            sections, w, valid = self.run_phase2(
                topo, shape, pop_size=minlp_pop, max_gen=minlp_gen
            )
            combined_p2.extend(self.hist_p2)

            if valid and w < best_weight:
                best_weight = w
                best_pack   = (sections, topo, shape, w, valid)

        # Fallback: accept the best GA candidate even if MINLP is infeasible
        if best_pack is None:
            topo, shape, _ = elite[0]
            sections, w, valid = self.run_phase2(
                topo, shape, pop_size=minlp_pop, max_gen=minlp_gen
            )
            combined_p2.extend(self.hist_p2)
            best_pack = (sections, topo, shape, w, valid)

        self.hist_p2              = combined_p2
        sections, topo, shape, fw, is_valid = best_pack

        topology_dict = {
            m_id: bool(topo[i])
            for i, m_id in enumerate(self.member_ids)
        }
        node_shifts = {
            n_id: {"dx": shape[3*j], "dy": shape[3*j+1], "dz": shape[3*j+2]}
            for j, n_id in enumerate(self._shape_nids)
        }

        return (
            sections,
            topology_dict,
            node_shifts,
            fw,
            is_valid,
            self.hist_p1,
            self.hist_p2,
        )
