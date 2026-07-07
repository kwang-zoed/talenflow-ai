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

    <el-row :gutter="20" class="function-row">
      <el-col :span="24">
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
    </el-row>

    <el-row :gutter="20" class="recommend-row">
      <el-col :span="9" class="ref-column">
        <RecommendReferencePanel
          mode="resume"
          :data="myResume || {}"
          :loading="resumeLoading"
          title="我的简历"
          badge="对照"
          badge-type="success"
          :empty-text="resumeEmptyHint"
        />
        <el-button v-if="!myResume && !resumeLoading" type="primary" link class="go-resume-btn" @click="goToResume">
          去创建/完善简历 →
        </el-button>
      </el-col>

      <el-col :span="15" class="list-column">
        <section class="list-panel" v-loading="pageLoading && recommendedJobs.length === 0">
          <div class="list-panel-header">
            <div class="header-title">
              <span class="header-main">平台推荐</span>
              <el-tag size="small" type="info" effect="plain" round>已展示 {{ recommendedJobs.length }} 条</el-tag>
              <el-tag v-if="sessionStatus === 'rerank_queued'" size="small" type="info" effect="plain" round>
                排队中
              </el-tag>
              <el-tag v-else-if="sessionStatus === 'reranking'" size="small" type="warning" effect="plain" round>
                精排中
              </el-tag>
              <el-tag v-else-if="rerankApplied" size="small" type="success" effect="plain" round>
                已精排
              </el-tag>
              <el-tag v-else-if="rerankAvailable && !rerankApplied" size="small" type="warning" effect="plain" round>
                精排已完成
              </el-tag>
              <el-tag v-else size="small" type="info" effect="plain" round>
                粗排
              </el-tag>
            </div>
            <div class="header-actions">
              <el-button
                v-if="sessionId && !rerankApplied"
                type="primary"
                size="small"
                round
                :loading="applyingRerank || sessionStatus === 'reranking' || sessionStatus === 'rerank_queued'"
                :disabled="sessionStatus === 'reranking' || sessionStatus === 'rerank_queued'"
                @click="applyRerankSort"
              >
                {{ rerankButtonLabel }}
              </el-button>
              <el-button circle size="small" :loading="pageLoading" @click="startSession(true)">
                <el-icon><Refresh /></el-icon>
              </el-button>
            </div>
          </div>

          <div ref="scrollRef" class="scroll-container" @scroll="onScroll">
            <el-empty v-if="recommendedJobs.length === 0 && !pageLoading" description="暂无推荐职位">
              <el-button type="primary" round @click="startSession(true)">开始推荐</el-button>
            </el-empty>

            <div v-else class="match-list">
              <RecommendMatchCard
                v-for="(item, index) in recommendedJobs"
                :key="item.job?.id || item.job_id || index"
                :item="item"
                :title="item.job?.title || item.job_title || '未知职位'"
                :subtitle="item.job?.company || item.company || '未知公司'"
                :extra="[item.job?.salary || item.salary, item.distance_text ? `距您${item.distance_text}` : ''].filter(Boolean).join(' · ')"
              >
                <template #actions>
                  <el-button type="primary" link @click="openJobDetail(item)">查看对照</el-button>
                  <el-button type="primary" link :loading="item.loading" @click="handleSmartApply(item)">
                    {{ item.loading ? '投递中...' : '智能投递' }}
                  </el-button>
                </template>
              </RecommendMatchCard>

              <div v-if="loadingMore" class="load-more-hint">
                <el-icon class="is-loading"><Refresh /></el-icon> 加载更多...
              </div>
              <div v-else-if="hasMore && recommendedJobs.length" class="load-more-hint">
                向下滚动加载更多
              </div>
              <div v-else-if="!hasMore && recommendedJobs.length" class="load-more-hint muted">
                已加载全部推荐
              </div>
            </div>
          </div>
        </section>
      </el-col>
    </el-row>

    <el-dialog v-model="jobDetailVisible" title="职位与简历对照" width="960px" destroy-on-close align-center>
      <div class="dialog-compare">
        <div class="dialog-ref">
          <RecommendReferencePanel mode="resume" :data="myResume || {}" title="我的简历" badge="CV" compact />
        </div>
        <div class="dialog-job">
          <RecommendReferencePanel mode="job" :data="selectedJob || {}" title="职位要求" badge="JD" compact />
        </div>
      </div>
    </el-dialog>

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
  Refresh 
} from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

