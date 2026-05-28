import { useEffect, useState } from 'react'
import Button from '../common/Button'
import SectionCard from '../common/SectionCard'
import type { Checkpoint, CheckpointSubmit } from '../../types/workflow'

function ScriptCheckpointSection({
  checkpoint,
  state,
  onSubmit,
}: {
  checkpoint: Checkpoint | null
  state: Record<string, unknown>
  onSubmit: (payload: CheckpointSubmit) => Promise<void>
}) {
  const isActive = checkpoint?.type === 'script_confirm'
  const payload = isActive ? checkpoint.payload : {}
  const [fullScript, setFullScript] = useState('')
  const [scenesText, setScenesText] = useState('[]')

  useEffect(() => {
    setFullScript(String(payload.full_script ?? state.full_script ?? ''))
    setScenesText(JSON.stringify(payload.scenes ?? state.scenes ?? [], null, 2))
  }, [payload.full_script, payload.scenes, state.full_script, state.scenes])

  const submit = () => {
    let scenes: unknown[] = []
    try {
      scenes = JSON.parse(scenesText) as unknown[]
    } catch {
      window.alert('分镜 JSON 格式不正确')
      return
    }
    void onSubmit({ type: 'script_confirm', full_script: fullScript, scenes })
  }

  return (
    <SectionCard title="5. 口播脚本与分镜" status={isActive ? '等待确认' : fullScript ? '完成' : '未执行'}>
      <label>
        完整脚本
        <textarea value={fullScript} onChange={(e) => setFullScript(e.target.value)} />
      </label>
      <label>
        分镜 JSON
        <textarea value={scenesText} onChange={(e) => setScenesText(e.target.value)} />
      </label>
      {isActive && (
        <div className="section-actions">
          <Button variant="primary" onClick={submit}>
            确认脚本
          </Button>
        </div>
      )}
    </SectionCard>
  )
}

export default ScriptCheckpointSection
