import request from '../utils/request'
import { pollTaskResult, normalizeTaskStatus, createProcessingStatusHandler } from '../utils/taskPoller'

export const submitResumeParseTask = (file) => {
  const formData = new FormData()
  formData.append('file', file)
  return request({
    url: '/admin/resumes/parse/submit',
    method: 'POST',
    headers: { 'Content-Type': 'multipart/form-data' },
    data: formData,
  })
}

export const getResumeParseStatus = (taskId) => {
  return request({
    url: `/admin/resumes/parse/status/${taskId}`,
    method: 'GET',
    headers: { 'Cache-Control': 'no-cache' },
  })
}

export const pollResumeParseResult = (taskId, maxTime = 300000) => {
  return pollTaskResult({
    getStatus: async () => normalizeTaskStatus(await getResumeParseStatus(taskId)),
    maxTime,
    handleStatus: createProcessingStatusHandler(),
  })
}
