import SectionCard from '../common/SectionCard'

function FeatureVoiceSection({ state }: { state: Record<string, unknown> }) {
  return (
    <SectionCard title="3. 人物视觉与音色" status={state.feature_prompt || state.voice_type ? '完成' : '未执行'}>
      <div className="two-column">
        <div>
          <h3>视觉提示词</h3>
          <pre className="text-block">{String(state.feature_prompt ?? '等待生成')}</pre>
        </div>
        <div>
          <h3>音色</h3>
          <div className="code-block">{String(state.voice_type ?? '等待选择')}</div>
        </div>
      </div>
    </SectionCard>
  )
}

export default FeatureVoiceSection
