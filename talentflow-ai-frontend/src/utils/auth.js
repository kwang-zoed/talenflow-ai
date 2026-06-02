/**
 * @file src/utils/auth.js
 * @description 统一处理认证相关的逻辑 (Token 和 User 信息)
 */

const TOKEN_KEY = 'token'
const USER_KEY = 'user'

export default {
  /**
   * 1. 获取 Token
   * 逻辑：优先从 LocalStorage 获取 -> 如果没有，尝试从 URL 参数中提取并保存
   */
  getToken() {
    // A. 尝试从 LocalStorage 获取
    let token = localStorage.getItem(TOKEN_KEY)

    // B. 如果 LocalStorage 没有，检查 URL 参数 (处理首次登录跳转的情况)
    if (!token) {
      const urlParams = new URLSearchParams(window.location.search)
      const urlToken = urlParams.get('token')

      if (urlToken) {
        // 如果 URL 中有 token，存入 LocalStorage 并清理 URL
        localStorage.setItem(TOKEN_KEY, urlToken)
        
        // 清理 URL 中的 token 参数，保持地址栏整洁
        const newUrl = new URL(window.location)
        newUrl.searchParams.delete('token')
        window.history.replaceState({}, document.title, newUrl)
        
        return urlToken
      }
    }

    return token
  },

  /**
   * 2. 设置 Token
   */
  setToken(token) {
    localStorage.setItem(TOKEN_KEY, token)
  },

  /**
   * 3. 移除 Token (登出时使用)
   */
  removeToken() {
    localStorage.removeItem(TOKEN_KEY)
  },

  /**
   * 4. 获取用户信息 (用于获取 Tenant-ID)
   */
  getUser() {
    const userStr = localStorage.getItem(USER_KEY)
    if (userStr) {
      try {
        return JSON.parse(userStr)
      } catch (e) {
        console.error('解析用户信息失败', e)
        return null
      }
    }
    return null
  },

  /**
   * 5. 设置用户信息
   */
  setUser(user) {
    localStorage.setItem(USER_KEY, JSON.stringify(user))
  },

  /**
   * 6. 移除用户信息
   */
  removeUser() {
    localStorage.removeItem(USER_KEY)
  }
}