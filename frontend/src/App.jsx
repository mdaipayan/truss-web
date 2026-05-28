import { useStore }      from './store'
import InputPanel        from './components/InputPanel'
import Viewer3D          from './components/Viewer3D'
import ResultsPanel      from './components/ResultsPanel'
import OptimiserPanel    from './components/OptimiserPanel'
import { solve }         from './api/client'

export default function App() {
  const {
    model, solving, setSolving, setSolveResult, setSolveError,
    activePanel, setActivePanel, solveResult,
  } = useStore()

  async function handleSolve() {
    setSolving(true)
    setSolveError(null)
    try {
      const result = await solve(model)
      setSolveResult(result)
      setActivePanel('results')
    } catch (e) {
      setSolveError(e.message)
    } finally {
      setSolving(false)
    }
  }

  return (
    <div className="flex flex-col h-screen overflow-hidden" style={{ background: 'var(--bg-base)' }}>

      {/* ── Top bar ─────────────────────────────────────────── */}
      <header
        style={{
          background: 'var(--bg-panel)',
          borderBottom: '1px solid var(--border)',
          padding: '0 16px',
          display: 'flex', alignItems: 'center', gap: 16,
          height: 48, flexShrink: 0,
        }}
      >
        <span style={{ fontSize: 16, fontWeight: 700, color: 'var(--text-1)' }}>
          🏗️ Space Truss Suite
        </span>
        <span style={{ fontSize: 11, color: 'var(--text-3)', marginRight: 'auto' }}>
          3D DSM · IS 800:2007 · GA-MINLP  |  D Mandal, KITS Ramtek
        </span>

        {/* Nav tabs */}
        {['input','results','optimizer'].map(tab => (
          <button
            key={tab}
            className={`tab${activePanel === tab ? ' active' : ''}`}
            style={{ borderBottom: activePanel === tab ? '2px solid var(--accent)' : '2px solid transparent' }}
            onClick={() => setActivePanel(tab)}
          >
            {tab === 'input' ? '📐 Input' : tab === 'results' ? '📊 Results' : '🧬 Optimise'}
          </button>
        ))}

        <button
          className={`btn btn-primary btn-sm${solving ? '' : ''}`}
          disabled={solving || model.nodes.length < 2}
          onClick={handleSolve}
        >
          {solving ? '⏳ Solving…' : '▶ Solve'}
        </button>
      </header>

      {/* ── Body: 3-column grid ─────────────────────────────── */}
      <div style={{ flex: 1, display: 'grid', gridTemplateColumns: '340px 1fr 320px', overflow: 'hidden' }}>

        {/* Left — Input / Optimiser panel */}
        <div style={{ borderRight: '1px solid var(--border)', overflowY: 'auto', padding: 12 }}>
          {activePanel === 'optimizer'
            ? <OptimiserPanel onSolveFirst={handleSolve} />
            : <InputPanel />
          }
        </div>

        {/* Centre — 3D Viewer */}
        <div style={{ position: 'relative', overflow: 'hidden' }}>
          <Viewer3D />
        </div>

        {/* Right — Results */}
        <div style={{ borderLeft: '1px solid var(--border)', overflowY: 'auto', padding: 12 }}>
          <ResultsPanel />
        </div>

      </div>
    </div>
  )
}
