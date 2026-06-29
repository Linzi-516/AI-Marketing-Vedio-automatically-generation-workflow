const API_BASE = import.meta.env.VITE_API_BASE_URL ?? ''

export function runFileUrl(runId: string, path: string): string {
  return `${API_BASE}/api/runs/${encodeURIComponent(runId)}/files/${encodeURIComponent(fileName(path))}`
}

export function fileName(path: string): string {
  return path.split(/[\\/]/).pop() ?? path
}
