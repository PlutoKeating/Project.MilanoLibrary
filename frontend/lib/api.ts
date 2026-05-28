export function getApiBaseUrl(): string {
  if (typeof window !== 'undefined') {
    const stored = window.localStorage.getItem('backend-base-url')
    if (stored) {
      try {
        const parsed = JSON.parse(stored)
        if (parsed) {
          return typeof parsed === 'string' ? parsed.replace(/\/$/, '') : parsed
        }
      } catch (e) {
        return stored
      }
    }
  }
  return process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
}

export async function pausePipeline(taskId: string): Promise<any> {
  const baseUrl = getApiBaseUrl()
  const res = await fetch(`${baseUrl}/api/pipeline/pause/${taskId}`, {
    method: 'POST',
  })
  if (!res.ok) {
    throw new Error('Failed to pause pipeline')
  }
  return res.json()
}

export async function stopPipeline(taskId: string): Promise<any> {
  const baseUrl = getApiBaseUrl()
  const res = await fetch(`${baseUrl}/api/pipeline/stop/${taskId}`, {
    method: 'POST',
  })
  if (!res.ok) {
    throw new Error('Failed to stop pipeline')
  }
  return res.json()
}
