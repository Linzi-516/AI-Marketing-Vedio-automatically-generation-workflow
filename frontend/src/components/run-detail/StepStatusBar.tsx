import type { RunStatus } from '../../types/workflow'

const steps = [
  { key: 'story', label: '人物小传' },
  { key: 'image', label: '人物图片' },
  { key: 'script', label: '脚本' },
  { key: 'tts', label: '音频' },
  { key: 'scene_image_select', label: '首帧' },
  { key: 'video', label: '视频' },
  { key: 'model_card', label: '模卡' },
]

function StepStatusBar({ run }: { run: RunStatus; state: Record<string, unknown> }) {
  const completed = new Set(run.progress.completed_steps)

  return (
    <div className="step-bar">
      {steps.map((step) => {
        const active = run.current_step === step.key || run.pending_checkpoint === step.key
        const done = completed.has(step.key)
        const className = done ? 'done' : active ? run.status === 'waiting_user' ? 'waiting' : 'running' : 'idle'
        return (
          <div className={`step-pill ${className}`} key={step.key}>
            {step.label}
          </div>
        )
      })}
    </div>
  )
}

export default StepStatusBar
