// api/job.js
import request from '../utils/request'
import { normalizeTaskStatus } from '../utils/taskPoller'

function createParsePoll(getStatusFn, taskId, maxTime, successMessage) {
  let onProgress = null
  let cancelled = false
  let timerId = null

  const promise = new Promise((resolve, reject) => {
    const startTime = Date.now()

    const attempt = async (delay = 1500) => {
      if (cancelled) return reject(new Error('轮询已取消'))
      if (Date.now() - startTime > maxTime) return reject(new Error('解析超时'))

      try {
        const response = await getStatusFn(taskId)
        const data = normalizeTaskStatus(response)

        if (data.status === 'success') {
          onProgress?.({
            status: 'success',
            message: successMessage,
            percent: 100,
            data: data.data,
          })
          resolve(data.data)
          return
        }
        if (data.status === 'processing') {
          onProgress?.(data)
          const next = Math.min(delay * 1.5, 5000)
          timerId = setTimeout(() => attempt(next), delay)
          return
        }
        reject(new Error(data.message || '解析失败'))
      } catch (e) {
        reject(e)
      }
    }

    attempt()
  })

  promise.cancel = () => {
    cancelled = true
    if (timerId) clearTimeout(timerId)
  }

  Object.defineProperty(promise, 'onProgress', {
    get: () => onProgress,
    set: (fn) => {
      onProgress = fn
    },
  })

  return promise
}

export const submitParseTask = (file, isBatch = false) => {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('is_batch', isBatch)
  return request({
    url: '/admin/jobs/parse/submit',
    method: 'POST',
    headers: { 'Content-Type': 'multipart/form-data' },
    data: formData,
  })
}

export const getParseTaskStatus = (taskId) => {
  return request({
    url: `/admin/jobs/parse/status/${taskId}`,
    method: 'GET',
    headers: { 'Cache-Control': 'no-cache' },
  })
}

export const pollParseTaskResult = (taskId, maxTime = 300000) => {
  return createParsePoll(
    getParseTaskStatus,
    taskId,
    maxTime,
    '解析完成，点击前往填充表单'
  )
}

const hrRequest = (opts) => request({ ...opts, url: '/mentor' + opts.url })

export const hrSubmitParseTask = (file, isBatch = false) => {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('is_batch', isBatch)
  return hrRequest({
    url: '/jobs/parse/submit',
    method: 'POST',
    headers: { 'Content-Type': 'multipart/form-data' },
    data: formData,
  })
}

export const hrGetParseTaskStatus = (taskId) => {
  return hrRequest({
    url: `/jobs/parse/status/${taskId}`,
    method: 'GET',
    headers: { 'Cache-Control': 'no-cache' },
  })
}

export const hrPollParseTaskResult = (taskId, maxTime = 300000) => {
  return createParsePoll(
    hrGetParseTaskStatus,
    taskId,
    maxTime,
    '解析完成，点击前往填充表单'
  )
}

export { createParsePoll }
