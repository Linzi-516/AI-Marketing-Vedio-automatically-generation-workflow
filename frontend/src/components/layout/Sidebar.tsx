import type { PageKey } from '../../types/workflow'

interface SidebarProps {
  activePage: PageKey
  activeRunId: string | null
  recentRunIds: string[]
  onNavigate: (page: PageKey) => void
  onOpenRun: (runId: string) => void
}

const navItems: Array<{ key: PageKey; label: string }> = [
  { key: 'config', label: '配置状态' },
  { key: 'create', label: '新建任务' },
  { key: 'list', label: '任务列表' },
  { key: 'detail', label: '任务详情' },
]

function Sidebar({ activePage, activeRunId, recentRunIds, onNavigate, onOpenRun }: SidebarProps) {
  return (
    <aside className="sidebar">
      <div className="brand">
        <div className="brand-title">AIGC视频自动化生成</div>
        <div className="brand-subtitle">Automation Tool</div>
      </div>

      <nav className="nav-list">
        {navItems.map((item) => (
          <button
            key={item.key}
            className={activePage === item.key ? 'nav-item active' : 'nav-item'}
            type="button"
            onClick={() => onNavigate(item.key)}
          >
            {item.label}
          </button>
        ))}
      </nav>

      <div className="recent-runs">
        <div className="sidebar-heading">最近任务</div>
        {recentRunIds.length === 0 && <div className="muted small">暂无任务</div>}
        {recentRunIds.map((runId) => (
          <button
            key={runId}
            type="button"
            className={runId === activeRunId ? 'recent-run active' : 'recent-run'}
            onClick={() => onOpenRun(runId)}
          >
            {runId}
          </button>
        ))}
      </div>
    </aside>
  )
}

export default Sidebar
