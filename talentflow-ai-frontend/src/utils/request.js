import axios from 'axios'
import { ElMessage, ElMessageBox } from 'element-plus'
import router from '@/router'

// 1. 创建 axios 实例
const service = axios.create({
  // 根据你提供的地址结构，基础路径应为 /api/v1
  baseURL: '/api/v1', 
  timeout: 60000 // 请求超时时间（批量解析需要更长时间）
})

// 2. 请求拦截器
service.interceptors.request.use(
  config => {
    // 从 localStorage 获取 Token
    const token = localStorage.getItem('token')
    
    if (token) {
      // FastAPI OAuth2PasswordBearer 标准格式：Bearer <token>
      config.headers['Authorization'] = 'Bearer ' + token
    }
    
    return config
  },
  error => {
    console.error('Request Error:', error)
    return Promise.reject(error)
  }
)

// 3. 响应拦截器
service.interceptors.response.use(
  response => {
    // 直接返回响应数据，方便在组件中使用 .then(res => ...)
    return response.data
  },
  error => {
    // 统一错误处理
    const { response } = error
    
    if (response) {
      switch (response.status) {
        case 401:
          // Token 过期或无效
          ElMessageBox.confirm('登录状态已失效，请重新登录', '系统提示', {
            confirmButtonText: '重新登录',
            type: 'warning',
            showClose: false,
            closeOnClickModal: false,
            closeOnPressEscape: false
          }).then(() => {
            localStorage.removeItem('token')
            localStorage.removeItem('user_info')
            router.push('/login')
          })
          break
          
        case 403:
          // 权限不足
          ElMessage.error('权限不足，无法执行此操作')
          break
          
        case 404:
          ElMessage.error('请求资源不存在')
          break
          
        case 500:
          ElMessage.error('服务器内部错误')
          break
          
        default:
          ElMessage.error(response.data.detail || '请求失败')
      }
    } else {
      // 网络错误
      ElMessage.error('网络连接失败，请检查网络')
    }
    
    return Promise.reject(error)
  }
)

export default service