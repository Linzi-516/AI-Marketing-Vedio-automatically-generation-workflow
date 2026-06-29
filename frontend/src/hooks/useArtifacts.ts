import { useCallback, useEffect, useState } from 'react'
import { getArtifacts } from '../api/workflowApi'
import type { ArtifactsResponse, RunStatus } from '../types/workflow'

export function useArtifacts(runId: string | null, run: RunStatus | null) {
  const [artifacts, setArtifacts] = useState<ArtifactsResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    if (!runId) return
    setLoading(true)
    setError(null)
    try {
      setArtifacts(await getArtifacts(runId))
    } catch (err) {
      setError(err instanceof Error ? err.message : '获取产物失败')
    } finally {
      setLoading(false)
    }
  }, [runId])

  useEffect(() => {
    void refresh()
  }, [refresh, run?.status, run?.pending_checkpoint])

  return { artifacts, loading, error, refresh }
}
