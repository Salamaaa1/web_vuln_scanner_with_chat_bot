'use client'

import { useEffect, useRef } from 'react'

const LEVEL_COLORS = {
  info:    'var(--log-info)',
  success: 'var(--log-success)',
  warn:    'var(--log-warn)',
  error:   'var(--log-error)',
}

const LEVEL_PREFIX = {
  info:    '→',
  success: '✓',
  warn:    '⚠',
  error:   '✗',
}

export default function LiveConsole({ logs }) {
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [logs])

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--text-dim)" strokeWidth="1.5" aria-hidden="true">
            <polyline points="4 17 10 11 4 5"/><line x1="12" y1="19" x2="20" y2="19"/>
          </svg>
          <span style={{ fontSize: '12px', fontWeight: 500, color: 'var(--text-secondary)' }}>Console</span>
          <span style={{ fontSize: '10px', fontFamily: 'var(--font-mono)', color: 'var(--text-dim)', padding: '1px 6px', background: 'var(--bg-elevated)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border)' }}>
            {logs.length} lignes
          </span>
        </div>
        <button
          onClick={() => navigator.clipboard?.writeText(logs.map(l => `[${l.ts}] ${l.message}`).join('\n'))}
          style={{ fontSize: '11px', color: 'var(--text-dim)', padding: '3px 8px', background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)' }}
        >
          Copier
        </button>
      </div>

      <div style={{
        background: 'var(--bg-surface)',
        border: '1px solid var(--border)',
        borderRadius: 'var(--radius-md)',
        padding: '14px',
        height: '320px',
        overflowY: 'auto',
        display: 'flex',
        flexDirection: 'column',
        gap: '3px',
      }}>
        {logs.length === 0 ? (
          <div style={{ color: 'var(--text-dim)', fontFamily: 'var(--font-mono)', fontSize: '12px', margin: 'auto', textAlign: 'center' }}>
            En attente d'un scan…
          </div>
        ) : (
          logs.map((log, i) => (
            <div key={i} style={{ display: 'flex', gap: '10px', fontFamily: 'var(--font-mono)', fontSize: '12px', lineHeight: '1.5' }}>
              <span style={{ color: 'var(--text-dim)', flexShrink: 0 }}>{log.ts}</span>
              <span style={{ color: LEVEL_COLORS[log.level] || 'var(--text-secondary)', flexShrink: 0 }}>
                {LEVEL_PREFIX[log.level] || '·'}
              </span>
              <span style={{ color: log.level === 'error' ? 'var(--critical)' : log.level === 'warn' ? 'var(--high)' : 'var(--text-secondary)', wordBreak: 'break-all' }}>
                {log.message}
              </span>
            </div>
          ))
        )}
        {/* Curseur clignotant si actif */}
        {logs.length > 0 && (
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: '12px', color: 'var(--text-dim)' }}>
            <span style={{ animation: 'blink 1s step-end infinite' }}>▌</span>
          </div>
        )}
        <div ref={bottomRef}/>
        <style>{`@keyframes blink { 0%,100%{opacity:1} 50%{opacity:0} }`}</style>
      </div>
    </div>
  )
}
