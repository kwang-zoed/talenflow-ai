import {
  pollResumeRecommendResult,
  checkResumeRecommendStatus,
} from '@/api/hrRecommend'
import { normalizeTaskStatus } from '@/utils/taskPoller'

export const HR_RESUME_RECOMMEND_TASKS_KEY = 'talentflow_hr_resume_recommend_tasks'
/** @deprecated 旧版单任务存储，启动时迁移后删除 */
export const HR_RESUME_RECOMMEND_STORAGE_KEY = 'talentflow_hr_resume_recommend_task'

const PROCESSING_TTL_MS = 600000
const COMPLETED_TTL_MS = 24 * 60 * 60 * 1000
const ESTIMATED_MAX_TIME = 120000

function readTasksRaw() {
  try {
    const raw = localStorage.getItem(HR_RESUME_RECOMMEND_TASKS_KEY)
    if (!raw) return []
    const list = JSON.parse(raw)
    return Array.isArray(list) ? list : []
  } catch {
    return []
  }
}

function isTaskVisible(task) {
  if (!task?.taskId) return false
  const ts = task.timestamp || 0
  if (task.status === 'success' || task.status === 'error') {
    return Date.now() - (task.completedAt || ts) < COMPLETED_TTL_MS
  }
  return Date.now() - ts < PROCESSING_TTL_MS
}

/** @type {Map<string, { promise: Promise<any>, cancel: () => void }>} */
const activePolls = new Map()
/** @type {Set<(tasks: any[]) => void>} */
const queueListeners = new Set()

function notifyQueue() {
  const tasks = getHrRecommendTasks()
  queueListeners.forEach((fn) => fn(tasks))
}

export function subscribeHrRecommendQueue(callback) {
  queueListeners.add(callback)
  callback(getHrRecommendTasks())
  return () => queueListeners.delete(callback)
}

export function getHrRecommendTasks() {
  return readTasksRaw().filter(isTaskVisible)
}

/** 取某职位最新一条推荐任务（同职位仅保留一条会话任务） */
export function getHrRecommendTaskByJobId(jobId) {
  const id = Number(jobId)
  const tasks = getHrRecommendTasks()
    .filter((t) => Number(t.jobId) === id)
    .sort((a, b) => (b.timestamp || 0) - (a.timestamp || 0))
  if (!tasks.length) return null
  const sessionTask = tasks.find((t) => t.taskId?.startsWith('session:'))
  if (sessionTask) return sessionTask
  const success = tasks.find((t) => t.status === 'success')
  if (success) return success
  const processing = tasks.find((t) => t.status === 'processing')
  if (processing) return processing
  return tasks[0]
}

/** 读取已完成的推荐结果（队列持久化 + session 缓存） */
export function loadRecommendResultForJob(jobId) {
  const queueTask = getHrRecommendTaskByJobId(jobId)
  if (queueTask?.status === 'success' && Array.isArray(queueTask.result)) {
    return { data: queueTask.result, taskId: queueTask.taskId, source: 'queue' }
  }
  try {
    const raw = sessionStorage.getItem(`resume_recommend_${jobId}_result`)
    const taskId = sessionStorage.getItem(`resume_recommend_${jobId}_task_id`)
    if (raw) {
      return { data: JSON.parse(raw), taskId, source: 'session' }
    }
  } catch (_) {}
  return null
}

function saveTasks(tasks) {
  localStorage.setItem(HR_RESUME_RECOMMEND_TASKS_KEY, JSON.stringify(tasks))
  notifyQueue()
}

function cacheResultForJob(jobId, taskId, data) {
  try {
    sessionStorage.setItem(`resume_recommend_${jobId}_task_id`, taskId)
    sessionStorage.setItem(`resume_recommend_${jobId}_result`, JSON.stringify(data))
    sessionStorage.setItem(`resume_recommend_${jobId}_time`, String(Date.now()))
  } catch (_) {}
}

function markTaskSuccess(taskId, jobId, data, jobTitle) {
  const count = Array.isArray(data) ? data.length : 0
  updateHrRecommendTask(taskId, {
    status: 'success',
    percent: 100,
    resultCount: count,
    result: data,
    completedAt: Date.now(),
    jobTitle,
  })
  cacheResultForJob(jobId, taskId, data)
}

