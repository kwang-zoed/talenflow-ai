// store/resume.js
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

// 假设你有一个获取简历列表的 API
import { getResumeListAPI } from '../api/resume' 

export const useResumeStore = defineStore('resume', () => {
  // ================= 1. State (状态) =================
  
  // 存储所有简历的列表
  const resumes = ref([])
  
  // 存储当前选中的简历 ID (用于投递)
  // 初始值尝试从 localStorage 获取，如果没有则为 null
  const currentResumeId = ref(Number(localStorage.getItem('currentResumeId')) || null)

  // ================= 2. Getters (计算属性) =================

  // 获取当前选中的简历完整对象
  const currentResume = computed(() => {
    return resumes.value.find(r => r.id === currentResumeId.value) || null
  })

  // 获取默认简历（如果没有手动选中，或者选中的被删了，用这个兜底）
  const defaultResume = computed(() => {
    // 优先找标记为 default: true 的
    const defaultOne = resumes.value.find(r => r.is_default === true)
    // 如果没有默认标记，就取第一份
    return defaultOne || resumes.value[0]
  })

  // 获取默认简历的 ID
  const defaultResumeId = computed(() => {
    return defaultResume.value ? defaultResume.value.id : null
  })

  // ================= 3. Actions (操作) =================

  /**
   * 初始化/获取简历列表
   * 通常在 App 启动或用户登录后调用
   */
  const fetchResumes = async () => {
    try {
      // --- 真实 API 调用示例 ---
      // const res = await getResumeListAPI()
      // resumes.value = res.data.list
      
      // --- 模拟数据 (请替换为真实 API) ---
      // 模拟后端返回的数据结构
      const mockData = [
        { id: 101, name: '李四-主简历-全栈开发', is_default: true, updated_at: '2023-10-01' },
        { id: 102, name: 'Li Si - English CV', is_default: false, updated_at: '2023-11-05' },
        { id: 103, name: '李四-精简版(实习)', is_default: false, updated_at: '2023-12-20' }
      ]
      resumes.value = mockData

      // 初始化逻辑：如果 currentResumeId 为空，或者当前的 ID 不在列表中，则自动设为默认简历
      if (!currentResumeId.value || !resumes.value.find(r => r.id === currentResumeId.value)) {
        currentResumeId.value = defaultResumeId.value
      }

    } catch (error) {
      console.error('获取简历列表失败:', error)
    }
  }

  /**
   * 切换当前使用的简历
   * @param {Number} id - 要切换到的简历 ID
   */
  const switchResume = (id) => {
    const target = resumes.value.find(r => r.id === id)
    if (target) {
      currentResumeId.value = id
      // 持久化存储：刷新页面后依然记住用户选了哪份简历
      localStorage.setItem('currentResumeId', id.toString())
    } else {
      console.warn('切换失败：简历 ID 不存在')
    }
  }

  /**
   * 添加新简历（当用户创建简历后调用）
   * @param {Object} newResume - 新简历对象
   */
  const addResume = (newResume) => {
    resumes.value.unshift(newResume) // 加到最前面
    // 创建新简历后，通常自动切换到这份新简历
    switchResume(newResume.id)
  }

  /**
   * 删除简历
   * @param {Number} id - 要删除的简历 ID
   */
  const removeResume = (id) => {
    const index = resumes.value.findIndex(r => r.id === id)
    if (index !== -1) {
      // 如果删除的是当前正在使用的简历，自动切换回默认简历
      if (currentResumeId.value === id) {
        // 注意：这里不能直接调用 switchResume，因为列表还没删，逻辑会冲突
        // 我们手动找一个新的 ID
        const remainingResumes = resumes.value.filter(r => r.id !== id)
        const newDefault = remainingResumes.find(r => r.is_default) || remainingResumes[0]
        currentResumeId.value = newDefault ? newDefault.id : null
        if(currentResumeId.value) localStorage.setItem('currentResumeId', currentResumeId.value.toString())
      }
      
      // 从列表中移除
      resumes.value.splice(index, 1)
    }
  }

  // ================= 4. 返回给组件使用 =================
  return {
    resumes,
    currentResumeId,
    currentResume,
    defaultResumeId,
    fetchResumes,
    switchResume,
    addResume,
    removeResume
  }
}, {
  // 可选：配置持久化插件 (如果你使用了 pinia-plugin-persistedstate)
  // persist: true 
})