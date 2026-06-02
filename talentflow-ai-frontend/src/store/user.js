import { defineStore } from 'pinia'

export const useUserStore = defineStore('user', {
  // 1. 状态：存放用户数据
  state: () => ({
    token: localStorage.getItem('token') || '', // 初始化时尝试从 localStorage 读取
    userInfo: JSON.parse(localStorage.getItem('user')) || null,
  }),

  // 2. 计算属性：方便在组件中获取特定字段
  getters: {
    // 获取角色，如果没有则默认为 'user'
    role: (state) => state.userInfo?.role || 'user',
    
    // 获取用户名
    username: (state) => state.userInfo?.username || '',
    
    // 判断是否已登录
    isLogin: (state) => !!state.token,
  },

  // 3. 动作：修改状态的方法
  actions: {
    // 登录逻辑（示例）
    setToken(token) {
      this.token = token
      localStorage.setItem('token', token)
    },

    // 保存用户信息（示例）
    setUserInfo(user) {
      this.userInfo = user
      localStorage.setItem('user', JSON.stringify(user))
    },

    // ==========================================
    // 退出登录逻辑 (你需要的部分)
    // ==========================================
    logout() {
      // 1. 重置 Store 状态为初始值
      this.token = ''
      this.userInfo = null

      // 2. 清除 LocalStorage 中的缓存
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      
      // 注意：这里不需要写 router.push('/login')
      // 路由跳转应该在组件（AdminLayout.vue）中调用 logout 后执行
    }
  }
})