import axios from 'axios'
import { ElMessage } from 'element-plus'

// 1. 创建 axios 实例
const service = axios.create({
  baseURL: '/api/v1', // 对应后端的 /api/v1 前缀
  timeout: 60000, // 流式对话可能较长，设置 60秒超时
  headers: {
    'Content-Type': 'application/json'
  }
})

// 2. 请求拦截器 (如果有 token 需求)
service.interceptors.request.use(
  config => {
    // 假设你把 token 存在 localStorage 里，key 为 'token'
    const token = localStorage.getItem('token')
    if (token) {
      config.headers['Authorization'] = 'Bearer ' + token
    }
    return config
  },
  error => {
    return Promise.reject(error)
  }
)

// 3. 响应拦截器 (处理通用错误)
service.interceptors.response.use(
  response => {
    return response
  },
  error => {
    console.error('API Error:', error)
    ElMessage.error(error.response?.data?.message || '网络请求失败')
    return Promise.reject(error)
  }
)

/**
 * 流式对话接口
 * @param {Object} data - { message: string, thread_id: string }
 * @param {Function} onMessage - 收到数据块时的回调 (用于实时更新界面)
 * @param {Function} onDone - 结束时的回调 (用于处理完成状态)
 */
export function chatStream(data, onMessage, onDone) {
  return service({
    url: '/chat/stream', // 对应后端路由
    method: 'post',
    data: data,
    responseType: 'text', // 关键：必须设置为 text，否则无法处理流
    onDownloadProgress: (progressEvent) => {
      // 关键：浏览器下载进度事件，用于捕获 SSE 流
      const event = progressEvent.event
      if (event && event.target && event.target.responseText) {
        const text = event.target.responseText

        // SSE 数据格式通常是 "data: xxx\n\n"，我们需要提取出 xxx
        // 这里做一个简单的处理，实际可能需要更严谨的解析
        const lines = text.split('\n')
        const lastLine = lines[lines.length - 1]

        if (lastLine.startsWith('data:')) {
          const jsonData = lastLine.replace('data:', '').trim()
          if (jsonData) {
            try {
              const parsed = JSON.parse(jsonData)
              // 假设后端返回的是 { content: "..." } 或者直接是字符串
              onMessage(parsed.content || parsed)
            } catch (e) {
              // 如果不是 JSON，直接当文本处理
              onMessage(jsonData)
            }
          }
        }
      }
    }
  }).then(res => {
    // 请求完全结束后调用
    onDone && onDone()
  }).catch(err => {
    onDone && onDone(err)
  })
}

// 4. 获取历史会话列表 (可选)
export function getHistoryList() {
  return service({
    url: '/chat/history',
    method: 'get'
  })
}

// 5. 创建新会话 (可选)
export function createNewChat() {
  return service({
    url: '/chat/new',
    method: 'post'
  })
}