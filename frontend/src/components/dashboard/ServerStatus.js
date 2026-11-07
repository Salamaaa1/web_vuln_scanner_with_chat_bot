'use client'

import { useEffect, useState } from 'react'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

// Pings the API on page load. If it isn't reachable yet (server starting or
// restarting), shows a short notice instead of letting requests fail silently,
// and hides itself as soon as the API answers.
export default function ServerStatus() {
  const [state, setState] = useState('checking') // checking | waking | online
  const [seconds, setSeconds] = useState(0)

  useEffect(() => {
    let cancelled = false
    let timer
    const started = Date.now()

    const ping = async () => {
      const ctrl = new AbortController()
      const abort = setTimeout(() => ctrl.abort(), 8000)
      try {
        const r = await fetch(`${API}/`, { signal: ctrl.signal, cache: 'no-store' })
        if (r.ok) {
          if (!cancelled) setState('online')
          return
        }
      } catch (_) {
        // not up yet
      } finally {
        clearTimeout(abort)
      }
      if (cancelled) return
      setState('waking')
      setSeconds(Math.round((Date.now() - started) / 1000))
      timer = setTimeout(ping, 4000)
    }

    ping()
    return () => { cancelled = true; clearTimeout(timer) }
  }, [])

  if (state !== 'waking') return null

  return (
    <div role="status" style={{
      display: 'flex', alignItems: 'center', gap: '10px',
      fontSize: '13px', padding: '10px 14px',
      background: 'rgba(240,180,60,0.08)',
      border: '1px solid rgba(240,180,60,0.35)',
      borderRadius: 'var(--radius-md)',
      color: 'var(--text-secondary)',
    }}>
      <span style={{
        width: '8px', height: '8px', borderRadius: '50%',
        background: 'rgb(240,180,60)', flexShrink: 0,
      }} />
      <span>
        Connexion au serveur d'analyse… (s'il vient de démarrer, cela peut prendre une minute)
        <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-dim)', marginLeft: '8px' }}>
          {seconds}s
        </span>
      </span>
    </div>
  )
}
