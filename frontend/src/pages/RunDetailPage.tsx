import Button from '../components/common/Button'
import EmptyState from '../components/common/EmptyState'
import SectionCard from '../components/common/SectionCard'
import PageHeader from '../components/layout/PageHeader'
import ArtifactSection from '../components/run-detail/ArtifactSection'
import AudioSection from '../components/run-detail/AudioSection'
import FeatureVoiceSection from '../components/run-detail/FeatureVoiceSection'
import ImageCheckpointSection from '../components/run-detail/ImageCheckpointSection'
import ProductInputSection from '../components/run-detail/ProductInputSection'
import RunSummary from '../components/run-detail/RunSummary'
import SceneImageAssignSection from '../components/run-detail/SceneImageAssignSection'
import ScriptCheckpointSection from '../components/run-detail/ScriptCheckpointSection'
import StepStatusBar from '../components/run-detail/StepStatusBar'
import StorySection from '../components/run-detail/StorySection'
import { useArtifacts } from '../hooks/useArtifacts'
import { useCheckpoint } from '../hooks/useCheckpoint'
import { useRunPolling } from '../hooks/useRunPolling'

function RunDetailPage({ runId }: { runId: string | null }) {
  const { run, loading, error, refresh } = useRunPolling(runId)
  const { checkpoint, error: checkpointError, submit } = useCheckpoint(runId, run, refresh)
  const { artifacts, error: artifactsError, refresh: refreshArtifacts } = useArtifacts(runId, run)

  if (!runId) {
    return (
      <>
        <PageHeader title="任务详情" />
        <EmptyState text="请先从新建任务或任务列表打开一个 run_id。" />
      </>
    )
  }

  const state = artifacts?.state ?? {}

  return (
    <>
      <PageHeader
        title="任务详情"
        description={`Run ID: ${runId}`}
        actions={
          <Button
            onClick={() => {
              void refresh()
              void refreshArtifacts()
            }}
          >
            刷新
          </Button>
        }
      />
      {error && <div className="error-box">{error}</div>}
      {checkpointError && <div className="error-box">{checkpointError}</div>}
      {artifactsError && <div className="error-box">{artifactsError}</div>}
      {loading && <div className="muted">正在读取任务状态...</div>}
      {run && <RunSummary run={run} />}
      {run && <StepStatusBar run={run} state={state} />}

      <ProductInputSection artifacts={artifacts} run={run} state={state} />
      <StorySection state={state} />
      <FeatureVoiceSection state={state} />
      <ImageCheckpointSection checkpoint={checkpoint} runId={runId} state={state} onSubmit={submit} />
      <ScriptCheckpointSection checkpoint={checkpoint} state={state} onSubmit={submit} />
      <AudioSection artifacts={artifacts} state={state} />
      <SceneImageAssignSection checkpoint={checkpoint} runId={runId} state={state} onSubmit={submit} />
      <ArtifactSection artifacts={artifacts} state={state} />

      {!run && !loading && <SectionCard title="状态" status="未执行">任务状态暂不可用。</SectionCard>}
    </>
  )
}

export default RunDetailPage
