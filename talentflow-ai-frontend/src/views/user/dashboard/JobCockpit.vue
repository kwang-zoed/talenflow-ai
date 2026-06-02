<template>
  <div class="cockpit-container">
    <!-- 1. 顶部数据看板 -->
    <el-row :gutter="20" class="stats-row">
      <el-col :span="6" v-for="item in statsData" :key="item.label">
        <el-card shadow="hover" class="stat-card">
          <div class="card-content">
            <div class="icon-wrapper" :style="{ backgroundColor: item.color }">
              <el-icon :size="24" color="#fff">
                <component :is="item.icon" />
              </el-icon>
            </div>
            <div class="text-wrapper">
              <p class="label">{{ item.label }}</p>
              <p class="value">{{ item.value }}</p>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" class="main-content">
      <!-- 2. 左侧核心功能区 -->
      <el-col :span="16">
        <el-card shadow="never" class="function-card">
          <template #header>
            <div class="card-header">
              <span>核心功能</span>
            </div>
          </template>
          <div class="function-grid">
            <div class="func-item" @click="goToTaskHall">
              <el-icon :size="40" color="#409EFF"><Search /></el-icon>
              <span>寻找新机会</span>
            </div>
            <div class="func-item" @click="goToMyApplications">
              <el-icon :size="40" color="#67C23A"><Document /></el-icon>
              <span>我的投递记录</span>
            </div>
            <div class="func-item" @click="goToResume">
              <el-icon :size="40" color="#E6A23C"><List /></el-icon>
              <span>管理我的简历</span>
            </div>
          </div>
        </el-card>
      </el-col>

      <!-- 3. 右侧智能推荐区 -->
      <el-col :span="8">
        <el-card shadow="never" class="recommend-card" v-loading="pageLoading">
          <template #header>
            <div class="card-header">
              <div class="header-title">
                <span>平台推荐</span>
                <el-tooltip content="基于您的简历和RAG技术智能匹配">
                  <el-icon class="question-icon"><QuestionFilled /></el-icon>
                </el-tooltip>
              </div>
              <el-tooltip content="刷新推荐列表">
                <el-icon 
                  class="refresh-icon" 
                  :class="{ 'is-rotating': pageLoading }" 
                  @click="fetchRecommendations(true)"
                >
                  <Refresh />
                </el-icon>
              </el-tooltip>
            </div>
          </template>

          <div class="scroll-container">
            <el-pull-refresh v-model="isRefreshing" @refresh="onRefresh" :pull-distance="60">
              <!-- 空状态 -->
              <div v-if="recommendedJobs.length === 0" class="empty-jobs">
                <el-empty :image-size="100" description="暂无推荐职位">
                  <el-button type="primary" @click="fetchRecommendations(true)">点击刷新</el-button>
                </el-empty>
              </div>

              <!-- 职位列表 -->
              <div v-else class="job-list">
                <div v-for="(item, index) in recommendedJobs" :key="item.job?.id || item.job_id || index" class="job-item">
                  <div class="score-tag">匹配度 {{ item.score }}%</div>
                  <h3 class="job-title">{{ item.job?.title || item.job_title || '未知职位' }}</h3>
                  <div class="job-meta">
                    <span>{{ item.job?.company || item.company || '未知公司' }}</span>
                    <span class="salary">{{ item.job?.salary || item.salary || '面议' }}</span>
                  </div>
                  <div class="skills">
                    <el-tag 
                      v-for="skill in item.matched_skills" 
                      :key="skill" 
                      size="small" 
                      class="skill-tag"
                    >
                      {{ skill }}
                    </el-tag>
                  </div>
                  <div class="action-area">
                    <el-button 
                      type="primary" 
                      link 
                      :loading="item.loading" 
                      @click="handleSmartApply(item)"
                    >
                      {{ item.loading ? 'AI处理中...' : '一键智能投递' }}
                    </el-button>
                  </div>
                  <el-divider />
                </div>
              </div>
            </el-pull-refresh>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-dialog
      v-model="showResumeDialog"
      title="选择简历"
      width="520px"
      class="resume-select-dialog"
      destroy-on-close
      @closed="resumePage = 1"
    >
      <div v-if="resumeTotal > 0" class="resume-select-body">
        <p class="resume-select-tip">共 {{ resumeTotal }} 份简历，请选择用于本次投递的版本</p>
        <el-scrollbar max-height="300px">
          <el-radio-group v-model="selectedResumeId" class="resume-radio-group">
            <el-radio
              v-for="resume in paginatedResumeList"
              :key="resume.id"
              :label="resume.id"
              class="resume-radio-item"
            >
              <span class="resume-radio-label" :title="formatResumeLabel(resume)">
                {{ formatResumeLabel(resume) }}
              </span>
              <el-tag v-if="resume.is_default" size="small" type="success" class="default-tag">默认</el-tag>
            </el-radio>
          </el-radio-group>
        </el-scrollbar>
        <el-pagination
          v-if="resumeTotal > resumePageSize"
          v-model:current-page="resumePage"
          :page-size="resumePageSize"
          :total="resumeTotal"
          :page-sizes="[5, 10, 15]"
          layout="total, sizes, prev, pager, next"
          small
          background
          class="resume-pagination"
          @size-change="(s) => { resumePageSize = s; resumePage = 1 }"
        />
      </div>
      <el-empty v-else description="暂无简历，请先创建" />
      <template #footer>
        <el-button @click="showResumeDialog = false">取消</el-button>
        <el-button type="primary" :loading="confirmLoading" @click="confirmSelection">确认投递</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, inject } from 'vue'
