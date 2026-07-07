import { getRecommendSessionStatus } from '@/api/hrRecommend'
import {
  upsertHrRecommendTask,
  updateHrRecommendTask,
  getHrRecommendTasks,
  subscribeHrRecommendQueue,
  dismissJobSessionTasks,
} from '@/utils/hrResumeRecommendTaskRunner'

export { subscribeHrRecommendQueue, getHrRecommendTasks }

const RERANK_POLL_INTERVAL_MS = 3000
/** 含排队在内的总等待上限（Celery 单 worker 串行时后几个任务会在队列里等很久） */
const RERANK_QUEUE_MAX_WAIT_MS = 900000
/** Worker 真正开始精排后的处理上限 */
const RERANK_PROCESS_MAX_WAIT_MS = 360000

/** @type {Map<string, { timer: ReturnType<typeof setInterval>, startedAt: number, processingStartedAt: number | null }>} */
const activeSessionPolls = new Map()
/** @type {Map<string, Set<{ onUpdate?: Function, onReady?: Function, onError?: Function }>>} */
const sessionListeners = new Map()

function sessionTaskId(sessionId) {
  return `session:${sessionId}`
}

function notifyListeners(sessionId, event, payload) {
  sessionListeners.get(sessionId)?.forEach((cb) => cb[event]?.(payload))
}

function isRerankPendingStatus(status) {
  return status === 'rerank_queued' || status === 'reranking'
}

export function upsertCoarseRecommendTask({ sessionId, jobId, jobTitle, resultCount = 0, result = null }) {
  const taskId = sessionTaskId(sessionId)
  dismissJobSessionTasks(jobId, { keepTaskId: taskId, sessionId })
  upsertHrRecommendTask({
    taskId,
    sessionId,
    jobId: Number(jobId),
    jobTitle: jobTitle || `职位 #${jobId}`,
    phase: 'coarse',
    status: 'success',
    percent: 100,
    resultCount,
    result,
    ranking: 'coarse',
    completedAt: Date.now(),
  })
}

/** 后端精排计算完成（rerank_ready），与前端「应用精排」无关 */
export function markRerankComputeComplete(sessionId, statusRes = {}) {
  const resultCount = statusRes.rerank_total ?? statusRes.coarse_total ?? 0
  updateHrRecommendTask(sessionTaskId(sessionId), {
    phase: 'rerank',
    status: 'success',
    percent: 100,
    resultCount,
    rerank_available: true,
    ranking: 'rerank',
    rerankPhase: 'done',
    completedAt: Date.now(),
  })
  window.dispatchEvent(
    new CustomEvent('hrRecommendRerankReady', {
      detail: {
        sessionId,
        jobId: statusRes.job_id,
        resultCount,
      },
    })
  )
}

export function startRerankRecommendTask({ sessionId, jobId, jobTitle }) {
  const taskId = sessionTaskId(sessionId)
  dismissJobSessionTasks(jobId, { keepTaskId: taskId, sessionId })
  upsertHrRecommendTask({
    taskId,
    sessionId,
    jobId: Number(jobId),
    jobTitle: jobTitle || `职位 #${jobId}`,
    phase: 'rerank',
    status: 'processing',
    percent: 3,
    rerankPhase: 'queued',
    startedAt: Date.now(),
  })
  ensureSessionRerankPoll(sessionId)
}

/** 前端应用精排后更新结果缓存 */
export function markRerankRecommendApplied({ sessionId, resultCount = 0, result = null }) {
  updateHrRecommendTask(sessionTaskId(sessionId), {
    phase: 'rerank',
    status: 'success',
    percent: 100,
    resultCount,
    result,
    ranking: 'rerank',
    rerank_applied: true,
    rerankPhase: 'done',
    completedAt: Date.now(),
  })
}

export function markRerankRecommendError(sessionId, error = '精排失败') {
  updateHrRecommendTask(sessionTaskId(sessionId), {
    phase: 'rerank',
    status: 'error',
    error,
    rerankPhase: 'error',
    completedAt: Date.now(),
  })
}

export function getRecommendTasksForJob(jobId) {
  const id = Number(jobId)
  return getHrRecommendTasks()
    .filter((t) => Number(t.jobId) === id && t.sessionId)
    .sort((a, b) => (b.timestamp || 0) - (a.timestamp || 0))
}

export function getLatestRecommendSessionForJob(jobId) {
  const tasks = getRecommendTasksForJob(jobId)
  return tasks[0] || null
}

function stopSessionPoll(sessionId) {
  const entry = activeSessionPolls.get(sessionId)
  if (!entry) return
  clearInterval(entry.timer)
  activeSessionPolls.delete(sessionId)
}

function handleRerankReady(sessionId, res) {
  stopSessionPoll(sessionId)
  markRerankComputeComplete(sessionId, res)
  notifyListeners(sessionId, 'onReady', res)
}

function markRerankTimeout(sessionId, pollState) {
  const msg = pollState.processingStartedAt
    ? '精排处理超时，请稍后重试'
    : '精排排队超时，请稍后重试'
  stopSessionPoll(sessionId)
  markRerankRecommendError(sessionId, msg)
  notifyListeners(sessionId, 'onError', new Error(msg))
}

