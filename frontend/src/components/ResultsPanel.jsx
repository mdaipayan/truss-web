/**
 * ResultsPanel.jsx
 * ─────────────────
 * Right panel showing:
 *  • Combo selector
 *  • Summary metrics (max disp, max force)
 *  • Nodal displacements table
 *  • Member force table (colour-coded)
 *  • Optimiser section assignments (when available)
 */
import { useStore } from '../store'

function Metric({ label, value, unit, color }) {
  return (
    <div style={{
      background: 'var(--bg-card)', borderRadius: 8, padding: '8px 10px',
      border: '1px solid var(--border)', flex: 1, textAlign: 'center',
    }}>
      <div style={{ fontSize: 18, fontWeight: 700, color: color || 'var(--text-1)' }}>
        {value}
        <span style={{ fontSize: 11, color: 'var(--text-3)', marginLeft: 4 }}>{unit}</span>
      </div>
      <div style={{ fontSize: 11, color: 'var(--text-3)', marginTop: 2 }}>{label}</div>
    </div>
  )
}

export default function ResultsPanel() {
  const { solveResult, selectedCombo, setSelectedCombo, solveError, solving, optResult } = useStore()

  if (solving) {
    return (
      <div style={{ padding: 20, color: 'var(--text-3)', textAlign: 'center' }}>
        <div style={{ fontSize: 24, marginBottom: 8 }}>⏳</div>
        Solving…
      </div>
    )
  }

  if (solveError) {
    return (
      <div style={{
        padding: 12, background: 'rgba(239,68,68,.1)',
        border: '1px solid rgba(239,68,68,.3)', borderRadius: 8, color: '#ef4444', fontSize: 12,
      }}>
        ⚠️ {solveError}
      </div>
    )
  }

  if (!solveResult) {
    return (
      <div style={{ color: 'var(--text-3)', fontSize: 12, padding: 12 }}>
        Click <strong>▶ Solve</strong> to see results here.
      </div>
    )
  }

  const combos  = solveResult.combos
  const combo   = combos[selectedCombo]
  if (!combo) return null

  const maxDisp = combo.max_displacement_m * 1000   // → mm
  const maxF    = Math.max(...combo.members.map(m => Math.abs(m.force_kn)))

  return (
    <div>
      {/* Combo selector */}
      <div style={{ marginBottom: 10 }}>
        <div style={{ fontSize: 11, color: 'var(--text-3)', marginBottom: 5, fontWeight: 500 }}>
          LOAD COMBINATION
        </div>
        <select
          style={{ width: '100%', background: 'var(--bg-input)', color: 'var(--text-1)',
            border: '1px solid var(--border)', borderRadius: 6, padding: '5px 8px', fontSize: 12 }}
          value={selectedCombo}
          onChange={e => setSelectedCombo(Number(e.target.value))}
        >
          {combos.map((c, i) => (
            <option key={i} value={i}>{c.combo_name}</option>
          ))}
        </select>
      </div>

      {/* Summary metrics */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
        <Metric label="Max displacement" value={maxDisp.toFixed(3)} unit="mm"
          color={maxDisp > 50 ? '#ef4444' : '#10b981'} />
        <Metric label="Max |force|" value={maxF.toFixed(1)} unit="kN" />
      </div>

      {/* Member forces */}
      <div style={{ marginBottom: 14 }}>
        <div style={{ fontSize: 11, color: 'var(--text-3)', marginBottom: 6, fontWeight: 500 }}>
          MEMBER FORCES
        </div>
        <div style={{ overflowX: 'auto' }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>Member</th>
                <th>Force (kN)</th>
                <th>σ (MPa)</th>
                <th>Nature</th>
              </tr>
            </thead>
            <tbody>
              {combo.members.map(m => {
                const badge = m.nature === 'Tension'     ? 'badge-ok'
                            : m.nature === 'Compression' ? 'badge-danger'
                            :                              'badge-neutral'
                return (
                  <tr key={m.id}>
                    <td style={{ color: 'var(--text-2)' }}>M{m.id}</td>
                    <td style={{ color: m.force_kn > 0 ? '#6366f1' : m.force_kn < 0 ? '#ef4444' : 'var(--text-3)' }}>
                      {m.force_kn > 0 ? '+' : ''}{m.force_kn}
                    </td>
                    <td style={{ color: 'var(--text-2)' }}>{Math.abs(m.stress_mpa).toFixed(1)}</td>
                    <td><span className={`badge ${badge}`}>{m.nature}</span></td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Nodal displacements */}
      <div style={{ marginBottom: 14 }}>
        <div style={{ fontSize: 11, color: 'var(--text-3)', marginBottom: 6, fontWeight: 500 }}>
          NODAL DISPLACEMENTS
        </div>
        <div style={{ overflowX: 'auto' }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>Node</th>
                <th>Ux (mm)</th>
                <th>Uy (mm)</th>
                <th>Uz (mm)</th>
              </tr>
            </thead>
            <tbody>
              {combo.nodes.map(n => (
                <tr key={n.id}>
                  <td style={{ color: 'var(--text-2)' }}>N{n.id}</td>
                  <td>{(n.ux*1000).toFixed(4)}</td>
                  <td>{(n.uy*1000).toFixed(4)}</td>
                  <td>{(n.uz*1000).toFixed(4)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Optimiser results */}
      {optResult && (
        <div>
          <div style={{ fontSize: 11, color: 'var(--text-3)', marginBottom: 6, fontWeight: 500 }}>
            OPTIMISED SECTIONS (IS 800)
          </div>
          <div style={{ display: 'flex', gap: 8, marginBottom: 10 }}>
            <Metric label="Optimised weight" value={optResult.weight_kg.toFixed(1)} unit="kg"
              color="#10b981" />
            <Metric label="Original weight"  value={optResult.orig_weight_kg.toFixed(1)} unit="kg" />
          </div>
          <table className="data-table">
            <thead>
              <tr><th>Member</th><th>Section</th><th>Status</th></tr>
            </thead>
            <tbody>
              {optResult.sections.map(s => (
                <tr key={s.member_id}>
                  <td>M{s.member_id}</td>
                  <td style={{ color: 'var(--text-1)' }}>{s.section}</td>
                  <td>
                    <span className={`badge ${s.active ? 'badge-ok' : 'badge-danger'}`}>
                      {s.active ? 'Active' : 'Removed'}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