import { useRouter } from 'vue-router'
import { 
  Search, 
  List, 
  Document, 
  QuestionFilled, 
  Refresh 
} from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'

// 1. 引入 Pinia Store
// 注意：请确保路径正确，通常位于 src/store/
import { useUserStore } from '../../../store/user'
import { useResumeStore } from '../../../store/resume' // 需要创建这个文件

// 2. 引入 API (请确保路径正确)
import { submitRecommendTask, pollRecommendResult, checkRecommendStatus } from '../../../api/user'
import { getResumeListAPI} from '../../../api/resume'
import { startSmartApplyBackground } from '../../../utils/smartApplyTaskRunner'
import { wirePollToProgress } from '../../../utils/taskProgressRunner'

const router = useRouter()
const userStore = useUserStore()
const resumeStore = useResumeStore()
const taskProgress = inject('parseProgress', null)

// --- 数据定义 ---
const pageLoading = ref(false)
const isRefreshing = ref(false)
const recommendedJobs = ref([])

// 顶部统计数据
const statsData = ref([
  { label: '累计收益', value: '¥ 0.00', icon: 'Wallet', color: '#67C23A' },
  { label: '简历浏览量', value: 128, icon: 'TrendCharts', color: '#409EFF' },
  { label: '面试邀请', value: 5, icon: 'Document', color: '#E6A23C' },
  { label: '待处理事项', value: 2, icon: 'List', color: '#F56C6C' },
])

// --- 核心逻辑：获取用户 ID (基于你提供的 Store 结构) ---
// 因为 userInfo 是对象，所以取 id 字段
const currentUserId = computed(() => userStore.userInfo?.id)

// --- 页面跳转 ---
const goToTaskHall = () => router.push('/dashboard/jobs/list')
const goToMyApplications = () => router.push('/dashboard/applications')
const goToResume = () => router.push('/dashboard/resume')

// --- 缓存相关常量 ---
const CACHE_KEY_PREFIX = 'recommend_'
const CACHE_EXPIRE_MS = 10 * 60 * 1000 // 缓存10分钟有效

// --- 当前轮询的取消函数 ---
let cancelPolling = null

// --- 缓存工具函数 ---
const getCacheKey = (type) => `${CACHE_KEY_PREFIX}${currentUserId.value}_${type}`

const saveCache = (type, data) => {
  try {
    sessionStorage.setItem(getCacheKey(type), JSON.stringify(data))
  } catch (e) { /* ignore */ }
}

const loadCache = (type) => {
  try {
    const raw = sessionStorage.getItem(getCacheKey(type))
    return raw ? JSON.parse(raw) : null
  } catch (e) { return null }
}

