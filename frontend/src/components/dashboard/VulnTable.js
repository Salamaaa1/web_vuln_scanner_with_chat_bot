'use client'

const SEVERITY = {
  critical: { color: 'var(--critical)', bg: 'var(--critical-bg)', label: 'Critique' },
  high:     { color: 'var(--high)',     bg: 'var(--high-bg)',     label: 'Haute'    },
  medium:   { color: 'var(--medium)',   bg: 'var(--medium-bg)',   label: 'Moyenne'  },
  low:      { color: 'var(--low)',      bg: 'var(--low-bg)',      label: 'Basse'    },
  info:     { color: 'var(--info)',     bg: 'var(--info-bg)',     label: 'Info'     },
}

const FILTERS = ['all', 'critical', 'high', 'medium', 'low']

function SeverityBadge({ severity }) {
  const s = SEVERITY[severity] || SEVERITY.info
  return (
    <span style={{
      fontSize: '10px', fontWeight: 500, fontFamily: 'var(--font-mono)',
      padding: '2px 8px', borderRadius: 'var(--radius-sm)',
      background: s.bg, color: s.color,
      border: `1px solid ${s.color}40`,
      whiteSpace: 'nowrap',
    }}>{s.label}</span>
  )
}

export default function VulnTable({ findings, filter, onFilter, total }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--text-dim)" strokeWidth="1.5" aria-hidden="true">
            <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/>
            <line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>
          </svg>
          <span style={{ fontSize: '12px', fontWeight: 500, color: 'var(--text-secondary)' }}>Vulnérabilités</span>
          <span style={{ fontSize: '10px', fontFamily: 'var(--font-mono)', color: 'var(--text-dim)', padding: '1px 6px', background: 'var(--bg-elevated)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border)' }}>
            {total}
          </span>
        </div>

        {/* Filtres */}
        <div style={{ display: 'flex', gap: '4px' }}>
          {FILTERS.map(f => (
            <button key={f} onClick={() => onFilter(f)} style={{
              fontSize: '10px', fontFamily: 'var(--font-mono)',
              padding: '3px 8px',
              background: filter === f ? 'var(--accent)' : 'var(--bg-elevated)',
              border: `1px solid ${filter === f ? 'var(--accent)' : 'var(--border)'}`,
              borderRadius: 'var(--radius-sm)',
              color: filter === f ? 'white' : 'var(--text-dim)',
              textTransform: 'capitalize',
            }}>
              {f === 'all' ? 'Toutes' : SEVERITY[f]?.label ?? f}
            </button>
          ))}
        </div>
      </div>

      <div style={{
        background: 'var(--bg-surface)',
        border: '1px solid var(--border)',
        borderRadius: 'var(--radius-md)',
        height: '320px',
        overflowY: 'auto',
        display: 'flex',
        flexDirection: 'column',
      }}>
        {/* Header */}
        <div style={{
          display: 'grid', gridTemplateColumns: '1fr 90px 70px 70px',
          gap: '8px', padding: '8px 14px',
          background: 'var(--bg-elevated)',
          borderBottom: '1px solid var(--border)',
          fontSize: '10px', fontFamily: 'var(--font-mono)',
          color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '0.06em',
          position: 'sticky', top: 0,
        }}>
          <span>Titre</span><span>Cible</span><span>Outil</span><span>Sévérité</span>
        </div>

        {findings.length === 0 ? (
          <div style={{ color: 'var(--text-dim)', fontFamily: 'var(--font-mono)', fontSize: '12px', margin: 'auto', textAlign: 'center' }}>
            Aucune vulnérabilité détectée
          </div>
        ) : (
          findings.map((f, i) => (
            <div key={f.id ?? i} style={{
              display: 'grid', gridTemplateColumns: '1fr 90px 70px 70px',
              gap: '8px', padding: '10px 14px',
              borderBottom: '1px solid var(--border)',
              alignItems: 'start',
              transition: 'background 0.15s',
            }}
            onMouseEnter={e => e.currentTarget.style.background = 'var(--bg-elevated)'}
            onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
            >
              <div>
                <div style={{ fontSize: '12px', fontWeight: 500, color: 'var(--text-primary)', marginBottom: '2px' }}>
                  {f.title}
                </div>
                {f.description && (
                  <div style={{ fontSize: '11px', color: 'var(--text-dim)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    {f.description}
                  </div>
                )}
              </div>
              <span style={{ fontSize: '10px', fontFamily: 'var(--font-mono)', color: 'var(--text-dim)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', paddingTop: 2 }}>
                {f.target?.replace(/^https?:\/\//, '') ?? '—'}
              </span>
              <span style={{ fontSize: '10px', fontFamily: 'var(--font-mono)', color: 'var(--text-dim)', paddingTop: 2 }}>
                {f.tool}
              </span>
              <div style={{ paddingTop: 1 }}>
                <SeverityBadge severity={f.severity} />
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
