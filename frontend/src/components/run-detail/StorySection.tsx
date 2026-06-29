import SectionCard from '../common/SectionCard'

function StorySection({ state }: { state: Record<string, unknown> }) {
  const story = typeof state.story === 'string' ? state.story : ''
  return (
    <SectionCard title="2. 用户画像 / 人物小传" status={story ? '完成' : '未执行'}>
      {story ? <pre className="text-block">{story}</pre> : <div className="muted">等待人物小传生成。</div>}
    </SectionCard>
  )
}

export default StorySection