import RecommendReferencePanel from '@/components/RecommendReferencePanel.vue'
import RecommendMatchCard from '@/components/RecommendMatchCard.vue'
import { useUserStore } from '../../../store/user'
import {
  createJobRecommendSession,
  getJobRecommendSessionMore,
  getJobRecommendSessionStatus,
  applyJobRecommendSessionRerank,
} from '../../../api/user'
import { getResumeListAPI, getResumeDetailAPI } from '../../../api/resume'
import { startSmartApplyBackground } from '../../../utils/smartApplyTaskRunner'

const PAGE_SIZE = 10
const APPLY_RERANK_LIMIT = 50
const RERANK_POLL_INTERVAL_MS = 3000
const RERANK_QUEUE_MAX_WAIT_MS = 900000
const RERANK_PROCESS_MAX_WAIT_MS = 360000

const router = useRouter()
const userStore = useUserStore()
const taskProgress = inject('parseProgress', null)

const pageLoading = ref(false)
const loadingMore = ref(false)
const recommendedJobs = ref([])
const scrollRef = ref(null)

const sessionId = ref(null)
const hasMore = ref(false)
const ranking = ref('coarse')
const sessionStatus = ref('coarse_ready')
const rerankAvailable = ref(false)
const rerankApplied = ref(false)
const applyingRerank = ref(false)

let rerankPollTimer = null

const rerankButtonLabel = computed(() => {
  if (sessionStatus.value === 'rerank_queued') return '排队中...'
  if (sessionStatus.value === 'reranking' || applyingRerank.value) return '精排中...'
  if (rerankAvailable.value && !rerankApplied.value) return '应用精排'
  return '启用精排'
})
const myResume = ref(null)
const resumeLoading = ref(false)
const jobDetailVisible = ref(false)
const selectedJob = ref(null)

const resumeEmptyHint = computed(() =>
  resumeLoading.value ? '加载简历中...' : '暂无简历，推荐将基于空简历匹配，请先创建简历'
)

// 顶部统计数据
const statsData = ref([
  { label: '累计收益', value: '¥ 0.00', icon: 'Wallet', color: '#67C23A' },
  { label: '简历浏览量', value: 128, icon: 'TrendCharts', color: '#409EFF' },
  { label: '面试邀请', value: 5, icon: 'Document', color: '#E6A23C' },
  { label: '待处理事项', value: 2, icon: 'List', color: '#F56C6C' },
])

const currentUserId = computed(() => userStore.userInfo?.id)

const shownJobIds = computed(() =>
  recommendedJobs.value.map((x) => x.job?.id || x.job_id).filter(Boolean)
)

const goToTaskHall = () => router.push('/dashboard/jobs/list')
const goToMyApplications = () => router.push('/dashboard/applications')
const goToResume = () => router.push('/dashboard/resume')

const CACHE_KEY_PREFIX = computed(() => `job_recommend_${currentUserId.value}_`)

const getCacheKey = (type) => `${CACHE_KEY_PREFIX.value}${type}`

const saveSessionCache = () => {
  try {
    sessionStorage.setItem(getCacheKey('session_id'), sessionId.value || '')
    sessionStorage.setItem(getCacheKey('result'), JSON.stringify(recommendedJobs.value))
    sessionStorage.setItem(getCacheKey('has_more'), hasMore.value ? '1' : '0')
    sessionStorage.setItem(getCacheKey('ranking'), ranking.value || 'coarse')
    sessionStorage.setItem(getCacheKey('session_status'), sessionStatus.value || 'coarse_ready')
    sessionStorage.setItem(getCacheKey('rerank_applied'), rerankApplied.value ? '1' : '0')
    sessionStorage.setItem(getCacheKey('time'), String(Date.now()))
  } catch (_) {}
}

