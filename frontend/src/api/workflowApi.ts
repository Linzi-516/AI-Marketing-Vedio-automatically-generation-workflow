import type {
  ArtifactsResponse,
  Checkpoint,
  CheckpointSubmit,
  ConfigStatusResponse,
  CreateRunInput,
  CreateRunResponse,
  RunListResponse,
  RunStatus,
  RuntimeConfig,
} from '../types/workflow'

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? ''

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers ?? {}),
    },
    ...init,
  })

  if (!response.ok) {
    const detail = await response.text()
    throw new Error(detail || `Request failed: ${response.status}`)
  }

  return response.json() as Promise<T>
}

export function getConfig(): Promise<RuntimeConfig> {
  return requestJson('/api/config')
}

export function getConfigStatus(): Promise<ConfigStatusResponse> {
  return requestJson('/api/config/status')
}

export function createRun(input: CreateRunInput): Promise<CreateRunResponse> {
  return requestJson('/api/runs', {
    method: 'POST',
    body: JSON.stringify(input),
  })
}

export function getRuns(): Promise<RunListResponse> {
  return requestJson('/api/runs')
}

export function getRun(runId: string): Promise<RunStatus> {
  return requestJson(`/api/runs/${encodeURIComponent(runId)}`)
}

export async function getCheckpoint(runId: string): Promise<Checkpoint | null> {
  try {
    return await requestJson(`/api/runs/${encodeURIComponent(runId)}/checkpoint`)
  } catch {
    return null
  }
}

export function submitCheckpoint(
  runId: string,
  payload: CheckpointSubmit,
): Promise<{ run_id: string; status: string }> {
  return requestJson(`/api/runs/${encodeURIComponent(runId)}/checkpoint`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function getArtifacts(runId: string): Promise<ArtifactsResponse> {
  return requestJson(`/api/runs/${encodeURIComponent(runId)}/artifacts`)
}
