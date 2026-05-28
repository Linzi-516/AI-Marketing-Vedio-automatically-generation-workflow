import { useCallback, useEffect, useState } from 'react'
import { getCheckpoint, submitCheckpoint } from '../api/workflowApi'
import type { Checkpoint, CheckpointSubmit, RunStatus } from '../types/workflow'

export function useCheckpoint(runId: string | null, run: RunStatus | null, onSubmitted: () => void) {
  const [checkpoint, setCheckpoint] = useState<Checkpoint | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    if (!runId || run?.status !== 'waiting_user') {
      setCheckpoint(null)
      return
    }
    setLoading(true)
    setError(null)
    try {
      setCheckpoint(await getCheckpoint(runId))
    } catch (err) {
      setError(err instanceof Error ? err.message : '获取确认点失败')
    } finally {
      setLoading(false)
    }
  }, [run?.status, runId])

  const submit = useCallback(
    async (payload: CheckpointSubmit) => {
      if (!runId) return
      setLoading(true)
      setError(null)
      try {
        await submitCheckpoint(runId, payload)
        setCheckpoint(null)
        onSubmitted()
      } catch (err) {
        setError(err instanceof Error ? err.message : '提交确认点失败')
      } finally {
        setLoading(false)
      }
    },
    [onSubmitted, runId],
  )

  useEffect(() => {
    void refresh()
  }, [refresh])

  return { checkpoint, loading, error, refresh, submit }
}
