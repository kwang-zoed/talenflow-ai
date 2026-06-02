/**
 * 将 pollTaskResult 与 GlobalTaskProgress（parseProgress）对接
 */

export function wirePollToProgress(pollPromise, progressRef, options = {}) {
  const {
    showMessage,
    taskType = 'parse',
    completeHint,
    completeButtonText,
    reset = true,
    pendingReviewCount,
  } = options

  if (progressRef && showMessage) {
    progressRef.show(showMessage, {
      taskType,
      completeHint,
      completeButtonText,
      reset,
      pendingReviewCount,
    })
  }

  pollPromise.onProgress = (statusData) => {
    progressRef?.update({
      ...statusData,
      taskType: statusData.taskType ?? taskType,
    })
  }

  return pollPromise
}

/**
 * 从 localStorage 恢复未完成任务并轮询
 */
export async function resumeStoredTaskPoll({
  storageKey,
  resultStorageKey,
  ttlMs = 600000,
  fetchStatus,
  createPoll,
  progressRef,
  buildCompleteMessage,
  onSuccess,
}) {
  try {
    const savedStr = localStorage.getItem(storageKey)
    if (!savedStr) return null

    const saved = JSON.parse(savedStr)
    if (!saved?.taskId || Date.now() - (saved.timestamp || 0) > ttlMs) {
      localStorage.removeItem(storageKey)
      return null
    }

    const current = await fetchStatus(saved.taskId)

    if (current.status === 'success') {
      if (resultStorageKey && current.data) {
        localStorage.setItem(
          resultStorageKey,
          JSON.stringify({ data: current.data, timestamp: Date.now() })
        )
      }
      const message = buildCompleteMessage?.(saved, current.data, true) || '任务已完成'
      progressRef?.show(message, { taskType: saved.taskType || 'parse' })
      progressRef?.update({
        status: 'success',
        message,
        percent: 100,
        data: current.data,
        taskType: saved.taskType || 'parse',
      })
      onSuccess?.(current.data, saved)
      return current.data
    }

    if (current.status === 'error') {
      localStorage.removeItem(storageKey)
      return null
    }

    const poll = createPoll(saved.taskId)

    wirePollToProgress(poll, progressRef, {
      showMessage: saved.filename
        ? `正在后台处理: ${saved.filename}`
        : '任务进行中...',
      taskType: saved.taskType || 'parse',
    })

    const baseOnProgress = poll.onProgress
    poll.onProgress = (statusData) => {
      baseOnProgress?.(statusData)
      if (statusData.status === 'success' && statusData.data) {
        if (resultStorageKey) {
          localStorage.setItem(
            resultStorageKey,
            JSON.stringify({ data: statusData.data, timestamp: Date.now() })
          )
        }
        localStorage.removeItem(storageKey)
      }
    }

    const finalData = await poll
    onSuccess?.(finalData, saved)
    return finalData
  } catch (err) {
    console.warn('[resumeStoredTaskPoll]', err.message)
    return null
  }
}

export function saveTaskToStorage(storageKey, payload) {
  localStorage.setItem(
    storageKey,
    JSON.stringify({ ...payload, timestamp: Date.now() })
  )
}

export function clearTaskStorage(storageKey, resultKey) {
  localStorage.removeItem(storageKey)
  if (resultKey) localStorage.removeItem(resultKey)
}
