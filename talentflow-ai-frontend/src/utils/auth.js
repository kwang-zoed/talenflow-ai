/**
 * @file src/utils/auth.js
 * @description 统一处理认证相关的逻辑 (Token 和 User 信息)
 */

const TOKEN_KEY = 'token'
const REFRESH_TOKEN_KEY = 'refresh_token'
const USER_KEY = 'user'

export default {
  getToken() {
    let token = localStorage.getItem(TOKEN_KEY)

    if (!token) {
      const urlParams = new URLSearchParams(window.location.search)
      const urlToken = urlParams.get('token')

      if (urlToken) {
        localStorage.setItem(TOKEN_KEY, urlToken)

        const newUrl = new URL(window.location)
        newUrl.searchParams.delete('token')
        window.history.replaceState({}, document.title, newUrl)

        return urlToken
      }
    }

    return token
  },

  getRefreshToken() {
    return localStorage.getItem(REFRESH_TOKEN_KEY)
  },

  setToken(token) {
    localStorage.setItem(TOKEN_KEY, token)
  },

  setRefreshToken(refreshToken) {
    localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken)
  },

  setTokens(accessToken, refreshToken) {
    if (accessToken) this.setToken(accessToken)
    if (refreshToken) this.setRefreshToken(refreshToken)
  },

  removeToken() {
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(REFRESH_TOKEN_KEY)
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