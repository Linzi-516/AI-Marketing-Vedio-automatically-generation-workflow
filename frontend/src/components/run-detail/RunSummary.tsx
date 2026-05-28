import StatusBadge from '../common/StatusBadge'
import type { RunStatus } from '../../types/workflow'

function RunSummary({ run }: { run: RunStatus }) {
  return (
    <section className="summary-panel">
      <div>
        <span className="muted small">Run ID</span>
        <strong>{run.run_id}</strong>
      </div>
      <div>
        <span className="muted small">状态</span>
        <StatusBadge status={run.status} />
      </div>
      <div>
        <span className="muted small">当前步骤</span>
        <strong>{run.current_step ?? '-'}</strong>
      </div>
      <div>
        <span className="muted small">分镜数</span>
        <strong>{run.progress.total_scenes}</strong>
      </div>
    </section>
  )
}

export default RunSummary
