import { ElMessage } from 'element-plus'
import { getSmartApplyStatus, submitSmartApply, pollSmartApplyResult } from '../api/user'

export const SMART_APPLY_TASKS_KEY = 'talentflow_smart_apply_tasks'
const TASK_TTL_MS = 600000

/** @typedef {{ taskId: string, threadId?: string, jobTitle: string, timestamp: number, awaitingReview?: boolean, lastPercent?: number, reviewType?: string }} SmartApplyTask */

/** @returns {SmartApplyTask[]} */
export function getActiveSmartApplyTasks() {
  try {
    const raw = localStorage.getItem(SMART_APPLY_TASKS_KEY)
    if (!raw) return []
    const list = JSON.parse(raw)
    if (!Array.isArray(list)) return []
    return list.filter((t) => t?.taskId && Date.now() - (t.timestamp || 0) < TASK_TTL_MS)
  } catch {
    return []
  }
}

function saveActiveTasks(tasks) {
  localStorage.setItem(SMART_APPLY_TASKS_KEY, JSON.stringify(tasks))
}

export function addActiveSmartApplyTask(task) {
  const tasks = getActiveSmartApplyTasks().filter((t) => t.taskId !== task.taskId)
  tasks.push(task)
  saveActiveTasks(tasks)
}

export function updateActiveSmartApplyTask(taskId, patch) {
  const tasks = getActiveSmartApplyTasks()
  const idx = tasks.findIndex((t) => t.taskId === taskId)
  if (idx === -1) return
  tasks[idx] = { ...tasks[idx], ...patch, timestamp: Date.now() }
  saveActiveTasks(tasks)
}

export function removeActiveSmartApplyTask(taskId) {
  saveActiveTasks(getActiveSmartApplyTasks().filter((t) => t.taskId !== taskId))
}

function getAwaitingReviewTasks() {
  return getActiveSmartApplyTasks().filter((t) => t.awaitingReview && t.threadId)
}

/** @type {null | import('vue').Ref} */
let reviewDialogRef = null
let reviewDialogBusy = false
/** @type {any} */
let lastTaskProgress = null

export function registerSmartApplyReviewDialog(dialogRef) {
  reviewDialogRef = dialogRef
}

function rememberTaskProgress(taskProgress) {
  if (taskProgress) lastTaskProgress = taskProgress
}

function buildReviewPayload(task, reviewType, reviewMessage) {
  return {
    threadId: task.threadId,
    taskId: task.taskId,
    jobTitle: task.jobTitle,
    reviewType: reviewType || task.reviewType,
    reviewMessage,
    onComplete: () => {
      removeActiveSmartApplyTask(task.taskId)
      reviewDialogBusy = false
      ElMessage.success(`「${task.jobTitle}」投递成功`)
      syncProgressBar(lastTaskProgress)
      showAllSmartApplyComplete(lastTaskProgress)
      processReviewQueue(lastTaskProgress)
    },
    onInterrupted: (res) => {
      updateActiveSmartApplyTask(task.taskId, {
        awaitingReview: true,
        threadId: task.threadId,
        reviewType: res.review_type || task.reviewType,
        lastPercent: res.percent || task.lastPercent || 60
      })
      syncProgressBar(lastTaskProgress)
    },
    onDismiss: () => {
      reviewDialogBusy = false
    }
  }
}

function openReviewDialog(payload) {
  if (!reviewDialogRef?.value?.open) {
    ElMessage.warning('请刷新页面后，在顶部进度条点击「审核待办」')
    return false
  }
  reviewDialogRef.value.open({
    ...payload,
    onComplete: (...args) => {
      payload.onComplete?.(...args)
    },
    onInterrupted: (...args) => {
      payload.onInterrupted?.(...args)
    },
    onDismiss: () => {
      payload.onDismiss?.()
    }
  })
  return true
}

