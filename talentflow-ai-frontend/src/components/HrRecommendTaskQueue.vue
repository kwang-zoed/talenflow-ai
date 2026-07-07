<template>
  <Transition name="fade">
    <div v-if="visibleTasks.length" class="hr-recommend-queue">
      <div class="queue-header" @click="expanded = !expanded">
        <div class="header-left">
          <el-icon class="header-icon"><List /></el-icon>
          <span class="header-title">简历推荐任务</span>
          <el-tag size="small" type="info" effect="dark" class="count-tag">
            {{ processingCount }} 进行中
          </el-tag>
          <el-tag v-if="successCount" size="small" type="success" effect="dark" class="count-tag">
            {{ successCount }} 已完成
          </el-tag>
        </div>
        <el-icon class="toggle-icon" :class="{ expanded }"><ArrowDown /></el-icon>
      </div>

      <Transition name="expand">
        <div v-show="expanded" class="queue-body">
          <div
            v-for="task in visibleTasks"
            :key="task.taskId"
            class="queue-item"
            :class="`status-${task.status}`"
            @click="handleItemClick(task)"
          >
            <div class="item-row">
              <div class="item-main">
                <div class="item-title">{{ task.jobTitle || `职位 #${task.jobId}` }}</div>
                <div class="item-meta">
                  <template v-if="task.phase === 'coarse' && task.status === 'success'">
                    粗排 · 已完成
                  </template>
                  <template v-else-if="task.phase === 'rerank' && task.status === 'processing' && task.rerankPhase === 'queued'">
                    排队中
                  </template>
                  <template v-else-if="task.phase === 'rerank' && task.status === 'processing'">
                    精排中 {{ task.percent || 0 }}%
                  </template>
                  <template v-else-if="task.phase === 'rerank' && task.status === 'success'">
                    精排 · 已完成{{ task.rerank_applied ? '' : '（待查看）' }}
                  </template>
                  <template v-else-if="task.status === 'processing'">匹配中 {{ task.percent || 0 }}%</template>
                  <template v-else-if="task.status === 'success'">已完成</template>
                  <template v-else>{{ task.error || '推荐失败' }}</template>
                </div>
              </div>
              <div class="item-actions" @click.stop>
                <el-button
                  v-if="task.status === 'success'"
                  type="primary"
                  link
                  size="small"
                  @click="goToResult(task)"
                >
                  查看
                </el-button>
                <el-button
                  v-if="task.status !== 'processing'"
                  type="info"
                  link
                  size="small"
                  @click="dismiss(task.taskId)"
                >
                  移除
                </el-button>
              </div>
            </div>
            <el-progress
              v-if="task.status === 'processing'"
              :percentage="task.percent || 0"
              :stroke-width="4"
              :show-text="false"
              class="item-progress"
            />
          </div>
        </div>
      </Transition>
    </div>
  </Transition>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { List, ArrowDown } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import {
  subscribeHrRecommendQueue,
  dismissHrRecommendTask,
  getHrRecommendTasks,
} from '@/utils/hrResumeRecommendTaskRunner'

const router = useRouter()
const route = useRoute()
const tasks = ref([])
const expanded = ref(true)
let unsubscribe = null

const visibleTasks = computed(() => tasks.value)
const processingCount = computed(() => tasks.value.filter((t) => t.status === 'processing').length)
const successCount = computed(() => tasks.value.filter((t) => t.status === 'success').length)

async function goToResult(task) {
  const jobId = Number(task?.jobId)
  if (!Number.isFinite(jobId) || jobId <= 0) {
    ElMessage.warning('无法跳转：任务缺少职位 ID')
    return
  }

  const query = { from: 'queue' }
  if (task.sessionId) query.sessionId = task.sessionId

  const target = {
    name: 'HrResumeRecommend',
    params: { jobId: String(jobId) },
    query,
  }

  const sameJob =
    route.name === 'HrResumeRecommend' && Number(route.params.jobId) === jobId

  try {
    if (sameJob) {
      await router.replace({ ...target, query: { ...query, _r: String(Date.now()) } })
    } else {
      await router.push(target)
    }
  } catch {
    await router.replace({ ...target, query: { ...query, _r: String(Date.now()) } })
  }
}

function handleItemClick(task) {
  if (task.status === 'success') {
    goToResult(task)
    return
  }
  if (task.status === 'processing') {
    goToResult(task)
  }
}

function dismiss(taskId) {
  dismissHrRecommendTask(taskId)
}

onMounted(() => {
  unsubscribe = subscribeHrRecommendQueue((list) => {
    tasks.value = list
    if (list.some((t) => t.status === 'processing')) {
      expanded.value = true
    }
  })
  if (getHrRecommendTasks().length) {
    expanded.value = true
  }
})

onUnmounted(() => {
  unsubscribe?.()
})
</script>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.25s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.expand-enter-active,
.expand-leave-active {
  transition: max-height 0.25s ease, opacity 0.2s ease;
  overflow: hidden;
}
.expand-enter-from,
.expand-leave-to {
  max-height: 0;
  opacity: 0;
}
.expand-enter-to,
.expand-leave-from {
  max-height: 480px;
  opacity: 1;
}

.hr-recommend-queue {
  position: fixed;
  top: 12px;
  right: 16px;
  width: 320px;
  z-index: 9998;
  background: #fff;
  border-radius: 10px;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.12);
  border: 1px solid #e5e7eb;
  overflow: hidden;
}

.queue-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  cursor: pointer;
  background: linear-gradient(135deg, #eef2ff 0%, #f8fafc 100%);
  border-bottom: 1px solid #e5e7eb;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.header-icon {
  color: #4f46e5;
}

.header-title {
  font-size: 13px;
  font-weight: 600;
  color: #1e293b;
}

.count-tag {
  border: none;
}

.toggle-icon {
  transition: transform 0.2s ease;
  color: #64748b;
}
.toggle-icon.expanded {
  transform: rotate(180deg);
}

.queue-body {
  max-height: 360px;
  overflow-y: auto;
}

.queue-item {
  padding: 10px 12px 8px;
  border-bottom: 1px solid #f1f5f9;
  cursor: pointer;
  transition: background 0.15s ease;
}
.queue-item:last-child {
  border-bottom: none;
}
.queue-item:hover {
  background: #f8fafc;
}
.queue-item.status-success {
  border-left: 3px solid #22c55e;
}
.queue-item.status-processing {
  border-left: 3px solid #6366f1;
}
.queue-item.status-error {
  border-left: 3px solid #ef4444;
}

.item-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.item-row {
  display: flex;
  align-items: flex-start;
  gap: 8px;
}

.item-title {
  font-size: 13px;
  font-weight: 500;
  color: #0f172a;
  line-height: 1.3;
}

.item-meta {
  font-size: 11px;
  color: #64748b;
}

.item-actions {
  flex-shrink: 0;
  display: flex;
  gap: 4px;
}

.item-progress {
  margin-top: 8px;
}
</style>