async function pollSessionRerankOnce(sessionId, pollState) {
  const res = await getRecommendSessionStatus(sessionId)
  notifyListeners(sessionId, 'onUpdate', res)

  const status = res.session_status || res.sessionStatus
  const totalElapsed = Date.now() - pollState.startedAt

  if (status === 'rerank_queued') {
    const percent = Math.min(8, 3 + Math.floor((totalElapsed / RERANK_QUEUE_MAX_WAIT_MS) * 5))
    updateHrRecommendTask(sessionTaskId(sessionId), {
      percent,
      status: 'processing',
      phase: 'rerank',
      rerankPhase: 'queued',
    })
    if (totalElapsed > RERANK_QUEUE_MAX_WAIT_MS) {
      markRerankTimeout(sessionId, pollState)
      return 'done'
    }
    return 'continue'
  }

  if (status === 'reranking') {
    if (!pollState.processingStartedAt) {
      pollState.processingStartedAt = Date.now()
    }
    const procElapsed = Date.now() - pollState.processingStartedAt
    const percent = Math.min(92, 10 + Math.floor((procElapsed / RERANK_PROCESS_MAX_WAIT_MS) * 82))
    updateHrRecommendTask(sessionTaskId(sessionId), {
      percent,
      status: 'processing',
      phase: 'rerank',
      rerankPhase: 'running',
    })
    if (procElapsed > RERANK_PROCESS_MAX_WAIT_MS || totalElapsed > RERANK_QUEUE_MAX_WAIT_MS) {
      markRerankTimeout(sessionId, pollState)
      return 'done'
    }
    return 'continue'
  }

  if (status === 'rerank_ready') {
    handleRerankReady(sessionId, res)
    return 'done'
  }

  if (status === 'error') {
    stopSessionPoll(sessionId)
    markRerankRecommendError(sessionId, '精排失败')
    notifyListeners(sessionId, 'onError', new Error('精排失败'))
    return 'done'
  }

  if (isRerankPendingStatus(status)) {
    return 'continue'
  }

  if (totalElapsed > RERANK_QUEUE_MAX_WAIT_MS) {
    markRerankTimeout(sessionId, pollState)
    return 'done'
  }

  return 'continue'
}

/** 全局精排轮询：离开推荐页也不中断，rerank_ready 即标记队列已完成 */
export function ensureSessionRerankPoll(sessionId) {
  if (!sessionId) return

  if (!activeSessionPolls.has(sessionId)) {
    const pollState = {
      timer: null,
      startedAt: Date.now(),
      processingStartedAt: null,
    }

    const tick = async () => {
      try {
        const outcome = await pollSessionRerankOnce(sessionId, pollState)
        if (outcome === 'done') {
          stopSessionPoll(sessionId)
        }
      } catch (err) {
        stopSessionPoll(sessionId)
        markRerankRecommendError(sessionId, err?.message || '精排状态查询失败')
        notifyListeners(sessionId, 'onError', err)
      }
    }

    const timer = setInterval(tick, RERANK_POLL_INTERVAL_MS)
    pollState.timer = timer
    activeSessionPolls.set(sessionId, pollState)
    tick()
    return
  }

  const existing = getHrRecommendTasks().find((t) => t.sessionId === sessionId && t.startedAt)
  if (existing?.startedAt) {
    const pollState = activeSessionPolls.get(sessionId)
    if (pollState && pollState.startedAt > existing.startedAt) {
      pollState.startedAt = existing.startedAt
    }
  }
}

/** 页面级监听：仅订阅回调，不拥有轮询生命周期 */
export function subscribeSessionRerank(sessionId, callbacks = {}) {
  if (!sessionId) return () => {}
  if (!sessionListeners.has(sessionId)) {
    sessionListeners.set(sessionId, new Set())
  }
  sessionListeners.get(sessionId).add(callbacks)
  ensureSessionRerankPoll(sessionId)

  return () => {
    sessionListeners.get(sessionId)?.delete(callbacks)
  }
}

/** @deprecated 使用 subscribeSessionRerank */
export function watchSessionRerank(sessionId, callbacks = {}) {
  return subscribeSessionRerank(sessionId, callbacks)
}

/** 启动时：恢复进行中的精排轮询，并修正已完成但未更新的队列项 */
export async function resumeAllSessionRerankPolls() {
  const processing = getHrRecommendTasks().filter(
    (t) => t.phase === 'rerank' && t.status === 'processing' && t.sessionId
  )

  for (const task of processing) {
    try {
      const res = await getRecommendSessionStatus(task.sessionId)
      const status = res.session_status || res.sessionStatus
      if (status === 'rerank_ready') {
        handleRerankReady(task.sessionId, res)
        continue
      }
      if (status === 'rerank_queued' || status === 'reranking') {
        ensureSessionRerankPoll(task.sessionId)
        continue
      }
      if (status === 'coarse_ready') {
        markRerankRecommendError(task.sessionId, '精排未完成')
      }
    } catch {
      ensureSessionRerankPoll(task.sessionId)
    }
  }
}
