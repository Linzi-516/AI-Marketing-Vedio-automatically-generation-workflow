import SectionCard from '../common/SectionCard'
import type { ArtifactsResponse, RunStatus } from '../../types/workflow'

function ProductInputSection({
  artifacts,
  run,
  state,
}: {
  artifacts: ArtifactsResponse | null
  run: RunStatus | null
  state: Record<string, unknown>
}) {
  const request = artifacts?.request ?? run?.request ?? {}

  return (
    <SectionCard title="1. 产品输入" status={request.product_name ? '完成' : '只读'}>
      <div className="kv-grid">
        <Info label="产品名称" value={request.product_name} />
        <Info label="目标受众" value={request.target_audience} />
        <Info label="产品功能 / Offer" value={request.product_offer} />
        <Info label="目标时长" value={request.total_duration ? `${request.total_duration}s` : undefined} />
      </div>
      <div className="kv-item wide-item">
        <span>核心痛点</span>
        <strong>{request.pain_points || '暂无'}</strong>
      </div>
      <pre className="code-block">{JSON.stringify(pick(state, ['run_id', 'run_dir']), null, 2)}</pre>
    </SectionCard>
  )
}

function Info({ label, value }: { label: string; value?: string | number | null }) {
  return (
    <div className="kv-item">
      <span>{label}</span>
      <strong>{value ? String(value) : '暂无'}</strong>
    </div>
  )
}

function pick(source: Record<string, unknown>, keys: string[]) {
  return Object.fromEntries(keys.map((key) => [key, source[key] ?? null]))
}

export default ProductInputSection
