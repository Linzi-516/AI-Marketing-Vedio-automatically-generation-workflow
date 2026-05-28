import type { ReactNode } from 'react'
import Sidebar from './Sidebar'
import type { PageKey } from '../../types/workflow'

interface AppShellProps {
  activePage: PageKey
  activeRunId: string | null
  recentRunIds: string[]
  onNavigate: (page: PageKey) => void
  onOpenRun: (runId: string) => void
  children: ReactNode
}

function AppShell({ activePage, activeRunId, recentRunIds, onNavigate, onOpenRun, children }: AppShellProps) {
  return (
    <div className="app-shell">
      <Sidebar
        activePage={activePage}
        activeRunId={activeRunId}
        recentRunIds={recentRunIds}
        onNavigate={onNavigate}
        onOpenRun={onOpenRun}
      />
      <main className="main-panel">{children}</main>
    </div>
  )
}

export default AppShell
