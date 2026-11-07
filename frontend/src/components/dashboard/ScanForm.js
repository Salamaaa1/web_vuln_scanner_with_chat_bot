'use client'

import { useState } from 'react'

const EXAMPLES = ['192.168.1.50', '192.168.1.0/24', 'example.com', 'https://api.target.ma']

function detectType(value) {
  if (/^https?:\/\//i.test(value))                    return 'url'
  if (/^(\d{1,3}\.){3}\d{1,3}\/\d{1,2}$/.test(value)) return 'cidr'
  if (/^(\d{1,3}\.){3}\d{1,3}$/.test(value))           return 'ip'
  if (/^[a-z0-9][a-z0-9.-]+\.[a-z]{2,}$/i.test(value)) return 'domain'
  return null
}

const TYPE_COLORS = {
  ip:     { color: '#3DC98E', label: 'IP' },
  cidr:   { color: '#3D8EF0', label: 'Réseau' },
  domain: { color: '#A78BFA', label: 'Domaine' },
  url:    { color: '#F2A93B', label: 'URL' },
}

export default function ScanForm({ isRunning, scan, onStart, onStop, progress: progressProp, step }) {
  const [target, setTarget] = useState('')
  const detectedType = detectType(target.trim())

  const handleSubmit = () => {
    if (target.trim() && !isRunning) onStart(target.trim())
  }

  const progress = progressProp ?? scan?.percent ?? 0
  const stepLabel = step ?? scan?.step ?? ''

  return (
    <div style={{
      background: 'var(--bg-surface)',
      border: '1px solid var(--border)',
      borderRadius: 'var(--radius-lg)',
      padding: '20px',
      display: 'flex',
      flexDirection: 'column',
      gap: '14px',
    }}>
      <div style={{ fontSize: '11px', color: 'var(--text-dim)', fontFamily: 'var(--font-mono)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
        Cible
      </div>

      {/* Input row */}
      <div style={{ display: 'flex', gap: '10px' }}>
        <div style={{ flex: 1, position: 'relative' }}>
          <input
            value={target}
            onChange={e => setTarget(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleSubmit()}
            placeholder="IP, CIDR, domaine ou URL…"
            disabled={isRunning}
            style={{
              width: '100%',
              padding: '10px 14px 10px 40px',
              background: 'var(--bg-elevated)',
              border: `1px solid ${detectedType ? TYPE_COLORS[detectedType].color + '60' : 'var(--border)'}`,
              borderRadius: 'var(--radius-md)',
              color: 'var(--text-primary)',
              fontFamily: 'var(--font-mono)',
              fontSize: '13px',
              outline: 'none',
              transition: 'border-color 0.2s',
            }}
          />
          {/* Crosshair icon */}
          <svg style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', opacity: 0.4 }} width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true">
            <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="12" x2="16" y2="12"/>
            <circle cx="12" cy="12" r="1" fill="currentColor"/>
          </svg>

          {/* Type badge */}
          {detectedType && (
            <span style={{
              position: 'absolute', right: 10, top: '50%', transform: 'translateY(-50%)',
              fontSize: '10px', fontFamily: 'var(--font-mono)',
              padding: '2px 7px', borderRadius: 'var(--radius-sm)',
              background: TYPE_COLORS[detectedType].color + '20',
              color: TYPE_COLORS[detectedType].color,
              border: `1px solid ${TYPE_COLORS[detectedType].color}40`,
            }}>
              {TYPE_COLORS[detectedType].label}
            </span>
          )}
        </div>

        {isRunning ? (
          <button onClick={onStop} style={{
            padding: '10px 20px',
            background: 'var(--critical-bg)',
            border: '1px solid var(--critical)',
            borderRadius: 'var(--radius-md)',
            color: 'var(--critical)',
            fontWeight: 500,
            fontSize: '13px',
            display: 'flex', alignItems: 'center', gap: '6px',
          }}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><rect x="6" y="6" width="12" height="12" rx="1"/></svg>
            Arrêter
          </button>
        ) : (
          <button onClick={handleSubmit} disabled={!target.trim() || !detectedType} style={{
            padding: '10px 24px',
            background: target.trim() && detectedType ? 'var(--accent)' : 'var(--bg-elevated)',
            border: `1px solid ${target.trim() && detectedType ? 'var(--accent)' : 'var(--border)'}`,
            borderRadius: 'var(--radius-md)',
            color: target.trim() && detectedType ? 'white' : 'var(--text-dim)',
            fontWeight: 500,
            fontSize: '13px',
            display: 'flex', alignItems: 'center', gap: '6px',
            transition: 'all 0.2s',
          }}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
              <polygon points="5 3 19 12 5 21 5 3"/>
            </svg>
            Lancer
          </button>
        )}
      </div>

      {/* Examples */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        <span style={{ fontSize: '11px', color: 'var(--text-dim)' }}>Ex :</span>
        {EXAMPLES.map(ex => (
          <button key={ex} onClick={() => !isRunning && setTarget(ex)} style={{
            fontSize: '11px', fontFamily: 'var(--font-mono)',
            padding: '2px 8px',
            background: 'var(--bg-elevated)',
            border: '1px solid var(--border)',
            borderRadius: 'var(--radius-sm)',
            color: 'var(--text-secondary)',
            transition: 'border-color 0.15s',
          }}>{ex}</button>
        ))}
      </div>

      {/* Progress */}
      {isRunning && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', fontFamily: 'var(--font-mono)', color: 'var(--text-dim)' }}>
            <span>{stepLabel}</span>
            <span>{progress}%</span>
          </div>
          <div style={{ height: 3, background: 'var(--bg-elevated)', borderRadius: 2, overflow: 'hidden' }}>
            <div style={{
              height: '100%',
              width: `${progress}%`,
              background: 'var(--accent)',
              borderRadius: 2,
              transition: 'width 0.4s ease',
              boxShadow: '0 0 8px var(--accent)',
            }}/>
          </div>
        </div>
      )}
    </div>
  )
}
