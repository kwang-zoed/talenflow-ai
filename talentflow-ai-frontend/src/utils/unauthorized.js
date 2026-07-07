import { ElMessageBox } from 'element-plus'
import router from '@/router'
import { useUserStore } from '@/store/user'

let showingReloginPrompt = false

/** 401 时仅弹出一次重新登录提示，避免并发请求叠多层弹窗 */
export function promptRelogin() {
  if (showingReloginPrompt) {
    return Promise.reject(new Error('Unauthorized'))
  }

  showingReloginPrompt = true

  const userStore = useUserStore()
  userStore.logout()
  localStorage.removeItem('user_info')

  return ElMessageBox.confirm('登录状态已失效，请重新登录', '系统提示', {
    confirmButtonText: '重新登录',
    type: 'warning',
    showClose: false,
    closeOnClickModal: false,
    closeOnPressEscape: false
  }).finally(() => {
    showingReloginPrompt = false
    router.replace('/login')
  })
}
