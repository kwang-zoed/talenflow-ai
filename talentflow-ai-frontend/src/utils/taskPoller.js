/**
 * 通用 Celery / 异步任务轮询
 */
export function pollTaskResult({
  getStatus,
  maxTime = 300000,
  initialDelay = 1500,
  maxDelay = 5000,
  backoffFactor = 1.5,
  onProgress,
  normalize = normalizeTaskStatus,
  handleStatus = defaultHandleStatus,
}) {
  let cancelled = false
  let timerId = null
  let progressHandler = null

  const promise = new Promise((resolve, reject) => {
    const startTime = Date.now()

    const attempt = async (delay = initialDelay) => {
      if (cancelled) {
        reject(new Error('轮询已取消'))
        return
      }
      if (Date.now() - startTime > maxTime) {
        reject(new Error('任务超时，请稍后重试'))
        return
      }

      try {
        const raw = await getStatus()
        const data = normalize(raw)
        const decision = handleStatus(data)

        if (decision === 'continue') {
          progressHandler?.(data)
          const nextDelay = Math.min(delay * backoffFactor, maxDelay)
          timerId = setTimeout(() => attempt(nextDelay), delay)
          return
        }

        if (decision?.resolve !== undefined) {
          progressHandler?.({
            ...data,
            status: data.status === 'interrupted' ? 'interrupted' : 'success',
            percent: data.percent ?? 100,
          })
          resolve(decision.resolve)
          return
        }

        if (decision?.reject) {
          reject(decision.reject instanceof Error ? decision.reject : new Error(String(decision.reject)))
          return
        }

        reject(new Error(data.message || '任务状态未知'))
      } catch (error) {
        reject(error instanceof Error ? error : new Error(String(error)))
      }
    }

    attempt()
  })

  promise.cancel = () => {
    cancelled = true
    if (timerId) clearTimeout(timerId)
  }

  Object.defineProperty(promise, 'onProgress', {
    get() {
      return progressHandler
    },
    set(fn) {
      progressHandler = fn
    },
  })

  return promise
}

/** 兼容 axios 拦截器解包后的响应 */
export function normalizeTaskStatus(raw) {
  if (!raw || typeof raw !== 'object') return { status: 'error', message: '无效响应' }
  if (raw.status) return raw
  if (raw.data?.status) return raw.data
  return raw
}

function defaultHandleStatus(data) {
  if (data.status === 'success') {
    return { resolve: data.data ?? data.result ?? data }
  }
  if (data.status === 'processing' || data.status === 'pending') {
    return 'continue'
  }
  if (data.status === 'error') {
    return { reject: new Error(data.message || '任务失败') }
  }
  return { reject: new Error(data.message || `未知状态: ${data.status}`) }
}

export function createProcessingStatusHandler({
  successStatuses = ['success'],
  continueStatuses = ['processing', 'pending'],
  errorStatuses = ['error'],
  extractResult = (data) => data.data ?? data.result ?? data,
  extractError = (data) => data.message || '任务失败',
} = {}) {
  return (data) => {
    if (successStatuses.includes(data.status)) {
      return { resolve: extractResult(data) }
    }
    if (continueStatuses.includes(data.status)) {
      return 'continue'
    }
    if (errorStatuses.includes(data.status)) {
      return { reject: new Error(extractError(data)) }
    }
    return { reject: new Error(extractError(data)) }
  }
}