/** 按队列依次打开待审核任务，避免多任务互相覆盖弹窗 */
export function processReviewQueue(taskProgress) {
  rememberTaskProgress(taskProgress)
  const tp = taskProgress || lastTaskProgress

  if (reviewDialogBusy) {
    syncProgressBar(tp)
    return
  }

  const awaiting = getAwaitingReviewTasks()
  if (!awaiting.length) {
    syncProgressBar(tp)
    return
  }

  if (awaiting.length > 1) {
    ElMessage.info(`共有 ${awaiting.length} 个任务待审核，将依次处理`)
  }

  const task = awaiting[0]
  reviewDialogBusy = true
  const opened = openReviewDialog(
    buildReviewPayload(task, task.reviewType, '请确认后继续投递')
  )
  if (!opened) {
    reviewDialogBusy = false
  }
  syncProgressBar(tp)
}

function markTaskInterrupted({ taskId, threadId, jobTitle, reviewType, reviewMessage, taskProgress }) {
  updateActiveSmartApplyTask(taskId, {
    threadId,
    awaitingReview: true,
    reviewType,
    lastPercent: reviewType === 'cover_letter' ? 80 : 40
  })
  syncProgressBar(taskProgress)

  if (reviewDialogBusy) {
    const count = getAwaitingReviewTasks().length
    if (count > 1) {
      ElMessage.info(`「${jobTitle}」已就绪，当前有 ${count} 个任务待审核`)
    }
    return
  }
  processReviewQueue(taskProgress)
}

function syncProgressBar(taskProgress) {
  if (!taskProgress) return

  const tasks = getActiveSmartApplyTasks()
  if (!tasks.length) {
    taskProgress.hide()
    return
  }

  const awaiting = tasks.filter((t) => t.awaitingReview)
  const running = tasks.filter((t) => !t.awaitingReview)
  const pendingReviewCount = awaiting.length

  let message
  let percent
  let status = 'processing'
  let completeHint = '可继续投递其他职位，任务在后台执行'

  if (awaiting.length > 0 && running.length > 0) {
    message = `${running.length} 个进行中，${awaiting.length} 个待审核`
    const allPercents = tasks.map((t) => t.lastPercent ?? (t.awaitingReview ? 40 : 10))
    percent = Math.round(allPercents.reduce((a, b) => a + b, 0) / allPercents.length)
    status = 'interrupted'
    completeHint = '点击「审核待办」处理等待确认的任务'
  } else if (awaiting.length > 0) {
    const names = awaiting
      .map((t) => t.jobTitle)
      .slice(0, 2)
      .join('、')
    message =
      awaiting.length === 1
        ? `待审核：${names}`
        : `${awaiting.length} 个任务待审核：${names}${awaiting.length > 2 ? '...' : ''}`
    percent = Math.max(...awaiting.map((t) => t.lastPercent || 40))
    status = 'interrupted'
    completeHint = '点击「审核待办」确认简历/求职信'
  } else if (running.length > 1) {
    message = `智能投递进行中（${running.length} 个任务）`
    percent = Math.round(
      running.reduce((sum, t) => sum + (t.lastPercent || 5), 0) / running.length
    )
  } else {
    message = `智能投递：${running[0]?.jobTitle || '职位'}`
    percent = running[0]?.lastPercent || 5
  }

  const barVisible = taskProgress.visible?.value ?? false
  if (!barVisible) {
    taskProgress.show(message, {
      reset: false,
      completeHint,
      completeButtonText: '',
      pendingReviewCount
    })
  }

  taskProgress.update({
    message,
    percent,
    status,
    completeHint,
    completeButtonText: '',
    pendingReviewCount
  })
}

function showAllSmartApplyComplete(taskProgress) {
  if (getActiveSmartApplyTasks().length > 0) return
  taskProgress?.show('智能投递已完成', {
    taskType: 'smart_apply',
    completeHint: '点击查看申请记录',
    completeButtonText: '查看申请记录',
    pendingReviewCount: 0,
  })
  taskProgress?.update({
    status: 'success',
    message: '智能投递已完成',
    percent: 100,
    taskType: 'smart_apply',
    completeHint: '点击查看申请记录',
    completeButtonText: '查看申请记录',
    pendingReviewCount: 0,
  })
}

