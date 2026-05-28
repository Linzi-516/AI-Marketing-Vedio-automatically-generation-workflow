import SectionCard from '../common/SectionCard'
import type { ArtifactsResponse } from '../../types/workflow'

function ArtifactSection({ artifacts, state }: { artifacts: ArtifactsResponse | null; state: Record<string, unknown> }) {
  const videos = artifacts?.videos ?? []
  const cards = artifacts?.model_cards ?? []

  return (
    <SectionCard title="8. 视频与模卡产物" status={videos.length || cards.length ? '完成' : '未执行'}>
      <h3>视频结果</h3>
      <div className="artifact-list">
        {videos.map((video) => (
          <div className="artifact-row" key={video.path}>
            <span>{video.name}</span>
            <code>{video.path}</code>
          </div>
        ))}
      </div>
      <h3>模卡图结果</h3>
      <div className="artifact-list">
        {cards.map((card) => (
          <div className="artifact-row" key={card.path}>
            <span>{card.name}</span>
            <code>{card.path}</code>
          </div>
        ))}
      </div>
      {Array.isArray(state.failed_scenes) && state.failed_scenes.length > 0 && (
        <div className="error-box">失败分镜：{state.failed_scenes.join(', ')}</div>
      )}
      {Array.isArray(state.card_failed_indices) && state.card_failed_indices.length > 0 && (
        <div className="error-box">失败模卡索引：{state.card_failed_indices.join(', ')}</div>
      )}
    </SectionCard>
  )
}

export default ArtifactSection