const clearCache = () => {
  try {
    sessionStorage.removeItem(getCacheKey('task_id'))
    sessionStorage.removeItem(getCacheKey('result'))
    sessionStorage.removeItem(getCacheKey('time'))
  } catch (e) { /* ignore */ }
}
// --- 核心逻辑：获取推荐列表（异步 Celery + 缓存模式）---
const fetchRecommendations = async (forceRefresh = false) => {
  // 如果强制刷新，清除旧缓存
  if (forceRefresh) {
    if (cancelPolling) { cancelPolling(); cancelPolling = null }
    clearCache()
  }

  pageLoading.value = true
  try {
    if (!currentUserId.value) {
      ElMessage.warning('请先登录')
      router.push('/login')
      return
    }

    // 第一步：检查是否有缓存结果（10分钟内有效）
    const cachedTime = loadCache('time')
    const cachedResult = loadCache('result')
    if (cachedResult && cachedTime && (Date.now() - cachedTime < CACHE_EXPIRE_MS) && !forceRefresh) {
      console.log('[推荐] 使用缓存结果')
      recommendedJobs.value = cachedResult.map(job => ({ ...job, loading: false }))
      return
    }

    // 第二步：检查是否有进行中的任务
    let taskId = loadCache('task_id')
    if (taskId && !forceRefresh) {
      try {
        const status = await checkRecommendStatus(taskId)
        if (status.status === 'success' && status.data) {
          // 任务已完成，直接用结果
          console.log('[推荐] 缓存任务已完成，直接使用结果')
          const data = Array.isArray(status.data) ? status.data : []
          recommendedJobs.value = data.map(job => ({ ...job, loading: false }))
          saveCache('result', data)
          saveCache('time', Date.now())
          return
        } else if (status.status === 'processing') {
          // 任务还在跑，继续轮询
          console.log('[推荐] 缓存任务进行中，恢复轮询:', taskId)
        } else {
          // 任务失败，重新提交
          taskId = null
        }
      } catch (e) {
        // 查询失败，重新提交
        console.warn('[推荐] 查询缓存任务状态失败，重新提交')
        taskId = null
      }
    } else {
      taskId = null
    }

    // 第三步：如果没有可用任务，提交新任务
    if (!taskId) {
      const submitRes = await submitRecommendTask(currentUserId.value)
      taskId = submitRes.task_id
      console.log('[推荐] 提交新任务，task_id:', taskId)
      saveCache('task_id', taskId)
    }

    // 第四步：轮询结果（全局进度条）
    const pollPromise = pollRecommendResult(taskId)
    cancelPolling = pollPromise.cancel

    wirePollToProgress(pollPromise, taskProgress, {
      showMessage: 'AI 正在计算职位推荐...',
      taskType: 'recommend',
      completeHint: '推荐列表已更新',
      completeButtonText: '',
    })

    const resultData = await pollPromise
    cancelPolling = null

    console.log('[推荐] 拿到结果:', resultData)

    taskProgress?.update({
      status: 'success',
      message: `已匹配 ${Array.isArray(resultData) ? resultData.length : 0} 个推荐职位`,
      percent: 100,
      taskType: 'recommend',
      data: resultData,
      completeHint: '列表已刷新',
      completeButtonText: '',
    })

    // 第五步：处理并缓存数据
    if (resultData && Array.isArray(resultData)) {
      recommendedJobs.value = resultData.map(job => ({ ...job, loading: false }))
      saveCache('result', resultData)
      saveCache('time', Date.now())
    } else {
      recommendedJobs.value = []
    }
  } catch (error) {
    cancelPolling = null
    if (error.message === '已取消') return // 页面切换取消，不报错
    console.error("获取推荐列表失败:", error)
    ElMessage.error('加载推荐职位失败: ' + (error.message || '未知错误'))
  } finally {
    pageLoading.value = false
    isRefreshing.value = false
  }
}

const onRefresh = () => {
  fetchRecommendations(true) // 强制刷新
}

// --- 页面卸载时取消轮询 ---
onUnmounted(() => {
  if (cancelPolling) {
    cancelPolling()
    cancelPolling = null
  }
})

