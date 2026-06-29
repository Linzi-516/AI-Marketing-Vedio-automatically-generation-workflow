import { useCallback, useEffect, useState } from 'react'
import { getConfig, getConfigStatus } from '../api/workflowApi'
import PageHeader from '../components/layout/PageHeader'
import SectionCard from '../components/common/SectionCard'
import StatusBadge from '../components/common/StatusBadge'
import Button from '../components/common/Button'
import type { ConfigStatusResponse, RuntimeConfig } from '../types/workflow'

function ConfigPage() {
  const [config, setConfig] = useState<RuntimeConfig | null>(null)
  const [status, setStatus] = useState<ConfigStatusResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)

  const refreshConfig = useCallback(() => {
    setIsLoading(true)
    setError(null)
    Promise.all([getConfig(), getConfigStatus()])
      .then(([runtimeConfig, configStatus]) => {
        setConfig(runtimeConfig)
        setStatus(configStatus)
      })
      .catch((err) => setError(err instanceof Error ? err.message : '读取配置失败'))
      .finally(() => setIsLoading(false))
  }, [])

  useEffect(() => {
    refreshConfig()
  }, [refreshConfig])

  return (
    <>
      <PageHeader
        title="配置状态"
        description="检测关键 API 与路径是否已配置，不显示密钥、Secret 或 Token。"
        actions={<Button onClick={refreshConfig}>{isLoading ? '刷新中' : '刷新配置'}</Button>}
      />
      <SectionCard title="配置健康检查" status={error ? '失败' : isLoading ? '执行中' : status?.overall_status === 'ready' ? '完成' : '需配置'}>
        {error && <div className="error-box">{error}</div>}
        {!error && !status && <div className="muted">正在读取配置状态...</div>}
        {status && (
          <div className="config-status-list">
            {status.items.map((item) => (
              <div className="config-status-row" key={item.key}>
                <div>
                  <strong>{item.label}</strong>
                  <div className="muted small">{item.key}</div>
                </div>
                <StatusBadge status={item.configured ? 'completed' : 'failed'} />
                <div className="muted small">{item.required_for.join(' / ')}</div>
                <div>{item.message}</div>
              </div>
            ))}
          </div>
        )}
      </SectionCard>

      <SectionCard title="运行参数" status={error ? '失败' : config ? '完成' : '执行中'}>
        {!error && !config && <div className="muted">正在读取运行参数...</div>}
        {config && (
          <div className="kv-grid">
            {Object.entries(config).map(([key, value]) => (
              <div className="kv-item" key={key}>
                <span>{key}</span>
                <strong>{String(value)}</strong>
              </div>
            ))}
          </div>
        )}
      </SectionCard>
    </>
  )
}

export default ConfigPage
