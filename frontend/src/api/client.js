/**
 * api/client.js
 * ─────────────
 * Typed wrappers around the FastAPI backend.
 * All functions throw on HTTP error (non-2xx status).
 */

const BASE = '/api'

async function _post(path, body) {
  const res = await fetch(`${BASE}${path}`, {
    method:  'POST',
    headers: { 'Content-Type': 'application/json' },
    body:    JSON.stringify(body),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || `HTTP ${res.status}`)
  }
  return res.json()
}

async function _get(path) {
  const res = await fetch(`${BASE}${path}`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

// ─────────────────────────────────────────────────────────────────
//  Solver
// ─────────────────────────────────────────────────────────────────

/** @param {object} solveRequest  @returns {Promise<{combos: ComboResult[]}>} */
export const solve = (solveRequest) => _post('/solve', solveRequest)

// ─────────────────────────────────────────────────────────────────
//  Catalog & benchmarks
// ─────────────────────────────────────────────────────────────────

export const getCatalog    = ()     => _get('/catalog')
export const getBenchmarks = ()     => _get('/benchmarks')
export const getBenchmark  = (name) => _get(`/benchmarks/${name}`)

// ─────────────────────────────────────────────────────────────────
//  Report generation
// ─────────────────────────────────────────────────────────────────

/**
 * POST /api/report — returns full HTML string.
 * Opens the report in a new browser tab automatically.
 */
export async function generateReport(payload) {
  const res = await fetch('/api/report', {
    method:  'POST',
    headers: { 'Content-Type': 'application/json' },
    body:    JSON.stringify(payload),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || `HTTP ${res.status}`)
  }
  const html = await res.text()
  // Open in new tab
  const blob = new Blob([html], { type: 'text/html' })
  const url  = URL.createObjectURL(blob)
  window.open(url, '_blank')
  return url
}
// ─────────────────────────────────────────────────────────────────

export function runDE(req, onProgress) {
  return new Promise((resolve, reject) => {
    const proto = window.location.protocol === 'https:' ? 'wss' : 'ws'
    const ws    = new WebSocket(`${proto}://${window.location.host}/api/optimize/de`)
    ws.onopen    = () => ws.send(JSON.stringify(req))
    ws.onmessage = (e) => {
      const msg = JSON.parse(e.data)
      if      (msg.type === 'result') { ws.close(); resolve(msg.result) }
      else if (msg.type === 'error')  { ws.close(); reject(new Error(msg.message)) }
      else    onProgress?.(msg)
    }
    ws.onerror = () => reject(new Error('WebSocket error'))
    ws.onclose = () => reject(new Error('WebSocket closed unexpectedly'))
  })
}

// ─────────────────────────────────────────────────────────────────
//  GA-MINLP  (WebSocket — streaming progress)
// ─────────────────────────────────────────────────────────────────

/**
 * Open a WebSocket to /api/optimize/ga-minlp, send the request,
 * and stream messages until the result arrives.
 *
 * @param {object}   req          GAMINLPRequest payload
 * @param {function} onProgress   called for each intermediate WS message
 * @returns {Promise<OptResult>}  resolves when the final result arrives
 */
export function runGAMINLP(req, onProgress) {
  return new Promise((resolve, reject) => {
    const proto = window.location.protocol === 'https:' ? 'wss' : 'ws'
    const host  = window.location.host          // e.g. localhost:5173
    const ws    = new WebSocket(`${proto}://${host}/api/optimize/ga-minlp`)

    ws.onopen = () => {
      ws.send(JSON.stringify(req))
    }

    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data)
      if (msg.type === 'result') {
        ws.close()
        resolve(msg.result)
      } else if (msg.type === 'error') {
        ws.close()
        reject(new Error(msg.message))
      } else {
        onProgress?.(msg)
      }
    }

    ws.onerror = (e) => {
      reject(new Error('WebSocket error — is the backend running?'))
    }

    ws.onclose = () => {
      // If closed without resolve/reject (e.g. server restart), reject
      reject(new Error('WebSocket closed unexpectedly'))
    }
  })
}