const SESSION_CACHE_TTL_MS = 50 * 60 * 1000

const loadSessionCache = () => {
  try {
    const sid = sessionStorage.getItem(getCacheKey('session_id'))
    const raw = sessionStorage.getItem(getCacheKey('result'))
    const result = raw ? JSON.parse(raw) : null
    const savedAt = Number(sessionStorage.getItem(getCacheKey('time')) || 0)
    if (!sid || !savedAt || Date.now() - savedAt > SESSION_CACHE_TTL_MS) {
      return null
    }
    return {
      sessionId: sid,
      result,
      hasMore: sessionStorage.getItem(getCacheKey('has_more')) !== '0',
      ranking: sessionStorage.getItem(getCacheKey('ranking')) || 'coarse',
      sessionStatus: sessionStorage.getItem(getCacheKey('session_status')) || 'coarse_ready',
      rerankApplied: sessionStorage.getItem(getCacheKey('rerank_applied')) === '1',
    }
  } catch {
    return null
  }
}

const clearSessionCache = () => {
  try {
    for (const key of ['session_id', 'result', 'has_more', 'ranking', 'session_status', 'rerank_applied', 'time']) {
      sessionStorage.removeItem(getCacheKey(key))
    }
  } catch (_) {}
}

/** 清除旧版 Celery 推荐缓存，避免与新版会话接口混用 */
const clearLegacyRecommendCache = () => {
  if (!currentUserId.value) return
  const uid = currentUserId.value
  try {
    for (const key of ['task_id', 'result', 'time']) {
      sessionStorage.removeItem(`recommend_${uid}_${key}`)
    }
  } catch (_) {}
}

const mergeResults = (items) => {
  const seen = new Set(shownJobIds.value)
  const merged = [...recommendedJobs.value]
  for (const item of items || []) {
    const id = item.job?.id || item.job_id
    if (!id || seen.has(id)) continue
    seen.add(id)
    merged.push({ ...item, loading: false })
  }
  recommendedJobs.value = merged
}

const applyRerankResults = async () => {
  const limit = Math.min(Math.max(recommendedJobs.value.length, PAGE_SIZE), APPLY_RERANK_LIMIT)
  const res = await applyJobRecommendSessionRerank(sessionId.value, limit)
  if (res.status === 'processing' || res.session_status === 'reranking' || res.session_status === 'rerank_queued') {
    return false
  }
  recommendedJobs.value = (res.data || []).map((job) => ({ ...job, loading: false }))
  hasMore.value = !!res.has_more
  ranking.value = 'rerank'
  rerankApplied.value = true
  rerankAvailable.value = true
  sessionStatus.value = 'rerank_ready'
  saveSessionCache()
  if (scrollRef.value) scrollRef.value.scrollTop = 0
  return true
}

const beginRerankWatch = () => {
  if (!sessionId.value || rerankPollTimer) return
  const startedAt = Date.now()
  let processingStartedAt = null
  const tick = async () => {
    try {
      const res = await getJobRecommendSessionStatus(sessionId.value)
      sessionStatus.value = res.session_status || sessionStatus.value
      rerankAvailable.value = !!(res.rerank_available ?? (sessionStatus.value === 'rerank_ready'))
      if (sessionStatus.value === 'rerank_ready') {
        stopRerankWatch()
        applyingRerank.value = true
        try {
          const ok = await applyRerankResults()
          if (ok) ElMessage.success('已按精排结果重新排序')
        } finally {
          applyingRerank.value = false
        }
        return
      }
      const totalElapsed = Date.now() - startedAt
      if (sessionStatus.value === 'reranking') {
        if (!processingStartedAt) processingStartedAt = Date.now()
        const procElapsed = Date.now() - processingStartedAt
        if (procElapsed > RERANK_PROCESS_MAX_WAIT_MS || totalElapsed > RERANK_QUEUE_MAX_WAIT_MS) {
          stopRerankWatch()
          sessionStatus.value = 'coarse_ready'
          ElMessage.error(procElapsed > RERANK_PROCESS_MAX_WAIT_MS ? '精排处理超时，请稍后重试' : '精排排队超时，请稍后重试')
        }
        return
      }
      if (sessionStatus.value === 'rerank_queued') {
        if (totalElapsed > RERANK_QUEUE_MAX_WAIT_MS) {
          stopRerankWatch()
          sessionStatus.value = 'coarse_ready'
          ElMessage.error('精排排队超时，请稍后重试')
        }
        return
      }
      stopRerankWatch()
      if (sessionStatus.value !== 'rerank_ready') {
        sessionStatus.value = 'coarse_ready'
        ElMessage.error('精排失败，请稍后重试')
      }
    } catch {
      stopRerankWatch()
      sessionStatus.value = 'coarse_ready'
      ElMessage.error('精排状态查询失败')
    }
  }
  rerankPollTimer = setInterval(tick, RERANK_POLL_INTERVAL_MS)
  tick()
}

