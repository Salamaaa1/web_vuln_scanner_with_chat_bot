'use client'

import { useState, useCallback } from 'react'
import Header       from '@/components/dashboard/Header'
import ServerStatus from '@/components/dashboard/ServerStatus'
import ScanForm     from '@/components/dashboard/ScanForm'
import MetricsBar   from '@/components/dashboard/MetricsBar'
import LiveConsole  from '@/components/dashboard/LiveConsole'
import VulnTable    from '@/components/dashboard/VulnTable'
import ExportBar    from '@/components/dashboard/ExportBar'
import LogsView     from '@/components/dashboard/LogsView'
import AiAssistant  from '@/components/dashboard/AiAssistant'
import { useScanner } from '@/hooks/useScanner'

function Tabs({ active, onChange }) {
  const tabs = [
    ['scanner', 'Scanner'],
    ['logs',    'Logs'],
    ['ai',      'Assistant IA'],
  ]
  return (
    <div style={{ display: 'flex', gap: '4px', borderBottom: '1px solid var(--border)' }}>
      {tabs.map(([id, label]) => (
        <button key={id} onClick={() => onChange(id)} style={{
          fontSize: '13px', fontWeight: 500, padding: '10px 18px',
          background: 'none', border: 'none',
          borderBottom: `2px solid ${active === id ? 'var(--accent)' : 'transparent'}`,
          color: active === id ? 'var(--text-primary)' : 'var(--text-dim)',
          cursor: 'pointer', marginBottom: '-1px',
        }}>
          {label}
        </button>
      ))}
    </div>
  )
}

function CacheModal({ info, onReuse, onRescan, onCancel }) {
  return (
    <div onClick={onCancel} style={{
      position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)',
      display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 200, padding: '24px',
    }}>
      <div onClick={e => e.stopPropagation()} style={{
        background: 'var(--bg-surface)', border: '1px solid var(--border)',
        borderRadius: 'var(--radius-md)', padding: '22px', maxWidth: '460px', width: '100%',
        display: 'flex', flexDirection: 'column', gap: '14px',
      }}>
        <div style={{ fontSize: '15px', fontWeight: 600, color: 'var(--text-primary)' }}>
          Résultat déjà en cache
        </div>
        <div style={{ fontSize: '13px', color: 'var(--text-secondary)', lineHeight: 1.55 }}>
          Un scan de <b style={{ color: 'var(--text-primary)' }}>{info.target}</b> existe déjà en cache
          {info.last_findings != null && <> ({info.last_findings} vulnérabilité(s))</>}
          {info.last_scan_at && <> — {new Date(info.last_scan_at).toLocaleString('fr-FR')}</>}.
          <br />
          Voulez-vous réutiliser ce résultat (instantané) ou relancer un scan complet ?
        </div>
        {info.ttl > 0 && (
          <div style={{ fontSize: '11px', fontFamily: 'var(--font-mono)', color: 'var(--text-dim)' }}>
            Cache valide encore {Math.round(info.ttl / 60)} min
          </div>
        )}
        <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end', flexWrap: 'wrap' }}>
          <button onClick={onCancel} style={{
            fontSize: '13px', padding: '8px 14px', background: 'none',
            border: '1px solid var(--border)', borderRadius: 'var(--radius-md)', color: 'var(--text-dim)',
          }}>Annuler</button>
          <button onClick={onRescan} style={{
            fontSize: '13px', padding: '8px 14px', background: 'var(--bg-elevated)',
            border: '1px solid var(--border)', borderRadius: 'var(--radius-md)', color: 'var(--text-primary)',
          }}>Relancer le scan</button>
          <button onClick={onReuse} style={{
            fontSize: '13px', padding: '8px 14px', background: 'var(--accent)',
            border: '1px solid var(--accent)', borderRadius: 'var(--radius-md)', color: '#fff', fontWeight: 500,
          }}>Utiliser le cache</button>
        </div>
      </div>
    </div>
  )
}

export default function Home() {
  const [severityFilter, setSeverityFilter] = useState('all')
  const [tab, setTab] = useState('scanner')

  const {
    scan,
    logs,
    findings,
    metrics,
    isRunning,
    startScan,
    stopScan,
    pendingCache,
    resolveCache,
    dismissCache,
  } = useScanner()

  const filteredFindings = severityFilter === 'all'
    ? findings
    : findings.filter(f => f.severity === severityFilter)

  return (
    <main style={{
      minHeight: '100vh',
      padding: '24px',
      maxWidth: '1280px',
      margin: '0 auto',
      display: 'flex',
      flexDirection: 'column',
      gap: '20px',
    }}>
      <Header isRunning={isRunning} />

      <ServerStatus />

      <Tabs active={tab} onChange={setTab} />

      {tab === 'scanner' ? (
        <>
          <ScanForm
            isRunning={isRunning}
            scan={scan}
            onStart={startScan}
            onStop={stopScan}
          />

          <MetricsBar metrics={metrics} />

          <div style={{
            display: 'grid',
            gridTemplateColumns: '1fr 1fr',
            gap: '20px',
          }}>
            <LiveConsole logs={logs} />
            <VulnTable
              findings={filteredFindings}
              filter={severityFilter}
              onFilter={setSeverityFilter}
              total={findings.length}
            />
          </div>

          <ExportBar scanId={scan?.id} isRunning={isRunning} findings={findings} />
        </>
      ) : tab === 'logs' ? (
        <LogsView />
      ) : (
        <AiAssistant />
      )}

      {pendingCache && (
        <CacheModal
          info={pendingCache}
          onReuse={() => resolveCache(false)}
          onRescan={() => resolveCache(true)}
          onCancel={dismissCache}
        />
      )}
    </main>
  )
}