function attachPollHandlers({ poll, taskId, threadId, jobTitle, taskProgress }) {
  poll.onProgress = (statusData) => {
    if (statusData.percent !== undefined) {
      updateActiveSmartApplyTask(taskId, { lastPercent: statusData.percent })
    }
    if (statusData.status !== 'interrupted') {
      syncProgressBar(taskProgress)
    }
  }

  poll
    .then((result) => {
      if (result?.__interrupted) {
        markTaskInterrupted({
          taskId,
          threadId: result.threadId || threadId,
          jobTitle,
          reviewType: result.reviewType,
          reviewMessage: result.reviewMessage,
          taskProgress
        })
        return
      }
      removeActiveSmartApplyTask(taskId)
      syncProgressBar(taskProgress)
      showAllSmartApplyComplete(taskProgress)
      ElMessage.success(`「${jobTitle}」投递成功`)
    })
    .catch((err) => {
      removeActiveSmartApplyTask(taskId)
      syncProgressBar(taskProgress)
      ElMessage.error(err.message || `「${jobTitle}」投递失败`)
    })
}

/**
 * 提交智能投递并在后台轮询，不阻塞调用方 UI。
 * @returns {Promise<{ taskId: string, threadId?: string }>}
 */
export async function startSmartApplyBackground({ payload, jobTitle, taskProgress }) {
  rememberTaskProgress(taskProgress)
  const submitRes = await submitSmartApply(payload)
  const taskId = submitRes?.task_id
  const threadId = submitRes?.thread_id
  if (!taskId) {
    throw new Error('未获取到任务 ID')
  }

  const title = jobTitle || '职位'
  addActiveSmartApplyTask({
    taskId,
    threadId,
    jobTitle: title,
    timestamp: Date.now(),
    awaitingReview: false,
    lastPercent: 5
  })

  syncProgressBar(taskProgress)

  const poll = pollSmartApplyResult(taskId, TASK_TTL_MS)
  attachPollHandlers({ poll, taskId, threadId, jobTitle: title, taskProgress })

  return { taskId, threadId }
}

async function resumeTaskPolling({ taskId, threadId, jobTitle, taskProgress }) {
  try {
    const status = await getSmartApplyStatus(taskId)
    if (status.percent !== undefined) {
      updateActiveSmartApplyTask(taskId, { lastPercent: status.percent })
    }
    if (status.status === 'interrupted') {
      markTaskInterrupted({
        taskId,
        threadId: status.thread_id || threadId,
        jobTitle,
        reviewType: status.review_type,
        reviewMessage: status.review_message || status.message,
        taskProgress
      })
      return
    }
    if (status.status === 'success') {
      removeActiveSmartApplyTask(taskId)
      syncProgressBar(taskProgress)
      return
    }
    if (status.status === 'error') {
      removeActiveSmartApplyTask(taskId)
      syncProgressBar(taskProgress)
      ElMessage.error(status.message || `「${jobTitle}」投递失败`)
      return
    }
  } catch {
    // 继续轮询
  }

  const poll = pollSmartApplyResult(taskId, TASK_TTL_MS)
  attachPollHandlers({ poll, taskId, threadId, jobTitle, taskProgress })
}

/** App 启动时恢复未完成的投递任务轮询 */
export function resumeSmartApplyPolling(taskProgress) {
  rememberTaskProgress(taskProgress)
  const tasks = getActiveSmartApplyTasks()
  if (!tasks.length || !taskProgress) return

  syncProgressBar(taskProgress)

  tasks.forEach(({ taskId, threadId, jobTitle, awaitingReview }) => {
    if (awaitingReview && threadId) {
      return
    }
    resumeTaskPolling({ taskId, threadId, jobTitle, taskProgress })
  })

  processReviewQueue(taskProgress)
}

/** 进度条「审核待办」按钮回调 */
export function openPendingSmartApplyReview(taskProgress) {
  rememberTaskProgress(taskProgress)
  reviewDialogBusy = false
  processReviewQueue(taskProgress || lastTaskProgress)
}