const stopRerankWatch = () => {
  if (rerankPollTimer) {
    clearInterval(rerankPollTimer)
    rerankPollTimer = null
  }
}

const applyRerankSort = async () => {
  if (!sessionId.value || applyingRerank.value) return
  applyingRerank.value = true
  try {
    if (sessionStatus.value === 'rerank_ready' && rerankAvailable.value) {
      const ok = await applyRerankResults()
      if (ok) ElMessage.success('已按精排结果重新排序')
      return
    }
    const limit = Math.min(Math.max(recommendedJobs.value.length, PAGE_SIZE), APPLY_RERANK_LIMIT)
    const res = await applyJobRecommendSessionRerank(sessionId.value, limit)
    if (res.status === 'processing' || res.session_status === 'reranking' || res.session_status === 'rerank_queued') {
      sessionStatus.value = res.session_status || 'rerank_queued'
      beginRerankWatch()
      ElMessage.info('精排已启动，完成后将自动更新排序')
      return
    }
    const ok = await applyRerankResults()
    if (ok) ElMessage.success('已按精排结果重新排序')
  } catch (error) {
    const detail = error?.response?.data?.detail || error.message || '未知错误'
    ElMessage.error('应用精排失败: ' + detail)
  } finally {
    applyingRerank.value = false
  }
}

const startSession = async (forceRefresh = false) => {
  if (!currentUserId.value) {
    ElMessage.warning('请先登录')
    router.push('/login')
    return
  }

  clearLegacyRecommendCache()

  if (forceRefresh) {
    clearSessionCache()
    sessionId.value = null
    recommendedJobs.value = []
    hasMore.value = false
    rerankApplied.value = false
    rerankAvailable.value = false
  }

  if (!forceRefresh) {
    const cached = loadSessionCache()
    if (cached?.sessionId && Array.isArray(cached.result) && cached.result.length) {
      try {
        const statusRes = await getJobRecommendSessionStatus(cached.sessionId)
        sessionId.value = cached.sessionId
        recommendedJobs.value = cached.result.map((job) => ({ ...job, loading: false }))
        hasMore.value = cached.hasMore
        ranking.value = statusRes.ranking || cached.ranking || 'coarse'
        sessionStatus.value = statusRes.session_status || cached.sessionStatus || 'coarse_ready'
        rerankApplied.value = !!(statusRes.rerank_applied ?? cached.rerankApplied)
        rerankAvailable.value = !!(statusRes.rerank_available ?? (sessionStatus.value === 'rerank_ready'))
        if (rerankApplied.value) ranking.value = 'rerank'
        if (sessionStatus.value === 'reranking' || sessionStatus.value === 'rerank_queued') beginRerankWatch()
        return
      } catch {
        clearSessionCache()
      }
    }
  }

  pageLoading.value = true
  try {
    const res = await createJobRecommendSession(PAGE_SIZE)
    if (!res?.session_id) {
      throw new Error('推荐会话创建失败，请确认后端已重启')
    }
    sessionId.value = res.session_id
    recommendedJobs.value = (res.data || []).map((job) => ({ ...job, loading: false }))
    hasMore.value = !!res.has_more
    ranking.value = res.ranking || 'coarse'
    sessionStatus.value = res.session_status || 'coarse_ready'
    rerankApplied.value = false
    rerankAvailable.value = false
    saveSessionCache()
  } catch (error) {
    const detail = error?.response?.data?.detail || error.message || '未知错误'
    ElMessage.error('加载推荐职位失败: ' + detail)
  } finally {
    pageLoading.value = false
  }
}