// --- 核心逻辑：智能投递 ---
// 状态变量
// --- 核心逻辑：智能投递 ---
// 状态变量
const showResumeDialog = ref(false);
const confirmLoading = ref(false);
const resumeList = ref([]);
const selectedResumeId = ref(null);
const resumePage = ref(1);
const resumePageSize = ref(5);
let pendingJobId = null;
let pendingJobTitle = ref('');
let pendingJobDesc = '';

const resumeTotal = computed(() => resumeList.value.length);

const paginatedResumeList = computed(() => {
  const start = (resumePage.value - 1) * resumePageSize.value;
  return resumeList.value.slice(start, start + resumePageSize.value);
});

const formatResumeLabel = (resume) => {
  const title = (resume.title || `简历 #${resume.id}`).trim();
  const name = (resume.name || '').trim();
  return name ? `${title}（${name}）` : title;
};

// 1. 点击“一键投递”按钮触发的函数
const handleSmartApply = async (job) => {
  try {
    // 第一步：获取简历列表
    const res = await getResumeListAPI();
    resumeList.value = res || [];

    // 第二步：根据简历数量决定逻辑
    if (resumeList.value.length === 0) {
      ElMessage.warning('请先去创建您的简历');
      return;
    }

    // 第三步：暂存职位信息 (兼容推荐服务返回的扁平结构)
    // 推荐服务返回的数据可能是扁平结构，而非嵌套结构
    pendingJobId = (job.job && (job.job.job_id || job.job.id)) || job.job_id || job.id;
    pendingJobTitle.value = (job.job && job.job.title) || job.job_title || job.title;
    pendingJobDesc = (job.job && job.job.description) || job.description || job.job_description || '';

    if (resumeList.value.length === 1) {
      selectedResumeId.value = resumeList.value[0].id;
      executeApply(pendingJobId, resumeList.value[0].id, pendingJobDesc);
    } else {
      resumePage.value = 1;
      const defaultResume = resumeList.value.find((r) => r.is_default);
      selectedResumeId.value = defaultResume?.id ?? resumeList.value[0]?.id ?? null;
      showResumeDialog.value = true;
    }
  } catch (error) {
    console.error("获取简历失败:", error);
    ElMessage.error("初始化投递失败");
  }
};

// 2. 弹窗确认按钮
const confirmSelection = () => {
  if (!selectedResumeId.value) {
    ElMessage.warning("请选择一份简历");
    return;
  }
  executeApply(pendingJobId, selectedResumeId.value, pendingJobDesc);
};

// 3. 提交后立即释放 UI，轮询在后台进行
const executeApply = async (jobId, resumeId, jobDesc) => {
  confirmLoading.value = true;
  const jobTitle = pendingJobTitle.value || '推荐职位';
  try {
    await startSmartApplyBackground({
      payload: {
        job_id: jobId,
        job_description: jobDesc,
        resume_id: resumeId,
        mode: 'auto'
      },
      jobTitle,
      taskProgress
    });
    showResumeDialog.value = false;
  } catch (error) {
    console.error('投递提交失败:', error);
    ElMessage.error(error.message || '投递提交失败，请重试');
  } finally {
    confirmLoading.value = false;
  }
};

// const handleSmartApply = async (jobItem) => {
//   jobItem.loading = true

//   // 1. 获取简历 ID (从 resume Store 获取)
//   // 请根据你 resumeStore 的实际字段名调整 (例如可能是 activeResumeId, selectedResumeId 等)
//   const resumeId = resumeStore.currentResumeId 

//   if (!resumeId) {
//     ElMessage.warning('请先选择一份简历')
//     jobItem.loading = false
//     return
//   }

//   try {
//     // 2. 调用 API (传入 user_id 和 resume_id)
//     const res = await smartApply({
//       user_id: currentUserId.value,
//       job_id: jobItem.job.id,
//       resume_id: resumeId, // 关键参数
//       job_description: jobItem.job.description || ""
//     })

//     // 3. 处理结果
//     if (res.success) {
//       ElMessage.success('投递成功！')
//       // 这里可以处理返回的 cover_letter
//     } else {
//       ElMessage.error(res.message || '投递失败')
//     }
//   } catch (error) {
//     console.error(error)
//     ElMessage.error('系统错误')
//   } finally {
//     jobItem.loading = false
//   }
//}

