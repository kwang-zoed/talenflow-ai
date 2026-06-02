<template>
  <GlobalTaskProgress 
    ref="progressBarRef" 
    @click-to-fill="handleProgressClickToFill"
    @open-review="handleOpenSmartApplyReview"
  />
  <SmartApplyReviewDialog ref="smartApplyReviewRef" />
  <router-view />
</template>

<script setup>
import { ref, provide, onMounted, onUnmounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import GlobalTaskProgress from './components/GlobalTaskProgress.vue'
import SmartApplyReviewDialog from './components/SmartApplyReviewDialog.vue'
import { getParseTaskStatus, pollParseTaskResult } from './api/job'
import { normalizeTaskStatus } from './utils/taskPoller'
import { resumeStoredTaskPoll, clearTaskStorage } from './utils/taskProgressRunner'
import {
  registerSmartApplyReviewDialog,
  resumeSmartApplyPolling,
  openPendingSmartApplyReview,
  SMART_APPLY_TASKS_KEY,
} from './utils/smartApplyTaskRunner'

const STORAGE_KEY = 'talentflow_parse_task'
const STORAGE_RESULT_KEY = 'talentflow_parse_result'
const RESUME_PARSE_STORAGE_KEY = 'talentflow_resume_parse_task'
const RESUME_PARSE_RESULT_KEY = 'talentflow_resume_parse_result'

const progressBarRef = ref(null)
const smartApplyReviewRef = ref(null)
const router = useRouter()
const route = useRoute()
let globalPollCancel = null

watch(() => route.path, (newPath) => {
  if (newPath === '/login') {
    progressBarRef.value?.hideProgress()
    progressBarRef.value?.resetProgress()
    try {
      localStorage.removeItem(STORAGE_KEY)
      localStorage.removeItem(STORAGE_RESULT_KEY)
      localStorage.removeItem(RESUME_PARSE_STORAGE_KEY)
      localStorage.removeItem(RESUME_PARSE_RESULT_KEY)
      localStorage.removeItem(SMART_APPLY_TASKS_KEY)
    } catch (e) {}
  }
})

const parseProgress = {
  show(msg, options) {
    progressBarRef.value?.showProgress(msg, options)
  },
  update(data) {
    progressBarRef.value?.updateProgress(data)
  },
  hide() {
    progressBarRef.value?.hideProgress()
  },
  reset() {
    progressBarRef.value?.resetProgress()
  },
  get visible() {
    return progressBarRef.value?.visible
  },
}

provide('parseProgress', parseProgress)

function handleProgressClickToFill(payload) {
  const data = payload?.data ?? payload
  const taskType = payload?.taskType ?? progressBarRef.value?.taskType ?? 'parse'

  if (taskType === 'smart_apply') {
    router.push('/dashboard/applications')
    return
  }

  if (taskType === 'recommend') {
    window.dispatchEvent(new CustomEvent('globalRecommendComplete', { detail: data }))
    if (!router.currentRoute.value.path.includes('/dashboard')) {
      router.push('/dashboard')
    }
    return
  }

  if (taskType === 'resume_parse') {
    window.dispatchEvent(new CustomEvent('globalResumeParseComplete', { detail: data }))
    if (!router.currentRoute.value.path.includes('/admin/resumes')) {
      router.push('/admin/resumes')
    }
    return
  }

  try {
    localStorage.setItem(STORAGE_RESULT_KEY, JSON.stringify({ data, timestamp: Date.now() }))
  } catch (e) {}

  const currentPath = router.currentRoute.value.path
  let targetPath = '/admin/jobs'
  if (currentPath.includes('/hr/')) {
    targetPath = '/hr/jobs'
  }

  if (!currentPath.includes('/jobs')) {
    router.push(targetPath)
  }

  setTimeout(() => {
    window.dispatchEvent(new CustomEvent('globalParseComplete', { detail: data }))
  }, 100)
}

async function startGlobalParsePollingIfNeeded() {
  await resumeStoredTaskPoll({
    storageKey: STORAGE_KEY,
    resultStorageKey: STORAGE_RESULT_KEY,
    fetchStatus: async (taskId) => normalizeTaskStatus(await getParseTaskStatus(taskId)),
    createPoll: (taskId) => {
      const poll = pollParseTaskResult(taskId, 600000)
      globalPollCancel = poll.cancel
      return poll
    },
    progressRef: parseProgress,
    buildCompleteMessage: (saved, _data, _done) =>
      saved.isBatch ? '批量解析完成，点击前往填充表单' : '解析完成，点击前往填充表单',
  })
}

async function startGlobalResumeParsePollingIfNeeded() {
  const { getResumeParseStatus, pollResumeParseResult } = await import('./api/adminResume')

  await resumeStoredTaskPoll({
    storageKey: RESUME_PARSE_STORAGE_KEY,
    resultStorageKey: RESUME_PARSE_RESULT_KEY,
    fetchStatus: async (taskId) => normalizeTaskStatus(await getResumeParseStatus(taskId)),
    createPoll: (taskId) => pollResumeParseResult(taskId, 600000),
    progressRef: parseProgress,
    buildCompleteMessage: () => '简历解析完成，点击填充表单',
  })
}

function handleOpenSmartApplyReview() {
  openPendingSmartApplyReview(parseProgress)
}

onMounted(() => {
  registerSmartApplyReviewDialog(smartApplyReviewRef)
  startGlobalParsePollingIfNeeded()
  startGlobalResumeParsePollingIfNeeded()
  resumeSmartApplyPolling(parseProgress)

  window.addEventListener('storage', (e) => {
    if (e.key === STORAGE_KEY && e.newValue) {
      startGlobalParsePollingIfNeeded()
    }
    if (e.key === RESUME_PARSE_STORAGE_KEY && e.newValue) {
      startGlobalResumeParsePollingIfNeeded()
    }
  })
})

onUnmounted(() => {
  globalPollCancel?.()
})

defineExpose({ parseProgress, clearTaskStorage })
</script>

<style>
body, html {
  margin: 0;
  padding: 0;
  height: 100%;
  font-family: 'Helvetica Neue', Helvetica, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', '微软雅黑', Arial, sans-serif;
}
</style>
