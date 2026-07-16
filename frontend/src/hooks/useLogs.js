'use client'
import { useState, useCallback } from 'react'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export function useLogs() {
  const [logs, setLogs]       = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError]     = useState(null)

  const fetchLogs = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res  = await fetch(`${API}/api/v1/scans/logs`)
      const data = await res.json()
      setLogs(data.logs ?? [])
    } catch (err) {
      setError(err.message)
      setLogs([])
    } finally {
      setLoading(false)
    }
  }, [])

  return { logs, loading, error, fetchLogs }
}