// --- 初始化 ---
onMounted(() => {
  fetchRecommendations(false) // 非强制刷新，优先使用缓存
})
</script>

<style scoped>
.cockpit-container {
  padding: 20px;
  background-color: #f5f7fa;
  min-height: 100vh;
}

/* 统计卡片样式 */
.stats-row {
  margin-bottom: 20px;
}
.stat-card {
  border-radius: 8px;
}
.card-content {
  display: flex;
  align-items: center;
}
.icon-wrapper {
  width: 50px;
  height: 50px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 15px;
}
.text-wrapper .label {
  font-size: 14px;
  color: #999;
  margin: 0;
}
.text-wrapper .value {
  font-size: 20px;
  font-weight: bold;
  color: #333;
  margin: 5px 0 0;
}

/* 主体布局 */
.main-content {
  display: flex;
}

/* 左侧功能区 */
.function-card {
  border-radius: 8px;
}
.function-grid {
  display: flex;
  justify-content: space-around;
  padding: 20px 0;
  text-align: center;
}
.func-item {
  cursor: pointer;
  display: flex;
  flex-direction: column;
  align-items: center;
  transition: transform 0.2s;
}
.func-item:hover {
  transform: translateY(-5px);
  color: #409EFF;
}
.func-item span {
  margin-top: 10px;
  font-size: 16px;
  font-weight: 500;
}

/* 右侧推荐区 */
.recommend-card {
  border-radius: 8px;
  height: 800px;
  display: flex;
  flex-direction: column;
}

/* 头部样式修改 */
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.header-title {
  display: flex;
  align-items: center;
  gap: 8px;
}
.question-icon {
  color: #909399;
  cursor: help;
}

/* 刷新按钮样式 */
.refresh-icon {
  font-size: 18px;
  color: #909399;
  cursor: pointer;
  transition: transform 0.3s;
}
.refresh-icon:hover {
  color: #409EFF;
}
/* 旋转动画 */
.is-rotating {
  animation: rotate 1s linear infinite;
}
@keyframes rotate {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.resume-select-body {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.resume-select-tip {
  margin: 0;
  font-size: 13px;
  color: #909399;
}

.resume-radio-group {
  display: flex;
  flex-direction: column;
  align-items: stretch;
  width: 100%;
}

.resume-radio-item {
  display: flex;
  align-items: center;
  margin: 0;
  padding: 10px 12px;
  border-radius: 6px;
  height: auto;
  white-space: normal;
}

.resume-radio-item:hover {
  background: #f5f7fa;
}

.resume-radio-item :deep(.el-radio__label) {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
  min-width: 0;
  padding-left: 8px;
  line-height: 1.5;
}

.resume-radio-label {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.default-tag {
  flex-shrink: 0;
}

.resume-pagination {
  justify-content: center;
  margin-top: 4px;
}

/* 滚动容器 */
.scroll-container {
  flex: 1;
  overflow-y: auto;
  height: 100%;
}
.job-item {
  margin-bottom: 10px;
  position: relative;
}
.score-tag {
  position: absolute;
  top: 0;
  right: 0;
  background-color: #67C23A;
  color: white;
  font-size: 12px;
  padding: 2px 6px;
  border-radius: 4px;
  font-weight: bold;
}
.job-title {
  font-size: 16px;
  font-weight: bold;
  color: #333;
  margin: 0 0 8px 0;
  line-height: 1.4;
  padding-right: 60px;
}
.job-meta {
  font-size: 13px;
  color: #999;
  margin-bottom: 10px;
  display: flex;
  justify-content: space-between;
}
.salary {
  color: #F56C6C;
  font-weight: bold;
}
.skills {
  margin-bottom: 15px;
}
.skill-tag {
  margin-right: 5px;
  margin-bottom: 5px;
  background-color: #f0f2f5;
  color: #606266;
  border: none;
}
.action-area {
  text-align: right;
}

/* 滚动条样式 */
.scroll-container::-webkit-scrollbar {
  width: 6px;
}
.scroll-container::-webkit-scrollbar-thumb {
  background-color: #ddd;
  border-radius: 3px;
}
</style>