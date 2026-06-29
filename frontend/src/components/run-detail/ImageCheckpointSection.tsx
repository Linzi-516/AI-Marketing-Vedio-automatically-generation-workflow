import { useState } from 'react'
import Button from '../common/Button'
import SectionCard from '../common/SectionCard'
import type { Checkpoint, CheckpointSubmit } from '../../types/workflow'
import { fileName, runFileUrl } from '../../utils/fileUrls'

function ImageCheckpointSection({
  checkpoint,
  runId,
  state,
  onSubmit,
}: {
  checkpoint: Checkpoint | null
  runId: string
  state: Record<string, unknown>
  onSubmit: (payload: CheckpointSubmit) => Promise<void>
}) {
  const [newPrompt, setNewPrompt] = useState('')
  const isActive = checkpoint?.type === 'image_confirm'
  const payload = isActive ? checkpoint.payload : {}
  const imagePaths = asList(payload.image_paths ?? state.image_paths)
  const featurePrompt = String(payload.feature_prompt ?? state.feature_prompt ?? '')

  return (
    <SectionCard title="4. 人物图片" status={isActive ? '等待确认' : imagePaths.length ? '完成' : '未执行'}>
      <div className="image-grid">
        {imagePaths.map((path) => (
          <div className="image-tile" key={path}>
            <img alt={fileName(path)} className="image-preview" src={runFileUrl(runId, path)} />
            <code>{fileName(path)}</code>
          </div>
        ))}
      </div>
      <h3>当前 Prompt</h3>
      <textarea value={newPrompt || featurePrompt} onChange={(e) => setNewPrompt(e.target.value)} />
      {isActive && (
        <div className="section-actions">
          <Button variant="primary" onClick={() => onSubmit({ type: 'image_confirm', action: 'next' })}>
            满意，继续
          </Button>
          <Button
            onClick={() =>
              onSubmit({
                type: 'image_confirm',
                action: 'regenerate',
                new_prompt: newPrompt || featurePrompt,
              })
            }
          >
            修改 Prompt 重绘
          </Button>
        </div>
      )}
    </SectionCard>
  )
}

function asList(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === 'string') : []
}

export default ImageCheckpointSection
