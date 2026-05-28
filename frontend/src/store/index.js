/**
 * store/index.js — Zustand global state
 *
 * Single source of truth for:
 *   • model  (nodes, members, loads, combos)
 *   • solver results
 *   • optimizer results + progress
 *   • UI flags (loading, active tab, selected combo)
 */
import { create } from 'zustand'

// ─── Default empty model ─────────────────────────────────────────
const EMPTY_MODEL = {
  nodes:   [],
  members: [],
  loads:   [],
  combos:  [{ name: 'Gravity (1.0 DL)', factors: { DL: 1.0 } }],
  analysis_type: 'linear',
  load_steps: 10,
}

export const useStore = create((set, get) => ({

  // ── Model ───────────────────────────────────────────────────────
  model: EMPTY_MODEL,
  setModel: (m) => set({ model: m }),
  patchModel: (patch) => set((s) => ({ model: { ...s.model, ...patch } })),

  updateNodes:   (nodes)   => set((s) => ({ model: { ...s.model, nodes   } })),
  updateMembers: (members) => set((s) => ({ model: { ...s.model, members } })),
  updateLoads:   (loads)   => set((s) => ({ model: { ...s.model, loads   } })),
  updateCombos:  (combos)  => set((s) => ({ model: { ...s.model, combos  } })),

  // ── Member groups string (for optimizer) ───────────────────────
  groupsStr: '',
  setGroupsStr: (s) => set({ groupsStr: s }),

  // ── Solver ──────────────────────────────────────────────────────
  solveResult: null,           // { combos: ComboResult[] }
  selectedCombo: 0,            // index into solveResult.combos
  solving: false,
  solveError: null,

  setSolveResult: (r)  => set({ solveResult: r, selectedCombo: 0, solveError: null }),
  setSelectedCombo: (i) => set({ selectedCombo: i }),
  setSolving: (b)      => set({ solving: b }),
  setSolveError: (e)   => set({ solveError: e }),

  // ── Optimizer ───────────────────────────────────────────────────
  optResult: null,
  optRunning: false,
  optProgress: [],             // list of WS progress messages
  optError: null,

  setOptResult:  (r) => set({ optResult: r, optError: null }),
  setOptRunning: (b) => set({ optRunning: b }),
  pushOptProgress: (msg) =>
    set((s) => ({ optProgress: [...s.optProgress.slice(-200), msg] })),
  clearOptProgress: ()   => set({ optProgress: [] }),
  setOptError: (e)       => set({ optError: e }),

  // ── UI ──────────────────────────────────────────────────────────
  activePanel:  'input',   // 'input' | 'results' | 'optimizer'
  setActivePanel: (p) => set({ activePanel: p }),

  // ── All-methods run ──────────────────────────────────────────
  allOptResults: [],           // [{method, result}, ...]
  setAllOptResults: (r) => set({ allOptResults: r }),
  pushAllOptResult: (item) =>
    set((s) => ({ allOptResults: [...s.allOptResults, item] })),
  clearAllOptResults: () => set({ allOptResults: [] }),

  // ── Reset ───────────────────────────────────────────────────────
  reset: () => set({
    model: EMPTY_MODEL,
    solveResult: null, solving: false, solveError: null,
    optResult: null, optRunning: false, optProgress: [], optError: null,
    groupsStr: '',
  }),
}))
