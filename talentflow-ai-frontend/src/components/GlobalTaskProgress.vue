<template>
  <Transition name="slide-down">
    <div 
      v-if="visible" 
      class="global-task-progress fixed top-0 left-0 right-0 z-[9999] select-none"
    >
      <div class="progress-inner">
        <div class="progress-left">
          <el-icon class="progress-icon" :loading="percent < 100">
            <Promotion v-if="percent < 100" />
            <CircleCheck v-else />
          </el-icon>
          
          <div class="progress-text">
            <div class="progress-message">{{ message }}</div>
            <div class="progress-hint">
              {{ percent < 100 ? `进度: ${percent}%` : completeHint }}
            </div>
          </div>
        </div>
        
        <div class="progress-bar-wrap">
          <div class="progress-bar-bg">
            <div 
              class="progress-bar-fill"
              :style="{ width: `${percent}%` }"
            />
          </div>
        </div>
        
        <div class="progress-actions">
          <el-button
            v-if="pendingReviewCount > 0"
            type="warning"
            size="small"
            class="btn-review"
            @click="handleOpenReview"
          >
            审核待办 ({{ pendingReviewCount }})
          </el-button>

          <el-button 
            v-if="percent === 100 && completeButtonText" 
            type="primary" 
            size="small" 
            class="btn-fill"
            @click="handleClickToFill"
          >
            {{ completeButtonText }}
          </el-button>
          
          <el-button 
            v-if="percent < 100 && pendingReviewCount === 0" 
            size="small" 
            class="btn-minimal"
            @click="visible = false"
          >
            后台继续
          </el-button>
        </div>
      </div>
    </div>
  </Transition>
</template>

<script setup>
import { ref } from 'vue'
import { Promotion, CircleCheck } from '@element-plus/icons-vue'

const visible = ref(false)
const message = ref('正在解析文档...')
const percent = ref(0)
const taskData = ref(null)
const completeHint = ref('点击跳转解析弹窗')
const completeButtonText = ref('前往填充表单')
const pendingReviewCount = ref(0)
const taskType = ref('parse')
const emit = defineEmits(['clickToFill', 'openReview'])

function showProgress(msg = '正在后台执行...', options = {}) {
  visible.value = true
  message.value = msg
  taskType.value = options.taskType ?? 'parse'
  if (options.reset !== false) {
    percent.value = 0
    taskData.value = null
  }
  if (options.pendingReviewCount !== undefined) {
    pendingReviewCount.value = options.pendingReviewCount
  }
  completeHint.value = options.completeHint ?? '点击跳转解析弹窗'
  completeButtonText.value = options.completeButtonText ?? '前往填充表单'
}

function updateProgress(data) {
  if (data.message !== undefined) message.value = data.message
  if (data.percent !== undefined) percent.value = Math.min(100, Math.max(0, parseInt(data.percent)))
  if (data.completeHint !== undefined) completeHint.value = data.completeHint
  if (data.completeButtonText !== undefined) completeButtonText.value = data.completeButtonText
  if (data.pendingReviewCount !== undefined) pendingReviewCount.value = data.pendingReviewCount
  if (data.status === 'success' && data.data) {
    taskData.value = data.data
    visible.value = true
  }
  if (data.status === 'interrupted') {
    visible.value = true
    if (data.percent !== undefined) percent.value = data.percent
  }
  if (percent.value === 100) {
    visible.value = true
  }
}

function hideProgress() {
  visible.value = false
}

function resetProgress() {
  visible.value = false
  message.value = '正在解析文档...'
  percent.value = 0
  taskData.value = null
  pendingReviewCount.value = 0
  completeHint.value = '点击跳转解析弹窗'
  completeButtonText.value = '前往填充表单'
}

function handleOpenReview() {
  visible.value = true
  emit('openReview')
}

function handleClickToFill() {
  emit('clickToFill', { data: taskData.value, taskType: taskType.value })
  visible.value = false
}

defineExpose({
  visible,
  taskType,
  showProgress,
  updateProgress,
  hideProgress,
  resetProgress
})
</script>

<style scoped>
.slide-down-enter-active,
.slide-down-leave-active {
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}
.slide-down-enter-from,
.slide-down-leave-to {
  transform: translateY(-100%);
  opacity: 0;
}

.global-task-progress {
  background: linear-gradient(135deg, #6366f1 0%, #4f46e5 50%, #4338ca 100%);
  box-shadow: 
    0 4px 20px rgba(99, 102, 241, 0.35),
    0 2px 10px rgba(0, 0, 0, 0.1);
}

.progress-inner {
  max-width: 900px;
  margin: 0 auto;
  padding: 12px 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  color: white;
}

.progress-left {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
}

.progress-icon {
  font-size: 24px;
}

.progress-text {
  line-height: 1.2;
}

.progress-message {
  font-weight: 500;
  font-size: 14px;
}

.progress-hint {
  font-size: 11px;
  opacity: 0.75;
  margin-top: 2px;
}

.progress-bar-wrap {
  flex: 1;
  max-width: 220px;
}

.progress-bar-bg {
  height: 8px;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 999px;
  overflow: hidden;
}

.progress-bar-fill {
  height: 100%;
  background: white;
  border-radius: 999px;
  transition: width 0.5s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 0 10px rgba(255, 255, 255, 0.5);
}

.progress-actions {
  flex-shrink: 0;
}

.btn-fill {
  background: white !important;
  color: #4338ca !important;
  font-weight: 500;
  border: none;
}
.btn-fill:hover {
  background: rgba(255, 255, 255, 0.9) !important;
}

.btn-minimal {
  color: rgba(255, 255, 255, 0.8);
  border-color: rgba(255, 255, 255, 0.25);
}
.btn-minimal:hover {
  color: white;
  border-color: rgba(255, 255, 255, 0.4);
  background: rgba(255, 255, 255, 0.08);
}

.btn-review {
  background: #fbbf24 !important;
  color: #78350f !important;
  border: none;
  font-weight: 600;
}
.btn-review:hover {
  background: #f59e0b !important;
}
</style>
