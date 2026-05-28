/**
 * Viewer3D.jsx
 * ─────────────
 * 3D Plotly canvas. Shows:
 *   • Undeformed geometry (nodes + dashed members) always
 *   • Member forces colour-coded when results are available
 *   • Support reactions as green annotations
 *   • Removed-by-GA members in red/dashed overlay if opt result exists
 */
import { useMemo }       from 'react'
import Plot              from 'react-plotly.js'
import { useStore }      from '../store'

const LAYOUT_BASE = {
  margin: { l: 0, r: 0, t: 0, b: 0 },
  paper_bgcolor: 'rgba(0,0,0,0)',
  plot_bgcolor:  'rgba(0,0,0,0)',
  scene: {
    xaxis: { title: 'X (m)', color: '#9ba3c4', gridcolor: '#2a2f45', zerolinecolor: '#343a52' },
    yaxis: { title: 'Y (m)', color: '#9ba3c4', gridcolor: '#2a2f45', zerolinecolor: '#343a52' },
    zaxis: { title: 'Z (m)', color: '#9ba3c4', gridcolor: '#2a2f45', zerolinecolor: '#343a52' },
    bgcolor: '#0f1117',
    aspectmode: 'data',
    camera: { eye: { x: 1.8, y: 1.8, z: 1.4 } },
  },
  showlegend: false,
  autosize: true,
}

export default function Viewer3D() {
  const { model, solveResult, selectedCombo, optResult } = useStore()

  // ── Build Plotly traces ──────────────────────────────────────
  const traces = useMemo(() => {
    const { nodes, members } = model
    if (!nodes.length) return []

    const nodeById = Object.fromEntries(nodes.map(n => [n.id, n]))
    const result   = solveResult?.combos?.[selectedCombo]
    const forceMap = result
      ? Object.fromEntries(result.members.map(m => [m.id, m]))
      : {}
    const topoMap  = optResult?.topology || {}

    const traces = []

    // ── Node scatter ────────────────────────────────────────────
    traces.push({
      type: 'scatter3d', mode: 'markers+text',
      x: nodes.map(n => n.x), y: nodes.map(n => n.y), z: nodes.map(n => n.z),
      text: nodes.map(n => `N${n.id}`), textposition: 'top center',
      textfont: { size: 10, color: '#9ba3c4' },
      marker: {
        size:  nodes.map(n => (n.rx || n.ry || n.rz) ? 7 : 5),
        color: nodes.map(n => (n.rx || n.ry || n.rz) ? '#f59e0b' : '#6366f1'),
        symbol: 'circle',
      },
      hovertemplate: nodes.map(n => `N${n.id} (${n.x},${n.y},${n.z})<extra></extra>`),
    })

    // ── Members ─────────────────────────────────────────────────
    for (const mb of members) {
      const ni = nodeById[mb.node_i]
      const nj = nodeById[mb.node_j]
      if (!ni || !nj) continue

      const fInfo   = forceMap[mb.id]
      const removed = topoMap[mb.id] === false

      let color = '#4a5280'   // undeformed default
      let width = 3
      let dash  = 'solid'

      if (fInfo) {
        const f = fInfo.force_n
        color = Math.abs(f) < 1 ? '#4a5280'
              : f < 0           ? '#ef4444'   // compression → red
              :                   '#6366f1'   // tension → indigo
        width = 5
      }
      if (removed) { color = '#ef4444'; dash = 'dash'; width = 2 }

      traces.push({
        type: 'scatter3d', mode: 'lines',
        x: [ni.x, nj.x], y: [ni.y, nj.y], z: [ni.z, nj.z],
        line: { color, width, dash },
        hovertemplate: fInfo
          ? `M${mb.id}: ${fInfo.force_kn > 0 ? '+' : ''}${fInfo.force_kn} kN (${fInfo.nature})<extra></extra>`
          : `M${mb.id}<extra></extra>`,
      })

      // Midpoint force label
      if (fInfo && Math.abs(fInfo.force_n) > 1) {
        traces.push({
          type: 'scatter3d', mode: 'text',
          x: [(ni.x+nj.x)/2], y: [(ni.y+nj.y)/2], z: [(ni.z+nj.z)/2],
          text: [`${Math.abs(fInfo.force_kn).toFixed(1)}kN`],
          textfont: { size: 9, color },
          hoverinfo: 'none',
        })
      }
    }

    return traces
  }, [model, solveResult, selectedCombo, optResult])

  // ── Annotations for support reactions ────────────────────────
  const annotations = useMemo(() => {
    const result = solveResult?.combos?.[selectedCombo]
    if (!result) return []
    const nodeById = Object.fromEntries(model.nodes.map(n => [n.id, n]))
    return result.nodes
      .filter(n => {
        const nd = nodeById[n.id]
        return nd && (nd.rx || nd.ry || nd.rz)
      })
      .map(n => {
        const nd = nodeById[n.id]
        return {
          x: nd.x, y: nd.y, z: nd.z,
          text: `Rx:${n.rx_val.toFixed(1)}<br>Ry:${n.ry_val.toFixed(1)}<br>Rz:${n.rz_val.toFixed(1)}`,
          showarrow: true, arrowcolor: '#10b981', arrowwidth: 1, arrowhead: 2,
          ax: 50, ay: -50,
          font: { size: 10, color: '#fff' },
          bgcolor: '#064e3b', bordercolor: '#10b981', borderwidth: 1,
          opacity: 0.92,
        }
      })
  }, [solveResult, selectedCombo, model.nodes])

  const layout = {
    ...LAYOUT_BASE,
    scene: {
      ...LAYOUT_BASE.scene,
      annotations,
    },
  }

  if (!model.nodes.length) {
    return (
      <div style={{
        height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center',
        color: 'var(--text-3)', fontSize: 13,
      }}>
        Add nodes in the Input panel or load a benchmark to see the 3D model.
      </div>
    )
  }

  return (
    <Plot
      data={traces}
      layout={layout}
      style={{ width: '100%', height: '100%' }}
      config={{
        displayModeBar: true,
        toImageButtonOptions: {
          format: 'png', filename: 'truss_3d',
          width: 1600, height: 1200, scale: 3,
        },
        responsive: true,
      }}
      useResizeHandler
    />
  )
}
