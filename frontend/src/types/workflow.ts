export type PageKey = 'config' | 'create' | 'list' | 'detail'

export type RunStatusValue = 'queued' | 'running' | 'waiting_user' | 'completed' | 'failed'

export type CheckpointType = 'image_confirm' | 'script_confirm' | 'scene_image_select'

export interface RuntimeConfig {
  video_engine: string
  qwen_model: string
  jimeng_image_model: string
  omni_video_model: string
  output_dir: string
  scene_min_duration: number
  scene_max_duration: number
}

export interface ConfigStatusItem {
  key: string
  label: string
  configured: boolean
  required_for: string[]
  message: string
}

export interface ConfigStatusResponse {
  overall_status: 'ready' | 'incomplete'
  items: ConfigStatusItem[]
}

export interface CreateRunInput {
  product_name: string
  product_offer: string
  target_audience: string
  pain_points: string
  total_duration: number
  run_id?: string | null
}

export interface CreateRunResponse {
  run_id: string
  status: string
}

export interface RunStatus {
  run_id: string
  status: RunStatusValue
  current_step: string | null
  pending_checkpoint: CheckpointType | null
  progress: {
    completed_steps: string[]
    total_scenes: number
  }
  error: string | null
  request?: Partial<CreateRunInput>
}

export interface RunListResponse {
  runs: RunStatus[]
}

export interface Checkpoint {
  type: CheckpointType
  payload: Record<string, unknown>
}

export interface ArtifactItem {
  path: string
  name: string
  exists: boolean
  url?: string
}

export interface ArtifactsResponse {
  run_id: string
  run_dir: string
  images: ArtifactItem[]
  audios: ArtifactItem[]
  videos: ArtifactItem[]
  model_cards: ArtifactItem[]
  request?: Partial<CreateRunInput>
  state: Record<string, unknown>
}

export type CheckpointSubmit = Record<string, unknown> & {
  type: CheckpointType
}
