import { useState, useCallback } from 'react'

function getApiBaseUrl() {
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

export function useClearCache() {
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState<string | null>(null)

  const clearCache = useCallback(async () => {
    setLoading(true)
    setMessage(null)

    try {
      const response = await fetch(`${getApiBaseUrl()}/api/cache`, {
        method: 'DELETE',
      })

      if (!response.ok) {
        const text = await response.text()
        throw new Error(`${response.status}::${text || 'Unknown error'}`)
      }

      const data = await response.json()
      if (data.success) {
        setMessage(`缓存已清除 (删除 ${data.deleted || 0} 条)`)
      } else {
        setMessage(`清除失败: ${data.error || '未知错误'}`)
      }
    } catch (error: any) {
      setMessage(`请求出错: ${error.message}`)
    } finally {
      setLoading(false)
      setTimeout(() => setMessage(null), 3000)
    }
  }, [])

  return { loading, clearCache, message }
}
