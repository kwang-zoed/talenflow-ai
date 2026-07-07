import axios from 'axios'
import { ElMessage } from 'element-plus'
import { promptRelogin } from './unauthorized'
import {
  ensureValidAccessToken,
  getAccessToken,
  refreshAccessToken,
  isAuthRefreshRequest,
} from './authToken'

const service = axios.create({
  baseURL: '/api/v1',
  timeout: 60000,
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
  (response) => response.data,
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

    if (response) {
      if (config?.skipGlobalError) {
        return Promise.reject(error)
      }
      switch (response.status) {
        case 401:
          promptRelogin()
          break
        case 403:
          ElMessage.error('权限不足，无法执行此操作')
          break
        case 404:
          ElMessage.error('请求资源不存在')
          break
        case 500:
          ElMessage.error('服务器内部错误')
          break
        default:
          ElMessage.error(response.data?.detail || '请求失败')
      }
    } else {
      ElMessage.error('网络连接失败，请检查网络')
    }

    return Promise.reject(error)
  }
)

export default service
