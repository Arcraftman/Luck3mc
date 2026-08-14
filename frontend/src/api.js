// API client for the STACrawler FastAPI backend.
// Override the base URL with VITE_API_BASE (e.g. the prod domain) if needed.
const BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8100'

export async function fetchPolicies({ q = '', source = '', limit = 50, skip = 0 } = {}) {
  const params = new URLSearchParams({ limit, skip })
  if (q) params.set('q', q)
  if (source) params.set('source', source)
  const res = await fetch(`${BASE}/api/policies?${params.toString()}`)
  if (!res.ok) throw new Error(`policies ${res.status}`)
  return res.json()
}

export async function fetchReports({ limit = 50, skip = 0, date = '', source = '' } = {}) {
  const params = new URLSearchParams({ limit, skip })
  if (date) params.set('date', date)
  if (source) params.set('source', source)
  const res = await fetch(`${BASE}/api/reports?${params.toString()}`)
  if (!res.ok) throw new Error(`reports ${res.status}`)
  return res.json()
}

// Subscribe to the SSE stream; returns the EventSource for cleanup.
export function connectStream(onMessage) {
  const es = new EventSource(`${BASE}/api/stream`)
  es.onmessage = (e) => {
    try {
      onMessage(JSON.parse(e.data))
    } catch (_) {
      /* ignore malformed frames */
    }
  }
  es.onerror = () => {
    // The browser auto-reconnects; nothing to do here.
  }
  return es
}
