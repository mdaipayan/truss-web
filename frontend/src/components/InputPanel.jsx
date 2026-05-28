/**
 * InputPanel.jsx
 * Editable tables for nodes, members, loads, load combinations.
 * Benchmark loader buttons at the top.
 */
import { useState }    from 'react'
import { useStore }    from '../store'
import { getBenchmark } from '../api/client'

// ── Tiny editable table ───────────────────────────────────────────
function EditTable({ columns, rows, onChange, onAdd, onDelete }) {
  return (
    <div style={{ overflowX: 'auto', marginBottom: 4 }}>
      <table className="data-table">
        <thead>
          <tr>
            {columns.map(c => <th key={c.key}>{c.label}</th>)}
            <th style={{ width: 24 }} />
          </tr>
        </thead>
        <tbody>
          {rows.map((row, ri) => (
            <tr key={ri}>
              {columns.map(c => (
                <td key={c.key} style={{ minWidth: c.width || 52 }}>
                  {c.type === 'bool'
                    ? <input
                        type="checkbox"
                        checked={!!row[c.key]}
                        onChange={e => onChange(ri, c.key, e.target.checked)}
                        style={{ width: 'auto', accentColor: 'var(--accent)' }}
                      />
                    : <input
                        type={c.type === 'text' ? 'text' : 'number'}
                        value={row[c.key] ?? ''}
                        step={c.step || 'any'}
                        onChange={e => {
                          const v = c.type === 'text' ? e.target.value
                            : e.target.value === '' ? '' : Number(e.target.value)
                          onChange(ri, c.key, v)
                        }}
                      />
                  }
                </td>
              ))}
              <td className="row-del" onClick={() => onDelete(ri)}>✕</td>
            </tr>
          ))}
        </tbody>
      </table>
      <button className="btn btn-ghost btn-sm" style={{ marginTop: 4 }} onClick={onAdd}>
        + Add row
      </button>
    </div>
  )
}

// ── Benchmark presets ─────────────────────────────────────────────
const BENCHMARKS = [
  { name: 'tetrahedron', label: '🔺 Tetra' },
  { name: '25bar',       label: '🗼 25-Bar' },
  { name: '72bar',       label: '🏗️ 72-Bar' },
]

