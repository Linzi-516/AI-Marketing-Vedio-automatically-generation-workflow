import { useCallback, useEffect, useState } from 'react'
import { getRuns } from '../api/workflowApi'
import type { RunStatus } from '../types/workflow'

function useRunList() {
  const [runs, setRuns] = useState<RunStatus[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    setIsLoading(true)
    setError(null)
    try {
      const response = await getRuns()
      setRuns(response.runs)
    } catch (err) {
      setError(err instanceof Error ? err.message : '任务列表读取失败')
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    refresh()
  }, [refresh])

  return { runs, isLoading, error, refresh }
}

export default useRunList
