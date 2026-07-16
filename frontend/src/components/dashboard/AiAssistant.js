'use client'
import { useEffect, useState } from 'react'
import { useAi } from '@/hooks/useAi'

const SEV_COLORS = {
  critical: 'var(--critical)',
  high:     'var(--high)',
  medium:   'var(--medium)',
  low:      'var(--low)',
  info:     'var(--accent)',
}

function SevBadge({ severity }) {
  const s = (severity || 'info').toLowerCase()
  return (
    <span style={{
      fontSize: '10px', fontFamily: 'var(--font-mono)', textTransform: 'uppercase',
      padding: '2px 8px', borderRadius: 'var(--radius-sm)', letterSpacing: '0.05em',
      color: SEV_COLORS[s] || 'var(--text-dim)',
      border: `1px solid ${SEV_COLORS[s] || 'var(--border)'}`,
      whiteSpace: 'nowrap',
    }}>{s}</span>
  )
}

function Field({ label, color, children }) {
  return (
    <div>
      <div style={{
        fontSize: '10px', fontFamily: 'var(--font-mono)', color: color || 'var(--text-dim)',
        textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '3px',
      }}>{label}</div>
      <div style={{ fontSize: '13px', color: 'var(--text-secondary)', lineHeight: 1.55, whiteSpace: 'pre-wrap' }}>
        {children}
      </div>
    </div>
  )
}

