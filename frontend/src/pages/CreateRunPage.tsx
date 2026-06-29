import { FormEvent, useState } from 'react'
import { createRun } from '../api/workflowApi'
import Button from '../components/common/Button'
import SectionCard from '../components/common/SectionCard'
import PageHeader from '../components/layout/PageHeader'
import type { CreateRunInput } from '../types/workflow'

const initialForm: CreateRunInput = {
  product_name: '',
  product_offer: '',
  target_audience: '',
  pain_points: '',
  total_duration: 25,
  run_id: '',
}

function CreateRunPage({ onCreated }: { onCreated: (runId: string) => void }) {
  const [form, setForm] = useState<CreateRunInput>(initialForm)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const update = (key: keyof CreateRunInput, value: string | number) => {
    setForm((prev) => ({ ...prev, [key]: value }))
  }

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    setSubmitting(true)
    setError(null)
    try {
      const payload = { ...form, run_id: form.run_id || null }
      const result = await createRun(payload)
      onCreated(result.run_id)
    } catch (err) {
      setError(err instanceof Error ? err.message : '创建任务失败')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <>
      <PageHeader title="新建任务" description="输入产品信息后创建异步生成任务。" />
      <SectionCard title="产品信息" status="待提交">
        <form className="form-grid" onSubmit={submit}>
          <label>
            产品名称
            <input value={form.product_name} onChange={(e) => update('product_name', e.target.value)} required />
          </label>
          <label>
            产品功能 / Offer
            <input value={form.product_offer} onChange={(e) => update('product_offer', e.target.value)} required />
          </label>
          <label>
            目标受众
            <input value={form.target_audience} onChange={(e) => update('target_audience', e.target.value)} required />
          </label>
          <label>
            视频总时长
            <input
              min={1}
              type="number"
              value={form.total_duration}
              onChange={(e) => update('total_duration', Number(e.target.value))}
            />
          </label>
          <label className="wide">
            核心痛点
            <textarea value={form.pain_points} onChange={(e) => update('pain_points', e.target.value)} required />
          </label>
          <label className="wide">
            可选 run_id
            <input value={form.run_id ?? ''} onChange={(e) => update('run_id', e.target.value)} />
          </label>
          {error && <div className="error-box wide">{error}</div>}
          <div className="form-actions wide">
            <Button variant="secondary" onClick={() => setForm(initialForm)}>
              清空
            </Button>
            <Button variant="primary" disabled={submitting} type="submit">
              {submitting ? '创建中...' : '创建任务'}
            </Button>
          </div>
        </form>
      </SectionCard>
    </>
  )
}

export default CreateRunPage
