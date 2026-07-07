import request from '../utils/request'
import { pollTaskResult, normalizeTaskStatus, createProcessingStatusHandler } from '../utils/taskPoller'

const hrRequest = (opts) => request({ ...opts, url: '/hr' + opts.url })

const unwrap = (res) => {
  if (!res || typeof res !== 'object') return res
  if (res.session_id != null || res.task_id != null) return res
  if (res.data?.session_id != null || res.data?.task_id != null) return res.data
  return res
}

export const createRecommendSession = (jobId, pageSize = 10) => {
  return hrRequest({
    url: '/recommend/session',
    method: 'post',
    data: { job_id: jobId, page_size: pageSize },
  }).then(unwrap)
}

export const getRecommendSessionMore = (sessionId, excludeIds = [], limit = 10) => {
  const exclude_ids = excludeIds.filter(Boolean).join(',')
  return hrRequest({
    url: `/recommend/session/${sessionId}/more`,
    method: 'get',
    params: { exclude_ids, limit },
  }).then(unwrap)
}

export const getRecommendSessionStatus = (sessionId) => {
  return hrRequest({
    url: `/recommend/session/${sessionId}/status`,
    method: 'get',
    skipGlobalError: true,
  }).then(unwrap)
}

export const applyRecommendSessionRerank = (sessionId, limit = 10) => {
  return hrRequest({
    url: `/recommend/session/${sessionId}/apply-rerank`,
    method: 'post',
    params: { limit },
    skipGlobalError: true,
  }).then(unwrap)
}

/** @deprecated 旧版 Celery 全量推荐（任务队列兼容） */
export const checkResumeRecommendStatus = async (taskId, jobId = null, topK = 5) => {
  const response = await hrRequest({
    url: `/recommend/status/${taskId}`,
    method: 'get',
    params: jobId != null ? { job_id: jobId, top_k: topK } : undefined,
    headers: { 'Cache-Control': 'no-cache', 'Pragma': 'no-cache' },
  })
  return normalizeTaskStatus(unwrap(response))
}

/** @deprecated */
export const pollResumeRecommendResult = (taskId, jobId = null, maxTime = 120000, topK = 5) => {
  return pollTaskResult({
    getStatus: async () => checkResumeRecommendStatus(taskId, jobId, topK),
    maxTime,
    handleStatus: createProcessingStatusHandler(),
  })
}

/** @deprecated 旧版 Celery 全量推荐 */
export const submitResumeRecommendTask = (jobId, topK = 5) => {
  return hrRequest({
    url: '/recommend/submit',
    method: 'post',
    data: { job_id: jobId, top_k: topK },
  }).then((response) => (response.data?.task_id ? response.data : response))
}

export const getHrResumeDetail = (resumeId) => {
  return hrRequest({
    url: `/resumes/${resumeId}`,
    method: 'get',
  })
}

export const getHrJobs = (params) => {
  return request({
    url: '/mentor/jobs',
    method: 'get',
    params,
  })
}
