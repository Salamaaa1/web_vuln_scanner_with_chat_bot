'use client'
import { useEffect, useState } from 'react'
import { useLogs } from '@/hooks/useLogs'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

function fmtDate(iso) {
  try {
    return new Date(iso).toLocaleString('fr-FR')
  } catch {
    return iso
  }
}

function fmtDuration(ms) {
  if (ms == null) return '—'
  if (ms < 1000) return `${ms} ms`
  return `${(ms / 1000).toFixed(1)} s`
}

const TYPE_COLORS = {
  URL:  'var(--accent)',
  DNS:  'var(--medium)',
  IP:   'var(--high)',
  CIDR: 'var(--high)',
}

export default function LogsView() {
  const { logs, loading, error, fetchLogs } = useLogs()
  const [detail, setDetail] = useState(null)

  useEffect(() => { fetchLogs() }, [fetchLogs])

  const downloadReport = async (targetId, value) => {
    const res  = await fetch(`${API}/api/v1/scans/report/${targetId}/pdf`)
    const blob = await res.blob()
    const url  = URL.createObjectURL(blob)
    const a    = document.createElement('a')
    a.href     = url
    a.download = `report-${(value || 'scan').replace(/[^a-z0-9.-]/gi, '_')}.pdf`
    a.click()
    URL.revokeObjectURL(url)
  }

  const viewDetail = async (targetId) => {
    const res  = await fetch(`${API}/api/v1/scans/report/${targetId}`)
    const data = await res.json()
    setDetail(data)
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <span style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-primary)' }}>
            Historique des scans
          </span>
          <span style={{ fontSize: '10px', fontFamily: 'var(--font-mono)', color: 'var(--text-dim)', padding: '2px 8px', background: 'var(--bg-elevated)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border)' }}>
            {logs.length}
          </span>
        </div>
        <button onClick={fetchLogs} style={{
          fontSize: '12px', padding: '7px 16px',
          background: 'var(--bg-elevated)', border: '1px solid var(--border)',
          borderRadius: 'var(--radius-md)', color: 'var(--text-secondary)',
        }}>
          {loading ? 'Chargement…' : 'Rafraîchir'}
        </button>
      </div>

      {error && (
        <div style={{ fontSize: '12px', color: 'var(--critical)', fontFamily: 'var(--font-mono)' }}>
          Erreur : {error}
        </div>
      )}

      <div style={{
        background: 'var(--bg-surface)', border: '1px solid var(--border)',
        borderRadius: 'var(--radius-md)', overflow: 'hidden',
      }}>
        {/* Header */}
        <div style={{
          display: 'grid', gridTemplateColumns: 'minmax(170px,1.6fr) 60px 70px 60px 55px 55px 80px 60px 150px',
          gap: '8px', padding: '10px 14px',
          background: 'var(--bg-elevated)', borderBottom: '1px solid var(--border)',
          fontSize: '10px', fontFamily: 'var(--font-mono)', color: 'var(--text-dim)',
          textTransform: 'uppercase', letterSpacing: '0.06em',
        }}>
          <span>Cible</span><span>Type</span><span>Sous-dom.</span><span>Endpts</span>
          <span>Ports</span><span>Vulns</span><span>Durée</span><span>Cache</span><span>Date</span>
        </div>

        {logs.length === 0 ? (
          <div style={{ color: 'var(--text-dim)', fontFamily: 'var(--font-mono)', fontSize: '12px', padding: '40px', textAlign: 'center' }}>
            {loading ? 'Chargement…' : 'Aucun scan enregistré'}
          </div>
        ) : (
          <div style={{ maxHeight: '460px', overflowY: 'auto' }}>
            {logs.map((log) => (
              <div key={log.id} style={{
                display: 'grid', gridTemplateColumns: 'minmax(170px,1.6fr) 60px 70px 60px 55px 55px 80px 60px 150px',
                gap: '8px', padding: '10px 14px', alignItems: 'center',
                borderBottom: '1px solid var(--border)', cursor: 'pointer',
                fontSize: '12px', transition: 'background 0.15s',
              }}
              onMouseEnter={e => e.currentTarget.style.background = 'var(--bg-elevated)'}
              onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
              onClick={() => viewDetail(log.target_id)}
              >
                <span style={{ color: 'var(--text-primary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {log.target_value}
                </span>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', color: TYPE_COLORS[log.target_type] || 'var(--text-dim)' }}>
                  {log.target_type}
                </span>
                <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)' }}>{log.subdomains}</span>
                <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--low)' }}>{log.endpoints}</span>
                <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--high)' }}>{log.ports}</span>
                <span style={{ fontFamily: 'var(--font-mono)', color: log.findings > 0 ? 'var(--critical)' : 'var(--text-secondary)' }}>{log.findings}</span>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', color: 'var(--text-dim)' }}>{fmtDuration(log.duration_ms)}</span>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', color: log.cached ? 'var(--low)' : 'var(--text-dim)' }}>
                  {log.cached ? 'HIT' : 'live'}
                </span>
                <span style={{ display: 'flex', alignItems: 'center', gap: '6px', justifyContent: 'space-between' }}>
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', color: 'var(--text-dim)' }}>
                    {fmtDate(log.created_at)}
                  </span>
                  <button
                    title="Télécharger le rapport"
                    onClick={(e) => { e.stopPropagation(); downloadReport(log.target_id, log.target_value) }}
                    style={{ background: 'none', border: 'none', color: 'var(--accent)', cursor: 'pointer', padding: 0 }}
                  >
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                      <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>
                    </svg>
                  </button>
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      {detail && <DetailModal report={detail} onClose={() => setDetail(null)} />}
    </div>
  )
}

function Section({ title, count, children }) {
  return (
    <div style={{ marginBottom: '16px' }}>
      <div style={{ fontSize: '11px', fontFamily: 'var(--font-mono)', color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '8px' }}>
        {title} {count != null && <span style={{ color: 'var(--text-secondary)' }}>({count})</span>}
      </div>
      {children}
    </div>
  )
}

function DetailModal({ report, onClose }) {
  const s = report.summary || {}
  return (
    <div
      onClick={onClose}
      style={{
        position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)',
        display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100, padding: '24px',
      }}
    >
      <div
        onClick={e => e.stopPropagation()}
        style={{
          background: 'var(--bg-surface)', border: '1px solid var(--border)',
          borderRadius: 'var(--radius-md)', maxWidth: '760px', width: '100%',
          maxHeight: '82vh', overflowY: 'auto', padding: '24px',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '18px' }}>
          <div>
            <div style={{ fontSize: '16px', fontWeight: 600, color: 'var(--text-primary)' }}>
              {report.target?.value}
            </div>
            <div style={{ fontSize: '11px', fontFamily: 'var(--font-mono)', color: 'var(--text-dim)' }}>
              {report.target?.type} · généré {fmtDate(report.generated_at)}
            </div>
          </div>
          <button onClick={onClose} style={{ background: 'none', border: 'none', color: 'var(--text-dim)', fontSize: '20px', cursor: 'pointer', lineHeight: 1 }}>×</button>
        </div>

        {/* Summary chips */}
        <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap', marginBottom: '20px' }}>
          {[
            ['Sous-domaines', s.subdomains],
            ['Endpoints', s.endpoints],
            ['Ports', s.ports],
            ['Vulnérabilités', s.vulnerabilities],
          ].map(([label, val]) => (
            <div key={label} style={{ flex: 1, minWidth: '110px', background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)', padding: '10px 14px' }}>
              <div style={{ fontSize: '10px', fontFamily: 'var(--font-mono)', color: 'var(--text-dim)', textTransform: 'uppercase' }}>{label}</div>
              <div style={{ fontSize: '20px', fontFamily: 'var(--font-mono)', fontWeight: 600, color: 'var(--text-primary)' }}>{val ?? 0}</div>
            </div>
          ))}
        </div>

        {report.open_ports?.length > 0 && (
          <Section title="Ports ouverts" count={report.open_ports.length}>
            {report.open_ports.map((p, i) => (
              <div key={i} style={{ fontSize: '12px', fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)', padding: '3px 0' }}>
                <span style={{ color: 'var(--high)' }}>{p.port}/{p.protocol}</span> — {p.service || '?'} {p.product} {p.version}
              </div>
            ))}
          </Section>
        )}

        {report.live_endpoints?.length > 0 && (
          <Section title="Endpoints actifs" count={report.live_endpoints.length}>
            {report.live_endpoints.map((e, i) => (
              <div key={i} style={{ fontSize: '12px', fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)', padding: '3px 0' }}>
                <span style={{ color: 'var(--low)' }}>{e.status_code}</span> {e.url} {e.title ? `— ${e.title}` : ''} {e.tech?.length ? `[${e.tech.join(', ')}]` : ''}
              </div>
            ))}
          </Section>
        )}

        {report.subdomains?.length > 0 && (
          <Section title="Sous-domaines" count={report.subdomains.length}>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
              {report.subdomains.map((d, i) => (
                <span key={i} style={{ fontSize: '11px', fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)', background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)', padding: '2px 8px' }}>{d}</span>
              ))}
            </div>
          </Section>
        )}

        {report.discovered_resources?.length > 0 && (
          <Section title="Ressources découvertes" count={report.discovered_resources.length}>
            {report.discovered_resources.slice(0, 50).map((r, i) => (
              <div key={i} style={{ fontSize: '12px', fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)', padding: '2px 0' }}>
                <span style={{ color: 'var(--low)' }}>{r.status_code}</span> {r.url}
              </div>
            ))}
          </Section>
        )}

        {report.vulnerabilities?.length > 0 ? (
          <Section title="Vulnérabilités" count={report.vulnerabilities.length}>
            {report.vulnerabilities.map((v, i) => (
              <div key={i} style={{ fontSize: '12px', color: 'var(--text-secondary)', padding: '4px 0', borderBottom: '1px solid var(--border)' }}>
                <span style={{ color: 'var(--critical)', fontFamily: 'var(--font-mono)', fontSize: '10px', textTransform: 'uppercase' }}>{v.severity}</span> — {v.title}
              </div>
            ))}
          </Section>
        ) : (
          <div style={{ fontSize: '12px', color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>
            Aucune vulnérabilité détectée.
          </div>
        )}
      </div>
    </div>
  )
}
