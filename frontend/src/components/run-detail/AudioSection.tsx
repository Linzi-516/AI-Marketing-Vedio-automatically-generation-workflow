import SectionCard from '../common/SectionCard'
import type { ArtifactsResponse } from '../../types/workflow'

function AudioSection({ artifacts, state }: { artifacts: ArtifactsResponse | null; state: Record<string, unknown> }) {
  const audios = artifacts?.audios ?? []
  return (
    <SectionCard title="6. TTS 音频" status={audios.length ? '完成' : '未执行'}>
      {audios.length === 0 && <div className="muted">等待音频生成。</div>}
      <div className="artifact-list">
        {audios.map((audio) => (
          <div className="artifact-row" key={audio.path}>
            <span>{audio.name}</span>
            <code>{audio.path}</code>
          </div>
        ))}
      </div>
      {Array.isArray(state.tts_failed_indices) && state.tts_failed_indices.length > 0 && (
        <div className="error-box">失败音频索引：{state.tts_failed_indices.join(', ')}</div>
      )}
    </SectionCard>
  )
}

export default AudioSection
