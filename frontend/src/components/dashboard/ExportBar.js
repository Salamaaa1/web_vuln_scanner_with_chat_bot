'use client'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export default function ExportBar({ scanId, isRunning, findings }) {
  const handleFullReport = async () => {
    if (!scanId) return
    try {
      const res  = await fetch(`${API}/api/v1/scans/report/${scanId}/pdf`)
      const blob = await res.blob()
      const url  = URL.createObjectURL(blob)
      const a    = document.createElement('a')
      a.href     = url
      a.download = `report-${scanId}.pdf`
      a.click()
      URL.revokeObjectURL(url)
    } catch {
      window.open(`${API}/api/v1/scans/report/${scanId}/pdf`, '_blank')
    }
  }

  const handleExportLocal = () => {
    const data = {
      generated_at: new Date().toISOString(),
      scan_id: scanId,
      total: findings.length,
      findings,
    }
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
    const url  = URL.createObjectURL(blob)
    const a    = document.createElement('a')
    a.href     = url
    a.download = `scan-${scanId ?? 'export'}.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  const critical = findings.filter(f => f.severity === 'critical').length
  const high     = findings.filter(f => f.severity === 'high').length

  return (
    <div style={{
      background: 'var(--bg-surface)',
      border: '1px solid var(--border)',
      borderRadius: 'var(--radius-md)',
      padding: '14px 18px',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--text-dim)" strokeWidth="1.5" aria-hidden="true">
          <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/>
          <polyline points="14 2 14 8 20 8"/><line x1="12" y1="18" x2="12" y2="12"/>
          <line x1="9" y1="15" x2="12" y2="18"/><line x1="15" y1="15" x2="12" y2="18"/>
        </svg>
        <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
          {isRunning
            ? 'Rapport disponible à la fin du scan'
            : scanId
            ? `Scan terminé — ${findings.length} finding(s)`
            : 'Aucun scan effectué'}
        </span>

        {/* Résumé criticité */}
        {findings.length > 0 && (
          <div style={{ display: 'flex', gap: '8px' }}>
            {critical > 0 && (
              <span style={{ fontSize: '11px', fontFamily: 'var(--font-mono)', padding: '2px 8px', background: 'var(--critical-bg)', color: 'var(--critical)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--critical)40' }}>
                {critical} critique{critical > 1 ? 's' : ''}
              </span>
            )}
            {high > 0 && (
              <span style={{ fontSize: '11px', fontFamily: 'var(--font-mono)', padding: '2px 8px', background: 'var(--high-bg)', color: 'var(--high)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--high)40' }}>
                {high} haute{high > 1 ? 's' : ''}
              </span>
            )}
          </div>
        )}
      </div>

      <div style={{ display: 'flex', gap: '8px' }}>
        <button
          onClick={handleExportLocal}
          disabled={findings.length === 0}
          style={{
            fontSize: '12px', padding: '7px 16px',
            background: 'var(--bg-elevated)',
            border: '1px solid var(--border)',
            borderRadius: 'var(--radius-md)',
            color: findings.length > 0 ? 'var(--text-secondary)' : 'var(--text-dim)',
            display: 'flex', alignItems: 'center', gap: '6px',
          }}
        >
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
            <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>
          </svg>
          Exporter JSON
        </button>

        <button
          onClick={handleFullReport}
          disabled={!scanId || isRunning}
          style={{
            fontSize: '12px', padding: '7px 16px',
            background: scanId && !isRunning ? 'var(--accent)' : 'var(--bg-elevated)',
            border: `1px solid ${scanId && !isRunning ? 'var(--accent)' : 'var(--border)'}`,
            borderRadius: 'var(--radius-md)',
            color: scanId && !isRunning ? 'white' : 'var(--text-dim)',
            display: 'flex', alignItems: 'center', gap: '6px',
          }}
        >
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
            <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/>
          </svg>
          Rapport complet
        </button>
      </div>
    </div>
  )
}
