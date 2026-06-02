<template>
  <el-dialog
    v-model="visible"
    :title="dialogTitle"
    width="720px"
    :close-on-click-modal="false"
    destroy-on-close
    @closed="handleClosed"
  >
    <div v-loading="loading" class="review-body">
      <el-alert
        v-if="reviewMessage"
        :title="reviewMessage"
        type="info"
        show-icon
        :closable="false"
        class="review-alert"
      />

      <template v-if="reviewType === 'optimized_resume'">
        <p class="field-label">优化后的简历（JSON，可按需修改字段）</p>
        <el-input
          v-model="resumeJsonText"
          type="textarea"
          :rows="16"
          placeholder="加载中..."
        />
      </template>

      <template v-else-if="reviewType === 'cover_letter'">
        <p class="field-label">求职信</p>
        <el-input
          v-model="coverLetterText"
          type="textarea"
          :rows="14"
          placeholder="加载中..."
        />
      </template>
    </div>

    <template #footer>
      <el-button @click="visible = false" :disabled="submitting">稍后处理</el-button>
      <el-button type="primary" :loading="submitting" @click="handleConfirm">
        确认并继续
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { getSmartApplyThread, resumeSmartApplyThread } from '../api/user'

const visible = ref(false)
const loading = ref(false)
const submitting = ref(false)
const threadId = ref('')
const taskId = ref('')
const jobTitle = ref('')
const reviewType = ref('')
const reviewMessage = ref('')
const resumeJsonText = ref('')
const coverLetterText = ref('')

let onComplete = null
let onInterrupted = null
let onDismiss = null

const dialogTitle = computed(() => {
  const title = jobTitle.value ? `「${jobTitle.value}」` : ''
  if (reviewType.value === 'optimized_resume') {
    return `${title}确认优化简历`
  }
  if (reviewType.value === 'cover_letter') {
    return `${title}确认求职信`
  }
  return `${title}智能投递确认`
})

async function loadThreadDetails() {
  if (!threadId.value) return
  loading.value = true
  try {
    const data = await getSmartApplyThread(threadId.value, true)
    reviewType.value = data.review_type || reviewType.value
    reviewMessage.value = data.review_message || reviewMessage.value
    if (reviewType.value === 'optimized_resume') {
      const resume = data.state?.optimized_resume
      resumeJsonText.value = resume
        ? JSON.stringify(resume, null, 2)
        : ''
    } else if (reviewType.value === 'cover_letter') {
      coverLetterText.value = data.state?.cover_letter || ''
    }
  } catch (err) {
    ElMessage.error(err.message || '加载审核内容失败')
  } finally {
    loading.value = false
  }
}

function buildUpdates() {
  if (reviewType.value === 'optimized_resume') {
    if (!resumeJsonText.value.trim()) {
      throw new Error('简历内容不能为空')
    }
    let parsed
    try {
      parsed = JSON.parse(resumeJsonText.value)
    } catch {
      throw new Error('简历 JSON 格式不正确，请检查后再提交')
    }
    return { optimized_resume: parsed }
  }
  if (reviewType.value === 'cover_letter') {
    if (!coverLetterText.value.trim()) {
      throw new Error('求职信不能为空')
    }
    return { cover_letter: coverLetterText.value.trim() }
  }
  return {}
}

async function handleConfirm() {
  submitting.value = true
  try {
    const updates = buildUpdates()
    const res = await resumeSmartApplyThread(threadId.value, updates)

    if (res.status === 'interrupted') {
      reviewType.value = res.review_type || reviewType.value
      reviewMessage.value = res.review_message || res.message
      if (res.review_type === 'optimized_resume') {
        const resume = res.state?.optimized_resume
        resumeJsonText.value = resume ? JSON.stringify(resume, null, 2) : resumeJsonText.value
      } else if (res.review_type === 'cover_letter') {
        coverLetterText.value = res.state?.cover_letter || coverLetterText.value
      } else {
        await loadThreadDetails()
      }
      onInterrupted?.(res)
      ElMessage.info(res.message || '请继续下一步确认')
      return
    }

    if (res.status === 'error') {
      throw new Error(res.message || '续跑失败')
    }

    visible.value = false
    onComplete?.(res)
    if (!onComplete) {
      ElMessage.success(res.message || '投递完成')
    }
  } catch (err) {
    ElMessage.error(err.message || '提交失败')
  } finally {
    submitting.value = false
  }
}

function handleClosed() {
  onDismiss?.()
  threadId.value = ''
  taskId.value = ''
  jobTitle.value = ''
  reviewType.value = ''
  reviewMessage.value = ''
  resumeJsonText.value = ''
  coverLetterText.value = ''
  onComplete = null
  onInterrupted = null
  onDismiss = null
}

/**
 * @param {{ threadId: string, taskId?: string, jobTitle?: string, reviewType?: string, reviewMessage?: string, onComplete?: Function, onInterrupted?: Function, onDismiss?: Function }} payload
 */
async function open(payload) {
  threadId.value = payload.threadId
  taskId.value = payload.taskId || ''
  jobTitle.value = payload.jobTitle || ''
  reviewType.value = payload.reviewType || ''
  reviewMessage.value = payload.reviewMessage || ''
  onComplete = payload.onComplete || null
  onInterrupted = payload.onInterrupted || null
  onDismiss = payload.onDismiss || null
  visible.value = true
  await loadThreadDetails()
}

defineExpose({ open })
</script>

<style scoped>
.review-body {
  min-height: 200px;
}
.review-alert {
  margin-bottom: 16px;
}
.field-label {
  margin: 0 0 8px;
  font-size: 13px;
  color: #606266;
}
</style>
