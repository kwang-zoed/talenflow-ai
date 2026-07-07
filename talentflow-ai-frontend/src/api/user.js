import request from '../utils/request'
import { pollTaskResult, normalizeTaskStatus, createProcessingStatusHandler } from '../utils/taskPoller'

export function getUserProfile() {
  return request({ url: '/user/profile', method: 'get' })
}

export function updateUserProfile(data) {
  return request({ url: '/user/profile', method: 'put', data })
}

export function getTaskList(params) {
  return request({
    url: '/user/tasks/',
    method: 'get',
    params,
  })
}

export function getTaskDetail(taskId) {
  return request({
    url: `/user/tasks/${taskId}`,
    method: 'get',
  })
}

export function applyTask(taskId) {
  return request({
    url: `/user/tasks/${taskId}/apply`,
    method: 'post',
  })
}

export function smartApply(data) {
  return request({
    url: '/user/smart-apply',
    method: 'post',
    data,
  })
}

export const submitSmartApply = (payload) => {
  return request({
    url: '/user/smart-apply/submit',
    method: 'post',
    data: payload,
  })
}

export const getSmartApplyStatus = (taskId) => {
  return request({
    url: `/user/smart-apply/status/${taskId}`,
    method: 'get',
    headers: { 'Cache-Control': 'no-cache', 'Pragma': 'no-cache' },
  })
}

export const getSmartApplyThread = (threadId, includeDetails = false) => {
  return request({
    url: `/user/smart-apply/thread/${threadId}`,
    method: 'get',
    params: includeDetails ? { include_details: true } : undefined,
    headers: { 'Cache-Control': 'no-cache', 'Pragma': 'no-cache' },
  })
}

export const resumeSmartApplyThread = (threadId, updates = {}) => {
  return request({
    url: `/user/smart-apply/thread/${threadId}/resume`,
    method: 'post',
    data: { updates },
    timeout: 180000,
  })
}

export const pollSmartApplyResult = (taskId, maxTime = 300000) => {
  return pollTaskResult({
    getStatus: async () => normalizeTaskStatus(await getSmartApplyStatus(taskId)),
    maxTime,
    handleStatus: (data) => {
      if (data.status === 'success') {
        return { resolve: data.data }
      }
      if (data.status === 'interrupted') {
        return {
          resolve: {
            __interrupted: true,
            threadId: data.thread_id,
            taskId,
            reviewType: data.review_type,
            reviewMessage: data.review_message || data.message,
            stage: data.stage,
            percent: data.percent,
          },
        }
      }
      if (data.status === 'processing') {
        return 'continue'
      }
      return { reject: new Error(data.message || '智能投递失败') }
    },
  })
}

const unwrap = (res) => {
  if (!res || typeof res !== 'object') return res
  if (res.session_id != null || res.task_id != null) return res
  if (res.data?.session_id != null || res.data?.task_id != null) return res.data
  return res
}

export const createJobRecommendSession = (pageSize = 10) => {
  return request({
    url: '/user/recommend/session',
    method: 'post',
    data: { page_size: pageSize },
  }).then(unwrap)
}

export const getJobRecommendSessionMore = (sessionId, excludeIds = [], limit = 10) => {
  const exclude_ids = excludeIds.filter(Boolean).join(',')
  return request({
    url: `/user/recommend/session/${sessionId}/more`,
    method: 'get',
    params: { exclude_ids, limit },
  }).then(unwrap)
}

export const getJobRecommendSessionStatus = (sessionId) => {
  return request({
    url: `/user/recommend/session/${sessionId}/status`,
    method: 'get',
    skipGlobalError: true,
  }).then(unwrap)
}

export const applyJobRecommendSessionRerank = (sessionId, limit = 10) => {
  return request({
    url: `/user/recommend/session/${sessionId}/apply-rerank`,
    method: 'post',
    params: { limit },
    skipGlobalError: true,
  }).then(unwrap)
}

export const submitRecommendTask = (userId) => {
  return new Promise((resolve, reject) => {
    request({
      url: '/user/recommend/submit',
      method: 'post',
      data: { user_id: userId, top_k: 5 },
    })
      .then((response) => {
        const res = response.data?.task_id ? response.data : response
        resolve(res)
      })
      .catch(reject)
  })
}

export const pollRecommendResult = (taskId, maxTime = 120000) => {
  return pollTaskResult({
    getStatus: async () => {
      const response = await request({
        url: `/user/recommend/status/${taskId}`,
        method: 'get',
        headers: { 'Cache-Control': 'no-cache', 'Pragma': 'no-cache' },
      })
      return normalizeTaskStatus(response)
    },
    maxTime,
    handleStatus: createProcessingStatusHandler(),
  })
}

export const checkRecommendStatus = async (taskId) => {
  const response = await request({
    url: `/user/recommend/status/${taskId}`,
    method: 'get',
    headers: { 'Cache-Control': 'no-cache', 'Pragma': 'no-cache' },
  })
  return normalizeTaskStatus(response)
}

export function getMyApplications() {
  return request({
    url: '/user/applications',
    method: 'get',
  })
}

export function getJobList(params) {
  return request({
    url: '/user/job-list',
    method: 'get',
    params,
  })
}
