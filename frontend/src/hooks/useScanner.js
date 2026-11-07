'use client'
import { useState, useCallback, useEffect, useRef } from 'react'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export function useScanner() {
  const [scan,     setScan]     = useState(null)
  const [logs,     setLogs]     = useState([])
  const [findings, setFindings] = useState([])
  const [metrics,  setMetrics]  = useState({
    subdomains: 0, ports: 0, findings: 0, endpoints: 0, percent: 0, step: '', total: 0,
  })
  const [isRunning, setIsRunning] = useState(false)
  // When a cached result already exists we pause and let the user choose:
  // {targetId, target, last_scan_at, last_findings}
  const [pendingCache, setPendingCache] = useState(null)
  const pollRef = useRef(null)

  const log = (level, message) => setLogs(prev => [...prev, {
    ts: new Date().toLocaleTimeString('fr-FR'), level, message,
  }])

  // ── Lancer un scan ────────────────────────────────────────
  // Creates the target, then checks the cache. If a cached result exists we stop
  // here and surface a choice (reuse vs rescan) via `pendingCache`.
  const startScan = useCallback(async (target) => {
    setLogs([])
    setFindings([])
    setPendingCache(null)
    setMetrics({ subdomains: 0, ports: 0, findings: 0, endpoints: 0, percent: 0, step: 'Démarrage…', total: 0 })
    setIsRunning(true)

    try {
      // Détecter le type de cible
      let targetType = 'URL'
      if (/^\d{1,3}(\.\d{1,3}){3}$/.test(target)) targetType = 'IP'
      else if (/\//.test(target) && !target.startsWith('http')) targetType = 'CIDR'
      else if (!target.startsWith('http')) targetType = 'DNS'

      log('info', `Création de la cible ${target} (${targetType})...`)

      const targetRes = await fetch(`${API}/api/v1/targets/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ value: target, targetType }),
      })
      const targetData = await targetRes.json()
      setScan(targetData)
      log('info', `Cible créée (ID: ${targetData.id}).`)

      // Cache check — offer the user a choice instead of silently reusing.
      try {
        const cRes = await fetch(`${API}/api/v1/scans/cache-status/${targetData.id}`)
        if (cRes.ok) {
          const c = await cRes.json()
          if (c.cached) {
            setIsRunning(false)
            setPendingCache({ targetId: targetData.id, target, ...c })
            log('warn', 'Un résultat en cache existe pour cette cible — en attente de votre choix.')
            return
          }
        }
      } catch { /* cache check is best-effort */ }

      await runScan(targetData.id, false)
    } catch (err) {
      setIsRunning(false)
      log('error', `Erreur : ${err.message}`)
    }
  }, [])

  // ── Exécute réellement le scan (avec ou sans cache) ───────
  const runScan = useCallback(async (targetId, force) => {
    setPendingCache(null)
    setIsRunning(true)
    setMetrics(prev => ({ ...prev, percent: 10, step: 'Scan en cours…' }))
    log('info', force ? 'Relance d’un scan complet (cache ignoré)…' : 'Lancement du scan…')

    try {
      const scanRes = await fetch(`${API}/api/v1/scans/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ target_id: targetId, force: !!force }),
      })
      if (!scanRes.ok) {
        const errText = await scanRes.text()
        throw new Error(`Scan failed (${scanRes.status}): ${errText}`)
      }
      const scanData = await scanRes.json()
      const scanId = scanData.scan_id

      // 3. Suivre la progression en temps réel (polling du live-console)
      let seen = 0
      let finalStatus = 'running'
      // Progress estimate from the backend's step events:
      // "Étape i/n — tool1, tool2" starts a step; each "… terminé"/"échec" ends a tool.
      let pct = 10, stepBase = 10, stepSpan = 85, toolsInStep = 1, toolsDone = 0
      while (finalStatus === 'running') {
        await new Promise(r => setTimeout(r, 1200))
        let prog
        try {
          const pr = await fetch(`${API}/api/v1/scans/progress/${scanId}`)
          if (!pr.ok) break
          prog = await pr.json()
        } catch {
          continue // transient error — keep polling
        }

        const events = prog.events ?? []
        if (events.length > seen) {
          const fresh = events.slice(seen)
          seen = events.length
          setLogs(prev => [
            ...prev,
            ...fresh.map(e => ({
              ts: new Date(e.ts).toLocaleTimeString('fr-FR'),
              level: e.level || 'info',
              message: e.message,
            })),
          ])
          for (const e of fresh) {
            const msg = e.message || ''
            const m = /Étape (\d+)\/(\d+)\s*[—-]\s*(.*)$/.exec(msg)
            if (m) {
              const i = Number(m[1]), n = Number(m[2]) || 1
              stepSpan = 85 / n
              stepBase = 10 + (i - 1) * stepSpan
              toolsInStep = Math.max(1, m[3].split(',').length)
              toolsDone = 0
            } else if (/(terminé|arrêté|échec)/.test(msg)) {
              toolsDone = Math.min(toolsInStep, toolsDone + 1)
            }
            pct = Math.max(pct, Math.min(95, Math.round(stepBase + stepSpan * (toolsDone / toolsInStep))))
          }
          const last = events[events.length - 1]
          setMetrics(prev => ({ ...prev, step: last.message, percent: pct }))
        }

        if (prog.status !== 'running') {
          finalStatus = prog.status
        }
      }

      setMetrics(prev => ({ ...prev, percent: 100, step: finalStatus === 'error' ? 'Échec' : 'Terminé' }))

      // 4. Récupérer les résultats détaillés
      const resultsRes = await fetch(`${API}/api/v1/scans/results/${targetId}`)
      const resultsData = await resultsRes.json()
      setFindings(resultsData.vulnerabilities ?? [])

      const m = resultsData.metrics ?? {}
      setMetrics(prev => ({
        ...prev,
        subdomains: m.subdomains ?? 0,
        endpoints:  m.endpoints  ?? 0,
        ports:      m.ports      ?? 0,
        findings:   m.findings ?? resultsData.total ?? prev.findings,
      }))
      setIsRunning(false)

    } catch (err) {
      setIsRunning(false)
      setLogs(prev => [...prev, {
        ts: new Date().toLocaleTimeString('fr-FR'),
        level: 'error',
        message: `Erreur : ${err.message}`
      }])
    }
  }, [])

  // ── Arrêter un scan ───────────────────────────────────────
  const stopScan = useCallback(async () => {
    if (pollRef.current) clearInterval(pollRef.current)
    setIsRunning(false)
    setLogs(prev => [...prev, {
      ts: new Date().toLocaleTimeString('fr-FR'),
      level: 'warn',
      message: 'Scan arrêté manuellement'
    }])
  }, [])

  useEffect(() => () => {
    if (pollRef.current) clearInterval(pollRef.current)
  }, [])

  // Resolve the cache prompt: reuse the stored result, or force a fresh scan.
  const resolveCache = useCallback((force) => {
    if (!pendingCache) return
    runScan(pendingCache.targetId, force)
  }, [pendingCache, runScan])

  const dismissCache = useCallback(() => {
    setPendingCache(null)
    setIsRunning(false)
    log('warn', 'Scan annulé.')
  }, [])

  return {
    scan, logs, findings, metrics, isRunning, startScan, stopScan,
    pendingCache, resolveCache, dismissCache,
  }
}