export default function AiAssistant() {
  const {
    scans, vulns, status, loadingList,
    fetchStatus, fetchScans, loadVulns, loadConversation, explainOne, askQuestion,
  } = useAi()

  const [selectedScan, setSelectedScan] = useState('')
  const [openVuln, setOpenVuln]   = useState(null)  // title of the expanded vuln
  const [bilan, setBilan]         = useState(null)
  const [messages, setMessages]   = useState([])
  const [busy, setBusy]           = useState(false)
  const [question, setQuestion]   = useState('')
  const [asking, setAsking]       = useState(false)
  const [fromCache, setFromCache] = useState(false)

  useEffect(() => { fetchStatus(); fetchScans() }, [fetchStatus, fetchScans])

  const pickScan = async (id) => {
    setSelectedScan(id)
    setOpenVuln(null); setBilan(null); setMessages([])
    if (id) await loadVulns(id)
  }

  // Click a vulnerability -> load stored conversation, or analyse it on demand.
  const openVulnerability = async (v) => {
    if (openVuln === v.title) { setOpenVuln(null); return }
    setOpenVuln(v.title)
    setBilan(null); setMessages([]); setQuestion(''); setBusy(true); setFromCache(false)
    try {
      const convo = await loadConversation(selectedScan, v.title)
      if (convo.exists && convo.bilan) {
        setBilan(convo.bilan); setMessages(convo.messages || []); setFromCache(true)
      } else {
        const b = await explainOne(selectedScan, v)
        setBilan(b); setFromCache(!!b.cached)
      }
    } catch (e) {
      setBilan({ analysis: `Erreur : ${e.message}`, remediation: '' })
    }
    setBusy(false)
  }

  const submitQuestion = async (e) => {
    e.preventDefault()
    const q = question.trim()
    if (!q || asking) return
    setAsking(true)
    setMessages(m => [...m, { role: 'user', content: q }])
    setQuestion('')
    try {
      const res = await askQuestion(selectedScan, openVuln, q)
      setMessages(res.messages || [])
    } catch (err) {
      setMessages(m => [...m, { role: 'assistant', content: `Erreur : ${err.message}` }])
    }
    setAsking(false)
  }

  const configured = status && status.configured

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
        <span style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-primary)' }}>
          Assistant IA — Remédiation
        </span>
        {status && (
          <span style={{
            fontSize: '10px', fontFamily: 'var(--font-mono)', padding: '2px 8px',
            borderRadius: 'var(--radius-sm)', border: '1px solid var(--border)',
            color: configured ? 'var(--low)' : 'var(--critical)',
          }}>
            {configured ? `● ${status.model}` : '● IA non configurée'}
          </span>
        )}
      </div>

      {status && !configured && (
        <div style={{ fontSize: '12px', color: 'var(--critical)', fontFamily: 'var(--font-mono)' }}>
          Ajoutez NVIDIA_API_KEY dans le fichier .env pour activer l&apos;assistant.
        </div>
      )}

      {/* Scan picker */}
      <div style={{ display: 'flex', gap: '10px', alignItems: 'center', flexWrap: 'wrap' }}>
        <select
          value={selectedScan}
          onChange={e => pickScan(e.target.value)}
          style={{
            fontSize: '13px', padding: '8px 12px', minWidth: '280px',
            background: 'var(--bg-surface)', border: '1px solid var(--border)',
            borderRadius: 'var(--radius-md)', color: 'var(--text-primary)',
          }}
        >
          <option value="">Choisir un scan…</option>
          {scans.map(s => (
            <option key={s.target_id} value={s.target_id}>
              {s.target_value} ({s.target_type}) — {s.vuln_count} vuln. — {new Date(s.created_at).toLocaleString('fr-FR')}
            </option>
          ))}
        </select>
        {loadingList && <span style={{ fontSize: '12px', color: 'var(--text-dim)' }}>Chargement…</span>}
        {scans.length === 0 && (
          <span style={{ fontSize: '12px', color: 'var(--text-dim)' }}>
            Aucun scan avec vulnérabilités. Lancez d&apos;abord un scan.
          </span>
        )}
      </div>

      {vulns.length > 0 && (
        <div style={{ fontSize: '11px', color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>
          {vulns.length} vulnérabilité(s) unique(s) — cliquez-en une pour l&apos;analyser avec l&apos;IA
        </div>
      )}

      {/* Vulnerability list — click to analyse on demand */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
        {vulns.map((v, i) => {
          const isOpen = openVuln === v.title
          return (
            <div key={i} style={{
              background: 'var(--bg-surface)', border: `1px solid ${isOpen ? 'var(--accent)' : 'var(--border)'}`,
              borderRadius: 'var(--radius-md)', overflow: 'hidden',
            }}>
              <div
                onClick={() => configured && openVulnerability(v)}
                style={{
                  display: 'flex', alignItems: 'center', gap: '10px', padding: '12px 14px',
                  cursor: configured ? 'pointer' : 'default',
                }}
              >
                <SevBadge severity={v.severity} />
                <span style={{ fontSize: '13px', fontWeight: 500, color: 'var(--text-primary)', flex: 1 }}>
                  {v.title}
                </span>
                {v.count > 1 && (
                  <span style={{ fontSize: '10px', fontFamily: 'var(--font-mono)', color: 'var(--text-dim)' }}>×{v.count}</span>
                )}
                <span style={{ fontSize: '11px', color: 'var(--accent)', fontFamily: 'var(--font-mono)' }}>
                  {isOpen ? '▾' : '▸'}
                </span>
              </div>

              {isOpen && (
                <div style={{ padding: '0 14px 14px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  {busy && (
                    <div style={{ fontSize: '12px', color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>
                      L&apos;IA analyse cette vulnérabilité…
                    </div>
                  )}

                  {bilan && !busy && (
                    <>
                      {fromCache && (
                        <div style={{ fontSize: '10px', fontFamily: 'var(--font-mono)', color: 'var(--low)' }}>
                          ● analyse enregistrée (aucun token consommé)
                        </div>
                      )}
                      <Field label="Analyse">{bilan.analysis}</Field>
                      <Field label="Remédiation" color="var(--low)">{bilan.remediation}</Field>

                      {/* Follow-up Q&A */}
                      <div style={{ borderTop: '1px solid var(--border)', paddingTop: '10px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                        {messages.map((m, mi) => (
                          <div key={mi} style={{
                            alignSelf: m.role === 'user' ? 'flex-end' : 'flex-start',
                            maxWidth: '85%',
                            background: m.role === 'user' ? 'var(--bg-elevated)' : 'transparent',
                            border: `1px solid ${m.role === 'user' ? 'var(--border)' : 'transparent'}`,
                            borderRadius: 'var(--radius-md)', padding: m.role === 'user' ? '6px 10px' : '0',
                            fontSize: '12.5px', color: 'var(--text-secondary)',
                            lineHeight: 1.5, whiteSpace: 'pre-wrap',
                          }}>
                            {m.content}
                          </div>
                        ))}
                        {asking && (
                          <div style={{ fontSize: '11px', color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>
                            L&apos;IA réfléchit…
                          </div>
                        )}
                        <form onSubmit={submitQuestion} style={{ display: 'flex', gap: '8px' }}>
                          <input
                            value={question}
                            onChange={e => setQuestion(e.target.value)}
                            placeholder="Poser une question sur cette vulnérabilité…"
                            style={{
                              flex: 1, fontSize: '12.5px', padding: '8px 10px',
                              background: 'var(--bg-elevated)', border: '1px solid var(--border)',
                              borderRadius: 'var(--radius-md)', color: 'var(--text-primary)',
                            }}
                          />
                          <button type="submit" disabled={asking || !question.trim()} style={{
                            fontSize: '12.5px', padding: '8px 14px',
                            background: question.trim() && !asking ? 'var(--accent)' : 'var(--bg-elevated)',
                            border: '1px solid var(--border)', borderRadius: 'var(--radius-md)',
                            color: question.trim() && !asking ? '#fff' : 'var(--text-dim)',
                            cursor: question.trim() && !asking ? 'pointer' : 'default',
                          }}>Envoyer</button>
                        </form>
                      </div>
                    </>
                  )}
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
