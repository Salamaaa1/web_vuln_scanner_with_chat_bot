'use client'
import { useState, useCallback } from 'react'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export function useAi() {
  const [scans, setScans]     = useState([])
  const [vulns, setVulns]     = useState([])   // [{title, severity, count, description}]
  const [status, setStatus]   = useState(null) // {configured, model}
  const [loadingList, setLoadingList] = useState(false)

  const fetchStatus = useCallback(async () => {
    try {
      const r = await fetch(`${API}/api/v1/ai/status`)
      setStatus(await r.json())
    } catch { setStatus({ configured: false }) }
  }, [])

  const fetchScans = useCallback(async () => {
    try {
      const r = await fetch(`${API}/api/v1/ai/scans`)
      const d = await r.json()
      setScans(d.scans ?? [])
    } catch { setScans([]) }
  }, [])

  // Just list the vulnerabilities — NO LLM calls (cheap).
  const loadVulns = useCallback(async (targetId) => {
    setLoadingList(true)
    setVulns([])
    try {
      const r = await fetch(`${API}/api/v1/ai/scan/${targetId}/vulnerabilities`)
      const d = await r.json()
      setVulns(d.vulnerabilities ?? [])
    } catch { setVulns([]) }
    setLoadingList(false)
  }, [])

  // Stored bilan + Q&A history for one vuln (no LLM call).
  const loadConversation = useCallback(async (targetId, title) => {
    const r = await fetch(`${API}/api/v1/ai/conversation/${targetId}?title=${encodeURIComponent(title)}`)
    return await r.json()
  }, [])

  // Analyse ONE vulnerability on demand (served from Mongo if already done).
  const explainOne = useCallback(async (targetId, vuln) => {
    const r = await fetch(`${API}/api/v1/ai/explain`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        target_id: targetId,
        title: vuln.title,
        description: vuln.description || '',
        severity: vuln.severity || '',
      }),
    })
    if (!r.ok) throw new Error(`explain failed (${r.status})`)
    return await r.json()
  }, [])

  // Follow-up question about one vulnerability; history is persisted server-side.
  const askQuestion = useCallback(async (targetId, title, question) => {
    const r = await fetch(`${API}/api/v1/ai/ask`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ target_id: targetId, title, question }),
    })
    if (!r.ok) throw new Error(`ask failed (${r.status})`)
    return await r.json()
  }, [])

  return {
    scans, vulns, status, loadingList,
    fetchStatus, fetchScans, loadVulns, loadConversation, explainOne, askQuestion,
  }
}
