import { useState } from 'react'
import AppShell from './components/layout/AppShell'
import ConfigPage from './pages/ConfigPage'
import CreateRunPage from './pages/CreateRunPage'
import RunDetailPage from './pages/RunDetailPage'
import RunListPage from './pages/RunListPage'
import type { PageKey } from './types/workflow'

function App() {
  const [page, setPage] = useState<PageKey>('config')
  const [activeRunId, setActiveRunId] = useState<string | null>(null)
  const [recentRunIds, setRecentRunIds] = useState<string[]>([])

  const openRun = (runId: string) => {
    setActiveRunId(runId)
    setRecentRunIds((prev) => [runId, ...prev.filter((id) => id !== runId)].slice(0, 8))
    setPage('detail')
  }

  return (
    <AppShell
      activePage={page}
      activeRunId={activeRunId}
      recentRunIds={recentRunIds}
      onNavigate={setPage}
      onOpenRun={openRun}
    >
      {page === 'config' && <ConfigPage />}
      {page === 'create' && <CreateRunPage onCreated={openRun} />}
      {page === 'list' && <RunListPage onOpenRun={openRun} />}
      {page === 'detail' && <RunDetailPage runId={activeRunId} />}
    </AppShell>
  )
}

export default App
