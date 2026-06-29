import { useState } from 'react'
import Button from '../common/Button'
import SectionCard from '../common/SectionCard'
import type { Checkpoint, CheckpointSubmit } from '../../types/workflow'
import { fileName, runFileUrl } from '../../utils/fileUrls'

function SceneImageAssignSection({
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
  const isActive = checkpoint?.type === 'scene_image_select'
  const payload = isActive ? checkpoint.payload : {}
  const scenes = Array.isArray(payload.scenes) ? payload.scenes : Array.isArray(state.scenes) ? state.scenes : []
  const imagePaths = asList(payload.available_image_paths ?? state.image_paths)
  const imageUrls = asList(payload.available_image_urls ?? state.image_urls)
  const [selectedIndex, setSelectedIndex] = useState(0)

  const submitAll = () => {
    const imagePath = imagePaths[selectedIndex] ?? ''
    const imageUrl = imageUrls[selectedIndex] ?? ''
    const scene_image_selections = scenes.map((scene, index) => ({
      scene_id: getSceneId(scene, index),
      image_path: imagePath,
      image_url: imageUrl,
    }))
    void onSubmit({ type: 'scene_image_select', scene_image_selections })
  }

  return (
    <SectionCard title="7. 首帧分配" status={isActive ? '等待确认' : state.scene_image_selections ? '完成' : '未执行'}>
      <div className="two-column">
        <div>
          <h3>图片池</h3>
          {imagePaths.map((path, index) => (
            <label className="radio-row" key={path}>
              <input
                checked={selectedIndex === index}
                type="radio"
                onChange={() => setSelectedIndex(index)}
              />
              <img alt={fileName(path)} className="choice-thumb" src={runFileUrl(runId, path)} />
              <span>{fileName(path)}</span>
            </label>
          ))}
        </div>
        <div>
          <h3>分镜</h3>
          {scenes.map((scene, index) => (
            <div className="scene-card" key={getSceneId(scene, index)}>
              分镜 {getSceneId(scene, index)}：{getSceneScript(scene)}
            </div>
          ))}
        </div>
      </div>
      {isActive && (
        <div className="section-actions">
          <Button variant="primary" onClick={submitAll}>
            全部分镜使用所选图片
          </Button>
        </div>
      )}
    </SectionCard>
  )
}

function asList(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === 'string') : []
}

function getSceneId(scene: unknown, index: number) {
  return typeof scene === 'object' && scene && 'scene_id' in scene ? String(scene.scene_id) : String(index + 1)
}

function getSceneScript(scene: unknown) {
  return typeof scene === 'object' && scene && 'script' in scene ? String(scene.script).slice(0, 40) : ''
}

export default SceneImageAssignSection