const loadMore = async () => {
  if (!sessionId.value || !hasMore.value || loadingMore.value || pageLoading.value) return
  loadingMore.value = true
  try {
    const res = await getJobRecommendSessionMore(sessionId.value, shownJobIds.value, PAGE_SIZE)
    mergeResults(res.data || [])
    hasMore.value = !!res.has_more
    ranking.value = res.ranking || ranking.value
    sessionStatus.value = res.session_status || sessionStatus.value
    saveSessionCache()
  } catch (error) {
    ElMessage.error('加载更多失败: ' + (error.message || '未知错误'))
  } finally {
    loadingMore.value = false
  }
}

const onScroll = () => {
  const el = scrollRef.value
  if (!el || !hasMore.value || loadingMore.value) return
  if (el.scrollTop + el.clientHeight >= el.scrollHeight - 80) {
    loadMore()
  }
}

const loadMyResume = async () => {
  resumeLoading.value = true
  try {
    const list = await getResumeListAPI()
    const resumes = Array.isArray(list) ? list : (list?.data || [])
    if (!resumes.length) {
      myResume.value = null
      return
    }
    const pick = resumes.find((r) => r.is_default) || resumes[0]
    const detail = await getResumeDetailAPI(pick.id)
    myResume.value = detail?.data || detail || pick
  } catch {
    myResume.value = null
  } finally {
    resumeLoading.value = false
  }
}

const openJobDetail = (item) => {
  selectedJob.value = item.job || item
  jobDetailVisible.value = true
}

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

onMounted(async () => {
  clearLegacyRecommendCache()
  await loadMyResume()
  startSession(false)
})

onUnmounted(() => {
  stopRerankWatch()
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
.function-row {
  margin-bottom: 16px;
}

.recommend-row {
  align-items: stretch;
  margin-top: 4px;
}

.ref-column {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.ref-column :deep(.reference-panel) {
  min-height: 620px;
  max-height: calc(100vh - 220px);
}

.go-resume-btn {
  align-self: flex-start;
  margin-left: 8px;
  font-size: 13px;
}

.list-column {
  min-width: 0;
}

.list-panel {
  min-height: 620px;
  max-height: calc(100vh - 220px);
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  box-shadow: 0 4px 20px rgba(15, 23, 42, 0.05);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.list-panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  padding: 16px 20px;
  border-bottom: 1px solid #f1f5f9;
  background: #fafbfc;
}

.header-title {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.header-main {
  font-size: 15px;
  font-weight: 600;
  color: #1e293b;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.match-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.scroll-container {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 16px 20px 20px;
}

.dialog-compare {
  display: flex;
  gap: 20px;
  align-items: stretch;
  min-height: 440px;
}

.dialog-ref,
.dialog-job {
  flex: 1;
  min-width: 0;
  max-height: 560px;
  overflow: hidden;
}

.load-more-hint {
  text-align: center;
  padding: 16px 0 4px;
  color: #3b82f6;
  font-size: 13px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
}

.load-more-hint.muted {
  color: #94a3b8;
}

@media (max-width: 900px) {
  .dialog-compare {
    flex-direction: column;
  }
}

/* 左侧功能区 */
.function-card {
  border-radius: 12px;
  border: 1px solid #e2e8f0;
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

.scroll-container::-webkit-scrollbar {
  width: 6px;
}
.scroll-container::-webkit-scrollbar-thumb {
  background-color: #ddd;
  border-radius: 3px;
}
</style>