export function upsertHrRecommendTask(task) {
  const tasks = readTasksRaw()
  const idx = tasks.findIndex((t) => t.taskId === task.taskId)
  const next = {
    status: 'processing',
    percent: 0,
    ...task,
    timestamp: Date.now(),
    startedAt: task.startedAt || Date.now(),
  }
  if (idx >= 0) {
    tasks[idx] = { ...tasks[idx], ...next }
  } else {
    tasks.unshift(next)
  }
  saveTasks(tasks)
}

export function updateHrRecommendTask(taskId, patch) {
  const tasks = readTasksRaw()
  const idx = tasks.findIndex((t) => t.taskId === taskId)
  if (idx === -1) return
  tasks[idx] = { ...tasks[idx], ...patch, timestamp: Date.now() }
  saveTasks(tasks)
}

export function dismissHrRecommendTask(taskId) {
  activePolls.get(taskId)?.cancel?.()
  activePolls.delete(taskId)
  saveTasks(readTasksRaw().filter((t) => t.taskId !== taskId))
}

/** 移除同职位会话任务（保留 keepTaskId），并清理旧版 coarse/rerank 双任务 */
export function dismissJobSessionTasks(jobId, { keepTaskId = null, sessionId = null } = {}) {
  const id = Number(jobId)
  const legacyIds = sessionId
    ? [`session:${sessionId}:coarse`, `session:${sessionId}:rerank`]
    : []
  const removeIds = new Set(
    readTasksRaw()
      .filter((t) => {
        if (!t.taskId?.startsWith('session:')) return false
        if (keepTaskId && t.taskId === keepTaskId) return false
        if (legacyIds.includes(t.taskId)) return true
        return Number(t.jobId) === id
      })
      .map((t) => t.taskId)
  )
  if (!removeIds.size) return
  removeIds.forEach((tid) => {
    activePolls.get(tid)?.cancel?.()
    activePolls.delete(tid)
  })
  saveTasks(readTasksRaw().filter((t) => !removeIds.has(t.taskId)))
}

/** 启动时合并旧版双任务，同职位只保留最新一条会话任务 */
export function normalizeRecommendTaskQueue() {
  const raw = readTasksRaw()
  const legacyRe = /^session:([^:]+):(coarse|rerank)$/
  const sessionTasks = new Map()
  const others = []

  for (const t of raw) {
    const legacy = t.taskId?.match(legacyRe)
    if (legacy) {
      const sid = legacy[1]
      const phase = legacy[2]
      if (!sessionTasks.has(sid)) {
        sessionTasks.set(sid, { sessionId: sid, coarse: null, rerank: null, jobId: t.jobId })
      }
      const entry = sessionTasks.get(sid)
      entry[phase] = t
      if (t.jobId != null) entry.jobId = t.jobId
      continue
    }
    if (t.taskId?.startsWith('session:') && t.sessionId) {
      sessionTasks.set(t.sessionId, {
        sessionId: t.sessionId,
        unified: t,
        jobId: t.jobId,
      })
      continue
    }
    others.push(t)
  }

  const merged = [...others]
  const seenJobIds = new Set()
  const seenSessionIds = new Set()

  const sortedSessions = [...sessionTasks.values()].sort((a, b) => {
    const ta = a.unified?.timestamp || a.rerank?.timestamp || a.coarse?.timestamp || 0
    const tb = b.unified?.timestamp || b.rerank?.timestamp || b.coarse?.timestamp || 0
    return tb - ta
  })

  for (const entry of sortedSessions) {
    const jobKey = entry.jobId != null ? Number(entry.jobId) : null
    if (jobKey != null && seenJobIds.has(jobKey)) continue
    if (seenSessionIds.has(entry.sessionId)) continue
    seenSessionIds.add(entry.sessionId)
    if (jobKey != null) seenJobIds.add(jobKey)

    if (entry.unified) {
      merged.push(entry.unified)
      continue
    }

    const pick = entry.rerank || entry.coarse
    if (!pick) continue
    merged.push({
      ...pick,
      taskId: `session:${entry.sessionId}`,
      sessionId: entry.sessionId,
      phase: entry.rerank ? (entry.rerank.status === 'success' ? 'rerank' : 'rerank') : 'coarse',
    })
  }

  if (merged.length !== raw.length || merged.some((t, i) => t.taskId !== raw[i]?.taskId)) {
    saveTasks(merged)
  }
}

