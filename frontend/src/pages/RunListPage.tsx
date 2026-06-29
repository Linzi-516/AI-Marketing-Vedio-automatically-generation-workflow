import EmptyState from '../components/common/EmptyState'
import Button from '../components/common/Button'
import SectionCard from '../components/common/SectionCard'
import StatusBadge from '../components/common/StatusBadge'
import PageHeader from '../components/layout/PageHeader'
import useRunList from '../hooks/useRunList'

function RunListPage({ onOpenRun }: { onOpenRun: (runId: string) => void }) {
  const { runs, isLoading, error, refresh } = useRunList()

  return (
    <>
      <PageHeader
        title="任务列表"
        description="从后端读取当前内存任务与磁盘历史任务。"
        actions={<Button onClick={refresh}>刷新</Button>}
      />
      <SectionCard title="全部任务" status={runs.length ? '完成' : '未执行'}>
        {error && <div className="error-box">{error}</div>}
        {isLoading && <EmptyState text="正在读取任务列表。" />}
        {!isLoading && runs.length === 0 && <EmptyState text="暂无任务。创建任务后会出现在这里。" />}
        <div className="run-list">
          {runs.map((run) => (
            <div className="run-row" key={run.run_id}>
              <div className="run-main">
                <code>{run.run_id}</code>
                <span>{run.request?.product_name ?? '未记录产品名'}</span>
              </div>
              <StatusBadge status={run.status} />
              <span className="muted small">{run.current_step ?? 'unknown'}</span>
              <Button onClick={() => onOpenRun(run.run_id)}>打开详情</Button>
            </div>
          ))}
        </div>
      </SectionCard>
    </>
  )
}

export default RunListPage
