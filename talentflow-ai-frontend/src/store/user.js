import { defineStore } from 'pinia'

export const useUserStore = defineStore('user', {
  state: () => ({
    token: localStorage.getItem('token') || '',
    refreshToken: localStorage.getItem('refresh_token') || '',
    userInfo: JSON.parse(localStorage.getItem('user') || 'null'),
  }),

  getters: {
    role: (state) => state.userInfo?.role ?? 'user',
    username: (state) => state.userInfo?.username || '',
    isLogin: (state) => !!state.token,
  },

  actions: {
    setToken(token) {
      this.token = token
      localStorage.setItem('token', token)
    },

    setRefreshToken(refreshToken) {
      this.refreshToken = refreshToken
      localStorage.setItem('refresh_token', refreshToken)
    },

    setTokens(accessToken, refreshToken) {
      this.setToken(accessToken)
      if (refreshToken) {
        this.setRefreshToken(refreshToken)
      }
    },

    setUserInfo(user) {
      this.userInfo = user
      localStorage.setItem('user', JSON.stringify(user))
    },

    logout() {
      this.token = ''
      this.refreshToken = ''
      this.userInfo = null
      localStorage.removeItem('token')
      localStorage.removeItem('refresh_token')
      localStorage.removeItem('user')
    },
  },
})