export default function InputPanel() {
  const { model, updateNodes, updateMembers, updateLoads, updateCombos, patchModel, reset } = useStore()
  const [loading, setLoading] = useState(false)
  const [tab, setTab]         = useState('nodes')

  // ── Node table columns
  const nodeCols = [
    { key: 'id',  label: 'ID',  width: 32, step: 1 },
    { key: 'x',   label: 'X',   width: 52 },
    { key: 'y',   label: 'Y',   width: 52 },
    { key: 'z',   label: 'Z',   width: 52 },
    { key: 'rx',  label: 'Rx',  type: 'bool', width: 28 },
    { key: 'ry',  label: 'Ry',  type: 'bool', width: 28 },
    { key: 'rz',  label: 'Rz',  type: 'bool', width: 28 },
  ]

  // ── Member table columns
  const memCols = [
    { key: 'id',     label: 'ID',     width: 32, step: 1 },
    { key: 'node_i', label: 'N-i',    width: 44, step: 1 },
    { key: 'node_j', label: 'N-j',    width: 44, step: 1 },
    { key: 'area',   label: 'A (m²)', width: 70 },
    { key: 'E',      label: 'E (Pa)', width: 70 },
  ]

  // ── Load table columns
  const loadCols = [
    { key: 'node_id',    label: 'Node', width: 44, step: 1 },
    { key: 'fx',         label: 'Fx(N)', width: 60 },
    { key: 'fy',         label: 'Fy(N)', width: 60 },
    { key: 'fz',         label: 'Fz(N)', width: 60 },
    { key: 'load_case',  label: 'Case',  type: 'text', width: 44 },
  ]

  function editRow(arr, setter, ri, key, val) {
    const next = arr.map((r, i) => i === ri ? { ...r, [key]: val } : r)
    setter(next)
  }

  async function loadBenchmark(name) {
    setLoading(true)
    try {
      const payload = await getBenchmark(name)
      updateNodes(payload.nodes)
      updateMembers(payload.members)
      updateLoads(payload.loads)
      updateCombos(payload.combos)
      patchModel({ analysis_type: payload.analysis_type, load_steps: payload.load_steps })
    } catch(e) {
      alert('Could not load benchmark: ' + e.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      {/* Benchmark row */}
      <div style={{ marginBottom: 12 }}>
        <div style={{ fontSize: 11, color: 'var(--text-3)', marginBottom: 6, fontWeight: 500 }}>
          BENCHMARK LIBRARY
        </div>
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
          {BENCHMARKS.map(b => (
            <button
              key={b.name}
              className="btn btn-ghost btn-sm"
              disabled={loading}
              onClick={() => loadBenchmark(b.name)}
            >
              {b.label}
            </button>
          ))}
          <button className="btn btn-ghost btn-sm" onClick={reset}>🗑 Clear</button>
        </div>
      </div>

      {/* Tabs */}
      <div className="tabs" style={{ marginBottom: 10 }}>
        {['nodes','members','loads','combos'].map(t => (
          <div key={t} className={`tab${tab===t?' active':''}`} onClick={() => setTab(t)}>
            {t[0].toUpperCase() + t.slice(1)}
          </div>
        ))}
      </div>

      {tab === 'nodes' && (
        <EditTable
          columns={nodeCols}
          rows={model.nodes}
          onChange={(ri,k,v) => editRow(model.nodes, updateNodes, ri, k, v)}
          onAdd={() => updateNodes([...model.nodes, {
            id: (model.nodes.length || 0)+1, x:0, y:0, z:0, rx:false, ry:false, rz:false
          }])}
          onDelete={ri => updateNodes(model.nodes.filter((_,i) => i!==ri))}
        />
      )}

      {tab === 'members' && (
        <EditTable
          columns={memCols}
          rows={model.members}
          onChange={(ri,k,v) => editRow(model.members, updateMembers, ri, k, v)}
          onAdd={() => updateMembers([...model.members, {
            id: (model.members.length||0)+1, node_i:1, node_j:2, area:0.005, E:2e11
          }])}
          onDelete={ri => updateMembers(model.members.filter((_,i) => i!==ri))}
        />
      )}

      {tab === 'loads' && (
        <EditTable
          columns={loadCols}
          rows={model.loads}
          onChange={(ri,k,v) => editRow(model.loads, updateLoads, ri, k, v)}
          onAdd={() => updateLoads([...model.loads, {
            node_id:1, fx:0, fy:0, fz:-10000, load_case:'DL'
          }])}
          onDelete={ri => updateLoads(model.loads.filter((_,i) => i!==ri))}
        />
      )}

      {tab === 'combos' && (
        <div>
          {model.combos.map((c, ci) => (
            <div key={ci} style={{
              background: 'var(--bg-card)', borderRadius: 8,
              padding: '8px 10px', marginBottom: 8,
              border: '1px solid var(--border)',
            }}>
              <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 6 }}>
                <span style={{ fontSize: 11, color: 'var(--text-2)' }}>Name</span>
                <input
                  style={{ flex: 1, background: 'var(--bg-input)', color: 'var(--text-1)',
                    border: '1px solid var(--border)', borderRadius: 4, padding: '3px 6px', fontSize: 12 }}
                  value={c.name}
                  onChange={e => {
                    const next = model.combos.map((x,i) => i===ci ? {...x, name: e.target.value} : x)
                    updateCombos(next)
                  }}
                />
                <button className="btn btn-ghost btn-sm" style={{ color: 'var(--danger)' }}
                  onClick={() => updateCombos(model.combos.filter((_,i)=>i!==ci))}>✕</button>
              </div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                {Object.entries(c.factors).map(([lc, f]) => (
                  <div key={lc} style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                    <span style={{ fontSize: 11, color: 'var(--text-3)' }}>{lc}×</span>
                    <input type="number" step="0.1"
                      style={{ width: 52, background: 'var(--bg-input)', color: 'var(--text-1)',
                        border: '1px solid var(--border)', borderRadius: 4, padding: '2px 5px', fontSize: 12 }}
                      value={f}
                      onChange={e => {
                        const next = model.combos.map((x,i) => i===ci
                          ? {...x, factors: {...x.factors, [lc]: Number(e.target.value)}}
                          : x)
                        updateCombos(next)
                      }}
                    />
                  </div>
                ))}
              </div>
            </div>
          ))}
          <button className="btn btn-ghost btn-sm" onClick={() =>
            updateCombos([...model.combos, { name: 'New Combo', factors: { DL: 1.0 } }])
          }>+ Add combination</button>
        </div>
      )}

      {/* Analysis settings */}
      <div style={{ marginTop: 14, padding: '10px 12px', background: 'var(--bg-card)',
        borderRadius: 8, border: '1px solid var(--border)' }}>
        <div style={{ fontSize: 11, color: 'var(--text-3)', marginBottom: 8, fontWeight: 500 }}>
          SOLVER SETTINGS
        </div>
        <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer' }}>
            <input type="radio" name="atype" value="linear"
              checked={model.analysis_type === 'linear'}
              onChange={() => patchModel({ analysis_type: 'linear' })}
              style={{ accentColor: 'var(--accent)' }} />
            <span style={{ fontSize: 12 }}>Linear</span>
          </label>
          <label style={{ display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer' }}>
            <input type="radio" name="atype" value="nonlinear"
              checked={model.analysis_type === 'nonlinear'}
              onChange={() => patchModel({ analysis_type: 'nonlinear' })}
              style={{ accentColor: 'var(--accent)' }} />
            <span style={{ fontSize: 12 }}>Non-linear P-Δ</span>
          </label>
          {model.analysis_type === 'nonlinear' && (
            <label style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <span style={{ fontSize: 11, color: 'var(--text-3)' }}>Steps</span>
              <input type="number" min={5} max={50} step={5}
                style={{ width: 52, background: 'var(--bg-input)', color: 'var(--text-1)',
                  border: '1px solid var(--border)', borderRadius: 4, padding: '2px 5px', fontSize: 12 }}
                value={model.load_steps}
                onChange={e => patchModel({ load_steps: Number(e.target.value) })} />
            </label>
          )}
        </div>
      </div>
    </div>
  )
}
