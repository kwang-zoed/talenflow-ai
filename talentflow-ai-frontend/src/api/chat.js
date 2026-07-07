import axios from 'axios'
import { ElMessage } from 'element-plus'
import { promptRelogin } from '@/utils/unauthorized'
import {
  ensureValidAccessToken,
  getAccessToken,
  refreshAccessToken,
  isAuthRefreshRequest,
} from '@/utils/authToken'

const service = axios.create({
  baseURL: '/api/v1',
  timeout: 60000,
  headers: {
    'Content-Type': 'application/json',
  },
})

service.interceptors.request.use(
  async (config) => {
    if (!isAuthRefreshRequest(config)) {
      try {
        await ensureValidAccessToken()
      } catch (e) {
        console.warn('[auth] proactive refresh failed', e)
      }
    }

    const token = getAccessToken()
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

service.interceptors.response.use(
  (response) => response,
  async (error) => {
    const { response, config } = error

    if (response?.status === 401 && config && !config._retried && !isAuthRefreshRequest(config)) {
      config._retried = true
      try {
        await refreshAccessToken()
        config.headers.Authorization = `Bearer ${getAccessToken()}`
        return service(config)
      } catch (refreshErr) {
        promptRelogin()
        return Promise.reject(refreshErr)
      }
    }

    console.error('API Error:', error)
    if (response?.status === 401) {
      promptRelogin()
    } else {
      ElMessage.error(response?.data?.message || response?.data?.detail || '网络请求失败')
    }
    return Promise.reject(error)
  }
)

/**
 * 流式对话接口
 */
export function chatStream(data, onMessage, onDone) {
  return service({
    url: '/chat/stream',
    method: 'post',
    data,
    responseType: 'text',
    onDownloadProgress: (progressEvent) => {
      const event = progressEvent.event
      if (event?.target?.responseText) {
        const text = event.target.responseText
        const lines = text.split('\n')
        const lastLine = lines[lines.length - 1]

        if (lastLine.startsWith('data:')) {
          const jsonData = lastLine.replace('data:', '').trim()
          if (jsonData) {
            try {
              const parsed = JSON.parse(jsonData)
              onMessage(parsed.content || parsed)
            } catch {
              onMessage(jsonData)
            }
          }
        }
      }
    },
  })
    .then(() => {
      onDone?.()
    })
    .catch((err) => {
      onDone?.(err)
    })
}

export function getHistoryList() {
  return service({
    url: '/chat/history',
    method: 'get',
  })
}

export function createNewChat() {
  return service({
    url: '/chat/new',
    method: 'post',
  })
}
