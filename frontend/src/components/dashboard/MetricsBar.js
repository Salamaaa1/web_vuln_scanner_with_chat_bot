'use client'

function Metric({ label, value, color }) {
  return (
    <div style={{
      background: 'var(--bg-surface)',
      border: '1px solid var(--border)',
      borderRadius: 'var(--radius-md)',
      padding: '14px 18px',
      display: 'flex',
      flexDirection: 'column',
      gap: '4px',
      flex: 1,
    }}>
      <div style={{ fontSize: '11px', color: 'var(--text-dim)', fontFamily: 'var(--font-mono)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
        {label}
      </div>
      <div style={{ fontSize: '26px', fontWeight: 600, color: color || 'var(--text-primary)', fontFamily: 'var(--font-mono)', letterSpacing: '-0.02em' }}>
        {value}
      </div>
    </div>
  )
}

export default function MetricsBar({ metrics }) {
  return (
    <div style={{ display: 'flex', gap: '12px' }}>
      <Metric label="Sous-domaines"    value={metrics.subdomains} />
      <Metric label="Endpoints actifs" value={metrics.endpoints}  color="var(--low)" />
      <Metric label="Vulnérabilités"   value={metrics.findings}   color={metrics.findings > 0 ? 'var(--critical)' : 'var(--text-primary)'} />
      <Metric label="Ports ouverts"    value={metrics.ports}      color="var(--high)" />
    </div>
  )
}
