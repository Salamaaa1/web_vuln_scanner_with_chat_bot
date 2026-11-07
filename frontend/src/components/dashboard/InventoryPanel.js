'use client'

import { useMemo, useState } from 'react'

// What the scan discovered besides vulnerabilities: live hosts, crawled
// endpoints, brute-forced resources, open ports and subdomains. Filled live
// during the scan, then from the final report.

const TABS = [
  { id: 'endpoints',  label: 'Endpoints' },
  { id: 'hosts',      label: 'Hôtes' },
  { id: 'resources',  label: 'Ressources' },
  { id: 'ports',      label: 'Ports' },
  { id: 'subdomains', label: 'Sous-domaines' },
]

const EMPTY = {
  endpoints:  'Aucun endpoint découvert pour l’instant.',
  hosts:      'Aucun hôte web actif détecté pour l’instant.',
  resources:  'Aucune ressource cachée découverte pour l’instant.',
  ports:      'Aucun port ouvert détecté pour l’instant.',
  subdomains: 'Aucun sous-domaine (uniquement pour les cibles de type domaine).',
}

function statusColor(code) {
  const c = Number(code)
  if (c >= 200 && c < 300) return 'var(--low)'
  if (c >= 300 && c < 400) return 'var(--medium)'
  if (c >= 400 && c < 500) return 'var(--high)'
  if (c >= 500)            return 'var(--critical)'
  return 'var(--text-dim)'
}

function Pill({ children, color = 'var(--text-dim)', width }) {
  return (
    <span style={{
      display: 'inline-block', minWidth: width, textAlign: 'center',
      fontSize: '10px', fontFamily: 'var(--font-mono)', padding: '1px 6px',
      borderRadius: 'var(--radius-sm)', border: `1px solid ${color}55`, color,
      background: 'var(--bg-elevated)', whiteSpace: 'nowrap',
    }}>{children}</span>
  )
}

function rowText(tab, item) {
  if (tab === 'ports') return `${item.port} ${item.protocol} ${item.service} ${item.product} ${item.version}`
  if (tab === 'subdomains') return String(item)
  return `${item.url ?? ''} ${item.title ?? ''} ${item.method ?? ''} ${(item.tech ?? []).join(' ')}`
}

function Row({ tab, item }) {
  const mono = { fontFamily: 'var(--font-mono)', fontSize: '11.5px', color: 'var(--text-primary)', wordBreak: 'break-all' }
  const sub  = { fontSize: '11px', color: 'var(--text-dim)' }

  if (tab === 'ports') {
    return (<>
      <Pill color="var(--high)" width="64px">{item.port}/{item.protocol}</Pill>
      <span style={mono}>{item.service || '—'}</span>
      <span style={sub}>{[item.product, item.version].filter(Boolean).join(' ') || ''}</span>
    </>)
  }
  if (tab === 'subdomains') {
    return <span style={mono}>{item}</span>
  }
  if (tab === 'endpoints') {
    return (<>
      <Pill color={item.method === 'GET' ? 'var(--text-dim)' : 'var(--medium)'} width="44px">{item.method}</Pill>
      <a href={item.url} target="_blank" rel="noreferrer" style={{ ...mono, textDecoration: 'none' }}>{item.url}</a>
      {item.has_params && <Pill color="var(--accent)">params</Pill>}
    </>)
  }
  // hosts / resources
  return (<>
    <Pill color={statusColor(item.status_code)} width="36px">{item.status_code ?? '—'}</Pill>
    <a href={item.url} target="_blank" rel="noreferrer" style={{ ...mono, textDecoration: 'none' }}>{item.url}</a>
    {tab === 'hosts' && (
      <span style={sub}>
        {[item.title, item.webserver, ...(item.tech ?? [])].filter(Boolean).join(' · ')}
      </span>
    )}
  </>)
}

export default function InventoryPanel({ inventory, isRunning }) {
  const [tab, setTab] = useState('endpoints')
  const [query, setQuery] = useState('')

  const inv = inventory ?? {}
  const items = inv[tab] ?? []
  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    if (!q) return items
    return items.filter(it => rowText(tab, it).toLowerCase().includes(q))
  }, [items, query, tab])

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '12px', flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--text-dim)" strokeWidth="1.5" aria-hidden="true">
            <circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/>
            <path d="M12 2a15.3 15.3 0 014 10 15.3 15.3 0 01-4 10 15.3 15.3 0 01-4-10 15.3 15.3 0 014-10z"/>
          </svg>
          <span style={{ fontSize: '12px', fontWeight: 500, color: 'var(--text-secondary)' }}>Inventaire</span>
          {isRunning && <span style={{ fontSize: '10px', fontFamily: 'var(--font-mono)', color: 'var(--text-dim)' }}>mise à jour en direct…</span>}
        </div>

        <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
          {TABS.map(t => {
            const active = tab === t.id
            return (
              <button key={t.id} onClick={() => { setTab(t.id); setQuery('') }} style={{
                fontSize: '10px', fontFamily: 'var(--font-mono)', padding: '3px 8px',
                background: active ? 'var(--accent)' : 'var(--bg-elevated)',
                border: `1px solid ${active ? 'var(--accent)' : 'var(--border)'}`,
                borderRadius: 'var(--radius-sm)', color: active ? 'white' : 'var(--text-dim)',
              }}>
                {t.label} <span style={{ opacity: 0.8 }}>{(inv[t.id] ?? []).length}</span>
              </button>
            )
          })}
        </div>
      </div>

      <div style={{
        background: 'var(--bg-surface)', border: '1px solid var(--border)',
        borderRadius: 'var(--radius-md)', overflow: 'hidden',
      }}>
        <div style={{ padding: '8px 12px', borderBottom: '1px solid var(--border)', background: 'var(--bg-elevated)' }}>
          <input
            value={query}
            onChange={e => setQuery(e.target.value)}
            placeholder="Filtrer…"
            aria-label="Filtrer la liste"
            style={{
              width: '100%', background: 'transparent', border: 'none', outline: 'none',
              color: 'var(--text-primary)', fontFamily: 'var(--font-mono)', fontSize: '12px',
            }}
          />
        </div>

        <div style={{ maxHeight: '340px', overflowY: 'auto' }}>
          {filtered.length === 0 ? (
            <div style={{ padding: '28px', textAlign: 'center', fontSize: '12px', color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>
              {items.length === 0 ? EMPTY[tab] : 'Aucun résultat pour ce filtre.'}
            </div>
          ) : filtered.map((item, i) => (
            <div key={i} style={{
              display: 'flex', alignItems: 'center', gap: '10px', padding: '7px 12px',
              borderBottom: '1px solid var(--border)',
              background: i % 2 ? 'transparent' : 'rgba(255,255,255,0.01)',
            }}>
              <Row tab={tab} item={item} />
            </div>
          ))}
        </div>

        {items.length > 0 && (
          <div style={{ padding: '6px 12px', borderTop: '1px solid var(--border)', fontSize: '10px', fontFamily: 'var(--font-mono)', color: 'var(--text-dim)' }}>
            {filtered.length} / {items.length} élément(s)
          </div>
        )}
      </div>
    </div>
  )
}
