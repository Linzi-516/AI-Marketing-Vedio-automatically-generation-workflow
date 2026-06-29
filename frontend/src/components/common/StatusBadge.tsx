import type { RunStatusValue } from '../../types/workflow'

interface StatusBadgeProps {
  status?: RunStatusValue | string | null
}

function StatusBadge({ status }: StatusBadgeProps) {
  const value = status ?? 'unknown'
  return <span className={`status-badge status-${value}`}>{value}</span>
}

export default StatusBadge
