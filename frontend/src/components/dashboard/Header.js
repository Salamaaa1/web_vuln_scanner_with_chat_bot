'use client'

export default function Header({ isRunning }) {
  return (
    <header style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
          <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
          <path d="M9 12l2 2 4-4"/>
        </svg>
        <div>
          <div style={{ fontSize: '16px', fontWeight: 600, letterSpacing: '-0.02em', color: 'var(--text-primary)' }}>
            Security Scanner
          </div>
          <div style={{ fontSize: '11px', color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>
            Recon & Vulnerability Framework
          </div>
        </div>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        {/* Outil badges */}
        {['Nmap', 'Nuclei', 'Subfinder', 'Httpx'].map(tool => (
          <span key={tool} style={{
            fontSize: '10px',
            fontFamily: 'var(--font-mono)',
            padding: '3px 8px',
            background: 'var(--bg-elevated)',
            border: '1px solid var(--border)',
            borderRadius: 'var(--radius-sm)',
            color: 'var(--text-dim)',
          }}>{tool}</span>
        ))}

        {/* Indicateur statut */}
        <span style={{
          display: 'flex', alignItems: 'center', gap: '5px',
          fontSize: '11px', fontFamily: 'var(--font-mono)',
          padding: '4px 10px',
          background: isRunning ? 'rgba(61,201,142,0.1)' : 'var(--bg-elevated)',
          border: `1px solid ${isRunning ? 'var(--low)' : 'var(--border)'}`,
          borderRadius: 'var(--radius-sm)',
          color: isRunning ? 'var(--low)' : 'var(--text-dim)',
          marginLeft: '4px',
        }}>
          <span style={{
            width: 6, height: 6, borderRadius: '50%',
            background: isRunning ? 'var(--low)' : 'var(--text-dim)',
            animation: isRunning ? 'pulse 1.5s infinite' : 'none',
          }}/>
          {isRunning ? 'En cours' : 'En attente'}
        </span>
      </div>

      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.3; }
        }
      `}</style>
    </header>
  )
}
