import { useCallback, useEffect, useState } from 'react'
import { getRun } from '../api/workflowApi'
import type { RunStatus } from '../types/workflow'

export function useRunPolling(runId: string | null) {
  const [run, setRun] = useState<RunStatus | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    if (!runId) return
    setLoading(true)
    setError(null)
    try {
      setRun(await getRun(runId))
    } catch (err) {
      setError(err instanceof Error ? err.message : '获取任务状态失败')
    } finally {
      setLoading(false)
    }
  }, [runId])

  useEffect(() => {
    void refresh()
  }, [refresh])

  useEffect(() => {
    if (!runId || !run) return
    if (run.status !== 'queued' && run.status !== 'running') return

    const timer = window.setInterval(() => {
      void refresh()
    }, 3000)

    return () => window.clearInterval(timer)
  }, [refresh, run, runId])

  return { run, loading, error, refresh }
}