export function clearHrRecommendTasks() {
  activePolls.forEach((p) => p.cancel?.())
  activePolls.clear()
  localStorage.removeItem(HR_RESUME_RECOMMEND_TASKS_KEY)
  localStorage.removeItem(HR_RESUME_RECOMMEND_STORAGE_KEY)
  notifyQueue()
}

export function getHrRecommendPollPromise(taskId) {
  return activePolls.get(taskId)?.promise
}

function cancelProcessingTasksForJob(jobId, exceptTaskId) {
  getHrRecommendTasks()
    .filter((t) => t.jobId === jobId && t.status === 'processing' && t.taskId !== exceptTaskId)
    .forEach((t) => dismissHrRecommendTask(t.taskId))
}

function runPollForTask({ taskId, jobId, jobTitle }) {
  const existing = activePolls.get(taskId)
  if (existing) return existing.promise

  const pollStart = Date.now()
  const pollPromise = pollResumeRecommendResult(taskId, jobId, ESTIMATED_MAX_TIME)

  pollPromise.onProgress = () => {
    const percent = Math.min(92, Math.floor(((Date.now() - pollStart) / ESTIMATED_MAX_TIME) * 92))
    updateHrRecommendTask(taskId, { percent, status: 'processing', jobTitle })
  }

  const wrapped = pollPromise
    .then((data) => {
      markTaskSuccess(taskId, jobId, data, jobTitle)
      window.dispatchEvent(
        new CustomEvent('globalResumeRecommendComplete', { detail: { jobId, taskId, data } })
      )
      activePolls.delete(taskId)
      return data
    })
    .catch((err) => {
      activePolls.delete(taskId)
      if (err.message !== '轮询已取消') {
        updateHrRecommendTask(taskId, {
          status: 'error',
          error: err.message || '推荐失败',
          jobTitle,
        })
      }
      throw err
    })

  activePolls.set(taskId, {
    promise: wrapped,
    cancel: () => pollPromise.cancel?.(),
  })
  return wrapped
}

/**
 * 启动或接入简历推荐轮询（同 taskId 复用，不同职位并行）
 */
export function startHrResumeRecommendPoll({
  taskId,
  jobId,
  jobTitle,
  replaceSameJob = true,
}) {
  if (replaceSameJob) {
    cancelProcessingTasksForJob(jobId, taskId)
  }

  upsertHrRecommendTask({
    taskId,
    jobId,
    jobTitle: jobTitle || `职位 #${jobId}`,
    status: 'processing',
    percent: 0,
  })

  return runPollForTask({ taskId, jobId, jobTitle: jobTitle || `职位 #${jobId}` })
}

function migrateLegacySingleTaskStorage() {
  try {
    const raw = localStorage.getItem(HR_RESUME_RECOMMEND_STORAGE_KEY)
    if (!raw) return
    const saved = JSON.parse(raw)
    if (saved?.taskId && saved?.jobId) {
      upsertHrRecommendTask({
        taskId: saved.taskId,
        jobId: saved.jobId,
        jobTitle: saved.jobTitle,
        status: 'processing',
      })
    }
    localStorage.removeItem(HR_RESUME_RECOMMEND_STORAGE_KEY)
  } catch (_) {}
}

export async function resumeAllHrResumeRecommendPolls() {
  migrateLegacySingleTaskStorage()

  const tasks = getHrRecommendTasks()
  for (const task of tasks) {
    if (task.status === 'success' || task.status === 'error') continue
    if (activePolls.has(task.taskId)) continue

    try {
      const current = normalizeTaskStatus(
        await checkResumeRecommendStatus(task.taskId, task.jobId)
      )
      if (current.status === 'success' && current.data) {
        markTaskSuccess(task.taskId, task.jobId, current.data, task.jobTitle)
        continue
      }
      if (current.status === 'error') {
        updateHrRecommendTask(task.taskId, {
          status: 'error',
          error: current.message || '推荐失败',
        })
        continue
      }
      runPollForTask(task)
    } catch (err) {
      console.warn('[resumeAllHrResumeRecommendPolls]', err.message)
    }
  }
}
