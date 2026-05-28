/**
 * OptimiserPanel.jsx — Three modes: DE, GA-MINLP, All
 * Adds Run All + comparison table + Generate Full Report button
 */
import { useRef, useState }      from 'react'
import Plot              from 'react-plotly.js'
import { useStore }      from '../store'
import { runDE, runGAMINLP, generateReport } from '../api/client'

function Field({ label, value, onChange, min, max, step=1 }) {
  return (
    <label style={{display:'flex',alignItems:'center',gap:8}}>
      <span style={{fontSize:11,color:'var(--text-3)',minWidth:110}}>{label}</span>
      <input type="number" min={min} max={max} step={step} value={value}
        onChange={e=>onChange(Number(e.target.value))}
        style={{width:64,background:'var(--bg-input)',color:'var(--text-1)',
          border:'1px solid var(--border)',borderRadius:4,padding:'3px 6px',fontSize:12}}/>
    </label>
  )
}

function ComparisonTable({ results }) {
  if (!results || results.length < 2) return null
  const weights = results.map(r => r.result?.weight_kg ?? Infinity)
  const bestIdx = weights.indexOf(Math.min(...weights))
  const origW   = results[0].result?.orig_weight_kg ?? 1
  const rows = [
    ['Optimised weight (kg)', results.map(r => (r.result?.weight_kg??0).toFixed(2))],
    ['Weight saved (%)',       results.map(r => {
       const w = r.result?.weight_kg ?? origW; return ((origW-w)/origW*100).toFixed(1)+'%'
    })],
    ['IS 800 compliant',      results.map(r => r.result?.is_valid?'✅ Yes':'⚠️ Violated')],
    ['Members removed',       results.map(r => {
       const n = Object.values(r.result?.topology??{}).filter(v=>!v).length
       return n>0?`${n} removed`:'All retained'
    })],
  ]
  return (
    <div style={{marginBottom:14}}>
      <div style={{fontSize:11,color:'var(--text-3)',marginBottom:6,fontWeight:500}}>
        METHOD COMPARISON
      </div>
      <table className="data-table">
        <thead>
          <tr>
            <th style={{textAlign:'left'}}>Metric</th>
            {results.map((r,i)=>(
              <th key={i} style={{
                color:i===bestIdx?'#10b981':undefined,
                background:i===bestIdx?'rgba(16,185,129,.2)':undefined
              }}>{r.method}{i===bestIdx?' ★':''}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map(([label,vals])=>(
            <tr key={label}>
              <td style={{color:'var(--text-2)',fontWeight:500}}>{label}</td>
              {vals.map((v,i)=>(
                <td key={i} style={{
                  textAlign:'center',
                  background:i===bestIdx?'rgba(16,185,129,.07)':undefined,
                  fontWeight:i===bestIdx?600:undefined
                }}>{v}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default function OptimiserPanel({ onSolveFirst }) {
  const {
    model, solveResult, groupsStr, setGroupsStr,
    setOptResult, setOptRunning, pushOptProgress, clearOptProgress,
    optRunning, optProgress, optResult, optError, setOptError,
    allOptResults, pushAllOptResult, clearAllOptResults, setAllOptResults,
  } = useStore()

  const [mode,    setMode]    = useState('ga-minlp')
  const [yMPa,    setYMPa]    = useState(250)
  const [dfl,     setDfl]     = useState(50)
  const [gaPop,   setGaPop]   = useState(50)
  const [gaGen,   setGaGen]   = useState(80)
  const [mpPop,   setMpPop]   = useState(15)
  const [mpGen,   setMpGen]   = useState(80)
  const [elite,   setElite]   = useState(5)
  const [dePop,   setDePop]   = useState(20)
  const [deGen,   setDeGen]   = useState(100)
  const [status,  setStatus]  = useState('')
  const [proj,    setProj]    = useState('Space Truss Analysis')
  const [repLoad, setRepLoad] = useState(false)
  const stopRequestedRef       = useRef(false)

  function mkGroups() {
    const raw = groupsStr.trim()
    if (!raw) return model.members.map(m=>[m.id])
    return raw.split(';').map(g=>g.split(',').map(x=>parseInt(x.trim())).filter(x=>!isNaN(x))).filter(g=>g.length)
  }

  function base() {
    return {solve_request:model, member_groups:mkGroups(), shape_bounds:{},
            yield_stress:yMPa*1e6, max_deflection:dfl/1000}
  }

  async function runSingle(m) {
    if (!solveResult) { await onSolveFirst(); return }
    stopRequestedRef.current = false
    clearOptProgress(); setOptError(null); setOptRunning(true)
    try {
      const p=base(); let result
      if (m==='de') { p.pop_size=dePop; p.max_gen=deGen; result=await runDE(p, msg=>!stopRequestedRef.current&&pushOptProgress(msg)) }
      else { p.ga_pop=gaPop; p.ga_gen=gaGen; p.minlp_pop=mpPop; p.minlp_gen=mpGen; p.n_elite=elite
             result=await runGAMINLP(p, msg=>!stopRequestedRef.current&&pushOptProgress(msg)) }
      if (stopRequestedRef.current) return
      setOptResult(result)
    } catch(e) {
      if (!stopRequestedRef.current) setOptError(e.message)
    } finally { setOptRunning(false) }
  }

  async function runAll() {
    if (!solveResult) { await onSolveFirst(); return }
    stopRequestedRef.current = false
    clearOptProgress(); clearAllOptResults(); setOptError(null); setOptRunning(true)
    const methods=[{key:'de',label:'DE Optimizer'},{key:'ga-minlp',label:'GA-MINLP'}]
    const collected=[]
    for (const {key,label} of methods) {
      if (stopRequestedRef.current) break
      setStatus(`Running ${label}…`)
      try {
        const p=base(); let result
        if (key==='de') { p.pop_size=dePop; p.max_gen=deGen; result=await runDE(p,msg=>!stopRequestedRef.current&&pushOptProgress({...msg,method:key})) }
        else { p.ga_pop=gaPop; p.ga_gen=gaGen; p.minlp_pop=mpPop; p.minlp_gen=mpGen; p.n_elite=elite
               result=await runGAMINLP(p,msg=>!stopRequestedRef.current&&pushOptProgress({...msg,method:key})) }
        if (stopRequestedRef.current) break
        const item={method:label,result}; collected.push(item); pushAllOptResult(item); setOptResult(result)
      } catch(e) {
        if (!stopRequestedRef.current) pushAllOptResult({method:label,result:null,error:e.message})
      }
    }
    setAllOptResults(collected)
    setStatus(stopRequestedRef.current ? 'Run stopped by user' : 'All methods complete')
    setOptRunning(false)
  }

  async function doReport() {
    if (!solveResult) return; setRepLoad(true)
    try {
      const optPay=allOptResults.length>0?allOptResults
        :optResult?[{method:mode==='de'?'DE':'GA-MINLP',result:optResult}]:[]
      await generateReport({
        project_name:proj, engineer:'D Mandal', solve_request:model,
        solve_result:solveResult, opt_results:optPay.map(r=>({method:r.method,result:r.result})),
        yield_stress:yMPa*1e6
      })
    } catch(e) { alert('Report error: '+e.message) }
    finally { setRepLoad(false) }
  }

  const p1=optProgress.filter(m=>m.phase===1&&m.type==='progress')
  const p2=optProgress.filter(m=>m.phase===2&&m.type==='progress')
  const lastPh=optProgress.filter(m=>m.type==='phase').slice(-1)[0]
  const cL=(t)=>({height:150,margin:{l:42,r:8,t:8,b:30},
    paper_bgcolor:'rgba(0,0,0,0)',plot_bgcolor:'rgba(0,0,0,0)',
    xaxis:{title:t,color:'#5c6480',gridcolor:'#2a2f45'},
    yaxis:{title:'kg',color:'#5c6480',gridcolor:'#2a2f45'},font:{color:'#9ba3c4',size:10}})

  return (
    <div>
      <div style={{fontSize:11,color:'var(--text-3)',fontWeight:500,marginBottom:10}}>IS 800 OPTIMISER</div>

      <div style={{display:'flex',gap:5,marginBottom:12}}>
        {[['de','DE'],['ga-minlp','GA-MINLP'],['all','🔁 All']].map(([k,l])=>(
          <button key={k} className={`btn btn-sm ${mode===k?'btn-primary':'btn-ghost'}`} onClick={()=>setMode(k)}>{l}</button>
        ))}
      </div>

      <div style={{display:'flex',flexDirection:'column',gap:6,marginBottom:10,
        background:'var(--bg-card)',borderRadius:8,padding:'10px 12px',border:'1px solid var(--border)'}}>
        <div style={{fontSize:11,color:'var(--text-3)',marginBottom:2}}>CONSTRAINTS</div>
        <Field label="Yield stress (MPa)" value={yMPa} onChange={setYMPa} min={100} max={500}/>
        <Field label="Max deflection (mm)" value={dfl} onChange={setDfl} min={1} max={500}/>
      </div>

      {(mode==='de'||mode==='all') && (
        <div style={{display:'flex',flexDirection:'column',gap:6,marginBottom:10,
          background:'var(--bg-card)',borderRadius:8,padding:'10px 12px',border:'1px solid var(--border)'}}>
          <div style={{fontSize:11,color:'var(--text-3)',marginBottom:2}}>DE PARAMETERS</div>
          <Field label="Population" value={dePop} onChange={setDePop} min={5} max={100}/>
          <Field label="Generations" value={deGen} onChange={setDeGen} min={10} max={500}/>
        </div>
      )}

      {(mode==='ga-minlp'||mode==='all') && (
        <div style={{display:'flex',flexDirection:'column',gap:6,marginBottom:10,
          background:'var(--bg-card)',borderRadius:8,padding:'10px 12px',border:'1px solid var(--border)'}}>
          <div style={{fontSize:11,color:'var(--text-3)',marginBottom:2}}>GA-MINLP PARAMETERS</div>
          <Field label="GA population"  value={gaPop}  onChange={setGaPop}  min={10} max={200}/>
          <Field label="GA generations" value={gaGen}  onChange={setGaGen}  min={10} max={300}/>
          <Field label="MINLP pop"      value={mpPop}  onChange={setMpPop}  min={5}  max={50}/>
          <Field label="MINLP iters"    value={mpGen}  onChange={setMpGen}  min={10} max={300}/>
          <Field label="Elite K"        value={elite}  onChange={setElite}  min={1}  max={20}/>
        </div>
      )}

      <div style={{marginBottom:10}}>
        <div style={{fontSize:11,color:'var(--text-3)',marginBottom:4,fontWeight:500}}>MEMBER GROUPS</div>
        <textarea rows={2} value={groupsStr} onChange={e=>setGroupsStr(e.target.value)}
          placeholder="e.g. 1,2,3; 4,5,6  (blank = each member separate)"
          style={{width:'100%',background:'var(--bg-input)',color:'var(--text-1)',
            border:'1px solid var(--border)',borderRadius:6,padding:'5px 8px',fontSize:11,resize:'vertical'}}/>
      </div>

      <div style={{display:'flex',gap:8,marginBottom:12}}>
        <button className="btn btn-success" style={{flex:1}}
          disabled={optRunning||!model.members.length}
          onClick={()=>mode==='all'?runAll():runSingle(mode)}>
          {optRunning?`⏳ ${status||'Running…'}`:mode==='all'?'🔁 Run All Methods':mode==='de'?'🚀 Run DE':'🧬 Run GA-MINLP'}
        </button>
        {optRunning&&<button className="btn btn-danger" onClick={()=>{ stopRequestedRef.current = true; setOptRunning(false); setStatus('Stopping…') }}>■</button>}
      </div>

      {optError&&<div style={{padding:8,background:'rgba(239,68,68,.1)',border:'1px solid rgba(239,68,68,.3)',
        borderRadius:6,color:'#ef4444',fontSize:11,marginBottom:8}}>{optError}</div>}

      {optRunning&&lastPh&&<div style={{fontSize:11,color:'var(--accent)',marginBottom:8}}>{lastPh.message}</div>}

      {p1.length>1&&<div style={{marginBottom:8}}>
        <div style={{fontSize:11,color:'var(--text-3)',marginBottom:3}}>PHASE 1 — GA convergence</div>
        <Plot data={[{x:p1.map(m=>m.generation),y:p1.map(m=>m.best),type:'scatter',mode:'lines',line:{color:'#f59e0b',width:2}}]}
          layout={cL('Generation')} config={{displayModeBar:false,responsive:true}} style={{width:'100%'}} useResizeHandler/>
      </div>}
      {p2.length>1&&<div style={{marginBottom:8}}>
        <div style={{fontSize:11,color:'var(--text-3)',marginBottom:3}}>PHASE 2 — MINLP convergence</div>
        <Plot data={[{x:p2.map(m=>m.iteration),y:p2.map(m=>m.best),type:'scatter',mode:'lines',line:{color:'#10b981',width:2}}]}
          layout={cL('Iteration')} config={{displayModeBar:false,responsive:true}} style={{width:'100%'}} useResizeHandler/>
      </div>}

      {allOptResults.length>=2&&<ComparisonTable results={allOptResults}/>}

      {optResult&&!optRunning&&allOptResults.length<2&&(
        <div style={{background:'rgba(16,185,129,.1)',border:'1px solid rgba(16,185,129,.3)',
          borderRadius:8,padding:'10px 12px',textAlign:'center',marginBottom:12}}>
          <div style={{fontSize:20,fontWeight:700,color:'#10b981'}}>{optResult.weight_kg?.toFixed(1)} kg</div>
          <div style={{fontSize:11,color:'var(--text-3)'}}>
            {((1-optResult.weight_kg/(optResult.orig_weight_kg||1))*100).toFixed(1)}% saved
          </div>
          <span className={`badge ${optResult.is_valid?'badge-ok':'badge-warn'}`} style={{marginTop:6,display:'inline-block'}}>
            {optResult.is_valid?'✓ IS 800 compliant':'⚠ Constraints active'}
          </span>
        </div>
      )}

      {/* Report */}
      {solveResult&&(
        <div style={{borderTop:'1px solid var(--border)',paddingTop:12,marginTop:8}}>
          <div style={{fontSize:11,color:'var(--text-3)',fontWeight:500,marginBottom:8}}>GENERATE REPORT</div>
          <input value={proj} onChange={e=>setProj(e.target.value)}
            placeholder="Project title…"
            style={{width:'100%',background:'var(--bg-input)',color:'var(--text-1)',
              border:'1px solid var(--border)',borderRadius:6,padding:'5px 8px',fontSize:12,marginBottom:8}}/>
          <button className="btn btn-primary" style={{width:'100%'}} disabled={repLoad} onClick={doReport}>
            {repLoad?'⏳ Generating…':'📄 Generate Full IS 800 Report'}
          </button>
          <div style={{fontSize:10,color:'var(--text-3)',marginTop:4,textAlign:'center'}}>
            Opens in new tab · step-by-step IS 800 checks · print to PDF
          </div>
        </div>
      )}
    </div>
  )
}
